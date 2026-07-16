"""AUD-25 — feed-liveness coverage extensions.

Pins the two additions to the data_quality battery:
  1. chk_regime_guard now refuses to emit a 200DMA verdict on a FROZEN index feed (a stale
     Nifty tape would otherwise yield a plausible-but-stale 'regime OFF/ON');
  2. chk_feed_freshness now covers the news feed (sent_news) + concall filings (concalls),
     each on its own cadence.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.automation import data_quality as dq


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


def _index_feed(newest: date, n: int = 200):
    c = _conn()
    c.execute("CREATE TABLE index_rows (index_name TEXT, trade_date TEXT, close_value REAL)")
    # n distinct descending trade_dates ending at `newest`; rising close so last >= 200DMA
    c.executemany(
        "INSERT INTO index_rows VALUES ('Nifty 50', ?, ?)",
        [((newest - timedelta(days=i)).isoformat(), 20000 + (n - i)) for i in range(n)])
    c.commit()
    return c


def test_regime_guard_flags_a_frozen_index_feed():
    stale = dq.chk_regime_guard(_index_feed(date.today() - timedelta(days=30)))
    assert stale["severity"] == dq.SEV_WARN and "regime UNKNOWN" in stale["message"]
    fresh = dq.chk_regime_guard(_index_feed(date.today()))
    assert "regime UNKNOWN" not in fresh["message"]       # a fresh feed yields a real verdict
    assert "as of" in fresh["message"]                     # the verdict is now dated


def test_regime_guard_warmup_and_absent_are_safe():
    c = _conn()
    c.execute("CREATE TABLE index_rows (index_name TEXT, trade_date TEXT, close_value REAL)")
    c.execute("INSERT INTO index_rows VALUES ('Nifty 50','2020-01-01',20000)")
    assert "warmup" in dq.chk_regime_guard(c)["message"]   # <200 rows → OK warmup, never a crash
    assert dq.chk_regime_guard(_conn())["severity"] == dq.SEV_OK   # table absent → OK


def test_feed_freshness_covers_news_and_concalls():
    c = _conn()
    c.execute("CREATE TABLE sent_news (sent_at TEXT)")
    c.execute("CREATE TABLE concalls (result_filing_dt TEXT)")
    c.execute("INSERT INTO sent_news VALUES (?)",
              ((date.today() - timedelta(days=30)).isoformat() + " 00:00:00",))   # >7d stale
    c.execute("INSERT INTO concalls VALUES (?)",
              ((date.today() - timedelta(days=200)).isoformat(),))                # >120d stale
    c.commit()
    res = dq.chk_feed_freshness(c)
    assert res["severity"] == dq.SEV_WARN
    assert "news feed" in res["message"] and "concall filings" in res["message"]


def test_feed_freshness_fresh_news_is_clean():
    c = _conn()
    c.execute("CREATE TABLE sent_news (sent_at TEXT)")
    c.execute("INSERT INTO sent_news VALUES (?)", (date.today().isoformat() + " 12:00:00",))
    c.commit()
    assert dq.chk_feed_freshness(c)["severity"] == dq.SEV_OK   # fresh + others absent → OK


def _shp(rows):
    """A research.db-shaped shareholding_history seeded with (report_date, source) rows."""
    c = _conn()
    c.execute("CREATE TABLE shareholding_history (symbol TEXT, period_end TEXT, report_date TEXT, "
              "metric TEXT, value REAL, source TEXT)")
    c.executemany("INSERT INTO shareholding_history (report_date, source) VALUES (?, ?)", rows)
    c.commit()
    return c


def test_shareholding_xbrl_freshness_warns_on_a_dead_xbrl_feed():
    old = (date.today() - timedelta(days=200)).isoformat()          # >150d since the last XBRL broadcast
    res = dq.chk_shareholding_xbrl_freshness(_shp([(old, "NSE SHP XBRL")]))
    assert res["severity"] == dq.SEV_WARN and "may be dead" in res["message"]


def test_shareholding_xbrl_freshness_ignores_forward_dated_screener_rows():
    # a Screener-era row (source NULL) with a far-FUTURE report_date must NOT read as 'fresh' — the
    # source filter is the whole point (the perpetually-fresh trap chk_feed_freshness documents).
    future = (date.today() + timedelta(days=400)).isoformat()
    res = dq.chk_shareholding_xbrl_freshness(_shp([(future, None)]))
    assert res["severity"] == dq.SEV_OK and "no XBRL-sourced" in res["message"]


def test_shareholding_xbrl_freshness_clean_when_recent_and_safe_when_absent():
    fresh = (date.today() - timedelta(days=20)).isoformat()
    assert dq.chk_shareholding_xbrl_freshness(_shp([(fresh, "NSE SHP XBRL")]))["severity"] == dq.SEV_OK
    assert dq.chk_shareholding_xbrl_freshness(None)["severity"] == dq.SEV_OK        # research.db absent → OK
    assert dq.chk_shareholding_xbrl_freshness(_conn())["severity"] == dq.SEV_OK     # table absent → OK
