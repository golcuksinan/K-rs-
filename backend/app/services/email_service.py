from app.services.metrics import Event, increment


# Sayaçlar bu dosyada, çağıran auth.py'de değil: SMTP gerçek gönderimle değiştirilince
# ölçüm yerinde kalsın.
def send_verification_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> doğrulama kodu: {otp}")
    increment(Event.MAIL_VERIFICATION_SENT)


def send_reset_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> şifre sıfırlama kodu: {otp}")
    increment(Event.MAIL_RESET_SENT)


def send_already_registered_email(plain_email: str) -> None:
    # Register kayıtlı bir adres için de generic yanıt döner (enumeration koruması);
    # adresin gerçek sahibi durumu ancak bu mail'den öğrenebilir.
    print(f"[MAIL] {plain_email} -> bu adres zaten kayıtlı, giriş yapmayı deneyin")
    increment(Event.MAIL_ALREADY_REGISTERED_SENT)
