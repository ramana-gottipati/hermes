"""CPR (Central Pivot Range) "STRUCTURE" pillar engine — D53.

The 4th Patearn strategy, beside Positioning (DVPT — D28/D31/D43/D44), Relative
Strength (RS — D32/D33) and Quality (pt14). Where those answer *who's buying*,
*what's leading*, *what's good*, CPR answers what none of them do: **where is
price in its multi-degree structure, has the structure just turned, and is it
coiled for a move?**

ONE primitive, three degrees. From the PRIOR completed period's High/Low/Close:

    P  (pivot) = (H + L + C) / 3
    BC         = (H + L) / 2
    TC         = 2P − BC
    width%     = (TC − BC) / P × 100         (÷ pivot — OPEN-4; the narrowness metric)

read identically at Daily / Weekly / Monthly — only the period changes. A small
family of models over that one primitive (design: docs/cpr-strategy-design.md):

  * 3A Reversal  — three consecutive CPRs forming a U (bullish bottom) or an
    inverted-U / ∩ (bearish top). Each leg must be a CLEAN DIRECTIONAL STEP
    (both band lines move the same way — OPEN-1) which simultaneously builds the
    pattern and excludes engulfing/inside cases. Strength = narrowness of the two
    recent bands (C0, C1) → an R1–R4 rank derived on read (C0 the priority bar —
    OPEN-2).
  * 3B Compression — an *unusually narrow* single CPR (coiled spring). Measured
    both by the absolute per-TF knob (D 1.0 / W 2.5 / M 5.0%) AND by the
    own-history percentile (the truer "unusual" — OPEN-7), stored here.
  * 3C Regime    — sign(close − P): the higher-TF trend context for amplification.
  * 3D Confluence + the cross-TF amplification / ★ conviction tier are DERIVED ON
    READ in the dashboard (they join the latest D/W/M rows; weights stay tunable).

Design decisions embodied here (canonical at build = D53; local CPR-* log):
  * CPR-A4  geometry + widths STORED, rank/score DERIVED ON READ (mirrors D43-G).
  * CPR-A5  ONE timeframe-parameterized engine; SELF-RESAMPLES its own lightweight
            adjusted H/L/C bars from bhavcopy_rows — NOT blocked on the held MTF
            bars_weekly/bars_monthly. `_period_key` is replicated (not imported)
            so CPR carries no dependency on the uncommitted MTF module.
  * CPR-A6  split/bonus-ADJUSTED OHLC (adjust.adjusted prices) + |return|>0.30
            anomaly drop (D36) + equity-only allowlist (D42) — the band and the
            close it is compared against share one continuous price regime.
  * CPR-A7  freshness (`days_since_pattern`; 0 = formed this bar) — state-vs-event.

The daily engine in signals.py and the held mtf_signals.py are SIBLINGS, left
untouched. This module reads bhavcopy_rows + nse_equity_list and writes ONLY
cpr_signals. All re-derivable from the raw archive (Doctrine § C).
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from typing import Optional

from src.automation.adjust import adjustment_factors
from src.core.db import get_conn

log = logging.getLogger("hermes.cpr_signals")


# --- Timeframe parameterization --------------------------------------------
# Per-TF: the absolute narrowness default (OPEN-5; the rank/screen knob is
# applied ON READ, this is only metadata/echo), the own-history percentile
# window N (§5.2), and the minimum trading days a PRIOR period must have for its
# CPR to be trustworthy (thin-bar guard, §10).
_TF = {
    "D": {"label": "daily",   "key": "day",   "max_width_pct": 1.0, "pctile_n": 252, "min_days": 1},
    "W": {"label": "weekly",  "key": "week",  "max_width_pct": 2.5, "pctile_n": 52,  "min_days": 2},
    "M": {"label": "monthly", "key": "month", "max_width_pct": 5.0, "pctile_n": 24,  "min_days": 3},
    # Half-yearly (H1 = Jan–Jun, H2 = Jul–Dec) — the higher-degree CPR shown on the
    # MONTHLY chart (Ramana's ladder: daily→weekly, weekly→monthly, monthly→half-yearly).
    "H": {"label": "half-yearly", "key": "half", "max_width_pct": 8.0, "pctile_n": 12, "min_days": 20},
}

_ANOMALY_RET = 0.30   # |adjusted daily return| > 30% = a data anomaly to drop from H/L/C (D36)

_STORE_COLS = [
    "symbol", "period_end_date", "timeframe",
    "p", "bc", "tc", "width_pct", "c1_width_pct", "c2_width_pct",
    "compression_pctile", "pattern", "leg_in_clean", "leg_turn_clean",
    "separation_pct", "depth_pct", "regime", "days_since_pattern", "confirmed",
    "close", "adj_used", "is_partial", "n_bars_used",
]


# --- Period bucketing (replicated from mtf_signals — see CPR-A5) ------------

def _period_key(tf: str, trade_date: str):
    """Bucket key for a daily date. Daily → the date itself (each day its own
    CPR period); Weekly → (iso_year, iso_week); Monthly → 'YYYY-MM'. Keyed so the
    bar lands on the period's LAST trading day. Mirrors mtf_signals._period_key
    (W/M) but is replicated to keep CPR decoupled from the held MTF module."""
    if tf == "D":
        return trade_date
    if tf == "W":
        y, w, _ = datetime.strptime(trade_date, "%Y-%m-%d").isocalendar()
        return (y, w)
    if tf == "H":
        m = int(trade_date[5:7])
        return trade_date[:4] + ("-H1" if m <= 6 else "-H2")
    return trade_date[:7]   # monthly


# --- Resampling to lightweight adjusted H/L/C period bars -------------------

def _fetch_daily(conn, symbol: str) -> list:
    """All EQ daily rows for a symbol, OLDEST → NEWEST (only the fields a CPR
    needs: H/L/C + prev_close for split detection + value for a liquidity echo)."""
    return conn.execute(
        """
        SELECT trade_date, high, low, close, prev_close, value
        FROM bhavcopy_rows
        WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
        ORDER BY trade_date ASC
        """,
        (symbol,),
    ).fetchall()


def resample(tf: str, daily_rows: list, partial_key) -> list[dict]:
    """Resample OLDEST→NEWEST daily rows into timeframe period bars (oldest→newest),
    each carrying SPLIT-ADJUSTED H/L/C. A CPR only needs prior-period H/L/C, so
    this is far lighter than the MTF delivery bar (CPR-A5 / design §9).

    Split-safety (CPR-A6): adjustment factors are computed on the FULL daily
    series (corp-action detection needs the daily prev_close walk), then applied
    per day to H/L/C so the whole series sits in one continuous price regime;
    each bar aggregates adj_high=max, adj_low=min, adj_close=last over its days.
    Days whose ADJUSTED daily return exceeds ±30% (a residual data anomaly after
    corp-action adjustment — D36) are dropped from the H/L/C aggregation.
    """
    if not daily_rows:
        return []

    # Per-day cumulative back-adjustment factor (newest anchored at 1.0).
    factors = adjustment_factors([
        {"close": r["close"], "prev_close": r["prev_close"]} for r in daily_rows
    ])

    # Adjusted per-day H/L/C + anomaly flag (on the adjusted close-to-close move).
    adj_days = []
    prev_adj_c = None
    for r, f in zip(daily_rows, factors):
        c = r["close"]
        ac = (c * f) if c is not None else None
        ah = (r["high"] * f) if r["high"] is not None else None
        al = (r["low"] * f) if r["low"] is not None else None
        anomalous = False
        if ac is not None and prev_adj_c is not None and prev_adj_c > 0:
            if abs(ac / prev_adj_c - 1.0) > _ANOMALY_RET:
                anomalous = True
        adj_days.append({
            "trade_date": r["trade_date"], "raw_close": c,
            "ah": ah, "al": al, "ac": ac, "value": r["value"], "anom": anomalous,
        })
        if ac is not None:
            prev_adj_c = ac

    # Group consecutive days into period buckets (rows sorted ascending).
    buckets: list[tuple] = []
    cur_key, cur = None, []
    for d in adj_days:
        k = _period_key(tf, d["trade_date"])
        if k != cur_key:
            if cur:
                buckets.append((cur_key, cur))
            cur_key, cur = k, []
        cur.append(d)
    if cur:
        buckets.append((cur_key, cur))

    bars: list[dict] = []
    for key, days in buckets:
        # H/L/C aggregation EXCLUDES anomalous days; the close is the last
        # non-anomalous day's adjusted close (raw_close kept for display).
        good = [d for d in days if not d["anom"]]
        src = good if good else days   # all-anomalous (degenerate) → fall back
        highs = [d["ah"] for d in src if d["ah"] is not None]
        lows = [d["al"] for d in src if d["al"] is not None]
        closes = [(d["ac"], d["raw_close"]) for d in src if d["ac"] is not None]
        if not (highs and lows and closes):
            continue
        last = src[-1]
        bars.append({
            "period_end_date": last["trade_date"],
            "adj_high": max(highs),
            "adj_low": min(lows),
            "adj_close": closes[-1][0],
            "raw_close": closes[-1][1],
            "turnover": sum(d["value"] for d in src if d["value"] is not None) or None,
            "n_days": len(src),
            "is_partial": 1 if (partial_key is not None and key == partial_key) else 0,
        })
    return bars


# --- CPR primitive + pattern detection --------------------------------------

def _cpr_from(h, l, c) -> Optional[dict]:
    """The 3-line CPR built from a prior period's adjusted H/L/C. width% ÷ pivot."""
    if h is None or l is None or c is None:
        return None
    p = (h + l + c) / 3.0
    if p <= 0:
        return None
    bc = (h + l) / 2.0
    tc = 2.0 * p - bc
    lo, hi = (bc, tc) if tc >= bc else (tc, bc)
    return {"p": p, "bc": lo, "tc": hi, "width_pct": (hi - lo) / p * 100.0}


