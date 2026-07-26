from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.faculty import Faculty
from app.models.university import University
from app.models.user import User
from app.schemas.faculty import FacultyResponse, FacultyCreate, FacultyUpdate
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.get("", response_model=List[FacultyResponse])
def list_faculties(
    university_id: int = Query(..., description="Üniversite ID (zorunlu)"),
    search: Optional[str] = Query(default=None, description="Fakülte adında arama"),
    db: Session = Depends(get_db),
):
    query = db.query(Faculty).filter(
        Faculty.university_id == university_id,
        Faculty.deleted_at.is_(None),
    )
    if search:
        query = query.filter(Faculty.name.ilike(f"%{search}%"))
    return query.order_by(Faculty.name).all()


def _get_valid_university(db: Session, university_id: int) -> University:
    university = db.query(University).filter(
        University.id == university_id,
        University.deleted_at.is_(None),
    ).first()
    if not university:
        raise HTTPException(status_code=400, detail="Geçersiz university_id")
    return university


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    _get_valid_university(db, payload.university_id)

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
    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id,
        Faculty.deleted_at.is_(None),
    ).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Fakülte bulunamadı")

    data = payload.model_dump(exclude_unset=True)
    if "university_id" in data:
        _get_valid_university(db, data["university_id"])

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
    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id,
        Faculty.deleted_at.is_(None),
    ).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Fakülte bulunamadı")

    faculty.deleted_at = func.now()
    db.commit()
    return None