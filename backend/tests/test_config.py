"""Ayarların okunması ve uygulamaya gerçekten uygulanması."""
import anyio
import anyio.to_thread

from app.core.config import Settings, settings
from main import app, lifespan


def test_heroku_postgres_semasi_normalize_edilir():
    s = Settings(DATABASE_URL="postgres://u:p@h:5432/db")
    assert s.DATABASE_URL == "postgresql://u:p@h:5432/db"


def test_normal_sema_degistirilmez():
    url = "postgresql://u:p@h:5432/db"
    assert Settings(DATABASE_URL=url).DATABASE_URL == url


def test_yalnizca_bastaki_sema_degistirilir():
    s = Settings(DATABASE_URL="postgres://u:p@h:5432/postgres://x")
    assert s.DATABASE_URL == "postgresql://u:p@h:5432/postgres://x"


def test_lifespan_threadpool_token_sayisini_uygular(monkeypatch):
    monkeypatch.setattr(settings, "THREADPOOL_TOKENS", 6)

    async def run():
        async with lifespan(app):
            return anyio.to_thread.current_default_thread_limiter().total_tokens

    assert anyio.run(run) == 6
