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
# avoid = the hard-disqualifier kill-list (the framework's own "reject" verdict);
# structure = a bullish CPR structure read (a pillar for the multi-condition planner).
METRICS = {"return", "rs", "delivery", "valuation", "quality", "growth", "price_move",
           "pt14", "avoid", "credibility", "structure"}
WINDOWS = {"1d", "1w", "1m", "3m", "6m", "1y"}
ORDERS = {"best", "worst"}
OPS = {">", "<", ">=", "<=", "improving", "declining"}
# the strong-hand delivery CHARACTER (accumulation flow); distribution = exiting.
CHARACTERS = {"accumulation", "distribution", "consolidation"}
# market-cap bands (the multi-condition planner's universe scope) — from index
# membership (Smallcap 250 / Midcap 150 / Nifty 50 ∪ Next 50), not the sparse cap col.
CAPBANDS = {"small", "mid", "large"}
# strategy_registry keys askable as a strategy-board read ("what's the MEP/CPR/Wolfe
# strategy showing", "strategist overview"). 'all' = the whole board.
STRATEGY_KEYS = {"all", "mep", "dvpt", "rs", "cpr", "cci", "wolfe", "conviction",
                 "growth", "launchpad"}
# the metrics a "why is X …?" explanation can drill into (each maps to evidence rows).
WHY_METRICS = {"credibility", "accumulation", "rs", "valuation", "quality"}
TASKS = {"rank", "explain", "stock", "strategy", "compare", "why", "trend"}
# momentum-oscillator screens (the `oscillators` flow). Keys mirror OSC_SCREEN.
INDICATORS = {"rsi_oversold", "rsi_overbought", "macd_bull", "macd_bear", "macd_positive"}

_WS = re.compile(r"\s+")


def _norm(q: str) -> str:
    return _WS.sub(" ", (q or "").strip().lower())


def _has_any(q: str, phrases) -> bool:
    return any(p in q for p in phrases)


# Strip "what does X mean" / "what is X" / "explain X" filler so the glossary
# resolves the TERM, not the whole question. (Bug: find("what does RS rank mean")
# ranked Delivery % over RS rank because the filler words dominated the match.)
_EXPLAIN_LEAD = re.compile(
    r"^\s*(?:can you\s+)?(?:please\s+)?"
    r"(?:what\s+does|what\s+do|what\s+is|what\s+are|what'?s|whats|explain|define|"
    r"definition\s+of|meaning\s+of|tell\s+me\s+about|describe|the\s+meaning\s+of)\s+",
    re.I)
_EXPLAIN_TAIL = re.compile(
    r"\s+(?:mean|means|meaning|definition|defined|stand\s+for|stands\s+for|"
    r"metric|indicator|signify|signifies)\s*$", re.I)


def strip_explain_filler(q: str) -> str:
    t = (q or "").strip().rstrip(" ?.").strip()
    t = _EXPLAIN_LEAD.sub("", t)
    t = _EXPLAIN_TAIL.sub("", t)
    return t.strip(" ?.").strip()


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
    if task == "strategy":           # a strategy-registry board read ("what's MEP showing")
        key = str(obj.get("strategy") or obj.get("key") or "all").strip().lower()
        return {"task": "strategy", "strategy": key if key in STRATEGY_KEYS else "all"}
    if task == "compare":            # A-vs-B ("compare INFY and TCS")
        syms = obj.get("symbols")
        if not isinstance(syms, list):
            syms = [obj.get("a"), obj.get("b")]
        syms = [str(s).strip().upper() for s in syms if s and str(s).strip()]
        return {"task": "compare", "symbols": syms[:3]} if len(syms) >= 2 else None
    if task == "why":                # explanation ("why is INFY credible?")
        sym = obj.get("symbol") or obj.get("ticker")
        metric = obj.get("metric")
        if sym and str(sym).strip():
            return {"task": "why", "symbol": str(sym).strip().upper(),
                    "metric": metric if metric in WHY_METRICS else "credibility"}
        return None
    if task == "trend":              # credibility time-series ("credibility trend for X")
        sym = obj.get("symbol") or obj.get("ticker")
        return {"task": "trend", "symbol": str(sym).strip().upper()} if sym and str(sym).strip() else None
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

    # MEMBERSHIP pillars — a filter that names a strategy family as a PRESENCE condition
    # ("…with credible management", "…that are RS-leading") carries no comparison op (the
    # model often emits only {metric} or {metric,order}). Keep these metric-only so the
    # multi-condition planner sees the co-present pillar and INTERSECTS it (the QA-round2
    # #5 bug was these filters being dropped because an op in OPS was required, collapsing
    # a two-pillar refine to a single-pillar board). A comparison op is still honoured when
    # present (and required for the value-bearing numeric metrics, where a bare presence is
    # meaningless).
    _MEMBERSHIP_METRICS = {"credibility", "rs", "return", "delivery", "structure"}
    filters = []
    raw_filters = obj.get("filters")
    if isinstance(raw_filters, list):
        for f in raw_filters[:6]:
            if not isinstance(f, dict):
                continue
            fm, fw, fo = f.get("metric"), f.get("window"), f.get("op")
            if fm not in METRICS:
                continue
            if fo in OPS:
                ff = {"metric": fm, "op": fo}
            elif fm in _MEMBERSHIP_METRICS:
                ff = {"metric": fm}          # presence pillar — no comparison op needed
            else:
                continue                     # numeric metric with no valid op → drop
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
    cb = raw_scope.get("capband")
    if isinstance(cb, str) and cb.strip().lower() in CAPBANDS:
        scope["capband"] = cb.strip().lower()

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
            # CL-PAT-06: "getting better recently" = an upward op over a short window
            # with NO positive threshold yet (value unspecified, or a numeric value <= 0).
            # Test value explicitly: `is None` for missing, and a real number <= 0 — never
            # `value in (0, None)`, which also swallowed a boolean False (False == 0).
            v = f.get("value")
            v_is_nonpos = v is None or (
                isinstance(v, (int, float)) and not isinstance(v, bool) and v <= 0)
            if f.get("op") in (">", ">=") and f.get("window") in ("1m", "1w") and v_is_nonpos:
                return True
    return False


