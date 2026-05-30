"""Per-stock rolling delivery-value signals.

For each (symbol, trade_date), compute:
  - Today's delivery_value_per_trade = (deliv_qty * close) / no_of_trades
  - Flat rolling averages over 5/10/30/60/90/180/365 trading days (excluding today)
  - 'Power deliveries' — average of top-N within a window:
      1m → top 5 of last 22 trading days
      2m → top 10 of last 44
      3m → top 15 of last 66
      6m → top 40 of last 132
  - Ratios: today vs avg_30d, today vs power_1m, today vs power_3m

Stored nightly into stock_signals table; queries become instant lookups.

Usage:
    python -m src.automation.signals                        # compute today's row for every stock that has bhav data today
    python -m src.automation.signals --backfill             # compute signals for ALL historical days where missing
    python -m src.automation.signals --symbol RELIANCE      # one stock only (for debugging)
"""

import argparse
import logging
import time
from typing import Optional

from src.core.db import get_conn

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


def compute_signals_for_symbol_date(symbol: str, trade_date: str) -> Optional[dict]:
    """Compute the full signal row for one (symbol, trade_date).

    Reads the last ~365 trading days from bhavcopy_rows ending at trade_date,
    derives delivery_value_per_trade per day, then computes all rolling stats.

    Returns None if there's insufficient data (e.g. stock just listed).
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, close, value, deliv_qty, num_trades
            FROM bhavcopy_rows
            WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
              AND trade_date <= ?
            ORDER BY trade_date DESC
            LIMIT 366
            """,
            (symbol, trade_date),
        ).fetchall()

    if not rows:
        return None

    # rows[0] is the target trade_date
    today_row = rows[0]
    if today_row["trade_date"] != trade_date:
        # The symbol didn't actually trade on trade_date
        return None

    today_dvpt = _delivery_value_per_trade(
        today_row["deliv_qty"], today_row["close"], today_row["num_trades"]
    )
    today_dv = _delivery_value(today_row["deliv_qty"], today_row["close"])
    today_total = today_row["value"]

    # Baseline = the rows BEFORE today (we already have them in rows[1:])
    baseline = []
    for r in rows[1:]:
        v = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        if v is not None:
            baseline.append(v)

    n_baseline = len(baseline)

    def flat_avg(window: int) -> Optional[float]:
        if window > n_baseline:
            return None
        sub = baseline[:window]
        return sum(sub) / len(sub) if sub else None

    def power_avg(window: int, top_n: int) -> Optional[float]:
        if window > n_baseline:
            return None
        sub = baseline[:window]
        top = sorted(sub, reverse=True)[:top_n]
        return sum(top) / len(top) if top else None

    def safe_ratio(num, den) -> Optional[float]:
        if num is None or den is None or den <= 0:
            return None
        return num / den

    signal = {
        "symbol": symbol,
        "trade_date": trade_date,
        "delivery_value_today": today_dv,
        "total_value_today": today_total,
        "delivery_value_per_trade": today_dvpt,
        # Legacy flat averages (kept for /dvpt single-stock detail history)
        "avg_dvpt_5d":   flat_avg(5),
        "avg_dvpt_10d":  flat_avg(10),
        "avg_dvpt_30d":  flat_avg(30),
        "avg_dvpt_60d":  flat_avg(60),
        "avg_dvpt_90d":  flat_avg(90),
        "avg_dvpt_180d": flat_avg(180),
        "avg_dvpt_365d": flat_avg(365),
        # R-tier — rolling averages aligned with P-tier windows (D28)
        "avg_dvpt_1m":   flat_avg(22),
        "avg_dvpt_2m":   flat_avg(44),
        "avg_dvpt_3m":   flat_avg(66),
        "avg_dvpt_6m":   flat_avg(132),
        "avg_dvpt_12m":  flat_avg(264),
        # P-tier — top-N within window (5/22, 10/44, 15/66, 40/132, 80/264)
        "power_dvpt_1m":  power_avg(22, 5),
        "power_dvpt_2m":  power_avg(44, 10),
        "power_dvpt_3m":  power_avg(66, 15),
        "power_dvpt_6m":  power_avg(132, 40),
        "power_dvpt_12m": power_avg(264, 80),
        # Ratios — preserved for /dvpt detail
        "ratio_today_vs_avg_30d":  None,
        "ratio_today_vs_power_1m": None,
        "ratio_today_vs_power_3m": None,
        "data_points_used": n_baseline,
    }
    signal["ratio_today_vs_avg_30d"]  = safe_ratio(today_dvpt, signal["avg_dvpt_30d"])
    signal["ratio_today_vs_power_1m"] = safe_ratio(today_dvpt, signal["power_dvpt_1m"])
    signal["ratio_today_vs_power_3m"] = safe_ratio(today_dvpt, signal["power_dvpt_3m"])

    # --- Two-tier scoring + layered triggers (Decision D28) -------------
    r_keys = ("avg_dvpt_1m", "avg_dvpt_2m", "avg_dvpt_3m", "avg_dvpt_6m", "avg_dvpt_12m")
    p_keys = ("power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m", "power_dvpt_6m", "power_dvpt_12m")
    p_labels = ("P1M", "P2M", "P3M", "P6M", "P12M")

    r_score = _count_beaten(today_dvpt, [signal[k] for k in r_keys])
    p_score = _count_beaten(today_dvpt, [signal[k] for k in p_keys])
    signal["r_score"] = r_score
    signal["p_score"] = p_score
    signal["trigger_rank"] = _rank_from_p_score(p_score)

    next_above, gap = _next_p_above(today_dvpt, [signal[k] for k in p_keys], p_labels)
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
    # Legacy R-windows (kept for /dvpt history)
    "avg_dvpt_5d", "avg_dvpt_10d", "avg_dvpt_30d", "avg_dvpt_60d",
    "avg_dvpt_90d", "avg_dvpt_180d", "avg_dvpt_365d",
    # R-tier (D28)
    "avg_dvpt_1m", "avg_dvpt_2m", "avg_dvpt_3m", "avg_dvpt_6m", "avg_dvpt_12m",
    # P-tier
    "power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m", "power_dvpt_6m", "power_dvpt_12m",
    # Legacy ratios
    "ratio_today_vs_avg_30d", "ratio_today_vs_power_1m", "ratio_today_vs_power_3m",
    "data_points_used",
    # Two-tier triggers (D28)
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


