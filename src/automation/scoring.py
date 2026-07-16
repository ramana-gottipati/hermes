"""Rule-based patearn 14-pattern scorer (no LLM).

Reads fundamentals from the PRIMARY-SOURCE archive via `fundamentals_asof`
(research.db.fundamentals_history — NSE-XBRL where migrated, labeled Screener-era
legacy for pre-~2022 / gate-held rows — plus shareholding_history, and the bhav copy
for price), applies the explicit Yes/Partial/No criteria from
resources/patearn/patterns.md, and returns a structured score.
S148/3.4: this REPLACED the live screener.py scrape — the scoring path makes no
network call and no Screener request (Guardrail #8). See score_symbol().

Patterns that need data no filing carries (sector tailwinds, export mix, concall
narrative) are marked Estimated and contribute at 70% weight per the methodology,
OR are scored conservatively as Partial.

This file is the operational implementation of patearn Phase 3. Phase 4 (the
qualitative deep dive) still happens in claude.ai with the patearn skill — this
code only handles the quantitative scoring.
"""

import json
import logging
import re
from datetime import date
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.scoring")

# ── Pattern weights ─────────────────────────────────────────────────────
# Quality-Gate patterns 1-5 mirror resources/patearn/patterns.md EXACTLY (the
# load-bearing screen). Patterns 6-14 are a DELIBERATE reorganization to what
# is computable from fundamentals (see the module docstring): the code
# numbering / labels / weights here do NOT line up 1:1 with patterns.md's
# canonical 6-14. Authoritative code<->methodology map:
#   resources/patearn/patterns.md § "Implementation mapping (scoring.py)".
# ⚠ These weights drive the NS score — re-aligning them to patterns.md's
#   nominal numbers is a SCORING-BEHAVIOUR change, not a doc fix (needs sign-off; D114).
WEIGHTS = {
    1: 9,  # ROCE / ROE Trajectory        = methodology #1
    2: 9,  # Operating Leverage           = methodology #2
    3: 8,  # Structural Sectoral Tailwind = methodology #3
    4: 8,  # Valuation                    = methodology #4
    5: 8,  # Balance Sheet Quality        = methodology #5
    6: 7,  # Promoter Conviction          = methodology #8 (Promoter/Insider Accumulation)
    7: 7,  # Export / Mix Inflection      = methodology #6 + #9 (Mix Premiumisation + Export)
    8: 6,  # Institutional Neglect        = methodology #10
    9: 6,  # Earnings Momentum            = computable adjunct (no distinct methodology pattern)
    10: 6, # Margin Expansion             = margin facet of methodology #2 / #6
    11: 5, # VCP / Technical (price)      = methodology #11 (W6 in methodology)
    12: 7, # Receivables Discipline       = methodology #12 · receivables (w2)
    13: 6, # Working Capital              = methodology #12 · cash-conversion cycle (w1)
    14: 5, # Volume Confirmation          = volume facet of methodology #11 / #14
}

# MAX_CWS = sum(W * 6) for each pattern (3 signals * 2 pts each) = sum of W * 6
MAX_CWS = sum(w * 6 for w in WEIGHTS.values())  # = 582

# Top 5 patterns for Quality Gate (per SKILL.md):
QG_PATTERNS = [1, 2, 3, 4, 5]
QG_MAX = sum(WEIGHTS[p] * 6 for p in QG_PATTERNS)  # 252 (weights 9+9+8+8+8=42 ×6) — AUD-15 canonical
QG_THRESHOLD = 0.60 * QG_MAX  # 151.2

UNVERIFIED_MULTIPLIER = 0.70

