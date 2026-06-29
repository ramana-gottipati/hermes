import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.assistant import chat, conversations
from src.core.db import get_conn
from src.core.settings import settings
from src.pat.routes import router as pat_router
from src.web.dashboard import router as dashboard_router
from src.web.rrg_view import router as rrg_router
from src.web.rotation_view import router as rotation_router
from src.web.rsband_view import router as rsband_router
from src.web.participants_view import router as participants_router
from src.web.wolfe_view import router as wolfe_router
from src.web.cpr_overlay import router as cpr_router
from src.web.mep_overlay import router as mep_router
from src.web.rs_overlay import router as rs_router

app = FastAPI(title="Hermes", version="0.1.0")

# Gzip every response above 500 B. The dashboard ships large server-rendered HTML
# plus inline chart JSON; compressing at the app layer cuts bytes-on-wire on every
# navigation regardless of whether the (currently unversioned) edge proxy gzips.
# Isolated + additive + zero behaviour change. Part of the perf work-stream —
# see docs/perf-architecture.md. The render-layer caching/thinning items belong to
# the UI session — see docs/ui-perf-handoff.md.
app.add_middleware(GZipMiddleware, minimum_size=500)

# Web dashboard + installable PWA (served at /dash, manifest/sw/icon at root).
app.include_router(dashboard_router)
# Pat's JSON side-channels (feedback/learning) — mounted here so the contended
# dashboard.py page route never has to change to add a Pat backend endpoint.
app.include_router(pat_router)
# RS-deepening (session 20): multi-sector Relative Rotation Graph + RS-depth table
# at /dash/rrg. Isolated module so the parallel-session-held dashboard.py is untouched.
app.include_router(rrg_router)
# RS rotation (session 25): the four-phase weather rotation (Recovery/Tailwind/
# Rolling-over/Headwind) for stocks at /dash/rotation. Isolated module (same reason).
app.include_router(rotation_router)
# RS support/resistance band (2026-06-23): the mean-reversion / LEVEL lens — per-sector
# band position vs Nifty 500 at /dash/rsband. Isolated module (same reason).
app.include_router(rsband_router)
# Participant-wise OI (2026-06-23): market-level FII/DII/Pro/Client positioning at
# /dash/participants. Isolated module (same reason).
app.include_router(participants_router)
# Wolfe Wave (2026-06-23): geometry/reversal lens — 1·3·5 structure + point-5 zone +
# 1-4 EPA target + WolfeRank, at /dash/wolfe. Isolated module (same reason).
app.include_router(wolfe_router)
# CPR Spine overlay (2026-06-24): the stock-page price chart's signature ribbon —
# /dash/cpr/overlay serves cpr_signals→segments; the SNIPPET draws it on the existing
# chart (window.__wfpc). Isolated module (same reason — dashboard.py untouched core).
app.include_router(cpr_router)
# MEP accumulation/distribution phase tint (2026-06-24): /dash/mep/overlay serves smoothed-phase
# bands; the SNIPPET tints the price-chart background (green=accum / red=distrib) on the existing
# chart. Isolated module (dashboard.py core untouched).
app.include_router(mep_router)
# RS-vs-benchmark ratio line (2026-06-24): /dash/rs/overlay feeds the stock chart's
# docked RS lane (the one-chart engine, stock_chart.py). Isolated module.
app.include_router(rs_router)


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


# === v2 surfaces hook (durable) ===
# Mount the v2 website surfaces (Coverage ledger, RS hub, News/Wire, /v1) and
# integrate them into the live nav. Single source of truth = src/web/v2_surfaces.py.
# Re-applied idempotently by scripts/wire_v2_surfaces.py after any redeploy/clobber.
# Defensive: a failure inside wire() is logged, never fatal. Reversible: delete this block.
try:
    from src.web import v2_surfaces as _v2_surfaces
    _v2_surfaces.wire(app)
except Exception as _v2_hook_err:  # noqa: BLE001
    import logging as _v2_logging
    _v2_logging.getLogger("hermes.v2").warning("v2 surfaces hook skipped: %s", _v2_hook_err)
# === end v2 surfaces hook ===


# === nav glue hook (durable, Lane N3) ===
# Cross-page navigation glue: breadcrumbs (Markets → Sector → Stock) + lateral
# "see this lens elsewhere" rails, generated from src/web/lens_registry. Installs by
# monkeypatching dashboard._shell (the shell_skin/v2_surfaces runtime-injection pattern)
# so NO contended page body is edited and a dashboard.py redeploy cannot wipe it.
# Idempotent (sentinel) + defensive (a failure is logged, never fatal). Reversible:
# delete this block. Single source of truth = src/web/nav_links.py.
try:
    from src.web import nav_links as _nav_links
    _nav_links.install()
except Exception as _nav_glue_err:  # noqa: BLE001
    import logging as _nav_glue_logging
    _nav_glue_logging.getLogger("hermes.v2").warning("nav glue hook skipped: %s", _nav_glue_err)
# === end nav glue hook ===
