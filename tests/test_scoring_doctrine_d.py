"""test_scoring_doctrine_d.py — the Doctrine-D sector-adapted lender model (D134, Track D Step 4).

Ramana's LOCKED defaults (2026-07-15): sub-type-aware thresholds (bank RoA ~1% · NBFC 2-4% ·
HFC RoE 12-15%) · ALM = CET1/CRAR + GNPA proxy · the suppress-half folds into the scorer.

The bug this model exists to kill (D3-F1): pt14's generic ROCE/OPM/D-E thresholds are structurally
wrong for lenders — leverage IS the business — so every bank was auto-DISQUALIFIED on D/E > 2.

Two defects caught by these tests during the build (both pinned below):
  * UNITS — `roa_pct` is the DISCRETE-QUARTER RoA (HDFCBANK 0.47%) while the locked "bank RoA ~1%"
    is ANNUAL (HDFCBANK ≈1.9%/yr). Comparing raw scored every good bank a FAIL.
  * PER-LEG BARS — the RoE cross-check was being judged against the RoA threshold (14.2% vs 1.0%
    trivially "passes"). RoA and RoE are different scales; each leg carries its own bar.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.automation.scoring import (   # noqa: E402
    check_hard_disqualifiers, financial_subtype, score_fundamentals,
)

# HDFCBANK Q3FY25 — the live-probed prudential values (see extract_bank_prudential)
BANK = {"symbol": "HDFCBANK", "roa_pct": 0.47, "roe": 14.2, "gnpa_pct": 1.42, "nnpa_pct": 0.46,
        "cet1_pct": 19.97, "nii_growth_5y": 16.0, "cost_to_income": 41.0,
        "profit_growth_5y": 20.0, "roce": 6.0, "debt_to_equity": 7.5, "pe": 19.0, "pb": 2.8,
        "promoter_holding": 0.0}


# ── the D3-F1 bug this model kills ────────────────────────────────────────────────────
def test_generic_model_disqualifies_a_bank_for_being_a_bank():
    """The documented defect: without Doctrine D, leverage auto-disqualifies every lender."""
    g = score_fundamentals(BANK)
    assert g["hard_disqualified"] is True
    assert any("Debt/Equity" in r for r in g["disqualifier_reasons"])


def test_doctrine_d_disables_the_leverage_disqualifier_for_lenders():
    dd = score_fundamentals(BANK, is_financial=True, subtype="bank")
    assert dd["hard_disqualified"] is False, "leverage IS a lender's business"
    assert dd["tier"] != "DISQUALIFIED"
    assert dd["sector_model"] == "doctrine-d" and dd["sector_subtype"] == "Bank"


def test_disqualifier_helper_honours_the_flag_directly():
    assert check_hard_disqualifiers({"debt_to_equity": 7.5})[0] is True
    assert check_hard_disqualifiers({"debt_to_equity": 7.5}, is_financial=True)[0] is False
    # the pledge rule still applies to everyone
    assert check_hard_disqualifiers({"promoter_pledge": 30.0}, is_financial=True)[0] is True


# ── the two build-time defects, pinned ────────────────────────────────────────────────
def test_quarterly_roa_is_annualised_before_meeting_an_annual_bar():
    """0.47%/qtr ≈ 1.88%/yr — comfortably over the ~1% bank bar. Raw-comparing 0.47 vs 1.0
    would fail every good bank (the defect this pins)."""
    dd = score_fundamentals(BANK, is_financial=True, subtype="bank")
    roa_leg = dd["patterns"][1]["signals"][0]
    assert roa_leg["raw"] == 2 and roa_leg["verified"] is True


def test_each_profitability_leg_uses_its_own_bar():
    """RoE 14.2% must be judged on the RoE bar (15/12 -> partial), NOT the RoA bar (1.0 -> a
    meaningless pass)."""
    dd = score_fundamentals(BANK, is_financial=True, subtype="bank")
    roe_leg = dd["patterns"][1]["signals"][1]
    assert roe_leg["raw"] == 1 and roe_leg["verified"] is True


# ── the model actually discriminates ──────────────────────────────────────────────────
def test_a_weak_bank_still_fails_the_bar_is_real():
    weak = dict(BANK, roa_pct=0.10, roe=6.0, gnpa_pct=8.5, nnpa_pct=3.2, cet1_pct=9.0,
                nii_growth_5y=2.0, cost_to_income=68.0, profit_growth_5y=1.0)
    strong = score_fundamentals(BANK, is_financial=True, subtype="bank")
    w = score_fundamentals(weak, is_financial=True, subtype="bank")
    assert w["patterns"][5]["score"] == 0, "GNPA 8.5 / CET1 9 / NNPA 3.2 must score zero"
    assert w["ns_base"] < strong["ns_base"] - 10


def test_pattern5_is_asset_quality_plus_capital():
    """GNPA ≤1.5 · CET1 ≥13 · NNPA ≤0.5 — HDFCBANK clears all three."""
    dd = score_fundamentals(BANK, is_financial=True, subtype="bank")
    assert dd["patterns"][5]["score"] == dd["patterns"][5]["max"]


def test_subtypes_reach_different_verdicts_on_identical_inputs():
    """Ramana's locked sub-type requirement: an NBFC is held to RoA 2-4%, an HFC to RoE 12-15%."""
    b = score_fundamentals(BANK, is_financial=True, subtype="bank")["patterns"][1]["score"]
    n = score_fundamentals(BANK, is_financial=True, subtype="nbfc")["patterns"][1]["score"]
    h = score_fundamentals(BANK, is_financial=True, subtype="hfc")["patterns"][1]["score"]
    assert b > n, "RoA 1.88%/yr clears the bank bar (1.0) but not the NBFC bar (3.0)"
    assert len({b, n, h}) > 1, "sub-types must not collapse to one verdict"