# --- Financial-sector detector + label (Codex D3-F1, Track D) --------------
# pt14's generic ROCE / OPM / D-E thresholds are STRUCTURALLY WRONG for lenders
# (leverage IS the business; Screener reports ROCE ~1-7% for banks — nonsense),
# so every bank/NBFC/HFC is mis-rated bottom-tier (HDFCBANK/ICICIBANK → T4).
# Until the sector-adapted Doctrine-D model ships (GNPA/CAR/RoA from NSE XBRL —
# Track-D data plan), we LABEL the score for financials so no reader mistakes the
# generic tier for a real quality verdict. Detector = NSE financial-index
# membership (primary-source, guardrail-#8-clean; company_tags source='index').
_FINANCIAL_INDEX_TAGS = ("Financial Services", "Banks", "PSU Banks", "Private Banks")
_FIN_PENDING_NOTE = (
    "Financial-sector company — this rule-based pt14 uses generic ROCE / OPM / D-E "
    "thresholds that are structurally wrong for lenders (leverage IS the business). "
    "A sector-adapted Doctrine-D model (GNPA / CAR / RoA from NSE XBRL) is pending — "
    "treat the tier / NS below as NOT applicable for this name."
)

# --- Doctrine-D: the sector-adapted model for lenders (D134, Track D Step 4) ------
# Supersedes the D3-F1 interim LABEL above for names we can actually measure. Ramana's
# defaults, LOCKED 2026-07-15: sub-type-aware thresholds (bank RoA ~1% · NBFC 2-4% ·
# HFC RoE 12-15%) · ALM = CET1/CRAR + GNPA proxy (true maturity-gap ALM deferred) · the
# SUPPRESS half folds in HERE (the scorer decides), not at the surfaces.
#
# ⚠ MEASURED 2026-07-15 (primary source, `company_tags` source='index'): NSE exposes
# Banks / PSU Banks / Private Banks + the union 'Financial Services' — there is **NO
# housing/NBFC index tag**. So BANK is primary-source detectable, but NBFC-vs-HFC is not.
# The HFC leg is therefore a NARROW, LABELED name heuristic over our own security_master
# name (a CLASSIFICATION heuristic, not a data feed — guardrail #8 is untouched); anything
# unmatched falls back to NBFC thresholds, which is the conservative default for a lender.
_BANK_INDEX_TAGS = ("Banks", "PSU Banks", "Private Banks")
# Checked against the LIVE company_name values: "LIC Housing Finance" / "PNB Housing Finance"
# (housing) · "Can Fin Homes" (fin homes — note the reversed order the first draft missed) ·
# "Bajaj Finance" / "Muthoot Finance" / "Cholamandalam …Finance" must NOT match. Safe to key on a
# bare "housing" because this branch only runs for NSE financial-INDEX members, where housing ⇒ HFC
# (a real-estate developer is not in the financial index). Banks never reach here — the primary-source
# bank tag returns first.
_HFC_NAME_RE = re.compile(r"(housing|hsg\s*fin|home\s*fin|fin\s*homes?|\bhfc\b)", re.I)

# ⚠ UNITS ARE LOAD-BEARING. `roa_pct` is the **discrete-quarter** RoA the XBRL SA pass stores
# (HDFCBANK Q3FY25 = 0.47% — see extract_bank_prudential's context note), whereas Ramana's locked
# "bank RoA ~1%" is the ANNUAL figure (HDFCBANK ≈1.9%/yr, SBIN ≈1.0%/yr). So the quarterly value is
# annualised (×4) before it meets an annual threshold — comparing 0.47 against 1.0 raw would score
# every good bank a FAIL. `roe` comes from the ANNUAL "ROE %" archive and is already annual.
# Each leg therefore carries its OWN (yes, partial) — RoA and RoE are on different scales and one
# must never be judged by the other's bar.
_Q_TO_ANNUAL = 4.0

_FIN_SUBTYPES = {
    # legs: (key, display, yes, partial, annualise?) — leg[0] is the sub-type's headline ratio
    "bank": {"label": "Bank", "legs": (("roa_pct", "RoA", 1.0, 0.75, True),
                                       ("roe", "RoE", 15.0, 12.0, False))},
    "nbfc": {"label": "NBFC", "legs": (("roa_pct", "RoA", 3.0, 2.0, True),
                                       ("roe", "RoE", 15.0, 12.0, False))},
    "hfc":  {"label": "HFC",  "legs": (("roe", "RoE", 15.0, 12.0, False),
                                       ("roa_pct", "RoA", 2.0, 1.5, True))},
}

