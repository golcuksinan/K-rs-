from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.department import Department
from app.schemas.department import DepartmentGroupResponse

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=List[DepartmentGroupResponse])
def search_departments(
    search: str = Query(..., min_length=1, description="Bölüm adında arama (zorunlu)"),
    db: Session = Depends(get_db),
):
    departments = db.query(Department).filter(
        Department.name.ilike(f"%{search}%")
    ).all()

    groups: dict[str, list] = {}
    for dept in departments:
        groups.setdefault(dept.name, []).append(dept.faculty)

    return [
        DepartmentGroupResponse(department_name=name, faculties=facs)
        for name, facs in sorted(groups.items())
    ]