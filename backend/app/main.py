from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="Project Management MVP")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/example")
def example() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get("/", response_class=FileResponse)
def index() -> Path:
    return STATIC_DIR / "index.html"

