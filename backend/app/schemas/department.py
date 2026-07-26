from typing import List

from pydantic import BaseModel

from app.schemas.faculty import FacultyResponse


class DepartmentGroupResponse(BaseModel):
    department_name: str
    faculties: List[FacultyResponse]