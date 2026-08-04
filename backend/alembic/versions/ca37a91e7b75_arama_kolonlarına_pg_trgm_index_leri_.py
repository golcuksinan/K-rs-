"""arama kolonlarına pg_trgm index'leri eklendi

Revision ID: ca37a91e7b75
Revises: c68bdebc16e0
Create Date: 2026-08-04 17:13:48.272775

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ca37a91e7b75'
down_revision: Union[str, Sequence[str], None] = 'c68bdebc16e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# İfade, common.py:search_filter()'ın ürettiği SQL ile birebir aynı olmalı; farklı yazılırsa
# planlayıcı index'i kullanmaz, sessizce seq scan'e döner.
_FOLD = "lower(translate({col}, 'İIıŞşĞğÜüÖöÇç', 'iiissgguuoocc'))"

# search_filter() kullanan diğer kolonlar (universities, professors, faculties) index almadı:
# tablolar birkaç bin satır, planlayıcı orada seq scan'i seçiyor — index yazma maliyeti ve
# yer kaplar, kullanılmaz.
_INDEXES = [
    ("ix_departments_name_trgm", "departments", "name"),
    ("ix_courses_name_trgm", "courses", "name"),
    ("ix_courses_code_trgm", "courses", "code"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # Heroku Postgres eklentilerin `heroku_ext` şemasına kurulmasını şart koşar; şema yoksa
    # (yerel/docker) varsayılana kurulur.
    heroku_ext = op.get_bind().exec_driver_sql(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'heroku_ext'"
    ).first()
    target = " WITH SCHEMA heroku_ext" if heroku_ext else ""
    op.execute(f"CREATE EXTENSION IF NOT EXISTS pg_trgm{target}")
    for name, table, column in _INDEXES:
        op.execute(
            f"CREATE INDEX {name} ON {table} "
            f"USING gin ({_FOLD.format(col=column)} gin_trgm_ops)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for name, _, _ in _INDEXES:
        op.execute(f"DROP INDEX {name}")
    op.execute("DROP EXTENSION pg_trgm")