_DOCTRINE_D_NOTE = (
    "Sector-adapted thresholds (Doctrine D): this is a {label}, so profitability is read on "
    "{profit_name} (not ROCE), the top line is net interest income (not sales), balance-sheet "
    "quality is asset quality + capital (GNPA / Net NPA / CET1), and the generic Debt/Equity "
    "hard-disqualifier is disabled — leverage IS a lender's business. True maturity-gap ALM is "
    "deferred; CET1 + GNPA stand in as the balance-sheet-strength proxy."
)
_FIN_SUPPRESSED_NOTE = (
    "Financial-sector company with no Doctrine-D evidence yet (no RoA / RoE / GNPA / CET1 "
    "known as of this date) — the generic ROCE / OPM / D-E tier is structurally wrong for a "
    "lender, so NO quality tier is asserted for this name rather than a misleading one."
)


def financial_subtype(symbol: str, conn=None, *, company_name: Optional[str] = None) -> Optional[str]:
    """'bank' | 'hfc' | 'nbfc' | None — the Doctrine-D sub-type for a financial name.

    BANK is primary-source (NSE Banks/PSU/Private index tags, guardrail-#8-clean). HFC has NO
    primary-source discriminator (measured — NSE publishes no housing index tag here), so it is a
    narrow, labeled name heuristic; every other financial-index name is NBFC (the conservative
    default). Returns None for a non-financial. Fails closed on any error — detection must never
    break scoring.
    """
    if not symbol:
        return None

    def _tags(c) -> set:
        try:
            rows = c.execute("SELECT tag FROM company_tags WHERE symbol=? AND source='index' "
                             "AND approved=1", (symbol.upper(),)).fetchall()
            return {r[0] for r in rows}
        except Exception:  # noqa: BLE001 — never break scoring
            return set()

    def _name(c) -> str:
        # NB the column is `company_name` (verified against the live schema) — a wrong name here
        # would throw, be swallowed by the fail-closed except, and silently degrade EVERY HFC to
        # the NBFC default. The test fixture mirrors the real schema for exactly that reason.
        if company_name:
            return company_name
        try:
            row = c.execute("SELECT company_name FROM security_master WHERE symbol=? LIMIT 1",
                            (symbol.upper(),)).fetchone()
            return (row[0] or "") if row else ""
        except Exception:  # noqa: BLE001
            return ""

    def _resolve(c) -> Optional[str]:
        tags = _tags(c)
        if not tags & set(_FINANCIAL_INDEX_TAGS):
            return None                                   # not a financial at all
        if tags & set(_BANK_INDEX_TAGS):
            return "bank"                                 # primary-source
        blob = f"{symbol} {_name(c)}"
        return "hfc" if _HFC_NAME_RE.search(blob) else "nbfc"

    if conn is not None:
        return _resolve(conn)
    try:
        with get_conn() as c:
            return _resolve(c)
    except Exception:  # noqa: BLE001
        return None