# ── multi-condition PLANNER pillar extraction ─────────────────────────────────
# Collect the strategy PILLARS a stock-universe intent names, collapsing the
# fundamentals sub-metrics (valuation/quality/growth) into ONE family so a plain
# "cheap quality compounder" still routes to the single fundamentals flow (no
# regression) — the planner only fires when the ask spans ≥2 DIFFERENT families
# (e.g. credible × accumulating × RS-leading), which no single flow can serve.
def _plan_pillars(rank, filters, character):
    metrics = set()
    if rank.get("metric"):
        metrics.add(rank["metric"])
    for f in (filters or []):
        if f.get("metric"):
            metrics.add(f["metric"])
    pillars: list[str] = []
    families: set[str] = set()
    if "credibility" in metrics:
        pillars.append("credibility"); families.add("cci")
    if character == "distribution":
        pillars.append("distribution"); families.add("mep")
    elif character == "accumulation" or "delivery" in metrics:
        pillars.append("accumulation"); families.add("mep")
    if "rs" in metrics or "return" in metrics:
        pillars.append("rs"); families.add("rs")
    if "valuation" in metrics:
        pillars.append("value"); families.add("fund")
    if "quality" in metrics:
        pillars.append("quality"); families.add("fund")
    if "structure" in metrics:
        pillars.append("structure"); families.add("cpr")
    return pillars, families


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
        raw = (intent.get("explain") or "").strip()
        if not raw:
            return None
        # the parser sometimes hands back the whole question; strip the filler so the
        # glossary matches the TERM ("what does RS rank mean" → "RS rank" → rs_rank).
        term = strip_explain_filler(raw) or raw
        try:
            from src.pat.glossary import GLOSSARY, find
            for cand in (term, raw):
                if cand in GLOSSARY:
                    return {"flow": "explain", "explain": cand}
            # an EXACT term/alias match beats fuzzy find() — stops "all-time-high
            # DVPT" collapsing to the generic "dvpt" on a substring match.
            tl = term.strip().lower()
            for slug, e in GLOSSARY.items():
                names = [e["term"].lower()] + [a.lower() for a in e.get("aliases", [])]
                if tl in names:
                    return {"flow": "explain", "explain": slug}
            hits = find(term, limit=1)          # resolve "DVPT"/"delivery" → real slug
            if hits:
                return {"flow": "explain", "explain": hits[0][0]}
        except Exception:
            pass
        return None

    if intent.get("task") == "stock":     # single-symbol snapshot / red-flag card
        sym = (intent.get("symbol") or "").strip()
        return {"flow": "card", "params": {"sym": sym}} if sym else None

    if intent.get("task") == "strategy":  # a strategy_registry board read (any strategy)
        key = (intent.get("strategy") or "all").strip().lower()
        return {"flow": "strategy", "params": {"key": key if key in STRATEGY_KEYS else "all"}}

    if intent.get("task") == "compare":   # A-vs-B side-by-side
        syms = [s for s in (intent.get("symbols") or []) if s]
        return {"flow": "compare", "params": {"syms": ",".join(syms[:3])}} if len(syms) >= 2 else None

    if intent.get("task") == "why":       # explain the evidence behind a read
        sym = (intent.get("symbol") or "").strip()
        metric = intent.get("metric") if intent.get("metric") in WHY_METRICS else "credibility"
        return {"flow": "why", "params": {"sym": sym, "metric": metric}} if sym else None

    if intent.get("task") == "trend":     # credibility time-series for one name
        sym = (intent.get("symbol") or "").strip()
        return {"flow": "trend", "params": {"sym": sym}} if sym else None

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
    top_n = rank.get("top_n")
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
            return _compile_stock(metric, window, order, filters, scope, turning, character, top_n)
        params: dict = {}
        iw = _index_window(window)
        if iw:
            params["window"] = iw
        if order == "worst":
            params["direction"] = "laggards"
        if turning:
            params["turning"] = "turn"
        return {"flow": "index", "params": params}

    # ── MULTI-CONDITION PLANNER (stock universe) — ≥2 strategy FAMILIES ────────
    # "credible + accumulating + RS-leading small-caps" spans families no single
    # flow serves → intersect them. The dedicated credibility×accumulation view
    # (with its dual-lens as-of badge) still wins for EXACTLY that pair with no
    # extra scope; everything else routes to the general planner.
    pillars, families = _plan_pillars(rank, filters, character)
    sector = scope.get("sector", "") if isinstance(scope, dict) else ""
    capband = scope.get("capband", "") if isinstance(scope, dict) else ""
    # Planner when ≥2 families span flows no single flow serves, OR a single pillar is
    # scoped to a cap-band (the single flows have a `sector` param but no cap-band, so
    # "RS leaders small-caps" must intersect rs_rank ∩ small-cap membership via the planner).
    if len(families) >= 2 or (families and capband):
        if set(pillars) == {"credibility", "accumulation"} and not sector and not capband:
            return {"flow": "confluence", "params": {}}
        return {"flow": "confluence_plan",
                "params": {"pillars": ",".join(pillars), "sector": sector, "capband": capband}}

    # ── STOCK universe (single flow) ──────────────────────────────────────────
    return _compile_stock(metric, window, order, filters, scope, turning, character, top_n)


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


