"""src/web/home/cutover.py — the LANDING CUTOVER (owner decision 2026-07-27, mechanism (b)).

Makes the Graphite home the site's default landing and demotes the classic dashboard into the
"Classic site" directory that the Graphite chrome already carries.

WHY A MIDDLEWARE (and not an edit to `dashboard.py`): the standing rule is that classic source is
never edited and every change ships as a NEW, unpluggable module (S177 revert). This intercepts two
paths at the ASGI layer, ahead of routing, and touches no classic file:

    GET /dash          → 302 to /dash/home      (the new default landing)
    GET /dash/classic  → internally rewritten to /dash, so the classic home still renders
                         BYTE-IDENTICALLY at a preserved, linkable URL

Everything else passes through untouched — every classic lens keeps its own URL and its own output.

REVERSIBILITY (deliberate): the redirect is **302, never 301** — a permanent redirect would be cached
by browsers and make a rollback effectively impossible. Removing the single `install(app)` call
restores the previous landing instantly, with no other change.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

LANDING = "/dash/home"        # the new default landing
CLASSIC_ALIAS = "/dash/classic"   # the classic home's preserved URL
CLASSIC_REAL = "/dash"            # what the classic home handler is actually registered as


class LandingCutover:
    """A minimal pure-ASGI middleware (no body buffering — it only rewrites/redirects paths)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        method = (scope.get("method") or "GET").upper()
        if path == CLASSIC_REAL and method in ("GET", "HEAD"):
            from starlette.responses import RedirectResponse
            qs = scope.get("query_string") or b""
            target = LANDING + (("?" + qs.decode("latin-1")) if qs else "")
            # 302 (temporary) — see the module docstring: never 301, so this stays revertible.
            await RedirectResponse(target, status_code=302)(scope, receive, send)
            return
        if path == CLASSIC_ALIAS:
            scope = dict(scope)
            scope["path"] = CLASSIC_REAL
            if scope.get("raw_path"):
                scope["raw_path"] = CLASSIC_REAL.encode("latin-1")
        await self.app(scope, receive, send)


def install(app) -> bool:
    """Install once. Idempotent + defensive — a failure here must never break app wiring (the site
    simply keeps the old landing)."""
    try:
        if getattr(app.state, "_landing_cutover", False):
            return True
    except Exception:  # noqa: BLE001 — a stateless app object: fall through and add once
        pass
    try:
        app.add_middleware(LandingCutover)
        try:
            app.state._landing_cutover = True
        except Exception:  # noqa: BLE001
            pass
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("landing cutover skipped: %s", e)
        return False
