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
from calendar import monthrange
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
    from src.core.db import _ensure_column
    _ensure_column(conn, "concall_guidance", "resolved_knowable_date", "TEXT")   # D6-F2 (idempotent)
    order = _order_map(conn, symbol)                       # period_label -> (year, month)
    if not order:
        return 0
    guid = conn.execute(
        "SELECT source_period, status, resolved_period, resolved_knowable_date, claim_text "
        "FROM concall_guidance WHERE symbol=?",
        (symbol,)).fetchall()
    flags = conn.execute(
        "SELECT period_label, flag_type FROM concall_redflags WHERE symbol=? AND flag_type IN (%s)"
        % ",".join("?" * len(_DETERMINISTIC_FLAGS)), (symbol, *_DETERMINISTIC_FLAGS)).fetchall()

    # pre-compute each promise's (made_ym, resolved_ym, quantified?, status)
    promises = []
    for g in guid:
        promises.append({
            "made": order.get(g["source_period"]),
            # D6-F2: gate on the actual's PUBLIC/knowable date when we have it (deep-actuals path);
            # else fall back to the period-end (legacy, Screener concall_results path).
            "res": _ym(g["resolved_knowable_date"] or g["resolved_period"]) if g["status"] in _RESOLVED else None,
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
    n = 0
    for i, (T, tym) in enumerate(periods):
        # promises RESOLVED by T (no look-ahead); and which became known SINCE the prior period.
        # "Newly graded" is counted once per promise — at the FIRST series point where it is
        # resolved — tracked by a per-promise `graded` flag rather than a `res > prev_concall_ym`
        # window. The old window mis-timed irregular cadence: a >1-quarter filing gap collapsed
        # (a promise resolved two periods back re-counted as new) and a sub-quarter cadence could
        # miss the boundary (res == prev_ym excluded by the strict `>`). (CL-CCI-06)
        # D6-F2 (Track C) FIXED: `p["res"]` now derives from the resolving actual's PUBLIC/knowable
        # date (`resolved_knowable_date`, set on settlement from fundamentals_history.report_date)
        # when available, so `p["res"] <= tym` gates on WHEN the actual became public — not the
        # period-end (which was ~1-2 months too early). Where the knowable date is absent (the
        # Screener concall_results path has no report date), it falls back to the period-end
        # (legacy). Activation needs a VPS re-settle + credibility_series rebuild to populate the
        # new column on already-settled rows. No live conclusion moves (CCI is descriptive-only /
        # falsified). (docs/codex-review/TRACK-C-RESULTS.md §D6-F2)
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
                if not p.get("graded"):                      # first period this promise is resolved
                    p["graded"] = True
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


def _real_clock_map(conn, symbol: str) -> dict:
    """period_label -> ISO date the period's CALL content became public (D104 EVENT tier).

    Uses max(concall_dt, transcript_publish_dt) per filing — the LATER real clock is the
    stricter availability bound — and max again across duplicate filings. 16k+ concalls
    rows carry a real clock (the S84 BSE calibration), so "the intra-month date is not
    stored" no longer holds; when it IS stored, serve it. ``result_filing_dt`` is
    deliberately NOT a knowable clock: filings usually PRECEDE the call, so using them
    would claim call-derived content knowable too early (the leak direction).
    Unparseable clocks are skipped; an absent concalls table (stub DBs) returns {} and
    callers fall back to the month-end rule."""
    out: dict = {}
    try:
        rows = conn.execute(
            "SELECT period_label, concall_dt, transcript_publish_dt FROM concalls "
            "WHERE symbol=? AND (concall_dt IS NOT NULL OR transcript_publish_dt IS NOT NULL)",
            (symbol,)).fetchall()
    except Exception:  # noqa: BLE001 — no concalls table here: month-end fallback everywhere
        return out
    for r in rows:
        real = []
        for c in (r["concall_dt"], r["transcript_publish_dt"]):
            s = str(c or "").strip()[:10]
            if len(s) == 10:
                try:
                    date.fromisoformat(s)
                except ValueError:
                    continue
                real.append(s)
        if real:
            best = max(real)
            if best > out.get(r["period_label"], ""):
                out[r["period_label"]] = best
    return out


def series_asof(conn, symbol: str, as_of: str) -> Optional[dict]:
    """The newest credibility point KNOWABLE on `as_of` (AUD-38 PIT serve), or None.

    Knowable-date rule (D104, two tiers, both no-look-ahead):
      * EVENT — when the period's REAL public clock is captured (concalls.concall_dt /
        transcript_publish_dt), the row is knowable from max(call, transcript) of that
        period. Real clocks can PRECEDE the label month (live case: an ICICIPRULI
        'Feb 2019' point whose call was held 2019-01-22), so every row's own clock is
        checked and the newest qualifying PERIOD wins — never a label-order shortcut.
      * MODELED — with no captured clock, the row is knowable from the LAST calendar
        day of its period month: a query dated mid-month excludes that month's row
        rather than risk serving a point from a call that hadn't happened yet.
    Rows with no period_year/month cannot be dated and are excluded from PIT serves.
    The chosen row is returned with `knowable_from` (ISO date) + `knowable_basis`
    (EVENT | MODELED — provenance.py's basis vocabulary) stamped.
    """
    try:
        target = date.fromisoformat(str(as_of).strip()[:10])
    except ValueError:
        return None
    real = _real_clock_map(conn, symbol.upper().strip())
    best: Optional[dict] = None
    for r in series_for(conn, symbol):          # ordered oldest -> newest
        clock = real.get(r.get("period_label"))
        if clock:
            knowable, basis = date.fromisoformat(clock), "EVENT"
        else:
            y, m = r.get("period_year"), r.get("period_month")
            if not y or not m:
                continue
            knowable, basis = date(int(y), int(m), monthrange(int(y), int(m))[1]), "MODELED"
        if knowable <= target:
            best = dict(r)
            best["knowable_from"] = knowable.isoformat()
            best["knowable_basis"] = basis
    return best


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
