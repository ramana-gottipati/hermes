"""Patearn `/v1` — the entitled, metered, provenance-stamped read layer ("one bus, four faces").

`build_app()` returns a self-contained FastAPI sub-app to MOUNT at /v1. The 1-line, GATED
hook in main.py (deferred until the parallel web layer frees) is:

    import os
    if os.environ.get("HERMES_V1_ENABLED") == "1":
        from src.api.v1 import build_app
        app.mount("/v1", build_app())

A mounted sub-app gives /v1 its own OpenAPI, its own exception handlers (RFC-7807), and a
scoped middleware (request-id, metering, RateLimit-* headers) — without touching the host app.
Strangler-fig: it consumes the existing modules read-only via resources.py; it rewrites nothing.
"""
from __future__ import annotations

import logging
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.api.v1.routes import router
from src.api.v1 import envelope as E
from src.api.v1.metering import record_usage

log = logging.getLogger("hermes.v1")

__all__ = ["build_app"]


def build_app() -> FastAPI:
    app = FastAPI(title="Patearn /v1", version=E.METHODOLOGY_VERSION,
                  description=(
                      "Entitled, metered, provenance-stamped Indian-equity read API.\n\n"
                      "**PIT semantics (AUD-38/D104):** `/universe`, `/securities/{symbol}/credibility` "
                      "and `/attention` accept `as_of=YYYY-MM-DD` and serve what was KNOWABLE on "
                      "that date — credibility by the two-tier knowable rule (the period's REAL "
                      "public clock — concall held / transcript published — when captured, basis "
                      "EVENT; else the month's last calendar day, basis MODELED; the served row "
                      "carries `knowable_from` + `knowable_basis`), attention by resolving to the "
                      "last computed event batch on-or-before the date. The same `as_of` always "
                      "returns the same answer, so clients can run their own leak audits. Every "
                      "response is additionally stamped with `_meta.as_of` + per-class provenance, "
                      "with or without the parameter."))

    def _meter(request: Request, *, status: int, bytes_out, latency_ms: int, rid: str) -> None:
        p = getattr(request.state, "principal", None)
        record_usage(tenant_id=getattr(p, "tenant_id", None), key_id=getattr(p, "key_id", None),
                     endpoint=request.url.path, path=str(request.url), status=status,
                     bytes_out=bytes_out, latency_ms=latency_ms,
                     scope_used=getattr(request.state, "scope_used", None), request_id=rid)

    def _stamp(response, request: Request, rid: str) -> None:
        response.headers["X-Request-ID"] = rid
        rate = getattr(request.state, "rate", None)
        if rate:
            response.headers["RateLimit-Limit"] = str(rate[0])
            response.headers["RateLimit-Remaining"] = str(max(0, rate[0] - rate[1]))

    @app.middleware("http")
    async def _observe(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = rid
        t0 = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            # AUD-37: an unhandled error propagates to ServerErrorMiddleware (OUTSIDE this
            # middleware), so without this the 500 was NEVER metered — breaking the "one row
            # per request incl. 5xx" audit guarantee. Meter it (bytes unknown — the RFC-7807
            # body is produced downstream), then re-raise so _any_problem still responds.
            _meter(request, status=500, bytes_out=None,
                   latency_ms=int((monotonic() - t0) * 1000), rid=rid)
            raise
        latency = int((monotonic() - t0) * 1000)
        _stamp(response, request, rid)
        # AUD-37: a BaseHTTPMiddleware wrapper exposes the body as a STREAM (no `.body`), so
        # the old getattr(response,"body") was b"" → bytes_out=0 on EVERY row. Content-Length
        # is set on the JSON responses /v1 serves and preserved through the wrapper.
        try:
            body_len = int(response.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            body_len = 0
        _meter(request, status=response.status_code, bytes_out=body_len, latency_ms=latency, rid=rid)
        return response

    @app.exception_handler(HTTPException)
    async def _http_problem(request: Request, exc: HTTPException):
        rid = getattr(request.state, "request_id", None) or uuid4().hex
        title = exc.detail if isinstance(exc.detail, str) else "request error"
        resp = JSONResponse(status_code=exc.status_code,
                            content=E.problem(exc.status_code, title, request_id=rid),
                            media_type="application/problem+json")
        _stamp(resp, request, rid)   # 4xx pass back through _observe too, but stamp defensively
        return resp

    @app.exception_handler(Exception)
    async def _any_problem(request: Request, exc: Exception):
        # AUD-36: str(exc) went to the CLIENT verbatim (sqlite paths / SQL fragments on an
        # internet-facing surface). Full detail now stays server-side keyed by request id;
        # the client gets a generic detail + the id to quote.
        # AUD-37: this response is produced ABOVE _observe (ServerErrorMiddleware), so it
        # must carry X-Request-ID / RateLimit itself — _observe never sees it.
        rid = getattr(request.state, "request_id", None) or uuid4().hex
        log.exception("v1 unhandled error request_id=%s path=%s", rid, request.url.path)
        resp = JSONResponse(status_code=500,
                            content=E.problem(500, "internal error",
                                              "unexpected error — quote this request id when reporting",
                                              request_id=rid),
                            media_type="application/problem+json")
        _stamp(resp, request, rid)
        return resp

    app.include_router(router)
    return app
