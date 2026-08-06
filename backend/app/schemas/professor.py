from typing import List, Optional

from pydantic import BaseModel


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


class ProfessorCourseTerm(BaseModel):
    course_professor_id: int
    term: str


class ProfessorCourseSummary(BaseModel):
    # Ders kanoniktir: aynı dersin dönemleri tek girdide toplanır, puanlar ders havuzundan gelir.
    course_id: int
    course_code: str
    course_name: str
    terms: List[ProfessorCourseTerm]
    average_teaching_score: Optional[float]
    average_difficulty_score: Optional[float]
    average_fairness_score: Optional[float]
    review_count: int


class ProfessorDetail(BaseModel):
    id: int
    full_name: str
    courses: List[ProfessorCourseSummary]

    class Config:
        from_attributes = True