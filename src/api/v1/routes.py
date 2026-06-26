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

from fastapi import APIRouter, Depends, Request

from src.core.db import get_conn
from src.api.v1 import resources as R
from src.api.v1 import envelope as E
from src.api.v1.auth import require_scope, Principal

router = APIRouter()

# §C FALSIFIED the credibility return edge (docs/product-strategy-2026.md §9): CCI survives ONLY
# as a DESCRIPTIVE per-name diligence lens, never a ranked buy/sell signal. Client-facing labels
# drop A+/A/B/C/D -> strong/mixed/weak/unproven (n_resolved<3 => unproven).
_CRED_NOTE = ("DESCRIPTIVE guidance track-record for diligence in confluence — §C-backtested: NO "
              "validated return edge. NOT a recommendation, NOT a ranked buy/sell signal.")


def _track_record(tier, n_resolved, ga) -> str:
    if ga is None or (n_resolved or 0) < 3:
        return "unproven"
    return {"A+": "strong", "A": "strong", "B": "mixed", "C": "weak", "D": "weak"}.get(tier, "mixed")


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


@router.get("/securities/{symbol}/credibility", tags=["research"])
def credibility(symbol: str, request: Request, p: Principal = Depends(require_scope("credibility"))):
    """DESCRIPTIVE per-name guidance track-record (the §C-surviving use). Never ranked; no edge claim."""
    with get_conn() as conn:
        sym, latest = R.credibility(conn, symbol)
        if not latest:
            data = {"symbol": sym,
                    "credibility": E.absence(f"no settled credibility for {sym} (unproven / not covered)"),
                    "note": _CRED_NOTE}
            return E.ok(conn, data=data, classes=["cci_series"], principal=p, request_id=_rid(request),
                        prov_kw={"cci_series": {"symbol": sym}},
                        coverage="descriptive credibility track-record (no validated return edge — §C); settled subset only",
                        degraded=True, scope_used=_scope(request))
        n = latest.get("n_resolved") or 0
        cred = {"track_record": _track_record(latest.get("tier"), n, latest.get("ga")),  # strong/mixed/weak/unproven
                "n_resolved": n, "as_of": latest.get("period_label"),
                "guidance_accuracy": latest.get("ga"), "momentum": latest.get("momentum"), "trend": latest.get("trend"),
                "robust": n >= 10,
                "_raw_tier": latest.get("tier"), "_raw_level": latest.get("level")}  # data-first transparency
        data = {"symbol": sym, "credibility": cred, "note": _CRED_NOTE}
        return E.ok(conn, data=data, classes=["cci_series"], principal=p, request_id=_rid(request),
                    prov_kw={"cci_series": {"symbol": sym, "as_of": latest.get("period_label")}},
                    coverage="descriptive credibility track-record (no validated return edge — §C)",
                    scope_used=_scope(request))


@router.get("/attention", tags=["research"])
def attention(request: Request, limit: int = 6, p: Principal = Depends(require_scope("attention"))):
    """Recent typed state-change events — DESCRIPTIVE context, not signals to trade."""
    with get_conn() as conn:
        q = R.attention(conn, limit=limit)
        return E.ok(conn, data={"attention": q}, classes=["signal_events"], principal=p, request_id=_rid(request),
                    coverage="descriptive state-changes (not signals to trade)", scope_used=_scope(request))
