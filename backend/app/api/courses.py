from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.masking import DELETED_DEPARTMENT, masked_name
from app.db.session import get_db
from app.models.course import Course
from app.models.department import Department
from app.models.user import User
from app.schemas.common import Page
from app.schemas.course import CourseResponse, CourseCreate, CourseUpdate
from app.api.common import PageParams, get_active_or_400, get_active_or_404, page, paginate, pagination
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/courses", tags=["courses"])


def _to_response(course: Course) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        department_id=course.department_id,
        department_name=masked_name(
            course.department.deleted_at, course.department.name, DELETED_DEPARTMENT
        ),
        deleted_at=course.deleted_at,
    )


@router.get("", response_model=Page[CourseResponse])
def list_courses(
    department_id: int = Query(...),
    search: str | None = Query(None),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Course)
        .options(joinedload(Course.department))
        .filter(Course.department_id == department_id, Course.deleted_at.is_(None))
    )

    if search:
        query = query.filter(
            (Course.name.ilike(f"%{search}%")) | (Course.code.ilike(f"%{search}%"))
        )

    courses, total = paginate(query.order_by(Course.name), params)

    return page([_to_response(c) for c in courses], total, params)


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
    return _to_response(course)


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
    return _to_response(course)


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
