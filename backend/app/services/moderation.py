import enum
import logging
import httpx
from app.core.config import settings
from app.services.metrics import Event, increment

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

# HF'e gönderilen azami uzunluk. Yorum şeması (schemas.review.MAX_COMMENT_LENGTH) bunu
# doğrudan kullanır: daha uzun yorum kabul edilirse fazlası denetlenmeden yayına girerdi.
MAX_MODERATED_CHARS = 1000


def _undecided() -> ModerationStatus:
    """Moderasyonun karar üretemediği her dal buradan döner: yorum insan onayına düşer ve
    olay sayılır. ⚠️ Senkron DB yazımı async fonksiyon içinde çağrılıyor; `asyncio.run`
    altında tek başına çalıştığı için paylaşılan bir event loop bloke etmiyor."""
    increment(Event.MODERATION_FAILED)
    return ModerationStatus.PENDING


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
        return _undecided()

    hf_url = _normalize_hf_url(settings.HF_MODEL_URL)
    headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
    payload = {"inputs": text[:MAX_MODERATED_CHARS]}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                hf_url,
                headers=headers,
                json=payload,
                # HF modeli boşta kalınca uykuya geçiyor; soğuk başlangıç 3 sn'yi aşıyor ve
                # her dinlenme sonrası ilk yorumlar sessizce admin kuyruğuna birikiyordu.
                timeout=20.0,
            )

        if response.status_code != 200:
            logger.warning(f"HF API non-200 response: {response.status_code}")
            return _undecided()

        result = response.json()

        # Toxic-BERT API yanıt yapısı: [[{'label': 'toxic', 'score': 0.92}, ...]]
        if isinstance(result, list) and len(result) > 0:
            predictions = result[0] if isinstance(result[0], list) else result
            
            # default=None: tanınan tek bir etiket bile yoksa skor 0.0 sayılıp yorum
            # "temiz" kabul edilirdi. Model veya etiket adları değişirse bu sessizce
            # her yorumu onaylardı.
            max_score = max(
                (
                    pred.get("score", 0.0)
                    for pred in predictions
                    if isinstance(pred, dict) and pred.get("label", "").lower() in TOXIC_LABELS
                ),
                default=None,
            )

            if max_score is None:
                logger.warning("HF response carries no known toxicity label")
                return _undecided()

            if max_score > REJECT_THRESHOLD:
                return ModerationStatus.REJECTED
            if max_score >= PENDING_THRESHOLD:
                return ModerationStatus.PENDING
            return ModerationStatus.APPROVED

        return _undecided()

    except Exception:
        logger.exception("Hugging Face Moderation Service Error")
        # Hata yukarı fırlatılmaz: moderasyon servisi review yazma akışını kırmamalı,
        # karar veremediğimiz yorum insan onayına düşer.
        return _undecided()