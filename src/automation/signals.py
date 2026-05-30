"""Per-stock rolling delivery-value signals.

For each (symbol, trade_date), compute:
  - Today's delivery_value_per_trade = (deliv_qty * close) / no_of_trades

  - LEGACY flat rolling averages over 5/10/30/60/90/180/365 trading days
    (kept for /dvpt single-stock detail history table)

  - D31 R-tier — flat rolling averages over CALENDAR-day windows:
      R1M  = avg DVPT over last  30 calendar days (excl today)
      R2M  =                     60
      R3M  =                     90
      R6M  =                    180
      R12M =                    360

  - D31 P-tier — avg of top-N DVPT within CALENDAR-day windows:
      P1M  = top  4 DVPT in last  30 calendar days
      P2M  = top  7         in last  60
      P3M  = top 12         in last  90
      P6M  = top 20         in last 180
      P12M = top 30         in last 360

  - D31 Institutional price zones — for every R/P baseline, the avg CLOSE
    on the same days (R: avg close over window; P: avg close on the
    top-N-by-DVPT days). Lets us read "where institutions transacted."

  - Scores: r_score / p_score = count of R/P baselines today's DVPT beats
  - trigger_rank = SS(5)/S(4)/A(3)/B(2)/C(1)/'-' from p_score
  - ATH-DVPT, hot_days_avg_price, near-break pointer (next_p_above + gap)

Stored nightly into stock_signals table; queries become instant lookups.

Usage:
    python -m src.automation.signals                        # compute today's row for every stock that has bhav data today
    python -m src.automation.signals --backfill             # compute signals for ALL historical days where missing
    python -m src.automation.signals --backfill-triggers    # recompute D28/D31 trigger fields on existing rows
    python -m src.automation.signals --symbol RELIANCE      # one stock only (for debugging)
"""

import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from src.core.db import get_conn

# D31 windowing — calendar days (NOT trading days).
# Format: (label, calendar_days, top_n_for_power)
_WINDOWS = (
    ("1m",   30,  4),
    ("2m",   60,  7),
    ("3m",   90, 12),
    ("6m",  180, 20),
    ("12m", 360, 30),
)
_P_LABELS = ("P1M", "P2M", "P3M", "P6M", "P12M")

log = logging.getLogger("hermes.signals")


def _delivery_value_per_trade(deliv_qty, close, num_trades) -> Optional[float]:
    """(deliv_qty * close) / num_trades. Returns None on any missing piece."""
    if deliv_qty is None or close is None or num_trades is None or num_trades == 0:
        return None
    if deliv_qty <= 0 or close <= 0:
        return None
    return (deliv_qty * close) / num_trades


def _delivery_value(deliv_qty, close) -> Optional[float]:
    if deliv_qty is None or close is None:
        return None
    return deliv_qty * close


def _cutoff_date(trade_date: str, days: int) -> str:
    """Calendar-day cutoff string for SQL filter. Inclusive lower bound."""
    dt = datetime.strptime(trade_date, "%Y-%m-%d")
    return (dt - timedelta(days=days)).strftime("%Y-%m-%d")


