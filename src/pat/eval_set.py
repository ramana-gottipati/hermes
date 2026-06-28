"""Pat routing — the gold evaluation set + a runner.

The thing Pat was missing: a way to MEASURE whether it understands a query. Two layers:

  1. COMPILER eval (``run_compiler_eval``) — hand-authored structured intents →
     expected flow/params. Pure, deterministic, ₹0: verifies the *reasoning core*
     (understand.compile_intent) with no model. Run on every change.

  2. ROUTE eval (``run_route_eval``) — real analyst questions → expected route,
     grouped by the catalog's five BANDS (see docs/pat-question-catalog.md). The
     "fallback" parser is ₹0 (degraded); "live" is the real Gemini parse. The
     per-band score is the honest "where do we stand" picture: LIVE/CLARIFY should
     be ~100% (right today); OOD/PARTIAL surface the prioritized remaining work.

Cases are seeded from the master catalog (Appendix A). They double as the labeled
dataset for the eventual owned model.

Run:  python -m src.pat.eval_set
"""

from __future__ import annotations

from src.pat.understand import compile_intent, parse_fallback


# ── 1) compiler cases — structured intent → expected selection (the reasoning) ─
INTENT_CASES = [
    ("index: worst 1Y + turning 1M  (the original miss)",
     {"universe": "index", "rank": {"metric": "return", "window": "1y", "order": "worst"},
      "filters": [{"metric": "return", "window": "1m", "op": "improving"}], "confidence": 95},
     {"flow": "index", "params": {"direction": "laggards", "window": "1y", "turning": "turn"}}),
    ("index: best this month",
     {"universe": "index", "rank": {"metric": "return", "window": "1m", "order": "best"}},
     {"flow": "index", "params": {"window": "1m"}}),
    ("sector performance → index flow",
     {"universe": "sector", "rank": {"metric": "return", "window": "3m", "order": "best"}},
     {"flow": "index", "params": {}}),
    ("stock: RS leaders",
     {"universe": "stock", "rank": {"metric": "rs", "window": "3m", "order": "best"}},
     {"flow": "rs", "params": {}}),
    ("stock: RS 1M in a sector",
     {"universe": "stock", "rank": {"metric": "rs", "window": "1m", "order": "best"}, "scope": {"sector": "IT"}},
     {"flow": "rs", "params": {"window": "1m", "sector": "IT"}}),
    ("stock: WORST rs/return → RS laggards (the §3.2 flip, no longer a dead-end)",
     {"universe": "stock", "rank": {"metric": "return", "window": "1y", "order": "worst"}},
     {"flow": "rs", "params": {"direction": "laggards", "window": "12m"}}),
    ("distribution → accumulation w/ character chip (§3.1)",
     {"universe": "stock", "rank": {"metric": "delivery"}, "character": "distribution",
      "scope": {"sector": "IT"}},
     {"flow": "accumulation", "params": {"character": "distribution", "sector": "IT"}}),
    ("kill-list → disqualified flow (§3.3)",
     {"universe": "stock", "rank": {"metric": "avoid"}},
     {"flow": "disqualified"}),
    ("pt14 tier screen → pt14 flow (§3.6)",
     {"universe": "stock", "rank": {"metric": "pt14"}},
     {"flow": "pt14"}),
    ("single stock → card (§3.5)",
     {"task": "stock", "symbol": "INFY"},
     {"flow": "card", "params": {"sym": "INFY"}}),
    ("stock: delivery → accumulation",
     {"universe": "stock", "rank": {"metric": "delivery", "window": "1m"}},
     {"flow": "accumulation", "params": {"window": "1m"}}),
    ("stock: price move worst this week → movers losers 1w",
     {"universe": "stock", "rank": {"metric": "price_move", "window": "1w", "order": "worst"}},
     {"flow": "movers", "params": {"window": "1w", "direction": "losers"}}),
    ("stock: no metric → ask (don't guess)",
     {"universe": "stock", "rank": {"order": "best"}},
     {"flow": "clarify", "reason": "intent"}),
    ("explain a metric",
     {"task": "explain", "explain": "p_score"},
     {"flow": "explain", "explain": "p_score"}),
    # ── fundamentals op/value (the §3.4 fix: honor the op, don't drop it) ──
    ("fundamentals: OVERVALUED (worst valuation) → rich, NOT cheap (the live bug)",
     {"universe": "stock", "rank": {"metric": "valuation", "order": "worst"}},
     {"flow": "fundamentals", "params": {"val": "rich"}}),
    ("fundamentals: PE over 80 → rich",
     {"universe": "stock", "rank": {"metric": "valuation"},
      "filters": [{"metric": "valuation", "op": ">", "value": 80}]},
     {"flow": "fundamentals", "params": {"val": "rich"}}),
    ("fundamentals: under PE 15 → deep value",
     {"universe": "stock", "rank": {"metric": "valuation"},
      "filters": [{"metric": "valuation", "op": "<", "value": 15}]},
     {"flow": "fundamentals", "params": {"val": "deep"}}),
    ("fundamentals: ROCE above 22 → elite",
     {"universe": "stock", "rank": {"metric": "quality"},
      "filters": [{"metric": "quality", "op": ">", "value": 22}]},
     {"flow": "fundamentals", "params": {"qual": "elite"}}),
    ("fundamentals: hyper growth (>25) → hyper",
     {"universe": "stock", "rank": {"metric": "growth"},
      "filters": [{"metric": "growth", "op": ">", "value": 25}]},
     {"flow": "fundamentals", "params": {"grow": "hyper"}}),
    ("fundamentals: cheap + ROCE>20 → default cheap + default quality (no regression)",
     {"universe": "stock", "rank": {"metric": "valuation", "order": "best"},
      "filters": [{"metric": "quality", "op": ">", "value": 20}]},
     {"flow": "fundamentals", "params": {"val": "", "qual": ""}}),
    ("oscillator: RSI oversold → oscillators (§4.1)",
     {"universe": "stock", "rank": {}, "indicator": "rsi_oversold"},
     {"flow": "oscillators", "params": {"screen": "rsi_oversold"}}),
    ("oscillator: MACD bullish crossover → oscillators",
     {"universe": "stock", "rank": {}, "indicator": "macd_bull"},
     {"flow": "oscillators", "params": {"screen": "macd_bull"}}),
    # ── multi-condition PLANNER (≥2 strategy families) ──
    ("planner: credible + accumulating + RS small-caps → confluence_plan",
     {"universe": "stock", "rank": {"metric": "credibility"}, "character": "accumulation",
      "filters": [{"metric": "rs", "op": ">="}], "scope": {"capband": "small"}},
     {"flow": "confluence_plan", "params": {"pillars": "credibility,accumulation,rs", "capband": "small"}}),
    ("planner: quality compounders being accumulated → confluence_plan",
     {"universe": "stock", "rank": {"metric": "quality"}, "character": "accumulation"},
     {"flow": "confluence_plan", "params": {"pillars": "accumulation,quality"}}),
    ("planner: cred+accum, NO scope → stays the dedicated confluence (no regression)",
     {"universe": "stock", "rank": {"metric": "credibility"}, "character": "accumulation"},
     {"flow": "confluence"}),
    ("planner: cred+accum WITH cap-band → confluence_plan (scope applies)",
     {"universe": "stock", "rank": {"metric": "credibility"}, "character": "accumulation",
      "scope": {"capband": "mid"}},
     {"flow": "confluence_plan", "params": {"pillars": "credibility,accumulation", "capband": "mid"}}),
    # ── strategy_registry board read (any strategy askable) ──
    ("strategy: CPR board → strategy flow",
     {"task": "strategy", "strategy": "cpr"},
     {"flow": "strategy", "params": {"key": "cpr"}}),
    ("strategy: whole board → strategy flow (all)",
     {"task": "strategy", "strategy": "all"},
     {"flow": "strategy", "params": {"key": "all"}}),
    # ── compare A vs B ──
    ("compare: A vs B → compare flow",
     {"task": "compare", "symbols": ["INFY", "TCS"]},
     {"flow": "compare", "params": {"syms": "INFY,TCS"}}),
]


