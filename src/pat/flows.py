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

# character chip key -> (label, accum_character value bound into the query). The
# D43 `accum_character` column already classifies every stock as one of these four
# labels nightly; the accumulation flow only ever read ACCUMULATION. Binding the
# chosen side here unlocks the mirror screens (DISTRIBUTION = strong-hand EXITING,
# CONSOLIDATION = coiling) with no new data. The value comes ONLY from this dict.
ACC_CHARACTER: dict[str, tuple[str, str]] = {
    "":              ("Accumulation",  "ACCUMULATION"),
    "distribution":  ("Distribution",  "DISTRIBUTION"),
    "consolidation": ("Consolidation", "CONSOLIDATION"),
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


def _eff_limit(default_cap: int, top_n=None) -> int:
    """Resolve the effective LIMIT for a list flow: an explicit user 'top N'
    (clamped to 1..default_cap) when given, else the safety cap. The rows are
    ALWAYS ranked by the flow's metric first, so 'top N' = the N strongest —
    never an arbitrary slice. Non-numeric/absent top_n → the safety cap."""
    try:
        n = int(top_n) if top_n is not None else 0
    except (TypeError, ValueError):
        n = 0
    return min(max(n, 1), default_cap) if n > 0 else default_cap


def build_accumulation_query(sector: str = "", strength: str = "", entry: str = "",
                             window: str = "", character: str = "", top_n=None) -> tuple[str, list]:
    """Compile the accumulation screen to a read-only SELECT over stock_signals.

    Enforces the chosen `character` (ACCUMULATION default; DISTRIBUTION / CONSOLIDATION
    are the mirror screens) + an active strong hand (p_score >= the chosen strength)
    over the equity-only universe, for the latest date. `sector` and `entry` are
    optional narrowings. `window` (''/1m/3m) chooses the DVPT power-ratio to RANK BY
    and LEAD with, so "being accumulated over the last month" ranks by the 1M reading
    — the column comes only from the ACC_WINDOW constant. The character VALUE comes
    only from ACC_CHARACTER. Every value is bound via a placeholder — never string-
    formatted in.
    """
    min_p = ACC_STRENGTH.get(strength, ACC_STRENGTH[""])[1]
    ratio_col = ACC_WINDOW.get(window, ACC_WINDOW[""])[1]
    char_val = ACC_CHARACTER.get(character, ACC_CHARACTER[""])[1]
    where = [
        "s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
        "s.accum_character = ?",
        "s.symbol IN (SELECT symbol FROM nse_equity_list)",
        "s.p_score >= ?",
    ]
    params: list = [char_val, min_p]
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
        "LIMIT " + str(_eff_limit(ACC_LIMIT, top_n))
    )
    return sql, params


def build_accumulation_sectors_query(character: str = "") -> tuple[str, list]:
    """Sectors that actually have the chosen character today — drives the sector chips."""
    char_val = ACC_CHARACTER.get(character, ACC_CHARACTER[""])[1]
    return (
        "SELECT s.primary_sector AS sector, COUNT(*) AS c "
        "FROM stock_signals s "
        "WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals) "
        "AND s.accum_character = ? "
        "AND s.primary_sector IS NOT NULL "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list) "
        "GROUP BY s.primary_sector ORDER BY c DESC, s.primary_sector LIMIT 14"
    ), [char_val]


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

