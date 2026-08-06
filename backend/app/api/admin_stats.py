"""Admin metrik uçları.

İki farklı soru, iki ayrı uç: `/admin/stats` mevcut tablolardan **anlık durumu** agregat
sorguyla çıkarır (şema değişikliği gerektirmez), `/admin/stats/events` olup biten ve hiçbir
tabloda iz bırakmayan olayların sayaçlarını döner (`app/services/metrics.py`).

⚠️ Metrik yanıtları liste değildir: `Page[T]` zarfı kullanılmaz, düz nesne döner.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.course import Course, CourseDepartment
from app.models.course_professor import CourseProfessor
from app.models.department import Department
from app.models.email_verification import EmailVerification
from app.models.enums import UserRole
from app.models.event_counter import EventDailyCounter
from app.models.faculty import Faculty
from app.models.professor import Professor
from app.models.report import Report
from app.models.review import Review
from app.models.university import University
from app.models.user import User
from app.schemas.stats import (
    ContentStats,
    DataHealthStats,
    EventDayCounts,
    EventStatsResponse,
    ModerationStats,
    StatsResponse,
    UserStats,
)
from app.services.metrics import ALL_EVENTS, utc_today

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])

REVIEW_STATUSES = ("pending", "approved", "rejected")
REPORT_STATUSES = ("pending", "resolved", "dismissed")


def _count(model, *conditions):
    stmt = select(func.count()).select_from(model)
    return (stmt.where(*conditions) if conditions else stmt).scalar_subquery()


def _count_on_active_course(model):
    """`course_departments`/`course_professors`'ta soft-delete yok; "aktif" sayısı dersin
    kendi `deleted_at`'inden okunur."""
    return (
        select(func.count())
        .select_from(model)
        .join(Course, Course.id == model.course_id)
        .where(Course.deleted_at.is_(None))
        .scalar_subquery()
    )


# Tek satırlık tek sorgu: blok başına ayrı COUNT round-trip'i atılmaz.
_SCALAR_COUNTS = {
    "universities": _count(University, University.deleted_at.is_(None)),
    "faculties": _count(Faculty, Faculty.deleted_at.is_(None)),
    "departments": _count(Department, Department.deleted_at.is_(None)),
    "courses": _count(Course, Course.deleted_at.is_(None)),
    "course_departments": _count_on_active_course(CourseDepartment),
    "professors": _count(Professor),
    "course_professors": _count_on_active_course(CourseProfessor),
    "courses_without_professor": _count(
        Course,
        Course.deleted_at.is_(None),
        ~select(CourseProfessor.id)
        .where(CourseProfessor.course_id == Course.id)
        .exists(),
    ),
    # Silinmiş ders ya da bölüme ait bağ hiçbir zaman kapatılamayacak bir iş kalemi olurdu;
    # `content.course_departments` ile aynı tanımda kalması için iki join de gerekli.
    "course_departments_without_curriculum": (
        select(func.count())
        .select_from(CourseDepartment)
        .join(Course, Course.id == CourseDepartment.course_id)
        .join(Department, Department.id == CourseDepartment.department_id)
        .where(
            Course.deleted_at.is_(None),
            Department.deleted_at.is_(None),
            or_(CourseDepartment.semesters.is_(None), CourseDepartment.is_elective.is_(None)),
        )
        .scalar_subquery()
    ),
    # `email_verifications` iki akışı birden tutuyor, ayırt edici `purpose` kolonu yok:
    # şifre sıfırlama kaydında `department_id` boş kalır (`auth.py` verify-otp guard'ı da
    # bu varsayıma dayanıyor).
    "pending_registration_verifications": _count(
        EmailVerification,
        EmailVerification.expires_at > func.now(),
        EmailVerification.department_id.isnot(None),
    ),
    "pending_password_resets": _count(
        EmailVerification,
        EmailVerification.expires_at > func.now(),
        EmailVerification.department_id.is_(None),
    ),
}


def _scalar_counts(db: Session) -> Dict[str, int]:
    row = db.execute(
        select(*[subquery.label(name) for name, subquery in _SCALAR_COUNTS.items()])
    ).mappings().one()
    return dict(row)


