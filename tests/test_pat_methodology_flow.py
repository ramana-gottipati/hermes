"""test_pat_methodology_flow.py — contracts for the strategy-methodology explain flow (S150 Ph3).

Guards the recognizer (methodology cue + strategy name; does NOT steal the glossary explain
of a bare term, nor the wolfe data flow), the sanitized summary extraction (no governance/ID/
"Ramana" leakage), and engine.route wiring. Pat eval battery left UNCHANGED.
"""
from __future__ import annotations

import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import methodology_flow as MF     # noqa: E402
from src.pat import engine as ENGINE           # noqa: E402
from src.web import strategies_view as SV       # noqa: E402


def test_recognizes_methodology_asks():
    assert MF.parse_methodology("explain the wolfe methodology")["params"]["slug"] == "wolfe-wave"
    assert MF.parse_methodology("how does CPR work")["params"]["slug"] == "cpr"
    assert MF.parse_methodology("what's the DVPT idea")["params"]["slug"] == "dvpt"
    assert MF.parse_methodology("explain the reversal strategy")["params"]["slug"] == "reversal-context"
    assert MF.parse_methodology("walk me through harmonic patterns")["params"]["slug"] == "harmonic"
    assert MF.parse_methodology("explain the union strategy")["params"]["slug"] == "union"
    assert MF.parse_methodology("what's the union ladder concept")["params"]["slug"] == "union-ladder"
    assert MF.parse_methodology("how does sector rotation work")["params"]["slug"] == "sector-rotation"
    assert MF.parse_methodology("explain the rule lab idea")["params"]["slug"] == "rule-lab"
    # bare "rotation" stays with the momentum engine hooks, not the sector page
    assert MF.parse_methodology("how does the rotation engine work")["params"]["slug"] == "momentum-riskadj"


def test_every_served_page_is_reachable_by_a_methodology_ask():
    """Every methodology page must have at least one recognizer hook — a summary nobody
    can ask for is dead knowledge (the union/ladder/sector-rotation/rule-lab gap, S188)."""
    hooked = {slug for slug, _hooks in MF._SLUG_HOOKS}
    for slug in SV._PAGES:
        if slug in ("origins",):
            continue
        assert slug in hooked, f"{slug} has a served page but no _SLUG_HOOKS entry"


def test_does_not_steal_glossary_or_data_asks():
    assert MF.parse_methodology("what is DVPT") is None       # bare term → glossary explain
    assert MF.parse_methodology("any wolfe setups") is None   # data flow
    assert MF.parse_methodology("explain the quantum strategy") is None
    assert MF.parse_methodology("") is None


def test_engine_routing_respects_precedence():
    assert ENGINE.route("explain the wolfe methodology")["flow"] == "methodology"
    assert ENGINE.route("how does the wolfe wave work")["flow"] == "methodology"  # before wolfe data flow
    assert ENGINE.route("what is DVPT")["flow"] == "explain"                      # bare term glossary
    assert ENGINE.route("any wolfe setups")["flow"] == "wolfe"                    # data flow intact


def test_summary_is_plain_and_sanitized_for_every_page():
    banned = ("Ramana", "Governing decision", "do not archive", "Reconciled:")
    for slug in SV._PAGES:
        if slug in ("origins",):
            continue  # a governance index, not a methodology page
        s = MF.summary(slug)
        assert s is not None, f"no summary for {slug}"
        assert len(s["plain"]) > 40 and s["link"] == f"/dash/strategy-ref?p={slug}"
        for b in banned:
            assert b not in s["plain"], f"{slug} leaked {b!r}"
        assert not re.search(r"\b[SD]\d{2,3}[a-z]?\b", s["plain"]), f"{slug} leaked a session/decision id"
        # the extractor is line-anchored: a WRAPPED one-liner ships a mid-sentence fragment
        # (the union page, S188) — every summary must read as a complete sentence
        assert s["plain"].rstrip().endswith((".", "…", ")")), f"{slug} summary is a fragment: …{s['plain'][-60:]!r}"


def test_wolfe_methodology_answers_in_plain_words():
    """The audit done-bar: 'explain the Wolfe methodology' → a plain-language answer."""
    s = MF.summary("wolfe-wave")
    assert s and ("5-pivot" in s["plain"] or "reversal" in s["plain"])


def test_selftest_passes():
    assert MF._selftest() == 0
