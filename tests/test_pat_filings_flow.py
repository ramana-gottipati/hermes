"""test_pat_filings_flow.py — contracts for the per-symbol Ownership & filings flow (S150).

Guards the recognizer (filings cue + symbol-anchored; does NOT steal participants / news /
rotation), the four bounded reads, and the engine.route wiring. The Pat eval battery is left
UNCHANGED (a separate suite) — this is additive coverage, proof the new flow steals nothing.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import filings_flow as FF        # noqa: E402
from src.pat import engine as ENGINE          # noqa: E402


# ── recognition ───────────────────────────────────────────────────────────────────────
def test_recognizes_filings_asks_with_a_symbol():
    assert FF.parse_filings("filings for TCS")["params"] == {"symbol": "TCS", "focus": "all"}
    assert FF.parse_filings("insider activity in RELIANCE")["params"]["focus"] == "insider"
    assert FF.parse_filings("any pledge on INFY")["params"]["focus"] == "sast"
    assert FF.parse_filings("credit rating of HDFCBANK")["params"] == {"symbol": "HDFCBANK", "focus": "ratings"}
    assert FF.parse_filings("shareholding of WIPRO")["params"]["focus"] == "shp"
    assert FF.parse_filings("who holds ITC")["params"]["symbol"] == "ITC"


def test_yields_without_a_symbol_or_cue():
    assert FF.parse_filings("insider activity") is None          # market-wide → not us
    assert FF.parse_filings("any pledge disclosures") is None
    assert FF.parse_filings("are FIIs buying") is None           # market FII stance
    assert FF.parse_filings("TCS news") is None                  # no filings cue
    assert FF.parse_filings("what phase is TCS in") is None
    assert FF.parse_filings("") is None


# ── engine.route wiring: filings claims per-symbol, steals nothing market-wide ──────────
def test_engine_routes_filings_and_does_not_steal_neighbours():
    assert ENGINE.route("filings for TCS") == {"flow": "filings", "params": {"symbol": "TCS", "focus": "all"}}
    assert ENGINE.route("credit rating of INFY")["flow"] == "filings"
    # neighbours keep their asks
    assert ENGINE.route("are FIIs buying")["flow"] == "participants"
    assert ENGINE.route("TCS news")["flow"] == "news"
    assert ENGINE.route("what phase is TCS in")["flow"] == "rotation"


# ── bounded reads ───────────────────────────────────────────────────────────────────
def _hermes_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE insider_events(symbol TEXT, disclosure_dt TEXT, category TEXT, "
              "txn_class TEXT, signal_class TEXT, value_rs REAL, mode TEXT, amendment_flag INT)")
    c.executemany("INSERT INTO insider_events VALUES (?,?,?,?,?,?,?,?)", [
        ("TCS", "2026-07-10", "Promoter", "OPEN_MARKET_BUY", "conviction", 5.2e7, "Market", 0),
        ("TCS", "2026-06-01", "KMP", "OPEN_MARKET_SELL", "caution", 1.1e7, "Market", 0),
        ("TCS", "2026-05-01", "Promoter", "PLEDGE_CREATE", "pledge_risk", 0, "Off Market", 1)])
    c.execute("CREATE TABLE credit_rating_events(symbol TEXT, broadcast_dt TEXT, rating_date TEXT, "
              "agency TEXT, action_class TEXT, rating_raw TEXT, rating_earlier_raw TEXT, "
              "outlook TEXT, notch_delta INT)")
    c.execute("INSERT INTO credit_rating_events VALUES "
              "('TCS','2026-07-05',NULL,'CRISIL','UPGRADE','AAA','AA+','Stable',1)")
    return c


def test_insider_and_ratings_reads():
    c = _hermes_conn()
    ins = FF.insider_recent(c, "TCS")
    assert len(ins) == 2, "amended filing excluded"
    assert ins[0]["signal"] == "conviction" and ins[0]["value_rs"] == 5.2e7
    rat = FF.ratings_recent(c, "TCS")
    assert rat and rat[0]["action"] == "UPGRADE" and rat[0]["prior"] == "AA+"
    c.close()


def test_reads_degrade_to_empty_on_absent_tables_and_symbols():
    c = _hermes_conn()
    assert FF.insider_recent(c, "NOSUCH") == []
    assert FF.sast_summary(c, "TCS") is None            # no sast_pledge_events table
    b = FF.filings_for(c, "TCS")
    assert FF.has_any(b) and b["insider"] and b["ratings"]
    assert not FF.has_any(FF.filings_for(c, "NOSUCH"))
    # holdings opens research.db read-only; absent/gap → None, never crashes
    assert FF.holdings_latest("NOSUCH") is None or isinstance(FF.holdings_latest("NOSUCH"), dict)
    c.close()


def test_selftest_passes():
    assert FF._selftest() == 0