def _compile_stock(metric, window, order, filters, scope, turning, character=None,
                   top_n=None) -> dict | None:
    sector = scope.get("sector", "") if isinstance(scope, dict) else ""
    # explicit "top N" → carried only on the ranked LIST flows (credibility/rs/
    # accumulation); a single-name/explain flow ignores it (no list to cap).

    def _tn(p: dict) -> dict:
        if top_n:
            p = dict(p)
            p["top_n"] = int(top_n)
        return p

    # Special framework screens (no metric ranking): the kill-list + the pt14 tiers.
    if metric == "avoid":
        return {"flow": "disqualified", "params": {}}
    if metric == "pt14":
        return {"flow": "pt14", "params": {}}

    # Management CREDIBILITY (CCI) — the DESCRIPTIVE concall track-record lens (a
    # measurable kept-promise / guidance-falsifiability read, veto-excluded; NOT a
    # ranked buy signal — the §C backtest found no return edge). Parameterless flows:
    # the leaders board, or the deterioration / avoid tape for the worst side.
    if metric == "credibility":
        # credibility × accumulation CONFLUENCE — when the ask pairs credibility with
        # the accumulation character, both lenses must agree (the §9.8 "one fusion").
        if character == "accumulation":
            return {"flow": "confluence", "params": {}}
        if order == "worst":
            return {"flow": "deterioration", "params": {}}
        return {"flow": "credibility", "params": _tn({})}

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
        return {"flow": "rs", "params": _tn(params)}

    if metric == "delivery":
        params = {}
        aw = _acc_window(window)
        if aw:
            params["window"] = aw
        if sector:
            params["sector"] = sector
        return {"flow": "accumulation", "params": _tn(params)}

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
    "pt14, avoid, credibility, structure]; window ∈ [1d,1w,1m,3m,6m,1y]; order ∈ [best, worst]. "
    "Use 'structure' for a bullish CPR / reversal STRUCTURE read ('bullish structure', "
    "'CPR bull-U', 'reversal setup', 'coiled and breaking out'). "
    "'worst/laggard/weakest/underperform' = worst; 'best/top/strongest/leaders' = best. "
    "Use 'pt14' for the 14-pattern quality TIER ('pt14', 'Tier-1', 'T1 names', 'passes "
    "the quality gate') — distinct from 'quality' (ROCE/valuation). Use 'avoid' for the "
    "hard-disqualifier KILL-LIST ('stocks to avoid', 'red-flag stocks', 'what did "
    "Patearn reject', 'disqualified names').\n"
    "  Use 'credibility' for MANAGEMENT CREDIBILITY from earnings concalls — 'most "
    "credible managements', 'promise-keepers', 'guidance accuracy', 'trustworthy "
    "management', 'best concall track record', 'managements that deliver on guidance'; "
    "order 'worst' (or 'deteriorating credibility', 'broken promises', 'walked-back "
    "guidance', 'managements to avoid', 'credibility decay') selects the deterioration/"
    "avoid tape. It is a DESCRIPTIVE track-record lens, not a buy ranking. Pair credibility "
    "with character 'accumulation' for the credibility×accumulation CONFLUENCE — names that "
    "are BOTH credible AND being accumulated ('credible companies being accumulated', "
    "'strong-hand buying in credible names').\n"
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
    "  MULTI-CONDITION: when the analyst names SEVERAL conditions at once ('credible "
    "AND being accumulated AND RS-leading small-caps'), put the PRIMARY one in rank "
    "and EACH additional one as its own filter (and set character for accumulation/"
    "distribution). Don't collapse — every condition must appear so the planner can "
    "intersect them. Set scope.capband ∈ [small, mid, large] for 'small-cap'/'midcap'/"
    "'largecap'/'bluechip'.\n"
    "  STRATEGY BOARD: 'what is the MEP/CPR/Wolfe strategy showing', 'strategist "
    "overview', 'what are all the strategies showing' → {\"task\":\"strategy\","
    "\"strategy\":\"<mep|dvpt|rs|cpr|cci|wolfe|conviction|all>\"} (use 'all' for the whole board).\n"
    "  COMPARE: 'compare INFY and TCS', 'INFY vs TCS', 'X versus Y' → "
    "{\"task\":\"compare\",\"symbols\":[\"INFY\",\"TCS\"]}.\n"
    "  WHY / EXPLAIN-A-READ: 'why is INFY credible', 'what makes TCS a leader', 'why is X "
    "being accumulated', 'why is X cheap/expensive' → {\"task\":\"why\",\"symbol\":\"<TICKER>\","
    "\"metric\":\"<credibility|accumulation|rs|valuation|quality>\"} (drills into the evidence "
    "+ provenance behind that read; default metric credibility). Distinct from 'tell me about X' "
    "(the whole card) and 'what is RS' (a definition).\n"
    "  CREDIBILITY TREND (time-series): 'credibility trend for X', 'how has X's credibility "
    "moved over time', 'X credibility over the quarters', 'credibility history of X' → "
    "{\"task\":\"trend\",\"symbol\":\"<TICKER>\"} (a PIT level/momentum/trend SERIES over the "
    "concall periods — distinct from the single-period 'why is X credible' evidence drill).\n"
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
    "'stocks to avoid' → {\"task\":\"rank\",\"universe\":\"stock\",\"rank\":{\"metric\":\"avoid\"},\"confidence\":90}\n"
    "'most credible managements' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"credibility","order":"best"},"confidence":90}\n'
    "'managements with deteriorating credibility' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"credibility","order":"worst"},"confidence":88}\n'
    "'credible companies being accumulated' / 'strong-hand buying in credible names' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"credibility"},"character":"accumulation","confidence":88}\n'
    "'credible, being accumulated, RS-leading small-caps' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"credibility"},"character":"accumulation",'
    '"filters":[{"metric":"rs","op":">="}],"scope":{"capband":"small"},"confidence":90}\n'
    "'quality compounders being accumulated' → "
    '{"task":"rank","universe":"stock","rank":{"metric":"quality"},"character":"accumulation","confidence":88}\n'
    "'what is the CPR strategy showing' → {\"task\":\"strategy\",\"strategy\":\"cpr\"}\n"
    "'strategist overview' / 'what are all the strategies showing' → {\"task\":\"strategy\",\"strategy\":\"all\"}\n"
    "'compare INFY and TCS' → {\"task\":\"compare\",\"symbols\":[\"INFY\",\"TCS\"]}\n"
    "'why is HDFCBANK credible' → {\"task\":\"why\",\"symbol\":\"HDFCBANK\",\"metric\":\"credibility\"}\n"
    "'what makes TITAN a market leader' → {\"task\":\"why\",\"symbol\":\"TITAN\",\"metric\":\"rs\"}"
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


