import anyio
import anyio.to_thread

from app.core.config import settings
from main import app, lifespan


def test_lifespan_threadpool_token_sayisini_uygular(monkeypatch):
    monkeypatch.setattr(settings, "THREADPOOL_TOKENS", 6)

    async def run():
        async with lifespan(app):
            return anyio.to_thread.current_default_thread_limiter().total_tokens

    assert anyio.run(run) == 6
