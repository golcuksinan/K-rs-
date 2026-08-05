from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.sentry import init_sentry
from app.db import base  # noqa: F401
from app.core.limiter import limiter, from_cloudflare, NestedRouteSlowAPIMiddleware
from app.api import auth, reviews, reports, course_professors, professors, universities, departments, courses, users, faculties, admin_stats


# app kurulmadan önce: entegrasyonlar ASGI uygulamasını sarmalıyor.
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    anyio.to_thread.current_default_thread_limiter().total_tokens = settings.THREADPOOL_TOKENS
    yield


app = FastAPI(
    title="Kürsü API",
    version="0.1.0",
    description=(
        "Anonim ders ve akademisyen değerlendirme platformunun API'si. "
        "Zarflar, akışlar, maskeleme ve hata gövdeleri gibi bu şemadan okunamayan "
        "kurallar için `docs/api-contract.md`."
    ),
    lifespan=lifespan,
    # Prod'da kapalı: uçların, admin imzalarının ve gövde şekillerinin kimliksiz listelenmesi
    # saldırı yüzeyini bedavaya verir. Ekip şemayı docs/openapi.json'dan okur.
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(NestedRouteSlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS'tan sonra eklendi: Starlette'te en son eklenen middleware en dışta koşar, kilide
# takılan istek limiter'ı da uçları da hiç görmesin.
@app.middleware("http")
async def origin_lock(request: Request, call_next):
    # *.herokuapp.com kapatılamıyor; Cloudflare'i atlayan doğrudan istek reddedilmezse kenar
    # önbelleği ve managed challenge katmanları devreye bile girmez.
    if settings.CF_ORIGIN_SECRET and request.url.path != "/health":
        if not from_cloudflare(request):
            return JSONResponse({"detail": "Erişim reddedildi"}, status_code=403)
    return await call_next(request)


app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(reports.router)
app.include_router(course_professors.router)
app.include_router(professors.router)
app.include_router(universities.router)
app.include_router(faculties.router)
app.include_router(departments.router)
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(admin_stats.router)

@app.get("/health")
@limiter.exempt
def health_check():
    return {"status": "ok"}