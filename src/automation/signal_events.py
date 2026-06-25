"""Signal-event bus — the Tier-0 spine of the v2 platform (product-strategy-2026.md §9).

Every lens emits TYPED state-change events to one table; every consumer reads from it:
the "since you last looked" brief, the Attention Queue, the alert rail, and (later)
the SSE stream + the /v1 API. "One bus, four faces."

A signal-event is a *derived judgement that something changed* — not a raw value:
  • level_cross      — a metric crossed a meaningful threshold (e.g. RS-band into support)
  • percentile_breach— a percentile rank crossed a band (e.g. delivery-value into the 95th)
  • phase_flip       — a categorical state changed (MEP ACCUM↔DISTRIB, RS weather)
  • oi_flip          — F&O positioning quadrant changed (LONG_BUILDUP↔SHORT_BUILDUP)
  • credibility_step — CCI credibility level/trend stepped (the wedge's event)
  • deal_print       — a bulk/block deal was recorded
Each event keeps the raw before→after states beside the verdict (data-first doctrine)
and an `as_of` so it is point-in-time honest.

DOCTRINE: rule-based, no LLM. Isolation (per §0.8): brand-new module, owns its
`signal_events` table via ensure_schema() — no db.py edit, no contended-file edit.
The detection ORCHESTRATOR (`run_detection`) reads existing signal tables defensively
(each lens in its own try/except) so a missing table/column degrades to "no events",
never a crash. The core (emit + the read-APIs + the pure detectors) is fully testable
without the production tables.

CLI:
    python -m src.automation.signal_events --detect [--asof YYYY-MM-DD]
    python -m src.automation.signal_events --stats
    python -m src.automation.signal_events --since "2026-06-20 00:00:00" --symbols RELIANCE,VEDL
"""
from __future__ import annotations

import argparse
import logging
from typing import Iterable, Optional

log = logging.getLogger("hermes.signal_events")

