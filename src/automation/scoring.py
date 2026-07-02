"""Rule-based patearn 14-pattern scorer (no LLM).

Reads fundamentals from the `fundamentals` table (populated by screener.py),
applies the explicit Yes/Partial/No criteria from resources/patearn/patterns.md,
and returns a structured score.

Patterns that need data we don't reliably have from Screener.in (sector tailwinds,
export mix, concall narrative) are marked Estimated and contribute at 70% weight
per the methodology, OR are scored conservatively as Partial.

This file is the operational implementation of patearn Phase 3. Phase 4 (the
qualitative deep dive) still happens in claude.ai with the patearn skill — this
code only handles the quantitative scoring.
"""

import json
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.scoring")

# Pattern weights from patterns.md
WEIGHTS = {
    1: 9,  # ROCE
    2: 9,  # Operating Leverage
    3: 8,  # Structural Sectoral Tailwind
    4: 8,  # Valuation
    5: 8,  # Balance Sheet Quality
    6: 7,  # Promoter Conviction
    7: 7,  # Export / Mix Inflection
    8: 6,  # Institutional Neglect
    9: 6,  # Earnings Momentum
    10: 6, # Margin Expansion
    11: 5, # VCP / Technical (price action)
    12: 7, # Receivables Discipline
    13: 6, # Working Capital
    14: 5, # Volume Confirmation
}

# MAX_CWS = sum(W * 6) for each pattern (3 signals * 2 pts each) = sum of W * 6
MAX_CWS = sum(w * 6 for w in WEIGHTS.values())  # = 582

# Top 5 patterns for Quality Gate (per SKILL.md):
QG_PATTERNS = [1, 2, 3, 4, 5]
QG_MAX = sum(WEIGHTS[p] * 6 for p in QG_PATTERNS)  # 252 (weights 9+9+8+8+8=42 ×6) — AUD-15 canonical
QG_THRESHOLD = 0.60 * QG_MAX  # 151.2

UNVERIFIED_MULTIPLIER = 0.70


# --- Hard Disqualifiers ----------------------------------------------------

def check_hard_disqualifiers(f: dict) -> tuple[bool, list[str]]:
    """Return (disqualified, list_of_reasons). Per SKILL.md, 5 conditions.

    Some are not checkable without quarterly time series (CFO trend, auditor)
    so we conservatively check what's available and surface the rest as
    'manual_check_required' rather than auto-disqualifying.
    """
    reasons = []
    pledge = f.get("promoter_pledge")
    if pledge is not None and pledge > 20:
        reasons.append(f"Promoter pledge {pledge:.1f}% > 20%")

    de = f.get("debt_to_equity")
    if de is not None and de > 2:
        reasons.append(f"Debt/Equity {de:.2f} > 2.0x")

    # CFO 2-year negative — needs time series. Flag as manual.
    # Auditor resignation — needs filings. Flag as manual.
    # Related party — needs annual report parsing. Flag as manual.

    return (len(reasons) > 0, reasons)


# --- Per-pattern scoring ---------------------------------------------------

def _score(value: Optional[float], yes_threshold: float, partial_threshold: float,
           reverse: bool = False) -> int:
    """Map a metric to 0/1/2.

    If reverse=False: higher is better. value >= yes_threshold → 2, >= partial → 1, else 0.
    If reverse=True: lower is better. value <= yes_threshold → 2, <= partial → 1, else 0.
    Returns -1 if value is None (signal "missing data").
    """
    if value is None:
        return -1
    if reverse:
        if value <= yes_threshold:
            return 2
        if value <= partial_threshold:
            return 1
        return 0
    if value >= yes_threshold:
        return 2
    if value >= partial_threshold:
        return 1
    return 0


