"""olay sayaçları için event_daily_counters tablosu eklendi

Revision ID: a4c17e93d052
Revises: f2a6d81b0c37
Create Date: 2026-07-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4c17e93d052'
down_revision: Union[str, Sequence[str], None] = 'f2a6d81b0c37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite PK aynı zamanda upsert'in ON CONFLICT (day, event) hedefi — ayrı unique
    # constraint gerekmiyor ama biri olmadan sayaç artırma çalışmaz.
    op.create_table(
        "event_daily_counters",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("day", "event", name="pk_event_daily_counters"),
    )


def downgrade() -> None:
    op.drop_table("event_daily_counters")
