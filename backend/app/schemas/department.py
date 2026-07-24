from typing import List

from pydantic import BaseModel

from app.schemas.university import UniversityResponse


class DepartmentGroupResponse(BaseModel):
    department_name: str
    universities: List[UniversityResponse]