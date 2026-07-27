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
    # `data-ui-g` is the real Graphite marker. (The badge said "PREVIEW" until the 2026-07-27 landing
    # cutover made this the default landing — a "PREVIEW" badge on a live front door is misleading
    # chrome, so it now reads "NEW". The marker, not the badge copy, is what this gate protects.)
    assert "data-ui-g" in r.text
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


def test_classic_pages_never_link_the_home():
    """The anti-drift contract, post-cutover. Classic LENS pages still carry zero Graphite links —
    no classic page was edited to know the new home exists. What changed on 2026-07-27 is only the
    LANDING: bare `/dash` now 302s to `/dash/home` (owner decision, mechanism (b)), and the classic
    home keeps its own preserved URL at `/dash/classic` — which must itself stay Graphite-free."""
    client = TestClient(_app())
    for path in ("/dash/classic", "/dash/glossary", "/dash/coverage"):
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        assert "/dash/home" not in r.text, path


def test_landing_cutover_redirects_dash_and_preserves_the_classic_home():
    """The cutover itself: `/dash` → the Graphite home (302, never a cacheable 301 — the rollback
    must stay possible), while `/dash/classic` still renders the untouched classic home."""
    client = TestClient(_app())
    r = client.get("/dash", follow_redirects=False)
    assert r.status_code == 302, r.status_code
    assert r.headers["location"] == "/dash/home"
    c = client.get("/dash/classic")
    assert c.status_code == 200 and 'id="uk-main"' in c.text, "classic home must survive at /dash/classic"
    landed = client.get("/dash", follow_redirects=True)
    assert "data-ui-g" in landed.text, "following /dash must land on the Graphite home"


def test_cutover_is_unpluggable():
    """Removing the single install() call restores the previous landing — no other change. Proven by
    building an app WITHOUT the middleware and seeing classic serve /dash again."""
    from fastapi import FastAPI
    from src.web import dashboard
    bare = FastAPI()
    bare.include_router(dashboard.router)
    r = TestClient(bare).get("/dash", follow_redirects=False)
    assert r.status_code == 200, "without the cutover middleware, /dash must serve classic directly"


def test_classic_site_directory_bundles_the_whole_registry_one_way():
    """The top-right 'Classic site' dropdown lists EVERY classic lens, generated from the canonical
    lens_registry (single source → can't drift), as one-way links. The classic site is untouched;
    the directory never links back to /dash/home (that would break the never-links-home contract)."""
    from src.web.home import shell
    from src.web import lens_registry as LR
    html = shell.shell("Home", "<p>x</p>")
    assert 'class="g-classic"' in html and "Classic site" in html
    missing = [ln.route for ln in LR.LENSES if ln.route and ln.route not in html]
    assert not missing, ("the classic directory dropped registry routes", missing[:5])
    # the directory routes come from lens_registry, which has no /dash/home lens → one-way by construction
    assert not any((ln.route or "") == "/dash/home" for ln in LR.LENSES)


def test_home_toggle_is_post_only():
    client = TestClient(_app())
    assert client.get("/dash/home/toggle").status_code == 405
    r = client.post("/dash/home/toggle", follow_redirects=False)
    assert r.status_code == 303 and r.cookies.get("pvg") == "1"


def test_home_kit_renders():
    client = TestClient(_app())
    r = client.get("/dash/home/_kit")
    assert r.status_code == 200 and "data-ui-g" in r.text and "g-chip" in r.text
