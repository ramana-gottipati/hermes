"""AUD-01a perimeter guard — secret-gate the /conversations surface + the Tracker.

The /conversations GET/DELETE routes in main.py return Telegram transcripts
(PII) and allow deletes, unauthenticated (AUD-01). main.py is a frozen
contended file, so the guard lives HERE (new module) and main.py only gains a
2-line surgical mount, mirroring /chat's own CHAT_SHARED_SECRET semantics:
when the secret is UNSET the surface stays open (single-tenant LAN premise);
when set in .env, requests must carry a matching X-Hermes-Secret header
(constant-time compare). Same header name as /chat so one secret covers both.

P0-6 (S-A UX remediation, 2026-07-14): `/dash/tracker/*` renders the OWNER'S
LIVE PORTFOLIO (books, open MTM, gainers) and was publicly readable by any
anonymous visitor. Ramana chose "hide/gate now". Because the tracker is a
BROWSER surface (a header-only gate would lock the owner out too), it accepts
the shared secret via HEADER, COOKIE, or a one-time ``?hermes_key=`` query param
that sets the cookie — so the owner opens it once with the key and this browser
remembers it, while anonymous visitors get a minimal "private" page. Same
CHAT_SHARED_SECRET; when unset the tracker stays open (LAN premise unchanged).

Middleware, not route edits: the /conversations handlers and the /dash/tracker
handlers keep their exact signatures; main.py's frozen body and the forked
dashboard.py are untouched (D80 patch doctrine).
"""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from src.core.settings import settings

_GUARDED_PREFIX = "/conversations"
_TRACKER_PREFIX = "/dash/tracker"
_TRACKER_COOKIE = "hermes_key"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 180          # ~6 months

_PRIVATE_HTML = (
    "<!doctype html><html lang=en><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>Private surface</title>"
    "<style>body{font:16px/1.65 system-ui,-apple-system,'Segoe UI',sans-serif;color:#3a3f4b;"
    "background:#fafafb;margin:0}main{max-width:34rem;margin:14vh auto;padding:0 1.5rem}"
    "h1{font-size:1.35rem;color:#191c22;margin:0 0 .6rem}a{color:#c67c1e}"
    "@media(prefers-color-scheme:dark){body{background:#13151a;color:#9aa1b0}h1{color:#e7e9ed}}</style>"
    "<main><h1>This surface is private</h1><p>The tracker holds a live personal portfolio and is not "
    "publicly viewable. Explore the rest of the platform from <a href='/dash'>the dashboard</a>.</p></main>"
)


class ConversationsGuard(BaseHTTPMiddleware):
    """Secret-gate /conversations (header) and /dash/tracker (browser-friendly); no-store /dash HTML."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        secret = settings.chat_shared_secret

        # /conversations PII gate — API surface, header only (AUD-01a, unchanged).
        if path.startswith(_GUARDED_PREFIX) and secret:
            given = request.headers.get("x-hermes-secret") or ""
            if not hmac.compare_digest(given, secret):
                return JSONResponse(
                    {"detail": "missing or invalid X-Hermes-Secret"}, status_code=401)

        # Tracker gate — browser surface, accept secret via header / cookie / one-time param (P0-6).
        set_cookie = False
        if path.startswith(_TRACKER_PREFIX) and secret:
            param = request.query_params.get("hermes_key") or ""
            cookie = request.cookies.get(_TRACKER_COOKIE) or ""
            header = request.headers.get("x-hermes-secret") or ""
            if not any(v and hmac.compare_digest(v, secret) for v in (param, cookie, header)):
                return HTMLResponse(_PRIVATE_HTML, status_code=403)
            set_cookie = bool(param) and hmac.compare_digest(param, secret)

        response = await call_next(request)

        if set_cookie:                          # remember this browser so the owner needn't repeat the key
            response.set_cookie(_TRACKER_COOKIE, secret, max_age=_COOKIE_MAX_AGE,
                                httponly=True, samesite="lax")
        # Dynamic dashboard pages must never be served from a stale cache (old links survive a deploy).
        if path.startswith("/dash"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response