# direction chip key -> (label, comparator, sort). Laggards are the mirror Pat never
# served (the worst-stock side it used to honestly redirect away from): the weak end
# of rs_rank, ranked weakest-first. The leaders strength tiers are FLOORS (rs_rank >=
# N); for laggards the same chip keys become CEILINGS via RS_LAG_STRENGTH. The
# comparator + sort come ONLY from this constant — never from user input.
RS_DIRECTION: dict[str, tuple[str, str, str]] = {
    "":         ("Leaders (strong)", ">=", "DESC"),
    "laggards": ("Laggards (weak)",  "<=", "ASC"),
}
# strength key -> (label, rs_rank CEILING) for the laggard side (mirror of RS_STRENGTH).
RS_LAG_STRENGTH: dict[str, tuple[str, int]] = {
    "":      ("Laggards (RS ≤ 20)",      20),
    "elite": ("Deep laggards (RS ≤ 10)", 10),
    "above": ("Below market (RS ≤ 50)",  50),
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
                   window: str = "", direction: str = "", top_n=None) -> tuple[str, list]:
    """Compile the RS leaders/laggards screen to a read-only SELECT over stock_signals.

    `direction` flips leaders (rs_rank floor, DESC) vs laggards (rs_rank ceiling, ASC
    — the weak end Pat used to redirect away from). `strength` gates on rs_rank (a
    FLOOR for leaders via RS_STRENGTH, a CEILING for laggards via RS_LAG_STRENGTH);
    `sector` narrows to one primary sector; `align='sis'` (leaders only) requires
    above-200-DMA on BOTH RS lines. `window` (1m/3m/6m/12m) chooses which RS slope to
    RANK BY and DISPLAY. The comparator/sort come only from RS_DIRECTION and the
    slope-column suffix only from RS_WINDOW (never raw input); all values are bound.
    """
    lag = (direction == "laggards")
    _dlbl, cmp_op, sort = RS_DIRECTION.get(direction, RS_DIRECTION[""])
    rank_val = (RS_LAG_STRENGTH.get(strength, RS_LAG_STRENGTH[""])[1] if lag
                else RS_STRENGTH.get(strength, RS_STRENGTH[""])[1])
    col = "rs_vs_broad_slope_" + RS_WINDOW.get(window, RS_WINDOW[""])[1]
    where = [
        "s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
        "s.symbol IN (SELECT symbol FROM nse_equity_list)",
        "s.rs_rank IS NOT NULL",
        f"s.rs_rank {cmp_op} ?",
    ]
    params: list = [rank_val]
    if sector:
        where.append("s.primary_sector = ?")
        params.append(sector)
    if align == "sis" and not lag:          # strong-in-strong is a leaders-only lens
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
        f"ORDER BY (s.{col} IS NULL), s.{col} {sort}, s.symbol "
        "LIMIT " + str(_eff_limit(RS_LIMIT, top_n))
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
    "rich":     ("P/E > 40",       "pe", ">", 40),   # the expensive end — overvalued screen
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
    "overvalued":  ("Overvalued (expensive)",
                    {"val": "rich", "qual": "any", "grow": "any", "bs": "any", "own": "any"}),
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


# ── index flow — performance / rotation of NSE INDICES (D32 index_signals) ────
# The universe Pat was missing: sectoral + thematic indices, not single stocks.
# index_signals is pre-computed nightly with returns over every window + RS slopes.
# window chip -> (label, return column to RANK BY + lead with). "" = 3M default.
INDEX_WINDOW: dict[str, tuple[str, str]] = {
    "":   ("3M", "ret_3m_pct"),
    "1m": ("1M", "ret_1m_pct"),
    "6m": ("6M", "ret_6m_pct"),
    "1y": ("1Y", "ret_12m_pct"),
}
# direction chip -> (label, sort). leaders = best (DESC); laggards = WORST (ASC) —
# the polarity the stock flows never had ("worst performing ...").
INDEX_DIRECTION: dict[str, tuple[str, str]] = {
    "":         ("Leaders (best)",   "DESC"),
    "laggards": ("Laggards (worst)", "ASC"),
}
# turning chip -> label. When on, keep only indices UP over the last month
# (ret_1m_pct > 0) — "started performing better recently". Paired with laggards
# this is the 1-year-laggard-now-reversing screen (rotation into the beaten-down).
INDEX_TURNING: dict[str, str] = {
    "":     "Any",
    "turn": "Turning up (1M)",
}
INDEX_LIMIT = 40


