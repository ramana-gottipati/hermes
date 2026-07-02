"""Backfill SHORT-horizon (1-week / 2-week) RS momentum + RSI-of-RS.

Roadmap Phase 2 (docs/rs-momentum-divergence-roadmap.md). Ramana's ask: the RSI-of-RS
exists only at the long horizon — add 1w and 2w so the recovery ladder can light its
earliest rungs and the horizon heat-strip can show momentum building short→long.

ADDITIVE + IDEMPOTENT + ISOLATED. NEW file; edits nothing. Adds nullable columns via
db._ensure_column (never touches db.py) and fills them from the ALREADY-computed clean
RS line:
  * sectors/indices → rs_extras.rs_ratio          → rs_extras.{rs_1w_pct,rs_2w_pct,rsi_of_rs_1w,rsi_of_rs_2w}
  * stocks          → stock_signals.rs_vs_broad_today → stock_signals.{rs_vs_broad_1w,rs_vs_broad_2w,rsi_of_rs_1w,rsi_of_rs_2w}

Short-horizon defs: RS_Nw = %Δ of the RS line over N*5 trading days; RSI period ~5 (1w)
and ~10 (2w), Wilder, on the RS line itself. Value-based/self-scaling; no static thresholds.

⚠ WRITES DATA. Runs on the VPS (the box with the populated DB). Owner-run:
    /opt/hermes/.venv/bin/python scripts/backfill_rs_short_horizons.py --sectors --stocks
Dry-run first:  ... --sectors --stocks --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# repo root on path so `python scripts/backfill_rs_short_horizons.py` finds `src` (VPS-safe).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("hermes.backfill_rs_short")

# additive nullable columns (never edit db.py); {table: [(col, decl), ...]}
_COLS = {
    "rs_extras": [("rs_1w_pct", "REAL"), ("rs_2w_pct", "REAL"),
                  ("rsi_of_rs_1w", "REAL"), ("rsi_of_rs_2w", "REAL")],
    "stock_signals": [("rs_vs_broad_1w", "REAL"), ("rs_vs_broad_2w", "REAL"),
                      ("rsi_of_rs_1w", "REAL"), ("rsi_of_rs_2w", "REAL")],
}
_W1, _W2 = 5, 10          # trading days for 1-week / 2-week horizons
_P1, _P2 = 5, 10          # Wilder RSI periods for 1w / 2w


def _wilder_rsi(vals, period: int):
    """Wilder's RSI over the whole series; None until `period` bars are available."""
    out = [None] * len(vals)
    if len(vals) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / period, losses / period
    out[period] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(period + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def _pct(vals, i: int, n: int):
    j = i - n
    if j < 0 or vals[j] in (None, 0):
        return None
    return (vals[i] / vals[j] - 1.0) * 100.0


def _tables(conn) -> set:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _ensure(conn) -> None:
    from src.core.db import _ensure_column
    present = _tables(conn)
    for table, cols in _COLS.items():
        if table not in present:
            log.warning("skip %s (absent)", table)
            continue
        for col, decl in cols:
            _ensure_column(conn, table, col, decl)


def _series_rows(vals):
    """(rsi1[], rsi2[], pct1[], pct2[]) computed for a single ordered RS line."""
    rsi1 = _wilder_rsi(vals, _P1)
    rsi2 = _wilder_rsi(vals, _P2)
    pct1 = [_pct(vals, i, _W1) for i in range(len(vals))]
    pct2 = [_pct(vals, i, _W2) for i in range(len(vals))]
    return rsi1, rsi2, pct1, pct2


def _run_group(conn, keys, dates, vals, sql, dry, counters):
    rsi1, rsi2, pct1, pct2 = _series_rows(vals)
    for i, dt in enumerate(dates):
        if rsi1[i] is None and pct1[i] is None:
            continue
        counters["rows"] += 1
        if not dry:
            conn.execute(sql, (pct1[i], pct2[i], rsi1[i], rsi2[i], *keys, dt))


def backfill_sectors(conn, dry: bool) -> dict:
    c = {"groups": 0, "rows": 0}
    if "rs_extras" not in _tables(conn):
        return c
    pairs = conn.execute("SELECT DISTINCT numerator, denominator FROM rs_extras").fetchall()
    sql = ("UPDATE rs_extras SET rs_1w_pct=?, rs_2w_pct=?, rsi_of_rs_1w=?, rsi_of_rs_2w=? "
           "WHERE numerator=? AND denominator=? AND trade_date=?")
    for num, den in pairs:
        rows = conn.execute(
            "SELECT trade_date, rs_ratio FROM rs_extras "
            "WHERE numerator=? AND denominator=? AND rs_ratio IS NOT NULL ORDER BY trade_date",
            (num, den)).fetchall()
        if len(rows) <= _P2:
            continue
        c["groups"] += 1
        _run_group(conn, (num, den), [r[0] for r in rows], [float(r[1]) for r in rows],
                   sql, dry, c)
        if not dry:
            conn.commit()
    return c


def backfill_stocks(conn, dry: bool, limit: int | None) -> dict:
    c = {"groups": 0, "rows": 0}
    if "stock_signals" not in _tables(conn):
        return c
    cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_signals)").fetchall()}
    if "rs_vs_broad_today" not in cols:
        log.warning("stock_signals has no rs_vs_broad_today — skipping stocks")
        return c
    syms = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM stock_signals WHERE rs_vs_broad_today IS NOT NULL"
        + (f" LIMIT {int(limit)}" if limit else "")).fetchall()]
    sql = ("UPDATE stock_signals SET rs_vs_broad_1w=?, rs_vs_broad_2w=?, "
           "rsi_of_rs_1w=?, rsi_of_rs_2w=? WHERE symbol=? AND trade_date=?")
    for sym in syms:
        rows = conn.execute(
            "SELECT trade_date, rs_vs_broad_today FROM stock_signals "
            "WHERE symbol=? AND rs_vs_broad_today IS NOT NULL ORDER BY trade_date",
            (sym,)).fetchall()
        if len(rows) <= _P2:
            continue
        c["groups"] += 1
        _run_group(conn, (sym,), [r[0] for r in rows], [float(r[1]) for r in rows],
                   sql, dry, c)
        if not dry:
            conn.commit()
    return c


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill 1w/2w RS momentum + RSI-of-RS (additive).")
    p.add_argument("--sectors", action="store_true", help="backfill rs_extras (sectors/indices)")
    p.add_argument("--stocks", action="store_true", help="backfill stock_signals (stocks)")
    p.add_argument("--limit", type=int, default=None, help="cap #stocks (testing)")
    p.add_argument("--dry-run", action="store_true", help="compute + count, write nothing")
    p.add_argument("--selftest", action="store_true", help="unit-test the RSI math, no DB")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.selftest:
        r = _wilder_rsi([1, 2, 3, 4, 5, 6, 7, 8], 5)
        assert r[5] == 100.0 and r[4] is None, r      # all-up ⇒ RSI 100 once seeded
        assert abs(_pct([100, 105], 1, 1) - 5.0) < 1e-9
        print("backfill_rs_short_horizons selftest: OK")
        return
    if not (args.sectors or args.stocks):
        p.error("pass --sectors and/or --stocks (or --selftest)")

    from src.core.db import get_conn
    with get_conn() as conn:
        _ensure(conn)
        if not args.dry_run:
            conn.commit()
        if args.sectors:
            log.info("sectors: %s", backfill_sectors(conn, args.dry_run))
        if args.stocks:
            log.info("stocks: %s", backfill_stocks(conn, args.dry_run, args.limit))
    log.info("done (%s)", "DRY-RUN — nothing written" if args.dry_run else "committed")


if __name__ == "__main__":
    main()
