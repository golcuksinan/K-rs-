from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email_hash = Column(String, unique=True, index=True, nullable=False)  # email yerine
    hashed_password = Column(String, nullable=False)  # password_hash yerine
    is_verified = Column(Boolean, default=False)

    reviews = relationship("Review", back_populates="user")
    reports = relationship("Report", back_populates="reporter")