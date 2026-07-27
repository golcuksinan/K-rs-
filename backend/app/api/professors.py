from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.api.deps import get_optional_current_user
from app.core.masking import DELETED_COURSE, masked_name
from app.db.session import get_db
from app.models.course_professor import CourseProfessor
from app.models.enums import UserRole
from app.models.professor import Professor
from app.models.user import User
from app.schemas.professor import ProfessorDetail, CourseProfessorSummary
from app.services.ratings import APPROVED, EMPTY_RATING, rating_by_course_professor

router = APIRouter(prefix="/professors", tags=["professors"])


@router.get("/{professor_id}", response_model=ProfessorDetail)
def get_professor_detail(
    professor_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    professor = (
        db.query(Professor)
        .options(
            joinedload(Professor.course_professors).joinedload(CourseProfessor.course),
            joinedload(Professor.course_professors).joinedload(CourseProfessor.reviews),
        )
        .filter(Professor.id == professor_id)
        .first()
    )
    if not professor:
        raise HTTPException(status_code=404, detail="Hoca bulunamadı")

    is_admin = current_user is not None and current_user.role == UserRole.admin

    ratings = rating_by_course_professor(db, [cp.id for cp in professor.course_professors])

    course_summaries = []
    all_reviews = []

    for cp in professor.course_professors:
        rating = ratings.get(cp.id, EMPTY_RATING)
        all_reviews.extend(
            cp.reviews if is_admin else [r for r in cp.reviews if r.status == APPROVED]
        )

        course_summaries.append(CourseProfessorSummary(
            id=cp.id,
            course_name=masked_name(cp.course.deleted_at, cp.course.name, DELETED_COURSE),
            course_code=cp.course.code,
            term=cp.term,
            average_teaching_score=rating.average_teaching_score,
            average_difficulty_score=rating.average_difficulty_score,
            average_fairness_score=rating.average_fairness_score,
            review_count=rating.review_count,
        ))

    return ProfessorDetail(
        id=professor.id,
        full_name=professor.full_name,
        courses=course_summaries,
        reviews=all_reviews,
    )
