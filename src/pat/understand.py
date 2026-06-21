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
METRICS = {"return", "rs", "delivery", "valuation", "quality", "growth", "price_move"}
WINDOWS = {"1d", "1w", "1m", "3m", "6m", "1y"}
ORDERS = {"best", "worst"}
OPS = {">", "<", ">=", "<=", "improving", "declining"}

_WS = re.compile(r"\s+")


def _norm(q: str) -> str:
    return _WS.sub(" ", (q or "").strip().lower())


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

    conf = obj.get("confidence")
    try:
        conf = int(conf)
    except (TypeError, ValueError):
        conf = None

    if not rank and not filters and not scope:
        # nothing actionable parsed
        return None
    return {"task": task if task in ("rank", "explain") else "rank",
            "universe": universe, "rank": rank, "filters": filters,
            "scope": scope, "confidence": conf}


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

    universe = intent.get("universe", "stock")
    rank = intent.get("rank") or {}
    filters = intent.get("filters") or []
    scope = intent.get("scope") or {}
    metric = rank.get("metric")
    window = rank.get("window")
    order = rank.get("order")
    turning = _filters_improving_1m(filters)

    # ── INDEX / SECTOR universe → the index-performance flow ──────────────────
    # (sector-performance questions are index questions: the sector's index.)
    if universe in ("index", "sector"):
        # If they want stock-level facts ABOUT a sector (delivery/valuation/quality),
        # that's a stock screen scoped to the sector, not an index-performance pull.
        if metric in ("delivery", "valuation", "quality", "growth") and universe == "sector":
            return _compile_stock(metric, window, order, filters, scope, turning)
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
    return _compile_stock(metric, window, order, filters, scope, turning)


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


def _compile_stock(metric, window, order, filters, scope, turning) -> dict | None:
    sector = scope.get("sector", "") if isinstance(scope, dict) else ""

    if metric == "price_move":
        params = {}
        mw = _movers_window(window)
        if mw:
            params["window"] = mw
        if order == "worst":
            params["direction"] = "losers"
        return {"flow": "movers", "params": params}

    if metric in ("rs", "return"):
        # "return" at the STOCK level has no absolute-return screen; relative
        # strength (RS) is the performance proxy. Worst-side has no stock screen —
        # be honest and redirect rather than dump leaders (the original bug).
        if order == "worst":
            return _clarify(
                "unsupported",
                "I don't have a worst-performing-STOCKS screen yet. Did you mean the "
                "worst-performing INDICES, or RS leaders (the strong stocks)?",
                [{"label": "Worst-performing indices", "href": "/dash/pat?flow=index&strength=laggards&entry=1y"},
                 {"label": "RS leaders (strong stocks)", "href": "/dash/pat?flow=rs"}],
            )
        params = {}
        rw = _rs_window(window)
        if rw:
            params["window"] = rw
        if sector:
            params["sector"] = sector
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
    "order. metric ∈ [return, rs, delivery, valuation, quality, growth, price_move]; "
    "window ∈ [1d,1w,1m,3m,6m,1y]; order ∈ [best, worst]. 'worst/laggard/weakest' = "
    "worst; 'best/top/strongest/leaders' = best.\n"
    "  STEP 3 — FILTERS: every ADDITIONAL condition, each as its own {metric,window,"
    "op,value}. op ∈ [>,<,>=,<=,improving,declining]. A phrase like 'started "
    "performing better in the last month' / 'turning up' / 'recovering' is a filter "
    "{metric:return, window:1m, op:improving}. This list is how a TWO-WINDOW ask "
    "('worst over 1Y AND improving over 1M') is captured — never collapse it to one.\n"
    "Also set scope.sector or scope.index when named, and a 0-100 confidence.\n"
    "For a 'what is X' / 'define' question, reply {\"task\":\"explain\",\"explain\":\"<term>\"}.\n"
    "Reply with COMPACT JSON ONLY, no prose:\n"
    '{"task":"rank","universe":"stock|index|sector",'
    '"rank":{"metric":..,"window":..,"order":..},'
    '"filters":[{"metric":..,"window":..,"op":..,"value":..}],'
    '"scope":{"sector":..,"index":..},"confidence":0-100}\n'
    "WORKED EXAMPLE — 'worst performing index in the last one year that started "
    "performing better in the past month':\n"
    '{"task":"rank","universe":"index","rank":{"metric":"return","window":"1y","order":"worst"},'
    '"filters":[{"metric":"return","window":"1m","op":"improving"}],"scope":{},"confidence":95}'
)


# ── degraded deterministic fallback (ONLY when the model is unavailable) ───────
# Reuses the heuristics from disambiguate; this is a safety net for a Gemini
# outage/quota, explicitly NOT the primary reasoning path.
def parse_fallback(query: str) -> dict | None:
    """Best-effort structured intent from rules alone. None if nothing confident."""
    try:
        qn = _norm(query)
        from src.pat import disambiguate as D

        # explain
        if D._has_any(qn, D.SYNONYMS["explain"]):
            return None      # let the glossary keyword search handle definitions

        universe = "stock"
        if D._has_any(qn, ["index", "indices", "sectoral", "sector rotation",
                           "which sector", "sector performance"]) \
                and not D._has_any(qn, D._CONSTITUENT):
            universe = "index"

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
        if universe == "index":
            metric = "return"
        elif "movers" in cs or D._has_any(qn, ["today", "intraday", "gainer", "loser", "moved"]):
            metric = "price_move"
        elif "fundamentals" in cs:
            metric = "valuation" if D._has_any(qn, ["valuation", "cheap", "p/e", "pe ratio", "undervalued"]) \
                else ("growth" if "growth" in qn else "quality")
        elif "accumulation" in cs:
            metric = "delivery"
        elif "rs" in cs:
            metric = "rs"
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
        if not rank and not filters:
            return None
        return {"task": "rank", "universe": universe, "rank": rank,
                "filters": filters, "scope": {}, "confidence": 55}
    except Exception:
        return None