def build_index_query(window: str = "", direction: str = "", turning: str = "") -> tuple[str, list]:
    """Compile the index-performance screen to a read-only SELECT over index_signals.

    `window` picks the return column to RANK BY + lead with; `direction` flips best
    (DESC) vs worst (ASC); `turning='turn'` keeps only indices up over the last
    month (ret_1m_pct > 0). The ranked column + sort come ONLY from the INDEX_*
    constants; the latest date is the only date. No user value is formatted into SQL.
    """
    ret_col = INDEX_WINDOW.get(window, INDEX_WINDOW[""])[1]
    sort = INDEX_DIRECTION.get(direction, INDEX_DIRECTION[""])[1]
    where = [
        "trade_date = (SELECT MAX(trade_date) FROM index_signals)",
        f"{ret_col} IS NOT NULL",
    ]
    if turning == "turn":
        where.append("ret_1m_pct > 0")
    sql = (
        f"SELECT index_name, close_value, {ret_col} AS lead_ret, "
        "ret_1m_pct, ret_3m_pct, ret_6m_pct, ret_12m_pct, "
        "rs_vs_broad_slope_1m, rs_vs_broad_trend_state, pct_off_52w_high "
        "FROM index_signals "
        "WHERE " + " AND ".join(where) + " "
        f"ORDER BY {ret_col} {sort}, index_name "
        "LIMIT " + str(INDEX_LIMIT)
    )
    return sql, []


# ── pt14 quality-tier + hard-disqualifier flows (over pattern_scores) ─────────
# pattern_scores holds one row per scoring RUN per stock; the latest run per symbol
# is MAX(id) (autoincrement PK — a unique, tie-free "newest"). These surface two
# things the framework already computes but no flow ever read: the quality TIERS
# (the pt14 headline) and the hard-disqualifier KILL-LIST (its own "avoid" verdict).
PT14_TIER: dict[str, tuple[str, str | None]] = {
    "":   ("All (gate pass)", None),
    "t1": ("Tier 1 only",     "T1"),
    "t2": ("Tier 2",          "T2"),
    "t3": ("Tier 3",          "T3"),
}
PT14_LIMIT = 80

_LATEST_PATTERN_JOIN = (
    "JOIN (SELECT symbol, MAX(id) AS mid FROM pattern_scores GROUP BY symbol) lx "
    "  ON lx.symbol = ps.symbol AND lx.mid = ps.id "
)


def build_pt14_query(tier: str = "") -> tuple[str, list]:
    """Latest pt14 score per stock, ordered by ns_base (the 0-100 headline) as a QUALITY-RISK
    triage — NOT a return rank (D66; pt14 is a filter/veto-context lens, NS long-short ≈ 0) —
    excluding hard-disqualified names. `tier` optionally narrows to one tier — the value comes
    only from PT14_TIER; ns_base ordering is fixed; bound throughout."""
    tval = PT14_TIER.get(tier, PT14_TIER[""])[1]
    where = ["(ps.hard_disqualified IS NULL OR ps.hard_disqualified = 0)"]
    params: list = []
    if tval:
        where.append("ps.tier = ?")
        params.append(tval)
    sql = (
        "SELECT ps.symbol, ps.tier, ps.ns_base, ps.ns_pessimistic, ps.ns_optimistic, "
        "ps.pac, ps.qg_pass "
        "FROM pattern_scores ps " + _LATEST_PATTERN_JOIN +
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY (ps.ns_base IS NULL), ps.ns_base DESC, ps.symbol "
        "LIMIT " + str(PT14_LIMIT)
    )
    return sql, params


def build_disqualified_query() -> tuple[str, list]:
    """The hard-disqualifier KILL-LIST: latest scoring run per stock where the
    framework flagged a fatal case, with the reason. Read-only, no user input."""
    sql = (
        "SELECT ps.symbol, ps.tier, ps.ns_base, ps.disqualifier_reasons "
        "FROM pattern_scores ps " + _LATEST_PATTERN_JOIN +
        "WHERE ps.hard_disqualified = 1 "
        "ORDER BY ps.symbol "
        "LIMIT " + str(PT14_LIMIT)
    )
    return sql, []


