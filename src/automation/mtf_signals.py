"""Multi-timeframe (MTF) signal engine — D52 foundation.

Resamples the raw daily `bhavcopy_rows` archive into TRUE weekly and monthly
OHLC + delivery bars (`bars_weekly` / `bars_monthly`), then runs the D28/D31
two-tier DVPT trigger scheme ON THOSE BARS to produce `weekly_signals` /
`monthly_signals`. The point is multi-timeframe ALIGNMENT (daily + weekly +
monthly agreeing = high conviction), not a bigger score.

Design: docs/multi-timeframe-positioning-design.md (labelled D42/D43 there,
predating the now-shipped D42 equity-allowlist / D43 character — this build is
D52). Key rules it locks:

  * D43-B  period DVPT = SUM(delivery value) / SUM(num_trades) over the bar,
           NEVER the average of daily DVPTs (ratio-of-sums != mean-of-ratios;
           averaging dilutes the big institutional days).
  * D43-A  resample to true calendar bars (week-ending / month-end), keyed on
           the period's LAST trading day.
  * D43-D  ONE timeframe-parameterized engine for W and M (DRY); the daily
           engine in signals.py is the sibling and is left untouched.
  * D43-G  baselines & top-N scale per timeframe (windows below), raw stored,
           score derived -> re-tuning needs no re-aggregation.
  * D43-H  adjusted closes for DIRECTION (stored on the bar for the later
           character phase); delivery VALUE (value-based, split-invariant) for
           magnitude, so summing components across a bar is safe.
  * D43-I  flag the partial current bar (`is_partial`) so week/month-to-date is
           never read as a closed signal.

DRY: the pure scoring helpers (_count_beaten / _rank_from_p_score /
_next_p_above) and the corp-action `adjusted_closes` are IMPORTED, not copied.

NOT in this foundation (deferred, see the design doc Phasing section): the
three-axis accumulation/distribution CHARACTER on the bars (rides on this same
engine later), the dashboard / Telegram surfacing, weekly/monthly RS. This
module ships the bars + the DVPT/baseline/score/rank/near-break/ATH layer only.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from typing import Optional

from src.automation.adjust import adjusted_closes
from src.automation.signals import (
    _count_beaten,
    _next_p_above,
    _rank_from_p_score,
)
from src.core.db import get_conn

log = logging.getLogger("hermes.mtf_signals")

# --- Timeframe parameterization --------------------------------------------
# windows: (label, n_bars_lookback, top_n_for_power). Excludes the current bar.
# Mirrors signals._WINDOWS but counted in BARS (weeks / months), per the design
# doc table. Top-N are tunable defaults; raw baselines are stored and the score
# is derived, so re-tuning needs no re-aggregation of bars.
_TF = {
    "W": {
        "label": "weekly",
        "bars_table": "bars_weekly",
        "sig_table": "weekly_signals",
        "key": "week_end_date",
        "windows": (("w4", 4, 1), ("w8", 8, 1), ("w13", 13, 2), ("w26", 26, 4), ("w52", 52, 6)),
        "p_labels": ("Pw4", "Pw8", "Pw13", "Pw26", "Pw52"),
    },
    "M": {
        "label": "monthly",
        "bars_table": "bars_monthly",
        "sig_table": "monthly_signals",
        "key": "month_end_date",
        "windows": (("m3", 3, 1), ("m6", 6, 1), ("m12", 12, 2), ("m18", 18, 3), ("m24", 24, 4)),
        "p_labels": ("Pm3", "Pm6", "Pm12", "Pm18", "Pm24"),
    },
}

_HOT_BARS_LOOKBACK = 10  # bars in the hot-bar avg-price window (mirrors daily's 10)


# --- Bar columns (must match the CREATE TABLE order in db.py) ---------------
_BAR_COLS_W = [
    "symbol", "week_end_date", "iso_year", "iso_week",
    "open", "high", "low", "close", "prev_close", "adj_close",
    "volume", "deliv_qty", "delivery_value", "num_trades", "turnover",
    "n_days", "is_partial",
]
_BAR_COLS_M = [
    "symbol", "month_end_date", "ym",
    "open", "high", "low", "close", "prev_close", "adj_close",
    "volume", "deliv_qty", "delivery_value", "num_trades", "turnover",
    "n_days", "is_partial",
]


def _bar_cols(tf: str) -> list[str]:
    return _BAR_COLS_W if tf == "W" else _BAR_COLS_M


def _sig_cols(tf: str) -> list[str]:
    """Stored signal columns for the timeframe (matches the CREATE TABLE order)."""
    spec = _TF[tf]
    labels = [w[0] for w in spec["windows"]]
    cols = ["symbol", spec["key"], "dvpt",
            "delivery_value_period", "total_value_period", "num_trades_period"]
    cols += [f"avg_dvpt_{l}" for l in labels]
    cols += [f"power_dvpt_{l}" for l in labels]
    cols += [f"avg_close_r{l}" for l in labels]
    cols += [f"avg_close_p{l}" for l in labels]
    cols += ["r_score", "p_score", "trigger_rank", "next_p_above", "gap_to_next_p_pct",
             "is_ath_dvpt", "hot_bars_avg_price", "price_vs_hot_avg_pct",
             "n_bars_used", "is_partial"]
    return cols


# --- Resampling -------------------------------------------------------------

def _period_key(tf: str, trade_date: str):
    """Bucket key for a daily date. Weekly -> (iso_year, iso_week);
    monthly -> 'YYYY-MM'. Keyed so the bar lands on the period's last day."""
    if tf == "W":
        y, w, _ = datetime.strptime(trade_date, "%Y-%m-%d").isocalendar()
        return (y, w)
    return trade_date[:7]


