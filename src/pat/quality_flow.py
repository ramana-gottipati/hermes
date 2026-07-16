"""Pat 'quality' data-flow — a SYMBOL's own fundamentals + quality read (S155-c).

The gap this closes (measured, not assumed): after S154/S155 Pat could EXPLAIN the lender
metrics ("what is CET1" → the definition) but could not tell you **HDFCBANK's** CET1. Asking a
per-symbol fundamental returned the generic definition, nothing at all, or — worse — a
market-wide SCREEN ("HDFCBANK asset quality" ran the whole-universe fundamentals screen). The
Doctrine-D model shipped unreachable by a human question.

    "what's HDFCBANK's CET1"      -> 19.97% (its own value)
    "is HDFCBANK a good bank"     -> the Doctrine-D read, on its own numbers
    "what's TCS's ROCE / pt14 tier" -> TCS's actual figures
    "what are the risks in X"     -> the disqualifiers / asset-quality flags

CONTRACT (mirrors filings_flow.py / rotation_flow.py):
  * PURE logic here — `parse_quality()` (a ₹0 pre-pass in engine.route; needs a fundamentals cue
    AND a symbol) and `quality_for()` (a bounded read). Render = web.py:_quality_flow.
  * REUSES the existing chain — `fundamentals_asof.as_of_fundamentals` (point-in-time, over the
    research archive + NSE-XBRL) → `scoring.financial_subtype` → `scoring.score_fundamentals`.
    Guardrail-#8 clean: it never calls screener.fetch_company (the vendor path `score_symbol` uses).
  * SYMBOL-ANCHORED: fires only with a ticker, so "overvalued stocks" / "elite ROCE names" stay the
    market-wide screen and a bare "tell me about TCS" stays the snapshot card.
  * DESCRIPTIVE / SEBI-safe: a quality read is evidence, never a buy/sell call. It carries
    Doctrine-D's own honesty — an unmeasurable lender shows NO tier, a thinly-fed one is PROVISIONAL.
"""
from __future__ import annotations

import re
from datetime import date

# a fundamentals / quality cue must be present (a bare "tell me about X" is the card's job)
_QUAL_RE = re.compile(
    r"\b(gnpa|gross npa|net npa|nnpa|cet1|tier 1|tier-1|capital adequacy|crar|car\b|"
    r"asset quality|npa|provision|credit cost|nii|net interest income|cost[- ]to[- ]income|"
    r"roa\b|return on assets|roce|roe\b|return on equity|"
    r"pt14|quality score|quality tier|\btier\b|ns score|"
    r"fundamental|fundamentals|valuation|overvalued|undervalued|expensive|cheap|"
    r"\bpe\b|p/e|\bpb\b|p/b|book value|debt|leverage|debt to equity|d/e|balance sheet|"
    r"promoter holding|margin|opm|"
    r"good bank|good business|how safe|safe(?:ty)?|risks?|red flags?|disqualif|"
    r"how is .* (?:looking|doing|placed)|how good is)\b")

# these belong to OTHER flows even with a symbol — never steal them.
# `pledge` sits here rather than in the cue: a pledge is a SAST DISCLOSURE, so filings_flow owns it.
# Ordering alone (filings runs first) would cover it, but yielding in the recognizer keeps the
# contract true when parse_quality is called directly — defence in depth, not luck.
_NOT_US = re.compile(r"\b(news|headline|rotation|phase|weather|wolfe|setup|seasonal|usually|"
                     r"insider|sast|shareholding|holders?|credit rating|rating action|"
                     r"upgrade[ds]?|downgrade[ds]?|credib|concall|trend for|pledge[ds]?)\b")

_ON_RE = re.compile(r"\b(?:is|for|of|in|on|about|does|do|has)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_POSS_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9&.\-]{1,14})'s\b")
_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")
_NOT_TICKER = {"WHAT", "WHATS", "ANY", "THE", "IS", "IN", "ON", "OF", "HOW", "GOOD", "SAFE",
               "RISK", "RISKS", "GNPA", "NPA", "CET1", "ROA", "ROE", "ROCE", "PE", "PB",
               "PT14", "NII", "CRAR", "CAR", "DE", "OPM", "QUALITY", "TIER", "BANK",
               "FUNDAMENTALS", "VALUATION", "DEBT", "MARGIN", "ASSET"}