# ── CCI: Management Credibility (concall intelligence, P5) ────────────────────
# Ranked over concall_scores (the measurable-only composite, D61). Two views:
# credibility LEADERS (veto-excluded, best composite) and the DETERIORATION /
# avoid tape (veto OR a deterministic deterioration flag, worst-first). Latest
# score per symbol; all columns fixed, no user input → no injection surface.
CCI_LIMIT = 80
_CCI_LATEST = (
    "FROM concall_scores s "
    "JOIN (SELECT symbol, MAX(last_updated) AS m FROM concall_scores GROUP BY symbol) x "
    "  ON x.symbol = s.symbol AND x.m = s.last_updated "
)
_CCI_COLS = ("s.symbol, s.tier, s.composite_score, s.guidance_accuracy_score, "
             "s.quantification_rate, s.forward_direction, s.deterioration_score, "
             "s.veto_active, s.veto_reason, s.n_promises_resolved, s.as_of_period ")


def build_credibility_query(top_n=None) -> tuple[str, list]:
    """CCI TRACK RECORD — veto-excluded, coverage-first; NOT a ranked credibility list
    (D6-F1: CCI is falsified as a return factor). Latest score per symbol, ordered by
    #settled promises (coverage), never the composite. Read-only, no user input.
    ``top_n`` caps the list length (still coverage-ordered, not a 'top N strongest')."""
    sql = ("SELECT " + _CCI_COLS + _CCI_LATEST +
           "WHERE COALESCE(s.veto_active, 0) = 0 "
           "ORDER BY COALESCE(s.n_promises_resolved, 0) DESC, s.symbol "
           "LIMIT " + str(_eff_limit(CCI_LIMIT, top_n)))
    return sql, []


def build_deterioration_query() -> tuple[str, list]:
    """The AVOID TAPE — names carrying a ⛔ veto OR a deterministic deterioration
    flag (walk-back / dropped promise / stopped-disclosing), worst-first. The
    credibility-decay tape the sell-side won't publish. Read-only, no user input."""
    sql = ("SELECT " + _CCI_COLS + _CCI_LATEST +
           "WHERE COALESCE(s.veto_active, 0) = 1 OR COALESCE(s.deterioration_score, 0) > 0 "
           "ORDER BY COALESCE(s.veto_active, 0) DESC, COALESCE(s.deterioration_score, 0) DESC, s.symbol "
           "LIMIT " + str(CCI_LIMIT))
    return sql, []


# ── single-stock snapshot / red-flag card (one symbol → its row) ──────────────
# A different SHAPE from the ranked-universe flows: resolve a typed token to an NSE
# symbol, then read that symbol's latest signals + fundamentals + pt14. Answers
# "tell me about X / what's wrong with X" — which the screener engine never served.
def build_confluence_query() -> tuple[str, list]:
    """CCI x MEP CONFLUENCE — names that are BOTH being accumulated (the MEP/strong-hand
    delivery lens: accum_character ACCUMULATION + an active p_score) AND credible on the
    concall track record (veto-excluded, >=3 resolved promises, a real composite). The two
    INDEPENDENT lenses agreeing = the highest-evidence read. DESCRIPTIVE evidence only —
    never a ranked buy signal (the §C backtest found no return edge); the two reads are at
    different grains (daily delivery x quarterly credibility), disclosed by the as-of badges.
    Read-only, no user input → no injection surface."""
    sql = (
        "SELECT s.symbol, pe.close AS cmp, s.accum_character, s.p_score, s.r_score, "
        "s.trigger_rank, s.rs_rank, s.primary_sector, s.delivery_value_today, "
        "c.tier, c.composite_score, c.guidance_accuracy_score, c.n_promises_resolved, "
        "c.forward_direction, c.as_of_period "
        "FROM stock_signals s "
        "JOIN ( SELECT cs.symbol, cs.tier, cs.composite_score, cs.guidance_accuracy_score, "
        "              cs.n_promises_resolved, cs.forward_direction, cs.veto_active, cs.as_of_period "
        "       FROM concall_scores cs "
        "       JOIN (SELECT symbol, MAX(last_updated) AS m FROM concall_scores GROUP BY symbol) x "
        "         ON x.symbol = cs.symbol AND x.m = cs.last_updated ) c ON c.symbol = s.symbol "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "WHERE s.trade_date = (SELECT MAX(trade_date) FROM stock_signals) "
        "  AND s.symbol IN (SELECT symbol FROM nse_equity_list) "
        "  AND s.accum_character = 'ACCUMULATION' AND s.p_score > 0 "
        "  AND COALESCE(c.veto_active, 0) = 0 "
        "  AND COALESCE(c.n_promises_resolved, 0) >= 3 "
        "  AND c.composite_score IS NOT NULL "
        "ORDER BY s.p_score DESC, COALESCE(c.n_promises_resolved, 0) DESC, s.symbol "
        "LIMIT 60"
    )
    return sql, []


