"""AUD-38 regression — /v1 PIT semantics (S96b).

Seam-level and hermetic: exercises the two public readers (cci_series.series_asof,
signal_events.latest_batch_on_or_before) and the resources.py functions the /v1 routes
call, on an in-memory DB. The load-bearing claims:

  1. credibility as_of obeys the MONTH-END knowable rule — a period (Y,M) row is NOT
     servable before the last calendar day of month M (no look-ahead over precision),
     and IS servable from that day on, `knowable_from` stamped.
  2. undateable rows (NULL period_year/month) are excluded from PIT serves while still
     present in the plain series.
  3. attention as_of resolves to the last computed batch ON-OR-BEFORE the date (an
     exact-date miss is not an empty tape); before the first batch the honest answer
     is empty.
  4. the no-as_of paths are byte-identical to the old behaviour (latest row / latest batch).
"""
from __future__ import annotations

import sqlite3

import pytest

from src.automation import cci_series, signal_events
from src.api.v1 import resources as R


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    cci_series.ensure_schema(c)
    signal_events.ensure_schema(c)
    # resources.credibility resolves renames first; canonical() reads this table raw.
    c.execute("CREATE TABLE security_renames (old_symbol TEXT, new_symbol TEXT, "
              "confirmed INT, effective_date TEXT)")

    def cred(symbol, label, y, m, level, tier, n_resolved, ga):
        c.execute("INSERT INTO credibility_series (symbol, period_label, period_year, "
                  "period_month, level, tier, n_resolved, ga, trend) "
                  "VALUES (?,?,?,?,?,?,?,?, 'STABLE')",
                  (symbol, label, y, m, level, tier, n_resolved, ga))

    cred("TESTCO", "Q1FY25", 2024, 8, 61.0, "B", 12, 0.71)
    cred("TESTCO", "Q2FY25", 2024, 11, 66.0, "B", 14, 0.74)
    cred("LEAPCO", "Q4FY24", 2024, 2, 50.0, "C", 4, 0.55)          # leap February
    cred("DARKCO", "FY10", None, None, 40.0, "D", 3, 0.40)          # undateable row

    def ev(symbol, as_of, magnitude):
        c.execute("INSERT INTO signal_events (symbol, lens, event_type, direction, "
                  "magnitude, as_of, note) VALUES (?, 'rs', 'level_cross', 'up', ?, ?, 't')",
                  (symbol, magnitude, as_of))

    ev("AAA", "2024-08-01", 0.9)
    ev("BBB", "2024-08-01", 0.5)
    ev("CCC", "2024-08-05", 0.7)
    c.commit()
    yield c
    c.close()


# ── 1. the month-end knowable rule ───────────────────────────────────────────

def test_credibility_asof_excludes_midmonth(conn):
    # Aug-2024 row is knowable only from Aug-31; the 30th must serve NOTHING.
    assert cci_series.series_asof(conn, "TESTCO", "2024-08-30") is None


def test_credibility_asof_serves_from_month_end(conn):
    row = cci_series.series_asof(conn, "TESTCO", "2024-08-31")
    assert row is not None and row["period_label"] == "Q1FY25"
    assert row["knowable_from"] == "2024-08-31"


def test_credibility_asof_picks_newest_knowable(conn):
    row = cci_series.series_asof(conn, "TESTCO", "2024-12-01")
    assert row is not None and row["period_label"] == "Q2FY25"
    assert row["knowable_from"] == "2024-11-30"


def test_credibility_asof_leap_month_end(conn):
    assert cci_series.series_asof(conn, "LEAPCO", "2024-02-28") is None
    row = cci_series.series_asof(conn, "LEAPCO", "2024-02-29")
    assert row is not None and row["knowable_from"] == "2024-02-29"


def test_credibility_asof_bad_date_is_none(conn):
    assert cci_series.series_asof(conn, "TESTCO", "not-a-date") is None


# ── 2. undateable rows are PIT-excluded, series-visible ──────────────────────

def test_undateable_rows_excluded_from_pit(conn):
    assert len(cci_series.series_for(conn, "DARKCO")) == 1
    assert cci_series.series_asof(conn, "DARKCO", "2026-01-01") is None


# ── 3. attention batch resolution ────────────────────────────────────────────

def test_batch_resolver_on_or_before(conn):
    f = signal_events.latest_batch_on_or_before
    assert f(conn, "2024-07-31") is None
    assert f(conn, "2024-08-01") == "2024-08-01"
    assert f(conn, "2024-08-04") == "2024-08-01"      # weekend/holiday-style miss
    assert f(conn, "2024-08-05") == "2024-08-05"
    assert f(conn, "2024-09-01") == "2024-08-05"


def test_attention_resource_pit(conn):
    rows = R.attention(conn, as_of="2024-08-04")
    assert rows and all(r["as_of"] == "2024-08-01" for r in rows)
    assert len(rows) == 2
    assert R.attention(conn, as_of="2024-07-31") == []


# ── 4. the no-as_of paths are unchanged ──────────────────────────────────────

def test_latest_paths_unchanged(conn):
    sym, latest = R.credibility(conn, "testco")
    assert sym == "TESTCO" and latest["period_label"] == "Q2FY25"
    assert "knowable_from" not in latest              # PIT stamp only on PIT serves
    rows = R.attention(conn)
    assert rows and all(r["as_of"] == "2024-08-05" for r in rows)


def test_credibility_resource_pit_roundtrip(conn):
    sym, row = R.credibility(conn, "TESTCO", as_of="2024-09-15")
    assert sym == "TESTCO" and row["period_label"] == "Q1FY25"
    assert row["knowable_from"] == "2024-08-31"
    _, none_row = R.credibility(conn, "TESTCO", as_of="2024-01-01")
    assert none_row is None
