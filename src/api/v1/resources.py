"""The strangler seam — the ONLY module that imports the existing data layer.

Every `/v1` value flows through here, so the blast radius of an upstream signature/column
change is this one file (red-team #6: don't read producer tables raw across the app). It
calls the modules' STABLE public read-APIs (which already tolerate schema drift), never raw
producer SQL. All functions take an explicit `conn` so a request uses ONE connection and a
consistent as-of.
"""
from __future__ import annotations

from src.automation import provenance as P
from src.automation import cci_series, signal_events, security_master


def coverage(conn) -> dict:
    return P.coverage_snapshot(conn)


def universe(conn, *, as_of: str | None = None) -> dict:
    return P.universe_policy(conn, as_of=as_of)


def registry() -> list:
    return P.provenance_registry_digest()


def is_degraded(snap: dict) -> bool:
    uni = snap.get("universe") or {}
    return uni.get("status") == "security_master_empty" or not snap.get("as_of")


def health(conn) -> dict:
    snap = P.coverage_snapshot(conn)
    return {"status": "ok", "as_of": snap.get("as_of"), "degraded": is_degraded(snap)}


def credibility(conn, symbol: str):
    """(canonical_symbol, latest_series_row|None). Resolves renames first (no look-ahead)."""
    sym = security_master.canonical(symbol, conn=conn) or symbol.upper().strip()
    series = cci_series.series_for(conn, sym)
    return sym, (series[-1] if series else None)


def attention(conn, *, limit: int = 6) -> list:
    return signal_events.attention_queue(conn, limit=min(limit, 6))