# ── the GENERAL multi-condition confluence PLANNER (N pillars + scope) ─────────
# The generalization of build_confluence_query: instead of the fixed credibility ×
# accumulation pair, intersect ANY combination of the strategy pillars over the
# precomputed tables — "credible + accumulating + RS-leading small-caps". Every
# pillar maps to a precomputed condition; the pillar KEYS come ONLY from PLAN_PILLARS
# (a closed set, never user input), and sector/cap-band are bound — so the dynamic
# WHERE can never reference an invented column or value. DESCRIPTIVE evidence only
# (independent lenses agreeing = highest-evidence read, NOT a buy call); the reads
# sit at different grains (daily delivery/RS × quarterly credibility × period CPR),
# disclosed by the as-of badges in the renderer.
PLAN_PILLARS: dict[str, str] = {
    "credibility":  "credible management — concall track-record (veto-free · ≥3 resolved promises · real composite)",
    "accumulation": "strong-hand accumulation — delivery character ACCUMULATION + active p_score",
    "distribution": "strong-hand distribution — delivery character DISTRIBUTION (exiting)",
    "rs":           "RS leadership — rs_rank ≥ 80 vs the broad market",
    "value":        "reasonable valuation — P/E < 25",
    "quality":      "high quality — ROCE > 18%",
    "structure":    "bullish CPR structure — a daily bull-U reversal",
}
# cap-band -> (label, the membership index that defines it). 'large' is special
# (Nifty 50 ∪ Next 50 — there is no single 'Nifty 100' membership snapshot). Names
# verified against stock_index_membership; market_cap_cr is too sparse to use.
PLAN_CAPBAND: dict[str, tuple] = {
    "small": ("Small-cap", "Nifty Smallcap 250"),
    "mid":   ("Mid-cap",   "Nifty Midcap 150"),
    "large": ("Large-cap", None),
}
PLAN_LIMIT = 80

# the per-pillar WHERE fragment (NO user input — keys validated against PLAN_PILLARS).
_PLAN_WHERE = {
    "credibility":  "COALESCE(c.veto_active,0)=0 AND c.composite_score IS NOT NULL "
                    "AND COALESCE(c.n_promises_resolved,0)>=3",
    "accumulation": "s.accum_character='ACCUMULATION' AND s.p_score>0",
    "distribution": "s.accum_character='DISTRIBUTION'",
    "rs":           "s.rs_rank>=80",
    "value":        "f.pe IS NOT NULL AND f.pe<25",
    "quality":      "f.roce IS NOT NULL AND f.roce>18",
    "structure":    "st.pattern='BULL_U'",
}


