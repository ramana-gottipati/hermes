"""Phase-3 backfill orchestrator: worklist tiering, the resumable progress ledger, the
throttle-stop / terminal-skip / gate-fail transitions, and the pre-window period floor.

No network: ingest() is monkeypatched with a fake that mimics its DB side-effects (writes
a gate verdict + returns a stats dict). The period-floor test drives the real write_rows.
"""
import os
import sqlite3
import tempfile

import pytest

from src.automation import fundamentals_xbrl as fx


# ── fixtures: a temp research.db (fundamentals_history + source col) and hermes.db ──
def _research_db(path, addressable):
    """addressable: list of (symbol, period_end) Screener rows (source NULL)."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
                "period_end TEXT, report_date TEXT, metric TEXT, value REAL, source TEXT)")
    for sym, pend in addressable:
        con.execute("INSERT INTO fundamentals_history(symbol,period_type,period_end,metric,value,source)"
                    " VALUES (?,?,?,?,?,NULL)", (sym, "Q", pend, "Sales", 100.0))
    con.commit()
    con.close()


def _hermes_db(path, universe):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE stock_index_membership(symbol TEXT, idx TEXT)")
    for s in universe:
        con.execute("INSERT INTO stock_index_membership(symbol,idx) VALUES (?, 'NIFTY50')", (s,))
    con.commit()
    con.close()


def test_worklist_tier1_first():
    with tempfile.TemporaryDirectory() as td:
        rdb, hdb = os.path.join(td, "r.db"), os.path.join(td, "h.db")
        _research_db(rdb, [("ZZZ", "2024-03-31"), ("AAA", "2024-03-31"), ("MMM", "2024-03-31")])
        _hermes_db(hdb, ["AAA", "ZZZ"])          # MMM out of index
        con = sqlite3.connect(rdb)
        wl = fx._backfill_worklist(con, window_start="2018-01-01", hermes_db=hdb)
        con.close()
        assert wl == [("AAA", 1), ("ZZZ", 1), ("MMM", 2)]


def test_period_floor_freezes_pre_window():
    """write_rows must skip a pre-window period and write an in-window one — the machine
    guard behind 'pre-2018 stays Screener'."""
    with tempfile.TemporaryDirectory() as td:
        rdb = os.path.join(td, "r.db")
        con = sqlite3.connect(rdb)
        con.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
                    "period_end TEXT, report_date TEXT, metric TEXT, value REAL, "
                    "PRIMARY KEY(symbol,period_type,period_end,metric))")
        con.commit()
        con.close()
        _obs = fx.provenance.observe
        fx.provenance.observe = lambda *a, **k: None
        try:
            pre = {"symbol": "T", "period": "Quarterly", "to_date": "2017-12-31",
                   "consolidated": True, "broadcast": "2018-02-10T18:00:00"}
            inw = {"symbol": "T", "period": "Quarterly", "to_date": "2018-03-31",
                   "consolidated": True, "broadcast": "2018-05-10T18:00:00"}
            assert fx.write_rows(pre, {"Sales": 10.0}, research_db=rdb, min_period_end="2018-01-01") == 0
            assert fx.write_rows(inw, {"Sales": 11.0}, research_db=rdb, min_period_end="2018-01-01") == 1
        finally:
            fx.provenance.observe = _obs
        con = sqlite3.connect(rdb)
        got = con.execute("SELECT period_end FROM fundamentals_history").fetchall()
        con.close()
        assert got == [("2018-03-31",)]


def _fake_ingest_factory(rdb, *, gate_pass=1, throttle_on=None, rows=5):
    """Return a stand-in ingest() that writes a gate verdict for the symbol and returns a
    stats dict — no network. throttle_on: a symbol name that reports aborted_throttled."""
    def _fake(*, symbols, since, until=None, overwrite_screener=False,
             research_db=None, min_period_end=None):
        sym = symbols[0]
        con = sqlite3.connect(rdb)
        con.execute("CREATE TABLE IF NOT EXISTS fundamentals_xbrl_gate("
                    "symbol TEXT PRIMARY KEY, checked_at TEXT, pass INTEGER, detail TEXT)")
        gp = 0 if (isinstance(gate_pass, dict) and gate_pass.get(sym) == 0) else \
            (gate_pass if isinstance(gate_pass, int) else 1)
        con.execute("INSERT OR REPLACE INTO fundamentals_xbrl_gate VALUES (?,datetime('now'),?,?)",
                    (sym, gp, "fake"))
        con.commit()
        con.close()
        return {"rows": rows, "aborted_throttled": (sym == throttle_on)}
    return _fake


def test_backfill_marks_done_and_is_resumable(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb, hdb = os.path.join(td, "r.db"), os.path.join(td, "h.db")
        _research_db(rdb, [("AAA", "2024-03-31"), ("BBB", "2024-03-31"), ("CCC", "2024-03-31")])
        _hermes_db(hdb, ["AAA", "BBB", "CCC"])
        monkeypatch.setattr(fx, "ingest", _fake_ingest_factory(rdb, gate_pass=1))
        s1 = fx.backfill(limit=2, research_db=rdb, hermes_db=hdb)
        assert s1["done"] == 2 and s1["queue_remaining"] == 1
        # second pass skips the two terminal 'done' rows, finishes the last one
        s2 = fx.backfill(limit=10, research_db=rdb, hermes_db=hdb)
        assert s2["attempted"] == 1 and s2["done"] == 1 and s2["queue_remaining"] == 0


def test_backfill_gate_fail_recorded_terminal(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb, hdb = os.path.join(td, "r.db"), os.path.join(td, "h.db")
        _research_db(rdb, [("GOOD", "2024-03-31"), ("BADD", "2024-03-31")])
        _hermes_db(hdb, ["GOOD", "BADD"])
        monkeypatch.setattr(fx, "ingest",
                            _fake_ingest_factory(rdb, gate_pass={"BADD": 0, "GOOD": 1}))
        s = fx.backfill(limit=10, research_db=rdb, hermes_db=hdb)
        assert s["done"] == 1 and s["gate_fail"] == 1 and s["queue_remaining"] == 0
        # gate_fail is terminal — a re-run attempts nothing
        s2 = fx.backfill(limit=10, research_db=rdb, hermes_db=hdb)
        assert s2["attempted"] == 0


def test_backfill_stops_cleanly_on_throttle(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb, hdb = os.path.join(td, "r.db"), os.path.join(td, "h.db")
        _research_db(rdb, [("AAA", "2024-03-31"), ("BBB", "2024-03-31"), ("CCC", "2024-03-31")])
        _hermes_db(hdb, ["AAA", "BBB", "CCC"])
        # BBB throttles -> AAA done, BBB partial, run stops before CCC
        monkeypatch.setattr(fx, "ingest", _fake_ingest_factory(rdb, throttle_on="BBB"))
        s = fx.backfill(limit=10, research_db=rdb, hermes_db=hdb)
        assert s["aborted_throttled"] is True
        assert s["done"] == 1 and s["partial"] == 1
        con = sqlite3.connect(rdb)
        st = dict(con.execute("SELECT symbol,status FROM fundamentals_xbrl_backfill_progress").fetchall())
        con.close()
        assert st == {"AAA": "done", "BBB": "partial"}     # CCC never attempted
        # resume: BBB (partial, non-terminal) retried, then CCC
        monkeypatch.setattr(fx, "ingest", _fake_ingest_factory(rdb, gate_pass=1))
        s2 = fx.backfill(limit=10, research_db=rdb, hermes_db=hdb)
        assert s2["done"] == 2 and s2["queue_remaining"] == 0


def test_backfill_tier_filter(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        rdb, hdb = os.path.join(td, "r.db"), os.path.join(td, "h.db")
        _research_db(rdb, [("INIDX", "2024-03-31"), ("OUTIDX", "2024-03-31")])
        _hermes_db(hdb, ["INIDX"])               # OUTIDX is tier 2
        monkeypatch.setattr(fx, "ingest", _fake_ingest_factory(rdb, gate_pass=1))
        s = fx.backfill(tier=1, research_db=rdb, hermes_db=hdb)
        assert s["attempted"] == 1 and s["done"] == 1
        con = sqlite3.connect(rdb)
        st = dict(con.execute("SELECT symbol,status FROM fundamentals_xbrl_backfill_progress").fetchall())
        con.close()
        assert st == {"INIDX": "done"}           # OUTIDX (tier 2) untouched
