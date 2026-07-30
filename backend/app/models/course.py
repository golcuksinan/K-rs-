from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, SmallInteger, String, text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Course(Base):
    """Kanonik ders: bölüme değil ÜNİVERSİTEYE bağlı.

    Ders bölüme bağlıyken ortak dersler her bölümde ayrı satır oluyordu ve aynı fiziksel
    ders N ayrı değerlendirme havuzuna bölünüyordu. Bölüm bağı + müfredat verisi artık
    `course_departments` join tablosunda; `CourseProfessor`/`Review` kanonik derse bağlı.
    """
    __tablename__ = "courses"
    __table_args__ = (
        Index(
            "uq_university_course_code_name_active",
            "university_id", "code", "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    university = relationship("University", back_populates="courses")
    course_departments = relationship("CourseDepartment", back_populates="course")
    course_professors = relationship("CourseProfessor", back_populates="course")


class CourseDepartment(Base):
    """Dersin bir bölümün müfredatındaki yeri. Soft-delete YOK: public içerik (review)
    bu satıra bağlı değil (zincir cp→course) ve satır seed'den yeniden üretilir.
    """
    __tablename__ = "course_departments"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), primary_key=True, index=True)
    # Yarıyıl KÜMESİ, aralık değil: ders {2,3,5}'te açılıp 4'te açılmayabiliyor (derslerin
    # %28,9'unda küme süreksiz). NULL = bilinmiyor; boş dizi yazılmaz.
    semesters = Column(ARRAY(SmallInteger), nullable=True)
    is_elective = Column(Boolean, nullable=True)

    course = relationship("Course", back_populates="course_departments")
    department = relationship("Department", back_populates="course_departments")