def compute_signals_for_symbol_date(symbol: str, trade_date: str) -> Optional[dict]:
    """Compute the full signal row for one (symbol, trade_date).

    Fetches all bhav rows for the symbol within the last 360 calendar days,
    then slices per window (30/60/90/180/360 calendar days) for R-tier and
    P-tier baselines. D31 calendar-day windowing replaces D28's trading-day
    windowing.
    """
    cutoff_360 = _cutoff_date(trade_date, 360)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, close, value, deliv_qty, num_trades
            FROM bhavcopy_rows
            WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
              AND trade_date <= ? AND trade_date >= ?
            ORDER BY trade_date DESC
            """,
            (symbol, trade_date, cutoff_360),
        ).fetchall()

    if not rows:
        return None

    today_row = rows[0]
    if today_row["trade_date"] != trade_date:
        return None

    today_dvpt = _delivery_value_per_trade(
        today_row["deliv_qty"], today_row["close"], today_row["num_trades"]
    )
    today_dv = _delivery_value(today_row["deliv_qty"], today_row["close"])
    today_total = today_row["value"]

    # Build a per-day baseline list (excluding today) with both DVPT and close.
    # Each entry: (trade_date_str, dvpt, close).
    baseline_full = []
    for r in rows[1:]:
        dvpt = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        if dvpt is None:
            continue
        baseline_full.append((r["trade_date"], dvpt, r["close"]))

    n_baseline = len(baseline_full)

    # Legacy trading-day windows — used only for /dvpt history backward compat.
    legacy_dvpts = [x[1] for x in baseline_full]

    def legacy_flat_avg(td_window: int) -> Optional[float]:
        if td_window > len(legacy_dvpts):
            return None
        sub = legacy_dvpts[:td_window]
        return sum(sub) / len(sub)

    def safe_ratio(num, den) -> Optional[float]:
        if num is None or den is None or den <= 0:
            return None
        return num / den

    # D31 calendar-day windowing helpers.
    def window_subset(days: int):
        """Return the baseline rows within the last `days` calendar days."""
        cutoff = _cutoff_date(trade_date, days)
        return [b for b in baseline_full if b[0] >= cutoff]

    def r_stats(days: int) -> tuple:
        """R-tier: flat avg DVPT + flat avg close over the calendar window."""
        sub = window_subset(days)
        if not sub:
            return None, None
        avg_dvpt = sum(b[1] for b in sub) / len(sub)
        closes = [b[2] for b in sub if b[2] is not None]
        avg_close = (sum(closes) / len(closes)) if closes else None
        return avg_dvpt, avg_close

    def p_stats(days: int, top_n: int) -> tuple:
        """P-tier: avg of top-N DVPT + avg close on those same top-N days."""
        sub = window_subset(days)
        if not sub:
            return None, None
        # Sort by DVPT descending, take top_n.
        top = sorted(sub, key=lambda b: b[1], reverse=True)[:top_n]
        if not top:
            return None, None
        avg_dvpt = sum(b[1] for b in top) / len(top)
        closes = [b[2] for b in top if b[2] is not None]
        avg_close = (sum(closes) / len(closes)) if closes else None
        return avg_dvpt, avg_close

    signal = {
        "symbol": symbol,
        "trade_date": trade_date,
        "delivery_value_today": today_dv,
        "total_value_today": today_total,
        "delivery_value_per_trade": today_dvpt,
        # LEGACY flat averages (trading-day windows; /dvpt history table)
        "avg_dvpt_5d":   legacy_flat_avg(5),
        "avg_dvpt_10d":  legacy_flat_avg(10),
        "avg_dvpt_30d":  legacy_flat_avg(30),
        "avg_dvpt_60d":  legacy_flat_avg(60),
        "avg_dvpt_90d":  legacy_flat_avg(90),
        "avg_dvpt_180d": legacy_flat_avg(180),
        "avg_dvpt_365d": legacy_flat_avg(365),
        "data_points_used": n_baseline,
    }

    # D31 R-tier + P-tier — calendar-day windows.
    for label, days, top_n in _WINDOWS:
        r_dvpt, r_close = r_stats(days)
        p_dvpt, p_close = p_stats(days, top_n)
        signal[f"avg_dvpt_{label}"]   = r_dvpt
        signal[f"power_dvpt_{label}"] = p_dvpt
        signal[f"avg_close_r{label}"] = r_close
        signal[f"avg_close_p{label}"] = p_close

    # Legacy ratios (kept for backward compat — point at the new calendar-day baselines).
    signal["ratio_today_vs_avg_30d"]  = safe_ratio(today_dvpt, signal["avg_dvpt_1m"])
    signal["ratio_today_vs_power_1m"] = safe_ratio(today_dvpt, signal["power_dvpt_1m"])
    signal["ratio_today_vs_power_3m"] = safe_ratio(today_dvpt, signal["power_dvpt_3m"])

    # --- Two-tier scoring + layered triggers (D28 logic, D31 baselines) ----
    r_keys = tuple(f"avg_dvpt_{lbl}"   for lbl, _, _ in _WINDOWS)
    p_keys = tuple(f"power_dvpt_{lbl}" for lbl, _, _ in _WINDOWS)

    r_score = _count_beaten(today_dvpt, [signal[k] for k in r_keys])
    p_score = _count_beaten(today_dvpt, [signal[k] for k in p_keys])
    signal["r_score"] = r_score
    signal["p_score"] = p_score
    signal["trigger_rank"] = _rank_from_p_score(p_score)

    next_above, gap = _next_p_above(today_dvpt, [signal[k] for k in p_keys], _P_LABELS)
    signal["next_p_above"] = next_above
    signal["gap_to_next_p_pct"] = gap

    # ATH-DVPT — true full-history check via stock_signals (not just the
    # 365-day window in `baseline`).
    if today_dvpt is not None:
        with get_conn() as conn:
            prow = conn.execute(
                """SELECT MAX(delivery_value_per_trade) AS pm
                   FROM stock_signals
                   WHERE symbol = ? AND trade_date < ?""",
                (symbol, trade_date),
            ).fetchone()
        prior_max = prow["pm"] if prow else None
        signal["is_ath_dvpt"] = 1 if (prior_max is None or today_dvpt > prior_max) else 0
    else:
        signal["is_ath_dvpt"] = None

    # Hot-day average close: avg close on last 10 days where that day's
    # DVPT > its own 1m power baseline.
    hot_avg = _hot_days_avg_close(rows[1:])
    signal["hot_days_avg_price"] = hot_avg
    if hot_avg is not None and today_row["close"] is not None and hot_avg > 0:
        signal["price_vs_hot_avg_pct"] = (today_row["close"] - hot_avg) / hot_avg * 100.0
    else:
        signal["price_vs_hot_avg_pct"] = None

    return signal


def _count_beaten(today_v, baselines: list) -> int:
    """How many baselines (non-None) does today's value strictly exceed."""
    if today_v is None:
        return 0
    return sum(1 for b in baselines if b is not None and today_v > b)


