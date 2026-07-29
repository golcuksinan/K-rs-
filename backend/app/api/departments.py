from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.masking import DELETED_FACULTY, masked_name
from app.db.session import get_db
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.common import Page
from app.schemas.department import DepartmentGroupResponse, DepartmentResponse, DepartmentCreate, DepartmentUpdate
from app.schemas.faculty import FacultyResponse
from app.api.common import PageParams, get_active_or_400, get_active_or_404, page, pagination, paginated
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/departments", tags=["departments"])

# Gruplama dalı satırları Python'da toplamak zorunda (grup = bölüm adı, SQL'de sayfalanamıyor).
# Bu yüzden ham satır sayısına sabit bir güvenlik tavanı konuyor: search="a" gibi geniş bir
# terim on binlerce bölüm satırının büyük kısmını eşleştirebilir.
GROUP_SEARCH_ROW_CAP = 500


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
            query = query.filter(Department.name.ilike(f"%{search}%"))
        return paginated(query.order_by(Department.name), params)

    if not search:
        raise HTTPException(status_code=422, detail="faculty_id veya search parametrelerinden biri gönderilmeli")

    departments = (
        db.query(Department)
        .options(joinedload(Department.faculty))
        .filter(
            Department.name.ilike(f"%{search}%"),
            Department.deleted_at.is_(None),
        )
        .order_by(Department.name)
        .limit(GROUP_SEARCH_ROW_CAP)
        .all()
    )

    groups: dict[str, list] = {}
    for dept in departments:
        groups.setdefault(dept.name, []).append(dept.faculty)

    # limit/offset satır değil **grup** seviyesinde uygulanır — kullanıcının gördüğü birim grup.
    # Dolayısıyla total = grup sayısı, eşleşen bölüm satırı sayısı DEĞİL.
    ordered = sorted(groups.items())
    window = ordered[params.offset : params.offset + params.limit]

    items = [
        DepartmentGroupResponse(
            department_name=name,
            faculties=[
                FacultyResponse(
                    id=fac.id,
                    name=masked_name(fac.deleted_at, fac.name, DELETED_FACULTY),
                    university_id=fac.university_id,
                    deleted_at=fac.deleted_at,
                )
                for fac in facs
            ],
        )
        for name, facs in window
    ]
    return page(items, len(ordered), params)


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

    data = payload.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        get_active_or_400(db, Faculty, data["faculty_id"], "faculty_id")

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
    department = get_active_or_404(db, Department, department_id, "Bölüm bulunamadı")

    department.deleted_at = func.now()
    db.commit()
    return None