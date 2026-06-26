"""
v2_surfaces.py — durable, idempotent wiring of the Patearn v2 website surfaces.

This is the SINGLE SOURCE OF TRUTH for mounting the trust-first v2 surfaces and
integrating them into the live site navigation. It supersedes the earlier
hand-appended blocks in ``main.py`` / ``dashboard.py`` (which were VPS-only and
fragile — a parallel chart-session redeploy of those files would silently wipe
the Coverage tab and unmount the routes, leaving them orphaned).

Why a module instead of inline appends
--------------------------------------
* The router mounts AND the nav integration live in ONE committed file -> durable.
* ``main.py`` needs only a 2-line hook::

      from src.web import v2_surfaces
      v2_surfaces.wire(app)

  re-applied idempotently by ``scripts/wire_v2_surfaces.py`` after any clobber.
* ``dashboard.py`` needs ZERO v2 edits. The nav is wrapped at runtime by mutating
  the imported dashboard module's ``_nav`` / ``_WS`` globals; the page handlers
  resolve ``_nav`` as a module global at call time, so they pick up the wrap
  automatically on every app start. A chart-session redeploy of ``dashboard.py``
  therefore cannot remove the wrap (it isn't *in* dashboard.py).

Properties
----------
* DEFENSIVE — every step is isolated in try/except; a bad module is skipped
  (logged) and never fatal to the live app (the preserve-everything doctrine).
* IDEMPOTENT — safe to call ``wire(app)`` more than once (sentinel + per-route /
  per-link presence checks); safe even alongside a residual hand-appended block.
* ADAPTIVE — if dashboard exposes ``_SUBNAV`` (the newer repo structure) the RS
  hub + News land in the Markets sub-nav (IA-correct, ui-architecture-v2 §0.1);
  on the older flat-nav VPS build they land as reachable top-nav tabs so the v2
  surfaces are NEVER orphaned (the integrate-not-orphan lesson).
* ADDITIVE — never edits or removes an existing route or nav entry; the sacred
  routes (/dash/ratio, /dash/rrg, /dash/compare) are untouched.

Surfaces wired (all already built + committed as isolated modules):
  /dash/coverage   coverage_view.py  — the Coverage & Settlement ledger (lead wedge)
  /dash/rs-hub     rs_section.py      — the Markets-altitude Relative-Strength hub
  /dash/news       news_view.py      — per-stock News/Timeline
  /dash/wire       news_view.py      — the watchlist Market Wire
  /v1              src.api.v1        — the entitled/metered "one bus, four faces" API
"""

from __future__ import annotations

import importlib
import logging

log = logging.getLogger("hermes.v2")

# Sentinel attribute set on the dashboard module once its _nav has been wrapped,
# so a second wire() call (or a residual hook) cannot double-wrap.
_NAV_SENTINEL = "_v2_nav_wrapped"

# (label-key, module path, a sample route path to test for prior mount)
_ROUTER_SPECS = [
    ("coverage", "src.web.coverage_view", "/dash/coverage"),
    ("rs-hub", "src.web.rs_section", "/dash/rs-hub"),
    ("news", "src.web.news_view", "/dash/wire"),
]


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


def _install_nav() -> None:
    """Wrap dashboard._nav (and enrich _SUBNAV when present) at runtime."""
    import src.web.dashboard as D

    if getattr(D, _NAV_SENTINEL, False):
        return
    if not hasattr(D, "_nav"):
        log.warning("v2 nav skipped: dashboard._nav not found")
        return

    orig_nav = D._nav
    has_subnav = isinstance(getattr(D, "_SUBNAV", None), dict)

    # Workspace map so the correct base tab / sub-nav highlights. On the sub-nav
    # build, RS/News belong to the Markets altitude; on the flat build they get
    # their own top-tab highlight.
    try:
        if has_subnav:
            D._WS.update({"coverage": "coverage", "rs-hub": "markets",
                          "wire": "markets", "news": "markets"})
        else:
            D._WS.update({"coverage": "coverage", "rs-hub": "rs-hub",
                          "wire": "news", "news": "news"})
    except Exception as e:  # noqa: BLE001
        log.warning("v2 _WS update skipped: %s", e)

    def _wrapped_nav(active):
        html = orig_nav(active)
        links = []
        if not has_subnav:
            # flat VPS build: surface RS + News as reachable top tabs (never orphan)
            links.append(("/dash/rs-hub", "Relative strength", active == "rs-hub"))
            links.append(("/dash/wire", "News", active in ("wire", "news")))
        # Coverage is the lead trust/compliance wedge -> a top tab on both builds.
        links.append(("/dash/coverage", "Coverage", active == "coverage"))
        frag = "".join(
            f'<a class="{"on" if act else ""}" href="{href}">{label}</a>'
            for href, label, act in links
            if f'href="{href}"' not in html  # idempotent: never double-add a link
        )
        return html.replace("</div>", frag + "</div>", 1) if frag else html

    D._nav = _wrapped_nav

    # IA-correct placement on the newer (sub-nav) structure.
    if has_subnav:
        try:
            mk = D._SUBNAV.setdefault("markets", [])
            existing = {it[1] for it in mk if len(it) >= 2 and it[1]}
            for item in (({"rs-hub"}, "/dash/rs-hub", "Relative strength"),
                         ({"wire", "news"}, "/dash/wire", "News")):
                if item[1] not in existing:
                    mk.append(item)
        except Exception as e:  # noqa: BLE001
            log.warning("v2 sub-nav enrich skipped: %s", e)

    setattr(D, _NAV_SENTINEL, True)


def wire(app):
    """Mount the v2 routes + integrate them into the nav. Idempotent + defensive."""
    _mount_routers(app)
    _mount_v1(app)
    try:
        _install_nav()
    except Exception as e:  # noqa: BLE001 — nav integration must never break import
        log.warning("v2 nav install skipped: %s", e)
    return app


def _selftest() -> int:
    """Mount on a throwaway app + assert the v2 surfaces are reachable and in-nav."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import src.web.dashboard as D

    app = FastAPI()
    app.include_router(D.router)
    wire(app)
    wire(app)  # second call must be a no-op (idempotency)

    c = TestClient(app)
    for path in ("/dash/coverage", "/dash/rs-hub", "/dash/wire", "/dash/news"):
        code = c.get(path).status_code
        assert code == 200, f"{path} -> {code}"

    # Coverage is a top tab on every build -> present on the home shell.
    home = c.get("/dash").text
    assert "/dash/coverage" in home, "Coverage link missing from nav"
    # On the sub-nav build the RS hub appears in the Markets sub-nav.
    if isinstance(getattr(D, "_SUBNAV", None), dict):
        markets = c.get("/dash/markets").text
        assert "/dash/rs-hub" in markets, "RS hub missing from Markets sub-nav"
        # idempotency: the coverage link must not be duplicated
        assert home.count('href="/dash/coverage"') == 1, "Coverage link duplicated"
    print("v2_surfaces selftest OK "
          f"(_SUBNAV={'yes' if isinstance(getattr(D, '_SUBNAV', None), dict) else 'no'})")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
