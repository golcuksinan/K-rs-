#!/bin/bash

set -e

echo "Alembic migration'ları uygulanıyor..."
alembic upgrade head

echo "Kürsü FastAPI sunucusu başlatılıyor..."
# exec komutu, uvicorn'un konteynerin ana process'i (PID 1) olmasını sağlar
exec uvicorn main:app --host 0.0.0.0 --port 8000