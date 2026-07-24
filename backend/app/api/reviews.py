from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.review import Review
from app.models.report import Report
from app.models.course_professor import CourseProfessor
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStatusUpdate, ReviewFullResponse, ReviewUpdate
from app.api.deps import get_current_user, get_current_admin_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------- 1. Review oluştur ----------

@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_professor = db.query(CourseProfessor).filter(
        CourseProfessor.id == payload.course_professor_id
    ).first()
    if not course_professor:
        raise HTTPException(status_code=404, detail="Ders/hoca eşleşmesi bulunamadı")

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
    return review

@router.get("/me", response_model=list[ReviewFullResponse])
def list_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Review)
        .filter(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )

@router.patch("/{review_id}", response_model=ReviewFullResponse)
def update_my_review(
    review_id: int,
    payload: ReviewUpdate,
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
    else:
        # pending / rejected -> direkt güncellenir, tekrar onaya düşer
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
    db.refresh(review)
    return review

# ---------- 2. Review listele (onaylanmış olanlar, herkese açık) ----------

@router.get("", response_model=list[ReviewResponse])
def list_reviews(
    course_professor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(Review.status == "approved")

    if course_professor_id is not None:
        query = query.filter(Review.course_professor_id == course_professor_id)

    return query.order_by(Review.created_at.desc()).all()


# ---------- 3. Bekleyen review'ları listele (sadece admin) ----------

@router.get("/pending", response_model=list[ReviewFullResponse])
def list_pending_reviews(
    course_professor_id: Optional[int] = None,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(
        or_(Review.status == "pending", Review.has_pending_edit == True)  # noqa: E712
    )

    if course_professor_id is not None:
        query = query.filter(Review.course_professor_id == course_professor_id)

    return query.order_by(Review.created_at.asc()).all()


# ---------- 4. Review durumunu güncelle (sadece admin) ----------

@router.patch("/{review_id}/status", response_model=ReviewResponse)
def update_review_status(
    review_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Değerlendirme bulunamadı")

    if review.has_pending_edit:
        # bu bir edit onayı/reddi
        if payload.status == "approved":
            review.teaching_score = review.pending_teaching_score
            review.difficulty_score = review.pending_difficulty_score
            review.fairness_score = review.pending_fairness_score
            review.comment = review.pending_comment
        # approve veya reject fark etmeksizin gölge temizlenir
        review.pending_teaching_score = None
        review.pending_difficulty_score = None
        review.pending_fairness_score = None
        review.pending_comment = None
        review.has_pending_edit = False
        # review.status zaten "approved" idi, dokunulmuyor
    else:
        # normal ilk review onayı/reddi
        review.status = payload.status

    db.commit()
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