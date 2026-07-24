from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.university import University
from app.schemas.university import UniversityResponse

router = APIRouter(prefix="/universities", tags=["universities"])


@router.get("", response_model=List[UniversityResponse])
def list_universities(
    search: Optional[str] = Query(default=None, description="Üniversite adı veya kısaltmasında arama"),
    db: Session = Depends(get_db),
):
    query = db.query(University)
    if search:
        query = query.filter(
            or_(
                University.name.ilike(f"%{search}%"),
                University.short_name.ilike(f"%{search}%"),
            )
        )
    return query.order_by(University.name).all()