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
    name: Optional[str] = Field(default=None, min_length=1)
    university_id: Optional[int] = None