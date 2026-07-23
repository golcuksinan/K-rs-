from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
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

    reviews = relationship("Review", back_populates="user")
    reports = relationship("Report", back_populates="reporter")