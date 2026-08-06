from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.enums import UserRole, Sinif

class UserMeResponse(BaseModel):
    role: UserRole
    current_grade: Sinif
    enrollment_year: int
    is_verified: bool
    created_at: datetime
    department_id: int
    department_name: str
    faculty_id: int
    faculty_name: str
    university_id: int
    university_name: str
    university_short_name: Optional[str]

    class Config:
        from_attributes = True