def _fetch_daily(conn, symbol: str) -> list:
    """All EQ daily rows for a symbol, OLDEST -> NEWEST."""
    return conn.execute(
        """
        SELECT trade_date, open, high, low, close, prev_close, avg_price,
               volume, value, num_trades, deliv_qty, deliv_per
        FROM bhavcopy_rows
        WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
        ORDER BY trade_date ASC
        """,
        (symbol,),
    ).fetchall()


def resample(tf: str, daily_rows: list, partial_key) -> list[dict]:
    """Resample OLDEST->NEWEST daily rows into timeframe bars (oldest->newest).

    `partial_key` is the period key of the market's latest trading session; the
    bar carrying that key is flagged is_partial (week/month-to-date). A delisted
    stock has no bar in the current period, so its final bar stays complete.
    """
    if not daily_rows:
        return []

    # Adjusted closes computed on the full DAILY series (corp-action detection
    # needs daily prev_close); each bar takes its last day's adjusted close.
    adj = adjusted_closes([
        {"trade_date": r["trade_date"], "close": r["close"], "prev_close": r["prev_close"]}
        for r in daily_rows
    ])

    # Group consecutive days into buckets (rows already sorted ascending).
    buckets: list[tuple] = []   # (key, [(row, adj_close), ...])
    cur_key = None
    cur: list = []
    for r, a in zip(daily_rows, adj):
        k = _period_key(tf, r["trade_date"])
        if k != cur_key:
            if cur:
                buckets.append((cur_key, cur))
            cur_key, cur = k, []
        cur.append((r, a))
    if cur:
        buckets.append((cur_key, cur))

    bars: list[dict] = []
    prev_close = None
    for key, days in buckets:
        rows = [d[0] for d in days]
        last = rows[-1]
        opens = [x["open"] for x in rows if x["open"] is not None]
        highs = [x["high"] for x in rows if x["high"] is not None]
        lows = [x["low"] for x in rows if x["low"] is not None]

        def _sum(field):
            vals = [x[field] for x in rows if x[field] is not None]
            return sum(vals) if vals else None

        # Delivery VALUE per day = deliv_qty * close (value-based, split-safe);
        # summed across the bar. This is the magnitude that feeds period DVPT.
        dv_days = [
            (x["deliv_qty"] * x["close"])
            for x in rows
            if x["deliv_qty"] is not None and x["close"] is not None
        ]
        delivery_value = sum(dv_days) if dv_days else None

        bar = {
            # "symbol" is stamped by process_symbol (the daily fetch is already
            # filtered to one symbol, so it isn't re-selected per row).
            "open": opens[0] if opens else None,
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
            "close": last["close"],
            "prev_close": prev_close,
            "adj_close": days[-1][1],
            "volume": _sum("volume"),
            "deliv_qty": _sum("deliv_qty"),
            "delivery_value": delivery_value,
            "num_trades": _sum("num_trades"),
            "turnover": _sum("value"),
            "n_days": len(rows),
            "is_partial": 1 if key == partial_key else 0,
        }
        if tf == "W":
            bar["week_end_date"] = last["trade_date"]
            bar["iso_year"], bar["iso_week"] = key
        else:
            bar["month_end_date"] = last["trade_date"]
            bar["ym"] = key
        # period DVPT = sum(delivery value) / sum(num_trades) — NOT a mean of
        # daily DVPTs (D43-B).
        nt = bar["num_trades"]
        bar["dvpt"] = (delivery_value / nt) if (delivery_value is not None and nt) else None
        bars.append(bar)
        prev_close = last["close"]

    return bars


