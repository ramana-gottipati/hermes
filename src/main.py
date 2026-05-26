from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.assistant import chat
from src.core.settings import settings

app = FastAPI(title="Hermes", version="0.0.1")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User message")
    fast: bool = Field(False, description="Use HERMES_FAST_MODEL instead of default")


class ChatResponse(BaseModel):
    reply: str
    model: str
    stop_reason: str
    usage: dict


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


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> dict:
    return chat.handle(req.message, fast=req.fast)
