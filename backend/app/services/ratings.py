"""Review puan ortalamalarının tek noktadan hesaplanması.

Kural (CLAUDE.md §6): ortalamalar **her zaman** sadece `approved` review'lardan
hesaplanır — admin tüm review'ları görse bile. Bu filtre burada sabittir, çağıran
endpoint'in geçebileceği bir parametre değildir.

Her fonksiyon tek bir GROUP BY sorgusu çalıştırır; endpoint'ler ilişki üzerinden
Python döngüsüyle ortalama hesaplamaz (N+1).
"""

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course_professor import CourseProfessor
from app.models.review import Review

APPROVED = "approved"


@dataclass(frozen=True)
class RatingAggregate:
    average_teaching_score: Optional[float] = None
    average_difficulty_score: Optional[float] = None
    average_fairness_score: Optional[float] = None
    review_count: int = 0


EMPTY_RATING = RatingAggregate()


def _to_float(value) -> Optional[float]:
    # Postgres avg() Decimal döner; şemalar float bekliyor.
    return float(value) if value is not None else None


def _aggregate_columns():
    return (
        func.avg(Review.teaching_score),
        func.avg(Review.difficulty_score),
        func.avg(Review.fairness_score),
        func.count(Review.id),
    )


def _rows_to_map(rows) -> Dict[int, RatingAggregate]:
    return {
        key: RatingAggregate(
            average_teaching_score=_to_float(teaching),
            average_difficulty_score=_to_float(difficulty),
            average_fairness_score=_to_float(fairness),
            review_count=count,
        )
        for key, teaching, difficulty, fairness, count in rows
    }


def rating_by_course_professor(db: Session, cp_ids: Iterable[int]) -> Dict[int, RatingAggregate]:
    """course_professor_id -> RatingAggregate. Hiç approved review'ı olan anahtar döner;
    olmayanlar için çağıran taraf EMPTY_RATING kullanır."""
    ids = list(cp_ids)
    if not ids:
        return {}

    rows = (
        db.query(Review.course_professor_id, *_aggregate_columns())
        .filter(Review.course_professor_id.in_(ids), Review.status == APPROVED)
        .group_by(Review.course_professor_id)
        .all()
    )
    return _rows_to_map(rows)


def rating_by_course(db: Session, professor_id: int) -> Dict[int, RatingAggregate]:
    """course_id -> RatingAggregate, tek hocanın verdiği dersler için (dönemler birleştirilir)."""
    rows = (
        db.query(CourseProfessor.course_id, *_aggregate_columns())
        .join(Review, Review.course_professor_id == CourseProfessor.id)
        .filter(CourseProfessor.professor_id == professor_id, Review.status == APPROVED)
        .group_by(CourseProfessor.course_id)
        .all()
    )
    return _rows_to_map(rows)


def rating_by_professor(db: Session, professor_ids: Iterable[int]) -> Dict[int, RatingAggregate]:
    """professor_id -> RatingAggregate (hocanın tüm ders/dönem açılışları birleştirilir)."""
    ids = list(professor_ids)
    if not ids:
        return {}

    rows = (
        db.query(CourseProfessor.professor_id, *_aggregate_columns())
        .join(Review, Review.course_professor_id == CourseProfessor.id)
        .filter(CourseProfessor.professor_id.in_(ids), Review.status == APPROVED)
        .group_by(CourseProfessor.professor_id)
        .all()
    )
    return _rows_to_map(rows)
