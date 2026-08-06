"""university'e deleted_at eklendi (unutulmuş migration)

Revision ID: e24c0e47968f
Revises: c5a957e49994
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e24c0e47968f'
down_revision: Union[str, Sequence[str], None] = 'c5a957e49994'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("universities", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("universities", "deleted_at")
