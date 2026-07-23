"""test_home_reduced_motion.py — the reduced-motion gate (Codex #8/#10, spec §7/§8).

Under prefers-reduced-motion the token layer kills all animation/transition, and every JS animation
path checks the media query. The home leans on data reveals, not an ambient animated canvas.
"""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from src.web.home import components as C
from src.web.home import pat_dock
from src.web.home.tokens import tokens_css


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


def test_tokens_kill_animation_under_reduced_motion():
    css = tokens_css()
    assert "prefers-reduced-motion:reduce" in css
    assert "animation:none!important" in css and "transition:none!important" in css


def test_pat_and_component_js_check_the_media_query():
    for js in (pat_dock.dock_html(_conn()), C.assets()):
        assert 'matchMedia("(prefers-reduced-motion:reduce)")' in js


def test_home_has_no_animated_canvas():
    from src.main import app
    r = TestClient(app).get("/dash/home", follow_redirects=True)
    assert r.status_code == 200 and "<canvas" not in r.text
