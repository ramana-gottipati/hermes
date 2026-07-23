"""test_home_persona.py — the Beginner⇄Pro persona gate (Codex #3, spec §7/§8).

The persona control is a real toggle (aria-pressed, persisted); Beginner adds plain-English
explainers that are persona-gated so Pro renders denser — a distinct DOM per persona, not just a
label swap.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.web.home import components as C


def _home() -> str:
    from src.main import app
    r = TestClient(app).get("/dash/home", follow_redirects=True)
    assert r.status_code == 200
    return r.text


def test_persona_control_present_with_aria_pressed():
    h = _home()
    assert 'id="g-mnew"' in h and 'id="g-mpro"' in h
    assert 'aria-pressed="true"' in h and 'data-persona="new"' in h


def test_persona_mechanism_produces_distinct_dom_per_persona():
    h = _home()
    # the CSS mechanism that makes Beginner and Pro render differently
    assert '[data-persona="new"] .new-only{display:revert}' in h
    assert '[data-persona="pro"] .pro-only' in h
    assert "new-only" in h                                   # beginner explainer content is present + gated


def test_persona_persists_across_visits():
    h = _home()
    assert "pvgmode" in h and 'setAttribute("data-persona"' in h


def test_learn_component_is_beginner_only():
    out = C.learn("FII means foreign institutions.")
    assert "new-only" in out and "foreign institutions" in out
