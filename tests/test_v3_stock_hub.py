"""test_v3_stock_hub.py — the M4 landing gate (spec §7/§8, increment 1).

Covers: route + nav-contract assertions · digest/checks/sections contracts · URL-state
discipline (`?sym=`, `?section=` preservation; `?symbol=` never) · ONE related block ≤5 ·
payload budget (UNCOMPRESSED initial HTML bytes < 1,000,000 — Codex A5 semantics) · no v3
leak to legacy · narrative fence discipline. Chart-fork assertions (seams · `?cmp=` ·
series CSV) land with increment 2 (`stock_chart_v3.py`), tracked in the spec.

Data-independence: tests must pass on a bare dev DB — a symbol WITH data exercises the full
path when available; the no-data path is always exercised via a synthetic symbol.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient


def _app():
    from src.main import app
    return app


def _any_symbol_with_bar() -> str | None:
    try:
        from src.core.db import get_conn
        with get_conn() as conn:
            r = conn.execute("SELECT symbol FROM bhavcopy_rows WHERE series='EQ' "
                             "ORDER BY trade_date DESC LIMIT 1").fetchone()
            return str(r[0]) if r else None
    except Exception:
        return None


# ── route + nav contract (requirement #0) ─────────────────────────────────────────────

def test_hub_route_serves_and_carries_the_nav_contract():
    client = TestClient(_app())
    r = client.get("/dash/preview/stock", params={"sym": "ZZNOSUCHZZ"})
    assert r.status_code == 200
    body = r.text.split("</head>", 1)[1]
    assert '<nav class="pv3-dests"' in body                 # the 6-destination bar
    assert 'aria-current="page">Stocks' in body             # you-are-here
    assert '<nav class="pv3-crumbs"' in body                # canonical breadcrumb
    assert '<nav class="pv3-navrail"' in body               # Stocks rail, visible by default
    assert "pv3Nav()" in r.text and "pv3-navshow" in r.text  # user-invoked collapse + restore
    assert body.index('pv3-dests') < body.index('pv3-crumbs')


def test_hub_dest_bar_has_exactly_six_fixed_destinations():
    from src.web.shell_v3 import DESTS
    assert [k for k, _ in DESTS] == ["today", "markets", "stocks", "strategies", "tracker", "proof"]


def test_hub_unknown_symbol_recovers_never_dead_ends():
    client = TestClient(_app())
    r = client.get("/dash/preview/stock", params={"sym": "ZZNOSUCHZZ"})
    assert r.status_code == 200 and "Symbol not found" in r.text
    assert "screener" in r.text.lower()                     # a way forward is offered


def test_hub_no_sym_renders_picker():
    client = TestClient(_app())
    r = client.get("/dash/preview/stock")
    assert r.status_code == 200 and "Pick a stock" in r.text


# ── the evidence-scroll contracts ─────────────────────────────────────────────────────

def test_hub_full_page_contracts_on_real_symbol():
    sym = _any_symbol_with_bar()
    if not sym:
        return  # bare clone — the synthetic-path tests above still hold the contract
    client = TestClient(_app())
    r = client.get("/dash/preview/stock", params={"sym": sym})
    assert r.status_code == 200
    t = r.text
    assert 'class="hub-idx"' in t                           # sticky section index
    assert 'data-sec="chart"' in t and 'data-sec="pos"' in t  # default-open sections
    assert "of 6 pillars" in t                              # confluence checks-as-UI
    assert "Open section" in t                              # collapsed sections expandable
    assert "?symbol=" not in t                              # the P0-1 bug class stays dead
    assert 'section=all' in t                               # open-everything affordance
    assert "pv3-dock" in t and "sym=" + sym in t            # M3 dock, symbol-filtered
    # payload budget: UNCOMPRESSED initial document bytes (Codex A5 semantics)
    assert len(r.content) < 1_000_000, len(r.content)


def test_hub_section_param_expands_and_preserves_sym():
    sym = _any_symbol_with_bar()
    if not sym:
        return
    client = TestClient(_app())
    r = client.get("/dash/preview/stock", params={"sym": sym, "section": "qual"})
    assert r.status_code == 200
    # qual now open (its checks render), and expansion links still carry the symbol
    assert "Quality gates" in r.text or "No pt14 score" in r.text
    assert "sym=" + sym + "&section=" in r.text.replace("&amp;", "&")


def test_hub_related_block_is_single_and_capped():
    sym = _any_symbol_with_bar()
    if not sym:
        return
    client = TestClient(_app())
    t = client.get("/dash/preview/stock", params={"sym": sym}).text
    assert t.count(">Related<") == 1
    related_tail = t.split(">Related<", 1)[1].split("</div>", 2)[-2]
    assert related_tail.count("pv3-ev") <= 5


def test_hub_checks_use_real_thresholds():
    from src.automation.scoring import QG_THRESHOLD, QG_MAX, UNVERIFIED_MULTIPLIER
    from src.web import hub_sections_v3 as H
    core = {"sym": "T", "pt": {"qg_pass": 1, "hard_disqualified": 0,
                               "disqualifier_reasons": None}, "ca": None}
    out = H.checks_pt14(core)
    assert format(QG_THRESHOLD, ".1f") in out and str(QG_MAX) in out
    assert format(UNVERIFIED_MULTIPLIER, ".2f") in out


def test_hub_narrative_is_descriptive_only():
    from src.web import hub_sections_v3 as H
    core = {"sym": "T",
            "sig": {"trigger_rank": "SS", "rs_rank": 91, "p_score": 5},
            "mep": {"mep_state_smooth": "STRONG_ACCUM"},
            "pt": {"tier": "A"}, "cci": {"tier": "A+"}}
    n = H.narrative(core).lower()
    assert n and "top trigger band" in n
    for verb in ("buy", "sell", "avoid", "ride", "fade"):
        assert re.search(r"\b" + verb + r"\b", n) is None, verb


# ── isolation holds with the new module mounted ───────────────────────────────────────

def test_legacy_pages_still_carry_no_hub_markers():
    client = TestClient(_app())
    for path in ("/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert "hub-idx" not in r.text and "/dash/preview/stock" not in r.text, path
