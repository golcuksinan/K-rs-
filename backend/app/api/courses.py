from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.course import Course
from app.models.department import Department
from app.models.user import User
from app.schemas.course import CourseResponse, CourseCreate, CourseUpdate
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/courses", tags=["courses"])


def _to_response(course: Course) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        department_id=course.department_id,
        department_name="Silinmiş Bölüm" if course.department.deleted_at is not None else course.department.name,
        deleted_at=course.deleted_at,
    )


@router.get("", response_model=list[CourseResponse])
def list_courses(
    department_id: int = Query(...),
    search: str | None = Query(None),
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

    courses = query.order_by(Course.name).all()

    return [_to_response(c) for c in courses]


def _get_valid_department(db: Session, department_id: int) -> Department:
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.deleted_at.is_(None),
    ).first()
    if not department:
        raise HTTPException(status_code=400, detail="Geçersiz department_id")
    return department


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    _get_valid_department(db, payload.department_id)

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
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")

    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data:
        _get_valid_department(db, data["department_id"])

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
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")

    course.deleted_at = func.now()
    db.commit()
    return None
