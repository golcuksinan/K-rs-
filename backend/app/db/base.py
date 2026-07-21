from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.university import University
from app.models.department import Department
from app.models.course import Course
from app.models.professor import Professor
from app.models.course_professor import CourseProfessor
from app.models.user import User
from app.models.review import Review
from app.models.report import Report