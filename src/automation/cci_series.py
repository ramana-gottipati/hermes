"""CCI credibility SERIES (Phase 2) — credibility as a point-in-time time series,
not a static snapshot. For each symbol, at each concall period T it computes the
credibility composite using ONLY what was knowable by T (promises resolved by T,
quantification of promises made by T, deterioration flags seen by T — no
look-ahead), then derives MOMENTUM (level vs the prior period) and a TAPE event
(EARNING_TRUST when trust is being earned, DETERIORATION when it's eroding).

This is the spine of the credibility-as-a-price idea: a level that MOVES, a slope
that says improving/eroding, and the symmetric tapes (the deterioration AVOID tape
already existed; this adds its positive mirror). It feeds Phase 3 (the
credibility-RRG = level × momentum, and the credibility÷price divergence screen).

MEASURABLE-ONLY (D61), same as the snapshot scorer: it REUSES that scorer's exact
constants + formula (W_GA/W_QR/UNPROVEN_CEILING/DETER_PEN_PER/_tier/_clamp) so the
series and the snapshot never diverge. The forensic veto is a CURRENT fundamentals
gate (pledge/auditor-exit), not historically reconstructable, so it is NOT applied
to the historical series — it stays on the live snapshot in concall_scores.

Deep settlement (cci_deep_actuals → concall_settle) is what gives this series real
history: promises graded back to ~2017 against the 24-yr fundamentals_history.

CLI:
    python -m src.automation.cci_series --all
    python -m src.automation.cci_series --symbol CGPOWER --show
    python -m src.automation.cci_series --tape         # latest movers (earning-trust / deterioration)
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import date
from typing import Optional

from src.core.db import get_conn
from src.automation.cci_normalize import classify_commitment
from src.automation.concall_scores import (
    W_GA, W_QR, UNPROVEN_CEILING, DETER_PEN_PER, RECENT_PERIODS,
    _DETERMINISTIC_FLAGS, _tier, _clamp, _order_map,
)

log = logging.getLogger("hermes.cci_series")

MOM_TREND = 3.0      # |momentum| >= this → IMPROVING / DETERIORATING (else STABLE)
MOM_EVENT = 5.0      # |momentum| >= this → a tape event even without a discrete trigger

_SCHEMA = """
CREATE TABLE IF NOT EXISTS credibility_series (
    symbol        TEXT NOT NULL,
    period_label  TEXT NOT NULL,        -- the concall period T this point is as-of
    period_year   INTEGER,
    period_month  INTEGER,
    level         REAL,                 -- credibility composite AS OF T (PIT, 0-100)
    ga            REAL,                 -- guidance accuracy as of T (NULL until promises resolve)
    qr            REAL,                 -- quantification rate as of T
    n_resolved    INTEGER,              -- promises resolved (graded) by T
    deter         INTEGER,              -- deterministic deterioration flags in the recent window
    momentum      REAL,                 -- level(T) - level(prev period)
    momentum_3p   REAL,                 -- level(T) - level(3 periods earlier)
    trend         TEXT,                 -- IMPROVING | STABLE | DETERIORATING
    tape          TEXT,                 -- EARNING_TRUST | DETERIORATION | NULL
    tape_note     TEXT,
    tier          TEXT,
    computed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, period_label)
);
CREATE INDEX IF NOT EXISTS idx_cred_series_sym  ON credibility_series(symbol, period_year, period_month);
CREATE INDEX IF NOT EXISTS idx_cred_series_tape ON credibility_series(tape, period_year, period_month);
"""

_RESOLVED = ("MET", "MISSED", "PARTIAL")
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def _ym(period: Optional[str]):
    """A resolved_period → (year, month). Handles the deep-actuals ISO date
    'YYYY-MM-DD' and Screener's 'Mon YYYY'. None if unparseable."""
    if not period:
        return None
    s = str(period).strip()
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", s)
    if m:
        return _bounded(int(m.group(1)), int(m.group(2)))
    m = re.match(r"([A-Za-z]{3,})\s+(\d{4})", s)
    if m and m.group(1)[:3].lower() in _MONTHS:
        return _bounded(int(m.group(2)), _MONTHS[m.group(1)[:3].lower()])
    return None


