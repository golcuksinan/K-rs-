"""Olay sayaçları: `event_daily_counters` tablosuna günlük kova upsert'i.

Sayaç çağıranın session'ında DEĞİL, kendi kısa transaction'ında artırılır. İki sebebi var:
`(gün, olay)` satırı `ON CONFLICT` ile kilitlenir — istek transaction'ında artırılsaydı kilit
isteğin sonuna kadar tutulur, aynı olayı üreten istekler sıraya girerdi; ayrıca login gibi hiç
commit etmeyen akışlarda sayaç hiç yazılmazdı. "Başarısız işlem sayılmasın" kuralı bu yüzden
transaction'a değil çağrının YERİNE bağlıdır: `increment()` olayın gerçekleştiği noktada
(state değiştiren akışlarda commit'ten sonra) çağrılır.
"""

import enum
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.db.session import SessionLocal
from app.models.event_counter import EventDailyCounter

logger = logging.getLogger(__name__)


class Event(str, enum.Enum):
    """Olay adları tek yerde: serbest string kullanılmaz, yazım hatası sessizce yeni bir
    olay tipi yaratmasın. Postgres native enum bilinçli olarak değil — yeni olay tipi
    eklemek migration gerektirirdi."""

    AUTH_REGISTER_STARTED = "auth.register_started"
    AUTH_REGISTER_COMPLETED = "auth.register_completed"
    AUTH_OTP_FAILED = "auth.otp_failed"
    AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    AUTH_PASSWORD_RESET_COMPLETED = "auth.password_reset_completed"

    MAIL_VERIFICATION_SENT = "mail.verification_sent"
    MAIL_RESET_SENT = "mail.reset_sent"
    MAIL_ALREADY_REGISTERED_SENT = "mail.already_registered_sent"

    REVIEW_CREATED = "review.created"
    REVIEW_EDIT_REQUESTED = "review.edit_requested"
    REVIEW_APPROVED = "review.approved"
    REVIEW_REJECTED = "review.rejected"
    REVIEW_EDIT_APPROVED = "review.edit_approved"
    REVIEW_EDIT_REJECTED = "review.edit_rejected"

    REPORT_CREATED = "report.created"
    REPORT_RESOLVED = "report.resolved"
    REPORT_DISMISSED = "report.dismissed"

    MODERATION_APPROVED = "moderation.approved"
    MODERATION_REJECTED = "moderation.rejected"
    MODERATION_PENDING = "moderation.pending"
    MODERATION_FAILED = "moderation.failed"


ALL_EVENTS = [event.value for event in Event]


def utc_today():
    return datetime.now(timezone.utc).date()


def increment(event: Event, amount: int = 1) -> None:
    # Session açmanın kendisi de patlayabilir (havuz doluysa) — o yüzden try'ın içinde.
    try:
        db = SessionLocal()
        try:
            stmt = insert(EventDailyCounter).values(
                day=utc_today(), event=event.value, count=amount
            )
            db.execute(
                stmt.on_conflict_do_update(
                    index_elements=["day", "event"],
                    set_={"count": EventDailyCounter.count + stmt.excluded.count},
                )
            )
            db.commit()
        finally:
            db.close()  # commit edilmemiş transaction'ı geri alır
    except Exception:
        # Sayaç hatası kullanıcının isteğini düşürmez ama sessizce de yutulmaz.
        logger.exception("Olay sayacı artırılamadı: %s", event.value)