# ── 2) route cases — real questions → expected route, by BAND (catalog Appendix A) ─
# band ∈ LIVE (must answer today) · CLARIFY (must ask) · OOD (must redirect) ·
# PARTIAL (flow built in flows.py, free-text dispatch pending → currently fails;
# tracks the wiring gap). Each: (query, expect, band).
ROUTE_CASES = [
    # ---- LIVE: must be served correctly today ----
    ("top losers this week", {"flow": "movers", "params": {"window": "1w", "direction": "losers"}}, "LIVE"),
    ("most active stocks today", {"flow": "movers"}, "LIVE"),
    ("biggest movers today", {"flow": "movers"}, "LIVE"),
    ("RS leaders", {"flow": "rs"}, "LIVE"),
    ("strongest stocks over the last month", {"flow": "rs", "params": {"window": "1m"}}, "LIVE"),
    ("best performing sectoral index this month", {"flow": "index", "params": {"window": "1m"}}, "LIVE"),
    ("which sectors are leading over 3 months", {"flow": "index"}, "LIVE"),
    ("worst performing index over the last year that started turning up",
     {"flow": "index", "params": {"direction": "laggards", "window": "1y", "turning": "turn"}}, "LIVE"),
    ("beaten-down indices reversing", {"flow": "index", "params": {"direction": "laggards", "turning": "turn"}}, "LIVE"),
    ("stocks being accumulated now", {"flow": "accumulation"}, "LIVE"),
    ("overvalued stocks", {"flow": "fundamentals", "params": {"val": "rich"}}, "LIVE"),
    ("most expensive stocks by PE", {"flow": "fundamentals", "params": {"val": "rich"}}, "LIVE"),
    ("cheap stocks under PE 15", {"flow": "fundamentals", "params": {"val": "deep"}}, "LIVE"),
    ("oversold stocks", {"flow": "oscillators", "params": {"screen": "rsi_oversold"}}, "LIVE"),
    ("RSI below 30", {"flow": "oscillators", "params": {"screen": "rsi_oversold"}}, "LIVE"),
    ("overbought stocks", {"flow": "oscillators", "params": {"screen": "rsi_overbought"}}, "LIVE"),
    ("MACD bullish crossover", {"flow": "oscillators", "params": {"screen": "macd_bull"}}, "LIVE"),
    # ---- CLARIFY: must ask, not guess ----
    ("strong stocks", {"flow": "clarify"}, "CLARIFY"),
    ("best stocks", {"flow": "clarify"}, "CLARIFY"),
    ("show me strength", {"flow": "clarify"}, "CLARIFY"),
    ("RS leaders recently", {"flow": "clarify", "reason": "timeframe"}, "CLARIFY"),
    ("accumulation lately", {"flow": "clarify", "reason": "timeframe"}, "CLARIFY"),
    # ---- OOD: must redirect/refuse (guardrails — Part 5; currently a GAP) ----
    ("should I buy RELIANCE", {"flow": "clarify"}, "OOD"),
    ("predict tomorrow's nifty", {"flow": "clarify"}, "OOD"),
    ("option chain for bank nifty", {"flow": "clarify"}, "OOD"),
    ("set an alert when INFY crosses 3000", {"flow": "clarify"}, "OOD"),
    ("gold price today", {"flow": "clarify"}, "OOD"),
    # ---- PARTIAL: flow exists in flows.py, free-text dispatch pending ----
    ("stocks under distribution", {"flow": "accumulation", "params": {"character": "distribution"}}, "PARTIAL"),
    ("weakest stocks in IT", {"flow": "rs", "params": {"direction": "laggards"}}, "PARTIAL"),
    ("stocks to avoid", {"flow": "disqualified"}, "PARTIAL"),
    ("top pt14 quality stocks", {"flow": "pt14"}, "PARTIAL"),
    ("what's wrong with INFY", {"flow": "card"}, "PARTIAL"),
    # ---- PLANNER: the analytics-copilot upgrade (multi-condition + strategy + compare) ----
    ("credible companies being accumulated that are RS-leading small caps",
     {"flow": "confluence_plan"}, "PLANNER"),
    ("quality compounders being accumulated", {"flow": "confluence_plan"}, "PLANNER"),
    ("credible accumulating mid caps", {"flow": "confluence_plan"}, "PLANNER"),
    ("what is the CPR strategy showing", {"flow": "strategy", "params": {"key": "cpr"}}, "PLANNER"),
    ("wolfe setups", {"flow": "strategy", "params": {"key": "wolfe"}}, "PLANNER"),
    ("strategist overview", {"flow": "strategy", "params": {"key": "all"}}, "PLANNER"),
    ("compare INFY and TCS", {"flow": "compare"}, "PLANNER"),
    ("INFY vs TCS", {"flow": "compare"}, "PLANNER"),
    # cred+accum WITHOUT scope must stay the dedicated confluence view (no regression)
    ("credible companies being accumulated", {"flow": "confluence"}, "PLANNER"),
]


