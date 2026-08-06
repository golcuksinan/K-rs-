"""email_verifications.email_plain kolonu kaldırıldı

Revision ID: d3b1f6c0a2e9
Revises: ca37a91e7b75
Create Date: 2026-08-05 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3b1f6c0a2e9'
down_revision: Union[str, Sequence[str], None] = 'ca37a91e7b75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("email_verifications", "email_plain")


def downgrade() -> None:
    # Geri alınırsa bekleyen satırlarda adres yok; NOT NULL için boş string yazılır.
    op.add_column(
        "email_verifications",
        sa.Column("email_plain", sa.String(), nullable=False, server_default=""),
    )
    op.alter_column("email_verifications", "email_plain", server_default=None)
