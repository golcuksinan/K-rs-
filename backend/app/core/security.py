import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def normalize_email(email: str) -> str:
    return email.strip().lower()

def hash_email(email: str) -> str:
    normalized = normalize_email(email)
    return hmac.new(
        settings.EMAIL_PEPPER_KEY.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()

def is_valid_edu_tr_email(email: str) -> bool:
    normalized = normalize_email(email)
    return normalized.endswith("@posta.pau.edu.tr")

def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(plain_otp), otp_hash)

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except JWTError:
        return None