def _lender_patterns(f: dict, sub: dict) -> dict:
    """Doctrine-D replacements for patterns 1 / 2 / 5 on a lender. Every leg is NULL-tolerant:
    an absent ratio scores -1, which `_pattern_block` renders as a conservative unverified
    Partial — never a false pass or a false fail. (RoA/CET1 are XBRL-only and start empty, so
    abstention is the COMMON case for months — it must be the safe one.)"""
    out = {}

    # --- Pattern 1: profitability on the sub-type's ratios (ROCE is meaningless for a lender) ---
    # Each leg is judged on its OWN bar, and a quarterly ratio is annualised first (see _Q_TO_ANNUAL).
    legs = []
    for key, _disp, yes, partial, annualise in sub["legs"]:
        v = f.get(key)
        if v is not None and annualise:
            v = v * _Q_TO_ANNUAL
        legs.append((_score(v, yes, partial), v is not None))
    legs.append((-1, False))      # multi-year lender-ratio trend not stored yet -> abstain
    head = sub["legs"][0]
    out[1] = _pattern_block(1, legs, note=(
        f"Doctrine D: {sub['label']} profitability on {head[1]} (yes ≥{head[2]}% / partial "
        f"≥{head[3]}%, annualised from the discrete quarter), cross-checked on "
        f"{sub['legs'][1][1]} on its own bar; multi-year trend not yet stored → abstains"))

    # --- Pattern 2: operating leverage on NET INTEREST INCOME (a lender's top line) ---
    nii_g = f.get("nii_growth_5y")
    profit_g = f.get("profit_growth_5y")
    lev = (profit_g / nii_g) if (profit_g is not None and nii_g is not None and nii_g > 0) else None
    cti = f.get("cost_to_income")
    out[2] = _pattern_block(2, [
        (_score(nii_g, 15.0, 10.0), nii_g is not None),
        (_score(cti, 45.0, 55.0, reverse=True), cti is not None),
        (_score(lev, 2.0, 1.5), lev is not None),
    ], note="Doctrine D: NII growth (Revenue−Interest) · cost-to-income (opex ÷ NII+other income; "
            "abstains until Provisions is stored, ~Jul-2026) · operating leverage = profit growth "
            "÷ NII growth")

    # --- Pattern 5: asset quality + capital (the CET1+GNPA proxy for balance-sheet strength) ---
    gnpa = f.get("gnpa_pct")
    cet1 = f.get("cet1_pct")
    nnpa = f.get("nnpa_pct")
    out[5] = _pattern_block(5, [
        (_score(gnpa, 1.5, 3.0, reverse=True), gnpa is not None),
        (_score(cet1, 13.0, 11.0), cet1 is not None),
        (_score(nnpa, 0.5, 1.0, reverse=True), nnpa is not None),
    ], note="Doctrine D: Gross NPA (yes ≤1.5%) · CET1 (yes ≥13%) · Net NPA (yes ≤0.5%). True "
            "maturity-gap ALM is deferred — CET1 + GNPA are the locked balance-sheet proxy")
    return out


# LENDER-SPECIFIC evidence only. RoE is deliberately EXCLUDED: every company has an RoE, so it
# proves nothing about lender-ness — it is a cross-check leg, never the trigger.
# ⚠ WHY THIS MATTERS (found by classifying the live 38-name financial universe): the NSE
# 'Financial Services' index also carries INSURERS (HDFCLIFE / ICICIGI / MFSL), an EXCHANGE (BSE)
# and holdcos (BAJAJFINSV). They are NOT lenders — no NII, no GNPA, no CET1 — so asserting an
# "NBFC, profitability read on RoA" verdict over them would repeat the exact D3-F1 category error
# in a new place. Requiring lender-specific evidence routes them to SUPPRESSED (no tier) instead,
# which is the honest answer for a name neither the generic nor the lender model fits.
_LENDER_EVIDENCE_KEYS = ("roa_pct", "gnpa_pct", "cet1_pct", "nnpa_pct", "nii_growth_5y")


def _has_doctrine_d_evidence(f: dict) -> bool:
    """Any measured LENDER evidence? Drives the SUPPRESS half (Ramana-locked): with none of it,
    a financial gets NO tier rather than the structurally-wrong generic one (D3-F1) — or a
    lender verdict it never earned (an insurer / exchange)."""
    return any(f.get(k) is not None for k in _LENDER_EVIDENCE_KEYS)


def is_financial_symbol(symbol: str, conn=None) -> bool:
    """True iff `symbol` is an NSE financial-sector index constituent (bank/NBFC/HFC).

    Primary-source detector via `company_tags` (source='index'): 'Financial Services'
    is the union tag that catches banks + NBFCs + HFCs. Guardrail-#8-clean (NSE index
    constituents, already stored — no Screener/vendor call). Fails closed (False) on
    any error so scoring never breaks. Coverage caveat: a lender OUTSIDE the NSE
    financial indices is not caught — acceptable for the interim label; the full
    Doctrine-D build detects lenders directly via the XBRL InterestEarned tag.
    """
    if not symbol:
        return False
    q = ("SELECT 1 FROM company_tags WHERE symbol=? AND source='index' AND approved=1 "
         "AND tag IN (%s) LIMIT 1" % ",".join("?" * len(_FINANCIAL_INDEX_TAGS)))
    args = (symbol.upper(), *_FINANCIAL_INDEX_TAGS)

    def _check(c) -> bool:
        try:
            return c.execute(q, args).fetchone() is not None
        except Exception:  # noqa: BLE001 — detection must never break scoring
            return False

    if conn is not None:
        return _check(conn)
    try:
        with get_conn() as c:
            return _check(c)
    except Exception:  # noqa: BLE001
        return False


