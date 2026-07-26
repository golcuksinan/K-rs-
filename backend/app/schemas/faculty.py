from pydantic import BaseModel


class FacultyResponse(BaseModel):
    id: int
    name: str
    university_id: int

    class Config:
        from_attributes = True