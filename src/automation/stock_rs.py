"""D33a/b — Stock-level Relative Strength vs the broad market AND its sector.

For each (symbol, trade_date) we compute two canonical RS series + their
D32-vocabulary technical reads, denormalized onto the existing `stock_signals`
row:

    rs_vs_broad  = adjusted_close(stock) / close(Nifty 500)              # D33a
    rs_vs_sector = adjusted_close(stock) / close(primary_sector_index)  # D33b

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
    than 90% of the market." Computed in SQL with PERCENT_RANK(). (Broad only —
    sector RS is not cross-ranked; comparing a bank vs its bank peers and a
    pharma vs its pharma peers on one 1-99 scale would be apples-to-oranges.)

  D33b — primary sector: each stock's NARROWEST NSE sectoral index, from
  `stock_index_membership` (size/broad indices excluded). "Narrowest" = the
  index with the FEWEST members (most specific), ties broken alphabetically.
  A stock in no NSE sectoral index has primary_sector = NULL (broad RS only).

We UPDATE the existing stock_signals row for (symbol, trade_date) — those rows
already exist from signals.py; we never INSERT here.

Usage:
    python -m src.automation.stock_rs --symbol PARAS      # one stock's full broad+sector RS + print latest 5 days
    python -m src.automation.stock_rs --date 2026-06-05   # one date: broad + sector + percentile pass
    python -m src.automation.stock_rs --backfill          # all symbols: broad + rank + sector
    python -m src.automation.stock_rs --sector-backfill   # just the stock-vs-sector pass (~500 symbols, fast)
    python -m src.automation.stock_rs --rank-only         # just the percentile pass (all dates)
"""

import argparse
import logging
import math
from typing import Optional

from src.core.db import get_conn
from src.automation.adjust import adjusted_closes
# REUSE the D32 ratio engine + the size/broad-index exclusion set — do not
# reinvent the RS math nor re-list which indices count as "the market".
from src.automation.index_signals import compute_ratio_signal, SIZE_BASED_INDEX_NAMES
# Rotation layer (session 25): the shared phase classifier + additive-column
# guard, and rrg's one-pass Wilder RSI (run on the RS series → RSI-of-RS).
from src.automation import rrg, rs_phase


def _fin(v):
    """Coerce non-finite (inf/nan) to None so it never poisons the DB or a sort."""
    return v if (v is not None and isinstance(v, (int, float)) and math.isfinite(v)) else None

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
      AND s.symbol IN (SELECT symbol FROM nse_equity_list)
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


