from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.db import base  # noqa: F401
from app.core.limiter import limiter
from app.api import auth, reviews, reports, course_professors, professors, universities, departments, courses, users

app = FastAPI(title="Kürsü API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(departments.router)
app.include_router(courses.router)
app.include_router(users.router)

@app.get("/health")
@limiter.exempt
def health_check():
    return {"status": "ok"}