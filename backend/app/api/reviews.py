import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.academic import MAX_STUDY_YEARS, parse_term_start_year
from app.core.config import settings
from app.core.masking import DELETED_COURSE, masked_name
from app.db.session import get_db, SessionLocal
from app.models.course import Course, CourseDepartment
from app.models.user import User
from app.models.review import Review
from app.models.report import Report
from app.models.course_professor import CourseProfessor
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStatusUpdate, ReviewFullResponse, ReviewUpdate
from app.api.common import PageParams, get_active_or_400, page, paginate, paginated, pagination
from app.api.deps import get_current_user, get_current_admin_user, get_optional_current_user
from app.services.ai_service import moderate_review
from app.services.metrics import Event, increment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Liste uçlarında N+1 olmasın diye eşleşme zinciri tek sorguda çekilir.
_CP_LOAD = (
    joinedload(Review.course_professor).joinedload(CourseProfessor.course),
    joinedload(Review.course_professor).joinedload(CourseProfessor.professor),
)


def _full_response(review: Review) -> ReviewFullResponse:
    cp = review.course_professor
    return ReviewFullResponse(
        id=review.id,
        course_professor_id=review.course_professor_id,
        teaching_score=review.teaching_score,
        difficulty_score=review.difficulty_score,
        fairness_score=review.fairness_score,
        comment=review.comment,
        status=review.status,
        created_at=review.created_at,
        course_name=masked_name(cp.course.deleted_at, cp.course.name, DELETED_COURSE),
        course_code=cp.course.code,
        professor_name=cp.professor.full_name,
        term=cp.term,
        has_pending_edit=review.has_pending_edit,
        pending_teaching_score=review.pending_teaching_score,
        pending_difficulty_score=review.pending_difficulty_score,
        pending_fairness_score=review.pending_fairness_score,
        pending_comment=review.pending_comment,
    )


def _schedule_moderation(background_tasks: BackgroundTasks, review_id: int):
    # Bayrak kapalıyken hiç sıraya alınmaz: yorum pending'de kalır, kararı admin verir.
    if settings.AI_MODERATION_ENABLED:
        background_tasks.add_task(_run_moderation_background, review_id)


def _run_moderation_background(review_id: int):
    # HF çağrısı saniyeler sürebilir; hiçbir DB transaction'ı onu kapsamamalı, yoksa
    # bağlantı o süre boyunca havuzdan çıkmış hâlde idle in transaction bekler.
    db = SessionLocal()
    try:
        row = db.query(Review.comment).filter(Review.id == review_id).first()
    finally:
        db.close()
    if row is None:
        return
    moderated_comment = row[0]

    verdict = moderate_review(moderated_comment)

    db = SessionLocal()
    try:
        # HF çağrısı sürerken araya admin kararı (status artık pending değil) veya kullanıcı
        # düzenlemesi (comment değişti) girmiş olabilir; ikisi de bu task'ı geçersiz kılar —
        # değişen metni zaten yeni bir task moderasyona sokmuştur.
        db.query(Review).filter(
            Review.id == review_id,
            Review.status == "pending",
            Review.comment == moderated_comment,
        ).update({"status": verdict}, synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        # Yanıt gönderildikten sonra koşuyor: hata yutulursa yorum kimsenin haberi olmadan
        # pending'de kalır, kullanıcıya da bir işaret gitmez.
        logger.exception("Moderasyon sonucu yazılamadı: review_id=%s", review_id)
    finally:
        db.close()


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_professor = db.query(CourseProfessor).filter(
        CourseProfessor.id == payload.course_professor_id
    ).first()
    if not course_professor:
        raise HTTPException(status_code=404, detail="Ders/hoca eşleşmesi bulunamadı")
    course = get_active_or_400(db, Course, course_professor.course_id, "course_id")
    if course.university_id != current_user.department.faculty.university_id:
        raise HTTPException(
            status_code=403,
            detail="Yalnızca kendi üniversitenizin derslerini değerlendirebilirsiniz",
        )

    in_curriculum = db.query(CourseDepartment).filter(
        CourseDepartment.course_id == course.id,
        CourseDepartment.department_id == current_user.department_id,
    ).first()
    if not in_curriculum:
        raise HTTPException(
            status_code=403,
            detail="Bu ders bölümünüzün müfredatında değil",
        )

    # Dersi gerçekten aldığını doğrulayacak bir kaynak yok; en azından dönem kayıt yılına
    # göre makul olmalı. Biçimi tanınmayan dönem etiketinde kontrol atlanır.
    term_year = parse_term_start_year(course_professor.term)
    if term_year is not None and not (
        current_user.enrollment_year <= term_year <= current_user.enrollment_year + MAX_STUDY_YEARS
    ):
        raise HTTPException(status_code=400, detail="Bu dönem kayıt yılınıza uymuyor")

    review = Review(
        user_id=current_user.id,
        course_professor_id=payload.course_professor_id,
        teaching_score=payload.teaching_score,
        difficulty_score=payload.difficulty_score,
        fairness_score=payload.fairness_score,
        comment=payload.comment,
    )
    db.add(review)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Bu derse zaten bir değerlendirme yaptınız",
        )

    db.refresh(review)
    increment(Event.REVIEW_CREATED)
    # review.status model default'u "pending" — AI moderasyonu arka planda çalışıp güncelleyecek
    _schedule_moderation(background_tasks, review.id)
    return review

