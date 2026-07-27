from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserMeResponse
from app.models.user import User
from app.core.academic import compute_sinif

router = APIRouter(prefix="/users", tags=["users"])

def _masked(deleted_at, name: str, placeholder: str) -> str:
    return placeholder if deleted_at is not None else name

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
        department_name=_masked(department.deleted_at, department.name, "Silinmiş Bölüm"),
        faculty_id=faculty.id,
        faculty_name=_masked(faculty.deleted_at, faculty.name, "Silinmiş Fakülte"),
        university_id=university.id,
        university_name=_masked(university.deleted_at, university.name, "Silinmiş Üniversite"),
        university_short_name=None if university.deleted_at is not None else university.short_name,
    )