from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime
from app.db.base_class import Base


def default_expiry():
    return datetime.utcnow() + timedelta(minutes=10)


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email_hash = Column(String, unique=True, index=True, nullable=False)  # dup-request kontrolü için
    email_plain = Column(String, nullable=False)  # sadece doğrulama tamamlanana kadar geçici
    otp_hash = Column(String, nullable=False)  # OTP'nin kendisi de DB'de plain tutulmuyor
    hashed_password = Column(String, nullable=False)  # kayıt anında hash'lenir, plain hiç saklanmaz
    expires_at = Column(DateTime, default=default_expiry, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)  # OTP brute-force limiti için
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)