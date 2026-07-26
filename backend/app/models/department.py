from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("faculty_id", "name", name="uq_faculty_department_name"),
    )

    id = Column(Integer, primary_key=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    name = Column(String, nullable=False)

    faculty = relationship("Faculty", back_populates="departments")
    courses = relationship("Course", back_populates="department")