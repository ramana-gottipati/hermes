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

# ── SELF-CONTAINMENT: a symbol click must never eject the reader into classic ──────
# Since the D148 landing cutover the Graphite home is the DEFAULT landing, so a classic
# `/dash/stock?sym=` deep-link inside the package is a one-way door OUT of the new experience and
# into classic chrome. Every symbol surface in `src/web/home/` resolves to `/dash/home/stock?sym=`.
#
# The lookahead is load-bearing in two directions, and both were live traps here:
#   • `/dash/stocks` — the classic Stocks WORKSPACE, carried by `shell.DESTS` and by the one-way
#     classic directory — merely shares a prefix and is NOT an offender.
#   • Prose that names the classic route in a docstring (components.sym_link explains the retarget
#     in backticks) documents the contract rather than violating it.
# So the match requires a URL terminator (`?`, `"` or `'`): the route being USED as a link target.
CLASSIC_DOSSIER_LINK = re.compile(r"""/dash/stock(?=[?"'])""")

# The ONE declared exception, keyed on its own CSS marker so it cannot silently widen: the stock
# page's explicit, labelled "Full classic view →" affordance. That is an opt-in the reader chooses
# deliberately — not a symbol deep-link that ejects them by surprise — and it is the escape hatch
# the cutover promised when it retargeted the home's own links. Anything else is a regression.
ESCAPE_HATCH_FILE = "stock_view.py"
ESCAPE_HATCH_MARKER = "g-sc-classic"
_ESCAPE_HATCH_ANCHOR = re.compile(r"<a class=\"g-sc-classic\"[^>]*>.*?</a>", re.S)


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


def test_no_home_module_deep_links_the_classic_dossier():
    """PACKAGE-WIDE self-containment (source). Every module under `src/web/home/` — not just the
    ones a given lane happened to own — must send a symbol to the Graphite stock page. Scoping this
    per-lane is what let `pat_dock`'s typed-box deep-link keep pointing at classic long after the
    shared `components.sym_link`/`_hm_tile` had been retargeted: three call sites, one contract."""
    offenders = []
    for py in sorted(HOME_DIR.rglob("*.py")):
        for n, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not CLASSIC_DOSSIER_LINK.search(line):
                continue
            if py.name == ESCAPE_HATCH_FILE and ESCAPE_HATCH_MARKER in line:
                continue                                   # the one declared escape hatch
            offenders.append(f"{py.name}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "a Graphite module deep-links the CLASSIC dossier — a symbol click would eject the reader "
        "out of the new experience. Use `/dash/home/stock?sym=` (components.sym_link).", offenders)


def test_the_classic_escape_hatch_still_exists_and_is_the_only_one():
    """The exception is a real, LABELLED affordance — not a loophole. If the stock page ever drops its
    'Full classic view →' link this fails too, so the allowance can't outlive what it allows.

    This also keeps the rendered gate HONEST. On a box whose `stock_signals` is empty the stock page
    has no core to render, so the escape hatch never appears and the strip in the rendered gate would
    pass vacuously — proving nothing. Rendering from an explicit core here exercises the real anchor
    on every box, so the allowance is verified against output, not just against source text."""
    from src.web.home import stock_view
    src = (HOME_DIR / ESCAPE_HATCH_FILE).read_text(encoding="utf-8", errors="replace")
    hatch = [ln for ln in src.splitlines() if ESCAPE_HATCH_MARKER in ln and CLASSIC_DOSSIER_LINK.search(ln)]
    assert len(hatch) == 1, ("expected exactly ONE declared classic escape hatch", hatch)
    assert "Full classic view" in hatch[0], "the escape hatch must stay explicitly LABELLED"

    core = {"symbol": "TCS", "close": 3900.5, "pct": 1.2, "date": "2026-07-24",
            "industry": "IT", "signals": {}}
    html = stock_view.stock_page(core, {}, {}, {}, "TCS")
    anchors = _ESCAPE_HATCH_ANCHOR.findall(html)
    assert len(anchors) == 1, ("the rendered stock page must carry exactly one escape hatch", anchors)
    assert "Full classic view" in anchors[0]
    classic = re.findall(r"""href=["'](/dash/stock(?:\?[^"']*)?)["']""", html)
    assert classic == ["/dash/stock?sym=TCS"], ("the hatch is the page's ONLY classic link", classic)
    assert not re.findall(r"""href=["'](/dash/stock(?:\?[^"']*)?)["']""",
                          _ESCAPE_HATCH_ANCHOR.sub("", html)), "stripping the hatch must leave none"


def test_rendered_home_pages_carry_no_classic_symbol_deep_links():
    """PACKAGE-WIDE self-containment (rendered) — the journey, not just the source. Walks every
    Graphite GET route and asserts the delivered HTML routes symbols inward. Strips the declared
    escape-hatch anchor first, so the page keeps its one labelled way out and nothing more.

    This does NOT subsume the source gate above, and neither is redundant — verified by reverting
    the fix: Pat builds its anchor in JS (`a.setAttribute("href", …)`), so a classic deep-link there
    never appears as a literal `href=` in delivered HTML and ONLY the source scan caught it. Server-
    rendered leaks are the mirror case. Delete either one and a real regression walks through."""
    client = TestClient(_app())
    for path in ("/dash/home", "/dash/home/rotation", "/dash/home/stock",
                 "/dash/home/stock?sym=TCS", "/dash/home/_kit"):
        r = client.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        stripped = _ESCAPE_HATCH_ANCHOR.sub("", r.text)
        # same boundary discipline as CLASSIC_DOSSIER_LINK: `/dash/stocks` (the Stocks workspace
        # in the nav + the one-way classic directory) shares a prefix and is legitimate chrome.
        leaked = sorted(set(re.findall(r"""href=["'](/dash/stock(?:\?[^"']*)?)["']""", stripped)))
        assert not leaked, (path, "leaked a classic dossier deep-link", leaked)


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
