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

PRODUCTION WIRING (S101, 2026-07-10): `--detect` runs as step 60 of the nightly
hermes-bhavcopy chain (scripts/systemd/vps-live/hermes-bhavcopy.service.d/
60-signal-events.conf) — sequentially AFTER the 10-signals (mep_signals),
20-rsdepth (rsband_signals) and 30-fnooi (fno_oi_signals) steps that write the
tables this reads; deals (14:30 UTC) and credibility (07:00 UTC) land earlier via
their own timers. Live lenses: mep · cci · oi · rs (INDEX-grain, vs Nifty 500 —
the stock-grain RS estate has no banded state column) · deal. NOT yet emitting:
dvpt (no banded state column exists — needs its own design), quality, cpr.
Writes are collect-then-commit per lens: the read loops run lock-free and each
lens flushes in one short transaction (the DB write-lock outage class — never
hold a write txn across thousands of reads).

CLI:
    python -m src.automation.signal_events --detect [--asof YYYY-MM-DD]
    python -m src.automation.signal_events --stats
    python -m src.automation.signal_events --since "2026-06-20 00:00:00" --symbols RELIANCE,VEDL
"""
from __future__ import annotations

import argparse
import logging
import re
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


def latest_batch_on_or_before(conn, as_of: str) -> Optional[str]:
    """The newest signal_events batch date <= `as_of`, or None when none exists yet.

    The PIT resolver behind `/v1/attention?as_of=…` (AUD-38): "the queue as it stood on
    date D" serves the last computed event batch on-or-before D — an exact-date miss
    (weekend/holiday, or a date before the feed began) must not read as an empty tape.
    Callers pass the result to attention_queue(as_of=…), whose exact-match semantics
    stay unchanged for every existing consumer.
    """
    ensure_schema(conn)
    row = conn.execute("SELECT MAX(as_of) FROM signal_events WHERE as_of <= ?",
                       (str(as_of).strip()[:10],)).fetchone()
    return row[0] if row and row[0] else None


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
# These identifiers are interpolated into SQL (values can't be bound for table/column names),
# so the table/order/cols a caller may pass are constrained to a fixed allow-list. All current
# callers pass literals; this asserts the invariant so the pattern can never become an injection
# vector if a future caller ever derives one of these from data.
_ALLOWED_TABLES = frozenset({"mep_signals", "credibility_series", "fno_oi_signals"})
_ALLOWED_ORDER = frozenset({"trade_date", "as_of"})
_IDENT_LIST_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*")


def _latest_two(conn, table: str, symbol: str, cols: str, order: str = "trade_date"):
    """The two most-recent rows for a symbol (curr, prev) or (curr, None). Defensive."""
    if table not in _ALLOWED_TABLES or order not in _ALLOWED_ORDER \
            or not _IDENT_LIST_RE.fullmatch(cols):
        log.error("signal_events._latest_two: rejected non-allowlisted identifier "
                  "(table=%r order=%r cols=%r)", table, order, cols)
        return None, None
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
    if table not in _ALLOWED_TABLES:
        log.error("signal_events._symbols_in: rejected non-allowlisted table=%r", table)
        return []
    try:
        return [r[0] for r in conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()]
    except Exception:
        return []


# The rs lens benchmark: rsband_signals is keyed (numerator, denominator, trade_date)
# — index/sector numerators against two benchmarks; the bus reads the canonical one.
_RS_BENCHMARK = "Nifty 500"


def _flush(conn, lens: str, pending: list) -> int:
    """Write one lens's collected (symbol, as_of, ev, note) events in a single short
    transaction. The lens read-loops above run lock-free; holding a write txn across
    thousands of interleaved reads is the known DB write-lock outage class."""
    n = 0
    for sym, as_of, ev, note in pending:
        n += emit(conn, sym, lens, as_of, ev, note=note)
    conn.commit()
    return n


def run_detection(conn, as_of: Optional[str] = None) -> dict:
    """Compare the latest two states per lens per symbol and emit events. Each lens is
    independent + defensive — a missing table/column yields zero events, never a crash.
    Column names are probed tolerantly so this survives schema drift across the VPS DB.
    Live lenses: mep, cci, oi, rs (index-grain), deal — see the module header for why
    dvpt/quality/cpr do not emit yet. Reads collect per lens; writes flush per lens."""
    ensure_schema(conn)
    emitted = {lens: 0 for lens in LENSES}

    # MEP phase flip (mep_signals.mep_state_smooth or mep_phase) ---------------
    pending: list = []
    for sym in _symbols_in(conn, "mep_signals"):
        for col in ("mep_state_smooth", "mep_phase", "mep_state"):
            curr, prev = _latest_two(conn, "mep_signals", sym, col)
            if curr is None or col not in curr:
                continue
            if prev is not None:
                ev = detect_phase_flip(prev.get(col), curr.get(col))
                if ev:
                    pending.append((sym, str(curr.get("_o") or as_of or ""), ev, ""))
            break
    emitted["mep"] = _flush(conn, "mep", pending)

    # CCI credibility step (credibility_series.level/trend) --------------------
    # PERIOD-keyed table: ordered by (period_year, period_month) — it has NO
    # trade_date/as_of column (the original order="as_of" probe errored on every
    # symbol and the defensive except made this lens a silent permanent no-op —
    # the S101 fix). Event as_of = the day the new period row LANDED (computed_at
    # date): the PIT-knowable date, and the one that lets a step surface in that
    # day's attention batch instead of being backdated weeks to the concall period.
    pending = []
    for sym in _symbols_in(conn, "credibility_series"):
        try:
            rows = conn.execute(
                "SELECT level, trend, substr(computed_at, 1, 10) AS _knowable "
                "FROM credibility_series WHERE symbol = ? "
                "AND period_year IS NOT NULL AND period_month IS NOT NULL "
                "ORDER BY period_year DESC, period_month DESC LIMIT 2",
                (sym,)).fetchall()
        except Exception:
            rows = []
        if len(rows) == 2:
            curr, prev = dict(rows[0]), dict(rows[1])
            ev = detect_credibility_step(prev.get("level"), curr.get("level"),
                                         prev.get("trend"), curr.get("trend"))
            if ev:
                pending.append((sym, str(curr.get("_knowable") or as_of or ""), ev, ""))
    emitted["cci"] = _flush(conn, "cci", pending)

    # F&O OI quadrant flip (fno_oi_signals.quadrant) ---------------------------
    pending = []
    for sym in _symbols_in(conn, "fno_oi_signals"):
        curr, prev = _latest_two(conn, "fno_oi_signals", sym, "quadrant")
        if curr is not None and prev is not None and "quadrant" in curr:
            ev = detect_phase_flip(prev.get("quadrant"), curr.get("quadrant"))
            if ev:
                ev["event_type"] = "oi_flip"
                pending.append((sym, str(curr.get("_o") or as_of or ""), ev, ""))
    emitted["oi"] = _flush(conn, "oi", pending)

    # RS-band state flip (rsband_signals — INDEX-grain: index/sector numerators vs
    # the Nifty 500 benchmark; event symbol = the numerator name) ---------------
    pending = []
    try:
        nums = [r[0] for r in conn.execute(
            "SELECT DISTINCT numerator FROM rsband_signals WHERE denominator = ?",
            (_RS_BENCHMARK,)).fetchall()]
    except Exception:
        nums = []
    for num in nums:
        try:
            rows = conn.execute(
                "SELECT rs_band_state, trade_date FROM rsband_signals "
                "WHERE numerator = ? AND denominator = ? AND rs_band_state IS NOT NULL "
                "ORDER BY trade_date DESC LIMIT 2",
                (num, _RS_BENCHMARK)).fetchall()
        except Exception:
            rows = []
        if len(rows) == 2:
            curr, prev = dict(rows[0]), dict(rows[1])
            ev = detect_phase_flip(prev.get("rs_band_state"), curr.get("rs_band_state"))
            if ev:
                pending.append((num, str(curr.get("trade_date") or as_of or ""), ev,
                                f"{num}: RS-band state {ev['from_state']} → {ev['to_state']} "
                                f"vs {_RS_BENCHMARK}"))
    emitted["rs"] = _flush(conn, "rs", pending)

    # Deal print (bulk_block_deals — one event per symbol on the latest deal day;
    # magnitude = the symbol's total deal value PERCENTILE within that day's
    # printed symbols — relative, never a rupee-constant threshold) -------------
    pending = []
    try:
        row = conn.execute("SELECT MAX(trade_date) FROM bulk_block_deals").fetchone()
        deal_day = row[0] if row else None
    except Exception:
        deal_day = None
    if deal_day:
        try:
            aggs = [dict(r) for r in conn.execute(
                "SELECT symbol, COUNT(*) AS n, "
                "SUM(CASE WHEN side = 'BUY'  THEN COALESCE(qty, 0) * COALESCE(price, 0) "
                "         ELSE 0 END) AS buy_val, "
                "SUM(CASE WHEN side = 'SELL' THEN COALESCE(qty, 0) * COALESCE(price, 0) "
                "         ELSE 0 END) AS sell_val "
                "FROM bulk_block_deals WHERE trade_date = ? GROUP BY symbol",
                (deal_day,)).fetchall()]
        except Exception:
            aggs = []
        totals = sorted((r["buy_val"] or 0) + (r["sell_val"] or 0) for r in aggs)
        for r in aggs:
            total = (r["buy_val"] or 0) + (r["sell_val"] or 0)
            pct = (sum(1 for t in totals if t <= total) / len(totals)) if totals else 0.0
            net = (r["buy_val"] or 0) - (r["sell_val"] or 0)
            direction = "up" if net > 0 else ("down" if net < 0 else "flip")
            side_word = "net BUY" if net > 0 else ("net SELL" if net < 0 else "two-sided")
            ev = {"event_type": "deal_print", "direction": direction,
                  "from_state": None,
                  "to_state": f"{r['n']} print(s) ₹{total / 1e7:.1f}cr",
                  "magnitude": round(pct, 4)}
            pending.append((r["symbol"], str(deal_day), ev,
                            f"{r['symbol']}: {r['n']} bulk/block deal print(s) — "
                            f"₹{total / 1e7:.1f}cr {side_word}"))
    emitted["deal"] = _flush(conn, "deal", pending)

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
            result = run_detection(conn, as_of=args.asof)
            # Piggyback the alert-rail promotion (the bus's 4th face) onto the same nightly
            # --detect step so no systemd unit changes. Isolated + non-fatal: a failure here
            # never fails detection. run_detection stays pure (no alert coupling) for tests.
            # Promote a WINDOW of recent batches, not just MAX(as_of): the five lenses set as_of
            # from independent clocks (deal = last deal day, cci = filing day, mep/oi/rs = trade
            # date), so on a night when one feed lags, its events sit in an earlier batch that a
            # single-batch promote would skip forever. backfill is edge-triggered/idempotent.
            try:
                from src.automation.signal_alerts import backfill as _backfill_alerts
                alerts = _backfill_alerts(conn, batches=8)
            except Exception:  # noqa: BLE001
                log.exception("signal_alerts backfill failed (non-fatal)")
                alerts = {"promoted": "error"}
            log.info("done: %s | alert-rail: %s", result, alerts)
            # Optional OWNER-DM of NEW critical alerts. Ships DORMANT — only fires when
            # HERMES_ALERT_DM=1 is set on the box, so deploying the code never sends until it
            # is deliberately enabled. Isolated + non-fatal + fire-once (its own delivery
            # ledger); never fails detection. A PRIVATE owner DM (like the season / board-health
            # pagers), NOT the public approval-gated channel (that is S-F).
            import os as _os
            if _os.environ.get("HERMES_ALERT_DM") == "1":
                try:
                    from src.automation.signal_alert_telegram import push as _push_alerts
                    log.info("alert-DM: %s", _push_alerts(conn, as_of=args.asof))
                except Exception:  # noqa: BLE001
                    log.exception("alert DM push failed (non-fatal)")
        elif args.stats:
            import json
            print(json.dumps(stats(conn), indent=2))
        else:
            for e in events_since(conn, args.since, symbols=syms):
                print(f"  {e['as_of']}  {e['lens']:5} {e['event_type']:18} {e['note']}")


if __name__ == "__main__":
    main()
