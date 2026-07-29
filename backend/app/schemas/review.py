from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    course_professor_id: int
    teaching_score: int = Field(ge=1, le=5)
    difficulty_score: int = Field(ge=1, le=5)
    fairness_score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    teaching_score: int = Field(ge=1, le=5)
    difficulty_score: int = Field(ge=1, le=5)
    fairness_score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    course_professor_id: int
    teaching_score: int
    difficulty_score: int
    fairness_score: int
    comment: Optional[str]
    status: str
    created_at: datetime
    # user_id review anonimliği gereksiniminden dolayı dahil edilmedi

    class Config:
        from_attributes = True


# Yalnızca review'un sahibine ve admin'e döner; gölge alanlar edit'in öncesi/sonrası
# karşılaştırılabilsin diye taşınır, public ReviewResponse'ta bulunmaz.
class ReviewFullResponse(ReviewResponse):
    has_pending_edit: bool
    pending_teaching_score: Optional[int]
    pending_difficulty_score: Optional[int]
    pending_fairness_score: Optional[int]
    pending_comment: Optional[str]


class ReviewStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]