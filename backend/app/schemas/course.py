from pydantic import BaseModel

class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    department_id: int
    department_name: str

    class Config:
        from_attributes = True