# which figure the analyst actually asked for → the render leads with it
_FOCUS = [
    ("asset_quality", re.compile(r"\b(gnpa|gross npa|net npa|nnpa|npa|asset quality|provision|credit cost)\b")),
    ("capital",       re.compile(r"\b(cet1|tier 1|tier-1|capital adequacy|crar|car\b|how safe|safe(?:ty)?)\b")),
    ("profitability", re.compile(r"\b(roa\b|return on assets|roce|roe\b|return on equity|margin|opm|nii|"
                                 r"net interest income|cost[- ]to[- ]income)\b")),
    ("valuation",     re.compile(r"\b(valuation|overvalued|undervalued|expensive|cheap|\bpe\b|p/e|\bpb\b|p/b|book value)\b")),
    ("balance_sheet", re.compile(r"\b(debt|leverage|debt to equity|d/e|balance sheet)\b")),
    ("risk",          re.compile(r"\b(risks?|red flags?|disqualif)\b")),
]


def _candidate_symbol(query: str) -> str:
    q = re.sub(r"\s+", " ", (query or "").strip())
    m = _POSS_RE.search(q)                      # "HDFCBANK's CET1"
    if m and m.group(1).upper() not in _NOT_TICKER:
        return m.group(1).upper()
    m = _ON_RE.search(q)                        # "risks in HDFCBANK" / "is HDFCBANK a good bank"
    if m and m.group(1).upper() not in _NOT_TICKER:
        return m.group(1).upper()
    caps = [t for t in _CAPS_RE.findall(q) if t.upper() not in _NOT_TICKER]
    return caps[0].upper() if len(caps) == 1 else ""


def _focus(ql: str) -> str:
    for name, rx in _FOCUS:
        if rx.search(ql):
            return name
    return "all"


def parse_quality(query: str) -> dict | None:
    """"what's HDFCBANK's CET1 / is HDFCBANK a good bank / what's TCS's ROCE / risks in X" ->
    {flow:"quality", params:{symbol, focus}} | None. Needs a fundamentals cue AND a symbol, and
    yields any ask that belongs to another per-symbol flow (news / rotation / filings / credibility)."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    if _NOT_US.search(ql):
        return None                              # another flow owns this shape
    if not _QUAL_RE.search(ql):
        return None
    sym = _candidate_symbol(q)
    if not sym:
        return None                              # symbol-anchored: the market-wide screen keeps it
    return {"flow": "quality", "params": {"symbol": sym, "focus": _focus(ql)}}


def quality_for(symbol: str, *, as_of: str | None = None) -> dict | None:
    """The symbol's point-in-time fundamentals + its scored quality read.

    Returns {symbol, as_of, f, score, subtype} or None when nothing is known. REUSES the existing
    chain end-to-end (no new query, no vendor call): as_of_fundamentals → financial_subtype →
    score_fundamentals, so a lender automatically gets the Doctrine-D model + its NA/PROVISIONAL
    honesty and a non-financial gets the generic pt14 — exactly what the rest of the estate shows.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    try:
        from src.automation.fundamentals_asof import as_of_fundamentals
        from src.automation.scoring import score_fundamentals
    except Exception:
        return None
    try:
        f = as_of_fundamentals(sym, as_of or date.today().isoformat())
    except Exception:
        f = None
    if not f:
        return None
    # Doctrine D is resolved SEPARATELY and defensively: `financial_subtype` is newer than the rest
    # of the scorer, and on a multi-lane estate this module can legitimately run against a box where
    # a sibling's scoring.py deploy has not caught up yet (observed 2026-07-16). A hard import here
    # made the whole flow answer "no fundamentals on record" for EVERY symbol — a lie, since the
    # fundamentals were right there. So: no sub-type -> fall back to the generic read and still show
    # the numbers; the lender model switches itself on the moment scoring.py carries it.
    sub = None
    try:
        from src.automation.scoring import financial_subtype
        sub = financial_subtype(sym)
    except Exception:
        sub = None
    try:
        score = score_fundamentals(f, is_financial=sub is not None, subtype=sub)
    except TypeError:
        score = score_fundamentals(f)          # pre-Doctrine-D signature — still render the figures
    except Exception:
        return None
    return {"symbol": sym, "as_of": f.get("as_of_period_end") or f.get("as_of"),
            "f": f, "score": score, "subtype": sub}


