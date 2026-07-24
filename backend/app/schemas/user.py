from pydantic import BaseModel
from datetime import datetime
from app.models.enums import UserRole

class UserMeResponse(BaseModel):
    role: UserRole
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True