def _clean_step(x: dict, y: dict) -> Optional[str]:
    """Direction of a clean step from band X to the more-recent band Y, or None.
    Clean = BOTH lines move the same way (OPEN-1) — this single rule excludes
    engulfing (TC up while BC down) and inside (TC down while BC up)."""
    if y["tc"] > x["tc"] and y["bc"] > x["bc"]:
        return "up"
    if y["tc"] < x["tc"] and y["bc"] < x["bc"]:
        return "down"
    return None


def compute_signals(tf: str, symbol: str, bars: list[dict]) -> list[dict]:
    """Walk the oldest→newest period-bar series, emitting one cpr_signals row per
    bar. The CPR plotted ON bar i (C0) is built from bar i-1's H/L/C; C1 = the
    CPR on bar i-1 (from i-2), C2 = the CPR on bar i-2 (from i-3)."""
    spec = _TF[tf]
    n_pctile = spec["pctile_n"]
    min_days = spec["min_days"]

    # cpr[i] = the CPR plotted on bar i (built from bar i-1). None for i==0 and
    # for bars whose PRIOR period was too thin to trust (thin-bar guard, §10).
    cpr: list[Optional[dict]] = [None] * len(bars)
    for i in range(1, len(bars)):
        prev = bars[i - 1]
        if prev["n_days"] < min_days:
            continue
        cpr[i] = _cpr_from(prev["adj_high"], prev["adj_low"], prev["adj_close"])

    widths = [(cpr[i]["width_pct"] if cpr[i] else None) for i in range(len(bars))]

    out: list[dict] = []
    prev_pattern, run_len = None, 0
    for i, b in enumerate(bars):
        c0 = cpr[i]
        c1 = cpr[i - 1] if i - 1 >= 0 else None
        c2 = cpr[i - 2] if i - 2 >= 0 else None
        adj_close = b["adj_close"]

        pattern = "NONE"
        leg_in_clean = leg_turn_clean = None
        separation_pct = depth_pct = None
        if c0 and c1 and c2:
            in_step = _clean_step(c2, c1)     # the lead-in leg C2→C1
            turn_step = _clean_step(c1, c0)   # the turn leg C1→C0
            leg_in_clean = 1 if in_step else 0
            leg_turn_clean = 1 if turn_step else 0
            if in_step == "down" and turn_step == "up":
                pattern = "BULL_U"            # valley at C1, turning up
            elif in_step == "up" and turn_step == "down":
                pattern = "BEAR_INVU"         # peak at C1, turning down
            if pattern != "NONE":
                # depth = how far the valley/peak C1 over-ran the lead-in C2.
                if c2["p"] > 0:
                    depth_pct = abs(c1["p"] - c2["p"]) / c2["p"] * 100.0
                # separation = full non-overlap on the TURN leg (signed by dir).
                denom = c1["p"] if c1["p"] else None
                if denom:
                    if pattern == "BULL_U":
                        separation_pct = (c0["bc"] - c1["tc"]) / denom * 100.0
                    else:
                        separation_pct = (c1["bc"] - c0["tc"]) / denom * 100.0

        # regime — sign(close − P), both on the continuous adjusted scale.
        regime = None
        if c0 and adj_close is not None:
            regime = 1 if adj_close > c0["p"] else (-1 if adj_close < c0["p"] else 0)

        # confirmed — price has actually engaged the turning band.
        # CL-RS-03: an in-progress (is_partial) W/M period's close is not final, so a
        # "confirmed" verdict computed against it can still flip before the period
        # closes. Mirror MTF: never mark a partial row confirmed — it stays an
        # unconfirmed, descriptive read until the period locks.
        confirmed = 0
        if c0 and adj_close is not None and not b["is_partial"]:
            if pattern == "BULL_U" and adj_close > c0["tc"]:
                confirmed = 1
            elif pattern == "BEAR_INVU" and adj_close < c0["bc"]:
                confirmed = 1

        # days_since_pattern — bars since this exact pattern first appeared
        # (0 = fresh this bar; NULL when no pattern). State-vs-event (CPR-A7).
        if pattern == "NONE":
            days_since = None
            prev_pattern, run_len = None, 0
        else:
            if pattern == prev_pattern:
                run_len += 1
            else:
                run_len = 0
            days_since = run_len
            prev_pattern = pattern

        # compression percentile — fraction of the trailing N CPR widths that are
        # WIDER than the current one (high = unusually coiled FOR THIS STOCK §5.2).
        comp_pctile = None
        if c0 is not None:
            lo = max(0, i - n_pctile)
            hist = [w for w in widths[lo:i] if w is not None]
            if len(hist) >= 10:
                wider = sum(1 for w in hist if w > c0["width_pct"])
                comp_pctile = wider / len(hist)

        out.append({
            "symbol": symbol,
            "period_end_date": b["period_end_date"],
            "timeframe": tf,
            "p": (c0["p"] if c0 else None),
            "bc": (c0["bc"] if c0 else None),
            "tc": (c0["tc"] if c0 else None),
            "width_pct": (c0["width_pct"] if c0 else None),
            "c1_width_pct": (c1["width_pct"] if c1 else None),
            "c2_width_pct": (c2["width_pct"] if c2 else None),
            "compression_pctile": comp_pctile,
            "pattern": pattern,
            "leg_in_clean": leg_in_clean,
            "leg_turn_clean": leg_turn_clean,
            "separation_pct": separation_pct,
            "depth_pct": depth_pct,
            "regime": regime,
            "days_since_pattern": days_since,
            "confirmed": confirmed,
            "close": b["raw_close"],
            "adj_used": 1,
            "is_partial": b["is_partial"],
            "n_bars_used": i,
        })
    return out


