import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.db.session import get_db
from app.models.course import Course
from app.models.course_professor import CourseProfessor
from app.models.user import User
from app.models.enums import UserRole
from app.api.deps import get_optional_current_user
from app.schemas.course_professor import CourseProfessorDetail, CourseProfessorListItem

router = APIRouter(prefix="/course-professors", tags=["course-professors"])

_SEASON_ORDER = {"güz": 0, "bahar": 1}

def _average(values: list[int]) -> Optional[float]:
    return sum(values) / len(values) if values else None

def _course_name(course: Course) -> str:
    return "Silinmiş Ders" if course.deleted_at is not None else course.name

def _parse_term_key(term: str) -> tuple[int, int]:
    """'2025-2026 Güz' -> (2025, 0). Bilinmeyen formatı en sona atar."""
    match = re.match(r"(\d{4})-\d{4}\s+(\S+)", term.strip())
    if not match:
        return (0, -1)
    start_year = int(match.group(1))
    season_rank = _SEASON_ORDER.get(match.group(2).lower(), -1)
    return (start_year, season_rank)

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
        course_name=_course_name(cp.course),
        course_code=cp.course.code,
        professor_name=cp.professor.full_name,
        term=cp.term,
        average_teaching_score=_average([r.teaching_score for r in approved]),
        average_difficulty_score=_average([r.difficulty_score for r in approved]),
        average_fairness_score=_average([r.fairness_score for r in approved]),
        review_count=len(approved),
        reviews=reviews_to_show,
    )

@router.get("", response_model=List[CourseProfessorListItem])
def list_course_professors(
    course_id: int,
    term: Optional[str] = None,
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")

    if term is None:
        terms = [
            row[0]
            for row in db.query(CourseProfessor.term)
            .filter(CourseProfessor.course_id == course_id)
            .distinct()
        ]
        term = max(terms, key=_parse_term_key) if terms else None

    query = (
        db.query(CourseProfessor)
        .options(joinedload(CourseProfessor.professor))
        .filter(CourseProfessor.course_id == course_id)
    )
    if term is not None:
        query = query.filter(CourseProfessor.term == term)

    result = []
    for cp in query.all():
        approved = [r for r in cp.reviews if r.status == "approved"]
        result.append(
            CourseProfessorListItem(
                id=cp.id,
                professor_name=cp.professor.full_name,
                term=cp.term,
                avg_teaching=_average([r.teaching_score for r in approved]),
                avg_difficulty=_average([r.difficulty_score for r in approved]),
                avg_fairness=_average([r.fairness_score for r in approved]),
            )
        )
    return result