"""faculty'e partial unique index eklendi

Revision ID: 2a948bd3bc2d
Revises: b09d67b926f0
Create Date: 2026-07-26 20:15:21.139017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a948bd3bc2d'
down_revision: Union[str, Sequence[str], None] = 'b09d67b926f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("faculties", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("uq_university_faculty_name", "faculties", type_="unique")
    op.create_index(
        "uq_university_faculty_name_active",
        "faculties",
        ["university_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    op.drop_index("uq_university_faculty_name_active", table_name="faculties")
    op.create_unique_constraint("uq_university_faculty_name", "faculties", ["university_id", "name"])
    op.drop_column("faculties", "deleted_at")
