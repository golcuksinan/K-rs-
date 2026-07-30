from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer,
    SmallInteger, String, text,
)
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
        CheckConstraint(
            "semester_min IS NULL OR semester_max IS NULL OR semester_min <= semester_max",
            name="ck_course_semester_range",
        ),
    )

    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    # Müfredat verisi (EBS ders planından). Üçü de nullable: PAÜ dışı / admin'in elle açtığı
    # derste bilgi yok, NULL "bilinmiyor" demek.
    # ⚠️ semester_min/max bir ARALIK, veri ise KÜME: ders {2,3,5} yarıyılda açılıyorsa 2-5
    # saklanır ve 4 de kapsanmış görünür (ölçüm: derslerin %28,9'u böyle). Etiket/sıralama
    # için yeterli, yarıyıl FİLTRESİ için değil — filtre bu yüzden bilinçli olarak yok (§9.3).
    semester_min = Column(SmallInteger, nullable=True)
    semester_max = Column(SmallInteger, nullable=True)
    is_elective = Column(Boolean, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    department = relationship("Department", back_populates="courses")
    course_professors = relationship("CourseProfessor", back_populates="course")