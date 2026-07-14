"""D6-F2 regression: credibility_series must gate a resolved promise on the actual's
PUBLIC/knowable date (`resolved_knowable_date`) when present, not on the period-end.

The leak: a promise for FY-period ending 2024-03 whose actual is only REPORTED in
2024-06 was counted as "knowable" at the 2024-03 series point (~a quarter too early).
The fix keys on the report date; when it is absent (Screener path) it falls back to the
period-end (legacy). Both behaviors are pinned here. CCI is descriptive-only, so no
live conclusion moves — this guards the PIT correctness of the series.
"""
import sqlite3

import pytest

from src.automation import cci_series


def _mk_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE concalls (
            symbol TEXT, period_label TEXT, concall_year INT, concall_month INT
        );
        CREATE TABLE concall_guidance (
            symbol TEXT, source_period TEXT, status TEXT, resolved_period TEXT,
            resolved_knowable_date TEXT, claim_text TEXT
        );
        CREATE TABLE concall_redflags (symbol TEXT, period_label TEXT, flag_type TEXT);
        """
    )
    # three quarterly concall periods
    for lbl, y, m in [("Mar 2024", 2024, 3), ("Jun 2024", 2024, 6), ("Sep 2024", 2024, 9)]:
        conn.execute("INSERT INTO concalls VALUES (?,?,?,?)", ("TEST", lbl, y, m))
    return conn


def _n_resolved_by_period(conn):
    return {(r["period_year"], r["period_month"]): r["n_resolved"]
            for r in conn.execute(
                "SELECT period_year, period_month, n_resolved FROM credibility_series WHERE symbol='TEST'")}


def test_gates_on_knowable_date_when_present():
    conn = _mk_db()
    # a HARD numeric promise made in Mar-2024, MET, whose actual was REPORTED 2024-06-15
    conn.execute(
        "INSERT INTO concall_guidance (symbol, source_period, status, resolved_period, "
        "resolved_knowable_date, claim_text) VALUES (?,?,?,?,?,?)",
        ("TEST", "Mar 2024", "MET", "2024-03-31", "2024-06-15",
         "revenue will be 1000 cr this quarter"))
    cci_series.build_series(conn, "TEST")
    n = _n_resolved_by_period(conn)
    # period-end was 2024-03, but the actual was knowable only 2024-06 -> NOT counted at Mar.
    assert n[(2024, 3)] == 0
    # counted from Jun onward (report date reached).
    assert n[(2024, 6)] == 1
    assert n[(2024, 9)] == 1


def test_falls_back_to_period_end_when_no_knowable_date():
    conn = _mk_db()
    # same promise but NO knowable date (Screener concall_results path) -> legacy period-end gate.
    conn.execute(
        "INSERT INTO concall_guidance (symbol, source_period, status, resolved_period, "
        "resolved_knowable_date, claim_text) VALUES (?,?,?,?,?,?)",
        ("TEST", "Mar 2024", "MET", "2024-03-31", None,
         "revenue will be 1000 cr this quarter"))
    cci_series.build_series(conn, "TEST")
    n = _n_resolved_by_period(conn)
    # with no report date we fall back to the period-end -> counted already at Mar (legacy behavior).
    assert n[(2024, 3)] == 1
    assert n[(2024, 6)] == 1
