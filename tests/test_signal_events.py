"""Signal-event bus producer regressions (S101 — the wiring session).

The bus sat at 0 rows in prod because the producer was never wired into any
nightly unit AND the cci lens was silently dead (it ordered credibility_series
by an `as_of` column that table does not have; the defensive except turned the
SQL error into a permanent no-op). These tests pin the producer:

  1. every live lens (mep / cci / oi / rs / deal) emits from a two-state fixture
     — the cci case is the regression that would have caught the dead loop;
  2. run_detection is idempotent (a second run emits zero);
  3. the attention queue surfaces the latest batch after a detect pass, and the
     PIT resolver reaches the older cci batch;
  4. cci events are dated to the day the new period row LANDED (computed_at),
     not the concall period — the PIT-knowable date;
  5. deal magnitude is a within-day value percentile (relative, no rupee
     constants) and direction follows the net side.

Reader semantics (attention_queue / latest_batch_on_or_before) are FINAL and
covered by tests/test_v1_pit.py — nothing here re-tests them beyond the
producer→reader seam.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.automation import signal_events as se


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    se.ensure_schema(c)
    # minimal source-table shapes — only the columns the producer reads
    c.executescript("""
    CREATE TABLE mep_signals (symbol TEXT, trade_date TEXT, mep_state_smooth TEXT,
                              PRIMARY KEY (symbol, trade_date));
    CREATE TABLE credibility_series (symbol TEXT, period_label TEXT, period_year INT,
                                     period_month INT, level REAL, trend TEXT,
                                     computed_at TEXT,
                                     PRIMARY KEY (symbol, period_label));
    CREATE TABLE fno_oi_signals (symbol TEXT, trade_date TEXT, quadrant TEXT,
                                 PRIMARY KEY (symbol, trade_date));
    CREATE TABLE rsband_signals (numerator TEXT, denominator TEXT, trade_date TEXT,
                                 rs_band_state TEXT);
    CREATE TABLE bulk_block_deals (trade_date TEXT, symbol TEXT, deal_type TEXT,
                                   client_name TEXT, side TEXT, qty INTEGER, price REAL);
    """)
    # mep: one flip on the latest pair, one non-flipper
    c.execute("INSERT INTO mep_signals VALUES ('FLIPCO','2026-07-08','ACCUM')")
    c.execute("INSERT INTO mep_signals VALUES ('FLIPCO','2026-07-09','DISTRIB')")
    c.execute("INSERT INTO mep_signals VALUES ('STAYCO','2026-07-08','NEUTRAL')")
    c.execute("INSERT INTO mep_signals VALUES ('STAYCO','2026-07-09','NEUTRAL')")
    # cci: +8 level step between the last two PERIODS; the new row landed Jul-01.
    # Regression: the old order="as_of" probe errored here and emitted nothing, ever.
    c.execute("INSERT INTO credibility_series VALUES "
              "('STEPCO','Q4FY26',2026,3,55.0,'STABLE','2026-04-02 03:00:00')")
    c.execute("INSERT INTO credibility_series VALUES "
              "('STEPCO','Q1FY27',2026,6,63.0,'IMPROVING','2026-07-01 03:00:00')")
    # oi: positioning quadrant flip
    c.execute("INSERT INTO fno_oi_signals VALUES ('OICO','2026-07-08','LONG_BUILDUP')")
    c.execute("INSERT INTO fno_oi_signals VALUES ('OICO','2026-07-09','SHORT_BUILDUP')")
    # rs: index-grain band-state flip vs the benchmark; a non-benchmark pair is ignored
    c.execute("INSERT INTO rsband_signals VALUES ('Nifty IT','Nifty 500','2026-07-08','MID')")
    c.execute("INSERT INTO rsband_signals VALUES ('Nifty IT','Nifty 500','2026-07-09','SUPPORT')")
    c.execute("INSERT INTO rsband_signals VALUES ('Nifty IT','Nifty 50','2026-07-09','RESIST')")
    # deals on the latest day: BIGCO 2 prints ₹60cr net BUY; SMALLCO 1 print ₹0.1cr SELL
    c.execute("INSERT INTO bulk_block_deals VALUES "
              "('2026-07-09','BIGCO','bulk','Fund A','BUY',1000000,400.0)")
    c.execute("INSERT INTO bulk_block_deals VALUES "
              "('2026-07-09','BIGCO','block','Fund B','BUY',500000,400.0)")
    c.execute("INSERT INTO bulk_block_deals VALUES "
              "('2026-07-09','SMALLCO','bulk','Trader','SELL',10000,100.0)")
    c.commit()
    yield c
    c.close()


def _events(c, lens):
    return [dict(r) for r in c.execute(
        "SELECT * FROM signal_events WHERE lens=? ORDER BY symbol", (lens,)).fetchall()]


def test_every_live_lens_emits(conn):
    out = se.run_detection(conn)
    assert out["emitted"]["mep"] == 1
    assert out["emitted"]["cci"] == 1          # the dead-loop regression
    assert out["emitted"]["oi"] == 1
    assert out["emitted"]["rs"] == 1
    assert out["emitted"]["deal"] == 2
    assert out["total"] == 6


def test_mep_flip_shape(conn):
    se.run_detection(conn)
    (e,) = _events(conn, "mep")
    assert (e["symbol"], e["event_type"], e["from_state"], e["to_state"], e["as_of"]) == \
        ("FLIPCO", "phase_flip", "ACCUM", "DISTRIB", "2026-07-09")


def test_cci_step_dated_to_knowable_day(conn):
    se.run_detection(conn)
    (e,) = _events(conn, "cci")
    assert e["symbol"] == "STEPCO"
    assert e["event_type"] == "credibility_step"
    assert e["direction"] == "up"
    assert e["as_of"] == "2026-07-01"          # the day the row landed, NOT the period


def test_oi_flip_typed(conn):
    se.run_detection(conn)
    (e,) = _events(conn, "oi")
    assert e["event_type"] == "oi_flip"
    assert (e["from_state"], e["to_state"]) == ("LONG_BUILDUP", "SHORT_BUILDUP")


def test_rs_index_grain_flip(conn):
    se.run_detection(conn)
    (e,) = _events(conn, "rs")
    assert e["symbol"] == "NIFTY IT"           # emit() canonicalizes to upper
    assert (e["from_state"], e["to_state"]) == ("MID", "SUPPORT")
    assert "Nifty 500" in e["note"]


def test_deal_print_percentile_magnitude(conn):
    se.run_detection(conn)
    big, small = _events(conn, "deal")         # ordered by symbol: BIGCO, SMALLCO
    assert big["symbol"] == "BIGCO" and small["symbol"] == "SMALLCO"
    assert big["magnitude"] == 1.0             # the day's largest print
    assert small["magnitude"] == 0.5           # rank 1 of 2
    assert big["direction"] == "up" and small["direction"] == "down"
    assert "net BUY" in big["note"]


def test_idempotent_rerun(conn):
    assert se.run_detection(conn)["total"] == 6
    assert se.run_detection(conn)["total"] == 0


def test_attention_queue_serves_latest_batch(conn):
    se.run_detection(conn)
    q = se.attention_queue(conn, limit=6)
    # latest batch = MAX(as_of) = 2026-07-09 (mep/oi/rs/deal events); the Jul-01
    # cci step is an older batch — reachable via as_of, absent from the headline
    assert q and all(e["as_of"] == "2026-07-09" for e in q)
    assert {e["lens"] for e in q} <= {"mep", "oi", "rs", "deal"}
    assert se.latest_batch_on_or_before(conn, "2026-07-05") == "2026-07-01"
