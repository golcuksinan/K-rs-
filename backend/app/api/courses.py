from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.masking import (
    DELETED_DEPARTMENT,
    DELETED_FACULTY,
    DELETED_UNIVERSITY,
    masked_name,
    masked_optional,
)
from app.db.session import get_db
from app.models.course import Course
from app.models.course_professor import CourseProfessor
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.common import Page
from app.schemas.course import CourseResponse, CourseCreate, CourseUpdate
from app.api.common import PageParams, get_active_or_400, get_active_or_404, like_pattern, page, paginate, pagination
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/courses", tags=["courses"])


MIN_SEARCH_LENGTH = 2

# CourseResponse tüm zinciri (bölüm/fakülte/üniversite) döndürdüğü için her sorguda önden
# çekilir; ilişkiler lazy bırakılırsa liste ucu satır başına 3 ek sorgu atar (N+1).
_CHAIN = joinedload(Course.department).joinedload(Department.faculty).joinedload(Faculty.university)


def _professor_counts(db: Session, course_ids: list[int]) -> dict[int, int]:
    """Ders id -> tekil hoca sayısı, tek sorguda. Satır değil hoca sayılır: aynı hocanın farklı
    dönemleri tek sayılır (`/professors`'daki course_count ile aynı kural)."""
    if not course_ids:
        return {}
    rows = (
        db.query(CourseProfessor.course_id, func.count(func.distinct(CourseProfessor.professor_id)))
        .filter(CourseProfessor.course_id.in_(course_ids))
        .group_by(CourseProfessor.course_id)
        .all()
    )
    return dict(rows)


def _to_response(course: Course, professor_count: int) -> CourseResponse:
    department = course.department
    faculty = department.faculty
    university = faculty.university
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        professor_count=professor_count,
        semester_min=course.semester_min,
        semester_max=course.semester_max,
        is_elective=course.is_elective,
        department_id=course.department_id,
        department_name=masked_name(department.deleted_at, department.name, DELETED_DEPARTMENT),
        faculty_id=faculty.id,
        faculty_name=masked_name(faculty.deleted_at, faculty.name, DELETED_FACULTY),
        university_id=university.id,
        university_name=masked_name(university.deleted_at, university.name, DELETED_UNIVERSITY),
        university_short_name=masked_optional(university.deleted_at, university.short_name),
        deleted_at=course.deleted_at,
    )


@router.get("", response_model=Page[CourseResponse])
def list_courses(
    department_id: int | None = Query(default=None, description="Bölüm ID (verilmezse search zorunlu)"),
    search: str | None = Query(default=None, description="Ders adı/kodunda arama"),
    is_elective: bool | None = Query(
        default=None, description="true=seçmeli, false=zorunlu; verilmezse ikisi de"
    ),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    if department_id is None and (search is None or len(search.strip()) < MIN_SEARCH_LENGTH):
        raise HTTPException(
            status_code=422,
            detail=f"department_id verilmediğinde search zorunludur (en az {MIN_SEARCH_LENGTH} karakter)",
        )

    query = db.query(Course).options(_CHAIN).filter(Course.deleted_at.is_(None))

    if department_id is not None:
        query = query.filter(Course.department_id == department_id)

    # is_elective NULL olan dersler (müfredat verisi olmayan) hiçbir filtre dalında dönmez —
    # "zorunlu" ile "bilinmiyor" aynı kovaya konmaz.
    if is_elective is not None:
        query = query.filter(Course.is_elective.is_(is_elective))

    if search:
        pattern = like_pattern(search)
        query = query.filter(
            Course.name.ilike(pattern, escape="\\") | Course.code.ilike(pattern, escape="\\")
        )

    courses, total = paginate(query.order_by(Course.name), params)
    counts = _professor_counts(db, [c.id for c in courses])

    return page([_to_response(c, counts.get(c.id, 0)) for c in courses], total, params)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    get_active_or_400(db, Department, payload.department_id, "department_id")

    course = Course(department_id=payload.department_id, name=payload.name, code=payload.code)
    db.add(course)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu bölümde bu isimde bir ders zaten var")
    db.refresh(course)
    return _to_response(course, 0)


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    course = get_active_or_404(db, Course, course_id, "Ders bulunamadı")

    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data:
        get_active_or_400(db, Department, data["department_id"], "department_id")

    for field, value in data.items():
        setattr(course, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu bölümde bu isimde bir ders zaten var")
    db.refresh(course)
    return _to_response(course, _professor_counts(db, [course.id]).get(course.id, 0))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    course = get_active_or_404(db, Course, course_id, "Ders bulunamadı")

    course.deleted_at = func.now()
    db.commit()
    return None