def build_confluence_plan_query(pillars, sector: str = "", capband: str = "") -> tuple[str, list]:
    """Intersect the requested strategy pillars over the precomputed tables.

    ``pillars`` is filtered against PLAN_PILLARS (closed set) — anything off-menu is
    dropped, so a hallucinated pillar can never reach SQL. Every name's full evidence
    (credibility / accumulation / RS / CPR / value / quality) is SELECTed via LEFT
    JOINs and shown; the requested pillars add the WHERE filters. ``sector`` and
    ``capband`` narrow the universe (bound / membership-subquery). Read-only.
    """
    pset = [p for p in (pillars or []) if p in _PLAN_WHERE]
    where = [
        "s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
        "s.symbol IN (SELECT symbol FROM nse_equity_list)",
    ]
    params: list = []
    for p in pset:
        where.append("(" + _PLAN_WHERE[p] + ")")
    if sector:
        where.append("s.primary_sector = ?")
        params.append(sector)
    if capband == "large":
        where.append("s.symbol IN (SELECT symbol FROM stock_index_membership "
                     "WHERE index_name IN ('Nifty 50','Nifty Next 50'))")
    elif capband in ("small", "mid"):
        where.append("s.symbol IN (SELECT symbol FROM stock_index_membership WHERE index_name=?)")
        params.append(PLAN_CAPBAND[capband][1])
    sql = (
        "SELECT s.symbol, pe.close AS cmp, s.accum_character, s.p_score, s.r_score, "
        "s.trigger_rank, s.rs_rank, s.primary_sector, s.delivery_value_today, "
        "c.tier, c.composite_score, c.n_promises_resolved, c.forward_direction, c.as_of_period, "
        "st.pattern AS cpr_pat, st.compression_pctile, f.pe, f.roce, f.market_cap_cr "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "LEFT JOIN ( SELECT cs.symbol, cs.tier, cs.composite_score, cs.n_promises_resolved, "
        "                   cs.forward_direction, cs.veto_active, cs.as_of_period "
        "            FROM concall_scores cs "
        "            JOIN (SELECT symbol, MAX(last_updated) AS m FROM concall_scores GROUP BY symbol) x "
        "              ON x.symbol = cs.symbol AND x.m = cs.last_updated ) c ON c.symbol = s.symbol "
        "LEFT JOIN ( SELECT cp.symbol, cp.pattern, cp.compression_pctile "
        "            FROM cpr_signals cp "
        "            JOIN (SELECT symbol, MAX(period_end_date) AS d FROM cpr_signals "
        "                  WHERE timeframe='D' GROUP BY symbol) y "
        "              ON y.symbol = cp.symbol AND y.d = cp.period_end_date AND cp.timeframe='D' ) st "
        "         ON st.symbol = s.symbol "
        "LEFT JOIN fundamentals f ON f.symbol = s.symbol "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY (s.rs_rank IS NULL), s.rs_rank DESC, s.p_score DESC, "
        "         COALESCE(c.n_promises_resolved, 0) DESC, s.symbol "
        "LIMIT " + str(PLAN_LIMIT)
    )
    return sql, params


def build_credibility_detail_query(symbol: str) -> tuple[str, list]:
    """The full credibility EVIDENCE row for one symbol (the 'why is X credible' drill):
    every measurable that feeds the composite + the veto/deterioration flags + the as-of
    period (provenance). Latest score for the symbol. Bound on symbol."""
    sql = (
        "SELECT s.symbol, s.composite_score, s.credibility_score, s.guidance_accuracy_score, "
        "s.transparency_score, s.quantification_rate, s.forward_direction, s.forward_conviction, "
        "s.credibility_trend, s.tier, s.rank, s.n_concalls, s.n_promises_resolved, "
        "s.veto_active, s.veto_reason, s.deterioration_score, s.mispricing_flag, "
        "s.peer_median, s.as_of_period, s.as_of_date "
        "FROM concall_scores s "
        "JOIN (SELECT symbol, MAX(last_updated) AS m FROM concall_scores GROUP BY symbol) x "
        "  ON x.symbol = s.symbol AND x.m = s.last_updated "
        "WHERE s.symbol = ? "
        "LIMIT 1"
    )
    return sql, [symbol]


def build_credibility_evidence_query(symbol: str, limit: int = 6) -> tuple[str, list]:
    """The UNDERLYING promise-vs-delivery rows behind a credibility read (the F3-4 drill):
    the specific guidance the management gave and how it actually landed (BEAT / IN_LINE /
    MISS / OVERSTATED / CONCEALED), newest first, from concall_expectations_vs_actual
    (14,942 rows). Descriptive evidence — the *receipts* under the score. Bound on symbol;
    LIMIT clamped + bound."""
    limit = max(1, min(int(limit or 6), 20))
    sql = (
        "SELECT period_label, metric, mgmt_expectation, expected_value, actual_value, "
        "classification, evidence "
        "FROM concall_expectations_vs_actual "
        "WHERE symbol = ? AND classification IS NOT NULL "
        "ORDER BY id DESC "
        "LIMIT ?"
    )
    return sql, [symbol, limit]


