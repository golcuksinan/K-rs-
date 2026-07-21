from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_professor_id = Column(Integer, ForeignKey("course_professors.id"), nullable=False)
    teaching_score = Column(Integer, nullable=False)
    difficulty_score = Column(Integer, nullable=False)
    fairness_score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reviews")
    course_professor = relationship("CourseProfessor", back_populates="reviews")
    reports = relationship("Report", back_populates="review")