def _user_stats(db: Session) -> UserStats:
    rows = db.execute(
        select(User.role, User.is_verified, func.count()).group_by(User.role, User.is_verified)
    ).all()

    by_role = {role.value: 0 for role in UserRole}
    total = 0
    verified = 0
    for role, is_verified, count in rows:
        by_role[role.value] = by_role.get(role.value, 0) + count
        total += count
        if is_verified:
            verified += count

    years = db.execute(
        select(User.enrollment_year, func.count())
        .group_by(User.enrollment_year)
        .order_by(User.enrollment_year)
    ).all()

    return UserStats(
        total=total,
        verified=verified,
        unverified=total - verified,
        by_role=by_role,
        by_enrollment_year={year: count for year, count in years},
    )


def _status_breakdown(rows, known_statuses) -> Tuple[Dict[str, int], int]:
    breakdown = {status: 0 for status in known_statuses}
    total = 0
    for status, count in rows:
        key = status or "unknown"
        breakdown[key] = breakdown.get(key, 0) + count
        total += count
    return breakdown, total


def _moderation_stats(
    db: Session, pending_registration_verifications: int, pending_password_resets: int
) -> ModerationStats:
    review_rows = db.execute(
        select(
            Review.status,
            func.count(),
            func.count().filter(Review.has_pending_edit.is_(True)),
        ).group_by(Review.status)
    ).all()
    reviews_by_status, reviews_total = _status_breakdown(
        [(status, count) for status, count, _ in review_rows], REVIEW_STATUSES
    )

    report_rows = db.execute(
        select(Report.status, func.count()).group_by(Report.status)
    ).all()
    reports_by_status, reports_total = _status_breakdown(report_rows, REPORT_STATUSES)

    return ModerationStats(
        reviews_total=reviews_total,
        reviews_by_status=reviews_by_status,
        reviews_with_pending_edit=sum(edit_count for _, _, edit_count in review_rows),
        reports_total=reports_total,
        reports_by_status=reports_by_status,
        pending_registration_verifications=pending_registration_verifications,
        pending_password_resets=pending_password_resets,
    )


@router.get("", response_model=StatsResponse)
def platform_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    counts = _scalar_counts(db)
    return StatsResponse(
        generated_at=datetime.now(timezone.utc),
        users=_user_stats(db),
        content=ContentStats(
            universities=counts["universities"],
            faculties=counts["faculties"],
            departments=counts["departments"],
            courses=counts["courses"],
            course_departments=counts["course_departments"],
            professors=counts["professors"],
            course_professors=counts["course_professors"],
        ),
        data_health=DataHealthStats(
            courses_without_professor=counts["courses_without_professor"],
            course_departments_without_curriculum=counts["course_departments_without_curriculum"],
        ),
        moderation=_moderation_stats(
            db,
            counts["pending_registration_verifications"],
            counts["pending_password_resets"],
        ),
    )


@router.get("/events", response_model=EventStatsResponse)
def event_stats(
    days: int = Query(default=30, ge=1, le=365, description="Kaç günlük pencere"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    end_day = utc_today()
    start_day = end_day - timedelta(days=days - 1)

    rows = db.execute(
        select(EventDailyCounter.day, EventDailyCounter.event, EventDailyCounter.count).where(
            EventDailyCounter.day >= start_day, EventDailyCounter.day <= end_day
        )
    ).all()
    first_recorded_day = db.execute(select(func.min(EventDailyCounter.day))).scalar()

    # Kodda artık tanımlı olmayan bir olay adı DB'de duruyorsa da döner: veri gizlenmez.
    events = sorted(set(ALL_EVENTS) | {event for _, event, _ in rows})

    totals = {event: 0 for event in events}
    per_day: Dict[object, Dict[str, int]] = {}
    for day, event, count in rows:
        per_day.setdefault(day, {})[event] = count
        totals[event] += count

    series = [
        EventDayCounts(
            day=start_day + timedelta(days=offset),
            counts={
                event: per_day.get(start_day + timedelta(days=offset), {}).get(event, 0)
                for event in events
            },
        )
        for offset in range(days)
    ]

    return EventStatsResponse(
        days=days,
        start_day=start_day,
        end_day=end_day,
        first_recorded_day=first_recorded_day,
        events=events,
        totals=totals,
        series=series,
    )
