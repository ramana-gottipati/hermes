"""x_setups_signals (S205) — the nightly pre-compute persist/read round-trip as a gate-0 test.

The selftest builds an in-memory DB and asserts the load-bearing plumbing: DELETE+INSERT
materialisation, per-module rank ordering, payload JSON round-trip, a zero-hit module still
producing a VALID snapshot + meta counts, and idempotency (a second persist replaces, not
appends). No bhavcopy needed. One source of assertions — this wrapper makes pytest own it.
"""
from src.automation.x_setups_signals import selftest


def test_x_setups_signals_selftest():
    assert selftest() == 0
