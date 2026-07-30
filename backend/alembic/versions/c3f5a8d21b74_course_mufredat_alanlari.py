"""courses'a müfredat alanları (semester_min/max, is_elective); course_professors.target_grade_* düşürüldü

Revision ID: c3f5a8d21b74
Revises: e7b2c9d5a4f1
Create Date: 2026-07-29 00:00:00.000000

Müfredat verisi (yarıyıl + zorunlu/seçmeli) EBS ders planından geliyor ve (ders, program)
düzeyinde — yani Course'a ait. target_grade_min/max yanlış katmandaydı: 37 bin
course_professor satırına tekrar eden bir müfredat bilgisiydi, tamamı NULL kaldı ve hocası
olmayan 5.322 dersi hiç kapsayamıyordu. Hiçbir kod okumuyor/yazmıyordu, veri kaybı yok.

⚠️ Üç yeni kolon da nullable — PAÜ dışı ve admin'in elle açtığı derslerde bilgi yok.
Bu yüzden server_default gerekmiyor (§7'deki NOT NULL tuzağı burada geçerli değil).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f5a8d21b74'
down_revision: Union[str, Sequence[str], None] = 'e7b2c9d5a4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('courses', sa.Column('semester_min', sa.SmallInteger(), nullable=True))
    op.add_column('courses', sa.Column('semester_max', sa.SmallInteger(), nullable=True))
    op.add_column('courses', sa.Column('is_elective', sa.Boolean(), nullable=True))
    op.create_check_constraint(
        'ck_course_semester_range',
        'courses',
        'semester_min IS NULL OR semester_max IS NULL OR semester_min <= semester_max',
    )

    op.drop_constraint('ck_course_professor_target_grade_range', 'course_professors', type_='check')
    op.drop_column('course_professors', 'target_grade_max')
    op.drop_column('course_professors', 'target_grade_min')


def downgrade() -> None:
    op.add_column('course_professors', sa.Column('target_grade_min', sa.SmallInteger(), nullable=True))
    op.add_column('course_professors', sa.Column('target_grade_max', sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        'ck_course_professor_target_grade_range',
        'course_professors',
        'target_grade_min IS NULL OR target_grade_max IS NULL OR target_grade_min <= target_grade_max',
    )

    op.drop_constraint('ck_course_semester_range', 'courses', type_='check')
    op.drop_column('courses', 'is_elective')
    op.drop_column('courses', 'semester_max')
    op.drop_column('courses', 'semester_min')
