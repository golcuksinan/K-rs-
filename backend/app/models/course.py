from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index, text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        Index(
            "uq_department_course_name_active",
            "department_id", "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    department = relationship("Department", back_populates="courses")
    course_professors = relationship("CourseProfessor", back_populates="course")