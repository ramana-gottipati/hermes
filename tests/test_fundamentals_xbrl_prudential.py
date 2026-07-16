"""test_fundamentals_xbrl_prudential.py — Doctrine-D Pattern-5 SA-instance extraction (D134).

Pins the behaviour VERIFIED against the live HDFCBANK Q3FY25 filing (read-only NSE probe,
2026-07-15, period-end 2024-12-31):

  * the prudential ratios live ONLY in the STANDALONE instance — HDFCBANK's CONSOLIDATED
    instance reports 0.00 for all five tags (the group folds in non-bank subs), which is why
    `_prefer_consolidated()` alone loses them and the four put()s are inert without an SA pass;
  * the raw tags are FRACTIONS: PercentageOfGrossNpa=0.0142 → 1.42% (the filed figure);
  * ⚠ ReturnOnAssets is CONTEXT-DEPENDENT — OneD (discrete quarter) 0.0047 = 0.47% vs FourD
    (cumulative YTD) 0.0143 = 1.43%. Reading the wrong context silently stores the YTD number as
    the quarterly RoA. That trap is the reason this suite exists.
  * NBFC/HFC (NBFC_INDAS) tag InterestEarned but NONE of the prudential block — so
    `_is_bank_instance` alone cannot gate the SA fetch; `_has_prudential_tags` does.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.automation.fundamentals_xbrl import (   # noqa: E402
    _has_prudential_tags, _is_bank_instance, augment_prudential,
    extract_bank_prudential, parse_instance,
)

_ONE_D = ('<context id="OneD"><entity><identifier scheme="s">x</identifier></entity>'
          '<period><startDate>2024-10-01</startDate><endDate>2024-12-31</endDate>'
          '</period></context>')
_FOUR_D = ('<context id="FourD"><entity><identifier scheme="s">x</identifier></entity>'
           '<period><startDate>2024-04-01</startDate><endDate>2024-12-31</endDate>'
           '</period></context>')


def _fact(name, v, ctx="OneD"):
    return f'<{name} contextRef="{ctx}" unitRef="INR" decimals="4">{v}</{name}>'


def _xbrl(*facts, contexts=(_ONE_D, _FOUR_D)):
    return ('<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            + "".join(contexts) + "".join(facts) + '</xbrl>')


def _hdfc_sa():
    """The REAL HDFCBANK Q3FY25 standalone values (probe-verified)."""
    return parse_instance(_xbrl(
        _fact("InterestEarned", 871825000000),
        _fact("PercentageOfGrossNpa", "0.0142"), _fact("PercentageOfGrossNpa", "0.0142", "FourD"),
        _fact("PercentageOfNpa", "0.0046"), _fact("PercentageOfNpa", "0.0046", "FourD"),
        _fact("ReturnOnAssets", "0.0047"), _fact("ReturnOnAssets", "0.0143", "FourD"),
        _fact("CET1Ratio", "0.1997"), _fact("CET1Ratio", "0.1997", "FourD"),
        _fact("AdditionalTier1Ratio", "0.00"),
    ))


def _hdfc_conso():
    """The REAL HDFCBANK Q3FY25 consolidated instance — the block is DECLARED but all-zero."""
    return parse_instance(_xbrl(
        _fact("InterestEarned", 871825000000),
        _fact("PercentageOfGrossNpa", "0.00"), _fact("PercentageOfNpa", "0.00"),
        _fact("ReturnOnAssets", "0.00"), _fact("CET1Ratio", "0.00"),
        _fact("AdditionalTier1Ratio", "0.00"),
    ))


def _nbfc():
    """NBFC_INDAS: tags InterestEarned (so it IS a 'bank instance') but no prudential block."""
    return parse_instance(_xbrl(_fact("InterestEarned", 100000000),
                                _fact("InterestExpended", 40000000)))


# ── extraction ────────────────────────────────────────────────────────────────────────
def test_standalone_instance_yields_filed_percents():
    m = extract_bank_prudential(_hdfc_sa(), kind="Q", end="2024-12-31")
    assert m["Gross NPA %"] == 1.42          # 0.0142 x100 — the filed figure
    assert m["Net NPA %"] == 0.46
    assert m["CET1 %"] == 19.97
    # AT1 is a genuine 0.00 for HDFCBANK -> non-zero-gated out (absent == not disclosed;
    # the CET1+AT1 CRAR proxy treats absent as zero, so nothing is lost)
    assert "Additional Tier 1 %" not in m


def test_roa_reads_the_discrete_quarter_not_the_ytd():
    """THE trap: RoA is 0.47% in OneD but 1.43% in FourD (cumulative). We must read the
    discrete quarter, consistent with extract_bank_for's P&L set."""
    m = extract_bank_prudential(_hdfc_sa(), kind="Q", end="2024-12-31")
    assert m["Return on Assets %"] == 0.47, "read the YTD context — the silent-wrong-number bug"


