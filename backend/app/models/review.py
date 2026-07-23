from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "course_professor_id", name="uq_user_course_professor_review"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_professor_id = Column(Integer, ForeignKey("course_professors.id"), nullable=False)
    teaching_score = Column(Integer, nullable=False)
    difficulty_score = Column(Integer, nullable=False)
    fairness_score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reviews")
    course_professor = relationship("CourseProfessor", back_populates="reviews")
    reports = relationship("Report", back_populates="review")