"""test_pat_quality_flow.py — the per-symbol quality/fundamentals flow (S155-c).

The gap this closes, measured before the build: Pat could EXPLAIN the Doctrine-D metrics but not
show a NAME's values. Asking a per-symbol fundamental returned the generic DEFINITION
("what's HDFCBANK's CET1" -> the CET1 definition), nothing at all ("is HDFCBANK a good bank"), or
a MARKET-WIDE SCREEN ("HDFCBANK asset quality" screened the whole universe). The Doctrine-D model
shipped unreachable by a human question.

These contracts pin the two things that make the flow safe: it fires ONLY with a symbol (so the
market-wide screen is never stolen) and it yields every ask another per-symbol flow owns.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import quality_flow as QF        # noqa: E402
from src.pat import engine as ENGINE          # noqa: E402


# ── recognition: a fundamentals cue + a symbol ────────────────────────────────────────
def test_recognizes_per_symbol_fundamental_asks():
    assert QF.parse_quality("what's HDFCBANK's CET1")["params"] == {"symbol": "HDFCBANK", "focus": "capital"}
    assert QF.parse_quality("what is HDFCBANK gnpa")["params"]["focus"] == "asset_quality"
    assert QF.parse_quality("is HDFCBANK a good bank")["params"]["symbol"] == "HDFCBANK"
    assert QF.parse_quality("what's TCS's ROCE")["params"] == {"symbol": "TCS", "focus": "profitability"}
    assert QF.parse_quality("what are the risks in HDFCBANK")["params"]["focus"] == "risk"
    assert QF.parse_quality("is TCS overvalued")["params"]["focus"] == "valuation"
    assert QF.parse_quality("HDFCBANK asset quality")["params"]["focus"] == "asset_quality"


def test_the_market_wide_screen_is_never_stolen():
    """THE guard: no symbol -> the whole-universe fundamentals screen keeps the ask."""
    for q in ("overvalued stocks", "elite ROCE names", "deep value", "cheap stocks under PE 15",
              "no-pledge names", "highly leveraged companies"):
        assert QF.parse_quality(q) is None, q


def test_yields_asks_that_belong_to_another_per_symbol_flow():
    for q in ("TCS news", "what phase is TCS in", "any pledge on INFY", "credit rating of INFY",
              "is TCS credible", "is TCS usually up in July", "tell me about TCS", ""):
        assert QF.parse_quality(q) is None, q


# ── engine precedence: the neighbours all survive ─────────────────────────────────────
def test_engine_routes_quality_without_breaking_neighbours():
    assert ENGINE.route("what's HDFCBANK's CET1")["flow"] == "quality"
    assert ENGINE.route("is HDFCBANK a good bank")["flow"] == "quality"
    assert ENGINE.route("HDFCBANK asset quality")["flow"] == "quality"   # was a market-wide screen
    # neighbours keep their asks
    assert ENGINE.route("overvalued stocks")["flow"] == "fundamentals"   # the SCREEN
    assert ENGINE.route("any pledge on INFY")["flow"] == "filings"
    assert ENGINE.route("TCS news")["flow"] == "news"
    assert ENGINE.route("what phase is TCS in")["flow"] == "rotation"
    assert ENGINE.route("tell me about TCS")["flow"] == "card"
    assert ENGINE.route("what is CET1")["flow"] == "explain"             # the DEFINITION still works


# ── the rows: an absent ratio is "not known", never zero ──────────────────────────────
def test_unknown_values_are_skipped_not_shown_as_zero():
    b = {"subtype": "bank", "f": {"gnpa_pct": 1.42, "nnpa_pct": None, "cet1_pct": 19.97}}
    assert QF.rows_for(b, "asset_quality") == [("Gross NPA", 1.42, "%")]
    assert QF.rows_for(b, "capital")[0] == ("CET1", 19.97, "%")
    assert QF.rows_for({"subtype": None, "f": {}}, "all") == []


def test_lender_and_non_lender_get_different_headline_rows():
    lender = {"subtype": "bank", "f": {"gnpa_pct": 1.42, "cet1_pct": 19.97, "roce": 6.0}}
    plain = {"subtype": None, "f": {"roce": 45.0, "pe": 28.0}}
    lab_l = [r[0] for r in QF.rows_for(lender, "all")]
    lab_p = [r[0] for r in QF.rows_for(plain, "all")]
    assert "Gross NPA" in lab_l and "CET1" in lab_l, "a lender leads with asset quality + capital"
    assert "ROCE" in lab_p and "Gross NPA" not in lab_p, "a non-lender never shows lender ratios"


def test_read_degrades_and_never_raises():
    assert QF.quality_for("") is None
    assert QF.quality_for("ZZZZNOTREAL") is None or isinstance(QF.quality_for("ZZZZNOTREAL"), dict)


def test_selftest_passes():
    assert QF._selftest() == 0
