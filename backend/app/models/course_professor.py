from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class CourseProfessor(Base):
    __tablename__ = "course_professors"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    term = Column(String, nullable=False)

    course = relationship("Course", back_populates="course_professors")
    professor = relationship("Professor", back_populates="course_professors")
    reviews = relationship("Review", back_populates="course_professor")