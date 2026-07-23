from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- Create ----------

class ReviewCreate(BaseModel):
    course_professor_id: int
    teaching_score: int = Field(ge=1, le=5)
    difficulty_score: int = Field(ge=1, le=5)
    fairness_score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


# ---------- Response ----------

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


# ---------- Admin: status güncelleme ----------

class ReviewStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]