def _rank_from_p_score(p_score: int) -> str:
    """Pure count-based rank — no hidden ordering between P-windows (D28)."""
    return {5: "SS", 4: "S", 3: "A", 2: "B", 1: "C", 0: "-"}.get(p_score, "-")


def _next_p_above(today_v, p_baselines: list, p_labels: tuple) -> tuple:
    """Find the smallest P-baseline today does NOT beat (the next 'wall').

    Returns (label, gap_pct) where gap_pct is (today - p) / p * 100, negative
    means today is below the wall. None,None if today beats all five (clean SS).
    """
    if today_v is None:
        return None, None
    candidates = []
    for label, p in zip(p_labels, p_baselines):
        if p is None or p <= 0:
            continue
        if today_v <= p:
            candidates.append((p, label))
    if not candidates:
        return None, None
    # Smallest p-baseline today fails to beat = the closest wall above.
    candidates.sort()
    p, label = candidates[0]
    gap_pct = (today_v - p) / p * 100.0
    return label, gap_pct


def _hot_days_avg_close(prior_rows) -> Optional[float]:
    """Avg close on the last 10 prior days where that day's DVPT exceeded its
    own 1m power baseline (top-5 avg of preceding 22 days). Used to anchor the
    'price vs where smart money was buying' (D26 / D28). None if <1 hot day.
    """
    if not prior_rows:
        return None
    cap = min(len(prior_rows), 250)
    dvpts = []
    closes = []
    for r in prior_rows[:cap]:
        v = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        dvpts.append(v)
        closes.append(r["close"])

    hot_closes = []
    for i in range(len(dvpts)):
        today_v = dvpts[i]
        if today_v is None:
            continue
        baseline_window = [v for v in dvpts[i + 1 : i + 1 + 22] if v is not None]
        if len(baseline_window) < 22:
            continue
        top5 = sorted(baseline_window, reverse=True)[:5]
        if not top5:
            continue
        power_1m = sum(top5) / len(top5)
        if power_1m <= 0:
            continue
        if today_v / power_1m > 1.0 and closes[i] is not None and closes[i] > 0:
            hot_closes.append(closes[i])
            if len(hot_closes) == 10:
                break
    if not hot_closes:
        return None
    return sum(hot_closes) / len(hot_closes)


