"""Endpoint'ler arası ortak yardımcılar: sayfalama ve soft-delete doğrulaması."""

from dataclasses import dataclass
from typing import Any, List, Tuple, Type

from fastapi import HTTPException, Query
from sqlalchemy.orm import Query as SAQuery, Session


# ---------- Sayfalama ----------

@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def pagination(
    limit: int = Query(default=50, ge=1, le=100, description="Sayfa başına kayıt"),
    offset: int = Query(default=0, ge=0, description="Atlanacak kayıt sayısı"),
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


def paginate(query: SAQuery, params: PageParams) -> Tuple[List[Any], int]:
    """(items, total) döner. total sayımında ORDER BY düşürülür (gereksiz sıralama maliyeti)."""
    total = query.order_by(None).count()
    items = query.limit(params.limit).offset(params.offset).all()
    return items, total


def page(items: List[Any], total: int, params: PageParams) -> dict:
    """Page[T] zarfını kurar. response_model doğrulaması FastAPI tarafında yapılır."""
    return {"items": items, "total": total, "limit": params.limit, "offset": params.offset}


def paginated(query: SAQuery, params: PageParams) -> dict:
    """paginate + page kısayolu: item'lar dönüştürülmeden döndürülecekse kullanılır."""
    items, total = paginate(query, params)
    return page(items, total, params)


# ---------- Soft-delete doğrulaması ----------

def get_active_or_400(db: Session, model: Type[Any], obj_id: int, field_name: str) -> Any:
    """Payload'dan gelen FK'yi doğrular: silinmemiş kayıt yoksa 400."""
    obj = db.query(model).filter(model.id == obj_id, model.deleted_at.is_(None)).first()
    if not obj:
        raise HTTPException(status_code=400, detail=f"Geçersiz {field_name}")
    return obj


def get_active_or_404(db: Session, model: Type[Any], obj_id: int, detail: str) -> Any:
    """Path'ten gelen kaydı getirir: silinmemiş kayıt yoksa 404."""
    obj = db.query(model).filter(model.id == obj_id, model.deleted_at.is_(None)).first()
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj
