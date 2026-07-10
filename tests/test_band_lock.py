"""X-05 band-lock regression (S96c) — the module's hermetic selftest as a gate-0 test.

The selftest builds an in-memory DB and asserts the load-bearing math: band-at-date
reconstruction through the change log (incl. the pre-FEED_BIRTH empty guard), upper/lower
lock detection with the unbanded-name exclusion, streak walking, and the ≥2d flag rule.
One source of assertions (band_lock.selftest) — this wrapper just makes pytest own it.
"""
from src.automation.band_lock import selftest


def test_band_lock_selftest():
    assert selftest() == 0
