from sqlalchemy import Column, Integer, String, DateTime, Index, text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class University(Base):
    __tablename__ = "universities"
    __table_args__ = (
        Index(
            "uq_university_name_active",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=True)
    city = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    faculties = relationship("Faculty", back_populates="university")