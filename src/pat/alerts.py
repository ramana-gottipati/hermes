"""Pat proactive ALERTS — edge-triggered "what newly aligned" (descriptive, opt-in).

Self-contained like ``feedback.py`` / ``boards.py``: OWNS the ``pat_alert_snapshots``
table (lazy ``CREATE TABLE IF NOT EXISTS``). Watches the CONFLUENCE set (names that
are BOTH credible AND being accumulated — the highest-evidence read) and the user's
watchlist, and flags what has NEWLY entered since the last snapshot.

Edge-triggered, not a stream: ``compute(conn)`` diffs the current confluence set vs
the last stored snapshot and returns {new, dropped, current}. The FIRST run silently
establishes a baseline (no false "new" spam). ``rebaseline(conn)`` ("mark seen")
stores the current set as the new baseline — call it from the workbench's "mark seen"
action or a nightly job. DESCRIPTIVE only — a new alignment is evidence, never a buy
call (the §C falsification stands).

Nothing here raises to the caller — failures degrade to empty alerts.
"""
from __future__ import annotations

import json

from src.core.db import get_conn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pat_alert_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL DEFAULT 'confluence',
    symbols_json TEXT NOT NULL,
    as_of       TEXT,
    taken_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pat_alert_kind ON pat_alert_snapshots(kind, taken_at DESC);
"""

_ready = False


def _ensure(conn) -> None:
    global _ready
    if not _ready:
        conn.executescript(_SCHEMA)
        _ready = True


def _current_confluence(conn) -> tuple[list, str | None]:
    """The current confluence membership (credible ∩ accumulated) + its as-of date.
    Reuses the deterministic build_confluence_query (precomputed reads only)."""
    try:
        from src.pat.flows import build_confluence_query
        sql, params = build_confluence_query()
        rows = list(conn.execute(sql, params))
    except Exception:
        return [], None
    syms = [r["symbol"] for r in rows]
    asof = None
    try:
        asof = conn.execute("SELECT MAX(trade_date) FROM stock_signals").fetchone()[0]
    except Exception:
        asof = None
    return syms, asof


def _last_snapshot(conn, kind: str = "confluence"):
    try:
        return conn.execute(
            "SELECT symbols_json, as_of, taken_at FROM pat_alert_snapshots "
            "WHERE kind=? ORDER BY taken_at DESC LIMIT 1", (kind,)).fetchone()
    except Exception:
        return None


def _store(conn, syms, asof, kind: str = "confluence") -> None:
    try:
        conn.execute(
            "INSERT INTO pat_alert_snapshots (kind, symbols_json, as_of) VALUES (?,?,?)",
            (kind, json.dumps(sorted(set(syms)), separators=(",", ":")), asof))
    except Exception:
        pass


def compute(conn, kind: str = "confluence") -> dict:
    """Diff the current confluence set vs the last snapshot. First run baselines silently.
    Returns {new, dropped, current, count, as_of, baseline_at, first_run}."""
    out = {"new": [], "dropped": [], "current": [], "count": 0,
           "as_of": None, "baseline_at": None, "first_run": False}
    if conn is None:
        return out
    try:
        _ensure(conn)
        cur_syms, asof = _current_confluence(conn)
        cur = set(cur_syms)
        out["current"] = sorted(cur)
        out["count"] = len(cur)
        out["as_of"] = asof
        last = _last_snapshot(conn, kind)
        if not last:
            _store(conn, cur_syms, asof, kind)         # silent baseline
            out["first_run"] = True
            return out
        try:
            base = set(json.loads(last["symbols_json"] or "[]"))
        except Exception:
            base = set()
        out["baseline_at"] = last["taken_at"]
        out["new"] = sorted(cur - base)
        out["dropped"] = sorted(base - cur)
    except Exception:
        return out
    return out


def rebaseline(conn, kind: str = "confluence") -> bool:
    """Store the current confluence set as the new baseline ('mark seen' / nightly)."""
    if conn is None:
        return False
    try:
        _ensure(conn)
        cur_syms, asof = _current_confluence(conn)
        _store(conn, cur_syms, asof, kind)
        return True
    except Exception:
        return False


def diff_set(conn, kind: str, current_syms, as_of=None) -> dict:
    """GENERIC since-last-refresh diff for ANY named symbol set (e.g. a strategy's
    top names) — the engine behind the strategist 'what changed' read. Diffs the
    passed ``current_syms`` against the last snapshot stored under ``kind`` and
    re-baselines to the current set so the NEXT call shows the delta since this one.
    First call baselines silently. Returns {new, dropped, count, baseline_at,
    first_run}. Descriptive; never raises. ``kind`` should be namespaced per strategy
    (e.g. 'strat:mep')."""
    out = {"new": [], "dropped": [], "count": 0, "baseline_at": None, "first_run": False}
    if conn is None:
        return out
    try:
        _ensure(conn)
        cur = sorted({(s or "").strip().upper() for s in (current_syms or []) if (s or "").strip()})
        out["count"] = len(cur)
        last = _last_snapshot(conn, kind)
        # re-baseline to the current set every read (a board view = the new reference)
        _store(conn, cur, as_of, kind)
        if not last:
            out["first_run"] = True
            return out
        try:
            base = set(json.loads(last["symbols_json"] or "[]"))
        except Exception:
            base = set()
        out["baseline_at"] = last["taken_at"]
        out["new"] = sorted(set(cur) - base)
        out["dropped"] = sorted(base - set(cur))
    except Exception:
        return out
    return out


def watchlist_alignment(conn, limit: int = 40) -> list[dict]:
    """Which WATCHLIST names are currently in the confluence set (credible AND being
    accumulated) — the opt-in 'something you're watching just aligned' read. Empty if
    no watchlist / no overlap. Descriptive."""
    if conn is None:
        return []
    try:
        wl = [r["symbol"] for r in conn.execute("SELECT symbol FROM watchlist").fetchall()]
    except Exception:
        wl = []
    if not wl:
        return []
    cur, _asof = _current_confluence(conn)
    cset = set(cur)
    hits = [s for s in wl if s in cset][:limit]
    return [{"symbol": s} for s in hits]
