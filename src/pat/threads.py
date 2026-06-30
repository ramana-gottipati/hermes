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
-- CL-PAT-10: enforce one row per (tid, turn). `MAX(turn)+1` then INSERT can collide under
-- concurrency; this UNIQUE index turns a colliding INSERT into an IntegrityError the writer
-- retries instead of silently duplicating a turn. Created IF NOT EXISTS so it is a no-op on
-- a clean store; on a store that somehow already holds a dup it will error here and the
-- caller's try/except degrades gracefully (the feature is best-effort).
CREATE UNIQUE INDEX IF NOT EXISTS uq_pat_threads_tid_turn ON pat_threads(tid, turn);
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
    import sqlite3 as _sqlite3
    try:
        with get_conn() as conn:
            _ensure(conn)
            # CL-PAT-10: compute MAX(turn)+1 and INSERT; on the (rare, single-user)
            # concurrent collision the UNIQUE(tid,turn) index raises IntegrityError —
            # retry with a freshly-read max a few times rather than duplicating a turn.
            nxt = None
            for _ in range(5):
                r = conn.execute(
                    "SELECT COALESCE(MAX(turn), 0) m FROM pat_threads WHERE tid=?",
                    (tid,)).fetchone()
                nxt = (int(r["m"]) if r else 0) + 1
                try:
                    conn.execute(
                        "INSERT INTO pat_threads (tid, turn, query, flow, params_json) "
                        "VALUES (?,?,?,?,?)",
                        (tid, nxt, query, flow, pj),
                    )
                    break
                except _sqlite3.IntegrityError:
                    nxt = None
                    continue
            if nxt is None:
                return None
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
                "SELECT * FROM pat_threads WHERE tid=? ORDER BY turn DESC, id DESC LIMIT ?",
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


# ── CONJUNCTIVE refine across turns (AND, not replace) ────────────────────────
# When the prior turn produced a ranked LIST (RS leaders / accumulation / credibility
# / a confluence), a follow-up that ADDS a criterion ("…with credible management",
# "and the cheap ones", "only small-caps") must REFINE that list — i.e. intersect the
# new pillar with the prior set — NOT re-route to a pure single-pillar board (which is
# the QA-round2 #5 bug: "strongest stocks … with credible management" returned a pure
# credibility list, ~1/80 overlap with the RS leaders it was meant to refine).
#
# The mechanism reuses the SAME proven path the URL refine-chips already use: rebuild a
# COMBINED query ("RS leaders with credible management") and re-route it — the engine's
# semantic parse (and its deterministic fallback) then sees >=2 strategy families and
# the compiler intersects them via the confluence planner. We deliberately rebuild the
# base from the prior flow's CANONICAL phrase (below), not the raw prior text, so the
# base pillar always fires its keyword in both the LLM and the quota-down fallback path
# (e.g. a prior "strongest stocks" → canonical "RS leaders", which the fallback's _PIL_RS
# recognises; "strongest" alone would not).

# Planner-eligible LIST flows → the canonical phrase that re-states the base pillar.
# MIRRORS web._FLOW_BASE_Q for exactly the multi-row screens a refinement can narrow.
# (Single-name flows — card/why/trend/compare/stock — are intentionally absent: those
# are pronoun-subject follow-ups, handled by last_symbol(), not list refinement.)
LIST_FLOW_BASE = {
    "rs": "RS leaders",
    "rslag": "weak laggard stocks",
    "accumulation": "stocks being accumulated",
    "distribution": "stocks being distributed",
    "consolidation": "consolidating stocks",
    "fundamentals": "quality value stocks",
    "credibility": "credible companies",
    "deterioration": "managements with deteriorating credibility",
    "confluence": "credible companies being accumulated",
    "confluence_plan": "",   # already a planner; refine appends to its own prior text
    "movers": "biggest movers today",
    "pt14": "pt14 quality tier stocks",
}

# A turn that LOOKS like a conjunctive refinement of a prior list: it leads with an
# additive connector ("with / and / that are / also / plus / only / but / restricted to")
# OR is one of the bare added-criteria the refine-chips emit ("small caps", "mid caps",
# "large caps"). These are the phrases meant to be AND-ed onto the running result, never
# to stand alone as a fresh screen.
_REFINE_LEAD = re.compile(
    r"^\s*(?:"
    r"with\b|and\b|&\s|that\s+are\b|that\s+is\b|that\s+have\b|which\s+are\b|"
    r"also\b|plus\b|only\b|but\b|just\b|restrict(?:ed)?\s+to\b|limited\s+to\b|"
    r"in\s+(?:the\s+)?(?:it|pharma|auto|bank|fmcg|metal|energy|chemical)\b|"
    r"small[\s-]?caps?\b|mid[\s-]?caps?\b|large[\s-]?caps?\b|micro[\s-]?caps?\b"
    r")",
    re.I,
)
# A bare cap-band added-criterion (the chip phrasings) with no connector — still a refine.
_REFINE_BARE = re.compile(r"^\s*(?:small|mid|large|micro)[\s-]?caps?\s*$", re.I)
# If the follow-up itself NAMES a ticker-shaped token, it is not a list-refinement of the
# running set (it's a new subject ask) — let the normal router handle it. (Stopwords that
# are uppercase but not tickers are excluded so "with credible management" isn't blocked.)
_REFINE_HAS_SYM = re.compile(r"\b[A-Z][A-Z0-9&.\-]{2,15}\b")
# CL-PAT-05: SINGLE source of truth for "uppercase tokens that look like a ticker but
# are really an indicator/word" — shared with pat.web's follow-up resolver so the two
# stopword lists can't drift. Superset of both prior lists.
SYM_STOPWORDS = frozenset({"RS", "MACD", "RSI", "CCI", "MEP", "CPR", "DVPT",
                           "PE", "P", "Q", "IT", "AND", "WITH"})
