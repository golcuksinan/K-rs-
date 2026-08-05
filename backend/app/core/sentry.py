import sentry_sdk

from app.core.config import settings


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        # Anonimlik değişmezi: hiçbir olayda yorum metni, e-posta veya kullanıcı eşleşmesi
        # dışarı çıkmamalı. Üç ayarın hepsi gerekli — biri açık kalırsa yorum gövdesi
        # (request body), e-posta/email_hash (local değişkenler) veya IP (default PII) sızar.
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        # Performans izleme kapalı: hata takibi için gerekmiyor, ücretsiz kotayı yiyor.
        traces_sample_rate=0.0,
        before_send=_scrub,
    )


def _scrub(event, hint):
    # Header'lar send_default_pii'den bağımsız gönderilir; token ve çerez burada düşer.
    headers = event.get("request", {}).get("headers")
    if headers:
        for name in list(headers):
            if name.lower() in ("authorization", "cookie", "cf-connecting-ip", "x-forwarded-for"):
                del headers[name]
    return event
