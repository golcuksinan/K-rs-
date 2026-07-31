import asyncio

from app.services.metrics import Event, increment
from app.services.moderation import analyze_review_with_hf, ModerationStatus

_VERDICT_EVENTS = {
    ModerationStatus.APPROVED: Event.MODERATION_APPROVED,
    ModerationStatus.REJECTED: Event.MODERATION_REJECTED,
    ModerationStatus.PENDING: Event.MODERATION_PENDING,
}


def moderate_review(comment: str) -> str:
    """
    HF moderasyon servisini senkron review akışına bağlar.
    Dönüş: "approved" | "rejected" | "pending"

    Servis çökerse veya beklenmeyen bir hata olursa güvenli tarafta kalınır:
    "pending".

    Sayaç: her çalıştırma tam olarak bir verdict olayı sayar (approved+rejected+pending =
    toplam moderasyon). ⚠️ `moderation.failed` bunların yerine değil YANINA sayılır ve
    `moderation.pending`'in alt kümesidir — karar verilemeyen yorum pending'e düşer.
    """
    try:
        decision = asyncio.run(analyze_review_with_hf(comment or ""))
    except Exception:
        increment(Event.MODERATION_FAILED)
        decision = ModerationStatus.PENDING

    if not isinstance(decision, ModerationStatus):
        decision = ModerationStatus.PENDING

    increment(_VERDICT_EVENTS[decision])
    return decision.value
