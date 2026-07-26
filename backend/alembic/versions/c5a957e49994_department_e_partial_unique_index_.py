"""department'e partial unique index eklendi

Revision ID: c5a957e49994
Revises: 2a948bd3bc2d
Create Date: 2026-07-26 20:19:27.754583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5a957e49994'
down_revision: Union[str, Sequence[str], None] = '2a948bd3bc2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("departments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("uq_faculty_department_name", "departments", type_="unique")
    op.create_index(
        "uq_faculty_department_name_active",
        "departments",
        ["faculty_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    op.drop_index("uq_faculty_department_name_active", table_name="departments")
    op.create_unique_constraint("uq_faculty_department_name", "departments", ["faculty_id", "name"])
    op.drop_column("departments", "deleted_at")