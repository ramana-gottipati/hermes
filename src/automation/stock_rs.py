"""D33a — Stock-level Relative Strength vs the broad market (Nifty 500).

For each (symbol, trade_date) we compute the canonical RS-vs-broad series and
its D32-vocabulary technical reads, denormalized onto the existing
`stock_signals` row:

    rs_vs_broad = adjusted_close(stock) / close(Nifty 500)

RULES (D37):
  - ADJUSTED stock price ÷ RAW index close. The index is split-free; the stock
    must be back-adjusted (`adjust.adjusted_closes`) or a split fakes an RS
    collapse.
  - Same windows as everything else: 1m/3m/6m/12m slopes.
  - Same technical reads + trend_state vocabulary as D32 — we REUSE
    `index_signals.compute_ratio_signal`, feeding it the stock's RS series.
  - Percentile RS rank (1-99): the cross-stock standardization. Per trade_date,
    rank a blended RS momentum (0.6·3m + 0.4·6m rs_vs_broad slope) across the
    LIQUID universe (the same filter signals/dashboard use). "RS 90 = stronger
    than 90% of the market." Computed in SQL with PERCENT_RANK().

We UPDATE the existing stock_signals row for (symbol, trade_date) — those rows
already exist from signals.py; we never INSERT here.

Usage:
    python -m src.automation.stock_rs --symbol PARAS      # one stock's full RS series + print latest 5 days
    python -m src.automation.stock_rs --date 2026-06-05   # one date, all symbols, + percentile pass for that date
    python -m src.automation.stock_rs --backfill          # all symbols + percentile pass
    python -m src.automation.stock_rs --rank-only         # just the percentile pass (all dates)
"""

import argparse
import logging
from typing import Optional

from src.core.db import get_conn
from src.automation.adjust import adjusted_closes
# REUSE the D32 ratio engine + helpers — do not reinvent the RS math.
from src.automation.index_signals import compute_ratio_signal

# Canonical broad benchmark. TITLE case — NSE's ind_close_all CSV stores index
# names title-case ("Nifty 500"), and that's how index_rows holds them. Must
# match the stored casing exactly or the denominator lookup finds nothing.
BROAD = "Nifty 500"

log = logging.getLogger("hermes.stock_rs")

# The liquid-universe filter — IDENTICAL to the dashboard's _SCAN_FILTERS and
# the screen signals use: real EQ, traded value > ₹1cr, price > ₹20, excluding
# ETFs / commodity trackers / index proxies. Used only for the percentile rank
# (the per-stock RS series itself is computed for every symbol with bhav data).
_LIQUID_FILTER = """
      b.series = 'EQ' AND (b.segment = 'CM' OR b.segment IS NULL)
      AND b.value > 10000000 AND b.close > 20
      AND s.symbol NOT LIKE '%ETF%' AND s.symbol NOT LIKE '%IETF%'
      AND s.symbol NOT LIKE '%BEES%' AND s.symbol NOT LIKE '%GOLD%'
      AND s.symbol NOT LIKE '%SILVER%' AND s.symbol NOT LIKE 'MON%'
      AND s.symbol NOT LIKE 'NIFTY%'
"""


# --- Broad benchmark history ------------------------------------------------

def _broad_closes() -> dict[str, float]:
    """All Nifty 500 closes keyed by trade_date. Loaded once per run."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT trade_date, close_value
               FROM index_rows
               WHERE index_name = ? AND close_value IS NOT NULL AND close_value > 0
               ORDER BY trade_date ASC""",
            (BROAD,),
        ).fetchall()
    return {r["trade_date"]: r["close_value"] for r in rows}


# --- Per-symbol RS series ---------------------------------------------------

