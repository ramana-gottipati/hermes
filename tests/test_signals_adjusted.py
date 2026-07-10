"""AUD-06/07/11 golden regression — zones/hot/key-price on adjusted closes,
and the nightly↔backfill agreement contract.

Synthetic 400-trading-day series with a 1:10 split at day 200 (tape event
present, exactly like a real corp_actions row). Asserts:

  1. Zone averages (avg_close_r*/p*), hot_days_avg_price and key_price_p* on
     the NEWEST date land in the post-split price scale (~100), never the
     mixed/raw scale (~500-1000) that AUD-06 produced.
  2. GOLDEN AGREEMENT (AUD-07): for a pre-split date AND a post-split date,
     the backfill path stores byte-close values to what the realtime path
     computes fresh for the same (symbol, date) — one definition, two paths.
  3. Key-price backfill on a PRE-split date lands in THAT date's own price
     basis (the historical basis-mix regression).

Stdlib-only; run:  python tests/test_signals_adjusted.py
"""
import contextlib
import os
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.automation import signals  # noqa: E402

SYM = "SPLITCO"
N_DAYS = 400
SPLIT_I = 200          # 1:10 split takes effect on this row's date
RATIO = 0.1

FAILS = []


def check(name, cond, detail=""):
    print("  %s %s%s" % ("ok  " if cond else "FAIL", name,
                         (" — " + str(detail)) if (detail and not cond) else ""))
    if not cond:
        FAILS.append(name)


