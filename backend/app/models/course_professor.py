from sqlalchemy import Column, Integer, SmallInteger, String, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class CourseProfessor(Base):
    __tablename__ = "course_professors"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    term = Column(String, nullable=False)
    # Bu dönem/hoca açılışının hedeflediği sınıf aralığı. İkisi de NULL -> herkese açık.
    # min=max -> tek sınıf. Course'a değil buraya konuldu: aynı ders farklı dönemde farklı
    # hocayla farklı sınıflara açılabiliyor. Native enum DEĞİL, düz SmallInteger (BETWEEN için).
    target_grade_min = Column(SmallInteger, nullable=True)
    target_grade_max = Column(SmallInteger, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "target_grade_min IS NULL OR target_grade_max IS NULL OR target_grade_min <= target_grade_max",
            name="ck_course_professor_target_grade_range",
        ),
        UniqueConstraint("course_id", "professor_id", "term", name="uq_course_professor_term"),
    )

    course = relationship("Course", back_populates="course_professors")
    professor = relationship("Professor", back_populates="course_professors")
    reviews = relationship("Review", back_populates="course_professor")