@router.get("/me", response_model=Page[ReviewFullResponse])
def list_my_reviews(
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Review)
        .options(*_CP_LOAD)
        .filter(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
    )
    reviews, total = paginate(query, params)
    return page([_full_response(review) for review in reviews], total, params)

@router.patch("/{review_id}", response_model=ReviewFullResponse)
def update_my_review(
    review_id: int,
    payload: ReviewUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Değerlendirme bulunamadı")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu değerlendirme size ait değil")

    if review.status == "approved":
        # onaylanmış review'ın canlı hali değişmez, düzenleme admin onayına düşer
        review.pending_teaching_score = payload.teaching_score
        review.pending_difficulty_score = payload.difficulty_score
        review.pending_fairness_score = payload.fairness_score
        review.pending_comment = payload.comment
        review.has_pending_edit = True
        db.commit()
        increment(Event.REVIEW_EDIT_REQUESTED)
    else:
        # pending / rejected -> direkt güncellenir, create ile aynı moderasyon döngüsüne girer
        review.teaching_score = payload.teaching_score
        review.difficulty_score = payload.difficulty_score
        review.fairness_score = payload.fairness_score
        review.comment = payload.comment
        review.status = "pending"
        review.has_pending_edit = False
        review.pending_teaching_score = None
        review.pending_difficulty_score = None
        review.pending_fairness_score = None
        review.pending_comment = None
        db.commit()
        _schedule_moderation(background_tasks, review.id)

    db.refresh(review)
    return _full_response(review)


@router.get("", response_model=Page[ReviewResponse])
def list_reviews(
    course_professor_id: Optional[int] = None,
    professor_id: Optional[int] = None,
    course_id: Optional[int] = None,
    status: Optional[Literal["approved", "pending", "rejected"]] = None,
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    if status is not None and (current_user is None or current_user.role != UserRole.admin):
        raise HTTPException(status_code=403, detail="status filtresi yalnızca adminler içindir")

    query = db.query(Review).filter(Review.status == (status or "approved"))

    if course_professor_id is not None:
        query = query.filter(Review.course_professor_id == course_professor_id)
    # İki filtre birlikte verilebilir, join yalnızca bir kez kurulur.
    if professor_id is not None or course_id is not None:
        query = query.join(CourseProfessor, CourseProfessor.id == Review.course_professor_id)
        if professor_id is not None:
            query = query.filter(CourseProfessor.professor_id == professor_id)
        if course_id is not None:
            query = query.filter(CourseProfessor.course_id == course_id)

    return paginated(query.order_by(Review.created_at.desc()), params)


@router.get("/pending", response_model=Page[ReviewFullResponse])
def list_pending_reviews(
    course_professor_id: Optional[int] = None,
    params: PageParams = Depends(pagination),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Review).options(*_CP_LOAD).filter(
        or_(Review.status == "pending", Review.has_pending_edit == True)  # noqa: E712
    )

    if course_professor_id is not None:
        query = query.filter(Review.course_professor_id == course_professor_id)

    reviews, total = paginate(query.order_by(Review.created_at.asc()), params)
    return page([_full_response(review) for review in reviews], total, params)


@router.patch("/{review_id}/status", response_model=ReviewResponse)
def update_review_status(
    review_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Review'un KENDİSİNİN onayı/reddi. Bekleyen edit'in kararı ayrı uçta (/edit-status);
    burada reject, edit beklese bile review'u komple yayından kaldırır."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Değerlendirme bulunamadı")

    review.status = payload.status
    if payload.status == "rejected" and review.has_pending_edit:
        # reddedilen review'un bekleyen edit'i anlamını yitirir, kuyruğda da kalmamalı
        review.pending_teaching_score = None
        review.pending_difficulty_score = None
        review.pending_fairness_score = None
        review.pending_comment = None
        review.has_pending_edit = False

    db.commit()
    increment(Event.REVIEW_APPROVED if payload.status == "approved" else Event.REVIEW_REJECTED)
    db.refresh(review)
    return review


@router.patch("/{review_id}/edit-status", response_model=ReviewFullResponse)
def update_review_edit_status(
    review_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Bekleyen edit'in onayı/reddi. approve gölge alanları asıl alanlara kopyalar,
    reject sadece temizler; iki durumda da review.status'a dokunulmaz (approved kalır)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Değerlendirme bulunamadı")
    if not review.has_pending_edit:
        raise HTTPException(status_code=400, detail="Bu değerlendirmenin bekleyen bir düzenlemesi yok")

    if payload.status == "approved":
        review.teaching_score = review.pending_teaching_score
        review.difficulty_score = review.pending_difficulty_score
        review.fairness_score = review.pending_fairness_score
        review.comment = review.pending_comment
    review.pending_teaching_score = None
    review.pending_difficulty_score = None
    review.pending_fairness_score = None
    review.pending_comment = None
    review.has_pending_edit = False

    db.commit()
    increment(
        Event.REVIEW_EDIT_APPROVED if payload.status == "approved" else Event.REVIEW_EDIT_REJECTED
    )
    db.refresh(review)
    return _full_response(review)

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review bulunamadı")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu review'u silme yetkiniz yok")

    db.query(Report).filter(Report.review_id == review_id).delete(synchronize_session=False)
    db.delete(review)
    db.commit()
    return None