def _trading_days(n):
    out, d = [], date(2025, 1, 1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def build_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE bhavcopy_rows (
        symbol TEXT, series TEXT, segment TEXT, trade_date TEXT,
        close REAL, prev_close REAL, avg_price REAL, value REAL, volume REAL,
        deliv_qty REAL, deliv_per REAL, num_trades REAL)""")
    conn.execute("""CREATE TABLE stock_signals (
        symbol TEXT, trade_date TEXT, delivery_value_per_trade REAL,
        avg_dvpt_1m REAL, avg_dvpt_2m REAL, avg_dvpt_3m REAL, avg_dvpt_6m REAL, avg_dvpt_12m REAL,
        power_dvpt_1m REAL, power_dvpt_2m REAL, power_dvpt_3m REAL, power_dvpt_6m REAL, power_dvpt_12m REAL,
        avg_close_r1m REAL, avg_close_r2m REAL, avg_close_r3m REAL, avg_close_r6m REAL, avg_close_r12m REAL,
        avg_close_p1m REAL, avg_close_p2m REAL, avg_close_p3m REAL, avg_close_p6m REAL, avg_close_p12m REAL,
        r_score INTEGER, p_score INTEGER, trigger_rank TEXT,
        is_ath_dvpt INTEGER, hot_days_avg_price REAL, price_vs_hot_avg_pct REAL,
        next_p_above TEXT, gap_to_next_p_pct REAL,
        deliv_value_ratio_1m_6m REAL, trade_count_ratio_1m_6m REAL, ticket_ratio_1m_6m REAL,
        avg_deliv_pct_1m REAL, avg_deliv_pct_6m REAL,
        deliv_updown_ratio_3m REAL, accum_price_drift_3m REAL,
        pct_from_52w_high REAL, accum_character TEXT,
        key_price_p1m REAL, key_price_p2m REAL, key_price_p3m REAL, key_price_p6m REAL, key_price_p12m REAL,
        gap_to_key_p1m REAL, gap_to_key_p2m REAL, gap_to_key_p3m REAL, gap_to_key_p6m REAL, gap_to_key_p12m REAL,
        avg_trade_qty REAL, avg_deliv_qty_per_trade REAL,
        turnover_surge_1m REAL, turnover_surge_3m REAL, turnover_surge_1y REAL)""")

    dates = _trading_days(N_DAYS)
    prev = None
    for i, d in enumerate(dates):
        level = 1000.0 + i * 0.5                      # gently rising adjusted path
        close = level if i < SPLIT_I else level * RATIO
        qty = (10000.0 if i < SPLIT_I else 100000.0)  # shares ×10 across the split
        if i % 10 == 3:                               # periodic institutional day
            qty *= 3.0
        volume = qty * 2.0
        conn.execute(
            "INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (SYM, "EQ", "CM", d, close, prev, close * 0.999, close * volume,
             volume, qty, 50.0, 1000.0),
        )
        conn.execute(
            "INSERT INTO stock_signals (symbol, trade_date) VALUES (?, ?)",
            (SYM, d),
        )
        prev = close
    conn.commit()
    return conn, dates


def main():
    conn, dates = build_db()
    split_date = dates[SPLIT_I]
    tape = {split_date: RATIO}

    @contextlib.contextmanager
    def fake_get_conn():
        yield conn

    signals.get_conn = fake_get_conn
    signals._action_events = lambda _conn, _sym: dict(tape)

    last = dates[-1]
    pre = dates[150]        # pre-split date whose 12m window is pre-split only
    post = dates[380]       # post-split date whose 12m window SPANS the split

    # ── 1. realtime on the newest date: everything in post-split scale ──────
    sig = signals.compute_signals_for_symbol_date(SYM, last)
    check("realtime computes", sig is not None)
    lo, hi = 80.0, 130.0
    for col in ("avg_close_p12m", "avg_close_r12m", "hot_days_avg_price",
                "key_price_p12m"):
        v = sig.get(col)
        check(f"{col} in post-split scale", v is not None and lo <= v <= hi, v)
    g = sig.get("gap_to_key_p12m")
    check("gap_to_key_p12m sane (<50%)", g is not None and abs(g) < 50.0, g)
    pvh = sig.get("price_vs_hot_avg_pct")
    check("price_vs_hot_avg_pct sane (<50%)", pvh is not None and abs(pvh) < 50.0, pvh)

    # ── 2. run both backfills, then golden agreement on pre+post dates ──────
    n1 = signals._backfill_triggers_for_symbol(conn, SYM)
    n2 = signals._backfill_keyprice_for_symbol(conn, SYM)
    conn.commit()
    check("backfills wrote rows", n1 > 300 and n2 > 300, (n1, n2))

    AGREE_COLS = [
        "avg_dvpt_1m", "avg_dvpt_3m", "avg_dvpt_12m",
        "power_dvpt_1m", "power_dvpt_3m", "power_dvpt_12m",
        "avg_close_r1m", "avg_close_r3m", "avg_close_r12m",
        "avg_close_p1m", "avg_close_p3m", "avg_close_p12m",
        "r_score", "p_score", "hot_days_avg_price", "price_vs_hot_avg_pct",
        "gap_to_next_p_pct",
    ]
    for d in (pre, post):
        fresh = signals.compute_signals_for_symbol_date(SYM, d)
        stored = conn.execute(
            "SELECT * FROM stock_signals WHERE symbol=? AND trade_date=?",
            (SYM, d),
        ).fetchone()
        for col in AGREE_COLS:
            a, b = fresh.get(col), stored[col]
            if a is None and b is None:
                agree = True
            elif a is None or b is None:
                agree = False
            elif isinstance(a, float) or isinstance(b, float):
                agree = abs(float(a) - float(b)) <= max(1e-6, abs(float(a)) * 1e-9)
            else:
                agree = a == b
            check(f"nightly==backfill {col} @ {d}", agree, (a, b))

    # ── 3. historical key-price basis: pre-split row lives in its own scale ─
    kp_pre = conn.execute(
        "SELECT key_price_p12m, gap_to_key_p12m FROM stock_signals "
        "WHERE symbol=? AND trade_date=?", (SYM, pre),
    ).fetchone()
    check("pre-split key_price_p12m in PRE-split scale",
          kp_pre[0] is not None and 700.0 <= kp_pre[0] <= 1300.0, kp_pre[0])
    check("pre-split gap_to_key_p12m sane (<50%)",
          kp_pre[1] is not None and abs(kp_pre[1]) < 50.0, kp_pre[1])

    print("test_signals_adjusted:", "OK" if not FAILS else f"FAILED ({len(FAILS)})")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
