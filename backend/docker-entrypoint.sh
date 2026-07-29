#!/bin/sh
set -e

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  python - <<'PY'
import os, sys, time
import psycopg2

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        psycopg2.connect(url).close()
        sys.exit(0)
    except psycopg2.OperationalError as exc:
        print(f"[entrypoint] veritabani hazir degil ({attempt + 1}/30): {exc.args[0].strip()}")
        time.sleep(2)
print("[entrypoint] veritabanina baglanilamadi")
sys.exit(1)
PY
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
