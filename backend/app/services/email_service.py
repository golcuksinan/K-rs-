import logging

import resend
from resend.http_client_requests import RequestsClient

from app.core.config import settings
from app.services.metrics import Event, increment

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY
# SDK varsayılanı 30 sn: gönderim kayıt isteğinin içinde, threadpool token'ı tutuyor.
resend.default_http_client = RequestsClient(timeout=5)


def _send(plain_email: str, subject: str, body: str) -> bool:
    """Gönderim başarılıysa True. Hata yukarı fırlatılmaz: mail servisi kayıt/sıfırlama
    akışını kırmamalı, ama sayaç da artmamalı — gitmeyen mail 'gönderildi' sayılmaz."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing, mail not sent")
        print(f"[MAIL] {plain_email} -> {subject}: {body}")
        return True

    try:
        resend.Emails.send({
            "from": settings.MAIL_FROM,
            "to": [plain_email],
            "subject": subject,
            "text": body,
        })
    except Exception as e:
        # Hata metni adresi içerebilir, tipiyle yetiniliyor.
        logger.error(f"Mail Service Error: {type(e).__name__}")
        increment(Event.MAIL_FAILED)
        return False

    return True


# Sayaçlar bu dosyada, çağıran auth.py'de değil: SMTP gerçek gönderimle değiştirilince
# ölçüm yerinde kalsın.
def send_verification_email(plain_email: str, otp: str) -> None:
    if _send(
        plain_email,
        "Kürsü doğrulama kodu",
        f"Doğrulama kodunuz: {otp}\n\n"
        f"Kod {settings.OTP_EXPIRE_MINUTES} dakika geçerlidir. "
        "Bu isteği siz yapmadıysanız bu e-postayı yok sayın.",
    ):
        increment(Event.MAIL_VERIFICATION_SENT)


def send_reset_email(plain_email: str, otp: str) -> None:
    if _send(
        plain_email,
        "Kürsü şifre sıfırlama kodu",
        f"Şifre sıfırlama kodunuz: {otp}\n\n"
        f"Kod {settings.OTP_EXPIRE_MINUTES} dakika geçerlidir. "
        "Bu isteği siz yapmadıysanız bu e-postayı yok sayın.",
    ):
        increment(Event.MAIL_RESET_SENT)


def send_already_registered_email(plain_email: str) -> None:
    # Register kayıtlı bir adres için de generic yanıt döner (enumeration koruması);
    # adresin gerçek sahibi durumu ancak bu mail'den öğrenebilir.
    if _send(
        plain_email,
        "Kürsü hesabınız zaten var",
        "Bu adresle bir Kürsü hesabı zaten kayıtlı. Giriş yapmayı deneyin, "
        "şifrenizi hatırlamıyorsanız şifre sıfırlama akışını kullanın.",
    ):
        increment(Event.MAIL_ALREADY_REGISTERED_SENT)
