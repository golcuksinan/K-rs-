from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | resolved | dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="reports")
    reporter = relationship("User", back_populates="reports")