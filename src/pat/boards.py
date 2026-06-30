"""Pat saved BOARDS — name any NL query (or screen) and reload it later.

Self-contained like ``feedback.py``: this module OWNS the ``pat_boards`` table
(lazy ``CREATE TABLE IF NOT EXISTS``; never edits ``src/core/db.py``) and reuses
the project's single SQLite file via ``get_conn()``. A "board" is a saved,
named query the analyst pinned — a NL Pat query (``kind='pat'``) or a screener
configuration (``kind='screen'``, used by screener_plus). Boards power the
configurable workbench (the strategist page renders them as cards).

Nothing here raises to the caller — a board failure must never break an answer.
Reads degrade to ``[]`` / ``None``.
"""
from __future__ import annotations

import json
import re

from src.core.db import get_conn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pat_boards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'pat',     -- 'pat' (NL query) | 'screen'
    query       TEXT NOT NULL DEFAULT '',        -- the NL query (kind='pat')
    flow        TEXT,                            -- the routed flow (if known)
    params_json TEXT,                            -- flow params or screen config
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (name, kind)
);
CREATE INDEX IF NOT EXISTS idx_pat_boards_kind ON pat_boards(kind, updated_at DESC);
"""

_ready = False


def _ensure(conn) -> None:
    global _ready
    if not _ready:
        conn.executescript(_SCHEMA)
        _ready = True


def _clip(s, n: int):
    s = (s or "").strip()
    return s[:n] if s else ""


_NAME_OK = re.compile(r"[^\w \-./&+()]+")


def _clean_name(name: str) -> str:
    return _NAME_OK.sub("", (name or "").strip())[:60]


def save(name: str, query: str = "", flow: str = "", params: dict | None = None,
         kind: str = "pat") -> int | None:
    """Upsert a board by (name, kind). Returns the row id (or None on failure).
    All values bound; params JSON-encoded."""
    name = _clean_name(name)
    if not name:
        return None
    kind = "screen" if str(kind).strip().lower() == "screen" else "pat"
    pj = None
    if params:
        try:
            pj = json.dumps(params, separators=(",", ":"), ensure_ascii=False)[:4000]
        except Exception:
            pj = None
    try:
        with get_conn() as conn:
            _ensure(conn)
            conn.execute(
                "INSERT INTO pat_boards (name, kind, query, flow, params_json) "
                "VALUES (?,?,?,?,?) "
                "ON CONFLICT(name, kind) DO UPDATE SET "
                "query=excluded.query, flow=excluded.flow, params_json=excluded.params_json, "
                "updated_at=datetime('now')",
                (name, kind, _clip(query, 500), _clip(flow, 40), pj),
            )
            r = conn.execute("SELECT id FROM pat_boards WHERE name=? AND kind=?",
                             (name, kind)).fetchone()
            return int(r["id"]) if r else None
    except Exception:
        return None


def _row(r) -> dict:
    params = {}
    if r["params_json"]:
        try:
            params = json.loads(r["params_json"])
        except Exception:
            params = {}
    return {"id": r["id"], "name": r["name"], "kind": r["kind"], "query": r["query"],
            "flow": r["flow"], "params": params, "updated_at": r["updated_at"]}


def list_boards(kind: str | None = None, limit: int = 60) -> list[dict]:
    """Saved boards, newest first. Optional kind filter ('pat' / 'screen')."""
    limit = max(1, min(int(limit or 60), 200))
    try:
        with get_conn() as conn:
            _ensure(conn)
            if kind in ("pat", "screen"):
                rows = conn.execute(
                    "SELECT * FROM pat_boards WHERE kind=? ORDER BY updated_at DESC LIMIT ?",
                    (kind, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM pat_boards ORDER BY updated_at DESC LIMIT ?",
                    (limit,)).fetchall()
            return [_row(r) for r in rows]
    except Exception:
        return []


def get(name: str, kind: str = "pat") -> dict | None:
    try:
        with get_conn() as conn:
            _ensure(conn)
            r = conn.execute("SELECT * FROM pat_boards WHERE name=? AND kind=?",
                             (_clean_name(name), "screen" if kind == "screen" else "pat")).fetchone()
            return _row(r) if r else None
    except Exception:
        return None


def delete(name: str, kind: str = "pat") -> bool:
    try:
        with get_conn() as conn:
            _ensure(conn)
            cur = conn.execute("DELETE FROM pat_boards WHERE name=? AND kind=?",
                               (_clean_name(name), "screen" if kind == "screen" else "pat"))
            return cur.rowcount > 0
    except Exception:
        return False


def count() -> int:
    try:
        with get_conn() as conn:
            _ensure(conn)
            return int(conn.execute("SELECT COUNT(*) n FROM pat_boards").fetchone()["n"])
    except Exception:
        return 0
