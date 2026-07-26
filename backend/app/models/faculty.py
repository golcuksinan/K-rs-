from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Faculty(Base):
    __tablename__ = "faculties"
    __table_args__ = (
        UniqueConstraint("university_id", "name", name="uq_university_faculty_name"),
    )

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    name = Column(String, nullable=False)

    university = relationship("University", back_populates="faculties")
    departments = relationship("Department", back_populates="faculty")