# ── deterministic keyword sets for the planner / strategy / compare fallbacks ──
_CB_SMALL = ["small cap", "small-cap", "smallcap", "small caps", "small-caps"]
_CB_MID = ["mid cap", "mid-cap", "midcap", "mid caps", "midcaps"]
_CB_LARGE = ["large cap", "large-cap", "largecap", "large caps", "blue chip", "bluechip", "blue-chip"]
_PIL_CRED = ["credib", "promise-keep", "promise keep", "kept promise", "trustworthy management",
             "guidance accuracy", "concall track"]
_PIL_ACCUM = ["accumulat", "being accumulated", "being bought", "strong hand", "strong-hand",
              "smart money", "smart-money", "strong-hand buying"]
_PIL_RS = ["rs-leading", "rs leading", "relative strength", "rs leader", "leading the market",
           "outperform", "market leader", "momentum leader", "high rs", "rs rank"]
_PIL_VALUE = ["cheap", "undervalued", "low pe", "low p/e", "reasonably valued", "reasonable valuation",
              "good value", "value stock"]
_PIL_QUALITY = ["high quality", "quality compan", "quality compound", "compounder", "high roce",
                "high roe", "great business"]
_PIL_STRUCT = ["bullish structure", "bull-u", "bull u", "cpr ", "reversal setup", "coiled",
               "breaking out of"]
# strategy-board phrasings → a strategy_registry key (the gap: CPR + Wolfe + overview)
_STRAT_BOARD = ["strategist", "all strategies", "every strategy", "strategy board",
                "strategy dashboard", "what are the strategies", "overview of strategies"]
