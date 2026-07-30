from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FacultyResponse(BaseModel):
    id: int
    name: str
    university_id: int
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FacultyCreate(BaseModel):
    university_id: int
    name: str = Field(min_length=1)


class FacultyUpdate(BaseModel):
    # university_id bilinçli olarak YOK: fakültenin üniversitesi değişirse altındaki derslerin
    # Course.university_id'si takip etmez, kanonik ders kimliği (university_id, code, name) kırılır.
    name: Optional[str] = Field(default=None, min_length=1)