"""The canonical `/v1` response envelope — the ONLY place outbound JSON is shaped, so the
honesty rules are structural (every endpoint inherits them by calling `ok()`).

Shape: ``{data, _provenance (per data-class), _meta, _entitlement}``.

Red-team laws made structural:
  * A MODELED value never serialises as a bare scalar — `modeled_value()` wraps it as
    ``{value, basis, lag_days, as_of_kind, display}`` so an SDK/MCP/LLM cannot strip the caveat.
  * NO single top-level `as_of` on a blended response — `_meta.as_of` is an OBJECT keyed by
    data-class, plus `knowable_as_of_oldest` (the weakest clock), never the freshest.
  * A market-level value is nested under `market_context` with `applies_to`, never under a stock key.
  * "We don't have it" is a typed `absence()` (``available:false, do_not_estimate:true``), never bare null.
  * RFC-7807 `problem()` for errors.
"""
from __future__ import annotations

from fastapi import HTTPException

from src.automation import provenance as P

METHODOLOGY_VERSION = "v1.0"

# ── redistribution licensing gate (docs/data-licensing-decision.md) ──
# The `data-feed` scope is the external REDISTRIBUTION channel; it must NOT be served a
# data-class whose licence forbids redistribution. compliance/research are diligence
# (own-use) consumers, not redistributors, so they are unaffected. Conservative by design:
# every currently-live endpoint serves OWNED classes (survivorship/cci_series/signal_events),
# so this blocks nothing today — it closes the hole structurally for any future route that
# exposes a vendor-sourced class. NOTE (flagged for Codex/Ramana review): the predicate is
# scoped to the resolved scope_used == data-feed; broaden to principal-scope if a redistributor
# key should be refused even when another scope happened to satisfy the endpoint.
_NON_REDISTRIBUTABLE = {P.VENDOR_TOS, P.NEWS_LICENSE}
_REDISTRIBUTION_SCOPE = "data-feed"


def modeled_value(value, prov: dict) -> dict:
    """Wrap a value whose availability is MODELED so the basis rides the value, not a sibling key."""
    return {"value": value, "basis": prov.get("basis"), "lag_days": prov.get("lag_days"),
            "as_of_kind": prov.get("as_of_kind"), "display": prov.get("display")}


def absence(reason: str, **extra) -> dict:
    """A typed 'not available' — strip-resistant for an LLM (no bare null to fill in)."""
    return {"available": False, "reason": reason, "do_not_estimate": True, **extra}


def market_block(values: dict, prov: dict, *, symbol: str | None = None) -> dict:
    """A market-level (no per-stock split) block, structurally separated from any stock payload."""
    return {**values, "_provenance": prov,
            "applies_to": f"market (NOT {symbol})" if symbol else "market"}


def problem(status: int, title: str, detail: str = "", *, request_id: str | None = None,
            type_: str = "about:blank") -> dict:
    """RFC-7807 application/problem+json body."""
    return {"type": type_, "title": title, "status": status, "detail": detail, "instance": request_id}


def _min_date(values) -> str | None:
    dates = [str(v)[:10] for v in values if v and len(str(v)) >= 7 and str(v)[0].isdigit()]
    return min(dates) if dates else None


def meta(*, prov_map: dict, request_id: str | None, tenant: str | None,
         coverage: str = "", degraded: bool = False) -> dict:
    as_of = {k: v.get("as_of") for k, v in prov_map.items()}
    return {
        "as_of": as_of,                                   # OBJECT, never a single scalar
        "knowable_as_of_oldest": _min_date(as_of.values()),
        "basis": {k: v.get("basis") for k, v in prov_map.items()},
        "coverage": coverage,
        "methodology_version": METHODOLOGY_VERSION,
        "request_id": request_id,
        "tenant": tenant,
        "degraded": bool(degraded),
        "disclaimer": ("Descriptors / percentile rank-gaps and point-in-time evidence — "
                       "NOT investment advice and NOT a performance claim."),
    }


def ok(conn, *, data, classes, principal, request_id, prov_kw: dict | None = None,
       coverage: str = "", degraded: bool = False, scope_used: str | None = None) -> dict:
    """Assemble a stamped envelope. `classes` = the data-classes present; `prov_kw[class]` =
    kwargs (symbol/as_of/period_type) for that class's provenance_for()."""
    # Redistribution gate: refuse a non-redistributable class on the external data-feed scope.
    if scope_used == _REDISTRIBUTION_SCOPE:
        blocked = [c for c in classes if P.redistribution_status(c) in _NON_REDISTRIBUTABLE]
        if blocked:
            raise HTTPException(
                403, f"redistribution not licensed for data-class(es) {blocked} on the "
                     f"data-feed (external) scope — see /v1/provenance/registry and "
                     f"docs/data-licensing-decision.md")
    prov_kw = prov_kw or {}
    prov_map = {}
    for cls in classes:
        try:
            prov_map[cls] = P.provenance_for(cls, conn=conn, **prov_kw.get(cls, {}))
        except Exception as e:  # noqa: BLE001 — provenance must never break the envelope
            prov_map[cls] = {"data_class": cls, "basis": "UNKNOWN", "as_of": None,
                             "display": f"provenance error: {e}"}
    return {
        "data": data,
        "_provenance": prov_map,
        "_meta": meta(prov_map=prov_map, request_id=request_id, tenant=getattr(principal, "tenant_id", None),
                      coverage=coverage, degraded=degraded),
        "_entitlement": {"tier": getattr(principal, "tier", None), "scope_used": scope_used},
    }
