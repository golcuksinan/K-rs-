import requests

from app.core.config import settings

AI_SERVICE_TIMEOUT = 5  # saniye

def moderate_review(review) -> str:
    """
    AI moderasyon servisine review'u gönderir.
    Dönüş: "approved" | "rejected" | "pending"

    Servise ulaşılamazsa (henüz hazır değil, timeout, bağlantı hatası) veya
    beklenmeyen bir yanıt gelirse güvenli tarafta kalınır: "pending"
    (admin elle karar verir) — hiçbir zaman hataya düşüp review oluşturmayı engellemez.
    """
    payload = {
        "review_id": review.id,
        "comment": review.comment,
        "teaching_score": review.teaching_score,
        "difficulty_score": review.difficulty_score,
        "fairness_score": review.fairness_score,
    }

    try:
        response = requests.post(settings.AI_SERVICE_URL, json=payload, timeout=AI_SERVICE_TIMEOUT)
        response.raise_for_status()
        decision = response.json().get("decision")
    except (requests.RequestException, ValueError):
        return "pending"

    if decision in ("approved", "rejected", "pending"):
        return decision
    return "pending"