def _bounded(year: int, month: int):
    """Reject calendar-implausible (year, month) — e.g. the corrupt concalls label 'Aug 0225'
    (year 225). Keeps a malformed source row from minting a credibility point."""
    if 2000 <= year <= date.today().year + 1 and 1 <= month <= 12:
        return (year, month)
    return None


# --- the per-symbol series build --------------------------------------------

def build_series(conn, symbol: str) -> int:
    """(Re)compute the full PIT credibility series for one symbol. Returns #points."""
    ensure_schema(conn)
    order = _order_map(conn, symbol)                       # period_label -> (year, month)
    if not order:
        return 0
    guid = conn.execute(
        "SELECT source_period, status, resolved_period, claim_text FROM concall_guidance WHERE symbol=?",
        (symbol,)).fetchall()
    flags = conn.execute(
        "SELECT period_label, flag_type FROM concall_redflags WHERE symbol=? AND flag_type IN (%s)"
        % ",".join("?" * len(_DETERMINISTIC_FLAGS)), (symbol, *_DETERMINISTIC_FLAGS)).fetchall()

    # pre-compute each promise's (made_ym, resolved_ym, quantified?, status)
    promises = []
    for g in guid:
        promises.append({
            "made": order.get(g["source_period"]),
            "res": _ym(g["resolved_period"]) if g["status"] in _RESOLVED else None,
            "status": g["status"],
            "quant": classify_commitment(g["claim_text"]) in ("HARD", "SOFT"),
        })
    flags_by_period = {}
    for f in flags:
        flags_by_period.setdefault(f["period_label"], 0)
        flags_by_period[f["period_label"]] += 1

    periods = sorted(order.items(), key=lambda kv: kv[1])   # [(label, (y,m)), ...] chronological
    # drop corrupt source periods (e.g. concalls 'Aug 0225' → year 225) so credibility_series can
    # never carry an out-of-range period_year — the data_quality monitor still flags the source row.
    _ymax = date.today().year + 1
    periods = [(lbl, ym) for (lbl, ym) in periods
               if ym and 2000 <= ym[0] <= _ymax and 1 <= ym[1] <= 12]
    conn.execute("DELETE FROM credibility_series WHERE symbol=?", (symbol,))

    levels: list[float] = []
    prev_ym = None
    n = 0
    for i, (T, tym) in enumerate(periods):
        # promises RESOLVED by T (no look-ahead); and which became known SINCE the prior period
        met = missed = partial = 0
        new_met = new_missed = 0
        for p in promises:
            if p["res"] and p["res"] <= tym:
                if p["status"] == "MET":
                    met += 1
                elif p["status"] == "MISSED":
                    missed += 1
                else:
                    partial += 1
                if prev_ym is None or p["res"] > prev_ym:    # newly graded in this period's window
                    if p["status"] == "MET":
                        new_met += 1
                    elif p["status"] == "MISSED":
                        new_missed += 1
        resolved = met + missed + partial
        ga = (100.0 * (met + 0.5 * partial) / resolved) if resolved else None

        made = [p for p in promises if p["made"] and p["made"] <= tym]
        qr = round(100.0 * sum(1 for p in made if p["quant"]) / len(made), 1) if made else 0.0

        window = {lbl for lbl, _ in periods[max(0, i - RECENT_PERIODS + 1): i + 1]}
        deter = sum(c for lbl, c in flags_by_period.items() if lbl in window)
        rf_at_T = flags_by_period.get(T, 0)

        base = (W_GA * ga + W_QR * qr) if ga is not None else qr
        level = _clamp(base - DETER_PEN_PER * deter)
        if ga is None:
            level = min(level, UNPROVEN_CEILING)

        momentum = round(level - levels[-1], 1) if levels else None
        momentum_3p = round(level - levels[-4], 1) if len(levels) >= 4 else None
        trend = ("IMPROVING" if (momentum or 0) >= MOM_TREND else
                 "DETERIORATING" if (momentum or 0) <= -MOM_TREND else "STABLE") if momentum is not None else "NEW"

        # tape: trust being earned vs eroded, from this period's flow + slope. A
        # momentum-ONLY event needs a real (settled) track record — `proven` — so the
        # unproven-phase level jump (0→qr when guidance first appears) doesn't fire a
        # spurious tape; settlement (new_met/new_missed) and disclosure flags always count.
        tape = tape_note = None
        proven = ga is not None
        mom_down = proven and momentum is not None and momentum <= -MOM_EVENT
        mom_up = proven and momentum is not None and momentum >= MOM_EVENT
        if rf_at_T or new_missed > new_met or mom_down:
            tape = "DETERIORATION"
            bits = []
            if rf_at_T:
                bits.append(f"{rf_at_T} disclosure flag(s)")
            if new_missed:
                bits.append(f"{new_missed} promise(s) missed")
            if mom_down:
                bits.append(f"level {momentum:+.0f}")
            tape_note = "; ".join(bits)
        elif new_met and new_missed == 0 and (momentum is None or momentum >= 0):
            tape = "EARNING_TRUST"
            tape_note = f"{new_met} promise(s) met" + (f"; level +{momentum:.0f}" if momentum else "")
        elif mom_up:
            tape = "EARNING_TRUST"
            tape_note = f"level +{momentum:.0f}"

        conn.execute(
            "INSERT INTO credibility_series (symbol, period_label, period_year, period_month, level, ga, qr, "
            "n_resolved, deter, momentum, momentum_3p, trend, tape, tape_note, tier, computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
            (symbol, T, tym[0], tym[1], round(level, 1), round(ga, 1) if ga is not None else None, qr,
             resolved, deter, momentum, momentum_3p, trend, tape, tape_note, _tier(level)))
        levels.append(level)
        prev_ym = tym
        n += 1
    return n


