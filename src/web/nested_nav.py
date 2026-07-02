"""Registry-driven URL nesting (D80): the canonical public URL for every workspace
sub-page is ``/dash/<workspace>/<page>`` so the address mirrors the nav hierarchy —
Strategies › MEP is ``/dash/strategies/mep``, Screener › Screen+ is
``/dash/screener/screen2``, Tracker › Performance is ``/dash/tracker/performance``.

ONE engine, applied uniformly from ``src.web.lens_registry`` (the single source), so no
workspace is nested piecemeal and any lens a session adds is nested automatically.
Additive + reversible + DEFENSIVE: the flat ``/dash/<page>`` URL is kept alive as a 307
redirect (query string preserved) so no existing link / bookmark / internal redirect
breaks, and if the route surgery fails for any reason the app still boots on the
original flat routes (never a 500).
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.web import lens_registry as _LR

log = logging.getLogger("hermes.nested_nav")

# Workspaces whose sub-pages carry a nested /dash/<altitude>/<page> URL. Trust is a
# 2-item right-side utility with a hard-coded /dash/coverage tab href — left flat.
NEST_ALTITUDES = frozenset({"markets", "screener", "strategies", "tracker"})

_DONE = "_nested_nav_installed"


def nested_path(ln) -> str | None:
    """The canonical (nested) URL for a lens. Pure + idempotent:
      * overlay-only lens (route is None)                 -> None
      * altitude not nested (e.g. trust)                  -> its flat route, unchanged
      * the workspace-root landing (route == /dash/<alt>) -> kept flat (the section root)
      * already nested (route startswith /dash/<alt>/)    -> unchanged (e.g. Tracker)
      * everything else                                   -> /dash/<altitude>/<key>
    """
    route = ln.route
    if route is None:
        return None
    alt = ln.altitude
    if alt not in NEST_ALTITUDES:
        return route
    if route == f"/dash/{alt}" or route.startswith(f"/dash/{alt}/"):
        return route
    return f"/dash/{alt}/{ln.key}"


def _mk_redirect(dest: str):
    """A GET handler that 307-redirects to ``dest`` with the original query preserved."""
    def _redirect(request: Request, _dest: str = dest) -> RedirectResponse:
        q = request.url.query
        return RedirectResponse(_dest + (f"?{q}" if q else ""), status_code=307)
    return _redirect


def nest_routes(app) -> None:
    """For every routed lens, mount the nested canonical route (serving the SAME handler
    that already lives at the flat path) and make the flat path 307-redirect to it.

    Removal-free by design: the nested serving route is APPENDED, and the flat→nested
    redirect is INSERTED AT THE FRONT of the route list so it wins over the original
    flat handler without deleting it. That is robust to re-mounts / double-``wire()``
    (a re-added flat handler still sits behind the front redirect) and leaves the app
    working on flat routes if anything fails. Idempotent (app-level guard) + defensive
    (per-lens try/except)."""
    if getattr(app, _DONE, False):
        return
    try:
        from fastapi.routing import APIRoute
        routes = app.router.routes
        by_path = {r.path: r for r in routes if isinstance(r, APIRoute)}
        nested_added, flat_redirected = set(), set()
        for ln in _LR.LENSES:
            try:
                flat = ln.route
                nested = nested_path(ln)
                if not flat or not nested or nested == flat:
                    continue
                src = by_path.get(flat)
                if src is None:
                    continue  # handler not mounted here → leave the lens on its flat URL
                # 1) serve the page at the nested URL (append). Lens handlers return
                #    explicit Response objects, so response_class is a formality.
                if nested not in by_path and nested not in nested_added:
                    app.add_api_route(nested, src.endpoint, methods=["GET"],
                                      response_class=HTMLResponse, include_in_schema=False,
                                      name=f"nested_{ln.key}")
                    nested_added.add(nested)
                # 2) flat -> 307 redirect to nested, inserted at the FRONT so it wins
                #    over the (retained) flat handler. Query string preserved.
                if flat not in flat_redirected:
                    rr = APIRoute(flat, _mk_redirect(nested), methods=["GET"],
                                  include_in_schema=False, name=f"compat_{ln.key}")
                    routes.insert(0, rr)
                    flat_redirected.add(flat)
            except Exception as e:  # noqa: BLE001 — one lens must never break the rest
                log.warning("nest_routes: skipped lens %s: %s",
                            getattr(ln, "key", "?"), e)
        setattr(app, _DONE, True)
        log.info("nest_routes: nested %d lens routes", len(nested_added))
    except Exception as e:  # noqa: BLE001 — nesting is additive; never break boot
        log.warning("nest_routes disabled: %s", e)
