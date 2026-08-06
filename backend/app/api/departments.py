from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.masking import DELETED_FACULTY, DELETED_UNIVERSITY, masked_name
from app.db.session import get_db
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.common import Page
from app.schemas.department import DepartmentGroupResponse, DepartmentResponse, DepartmentCreate, DepartmentUpdate, GroupedFacultyResponse
from app.api.common import PageParams, get_active_or_400, get_active_or_404, page, pagination, paginated, search_filter
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=Union[Page[DepartmentResponse], Page[DepartmentGroupResponse]])
def list_departments(
    faculty_id: Optional[int] = Query(default=None, description="Fakülte ID (verilirse düz liste döner)"),
    search: Optional[str] = Query(default=None, description="Bölüm adında arama"),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    if faculty_id is not None:
        query = db.query(Department).filter(
            Department.faculty_id == faculty_id,
            Department.deleted_at.is_(None),
        )
        if search:
            query = query.filter(search_filter(Department.name, search))
        return paginated(query.order_by(Department.name), params)

    if not search:
        raise HTTPException(status_code=422, detail="faculty_id veya search parametrelerinden biri gönderilmeli")

    # limit/offset satır değil **grup** seviyesinde uygulanır — kullanıcının gördüğü birim grup.
    # Dolayısıyla total = grup sayısı, eşleşen bölüm satırı sayısı DEĞİL.
    grouped = (
        db.query(Department.name)
        .filter(
            search_filter(Department.name, search),
            Department.deleted_at.is_(None),
        )
        .group_by(Department.name)
    )
    total = grouped.count()
    names = [
        row[0]
        for row in grouped.order_by(Department.name)
        .offset(params.offset)
        .limit(params.limit)
        .all()
    ]

    departments = (
        db.query(Department)
        .options(joinedload(Department.faculty).joinedload(Faculty.university))
        .filter(Department.name.in_(names), Department.deleted_at.is_(None))
        .order_by(Department.name)
        .all()
    ) if names else []

    groups: dict[str, list] = {name: [] for name in names}
    for dept in departments:
        groups[dept.name].append(dept.faculty)

    items = [
        DepartmentGroupResponse(
            department_name=name,
            faculties=[
                GroupedFacultyResponse(
                    id=fac.id,
                    name=masked_name(fac.deleted_at, fac.name, DELETED_FACULTY),
                    university_id=fac.university_id,
                    university_name=masked_name(
                        fac.university.deleted_at, fac.university.name, DELETED_UNIVERSITY
                    ),
                    deleted_at=fac.deleted_at,
                )
                for fac in facs
            ],
        )
        for name, facs in groups.items()
    ]
    return page(items, total, params)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    get_active_or_400(db, Faculty, payload.faculty_id, "faculty_id")

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
    department = get_active_or_404(db, Department, department_id, "Bölüm bulunamadı")

    for field, value in payload.model_dump(exclude_unset=True).items():
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
    department = get_active_or_404(db, Department, department_id, "Bölüm bulunamadı")

    department.deleted_at = func.now()
    db.commit()
    return None