import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.assistant import chat, conversations
from src.core.db import get_conn
from src.core.settings import settings
from src.web.dashboard import router as dashboard_router

app = FastAPI(title="Hermes", version="0.1.0")

# Web dashboard + installable PWA (served at /dash, manifest/sw/icon at root).
app.include_router(dashboard_router)


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


# --- patearn screen candidates view ----------------------------------------

CANDIDATES_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hermes — patearn Candidates</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif;
           background:#0e1116; color:#e6edf3; margin:0; padding:16px; }
    h1 { font-size:20px; margin:0 0 8px; }
    .meta { color:#8b949e; font-size:13px; margin-bottom:16px; }
    .filters { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
    .filters a { background:#21262d; color:#e6edf3; text-decoration:none;
                 padding:6px 12px; border-radius:6px; font-size:13px;
                 border:1px solid #30363d; }
    .filters a.active { background:#1f6feb; border-color:#1f6feb; }
    .card { background:#161b22; border:1px solid #30363d; border-radius:8px;
            padding:14px; margin-bottom:10px; }
    .row1 { display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap; }
    .sym { font-weight:700; font-size:16px; }
    .verdict { font-size:11px; padding:2px 8px; border-radius:10px; font-weight:600; letter-spacing:.5px; }
    .v-PASS { background:#1f6f3a; color:#9aff9a; }
    .v-WATCH { background:#6f5a1f; color:#ffd99a; }
    .src { color:#58a6ff; font-size:12px; text-decoration:none; }
    .src:hover { text-decoration:underline; }
    .rationale { color:#c9d1d9; font-size:14px; line-height:1.4; margin:6px 0; }
    .signals { font-size:11px; color:#8b949e; }
    .ts { color:#6e7681; font-size:11px; margin-left:auto; }
    .empty { color:#8b949e; text-align:center; padding:40px 16px; }
    .copy-hint { background:#0d2535; border:1px solid #1f4068; padding:10px;
                 border-radius:6px; font-size:13px; color:#9ad1ff; margin-bottom:16px; }
    code { background:#21262d; padding:1px 5px; border-radius:3px; font-size:13px; }
    .news { color:#8b949e; font-size:13px; margin-top:2px; }
  </style>
</head>
<body>
  <h1>📊 patearn Candidates</h1>
  <div class="meta">{n_total} total · {n_pass} PASS · {n_watch} WATCH · updated {now}</div>

  <div class="copy-hint">
    💡 To deep-dive: tap a row → copy → paste into <b>claude.ai</b> →
    ask <i>"Run full patearn Mode 1 analysis on this candidate."</i>
  </div>

  <div class="filters">
    <a href="?verdict=all" class="{cls_all}">All</a>
    <a href="?verdict=PASS" class="{cls_pass}">PASS only</a>
    <a href="?verdict=WATCH" class="{cls_watch}">WATCH only</a>
    <a href="?days=1" class="{cls_d1}">Today</a>
    <a href="?days=7" class="{cls_d7}">7 days</a>
    <a href="?days=30" class="{cls_d30}">30 days</a>
  </div>

  {rows_html}
</body>
</html>"""


def _esc_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@app.get("/candidates", response_class=HTMLResponse)
def candidates_page(
    verdict: str = Query("all"),
    days: int = Query(30, ge=1, le=365),
) -> HTMLResponse:
    """Mobile-friendly HTML table of Stage 1 patearn screen candidates."""
    where = ["screened_at >= datetime('now', ?)"]
    params: list = [f"-{days} days"]
    if verdict.upper() in ("PASS", "WATCH"):
        where.append("verdict = ?")
        params.append(verdict.upper())

    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT symbol, verdict, rationale, signals_json,
                       news_url, news_title, news_source, screened_at
                FROM screen_candidates
                WHERE {' AND '.join(where)}
                ORDER BY (verdict='PASS') DESC, screened_at DESC""",
            params,
        ).fetchall()

    items = [dict(r) for r in rows]
    n_pass = sum(1 for r in items if r["verdict"] == "PASS")
    n_watch = sum(1 for r in items if r["verdict"] == "WATCH")

    if not items:
        rows_html = '<div class="empty">No candidates in this window. Try widening the date filter.</div>'
    else:
        cards = []
        for r in items:
            try:
                signals = json.loads(r["signals_json"] or "[]")
            except json.JSONDecodeError:
                signals = []
            cards.append(
                f"""<div class="card">
  <div class="row1">
    <span class="sym">{_esc_html(r['symbol'])}</span>
    <span class="verdict v-{r['verdict']}">{r['verdict']}</span>
    <span class="ts">{r['screened_at']}</span>
  </div>
  <div class="rationale">{_esc_html(r['rationale'])}</div>
  <div class="signals">{', '.join(_esc_html(s) for s in signals) if signals else '—'}</div>
  <div class="news">📰 <a class="src" href="{r['news_url']}" target="_blank">{_esc_html(r['news_source'])}</a>: {_esc_html(r['news_title'])}</div>
</div>"""
            )
        rows_html = "\n".join(cards)

    def cls(active: str) -> str:
        return "active" if active else ""

    html = CANDIDATES_HTML.format(
        n_total=len(items),
        n_pass=n_pass,
        n_watch=n_watch,
        now=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        rows_html=rows_html,
        cls_all=cls(verdict == "all"),
        cls_pass=cls(verdict.upper() == "PASS"),
        cls_watch=cls(verdict.upper() == "WATCH"),
        cls_d1=cls(days == 1),
        cls_d7=cls(days == 7),
        cls_d30=cls(days == 30),
    )
    return HTMLResponse(content=html)
