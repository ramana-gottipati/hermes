"""
v2_surfaces.py — durable wiring of the v2 surfaces + the canonical navigation IA.

Single source of truth for (a) mounting the v2 surfaces (Coverage, RS hub, News, /v1)
and (b) the SITE NAVIGATION. It replaces the old flat "dump every lens on the top bar"
nav with the altitudes-vs-lenses model (docs/ui-architecture-v2.md §3), grounded in how
the best institutional products are built (Koyfin ~5 sections, Morningstar 3 modules,
FactSet pinned apps): a few PRIMARY destinations on top, every analytical LENS one level
down in a contextual sub-nav, Pat as a global ⌘K summon, Coverage as a "Trust" utility.

Why a module (not edits to dashboard.py)
----------------------------------------
* main.py needs only a 2-line hook (`from src.web import v2_surfaces; v2_surfaces.wire(app)`),
  re-applied idempotently by scripts/wire_v2_surfaces.py after any clobber.
* dashboard.py needs ZERO edits: the nav is REPLACED at runtime by rebinding the imported
  dashboard module's `_nav` (and neutralising its legacy `_subnav`); page handlers resolve
  `_nav` as a module global at call time, so they pick up the new chrome on every start. A
  chart-session redeploy of dashboard.py therefore cannot break it.

Properties: DEFENSIVE (each step try/except, never fatal) · IDEMPOTENT (sentinel) ·
NO-LOSS (any destination the old nav exposed that the IA doesn't home falls into a "More"
group — nothing is dropped; the sacred routes /dash/ratio, /dash/rrg, /dash/compare keep
their URLs) · ADDITIVE + REVERSIBLE (restore the previous file + restart).
"""

from __future__ import annotations

import importlib
import logging
import re

log = logging.getLogger("hermes.v2")

# Sentinel set on the dashboard module once its _nav has been replaced (no double-wrap).
_NAV_SENTINEL = "_v2_nav_wrapped"

# (label-key, module path, a sample route path to test for prior mount)
_ROUTER_SPECS = [
    ("coverage", "src.web.coverage_view", "/dash/coverage"),
    ("rs-hub", "src.web.rs_section", "/dash/rs-hub"),
    ("news", "src.web.news_view", "/dash/wire"),
]

# ── the canonical site IA — the single source of the top menu ────────────────
# Altitudes = the top bar (a place you go). Each altitude's sub-nav = its lenses /
# sections (how you evaluate — NEVER an altitude tab). Pat = a global summon (Ask
# Pat ⌘K); Coverage = a "Trust" utility — both right-side, not altitude tabs.
_IA_ALT = [
    ("markets", "/dash/markets", "Markets"),
    ("screener", "/dash/screener", "Screener"),
    ("strategies", "/dash/strategies", "Strategies"),
    ("tracker", "/dash/dashboard", "Tracker"),
]
_IA_SUB = {
    "markets": [
        ("markets", "/dash/markets", "Overview"),
        ("sectors", "/dash/sectors", "Sectors"),
        ("rs-hub", "/dash/rs-hub", "Relative strength"),
        ("rrg", "/dash/rrg", "Rotation · Map"),
        ("rotation", "/dash/rotation", "Rotation · Weather"),
        ("rsband", "/dash/rsband", "Rotation · Band"),
        ("participants", "/dash/participants", "Participants"),
        ("wire", "/dash/wire", "News / Wire"),
        ("compare", "/dash/compare", "Compare"),
    ],
    "screener": [
        ("screener", "/dash/screener", "Screen"),
        ("themes", "/dash/themes", "Themes / Baskets"),
        ("tags-review", "/dash/tags-review", "Review"),
        ("workbench", "/dash/workbench", "Workbench"),
    ],
    "strategies": [
        ("strategies", "/dash/strategies", "Hub"),
        ("conviction", "/dash/conviction", "Conviction"),
        ("stocks", "/dash/stocks", "Positioning"),
        ("mep", "/dash/mep", "Accumulation"),
        ("cpr", "/dash/cpr", "Structure"),
        ("leaders", "/dash/leaders", "Strength"),
        ("concalls", "/dash/concalls", "Credibility"),
        ("growth", "/dash/growth", "Growth-intent"),
        ("wolfe", "/dash/wolfe/scan", "Wolfe"),
        ("launchpad", "/dash/launchpad", "Launchpad"),
        ("testing", "/dash/testing", "Lab"),
    ],
    "tracker": [
        ("dashboard", "/dash/dashboard", "Dashboard"),
        ("portfolios", "/dash/portfolios", "Portfolios"),
        ("watchlists", "/dash/watchlists", "Watchlists"),
        ("performance", "/dash/performance", "Performance"),
        ("import", "/dash/import", "Import"),
    ],
}
# sub-nav key -> the set of route `active` values that should highlight it
_SUB_ALIAS = {
    "sectors": {"sectors", "rs"}, "stocks": {"stocks", "scan", "stock"},
    "leaders": {"leaders", "laggards"}, "wire": {"wire", "news"},
    "themes": {"themes", "theme"}, "wolfe": {"wolfe"},
    "dashboard": {"dashboard", "tracker", "track"},
}
# route `active` value -> its altitude (top-bar highlight + which sub-nav renders).
_ALT_OF: dict[str, str] = {}
for _a, _its in _IA_SUB.items():
    for _k, _h, _l in _its:
        _ALT_OF[_k] = _a
        for _alias in _SUB_ALIAS.get(_k, ()):
            _ALT_OF[_alias] = _a
