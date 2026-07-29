import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Kabul edilen e-posta domain'i -> o domain'in bağlı olduğu üniversitenin DB'deki adı.
# Register hem e-postayı bu domain'lerle sınırlar hem de seçilen bölümün bu üniversiteye
# ait olduğunu doğrular. Yeni üniversite desteği = buraya bir satır.
EMAIL_DOMAIN_UNIVERSITIES = {
    "posta.pau.edu.tr": "Pamukkale Üniversitesi",
}

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def dummy_verify_password() -> None:
    """Kullanıcı bulunamadığında da bcrypt maliyeti ödenir; yoksa yanıt süresi farkı
    e-postanın kayıtlı olup olmadığını sızdırır (timing enumeration)."""
    pwd_context.dummy_verify()

def normalize_email(email: str) -> str:
    return email.strip().lower()

def hash_email(email: str) -> str:
    normalized = normalize_email(email)
    return hmac.new(
        settings.EMAIL_PEPPER_KEY.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()

def email_domain(email: str) -> str:
    return normalize_email(email).rsplit("@", 1)[-1]

def is_valid_edu_tr_email(email: str) -> bool:
    return email_domain(email) in EMAIL_DOMAIN_UNIVERSITIES

def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(plain_otp), otp_hash)

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except JWTError:
        return None