def build_credibility_trend_query(symbol: str, limit: int = 24) -> tuple[str, list]:
    """The PIT credibility TIME-SERIES for one symbol (the 'credibility trend for X' ask):
    level + guidance-accuracy + momentum + trend-state + tape, period by period, newest
    first, off the precomputed ``credibility_series`` table (18,944 rows). Descriptive —
    a credibility SERIES, never a buy signal. Bound on symbol; LIMIT bound and clamped."""
    limit = max(2, min(int(limit or 24), 60))
    sql = (
        "SELECT symbol, period_label, period_year, period_month, level, ga, qr, "
        "n_resolved, deter, momentum, momentum_3p, trend, tape, tape_note, tier "
        "FROM credibility_series "
        "WHERE symbol = ? "
        "ORDER BY period_year DESC, period_month DESC "
        "LIMIT ?"
    )
    return sql, [symbol, limit]


def _like_escape(s: str) -> str:
    """Escape the LIKE metacharacters so a token containing % or _ is matched
    LITERALLY (CL-PAT-08). Pairs with an `ESCAPE '\\'` clause on the LIKE."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_symbol_resolve_query(token: str) -> tuple[str, list]:
    """Resolve a free-text token to candidate NSE symbols (exact > prefix > name).
    All values bound; LIKE wildcards are added here, the token is never formatted in.
    CL-PAT-08: the user token is LIKE-escaped (+ ESCAPE clause) so a '%'/'_' in it
    matches literally instead of turning the prefix/name probe into a match-all."""
    t = (token or "").strip().upper()
    pref = _like_escape(t) + "%"
    namelike = "%" + _like_escape((token or "").strip()) + "%"
    sql = (
        "SELECT symbol, company_name, "
        "CASE WHEN symbol = ? THEN 0 WHEN symbol LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END AS r "
        "FROM nse_equity_list "
        "WHERE symbol = ? OR symbol LIKE ? ESCAPE '\\' OR company_name LIKE ? ESCAPE '\\' "
        "ORDER BY r, length(symbol), symbol "
        "LIMIT 8"
    )
    return sql, [t, pref, t, pref, namelike]


def build_stock_card_query(symbol: str) -> tuple[str, list]:
    """One row: the symbol's latest signals + its cached fundamentals (LEFT JOIN, so a
    name with no fundamentals snapshot still renders its signals). Bound on symbol."""
    sql = (
        "SELECT s.symbol, pe.close AS cmp, s.rs_rank, s.accum_character, s.trigger_rank, "
        "s.p_score, s.r_score, s.pct_from_52w_high, s.rs_vs_broad_trend_state, "
        "s.rs_vs_sector_trend_state, s.primary_sector, s.price_vs_hot_avg_pct, "
        "s.delivery_value_today, "
        "f.pe, f.roce, f.roe, f.debt_to_equity, f.promoter_holding, f.promoter_pledge, "
        "f.market_cap_cr, f.dividend_yield, f.profit_growth_5y "
        "FROM stock_signals s "
        "LEFT JOIN prices_eq pe ON pe.symbol = s.symbol AND pe.trade_date = s.trade_date "
        "LEFT JOIN fundamentals f ON f.symbol = s.symbol "
        "WHERE s.symbol = ? AND s.trade_date = (SELECT MAX(trade_date) FROM stock_signals)"
    )
    return sql, [symbol]


def build_stock_pattern_query(symbol: str) -> tuple[str, list]:
    """The symbol's latest pt14 row (tier + disqualifier reason), or no row."""
    sql = (
        "SELECT tier, ns_base, qg_pass, hard_disqualified, disqualifier_reasons "
        "FROM pattern_scores WHERE symbol = ? ORDER BY id DESC LIMIT 1"
    )
    return sql, [symbol]