def _match(sel, expect) -> bool:
    if expect.get("flow") is None:
        return sel is None
    if not sel or sel.get("flow") != expect["flow"]:
        return False
    if expect["flow"] == "clarify":
        return ("reason" not in expect) or sel.get("reason") == expect["reason"]
    if expect["flow"] == "explain":
        return sel.get("explain") == expect.get("explain")
    want = expect.get("params", {})
    have = sel.get("params", {})
    return all(have.get(k) == v for k, v in want.items())


def run_compiler_eval() -> dict:
    fails = []
    for label, intent, expect in INTENT_CASES:
        sel = compile_intent(intent)
        if not _match(sel, expect):
            fails.append({"label": label, "expect": expect, "got": sel})
    return {"total": len(INTENT_CASES), "passed": len(INTENT_CASES) - len(fails), "fails": fails}


def _route_one(query, parser):
    if parser == "live":
        from src.pat.engine import route, _CACHE
        _CACHE.pop(query.strip().lower(), None)
        return route(query)
    # Mirror engine.route's ORDER for the degraded path: the ₹0 deterministic
    # clarify runs FIRST (so "RS leaders recently" asks the timeframe), THEN the
    # rules-only parse_fallback.
    try:
        from src.pat.disambiguate import check
        clar = check(query)
    except Exception:
        clar = None
    if clar:
        return clar
    intent = parse_fallback(query)
    return compile_intent(intent) if intent else None


