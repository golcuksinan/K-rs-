"""Snapshot .sqlite dosyasını boş bir DB'ye yükler.

Kullanım (çalışma dizini backend/ olmalı):
    python seeds/load_snapshot.py --dry-run
    python seeds/load_snapshot.py
    python seeds/load_snapshot.py --file /yol/kursu-seed.sqlite --database-url postgresql://...

Önkoşul: `alembic upgrade head` çalıştırılmış, hedef tablolar BOŞ olmalı. Prod'un ilk
kurulumunda ve dev DB sıfırlandıktan sonra çalıştırılır; `seed_from_sqlite.py` /
`seed_pau_all.py` yerine geçer (onlar artık yalnızca YENİ veri toplamak için).

İki güvenlik kontrolü, ikisi de sessiz veri bozulmasına karşı:
- Snapshot'ın `_meta.alembic_head`'i hedef DB'nin head'iyle aynı olmalı. Farklıysa şema
  kaymış demektir; yükleme reddedilir (`--skip-head-check` bilerek geçmek için).
- Kolonlar ADA göre eşleşir. Snapshot'ta olmayan bir NOT NULL kolon veya modelde olmayan
  bir kolon varsa hata verilir — pozisyona göre kayıp eşleşme olmaz.

ID'ler snapshot'taki değerleriyle yazılır, sonda sequence'ler max(id)+1'e çekilir. Tek
transaction: herhangi bir tablo patlarsa hiçbiri yazılmaz.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from sqlalchemy import ARRAY, Boolean, DateTime, create_engine, insert, text  # noqa: E402

import app.db.base  # noqa: E402, F401

from snapshot_schema import TABLES, DEFAULT_SNAPSHOT  # noqa: E402

BATCH = 5000


def from_sqlite(column, value):
    if value is None:
        return None
    if isinstance(column.type, ARRAY):
        return json.loads(value)
    if isinstance(column.type, Boolean):
        return bool(value)
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    return value


def check_columns(snapshot: sqlite3.Connection, model) -> list[str]:
    table = model.__tablename__
    dosyadaki = {row[1] for row in snapshot.execute(f'PRAGMA table_info("{table}")')}
    if not dosyadaki:
        raise SystemExit(f"HATA: snapshot'ta '{table}' tablosu yok.")

    modeldeki = {c.name for c in model.__table__.columns}
    fazla = dosyadaki - modeldeki
    if fazla:
        raise SystemExit(
            f"HATA: '{table}' snapshot'ında modelde olmayan kolon(lar): {sorted(fazla)}"
        )

    eksik_zorunlu = [
        c.name
        for c in model.__table__.columns
        if c.name not in dosyadaki and not c.nullable and c.default is None and not c.primary_key
    ]
    if eksik_zorunlu:
        raise SystemExit(
            f"HATA: '{table}' snapshot'ında zorunlu kolon(lar) eksik: {eksik_zorunlu}"
        )

    for name in modeldeki - dosyadaki:
        print(f"  ⚠️ {table}.{name} snapshot'ta yok, NULL yazılacak")

    return [c.name for c in model.__table__.columns if c.name in dosyadaki]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_SNAPSHOT, help="Snapshot dosyası")
    parser.add_argument("--database-url", default=None, help="Hedef DB (yoksa .env'den)")
    parser.add_argument("--dry-run", action="store_true", help="Sonunda rollback")
    parser.add_argument(
        "--skip-head-check", action="store_true", help="Alembic head uyuşmazlığını yok say"
    )
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"HATA: {args.file} yok.")

    if args.database_url:
        url = args.database_url
    else:
        from app.core.config import settings

        url = settings.DATABASE_URL

    snapshot = sqlite3.connect(args.file)
    engine = create_engine(url)
    try:
        meta = dict(snapshot.execute("SELECT key, value FROM _meta"))
        print(f"Snapshot: {args.file}")
        print(f"  alembic head : {meta.get('alembic_head')}")
        print(f"  export tarihi: {meta.get('exported_at')}\n")

        with engine.begin() as connection:
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if head != meta.get("alembic_head"):
                mesaj = (
                    f"Alembic head uyuşmuyor: hedef DB {head!r}, snapshot "
                    f"{meta.get('alembic_head')!r}."
                )
                if not args.skip_head_check:
                    raise SystemExit(
                        f"HATA: {mesaj}\nSnapshot yeniden dökülmeli "
                        f"(veya --skip-head-check ile bilerek geçilmeli)."
                    )
                print(f"⚠️ {mesaj} --skip-head-check ile devam ediliyor.\n")

            dolu = [
                model.__tablename__
                for model in TABLES
                if connection.execute(
                    text(f"SELECT 1 FROM {model.__tablename__} LIMIT 1")
                ).scalar()
            ]
            if dolu:
                raise SystemExit(
                    f"HATA: hedef tablolar boş değil: {dolu}. Snapshot yalnızca temiz bir "
                    f"kuruluma yüklenir."
                )

            for model in TABLES:
                table = model.__tablename__
                names = check_columns(snapshot, model)
                columns = [model.__table__.columns[n] for n in names]
                cursor = snapshot.execute(
                    f'SELECT {", ".join(chr(34) + n + chr(34) for n in names)} FROM "{table}"'
                )
                toplam = 0
                while rows := cursor.fetchmany(BATCH):
                    connection.execute(
                        insert(model.__table__),
                        [
                            {c.name: from_sqlite(c, v) for c, v in zip(columns, row)}
                            for row in rows
                        ],
                    )
                    toplam += len(rows)
                print(f"{table:<20} {toplam:>8} satır")

            for model in TABLES:
                table = model.__tablename__
                if "id" not in model.__table__.columns:
                    continue  # composite PK'lı join tablosunda sequence yok
                connection.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                    )
                )

            if args.dry_run:
                connection.rollback()
                print("\n--dry-run: hiçbir değişiklik commit edilmedi.")
                return

        print("\n✓ Yükleme tamamlandı.")
    finally:
        snapshot.close()
        engine.dispose()


if __name__ == "__main__":
    main()
