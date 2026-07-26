from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.department import DepartmentGroupResponse, DepartmentResponse, DepartmentCreate, DepartmentUpdate
from app.schemas.faculty import FacultyResponse
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=Union[List[DepartmentResponse], List[DepartmentGroupResponse]])
def list_departments(
    faculty_id: Optional[int] = Query(default=None, description="Fakülte ID (verilirse düz liste döner)"),
    search: Optional[str] = Query(default=None, description="Bölüm adında arama"),
    db: Session = Depends(get_db),
):
    if faculty_id is not None:
        query = db.query(Department).filter(
            Department.faculty_id == faculty_id,
            Department.deleted_at.is_(None),
        )
        if search:
            query = query.filter(Department.name.ilike(f"%{search}%"))
        return query.order_by(Department.name).all()

    if not search:
        raise HTTPException(status_code=422, detail="faculty_id veya search parametrelerinden biri gönderilmeli")

    departments = db.query(Department).filter(
        Department.name.ilike(f"%{search}%"),
        Department.deleted_at.is_(None),
    ).all()

    groups: dict[str, list] = {}
    for dept in departments:
        groups.setdefault(dept.name, []).append(dept.faculty)

    return [
        DepartmentGroupResponse(
            department_name=name,
            faculties=[
                FacultyResponse(
                    id=fac.id,
                    name="Silinmiş Fakülte" if fac.deleted_at is not None else fac.name,
                    university_id=fac.university_id,
                    deleted_at=fac.deleted_at,
                )
                for fac in facs
            ],
        )
        for name, facs in sorted(groups.items())
    ]


def _get_valid_faculty(db: Session, faculty_id: int) -> Faculty:
    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id,
        Faculty.deleted_at.is_(None),
    ).first()
    if not faculty:
        raise HTTPException(status_code=400, detail="Geçersiz faculty_id")
    return faculty


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    _get_valid_faculty(db, payload.faculty_id)

    department = Department(faculty_id=payload.faculty_id, name=payload.name)
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu fakültede bu isimde bir bölüm zaten var")
    db.refresh(department)
    return department


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.deleted_at.is_(None),
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bölüm bulunamadı")

    data = payload.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        _get_valid_faculty(db, data["faculty_id"])

    for field, value in data.items():
        setattr(department, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu fakültede bu isimde bir bölüm zaten var")
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.deleted_at.is_(None),
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bölüm bulunamadı")

    department.deleted_at = func.now()
    db.commit()
    return None