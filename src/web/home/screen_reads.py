"""src/web/home/screen_reads.py — the Graphite screener's self-contained, read-only data layer.

Lane W4 (milestone M8). The twin of `reads.py` for the screener estate, kept in a SEPARATE
lane-owned module so the Markets/Today read layer is never co-edited.

IMPORT BAN (gate: tests/test_home_isolation.py): imports ONLY `src.core.db` + genuinely-shared,
NON-render, read-only helpers (`src.automation.theme_tags` — a data module that returns rows, not
HTML). It NEVER imports a classic web-VIEW module (`screener_plus`, `dashboard`, `cockpit`, …) to
borrow an engine: the approved pattern is to read the SAME precomputed tables directly.

Doctrine carried over verbatim from the classic screener:
  * PRECOMPUTED tables only — never recompute a strategy on read.
  * The liquidity gate is a self-scaling TURNOVER PERCENTILE (CL-VIEW-15), never a static rupee
    threshold: keep names at/above the 30th percentile of THAT day's EQ turnover.
  * Every read is bounded + defensive: a missing table returns an empty result, never an exception.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

# ── the universe cap. The base query is ordered by a stable conviction key BEFORE the cap, so a
# scope larger than this keeps its most-aligned names. Disclosed on the page (never a silent trim).
UNIVERSE_CAP = 2000

_LIQ_PCTILE = 0.30

_BROAD = ("Nifty 50", "Nifty Next 50", "Nifty Midcap 150", "Nifty Smallcap 250", "Nifty 500")
_SECTORS = ("Nifty Bank", "Nifty Financial Services", "Nifty IT", "Nifty Auto", "Nifty Pharma",
            "Nifty FMCG", "Nifty Metal", "Nifty Energy", "Nifty Realty", "Nifty Media",
            "Nifty Infrastructure", "Nifty Commodities", "Nifty Healthcare Index",
            "Nifty Consumer Durables", "Nifty Oil & Gas", "Nifty India Defence",
            "Nifty Private Bank", "Nifty Chemicals")


def broad_indices() -> tuple:
    return _BROAD


def sector_indices() -> tuple:
    return _SECTORS


# ── primitives (own copies — reads.py is a sibling lane's file, never edited from here) ──────
def _has(conn, table: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _rows(conn, sql: str, params=()) -> list:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def latest_date(conn) -> Optional[str]:
    try:
        r = conn.execute("SELECT MAX(trade_date) AS d FROM stock_signals").fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None


def turnover_floor(conn, sig_date) -> float:
    """The day's 30th-percentile EQ turnover — a self-scaling liquidity floor (CL-VIEW-15: no static
    rupee number; the cutoff re-derives every day from the data). 0.0 on any miss, so the gate
    degrades to 'all turnover > 0' rather than an error."""
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM bhavcopy_rows b WHERE b.trade_date=? AND b.series='EQ' "
            "AND (b.segment='CM' OR b.segment IS NULL) AND b.value > 0 "
            "AND b.symbol IN (SELECT symbol FROM nse_equity_list)", (sig_date,)).fetchone()[0]
        if not n:
            return 0.0
        r = conn.execute(
            "SELECT b.value FROM bhavcopy_rows b WHERE b.trade_date=? AND b.series='EQ' "
            "AND (b.segment='CM' OR b.segment IS NULL) AND b.value > 0 "
            "AND b.symbol IN (SELECT symbol FROM nse_equity_list) "
            "ORDER BY b.value LIMIT 1 OFFSET ?", (sig_date, int(_LIQ_PCTILE * n))).fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except (sqlite3.Error, TypeError, ValueError):
        return 0.0


def scope_symbols(conn, scope: str) -> Optional[list]:
    """The symbol universe for a scope. None = 'every liquid EQ name' (no symbol restriction).

    Scopes: `all` · `watch` · `theme:<Tag>` (the themes page's hand-off) · any index name."""
    s = (scope or "").strip()
    low = s.lower()
    if low == "all":
        return None
    if low in ("watch", "watchlist"):
        out = [r["symbol"] for r in _rows(conn, "SELECT symbol FROM watchlist ORDER BY symbol")]
        if not out:
            out = [r["symbol"] for r in _rows(
                conn, "SELECT symbol FROM stocks_in_play WHERE status='watch' ORDER BY symbol")]
        return out
    if low.startswith("theme:"):
        return theme_members(conn, s.split(":", 1)[1])
    return [r["symbol"] for r in _rows(
        conn,
        "SELECT symbol FROM stock_index_membership WHERE index_name=? AND snapshot_date=("
        "  SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name=?) ORDER BY symbol",
        (s, s))]


# ── the base universe read ───────────────────────────────────────────────────────────────────
# Ordered by the same descriptive conviction key the classic screener uses, so the UNIVERSE_CAP
# keeps the most-aligned names. `conv` is a SORTING HEURISTIC, never a validated model (fenced
# on the page); it is not exposed as a column.
_CONV = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"

_BASE_SQL = """
SELECT s.symbol, s.primary_sector, b.close, b.deliv_per, b.value AS turnover,
       s.delivery_value_per_trade, s.trigger_rank, s.p_score, s.r_score,
       s.ratio_today_vs_power_1m, s.next_p_above, s.gap_to_next_p_pct, s.is_ath_dvpt,
       s.power_dvpt_1m, s.power_dvpt_2m, s.power_dvpt_3m, s.power_dvpt_6m, s.power_dvpt_12m,
       s.rs_rank, s.rs_vs_broad_trend_state, s.rs_phase, s.rsi_of_rs, s.rs_vs_broad_1w,
       s.rs_vs_broad_slope_1m, s.rs_vs_broad_slope_3m, s.rs_vs_broad_slope_6m,
       s.rs_vs_broad_slope_12m, s.rs_vs_broad_slope_18m, s.rs_vs_broad_slope_24m,
       s.accum_character, s.turnover_surge_1m, s.turnover_surge_3m, s.turnover_surge_1y,
       s.ticket_ratio_1m_6m, s.trade_count_ratio_1m_6m, s.deliv_updown_ratio_3m,
       s.pct_from_52w_high, s.deliv_value_ratio_1m_6m, s.avg_deliv_pct_1m, s.avg_deliv_pct_6m,
       s.accum_price_drift_3m,
       s.key_price_p3m, s.key_price_p6m, s.key_price_p12m,
       s.gap_to_key_p3m, s.gap_to_key_p6m, s.gap_to_key_p12m,
       s.avg_close_p3m, s.avg_trade_qty, s.avg_deliv_qty_per_trade,
       s.delivery_value_today, s.total_value_today,
       m.mep_score_smooth, m.mep_state_smooth
FROM stock_signals s
JOIN bhavcopy_rows b USING (symbol, trade_date)
LEFT JOIN mep_signals m ON m.symbol=s.symbol AND m.trade_date=s.trade_date
WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
  AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
  AND b.value >= ?
  AND s.symbol IN (SELECT symbol FROM nse_equity_list)
"""


def base_rows(conn, sig_date, syms: Optional[list], cap: int = UNIVERSE_CAP) -> list:
    """The scope's liquid universe, bounded by `cap`. Rows are plain dicts (never HTML)."""
    if not sig_date:
        return []
    params: list = [sig_date, turnover_floor(conn, sig_date)]
    clause = ""
    if syms is not None:
        use = syms or ["\x00"]                 # an empty scope must select nothing, not everything
        clause = " AND s.symbol IN (" + ",".join("?" for _ in use) + ")"
        params += list(use)
    params.append(int(cap))
    return _rows(conn, _BASE_SQL + clause + f" ORDER BY {_CONV} DESC, COALESCE(s.p_score,-1) DESC LIMIT ?",
                 params)


# ── the auxiliary per-symbol lookups (one batched query each; run only when needed) ───────────
def _in(syms):
    return ",".join("?" for _ in syms)


def cpr_by_tf(conn, syms, tf: str) -> dict:
    if not syms or not _has(conn, "cpr_signals"):
        return {}
    try:
        d = conn.execute("SELECT MAX(period_end_date) FROM cpr_signals WHERE timeframe=?", (tf,)).fetchone()[0]
    except (sqlite3.Error, TypeError):
        return {}
    if not d:
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"SELECT * FROM cpr_signals WHERE timeframe=? AND period_end_date=? "
              f"AND symbol IN ({_in(syms)})", [tf, d, *syms])}


