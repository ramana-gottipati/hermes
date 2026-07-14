"""S-E Phase 2 slice B (UX audit §8) — the Pat DATA flows: `participants` + `rotation`.

Pat now answers "are FIIs buying" (market FII net stance) and "what phase is TCS in"
(a stock's RS-rotation state) inline. These tests pin recognition, symbol extraction,
the bounded reads, the renders, and — the risk of two more broad recognizers — that they
steal no existing work and don't collide with the S142/S144 flows.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.pat import participants_flow as PF
from src.pat import rotation_flow as RF


def _route(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    return route(q)


# ── module selftests ──────────────────────────────────────────────────────────────
def test_participants_selftest():
    assert PF._selftest() == 0


def test_rotation_selftest():
    assert RF._selftest() == 0


# ── recognition ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("q", [
    "are FIIs buying", "FII flows", "FII positioning", "who's positioned",
    "who is positioned", "foreign flows", "DII vs FII", "institutional flows",
])
def test_participants_recognition(q):
    r = PF.parse_participants(q)
    assert r and r["flow"] == "participants", (q, r)


@pytest.mark.parametrize("q,sym", [
    ("what phase is TCS in", "TCS"),
    ("rotation state of INFY", "INFY"),
    ("is RELIANCE leading or lagging", "RELIANCE"),
    ("which quadrant is HDFCBANK in", "HDFCBANK"),
])
def test_rotation_recognition(q, sym):
    r = RF.parse_rotation(q)
    assert r and r["flow"] == "rotation" and r["params"]["symbol"] == sym, (q, r)


@pytest.mark.parametrize("q", ["rotation", "what's the rotation", "RS leaders",
                               "leading stocks", "TCS news", ""])
def test_rotation_yields_without_symbol_or_cue(q):
    assert RF.parse_rotation(q) is None


# ── routing through the REAL engine ───────────────────────────────────────────────
@pytest.mark.parametrize("q,flow", [
    ("are FIIs buying", "participants"),
    ("FII flows", "participants"),
    ("what phase is TCS in", "rotation"),
    ("is RELIANCE leading or lagging", "rotation"),
])
def test_flows_route(q, flow):
    sel = _route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


# ── the REGRESSION guard: steal nothing; page-finds still win ─────────────────────
@pytest.mark.parametrize("q,flow", [
    ("where do I see FII flows", "navigate"),   # page-find stays navigate (nav runs first)
    ("where do I see rotation", "navigate"),
    ("RS leaders", "explain"),                  # glossary term (pre-existing) — not rotation
    ("which stocks are accumulating", "accumulation"),
    ("biggest movers today", "movers"),
    ("TCS news", "news"),
])
def test_no_collision(q, flow):
    sel = _route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


# ── bounded reads + renders ────────────────────────────────────────────────────────
@pytest.fixture()
def db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE participant_oi(trade_date TEXT, client_type TEXT, "
              "fut_idx_long INTEGER, fut_idx_short INTEGER)")
    c.executemany("INSERT INTO participant_oi VALUES (?,?,?,?)",
                  [(f"2026-06-{i+1:02d}", "FII", 800 + i * 30, 1000) for i in range(30)]
                  + [(f"2026-06-{i+1:02d}", "CLIENT", 1000, 900) for i in range(30)])
    c.execute("CREATE TABLE stock_signals(symbol TEXT, rs_phase TEXT, rs_rank INTEGER, "
              "rs_vs_broad_trend_state TEXT, trade_date TEXT)")
    c.executemany("INSERT INTO stock_signals VALUES (?,?,?,?,?)", [
        ("TCS", "NEUTRAL", 40, "CONSOLIDATING", "2026-07-10"),
        ("TCS", "HEADWIND", 3, "DOWNTREND", "2026-07-14")])
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.execute("INSERT INTO security_master VALUES ('TCS')")
    yield c
    c.close()


def test_fii_stance_read(db):
    st = PF.fii_stance(db)
    assert st and st["as_of"] == "2026-06-30"
    assert st["ratio"] > 1.1 and st["pct"] >= 88          # latest = the peak → top percentile
    assert PF.fii_stance(None) is None


def test_participants_render(db):
    from src.pat.web import _participants_flow
    h = _participants_flow(db)
    assert ("net-LONG" in h or "net-long" in h) and "/dash/participants" in h and "D62" in h


def test_phase_read(db):
    p = RF.phase_for(db, "TCS")
    assert p["phase"] == "HEADWIND" and p["rank"] == 3 and "lagging" in p["read"]
    assert p["as_of"] == "2026-07-14"                     # newest row with a phase
    assert RF.phase_for(db, "UNKNOWN") is None


def test_rotation_render(db):
    from src.pat.web import _rotation_flow
    h = _rotation_flow(db, "TCS")
    assert "Headwind" in h and "lagging" in h and "sym=TCS" in h and "never a buy/sell" in h
    h2 = _rotation_flow(db, "ZZZZ")                       # unknown ticker
    assert "recognise" in h2 or "ticker" in h2
