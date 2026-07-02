"""Golden regression tests for the rule-based scorer.

Audit provenance: this is the first content of the AUD-39 harness (there were zero
numeric tests on the computational core). It pins two confirmed audit fixes:

  * AUD-15 — the canonical Quality-Gate constants (code computes 252 / 151.2 from the
    pattern weights; the docs used to say 240 / 144).
  * AUD-09 — a loss-making name (PE <= 0) must earn NO valuation credit inside the
    Quality Gate, instead of reading as maximum cheapness.

Inputs are plain dicts, so this needs no DB and no numpy — it runs as gate-0 anywhere.
"""
from src.automation import scoring


def test_qg_constants_are_canonical():
    # Weights of QG patterns {1,2,3,4,5} = 9+9+8+8+8 = 42; QG_MAX = 42*6 = 252.
    assert scoring.QG_MAX == 252
    assert scoring.QG_THRESHOLD == 0.60 * 252  # 151.2
    assert scoring.MAX_CWS == sum(w * 6 for w in scoring.WEIGHTS.values()) == 582


def test_loss_maker_earns_no_valuation_credit():
    # AUD-09: negative PE is a loss-maker, not "cheap". Its Pattern-4 (Valuation) score
    # must be strictly below an otherwise-identical profitable-and-cheap name.
    loss = scoring.score_fundamentals({"symbol": "LOSS", "pe": -8.0, "pb": 1.0})
    cheap = scoring.score_fundamentals({"symbol": "CHEAP", "pe": 8.0, "pb": 1.0})
    assert loss["patterns"][4]["score"] < cheap["patterns"][4]["score"]
    # The loss-maker's PE signal is a hard 0 (verified), not a Partial re-credit.
    pe_signal = loss["patterns"][4]["signals"][0]
    assert pe_signal["raw"] == 0 and pe_signal["verified"] is True


def test_negative_book_value_also_zeroed():
    # A negative book value (PB <= 0) is likewise not cheapness.
    neg_pb = scoring.score_fundamentals({"symbol": "NEGBK", "pe": 30.0, "pb": -1.0})
    pb_signal = neg_pb["patterns"][4]["signals"][1]
    assert pb_signal["raw"] == 0 and pb_signal["verified"] is True


def test_hard_disqualifiers_fire():
    disq, reasons = scoring.check_hard_disqualifiers({"promoter_pledge": 35.0, "debt_to_equity": 3.0})
    assert disq is True
    assert len(reasons) == 2


def test_missing_valuation_is_partial_not_zero():
    # Absent PE/PB (None) is missing-data → Partial estimated (raw 1, unverified),
    # distinct from the loss-maker's verified 0. Guards against AUD-09 over-reaching.
    missing = scoring.score_fundamentals({"symbol": "NA"})
    pe_signal = missing["patterns"][4]["signals"][0]
    assert pe_signal["raw"] == 1 and pe_signal["verified"] is False
