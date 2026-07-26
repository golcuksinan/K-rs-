from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UniversityResponse(BaseModel):
    id: int
    name: str
    short_name: Optional[str]
    city: str
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UniversityCreate(BaseModel):
    name: str = Field(min_length=1)
    short_name: Optional[str] = None
    city: str = Field(min_length=1)


class UniversityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    short_name: Optional[str] = None
    city: Optional[str] = Field(default=None, min_length=1)