# --- Hard Disqualifiers ----------------------------------------------------

def check_hard_disqualifiers(f: dict, *, is_financial: bool = False) -> tuple[bool, list[str]]:
    """Return (disqualified, list_of_reasons). Per SKILL.md, 5 conditions.

    Some are not checkable without quarterly time series (CFO trend, auditor)
    so we conservatively check what's available and surface the rest as
    'manual_check_required' rather than auto-disqualifying.

    `is_financial` (Doctrine D, D134): the generic Debt/Equity > 2.0x rule is DISABLED for
    lenders — a bank/NBFC/HFC funds its book with deposits/borrowings, so leverage IS the
    business and D/E > 2 is normal, not a red flag. It auto-disqualified every lender
    (the D3-F1 finding). Asset quality + capital carry that judgement instead (pattern 5:
    GNPA / Net NPA / CET1). The pledge rule still applies to everyone.
    """
    reasons = []
    pledge = f.get("promoter_pledge")
    if pledge is not None and pledge > 20:
        reasons.append(f"Promoter pledge {pledge:.1f}% > 20%")

    de = f.get("debt_to_equity")
    if de is not None and de > 2 and not is_financial:
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


def score_fundamentals(f: dict, *, is_financial: bool = False,
                       subtype: Optional[str] = None) -> dict:
    """Apply rule-based 14-pattern scoring to a fundamentals dict.

    Returns a structured score with sensitivity band, PAC, QG, tier, and
    per-pattern detail.

    `is_financial` + `subtype` (**Doctrine D**, D134 — supersedes the D3-F1 interim label):
    for a bank/NBFC/HFC the generic ROCE / OPM / D-E patterns are structurally wrong, so
    patterns 1 / 2 / 5 are REPLACED with sector-adapted ones (profitability on RoA/RoE vs
    sub-type thresholds · operating leverage on net interest income · asset quality + capital),
    and the generic D/E hard-disqualifier is disabled. `subtype` ∈ {'bank','nbfc','hfc'}
    (see `financial_subtype`); it defaults to 'nbfc' — the conservative lender default — when
    a name is financial but the sub-type is unknown.

    The **suppress half** (Ramana-locked) lives here, not at the surfaces: a lender with NO
    Doctrine-D evidence at all gets `sector_suppressed=True` and tier 'NA' rather than the
    structurally-wrong generic tier D3-F1 warned about. RoA/CET1 are XBRL-only and fill
    forward, so abstention is common and must stay the safe path.
    """
    if not f:
        return {"error": "no fundamentals"}

    sub_key = (subtype or "nbfc") if is_financial else None
    sub = _FIN_SUBTYPES.get(sub_key) if sub_key else None
    doctrine_d = bool(sub) and _has_doctrine_d_evidence(f)

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

    # --- Doctrine D (D134): sector-adapted patterns 1/2/5 REPLACE the generic ones for a
    # lender — BEFORE the aggregate, so NS / QG / PAC are all computed on the lender model.
    # The other patterns (3/4/6…14 — valuation, promoter conviction, institutional neglect,
    # momentum, volume) are sector-neutral and deliberately left as-is.
    if doctrine_d:
        patterns.update(_lender_patterns(f, sub))

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
    disqualified, disq_reasons = check_hard_disqualifiers(f, is_financial=is_financial)

    tier = _classify_tier(ns_base, qg_pass, disqualified)

    # The SUPPRESS half (Ramana-locked, D134): a lender we cannot measure at all gets NO tier
    # rather than the structurally-wrong generic one. Doctrine-D-scored lenders keep their tier.
    suppressed = bool(is_financial) and not doctrine_d
    if suppressed:
        tier = "NA"

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
        # --- Doctrine D (D134) — supersedes the D3-F1 interim label for measurable lenders ---
        "sector_model": ("doctrine-d" if doctrine_d else ("suppressed" if suppressed else None)),
        "sector_subtype": (sub["label"] if sub else None),
        # WHICH lender inputs actually backed this read. RoA/CET1 are XBRL-only and fill forward,
        # so today most banks qualify on NII growth alone and every other leg ABSTAINS — the tier
        # is then built mostly from conservative Partials and means "not yet known", NOT "poor".
        # Surfaces must show this so a thin T4 is never read as a quality verdict.
        "sector_evidence": ([k for k in _LENDER_EVIDENCE_KEYS if f.get(k) is not None]
                            if is_financial else []),
        "sector_evidence_max": (len(_LENDER_EVIDENCE_KEYS) if is_financial else 0),
        # kept for surfaces still reading the D3-F1 flag: pending == a financial we can't yet score
        "sector_model_pending": suppressed,
        "sector_suppressed": suppressed,
        "sector_note": (
            _DOCTRINE_D_NOTE.format(label=sub["label"], profit_name=sub["legs"][0][1])
            if doctrine_d else (_FIN_SUPPRESSED_NOTE if suppressed else None)
        ),
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

