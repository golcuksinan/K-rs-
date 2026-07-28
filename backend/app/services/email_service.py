def send_verification_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> doğrulama kodu: {otp}")


def send_reset_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> şifre sıfırlama kodu: {otp}")
