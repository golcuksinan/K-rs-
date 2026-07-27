from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserMeResponse
from app.models.user import User
from app.core.academic import compute_sinif
from app.core.masking import (
    DELETED_DEPARTMENT,
    DELETED_FACULTY,
    DELETED_UNIVERSITY,
    masked_name,
    masked_optional,
)

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
        department_name=masked_name(department.deleted_at, department.name, DELETED_DEPARTMENT),
        faculty_id=faculty.id,
        faculty_name=masked_name(faculty.deleted_at, faculty.name, DELETED_FACULTY),
        university_id=university.id,
        university_name=masked_name(university.deleted_at, university.name, DELETED_UNIVERSITY),
        university_short_name=masked_optional(university.deleted_at, university.short_name),
    )