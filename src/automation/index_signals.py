"""D32 Index signals + ratio time series + ratio signals.

For each (index, date), compute:
  - Returns over 1d/1w/1m/3m/6m/12m calendar windows
  - % distance from 50d / 200d MA (on level)
  - % off 52w high, % above 52w low
  - Denormalized RS vs broad benchmark (default NIFTY 500): today's ratio,
    slope at 1m/3m/6m/12m, above/below MA flags, breakout flags, trend_state

For each (numerator, denominator, date) pair we track, compute:
  - ratio = num_close / den_close
  - 20/50/200d MA on the ratio
  - 50d/200d/52w high+low of the ratio
  - Slopes at 1m/3m/6m/12m
  - Breakout flags + composite trend_state

Pairs computed in D32 (sector ↔ broad):
  Every sectoral/thematic NSE index × {NIFTY 50, NIFTY 500}.

Usage:
    python -m src.automation.index_signals                  # today
    python -m src.automation.index_signals --backfill       # all dates
    python -m src.automation.index_signals --date 2026-06-05
"""

import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.index_signals")


# Broad benchmarks against which we compute sector RS.
BROAD_BENCHMARKS = ("NIFTY 50", "NIFTY 500")
DEFAULT_BROAD = "NIFTY 500"

# Size-based indexes — not sectors. Excluded as numerators when computing
# "sector vs broad" ratios (they ARE the broad market).
SIZE_BASED_INDEX_NAMES = {
    "NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
    "NIFTY MIDCAP 100", "NIFTY MIDCAP 50", "NIFTY MIDCAP 150",
    "NIFTY SMALLCAP 50", "NIFTY SMALLCAP 100", "NIFTY SMALLCAP 250",
    "NIFTY MICROCAP 250", "NIFTY LARGEMIDCAP 250", "NIFTY MIDSMALLCAP 400",
    "NIFTY TOTAL MARKET",
}


def _cutoff(trade_date: str, days: int) -> str:
    dt = datetime.strptime(trade_date, "%Y-%m-%d")
    return (dt - timedelta(days=days)).strftime("%Y-%m-%d")


def _safe_ret_pct(curr, prev) -> Optional[float]:
    if curr is None or prev is None or prev <= 0:
        return None
    return (curr - prev) / prev * 100.0


def _safe_div(num, den) -> Optional[float]:
    if num is None or den is None or den <= 0:
        return None
    return num / den


# --- Per-index level signals -----------------------------------------------

