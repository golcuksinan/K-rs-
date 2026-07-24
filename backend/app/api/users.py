from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserMeResponse
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserMeResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user