_STRAT_KEY_KW = [
    ("cpr", ["cpr strategy", "structure strategy", "cpr setups", "cpr screen"]),
    ("wolfe", ["wolfe strategy", "wolfe scan", "wolfe setups", "wolfe wave", "wolfe"]),
    ("mep", ["mep strategy", "accumulation strategy", "mep board"]),
    ("rs", ["rs strategy", "strength strategy"]),
    ("cci", ["cci strategy", "credibility strategy"]),
    ("dvpt", ["dvpt strategy", "delivery strategy", "positioning strategy"]),
    ("conviction", ["conviction strategy", "conviction board"]),
]
_CMP_RE = re.compile(
    r"^\s*(?:compare|contrast)\s+([a-z0-9&.\-]{1,18})\s+(?:and|vs\.?|versus|with|to|against)\s+([a-z0-9&.\-]{1,18})",
    re.I)
_VS_RE = re.compile(
    r"^\s*([a-z0-9&.\-]{1,18})\s+(?:vs\.?|versus)\s+([a-z0-9&.\-]{1,18})\s*$", re.I)


def _detect_capband(qn: str):
    if _has_any(qn, _CB_SMALL):
        return "small"
    if _has_any(qn, _CB_MID):
        return "mid"
    if _has_any(qn, _CB_LARGE):
        return "large"
    return None


def detect_compare(query: str):
    """Two tickers from 'compare A and B' / 'A vs B' → ['A','B'], else None. ₹0."""
    for rx in (_CMP_RE, _VS_RE):
        m = rx.search(query or "")
        if m:
            a, b = m.group(1).strip().upper(), m.group(2).strip().upper()
            stop = {"AND", "VS", "THE", "A", "AN", "TO", "OF", "IT"}
            if a and b and a != b and a not in stop and b not in stop:
                return [a, b]
    return None


def detect_strategy_key(qn: str):
    """A strategy-board ask → a strategy_registry key (or 'all'), else None. ₹0."""
    if _has_any(qn, _STRAT_BOARD):
        return "all"
    for key, kws in _STRAT_KEY_KW:
        if _has_any(qn, kws):
            return key
    return None


_WHY_RE = re.compile(
    r"(?:why\s+(?:is|are|does|do|did)|what\s+makes|how\s+come)\s+([a-z0-9&.\-]{1,18})\b", re.I)
_WHY_METRIC_KW = [
    ("credibility", ["credib", "trustworth", "promise", "guidance", "concall", "management"]),
    ("accumulation", ["accumulat", "being bought", "being accumulated", "strong hand",
                      "strong-hand", "smart money", "distribut", "delivery"]),
    ("rs", ["leader", "leading", "relative strength", "rs ", "outperform", "momentum",
            "strong", "weak", "laggard"]),
    ("valuation", ["cheap", "undervalued", "expensive", "overvalued", "value", "pe ", "p/e", "valuation"]),
    ("quality", ["quality", "roce", "roe", "compounder", "good business"]),
]


# A credibility TIME-SERIES ask: "credibility trend for X", "X credibility over time",
# "how has X's credibility moved". The credibility WORD must be present (so it doesn't
# steal a plain RS/price "trend" ask), plus a time-series cue OR the word "trend".
_TS_CUE = ["trend", "over time", "history", "historical", "trajectory", "evolv",
           "over the years", "over the quarters", "across quarters", "time series",
           "changed over", "moved over", "track record"]
_CRED_WORD = ["credib", "trustworth", "concall", "guidance accuracy", "promise-keep",
              "promise keeping"]
# X-anchored: "<TICKER> credibility trend", "credibility trend for <TICKER>", etc.
_TREND_RE = re.compile(
    r"(?:credibility|trustworthiness|concall)\s+(?:trend|history|trajectory|over\s+time|"
    r"time\s+series)\s+(?:for|of|in)?\s*([a-z0-9&.\-]{2,18})\b", re.I)
_TREND_RE2 = re.compile(
    r"\b([a-z0-9&.\-]{2,18})(?:'s|s')?\s+credibility\s+(?:trend|history|trajectory|over\s+time)",
    re.I)
_TREND_RE3 = re.compile(
    r"how\s+(?:has|did)\s+([a-z0-9&.\-]{2,18})(?:'s|s')?\s+credibility\s+"
    r"(?:trend|chang|mov|evolv|track)", re.I)
# trailing "… for/of <TICKER>" (e.g. "credibility over the quarters for ACC") — only
# fires once the credibility + time-series cues already gated detect_trend.
_TREND_RE4 = re.compile(r"\b(?:for|of)\s+([a-z0-9&.\-]{2,18})\s*$", re.I)


def detect_trend(query: str):
    """A 'credibility trend for X' time-series ask → symbol, else None. ₹0.

    Requires BOTH a credibility cue AND a time-series cue (or an explicit X-anchored
    pattern) so a plain price/RS 'trend' ask is NOT captured here."""
    q = query or ""
    qn = _norm(q)
    if not _has_any(qn, _CRED_WORD):
        return None
    if not _has_any(qn, _TS_CUE):
        return None
    stop = {"THE", "THIS", "THAT", "IT", "A", "AN", "MY", "FOR", "OF", "IN",
            "TIME", "QUARTERS", "YEARS", "PERIODS"}
    for rx in (_TREND_RE, _TREND_RE2, _TREND_RE3, _TREND_RE4):
        m = rx.search(q)
        if m:
            sym = m.group(1).strip().upper().strip(".")
            if sym and sym not in stop and not sym.isdigit():
                return sym
    return None