def run_route_eval(parser: str = "fallback") -> dict:
    """End-to-end query → route, grouped by band. parser='fallback' (₹0) or 'live'."""
    bands: dict = {}
    fails = []
    for query, expect, band in ROUTE_CASES:
        sel = _route_one(query, parser)
        ok = _match(sel, expect)
        b = bands.setdefault(band, {"passed": 0, "total": 0})
        b["total"] += 1
        b["passed"] += 1 if ok else 0
        if not ok:
            fails.append({"band": band, "query": query, "expect": expect, "got": sel})
    total = sum(b["total"] for b in bands.values())
    passed = sum(b["passed"] for b in bands.values())
    return {"parser": parser, "passed": passed, "total": total, "bands": bands, "fails": fails}


def run_catalog_eval() -> dict:
    """Route EVERY real phrasing in docs/pat-question-catalog.md (Parts 1 & 3) and
    check it lands on the expected flow. This is the comprehensive self-check — the
    answer to 'don't you review the answers if they're logical'. Deterministic floor
    (check → route_extra → parse_fallback); None-routes defer to the live model.
    Skips silently if the catalog file isn't present (e.g. on the VPS)."""
    import os
    import re as _re
    path = None
    for p in ("docs/pat-question-catalog.md",
              os.path.join(os.path.dirname(__file__), "..", "..", "docs", "pat-question-catalog.md")):
        if os.path.exists(p):
            path = p
            break
    if not path:
        return {"total": 0, "passed": 0, "by_flow": {}, "fails": [], "skipped": True}

    from src.pat.disambiguate import check, route_extra
    PART3 = {"3.1": "accumulation", "3.2": "rs", "3.3": "disqualified",
             "3.4": "fundamentals", "3.5": "card", "3.6": "pt14"}

    def route(q):
        c = check(q)
        if c:
            return c
        e = route_extra(q)
        if e:
            return e
        i = parse_fallback(q)
        return compile_intent(i) if i else None

    expected, part, cases = None, None, []
    for ln in open(path, encoding="utf-8").read().split("\n"):
        pm = _re.match(r"^## PART (\d+)", ln)
        if pm:
            part, expected = int(pm.group(1)), None
            continue
        h = _re.match(r"^### .*[—-]\s*`(\w+)`", ln)
        if h:
            expected = h.group(1)
            continue
        h3 = _re.match(r"^### (\d+\.\d+)", ln)
        if h3:
            expected = PART3.get(h3.group(1))
            continue
        if " · " in ln and part in (1, 3) and expected:
            body = _re.sub(r"^(Presets:|Free-form:)", "", _re.sub(r"\*+", "", ln)).strip()
            for ph in body.split(" · "):
                ph = _re.sub(r"_.*?_", "", _re.sub(r"\(.*?\)", "", ph)).strip(" *_·.—")
                if ph and 2 < len(ph) < 70 and not ph.startswith("the original"):
                    cases.append((ph, expected))

    by_flow: dict = {}
    fails = []
    for ph, exp in cases:
        got = (route(ph) or {}).get("flow")
        by_flow.setdefault(exp, [0, 0])[1] += 1
        if got == exp:
            by_flow[exp][0] += 1
        else:
            fails.append({"q": ph, "want": exp, "got": got})
    return {"total": len(cases), "passed": len(cases) - len(fails),
            "by_flow": by_flow, "fails": fails, "skipped": False}


