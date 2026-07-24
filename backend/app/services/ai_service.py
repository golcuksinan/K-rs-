import asyncio

from app.services.moderation import analyze_review_with_hf, ModerationStatus


def moderate_review(review) -> str:
    """
    HF moderasyon servisini senkron review akışına bağlar.
    Dönüş: "approved" | "rejected" | "pending"

    Servis çökerse veya beklenmeyen bir hata olursa güvenli tarafta kalınır:
    "pending".
    """
    try:
        decision = asyncio.run(analyze_review_with_hf(review.comment or ""))
    except Exception:
        return ModerationStatus.PENDING.value

    return decision.value if isinstance(decision, ModerationStatus) else ModerationStatus.PENDING.value