def _pattern_block(pattern_id: int, signals: list[tuple[int, bool]],
                   note: str = "") -> dict:
    """Aggregate signals into a pattern-level dict.

    signals: list of (score_0_1_2, verified_bool); -1 score is treated as Partial+unverified
    """
    weight = WEIGHTS[pattern_id]
    contributions = []
    raw_sum = 0
    for raw, verified in signals:
        if raw == -1:
            # Missing data → treat as Partial estimated (conservative)
            raw = 1
            verified = False
        mult = 1.0 if verified else UNVERIFIED_MULTIPLIER
        contrib = raw * mult * weight
        contributions.append({"raw": raw, "verified": verified, "contrib": contrib})
        raw_sum += contrib
    return {
        "pattern": pattern_id,
        "weight": weight,
        "score": raw_sum,
        "max": weight * 6,
        "signals": contributions,
        "pac": any(c["raw"] >= 1 for c in contributions),
        "note": note,
    }


def score_fundamentals(f: dict) -> dict:
    """Apply rule-based 14-pattern scoring to a fundamentals dict.

    Returns a structured score with sensitivity band, PAC, QG, tier, and
    per-pattern detail.
    """
    if not f:
        return {"error": "no fundamentals"}

    patterns = {}

    # --- Pattern 1: ROCE Trajectory (W9) ---
    roce = f.get("roce")
    roce_rising = f.get("roce_rising_3y")      # real 3Y trend (present only when scored point-in-time)
    roce_3yavg = f.get("roce_3y_avg")
    r2 = (2 if roce_rising else 0, True) if roce_rising is not None else (_score(roce, 18, 14), False)
    r3 = (_score(roce_3yavg, 18, 14), True) if roce_3yavg is not None else (_score(roce, 22, 16), False)
    patterns[1] = _pattern_block(1, [
        (_score(roce, 18, 14), True),       # r1: current ROCE > 18%
        r2,                                 # r2: ROCE rising over 3Y (real) / current-level proxy
        r3,                                 # r3: sustained 3Y-avg ROCE (real) / absolute-level proxy
    ], note="r2/r3 use real 3Y ROCE trend + 3Y-avg when point-in-time; else estimated from current level")

    # --- Pattern 2: Operating Leverage (W9) ---
    profit_g = f.get("profit_growth_5y")
    sales_g = f.get("sales_growth_5y")
    # CL-SCO-13: drop the dead inner ternary (the `if` already guards sales_g!=0)
    # and require POSITIVE sales growth — operating leverage is meaningless (and
    # spuriously "good", since neg/neg → positive ratio) when the top line is
    # shrinking. A non-growing top line gets no leverage credit.
    if profit_g is not None and sales_g is not None and sales_g > 0:
        ratio = profit_g / sales_g
    else:
        ratio = None
    o1 = _score(ratio, 2.0, 1.5) if ratio is not None else -1
    opm = f.get("opm_latest")
    o2 = _score(opm, 25, 15) if opm is not None else -1
    opm_trend = f.get("opm_trend_3y")           # real 3Y OPM trend when point-in-time
    o3 = (_score(opm_trend, 2.0, 0.0), True) if opm_trend is not None else (o2, False)
    patterns[2] = _pattern_block(2, [
        (o1, ratio is not None),            # CL-SCO-13: confidence = leverage computable
        (o2, opm is not None),
        o3,                                 # o3: real 3Y OPM expansion / OPM-level proxy
    ], note="o3 uses real 3Y OPM trend when point-in-time; else OPM-level proxy")

    # --- Pattern 3: Structural Sectoral Tailwind (W8) ---
    # Cannot determine sector tailwind from numerics alone. Default Partial estimated.
    patterns[3] = _pattern_block(3, [
        (1, False), (1, False), (1, False)
    ], note="cannot determine from Screener data; requires sector judgment in Phase 4")

    # --- Pattern 4: Valuation (W8) ---
    pe = f.get("pe")
    pb = f.get("pb")
    # Yes if PE < 15, Partial if 15-25, No if > 25
    # CL-SCO-02: use `is not None` (rest of file does) — `if pe` discarded a real
    # negative PE (loss-making) and treated PE/PB == 0.0 as missing.
    # AUD-09: a non-positive PE (loss-maker) or PB (negative book) is NOT cheapness —
    # score it a hard 0, verified (it is known, not missing), so it earns no valuation
    # credit inside the Quality Gate. CL-SCO-02 kept negative PE but never handled the sign.
    v1 = (0 if pe <= 0 else _score(pe, 15, 25, reverse=True)) if pe is not None else -1
    v2 = (0 if pb <= 0 else _score(pb, 2.0, 4.0, reverse=True)) if pb is not None else -1
    v3 = v1  # EV/EBITDA proxy with PE
    patterns[4] = _pattern_block(4, [
        (v1, pe is not None),
        (v2, pb is not None),
        (v3, False),
    ], note="v3 estimated from PE; EV/EBITDA not available")

    # --- Pattern 5: Balance Sheet Quality (W8) ---
    de = f.get("debt_to_equity")
    # Lower D/E is better
    b1 = _score(de, 0.5, 1.5, reverse=True) if de is not None else -1
    icov = f.get("interest_coverage")           # real EBIT/interest when point-in-time
    b2 = (_score(icov, 4.0, 2.0), True) if icov is not None else (b1, False)
    # CFO positive — not in the Screener archive; conservative Partial
    patterns[5] = _pattern_block(5, [
        (b1, de is not None),
        b2,                                 # b2: real interest coverage / D/E proxy
        (1, False),
    ], note="b2 uses real interest coverage when point-in-time; b3 (CFO trend) not in archive → Partial")

    # --- Pattern 6: Promoter Conviction (W7) ---
    ph = f.get("promoter_holding")
    pledge = f.get("promoter_pledge")
    p1 = _score(ph, 50, 35) if ph is not None else -1
    p2 = _score(pledge, 0, 5, reverse=True) if pledge is not None else -1
    prom_rising = f.get("promoter_rising_4q")   # real promoter-holding-rising ~1y when point-in-time
    p3 = (2 if prom_rising else 0, True) if prom_rising is not None else (1, False)
    patterns[6] = _pattern_block(6, [
        (p1, ph is not None),
        (p2, pledge is not None),
        p3,                                 # p3: real promoter accumulation / estimated proxy
    ], note="p1/p3 real when shareholding feed present; pledge (p2) still needs BSE → estimated")

    # --- Pattern 7: Export / Mix Inflection (W7) ---
    # Not available from Screener top ratios — needs management commentary
    patterns[7] = _pattern_block(7, [
        (1, False), (1, False), (1, False)
    ], note="requires concall / segment data; Phase 4 manual check")

    # --- Pattern 8: Institutional Neglect (W6) ---
    fii = f.get("fii_holding")
    # Lower FII is better (less crowded)
    i1 = _score(fii, 5, 15, reverse=True) if fii is not None else -1
    patterns[8] = _pattern_block(8, [
        (i1, fii is not None),
        (1, False),  # analyst coverage — not in Screener
        (1, False),  # institutional ownership trend
    ], note="analyst coverage + ownership trend require external sources")

    # --- Pattern 9: Earnings Momentum (W6) ---
    pg_ttm = f.get("profit_growth_ttm")
    pg_3y = f.get("profit_growth_3y")
    e1 = _score(pg_ttm, 25, 15) if pg_ttm is not None else -1
    e2 = _score(pg_3y, 20, 12) if pg_3y is not None else -1
    accel = f.get("profit_accel_ttm")           # real quarterly YoY acceleration when point-in-time
    e3 = (_score(accel, 10.0, 0.0), True) if accel is not None else (e1, False)
    patterns[9] = _pattern_block(9, [
        (e1, pg_ttm is not None),
        (e2, pg_3y is not None),
        e3,                                 # e3: real quarterly acceleration / TTM-growth proxy
    ], note="e3 uses real quarterly profit acceleration when point-in-time; else TTM-growth proxy")

    # --- Pattern 10: Margin Expansion (W6) ---
    m2 = (_score(opm_trend, 2.0, 0.0), True) if opm_trend is not None else (1, False)
    patterns[10] = _pattern_block(10, [
        (o2, opm is not None),  # OPM level (reused from pattern 2)
        m2,                                 # m2: real 3Y OPM expansion when point-in-time
        (1, False),
    ], note="m2 uses real 3Y OPM trend when point-in-time; else OPM-level proxy")

    # --- Pattern 11: VCP / Technical (W5) ---
    # Requires price action analysis; default Partial-estimated
    patterns[11] = _pattern_block(11, [
        (1, False), (1, False), (1, False)
    ], note="technical pattern recognition not yet implemented; needs bhav copy + ATR")

    # --- Pattern 12: Receivables Discipline (W7) ---
    dd = f.get("debtor_days")                    # real debtor days when point-in-time
    c1 = (_score(dd, 45.0, 90.0, reverse=True), True) if dd is not None else (1, False)
    patterns[12] = _pattern_block(12, [
        c1, (1, False), (1, False)
    ], note="c1 uses real debtor days when point-in-time; receivables trend still estimated")

    # --- Pattern 13: Working Capital (W6) ---
    ccc = f.get("cash_conversion_cycle")
    wcd = f.get("working_capital_days")
    w1 = (_score(ccc, 30.0, 90.0, reverse=True), True) if ccc is not None else (1, False)
    w2 = (_score(wcd, 60.0, 120.0, reverse=True), True) if wcd is not None else (1, False)
    patterns[13] = _pattern_block(13, [
        w1, w2, (1, False)
    ], note="w1/w2 use real cash-conversion-cycle + working-capital-days when point-in-time; else estimated")

    # --- Pattern 14: Volume Confirmation (W5) ---
    patterns[14] = _pattern_block(14, [
        (1, False), (1, False), (1, False)
    ], note="volume breakouts require bhav copy + technical scan")

    # --- Aggregate ---
    pws = sum(p["score"] for p in patterns.values())
    ns_base = pws / MAX_CWS * 100
    pac = sum(1 for p in patterns.values() if p["pac"])

    # Sensitivity band — recompute by shifting raw signal values
    ns_pessimistic = _sensitivity(patterns, "pessimistic")
    ns_optimistic = _sensitivity(patterns, "optimistic")

    # Quality Gate
    qg_score = sum(patterns[p]["score"] for p in QG_PATTERNS)
    qg_pass = qg_score >= QG_THRESHOLD

    # Hard Disqualifiers
    disqualified, disq_reasons = check_hard_disqualifiers(f)

    tier = _classify_tier(ns_base, qg_pass, disqualified)

    return {
        "symbol": f.get("symbol"),
        "pws": pws,
        "ns_base": ns_base,
        "ns_pessimistic": ns_pessimistic,
        "ns_optimistic": ns_optimistic,
        "max_cws": MAX_CWS,
        "pac": pac,
        "pac_max": 14,
        "qg_score": qg_score,
        "qg_max": QG_MAX,
        "qg_threshold": QG_THRESHOLD,
        "qg_pass": qg_pass,
        "hard_disqualified": disqualified,
        "disqualifier_reasons": disq_reasons,
        "tier": tier,
        "patterns": patterns,
    }


