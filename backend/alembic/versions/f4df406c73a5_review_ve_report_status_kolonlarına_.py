"""review ve report status kolonlarına server_default eklendi

Revision ID: f4df406c73a5
Revises: a4c17e93d052
Create Date: 2026-07-31 21:10:04.259068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4df406c73a5'
down_revision: Union[str, Sequence[str], None] = 'a4c17e93d052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL'dan önce backfill: mevcut NULL satırlar olmasa da sıra bir kısıt.
    op.execute("UPDATE reviews SET status = 'pending' WHERE status IS NULL")
    op.execute("UPDATE reports SET status = 'pending' WHERE status IS NULL")
    op.alter_column(
        "reviews", "status", existing_type=sa.String(), nullable=False, server_default="pending"
    )
    op.alter_column(
        "reports", "status", existing_type=sa.String(), nullable=False, server_default="pending"
    )


def downgrade() -> None:
    op.alter_column(
        "reviews", "status", existing_type=sa.String(), nullable=True, server_default=None
    )
    op.alter_column(
        "reports", "status", existing_type=sa.String(), nullable=True, server_default=None
    )
