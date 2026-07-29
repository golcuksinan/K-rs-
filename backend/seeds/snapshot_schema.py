"""Snapshot'ın kapsamı: hangi tablolar, hangi sırada, hangi üst kayda bağlı.

`TABLES` sırası FK sırasıdır — dökerken de yüklerken de bu sırayla gezilir.
`ACTIVE_PARENTS` bir modelin soft-delete zincirini verir: satırın kendi `deleted_at`'i NULL
olsa bile zincirdeki bir üst kayıt silinmişse snapshot'a girmez.
"""

from pathlib import Path

from app.models.course import Course
from app.models.course_professor import CourseProfessor
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.professor import Professor
from app.models.university import University

DEFAULT_SNAPSHOT = Path(__file__).resolve().parent / "kursu-seed.sqlite"

TABLES = [University, Faculty, Department, Course, Professor, CourseProfessor]

_TO_UNIVERSITY = [(University, Faculty.university_id == University.id)]
_TO_FACULTY = [(Faculty, Department.faculty_id == Faculty.id), *_TO_UNIVERSITY]
_TO_DEPARTMENT = [(Department, Course.department_id == Department.id), *_TO_FACULTY]

ACTIVE_PARENTS = {
    University: [],
    Faculty: _TO_UNIVERSITY,
    Department: _TO_FACULTY,
    Course: _TO_DEPARTMENT,
    Professor: [],
    CourseProfessor: [(Course, CourseProfessor.course_id == Course.id), *_TO_DEPARTMENT],
}
