from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.db import base  # noqa: F401
from app.core.limiter import limiter
from app.api import auth, reviews, reports

app = FastAPI(title="Kürsü API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(reports.router)

@app.get("/health")
@limiter.exempt
def health_check():
    return {"status": "ok"}