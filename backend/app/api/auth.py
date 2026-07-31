from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.common import get_active_or_400
from app.db.session import get_db
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.models.department import Department

from app.schemas.auth import (
    RegisterRequest, VerifyOTPRequest, LoginRequest, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.core.security import (
    EMAIL_DOMAIN_UNIVERSITIES, email_domain, tr_casefold,
    hash_email, hash_password, verify_password, dummy_verify_password,
    generate_otp, hash_otp, verify_otp,
    create_access_token,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.services.email_service import (
    send_verification_email, send_reset_email, send_already_registered_email,
)
from app.services.metrics import Event, increment

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_OTP_ATTEMPTS = 5


def cleanup_expired_verifications(db: Session) -> None:
    db.query(EmailVerification).filter(
        EmailVerification.expires_at < datetime.now(timezone.utc)
    ).delete(synchronize_session=False)
    db.commit()


@router.post("/register", response_model=MessageResponse)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    cleanup_expired_verifications(db)

    department = get_active_or_400(db, Department, payload.department_id, "department_id")
    # Bölüm aktif olsa da üstü silinmiş olabilir; silinmiş fakülte/üniversite zincirine kayıt
    # olunmaz (create uçlarındaki "silinmiş üst kayda bağlama" kuralının kayıt tarafı).
    if department.faculty.deleted_at is not None or department.faculty.university.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Geçersiz department_id")

    # E-posta domain'i hangi üniversiteye aitse bölüm de o üniversiteden seçilmek zorunda.
    allowed_university = EMAIL_DOMAIN_UNIVERSITIES.get(email_domain(payload.email))
    if allowed_university is not None and tr_casefold(department.faculty.university.name) != tr_casefold(allowed_university):
        raise HTTPException(
            status_code=400,
            detail=f"Bu e-posta adresiyle yalnızca {allowed_university} bölümlerine kayıt olunabilir",
        )

    generic_response = MessageResponse(message="Doğrulama kodu e-postanıza gönderildi")

    # Hash her dalda hesaplanır; e-posta kayıtlıyken atlansa yanıt süresi farkı
    # adresin varlığını sızdırır (login'deki dummy_verify ile aynı gerekçe).
    email_hash = hash_email(payload.email)
    hashed_password = hash_password(payload.password)

    # Kayıtlı e-posta için de aynı yanıt döner (enumeration koruması); adresin sahibi
    # durumu mail'den öğrenir.
    if db.query(User).filter(User.email_hash == email_hash).first():
        send_already_registered_email(payload.email.strip().lower())
        return generic_response

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
        hashed_password=hashed_password,
        department_id=payload.department_id,
        enrollment_year=payload.enrollment_year,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(entry)
    db.commit()

    increment(Event.AUTH_REGISTER_STARTED)
    send_verification_email(entry.email_plain, otp)
    return generic_response


@router.post("/verify-otp", response_model=TokenResponse)
@limiter.limit("5/minute")
def verify_otp_endpoint(request: Request, payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    entry = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş doğrulama isteği")

    if entry.expires_at < datetime.now(timezone.utc):
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
        increment(Event.AUTH_OTP_FAILED)
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

    increment(Event.AUTH_REGISTER_COMPLETED)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    user = db.query(User).filter(User.email_hash == email_hash).first()

    # Sayaç yalnızca sayar: e-posta/IP tutulmaz. Üç dalın üçünde de tek increment var,
    # yanıt süresi farkı adresin varlığını sızdırmasın.
    if not user:
        # Kullanıcı yokken de bcrypt maliyeti ödenir; yanıt her iki durumda da aynı.
        dummy_verify_password()
        increment(Event.AUTH_LOGIN_FAILED)
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    if not verify_password(payload.password, user.hashed_password):
        increment(Event.AUTH_LOGIN_FAILED)
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    increment(Event.AUTH_LOGIN_SUCCEEDED)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


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
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(entry)
    db.commit()

    increment(Event.AUTH_PASSWORD_RESET_REQUESTED)
    send_reset_email(entry.email_plain, otp)
    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    entry = db.query(EmailVerification).filter(
        EmailVerification.email_hash == email_hash
    ).first()

    if not entry or entry.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    if entry.attempt_count >= MAX_OTP_ATTEMPTS:
        db.delete(entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Çok fazla yanlış deneme")

    if not verify_otp(payload.otp, entry.otp_hash):
        entry.attempt_count += 1
        db.commit()
        increment(Event.AUTH_OTP_FAILED)
        raise HTTPException(status_code=400, detail="Kod hatalı")

    user = db.query(User).filter(User.email_hash == email_hash).first()
    if not user:
        raise HTTPException(status_code=400, detail="Kullanıcı bulunamadı")

    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.delete(entry)
    db.commit()

    increment(Event.AUTH_PASSWORD_RESET_COMPLETED)
    return MessageResponse(message="Şifreniz güncellendi")