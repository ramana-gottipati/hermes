"""test_preview_retired.py — the PREVIEW RETIREMENT contract (cutover lane W6, 2026-07-27).

The redesign M0-M5 preview estate (`/dash/preview` · `/dash/preview/stock` · `/dash/_ui3` + the
hub's series-CSV child) was de-routed once the Graphite estate became the default landing (D148).
Owner OK for the retirement is on record in commit `3d13d97`.

What this gate holds, permanently:
  1. RETIRED — none of the four old URLs still serves a preview PAGE; each answers a 302 to its
     Graphite twin, so every old bookmark lands somewhere real instead of on a 404.
  2. TEMPORARY, never permanent — 302, never 301. A cached permanent redirect would make the
     rollback (restore the four `_ROUTER_SPECS` tuples) effectively impossible. Same reasoning
     D148 recorded for the landing switch itself.
  3. UNPLUGGABLE — the retirement is ONE router module + ONE mount tuple, and the preview render
     modules are still importable (de-routed, not deleted), so the revert is mechanical.
  4. `sym` SURVIVES the hop — a `/dash/preview/stock?sym=X` bookmark reaches the same company on
     the Graphite stock page, with the symbol URL-quoted (the `M&M` bug class stays dead).
  5. The retired POST toggle is GONE, not redirected — it gated an opt-in that no longer exists.

Deleted alongside this file's arrival (recorded so the count change is never a mystery):
`tests/test_v3_today.py` (11 tests) and `tests/test_v3_stock_hub.py` (18) asserted the RENDERED
preview surfaces, which no longer serve; their one still-live contract — legacy pages carry no hub
markers and link no preview URL — moved into `tests/test_v3_isolation.py`.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

RETIRED_PAGES = {
    "/dash/preview": "/dash/home",
    "/dash/preview/stock": "/dash/home/stock",
    "/dash/preview/stock/export": "/dash/home/stock",
    "/dash/_ui3": "/dash/home/_kit",
}


def _client() -> TestClient:
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    return TestClient(M.app)


def test_every_retired_preview_url_redirects_to_its_graphite_twin():
    c = _client()
    for path, twin in RETIRED_PAGES.items():
        r = c.get(path, follow_redirects=False)
        assert r.status_code == 302, (path, r.status_code, "must be a TEMPORARY redirect")
        assert r.headers["location"] == twin, (path, r.headers.get("location"))


def test_the_redirects_are_never_permanent():
    """301 is cacheable and would strand the rollback — the same argument D148 made for `/dash`."""
    c = _client()
    for path in RETIRED_PAGES:
        assert c.get(path, follow_redirects=False).status_code != 301, path


def test_following_a_retired_url_lands_on_a_real_graphite_page():
    """A redirect that points at a 404 is worse than a 404 — walk the hop end to end."""
    c = _client()
    for path in RETIRED_PAGES:
        r = c.get(path, follow_redirects=True)
        assert r.status_code == 200, (path, r.status_code)
        assert "data-ui-g" in r.text, (path, "must land inside the Graphite identity")


def test_the_stock_bookmark_carries_its_symbol_url_quoted():
    """`sym` is the one query key worth carrying; `&` in a ticker must be URL-quoted, not escaped
    (the live `M&M` / `ARE&M` bug class the W1 review fixed on the Graphite page)."""
    c = _client()
    r = c.get("/dash/preview/stock", params={"sym": "M&M"}, follow_redirects=False)
    assert r.headers["location"] == "/dash/home/stock?sym=M%26M", r.headers.get("location")
    r = c.get("/dash/preview/stock/export", params={"sym": "tcs"}, follow_redirects=False)
    assert r.headers["location"] == "/dash/home/stock?sym=TCS", r.headers.get("location")
    # a symbol-less bookmark must still land on the picker, never on `?sym=`
    assert c.get("/dash/preview/stock", follow_redirects=False
                 ).headers["location"] == "/dash/home/stock"


def test_the_preview_opt_in_toggle_is_gone_not_redirected():
    """POST `/dash/preview/toggle` set the `pv3` opt-in cookie. The opt-in no longer exists and a
    POST endpoint is not a bookmark class, so it is de-routed outright."""
    c = _client()
    assert c.post("/dash/preview/toggle", follow_redirects=False).status_code == 404
    assert c.get("/dash/preview/toggle", follow_redirects=False).status_code == 404


def test_no_preview_page_module_is_mounted_any_more():
    """The de-routing is real: no route in the app is served by a preview render module."""
    import src.main as M
    from src.web import v2_surfaces
    v2_surfaces.wire(M.app)
    retired_modules = {"src.web.v3_preview", "src.web.ui_showcase_v3", "src.web.stock_hub_v3",
                       "src.web.stock_chart_v3", "src.web.today_v3", "src.web.news_dock"}
    offenders = [(r.path, getattr(r.endpoint, "__module__", ""))
                 for r in M.app.routes
                 if getattr(r, "endpoint", None) is not None
                 and getattr(r.endpoint, "__module__", "") in retired_modules]
    assert not offenders, offenders
    # and the mount tuples are gone from the durable spec table
    specs = {m for _d, m, _s in v2_surfaces._ROUTER_SPECS}
    assert not (specs & retired_modules), sorted(specs & retired_modules)


def test_pat_never_sends_anyone_to_a_retired_preview_url():
    """The dock answers nav questions from `lens_registry` (via `src.pat.nav_flow`) and then
    upgrades any route with a live Graphite twin through `pat_dock._GRAPHITE_TWIN`. The preview
    surfaces were never lenses, so by construction Pat cannot name one — asserted, not assumed,
    because "by construction" is exactly the kind of claim that quietly stops being true."""
    from src.web import lens_registry as LR
    from src.web.home import pat_dock

    routes = {ln.route for ln in LR.LENSES if ln.route}
    assert not [r for r in routes if r.startswith(("/dash/preview", "/dash/_ui3"))], routes
    twins = set(pat_dock._GRAPHITE_TWIN.values()) | set(pat_dock._GRAPHITE_TWIN)
    assert not [t for t in twins if t.startswith(("/dash/preview", "/dash/_ui3"))], sorted(twins)
    # the markets overview — what `/dash/preview` used to BE — resolves to the Graphite home
    assert pat_dock._GRAPHITE_TWIN["/dash/markets"] == "/dash/home"
    # and the dock's own typed-symbol door is the Graphite stock page, not the retired hub
    src = pat_dock.__file__
    text = open(src, encoding="utf-8").read()
    assert "/dash/preview" not in text, "the Pat dock still names a retired preview URL"


def test_the_retirement_is_unpluggable_and_the_modules_survive():
    """De-routed, NOT deleted: every preview module still imports, so restoring the four
    `_ROUTER_SPECS` tuples is the entire revert."""
    import importlib
    for mod in ("src.web.v3_preview", "src.web.ui_showcase_v3", "src.web.stock_hub_v3",
                "src.web.stock_chart_v3", "src.web.today_v3", "src.web.shell_v3",
                "src.web.hub_sections_v3", "src.web.news_dock", "src.web.term_chip"):
        m = importlib.import_module(mod)
        assert m is not None, mod
    from src.web import v2_surfaces
    from src.web.home import preview_retired
    specs = [s for s in v2_surfaces._ROUTER_SPECS if s[1] == "src.web.home.preview_retired"]
    assert len(specs) == 1, ("exactly one mount tuple owns the retirement", specs)
    assert set(preview_retired.RETIRED) == set(RETIRED_PAGES)