def _latest_close(symbol: str) -> Optional[float]:
    """Latest bhav-copy close — the price PE/PB need. Primary-source, local, no network."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT close FROM bhavcopy_rows WHERE symbol = ? "
                "ORDER BY trade_date DESC LIMIT 1", (symbol,)).fetchone()
        return row["close"] if row else None
    except Exception:  # noqa: BLE001 — price is optional (PE/PB simply stay None)
        return None


def score_symbol(symbol: str, *, force_refresh: bool = False) -> dict:
    """Score a symbol from the PRIMARY-SOURCE archive — no Screener, no network (Guardrail #8).

    Reads `research.db.fundamentals_history` (NSE-XBRL where migrated; labeled Screener-era
    legacy for pre-~2022 / gate-held rows) + `shareholding_history`, point-in-time via
    `fundamentals_asof`, with the PE/PB price from the bhav copy. This REPLACED the live
    `screener.fetch_company` scrape (S148/3.4): the archive supplies every key
    score_fundamentals reads, PLUS the time-series keys Screener never did (roce_3y_avg,
    roce_rising_3y, opm_trend_3y, interest_coverage, profit_accel_ttm, …) — measured worth
    ~+5.1 NS points of real signal the scorer used to fall back to estimates for. Coverage
    also goes ~107 -> ~2,000 symbols (the old scrape cache only ever held the surfaced few).

    `force_refresh` is retained for call-site compatibility and is now a NO-OP — there is no
    scrape cache to refresh; every call reads the archive as of today.
    """
    from src.automation import fundamentals_asof
    f = fundamentals_asof.as_of_fundamentals(
        symbol, date.today().isoformat(), price=_latest_close(symbol))
    if not f:
        return {"error": f"no fundamentals in the archive for {symbol}", "symbol": symbol}
    # Doctrine D (D134): resolve the sub-type too — without it every lender would fall back to
    # the NBFC bar (RoA 3%), so a BANK would be judged on an NBFC's threshold. (Merged with the
    # 3.4 archive fetch above: fundamentals now come from the primary-source archive, no Screener.)
    sub = financial_subtype(symbol)
    score = score_fundamentals(f, is_financial=sub is not None, subtype=sub)
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

    lines = []
    # Doctrine D (D134): lead with the sector disclosure whenever there is one — either the
    # "sector-adapted thresholds" note (we scored this lender on its own model) or the
    # SUPPRESSED note (⚠️ no tier asserted). Gating on `sector_model_pending` alone would have
    # hidden the Doctrine-D note entirely once a lender became scoreable.
    _note = score.get("sector_note")
    if _note:
        _mark = "⚠️ " if score.get("sector_suppressed") else "ℹ️ "
        lines.append(f"{_mark}<b>{_note}</b>")
        _ev = score.get("sector_evidence") or []
        _evmax = score.get("sector_evidence_max") or 0
        if _evmax and not score.get("sector_suppressed"):
            # a tier resting on 1-of-5 inputs means "not yet known", not "poor" — say so
            _thin = " — most lender inputs are not yet known, so this tier is provisional" \
                if len(_ev) <= 2 else ""
            lines.append(f"<i>Read on {len(_ev)}/{_evmax} lender inputs "
                         f"({', '.join(_ev) or 'none'}){_thin}.</i>")
        lines.append("")
    lines += [
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
