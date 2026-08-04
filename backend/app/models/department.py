from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index, text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index(
            "uq_faculty_department_name_active",
            "faculty_id", "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # İfade common.py:search_filter()'ınkiyle birebir aynı olmalı, yoksa kullanılmaz.
        Index(
            "ix_departments_name_trgm",
            text("lower(translate(name, 'İIıŞşĞğÜüÖöÇç', 'iiissgguuoocc')) gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )

    id = Column(Integer, primary_key=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    name = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    faculty = relationship("Faculty", back_populates="departments")
    course_departments = relationship("CourseDepartment", back_populates="department")