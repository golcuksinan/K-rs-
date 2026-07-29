import enum
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModerationStatus(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"

TOXIC_LABELS = {"toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"}

# Üç bantlı karar eşikleri: > REJECT_THRESHOLD reddedilir, >= PENDING_THRESHOLD
# insan onayına düşer, altı otomatik onaylanır.
REJECT_THRESHOLD = 0.70
PENDING_THRESHOLD = 0.35


def _normalize_hf_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("https://api-inference.huggingface.co/models/"):
        return url.replace(
            "https://api-inference.huggingface.co/models/",
            "https://router.huggingface.co/hf-inference/models/",
        )
    return url


async def analyze_review_with_hf(text: str) -> ModerationStatus:
    """
    Hugging Face Inference API kullanarak yorumun moderasyon durumunu analiz eder.
    Servis çökerse, hata verirse veya yavaşlarsa SİSTEMİ KIRMAZ; PENDING döner.
    """
    if not text or not text.strip():
        return ModerationStatus.APPROVED

    if not settings.HF_API_TOKEN:
        logger.warning("HF_API_TOKEN missing, moderation falls back to pending")
        return ModerationStatus.PENDING

    hf_url = _normalize_hf_url(settings.HF_MODEL_URL)
    headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
    payload = {"inputs": text[:1000]}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                hf_url,
                headers=headers,
                json=payload,
                timeout=3.0,
            )

        if response.status_code != 200:
            logger.warning(f"HF API non-200 response: {response.status_code}")
            return ModerationStatus.PENDING

        result = response.json()

        # Toxic-BERT API yanıt yapısı: [[{'label': 'toxic', 'score': 0.92}, ...]]
        if isinstance(result, list) and len(result) > 0:
            predictions = result[0] if isinstance(result[0], list) else result
            
            max_score = max(
                (
                    pred.get("score", 0.0)
                    for pred in predictions
                    if pred.get("label", "").lower() in TOXIC_LABELS
                ),
                default=0.0,
            )

            if max_score > REJECT_THRESHOLD:
                return ModerationStatus.REJECTED
            if max_score >= PENDING_THRESHOLD:
                return ModerationStatus.PENDING
            return ModerationStatus.APPROVED

        return ModerationStatus.PENDING

    except Exception as e:
        logger.error(f"Hugging Face Moderation Service Error: {str(e)}")
        # Hata yukarı fırlatılmaz: moderasyon servisi review yazma akışını kırmamalı,
        # karar veremediğimiz yorum insan onayına düşer.
        return ModerationStatus.PENDING