def _sensitivity(patterns: dict, direction: str) -> float:
    """Recompute NS under pessimistic (Yes→Partial) or optimistic (Partial→Yes)."""
    total = 0.0
    for p in patterns.values():
        for sig in p["signals"]:
            raw = sig["raw"]
            if direction == "pessimistic" and raw == 2:
                raw = 1
            elif direction == "optimistic" and raw == 1:
                raw = 2
            mult = 1.0 if sig["verified"] else UNVERIFIED_MULTIPLIER
            total += raw * mult * p["weight"]
    return total / MAX_CWS * 100


def _classify_tier(ns: float, qg_pass: bool, disqualified: bool) -> str:
    if disqualified:
        return "DISQUALIFIED"
    if ns >= 72 and qg_pass:
        return "T1"
    if ns >= 55:
        return "T2"
    if ns >= 40:
        return "T3"
    return "T4"


# --- Persistence -----------------------------------------------------------

def save_score(score: dict) -> int:
    """Persist a score to pattern_scores. Returns the inserted row id."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pattern_scores
               (symbol, pws, ns_base, ns_pessimistic, ns_optimistic, pac, tier,
                qg_pass, hard_disqualified, disqualifier_reasons, detail_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                score["symbol"], score["pws"], score["ns_base"],
                score["ns_pessimistic"], score["ns_optimistic"],
                score["pac"], score["tier"],
                1 if score["qg_pass"] else 0,
                1 if score["hard_disqualified"] else 0,
                json.dumps(score["disqualifier_reasons"]),
                json.dumps(score["patterns"]),
            ),
        )
        return int(cur.lastrowid)


# --- Convenience entry points ---------------------------------------------

def score_symbol(symbol: str, *, force_refresh: bool = False) -> dict:
    """Fetch fundamentals (cache or fresh) then score. Returns full score dict."""
    from src.automation import screener
    f = screener.fetch_company(symbol, use_cache=not force_refresh)
    if not f:
        return {"error": f"could not fetch fundamentals for {symbol}", "symbol": symbol}
    score = score_fundamentals(f)
    save_score(score)
    return score


def format_score_for_telegram(score: dict, *, fundamentals: dict | None = None) -> str:
    """Render a structured Telegram-friendly summary of the rule-based score."""
    if "error" in score:
        return f"⚠️ {score['error']}"

    sym = score["symbol"]
    tier = score["tier"]
    ns_b = score["ns_base"]
    ns_p = score["ns_pessimistic"]
    ns_o = score["ns_optimistic"]
    pac = score["pac"]
    qg = "PASS" if score["qg_pass"] else "FAIL"

    tier_emoji = {"T1": "🟢", "T2": "🟡", "T3": "🟠", "T4": "⚪", "DISQUALIFIED": "🔴"}.get(tier, "")

    lines = [
        f"<b>{sym}</b>  {tier_emoji}<b>{tier}</b>",
        f"NS: <b>{ns_b:.1f}%</b>  (range {ns_p:.1f}–{ns_o:.1f})",
        f"PAC: {pac}/14   Quality Gate: <b>{qg}</b>",
    ]
    if score["hard_disqualified"]:
        lines.append("🔴 <b>Hard disqualified:</b>")
        for r in score["disqualifier_reasons"]:
            lines.append(f"  • {r}")

    if fundamentals:
        lines.append("")
        lines.append("<b>Key metrics</b>")
        if fundamentals.get("roce") is not None:
            lines.append(f"  ROCE: {fundamentals['roce']:.1f}%")
        if fundamentals.get("roe") is not None:
            lines.append(f"  ROE: {fundamentals['roe']:.1f}%")
        if fundamentals.get("pe") is not None:
            lines.append(f"  PE: {fundamentals['pe']:.1f}")
        if fundamentals.get("debt_to_equity") is not None:
            lines.append(f"  D/E: {fundamentals['debt_to_equity']:.2f}")
        if fundamentals.get("promoter_holding") is not None:
            lines.append(f"  Promoter: {fundamentals['promoter_holding']:.1f}%")
        if fundamentals.get("promoter_pledge") is not None:
            lines.append(f"  Pledge: {fundamentals['promoter_pledge']:.1f}%")
        if fundamentals.get("profit_growth_5y") is not None:
            lines.append(f"  5Y profit growth: {fundamentals['profit_growth_5y']:.1f}%")
        if fundamentals.get("sales_growth_5y") is not None:
            lines.append(f"  5Y sales growth: {fundamentals['sales_growth_5y']:.1f}%")

    lines.append("")
    lines.append("<i>For Phase 4 deep dive: paste this into claude.ai with patearn skill loaded. "
                 "Tier and PWS here are <b>rule-based on quantitative data only</b>; qualitative "
                 "patterns (3, 7, 11, 12, 13, 14) default to Partial-estimated and need claude.ai judgment.</i>")
    return "\n".join(lines)
