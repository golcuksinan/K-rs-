"""Review puan ortalamalarının tek noktadan hesaplanması.

Kural (CLAUDE.md §6): ortalamalar **her zaman** sadece `approved` review'lardan
hesaplanır — admin tüm review'ları görse bile. Bu filtre burada sabittir, çağıran
endpoint'in geçebileceği bir parametre değildir.

Her fonksiyon tek bir GROUP BY sorgusu çalıştırır; endpoint'ler ilişki üzerinden
Python döngüsüyle ortalama hesaplamaz (N+1).

Ders ve hoca düzeyi ortalamalar kişi başına tekilleştirilir (`_per_user_subquery`):
tekil kısıt `(user_id, course_professor_id)` olduğu için bir kullanıcı aynı hocanın
farklı dönem/ders açılışlarına ayrı ayrı yorum yazabilir — ki bu meşrudur, hocanın
davranışı dönemler arasında değişir — ama ortalamada bir kişi bir kez sayılmalıdır.
Dönem düzeyinde (`rating_by_course_professor`) tekilleştirmeye gerek yoktur, kısıt
zaten kişi başı tek yorum garanti eder.
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
            # sum() Decimal döner, count() int; şema int bekliyor.
            review_count=int(count),
        )
        for key, teaching, difficulty, fairness, count in rows
    }


def _per_user_subquery(db: Session, key_column, *filters):
    """İç adım: (anahtar, kullanıcı) başına ortalama. `user_id` yalnızca burada kullanılır,
    dış sorguya taşınmaz — anonimlik değişmezi gereği dışarıya hiç çıkmaz."""
    return (
        db.query(
            key_column.label("key"),
            Review.user_id.label("user_id"),
            func.avg(Review.teaching_score).label("teaching"),
            func.avg(Review.difficulty_score).label("difficulty"),
            func.avg(Review.fairness_score).label("fairness"),
            func.count(Review.id).label("review_count"),
        )
        .join(CourseProfessor, CourseProfessor.id == Review.course_professor_id)
        .filter(*filters, Review.status == APPROVED)
        .group_by(key_column, Review.user_id)
        .subquery()
    )


def _per_user_rows(db: Session, sub):
    """Dış adım: kişi ortalamalarının ortalaması. `review_count` yorum sayısı olarak kalır
    (yorumlayan sayısı değil) — kullanıcıya gösterilen "N değerlendirme" metni bu."""
    return (
        db.query(
            sub.c.key,
            func.avg(sub.c.teaching),
            func.avg(sub.c.difficulty),
            func.avg(sub.c.fairness),
            func.sum(sub.c.review_count),
        )
        .group_by(sub.c.key)
        .all()
    )


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
    """course_id -> RatingAggregate, tek hocanın verdiği dersler için (dönemler birleştirilir,
    aynı dersi birden çok dönem yorumlayan kullanıcı bir kez sayılır)."""
    sub = _per_user_subquery(
        db, CourseProfessor.course_id, CourseProfessor.professor_id == professor_id
    )
    return _rows_to_map(_per_user_rows(db, sub))


def rating_by_professor(db: Session, professor_ids: Iterable[int]) -> Dict[int, RatingAggregate]:
    """professor_id -> RatingAggregate (hocanın tüm ders/dönem açılışları birleştirilir,
    aynı hocayı birden çok kez yorumlayan kullanıcı bir kez sayılır)."""
    ids = list(professor_ids)
    if not ids:
        return {}

    sub = _per_user_subquery(
        db, CourseProfessor.professor_id, CourseProfessor.professor_id.in_(ids)
    )
    return _rows_to_map(_per_user_rows(db, sub))
