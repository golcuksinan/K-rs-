from sqlalchemy import Column, Date, Integer, String

from app.db.base_class import Base


class EventDailyCounter(Base):
    """Olay sayaçlarının günlük kovası. Olay başına satır DEĞİL: satır sayısı
    `gün × olay tipi` ile sınırlı kalır ve kişiye bağlanabilir hiçbir alan taşımaz
    (`user_id` koyacak yer yok → anonimlik kazara delinemez).

    `day` UTC günüdür (`app/services/metrics.py`). Composite PK aynı zamanda
    upsert'in `ON CONFLICT (day, event)` hedefidir.
    """

    __tablename__ = "event_daily_counters"

    day = Column(Date, primary_key=True)
    event = Column(String, primary_key=True)
    count = Column(Integer, nullable=False, server_default="0")
