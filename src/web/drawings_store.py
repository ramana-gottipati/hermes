"""drawings_store.py — server-side persistence for the on-chart drawing engine.

Promotes the /dash/stock drawing store (trendlines / zones / Fib / measure / text)
from browser ``localStorage`` to a real **per-symbol SQLite store**, so a user's
drawings survive a different device or browser — not just a reload in the same one.
``localStorage`` stays as the instant/offline fallback in ``stock_chart.py``; the
server copy is the source of truth when reachable.

Two tiny routes on this module's own APIRouter (mounted by being included INTO the
already-mounted ``wolfe_view`` router — the same no-main.py-edit, redeploy-durable
pattern ``harmonic_view`` uses):

  • GET  /dash/drawings?sym=X   → {"sym","items":[...]}   (the stored drawing list)
  • POST /dash/drawings?sym=X   → body = the drawing list  → {"ok":true,"n":N}

The table is **module-owned** (``CREATE TABLE IF NOT EXISTS`` here; ``db.py`` is left
untouched), matching ``harmonic_signals``. One row per symbol — the whole drawing
list is stored as a JSON blob (drawings are small, per-user, and always read/written
as a set; no need to normalise into rows).

Storage budget: each item is capped server-side (count + payload size) so a runaway
client can't bloat the DB. No look-ahead, no market data — this is pure user state.
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - dual import path (VPS runs from src/)
    from core.db import get_conn  # type: ignore

router = APIRouter()

# Guard rails: a single symbol's drawing set is bounded so a misbehaving client
# can't grow the DB without limit. Generous for real use (you won't hand-draw 500
# trendlines on one chart), tight enough to cap abuse.
_MAX_ITEMS = 500
_MAX_BYTES = 256 * 1024  # 256 KB of JSON per symbol — plenty for hundreds of shapes


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chart_drawings (
            symbol     TEXT PRIMARY KEY,
            items_json TEXT NOT NULL,
            n_items    INTEGER NOT NULL DEFAULT 0,
            updated_at REAL    NOT NULL
        )
        """
    )


def _norm_sym(sym: str) -> str:
    return (sym or "").strip().upper()[:24]


@router.get("/dash/drawings")
def get_drawings(sym: str = Query("", max_length=24)):
    """Return the stored drawing list for a symbol (empty list if none/blank)."""
    s = _norm_sym(sym)
    if not s:
        return JSONResponse({"sym": "", "items": []})
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            row = conn.execute(
                "SELECT items_json FROM chart_drawings WHERE symbol=?", (s,)
            ).fetchone()
        items = []
        if row and row["items_json"]:
            try:
                items = json.loads(row["items_json"])
                if not isinstance(items, list):
                    items = []
            except (ValueError, TypeError):
                items = []
        return JSONResponse({"sym": s, "items": items})
    except Exception:  # pragma: no cover - never 500 the chart over a read miss
        return JSONResponse({"sym": s, "items": []})


@router.post("/dash/drawings")
def put_drawings(sym: str = Query("", max_length=24),
                 items=Body(default=None)):
    """Replace the stored drawing list for a symbol. Body = the JSON array of items.

    Whole-set replace (the client always owns the canonical list and posts it after
    every change) — simpler and race-free vs per-item upserts for a single-user store.
    Caps count + payload size; an empty list deletes the row.
    """
    s = _norm_sym(sym)
    if not s:
        return JSONResponse({"ok": False, "error": "missing sym"}, status_code=400)
    if not isinstance(items, list):
        return JSONResponse({"ok": False, "error": "body must be a JSON array"}, status_code=400)
    items = items[:_MAX_ITEMS]
    blob = json.dumps(items, separators=(",", ":"), default=str)
    if len(blob.encode("utf-8")) > _MAX_BYTES:
        return JSONResponse({"ok": False, "error": "payload too large"}, status_code=413)
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            if items:
                conn.execute(
                    """
                    INSERT INTO chart_drawings (symbol, items_json, n_items, updated_at)
                    VALUES (?,?,?,?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        items_json=excluded.items_json,
                        n_items=excluded.n_items,
                        updated_at=excluded.updated_at
                    """,
                    (s, blob, len(items), time.time()),
                )
            else:
                conn.execute("DELETE FROM chart_drawings WHERE symbol=?", (s,))
            conn.commit()
        return JSONResponse({"ok": True, "n": len(items)})
    except Exception as e:  # pragma: no cover
        return JSONResponse({"ok": False, "error": str(e)[:120]}, status_code=500)
