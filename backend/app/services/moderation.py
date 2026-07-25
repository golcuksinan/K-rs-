import enum
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModerationStatus(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"

# Zararlı kabul edilecek etiket isimleri
TOXIC_LABELS = {"toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"}


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
    payload = {"inputs": text[:1000]}  # Uzun metinleri kesip gönderiyoruz

    try:
        # Asenkron HTTP İsteği (Max 3 saniye bekle)
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
            
            is_rejected = False
            for pred in predictions:
                label = pred.get("label", "").lower()
                score = pred.get("score", 0.0)

                # Toksik/saldırgan etiketlerden birinin skoru 0.70 üzerindeyse reddet
                if label in TOXIC_LABELS and score > 0.70:
                    is_rejected = True
                    break

            if is_rejected:
                return ModerationStatus.REJECTED
            else:
                return ModerationStatus.APPROVED

        return ModerationStatus.PENDING

    except Exception as e:
        # Bağlantı koptu, timeout oldu veya HF servis dışı
        logger.error(f"Hugging Face Moderation Service Error: {str(e)}")
        # Graceful Fallback: Sistemi kırmamak için manuel onaya düşür
        return ModerationStatus.PENDING