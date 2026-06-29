"""Pat conversation THREADS — server-side multi-turn memory keyed by a thread id.

Self-contained like ``boards.py`` / ``feedback.py``: this module OWNS the
``pat_threads`` table (lazy ``CREATE TABLE IF NOT EXISTS``; never edits
``src/core/db.py``) and reuses the project's single SQLite file via
``get_conn()``.

WHY this exists
---------------
Pat's multi-turn UX is today *stateless* — a refinement chip navigates to
``/dash/pat?q=<context + added-condition>`` and the whole conversation rides in
the URL. That works without any server state and stays the primary path. But a
TRUE multi-turn thread (server remembers the last turns for a given browser
session, so an implicit "…and the credible ones" can resolve against the prior
answer without re-stating it, and the page can show a short conversation trail)
needs a stable per-session key.

That key — ``tid`` — must be minted/forwarded by the page route (a cookie set on
the ``Request``/``Response`` at ``dashboard.py``). That call-site edit is the
ORCHESTRATOR's (the page route file is frozen for this lane). This module +
``web.render_pat``'s optional ``tid`` parameter are built so the feature works
**the moment** that one-line cookie plumb lands — and is completely inert
(zero behaviour change) until then, because ``render_pat`` defaults ``tid=""``.

Contract for the orchestrator (the one-line call-site change):
    # in dashboard.py /dash/pat route, with `request: Request` + `response: Response`
    tid = request.cookies.get("pat_tid") or threads.new_tid()
    response.set_cookie("pat_tid", tid, max_age=60*60*24*30, httponly=True, samesite="lax")
    body = render_pat(..., tid=tid, conn=conn)

Safety
------
Nothing here raises to the caller — a thread failure must NEVER break an answer.
All reads degrade to ``[]`` / ``None``. The ``tid`` is server-minted (uuid4 hex),
never reflected into HTML unescaped, and bound as a SQL parameter. Turns are
capped per thread (a rolling window) so the table can't grow unbounded.
"""
from __future__ import annotations

import json
import re
import uuid

from src.core.db import get_conn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pat_threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tid         TEXT NOT NULL,                   -- the per-session thread id (cookie)
    turn        INTEGER NOT NULL DEFAULT 0,      -- monotonically increasing within a tid
    query       TEXT NOT NULL DEFAULT '',        -- the NL query the analyst asked
    flow        TEXT,                            -- the routed flow (if known)
    params_json TEXT,                            -- the flow params (for context replay)
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pat_threads_tid ON pat_threads(tid, turn DESC);
"""

# Keep only the most recent N turns per thread (a rolling conversation window).
_MAX_TURNS = 12
_TID_OK = re.compile(r"^[0-9a-f]{8,40}$")

_ready = False


def _ensure(conn) -> None:
    global _ready
    if not _ready:
        conn.executescript(_SCHEMA)
        _ready = True


def new_tid() -> str:
    """Mint a fresh thread id (the orchestrator stores this in a cookie)."""
    return uuid.uuid4().hex


def _valid(tid: str) -> str:
    """Accept only a server-minted-shaped id; reject anything else (returns '')."""
    tid = (tid or "").strip().lower()
    return tid if _TID_OK.match(tid) else ""


def _clip(s, n: int):
    s = (s or "").strip()
    return s[:n] if s else ""


def record(tid: str, query: str = "", flow: str = "", params: dict | None = None) -> int | None:
    """Append a turn to a thread. Returns the turn number (or None on failure).

    Only records when there is something to remember (a concrete query OR flow) —
    a bare home/face/chooser view is not a conversation turn. Trims the thread to
    the rolling window so the table stays bounded.
    """
    tid = _valid(tid)
    if not tid:
        return None
    query = _clip(query, 500)
    flow = _clip(flow, 40)
    if not query and not flow:
        return None
    pj = None
    if params:
        try:
            pj = json.dumps(params, separators=(",", ":"), ensure_ascii=False)[:2000]
        except Exception:
            pj = None
    try:
        with get_conn() as conn:
            _ensure(conn)
            r = conn.execute("SELECT COALESCE(MAX(turn), 0) m FROM pat_threads WHERE tid=?",
                             (tid,)).fetchone()
            nxt = int(r["m"]) + 1 if r else 1
            conn.execute(
                "INSERT INTO pat_threads (tid, turn, query, flow, params_json) VALUES (?,?,?,?,?)",
                (tid, nxt, query, flow, pj),
            )
            # rolling-window trim: keep the newest _MAX_TURNS
            conn.execute(
                "DELETE FROM pat_threads WHERE tid=? AND turn <= ?",
                (tid, nxt - _MAX_TURNS),
            )
            return nxt
    except Exception:
        return None


def _row(r) -> dict:
    params = {}
    if r["params_json"]:
        try:
            params = json.loads(r["params_json"])
        except Exception:
            params = {}
    return {"turn": r["turn"], "query": r["query"], "flow": r["flow"],
            "params": params, "created_at": r["created_at"]}


def history(tid: str, limit: int = _MAX_TURNS) -> list[dict]:
    """The thread's turns, OLDEST first (chronological reading order). [] if none."""
    tid = _valid(tid)
    if not tid:
        return []
    limit = max(1, min(int(limit or _MAX_TURNS), 50))
    try:
        with get_conn() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT * FROM pat_threads WHERE tid=? ORDER BY turn DESC LIMIT ?",
                (tid, limit)).fetchall()
            return [_row(r) for r in reversed(rows)]
    except Exception:
        return []


