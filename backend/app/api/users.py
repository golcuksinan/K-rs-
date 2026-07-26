from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserMeResponse
from app.models.user import User
from app.core.academic import compute_sinif

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserMeResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    department = current_user.department
    faculty = department.faculty
    university = faculty.university

    return UserMeResponse(
        role=current_user.role,
        current_grade=compute_sinif(current_user.enrollment_year),
        enrollment_year=current_user.enrollment_year,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        department_id=department.id,
        department_name=department.name,
        faculty_id=faculty.id,
        faculty_name=faculty.name,
        university_id=university.id,
        university_name=university.name,
        university_short_name=university.short_name,
    )