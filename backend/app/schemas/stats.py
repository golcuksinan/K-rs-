from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class UserStats(BaseModel):
    """⚠️ Bölüm/üniversite kırılımı bilinçli olarak YOK: tek kullanıcılı bir bölümün
    sayısı yayınlanırsa o kullanıcının yorumları kimliklendirilebilir."""

    total: int
    verified: int
    unverified: int
    by_role: Dict[str, int]
    by_enrollment_year: Dict[int, int]


class ContentStats(BaseModel):
    universities: int
    faculties: int
    departments: int
    courses: int
    course_departments: int
    professors: int
    course_professors: int


class DataHealthStats(BaseModel):
    courses_without_professor: int
    course_departments_without_curriculum: int


class ModerationStats(BaseModel):
    reviews_total: int
    reviews_by_status: Dict[str, int]
    reviews_with_pending_edit: int
    reports_total: int
    reports_by_status: Dict[str, int]
    pending_registration_verifications: int
    pending_password_resets: int


class StatsResponse(BaseModel):
    generated_at: datetime
    users: UserStats
    content: ContentStats
    data_health: DataHealthStats
    moderation: ModerationStats


class EventDayCounts(BaseModel):
    day: date
    counts: Dict[str, int]


class EventStatsResponse(BaseModel):
    """`series` pencerenin HER günü için, `counts` bilinen HER olay için doludur
    (veri olmayan gün/olay 0) — istemci boşluk doldurmaz.

    `first_recorded_day` sayaçların devreye girdiği gün: ondan öncesi ölçülmedi,
    "0" ile "veri yok" bu alanla ayrılır."""

    days: int
    start_day: date
    end_day: date
    first_recorded_day: Optional[date]
    events: List[str]
    totals: Dict[str, int]
    series: List[EventDayCounts]
