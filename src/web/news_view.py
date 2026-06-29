"""News view — UI Architecture v2 §7 / P4 view layer (the consumer of news_tagging).

Renders the per-stock **News / Timeline** and the watchlist-scoped **Market Wire**
from the `news_symbol_tags` produced by `src/automation/news_tagging.py`. This is
the surface the friction log (§2b "News buried… the stock dossier has no News at
all") asks for.

Isolation (per §0.8): brand-new module; imports only the stable `_shell`/`_esc`/`_q`
from dashboard (import-safe — same as rs_section.py) plus the news_tagging read-APIs.
It exposes REUSABLE fragments — `render_stock_timeline(sym)` and
`render_market_wire()` — so the stock dossier can later grow a News tab and Markets
a Wire rail with a ONE-LINE embed call, AND standalone routes (`/dash/news?sym=`,
`/dash/wire`) wired by a single `include_router` in main.py (deferred until the web
layer frees). Additive only: it adds new routes, touches no existing route, deletes
nothing, changes no functionality. Defensive: a data error degrades to an empty
state, never a 500.

Wiring (deferred, when the tree frees):
    # src/main.py
    from src.web.news_view import router as news_router
    app.include_router(news_router)
    # dossier News tab body  ->  news_view.render_stock_timeline(sym, conn)
    # Markets Wire rail       ->  news_view.render_market_wire(conn)
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell, _esc, _q  # stable chrome + helpers (import-safe)
from src.core.db import get_conn

router = APIRouter()

_CSS = """<style>
.nv-wrap{max-width:1100px;}
.nv-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:2px 0 12px;}
.nv-head h2{margin:0;font-size:18px;}
.nv-count{color:#8b949e;font-size:12px;}
.nv-list{display:flex;flex-direction:column;border:1px solid #30363d;border-radius:10px;overflow:hidden;background:#161b22;}
.nv-row{display:flex;align-items:baseline;gap:10px;padding:9px 12px;text-decoration:none;color:inherit;border-top:1px solid #21262d;border-left:3px solid transparent;}
.nv-row:first-child{border-top:none;}
.nv-row:hover{background:#1c2230;border-left-color:#1f6feb;}
.nv-date{color:#6e7681;font-size:11px;font-variant-numeric:tabular-nums;white-space:nowrap;min-width:64px;}
.nv-src{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;min-width:84px;}
.nv-title{color:#c9d1d9;font-size:13px;flex:1;line-height:1.4;}
.nv-row:hover .nv-title{color:#e6edf3;}
.nv-syms{display:flex;gap:4px;flex-wrap:wrap;min-width:0;}
.nv-sym{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:1px 6px;font-size:10px;font-weight:600;color:#58a6ff;white-space:nowrap;}
.nv-prov{font-size:9px;color:#6e7681;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap;}
.nv-prov.ai{color:#8957e5;}
.nv-empty{color:#6e7681;font-size:12px;line-height:1.6;padding:14px;border:1px dashed #30363d;border-radius:10px;}
.nv-foot{color:#6e7681;font-size:11px;margin-top:10px;}
</style>"""


def _prov(method: str) -> str:
    """A tiny, honest provenance marker so the reader knows how a tag was derived
    (data-first: show the evidence). Rule-based = 'rule'; LLM-extracted = 'ai'."""
    if method == "classifier":
        return '<span class="nv-prov ai">ai</span>'
    return '<span class="nv-prov">rule</span>'


def _row(r: dict, *, syms_html: str = "") -> str:
    date = _esc((r.get("sent_at") or "")[:10])
    src = _esc((r.get("source") or "")[:14])
    title = _esc(r.get("title") or "")
    url = _esc(r.get("url") or "#")
    mid = syms_html or f'<span class="nv-src">{src}</span>'
    return (f'<a class="nv-row" href="{url}" target="_blank" rel="noopener">'
            f'<span class="nv-date">{date}</span>{mid}'
            f'<span class="nv-title">{title}</span>'
            f'{_prov(r.get("method") or "")}</a>')


def _read(fn, *args, conn=None, **kw):
    """Run a news_tagging read with an optional caller-supplied conn; defensive."""
    try:
        if conn is not None:
            return fn(conn, *args, **kw) or []
        with get_conn() as c:
            return fn(c, *args, **kw) or []
    except Exception:
        return []


def render_stock_timeline(sym: str, conn=None, *, limit: int = 40) -> str:
    """Per-stock News/Timeline fragment — newest-first headlines tagged to `sym`.
    Embeddable as a dossier News tab body (pass the dossier's conn)."""
    sym = (sym or "").strip().upper()
    if not sym:
        return _CSS + '<div class="nv-wrap"><div class="nv-empty">Pick a stock to see its news timeline.</div></div>'
    from src.automation.news_tagging import news_for_symbol
    rows = _read(news_for_symbol, sym, conn=conn, limit=limit)
    if not rows:
        return (_CSS + '<div class="nv-wrap">'
                f'<div class="nv-head"><h2>News · {_esc(sym)}</h2></div>'
                f'<div class="nv-empty">No tagged news yet for {_esc(sym)}. '
                'Headlines are tagged as they arrive (and a one-time backfill covers history); '
                'company news that uses a brand name differing from the legal name may not be linked.</div></div>')
    body = "".join(_row(r) for r in rows)
    return (_CSS + '<div class="nv-wrap">'
            f'<div class="nv-head"><h2>News · {_esc(sym)}</h2>'
            f'<span class="nv-count">{len(rows)} headline{"s" if len(rows) != 1 else ""}, newest first</span></div>'
            f'<div class="nv-list">{body}</div>'
            '<div class="nv-foot">Per-stock news from the market feed, linked by symbol. '
            '<span class="nv-prov">rule</span> = name/ticker match · <span class="nv-prov ai">ai</span> = classifier-extracted.</div>'
            '</div>')


def _watchlist_symbols(conn) -> list[str]:
    try:
        return [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]
    except Exception:
        return []


def render_market_wire(conn=None, symbols=None, *, limit: int = 40) -> str:
    """Watchlist-scoped Market Wire fragment — recent headlines across your names,
    each row showing the tagged symbol chips. Embeddable as a Markets rail (pass
    the page's conn); opens its own connection when called standalone."""
    if conn is not None:
        return _wire_html(conn, symbols, limit)
    with get_conn() as c:                 # get_conn is a @contextmanager — must use `with`
        return _wire_html(c, symbols, limit)


def _wire_html(c, symbols, limit: int) -> str:
    syms = symbols if symbols is not None else _watchlist_symbols(c)
    from src.automation.news_tagging import wire_for_symbols
    rows = _read(wire_for_symbols, list(syms), conn=c, limit=limit) if syms else []

    if not syms:
        return (_CSS + '<div class="nv-wrap"><div class="nv-head"><h2>Market wire</h2></div>'
                '<div class="nv-empty">Your watchlist is empty — add symbols to see their moving news here.</div></div>')
    if not rows:
        return (_CSS + '<div class="nv-wrap"><div class="nv-head"><h2>Market wire</h2>'
                f'<span class="nv-count">{len(syms)} watchlist names</span></div>'
                '<div class="nv-empty">No tagged news for your watchlist yet.</div></div>')
    out = []
    for r in rows:
        chips = "".join(f'<span class="nv-sym">{_esc(s)}</span>'
                        for s in (r.get("symbols") or "").split(",") if s)
        out.append(_row(r, syms_html=f'<span class="nv-syms">{chips}</span>'))
    return (_CSS + '<div class="nv-wrap">'
            f'<div class="nv-head"><h2>Market wire</h2>'
            f'<span class="nv-count">{len(rows)} headlines across {len(syms)} watchlist names</span></div>'
            f'<div class="nv-list">{"".join(out)}</div>'
            '<div class="nv-foot">Headlines from the market feed scoped to your watchlist, newest first.</div>'
            '</div>')


@router.get("/dash/news", response_class=HTMLResponse)
def news_page(sym: str = Query("")) -> HTMLResponse:
    title = f"News · {_esc(sym.strip().upper())}" if sym.strip() else "News · patearn"
    # News is Markets-altitude content (ui-architecture-v2 §0.1/§7) — highlight Markets,
    # consistent with /dash/wire (was "strategies", which mis-highlighted the tab).
    return HTMLResponse(_shell(title, render_stock_timeline(sym), active="markets", wide=True))


@router.get("/dash/wire", response_class=HTMLResponse)
def wire_page() -> HTMLResponse:
    # active="wire" (the Wire lens key) → the Markets-altitude tab AND the "News / Wire"
    # sub-nav item both highlight. "markets" lit the Overview sub-item instead (its key
    # collides with the altitude name); the registry resolves "wire" → the Markets altitude.
    return HTMLResponse(_shell("Market wire · patearn", render_market_wire(), active="wire", wide=True))