_ALT_OF.update({"ratio": "markets", "coverage": "trust"})

# every href the IA already homes (the no-loss known set).
_KNOWN_HREFS = ({h for _k, h, _l in _IA_ALT}
                | {h for _its in _IA_SUB.values() for _k, h, _l in _its}
                | {"/dash/coverage", "/dash/pat", "/dash/ratio", "/dash/news"})

_NAV_LINK_RE = re.compile(r'<a [^>]*href="([^"]+)">([^<]+)</a>')

_V2NAV_CSS = """<style>
.v2bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:2px}
.v2bar .wsnav{flex:0 1 auto}
.v2util{margin-left:auto;display:flex;align-items:center;gap:8px}
.v2util a,.v2util .v2askpat{font:inherit;font-size:12.5px;cursor:pointer;text-decoration:none;
  border:1px solid #2b3a52;background:#0d1117;color:#9fb0c3;border-radius:8px;padding:6px 11px}
.v2util a.on,.v2util a:hover,.v2util .v2askpat:hover{border-color:#1f6feb;color:#e6edf3}
.v2askpat kbd{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;background:#1b2230;
  border:1px solid #2b3a52;border-radius:4px;padding:1px 5px;margin-left:6px;color:#9fb0c3}
.v2subnav{display:flex;gap:4px;flex-wrap:wrap;padding:7px 0 0;margin:0 0 4px;
  border-bottom:1px solid #21262d;overflow-x:auto}
.v2subnav a{font-size:12.5px;color:#8b949e;text-decoration:none;padding:5px 10px;
  border-radius:7px 7px 0 0;white-space:nowrap}
.v2subnav a:hover{color:#e6edf3;background:#161b22}
.v2subnav a.on{color:#e6edf3;background:#161b22;font-weight:600;border-bottom:2px solid #1f6feb}
</style>"""


def _route_paths(app) -> set[str]:
    out: set[str] = set()
    for r in getattr(app, "routes", []):
        p = getattr(r, "path", None)
        if p:
            out.add(p)
    return out


def _mount_routers(app) -> None:
    """include_router for each v2 view module, skipping any already present."""
    have = _route_paths(app)
    for desc, mod_path, sample in _ROUTER_SPECS:
        try:
            if sample in have:
                continue
            mod = importlib.import_module(mod_path)
            app.include_router(mod.router)
            have = _route_paths(app)
        except Exception as e:  # noqa: BLE001 — a bad module must never be fatal
            log.warning("v2 router skipped (%s): %s", desc, e)


def _mount_v1(app) -> None:
    """Mount the /v1 service layer (the compliance/data-feed + SDK/MCP bus face)."""
    try:
        if "/v1" in _route_paths(app):
            return
        from src.api.v1 import build_app  # local import: optional dependency

        app.mount("/v1", build_app())
    except Exception as e:  # noqa: BLE001
        log.warning("v2 /v1 mount skipped: %s", e)


def _altitude_of(active) -> str | None:
    """Which altitude (markets/screener/strategies/tracker), the 'trust' utility, or
    None, the given route `active` value belongs to."""
    a = (active or "").strip().lower()
    if a in _ALT_OF:
        return _ALT_OF[a]
    try:
        import src.web.dashboard as D
        ws = D._WS.get(a, a)
        if ws == "themes":
            return "screener"
        if ws in ("markets", "screener", "strategies", "tracker"):
            return ws
    except Exception:  # noqa: BLE001
        pass
    return None


