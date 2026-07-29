"""Tüm modelleri tek noktadan import eder.

⚠️ Aşağıdaki importlar kullanılmıyor GİBİ görünür ama silinemez: alembic autogenerate
şemayı `Base.metadata`'dan okur (import edilmeyen model migration'a girmez) ve SQLAlchemy
`relationship("Faculty")` gibi string referansları ancak tüm sınıflar register edildikten
sonra çözebilir — eksik import mapper configure sırasında InvalidRequestError verir.
"""

from app.db.base_class import Base

from app.models.university import University
from app.models.faculty import Faculty 
from app.models.department import Department
from app.models.course import Course
from app.models.professor import Professor
from app.models.course_professor import CourseProfessor
from app.models.user import User
from app.models.review import Review
from app.models.report import Report
from app.models.email_verification import EmailVerification