# --- Signal computation on the bar series -----------------------------------

def compute_signals(tf: str, symbol: str, bars: list[dict]) -> list[dict]:
    """Walk the oldest->newest bar series, emitting a signal row per bar."""
    spec = _TF[tf]
    windows = spec["windows"]
    p_labels = spec["p_labels"]
    key = spec["key"]
    labels = [w[0] for w in windows]

    dvpts = [b["dvpt"] for b in bars]
    closes = [b["close"] for b in bars]

    out: list[dict] = []
    running_max_dvpt: Optional[float] = None   # for is_ath (in-memory, no DB hit)
    hot_closes: list[float] = []               # rolling hot-bar close window

    for i, b in enumerate(bars):
        today = dvpts[i]
        sig: dict = {
            "symbol": symbol,
            key: b[key],
            "dvpt": today,
            "delivery_value_period": b["delivery_value"],
            "total_value_period": b["turnover"],
            "num_trades_period": b["num_trades"],
            "n_bars_used": i,                  # prior bars available
            "is_partial": b["is_partial"],
        }

        r_vals, p_vals = [], []
        for label, n_bars, top_n in windows:
            lo = max(0, i - n_bars)
            win = [bars[j] for j in range(lo, i) if dvpts[j] is not None]
            if win:
                avg_dvpt = sum(x["dvpt"] for x in win) / len(win)
                rc = [x["close"] for x in win if x["close"] is not None]
                avg_close_r = (sum(rc) / len(rc)) if rc else None
                top = sorted(win, key=lambda x: x["dvpt"], reverse=True)[:top_n]
                avg_power = sum(x["dvpt"] for x in top) / len(top)
                pc = [x["close"] for x in top if x["close"] is not None]
                avg_close_p = (sum(pc) / len(pc)) if pc else None
            else:
                avg_dvpt = avg_close_r = avg_power = avg_close_p = None
            sig[f"avg_dvpt_{label}"] = avg_dvpt
            sig[f"power_dvpt_{label}"] = avg_power
            sig[f"avg_close_r{label}"] = avg_close_r
            sig[f"avg_close_p{label}"] = avg_close_p
            r_vals.append(avg_dvpt)
            p_vals.append(avg_power)

        r_score = _count_beaten(today, r_vals)
        p_score = _count_beaten(today, p_vals)
        sig["r_score"] = r_score
        sig["p_score"] = p_score
        sig["trigger_rank"] = _rank_from_p_score(p_score)
        next_above, gap = _next_p_above(today, p_vals, p_labels)
        sig["next_p_above"] = next_above
        sig["gap_to_next_p_pct"] = gap

        # ATH DVPT across the symbol's whole bar history (running max of PRIOR
        # bars; deepening the data re-defines this for all dates, as intended).
        if today is not None:
            sig["is_ath_dvpt"] = 1 if (running_max_dvpt is None or today > running_max_dvpt) else 0
        else:
            sig["is_ath_dvpt"] = None

        # Hot-bar avg price: avg close over the last N prior bars whose DVPT beat
        # their own shortest power baseline (mirrors the daily hot-day anchor).
        sig["hot_bars_avg_price"] = (sum(hot_closes) / len(hot_closes)) if hot_closes else None
        hp = sig["hot_bars_avg_price"]
        tc = closes[i]
        sig["price_vs_hot_avg_pct"] = (
            (tc - hp) / hp * 100.0 if (hp is not None and hp > 0 and tc is not None) else None
        )

        out.append(sig)

        # Roll forward the running aggregates AFTER emitting this bar's row.
        if today is not None:
            running_max_dvpt = today if running_max_dvpt is None else max(running_max_dvpt, today)
            shortest_power = p_vals[0]   # the tightest window's power baseline
            if shortest_power is not None and today > shortest_power and closes[i] is not None:
                hot_closes.append(closes[i])
                if len(hot_closes) > _HOT_BARS_LOOKBACK:
                    hot_closes.pop(0)

    return out


# --- Storage ----------------------------------------------------------------

