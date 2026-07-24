from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.course_professor import CourseProfessor
from app.models.user import User
from app.models.enums import UserRole
from app.api.deps import get_optional_current_user
from app.schemas.course_professor import CourseProfessorDetail

router = APIRouter(prefix="/course-professors", tags=["course-professors"])


def _average(values: list[int]) -> Optional[float]:
    return sum(values) / len(values) if values else None


@router.get("/{course_professor_id}", response_model=CourseProfessorDetail)
def get_course_professor_detail(
    course_professor_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    cp = db.query(CourseProfessor).filter(
        CourseProfessor.id == course_professor_id
    ).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Ders/hoca eşleşmesi bulunamadı")

    is_admin = current_user is not None and current_user.role == UserRole.admin

    approved = [r for r in cp.reviews if r.status == "approved"]
    reviews_to_show = cp.reviews if is_admin else approved

    return CourseProfessorDetail(
        id=cp.id,
        course_name=cp.course.name,
        course_code=cp.course.code,
        professor_name=cp.professor.full_name,
        term=cp.term,
        average_teaching_score=_average([r.teaching_score for r in approved]),
        average_difficulty_score=_average([r.difficulty_score for r in approved]),
        average_fairness_score=_average([r.fairness_score for r in approved]),
        review_count=len(approved),
        reviews=reviews_to_show,
    )