"""test_home_persona.py — the Free ⇄ Pro TIER gate (formerly the Beginner/Pro persona).

The tier control is a real toggle (aria-pressed, persisted). FREE shows the guided explainers
(`.free-only`); PRO hides them (denser) AND reveals the premium relative-context blocks (`.pro-more`)
— the reference points that make a bare number decision-useful. A distinct DOM per tier, not a label
swap. (Preview only — the switch previews both tiers; it's the entitlement seam for later.)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.web.home import components as C


def _home() -> str:
    from src.main import app
    r = TestClient(app).get("/dash/home", follow_redirects=True)
    assert r.status_code == 200
    return r.text


def test_tier_control_present_with_aria_pressed():
    h = _home()
    assert 'id="g-tfree"' in h and 'id="g-tpro"' in h
    assert 'aria-pressed="true"' in h and 'data-tier="free"' in h


def test_tier_mechanism_produces_distinct_dom_per_tier():
    h = _home()
    assert '[data-tier="free"] .free-only{display:revert}' in h    # Free reveals guided explainers
    assert '[data-tier="pro"] .pro-more{display:revert}' in h      # Pro reveals premium context
    assert "free-only" in h and "pro-more" in h                    # both layers present in the DOM


def test_tier_persists_across_visits():
    h = _home()
    assert "pvgtier" in h and 'setAttribute("data-tier"' in h


def test_learn_is_free_tier_and_pro_more_is_pro_tier():
    assert "free-only" in C.learn("FII means foreign institutions.")
    assert "pro-more" in C.pro_more("<span>context</span>") and "context" in C.pro_more("<span>context</span>")