_SIGNAL_COLS = [
    "symbol", "trade_date",
    "delivery_value_today", "total_value_today", "delivery_value_per_trade",
    # Legacy trading-day windows (kept for /dvpt history table)
    "avg_dvpt_5d", "avg_dvpt_10d", "avg_dvpt_30d", "avg_dvpt_60d",
    "avg_dvpt_90d", "avg_dvpt_180d", "avg_dvpt_365d",
    # D31 R-tier (calendar-day flat averages: 30/60/90/180/360)
    "avg_dvpt_1m", "avg_dvpt_2m", "avg_dvpt_3m", "avg_dvpt_6m", "avg_dvpt_12m",
    # D31 P-tier (top-N within calendar-day window: 4/30, 7/60, 12/90, 20/180, 30/360)
    "power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m", "power_dvpt_6m", "power_dvpt_12m",
    # D31 institutional price zones (avg close on baseline days, R + P)
    "avg_close_r1m", "avg_close_r2m", "avg_close_r3m", "avg_close_r6m", "avg_close_r12m",
    "avg_close_p1m", "avg_close_p2m", "avg_close_p3m", "avg_close_p6m", "avg_close_p12m",
    # Legacy ratios
    "ratio_today_vs_avg_30d", "ratio_today_vs_power_1m", "ratio_today_vs_power_3m",
    "data_points_used",
    # Two-tier triggers (D28 logic, D31 baselines)
    "r_score", "p_score", "trigger_rank",
    "is_ath_dvpt", "hot_days_avg_price", "price_vs_hot_avg_pct",
    "next_p_above", "gap_to_next_p_pct",
]


def store_signal(signal: dict) -> None:
    placeholders = ",".join("?" * len(_SIGNAL_COLS))
    sql = (
        f"INSERT OR REPLACE INTO stock_signals ({','.join(_SIGNAL_COLS)}) "
        f"VALUES ({placeholders})"
    )
    with get_conn() as conn:
        conn.execute(sql, [signal.get(c) for c in _SIGNAL_COLS])


def signal_exists(symbol: str, trade_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM stock_signals WHERE symbol = ? AND trade_date = ?",
            (symbol, trade_date),
        ).fetchone()
        return row is not None


# --- Modes -----------------------------------------------------------------

def compute_for_date(trade_date: str) -> int:
    """Compute signals for every symbol that traded on trade_date. Returns count."""
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE trade_date = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol""",
            (trade_date,),
        ).fetchall()]

    if not symbols:
        log.info("no symbols for %s — nothing to compute", trade_date)
        return 0

    log.info("computing signals for %d symbols on %s", len(symbols), trade_date)
    n = 0
    for i, sym in enumerate(symbols, 1):
        if signal_exists(sym, trade_date):
            continue
        sig = compute_signals_for_symbol_date(sym, trade_date)
        if sig and sig.get("delivery_value_per_trade") is not None:
            store_signal(sig)
            n += 1
        if i % 200 == 0:
            log.info("  progress: %d / %d", i, len(symbols))
    log.info("date %s done: %d signals stored", trade_date, n)
    return n


def run_today() -> tuple[bool, str]:
    """Compute signals for the most recent trade_date in bhavcopy_rows."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM bhavcopy_rows"
        ).fetchone()
    if not row or not row["d"]:
        return False, "no bhav data found"
    n = compute_for_date(row["d"])
    return True, f"computed {n} signals for {row['d']}"


def run_backfill() -> tuple[int, int]:
    """Compute signals for every date in bhavcopy_dates where missing."""
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT trade_date FROM bhavcopy_dates ORDER BY trade_date ASC"
        ).fetchall()]
    log.info("backfill: %d dates to potentially process", len(dates))
    total = 0
    for d in dates:
        n = compute_for_date(d)
        total += n
        time.sleep(0.05)  # let other DB writes through
    return len(dates), total


# --- Two-tier + price-zone trigger backfill (D28 + D31) --------------------

