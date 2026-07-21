from fastapi import FastAPI
from app.db import base  # noqa: F401

app = FastAPI(title="Kürsü API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

from app.api import auth
app.include_router(auth.router)