def _install_nav() -> None:
    """Replace dashboard._nav (at runtime) with the canonical 4-altitude IA chrome:
    a clean top bar + Ask-Pat/Trust utilities + a contextual sub-nav, so lenses live
    UNDER altitudes instead of cluttering the top bar. Gate-safe, reversible, no-loss."""
    import src.web.dashboard as D

    if getattr(D, _NAV_SENTINEL, False):
        return
    if not hasattr(D, "_nav"):
        log.warning("v2 nav skipped: dashboard._nav not found")
        return
    orig_nav = D._nav

    # highlight hints for any other dashboard code path that reads _WS
    try:
        D._WS.update({"coverage": "coverage", "rs-hub": "markets", "wire": "markets",
                      "news": "markets", "participants": "markets", "growth": "strategies",
                      "wolfe": "strategies", "testing": "strategies"})
    except Exception as e:  # noqa: BLE001
        log.warning("v2 _WS update skipped: %s", e)

    def _wrapped_nav(active):
        alt = _altitude_of(active)
        tabs = "".join(f'<a class="{"on" if alt == k else ""}" href="{h}">{lbl}</a>'
                       for k, h, lbl in _IA_ALT)
        # NO-LOSS: any destination the original nav exposed that the IA doesn't home
        # is preserved in a trailing "More" group, so a future route is never dropped.
        extra, seen = "", set()
        try:
            unknown = []
            for href, label in _NAV_LINK_RE.findall(orig_nav(active)):
                if href not in _KNOWN_HREFS and href not in seen:
                    seen.add(href)
                    unknown.append((href, label))
            if unknown:
                extra = "".join(f'<a href="{h}">{l}</a>' for h, l in unknown)
        except Exception:  # noqa: BLE001
            extra = ""
        util = ('<div class="v2util">'
                f'<a class="{"on" if alt == "trust" else ""}" href="/dash/coverage" '
                'title="Data coverage &amp; provenance">Trust</a>'
                '<button class="v2askpat" type="button" data-cmdk>Ask Pat <kbd>⌘K</kbd></button>'
                '</div>')
        top = f'<div class="v2bar"><nav class="wsnav v2nav">{tabs}{extra}</nav>{util}</div>'
        sub = ""
        items = _IA_SUB.get(alt)
        if items:
            links = "".join(
                f'<a class="{"on" if (active == k or active in _SUB_ALIAS.get(k, {k})) else ""}" '
                f'href="{h}">{lbl}</a>' for k, h, lbl in items)
            sub = f'<div class="v2subnav">{links}</div>'
        out = _V2NAV_CSS + top + sub
        try:
            from src.web import ui_kit as _K
            out += _K.cmdk_overlay()
        except Exception:  # noqa: BLE001 — the overlay is additive; never break the nav
            pass
        return out

    D._nav = _wrapped_nav
    # our nav renders its own sub-nav; neutralise the legacy _subnav to avoid a double.
    if hasattr(D, "_subnav"):
        try:
            D._subnav = lambda active="": ""
        except Exception:  # noqa: BLE001
            pass
    setattr(D, _NAV_SENTINEL, True)


def site_nav(active: str = ""):
    """The nav destination list for the v2 (ui_kit) chrome (e.g. Coverage): the four
    altitudes + the Trust utility, highlight-aware. ONE IA, two renderers."""
    alt = _altitude_of(active)
    items = [(h, lbl, alt == k) for k, h, lbl in _IA_ALT]
    items.append(("/dash/coverage", "Trust", alt == "trust"))
    return items


def wire(app):
    """Mount the v2 routes + install the canonical nav. Idempotent + defensive."""
    _mount_routers(app)
    _mount_v1(app)
    try:
        _install_nav()
    except Exception as e:  # noqa: BLE001 — nav install must never break import
        log.warning("v2 nav install skipped: %s", e)
    return app


def _selftest() -> int:
    """Mount on a throwaway app + assert the clean IA renders, is no-loss, idempotent."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import src.web.dashboard as D

    app = FastAPI()
    app.include_router(D.router)
    wire(app)
    wire(app)  # idempotent

    c = TestClient(app)
    for path in ("/dash/coverage", "/dash/rs-hub", "/dash/wire", "/dash/news"):
        assert c.get(path).status_code == 200, path

    # Test the nav RENDERER directly (no page render -> no data/route-mount dependency;
    # route liveness of every sub-nav target is verified separately on the VPS).
    home = D._nav("dash")
    for _k, h, lbl in _IA_ALT:                       # the 4 altitudes present
        assert f'href="{h}"' in home, f"altitude missing: {lbl}"
    assert "v2askpat" in home and 'href="/dash/coverage"' in home, "utilities missing"
    assert home.count('class="v2bar"') == 1, "nav rendered more than once (not idempotent)"
    # the OLD clutter must be GONE from the top bar (growth/wolfe/themes are now sub-nav)
    top_bar = home.split('class="v2subnav"')[0]
    for gone in ('>Growth<', '>Wolfe wave<', '>Themes<', '>News<', '>Relative strength<'):
        assert gone not in top_bar, f"lens still on top bar: {gone}"

    # every altitude renders its lenses as a contextual sub-nav (no-loss presence)
    for alt, items in _IA_SUB.items():
        nav = D._nav(alt if alt != "tracker" else "dashboard")
        for _k, h, _l in items:
            assert f'href="{h}"' in nav, f"{alt} sub-nav missing {h}"
    print("v2_surfaces selftest OK — 4 altitudes + contextual sub-nav + utilities; "
          "lenses off the top bar; no-loss; idempotent")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
