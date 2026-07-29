from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.review import ReviewResponse


class CourseProfessorCreate(BaseModel):
    course_id: int
    professor_id: int
    term: str = Field(min_length=1)


class CourseProfessorResponse(BaseModel):
    id: int
    course_id: int
    professor_id: int
    term: str

    class Config:
        from_attributes = True


class CourseProfessorDetail(BaseModel):
    id: int
    course_name: str
    course_code: str
    professor_name: str
    term: str
    average_teaching_score: Optional[float]
    average_difficulty_score: Optional[float]
    average_fairness_score: Optional[float]
    review_count: int
    reviews: List[ReviewResponse]

    class Config:
        from_attributes = True

class CourseProfessorListItem(BaseModel):
    id: int
    professor_name: str
    term: str
    avg_teaching: Optional[float]
    avg_difficulty: Optional[float]
    avg_fairness: Optional[float]

    class Config:
        from_attributes = True