def _rs_sig_to_update(sig: dict, rs_phase_key, rsi_val) -> tuple:
    """Map a compute_ratio_signal() output dict (+ rotation phase + RSI-of-RS) →
    the stock_signals RS columns UPDATE tuple (values, then symbol + trade_date
    for the WHERE)."""
    return (
        sig["ratio"],                 # rs_vs_broad_today
        sig["slope_1m_pct"],          # rs_vs_broad_slope_1m
        sig["slope_3m_pct"],          # rs_vs_broad_slope_3m
        sig["slope_6m_pct"],          # rs_vs_broad_slope_6m
        sig["slope_12m_pct"],         # rs_vs_broad_slope_12m
        sig["slope_18m_pct"],         # rs_vs_broad_slope_18m
        sig["slope_24m_pct"],         # rs_vs_broad_slope_24m
        sig["above_50_ma"],           # rs_vs_broad_above_50ma
        sig["above_200_ma"],          # rs_vs_broad_above_200ma
        sig["new_52w_high"],          # rs_vs_broad_new_52w_high
        sig["trend_state"],           # rs_vs_broad_trend_state
        rs_phase_key,                 # rs_phase   (rotation label, broad RS)
        rsi_val,                      # rsi_of_rs  (Wilder RSI on the RS series)
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
           rs_vs_broad_slope_18m    = ?,
           rs_vs_broad_slope_24m    = ?,
           rs_vs_broad_above_50ma   = ?,
           rs_vs_broad_above_200ma  = ?,
           rs_vs_broad_new_52w_high = ?,
           rs_vs_broad_trend_state  = ?,
           rs_phase                 = ?,
           rsi_of_rs                = ?
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

    # RSI-of-RS over the whole RS ratio series (Wilder; reuse rrg's one-pass
    # implementation). §4b-2: un-strand the RSI-of-RS read AND extend it from
    # sectors to stocks — the series is already in hand here, so it's one extra
    # O(n) pass, no new fetch. Parallel to rs_hist → map by date.
    # CL-RS-14: Wilder's RSI is recursive, so the full-series pass is unavoidable,
    # but on the nightly per-date path only ONE date's value is consumed — so we
    # build the by-date map only over the date(s) we'll actually emit, not the whole
    # multi-year history.
    target_dates = (
        [trade_date_filter] if trade_date_filter
        else [r["trade_date"] for r in rs_hist]
    )
    rsi_series = rrg._rsi_series([r["ratio"] for r in rs_hist])
    _want = set(target_dates)
    rsi_by_date = {rs_hist[i]["trade_date"]: _fin(rsi_series[i])
                   for i in range(len(rs_hist))
                   if rs_hist[i]["trade_date"] in _want}

    updates = []
    for d in target_dates:
        sig = compute_ratio_signal(symbol, BROAD, rs_hist, d)
        if sig:
            ph = rs_phase.phase_key(sig["slope_1m_pct"], sig["slope_3m_pct"],
                                    sig["slope_6m_pct"], sig["slope_12m_pct"],
                                    sig["trend_state"])
            updates.append(_rs_sig_to_update(sig, ph, rsi_by_date.get(d)))

    if updates:
        with get_conn() as conn:
            rs_phase.ensure_columns(conn)   # additive rotation columns (idempotent)
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
            -- CL-RS-08: a missing 6m slope now falls back to the 3m slope (the
            -- stock's own momentum), not to 0. The slope distribution isn't
            -- zero-mean, so coalescing a young listing's absent 6m to 0 dragged
            -- its blended momentum toward the population's neutral-ish midpoint
            -- and mis-ranked it. slope_3m is guaranteed present (WHERE clause).
            SELECT s.symbol, s.trade_date,
                   0.6 * s.rs_vs_broad_slope_3m
                 + 0.4 * COALESCE(s.rs_vs_broad_slope_6m, s.rs_vs_broad_slope_3m) AS mom
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
    is 0.6·3m + 0.4·6m of rs_vs_broad slope; a missing 6m falls back to the 3m
    slope (CL-RS-08) so a stock with only 3m history still ranks on its own
    momentum rather than being dragged toward 0.
    """
    if trade_date:
        sql = _rank_sql_for("AND b.trade_date = ?")
        params = (trade_date,)
    else:
        sql = _rank_sql_for("")
        params = ()
    with get_conn() as conn:
        before = conn.total_changes
        conn.execute(sql, params)
        # The CTE-driven UPDATE doesn't populate cursor.rowcount reliably;
        # use the connection's total_changes delta for an accurate count.
        n = conn.total_changes - before
    log.info("rank pass: %d rows ranked%s", n,
             f" for {trade_date}" if trade_date else " (all dates)")
    return n


# --- D33b: stock-vs-SECTOR RS ----------------------------------------------

def primary_sector_map() -> dict[str, str]:
    """Assign each stock its PRIMARY (narrowest) NSE sector index.

    Among the SECTORAL indices a symbol belongs to in `stock_index_membership`
    (size/broad indices excluded via the D32 `SIZE_BASED_INDEX_NAMES` set), pick
    the one with the FEWEST members — the most specific. So a bank in both
    "Nifty Financial Services" (~20) and "Nifty Bank" (~12) maps to Nifty Bank;
    a stock in "Nifty Healthcare Index" (~20) and "Nifty Pharma" (~20-tie) is
    resolved by the alphabetical tiebreak. Returns {symbol: index_name}; symbols
    in no sectoral index are absent (→ NULL primary_sector → broad RS only).
    Only the latest snapshot_date per index is used.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT m.symbol, m.index_name
               FROM stock_index_membership m
               JOIN (SELECT index_name, MAX(snapshot_date) sd
                       FROM stock_index_membership GROUP BY index_name) latest
                 ON latest.index_name = m.index_name
                AND latest.sd = m.snapshot_date""",
        ).fetchall()
    sizes: dict[str, int] = {}          # members per sectoral index
    by_symbol: dict[str, list[str]] = {}
    for r in rows:
        idx = r["index_name"]
        if idx.upper() in SIZE_BASED_INDEX_NAMES:
            continue                    # a size/broad index is not a "sector"
        sizes[idx] = sizes.get(idx, 0) + 1
        by_symbol.setdefault(r["symbol"], []).append(idx)
    # narrowest = fewest members; deterministic alphabetical tiebreak.
    return {sym: min(idxs, key=lambda nm: (sizes[nm], nm))
            for sym, idxs in by_symbol.items()}


def _sector_close_maps(names: set[str]) -> dict[str, dict[str, float]]:
    """{index_name: {trade_date: close}} for each given sector index. Loaded in
    one query so the per-symbol loop never re-hits the DB for the denominator."""
    out: dict[str, dict[str, float]] = {}
    if not names:
        return out
    with get_conn() as conn:
        qmarks = ",".join("?" * len(names))
        rows = conn.execute(
            f"""SELECT index_name, trade_date, close_value
                FROM index_rows
                WHERE index_name IN ({qmarks})
                  AND close_value IS NOT NULL AND close_value > 0
                ORDER BY trade_date ASC""",
            tuple(names),
        ).fetchall()
    for r in rows:
        out.setdefault(r["index_name"], {})[r["trade_date"]] = r["close_value"]
    return out


_RS_SECTOR_UPDATE_SQL = """
    UPDATE stock_signals
       SET primary_sector            = ?,
           rs_vs_sector_today        = ?,
           rs_vs_sector_slope_1m     = ?,
           rs_vs_sector_slope_3m     = ?,
           rs_vs_sector_slope_6m     = ?,
           rs_vs_sector_slope_12m    = ?,
           rs_vs_sector_slope_18m    = ?,
           rs_vs_sector_slope_24m    = ?,
           rs_vs_sector_above_50ma   = ?,
           rs_vs_sector_above_200ma  = ?,
           rs_vs_sector_new_52w_high = ?,
           rs_vs_sector_trend_state  = ?
     WHERE symbol = ? AND trade_date = ?
"""


def _sector_sig_to_update(sig: dict, symbol: str, sector_name: str) -> tuple:
    """compute_ratio_signal() output → the rs_vs_sector UPDATE tuple (+ the
    denormalized primary_sector), then symbol + trade_date for the WHERE."""
    return (
        sector_name,                  # primary_sector
        sig["ratio"],                 # rs_vs_sector_today
        sig["slope_1m_pct"],          # rs_vs_sector_slope_1m
        sig["slope_3m_pct"],          # rs_vs_sector_slope_3m
        sig["slope_6m_pct"],          # rs_vs_sector_slope_6m
        sig["slope_12m_pct"],         # rs_vs_sector_slope_12m
        sig["slope_18m_pct"],         # rs_vs_sector_slope_18m
        sig["slope_24m_pct"],         # rs_vs_sector_slope_24m
        sig["above_50_ma"],           # rs_vs_sector_above_50ma
        sig["above_200_ma"],          # rs_vs_sector_above_200ma
        sig["new_52w_high"],          # rs_vs_sector_new_52w_high
        sig["trend_state"],           # rs_vs_sector_trend_state
        symbol,                       # WHERE symbol
        sig["trade_date"],            # WHERE trade_date
    )


def compute_symbol_sector_rs(symbol: str, sector_name: str,
                             sector_close_map: dict[str, float],
                             trade_date_filter: Optional[str] = None) -> tuple[list[dict], int]:
    """Compute + store the rs_vs_sector series for one symbol against its
    primary sector index. REUSES `build_rs_history` (adjusted stock close ÷ the
    sector close map) + `compute_ratio_signal`, exactly like the broad path.
    Returns (rs_history, n_rows_updated). Idempotent UPDATE."""
    rs_hist = build_rs_history(symbol, sector_close_map)
    if not rs_hist:
        return [], 0
    target_dates = (
        [trade_date_filter] if trade_date_filter
        else [r["trade_date"] for r in rs_hist]
    )
    updates = []
    for d in target_dates:
        sig = compute_ratio_signal(symbol, sector_name, rs_hist, d)
        if sig:
            updates.append(_sector_sig_to_update(sig, symbol, sector_name))
    if updates:
        with get_conn() as conn:
            rs_phase.ensure_columns(conn)   # additive rotation columns (idempotent)
            conn.executemany(_RS_SECTOR_UPDATE_SQL, updates)
    return rs_hist, len(updates)


def run_sector_backfill() -> tuple[int, int]:
    """Sector RS for every symbol with a primary sector (~500), full series.
    Returns (n_symbols, n_rows_updated)."""
    assign = primary_sector_map()
    if not assign:
        log.warning("no sector assignments (stock_index_membership empty?) — "
                    "skipping sector RS")
        return 0, 0
    close_maps = _sector_close_maps(set(assign.values()))
    log.info("stock_rs SECTOR backfill: %d symbols with a primary sector across "
             "%d sector indices", len(assign), len(close_maps))
    total_rows = 0
    n_syms = 0
    for k, (sym, sector) in enumerate(sorted(assign.items()), 1):
        cm = close_maps.get(sector)
        if not cm:
            log.warning("no index history for sector %s (symbol %s) — skipping",
                        sector, sym)
            continue
        try:
            _, updated = compute_symbol_sector_rs(sym, sector, cm)
            total_rows += updated
            n_syms += 1
        except Exception as e:
            log.warning("sector RS failed for %s (%s): %s", sym, sector, e)
        if k % 50 == 0:
            log.info("  progress: %d / %d symbols, %d sector RS rows",
                     k, len(assign), total_rows)
    log.info("sector backfill complete: %d symbols, %d sector RS rows",
             n_syms, total_rows)
    return n_syms, total_rows


def compute_sector_for_date(trade_date: str) -> int:
    """Sector RS for one trade_date across all symbols that have a primary
    sector (the nightly path). Returns n rows updated."""
    assign = primary_sector_map()
    if not assign:
        return 0
    close_maps = _sector_close_maps(set(assign.values()))
    n = 0
    for sym, sector in assign.items():
        cm = close_maps.get(sector)
        if not cm:
            continue
        try:
            _, updated = compute_symbol_sector_rs(
                sym, sector, cm, trade_date_filter=trade_date)
            n += updated
        except Exception as e:
            log.warning("sector RS failed for %s (%s) on %s: %s",
                        sym, sector, trade_date, e)
    return n


# --- D33c: composite "strong-in-strong" leaders / laggards ------------------

_LEADER_STATES = ("UPTREND", "BREAKOUT")
_LAGGARD_STATES = ("DOWNTREND", "BREAKDOWN")


def leaders_laggards(kind: str = "leaders", limit: int = 50,
                     trade_date: Optional[str] = None) -> list[dict]:
    """Composite RS screen (D37 'strong-in-strong'). A LEADER has ALL THREE of
    {stock rs_vs_sector, stock rs_vs_broad, its sector's own rs_vs_broad (the
    D32 index_signals read)} in {UPTREND, BREAKOUT}; a LAGGARD has all three in
    {DOWNTREND, BREAKDOWN} — the stock is leading (lagging) its own pack, the
    pack is leading (lagging) the market, and the stock is leading (lagging) the
    market directly. Liquid universe only. Leaders ordered by broad rs_rank DESC
    (strongest first); laggards by rs_rank ASC (weakest first).

    Returns dicts: symbol, rs_rank, primary_sector, broad_state, sector_state,
    sector_broad_state, close, value. Shared by the dashboard (/dash/leaders +
    Home preview) and the Telegram /leaders /laggards commands.
    """
    states = _LEADER_STATES if kind == "leaders" else _LAGGARD_STATES
    qm = ",".join("?" * len(states))
    order = "DESC" if kind == "leaders" else "ASC"
    with get_conn() as conn:
        if trade_date is None:
            row = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()
            trade_date = row["d"] if row else None
        irow = conn.execute("SELECT MAX(trade_date) d FROM index_signals").fetchone()
        idx_date = irow["d"] if irow else None
        if not trade_date or not idx_date:
            return []
        sql = f"""
            SELECT s.symbol, s.rs_rank, s.primary_sector,
                   s.rs_vs_broad_trend_state  AS broad_state,
                   s.rs_vs_sector_trend_state AS sector_state,
                   i.rs_vs_broad_trend_state  AS sector_broad_state,
                   b.close, b.value
            FROM stock_signals s
            JOIN bhavcopy_rows b
              ON b.symbol = s.symbol AND b.trade_date = s.trade_date
            JOIN index_signals i
              ON i.index_name = s.primary_sector AND i.trade_date = ?
            WHERE s.trade_date = ?
              AND s.primary_sector IS NOT NULL
              AND s.rs_vs_sector_trend_state IN ({qm})
              AND s.rs_vs_broad_trend_state  IN ({qm})
              AND i.rs_vs_broad_trend_state  IN ({qm})
              AND {_LIQUID_FILTER}
            ORDER BY (s.rs_rank IS NULL), s.rs_rank {order}
            LIMIT ?
        """
        params = (idx_date, trade_date, *states, *states, *states, limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def conviction_shortlist(limit: int = 50, trade_date: Optional[str] = None) -> list[dict]:
    """D45 — the cross-pillar 'Conviction shortlist': names where ALL THREE
    strategy pillars align.
      RELATIVE STRENGTH — an RS LEADER (the D33c 3-layer test: stock-vs-sector,
        stock-vs-broad, and the sector's own RS vs broad all in {UPTREND,BREAKOUT}).
      POSITIONING       — institutions are ACCUMULATING it now (D43
        accum_character='ACCUMULATION', which already implies p_score≥2 active).
      QUALITY           — pt14 (D-quality) is surfaced as CONFIRMATION (LEFT JOIN
        pattern_scores; sparse, so it enriches/sorts but does not gate).
    Enriched with the D44 entry read (near-key gap + key price) so the user can
    see if it's a buyable entry now. Liquid universe; strongest leaders first.
    ONE shared read helper for the dashboard (/dash/conviction + Home preview)
    and the Telegram /conviction command (DRY)."""
    st = _LEADER_STATES
    qm = ",".join("?" * len(st))
    with get_conn() as conn:
        if trade_date is None:
            row = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()
            trade_date = row["d"] if row else None
        irow = conn.execute("SELECT MAX(trade_date) d FROM index_signals").fetchone()
        idx_date = irow["d"] if irow else None
        if not trade_date or not idx_date:
            return []
        sql = f"""
            SELECT s.symbol, s.rs_rank, s.primary_sector,
                   s.rs_vs_broad_trend_state  AS broad_state,
                   s.rs_vs_sector_trend_state AS sector_state,
                   s.accum_character, s.p_score, s.trigger_rank,
                   s.price_vs_hot_avg_pct AS pvh,
                   s.key_price_p3m, s.gap_to_key_p3m, s.gap_to_key_p6m, s.gap_to_key_p12m,
                   b.close, b.value,
                   ps.tier AS pt14_tier, ps.ns_base AS pt14_ns,
                   ps.hard_disqualified AS pt14_dq
            FROM stock_signals s
            JOIN bhavcopy_rows b
              ON b.symbol = s.symbol AND b.trade_date = s.trade_date
            JOIN index_signals i
              ON i.index_name = s.primary_sector AND i.trade_date = ?
            LEFT JOIN pattern_scores ps
              ON ps.id = (SELECT p2.id FROM pattern_scores p2
                          WHERE p2.symbol = s.symbol
                          ORDER BY p2.scored_at DESC LIMIT 1)
            WHERE s.trade_date = ?
              AND s.primary_sector IS NOT NULL
              AND s.rs_vs_sector_trend_state IN ({qm})
              AND s.rs_vs_broad_trend_state  IN ({qm})
              AND i.rs_vs_broad_trend_state  IN ({qm})
              AND s.accum_character = 'ACCUMULATION'
              AND {_LIQUID_FILTER}
            ORDER BY (s.rs_rank IS NULL), s.rs_rank DESC
            LIMIT ?
        """
        params = (idx_date, trade_date, *st, *st, *st, limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# --- D63: RS Rotation — the four-phase weather-rotation reads ----------------
# Design: docs/rs-rotation-design.md. Builds on the rs_phase label + the 18/24m
# slopes + rsi_of_rs this module now stores. Read-only, rule-based, ZERO LLM.
# STRICTLY ADDITIVE — leaders_laggards()/conviction_shortlist() are untouched
# (leaders_laggards stays the canonical strong-in-strong / weak-in-weak read; the
# rotation Tailwind/Headwind shortlists are a parallel, phase-keyed view of it).

# Per-quadrant "confirm" gate for the STRICT shortlist (design §3): on top of the
# stock AND its sector sharing the phase, require the MA-position confirmation.
_PHASE_CONFIRM = {
    "RECOVERY":     ("AND s.rs_vs_broad_above_50ma=1 AND s.rs_vs_broad_above_200ma=0 "
                     "AND s.rs_vs_broad_slope_12m<0"),
    "TAILWIND":     "AND s.rs_vs_broad_above_200ma=1",
    "ROLLING-OVER": "AND s.rs_vs_broad_above_200ma=1 AND s.rs_vs_broad_above_50ma=0",
    "HEADWIND":     "AND s.rs_vs_broad_above_200ma=0",
}

_ROTATION_SELECT = """
    SELECT s.symbol, s.rs_rank, s.primary_sector, s.rs_phase,
           s.rs_vs_broad_slope_1m  AS b1,  s.rs_vs_broad_slope_3m  AS b3,
           s.rs_vs_broad_slope_6m  AS b6,  s.rs_vs_broad_slope_12m AS b12,
           s.rs_vs_broad_slope_18m AS b18, s.rs_vs_broad_slope_24m AS b24,
           s.rs_vs_sector_slope_1m AS sc1, s.rs_vs_sector_slope_3m AS sc3,
           s.rs_vs_broad_above_50ma  AS a50, s.rs_vs_broad_above_200ma AS a200,
           s.rs_vs_broad_new_52w_high AS rs_nh, s.pct_from_52w_high AS pfh,
           s.rsi_of_rs AS rsi, s.accum_character AS ch, s.p_score AS psc,
           s.trigger_rank AS trk, s.accum_price_drift_3m AS apd,
           i.rs_phase AS sector_phase, b.close AS close, b.value AS value
    FROM stock_signals s
    JOIN bhavcopy_rows b ON b.symbol=s.symbol AND b.trade_date=s.trade_date
    LEFT JOIN index_signals i ON i.index_name=s.primary_sector AND i.trade_date=?
"""


def _max_sig_dates(conn) -> tuple:
    sd = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()["d"]
    ir = conn.execute("SELECT MAX(trade_date) d FROM index_signals").fetchone()
    return sd, (ir["d"] if ir else None)


def _enrich_rotation(r: dict) -> dict:
    """Attach the §4b RS-leverage reads — derived purely from stored columns."""
    b1, b3, b6, b12 = r.get("b1"), r.get("b3"), r.get("b6"), r.get("b12")
    stacked_up = (None not in (b1, b3, b6, b12) and b1 > b3 > b6 > b12 and b1 > 0)
    stacked_dn = (None not in (b1, b3, b6, b12) and b1 < b3 < b6 < b12 and b1 < 0)
    rsi, apd = r.get("rsi"), r.get("apd")
    r["rs_leads_price"]     = bool(r.get("rs_nh") and r.get("pfh") is not None and r["pfh"] <= -5)
    r["rs_accel_up"]        = bool(stacked_up)     # §4b-3 acceleration (stacked term structure)
    r["rs_accel_down"]      = bool(stacked_dn)
    r["delivery_confirmed"] = bool((r.get("psc") or 0) >= 2          # §4b-5 DVPT confirmation
                                   or r.get("trk") in ("SS", "S")
                                   or r.get("ch") == "ACCUMULATION")
    r["abs_trend_up"]       = bool(apd is not None and apd > 0)      # §4b-6 dual-momentum (abs price drift up)
    r["rsi_overbought"]     = bool(rsi is not None and rsi > 70)     # §4b-2 RSI-of-RS extension tier
    r["rsi_oversold"]       = bool(rsi is not None and rsi < 30)
    return r


def phase_members(phase: str, limit: int = 300, trade_date: Optional[str] = None) -> list[dict]:
    """Every liquid stock currently in `phase` (a grid cell / the full table),
    enriched with the §4b leverage reads + its sector's phase. rs_rank DESC."""
    with get_conn() as conn:
        rs_phase.ensure_columns(conn)
        sd, idd = _max_sig_dates(conn)
        trade_date = trade_date or sd
        if not trade_date:
            return []
        sql = (_ROTATION_SELECT
               + f" WHERE s.trade_date=? AND s.rs_phase=? AND {_LIQUID_FILTER} "
                 "ORDER BY (s.rs_rank IS NULL), s.rs_rank DESC LIMIT ?")
        rows = [dict(r) for r in conn.execute(sql, (idd, trade_date, phase, limit)).fetchall()]
    return [_enrich_rotation(r) for r in rows]


def phase_shortlist(phase: str, limit: int = 100, trade_date: Optional[str] = None) -> list[dict]:
    """The strict diagonal 'X-in-X' shortlist: the stock AND its primary sector
    share the phase, plus the per-phase MA-confirm gate (design §3) — the
    actionable list (Tailwind ≈ strong-in-strong; Recovery = confirmed base-turn;
    Rolling-over = a leader cracking)."""
    confirm = _PHASE_CONFIRM.get(phase, "")
    with get_conn() as conn:
        rs_phase.ensure_columns(conn)
        sd, idd = _max_sig_dates(conn)
        trade_date = trade_date or sd
        if not trade_date or not idd:
            return []
        sql = (_ROTATION_SELECT
               + f" WHERE s.trade_date=? AND s.rs_phase=? AND i.rs_phase=? {confirm} "
                 f"AND {_LIQUID_FILTER} "
                 "ORDER BY (s.rs_rank IS NULL), s.rs_rank DESC LIMIT ?")
        rows = [dict(r) for r in conn.execute(sql, (idd, trade_date, phase, phase, limit)).fetchall()]
    return [_enrich_rotation(r) for r in rows]


def phase_movers(limit: int = 60, trade_date: Optional[str] = None) -> list[dict]:
    """Names whose rs_phase CHANGED on the latest date vs the most recent PRIOR
    day that has a phase — the '✨ just turned' strip (Headwind→Recovery base-turns,
    Tailwind→Rolling-over cracks). Compares ONLY today vs the single prior date
    (two indexed date lookups + idx_signals_phase) — NOT a full-history window —
    so it stays fast as rotation history accrues. Empty until ≥2 days exist."""
    with get_conn() as conn:
        rs_phase.ensure_columns(conn)
        sd, _ = _max_sig_dates(conn)
        trade_date = trade_date or sd
        if not trade_date:
            return []
        # Prior trading date via the covering trade_date index (9ms) — NOT a
        # "rs_phase IS NOT NULL" scan (that mis-picks an index → ~5s over 5.9M
        # rows). The phase-not-null requirement is enforced in the JOIN below,
        # against just that one prior date's rows. If the prior date has no phase
        # computed yet, the join yields 0 → graceful empty.
        prev = conn.execute(
            "SELECT MAX(trade_date) d FROM stock_signals WHERE trade_date < ?",
            (trade_date,)).fetchone()
        prev_date = prev["d"] if prev else None
        if not prev_date:
            return []   # only one day of history → no transitions yet
        sql = f"""
            SELECT s.symbol, s.rs_rank, s.primary_sector, s.rs_phase,
                   p.rs_phase AS prev_phase, b.close AS close, b.value AS value
            FROM stock_signals s
            JOIN stock_signals p ON p.symbol=s.symbol AND p.trade_date=?
            JOIN bhavcopy_rows b ON b.symbol=s.symbol AND b.trade_date=s.trade_date
            WHERE s.trade_date=? AND s.rs_phase IS NOT NULL
              AND p.rs_phase IS NOT NULL AND p.rs_phase<>s.rs_phase
              AND {_LIQUID_FILTER}
            ORDER BY (s.rs_rank IS NULL), s.rs_rank DESC
            LIMIT ?
        """
        return [dict(r) for r in conn.execute(sql, (prev_date, trade_date, limit)).fetchall()]


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
    n_sector = compute_sector_for_date(trade_date)   # D33b stock-vs-sector RS
    n_ranked = run_rank_pass(trade_date)
    log.info("date %s done: %d broad RS rows, %d sector RS rows, %d ranked",
             trade_date, n, n_sector, n_ranked)
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

def _print_symbol_tail(symbol: str, rs_hist: list[dict], den_label: str = BROAD) -> None:
    """Print the latest 5 days' adj_close / RS ratio / slopes / trend_state for
    one symbol against `den_label` — the user's spot-check (e.g. PARAS broad, or
    a sector). den_label is only a display/label arg; the RS math is unchanged."""
    if not rs_hist:
        log.info("%s: no RS history (no overlap with %s, or no bhav)", symbol, den_label)
        return
    tail = rs_hist[-5:]
    print(f"\n{symbol} — latest {len(tail)} RS days (rs = adj_close / {den_label}):")
    print(f"{'date':<12}{'adj_close':>12}{'rs_ratio':>14}"
          f"{'s1m':>8}{'s3m':>8}{'s6m':>8}{'s12m':>8}  trend")
    for r in tail:
        sig = compute_ratio_signal(symbol, den_label, rs_hist, r["trade_date"])
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
                   help="All symbols: broad RS + percentile rank + sector RS.")
    p.add_argument("--sector-backfill", action="store_true",
                   help="Only the stock-vs-sector RS pass (~500 symbols, fast).")
    p.add_argument("--rank-only", action="store_true",
                   help="Only the cross-stock percentile rank pass (all dates).")
    p.add_argument("--date", type=str, help="YYYY-MM-DD — one date: broad + sector + that date's rank pass")
    p.add_argument("--symbol", type=str,
                   help="One symbol's full broad+sector RS + print latest 5 days for verification")
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
        log.info("%s: %d broad RS rows updated", sym, updated)
        _print_symbol_tail(sym, rs_hist)
        # D33b — sector RS for the same symbol against its primary sector.
        sector = primary_sector_map().get(sym)
        if not sector:
            log.info("%s: no primary sector (not in any NSE sectoral index) — "
                     "broad RS only", sym)
        else:
            cm = _sector_close_maps({sector}).get(sector)
            if not cm:
                log.warning("%s: sector %s has no index history", sym, sector)
            else:
                s_hist, s_updated = compute_symbol_sector_rs(sym, sector, cm)
                log.info("%s: %d sector RS rows updated (primary_sector=%s)",
                         sym, s_updated, sector)
                _print_symbol_tail(sym, s_hist, den_label=sector)
    elif args.rank_only:
        n = run_rank_pass()
        log.info("rank-only complete: %d rows ranked", n)
    elif args.sector_backfill:
        n_syms, n_rows = run_sector_backfill()
        log.info("sector-backfill complete: %d symbols, %d sector RS rows", n_syms, n_rows)
    elif args.date:
        n, n_ranked = compute_for_date(args.date)
        log.info("date %s done: %d broad RS rows, %d ranked (+ sector RS)",
                 args.date, n, n_ranked)
    elif args.backfill:
        n_syms, n_rows = run_backfill()
        log.info("broad backfill complete: %d symbols, %d RS rows updated", n_syms, n_rows)
        s_syms, s_rows = run_sector_backfill()
        log.info("sector backfill complete: %d symbols, %d sector RS rows", s_syms, s_rows)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