def test_consolidated_zeroes_yield_nothing():
    """A bank's conso instance reports 0.00 for all five — an artifact, never a disclosure."""
    assert extract_bank_prudential(_hdfc_conso(), kind="Q", end="2024-12-31") == {}


def test_annual_is_quarterly_only():
    assert extract_bank_prudential(_hdfc_sa(), kind="A", end="2024-12-31") == {}


def test_out_of_band_value_is_dropped_not_stored():
    """A filer tagging an already-percent 1.42 would x100 to 142% — implausible, so dropped
    rather than written into the fundamentals store."""
    p = parse_instance(_xbrl(_fact("InterestEarned", 1), _fact("PercentageOfGrossNpa", "1.42")))
    assert "Gross NPA %" not in extract_bank_prudential(p, kind="Q", end="2024-12-31")


# ── the bank-vs-NBFC discriminator (what gates the extra NSE round-trip) ──────────────
def test_declared_block_distinguishes_bank_from_nbfc():
    assert _has_prudential_tags(_hdfc_conso()) is True     # zeroed, but DECLARED -> a bank
    assert _has_prudential_tags(_hdfc_sa()) is True
    assert _has_prudential_tags(_nbfc()) is False          # NBFC never reports these
    # _is_bank_instance alone cannot make this call — an NBFC tags InterestEarned too
    assert _is_bank_instance(_nbfc()) is True


# ── augment: when do we spend an SA fetch? ────────────────────────────────────────────
def test_augment_falls_back_to_the_sa_sibling_when_conso_is_zeroed():
    calls = []

    def sa_lookup():
        calls.append(1)
        return _hdfc_sa()

    m = augment_prudential(_hdfc_conso(), kind="Q", end="2024-12-31", sa_lookup=sa_lookup)
    assert len(calls) == 1, "the zeroed conso bank MUST pull its standalone sibling"
    assert m["Gross NPA %"] == 1.42 and m["Return on Assets %"] == 0.47


def test_augment_does_not_fetch_when_the_instance_already_discloses():
    """AXISBANK's conso genuinely carried the ratios — no sibling round-trip needed."""
    calls = []
    m = augment_prudential(_hdfc_sa(), kind="Q", end="2024-12-31",
                           sa_lookup=lambda: calls.append(1) or _hdfc_sa())
    assert calls == [], "disclosed here — must not spend an NSE round-trip"
    assert m["CET1 %"] == 19.97


def test_augment_never_fetches_for_an_nbfc():
    """An NBFC declares no prudential block, so a sibling fetch could only ever be wasted."""
    calls = []
    m = augment_prudential(_nbfc(), kind="Q", end="2024-12-31",
                           sa_lookup=lambda: calls.append(1) or _hdfc_sa())
    assert calls == [] and m == {}


def test_augment_is_safe_without_a_lookup_or_on_a_failed_fetch():
    assert augment_prudential(_hdfc_conso(), kind="Q", end="2024-12-31") == {}
    assert augment_prudential(_hdfc_conso(), kind="Q", end="2024-12-31",
                              sa_lookup=lambda: None) == {}
