"""The `/v1` endpoints — wiring only. Each: a fail-closed scope dep -> a resources.* read
-> a stamped envelope. Honesty + entitlement + metering are enforced upstream (deps,
envelope, middleware), so a new endpoint inherits them by construction.

Scope to the HONEST faces (red-team sequencing verdict): the compliance/data-feed reads
(coverage, universe, registry, health) are live; the ALPHA reads (credibility, attention)
are gated behind HERMES_V1_ALPHA=1 (default OFF) and return 501 until the §C lead-time
backtest + data-licensing land — the entitlement split is still provable (a compliance key
gets 403 before the gate is ever reached).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.db import get_conn
from src.api.v1 import resources as R
from src.api.v1 import envelope as E
from src.api.v1.auth import require_scope, Principal

router = APIRouter()


def _alpha_enabled() -> bool:
    return os.environ.get("HERMES_V1_ALPHA") == "1"


def _rid(request: Request):
    return getattr(request.state, "request_id", None)


def _scope(request: Request):
    return getattr(request.state, "scope_used", None)


@router.get("/meta/health", tags=["meta"])
def health(request: Request, p: Principal = Depends(require_scope("health"))):
    with get_conn() as conn:
        h = R.health(conn)
        return E.ok(conn, data=h, classes=[], principal=p, request_id=_rid(request),
                    coverage="freshness / liveness probe", degraded=h["degraded"], scope_used=_scope(request))


@router.get("/coverage", tags=["compliance"])
def coverage(request: Request, p: Principal = Depends(require_scope("coverage"))):
    with get_conn() as conn:
        snap = R.coverage(conn)
        return E.ok(conn, data=snap, classes=["survivorship"], principal=p, request_id=_rid(request),
                    coverage=(snap.get("cci", {}) or {}).get("paused_note", ""),
                    degraded=R.is_degraded(snap), scope_used=_scope(request))


@router.get("/universe", tags=["compliance"])
def universe(request: Request, as_of: str | None = None,
            p: Principal = Depends(require_scope("universe"))):
    with get_conn() as conn:
        u = R.universe(conn, as_of=as_of)
        return E.ok(conn, data=u, classes=["survivorship"], principal=p, request_id=_rid(request),
                    coverage="survivorship-correct universe-as-of (delisted retained); see disclosures",
                    degraded=(u.get("status") == "security_master_empty"), scope_used=_scope(request))


@router.get("/provenance/registry", tags=["compliance"])
def provenance_registry(request: Request, p: Principal = Depends(require_scope("provenance_registry"))):
    data = {"registry": R.registry()}
    return E.ok(None, data=data, classes=[], principal=p, request_id=_rid(request),
                coverage="the per-data-class provenance registry (resolve _provenance keys here)",
                scope_used=_scope(request))


@router.get("/securities/{symbol}/credibility", tags=["alpha"])
def credibility(symbol: str, request: Request, p: Principal = Depends(require_scope("credibility"))):
    if not _alpha_enabled():
        raise HTTPException(501, "credibility (alpha tier) is gated on the §C lead-time backtest "
                                 "+ data-licensing; not yet served")
    with get_conn() as conn:
        sym, latest = R.credibility(conn, symbol)
        if not latest:
            data = {"symbol": sym,
                    "credibility": E.absence(f"no settled credibility for {sym} (unproven / not covered)")}
            return E.ok(conn, data=data, classes=["cci_series"], principal=p, request_id=_rid(request),
                        prov_kw={"cci_series": {"symbol": sym}},
                        coverage="credibility from the settled subset only", degraded=True, scope_used=_scope(request))
        cred = {k: latest.get(k) for k in ("level", "tier", "momentum", "n_resolved", "trend", "period_label")}
        nres = latest.get("n_resolved") or 0
        if nres < 10:        # robustness floor — never present a bare level as if proven
            cred = {**cred, "robust": False,
                    "caveat": f"n_resolved={nres} — NOT robust (needs >=10); descriptor only, not a track record"}
        else:
            cred["robust"] = True
        data = {"symbol": sym, "credibility": cred,
                "note": "percentile rank-gap / descriptor — UNBACKTESTED, not a performance claim"}
        return E.ok(conn, data=data, classes=["cci_series"], principal=p, request_id=_rid(request),
                    prov_kw={"cci_series": {"symbol": sym, "as_of": latest.get("period_label")}},
                    coverage="PIT credibility (descriptive, unbacktested)", scope_used=_scope(request))


@router.get("/attention", tags=["alpha"])
def attention(request: Request, limit: int = 6, p: Principal = Depends(require_scope("attention"))):
    if not _alpha_enabled():
        raise HTTPException(501, "attention queue (alpha tier) is gated on the §C lead-time backtest "
                                 "+ data-licensing; not yet served")
    with get_conn() as conn:
        q = R.attention(conn, limit=limit)
        return E.ok(conn, data={"attention": q}, classes=["signal_events"], principal=p, request_id=_rid(request),
                    coverage="typed state-change events (descriptors, not signals to trade)",
                    scope_used=_scope(request))