def _backfill_triggers_for_symbol(conn, symbol: str) -> int:
    """For one symbol: walk every (symbol, trade_date) in stock_signals and
    populate ALL D28 + D31 fields (R/P-tier baselines under calendar-day
    windowing, scores, rank, ATH, hot-day, near-break, AND the 10 institutional
    price-zone columns). Per-symbol bulk fetch + batch UPDATE.
    """
    bhav = conn.execute(
        """SELECT trade_date, close, deliv_qty, num_trades
           FROM bhavcopy_rows
           WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY trade_date ASC""",
        (symbol,),
    ).fetchall()
    if not bhav:
        return 0

    n = len(bhav)
    dvpts  = [None] * n
    closes = [None] * n
    dates  = [None] * n
    for i, r in enumerate(bhav):
        dvpts[i]  = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        closes[i] = r["close"]
        dates[i]  = r["trade_date"]
    date_to_idx = {d: i for i, d in enumerate(dates)}

    # Running ATH-DVPT max over strictly-prior history.
    prior_max = None

    sig_dates = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM stock_signals WHERE symbol = ? ORDER BY trade_date ASC",
        (symbol,),
    ).fetchall()]

    updates = []
    for d in sig_dates:
        i = date_to_idx.get(d)
        if i is None:
            continue
        today_v = dvpts[i]
        # ATH check uses strictly-prior values.
        if today_v is not None:
            is_ath = 1 if (prior_max is not None and today_v > prior_max) else 0
            if prior_max is None or today_v > prior_max:
                prior_max = today_v
        else:
            is_ath = None

        # Build the strictly-prior baseline list for THIS date `d`.
        # We need (date, dvpt, close) for every prior trade with non-None dvpt.
        prior = []
        for j in range(i):
            if dvpts[j] is None:
                continue
            prior.append((dates[j], dvpts[j], closes[j]))

        # Slice helpers — calendar-day windows on the prior list.
        def window_subset(days: int):
            cutoff = _cutoff_date(d, days)
            return [x for x in prior if x[0] >= cutoff]

        def r_stats(days: int):
            sub = window_subset(days)
            if not sub:
                return None, None
            avg_dvpt  = sum(x[1] for x in sub) / len(sub)
            cls       = [x[2] for x in sub if x[2] is not None]
            avg_close = (sum(cls) / len(cls)) if cls else None
            return avg_dvpt, avg_close

        def p_stats(days: int, top_n: int):
            sub = window_subset(days)
            if not sub:
                return None, None
            top = sorted(sub, key=lambda x: x[1], reverse=True)[:top_n]
            if not top:
                return None, None
            avg_dvpt  = sum(x[1] for x in top) / len(top)
            cls       = [x[2] for x in top if x[2] is not None]
            avg_close = (sum(cls) / len(cls)) if cls else None
            return avg_dvpt, avg_close

        r_dvpts  = []
        r_closes = []
        p_dvpts  = []
        p_closes = []
        for _label, win_days, top_n in _WINDOWS:
            rd, rc = r_stats(win_days)
            pd, pc = p_stats(win_days, top_n)
            r_dvpts.append(rd);  r_closes.append(rc)
            p_dvpts.append(pd);  p_closes.append(pc)

        r_score = _count_beaten(today_v, r_dvpts)
        p_score = _count_beaten(today_v, p_dvpts)
        rank = _rank_from_p_score(p_score)
        next_above, gap = _next_p_above(today_v, p_dvpts, _P_LABELS)

        # Hot-days avg close (same definition as D28 — last 10 prior days
        # where that day's DVPT exceeded its own 1m power baseline of
        # top-5 of the 22 trading days immediately preceding it).
        hot_closes = []
        j = i - 1
        while j >= 0 and len(hot_closes) < 10:
            v_j = dvpts[j]
            if v_j is not None and (j - 22) >= 0:
                sub = [v for v in dvpts[j - 22 : j] if v is not None]
                if len(sub) >= 22:
                    top5 = sorted(sub, reverse=True)[:5]
                    p1m_j = sum(top5) / len(top5)
                    if p1m_j > 0 and v_j / p1m_j > 1.0 and closes[j] is not None and closes[j] > 0:
                        hot_closes.append(closes[j])
            j -= 1
        hot_avg = (sum(hot_closes) / len(hot_closes)) if hot_closes else None
        if hot_avg is not None and closes[i] is not None and hot_avg > 0:
            pvh = (closes[i] - hot_avg) / hot_avg * 100.0
        else:
            pvh = None

        updates.append((
            # avg_dvpt_1m..12m (R-tier DVPT baselines, calendar-day)
            r_dvpts[0], r_dvpts[1], r_dvpts[2], r_dvpts[3], r_dvpts[4],
            # power_dvpt_1m..12m (P-tier DVPT baselines, calendar-day, new top-N)
            p_dvpts[0], p_dvpts[1], p_dvpts[2], p_dvpts[3], p_dvpts[4],
            # avg_close_r1m..r12m (R-tier price zones)
            r_closes[0], r_closes[1], r_closes[2], r_closes[3], r_closes[4],
            # avg_close_p1m..p12m (P-tier price zones)
            p_closes[0], p_closes[1], p_closes[2], p_closes[3], p_closes[4],
            # Scores + rank + ATH + hot + near-break
            r_score, p_score, rank,
            is_ath, hot_avg, pvh,
            next_above, gap,
            # WHERE clause
            symbol, d,
        ))

    if updates:
        conn.executemany(
            """UPDATE stock_signals
                  SET avg_dvpt_1m   = ?, avg_dvpt_2m   = ?, avg_dvpt_3m   = ?,
                      avg_dvpt_6m   = ?, avg_dvpt_12m  = ?,
                      power_dvpt_1m = ?, power_dvpt_2m = ?, power_dvpt_3m = ?,
                      power_dvpt_6m = ?, power_dvpt_12m = ?,
                      avg_close_r1m = ?, avg_close_r2m = ?, avg_close_r3m = ?,
                      avg_close_r6m = ?, avg_close_r12m = ?,
                      avg_close_p1m = ?, avg_close_p2m = ?, avg_close_p3m = ?,
                      avg_close_p6m = ?, avg_close_p12m = ?,
                      r_score = ?, p_score = ?, trigger_rank = ?,
                      is_ath_dvpt = ?, hot_days_avg_price = ?, price_vs_hot_avg_pct = ?,
                      next_p_above = ?, gap_to_next_p_pct = ?
                WHERE symbol = ? AND trade_date = ?""",
            updates,
        )
    return len(updates)


