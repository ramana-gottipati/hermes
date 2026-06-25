"""Entitlement: API key -> tenant -> scopes, and per-endpoint authorization.

Red-team blockers folded in:
  * 401 on missing/empty key — NO fallback/anonymous tenant (an anonymous principal is
    unrepresentable here).
  * key accepted ONLY in a header (Authorization: Bearer / X-API-Key); a key-shaped value
    in the query string is rejected (keys must never hit access logs / Referer).
  * hashed-at-rest + constant-time compare (in keys.verify via hash lookup + compare_digest).
  * fail-CLOSED authorization: an endpoint not in ENDPOINT_SCOPE, or a key lacking the
    required scope, is denied.
  * tenant derived from the key ONLY (never from a client-supplied tenant_id) — no IDOR.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request

from src.core.db import get_conn
from src.api.v1.schema import ensure_schema
from src.api.v1.keys import hash_key
from src.api.v1.metering import rate_check

# the scope vocabulary (code, PR-reviewable — like provenance.PROVENANCE)
SCOPES = frozenset({"alpha", "compliance", "data-feed"})

# endpoint logical name -> acceptable scopes (ANY-of). Absent => denied (fail-closed).
ENDPOINT_SCOPE: dict[str, tuple] = {
    "health":              ("alpha", "compliance", "data-feed"),
    "coverage":            ("compliance", "data-feed"),
    "universe":            ("compliance", "data-feed"),
    "provenance_registry": ("alpha", "compliance", "data-feed"),
    "credibility":         ("alpha", "data-feed"),
    "attention":           ("alpha",),
}


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    key_id: str
    tier: str
    scopes: frozenset
    rate_limit_per_min: int


def _extract_key(authorization: str | None, x_api_key: str | None, request: Request) -> str:
    # header only — reject a key-shaped query param outright (don't silently accept it)
    if any(k in request.query_params for k in ("api_key", "key", "apikey", "token")):
        raise HTTPException(400, "API key must be sent in a header (Authorization: Bearer / X-API-Key), not the URL")
    raw = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    elif x_api_key:
        raw = x_api_key.strip()
    if not raw:
        raise HTTPException(401, "missing API key (Authorization: Bearer <key> or X-API-Key)")
    return raw


def require_key(request: Request,
                authorization: str | None = Header(None),
                x_api_key: str | None = Header(None, alias="X-API-Key")) -> Principal:
    raw = _extract_key(authorization, x_api_key, request)
    h = hash_key(raw)
    with get_conn() as conn:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT k.key_id, k.key_hash, k.tenant_id, t.tier, t.rate_limit_per_min "
            "FROM v1_api_keys k JOIN v1_tenants t ON t.tenant_id = k.tenant_id "
            "WHERE k.key_hash = ? AND k.revoked = 0 AND t.active = 1", (h,)).fetchone()
        if row is None:
            raise HTTPException(401, "invalid or revoked API key")
        # constant-time confirm (defence-in-depth; the lookup already matched the hash)
        import hmac as _hmac
        if not _hmac.compare_digest(row["key_hash"], h):
            raise HTTPException(401, "invalid API key")
        scopes = frozenset(r["scope"] for r in conn.execute(
            "SELECT scope FROM v1_api_scopes WHERE tenant_id = ?", (row["tenant_id"],)))
        conn.execute("UPDATE v1_api_keys SET last_used_at = datetime('now') WHERE key_id = ?", (row["key_id"],))
    p = Principal(row["tenant_id"], row["key_id"], row["tier"], scopes, row["rate_limit_per_min"])
    request.state.principal = p           # for the metering middleware
    return p


def require_scope(endpoint: str):
    """Dependency factory: authn (require_key) + fail-closed authz + rate-limit.
    `endpoint` is the logical name keyed into ENDPOINT_SCOPE."""
    needed = ENDPOINT_SCOPE.get(endpoint)

    def dep(request: Request, p: Principal = Depends(require_key)) -> Principal:
        if not needed:                                  # endpoint not classified => deny
            raise HTTPException(403, f"endpoint '{endpoint}' is not entitled")
        if not (set(needed) & p.scopes):                # key lacks every acceptable scope => deny
            raise HTTPException(
                403, f"scope required: one of {list(needed)}; key has {sorted(p.scopes)}")
        ok, n = rate_check(p.key_id, p.rate_limit_per_min)
        request.state.rate = (p.rate_limit_per_min, n)  # for RateLimit-* headers
        request.state.scope_used = next((s for s in needed if s in p.scopes), None)
        if not ok:
            raise HTTPException(429, f"rate limit {p.rate_limit_per_min}/min exceeded")
        return p
    return dep
