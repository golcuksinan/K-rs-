from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.models.course import Course
from app.models.user import User
from app.models.review import Review
from app.models.report import Report
from app.models.course_professor import CourseProfessor
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStatusUpdate, ReviewFullResponse, ReviewUpdate
from app.api.common import PageParams, get_active_or_400, pagination, paginated
from app.api.deps import get_current_user, get_current_admin_user, get_optional_current_user
from app.services.ai_service import moderate_review
from app.services.metrics import Event, increment

router = APIRouter(prefix="/reviews", tags=["reviews"])


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
    background_tasks.add_task(_run_moderation_background, review.id)
    return review

@router.get("/me", response_model=Page[ReviewFullResponse])
def list_my_reviews(
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Review)
        .filter(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
    )
    return paginated(query, params)

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
        background_tasks.add_task(_run_moderation_background, review.id)

    db.refresh(review)
    return review


@router.get("", response_model=Page[ReviewResponse])
def list_reviews(
    course_professor_id: Optional[int] = None,
    professor_id: Optional[int] = None,
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
    if professor_id is not None:
        query = query.join(
            CourseProfessor, CourseProfessor.id == Review.course_professor_id
        ).filter(CourseProfessor.professor_id == professor_id)

    return paginated(query.order_by(Review.created_at.desc()), params)


@router.get("/pending", response_model=Page[ReviewFullResponse])
def list_pending_reviews(
    course_professor_id: Optional[int] = None,
    params: PageParams = Depends(pagination),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(
        or_(Review.status == "pending", Review.has_pending_edit == True)  # noqa: E712
    )

    if course_professor_id is not None:
        query = query.filter(Review.course_professor_id == course_professor_id)

    return paginated(query.order_by(Review.created_at.asc()), params)


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
    return review

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