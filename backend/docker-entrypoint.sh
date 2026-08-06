#!/bin/bash

set -e

# ENTRYPOINT olduğumuz için release phase komutu ("alembic upgrade head") bize argüman olarak
# gelir; yutulursa release adımı sessizce sunucu başlatır.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Heroku'da migration release phase'de koşar; burada da koşarsa her dyno restart'ında
# tekrarlanır ve bir hata crash-loop'a döner. Compose bu değişkeni vermez, varsayılan 1 kalır.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Alembic migration'ları uygulanıyor..."
  alembic upgrade head
fi

echo "Kürsü FastAPI sunucusu başlatılıyor..."
# exec komutu, uvicorn'un konteynerin ana process'i (PID 1) olmasını sağlar
# limit-concurrency: uçuştaki istek sayısı tavanı. Bağlantı, isteğin thread slot'undan uzun
# süre elde kalıyor (get_db teardown'ı yanıt gönderildikten sonra koşar), bu yüzden havuzu
# tüketen şey eşzamanlı çalışan istek değil uçuştaki istek sayısı. Tavansız kalırsa aşırı
# yükte havuz tükeniyor ve istekler 503 yerine 500 alıyor.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --limit-concurrency "${UVICORN_LIMIT_CONCURRENCY:-32}"