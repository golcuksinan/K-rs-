from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.department import Department
from app.schemas.department import DepartmentGroupResponse, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=Union[List[DepartmentResponse], List[DepartmentGroupResponse]])
def list_departments(
    faculty_id: Optional[int] = Query(default=None, description="Fakülte ID (verilirse düz liste döner)"),
    search: Optional[str] = Query(default=None, description="Bölüm adında arama"),
    db: Session = Depends(get_db),
):
    if faculty_id is not None:
        query = db.query(Department).filter(Department.faculty_id == faculty_id)
        if search:
            query = query.filter(Department.name.ilike(f"%{search}%"))
        return query.order_by(Department.name).all()

    if not search:
        raise HTTPException(status_code=422, detail="faculty_id veya search parametrelerinden biri gönderilmeli")

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