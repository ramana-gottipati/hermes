from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.assistant import chat, conversations
from src.core.settings import settings

app = FastAPI(title="Hermes", version="0.1.0")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User message")
    conversation_id: int | None = Field(
        None, description="Continue an existing conversation; omit to start a new one"
    )
    fast: bool = Field(False, description="Use HERMES_FAST_MODEL instead of default")


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
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
    return chat.handle(req.message, conversation_id=req.conversation_id, fast=req.fast)


@app.get("/conversations")
def list_conversations_endpoint(limit: int = 20) -> list[dict]:
    return conversations.list_conversations(limit=limit)


@app.get("/conversations/{conversation_id}")
def get_conversation_endpoint(conversation_id: int) -> dict:
    if not conversations.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return {
        "conversation_id": conversation_id,
        "messages": conversations.list_messages(conversation_id),
    }


@app.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(conversation_id: int) -> dict:
    if not conversations.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return {"deleted": conversation_id}
