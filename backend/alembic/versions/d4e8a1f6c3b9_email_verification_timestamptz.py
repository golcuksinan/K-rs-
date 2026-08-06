"""email_verification tarih kolonları timezone-aware yapıldı

Revision ID: d4e8a1f6c3b9
Revises: a1c9f4b7e2d3
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a1f6c3b9'
down_revision: Union[str, Sequence[str], None] = 'a1c9f4b7e2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Mevcut naive değerler utcnow ile yazılmıştı -> UTC varsayılarak dönüştürülür.
    op.alter_column(
        'email_verifications', 'expires_at',
        type_=sa.DateTime(timezone=True),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'email_verifications', 'created_at',
        type_=sa.DateTime(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'email_verifications', 'expires_at',
        type_=sa.DateTime(),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'email_verifications', 'created_at',
        type_=sa.DateTime(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
