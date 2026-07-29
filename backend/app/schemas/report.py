from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    review_id: int
    reason: str = Field(min_length=3, max_length=500)


class ReportResponse(BaseModel):
    id: int
    review_id: int
    reason: str
    status: str
    created_at: datetime
    # reporter_id BİLİNÇLİ OLARAK YOK

    class Config:
        from_attributes = True


class ReportStatusUpdate(BaseModel):
    status: Literal["resolved", "dismissed"]