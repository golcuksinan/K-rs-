from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Professor(Base):
    __tablename__ = "professors"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)

    course_professors = relationship("CourseProfessor", back_populates="professor")