# (key, label, unit) rows the render shows per focus — only non-None values are printed.
_ROWS = {
    "asset_quality": [("gnpa_pct", "Gross NPA", "%"), ("nnpa_pct", "Net NPA", "%"),
                      ("credit_cost_pct", "Credit cost", "%")],
    "capital":       [("cet1_pct", "CET1", "%"), ("debt_to_equity", "Debt / equity", "×")],
    "profitability": [("roa_pct", "RoA (quarter)", "%"), ("roe", "RoE", "%"),
                      ("roce", "ROCE", "%"), ("opm_latest", "OPM", "%"),
                      ("nii_growth_5y", "NII growth 5y", "%"), ("cost_to_income", "Cost-to-income", "%")],
    "valuation":     [("pe", "P/E", "×"), ("pb", "P/B", "×")],
    "balance_sheet": [("debt_to_equity", "Debt / equity", "×"), ("promoter_pledge", "Promoter pledge", "%"),
                      ("promoter_holding", "Promoter holding", "%")],
    "risk":          [("promoter_pledge", "Promoter pledge", "%"), ("gnpa_pct", "Gross NPA", "%"),
                      ("debt_to_equity", "Debt / equity", "×")],
}


def rows_for(bundle: dict, focus: str = "all") -> list[tuple]:
    """[(label, value, unit)] for the asked-about facet, else a sensible headline set. Skips
    unknowns rather than printing a zero — an absent ratio is 'not known', never 'nil'."""
    f = bundle.get("f") or {}
    if focus in _ROWS:
        keys = _ROWS[focus]
    else:
        lender = bool(bundle.get("subtype"))
        keys = (_ROWS["asset_quality"] + _ROWS["capital"] + _ROWS["profitability"][:2]
                if lender else
                [("roce", "ROCE", "%"), ("opm_latest", "OPM", "%"), ("pe", "P/E", "×"),
                 ("pb", "P/B", "×"), ("debt_to_equity", "Debt / equity", "×")])
    out = []
    for key, label, unit in keys:
        v = f.get(key)
        if isinstance(v, (int, float)):
            out.append((label, v, unit))
    return out


def _selftest() -> int:
    # ── recognition: a fundamentals cue + a symbol ──
    assert parse_quality("what's HDFCBANK's CET1")["params"] == {"symbol": "HDFCBANK", "focus": "capital"}
    assert parse_quality("what is HDFCBANK gnpa")["params"]["focus"] == "asset_quality"
    assert parse_quality("is HDFCBANK a good bank")["params"]["symbol"] == "HDFCBANK"
    assert parse_quality("what's TCS's ROCE")["params"] == {"symbol": "TCS", "focus": "profitability"}
    assert parse_quality("what is TCS pt14 tier")["params"]["symbol"] == "TCS"
    assert parse_quality("what are the risks in HDFCBANK")["params"]["focus"] == "risk"
    assert parse_quality("is TCS overvalued")["params"] == {"symbol": "TCS", "focus": "valuation"}
    assert parse_quality("HDFCBANK asset quality")["params"]["focus"] == "asset_quality"
    # ── yields: no symbol -> the market-wide SCREEN keeps it ──
    assert parse_quality("overvalued stocks") is None
    assert parse_quality("elite ROCE names") is None
    assert parse_quality("deep value") is None
    # ── yields: another per-symbol flow owns the shape ──
    assert parse_quality("TCS news") is None
    assert parse_quality("what phase is TCS in") is None
    assert parse_quality("any pledge on INFY") is None          # filings
    assert parse_quality("credit rating of INFY") is None       # filings
    assert parse_quality("is TCS credible") is None             # credibility/why
    assert parse_quality("tell me about TCS") is None           # the card's job — no fundamentals cue
    assert parse_quality("") is None
    # ── rows: unknowns are skipped, never printed as zero ──
    b = {"subtype": "bank", "f": {"gnpa_pct": 1.42, "nnpa_pct": None, "cet1_pct": 19.97}}
    got = rows_for(b, "asset_quality")
    assert got == [("Gross NPA", 1.42, "%")], got
    assert rows_for(b, "capital")[0] == ("CET1", 19.97, "%")
    assert rows_for({"subtype": None, "f": {}}, "all") == []
    # ── read degrades to None, never raises ──
    assert quality_for("") is None
    print("quality_flow selftest OK — recognition (fundamentals cue + symbol-anchored; yields to the "
          "market screen and to news/rotation/filings/credibility) + focus routing + unknown-skipping rows.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
