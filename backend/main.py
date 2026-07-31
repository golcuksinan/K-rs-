from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.db import base  # noqa: F401
from app.core.limiter import limiter, NestedRouteSlowAPIMiddleware
from app.api import auth, reviews, reports, course_professors, professors, universities, departments, courses, users, faculties, admin_stats

app = FastAPI(
    title="Kürsü API",
    version="0.1.0",
    description=(
        "Anonim ders ve akademisyen değerlendirme platformunun API'si. "
        "Zarflar, akışlar, maskeleme ve hata gövdeleri gibi bu şemadan okunamayan "
        "kurallar için `docs/api-contract.md`."
    ),
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