def build_rs_history(symbol: str, broad_map: dict[str, float]) -> list[dict]:
    """Build the stock's full RS-vs-broad ratio series, oldest→newest.

    Fetches the symbol's entire EQ bhav history, back-adjusts the close for
    splits/bonuses, and divides by the raw Nifty 500 close on each date present
    in BOTH series. Returns rows shaped for `compute_ratio_signal`:
        {"trade_date", "num_close" (adj stock), "den_close" (index), "ratio"}.
    """
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            """SELECT trade_date, close, prev_close
               FROM bhavcopy_rows
               WHERE symbol = ? AND series = 'EQ'
                 AND (segment = 'CM' OR segment IS NULL)
               ORDER BY trade_date ASC""",
            (symbol,),
        ).fetchall()]
    if not rows:
        return []

    adj = adjusted_closes(rows)  # parallel adjusted-close list, oldest→newest
    out: list[dict] = []
    for r, a in zip(rows, adj):
        if a is None or a <= 0:
            continue
        d = r["trade_date"]
        den = broad_map.get(d)
        if den is None or den <= 0:
            continue
        out.append({
            "trade_date": d,
            "num_close": a,        # ADJUSTED stock close
            "den_close": den,      # RAW index close
            "ratio": a / den,
        })
    return out


def _rs_sig_to_update(sig: dict) -> tuple:
    """Map a compute_ratio_signal() output dict → the stock_signals RS columns
    UPDATE tuple (values, then symbol + trade_date for the WHERE)."""
    return (
        sig["ratio"],                 # rs_vs_broad_today
        sig["slope_1m_pct"],          # rs_vs_broad_slope_1m
        sig["slope_3m_pct"],          # rs_vs_broad_slope_3m
        sig["slope_6m_pct"],          # rs_vs_broad_slope_6m
        sig["slope_12m_pct"],         # rs_vs_broad_slope_12m
        sig["above_50_ma"],           # rs_vs_broad_above_50ma
        sig["above_200_ma"],          # rs_vs_broad_above_200ma
        sig["new_52w_high"],          # rs_vs_broad_new_52w_high
        sig["trend_state"],           # rs_vs_broad_trend_state
        sig["numerator"],             # WHERE symbol
        sig["trade_date"],            # WHERE trade_date
    )


_RS_UPDATE_SQL = """
    UPDATE stock_signals
       SET rs_vs_broad_today        = ?,
           rs_vs_broad_slope_1m     = ?,
           rs_vs_broad_slope_3m     = ?,
           rs_vs_broad_slope_6m     = ?,
           rs_vs_broad_slope_12m    = ?,
           rs_vs_broad_above_50ma   = ?,
           rs_vs_broad_above_200ma  = ?,
           rs_vs_broad_new_52w_high = ?,
           rs_vs_broad_trend_state  = ?
     WHERE symbol = ? AND trade_date = ?
"""


def compute_symbol_rs(symbol: str, broad_map: dict[str, float],
                      trade_date_filter: Optional[str] = None) -> tuple[list[dict], int]:
    """Compute + store the RS series for one symbol.

    Returns (rs_history, n_rows_updated). If trade_date_filter is set, only
    that one date's row is UPDATEd (the per-date path); otherwise the whole
    series is written (the backfill / single-symbol path). Idempotent UPDATE.
    """
    rs_hist = build_rs_history(symbol, broad_map)
    if not rs_hist:
        return [], 0

    target_dates = (
        [trade_date_filter] if trade_date_filter
        else [r["trade_date"] for r in rs_hist]
    )

    updates = []
    for d in target_dates:
        sig = compute_ratio_signal(symbol, BROAD, rs_hist, d)
        if sig:
            updates.append(_rs_sig_to_update(sig))

    if updates:
        with get_conn() as conn:
            conn.executemany(_RS_UPDATE_SQL, updates)
    return rs_hist, len(updates)


# --- Percentile rank pass ---------------------------------------------------