def cci_by_sym(conn, syms) -> dict:
    if not syms or not _has(conn, "concall_scores"):
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"""SELECT s.symbol, s.composite_score, s.tier, s.credibility_trend
                  FROM concall_scores s
                  JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x
                    ON x.symbol=s.symbol AND x.m=s.last_updated
                  WHERE s.symbol IN ({_in(syms)})""", list(syms))}


def wolfe_by_sym(conn, syms) -> dict:
    """Latest Wolfe scan per symbol (wolfe_signals, owned by wolfe.py — READ-ONLY here).
    DESCRIPTIVE: the §C falsification stands — Wolfe is geometry SELECTION, never a call."""
    if not syms or not _has(conn, "wolfe_signals"):
        return {}
    out: dict = {}
    for r in _rows(conn, f"""SELECT w.sym, w.dir, w.in_zone, w.q, w.scan_date FROM wolfe_signals w
                             JOIN (SELECT sym, MAX(scan_date) m FROM wolfe_signals GROUP BY sym) x
                               ON x.sym=w.sym AND x.m=w.scan_date
                             WHERE w.sym IN ({_in(syms)})""", list(syms)):
        prev = out.get(r["sym"])
        if (prev is None or (r.get("in_zone") or 0) > (prev.get("in_zone") or 0)
                or ((r.get("in_zone") or 0) == (prev.get("in_zone") or 0)
                    and (r.get("q") or 0) > (prev.get("q") or 0))):
            out[r["sym"]] = r
    return out


