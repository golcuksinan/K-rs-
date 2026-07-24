import enum
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModerationStatus(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


async def analyze_review_with_hf(text: str) -> ModerationStatus:
    """
    Hugging Face Inference API kullanarak yorumun moderasyon durumunu analiz eder.
    Servis çökerse, hata verirse veya yavaşlarsa SİSTEMİ KIRMAZ; PENDING döner.
    """
    if not text or not text.strip():
        return ModerationStatus.APPROVED

    headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
    payload = {"inputs": text}

    try:
        # Asenkron HTTP İsteği (Max 3 saniye bekle)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.HF_MODEL_URL, 
                headers=headers, 
                json=payload, 
                timeout=3.0
            )

        if response.status_code != 200:
            logger.warning(f"HF API non-200 response: {response.status_code}")
            return ModerationStatus.PENDING

        result = response.json()

        # Hugging Face çıktı formatı: [[{'label': 'negative', 'score': 0.98}]]
        if isinstance(result, list) and len(result) > 0:
            predictions = result[0]
            top_pred = max(predictions, key=lambda x: x['score'])

            label = top_pred.get('label', '').lower()
            score = top_pred.get('score', 0.0)

            # Eşik Değer Kontrolü (Thresholding)
            if label == 'negative' and score > 0.85:
                return ModerationStatus.REJECTED
            elif label == 'positive' and score > 0.70:
                return ModerationStatus.APPROVED
            else:
                return ModerationStatus.PENDING

        return ModerationStatus.PENDING

    except Exception as e:
        # Bağlantı koptu, timeout oldu veya HF servis dışı
        logger.error(f"Hugging Face Moderation Service Error: {str(e)}")
        # Graceful Fallback: Sistemi kırmamak için manuel onaya düşür
        return ModerationStatus.PENDING