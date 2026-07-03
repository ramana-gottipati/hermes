"""AUD-01a perimeter guard — secret-gate the /conversations surface.

The /conversations GET/DELETE routes in main.py return Telegram transcripts
(PII) and allow deletes, unauthenticated (AUD-01). main.py is a frozen
contended file, so the guard lives HERE (new module) and main.py only gains a
2-line surgical mount, mirroring /chat's own CHAT_SHARED_SECRET semantics:
when the secret is UNSET the surface stays open (single-tenant LAN premise);
when set in .env, requests must carry a matching X-Hermes-Secret header
(constant-time compare). Same header name as /chat so one secret covers both.

Middleware, not route edits: the three /conversations handlers keep their
exact signatures and main.py's frozen body is untouched (D80 patch doctrine).
"""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.settings import settings

_GUARDED_PREFIX = "/conversations"


class ConversationsGuard(BaseHTTPMiddleware):
    """401 any /conversations request without the shared secret (when one is set)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(_GUARDED_PREFIX):
            secret = settings.chat_shared_secret
            if secret:
                given = request.headers.get("x-hermes-secret") or ""
                if not hmac.compare_digest(given, secret):
                    return JSONResponse(
                        {"detail": "missing or invalid X-Hermes-Secret"}, status_code=401)
        response = await call_next(request)
        # Dynamic dashboard pages must never be served from a stale cache: the
        # responses carry no ETag/Last-Modified, so a browser that cached an OLD
        # /dash page keeps its OLD links (e.g. a Stealth card still pointing at
        # `/dash/stocks` without `?view=stealth`) even after a deploy. Tell the
        # browser not to store /dash HTML so a fresh page (and fresh links) always
        # loads. (Static assets are served elsewhere and unaffected.)
        if request.url.path.startswith("/dash"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response
