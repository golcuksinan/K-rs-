from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.faculty import Faculty
from app.models.university import University
from app.models.user import User
from app.schemas.common import Page
from app.schemas.faculty import FacultyResponse, FacultyCreate, FacultyUpdate
from app.api.common import PageParams, get_active_or_400, get_active_or_404, pagination, paginated
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.get("", response_model=Page[FacultyResponse])
def list_faculties(
    university_id: int = Query(..., description="Üniversite ID (zorunlu)"),
    search: Optional[str] = Query(default=None, description="Fakülte adında arama"),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    query = db.query(Faculty).filter(
        Faculty.university_id == university_id,
        Faculty.deleted_at.is_(None),
    )
    if search:
        query = query.filter(Faculty.name.ilike(f"%{search}%"))
    return paginated(query.order_by(Faculty.name), params)


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    get_active_or_400(db, University, payload.university_id, "university_id")

    faculty = Faculty(university_id=payload.university_id, name=payload.name)
    db.add(faculty)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu üniversitede bu isimde bir fakülte zaten var")
    db.refresh(faculty)
    return faculty


@router.patch("/{faculty_id}", response_model=FacultyResponse)
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    faculty = get_active_or_404(db, Faculty, faculty_id, "Fakülte bulunamadı")

    data = payload.model_dump(exclude_unset=True)
    if "university_id" in data:
        get_active_or_400(db, University, data["university_id"], "university_id")

    for field, value in data.items():
        setattr(faculty, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu üniversitede bu isimde bir fakülte zaten var")
    db.refresh(faculty)
    return faculty


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    faculty = get_active_or_404(db, Faculty, faculty_id, "Fakülte bulunamadı")

    faculty.deleted_at = func.now()
    db.commit()
    return None