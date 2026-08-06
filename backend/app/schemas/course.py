from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    professor_count: int
    # Ders kaç bölümün müfredatında listeleniyor (ortak seçmeli havuzunda yüksek).
    department_count: int
    # Ders artık üniversite düzeyinde kanonik: bölüm/fakülte alanları yalnızca ?department_id=
    # dalında dolu. search dalında ders N bölüme ait olabildiği için hepsi None.
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    # Müfredat verisi (ders, bölüm) ikilisine ait — bölüm bilinmeden anlamı yok, search
    # dalında None. semesters bir KÜME: ders arada bir yarıyılda açılmıyor olabilir.
    semesters: Optional[list[int]] = None
    is_elective: Optional[bool] = None
    university_id: int
    university_name: str
    university_short_name: Optional[str] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    department_id: int
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    code: Optional[str] = Field(default=None, min_length=1)
