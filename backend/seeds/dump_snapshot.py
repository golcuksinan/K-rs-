"""Mevcut DB'deki akademik veriyi tek bir .sqlite dosyasına döker (seed snapshot'ı).

Kullanım (çalışma dizini backend/ olmalı):
    python seeds/dump_snapshot.py --dry-run
    python seeds/dump_snapshot.py
    python seeds/dump_snapshot.py --out /yol/kursu-seed.sqlite --force

Kapsam: universities, faculties, departments, courses, professors, course_professors.
users / email_verifications / reviews / reports BİLİNÇLİ olarak dışarıda — snapshot temiz
bir kurulumun başlangıç verisi, kullanıcı verisinin yedeği değil. Admin `scripts/make_admin.py`
ile açılır.

Yalnızca `deleted_at IS NULL` satırlar dökülür ve filtre ÜST kayıtlara da uygulanır: aktif
görünen ama üstü silinmiş satır snapshot'a girmez (girerse yükleme sırasında FK'sı boşa düşer).
Böyle satırlar sessizce atılmaz, sayısı raporlanır.

ID'ler korunur — `--department-id 5136` gibi dışarıda tutulan referanslar sıfırlamadan sonra
da geçerli kalsın diye. Yükleyici sequence'leri max(id)'ye çeker.

⚠️ Dosyaya `_meta` tablosu yazılır (alembic head + export tarihi). Yükleyici head'i hedef DB
ile karşılaştırır; uymuyorsa yüklemeyi reddeder. Şema değiştiğinde (§9.3) snapshot yeniden
dökülmek zorundadır.
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from sqlalchemy import Boolean, DateTime, Integer, text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
import app.db.base  # noqa: E402, F401

from snapshot_schema import ACTIVE_PARENTS, TABLES, DEFAULT_SNAPSHOT  # noqa: E402


def sqlite_type(column) -> str:
    if isinstance(column.type, Boolean):
        return "INTEGER"
    if isinstance(column.type, Integer):
        return "INTEGER"
    return "TEXT"


def to_sqlite(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def active_query(db, model):
    query = db.query(model)
    for parent, onclause in ACTIVE_PARENTS[model]:
        query = query.join(parent, onclause)
    for owner in [model] + [parent for parent, _ in ACTIVE_PARENTS[model]]:
        if hasattr(owner, "deleted_at"):
            query = query.filter(owner.deleted_at.is_(None))
    return query


def own_filter_count(db, model) -> int:
    query = db.query(model)
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    return query.count()


def read_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    connection = sqlite3.connect(path)
    try:
        names = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        return {
            model.__tablename__: connection.execute(
                f"SELECT COUNT(*) FROM {model.__tablename__}"
            ).fetchone()[0]
            for model in TABLES
            if model.__tablename__ in names
        }
    finally:
        connection.close()


def write_snapshot(path: Path, data: dict[str, list], alembic_head: str) -> None:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO _meta (key, value) VALUES (?, ?)",
            [
                ("alembic_head", alembic_head),
                ("exported_at", datetime.now(timezone.utc).isoformat()),
            ],
        )
        for model in TABLES:
            table = model.__tablename__
            columns = list(model.__table__.columns)
            column_sql = ", ".join(f'"{c.name}" {sqlite_type(c)}' for c in columns)
            connection.execute(f'CREATE TABLE "{table}" ({column_sql})')
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                [
                    tuple(to_sqlite(getattr(row, c.name)) for c in columns)
                    for row in data[table]
                ],
            )
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_SNAPSHOT, help="Hedef .sqlite dosyası")
    parser.add_argument("--dry-run", action="store_true", help="Dosyaya yazmadan raporla")
    parser.add_argument("--force", action="store_true", help="Mevcut dosyayı sormadan ez")
    args = parser.parse_args()

    onceki = read_counts(args.out)

    db = SessionLocal()
    try:
        head = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        data = {}
        print(f"Alembic head: {head}\n")
        print(f"{'tablo':<20} {'satır':>8} {'fark':>8}   üstü silinmiş")
        for model in TABLES:
            table = model.__tablename__
            rows = active_query(db, model).all()
            data[table] = rows
            dusen = own_filter_count(db, model) - len(rows)
            fark = f"{len(rows) - onceki[table]:+d}" if table in onceki else "-"
            print(f"{table:<20} {len(rows):>8} {fark:>8}   {dusen or ''}")
    finally:
        db.close()

    if args.dry_run:
        print("\n--dry-run: dosya yazılmadı.")
        return

    if args.out.exists() and not args.force:
        cevap = input(f"\n{args.out} üzerine yazılsın mı? [e/H] ").strip().lower()
        if cevap != "e":
            print("İptal edildi.")
            return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_snapshot(args.out, data, head)
    print(f"\n✓ {args.out} ({args.out.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