def _rank_sql_for(date_clause: str) -> str:
    """The cross-stock percentile rank UPDATE. `date_clause` is an extra
    predicate on bhavcopy_rows alias `b` (e.g. "AND b.trade_date = ?") so we
    can rank one date or every date with the same statement.

    Blended momentum: 0.6·COALESCE(slope_3m,?)+0.4·COALESCE(slope_6m,?), ranked
    via PERCENT_RANK() per trade_date over the LIQUID universe, mapped to 1-99.
    Only rows whose slope_3m IS NOT NULL get a rank.
    """
    return f"""
        WITH liquid AS (
            SELECT s.symbol, s.trade_date,
                   0.6 * COALESCE(s.rs_vs_broad_slope_3m, ?)
                 + 0.4 * COALESCE(s.rs_vs_broad_slope_6m, ?) AS mom
            FROM stock_signals s
            JOIN bhavcopy_rows b
              ON b.symbol = s.symbol AND b.trade_date = s.trade_date
            WHERE s.rs_vs_broad_slope_3m IS NOT NULL
              {date_clause}
              AND {_LIQUID_FILTER}
        ),
        ranked AS (
            SELECT symbol, trade_date,
                   CAST(ROUND(PERCENT_RANK() OVER (
                       PARTITION BY trade_date ORDER BY mom
                   ) * 98) + 1 AS INTEGER) AS rs_rank
            FROM liquid
        )
        UPDATE stock_signals
           SET rs_rank = (
               SELECT r.rs_rank FROM ranked r
               WHERE r.symbol = stock_signals.symbol
                 AND r.trade_date = stock_signals.trade_date
           )
         WHERE (symbol, trade_date) IN (SELECT symbol, trade_date FROM ranked)
    """


def run_rank_pass(trade_date: Optional[str] = None) -> int:
    """Compute rs_rank percentiles. One date if given, else every date.

    Returns the number of stock_signals rows whose rs_rank was set. The blend
    is 0.6·3m + 0.4·6m of rs_vs_broad slope; a missing 6m falls back to 0 via
    COALESCE so a stock with only 3m history still ranks.
    """
    if trade_date:
        sql = _rank_sql_for("AND b.trade_date = ?")
        params = (0.0, 0.0, trade_date)
    else:
        sql = _rank_sql_for("")
        params = (0.0, 0.0)
    with get_conn() as conn:
        before = conn.total_changes
        conn.execute(sql, params)
        # The CTE-driven UPDATE doesn't populate cursor.rowcount reliably;
        # use the connection's total_changes delta for an accurate count.
        n = conn.total_changes - before
    log.info("rank pass: %d rows ranked%s", n,
             f" for {trade_date}" if trade_date else " (all dates)")
    return n


# --- Orchestration ----------------------------------------------------------

def _all_symbols_with_bhav() -> list[str]:
    with get_conn() as conn:
        return [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol"""
        ).fetchall()]


def compute_for_date(trade_date: str) -> tuple[int, int]:
    """RS for one trade_date across all symbols, then the percentile pass for
    that date. Returns (n_symbols_updated, n_ranked)."""
    broad_map = _broad_closes()
    if not broad_map:
        log.warning("no %s index history — cannot compute stock RS", BROAD)
        return 0, 0
    symbols = [r["symbol"] for r in _symbols_on_date(trade_date)]
    if not symbols:
        log.info("no EQ symbols on %s", trade_date)
        return 0, 0
    log.info("computing stock RS for %d symbols on %s", len(symbols), trade_date)
    n = 0
    for i, sym in enumerate(symbols, 1):
        _, updated = compute_symbol_rs(sym, broad_map, trade_date_filter=trade_date)
        n += updated
        if i % 200 == 0:
            log.info("  progress: %d / %d", i, len(symbols))
    n_ranked = run_rank_pass(trade_date)
    log.info("date %s done: %d RS rows, %d ranked", trade_date, n, n_ranked)
    return n, n_ranked


def _symbols_on_date(trade_date: str) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE trade_date = ? AND series = 'EQ'
                 AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol""",
            (trade_date,),
        ).fetchall()