def run(symbol: Optional[str] = None) -> int:
    with get_conn() as conn:
        ensure_schema(conn)
        syms = [symbol.upper()] if symbol else [
            r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM concall_guidance").fetchall()]
        total = sum(build_series(conn, s) for s in syms)
        conn.commit()
    log.info("credibility series: %d points across %d symbols", total, len(syms))
    return total


# --- read helpers (Phase 3 + the dossier consume these) ---------------------

def series_for(conn, symbol: str) -> list[dict]:
    ensure_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT * FROM credibility_series WHERE symbol=? ORDER BY period_year, period_month",
        (symbol.upper().strip(),)).fetchall()]


def latest_tape(conn, kind: str = "DETERIORATION", limit: int = 20) -> list[dict]:
    """The most recent tape events of a kind (the avoid tape / the earning-trust tape)."""
    ensure_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT symbol, period_label, level, momentum, tape_note FROM credibility_series "
        "WHERE tape=? ORDER BY period_year DESC, period_month DESC LIMIT ?", (kind, limit)).fetchall()]


# --- CLI --------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="CCI credibility series (PIT level + momentum + tape)")
    ap.add_argument("--all", action="store_true", help="(re)build the series for every symbol")
    ap.add_argument("--symbol", help="(re)build / inspect one symbol")
    ap.add_argument("--show", action="store_true", help="print the series for --symbol")
    ap.add_argument("--tape", choices=["EARNING_TRUST", "DETERIORATION"], help="print latest tape events")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.all or (args.symbol and not args.show and not args.tape):
        print(f"built {run(args.symbol if args.symbol else None)} series points")
    if args.symbol and args.show:
        with get_conn() as conn:
            for r in series_for(conn, args.symbol):
                tp = f"  <{r['tape']}: {r['tape_note']}>" if r["tape"] else ""
                mom = f"{r['momentum']:+.0f}" if r["momentum"] is not None else "  ·"
                print(f"  {r['period_label']:9} level={r['level']:5.1f} ({r['tier']})  mom={mom:>5}  "
                      f"ga={r['ga'] if r['ga'] is not None else '--':>4}  res={r['n_resolved']:<3} {r['trend']:<13}{tp}")
    if args.tape:
        with get_conn() as conn:
            for r in latest_tape(conn, args.tape):
                print(f"  {r['symbol']:12} {r['period_label']:9} level={r['level']:5.1f}  "
                      f"mom={r['momentum']}  {r['tape_note']}")


if __name__ == "__main__":
    main()
