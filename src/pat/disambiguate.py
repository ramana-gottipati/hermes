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


# ── deterministic routers for the cheap-win flows (₹0, quota-proof) ───────────
# Each requires a DISTINCTIVE signal and returns None otherwise, so a clear ask
# never spends a Gemini token (mirrors route_index). Precedence is fixed in
# route_extra(): single-stock → distribution/consolidation → kill-list → pt14 →
# overvalued → rs-laggards. Sector-from-text is NOT extracted here (the chips
# narrow); that's a deliberate v1 cut to keep these deterministic.
_DISTRIBUTION = ["distribut", "being sold", "smart money exiting", "smart money is exiting",
                 "being dumped", "offloaded", "offloading", "strong hand selling",
                 "strong hands selling", "supply coming"]
_CONSOLIDATION = ["consolidat", "coiling"]
_REDFLAG_LIST = ["stocks to avoid", "stock to avoid", "red flag stock", "red-flag stock",
                 "hard disqualified", "hard-disqualified", "disqualified", "kill list",
                 "kill-list", "stay away from", "names to avoid", "avoid these"]
_PT14 = ["pt14", "pt-14", "14 pattern", "14-pattern", "pattern score", "quality score",
         "quality tier", "tier 1", "tier-1", "tier 2", "tier 3", "t1 quality"]
_OVERVALUED = ["overvalued", "over valued", "over-valued", "expensive stock", "expensive name",
               "expensive share", "high pe", "high p/e", "frothy", "bubble stock",
               "richly valued", "priciest", "most expensive"]
_RSLAG = ["weakest stock", "weak stock", "laggard stock", "rs laggard", "weakest name",
          "weak name", "losing momentum", "weak relative strength", "stocks lagging",
          "lagging stock", "underperforming stock", "weakest in", "biggest laggard",
          "weakest shares"]

# Explicit single-stock asks → capture the trailing name/symbol token. Deliberately
# excludes vague leads ("show me", "how is") that collide with screen asks.
_STOCK_TRIGGER = re.compile(
    r"^(?:tell me about|what'?s wrong with|whats wrong with|red flags? in|"
    r"details on|info on|snapshot of|look up|pull up)\s+(.+)$", re.I)
_STOCK_STOP = {"the", "a", "an", "this", "that", "it", "my", "any", "some", "these",
               "those", "market", "stock", "stocks", "share", "shares", "nifty", "sensex"}


def _extract_symbol(query: str) -> str | None:
    """A symbol/name token from an explicit single-stock ask, or None."""
    m = _STOCK_TRIGGER.match(_norm(query))
    if not m:
        return None
    tail = m.group(1).strip()
    tail = re.sub(r"\s+(doing|now|today|please|stock|share|shares)\b.*$", "", tail).strip()
    if not tail or tail in _STOCK_STOP:
        return None
    # a multi-word strength/concept phrase ("strong stocks") is not a stock name
    if " " in tail and _has_any(tail, ["strong", "weak", "best", "top ", "cheap", "quality",
                                       "momentum", "accumulat", "distribut", "leader", "laggard"]):
        return None
    return tail


def route_extra(query: str) -> dict | None:
    """Route the cheap-win flows deterministically (₹0). None → let the engine parse.

    Order matters: a named single-stock ask wins over the list flows (so "red flags
    in INFY" → the stock card, while "red flag stocks" → the kill-list). Never raises.
    """
    try:
        qn = _norm(query)
        if len(qn) < 2:
            return None

        sym = _extract_symbol(query)
        if sym:
            return {"flow": "card", "params": {"sym": sym}}

        # distribution / consolidation = the accumulation flow's character MIRROR
        # (canonical contract: a `character` param on accumulation, not a new flow).
        if _has_any(qn, _DISTRIBUTION):
            return {"flow": "accumulation", "params": {"character": "distribution"}}
        if _has_any(qn, _CONSOLIDATION):
            return {"flow": "accumulation", "params": {"character": "consolidation"}}

        # the hard-disqualifier kill-list (a plural "avoid" ask, no named stock)
        if _has_any(qn, _REDFLAG_LIST):
            return {"flow": "disqualified", "params": {}}

        # pt14 quality tiers (distinct from the generic "quality" → fundamentals)
        if _has_any(qn, _PT14):
            params: dict[str, str] = {}
            if _has_any(qn, ["tier 1", "tier-1", "t1"]):
                params["tier"] = "t1"
            elif _has_any(qn, ["tier 2", "tier-2"]):
                params["tier"] = "t2"
            elif _has_any(qn, ["tier 3", "tier-3"]):
                params["tier"] = "t3"
            return {"flow": "pt14", "params": params}

        # overvalued / expensive → the inverted valuation screen
        if _has_any(qn, _OVERVALUED):
            return {"flow": "fundamentals",
                    "params": {"val": "rich", "qual": "any", "grow": "any",
                               "bs": "any", "own": "any"}}

        # weak / RS-laggard stocks = the rs flow's `direction` MIRROR (canonical
        # contract: direction=laggards on rs). NOT index laggards, NOT today's price
        # losers (those are the index and movers flows respectively).
        if _has_any(qn, _RSLAG) and not _has_any(qn, _INDEX_UNIVERSE) \
                and not _has_any(qn, ["today", "this week", "intraday", "gainer", "loser",
                                      "gained", "fell"]):
            return {"flow": "rs", "params": {"direction": "laggards"}}
    except Exception:
        return None
    return None


