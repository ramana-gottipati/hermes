"""wolfe_learnings_store.py — isolated, persistent CAPTURE of Ramana's hand-drawn Wolfe
waves as LEARNING examples.

Capture-and-preserve ONLY (Ramana 2026-07-22): these curated expert examples are stored
faithfully; the live rule-based detector / §A / §B / winner_scan are NOT altered by them.
The dataset simply exists on the VPS SQLite so the captured expertise survives independently
of any cloud/agent session.

Fully additive + isolated, exactly like ``drawings_store.py``: its OWN module, its OWN table
(``CREATE TABLE IF NOT EXISTS`` here — ``db.py`` untouched), mounted by being included INTO the
already-mounted ``wolfe_view`` router (no ``main.py`` edit, redeploy-durable).

Routes:
  GET  /dash/wolfe/learnings?sym=X       -> {"sym","items":[{id,symbol,direction,points,zones,note,created_at}]}
  POST /dash/wolfe/learnings?sym=X       body={direction,points,zones,note} -> {"ok":true,"id":N}
  POST /dash/wolfe/learnings/note?id=N   body={note}                        -> {"ok":true}
  POST /dash/wolfe/learnings/delete?id=N                                    -> {"ok":true}

Single-operator store (Ramana), keyed by symbol — same auth note as drawings_store: if this
ever serves multiple users, add an owner key to the table + WHERE clauses and require auth.
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

# Guard rails so a misbehaving client can't grow the DB without bound.
_MAX_PER_SYM = 200          # generous — you won't hand-curate 200 waves on one symbol
_MAX_BYTES = 64 * 1024      # per-learning points+zones payload
_MAX_NOTE = 4000            # per-learning note


def _ensure(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wolfe_learnings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            direction   TEXT,
            points_json TEXT NOT NULL,
            zones_json  TEXT,
            note        TEXT,
            created_at  REAL NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_wolfe_learnings_sym ON wolfe_learnings(symbol)")


def _norm_sym(sym: str) -> str:
    return (sym or "").strip().upper()[:24]


@router.get("/dash/wolfe/learnings")
def list_learnings(sym: str = Query("", max_length=24)):
    """All saved learnings for a symbol, newest first."""
    s = _norm_sym(sym)
    if not s:
        return JSONResponse({"sym": "", "items": []})
    try:
        with get_conn() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT id, symbol, direction, points_json, zones_json, note, created_at "
                "FROM wolfe_learnings WHERE symbol=? ORDER BY id DESC",
                (s,),
            ).fetchall()
        items = []
        for r in rows:
            try:
                pts = json.loads(r["points_json"])
            except (ValueError, TypeError):
                pts = []
            try:
                zs = json.loads(r["zones_json"]) if r["zones_json"] else []
            except (ValueError, TypeError):
                zs = []
            items.append({
                "id": r["id"], "symbol": r["symbol"], "direction": r["direction"],
                "points": pts, "zones": zs, "note": r["note"] or "", "created_at": r["created_at"],
            })
        return JSONResponse({"sym": s, "items": items})
    except Exception:  # pragma: no cover - never 500 the chart over a read miss
        return JSONResponse({"sym": s, "items": []})


@router.post("/dash/wolfe/learnings")
def save_learning(sym: str = Query("", max_length=24), body=Body(default=None)):
    """Append one learning example. Body = {direction, points, zones, note}."""
    s = _norm_sym(sym)
    if not s:
        return JSONResponse({"ok": False, "error": "missing sym"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "body must be an object"}, status_code=400)
    pts = body.get("points")
    if not isinstance(pts, list) or not pts:
        return JSONResponse({"ok": False, "error": "points required"}, status_code=400)
    direction = str(body.get("direction") or "")[:8]
    note = str(body.get("note") or "")[:_MAX_NOTE]
    zones = body.get("zones") if isinstance(body.get("zones"), list) else []
    pj = json.dumps(pts, separators=(",", ":"), default=str)
    zj = json.dumps(zones, separators=(",", ":"), default=str)
    if len(pj.encode("utf-8")) + len(zj.encode("utf-8")) > _MAX_BYTES:
        return JSONResponse({"ok": False, "error": "payload too large"}, status_code=413)
    try:
        with get_conn() as conn:
            _ensure(conn)
            n = conn.execute("SELECT COUNT(*) c FROM wolfe_learnings WHERE symbol=?", (s,)).fetchone()["c"]
            if n >= _MAX_PER_SYM:
                return JSONResponse({"ok": False, "error": "too many learnings for this symbol"}, status_code=429)
            cur = conn.execute(
                "INSERT INTO wolfe_learnings (symbol, direction, points_json, zones_json, note, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (s, direction, pj, zj, note, time.time()),
            )
            conn.commit()
        return JSONResponse({"ok": True, "id": cur.lastrowid})
    except Exception as e:  # pragma: no cover
        return JSONResponse({"ok": False, "error": str(e)[:120]}, status_code=500)


@router.post("/dash/wolfe/learnings/note")
def update_note(id: int = Query(...), body=Body(default=None)):
    """Refine a learning's note incrementally (typed or dictated on the client)."""
    note = ""
    if isinstance(body, dict):
        note = str(body.get("note") or "")[:_MAX_NOTE]
    elif isinstance(body, str):
        note = body[:_MAX_NOTE]
    try:
        with get_conn() as conn:
            _ensure(conn)
            conn.execute("UPDATE wolfe_learnings SET note=? WHERE id=?", (note, id))
            conn.commit()
        return JSONResponse({"ok": True})
    except Exception as e:  # pragma: no cover
        return JSONResponse({"ok": False, "error": str(e)[:120]}, status_code=500)


@router.post("/dash/wolfe/learnings/delete")
def delete_learning(id: int = Query(...)):
    """Remove one learning."""
    try:
        with get_conn() as conn:
            _ensure(conn)
            conn.execute("DELETE FROM wolfe_learnings WHERE id=?", (id,))
            conn.commit()
        return JSONResponse({"ok": True})
    except Exception as e:  # pragma: no cover
        return JSONResponse({"ok": False, "error": str(e)[:120]}, status_code=500)
