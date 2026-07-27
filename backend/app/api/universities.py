from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.university import University
from app.models.user import User
from app.schemas.common import Page
from app.schemas.university import UniversityResponse, UniversityCreate, UniversityUpdate
from app.api.common import PageParams, get_active_or_404, pagination, paginated
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/universities", tags=["universities"])


@router.get("", response_model=Page[UniversityResponse])
def list_universities(
    search: Optional[str] = Query(default=None, description="Üniversite adı veya kısaltmasında arama"),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    query = db.query(University).filter(University.deleted_at.is_(None))
    if search:
        query = query.filter(
            or_(
                University.name.ilike(f"%{search}%"),
                University.short_name.ilike(f"%{search}%"),
            )
        )
    return paginated(query.order_by(University.name), params)


# ---------- Admin: oluştur ----------

@router.post("", response_model=UniversityResponse, status_code=status.HTTP_201_CREATED)
def create_university(
    payload: UniversityCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    university = University(name=payload.name, short_name=payload.short_name, city=payload.city)
    db.add(university)
    db.commit()
    db.refresh(university)
    return university


# ---------- Admin: güncelle ----------

@router.patch("/{university_id}", response_model=UniversityResponse)
def update_university(
    university_id: int,
    payload: UniversityUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    university = get_active_or_404(db, University, university_id, "Üniversite bulunamadı")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(university, field, value)

    db.commit()
    db.refresh(university)
    return university


# ---------- Admin: sil (soft delete) ----------

@router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_university(
    university_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    university = get_active_or_404(db, University, university_id, "Üniversite bulunamadı")

    university.deleted_at = func.now()
    db.commit()
    return None