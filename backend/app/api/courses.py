from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.masking import (
    DELETED_DEPARTMENT,
    DELETED_FACULTY,
    DELETED_UNIVERSITY,
    masked_name,
    masked_optional,
)
from app.db.session import get_db
from app.models.course import Course, CourseDepartment
from app.models.course_professor import CourseProfessor
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.common import Page
from app.schemas.course import CourseResponse, CourseCreate, CourseUpdate
from app.api.common import PageParams, get_active_or_400, get_active_or_404, like_pattern, page, paginate, pagination
from app.api.deps import get_current_admin_user

router = APIRouter(prefix="/courses", tags=["courses"])


MIN_SEARCH_LENGTH = 2

_CHAIN = joinedload(Course.university)


def _professor_counts(db: Session, course_ids: list[int]) -> dict[int, int]:
    """Ders id -> tekil hoca sayısı, tek sorguda. Satır değil hoca sayılır: aynı hocanın farklı
    dönemleri tek sayılır (`/professors`'daki course_count ile aynı kural)."""
    if not course_ids:
        return {}
    rows = (
        db.query(CourseProfessor.course_id, func.count(func.distinct(CourseProfessor.professor_id)))
        .filter(CourseProfessor.course_id.in_(course_ids))
        .group_by(CourseProfessor.course_id)
        .all()
    )
    return dict(rows)


def _department_counts(db: Session, course_ids: list[int]) -> dict[int, int]:
    if not course_ids:
        return {}
    rows = (
        db.query(CourseDepartment.course_id, func.count(CourseDepartment.department_id))
        .join(Department, Department.id == CourseDepartment.department_id)
        .filter(CourseDepartment.course_id.in_(course_ids), Department.deleted_at.is_(None))
        .group_by(CourseDepartment.course_id)
        .all()
    )
    return dict(rows)


def _to_response(
    course: Course,
    professor_count: int,
    department_count: int,
    link: CourseDepartment | None = None,
) -> CourseResponse:
    university = course.university
    response = CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        professor_count=professor_count,
        department_count=department_count,
        university_id=university.id,
        university_name=masked_name(university.deleted_at, university.name, DELETED_UNIVERSITY),
        university_short_name=masked_optional(university.deleted_at, university.short_name),
        deleted_at=course.deleted_at,
    )
    if link is not None:
        department = link.department
        faculty = department.faculty
        response.department_id = department.id
        response.department_name = masked_name(
            department.deleted_at, department.name, DELETED_DEPARTMENT
        )
        response.faculty_id = faculty.id
        response.faculty_name = masked_name(faculty.deleted_at, faculty.name, DELETED_FACULTY)
        response.semesters = link.semesters
        response.is_elective = link.is_elective
    return response


@router.get("", response_model=Page[CourseResponse])
def list_courses(
    department_id: int | None = Query(default=None, description="Bölüm ID (verilmezse search zorunlu)"),
    search: str | None = Query(default=None, description="Ders adı/kodunda arama"),
    is_elective: bool | None = Query(
        default=None, description="true=seçmeli, false=zorunlu; verilmezse ikisi de"
    ),
    params: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
):
    if department_id is None and (search is None or len(search.strip()) < MIN_SEARCH_LENGTH):
        raise HTTPException(
            status_code=422,
            detail=f"department_id verilmediğinde search zorunludur (en az {MIN_SEARCH_LENGTH} karakter)",
        )

    # is_elective NULL olan dersler (müfredat verisi olmayan) hiçbir filtre dalında dönmez —
    # "zorunlu" ile "bilinmiyor" aynı kovaya konmaz.
    if department_id is not None:
        # Var olmayan bölüm 200+boş yerine 404. Soft-delete edilmiş bölüm 404 DEĞİL: dersleri
        # "Silinmiş Bölüm" maskesiyle listelenmeye devam eder (§6 "kalan kayıtlar dursun").
        if db.query(Department.id).filter(Department.id == department_id).first() is None:
            raise HTTPException(status_code=404, detail="Bölüm bulunamadı")

        # Müfredat verisi (ders, bölüm) ikilisine ait: bölüm dalında join satırından okunur.
        query = (
            db.query(Course, CourseDepartment)
            .join(CourseDepartment, CourseDepartment.course_id == Course.id)
            .options(_CHAIN, joinedload(CourseDepartment.department).joinedload(Department.faculty))
            .filter(Course.deleted_at.is_(None), CourseDepartment.department_id == department_id)
        )
        if is_elective is not None:
            query = query.filter(CourseDepartment.is_elective.is_(is_elective))
    else:
        query = db.query(Course).options(_CHAIN).filter(Course.deleted_at.is_(None))
        if is_elective is not None:
            # Ders N bölümde N farklı türde olabilir → "en az bir bölümde seçmeli/zorunlu".
            query = query.filter(
                db.query(CourseDepartment)
                .filter(
                    CourseDepartment.course_id == Course.id,
                    CourseDepartment.is_elective.is_(is_elective),
                )
                .exists()
            )

    if search:
        pattern = like_pattern(search)
        query = query.filter(
            Course.name.ilike(pattern, escape="\\") | Course.code.ilike(pattern, escape="\\")
        )

    rows, total = paginate(query.order_by(Course.name), params)
    links = dict(rows) if department_id is not None else {}
    courses = [course for course, _ in rows] if department_id is not None else rows

    ids = [c.id for c in courses]
    professor_counts = _professor_counts(db, ids)
    department_counts = _department_counts(db, ids)

    return page(
        [
            _to_response(
                c, professor_counts.get(c.id, 0), department_counts.get(c.id, 0), links.get(c)
            )
            for c in courses
        ],
        total,
        params,
    )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    department = get_active_or_400(db, Department, payload.department_id, "department_id")
    university_id = department.faculty.university_id

    # Ders kanonik: aynı üniversitede aynı (kod, ad) varsa yeni ders açılmaz, bölüm bağı eklenir.
    course = (
        db.query(Course)
        .filter(
            Course.university_id == university_id,
            Course.code == payload.code,
            Course.name == payload.name,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if course is None:
        course = Course(university_id=university_id, name=payload.name, code=payload.code)
        db.add(course)
        db.flush()

    link = CourseDepartment(course_id=course.id, department_id=department.id)
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu ders zaten bu bölümün müfredatında")
    db.refresh(course)
    db.refresh(link)
    return _to_response(
        course,
        _professor_counts(db, [course.id]).get(course.id, 0),
        _department_counts(db, [course.id]).get(course.id, 0),
        link,
    )


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """⚠️ Ders kanonik: ad/kod değişikliği dersin listelendiği TÜM bölümleri etkiler.
    Bölüm bağı ve müfredat alanları dersin değil join satırının alanı, buradan düzenlenmez."""
    course = get_active_or_404(db, Course, course_id, "Ders bulunamadı")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Bu üniversitede bu kod ve isimde bir ders zaten var"
        )
    db.refresh(course)
    return _to_response(
        course,
        _professor_counts(db, [course.id]).get(course.id, 0),
        _department_counts(db, [course.id]).get(course.id, 0),
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """⚠️ Etki alanı üniversite geneli: ders kaç bölümün müfredatındaysa hepsinden düşer."""
    course = get_active_or_404(db, Course, course_id, "Ders bulunamadı")

    course.deleted_at = func.now()
    db.commit()
    return None
