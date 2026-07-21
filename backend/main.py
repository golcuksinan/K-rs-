from fastapi import FastAPI

app = FastAPI(title="Kürsü API")

@app.get("/health")
def health_check():
    return {"status": "ok"}