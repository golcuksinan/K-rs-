from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.models.department import Department

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
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_OTP_ATTEMPTS = 5


def send_verification_email(plain_email: str, otp: str) -> None:
    # TODO: gerçek mail servisi (DevOps ile konuşulacak)
    print(f"[MAIL] {plain_email} -> doğrulama kodu: {otp}")


def send_reset_email(plain_email: str, otp: str) -> None:
    print(f"[MAIL] {plain_email} -> şifre sıfırlama kodu: {otp}")

def cleanup_expired_verifications(db: Session) -> None:
    db.query(EmailVerification).filter(
        EmailVerification.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    db.commit()

# ---------- 1. Register ----------

@router.post("/register", response_model=MessageResponse)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    cleanup_expired_verifications(db) 

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

    if not db.query(Department).filter(Department.id == payload.department_id).first():
        raise HTTPException(status_code=400, detail="Geçersiz department_id")
    
    otp = generate_otp()
    entry = EmailVerification(
        email_hash=email_hash,
        email_plain=payload.email.strip().lower(),
        otp_hash=hash_otp(otp),
        hashed_password=hash_password(payload.password),
        department_id=payload.department_id,
        enrollment_year=payload.enrollment_year,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(entry)
    db.commit()

    send_verification_email(entry.email_plain, otp)
    return MessageResponse(message="Doğrulama kodu e-postanıza gönderildi")


# ---------- 2. Verify OTP ----------

@router.post("/verify-otp", response_model=TokenResponse)
@limiter.limit("5/minute")
def verify_otp_endpoint(request: Request, payload: VerifyOTPRequest, db: Session = Depends(get_db)):
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

    # Cross-flow koruması: forgot-password kaydında bu iki alan boş kalır. Guard olmazsa
    # ikinci bir User yaratılmaya çalışılıp email_hash unique + NOT NULL ihlali → 500.
    # Kalıcı çözüm EmailVerification.purpose kolonu olurdu (migration ister, MVP'de yok).
    if entry.department_id is None or entry.enrollment_year is None:
        raise HTTPException(
            status_code=400,
            detail="Bu kod şifre sıfırlama için üretilmiş, kayıt için kullanılamaz",
        )

    user = User(
        email_hash=entry.email_hash,
        hashed_password=entry.hashed_password,
        is_verified=True,
        department_id=entry.department_id,
        enrollment_year=entry.enrollment_year,
    )
    db.add(user)
    db.delete(entry)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ---------- 3. Login ----------

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    user = db.query(User).filter(User.email_hash == email_hash).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ---------- 4. Forgot password ----------

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    cleanup_expired_verifications(db) 
    
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
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
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