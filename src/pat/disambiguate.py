"""Deterministic synonym + ambiguity layer, in FRONT of the Gemini engine.

Two ₹0, rule-based jobs (no LLM here — honors the doctrine that the live picking
path stays deterministic):

  1. **Synonym hints.** Map the analyst's trade-desk words → Pat's canonical
     concepts (delivery→accumulation, momentum→RS, quality→fundamentals,
     gainers→movers) and surface them to the engine prompt, lifting first-answer
     routing without a model change.

  2. **Clarify-before-guess (§4.5).** When the ask is genuinely ambiguous, return a
     ``clarify`` payload — a short question + 2–3 *disambiguated re-runs* as chips —
     instead of letting the engine guess a default. Two ambiguity kinds:
       • **intent**: a strength word with no anchor ("strong stocks" — momentum or
         quality?), and no explicit timeframe (a timeframe implies a momentum read);
       • **timeframe**: a time-sensitive metric (RS / accumulation / movers) with a
         *vague* time word ("recently", "lately") and no explicit window.

The clarify chips re-run the ORIGINAL query with the ambiguity resolved
(``/dash/pat?q=…``), so every other bit of context the analyst gave (sector, etc.)
is preserved, and the disambiguated re-run carries an anchor so it can't loop back
into another clarify.

A separate :func:`clarify_from_flows` builds a clarify from whole-flow chips — used
by the engine's low-confidence fallback (Nous Hermes idea #2).
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

# Canonical concept -> distinctive trigger phrases (lowercased, substring-matched).
# NB: deliberately EXCLUDES the ambiguous strength words below, so they never
# auto-anchor — that is what lets "strong stocks" reach the intent clarify.
SYNONYMS: dict[str, list[str]] = {
    "accumulation": ["delivery", "deliveries", "deliv ", "strong hand", "strong-hand",
                     "stronghand", "accumulat", "being bought", "smart money",
                     "absorption", "dvpt", "distribut"],
    "rs":           ["relative strength", "rs rank", "rs leader", "momentum",
                     "outperform", "market leader", "leading the market",
                     "beating the market", "strong in strong", "strong-in-strong",
                     "strength vs"],
    "fundamentals": ["fundamental", "valuation", "undervalued", "p/e", "pe ratio",
                     "cheap", "expensive", "roce", "roe", "compounder", "quality",
                     "debt-free", "debt free", "balance sheet", "promoter",
                     "earnings growth", "profit growth", "margin"],
    "movers":       ["mover", "gainer", "loser", "top gain", "top los", "biggest move",
                     "most active", "what moved", "moved today", "up today",
                     "down today", "gained today", "fell today"],
    "explain":      ["what is ", "what's ", "explain", "define ", "definition",
                     "meaning of", "what does "],
    "index":        ["index", "indices", "sectoral", "sector rotation",
                     "which sector", "sector performance"],
}

# Vague time words = "a timeframe is intended but unspecified" → ask which.
_VAGUE_TIME = ["recently", "lately", "nowadays", "these days", "of late", "off late",
               "this period", "for a while", "past while"]

# Explicit timeframe markers — if any is present, the timeframe is NOT ambiguous.
_EXPLICIT_TIME = ["today", "yesterday", "this week", "last week", "this month",
                  "last month", "1 month", "1-month", "1m", "3 month", "3-month",
                  "3m", "6 month", "6-month", "6m", "this year", "last year",
                  "1 year", "1y", "12m", "ytd", "qtd", "52 week", "52-week", "52w",
                  "over the last", "over the past", "past month", "past week",
                  "past year", "latest session", "session", "intraday"]

# Strength words ambiguous between momentum (RS) and fundamentals (quality).
_AMBIG_INTENT = ["strongest", "strong", "strength", "best stocks", "best names",
                 "good stocks", "great stocks", "top stocks"]

_INTENT_SET = ("rs", "fundamentals", "accumulation", "movers", "explain")
_TIME_SENSITIVE = ("rs", "accumulation", "movers")

_WS = re.compile(r"\s+")


def _norm(q: str) -> str:
    return _WS.sub(" ", (q or "").strip().lower())


def _has_any(q: str, phrases) -> bool:
    return any(p in q for p in phrases)


def _concepts(qn: str) -> set:
    return {c for c, phrases in SYNONYMS.items() if _has_any(qn, phrases)}


def concepts(query: str) -> set:
    """Public: the canonical concepts a (raw) query touches, by synonym match."""
    return _concepts(_norm(query))


def hints(query: str) -> str:
    """A short prompt directive naming the matched concepts, or '' if none.

    Appended to the engine's system prompt so the model prefers the flows the
    analyst's vocabulary points at (deterministic routing lift, ₹0).
    """
    cs = _concepts(_norm(query))
    if not cs:
        return ""
    label = {"accumulation": "accumulation (strong-hand delivery)",
             "rs": "rs (relative-strength momentum)",
             "fundamentals": "fundamentals (valuation/quality/growth)",
             "movers": "movers (today's price moves)",
             "index": "index (NSE index/sector performance, best/worst/turning)",
             "explain": "explain (define a metric)"}
    named = ", ".join(label[c] for c in sorted(cs) if c in label)
    return ("VOCAB MATCH — the analyst's words map to these Pat flows: " + named +
            ". Prefer them unless the rest of the question clearly says otherwise.")


def _q_href(text: str) -> str:
    return "/dash/pat?q=" + quote_plus(text)


def _clarify_intent(orig: str) -> dict:
    o = orig.strip()
    return {
        "flow": "clarify", "reason": "intent",
        "question": (f'"{o}" — strong in which sense? Momentum (the market bidding it '
                     "up), company fundamentals, or strong-hand delivery?"),
        "chips": [
            {"label": "Momentum — relative strength", "href": _q_href(o + " by relative strength")},
            {"label": "Fundamentals — quality & value", "href": _q_href(o + " by fundamental quality")},
            {"label": "Strong-hand delivery", "href": _q_href(o + " by delivery accumulation")},
        ],
    }


def _clarify_timeframe(orig: str, cs: set) -> dict:
    o = orig.strip()
    if "movers" in cs and "rs" not in cs:
        opts = [("Today / latest", " today"), ("This week", " this week")]
    elif "accumulation" in cs and "rs" not in cs:
        opts = [("Latest day", " today"), ("Last month", " over the last month"),
                ("Last 3 months", " over the last 3 months")]
    else:  # rs (the common vague-timeframe case), or rs combined with others
        opts = [("Last month", " over the last month"),
                ("Last 3 months", " over the last 3 months"),
                ("Last 6 months", " over the last 6 months"),
                ("This year", " over the last year")]
    return {
        "flow": "clarify", "reason": "timeframe",
        "question": f'Over what window should I read "{o}"? Pick one and I\'ll rank by it:',
        "chips": [{"label": l, "href": _q_href(o + suf)} for l, suf in opts],
    }


def check(query: str) -> dict | None:
    """Return a ``clarify`` payload if the ask is genuinely ambiguous, else None.

    None means "not ambiguous — let the engine route it." Deterministic and ₹0;
    never raises.
    """
    try:
        qn = _norm(query)
        if len(qn) < 2:
            return None
        cs = _concepts(qn)
        has_explicit_time = _has_any(qn, _EXPLICIT_TIME)

        # 1) Intent ambiguity — a strength word, no anchoring concept, no timeframe
        #    (an explicit timeframe implies a momentum/performance read → not ambiguous).
        if _has_any(qn, _AMBIG_INTENT):
            anchored = cs & set(_INTENT_SET)
            if not anchored and not has_explicit_time:
                return _clarify_intent(query)

        # 2) Timeframe ambiguity — a time-sensitive metric with a VAGUE time word
        #    and no explicit window. (Bare omission keeps the sensible default.)
        time_sensitive = cs & set(_TIME_SENSITIVE)
        if time_sensitive and _has_any(qn, _VAGUE_TIME) and not has_explicit_time:
            return _clarify_timeframe(query, time_sensitive)
    except Exception:
        return None
    return None


# Whole-flow chips for the engine's low-confidence fallback (Nous Hermes #2).
_FLOW_CHIP = {
    "rs":           ("RS leaders — momentum", "/dash/pat?flow=rs"),
    "fundamentals": ("Fundamentals — quality & value", "/dash/pat?flow=fundamentals"),
    "accumulation": ("Accumulation — strong-hand delivery", "/dash/pat?flow=accumulation"),
    "movers":       ("Today's movers", "/dash/pat?flow=movers"),
    "explain":      ("Explain a metric", "/dash/pat?flow=explain"),
}


def clarify_from_flows(orig: str, flows, question: str | None = None) -> dict | None:
    """Build a clarify from whole-flow chips (deduped, in order). None if < 2 flows."""
    seen: set = set()
    chips: list = []
    for f in flows:
        if f in _FLOW_CHIP and f not in seen:
            seen.add(f)
            lbl, href = _FLOW_CHIP[f]
            chips.append({"label": lbl, "href": href})
    if len(chips) < 2:
        return None
    return {
        "flow": "clarify", "reason": "low_confidence",
        "question": question or (f'I wasn\'t fully sure what "{orig.strip()}" needs — '
                                 "which of these did you mean?"),
        "chips": chips[:3],
    }


# ── deterministic INDEX route ────────────────────────────────────────────────
# A clear index-PERFORMANCE ask ("worst performing index over the last year that
# started turning up") is routed straight to the index flow — ₹0, immune to
# mis-routing AND to the shared Gemini quota. This is the rule that fixes the miss
# where an index question landed on stock RS-leaders and returned nothing.
_INDEX_UNIVERSE = ["index", "indices", "sectoral", "sector rotation", "which sector",
                   "sector performance", "best performing sector", "worst performing sector",
                   "sectors doing"]
_INDEX_PERF = ["perform", "return", "best", "worst", "laggard", "leader", "strong",
               "weak", "gain", "loss", "rising", "falling", "turning", "rotation",
               "outperform", "underperform", "top ", "bottom", "beaten", "recover",
               "reversal", "up over", "down over"]
# Markers that the analyst wants the CONSTITUENTS (stocks), not index performance —
# in which case this layer steps aside and lets the stock flows handle it.
_CONSTITUENT = ["stocks in", "constituent", "names in", "members of", "shares in",
                "which stocks", "companies in", "stocks of", "stocks from"]


def route_index(query: str) -> dict | None:
    """Return ``{flow:"index", params:{...}}`` for a clear index-performance ask, else None.

    Deterministic and ₹0: infers direction (worst→laggards), window (timeframe),
    and the turning lens ("started performing better"/recovering). Returns None for
    constituent questions (those want stocks) or when no performance intent is named.
    """
    try:
        qn = _norm(query)
        if not _has_any(qn, _INDEX_UNIVERSE):
            return None
        if _has_any(qn, _CONSTITUENT):
            return None
        if not _has_any(qn, _INDEX_PERF):
            return None
        params: dict[str, str] = {}
        if _has_any(qn, ["worst", "laggard", "weakest", "underperform", "biggest loser",
                         "beaten", "fallen", "bottom"]):
            params["direction"] = "laggards"
        # Window — longest first so an explicit 1Y wins over the trailing "month".
        if _has_any(qn, ["1 year", "one year", "12 month", "12-month", "12m", "1y",
                         "last year", "past year", "this year", "yearly", "annual",
                         "52 week", "52-week"]):
            params["window"] = "1y"
        elif _has_any(qn, ["6 month", "6-month", "6m", "half year", "half-year"]):
            params["window"] = "6m"
        elif _has_any(qn, ["1 month", "one month", "past month", "last month",
                           "this month", "1-month", "1m", "monthly"]):
            params["window"] = "1m"
        # Turning — "started performing better / recovering / reversing recently".
        if _has_any(qn, ["turning", "turn around", "turnaround", "started performing better",
                         "performing better", "recover", "reversal", "reversing",
                         "bottoming", "bottomed", "picking up", "started rising",
                         "starting to rise", "improving", "uptick", "coming back",
                         "started to perform", "perform better"]):
            params["turning"] = "turn"
        return {"flow": "index", "params": params}
    except Exception:
        return None
