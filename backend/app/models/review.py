from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, func
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
    status = Column(String, nullable=False, server_default="pending", default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # status == approved iken düzenleme yapılırsa buraya yazılır, admin onaylayana kadar
    # asıl alanlar (teaching_score vs.) değişmez, public'te eski hali görünmeye devam eder.
    pending_teaching_score = Column(Integer, nullable=True)
    pending_difficulty_score = Column(Integer, nullable=True)
    pending_fairness_score = Column(Integer, nullable=True)
    pending_comment = Column(Text, nullable=True)
    has_pending_edit = Column(Boolean, default=False, nullable=False, server_default="false")

    user = relationship("User", back_populates="reviews")
    course_professor = relationship("CourseProfessor", back_populates="reviews")
    reports = relationship("Report", back_populates="review")