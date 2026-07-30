from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.faculty import FacultyResponse


class DepartmentGroupResponse(BaseModel):
    department_name: str
    faculties: List[FacultyResponse]

class DepartmentResponse(BaseModel):
    id: int
    name: str
    faculty_id: int
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    faculty_id: int
    name: str = Field(min_length=1)


class DepartmentUpdate(BaseModel):
    # faculty_id bilinçli olarak YOK: bölümün fakültesi değişirse üniversite de değişebilir,
    # Course.university_id takip etmez ve kanonik ders kimliği kırılır (bkz. FacultyUpdate).
    name: Optional[str] = Field(default=None, min_length=1)