import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.api.common import PageParams, get_active_or_400, page, paginate, pagination
from app.api.deps import get_current_admin_user, get_optional_current_user
from app.core.masking import DELETED_COURSE, masked_name
from app.db.session import get_db
from app.models.course import Course
from app.models.course_professor import CourseProfessor
from app.models.enums import UserRole
from app.models.professor import Professor
from app.models.user import User
from app.schemas.common import Page
from app.schemas.course_professor import (
    CourseProfessorCreate,
    CourseProfessorDetail,
    CourseProfessorListItem,
    CourseProfessorResponse,
)
from app.services.ratings import APPROVED, EMPTY_RATING, rating_by_course_professor

router = APIRouter(prefix="/course-professors", tags=["course-professors"])

# Akademik kronoloji: yıllık ders güz başlangıçlıdır, yaz okulu yılın en son dönemidir.
_SEASON_ORDER = {"güz": 0, "yıllık": 1, "bahar": 2, "yaz": 3}

def _parse_term_key(term: str) -> tuple[int, int]:
    """'2025-2026 Güz' -> (2025, 0). Bilinmeyen formatı ve bilinmeyen dönemi en sona atar."""
    match = re.match(r"(\d{4})-\d{4}\s+(\S+)", term.strip())
    if not match:
        return (0, -1)
    start_year = int(match.group(1))
    season_rank = _SEASON_ORDER.get(match.group(2).lower(), -1)
    return (start_year, season_rank)


def _latest_term(terms: list[str]) -> str:
    """Aynı anahtara düşen dönemlerde (ör. iki ayrıştırılamayan metin) seçim string'e göre
    kırılır — yoksa sonuç Postgres'in satır sırasına kalır, deterministik olmaz."""
    return max(terms, key=lambda t: (_parse_term_key(t), t))

@router.post("", response_model=CourseProfessorResponse, status_code=status.HTTP_201_CREATED)
def create_course_professor(
    payload: CourseProfessorCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    get_active_or_400(db, Course, payload.course_id, "course_id")
    if not db.query(Professor).filter(Professor.id == payload.professor_id).first():
        raise HTTPException(status_code=400, detail="Geçersiz professor_id")

    cp = CourseProfessor(
        course_id=payload.course_id,
        professor_id=payload.professor_id,
        term=payload.term,
    )
    db.add(cp)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu ders/hoca/dönem eşleşmesi zaten var")
    db.refresh(cp)
    return cp


@router.get("/{course_professor_id}", response_model=CourseProfessorDetail)
def get_course_professor_detail(
    course_professor_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    cp = (
        db.query(CourseProfessor)
        .options(
            joinedload(CourseProfessor.course),
            joinedload(CourseProfessor.professor),
            joinedload(CourseProfessor.reviews),
        )
        .filter(CourseProfessor.id == course_professor_id)
        .first()
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Ders/hoca eşleşmesi bulunamadı")

    is_admin = current_user is not None and current_user.role == UserRole.admin

    # Ortalamalar her zaman sadece approved'dan (ratings servisi garanti eder);
    # review listesi admin'e hepsi, public'e sadece approved.
    rating = rating_by_course_professor(db, [cp.id]).get(cp.id, EMPTY_RATING)
    reviews_to_show = cp.reviews if is_admin else [r for r in cp.reviews if r.status == APPROVED]

    return CourseProfessorDetail(
        id=cp.id,
        course_name=masked_name(cp.course.deleted_at, cp.course.name, DELETED_COURSE),
        course_code=cp.course.code,
        professor_name=cp.professor.full_name,
        term=cp.term,
        average_teaching_score=rating.average_teaching_score,
        average_difficulty_score=rating.average_difficulty_score,
        average_fairness_score=rating.average_fairness_score,
        review_count=rating.review_count,
        reviews=reviews_to_show,
    )

@router.get("", response_model=Page[CourseProfessorListItem])
def list_course_professors(
    course_id: int,
    term: Optional[str] = None,
    params: PageParams = Depends(pagination),
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
        term = _latest_term(terms) if terms else None

    query = (
        db.query(CourseProfessor)
        .options(joinedload(CourseProfessor.professor))
        .filter(CourseProfessor.course_id == course_id)
    )
    if term is not None:
        query = query.filter(CourseProfessor.term == term)

    course_professors, total = paginate(query.order_by(CourseProfessor.id), params)
    ratings = rating_by_course_professor(db, [cp.id for cp in course_professors])

    items = []
    for cp in course_professors:
        rating = ratings.get(cp.id, EMPTY_RATING)
        items.append(
            CourseProfessorListItem(
                id=cp.id,
                professor_name=cp.professor.full_name,
                term=cp.term,
                avg_teaching=rating.average_teaching_score,
                avg_difficulty=rating.average_difficulty_score,
                avg_fairness=rating.average_fairness_score,
            )
        )
    return page(items, total, params)
