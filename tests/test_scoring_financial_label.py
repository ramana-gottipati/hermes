"""Codex D3-F1 / Track D interim: pt14 must LABEL financials (bank/NBFC/HFC) so the
generic ROCE/OPM/D-E tier is not read as a real quality verdict for a lender.

Pins the primary-source detector (NSE financial-index membership via company_tags),
the non-suppressing flag on the score dict, and the Telegram advisory. The full
Doctrine-D financials model + score suppression are a separate decision-gated build.
"""
import sqlite3

import pytest

from src.automation import scoring


def _tags_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE company_tags (symbol TEXT, tag TEXT, source TEXT, approved INT)")
    rows = [
        ("HDFCBANK", "Banks", "index", 1),
        ("HDFCBANK", "Financial Services", "index", 1),
        ("BAJFINANCE", "Financial Services", "index", 1),
        ("RELIANCE", "Oil Gas & Consumable Fuels", "index", 1),
        # a financial tag that is NOT an approved index membership must NOT trigger:
        ("SOMENBFC", "Financial Services", "ai", 0),
    ]
    c.executemany("INSERT INTO company_tags VALUES (?,?,?,?)", rows)
    return c


def test_detector_flags_lenders_only():
    c = _tags_db()
    assert scoring.is_financial_symbol("HDFCBANK", c) is True
    assert scoring.is_financial_symbol("BAJFINANCE", c) is True
    assert scoring.is_financial_symbol("hdfcbank", c) is True          # case-insensitive
    assert scoring.is_financial_symbol("RELIANCE", c) is False
    assert scoring.is_financial_symbol("SOMENBFC", c) is False         # unapproved / non-index source
    assert scoring.is_financial_symbol("", c) is False


# ⚠ SUPERSEDED BY DOCTRINE D (D134, Track D Step 4). The two tests below originally pinned the
# D3-F1 INTERIM contract: "every financial is `sector_model_pending=True` + carries the
# model-pending label, tier left unchanged". Step 4 replaced that model, so the contract moved:
#   * a lender we CAN measure is now scored on the sector-adapted model → pending=False, and the
#     note becomes the "sector-adapted thresholds (Doctrine D)" disclosure;
#   * a lender we CANNOT measure is now SUPPRESSED (tier 'NA') rather than labelled — the
#     suppress-half Ramana locked.
# The assertions are rewritten to the new contract rather than deleted, so the disclosure
# guarantee (a reader is never handed a lender tier with no sector context) stays enforced.
def test_measurable_financial_is_scored_on_the_doctrine_d_model():
    # a real bank: RoE alone is NOT lender evidence (every company has one) — GNPA/CET1 are.
    f = {"symbol": "HDFCBANK", "roce": 7.0, "roe": 13.8, "pe": 16.8, "pb": 2.2,
         "gnpa_pct": 1.42, "cet1_pct": 19.97}
    fin = scoring.score_fundamentals(f, is_financial=True, subtype="bank")
    assert fin["sector_model"] == "doctrine-d"
    assert fin["sector_model_pending"] is False and fin["sector_suppressed"] is False
    assert fin["sector_note"] and "Doctrine D" in fin["sector_note"]
    assert "tier" in fin and "ns_base" in fin

    non = scoring.score_fundamentals(f)                                # default is_financial=False
    assert non["sector_model_pending"] is False
    assert non["sector_note"] is None and non["sector_model"] is None


def test_unmeasurable_financial_is_suppressed_and_still_labelled():
    f = {"symbol": "XYZFIN", "roce": 7.0, "pe": 16.8, "pb": 2.2}       # no RoA/RoE/GNPA/CET1
    fin = scoring.score_fundamentals(f, is_financial=True, subtype="nbfc")
    assert fin["sector_model_pending"] is True and fin["sector_suppressed"] is True
    assert fin["tier"] == "NA"


def test_telegram_leads_with_the_sector_disclosure_for_financials():
    f = {"symbol": "HDFCBANK", "roce": 7.0, "roe": 13.8, "pe": 16.8, "pb": 2.2,
         "gnpa_pct": 1.42, "cet1_pct": 19.97}
    fin = scoring.score_fundamentals(f, is_financial=True, subtype="bank")
    txt = scoring.format_score_for_telegram(fin)
    assert "Doctrine D" in txt
    assert txt.index("Doctrine D") < txt.index("HDFCBANK")             # disclosure leads

    # a suppressed lender still leads with its ⚠️ advisory
    sup = scoring.score_fundamentals({"symbol": "XYZFIN", "roce": 7.0}, is_financial=True)
    stxt = scoring.format_score_for_telegram(sup)
    assert "Financial-sector" in stxt and stxt.index("Financial-sector") < stxt.index("XYZFIN")

    non = scoring.score_fundamentals(f)
    out = scoring.format_score_for_telegram(non)
    assert "Doctrine D" not in out and "Financial-sector" not in out
