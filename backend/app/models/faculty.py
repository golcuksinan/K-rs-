from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index, text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Faculty(Base):
    __tablename__ = "faculties"
    __table_args__ = (
        Index(
            "uq_university_faculty_name_active",
            "university_id", "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    name = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    university = relationship("University", back_populates="faculties")
    departments = relationship("Department", back_populates="faculty")