from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.professor import Professor
from app.models.user import User
from app.models.enums import UserRole
from app.api.deps import get_optional_current_user
from app.api.course_professors import _average
from app.schemas.professor import ProfessorDetail, CourseProfessorSummary

router = APIRouter(prefix="/professors", tags=["professors"])


@router.get("/{professor_id}", response_model=ProfessorDetail)
def get_professor_detail(
    professor_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    professor = db.query(Professor).filter(Professor.id == professor_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail="Hoca bulunamadı")

    is_admin = current_user is not None and current_user.role == UserRole.admin

    course_summaries = []
    all_reviews = []

    for cp in professor.course_professors:
        approved = [r for r in cp.reviews if r.status == "approved"]
        all_reviews.extend(cp.reviews if is_admin else approved)

        course_summaries.append(CourseProfessorSummary(
            id=cp.id,
            course_name=cp.course.name,
            course_code=cp.course.code,
            term=cp.term,
            average_teaching_score=_average([r.teaching_score for r in approved]),
            average_difficulty_score=_average([r.difficulty_score for r in approved]),
            average_fairness_score=_average([r.fairness_score for r in approved]),
            review_count=len(approved),
        ))

    return ProfessorDetail(
        id=professor.id,
        full_name=professor.full_name,
        courses=course_summaries,
        reviews=all_reviews,
    )