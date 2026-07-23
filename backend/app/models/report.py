from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("reporter_id", "review_id", name="uq_reporter_review_report"),
    )

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | resolved | dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="reports")
    reporter = relationship("User", back_populates="reports")