def run_explain_eval() -> dict:
    """EVERY glossary term must resolve correctly from its real name + aliases via
    real 'explain' phrasings. This is the net for the class of bug that shipped
    "what does RS rank mean" → Delivery % (the question filler poisoned the match)."""
    import re as _re
    from src.pat.glossary import GLOSSARY
    fails = []
    total = 0
    for slug, e in GLOSSARY.items():
        short = _re.sub(r"\s*\(.*?\)\s*", "", e["term"]).strip()     # drop parentheticals
        probes = {short.lower()} | {a.lower() for a in (e.get("aliases") or [])[:3]}
        for probe in sorted(p for p in probes if p):
            for tmpl in ("what is {}", "what does {} mean", "explain {}"):
                total += 1
                q = tmpl.format(probe)
                intent = parse_fallback(q)
                sel = compile_intent(intent) if intent else None
                got = sel.get("explain") if sel and sel.get("flow") == "explain" else None
                if got != slug:
                    fails.append({"q": q, "want": slug, "got": got})
    return {"total": total, "passed": total - len(fails), "fails": fails}


if __name__ == "__main__":
    import sys
    c = run_compiler_eval()
    print(f"COMPILER eval: {c['passed']}/{c['total']} passed")
    for f in c["fails"]:
        print(f"  FAIL {f['label']}\n       expect={f['expect']} got={f['got']}")
    parser = sys.argv[1] if len(sys.argv) > 1 else "fallback"
    r = run_route_eval(parser)
    print(f"\nROUTE eval ({r['parser']}): {r['passed']}/{r['total']} passed")
    for band in ("LIVE", "CLARIFY", "OOD", "PARTIAL", "PLANNER"):
        if band in r["bands"]:
            b = r["bands"][band]
            print(f"  {band:8} {b['passed']}/{b['total']}")
    if r["fails"]:
        print("  failures:")
        for f in r["fails"]:
            print(f"    [{f['band']}] {f['query']!r}\n        expect={f['expect']} got={f['got']}")
    x = run_explain_eval()
    print(f"\nEXPLAIN eval (every glossary term, real phrasings): {x['passed']}/{x['total']}")
    for f in x["fails"][:20]:
        print(f"    {f['q']!r} want={f['want']} got={f['got']}")
    cat = run_catalog_eval()
    if not cat.get("skipped"):
        print(f"\nCATALOG eval (every real phrasing, deterministic floor): {cat['passed']}/{cat['total']}")
        for fl, (p, n) in sorted(cat["by_flow"].items()):
            print(f"  {fl:14} {p}/{n}")