def pt14_by_sym(conn, syms) -> dict:
    if not syms or not _has(conn, "pattern_scores"):
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"""SELECT p.symbol, p.ns_base, p.tier, p.qg_pass, p.hard_disqualified
                  FROM pattern_scores p
                  JOIN (SELECT symbol, MAX(scored_at) m FROM pattern_scores GROUP BY symbol) x
                    ON x.symbol=p.symbol AND x.m=p.scored_at
                  WHERE p.symbol IN ({_in(syms)})""", list(syms))}


def calloc_by_sym(conn, syms) -> dict:
    """Capital-allocation (C) composite. S77b: a DESCRIPTIVE column / blend tilt, never a veto."""
    if not syms or not _has(conn, "capital_allocation_scores"):
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"""SELECT c.symbol, c.ca_score, c.ca_tier FROM capital_allocation_scores c
                  JOIN (SELECT symbol, MAX(as_of) m FROM capital_allocation_scores GROUP BY symbol) x
                    ON x.symbol=c.symbol AND x.m=c.as_of
                  WHERE c.symbol IN ({_in(syms)})""", list(syms))}


def revctx_by_sym(conn, syms) -> dict:
    """reversal_context (owned by reversal_context.py — READ-ONLY here). DESCRIPTIVE ONLY: the whole
    reversal-pair arc was falsified as a trading signal (ledger 2026-07-13/14/14b). What survives is
    context — band state, own-history stretch percentile, the confirmed fractal as a risk level."""
    if not syms or not _has(conn, "reversal_context"):
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"SELECT * FROM reversal_context WHERE symbol IN ({_in(syms)})", list(syms))}


def fno_by_sym(conn, syms) -> dict:
    """Latest per-stock F&O positioning (NSE-primary `fno_oi_signals`). Phase-0 verdict (2026-07-24):
    PCR selects only weakly and is forward-test-only; max-pain / basis / OI-change FAILED. Carried
    here as DESCRIPTIVE context columns, never as a ranker."""
    if not syms or not _has(conn, "fno_oi_signals"):
        return {}
    try:
        d = conn.execute("SELECT MAX(trade_date) FROM fno_oi_signals").fetchone()[0]
    except (sqlite3.Error, TypeError):
        return {}
    if not d:
        return {}
    return {r["symbol"]: r for r in _rows(
        conn, f"""SELECT symbol, fut_oi, fut_oi_chg_pct, quadrant, pcr FROM fno_oi_signals
                  WHERE trade_date=? AND symbol IN ({_in(syms)})""", [d, *syms])}


# ── themes / baskets (the non-ticker discovery surface) ──────────────────────────────────────
def theme_members(conn, tag: str) -> list:
    try:
        from src.automation import theme_tags as TT
        return TT.theme_members(conn, (tag or "").strip())
    except Exception:  # noqa: BLE001 — a themes miss must never break the screener
        return []


def theme_board(conn) -> list:
    """[{group, themes:[{label, blurb, n, seeded}]}] — the browsable theme map, grouped in the
    canonical display order. Counts are APPROVED tags only (proposals are an owner workflow)."""
    try:
        from src.automation import theme_tags as TT
    except Exception:  # noqa: BLE001
        return []
    try:
        counts = TT.theme_counts(conn, approved_only=True)
    except Exception:  # noqa: BLE001
        counts = {}
    groups: list = []
    for g in getattr(TT, "THEME_GROUPS", []):
        items = []
        for entry in getattr(TT, "THEME_VOCAB", []):
            if entry.get("group") != g:
                continue
            items.append({"label": entry["label"], "blurb": entry.get("blurb") or "",
                          "n": int(counts.get(entry["label"], 0) or 0),
                          "seeded": bool(entry.get("seed_indices"))})
        if items:
            groups.append({"group": g, "themes": items})
    return groups


def theme_provenance(conn, tag: str) -> dict:
    """{source: n_symbols} for one theme — index-seeded facts vs approved vs AI-proposed."""
    out = {}
    for r in _rows(conn, "SELECT source, COUNT(DISTINCT symbol) c FROM company_tags "
                         "WHERE tag=? AND approved=1 GROUP BY source", ((tag or "").strip(),)):
        out[r["source"]] = r["c"]
    return out
