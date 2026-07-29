"""auth'a bölüm ve sınıf bilgisi eklendi

Revision ID: b09d67b926f0
Revises: 85d91433d9a2
Create Date: 2026-07-26 19:18:59.673310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b09d67b926f0'
down_revision: Union[str, Sequence[str], None] = '85d91433d9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'mezun'")

    op.execute("TRUNCATE TABLE reviews, reports, users RESTART IDENTITY CASCADE")

    op.add_column('users', sa.Column('department_id', sa.Integer(), nullable=False))
    op.add_column('users', sa.Column('enrollment_year', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'users', 'departments', ['department_id'], ['id'])

    op.add_column('course_professors', sa.Column('target_grade_min', sa.SmallInteger(), nullable=True))
    op.add_column('course_professors', sa.Column('target_grade_max', sa.SmallInteger(), nullable=True))

    op.add_column('email_verifications', sa.Column('department_id', sa.Integer(), nullable=True))
    op.add_column('email_verifications', sa.Column('enrollment_year', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'email_verifications', 'departments', ['department_id'], ['id'])
    op.create_check_constraint(
        "ck_course_professor_target_grade_range",
        "course_professors",
        "target_grade_min IS NULL OR target_grade_max IS NULL OR target_grade_min <= target_grade_max",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # FK'ler upgrade'de isimsiz (None) yaratıldı -> Postgres'in otomatik verdiği adla düşürülür.
    op.drop_constraint('users_department_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'enrollment_year')
    op.drop_column('users', 'department_id')
    op.drop_constraint('email_verifications_department_id_fkey', 'email_verifications', type_='foreignkey')
    op.drop_column('email_verifications', 'enrollment_year')
    op.drop_column('email_verifications', 'department_id')
    # Check constraint iki kolonu birden referansladığı için kolonlardan önce düşürülmek zorunda.
    op.drop_constraint('ck_course_professor_target_grade_range', 'course_professors', type_='check')
    op.drop_column('course_professors', 'target_grade_max')
    op.drop_column('course_professors', 'target_grade_min')
