"""test_home_isolation.py — the Graphite Home isolation gate (spec §1/§7).

Proves, permanently, that the fresh-and-parallel `/dash/home` section is fully separated from BOTH
the classic site AND the existing v3 preview: no import coupling, scoped markers in both directions,
route-gate registered, never linked from default chrome, and rendered without the legacy chrome
markers the middleware keys on (so `shell_skin`/`left_rail` can never reshape it).
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
HOME_DIR = ROOT / "src" / "web" / "home"

# the preview / legacy render modules the home must NEVER import
BANNED = ("today_v3", "news_dock", "shell_v3", "ui_tokens_v3", "ui_components_v3", "ui_showcase_v3",
          "v3_preview", "stock_hub_v3", "hub_sections_v3", "stock_chart_v3", "ui_skin_bold",
          "term_chip", "dashboard", "shell_skin", "left_rail")

GRAPHITE_MARKERS = ("data-ui-g", "g-tokens graphite", "pvg")
PREVIEW_LEGACY_MARKERS = ("data-ui-v3", "uk-tokens v3", "pv3-", "pv3chip", "uk-sub", 'id="uk-main"')


def _app():
    from src.main import app
    return app


def test_home_imports_no_preview_or_legacy_render_module():
    offenders = []
    for py in HOME_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        for mod in BANNED:
            if re.search(r"^\s*(from|import)\s+[\w.]*\b" + mod + r"\b", text, re.M):
                offenders.append(py.name + " -> " + mod)
    assert not offenders, offenders


def test_home_page_carries_graphite_marker_and_no_preview_legacy_markers():
    client = TestClient(_app())
    r = client.get("/dash/home", follow_redirects=True)
    assert r.status_code == 200, r.status_code
    assert "data-ui-g" in r.text and "PREVIEW" in r.text
    for m in PREVIEW_LEGACY_MARKERS:
        assert m not in r.text, ("home leaked a preview/legacy marker", m)


def test_classic_and_preview_pages_carry_no_graphite_markers():
    """Both-directions collision gate (Codex #8): Graphite must not leak onto legacy OR preview."""
    client = TestClient(_app())
    for path in ("/dash/glossary", "/dash/coverage", "/dash/preview"):
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        for m in GRAPHITE_MARKERS:
            assert m not in r.text, (path, m)


def test_home_routes_are_route_gate_registered():
    from tests import test_dash_route_registry as gate
    for path in ("/dash/home", "/dash/home/_kit"):
        assert path in gate.INTERNAL_DEV, path
        owner, rationale = gate.INTERNAL_DEV[path]
        assert owner and rationale


def test_default_chrome_never_links_the_home():
    client = TestClient(_app())
    for path in ("/dash", "/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert "/dash/home" not in r.text, path


def test_home_toggle_is_post_only():
    client = TestClient(_app())
    assert client.get("/dash/home/toggle").status_code == 405
    r = client.post("/dash/home/toggle", follow_redirects=False)
    assert r.status_code == 303 and r.cookies.get("pvg") == "1"


def test_home_kit_renders():
    client = TestClient(_app())
    r = client.get("/dash/home/_kit")
    assert r.status_code == 200 and "data-ui-g" in r.text and "g-chip" in r.text