def detect_why(query: str):
    """A 'why is X <metric>?' explanation ask → (symbol, metric), else None. ₹0.
    The default metric is credibility (the trust-wedge read most asked 'why' about)."""
    m = _WHY_RE.search(query or "")
    if not m:
        return None
    sym = m.group(1).strip().upper()
    if not sym or sym.lower() in ("the", "this", "that", "it", "a", "an", "my"):
        return None
    qn = _norm(query)
    metric = "credibility"
    for mk, kws in _WHY_METRIC_KW:
        if _has_any(qn, kws):
            metric = mk
            break
    return sym, metric


# Single-name credibility ask WITHOUT a "why"/"trend" cue: "is X credible",
# "how credible is X", "X credibility", "confluence on X". Routes to the `why`
# flow (the single-name evidence-backed credibility read) — the right answer for
# a one-name trust question. STOP words guard against catching a bare metric ask
# ("most credible managements" — no single subject → stays the leaders board).
_SINGLE_CRED_RE = [
    re.compile(r"\bis\s+([a-z0-9&.\-]{2,18})(?:'s)?\s+(?:a\s+)?(?:credible|trustworthy)\b", re.I),
    re.compile(r"\bhow\s+credible\s+is\s+([a-z0-9&.\-]{2,18})\b", re.I),
    re.compile(r"\bcredibility\s+(?:of|for)\s+([a-z0-9&.\-]{2,18})\b", re.I),
    re.compile(r"\b([a-z0-9&.\-]{2,18})(?:'s)?\s+credibility\b", re.I),
    re.compile(r"\bconfluence\s+(?:on|for|of)\s+([a-z0-9&.\-]{2,18})\b", re.I),
    re.compile(r"\bcan\s+i\s+trust\s+([a-z0-9&.\-]{2,18})(?:'s)?\s+management\b", re.I),
]
_SINGLE_CRED_STOP = {"THE", "THIS", "THAT", "IT", "A", "AN", "MY", "ITS", "THEIR",
                     "MANAGEMENT", "MANAGEMENTS", "COMPANY", "COMPANIES", "PROMOTER",
                     "PROMOTERS", "BUSINESS", "BUSINESSES", "NAME", "NAMES", "STOCK",
                     "STOCKS", "MOST", "ALL", "ANY", "WHICH", "WHAT", "SOME",
                     # verbs/fillers that precede "credibility" in a DEFINITION ask
                     "IS", "ARE", "DOES", "DO", "DID", "EXPLAIN", "DEFINE", "MEAN",
                     "MEANS", "WHATS", "HOW", "WHY", "GOOD", "HIGH", "LOW", "BEST",
                     "WORST", "MORE", "LESS", "VERY", "AND", "OR", "OF", "FOR", "IN",
                     "WITH", "ABOUT", "GET", "SHOW", "FIND", "MANAGEMENTS",
                     # DIRECTION qualifiers — "deteriorating/improving/weakening
                     # credibility" is a BOARD filter (the whole list moving that way),
                     # NOT a single name. Without these, "X credibility" captured the
                     # adjective as a ticker (→ a dead-end why{sym:DETERIORATING}); the
                     # qualifier hits a stop here so route_extra falls through to the
                     # deterioration / credibility board route instead.
                     "DETERIORATING", "DETERIORATED", "DETERIORATION", "IMPROVING",
                     "IMPROVED", "WEAKENING", "WEAKENED", "WEAK", "DECLINING",
                     "DECLINED", "FALLING", "RISING", "STRENGTHENING", "WORSENING",
                     "WANING", "SLIPPING", "ERODING", "DECAYING", "DECAY", "GROWING",
                     "INCREASING", "DECREASING", "POOR", "STRONG", "STRONGER", "WEAKER"}


# Explicit "top N" cap: "top 5 X", "top-10 X", "5 most credible", "best 3 …".
# N only caps the list to the N strongest ALREADY-RANKED rows (ranking unchanged);
# a bare "top stocks" (no number) leaves it unset → the safety cap applies as before.
_TOPN_RE = [
    re.compile(r"\btop[\s\-]*(\d{1,3})\b", re.I),
    re.compile(r"\b(\d{1,3})\s+(?:most|best|strongest|top|highest|weakest|worst)\b", re.I),
    re.compile(r"\b(?:best|top|strongest|highest)[\s\-]*(\d{1,3})\b", re.I),
]


def detect_top_n(query: str):
    """An explicit 'top N' count in the query → int N (1..200), else None. ₹0."""
    q = query or ""
    for rx in _TOPN_RE:
        m = rx.search(q)
        if m:
            try:
                n = int(m.group(1))
            except (TypeError, ValueError):
                continue
            if 1 <= n <= 200:
                return n
    return None