# ── out-of-scope / advisory guardrails (catalog Part 5) ──────────────────────
# Pat is SEARCH/SCREENING — not advice, not prediction, not execution — over NSE
# cash equities + sectoral indices only. These deterministic detectors return a
# clarify-shaped REDIRECT (₹0) instead of letting an advisory / out-of-domain ask
# fall through to a wrong answer or a blank result. The SEBI line is hard: Pat
# never issues a buy/sell/"safe" verdict. Triggers are kept PRECISE (e.g. "gold
# price", not bare "gold", so "gold loan stocks" still screens normally).
_G_ADVICE = ["should i buy", "should i sell", "should i hold", "should i exit",
             "should i invest", "should i book", "should i average", "is it a good time to buy",
             "good time to buy", "good time to enter", "worth buying", "is it a buy",
             "is it a sell", "will i make money", "make me rich", "double my money",
             "multiply my money", "guaranteed return", "safe to invest", "is it safe to invest",
             "what should i buy", "what to buy", "where should i invest", "tell me what to buy",
             "which stock should i", "is x a buy"]
_G_PREDICT = ["predict", "forecast", "price target", "target price", "tomorrow",
              "next week", "next month", "will it go up", "will it rise", "will it fall",
              "will it recover", "when will", "going to crash", "will the market",
              "where will", "by friday", "by monday", "intraday tip", "intraday tips",
              "tips for today", "multibagger for", "sure shot"]
_G_FEATURE = ["set an alert", "set alert", "alert me", "alert when", "notify me",
              "remind me", "buy 10", "buy 100", "buy shares", "place an order",
              "square off", "my portfolio", "my holdings", "my p&l", "my pnl",
              "add to watchlist", "add to my watchlist", "track my"]
_G_WRONG_ASSET = ["option chain", "call option", "put option", "f&o", "f and o",
                  "open interest", "max pain", "put call ratio", "futures and options",
                  "nifty futures", "stock futures", "gold price", "price of gold",
                  "buy gold", "gold etf", "silver price", "crude oil price", "crude price",
                  "commodity price",
                  "usd inr", "usd/inr", "rupee vs", "dollar rupee", "forex", "crypto",
                  "bitcoin", "ethereum", "tesla stock", "nvidia stock", "us stocks",
                  "nasdaq", "s&p 500", "dow jones", "hang seng", "upcoming ipo", "ipo gmp",
                  "grey market premium", "should i apply for the", "mutual fund",
                  "sovereign gold bond", "bond yield", "g-sec", "debenture"]


def _redirect(reason: str, question: str, chips: list) -> dict:
    return {"flow": "clarify", "reason": reason, "question": question,
            "chips": [{"label": l, "href": h} for l, h in chips]}


def route_guardrail(query: str) -> dict | None:
    """Return a clarify-shaped REDIRECT for an advisory / out-of-domain ask, else None.

    Deterministic, ₹0, never raises. Runs FIRST in engine.route so an advice/OOD ask
    pre-empts any flow routing (e.g. "should I buy the strongest stock" → the advice
    boundary, not RS leaders). Precise triggers keep legitimate screens unaffected."""
    try:
        qn = _norm(query)
        if len(qn) < 2:
            return None
        if _has_any(qn, _G_WRONG_ASSET):
            return _redirect(
                "out_of_scope",
                "I cover NSE cash equities and sectoral indices — not derivatives, "
                "commodities, forex, crypto, IPOs, mutual funds or global stocks. Here's "
                "what I can show:",
                [("Today's movers", "/dash/pat?flow=movers"),
                 ("RS leaders", "/dash/pat?flow=rs"),
                 ("Index performance", "/dash/pat?flow=index")])
        if _has_any(qn, _G_FEATURE):
            return _redirect(
                "out_of_scope",
                "I'm a screener — I can't set alerts, place trades or hold a portfolio. "
                "But I can show you the data behind the decision:",
                [("Today's movers", "/dash/pat?flow=movers"),
                 ("Accumulation", "/dash/pat?flow=accumulation"),
                 ("Fundamentals", "/dash/pat?flow=fundamentals")])
        if _has_any(qn, _G_PREDICT) or ("recover" in qn and "will" in qn):
            return _redirect(
                "prediction",
                "I report what the data shows right now — I don't forecast prices, "
                "targets or levels. Here's the current read:",
                [("Index performance", "/dash/pat?flow=index"),
                 ("Today's movers", "/dash/pat?flow=movers"),
                 ("RS leaders", "/dash/pat?flow=rs")])
        if _has_any(qn, _G_ADVICE):
            return _redirect(
                "advice",
                "I don't give buy/sell advice — I'm a screening tool, not a SEBI-"
                "registered adviser. I can show you the data to decide for yourself:",
                [("Quality & value", "/dash/pat?flow=fundamentals"),
                 ("RS leaders", "/dash/pat?flow=rs"),
                 ("Accumulation", "/dash/pat?flow=accumulation")])
    except Exception:
        return None
    return None
