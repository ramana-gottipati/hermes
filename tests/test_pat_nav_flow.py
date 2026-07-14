"""S-E Phase 1 (UX audit §8) — the Pat 'navigate' flow contracts.

Pat can now answer "where do I see X?" from `lens_registry`. These tests pin:
  · the audit's named topics route to the RIGHT lens,
  · a locational ask routes to `navigate` through the real engine,
  · data / explain / entity-ranking asks are NEVER stolen by the page-finder
    (the whole risk of adding a broad recognizer),
  · every routed lens is resolvable and carries a non-empty blurb (registry-
    generated coverage — a new lens is covered the day it's registered),
  · the render produces a real link and degrades safely on nonsense.
"""
from __future__ import annotations

import pytest

from src.pat import nav_flow as NAV


def test_module_selftest():
    assert NAV._selftest() == 0


# ── resolution: the audit's named topics land on the right lens ───────────────────
@pytest.mark.parametrize("topic,key", [
    ("breadth", "market-internals"),
    ("news", "wire"),
    ("seasonality", "seasonal-tape"),
    ("replay", "replay-any-date"),
    ("what changed today", "attention"),
    ("credibility", "concalls"),
    ("glossary", "glossary"),
    ("fii flows", "participants"),
    ("wolfe", "wolfe-scan"),
    ("model portfolios", "model-portfolios"),
])
def test_named_topics_resolve(topic, key):
    hits = NAV.resolve(topic)
    assert hits and hits[0]["key"] == key, (topic, [(h["key"], h["score"]) for h in hits])


# ── recognition through the REAL engine ───────────────────────────────────────────
@pytest.mark.parametrize("q", [
    "where do I see breadth",
    "which page shows the news",
    "how do I find seasonality",
    "take me to the wolfe scanner",
    "where can I see FII flows",
    "where is the glossary",
    "which screen has seasonality",
])
def test_locational_asks_route_to_navigate(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    sel = route(q)
    assert sel and sel.get("flow") == "navigate", (q, sel)
    assert sel["params"].get("topic")


# ── the REGRESSION guard: the page-finder must not steal real work ────────────────
# The core contract of adding a broad recognizer: it must never intercept a query
# that belongs to another flow. Asserts the routed flow is neither the page-finder
# nor a dead end (a real answer still fires) — across data, explain and ranking asks.
@pytest.mark.parametrize("q", [
    "which stocks are accumulating",
    "stocks being accumulated now",
    "RS leaders",                       # → explain (glossary term) — still NOT navigate
    "biggest movers today",
    "top stocks this month",
    "which stocks are overdue for results",
    "what does DVPT mean",
    "overvalued stocks",
    "compare INFY and TCS",
    "most credible managements",
])
def test_real_work_not_stolen_by_navigate(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    sel = route(q)
    assert sel and sel.get("flow") not in (None, "navigate"), (q, sel)


# the audit's core data/event asks still route to their OWN flow end-to-end (live path)
@pytest.mark.parametrize("q,flow", [
    ("which stocks are accumulating", "accumulation"),
    ("biggest movers today", "movers"),
    ("top stocks this month", "seasonal"),
    ("which stocks are overdue for results", "overdue"),
    ("overvalued stocks", "fundamentals"),
    ("compare INFY and TCS", "compare"),
])
def test_core_data_asks_route_correctly(q, flow):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    sel = route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


@pytest.mark.parametrize("q", [
    "strong stocks in pharma",       # a scoped ranking — never a page-find
    "where are the strong stocks",   # entity ranking even with 'where' → data, not nav
    "show me today's movers",
])
def test_entity_and_scoped_asks_not_navigate(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    sel = route(q)
    assert not (sel and sel.get("flow") == "navigate"), (q, sel)


def test_parse_yields_on_nonsense_topic():
    assert NAV.parse_navigate("where do I see the zxqw nonsense lens") is None


# ── registry-generated coverage: every routed lens is reachable + described ───────
def test_every_routed_lens_resolvable_and_described():
    from src.web.lens_registry import LENSES
    for ln in LENSES:
        if not ln.route:
            continue
        assert NAV.blurb(ln), f"{ln.key} has no blurb"
        # a lens must resolve from its OWN key (the floor of registry coverage)
        hits = NAV.resolve(ln.key.replace("-", " "))
        assert any(h["key"] == ln.key for h in hits), f"{ln.key} not resolvable by its key"


# ── the render ────────────────────────────────────────────────────────────────────
def test_render_links_the_top_lens():
    from src.pat.web import _navigate_flow
    html = _navigate_flow(None, "breadth")
    assert "/dash/market-internals" in html and "Market internals" in html


def test_render_degrades_on_no_match():
    from src.pat.web import _navigate_flow
    html = _navigate_flow(None, "")
    assert "couldn't match" in html.lower() or "empty" in html.lower()
