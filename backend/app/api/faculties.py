from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.faculty import Faculty
from app.schemas.faculty import FacultyResponse

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.get("", response_model=List[FacultyResponse])
def list_faculties(
    university_id: int = Query(..., description="Üniversite ID (zorunlu)"),
    search: Optional[str] = Query(default=None, description="Fakülte adında arama"),
    db: Session = Depends(get_db),
):
    query = db.query(Faculty).filter(Faculty.university_id == university_id)
    if search:
        query = query.filter(Faculty.name.ilike(f"%{search}%"))
    return query.order_by(Faculty.name).all()