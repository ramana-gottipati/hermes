from fastapi import FastAPI

from src.core.settings import settings

app = FastAPI(title="Hermes", version="0.0.1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.default_model}


@app.get("/")
def root() -> dict:
    return {
        "name": "Hermes",
        "workloads": ["assistant", "automation", "trading"],
        "trading_live": settings.trading_live,
    }