def _store(conn, tf: str, bars: list[dict], signals: list[dict],
           only_last: Optional[int] = None) -> None:
    """Upsert bars + signals. If only_last is set, store just the last N of each
    (the nightly incremental path — earlier bars are unchanged)."""
    bar_cols = _bar_cols(tf)
    sig_cols = _sig_cols(tf)
    b_rows = bars[-only_last:] if only_last else bars
    s_rows = signals[-only_last:] if only_last else signals
    if b_rows:
        conn.executemany(
            f"INSERT OR REPLACE INTO {_TF[tf]['bars_table']} ({','.join(bar_cols)}) "
            f"VALUES ({','.join('?' * len(bar_cols))})",
            [[b.get(c) for c in bar_cols] for b in b_rows],
        )
    if s_rows:
        conn.executemany(
            f"INSERT OR REPLACE INTO {_TF[tf]['sig_table']} ({','.join(sig_cols)}) "
            f"VALUES ({','.join('?' * len(sig_cols))})",
            [[s.get(c) for c in sig_cols] for s in s_rows],
        )


def _partial_key(conn, tf: str):
    """Period key of the market's most recent trading session."""
    row = conn.execute("SELECT MAX(trade_date) AS d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return None
    return _period_key(tf, row["d"])


def _all_symbols(conn) -> list[str]:
    return [r["symbol"] for r in conn.execute(
        """SELECT DISTINCT symbol FROM bhavcopy_rows
           WHERE series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY symbol"""
    ).fetchall()]


def process_symbol(conn, tf: str, symbol: str, partial_key,
                   only_last: Optional[int] = None) -> int:
    """Resample + compute + store one symbol for one timeframe. Returns #bars."""
    daily = _fetch_daily(conn, symbol)
    if not daily:
        return 0
    bars = resample(tf, daily, partial_key)
    if not bars:
        return 0
    for b in bars:
        b["symbol"] = symbol
    signals = compute_signals(tf, symbol, bars)
    _store(conn, tf, bars, signals, only_last=only_last)
    return len(bars)


# --- Modes ------------------------------------------------------------------

def run_backfill(tf: str) -> tuple[int, int]:
    """Full (re)materialization of every symbol for one timeframe."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        symbols = _all_symbols(conn)
        log.info("%s backfill: %d symbols", _TF[tf]["label"], len(symbols))
        nbars = 0
        for i, sym in enumerate(symbols, 1):
            nbars += process_symbol(conn, tf, sym, partial_key)
            if i % 200 == 0:
                log.info("  progress: %d / %d symbols (%d bars)", i, len(symbols), nbars)
                conn.commit()
                time.sleep(0.02)   # let other DB writes through (WAL)
        conn.commit()
    log.info("%s backfill done: %d symbols, %d bars", _TF[tf]["label"], len(symbols), nbars)
    return len(symbols), nbars


def run_recent(tf: str, only_last: int = 2) -> tuple[int, int]:
    """Nightly incremental — recompute only the latest `only_last` bars per
    symbol (the current partial bar + the one that may have just closed). Still
    resamples the full series for correct baselines, but only writes the tail."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        symbols = _all_symbols(conn)
        log.info("%s recent(%d): %d symbols", _TF[tf]["label"], only_last, len(symbols))
        n = 0
        for i, sym in enumerate(symbols, 1):
            if process_symbol(conn, tf, sym, partial_key, only_last=only_last):
                n += 1
            if i % 400 == 0:
                conn.commit()
        conn.commit()
    log.info("%s recent done: %d symbols updated", _TF[tf]["label"], n)
    return len(symbols), n


def run_symbol(tf: str, symbol: str) -> int:
    """One symbol, full series — for spot-checking post-foundation."""
    with get_conn() as conn:
        partial_key = _partial_key(conn, tf)
        n = process_symbol(conn, tf, symbol, partial_key)
        conn.commit()
    log.info("%s %s: %d bars", _TF[tf]["label"], symbol, n)
    return n


def _timeframes(arg: str) -> list[str]:
    if arg in ("W", "M"):
        return [arg]
    return ["W", "M"]   # 'both' / default


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    p = argparse.ArgumentParser(description="Multi-timeframe (weekly/monthly) DVPT signal engine")
    p.add_argument("--timeframe", choices=["W", "M", "both"], default="both")
    p.add_argument("--backfill", action="store_true",
                   help="full (re)materialization of all symbols")
    p.add_argument("--recent", action="store_true",
                   help="nightly incremental — recompute only the latest bars")
    p.add_argument("--only-last", type=int, default=2,
                   help="how many trailing bars --recent rewrites (default 2)")
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
