"""Pat data flows — pure, read-only SQL templates compiled from chip parameters.

No DB handle and no LLM live here: each builder returns ``(sql, params)`` for a
single parameterized SELECT. The chips ARE the parameters, so the query can
never reference a column the user invented — this is the deterministic,
zero-cost "gets me the data" path. (When the Gemini engine lands, it only picks
the flow + fills these same enumerated params; it never writes SQL.)

Phase 1: the accumulation flow over the daily ``stock_signals`` table — the only
table that carries the D43 ``accum_character`` read.
"""

from __future__ import annotations

# strength chip key -> (label, minimum p_score)
ACC_STRENGTH: dict[str, tuple[str, int]] = {
    "":    ("Strong (A+)",      3),
    "ss":  ("Very strong (SS)", 5),
    "any": ("Any active hand",  1),
}

# entry chip key -> label
ACC_ENTRY: dict[str, str] = {
    "":         "Any entry",
    "discount": "Near a discount",
}

ACC_LIMIT = 60  # safety cap on rows returned (not user-controllable)


def build_accumulation_query(sector: str = "", strength: str = "", entry: str = "") -> tuple[str, list]:
    """Compile the accumulation screen to a read-only SELECT over stock_signals.

    Always enforces ACCUMULATION character + an active strong hand (p_score >=
    the chosen strength) over the equity-only universe, for the latest date.
    `sector` and `entry` are optional narrowings. Every value is bound via a
    placeholder — never string-formatted into the SQL.
    """
    min_p = ACC_STRENGTH.get(strength, ACC_STRENGTH[""])[1]
    where = [
        "s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
        "s.accum_character = 'ACCUMULATION'",
        "s.symbol IN (SELECT symbol FROM nse_equity_list)",
        "s.p_score >= ?",
    ]
    params: list = [min_p]
    if sector:
        where.append("s.primary_sector = ?")
        params.append(sector)
    if entry == "discount":
        where.append("s.price_vs_hot_avg_pct <= -3")
    sql = (
        "SELECT s.symbol, pe.close AS cmp, s.trigger_rank, s.p_score, s.r_score, "
        "s.accum_character, s.price_vs_hot_avg_pct, s.gap_to_key_p3m, "
        "s.pct_from_52w_high, s.rs_rank, s.primary_sector, s.delivery_value_today "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY s.p_score DESC, (s.rs_rank IS NULL), s.rs_rank DESC, s.symbol "
        "LIMIT " + str(ACC_LIMIT)
    )
    return sql, params


def build_accumulation_sectors_query() -> str:
    """Sectors that actually have accumulation today — drives the sector chips."""
    return (
        "SELECT s.primary_sector AS sector, COUNT(*) AS c "
        "FROM stock_signals s "
        "WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals) "
        "AND s.accum_character = 'ACCUMULATION' "
        "AND s.primary_sector IS NOT NULL "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list) "
        "GROUP BY s.primary_sector ORDER BY c DESC, s.primary_sector LIMIT 14"
    )


# strength chip key -> (label, minimum rs_rank)
RS_STRENGTH: dict[str, tuple[str, int]] = {
    "":      ("Leaders (RS ≥ 80)",      80),
    "elite": ("Elite (RS ≥ 90)",        90),
    "above": ("Above market (RS ≥ 50)", 50),
}

# alignment chip key -> label. "sis" = strong-in-strong (beating market AND sector).
RS_ALIGN: dict[str, str] = {
    "":    "Any",
    "sis": "Strong in strong",
}

RS_LIMIT = 60


def build_rs_query(sector: str = "", strength: str = "", align: str = "") -> tuple[str, list]:
    """Compile the RS-leaders screen to a read-only SELECT over stock_signals.

    High rs_rank (cross-stock momentum percentile), equity-only, latest date.
    `sector` narrows to one primary sector; `align='sis'` requires the stock to
    be above its 200-DMA on BOTH the vs-broad and vs-sector RS lines (the
    stock-level "strong in strong" read). All values bound via placeholders.
    """
    min_rank = RS_STRENGTH.get(strength, RS_STRENGTH[""])[1]
    where = [
        "s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
        "s.symbol IN (SELECT symbol FROM nse_equity_list)",
        "s.rs_rank IS NOT NULL",
        "s.rs_rank >= ?",
    ]
    params: list = [min_rank]
    if sector:
        where.append("s.primary_sector = ?")
        params.append(sector)
    if align == "sis":
        where.append("s.rs_vs_broad_above_200ma = 1")
        where.append("s.rs_vs_sector_above_200ma = 1")
    sql = (
        "SELECT s.symbol, pe.close AS cmp, s.rs_rank, s.rs_vs_broad_slope_3m, "
        "s.rs_vs_broad_trend_state, s.rs_vs_sector_trend_state, "
        "s.rs_vs_broad_above_200ma, s.rs_vs_sector_above_200ma, "
        "s.primary_sector, s.trigger_rank, s.accum_character, s.delivery_value_today "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY s.rs_rank DESC, s.symbol "
        "LIMIT " + str(RS_LIMIT)
    )
    return sql, params


def build_rs_sectors_query() -> str:
    """Sectors that hold RS leaders (rs_rank >= 80) today — drives the sector chips."""
    return (
        "SELECT s.primary_sector AS sector, COUNT(*) AS c "
        "FROM stock_signals s "
        "WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals) "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list) "
        "AND s.rs_rank >= 80 AND s.primary_sector IS NOT NULL "
        "GROUP BY s.primary_sector ORDER BY c DESC, s.primary_sector LIMIT 14"
    )
