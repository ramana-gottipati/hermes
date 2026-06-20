"""Pat routing — the gold evaluation set + a runner.

The thing Pat was missing: a way to MEASURE whether it understands a query, and a
regression net so a fix for one shape doesn't silently break another. Two layers:

  1. COMPILER eval (``run_compiler_eval``) — hand-authored structured intents →
     expected flow/params. Pure, deterministic, ₹0: it verifies the *logical
     mapping* (the reasoning core in understand.compile_intent) WITHOUT any model.
     Run it on every change.

  2. ROUTE eval (``run_route_eval``) — real analyst questions → expected route.
     Runs each query through a parser then the compiler. The "fallback" parser is
     deterministic/₹0 (degraded mode); the "live" parser is the real Gemini parse
     (run when quota allows). This is the end-to-end "are first answers right?" score.

These cases are also the seed of the labeled dataset for the eventual OWNED model
(§4.4.2) — query → structured intent → route.

Run:  python -m src.pat.eval_set        (compiler eval + fallback route eval)
"""

from __future__ import annotations

from src.pat.understand import compile_intent, parse_fallback


# ── 1) compiler cases — structured intent → expected selection (the reasoning) ─
# Each: (label, intent, expect). expect.flow + expect.params (subset) must match;
# flow "clarify" matches any clarify (optionally its reason).
INTENT_CASES = [
    ("index: worst 1Y + turning 1M  (the original miss)",
     {"universe": "index", "rank": {"metric": "return", "window": "1y", "order": "worst"},
      "filters": [{"metric": "return", "window": "1m", "op": "improving"}], "confidence": 95},
     {"flow": "index", "params": {"direction": "laggards", "window": "1y", "turning": "turn"}}),

    ("index: best this month",
     {"universe": "index", "rank": {"metric": "return", "window": "1m", "order": "best"}},
     {"flow": "index", "params": {"window": "1m"}}),

    ("index: best 3M (default window has no key)",
     {"universe": "index", "rank": {"metric": "return", "window": "3m", "order": "best"}},
     {"flow": "index", "params": {}}),

    ("sector performance → index flow",
     {"universe": "sector", "rank": {"metric": "return", "window": "3m", "order": "best"}},
     {"flow": "index", "params": {}}),

    ("sector + delivery → stock accumulation scoped",
     {"universe": "sector", "rank": {"metric": "delivery"}, "scope": {"sector": "IT"}},
     {"flow": "accumulation", "params": {"sector": "IT"}}),

    ("stock: RS leaders",
     {"universe": "stock", "rank": {"metric": "rs", "window": "3m", "order": "best"}},
     {"flow": "rs", "params": {}}),

    ("stock: RS 1M in a sector",
     {"universe": "stock", "rank": {"metric": "rs", "window": "1m", "order": "best"}, "scope": {"sector": "IT"}},
     {"flow": "rs", "params": {"window": "1m", "sector": "IT"}}),

    ("stock: WORST return → honest unsupported clarify (the bug, inverted)",
     {"universe": "stock", "rank": {"metric": "return", "window": "1y", "order": "worst"}},
     {"flow": "clarify", "reason": "unsupported"}),

    ("stock: delivery → accumulation",
     {"universe": "stock", "rank": {"metric": "delivery", "window": "1m"}},
     {"flow": "accumulation", "params": {"window": "1m"}}),

    ("stock: valuation → fundamentals",
     {"universe": "stock", "rank": {"metric": "valuation"}},
     {"flow": "fundamentals", "params": {}}),

    ("stock: price move worst this week → movers losers 1w",
     {"universe": "stock", "rank": {"metric": "price_move", "window": "1w", "order": "worst"}},
     {"flow": "movers", "params": {"window": "1w", "direction": "losers"}}),

    ("stock: no metric → ask (don't guess)",
     {"universe": "stock", "rank": {"order": "best"}},
     {"flow": "clarify", "reason": "intent"}),

    ("explain a metric",
     {"task": "explain", "explain": "p_score"},
     {"flow": "explain", "explain": "p_score"}),
]


# ── 2) route cases — real questions → expected route (end-to-end) ──────────────
# live_only cases need the Gemini parse (the deterministic fallback can't infer
# them); they are skipped/counted separately in fallback mode.
ROUTE_CASES = [
    ("worst performing index in the last one year and started performing better from past one month",
     {"flow": "index", "params": {"direction": "laggards", "window": "1y", "turning": "turn"}}, False),
    ("best performing sectoral index this month",
     {"flow": "index", "params": {"window": "1m"}}, False),
    ("which sectors are leading over 3 months",
     {"flow": "index", "params": {}}, False),
    ("worst performing indices over the last year",
     {"flow": "index", "params": {"direction": "laggards", "window": "1y"}}, False),
    ("stocks being accumulated now",
     {"flow": "accumulation", "params": {}}, False),
    ("biggest movers today",
     {"flow": "movers", "params": {}}, False),
    ("top losers this week",
     {"flow": "movers", "params": {"window": "1w", "direction": "losers"}}, False),
    ("strong stocks",
     {"flow": "clarify"}, False),               # quota-proof deterministic clarify (engine.check)
    ("RS leaders in IT",
     {"flow": "rs"}, True),                      # sector extraction needs the live parse
    ("cheap stocks with ROCE above 20",
     {"flow": "fundamentals"}, True),
    ("what is p_score",
     {"flow": "explain", "explain": "p_score"}, True),
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
    """Deterministic ₹0 check of the reasoning core (compile_intent)."""
    fails = []
    for label, intent, expect in INTENT_CASES:
        sel = compile_intent(intent)
        if not _match(sel, expect):
            fails.append({"label": label, "expect": expect, "got": sel})
    return {"total": len(INTENT_CASES), "passed": len(INTENT_CASES) - len(fails), "fails": fails}


def run_route_eval(parser: str = "fallback") -> dict:
    """End-to-end query → route. parser='fallback' (₹0) or 'live' (Gemini)."""
    fails, skipped = [], 0
    ran = 0
    for query, expect, live_only in ROUTE_CASES:
        if live_only and parser != "live":
            skipped += 1
            continue
        ran += 1
        if parser == "live":
            from src.pat.engine import route, _CACHE
            _CACHE.pop(query.strip().lower(), None)
            sel = route(query)
        else:
            intent = parse_fallback(query)
            sel = compile_intent(intent) if intent else None
            # the engine's quota-proof clarify is part of the real fallback path:
            if sel is None:
                try:
                    from src.pat.disambiguate import check
                    sel = check(query)
                except Exception:
                    sel = None
        if not _match(sel, expect):
            fails.append({"query": query, "expect": expect, "got": sel})
    return {"parser": parser, "ran": ran, "skipped": skipped,
            "passed": ran - len(fails), "fails": fails}


if __name__ == "__main__":
    c = run_compiler_eval()
    print(f"COMPILER eval: {c['passed']}/{c['total']} passed")
    for f in c["fails"]:
        print(f"  FAIL {f['label']}\n       expect={f['expect']} got={f['got']}")
    r = run_route_eval("fallback")
    print(f"ROUTE eval (fallback): {r['passed']}/{r['ran']} passed ({r['skipped']} live-only skipped)")
    for f in r["fails"]:
        print(f"  FAIL {f['query']!r}\n       expect={f['expect']} got={f['got']}")
