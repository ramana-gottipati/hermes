"""test_home_zones.py — Graphite Home increment (ii): the live zones (pulse · today · flows).

Proves the zone reads + builders are defensive (empty DB -> honest empty states, never raise),
render real content when seeded, escape untrusted data (DOM safety), and never leak a preview/legacy
marker. Hermetic — synthetic in-memory DBs, no dependency on the live datastore.
"""
from __future__ import annotations

import sqlite3

from src.web.home import components as C
from src.web.home import reads


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


_NO_MOOD = {"word": "No data", "plain": "", "cls": "b-neu", "parts": []}


def test_zones_render_defensively_on_an_empty_db():
    c = _conn()  # no tables at all
    pulse = C.pulse_block(reads.index_pulse(c), _NO_MOOD, reads.breadth_latest(c), reads.index_series(c))
    assert pulse and "g-empty" in pulse                     # honest empty index/breadth
    assert "g-empty" in C.changed_rows(reads.what_changed(c))
    assert "g-empty" in C.flows_block(reads.fii_dii_recent(c))
    band = C.count_band(reads.severity_counts(c))
    assert band and ">0<" in band                           # renders honest zeros, never raises


def test_today_zone_renders_with_seeded_alert_rail():
    c = _conn()
    from src.automation import signal_alerts as SA
    SA.ensure_schema(c)
    c.execute("INSERT INTO signal_alert_state(symbol,lens,event_type,from_state,to_state,magnitude,"
              "severity,valence,as_of) VALUES "
              "('TCS','mep','state','DISTRIB','STRONG_DISTRIB',1.0,'critical','risk',date('now')),"
              "('INFY','rs','state','INSIDE','LEADING',1.0,'high','opportunity',date('now'))")
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.executemany("INSERT INTO security_master VALUES(?)", [("TCS",), ("INFY",)])
    counts = reads.severity_counts(c)
    assert counts["critical"] == 1 and counts["high"] == 1 and counts["total"] == 2
    assert "Critical" in C.count_band(counts)
    rows = reads.what_changed(c)
    assert rows, "the alert rail should return the seeded changes"
    ch = C.changed_rows(rows)
    assert "TCS" in ch and ("Delivery accumulation" in ch or "Relative strength" in ch)


def test_flows_zone_renders_signed_diverging_bars():
    c = _conn()
    c.execute("CREATE TABLE fii_dii_flows(trade_date TEXT,category TEXT,buy_value REAL,"
              "sell_value REAL,net_value REAL,fetched_at TEXT,UNIQUE(trade_date,category))")
    c.execute("INSERT INTO fii_dii_flows(trade_date,category,net_value) VALUES "
              "('2026-07-23','FII/FPI',-1240),('2026-07-23','DII',860)")
    fr = reads.fii_dii_recent(c)
    assert len(fr) == 2
    fb = C.flows_block(fr)
    assert "FII" in fb and "DII" in fb and "g-fbar up" in fb and "g-fbar dn" in fb


def test_zone_builders_escape_untrusted_data_and_leak_no_markers():
    ch = C.changed_rows([{"symbol": "<script>x</script>", "lens": "rs",
                          "from_state": "A", "to_state": "B", "as_of": "2026-07-23"}])
    assert "<script>" not in ch and "&lt;script&gt;" in ch
    for html in (ch, C.count_band({"critical": 1}), C.flows_block(
            [{"trade_date": "2026-07-23", "category": "FII/FPI", "net_value": -5}])):
        assert "pv3" not in html and "data-ui-v3" not in html and "uk-sub" not in html