def _fetch_index_history(index_name: str, trade_date: str) -> list[dict]:
    """All rows for one index within the last 380 calendar days, oldest first."""
    cutoff = _cutoff(trade_date, 380)
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT trade_date, close_value
               FROM index_rows
               WHERE index_name = ? AND trade_date <= ? AND trade_date >= ?
               ORDER BY trade_date ASC""",
            (index_name, trade_date, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def _closest_close_at_or_before(history: list[dict], target_date: str) -> Optional[float]:
    """Find the latest close at or before target_date in the history list."""
    result = None
    for r in history:
        if r["trade_date"] <= target_date:
            result = r["close_value"]
        else:
            break
    return result


def _moving_avg_on_levels(history: list[dict], today_idx: int, window: int) -> Optional[float]:
    if today_idx < window:
        return None
    sub = [history[today_idx - i]["close_value"] for i in range(window)]
    sub = [v for v in sub if v is not None]
    if len(sub) < window // 2:
        return None
    return sum(sub) / len(sub)


def _highest_lowest(history: list[dict], today_idx: int, window: int) -> tuple:
    if today_idx < 1:
        return None, None
    start = max(0, today_idx - window + 1)
    closes = [history[i]["close_value"] for i in range(start, today_idx + 1)]
    closes = [c for c in closes if c is not None]
    if not closes:
        return None, None
    return max(closes), min(closes)


def compute_index_signal(index_name: str, trade_date: str) -> Optional[dict]:
    history = _fetch_index_history(index_name, trade_date)
    if not history:
        return None
    # Find today's row index
    today_idx = None
    for i, r in enumerate(history):
        if r["trade_date"] == trade_date:
            today_idx = i
            break
    if today_idx is None:
        return None
    today_close = history[today_idx]["close_value"]
    if today_close is None or today_close <= 0:
        return None

    # Returns over windows — find close at-or-before (trade_date - N days)
    def ret(days: int) -> Optional[float]:
        prior_close = _closest_close_at_or_before(history, _cutoff(trade_date, days))
        return _safe_ret_pct(today_close, prior_close)

    ma_50 = _moving_avg_on_levels(history, today_idx, 50)
    ma_200 = _moving_avg_on_levels(history, today_idx, 200)
    high_252, low_252 = _highest_lowest(history, today_idx, 252)

    return {
        "index_name": index_name,
        "trade_date": trade_date,
        "close_value": today_close,
        "ret_1d_pct":  ret(1),
        "ret_1w_pct":  ret(7),
        "ret_1m_pct":  ret(30),
        "ret_3m_pct":  ret(90),
        "ret_6m_pct":  ret(180),
        "ret_12m_pct": ret(365),
        "pct_above_50d_avg":  _safe_ret_pct(today_close, ma_50),
        "pct_above_200d_avg": _safe_ret_pct(today_close, ma_200),
        "pct_off_52w_high":   _safe_ret_pct(today_close, high_252),  # negative if below
        "pct_above_52w_low":  _safe_ret_pct(today_close, low_252),   # positive if above
    }


# --- Ratio time series + ratio signals -------------------------------------

def _classify_trend_state(*, ratio, ma_50, ma_200, new_52w_high,
                          new_200d_high, slope_3m, pct_below_52w_high) -> str:
    """Composite trend state — string label for the one-glance read."""
    if ratio is None:
        return "UNKNOWN"
    above_200 = ma_200 is not None and ratio > ma_200
    above_50  = ma_50  is not None and ratio > ma_50
    if new_52w_high:
        return "BREAKOUT"
    if new_200d_high and above_200:
        return "BREAKOUT"
    if above_200 and (slope_3m is None or slope_3m > 0):
        return "UPTREND"
    if (pct_below_52w_high is not None and pct_below_52w_high <= -40
        and (ma_200 is not None and ratio < ma_200)):
        return "BREAKDOWN"
    if (ma_200 is not None and ratio < ma_200
        and (slope_3m is None or slope_3m < 0)):
        return "DOWNTREND"
    if (ma_50 is not None and abs(ratio - ma_50) / ma_50 < 0.05):
        return "CONSOLIDATING"
    return "CONSOLIDATING"


def _compute_ratio_history(numerator: str, denominator: str,
                            num_history: list[dict], den_history: list[dict],
                            trade_date: str) -> list[dict]:
    """Join the two index histories by date and compute the ratio series."""
    den_map = {r["trade_date"]: r["close_value"] for r in den_history}
    out = []
    for nr in num_history:
        d = nr["trade_date"]
        dn = den_map.get(d)
        if dn is None or dn <= 0 or nr["close_value"] is None:
            continue
        out.append({
            "trade_date": d,
            "num_close":  nr["close_value"],
            "den_close":  dn,
            "ratio":      nr["close_value"] / dn,
        })
    return out


def _store_ratio_rows(numerator: str, denominator: str,
                      ratio_history: list[dict], trade_date_filter: Optional[str] = None) -> int:
    """INSERT OR REPLACE the ratio_rows entries. If trade_date_filter set,
    only persist that one date (the today path); otherwise persist all
    (the backfill path)."""
    rows = ratio_history
    if trade_date_filter:
        rows = [r for r in ratio_history if r["trade_date"] == trade_date_filter]
    if not rows:
        return 0
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO ratio_rows
                 (numerator, denominator, trade_date, num_close, den_close, ratio)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(numerator, denominator, r["trade_date"], r["num_close"],
              r["den_close"], r["ratio"]) for r in rows],
        )
    return len(rows)


def compute_ratio_signal(numerator: str, denominator: str,
                          ratio_history: list[dict], trade_date: str) -> Optional[dict]:
    """Compute the technical signal row for one (num, den, date)."""
    # Find today's idx in ratio_history.
    today_idx = None
    for i, r in enumerate(ratio_history):
        if r["trade_date"] == trade_date:
            today_idx = i
            break
    if today_idx is None or today_idx < 1:
        return None
    today_ratio = ratio_history[today_idx]["ratio"]

    def ma(window):
        if today_idx + 1 < window:
            return None
        sub = [ratio_history[today_idx - i]["ratio"] for i in range(window)]
        return sum(sub) / len(sub)

    ma_20 = ma(20)
    ma_50 = ma(50)
    ma_200 = ma(200)

    # High/Low windows over the ratio (last N entries up to today inclusive).
    def hi_lo(window):
        if today_idx < 1:
            return None, None
        start = max(0, today_idx - window + 1)
        sub = [ratio_history[i]["ratio"] for i in range(start, today_idx + 1)]
        if not sub:
            return None, None
        return max(sub), min(sub)

    high_50d, low_50d = hi_lo(50)
    high_200d, _ = hi_lo(200)
    high_52w, low_52w = hi_lo(252)

    # Slopes (% change from prior anchor to today, by calendar window).
    def slope(days: int) -> Optional[float]:
        cutoff = _cutoff(trade_date, days)
        prior = None
        for r in ratio_history:
            if r["trade_date"] <= cutoff:
                prior = r["ratio"]
            else:
                break
        return _safe_ret_pct(today_ratio, prior)

    slope_1m = slope(30)
    slope_3m = slope(90)
    slope_6m = slope(180)
    slope_12m = slope(365)

    # Breakout flags
    above_50 = 1 if (ma_50 is not None and today_ratio > ma_50) else 0
    above_200 = 1 if (ma_200 is not None and today_ratio > ma_200) else 0

    yest_ratio = ratio_history[today_idx - 1]["ratio"]
    cross_50_today = 1 if (
        ma_50 is not None and today_ratio > ma_50 and yest_ratio <= ma_50
    ) else 0
    cross_200_today = 1 if (
        ma_200 is not None and today_ratio > ma_200 and yest_ratio <= ma_200
    ) else 0

    # New highs computed against the STRICTLY-PRIOR window (so today must beat
    # all prior days in the window, not match them).
    def new_high(window):
        if today_idx < 1:
            return 0
        start = max(0, today_idx - window)
        prior_window = [ratio_history[i]["ratio"] for i in range(start, today_idx)]
        if not prior_window:
            return 0
        return 1 if today_ratio > max(prior_window) else 0

    new_50d  = new_high(50)
    new_200d = new_high(200)
    new_52w  = new_high(252)

    pct_below_52w_high = (
        _safe_ret_pct(today_ratio, high_52w) if high_52w else None
    )

    trend_state = _classify_trend_state(
        ratio=today_ratio, ma_50=ma_50, ma_200=ma_200,
        new_52w_high=new_52w, new_200d_high=new_200d,
        slope_3m=slope_3m, pct_below_52w_high=pct_below_52w_high,
    )

    return {
        "numerator": numerator,
        "denominator": denominator,
        "trade_date": trade_date,
        "ratio": today_ratio,
        "ratio_ma_20": ma_20,
        "ratio_ma_50": ma_50,
        "ratio_ma_200": ma_200,
        "ratio_high_50d": high_50d,
        "ratio_low_50d": low_50d,
        "ratio_high_200d": high_200d,
        "ratio_high_52w": high_52w,
        "ratio_low_52w": low_52w,
        "slope_1m_pct": slope_1m,
        "slope_3m_pct": slope_3m,
        "slope_6m_pct": slope_6m,
        "slope_12m_pct": slope_12m,
        "above_50_ma": above_50,
        "above_200_ma": above_200,
        "cross_50_today": cross_50_today,
        "cross_200_today": cross_200_today,
        "new_50d_high": new_50d,
        "new_200d_high": new_200d,
        "new_52w_high": new_52w,
        "pct_below_52w_high": pct_below_52w_high,
        "trend_state": trend_state,
    }


_RATIO_SIG_COLS = [
    "numerator", "denominator", "trade_date", "ratio",
    "ratio_ma_20", "ratio_ma_50", "ratio_ma_200",
    "ratio_high_50d", "ratio_low_50d", "ratio_high_200d",
    "ratio_high_52w", "ratio_low_52w",
    "slope_1m_pct", "slope_3m_pct", "slope_6m_pct", "slope_12m_pct",
    "above_50_ma", "above_200_ma", "cross_50_today", "cross_200_today",
    "new_50d_high", "new_200d_high", "new_52w_high",
    "pct_below_52w_high", "trend_state",
]


def _store_ratio_signal(sig: dict) -> None:
    placeholders = ",".join("?" * len(_RATIO_SIG_COLS))
    sql = (f"INSERT OR REPLACE INTO ratio_signals ({','.join(_RATIO_SIG_COLS)}) "
           f"VALUES ({placeholders})")
    with get_conn() as conn:
        conn.execute(sql, [sig.get(c) for c in _RATIO_SIG_COLS])


# --- Index signals storage (with denormalized RS) --------------------------

_INDEX_SIG_COLS = [
    "index_name", "trade_date", "close_value",
    "ret_1d_pct", "ret_1w_pct", "ret_1m_pct", "ret_3m_pct", "ret_6m_pct", "ret_12m_pct",
    "pct_above_50d_avg", "pct_above_200d_avg",
    "pct_off_52w_high", "pct_above_52w_low",
    "broad_benchmark",
    "rs_vs_broad_today",
    "rs_vs_broad_slope_1m", "rs_vs_broad_slope_3m",
    "rs_vs_broad_slope_6m", "rs_vs_broad_slope_12m",
    "rs_vs_broad_above_50ma", "rs_vs_broad_above_200ma",
    "rs_vs_broad_new_52w_high", "rs_vs_broad_trend_state",
]


def _store_index_signal(sig: dict) -> None:
    placeholders = ",".join("?" * len(_INDEX_SIG_COLS))
    sql = (f"INSERT OR REPLACE INTO index_signals ({','.join(_INDEX_SIG_COLS)}) "
           f"VALUES ({placeholders})")
    with get_conn() as conn:
        conn.execute(sql, [sig.get(c) for c in _INDEX_SIG_COLS])


# --- Orchestration ---------------------------------------------------------

def compute_for_date(trade_date: str) -> tuple[int, int]:
    """For one trade_date: compute index signals for all indexes + ratio
    signals for every (sectoral, broad) pair. Returns (n_indexes, n_ratios).
    """
    with get_conn() as conn:
        all_indexes = [r["index_name"] for r in conn.execute(
            "SELECT DISTINCT index_name FROM index_rows WHERE trade_date = ? "
            "ORDER BY index_name",
            (trade_date,),
        ).fetchall()]

    if not all_indexes:
        log.info("no index rows for %s", trade_date)
        return 0, 0

    # Cache histories per index — used multiple times across the broad pairs.
    history_cache: dict[str, list[dict]] = {}

    def history(name: str) -> list[dict]:
        if name not in history_cache:
            history_cache[name] = _fetch_index_history(name, trade_date)
        return history_cache[name]

    # Pre-load broad benchmarks (denominators).
    for b in BROAD_BENCHMARKS:
        history(b)

    n_idx = 0
    n_ratio = 0

    for name in all_indexes:
        idx_sig = compute_index_signal(name, trade_date)
        if not idx_sig:
            continue

        # Sector-vs-broad ratios — only for non-size-based indexes.
        is_size_based = name in SIZE_BASED_INDEX_NAMES

        # Default RS-vs-broad fields (used for the denormalized index_signals row)
        rs_today = rs_s1 = rs_s3 = rs_s6 = rs_s12 = None
        rs_above50 = rs_above200 = rs_new52 = None
        rs_state = None

        if not is_size_based:
            num_hist = history(name)
            for broad in BROAD_BENCHMARKS:
                if broad == name:
                    continue
                den_hist = history(broad)
                if not den_hist:
                    continue
                rh = _compute_ratio_history(name, broad, num_hist, den_hist, trade_date)
                if not rh:
                    continue
                # Persist the whole computed series for this pair (idempotent
                # INSERT OR REPLACE on the today path is cheap; on backfill it
                # rebuilds the whole curve).
                _store_ratio_rows(name, broad, rh)
                n_ratio += 1

                sig = compute_ratio_signal(name, broad, rh, trade_date)
                if sig:
                    _store_ratio_signal(sig)
                    # If this is the DEFAULT broad benchmark, denormalize onto
                    # the index_signals row for fast lookup.
                    if broad == DEFAULT_BROAD:
                        rs_today      = sig["ratio"]
                        rs_s1         = sig["slope_1m_pct"]
                        rs_s3         = sig["slope_3m_pct"]
                        rs_s6         = sig["slope_6m_pct"]
                        rs_s12        = sig["slope_12m_pct"]
                        rs_above50    = sig["above_50_ma"]
                        rs_above200   = sig["above_200_ma"]
                        rs_new52      = sig["new_52w_high"]
                        rs_state      = sig["trend_state"]

        idx_sig.update({
            "broad_benchmark": DEFAULT_BROAD if not is_size_based else None,
            "rs_vs_broad_today":    rs_today,
            "rs_vs_broad_slope_1m": rs_s1,
            "rs_vs_broad_slope_3m": rs_s3,
            "rs_vs_broad_slope_6m": rs_s6,
            "rs_vs_broad_slope_12m": rs_s12,
            "rs_vs_broad_above_50ma":   rs_above50,
            "rs_vs_broad_above_200ma":  rs_above200,
            "rs_vs_broad_new_52w_high": rs_new52,
            "rs_vs_broad_trend_state":  rs_state,
        })
        _store_index_signal(idx_sig)
        n_idx += 1

    return n_idx, n_ratio


def run_today() -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM index_rows"
        ).fetchone()
    if not row or not row["d"]:
        return False, "no index data found"
    n_idx, n_ratio = compute_for_date(row["d"])
    return True, f"{n_idx} indexes, {n_ratio} ratio pairs for {row['d']}"


def run_backfill() -> tuple[int, int]:
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT trade_date FROM index_dates ORDER BY trade_date ASC"
        ).fetchall()]
    log.info("index_signals backfill: %d dates", len(dates))
    total_idx = 0
    total_ratio = 0
    for k, d in enumerate(dates, 1):
        n_idx, n_ratio = compute_for_date(d)
        total_idx += n_idx
        total_ratio += n_ratio
        if k % 50 == 0:
            log.info("  progress: %d / %d dates, %d indexes, %d ratio pairs",
                     k, len(dates), total_idx, total_ratio)
    return total_idx, total_ratio


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.date:
        n_idx, n_ratio = compute_for_date(args.date)
        log.info("date %s done: %d indexes, %d ratio pairs", args.date, n_idx, n_ratio)
    elif args.backfill:
        n_idx, n_ratio = run_backfill()
        log.info("backfill complete: %d index rows, %d ratio rows", n_idx, n_ratio)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
