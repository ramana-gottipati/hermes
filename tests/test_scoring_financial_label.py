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


def test_score_carries_sector_label_for_financials():
    f = {"symbol": "HDFCBANK", "roce": 7.0, "roe": 13.8, "pe": 16.8, "pb": 2.2}
    fin = scoring.score_fundamentals(f, is_financial=True)
    assert fin["sector_model_pending"] is True
    assert fin["sector_note"] and "Doctrine-D" in fin["sector_note"]
    # the computed tier is left unchanged (non-suppressing label)
    assert "tier" in fin and "ns_base" in fin

    non = scoring.score_fundamentals(f)                                # default is_financial=False
    assert non["sector_model_pending"] is False
    assert non["sector_note"] is None


def test_telegram_leads_with_advisory_for_financials():
    f = {"symbol": "HDFCBANK", "roce": 7.0, "roe": 13.8, "pe": 16.8, "pb": 2.2}
    fin = scoring.score_fundamentals(f, is_financial=True)
    txt = scoring.format_score_for_telegram(fin)
    assert "Financial-sector" in txt
    assert txt.index("Financial-sector") < txt.index("HDFCBANK")       # advisory leads

    non = scoring.score_fundamentals(f)
    assert "Financial-sector" not in scoring.format_score_for_telegram(non)
