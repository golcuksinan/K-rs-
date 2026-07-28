from typing import List, Optional

from pydantic import BaseModel

from app.schemas.review import ReviewResponse


class ProfessorListItem(BaseModel):
    id: int
    full_name: str
    title: Optional[str] = None
    course_count: int
    review_count: int
    average_teaching_score: Optional[float]
    average_difficulty_score: Optional[float]
    average_fairness_score: Optional[float]

    class Config:
        from_attributes = True


class CourseProfessorSummary(BaseModel):
    id: int
    course_name: str
    course_code: str
    term: str
    average_teaching_score: Optional[float]
    average_difficulty_score: Optional[float]
    average_fairness_score: Optional[float]
    review_count: int

    class Config:
        from_attributes = True


class ProfessorDetail(BaseModel):
    id: int
    full_name: str
    courses: List[CourseProfessorSummary]
    reviews: List[ReviewResponse]

    class Config:
        from_attributes = True