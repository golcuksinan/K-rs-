def send_verification_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> doğrulama kodu: {otp}")


def send_reset_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> şifre sıfırlama kodu: {otp}")


def send_already_registered_email(plain_email: str) -> None:
    # Register kayıtlı bir adres için de generic yanıt döner (enumeration koruması);
    # adresin gerçek sahibi durumu ancak bu mail'den öğrenebilir.
    print(f"[MAIL] {plain_email} -> bu adres zaten kayıtlı, giriş yapmayı deneyin")
