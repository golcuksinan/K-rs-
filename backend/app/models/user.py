from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email_hash = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.student)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    enrollment_year = Column(Integer, nullable=False)  # giriş yılı; sınıf buradan anlık hesaplanır
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Şifre sıfırlandığında dolar: bu andan ÖNCE üretilmiş token'lar geçersiz sayılır (deps.py).
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    department = relationship("Department")
    reviews = relationship("Review", back_populates="user")
    reports = relationship("Report", back_populates="reporter")