from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.api.common import PageParams, page, paginate, pagination, search_filter
from app.core.masking import DELETED_COURSE, masked_name
from app.db.session import get_db
from app.models.course import Course
from app.models.course_professor import CourseProfessor
from app.models.professor import Professor
from app.schemas.common import Page
from app.schemas.professor import ProfessorCourseSummary, ProfessorCourseTerm, ProfessorDetail, ProfessorListItem
from app.services.ratings import EMPTY_RATING, rating_by_course, rating_by_professor

router = APIRouter(prefix="/professors", tags=["professors"])


@router.get("", response_model=Page[ProfessorListItem])
def list_professors(
    search: Optional[str] = Query(default=None, description="Hoca adında arama"),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    query = db.query(Professor)
    if search:
        query = query.filter(search_filter(Professor.full_name, search))

    professors, total = paginate(query.order_by(Professor.full_name), params)

    ids = [p.id for p in professors]
    ratings = rating_by_professor(db, ids)
    course_counts = dict(
        db.query(CourseProfessor.professor_id, func.count(func.distinct(CourseProfessor.course_id)))
        .join(Course, Course.id == CourseProfessor.course_id)
        .filter(CourseProfessor.professor_id.in_(ids), Course.deleted_at.is_(None))
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
):
    professor = (
        db.query(Professor)
        .options(joinedload(Professor.course_professors).joinedload(CourseProfessor.course))
        .filter(Professor.id == professor_id)
        .first()
    )
    if not professor:
        raise HTTPException(status_code=404, detail="Hoca bulunamadı")

    ratings = rating_by_course(db, professor.id)

    grouped: dict[int, list[CourseProfessor]] = {}
    for cp in professor.course_professors:
        grouped.setdefault(cp.course_id, []).append(cp)

    course_summaries = []
    for course_id, cps in grouped.items():
        course = cps[0].course
        rating = ratings.get(course_id, EMPTY_RATING)
        course_summaries.append(ProfessorCourseSummary(
            course_id=course_id,
            course_code=course.code,
            course_name=masked_name(course.deleted_at, course.name, DELETED_COURSE),
            terms=[
                ProfessorCourseTerm(course_professor_id=cp.id, term=cp.term)
                for cp in sorted(cps, key=lambda cp: cp.term)
            ],
            average_teaching_score=rating.average_teaching_score,
            average_difficulty_score=rating.average_difficulty_score,
            average_fairness_score=rating.average_fairness_score,
            review_count=rating.review_count,
        ))

    return ProfessorDetail(
        id=professor.id,
        full_name=professor.full_name,
        courses=course_summaries,
    )