_REFINE_SYM_STOP = SYM_STOPWORDS


def refine_base(tid: str, q: str) -> str:
    """If ``q`` is a conjunctive refinement of the thread's most-recent LIST answer,
    return the COMBINED query ('<canonical base> <q>') to re-route through the planner
    (which intersects the pillars). Returns '' when it is NOT a list-refinement — a
    fresh screen, a pronoun/single-name follow-up, or no prior list turn — so the caller
    falls through to its normal routing. ₹0, never raises.
    """
    tid = _valid(tid)
    q = (q or "").strip()
    if not tid or not q:
        return ""
    if not (_REFINE_LEAD.match(q) or _REFINE_BARE.match(q)):
        return ""
    # don't hijack a follow-up that names its own subject ticker (e.g. "and TITAN too")
    syms = [m for m in _REFINE_HAS_SYM.findall(q) if m not in _REFINE_SYM_STOP]
    if syms:
        return ""
    lt = last_turn(tid)
    if not lt:
        return ""
    flow = (lt.get("flow") or "").strip()
    if flow not in LIST_FLOW_BASE:
        return ""
    # base = the flow's CANONICAL pillar phrase when it has one (so the base pillar's
    # keyword always fires in both the LLM parse and the quota-down deterministic
    # fallback — e.g. a free-text "strongest stocks" rebuilds as "RS leaders", which
    # _PIL_RS recognises). Only fall back to the prior turn's raw NL for a flow with no
    # canonical phrase (confluence_plan — already a planner; append to its own text).
    base = LIST_FLOW_BASE.get(flow, "") or (lt.get("query") or "").strip()
    if not base:
        return ""
    combined = f"{base} {q}".strip()
    # never return a no-op (base already contains the refinement, or q == base)
    if combined.lower() == base.lower():
        return ""
    return combined[:500]


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
    # ── refine_base: a conjunctive follow-up on a prior LIST rebuilds the combined
    #    query (canonical base ∩ new pillar) so the planner intersects, not replaces.
    t3 = new_tid()
    # the QA-round2 repro: a free-text RS screen, then "with credible management"
    record(t3, query="strongest stocks over the last month", flow="rs",
           params={"strength": "leaders", "window": "1m"})
    rb = refine_base(t3, "with credible management")
    assert rb == "RS leaders with credible management", \
        f"refine rebuilds from CANONICAL base (not 'strongest…'), got {rb!r}"
    # a chip-driven screen (query="") still rebuilds from the canonical phrase
    t4 = new_tid()
    record(t4, query="", flow="rs", params={"strength": "leaders"})
    assert refine_base(t4, "that are credible") == "RS leaders that are credible", \
        "chip-driven base uses canonical phrase"
    assert refine_base(t4, "small caps") == "RS leaders small caps", "bare cap-band is a refine"
    # NOT a refine: a pronoun/single-name follow-up, or a fresh screen, or naming a ticker
    assert refine_base(t4, "is it credible") == "", "pronoun ask is not a list-refine"
    assert refine_base(t4, "most credible managements") == "", "a fresh screen is not a refine"
    assert refine_base(t4, "and TITAN too") == "", "a follow-up naming a ticker is not a refine"
    # no prior list turn → no refine
    t5 = new_tid()
    record(t5, query="tell me about TITAN", flow="card", params={"sym": "TITAN"})
    assert refine_base(t5, "with credible management") == "", \
        "single-name prior turn is not a refinable list"
    assert refine_base(new_tid(), "with credible management") == "", "empty thread → no refine"
    clear(t3); clear(t4); clear(t5)
    # rolling-window trim
    for i in range(20):
        record(t, query=f"q{i}", flow="rs")
    assert len(history(t, limit=50)) <= _MAX_TURNS, "rolling window caps turns"
    clear(t)
    assert history(t) == [], "clear empties the thread"
    print(f"threads selftest: OK  (mint/validate/record/history/context/last_symbol/trim/clear; "
          f"window={_MAX_TURNS}, n1={n1} n2={n2})")
