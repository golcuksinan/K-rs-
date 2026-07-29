"""course_professors (course_id, professor_id, term) unique constraint

Revision ID: e7b2c9d5a4f1
Revises: d4e8a1f6c3b9
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b2c9d5a4f1'
down_revision: Union[str, Sequence[str], None] = 'd4e8a1f6c3b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_course_professor_term',
        'course_professors',
        ['course_id', 'professor_id', 'term'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_course_professor_term', 'course_professors', type_='unique')
