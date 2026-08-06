"""university name partial unique index eklendi

Revision ID: a1c9f4b7e2d3
Revises: 03e177d0692f
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f4b7e2d3'
down_revision: Union[str, Sequence[str], None] = '03e177d0692f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'uq_university_name_active',
        'universities',
        ['name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_university_name_active', table_name='universities')
