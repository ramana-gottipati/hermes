"""S-E Phase 2 (UX audit §8) — the Pat DATA flows: `news` + `whatchanged`.

Pat now answers the audit's two explicit Phase-2 done-bar examples inline:
"TCS news / today's headlines" and "what changed today / for SYMBOL". These tests pin
recognition, symbol extraction, the market-vs-symbol split, the render, and — the whole
risk of adding two more broad recognizers — that they steal no existing work and don't
collide with each other or with the S142 `navigate` page-finder.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.pat import news_flow as NF
from src.pat import whatchanged_flow as WC


def _route(q):
    from src.pat.engine import route, _CACHE
    _CACHE.pop(q.strip().lower(), None)
    return route(q)


# ── module selftests ──────────────────────────────────────────────────────────────
def test_news_selftest():
    assert NF._selftest() == 0


def test_whatchanged_selftest():
    assert WC._selftest() == 0


# ── news recognition ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("q,sym", [
    ("TCS news", "TCS"),
    ("news on RELIANCE", "RELIANCE"),
    ("any updates on INFY", "INFY"),
    ("TCS news today", "TCS"),          # 'today' is recency, not market-scope
    ("latest headlines", ""),
    ("market news today", ""),
    ("FII news", ""),                   # caps stopword, not a ticker
])
def test_news_recognition(q, sym):
    r = NF.parse_news(q)
    assert r and r["flow"] == "news" and r["params"]["symbol"] == sym, (q, r)


@pytest.mark.parametrize("q", ["which stocks are accumulating", "strong stocks", ""])
def test_news_yields_without_news_word(q):
    assert NF.parse_news(q) is None


# ── whatchanged recognition ───────────────────────────────────────────────────────
@pytest.mark.parametrize("q,sym", [
    ("what changed today", ""),
    ("what's new with INFY", "INFY"),
    ("what changed for TCS", "TCS"),
    ("any alerts", ""),
    ("recent changes in the market", ""),
])
def test_whatchanged_recognition(q, sym):
    r = WC.parse_whatchanged(q)
    assert r and r["flow"] == "whatchanged" and r["params"]["symbol"] == sym, (q, r)


@pytest.mark.parametrize("q", ["biggest movers today", "TCS news", "strong stocks", ""])
def test_whatchanged_yields_off_topic(q):
    assert WC.parse_whatchanged(q) is None


# ── routing through the REAL engine (the audit done-bar examples) ─────────────────
@pytest.mark.parametrize("q,flow", [
    ("TCS news", "news"),
    ("latest headlines", "news"),
    ("news on RELIANCE", "news"),
    ("what changed today", "whatchanged"),   # was mis-routed to movers before S144
    ("what's new with TCS", "whatchanged"),
    ("any alerts", "whatchanged"),
])
def test_done_bar_examples_route(q, flow):
    sel = _route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


# ── the REGRESSION guard: the data flows steal nothing, and page-find still wins ──
@pytest.mark.parametrize("q,flow", [
    ("where do I see the news", "navigate"),   # a page-find stays a navigate (nav runs first)
    ("which stocks are accumulating", "accumulation"),
    ("biggest movers today", "movers"),
    ("RS leaders", "explain"),                 # glossary term (pre-existing) — still not news/wc
    ("overvalued stocks", "fundamentals"),
])
def test_no_collision(q, flow):
    sel = _route(q)
    assert sel and sel.get("flow") == flow, (q, sel)


# ── bounded reads + render ────────────────────────────────────────────────────────
@pytest.fixture()
def db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.executemany("INSERT INTO security_master VALUES (?)", [("TCS",), ("INFY",)])
    c.execute("CREATE TABLE sent_news(id INTEGER PRIMARY KEY, url TEXT, title TEXT, "
              "source TEXT, sent_at TEXT)")
    c.execute("INSERT INTO sent_news(url,title,source,sent_at) VALUES "
              "('https://mint.com/a','TCS Q2 profit rises 9%','Mint','2026-07-14 08:00')")
    from src.automation import signal_alerts as SA
    SA.ensure_schema(c)
    c.execute("INSERT INTO signal_alert_state(symbol,lens,event_type,from_state,to_state,"
              "magnitude,severity,valence,as_of) VALUES "
              "('TCS','mep','state','DISTRIB','STRONG_DISTRIB',1.0,'critical','risk','2026-07-14'),"
              "('INFY','rs','state','INSIDE','TOUCH_RES',1.0,'high','opportunity','2026-07-14')")
    yield c
    c.close()


def test_news_reads(db):
    assert NF.is_symbol(db, "TCS") and not NF.is_symbol(db, "ZZZZ")
    assert NF.market_news(db)[0]["title"] == "TCS Q2 profit rises 9%"
    assert NF.market_news(None) == [] and NF.symbol_news(None, "TCS") == []


def test_news_render(db):
    from src.pat.web import _news_flow
    h = _news_flow(db, "")
    assert "TCS Q2 profit" in h and "/dash/wire" in h and "never a recommendation" in h
    h2 = _news_flow(db, "ZZZZ")           # unknown ticker → market fallback with a note
    assert "as a ticker" in h2


def test_whatchanged_reads(db):
    allc = WC.changes(db)
    assert allc and allc[0]["symbol"] == "TCS"           # critical first
    tcs = WC.changes(db, "TCS")
    assert [r["symbol"] for r in tcs] == ["TCS"] and tcs[0]["to_state"] == "STRONG_DISTRIB"
    assert WC.changes(None) == []


def test_whatchanged_render(db):
    from src.pat.web import _whatchanged_flow
    h = _whatchanged_flow(db, "")
    assert "TCS" in h and "STRONG_DISTRIB" in h and "/dash/attention" in h and "not a buy/sell" in h
