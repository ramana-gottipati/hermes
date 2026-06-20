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

# window chip -> (label, DVPT ratio column to RANK BY + LEAD with). "" keeps the
# default p_score order (today's strong-hand read). The 1M/3M lenses re-rank by
# how today's delivery compares to the best delivery days of that window — the
# accumulation analogue of the RS-window rule (reporting follows the question).
# Column names come ONLY from this constant, never from user input.
ACC_WINDOW: dict[str, tuple[str, str | None]] = {
    "":   ("Latest read", None),
    "1m": ("vs 1M power", "ratio_today_vs_power_1m"),
    "3m": ("vs 3M power", "ratio_today_vs_power_3m"),
}

ACC_LIMIT = 60  # safety cap on rows returned (not user-controllable)


def build_accumulation_query(sector: str = "", strength: str = "", entry: str = "",
                             window: str = "") -> tuple[str, list]:
    """Compile the accumulation screen to a read-only SELECT over stock_signals.

    Always enforces ACCUMULATION character + an active strong hand (p_score >=
    the chosen strength) over the equity-only universe, for the latest date.
    `sector` and `entry` are optional narrowings. `window` (''/1m/3m) chooses the
    DVPT power-ratio to RANK BY and LEAD with, so "being accumulated over the last
    month" ranks by the 1M reading — the column comes only from the ACC_WINDOW
    constant. Every value is bound via a placeholder — never string-formatted in.
    """
    min_p = ACC_STRENGTH.get(strength, ACC_STRENGTH[""])[1]
    ratio_col = ACC_WINDOW.get(window, ACC_WINDOW[""])[1]
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
    win_select = f"s.{ratio_col} AS win_ratio" if ratio_col else "NULL AS win_ratio"
    # When a window is asked, lead the ranking by that DVPT ratio (NULLs last),
    # then p_score; otherwise the default today's-strength order.
    order = (f"(s.{ratio_col} IS NULL), s.{ratio_col} DESC, s.p_score DESC, s.symbol"
             if ratio_col else
             "s.p_score DESC, (s.rs_rank IS NULL), s.rs_rank DESC, s.symbol")
    sql = (
        "SELECT s.symbol, pe.close AS cmp, " + win_select + ", s.trigger_rank, "
        "s.p_score, s.r_score, s.accum_character, s.price_vs_hot_avg_pct, "
        "s.gap_to_key_p3m, s.pct_from_52w_high, s.rs_rank, s.primary_sector, "
        "s.delivery_value_today "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY " + order + " "
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


# window chip -> (column label, RS-slope suffix). Maps a question's timeframe onto
# which RS slope to RANK BY + SHOW ("over the last month" -> 1m), so the reporting
# follows the ask instead of a fixed 3m.
RS_WINDOW = {
    "":    ("RS 3M", "3m"),
    "1m":  ("RS 1M", "1m"),
    "6m":  ("RS 6M", "6m"),
    "12m": ("RS 1Y", "12m"),
}


def build_rs_query(sector: str = "", strength: str = "", align: str = "",
                   window: str = "") -> tuple[str, list]:
    """Compile the RS-leaders screen to a read-only SELECT over stock_signals.

    `strength` gates on rs_rank; `sector` narrows to one primary sector;
    `align='sis'` requires above-200-DMA on BOTH RS lines. `window` (1m/3m/6m/12m)
    chooses which RS slope to RANK BY and DISPLAY — so "strongest over the last
    month" ranks by the 1m RS, not a fixed 3m. The slope-column suffix comes only
    from the RS_WINDOW constant (never raw input); all values are bound.
    """
    min_rank = RS_STRENGTH.get(strength, RS_STRENGTH[""])[1]
    col = "rs_vs_broad_slope_" + RS_WINDOW.get(window, RS_WINDOW[""])[1]
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
        f"SELECT s.symbol, pe.close AS cmp, s.rs_rank, s.{col} AS rs_slope, "
        "s.rs_vs_broad_trend_state, s.rs_vs_sector_trend_state, "
        "s.rs_vs_broad_above_200ma, s.rs_vs_sector_above_200ma, "
        "s.primary_sector, s.trigger_rank, s.accum_character, s.delivery_value_today "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "WHERE " + " AND ".join(where) + " "
        f"ORDER BY (s.{col} IS NULL), s.{col} DESC, s.symbol "
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


# ── fundamentals flow ────────────────────────────────────────────────────────
# Chip tuple = (label, column, op, threshold); "" = default tier, "any" = no
# clause. Thresholds reuse scoring.py's numbers so the screener and the 14-pattern
# scorer never disagree. Core gates (VAL/QUAL/GROW) are STRICT (`col op ?` — a
# missing value can't vouch for a name); BS/OWN are NULL-TOLERANT
# (`col op ? OR col IS NULL`) so a name isn't dropped for an unscraped ratio.
FUND_VAL = {
    "":         ("P/E < 25",       "pe", "<", 25),
    "deep":     ("P/E < 15",       "pe", "<", 15),
    "growthok": ("P/E < 40",       "pe", "<", 40),
    "any":      ("Any valuation",  None, None, None),
}
FUND_QUAL = {
    "":       ("ROCE > 18%",  "roce", ">", 18),
    "elite":  ("ROCE > 22%",  "roce", ">", 22),
    "decent": ("ROCE > 14%",  "roce", ">", 14),
    "any":    ("Any ROCE",    None, None, None),
}
FUND_GROW = {
    "":       ("Profit 5Y > 15%",  "profit_growth_5y",  ">", 15),
    "hyper":  ("Profit 5Y > 25%",  "profit_growth_5y",  ">", 25),
    "recent": ("Profit TTM > 20%", "profit_growth_ttm", ">", 20),
    "any":    ("Any growth",       None, None, None),
}
FUND_BS = {  # soft / NULL-tolerant
    "":         ("D/E < 1.0",      "debt_to_equity", "<", 1.0),
    "fortress": ("D/E < 0.5",      "debt_to_equity", "<", 0.5),
    "levok":    ("D/E < 2.0",      "debt_to_equity", "<", 2.0),
    "any":      ("Any leverage",   None, None, None),
}
FUND_OWN = {  # soft / NULL-tolerant
    "":      ("Promoter ≥ 35%", "promoter_holding", ">=", 35),
    "skin":  ("Promoter ≥ 50%", "promoter_holding", ">=", 50),
    "clean": ("Pledge < 5%",    "promoter_pledge",  "<", 5),
    "any":   ("Any ownership",  None, None, None),
}
FUND_SECTOR = {
    "":    "Exclude financials",
    "fin": "Financials only",
    "all": "All sectors",
}

# Financials detected via membership in any financial-sector NSE index — reuses
# the existing stock_index_membership table (no new table to seed). A heuristic,
# but dependency-free and good enough to honor the "don't judge banks on D/E" rule.
_FIN_SUBQUERY = (
    "SELECT DISTINCT symbol FROM stock_index_membership WHERE "
    "index_name LIKE '%Bank%' OR index_name LIKE '%Financ%' "
    "OR index_name LIKE '%NBFC%' OR index_name LIKE '%Insur%'"
)

FUND_LIMIT = 60
_FUND_OP_OK = {">", "<", ">=", "<="}

# One-tap presets — fixed chip combinations (analyst spec). label + param dict.
NAMED_SCREENS = {
    "compounders": ("Quality compounders",
                    {"qual": "elite", "grow": "hyper", "own": "skin", "val": "growthok"}),
    "deepvalue":   ("Deep value",
                    {"val": "deep", "qual": "decent", "bs": "fortress", "own": "clean", "grow": "any"}),
    "cleangrowth": ("Clean-sheet growth",
                    {"bs": "fortress", "own": "clean"}),
    "qualfin":     ("Quality financials",
                    {"sector": "fin"}),
}


def build_fundamentals_query(val="", qual="", grow="", bs="", sector="", own="") -> tuple[str, list]:
    """Compile the fundamentals screen to a read-only SELECT over `fundamentals`.

    Core gates (valuation/quality/growth) are strict; balance-sheet & ownership
    are NULL-tolerant. Financials get special handling: the leverage gate is
    dropped and the returns floor relaxed (their D/E is 6-8x by design and ROCE
    is leverage-suppressed), and the result is ranked by ROE not ROCE.
    """
    where = ["f.symbol IN (SELECT symbol FROM nse_equity_list)"]
    params: list = []
    # Sector handling first — it can rewrite bs/qual/own for financials.
    if sector == "fin":
        where.append(f"f.symbol IN ({_FIN_SUBQUERY})")
        bs = "any"                          # leverage gate off (6-8x is by design)
        own = "any"                         # banks are often widely held — promoter gate N/A
        if qual in ("", "elite"):
            qual = "decent"                 # relax returns floor (judged on ROE below)
    elif sector == "all":
        bs = "any"                          # don't let a D/E gate delete the banks
    else:
        where.append(f"f.symbol NOT IN ({_FIN_SUBQUERY})")
    # Strict core gates: valuation + growth.
    for grp, key in [(FUND_VAL, val), (FUND_GROW, grow)]:
        _lbl, col, op, thr = grp.get(key, grp[""])
        if col and op in _FUND_OP_OK:
            where.append(f"f.{col} {op} ?")
            params.append(thr)
    # Quality gate — ROCE normally, ROE for financials (their ROCE is leverage-suppressed).
    _qlbl, _qcol, qop, qthr = FUND_QUAL.get(qual, FUND_QUAL[""])
    if _qcol and qop in _FUND_OP_OK:
        where.append(f"f.{'roe' if sector == 'fin' else 'roce'} {qop} ?")
        params.append(qthr)
    # Soft, NULL-tolerant gates: balance sheet + ownership.
    for grp, key in [(FUND_BS, bs), (FUND_OWN, own)]:
        _lbl, col, op, thr = grp.get(key, grp[""])
        if col and op in _FUND_OP_OK:
            where.append(f"(f.{col} {op} ? OR f.{col} IS NULL)")
            params.append(thr)
    order = ("f.roe DESC, (f.pe IS NULL), f.pe ASC, f.symbol" if sector == "fin"
             else "f.roce DESC, (f.pe IS NULL), f.pe ASC, f.symbol")
    sql = (
        "SELECT f.symbol, f.current_price AS cmp, f.market_cap_cr, f.pe, f.roce, f.roe, "
        "f.profit_growth_5y, f.debt_to_equity, f.promoter_holding, f.promoter_pledge "
        "FROM fundamentals f "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY " + order + " LIMIT " + str(FUND_LIMIT)
    )
    return sql, params


# ── movers flow — biggest PRICE MOVES TODAY (the gap that mis-routed to RS) ───
# direction chip -> (label, ORDER BY); liq chip -> (label, min turnover ₹).
MOVERS_DIR = {
    "":       ("Top gainers", "pct DESC"),
    "losers": ("Top losers",  "pct ASC"),
    "active": ("Most active", "turnover DESC"),
}
MOVERS_LIQ = {
    "":    ("Liquid (≥ ₹5Cr)", 5e7),
    "all": ("All",             None),
}
# window chip -> (label, % column header, reference-date SQLite modifier). "" =
# today (vs the previous close); "1w" = the week's move (vs the close ~7 calendar
# days back, the latest session on-or-before). Reporting follows the question.
MOVERS_WINDOW: dict[str, tuple[str, str, str | None]] = {
    "":   ("Today", "% chg", None),
    "1w": ("This week", "% 1W", "-7 day"),
}
MOVERS_LIMIT = 60


def build_movers_query(direction: str = "", liq: str = "", window: str = "") -> tuple[str, list]:
    """Top % movers over the equity-cash universe, for the asked window.

    Default ('') = the latest session's move vs the previous close. window='1w'
    measures the move vs the close ~7 calendar days back (the latest session
    on-or-before that date), so "biggest movers this week" leads with the weekly
    %. A turnover floor (default ₹5Cr) keeps it to real liquidity. Read-only;
    ORDER BY and the date modifier come only from the MOVERS_DIR/MOVERS_WINDOW
    constants; every value is bound.
    """
    floor = MOVERS_LIQ.get(liq, MOVERS_LIQ[""])[1]
    order = MOVERS_DIR.get(direction, MOVERS_DIR[""])[1]
    modifier = MOVERS_WINDOW.get(window, MOVERS_WINDOW[""])[2]
    params: list = []

    if modifier is None:
        # Today: straight off the bhav copy (close vs prev_close).
        where = [
            "pe.trade_date = (SELECT MAX(trade_date) FROM bhavcopy_rows)",
            "pe.symbol IN (SELECT symbol FROM nse_equity_list)",
            "pe.prev_close > 0",
        ]
        if floor is not None:
            where.append("pe.value >= ?")
            params.append(floor)
        sql = (
            "SELECT pe.symbol, pe.close AS cmp, pe.prev_close AS ref_close, "
            "(pe.close - pe.prev_close) * 100.0 / pe.prev_close AS pct, "
            "pe.value AS turnover, pe.deliv_per, pe.volume "
            "FROM prices_eq pe "
            "WHERE " + " AND ".join(where) + " "
            "ORDER BY " + order + ", pe.symbol "
            "LIMIT " + str(MOVERS_LIMIT)
        )
        return sql, params

    # This week: join today's row to the week-ago session's close. The reference
    # date = the latest session on-or-before (latest − 7 days). Placeholder ORDER
    # matters: the date() modifier sits in the JOIN (earlier in the SQL text) so it
    # MUST be bound before the turnover floor in the WHERE.
    params.append(modifier)
    where = [
        "cur.trade_date = (SELECT MAX(trade_date) FROM bhavcopy_rows)",
        "cur.symbol IN (SELECT symbol FROM nse_equity_list)",
        "wk.close > 0",
    ]
    if floor is not None:
        where.append("cur.value >= ?")
        params.append(floor)
    sql = (
        "SELECT cur.symbol, cur.close AS cmp, wk.close AS ref_close, "
        "(cur.close - wk.close) * 100.0 / wk.close AS pct, "
        "cur.value AS turnover, cur.deliv_per, cur.volume "
        "FROM prices_eq cur "
        "JOIN prices_eq wk ON wk.symbol = cur.symbol AND wk.trade_date = ("
        "  SELECT MAX(trade_date) FROM bhavcopy_rows WHERE trade_date <= "
        "  date((SELECT MAX(trade_date) FROM bhavcopy_rows), ?)) "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY " + order + ", cur.symbol "
        "LIMIT " + str(MOVERS_LIMIT)
    )
    return sql, params