def last_turn(tid: str) -> dict | None:
    """The most recent turn (for resolving an implicit follow-up against). None if empty."""
    h = history(tid, limit=1)
    return h[-1] if h else None


def context_query(tid: str) -> str:
    """The latest concrete NL query in the thread — the phrase a typed implicit
    follow-up ('…and the credible ones') should be appended to. '' if none."""
    lt = last_turn(tid)
    if not lt:
        return ""
    return (lt.get("query") or "").strip()


def last_symbol(tid: str) -> str:
    """The most recently referenced SYMBOL in the thread (newest-first scan of the
    turn params) — the subject an implicit follow-up ('what about its credibility?')
    resolves the pronoun to. '' if no turn named a single symbol.

    Reads a single-name flow's `sym` param (card/why/trend/stock), or the FIRST of a
    compare's `syms`. A list/screen turn (no single subject) is skipped, so the
    pronoun binds to the last name actually discussed, not a screen."""
    tid = _valid(tid)
    if not tid:
        return ""
    for h in reversed(history(tid)):          # newest first
        p = h.get("params") or {}
        sym = (p.get("sym") or "").strip()
        if sym:
            return sym.upper()
        syms = (p.get("syms") or "").strip()
        if syms:
            first = syms.split(",")[0].strip()
            if first:
                return first.upper()
    return ""


def clear(tid: str) -> bool:
    """Forget a thread (the 'start over' affordance)."""
    tid = _valid(tid)
    if not tid:
        return False
    try:
        with get_conn() as conn:
            _ensure(conn)
            cur = conn.execute("DELETE FROM pat_threads WHERE tid=?", (tid,))
            return cur.rowcount >= 0
    except Exception:
        return False


def count_threads() -> int:
    try:
        with get_conn() as conn:
            _ensure(conn)
            return int(conn.execute("SELECT COUNT(DISTINCT tid) n FROM pat_threads").fetchone()["n"])
    except Exception:
        return 0


# ── self-test (no DB writes to the prod tables beyond a scratch tid) ──────────
if __name__ == "__main__":
    t = new_tid()
    assert _valid(t) == t, "minted tid must validate"
    assert _valid("../etc/passwd") == "", "non-hex tid rejected"
    assert _valid("") == "", "empty tid rejected"
    n1 = record(t, query="RS leaders", flow="rs", params={"window": "1m"})
    n2 = record(t, query="RS leaders that are credible", flow="confluence_plan",
                params={"pillars": "rs,credibility"})
    assert record(t, query="", flow="") is None, "empty turn not recorded"
    h = history(t)
    assert len(h) >= 2, f"expected >=2 turns, got {len(h)}"
    assert h[0]["query"] == "RS leaders", "history is oldest-first"
    assert context_query(t) == "RS leaders that are credible", "context = latest query"
    lt = last_turn(t)
    assert lt and lt["flow"] == "confluence_plan", "last_turn = newest"
    # last_symbol: the pronoun subject = the last single-name turn, screens skipped
    t2 = new_tid()
    record(t2, query="tell me about TITAN", flow="card", params={"sym": "TITAN"})
    record(t2, query="most credible managements", flow="credibility", params={})  # a screen
    assert last_symbol(t2) == "TITAN", "last_symbol = last single-name turn (screen skipped)"
    record(t2, query="compare INFY and TCS", flow="compare", params={"syms": "INFY,TCS"})
    assert last_symbol(t2) == "INFY", "last_symbol = first of the newest compare"
    assert last_symbol(new_tid()) == "", "no symbol in an empty thread"
    clear(t2)
    # rolling-window trim
    for i in range(20):
        record(t, query=f"q{i}", flow="rs")
    assert len(history(t, limit=50)) <= _MAX_TURNS, "rolling window caps turns"
    clear(t)
    assert history(t) == [], "clear empties the thread"
    print(f"threads selftest: OK  (mint/validate/record/history/context/last_symbol/trim/clear; "
          f"window={_MAX_TURNS}, n1={n1} n2={n2})")