# --- Two-tier trigger backfill (D28) ---------------------------------------

_P_WINDOWS = ((22, 5, "P1M"), (44, 10, "P2M"), (66, 15, "P3M"),
              (132, 40, "P6M"), (264, 80, "P12M"))
_R_WINDOWS = (22, 44, 66, 132, 264)


def _backfill_triggers_for_symbol(conn, symbol: str) -> int:
    """For one symbol: walk every (symbol, trade_date) in stock_signals and
    populate the D28 two-tier fields using one bulk fetch of the symbol's
    bhav history. Batch UPDATE.
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
    dvpts = [None] * n
    closes = [None] * n
    dates = [None] * n
    for i, r in enumerate(bhav):
        dvpts[i] = _delivery_value_per_trade(r["deliv_qty"], r["close"], r["num_trades"])
        closes[i] = r["close"]
        dates[i] = r["trade_date"]
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

        # Compute R-tier (flat avg of prior `window` days) and P-tier
        # (top-N of prior `window` days) baselines from in-memory dvpts.
        def flat_avg(window):
            if i - window < 0:
                return None
            sub = [v for v in dvpts[i - window : i] if v is not None]
            if len(sub) < window:
                return None
            return sum(sub) / len(sub)

        def power_avg(window, top_n):
            if i - window < 0:
                return None
            sub = [v for v in dvpts[i - window : i] if v is not None]
            if len(sub) < window:
                return None
            top = sorted(sub, reverse=True)[:top_n]
            return sum(top) / len(top) if top else None

        r_bases = [flat_avg(w) for w in _R_WINDOWS]
        p_bases = [power_avg(w, n_top) for (w, n_top, _) in _P_WINDOWS]
        p_labels = tuple(label for (_, _, label) in _P_WINDOWS)

        r_score = _count_beaten(today_v, r_bases)
        p_score = _count_beaten(today_v, p_bases)
        rank = _rank_from_p_score(p_score)
        next_above, gap = _next_p_above(today_v, p_bases, p_labels)

        # Hot-days avg close — walk backwards from i-1, the same logic as
        # `_hot_days_avg_close` but using our pre-computed dvpts/closes.
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

        # All five R + five P baselines also go into the row, since the
        # nightly compute path will populate them for new rows and the
        # backfill should fill them on historical rows too (so /dvpt
        # detail view shows the same shape everywhere).
        updates.append((
            r_bases[0], r_bases[1], r_bases[2], r_bases[3], r_bases[4],
            p_bases[4],  # power_dvpt_12m (the new column)
            r_score, p_score, rank,
            is_ath, hot_avg, pvh,
            next_above, gap,
            symbol, d,
        ))

    if updates:
        conn.executemany(
            """UPDATE stock_signals
                  SET avg_dvpt_1m  = ?, avg_dvpt_2m  = ?, avg_dvpt_3m  = ?,
                      avg_dvpt_6m  = ?, avg_dvpt_12m = ?,
                      power_dvpt_12m = ?,
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
