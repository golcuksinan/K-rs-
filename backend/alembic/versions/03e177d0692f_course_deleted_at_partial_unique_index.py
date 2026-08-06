"""course deleted_at ve partial unique index eklendi

Revision ID: 03e177d0692f
Revises: 8d594d8452ff
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03e177d0692f'
down_revision: Union[str, Sequence[str], None] = '8d594d8452ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('courses', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        'uq_department_course_name_active',
        'courses',
        ['department_id', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_department_course_name_active', table_name='courses')
    op.drop_column('courses', 'deleted_at')
