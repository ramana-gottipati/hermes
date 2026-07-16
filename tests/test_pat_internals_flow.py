"""S-E Phase 2 slice C (UX audit §8) — the Pat `internals` (market-breadth) flow.

Pat now answers "how's the breadth / market internals" inline. These tests pin
recognition, the bounded read, the render, and — the risk of another broad recognizer
— that it steals nothing and doesn't collide with the S142/S144/S146 flows.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.pat import internals_flow as IF


def _route(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    return route(q)


def test_selftest():
    assert IF._selftest() == 0


# ── recognition ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("q", [
    "how's the breadth", "market breadth", "market internals", "internals",
    "advance decline", "adv dec", "how many stocks are up", "how broad is the market",
    "how's the tape", "market health",
])
def test_recognition(q):
    r = IF.parse_internals(q)
    assert r and r["flow"] == "internals", (q, r)


@pytest.mark.parametrize("q", [
    "which stocks are advancing",     # entity ranking = a screen, not this market read
    "biggest movers today",
    "are FIIs buying",
    "",
])
def test_yields_off_topic(q):
    assert IF.parse_internals(q) is None


# ── routing through the REAL engine + no-collision guard ──────────────────────────
def test_routes_to_internals():
    assert _route("how's the breadth").get("flow") == "internals"
    assert _route("market internals").get("flow") == "internals"


@pytest.mark.parametrize("q,flow", [
    ("where do I see breadth", "navigate"),   # page-find stays navigate (nav runs first)
    ("biggest movers today", "movers"),
    ("are FIIs buying", "participants"),
    ("what phase is TCS in", "rotation"),
])
def test_no_collision(q, flow):
    sel = _route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


# ── bounded read + render ──────────────────────────────────────────────────────────
@pytest.fixture()
def db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE market_internals_daily(d TEXT, n_eq INT, adv INT, dec INT, unch INT, "
              "pct_adv REAL, mep_net REAL, disp REAL, avg_comp REAL)")
    rows = [(f"2026-05-{i+1:02d}", 2000, 900, 1100, 0, 45.0 + i * 0.7, -10 + i * 0.5, 2.0, 1.0)
            for i in range(40)]
    rows.append(("2026-07-10", 2370, 1758, 592, 20, 74.18, 16.92, 2.263, 0.9448))  # latest = high
    c.executemany("INSERT INTO market_internals_daily VALUES (?,?,?,?,?,?,?,?,?)", rows)
    yield c
    c.close()


def test_breadth_read(db):
    b = IF.breadth_now(db)
    assert b and b["as_of"] == "2026-07-10" and b["adv"] == 1758
    assert b["pct_adv"] == 74.18 and b["pct_adv_pctile"] >= 92      # latest = top of range
    assert b["mep_net"] == 16.92 and b["mep_pctile"] >= 92
    assert IF.breadth_now(None) is None


def test_render(db):
    from src.pat.web import _internals_flow
    h = _internals_flow(db)
    assert "74% of 2,370" in h and "1,758 up" in h and "592 down" in h
    assert "Effort tape" in h and "/dash/market-internals" in h and "never a buy/sell" in h


def test_render_empty_safe():
    from src.pat.web import _internals_flow
    h = _internals_flow(sqlite3.connect(":memory:"))
    assert "empty" in h.lower() or "can't read" in h.lower()
