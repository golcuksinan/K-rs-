from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("university_id", "name", name="uq_university_department_name"),
    )

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    name = Column(String, nullable=False)

    university = relationship("University", back_populates="departments")
    courses = relationship("Course", back_populates="department")