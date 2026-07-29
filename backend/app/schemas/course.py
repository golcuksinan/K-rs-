from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    professor_count: int
    department_id: int
    department_name: str
    faculty_id: int
    faculty_name: str
    university_id: int
    university_name: str
    university_short_name: Optional[str] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    department_id: int
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    code: Optional[str] = Field(default=None, min_length=1)
    department_id: Optional[int] = None
