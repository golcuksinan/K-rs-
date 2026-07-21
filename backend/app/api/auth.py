from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.schemas.auth import (
    RegisterRequest, VerifyOTPRequest, LoginRequest, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.core.security import (
    hash_email, hash_password, verify_password,
    generate_otp, hash_otp, verify_otp,
    create_access_token,
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_OTP_ATTEMPTS = 5


def send_verification_email(plain_email: str, otp: str) -> None:
    # TODO: gerçek mail servisi (3. kişi DevOps ile konuşulacak)
    print(f"[MAIL] {plain_email} -> doğrulama kodu: {otp}")


def send_reset_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> şifre sıfırlama kodu: {otp}")


# ---------- 1. Register ----------

@router.post("/register", response_model=MessageResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)

    if db.query(User).filter(User.email_hash == email_hash).first():
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")

    # Aynı mail için önceki bekleyen kayıt varsa temizle, yenisini oluştur
    existing = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    otp = generate_otp()
    entry = EmailVerification(
        email_hash=email_hash,
        email_plain=payload.email.strip().lower(),
        otp_hash=hash_otp(otp),
        hashed_password=hash_password(payload.password),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(entry)
    db.commit()

    send_verification_email(entry.email_plain, otp)
    return MessageResponse(message="Doğrulama kodu e-postanıza gönderildi")


# ---------- 2. Verify OTP ----------

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    entry = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş doğrulama isteği")

    if entry.expires_at < datetime.utcnow():
        db.delete(entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Kodun süresi doldu, tekrar kayıt olun")

    if entry.attempt_count >= MAX_OTP_ATTEMPTS:
        db.delete(entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Çok fazla yanlış deneme, tekrar kayıt olun")

    if not verify_otp(payload.otp, entry.otp_hash):
        entry.attempt_count += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Kod hatalı")

    user = User(
        email_hash=entry.email_hash,
        hashed_password=entry.hashed_password,
        is_verified=True,
    )
    db.add(user)
    db.delete(entry)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ---------- 3. Login ----------

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    user = db.query(User).filter(User.email_hash == email_hash).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ---------- 4. Forgot password ----------

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = MessageResponse(
        message="Eğer bu adres kayıtlıysa, şifre sıfırlama kodu gönderildi"
    )

    email_hash = hash_email(payload.email)
    user = db.query(User).filter(User.email_hash == email_hash).first()
    if not user:
        return generic_response  # enumeration fix: her durumda aynı cevap

    otp = generate_otp()
    existing = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    entry = EmailVerification(
        email_hash=email_hash,
        email_plain=payload.email.strip().lower(),
        otp_hash=hash_otp(otp),
        hashed_password=user.hashed_password,  # reset onaylanana kadar mevcut hash korunuyor
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(entry)
    db.commit()

    send_reset_email(entry.email_plain, otp)
    return generic_response


# ---------- 5. Reset password ----------

@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    entry = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()

    if not entry or entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    if entry.attempt_count >= MAX_OTP_ATTEMPTS:
        db.delete(entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Çok fazla yanlış deneme")

    if not verify_otp(payload.otp, entry.otp_hash):
        entry.attempt_count += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Kod hatalı")

    user = db.query(User).filter(User.email_hash == email_hash).first()
    if not user:
        raise HTTPException(status_code=400, detail="Kullanıcı bulunamadı")

    user.hashed_password = hash_password(payload.new_password)
    db.delete(entry)
    db.commit()

    return MessageResponse(message="Şifreniz güncellendi")