# --- Storage ----------------------------------------------------------------

def _store(conn, rows: list[dict], only_last: Optional[int] = None) -> None:
    """Upsert cpr rows. If only_last is set, store just the last N (the nightly
    incremental path — earlier bars are unchanged)."""
    r = rows[-only_last:] if only_last else rows
    if not r:
        return
    conn.executemany(
        f"INSERT OR REPLACE INTO cpr_signals ({','.join(_STORE_COLS)}) "
        f"VALUES ({','.join('?' * len(_STORE_COLS))})",
        [[row.get(c) for c in _STORE_COLS] for row in r],
    )


def _partial_key(conn, tf: str):
    """Period key of the market's most recent trading session (the open period).
    Daily bars are EOD-complete, so D has no partial concept (returns None); only
    Weekly/Monthly carry a current, not-yet-closed period."""
    if tf == "D":
        return None
    row = conn.execute("SELECT MAX(trade_date) AS d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return None
    return _period_key(tf, row["d"])


def _all_symbols(conn) -> list[str]:
    """Equity universe, oldest convention: equity-only allowlist when populated
    (D42 guard), else all EQ symbols (robust on a fresh/empty DB)."""
    has_list = conn.execute("SELECT 1 FROM nse_equity_list LIMIT 1").fetchone()
    if has_list:
        return [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT b.symbol FROM bhavcopy_rows b
               WHERE b.series = 'EQ' AND (b.segment = 'CM' OR b.segment IS NULL)
                 AND b.symbol IN (SELECT symbol FROM nse_equity_list)
               ORDER BY b.symbol""").fetchall()]
    return [r["symbol"] for r in conn.execute(
        """SELECT DISTINCT symbol FROM bhavcopy_rows
           WHERE series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY symbol""").fetchall()]


def process_symbol(conn, tf: str, symbol: str, partial_key,
                   only_last: Optional[int] = None) -> int:
    """Resample + compute + store one symbol for one timeframe. Returns #rows."""
    daily = _fetch_daily(conn, symbol)
    if not daily:
        return 0
    bars = resample(tf, daily, partial_key)
    if not bars:
        return 0
    signals = compute_signals(tf, symbol, bars)
    _store(conn, signals, only_last=only_last)
    return len(signals)


# --- Modes ------------------------------------------------------------------

def run_backfill(tf: str) -> tuple[int, int]:
    """Full (re)materialization of every symbol for one timeframe."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        symbols = _all_symbols(conn)
        log.info("%s CPR backfill: %d symbols", _TF[tf]["label"], len(symbols))
        nrows = 0
        for i, sym in enumerate(symbols, 1):
            nrows += process_symbol(conn, tf, sym, partial_key)
            if i % 200 == 0:
                log.info("  progress: %d / %d symbols (%d rows)", i, len(symbols), nrows)
                conn.commit()
                time.sleep(0.02)   # let dashboard reads through (WAL)
        conn.commit()
    log.info("%s CPR backfill done: %d symbols, %d rows", _TF[tf]["label"], len(symbols), nrows)
    return len(symbols), nrows


def run_recent(tf: str, only_last: int = 3) -> tuple[int, int]:
    """Nightly incremental — recompute only the latest `only_last` bars per
    symbol (the current partial bar + the one(s) that may have just closed). The
    full series is still resampled so compression percentiles + days_since stay
    correct, but only the tail is written."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        symbols = _all_symbols(conn)
        log.info("%s CPR recent(%d): %d symbols", _TF[tf]["label"], only_last, len(symbols))
        n = 0
        for i, sym in enumerate(symbols, 1):
            if process_symbol(conn, tf, sym, partial_key, only_last=only_last):
                n += 1
            if i % 400 == 0:
                conn.commit()
        conn.commit()
    log.info("%s CPR recent done: %d symbols updated", _TF[tf]["label"], n)
    return len(symbols), n


def run_symbol(tf: str, symbol: str) -> int:
    """One symbol, full series — for spot-checking."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        n = process_symbol(conn, tf, symbol, partial_key)
        conn.commit()
    log.info("%s CPR %s: %d rows", _TF[tf]["label"], symbol, n)
    return n


def _timeframes(arg: str) -> list[str]:
    if arg in ("D", "W", "M", "H"):
        return [arg]
    return ["D", "W", "M", "H"]   # 'all' / default


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    p = argparse.ArgumentParser(description="CPR (Central Pivot Range) multi-timeframe structure engine")
    p.add_argument("--timeframe", choices=["D", "W", "M", "H", "all"], default="all")
    p.add_argument("--backfill", action="store_true",
                   help="full (re)materialization of all symbols")
    p.add_argument("--recent", action="store_true",
                   help="nightly incremental — recompute only the latest bars")
    p.add_argument("--only-last", type=int, default=3,
                   help="how many trailing bars --recent rewrites (default 3)")
    p.add_argument("--symbol", type=str, help="process a single symbol (full series)")
    args = p.parse_args()

    tfs = _timeframes(args.timeframe)
    if args.symbol:
        for tf in tfs:
            run_symbol(tf, args.symbol)
    elif args.backfill:
        for tf in tfs:
            run_backfill(tf)
    elif args.recent:
        for tf in tfs:
            run_recent(tf, only_last=args.only_last)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
