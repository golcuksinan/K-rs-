from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.course import Course
from app.schemas.course import CourseResponse

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("", response_model=list[CourseResponse])
def list_courses(
    department_id: int = Query(...),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Course)
        .options(joinedload(Course.department))
        .filter(Course.department_id == department_id)
    )

    if search:
        query = query.filter(
            (Course.name.ilike(f"%{search}%")) | (Course.code.ilike(f"%{search}%"))
        )

    courses = query.order_by(Course.name).all()

    return [
        CourseResponse(
            id=c.id,
            name=c.name,
            code=c.code,
            department_id=c.department_id,
            department_name="Silinmiş Bölüm" if c.department.deleted_at is not None else c.department.name,
        )
        for c in courses
    ]