# --- owned table (fold into db.py SCHEMA_BASE later) -------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS signal_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    lens        TEXT NOT NULL,        -- rs | mep | dvpt | cci | oi | deal | quality | cpr
    event_type  TEXT NOT NULL,        -- level_cross | percentile_breach | phase_flip | oi_flip | credibility_step | deal_print
    direction   TEXT,                 -- up | down | in | out | flip
    from_state  TEXT,                 -- prior raw value/state (kept beside the verdict)
    to_state    TEXT,                 -- new raw value/state
    magnitude   REAL,                 -- |change|, for ranking impact (0..1 normalized where possible)
    as_of       TEXT NOT NULL,        -- the trade_date / period the event is computed for (PIT)
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    note        TEXT,                 -- one honest, pre-computed line (no LLM)
    UNIQUE(symbol, lens, event_type, as_of)   -- idempotent: one event per (symbol,lens,type,date)
);
CREATE INDEX IF NOT EXISTS idx_sigev_symbol   ON signal_events(symbol, as_of DESC);
CREATE INDEX IF NOT EXISTS idx_sigev_asof      ON signal_events(as_of DESC);
CREATE INDEX IF NOT EXISTS idx_sigev_detected  ON signal_events(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_sigev_lens       ON signal_events(lens, event_type);
"""

LENSES = ("rs", "mep", "dvpt", "cci", "oi", "deal", "quality", "cpr")
EVENT_TYPES = ("level_cross", "percentile_breach", "phase_flip", "oi_flip",
               "credibility_step", "deal_print")


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


# --- pure detectors (no DB; unit-testable) -----------------------------------

def detect_phase_flip(prev: Optional[str], curr: Optional[str]) -> Optional[dict]:
    """A categorical state changed (MEP phase, RS weather). Returns event kwargs or None."""
    p = (prev or "").strip().upper() or None
    c = (curr or "").strip().upper() or None
    if p is None or c is None or p == c:
        return None
    return {"event_type": "phase_flip", "direction": "flip",
            "from_state": p, "to_state": c, "magnitude": 1.0}


def detect_threshold_cross(prev, curr, threshold: float) -> Optional[dict]:
    """A numeric metric crossed `threshold` between prev and curr."""
    try:
        p, c = float(prev), float(curr)
    except (TypeError, ValueError):
        return None
    if p < threshold <= c:
        d = "up"
    elif p >= threshold > c:
        d = "down"
    else:
        return None
    return {"event_type": "level_cross", "direction": d,
            "from_state": f"{p:g}", "to_state": f"{c:g}",
            "magnitude": min(1.0, abs(c - p) / (abs(threshold) + 1e-9))}


def detect_percentile_breach(prev, curr, *, hi: float = 90.0, lo: float = 10.0) -> Optional[dict]:
    """A 0–100 percentile crossed into the top (hi) or bottom (lo) band."""
    try:
        p, c = float(prev), float(curr)
    except (TypeError, ValueError):
        return None
    if p < hi <= c:
        return {"event_type": "percentile_breach", "direction": "up",
                "from_state": f"{p:g}", "to_state": f"{c:g}", "magnitude": (c - hi) / (100 - hi + 1e-9)}
    if p > lo >= c:
        return {"event_type": "percentile_breach", "direction": "down",
                "from_state": f"{p:g}", "to_state": f"{c:g}", "magnitude": (lo - c) / (lo + 1e-9)}
    return None


def detect_credibility_step(prev_level, curr_level, prev_trend=None, curr_trend=None,
                            *, step: float = 5.0) -> Optional[dict]:
    """CCI credibility level moved ≥ step, or the trend label flipped (the wedge's event)."""
    flip = detect_phase_flip(prev_trend, curr_trend)
    try:
        p, c = float(prev_level), float(curr_level)
        moved = abs(c - p) >= step
    except (TypeError, ValueError):
        p = c = None
        moved = False
    if not moved and not flip:
        return None
    d = "up" if (c is not None and p is not None and c >= p) else "down"
    return {"event_type": "credibility_step", "direction": d,
            "from_state": (f"{p:g}" if p is not None else (flip["from_state"] if flip else None)),
            "to_state": (f"{c:g}" if c is not None else (flip["to_state"] if flip else None)),
            "magnitude": (min(1.0, abs(c - p) / 50.0) if (p is not None and c is not None) else 1.0)}


# --- persistence -------------------------------------------------------------

def emit(conn, symbol: str, lens: str, as_of: str, ev: dict, *, note: str = "") -> int:
    """Idempotently record one event (ev = a detector's output dict). Returns rows inserted."""
    symbol = (symbol or "").strip().upper()
    if not symbol or not ev:
        return 0
    cur = conn.execute(
        "INSERT OR IGNORE INTO signal_events "
        "(symbol, lens, event_type, direction, from_state, to_state, magnitude, as_of, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, lens, ev["event_type"], ev.get("direction"), ev.get("from_state"),
         ev.get("to_state"), ev.get("magnitude"), as_of, note or _auto_note(symbol, lens, ev)))
    return cur.rowcount or 0


def _auto_note(symbol: str, lens: str, ev: dict) -> str:
    label = {"rs": "RS", "mep": "accumulation", "dvpt": "delivery", "cci": "credibility",
             "oi": "F&O positioning", "deal": "deal", "quality": "quality", "cpr": "structure"}.get(lens, lens)
    et = ev["event_type"]
    fr, to = ev.get("from_state"), ev.get("to_state")
    if et == "phase_flip":
        return f"{symbol}: {label} flipped {fr} → {to}"
    if et == "credibility_step":
        return f"{symbol}: {label} {ev.get('direction')} ({fr} → {to})"
    if et == "percentile_breach":
        return f"{symbol}: {label} percentile {ev.get('direction')} to {to}"
    if et == "level_cross":
        return f"{symbol}: {label} crossed {ev.get('direction')} ({fr} → {to})"
    return f"{symbol}: {label} {et}"


# --- read APIs (the consumers: since-you-last-looked, Attention Queue) --------

def _rows(conn, sql: str, params: tuple) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def events_since(conn, since_detected_at: str, *, symbols: Optional[Iterable[str]] = None,
                 limit: int = 200) -> list[dict]:
    """The 'since you last looked' feed: events detected after a timestamp, optionally scoped."""
    ensure_schema(conn)
    where = ["detected_at > ?"]
    params: list = [since_detected_at]
    syms = [s.strip().upper() for s in symbols if s and s.strip()] if symbols else []
    if syms:
        where.append(f"symbol IN ({','.join('?' * len(syms))})")
        params += syms
    params.append(int(limit))
    return _rows(conn, f"SELECT * FROM signal_events WHERE {' AND '.join(where)} "
                       f"ORDER BY detected_at DESC, magnitude DESC LIMIT ?", tuple(params))


def events_for(conn, symbol: str, *, limit: int = 50) -> list[dict]:
    """A single name's event timeline, newest first (the dossier strip)."""
    ensure_schema(conn)
    return _rows(conn, "SELECT * FROM signal_events WHERE symbol = ? "
                       "ORDER BY as_of DESC, detected_at DESC LIMIT ?",
                 (symbol.strip().upper(), int(limit)))


def attention_queue(conn, *, as_of: Optional[str] = None, symbols: Optional[Iterable[str]] = None,
                    limit: int = 6) -> list[dict]:
    """The home headline: the most impactful recent state-changes (impact = magnitude × recency).
    Hard-capped (default 6) to stay an Attention Queue, not a firehose."""
    ensure_schema(conn)
    where: list[str] = []
    params: list = []
    if as_of:
        where.append("as_of = ?"); params.append(as_of)
    else:
        where.append("as_of = (SELECT MAX(as_of) FROM signal_events)")
    syms = [s.strip().upper() for s in symbols if s and s.strip()] if symbols else []
    if syms:
        where.append(f"symbol IN ({','.join('?' * len(syms))})"); params += syms
    params.append(int(limit))
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    return _rows(conn, f"SELECT * FROM signal_events{clause} "
                       f"ORDER BY magnitude DESC, detected_at DESC LIMIT ?", tuple(params))


def stats(conn) -> dict:
    ensure_schema(conn)
    total = conn.execute("SELECT COUNT(*) c FROM signal_events").fetchone()["c"]
    by_lens = {r["lens"]: r["c"] for r in conn.execute(
        "SELECT lens, COUNT(*) c FROM signal_events GROUP BY lens ORDER BY c DESC")}
    by_type = {r["event_type"]: r["c"] for r in conn.execute(
        "SELECT event_type, COUNT(*) c FROM signal_events GROUP BY event_type ORDER BY c DESC")}
    latest = conn.execute("SELECT MAX(as_of) m FROM signal_events").fetchone()["m"]
    return {"events": total, "by_lens": by_lens, "by_type": by_type, "latest_as_of": latest}


# --- detection orchestrator (reads existing signal tables; defensive per lens) ---

def _latest_two(conn, table: str, symbol: str, cols: str, order: str = "trade_date"):
    """The two most-recent rows for a symbol (curr, prev) or (curr, None). Defensive."""
    try:
        rows = conn.execute(
            f"SELECT {cols}, {order} AS _o FROM {table} WHERE symbol = ? "
            f"ORDER BY {order} DESC LIMIT 2", (symbol.strip().upper(),)).fetchall()
    except Exception:
        return None, None
    if not rows:
        return None, None
    return dict(rows[0]), (dict(rows[1]) if len(rows) > 1 else None)


def _symbols_in(conn, table: str) -> list[str]:
    try:
        return [r[0] for r in conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()]
    except Exception:
        return []


def run_detection(conn, as_of: Optional[str] = None) -> dict:
    """Compare the latest two states per lens per symbol and emit events. Each lens is
    independent + defensive — a missing table/column yields zero events, never a crash.
    Column names are probed tolerantly so this survives schema drift across the VPS DB."""
    ensure_schema(conn)
    emitted = {lens: 0 for lens in LENSES}

    # MEP phase flip (mep_signals.mep_state_smooth or mep_phase) ---------------
    for sym in _symbols_in(conn, "mep_signals"):
        for col in ("mep_state_smooth", "mep_phase", "mep_state"):
            curr, prev = _latest_two(conn, "mep_signals", sym, col)
            if curr is None or col not in curr:
                continue
            if prev is not None:
                ev = detect_phase_flip(prev.get(col), curr.get(col))
                if ev:
                    emitted["mep"] += emit(conn, sym, "mep", curr.get("_o") or (as_of or ""), ev)
            break

    # CCI credibility step (credibility_series.level/trend) --------------------
    for sym in _symbols_in(conn, "credibility_series"):
        curr, prev = _latest_two(conn, "credibility_series", sym, "level, trend", order="as_of")
        if curr is not None and prev is not None:
            ev = detect_credibility_step(prev.get("level"), curr.get("level"),
                                         prev.get("trend"), curr.get("trend"))
            if ev:
                emitted["cci"] += emit(conn, sym, "cci", str(curr.get("_o") or as_of or ""), ev)

    # F&O OI quadrant flip (fno_oi_signals.quadrant) ---------------------------
    for sym in _symbols_in(conn, "fno_oi_signals"):
        curr, prev = _latest_two(conn, "fno_oi_signals", sym, "quadrant")
        if curr is not None and prev is not None and "quadrant" in curr:
            ev = detect_phase_flip(prev.get("quadrant"), curr.get("quadrant"))
            if ev:
                ev["event_type"] = "oi_flip"
                emitted["oi"] += emit(conn, sym, "oi", str(curr.get("_o") or as_of or ""), ev)

    conn.commit()
    log.info("signal_events run_detection: %s", {k: v for k, v in emitted.items() if v})
    return {"emitted": emitted, "total": sum(emitted.values())}


# --- CLI ---------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Signal-event bus (rule-based, no LLM).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--detect", action="store_true", help="run detection over existing signal tables")
    g.add_argument("--stats", action="store_true", help="event coverage summary")
    g.add_argument("--since", metavar="TS", help="list events detected after this timestamp")
    ap.add_argument("--asof", default=None)
    ap.add_argument("--symbols", default="")
    args = ap.parse_args()

    from src.core.db import get_conn
    syms = [s for s in args.symbols.split(",") if s.strip()] or None
    with get_conn() as conn:
        if args.detect:
            log.info("done: %s", run_detection(conn, as_of=args.asof))
        elif args.stats:
            import json
            print(json.dumps(stats(conn), indent=2))
        else:
            for e in events_since(conn, args.since, symbols=syms):
                print(f"  {e['as_of']}  {e['lens']:5} {e['event_type']:18} {e['note']}")


if __name__ == "__main__":
    main()