# ── NULL-tolerance: absent evidence must ABSTAIN, never false pass/fail ───────────────
def test_absent_prudential_ratios_abstain_rather_than_fail():
    """RoA/CET1 are XBRL-only and fill forward — absence is the COMMON case for months and must
    never be read as a zero."""
    thin = {"symbol": "X", "gnpa_pct": 1.2, "debt_to_equity": 9.0}    # no CET1/NNPA/RoA
    dd = score_fundamentals(thin, is_financial=True, subtype="bank")
    p5 = dd["patterns"][5]["signals"]
    assert p5[0]["raw"] == 2 and p5[0]["verified"] is True            # GNPA known -> scored
    assert p5[1]["raw"] == 1 and p5[1]["verified"] is False           # CET1 absent -> abstain
    assert p5[2]["raw"] == 1 and p5[2]["verified"] is False           # NNPA absent -> abstain
    assert dd["sector_model"] == "doctrine-d"                          # GNPA alone is evidence


def test_financial_with_no_evidence_is_suppressed_not_mis_tiered():
    """The suppress-half (locked): no measurable lender evidence -> NO tier, not a wrong one."""
    blind = score_fundamentals({"symbol": "XYZFIN", "roce": 5.0, "debt_to_equity": 6.0, "pe": 12.0},
                               is_financial=True, subtype="nbfc")
    assert blind["tier"] == "NA"
    assert blind["sector_suppressed"] is True and blind["sector_model"] == "suppressed"
    assert blind["sector_model_pending"] is True          # the D3-F1 flag surfaces still read
    assert "no Doctrine-D evidence" in blind["sector_note"]


def test_unknown_subtype_defaults_to_nbfc_the_conservative_lender_default():
    dd = score_fundamentals(BANK, is_financial=True)      # no subtype passed
    assert dd["sector_subtype"] == "NBFC"


# ── no regression for the other 99% of the universe ──────────────────────────────────
def test_non_financials_are_completely_unchanged():
    nf = {"symbol": "TCS", "roce": 45.0, "pe": 28.0, "pb": 12.0, "debt_to_equity": 0.1,
          "opm_latest": 26.0, "profit_growth_5y": 12.0, "sales_growth_5y": 8.0,
          "promoter_holding": 72.0}
    a = score_fundamentals(nf)
    b = score_fundamentals(nf, is_financial=False)
    assert a["ns_base"] == b["ns_base"] and a["tier"] == b["tier"]
    assert a["sector_model"] is None and a["sector_note"] is None
    assert a["sector_suppressed"] is False


# ── sub-type detection (what is / isn't primary-source) ──────────────────────────────
def _conn():
    """⚠ The columns here MIRROR THE LIVE SCHEMA — `security_master.company_name` (NOT `name`).
    An invented column would pass against a matching-but-wrong query while the real box threw,
    got swallowed by the fail-closed except, and silently degraded every HFC to NBFC. That
    exact bug shipped into this file once and was caught only by checking the live schema."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE company_tags(symbol TEXT, tag TEXT, source TEXT, approved INT)")
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY, first_date TEXT, "
              "last_date TEXT, n_days INTEGER, isin TEXT, company_name TEXT, "
              "listing_date TEXT, currently_listed INTEGER)")
    c.executemany("INSERT INTO company_tags VALUES (?,?,'index',1)", [
        ("HDFCBANK", "Banks"), ("HDFCBANK", "Financial Services"), ("HDFCBANK", "Private Banks"),
        ("SBIN", "Banks"), ("SBIN", "PSU Banks"), ("SBIN", "Financial Services"),
        ("BAJFINANCE", "Financial Services"), ("LICHSGFIN", "Financial Services"),
        ("TCS", "IT"),
    ])
    c.executemany("INSERT INTO security_master (symbol, company_name) VALUES (?,?)", [
        ("HDFCBANK", "HDFC Bank Ltd"), ("SBIN", "State Bank of India"),
        ("BAJFINANCE", "Bajaj Finance Ltd"), ("LICHSGFIN", "LIC Housing Finance Ltd"),
        ("TCS", "Tata Consultancy Services"),
    ])
    return c


def test_subtype_query_matches_the_live_security_master_schema():
    """Regression guard for the bug this file shipped once: `financial_subtype` read a column
    that does not exist, the fail-closed except swallowed it, and every HFC silently became an
    NBFC. Prove the name lookup actually RESOLVES (not just that it doesn't raise)."""
    c = _conn()
    assert financial_subtype("LICHSGFIN", c) == "hfc", \
        "the company_name lookup silently failed — HFC degraded to the NBFC default"
    # and the explicit-name path agrees with the DB path
    assert financial_subtype("BAJFINANCE", c, company_name="Bajaj Housing Finance Ltd") == "hfc"
    c.close()


def test_bank_subtype_is_primary_source_via_index_tags():
    c = _conn()
    assert financial_subtype("HDFCBANK", c) == "bank"
    assert financial_subtype("SBIN", c) == "bank"
    c.close()


def test_hfc_is_a_labelled_name_heuristic_and_nbfc_is_the_default():
    """MEASURED: NSE publishes no housing/NBFC index tag, so HFC can only be a name heuristic
    and everything else financial falls back to NBFC."""
    c = _conn()
    assert financial_subtype("LICHSGFIN", c) == "hfc"      # 'Housing Finance' in the name
    assert financial_subtype("BAJFINANCE", c) == "nbfc"    # financial, not bank, not housing
    c.close()


def test_non_financial_has_no_subtype():
    c = _conn()
    assert financial_subtype("TCS", c) is None
    assert financial_subtype("", c) is None
    c.close()
