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
        # Flat averages
        "avg_dvpt_5d":   flat_avg(5),
        "avg_dvpt_10d":  flat_avg(10),
        "avg_dvpt_30d":  flat_avg(30),
        "avg_dvpt_60d":  flat_avg(60),
        "avg_dvpt_90d":  flat_avg(90),
        "avg_dvpt_180d": flat_avg(180),
        "avg_dvpt_365d": flat_avg(365),
        # Power deliveries
        "power_dvpt_1m": power_avg(22, 5),
        "power_dvpt_2m": power_avg(44, 10),
        "power_dvpt_3m": power_avg(66, 15),
        "power_dvpt_6m": power_avg(132, 40),
        # Ratios — computed below
        "ratio_today_vs_avg_30d":  None,
        "ratio_today_vs_power_1m": None,
        "ratio_today_vs_power_3m": None,
        "data_points_used": n_baseline,
    }
    signal["ratio_today_vs_avg_30d"]  = safe_ratio(today_dvpt, signal["avg_dvpt_30d"])
    signal["ratio_today_vs_power_1m"] = safe_ratio(today_dvpt, signal["power_dvpt_1m"])
    signal["ratio_today_vs_power_3m"] = safe_ratio(today_dvpt, signal["power_dvpt_3m"])
    return signal


_SIGNAL_COLS = [
    "symbol", "trade_date",
    "delivery_value_today", "total_value_today", "delivery_value_per_trade",
    "avg_dvpt_5d", "avg_dvpt_10d", "avg_dvpt_30d", "avg_dvpt_60d",
    "avg_dvpt_90d", "avg_dvpt_180d", "avg_dvpt_365d",
    "power_dvpt_1m", "power_dvpt_2m", "power_dvpt_3m", "power_dvpt_6m",
    "ratio_today_vs_avg_30d", "ratio_today_vs_power_1m", "ratio_today_vs_power_3m",
    "data_points_used",
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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
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
    elif args.date:
        compute_for_date(args.date)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
