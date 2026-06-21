"""Pat's query-understanding layer — semantic parse + a deterministic compiler.

This replaces the old "flat flow-classifier" (pick 1 of N buckets) with actual
*logical decomposition*:

    query  ──(LLM semantic parse, in engine.py)──▶  structured INTENT
    structured INTENT  ──(compile_intent here, ₹0)──▶  {flow,params} | clarify

The structured intent forces the model to reason in the three pieces an analyst's
question actually has:

    universe : stock | index | sector          (WHICH things — decided FIRST)
    rank     : {metric, window, order}          (HOW to order them)
    filters  : [{metric, window, op, value}…]   (extra CONDITIONS — a LIST, so a
                                                  two-window ask like "worst over 1Y
                                                  AND turning up over 1M" is native)

`compile_intent` is the "logical thought": it maps a parsed intent onto the
capability that can actually serve it, OR returns a clarify when the ask is
ambiguous / not yet supported — instead of confidently dumping a wrong table.
It is pure, deterministic, ₹0 and unit-tested by ``eval_set.py`` independent of
any model, so the reasoning can be verified without spending a token.

This module never calls an LLM. ``engine.py`` owns the Gemini call (never-Claude),
hands the parsed JSON to :func:`validate_intent`, then to :func:`compile_intent`.
:func:`parse_fallback` is a *degraded* deterministic parser used only when the
model is unavailable (e.g. the Gemini quota is exhausted) — it is a safety net,
explicitly NOT the primary brain.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

# ── the intent vocabulary (closed sets — the single source of truth) ──────────
UNIVERSES = {"stock", "index", "sector"}
# pt14 = the 14-pattern quality TIER screen (distinct from fundamentals "quality");
# avoid = the hard-disqualifier kill-list (the framework's own "reject" verdict).
METRICS = {"return", "rs", "delivery", "valuation", "quality", "growth", "price_move",
           "pt14", "avoid"}
WINDOWS = {"1d", "1w", "1m", "3m", "6m", "1y"}
ORDERS = {"best", "worst"}
OPS = {">", "<", ">=", "<=", "improving", "declining"}
# the strong-hand delivery CHARACTER (accumulation flow); distribution = exiting.
CHARACTERS = {"accumulation", "distribution", "consolidation"}
TASKS = {"rank", "explain", "stock"}
# momentum-oscillator screens (the `oscillators` flow). Keys mirror OSC_SCREEN.
INDICATORS = {"rsi_oversold", "rsi_overbought", "macd_bull", "macd_bear", "macd_positive"}

_WS = re.compile(r"\s+")


def _norm(q: str) -> str:
    return _WS.sub(" ", (q or "").strip().lower())


def _has_any(q: str, phrases) -> bool:
    return any(p in q for p in phrases)


# ── window mappers: an intent window → each flow's own window-chip key ─────────
def _index_window(w):           # index flow keys: "" (3m) | 1m | 6m | 1y
    return {"1m": "1m", "6m": "6m", "1y": "1y"}.get(w, "")


def _rs_window(w):              # rs flow keys: "" (3m) | 1m | 6m | 12m
    return {"1m": "1m", "6m": "6m", "1y": "12m"}.get(w, "")


def _acc_window(w):            # accumulation flow keys: "" (latest) | 1m | 3m
    return {"1m": "1m", "3m": "3m"}.get(w, "")


def _movers_window(w):         # movers flow keys: "" (today) | 1w
    return "1w" if w in ("1w",) else ""


# ── intent validation ─────────────────────────────────────────────────────────
def validate_intent(obj) -> dict | None:
    """Coerce a parsed model reply into a safe structured intent, or None.

    Every field is checked against the closed vocab above; anything off-menu is
    dropped (it can never reach SQL). Returns None only when there's nothing usable.
    """
    if not isinstance(obj, dict):
        return None
    task = obj.get("task")
    if task == "explain":
        slug = obj.get("explain") or obj.get("term")
        return {"task": "explain", "explain": slug} if slug else None
    if task == "stock":              # single-symbol card ("tell me about INFY")
        sym = obj.get("symbol") or obj.get("ticker")
        return {"task": "stock", "symbol": str(sym).strip()} if sym and str(sym).strip() else None
    if task == "ood":                # out-of-domain → a boundary clarify, never an answer
        kind = obj.get("kind")
        return {"task": "ood", "kind": kind if kind in ("advisory", "prediction", "feature", "asset") else "advisory"}

    universe = obj.get("universe")
    if universe not in UNIVERSES:
        universe = "stock"           # sensible default; the compiler still reasons

    rank_in = obj.get("rank") if isinstance(obj.get("rank"), dict) else {}
    rank = {}
    m = rank_in.get("metric")
    if m in METRICS:
        rank["metric"] = m
    w = rank_in.get("window")
    if w in WINDOWS:
        rank["window"] = w
    o = rank_in.get("order")
    if o in ORDERS:
        rank["order"] = o

    filters = []
    raw_filters = obj.get("filters")
    if isinstance(raw_filters, list):
        for f in raw_filters[:6]:
            if not isinstance(f, dict):
                continue
            fm, fw, fo = f.get("metric"), f.get("window"), f.get("op")
            if fm not in METRICS or fo not in OPS:
                continue
            ff = {"metric": fm, "op": fo}
            if fw in WINDOWS:
                ff["window"] = fw
            v = f.get("value")
            if isinstance(v, (int, float)):
                ff["value"] = v
            filters.append(ff)

    scope = {}
    raw_scope = obj.get("scope") if isinstance(obj.get("scope"), dict) else {}
    if isinstance(raw_scope.get("sector"), str) and raw_scope["sector"].strip():
        scope["sector"] = raw_scope["sector"].strip()
    if isinstance(raw_scope.get("index"), str) and raw_scope["index"].strip():
        scope["index"] = raw_scope["index"].strip()

    character = obj.get("character")
    if character not in CHARACTERS:
        character = None

    indicator = obj.get("indicator")
    if indicator not in INDICATORS:
        indicator = None

    conf = obj.get("confidence")
    try:
        conf = int(conf)
    except (TypeError, ValueError):
        conf = None

    if not rank and not filters and not scope and not character and not indicator:
        # nothing actionable parsed
        return None
    return {"task": "rank", "universe": universe, "rank": rank, "filters": filters,
            "scope": scope, "character": character, "indicator": indicator, "confidence": conf}


# ── clarify / unsupported helpers (clarify-shaped so web renders them as-is) ──
def _href(q: str) -> str:
    return "/dash/pat?q=" + quote_plus(q)


def _clarify(reason: str, question: str, chips: list) -> dict:
    return {"flow": "clarify", "reason": reason, "question": question, "chips": chips}


def _filters_improving_1m(filters) -> bool:
    """A condition that means 'getting better recently' over ~1 month."""
    for f in filters or []:
        if f.get("metric") in ("return", "rs", "price_move"):
            if f.get("op") == "improving":
                return True
            if f.get("op") in (">", ">=") and f.get("window") in ("1m", "1w") \
                    and (f.get("value") in (0, None) or (isinstance(f.get("value"), (int, float)) and f["value"] <= 0)):
                return True
    return False


# ── the compiler — the LOGICAL THOUGHT (pure, deterministic, ₹0) ──────────────
def compile_intent(intent: dict) -> dict | None:
    """Map a structured intent onto the capability that can serve it.

    Returns ``{flow, params}`` for a data/explain flow, or a clarify payload (incl.
    ``reason='unsupported'`` for asks we can't serve yet) — never a confident wrong
    dump. None means "nothing to do" (caller degrades to the glossary search).
    """
    if not isinstance(intent, dict):
        return None

    if intent.get("task") == "explain":
        slug = (intent.get("explain") or "").strip()
        if not slug:
            return None
        try:
            from src.pat.glossary import GLOSSARY, find
            if slug in GLOSSARY:
                return {"flow": "explain", "explain": slug}
            hits = find(slug, limit=1)          # resolve "DVPT"/"delivery" → real slug
            if hits:
                return {"flow": "explain", "explain": hits[0][0]}
        except Exception:
            pass
        return None

    if intent.get("task") == "stock":     # single-symbol snapshot / red-flag card
        sym = (intent.get("symbol") or "").strip()
        return {"flow": "card", "params": {"sym": sym}} if sym else None

    if intent.get("task") == "ood":       # advisory / prediction / feature / wrong-asset
        return ood_clarify(intent.get("kind"))

    universe = intent.get("universe", "stock")
    rank = intent.get("rank") or {}
    filters = intent.get("filters") or []
    scope = intent.get("scope") or {}
    character = intent.get("character")
    metric = rank.get("metric")
    window = rank.get("window")
    order = rank.get("order")
    turning = _filters_improving_1m(filters)

    # ── momentum oscillators (RSI/MACD) — a definitive screen selector ────────
    indicator = intent.get("indicator")
    if indicator in INDICATORS:
        return {"flow": "oscillators", "params": {"screen": indicator}}

    # ── INDEX / SECTOR universe → the index-performance flow ──────────────────
    # (sector-performance questions are index questions: the sector's index.)
    if universe in ("index", "sector"):
        # If they want stock-level facts ABOUT a sector (delivery/valuation/quality),
        # that's a stock screen scoped to the sector, not an index-performance pull.
        if (metric in ("delivery", "valuation", "quality", "growth", "pt14", "avoid")
                or character) and universe == "sector":
            return _compile_stock(metric, window, order, filters, scope, turning, character)
        params: dict = {}
        iw = _index_window(window)
        if iw:
            params["window"] = iw
        if order == "worst":
            params["direction"] = "laggards"
        if turning:
            params["turning"] = "turn"
        return {"flow": "index", "params": params}

    # ── STOCK universe ────────────────────────────────────────────────────────
    return _compile_stock(metric, window, order, filters, scope, turning, character)


# Map a parsed fundamentals condition (metric, op, value) → a FUND_* chip key. The
# chips are coarse tiers; we pick the closest one the condition implies. This is the
# fix for the catalog's §3.4 live bug: the compiler used to DROP the op/value and
# always return the default (cheap) screen — so "overvalued" returned *cheap* stocks.
def _fund_chip(metric, op, value):
    expensive = op in (">", ">=")
    v = value if isinstance(value, (int, float)) else None
    if metric == "valuation":            # P/E
        if expensive:
            return ("val", "rich")       # PE > 40 — the overvalued end
        if v is not None:
            if v <= 15:
                return ("val", "deep")
            if v <= 25:
                return ("val", "")
            if v <= 40:
                return ("val", "growthok")
            return ("val", "rich")
        return ("val", "")               # "cheap"/"low PE", no number → default PE<25
    if metric == "quality":              # ROCE / ROE
        if op in ("<", "<="):
            return None                  # no low-quality tier yet (catalog §3.4 gap)
        if v is not None and v >= 22:
            return ("qual", "elite")
        if v is not None and v >= 14 and v < 18:
            return ("qual", "decent")
        return ("qual", "")              # default ROCE>18 (covers "above 18/20")
    if metric == "growth":
        if op in ("<", "<="):
            return None
        if v is not None and v >= 25:
            return ("grow", "hyper")
        return ("grow", "")              # default profit 5Y>15
    return None


def _compile_fundamentals(metric, order, filters) -> dict:
    """Build the fundamentals params from the ranking metric + every parsed condition,
    honoring the op/value (so "overvalued"/"PE over 80"/"ROCE above 22" screen the
    RIGHT end), instead of dropping them. Coarse tiers, but the polarity is correct."""
    params: dict = {}
    conds = []
    # the ranking metric itself carries a polarity: worst valuation = most expensive.
    if metric == "valuation":
        conds.append(("valuation", ">" if order == "worst" else None, None))
    elif metric in ("quality", "growth"):
        conds.append((metric, None, None))
    for f in (filters or []):
        if f.get("metric") in ("valuation", "quality", "growth"):
            conds.append((f["metric"], f.get("op"), f.get("value")))
    for cm, cop, cv in conds:
        chip = _fund_chip(cm, cop, cv)
        if chip:
            params[chip[0]] = chip[1]
    return {"flow": "fundamentals", "params": params}


def _compile_stock(metric, window, order, filters, scope, turning, character=None) -> dict | None:
    sector = scope.get("sector", "") if isinstance(scope, dict) else ""

    # Special framework screens (no metric ranking): the kill-list + the pt14 tiers.
    if metric == "avoid":
        return {"flow": "disqualified", "params": {}}
    if metric == "pt14":
        return {"flow": "pt14", "params": {}}

    # Strong-hand delivery CHARACTER — distribution (exiting) / consolidation (coiling)
    # ride the accumulation flow's `character` chip (the catalog §3.1 cheap win).
    if character in ("distribution", "consolidation"):
        params = {"character": character}
        aw = _acc_window(window)
        if aw:
            params["window"] = aw
        if sector:
            params["sector"] = sector
        return {"flow": "accumulation", "params": params}

    if metric == "price_move":
        params = {}
        mw = _movers_window(window)
        if mw:
            params["window"] = mw
        if order == "worst":
            params["direction"] = "losers"
        return {"flow": "movers", "params": params}

    if metric in ("rs", "return"):
        # "return" at the STOCK level uses relative strength as the performance proxy.
        # WORST = the RS-laggard side (now a real screen via the `direction` chip —
        # §3.2, the flip of the old honest-but-dead-end unsupported redirect).
        params = {}
        rw = _rs_window(window)
        if rw:
            params["window"] = rw
        if sector:
            params["sector"] = sector
        if order == "worst":
            params["direction"] = "laggards"
        return {"flow": "rs", "params": params}

    if metric == "delivery":
        params = {}
        aw = _acc_window(window)
        if aw:
            params["window"] = aw
        if sector:
            params["sector"] = sector
        return {"flow": "accumulation", "params": params}

    if metric in ("valuation", "quality", "growth"):
        return _compile_fundamentals(metric, order, filters)

    # No metric resolved → genuinely ambiguous intent → ask (don't guess).
    return _clarify(
        "intent",
        "What would make a stock a match here — market momentum, fundamental "
        "quality, or strong-hand delivery?",
        [{"label": "Momentum — relative strength", "href": _href("RS leaders")},
         {"label": "Fundamentals — quality & value", "href": _href("quality compounders")},
         {"label": "Strong-hand delivery", "href": _href("stocks being accumulated now")}],
    )


# ── the reasoning prompt (built in engine.py, kept here as the source of truth) ─
SYSTEM_PARSE = (
    "You are the query-understanding step of an Indian-stock-market research tool. "
    "Do NOT answer the question and do NOT pick a screen. Your only job is to PARSE "
    "the analyst's question into a structured intent, reasoning in three steps:\n"
    "  STEP 1 — UNIVERSE: is the question about individual 'stock's, an 'index' "
    "(a sectoral/thematic NSE index, e.g. Nifty IT, Nifty Realty), or a 'sector'? "
    "If it says 'index'/'indices'/'sector', the universe is NOT stock.\n"
    "  STEP 2 — RANK: the single metric the result is ORDERED by, its window, and "
    "order. metric ∈ [return, rs, delivery, valuation, quality, growth, price_move, "
    "pt14, avoid]; window ∈ [1d,1w,1m,3m,6m,1y]; order ∈ [best, worst]. "
    "'worst/laggard/weakest/underperform' = worst; 'best/top/strongest/leaders' = best. "
    "Use 'pt14' for the 14-pattern quality TIER ('pt14', 'Tier-1', 'T1 names', 'passes "
    "the quality gate') — distinct from 'quality' (ROCE/valuation). Use 'avoid' for the "
    "hard-disqualifier KILL-LIST ('stocks to avoid', 'red-flag stocks', 'what did "
    "Patearn reject', 'disqualified names').\n"
    "  STEP 3 — FILTERS: every ADDITIONAL condition, each as its own {metric,window,"
    "op,value}. op ∈ [>,<,>=,<=,improving,declining]. A phrase like 'started "
    "performing better in the last month' / 'turning up' / 'recovering' is a filter "
    "{metric:return, window:1m, op:improving}. This list is how a TWO-WINDOW ask "
    "('worst over 1Y AND improving over 1M') is captured — never collapse it to one. "
    "Keep the op: 'overvalued'/'PE over 80'/'expensive' is op '>' (NOT cheap); "
    "'under PE 15'/'cheap' is op '<'.\n"
    "  CHARACTER: for strong-hand DELIVERY, set character ∈ [accumulation (default, "
    "smart money BUYING), distribution (smart money EXITING/'being dumped'/'topping "
    "out'), consolidation (coiling)] alongside metric 'delivery'.\n"
    "  SINGLE STOCK: 'tell me about INFY' / \"what's wrong with RELIANCE\" / 'is X a "
    "value trap' → {\"task\":\"stock\",\"symbol\":\"<TICKER>\"}.\n"
    "  OSCILLATORS: for a momentum-indicator screen set indicator ∈ [rsi_oversold "
    "(RSI<30 / oversold), rsi_overbought (RSI>70 / overbought), macd_bull (MACD "
    "bullish crossover / turning up), macd_bear (MACD bearish crossover), "
    "macd_positive (MACD above its signal line)].\n"
    "  BOUNDARY: for buy/sell/hold ADVICE, PRICE PREDICTIONS/targets/timing, alerts/"
    "trades/portfolio actions, or NON-equity assets (gold, crypto, F&O/options, US "
    "indices, bonds), reply {\"task\":\"ood\",\"kind\":\"advisory|prediction|feature|asset\"} "
    "— never screen or answer literally.\n"
    "Also set scope.sector or scope.index when named, and a 0-100 confidence.\n"
    "For a 'what is X' / 'define' question, reply {\"task\":\"explain\",\"explain\":\"<term>\"}.\n"
    "Reply with COMPACT JSON ONLY, no prose:\n"
    '{"task":"rank","universe":"stock|index|sector",'
    '"rank":{"metric":..,"window":..,"order":..},'
    '"filters":[{"metric":..,"window":..,"op":..,"value":..}],'
    '"character":..,"indicator":..,"scope":{"sector":..,"index":..},"confidence":0-100}\n'
    "WORKED EXAMPLES:\n"
    "'worst performing index over the last year that started performing better in the "
    "past month' → "
    '{"task":"rank","universe":"index","rank":{"metric":"return","window":"1y","order":"worst"},'
    '"filters":[{"metric":"return","window":"1m","op":"improving"}],"confidence":95}\n'
    "'stocks under distribution in IT' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"delivery"},"character":"distribution",'
    '"scope":{"sector":"IT"},"confidence":90}\n'
    "'weakest stocks this month' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"rs","window":"1m","order":"worst"},"confidence":90}\n'
    "'overvalued stocks' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"valuation","order":"worst"},"confidence":85}\n'
    "'stocks to avoid' → {\"task\":\"rank\",\"universe\":\"stock\",\"rank\":{\"metric\":\"avoid\"},\"confidence\":90}"
)


# ── OOD guardrails (catalog Part 5) — the #1 priority (SEBI-advice liability) ──
# Advisory / prediction / feature-assumption / wrong-asset are detected here
# deterministically (and the LLM is told to flag them); compile_intent turns the
# flag into a calm BOUNDARY clarify — never a literal answer or a silent empty pull.
_OOD_ADVISORY = ["should i buy", "should i sell", "should i hold", "should i exit",
                 "what to buy", "what should i buy", "is it safe", "safe to invest",
                 "will i make money", "double my money", "make me rich",
                 "right time to invest", "do you agree", "guaranteed", "best stock to buy"]
_OOD_PREDICT = ["predict", "price target", "target price", "will it bounce", "will it go up",
                "next week", "tomorrow's", "forecast", "in 6 months", "by friday",
                "goes up tomorrow", "future price", "where will"]
_OOD_FEATURE = ["set an alert", "set alert", "notify me", "buy 10", "sell my", "stop loss",
                "add to my watchlist", "my portfolio", "intraday tip", "place an order"]
_OOD_ASSET = ["gold price", "crude", "usd/inr", "bitcoin", "crypto", "nasdaq", "s&p 500",
              "hang seng", "option chain", "max pain", "open interest", "f&o ban",
              "nifty futures", "nifty options", "g-sec", "sovereign gold"]


def _detect_ood(qn: str):
    if _has_any(qn, _OOD_ADVISORY):
        return "advisory"
    if _has_any(qn, _OOD_PREDICT):
        return "prediction"
    if _has_any(qn, _OOD_FEATURE):
        return "feature"
    if _has_any(qn, _OOD_ASSET):
        return "asset"
    return None


_OOD_MSG = {
    "advisory": ("I'm a screening tool, not a SEBI-registered adviser — I can't tell you what "
                 "to buy, sell or hold. But I can show you the facts to decide for yourself:",
                 [("RS / momentum leaders", "RS leaders"),
                  ("Quality & value screen", "quality compounders"),
                  ("Strong-hand delivery", "stocks being accumulated now")]),
    "prediction": ("I report what the data shows right now — I don't forecast prices or timing. "
                   "Here's the current picture:",
                   [("Today's movers", "biggest movers today"),
                    ("Sectors turning up", "beaten-down indices reversing"),
                    ("RS leaders", "RS leaders")]),
    "feature": ("I can't set alerts, place trades or track a portfolio — I'm search-only. "
                "What I CAN do:",
                [("Today's movers", "biggest movers today"),
                 ("Screen by fundamentals", "quality compounders"),
                 ("Explain a metric", "what is RS rank")]),
    "asset": ("I only cover NSE cash equities and sectoral indices — no commodities, FX, crypto, "
              "F&O or foreign markets. Within that I can show:",
              [("Index performance", "best performing sectoral index this month"),
               ("Today's movers", "biggest movers today"),
               ("RS leaders", "RS leaders")]),
}


def ood_clarify(kind: str) -> dict:
    msg, opts = _OOD_MSG.get(kind, _OOD_MSG["advisory"])
    return {"flow": "clarify", "reason": "boundary", "question": msg,
            "chips": [{"label": l, "href": _href(q)} for l, q in opts]}


# ── degraded deterministic fallback (ONLY when the model is unavailable) ───────
# Reuses the heuristics from disambiguate; this is a safety net for a Gemini
# outage/quota, explicitly NOT the primary reasoning path.
def parse_fallback(query: str) -> dict | None:
    """Best-effort structured intent from rules alone. None if nothing confident."""
    try:
        qn = _norm(query)
        from src.pat import disambiguate as D

        # OOD guardrails FIRST (advisory / prediction / feature / non-equity asset)
        ood = _detect_ood(qn)
        if ood:
            return {"task": "ood", "kind": ood}

        # single-stock card — BEFORE the explain "what's" catch, since "what's wrong
        # with X" must resolve to the stock, not a glossary definition.
        for lead in ("tell me about ", "what's wrong with ", "whats wrong with ",
                     "pull up ", "red flags in "):
            if qn.startswith(lead):
                tok = query.strip()[len(lead):].strip(" ?.")
                tok = tok.split(" a value trap")[0].split(" looking")[0].split(" being")[0].strip()
                if 0 < len(tok) <= 20 and " " not in tok:
                    return {"task": "stock", "symbol": tok.upper()}

        # explain
        if D._has_any(qn, D.SYNONYMS["explain"]):
            return None      # let the glossary keyword search handle definitions

        # kill-list / pt14 — special framework screens (checked before metric)
        if D._has_any(qn, ["avoid", "red-flag", "red flag", "kill-list", "kill list",
                           "disqualif", "stocks to stay away", "reject"]):
            return {"task": "rank", "universe": "stock", "rank": {"metric": "avoid"},
                    "filters": [], "scope": {}, "character": None, "confidence": 55}
        if D._has_any(qn, ["pt14", "pt 14", "tier-1", "tier 1", "t1 ", "quality gate",
                           "14 pattern", "14-pattern"]):
            return {"task": "rank", "universe": "stock", "rank": {"metric": "pt14"},
                    "filters": [], "scope": {}, "character": None, "confidence": 55}

        # momentum oscillators (RSI / MACD) → the `oscillators` flow
        osc = None
        if _has_any(qn, ["oversold"]) or ("rsi" in qn and _has_any(qn, ["below 30", "under 30", "<30", "< 30", "less than 30"])):
            osc = "rsi_oversold"
        elif _has_any(qn, ["overbought"]) or ("rsi" in qn and _has_any(qn, ["above 70", "over 70", ">70", "> 70", "more than 70"])):
            osc = "rsi_overbought"
        elif "macd" in qn:
            if _has_any(qn, ["bearish", "bear cross", "cross down", "sell signal"]):
                osc = "macd_bear"
            elif _has_any(qn, ["positive", "above signal", "above the signal", "above its signal"]):
                osc = "macd_positive"
            else:
                osc = "macd_bull"     # default: the bullish crossover (most-asked)
        if osc:
            return {"task": "rank", "universe": "stock", "rank": {}, "filters": [],
                    "scope": {}, "character": None, "indicator": osc, "confidence": 55}

        universe = "stock"
        if D._has_any(qn, ["index", "indices", "sectoral", "sector rotation",
                           "which sector", "sector performance"]) \
                and not D._has_any(qn, D._CONSTITUENT):
            universe = "index"

        # strong-hand delivery character — distribution (exiting) / consolidation
        character = None
        if D._has_any(qn, ["distribut", "being dumped", "smart money exiting",
                           "strong hands selling", "topping out", "rolling over"]):
            character = "distribution"
        elif D._has_any(qn, ["consolidat", "coiling"]):
            character = "consolidation"

        # worst checked first so "top losers" (top + loser) reads as worst, not best
        order = "worst" if D._has_any(qn, ["worst", "laggard", "weakest", "underperform",
                                           "loser", "beaten", "fallen", "bottom", "decline"]) \
            else ("best" if D._has_any(qn, ["best", "top ", "strongest", "leader", "leading",
                                            "gainer"]) else None)

        window = None
        if D._has_any(qn, ["1 year", "one year", "12 month", "12m", "1y", "last year",
                           "past year", "this year", "annual", "52 week", "52-week"]):
            window = "1y"
        elif D._has_any(qn, ["6 month", "6m", "half year"]):
            window = "6m"
        elif D._has_any(qn, ["3 month", "3m", "quarter"]):
            window = "3m"
        elif D._has_any(qn, ["1 month", "one month", "past month", "last month",
                             "this month", "1m", "monthly"]):
            window = "1m"
        elif D._has_any(qn, ["today", "intraday", "this week", "1 week", "1w"]):
            window = "1w" if "week" in qn or "1w" in qn else "1d"

        # metric
        cs = D._concepts(qn)
        if D._has_any(qn, ["overvalued", "over-valued", "expensive", "frothy", "bubble"]):
            metric = "valuation"     # expensive end → compiler maps worst-valuation to "rich"
            order = "worst"
        elif universe == "index":
            metric = "return"
        elif character:
            metric = "delivery"      # distribution/consolidation ride the delivery flow
        elif "movers" in cs or D._has_any(qn, ["today", "intraday", "gainer", "loser", "moved"]):
            metric = "price_move"
        elif "fundamentals" in cs:
            metric = "valuation" if D._has_any(qn, ["valuation", "cheap", "p/e", "pe ratio", "undervalued", "expensive", "overvalued"]) \
                else ("growth" if "growth" in qn else "quality")
        elif "accumulation" in cs:
            metric = "delivery"
        elif "rs" in cs:
            metric = "rs"
        elif order is not None:
            metric = "rs"            # "strongest/weakest stocks" → RS is the proxy
        else:
            metric = None

        filters = []
        if D._has_any(qn, ["turning", "turn around", "turnaround", "started performing better",
                           "performing better", "perform better", "recover", "reversal",
                           "reversing", "bottoming", "bottomed", "picking up", "started rising",
                           "improving", "coming back", "uptick"]):
            filters.append({"metric": "return", "window": "1m", "op": "improving"})

        rank = {}
        if metric:
            rank["metric"] = metric
        if window:
            rank["window"] = window
        if order:
            rank["order"] = order
        if not rank and not filters and not character:
            return None
        return {"task": "rank", "universe": universe, "rank": rank,
                "filters": filters, "scope": {}, "character": character, "confidence": 55}
    except Exception:
        return None
