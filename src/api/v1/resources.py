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


def credibility(conn, symbol: str, *, as_of: str | None = None):
    """(canonical_symbol, series_row|None). Resolves renames first (no look-ahead).

    With `as_of` (AUD-38 PIT): the row as it was KNOWABLE on that date — month-granular
    knowable rule in cci_series.series_asof, `knowable_from` stamped on the row.
    Without: the latest settled row (unchanged behaviour).

    Input is normalized BEFORE rename-following (S96b): security_renames stores uppercase
    symbols, so an un-normalized query used to bypass rename resolution silently."""
    raw = symbol.upper().strip()
    sym = security_master.canonical(raw, conn=conn) or raw
    if as_of:
        return sym, cci_series.series_asof(conn, sym, as_of)
    series = cci_series.series_for(conn, sym)
    return sym, (series[-1] if series else None)


def attention(conn, *, limit: int = 6, as_of: str | None = None) -> list:
    """With `as_of` (AUD-38 PIT): the queue as it stood on that date — the last computed
    event batch on-or-before it (empty only when the feed has nothing that early)."""
    if as_of:
        batch = signal_events.latest_batch_on_or_before(conn, as_of)
        if batch is None:
            return []
        return signal_events.attention_queue(conn, as_of=batch, limit=min(limit, 6))
    return signal_events.attention_queue(conn, limit=min(limit, 6))