def detect_single_credibility(query: str):
    """A single-name credibility question → symbol, else None. ₹0.

    The credibility WORD must anchor it; a bare plural metric ask ('credible
    managements') hits a stop-word, not a symbol, so it correctly stays the
    leaders board rather than collapsing to one name."""
    q = query or ""
    qn = _norm(q)
    # don't steal an explicit trend/why ask — those have their own (richer) flows.
    if detect_trend(q) or detect_why(q):
        return None
    # don't steal a DEFINITION ask ("what is credibility", "explain credibility")
    # — that's the glossary explain flow, not a single-name read.
    from src.pat import disambiguate as _D
    if _D._has_any(qn, _D.SYNONYMS["explain"]) or qn.strip().startswith(("what is ", "what does ",
                                                                          "whats ", "define ")):
        return None
    for rx in _SINGLE_CRED_RE:
        m = rx.search(q)
        if m:
            sym = m.group(1).strip().upper().strip(".")
            if sym and sym not in _SINGLE_CRED_STOP and not sym.isdigit() and len(sym) >= 2:
                return sym
    return None


def _detect_pillars(qn: str, character):
    """The strategy FAMILIES a raw question names (for the degraded planner path)."""
    pillars: list[str] = []
    fam: set[str] = set()
    if _has_any(qn, _PIL_CRED):
        pillars.append("credibility"); fam.add("cci")
    if character == "accumulation" or _has_any(qn, _PIL_ACCUM):
        pillars.append("accumulation"); fam.add("mep")
    if _has_any(qn, _PIL_RS):
        pillars.append("rs"); fam.add("rs")
    if _has_any(qn, _PIL_VALUE):
        pillars.append("value"); fam.add("fund")
    if _has_any(qn, _PIL_QUALITY):
        pillars.append("quality"); fam.add("fund")
    if _has_any(qn, _PIL_STRUCT):
        pillars.append("structure"); fam.add("cpr")
    return pillars, fam


# ── degraded deterministic fallback (ONLY when the model is unavailable) ───────
# Reuses the heuristics from disambiguate; this is a safety net for a Gemini
# outage/quota, explicitly NOT the primary reasoning path.
def parse_fallback(query: str) -> dict | None:
    """Best-effort structured intent from rules alone (+ an explicit top-N stamp on
    the rank). None if nothing confident."""
    intent = _parse_fallback_inner(query)
    # stamp an explicit "top N" onto a ranked intent so BOTH the direct compile path
    # (eval) and the engine path cap the list consistently. Ranking is unchanged.
    if isinstance(intent, dict) and isinstance(intent.get("rank"), dict) \
            and not intent["rank"].get("top_n"):
        n = detect_top_n(query)
        if n:
            intent = dict(intent)
            intent["rank"] = dict(intent["rank"], top_n=n)
    return intent