def run_backfill() -> tuple[int, int]:
    """Per-symbol walk (mirror signals.run_backfill_triggers): compute + store
    each symbol's whole RS series, then ONE final cross-stock percentile pass
    over every date. Returns (n_symbols, n_rows_updated)."""
    broad_map = _broad_closes()
    if not broad_map:
        log.warning("no %s index history — cannot backfill stock RS", BROAD)
        return 0, 0
    symbols = _all_symbols_with_bhav()
    log.info("stock_rs backfill: %d symbols to walk (broad=%s, %d index days)",
             len(symbols), BROAD, len(broad_map))
    total_rows = 0
    for k, sym in enumerate(symbols, 1):
        try:
            _, updated = compute_symbol_rs(sym, broad_map)
            total_rows += updated
        except Exception as e:
            log.warning("stock_rs failed for %s: %s", sym, e)
        if k % 50 == 0:
            log.info("  progress: %d / %d symbols, %d RS rows updated",
                     k, len(symbols), total_rows)
    log.info("RS series done: %d symbols, %d rows. Running percentile pass...",
             len(symbols), total_rows)
    n_ranked = run_rank_pass()
    log.info("backfill complete: %d symbols, %d RS rows, %d ranked",
             len(symbols), total_rows, n_ranked)
    return len(symbols), total_rows


def run_today() -> tuple[bool, str]:
    """Compute RS for the most recent trade_date in bhavcopy_rows."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM bhavcopy_rows"
        ).fetchone()
    if not row or not row["d"]:
        return False, "no bhav data found"
    n, n_ranked = compute_for_date(row["d"])
    return True, f"computed {n} RS rows, {n_ranked} ranked for {row['d']}"


# --- CLI --------------------------------------------------------------------

def _print_symbol_tail(symbol: str, rs_hist: list[dict]) -> None:
    """Print the latest 5 days' adj_close / rs_vs_broad / slopes / trend_state
    for one symbol — the user's spot-check (e.g. PARAS)."""
    if not rs_hist:
        log.info("%s: no RS history (no overlap with %s, or no bhav)", symbol, BROAD)
        return
    tail = rs_hist[-5:]
    print(f"\n{symbol} — latest {len(tail)} RS days (rs_vs_broad = adj_close / {BROAD}):")
    print(f"{'date':<12}{'adj_close':>12}{'rs_vs_broad':>14}"
          f"{'s1m':>8}{'s3m':>8}{'s6m':>8}{'s12m':>8}  trend")
    for r in tail:
        sig = compute_ratio_signal(symbol, BROAD, rs_hist, r["trade_date"])
        if not sig:
            print(f"{r['trade_date']:<12}{r['num_close']:>12.2f}"
                  f"{r['ratio']:>14.6f}{'—':>8}{'—':>8}{'—':>8}{'—':>8}  (insufficient history)")
            continue

        def f(v):
            return f"{v:>8.2f}" if v is not None else f"{'—':>8}"
        print(f"{r['trade_date']:<12}{r['num_close']:>12.2f}{sig['ratio']:>14.6f}"
              f"{f(sig['slope_1m_pct'])}{f(sig['slope_3m_pct'])}"
              f"{f(sig['slope_6m_pct'])}{f(sig['slope_12m_pct'])}  {sig['trend_state']}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true",
                   help="All symbols' full RS series + final percentile pass.")
    p.add_argument("--rank-only", action="store_true",
                   help="Only the cross-stock percentile rank pass (all dates).")
    p.add_argument("--date", type=str, help="YYYY-MM-DD — one date, all symbols, + that date's rank pass")
    p.add_argument("--symbol", type=str,
                   help="One symbol's full RS series + print latest 5 days for verification")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.symbol:
        sym = args.symbol.upper()
        broad_map = _broad_closes()
        if not broad_map:
            log.warning("no %s index history — cannot compute RS", BROAD)
            return
        rs_hist, updated = compute_symbol_rs(sym, broad_map)
        log.info("%s: %d RS rows updated", sym, updated)
        _print_symbol_tail(sym, rs_hist)
    elif args.rank_only:
        n = run_rank_pass()
        log.info("rank-only complete: %d rows ranked", n)
    elif args.date:
        n, n_ranked = compute_for_date(args.date)
        log.info("date %s done: %d RS rows, %d ranked", args.date, n, n_ranked)
    elif args.backfill:
        n_syms, n_rows = run_backfill()
        log.info("backfill complete: %d symbols, %d RS rows updated", n_syms, n_rows)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
