"""Phase-3 gate correctness: the ₹0.5cr absolute-tolerance floor on the per-symbol
series-continuity gate (_continuity_gate).

Screener rounds small-cap rupee figures to whole crores, so the flat 2% RELATIVE gate
spuriously fails tiny values. The absolute floor recovers those without touching genuine
definitional breaks. Values below are the real XBRL-vs-Screener pairs from the
2026-07-14 Phase-3 coverage audit (docs/fundamentals-xbrl-phase3-backfill.md §4).
"""
import sqlite3

import pytest

from src.automation import fundamentals_xbrl as fx


def _con():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE fundamentals_history(symbol TEXT, period_type TEXT, "
              "period_end TEXT, report_date TEXT, metric TEXT, value REAL, source TEXT)")
    c.execute("CREATE TABLE fundamentals_xbrl_gate(symbol TEXT PRIMARY KEY, "
              "checked_at TEXT, pass INTEGER, detail TEXT)")
    return c


def _seed_screener(con, sym, rows):
    """rows: (period_type, period_end, metric, screener_value) — source=NULL (Screener era)."""
    for ptype, pend, metric, val in rows:
        con.execute("INSERT INTO fundamentals_history"
                    "(symbol, period_type, period_end, metric, value, source) "
                    "VALUES (?,?,?,?,?,NULL)", (sym, ptype, pend, metric, val))
    con.commit()


# ── the rounding cohort: must PASS via the absolute floor (would fail on 2% rel) ──────
@pytest.mark.parametrize("sym, ptype, pend, metric, screener, xbrl, rel_pct", [
    ("VIKASECO",   "A", "2024-03-31", "Net Profit",       7.0,  6.8465, 2.2),
    ("AHLEAST",    "Q", "2024-12-31", "Net Profit",       5.0,  4.8303, 3.4),
    ("NUVOCO",     "Q", "2024-06-30", "Net Profit",       3.0,  2.84,   5.3),
    ("UMIYA-MRO",  "Q", "2024-03-31", "Operating Profit", -0.13, -0.2704, 108.0),
    ("EIMCOELECO", "Q", "2023-12-31", "Net Profit",       8.0,  7.5479, 5.7),
])
def test_small_cap_rounding_recovered(sym, ptype, pend, metric, screener, xbrl, rel_pct):
    con = _con()
    _seed_screener(con, sym, [(ptype, pend, metric, screener)])
    assert abs(xbrl - screener) <= fx._GATE_ABS_FLOOR_CR, "test premise: within the abs floor"
    assert rel_pct > fx._GATE_TOL * 100, "test premise: would fail the relative gate"
    assert fx._continuity_gate(con, sym, [(ptype, pend, metric, xbrl)]) is True


# ── the definitional cohort: must STILL FAIL (|Δ| far exceeds the floor) ──────────────
@pytest.mark.parametrize("sym, ptype, pend, metric, screener, xbrl", [
    ("ITC",        "Q", "2024-12-31", "Sales",      18790.0, 20349.96),   # excise-gross
    ("HDFCBANK",   "Q", "2024-09-30", "Net Profit", 18627.0, 17825.91),   # MI-in-exceptionals
    ("LTF",        "Q", "2024-12-31", "Revenue",     4098.0,  3806.38),   # NBFC revenue defn
    ("ANANDRATHI", "A", "2024-03-31", "Sales",        752.0,   724.3225),  # ~28cr real gap
])
def test_definitional_break_still_fails(sym, ptype, pend, metric, screener, xbrl):
    con = _con()
    _seed_screener(con, sym, [(ptype, pend, metric, screener)])
    assert abs(xbrl - screener) > fx._GATE_ABS_FLOOR_CR, "test premise: outside the abs floor"
    assert fx._continuity_gate(con, sym, [(ptype, pend, metric, xbrl)]) is False


def test_floor_is_bounded_not_blanket_small_pass():
    """A small-value row OUTSIDE the ₹0.5cr band (and outside 2% rel) must still FAIL —
    the floor is an absolute band, not a free pass for every small number."""
    con = _con()
    _seed_screener(con, "X", [("Q", "2024-12-31", "Net Profit", 3.0)])
    # 2.0 vs 3.0 -> |Δ|=1.0cr (> 0.5) and 33% rel (> 2%) -> fail
    assert fx._continuity_gate(con, "X", [("Q", "2024-12-31", "Net Profit", 2.0)]) is False


def test_no_screener_overlap_auto_passes():
    """A symbol with no overlapping Screener rows (new listing) has nothing to contradict
    -> auto-pass, unchanged by the floor."""
    con = _con()
    assert fx._continuity_gate(con, "NEWCO", [("Q", "2024-12-31", "Sales", 123.4)]) is True