def _parse_fallback_inner(query: str) -> dict | None:
    """Best-effort structured intent from rules alone. None if nothing confident."""
    try:
        qn = _norm(query)
        from src.pat import disambiguate as D

        # OOD guardrails FIRST (advisory / prediction / feature / non-equity asset)
        ood = _detect_ood(qn)
        if ood:
            return {"task": "ood", "kind": ood}

        # TREND (credibility time-series) — "credibility trend for X" — checked before
        # WHY so the series drill wins over the single-period evidence drill.
        tr = detect_trend(query)
        if tr:
            return {"task": "trend", "symbol": tr}

        # WHY (explanation) — "why is X credible?" — checked before single-stock/compare
        # so the explanation drill wins over a bare card.
        wy = detect_why(query)
        if wy:
            return {"task": "why", "symbol": wy[0], "metric": wy[1]}

        # SINGLE-NAME CREDIBILITY ("is X credible", "confluence on X", "X credibility")
        # → the why flow's single-name evidence read. Checked after why/trend (which
        # have richer drills) and before compare/single-stock so a one-name trust
        # question lands on the evidence, not a bare card.
        sc = detect_single_credibility(query)
        if sc:
            return {"task": "why", "symbol": sc, "metric": "credibility"}

        # COMPARE (A vs B) — distinctive shape; checked before the single-stock catch.
        cmp_syms = detect_compare(query)
        if cmp_syms:
            return {"task": "compare", "symbols": cmp_syms}

        # STRATEGY BOARD ('CPR/Wolfe strategy', 'strategist overview') — a registry read.
        skey = detect_strategy_key(qn)
        if skey:
            return {"task": "strategy", "strategy": skey}

        # single-stock card — BEFORE the explain "what's" catch, since "what's wrong
        # with X" must resolve to the stock, not a glossary definition.
        for lead in ("tell me about ", "what's wrong with ", "whats wrong with ",
                     "pull up ", "red flags in "):
            if qn.startswith(lead):
                tok = query.strip()[len(lead):].strip(" ?.")
                tok = tok.split(" a value trap")[0].split(" looking")[0].split(" being")[0].strip()
                if 0 < len(tok) <= 20 and " " not in tok:
                    return {"task": "stock", "symbol": tok.upper()}

        # explain → extract the TERM and route to explain (passing the raw question
        # to the glossary search mis-ranks on filler words: "what does RS rank mean").
        # Triggers on a leading "what is/explain/define …" OR a trailing "… meaning".
        if D._has_any(qn, D.SYNONYMS["explain"]) or _EXPLAIN_TAIL.search(qn):
            term = strip_explain_filler(query)
            if term and len(term) <= 45:
                return {"task": "explain", "explain": term}
            return None

        # kill-list / pt14 — special framework screens (checked before metric)
        if D._has_any(qn, ["avoid", "red-flag", "red flag", "kill-list", "kill list",
                           "disqualif", "stocks to stay away", "reject"]):
            return {"task": "rank", "universe": "stock", "rank": {"metric": "avoid"},
                    "filters": [], "scope": {}, "character": None, "confidence": 55}
        if D._has_any(qn, ["pt14", "pt 14", "tier-1", "tier 1", "t1 ", "quality gate",
                           "14 pattern", "14-pattern"]):
            return {"task": "rank", "universe": "stock", "rank": {"metric": "pt14"},
                    "filters": [], "scope": {}, "character": None, "confidence": 55}

        # MULTI-CONDITION PLANNER (degraded path) — when ≥2 strategy FAMILIES are
        # named, emit a fully-populated intent (primary metric + extra filters +
        # character + cap-band) so compile_intent intersects them. Runs BEFORE the
        # single-pillar credibility/metric blocks (which return early on one family).
        _cb = _detect_capband(qn)
        _char = ("distribution" if D._has_any(qn, ["distribut", "being dumped", "topping out"])
                 else ("accumulation" if D._has_any(qn, _PIL_ACCUM) else None))
        _pillars, _fam = _detect_pillars(qn, _char)
        if len(_fam) >= 2 or (_fam and _cb):
            # primary metric = the strongest single signal; the rest become filters.
            order = "credibility" if "credibility" in _pillars else \
                    ("rs" if "rs" in _pillars else
                     ("valuation" if "value" in _pillars else
                      ("quality" if "quality" in _pillars else
                       ("structure" if "structure" in _pillars else None))))
            rank = {"metric": order} if order else {}
            fmap = {"rs": ("rs", ">="), "value": ("valuation", "<"),
                    "quality": ("quality", ">"), "structure": ("structure", ">"),
                    "credibility": ("credibility", ">=")}
            filters = []
            for p in _pillars:
                if p in ("accumulation", "distribution"):
                    continue
                fm = fmap.get(p)
                if fm and fm[0] != order:
                    filters.append({"metric": fm[0], "op": fm[1]})
            scope = {"capband": _cb} if _cb else {}
            return {"task": "rank", "universe": "stock", "rank": rank, "filters": filters,
                    "scope": scope, "character": _char, "confidence": 55}

        # management CREDIBILITY (CCI concall track-record) — a descriptive lens; the
        # worst / "managements to avoid" side routes to the deterioration tape.
        if D._has_any(qn, ["credibilit", "credible management", "credible compan",
                           "credible name", "credible stock", "credible busines",
                           "credible promoter", "promise-keep", "promise keep",
                           "kept promise", "kept its promise", "guidance accuracy",
                           "trustworthy management", "management trust", "concall track record",
                           "delivers on guidance", "deliver on guidance", "walked back",
                           "walked-back", "broken promise"]):
            cred_order = "worst" if D._has_any(qn, ["deteriorat", "broken promise", "walked back",
                                                    "walked-back", "least credible", "avoid",
                                                    "decay", "untrustworthy"]) else "best"
            # credibility × accumulation confluence when both lenses are named
            cred_char = "accumulation" if D._has_any(qn, ["accumulat", "being bought",
                        "being accumulated", "strong hand", "strong-hand", "smart money",
                        "smart-money"]) else None
            return {"task": "rank", "universe": "stock", "rank": {"metric": "credibility", "order": cred_order},
                    "filters": [], "scope": {}, "character": cred_char, "confidence": 55}

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
            # LAST RESORT (nothing screened): a bare glossary term/alias typed alone
            # ("VWAP", "primary sector", "CPR compression") → explain it. Runs only
            # here so screen queries ("RS leaders") win over a glossary-alias match.
            try:
                from src.pat.glossary import GLOSSARY
                for slug, e in GLOSSARY.items():
                    cands = [e["term"]] + list(e.get("aliases") or [])
                    pool = {c.lower() for c in cands}
                    pool |= {re.sub(r"\s*\(.*?\)", "", c).strip().lower() for c in cands}
                    if qn in pool:
                        return {"task": "explain", "explain": slug}
            except Exception:
                pass
            return None
        return {"task": "rank", "universe": universe, "rank": rank,
                "filters": filters, "scope": {}, "character": character, "confidence": 55}
    except Exception:
        return None
