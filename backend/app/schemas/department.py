from typing import List

from pydantic import BaseModel

from app.schemas.faculty import FacultyResponse


class DepartmentGroupResponse(BaseModel):
    department_name: str
    faculties: List[FacultyResponse]

class DepartmentResponse(BaseModel):
    id: int
    name: str
    faculty_id: int

    class Config:
        from_attributes = True