def run_backfill_triggers() -> tuple[int, int]:
    """Populate all D28 two-tier columns for every existing stock_signals row.

    Per-symbol bulk-load → batch UPDATE. Expected runtime ~20-30 min on the
    VPS for the current 2.35M-row baseline.
    """
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM stock_signals ORDER BY symbol"
        ).fetchall()]
    log.info("backfill-triggers: %d symbols to walk", len(symbols))

    total_rows = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            try:
                total_rows += _backfill_triggers_for_symbol(conn, sym)
            except Exception as e:
                log.warning("backfill-triggers failed for %s: %s", sym, e)
        if k % 100 == 0:
            log.info("  progress: %d / %d symbols, %d rows updated", k, len(symbols), total_rows)
    log.info("backfill-triggers complete: %d symbols, %d rows updated",
             len(symbols), total_rows)
    return len(symbols), total_rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--backfill-triggers", action="store_true",
                   help="Populate D28 two-tier columns (r_score, p_score, "
                        "trigger_rank, ATH, hot-day avg, near-break) for every "
                        "existing stock_signals row. Per-symbol bulk fetch + UPDATE.")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    p.add_argument("--symbol", type=str, help="compute one symbol's latest signal")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.symbol:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT MAX(trade_date) AS d FROM bhavcopy_rows WHERE symbol = ?",
                (args.symbol.upper(),),
            ).fetchone()
        if not row or not row["d"]:
            log.warning("no bhav data for %s", args.symbol)
            return
        sig = compute_signals_for_symbol_date(args.symbol.upper(), row["d"])
        if sig:
            store_signal(sig)
            log.info("computed signal for %s @ %s: dvpt=%.0f ratio_power_1m=%s",
                     args.symbol, row["d"],
                     sig.get("delivery_value_per_trade") or 0,
                     sig.get("ratio_today_vs_power_1m"))
    elif args.backfill:
        n_dates, total = run_backfill()
        log.info("backfill complete: %d dates, %d signals stored", n_dates, total)
    elif args.backfill_triggers:
        n_syms, n_rows = run_backfill_triggers()
        log.info("trigger backfill complete: %d symbols, %d rows updated",
                 n_syms, n_rows)
    elif args.date:
        compute_for_date(args.date)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
