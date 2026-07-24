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


# ---------- [YENİ] Düzenleme ----------

class ReviewUpdate(BaseModel):
    teaching_score: int = Field(ge=1, le=5)
    difficulty_score: int = Field(ge=1, le=5)
    fairness_score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


# ---------- Response (public) ----------

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


# ---------- [YENİ] Response (kullanıcının kendisi + admin, edit karşılaştırması için) ----------

class ReviewFullResponse(ReviewResponse):
    has_pending_edit: bool
    pending_teaching_score: Optional[int]
    pending_difficulty_score: Optional[int]
    pending_fairness_score: Optional[int]
    pending_comment: Optional[str]


# ---------- Admin: status güncelleme ----------

class ReviewStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]