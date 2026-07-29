from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.api.common import PageParams, page, paginate, pagination
from app.api.deps import get_optional_current_user
from app.core.masking import DELETED_COURSE, masked_name
from app.db.session import get_db
from app.models.course_professor import CourseProfessor
from app.models.enums import UserRole
from app.models.professor import Professor
from app.models.user import User
from app.schemas.common import Page
from app.schemas.professor import ProfessorDetail, ProfessorListItem, CourseProfessorSummary
from app.services.ratings import APPROVED, EMPTY_RATING, rating_by_course_professor, rating_by_professor

router = APIRouter(prefix="/professors", tags=["professors"])


@router.get("", response_model=Page[ProfessorListItem])
def list_professors(
    search: Optional[str] = Query(default=None, description="Hoca adında arama"),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    query = db.query(Professor)
    if search:
        # ⚠️ ILIKE Türkçe İ/ı eşleşmesi yapmaz (scraper'daki tr_casefold tuzağının arama karşılığı).
        query = query.filter(Professor.full_name.ilike(f"%{search}%"))

    professors, total = paginate(query.order_by(Professor.full_name), params)

    ids = [p.id for p in professors]
    ratings = rating_by_professor(db, ids)
    course_counts = dict(
        db.query(CourseProfessor.professor_id, func.count(func.distinct(CourseProfessor.course_id)))
        .filter(CourseProfessor.professor_id.in_(ids))
        .group_by(CourseProfessor.professor_id)
        .all()
    ) if ids else {}

    items = []
    for p in professors:
        rating = ratings.get(p.id, EMPTY_RATING)
        items.append(ProfessorListItem(
            id=p.id,
            full_name=p.full_name,
            title=p.title,
            course_count=course_counts.get(p.id, 0),
            review_count=rating.review_count,
            average_teaching_score=rating.average_teaching_score,
            average_difficulty_score=rating.average_difficulty_score,
            average_fairness_score=rating.average_fairness_score,
        ))

    return page(items, total, params)


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
