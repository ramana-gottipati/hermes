"""test_pat_wolfe_flow.py — contracts for the open-Wolfe-setups flow (S150).

Guards the recognizer (wolfe cue + open/setup/trade cue), the snapshot read's graceful
degradation, and the engine.route wiring. The Pat eval battery is left UNCHANGED (a separate
suite) — this is additive, proof the flow steals nothing.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import wolfe_flow as WF          # noqa: E402
from src.pat import engine as ENGINE          # noqa: E402


def test_recognizes_open_wolfe_asks():
    assert WF.parse_wolfe("any wolfe setups")["flow"] == "wolfe"
    assert WF.parse_wolfe("open wolfe trades")["params"]["symbol"] == ""
    assert WF.parse_wolfe("show me the wolfe waves")["flow"] == "wolfe"
    assert WF.parse_wolfe("wolfe setup on TCS")["params"]["symbol"] == "TCS"
    assert WF.parse_wolfe("are there any wolfe waves running")["flow"] == "wolfe"


def test_yields_on_bare_or_non_wolfe():
    assert WF.parse_wolfe("wolfe") is None          # bare word → not us
    assert WF.parse_wolfe("harmonic setups") is None
    assert WF.parse_wolfe("what changed today") is None
    assert WF.parse_wolfe("") is None


def test_engine_routes_wolfe_inline_but_keeps_nav_for_page_asks():
    assert ENGINE.route("any wolfe setups") == {"flow": "wolfe", "params": {"symbol": ""}}
    assert ENGINE.route("wolfe setup on TCS")["flow"] == "wolfe"
    # a locational "where do I see wolfe" stays a navigate (nav pre-pass runs first)
    assert ENGINE.route("where do I see wolfe")["flow"] == "navigate"


def test_read_degrades_to_none_without_a_snapshot():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    assert WF.open_trades(c) is None            # no wolfe_open_signals snapshot → None
    assert WF.open_trades(None) is None
    c.close()


def test_freshness_badge():
    assert WF.is_fresh({"age": 3}) and WF.is_fresh({"age": 15})
    assert not WF.is_fresh({"age": 40}) and not WF.is_fresh({"age": None})


def test_selftest_passes():
    assert WF._selftest() == 0
