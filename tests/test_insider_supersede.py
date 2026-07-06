"""Golden test for AUD-08 — revised insider filings must supersede, not double-count.

aggregate() takes plain event dicts, so this needs no DB. It pins that a Revised filing
(amendment_flag=1, corrected value, same person/date/type) replaces the original in the
promoter-cashflow roll-up, while genuinely distinct same-day trades are NOT merged.
"""
from src.automation import insider_events as ie


def _ev(person, txn_dt, value, *, amend=0, parsed="2025-01-11"):
    return {
        "disclosure_dt": "2025-01-15", "transaction_dt": txn_dt,
        "person_name_hash": person, "txn_type_raw": "buy",
        "txn_class": ie.OPEN_MARKET_BUY, "category": "Promoter",
        "value_rs": value, "amendment_flag": amend, "parsed_at": parsed,
    }


def test_revision_supersedes_not_double_counts():
    orig = _ev("P1", "2025-01-10", 100.0, amend=0, parsed="2025-01-11")
    revised = _ev("P1", "2025-01-10", 120.0, amend=1, parsed="2025-01-14")  # same nk, corrected
    other = _ev("P2", "2025-01-10", 50.0)                                   # distinct person
    agg = ie.aggregate([orig, revised, other], as_of="2025-01-31")
    # revision replaces original (120, NOT 100+120); plus the distinct 50 → 170, not 270.
    assert agg["net_promoter_cashflow_90d"] == 170.0
    assert agg["promoter_cluster_buy_30d"] == 2  # two distinct persons, not three rows


def test_distinct_same_day_trades_not_merged():
    # No amendment anywhere → two genuinely separate trades must both count.
    a = _ev("P1", "2025-01-10", 100.0)
    b = _ev("P1", "2025-01-10", 40.0)
    agg = ie.aggregate([a, b], as_of="2025-01-31")
    assert agg["net_promoter_cashflow_90d"] == 140.0
