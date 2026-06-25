"""Metering — an atomic per-minute rate limit + an append-only usage log.

Rate limit (red-team #10): the counter increment is a SINGLE statement
(``INSERT .. ON CONFLICT DO UPDATE SET n=n+1 RETURNING n``) so there is no
read-modify-write race within the process. Correct at ``--workers 1`` (the current prod
posture in scripts/setup-news.sh); a multi-worker deploy needs a shared counter (Redis /
SQLite shared-cache) — documented, not silently wrong.

Usage (red-team #11): one append-only row per request (incl. 4xx/5xx), written from the
middleware in all cases — never a mutable counter that couldn't survive a billing dispute.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.core.db import get_conn
from src.api.v1.schema import ensure_schema


def _minute_window() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def rate_check(key_id: str, limit_per_min: int) -> tuple[bool, int]:
    """Atomically increment this key's current-minute counter; return (within_limit, n)."""
    win = _minute_window()
    with get_conn() as conn:
        ensure_schema(conn)
        try:
            row = conn.execute(
                "INSERT INTO v1_ratelimit(key_id, window_start, n) VALUES(?,?,1) "
                "ON CONFLICT(key_id, window_start) DO UPDATE SET n = n + 1 RETURNING n",
                (key_id, win)).fetchone()
            n = row[0] if row else 1
        except Exception:           # older sqlite without RETURNING — fall back (tiny race, acceptable)
            conn.execute("INSERT INTO v1_ratelimit(key_id, window_start, n) VALUES(?,?,0) "
                         "ON CONFLICT(key_id, window_start) DO NOTHING", (key_id, win))
            conn.execute("UPDATE v1_ratelimit SET n = n + 1 WHERE key_id=? AND window_start=?", (key_id, win))
            n = conn.execute("SELECT n FROM v1_ratelimit WHERE key_id=? AND window_start=?",
                             (key_id, win)).fetchone()[0]
    return (n <= limit_per_min, n)


def record_usage(*, tenant_id, key_id, endpoint, path, status, bytes_out=None,
                 latency_ms=None, scope_used=None, request_id=None) -> None:
    """Append one usage event. Best-effort: metering must never break a response."""
    try:
        with get_conn() as conn:
            ensure_schema(conn)
            conn.execute(
                "INSERT INTO v1_usage(tenant_id,key_id,endpoint,path,status,bytes_out,latency_ms,scope_used,request_id) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (tenant_id, key_id, endpoint, path, status, bytes_out, latency_ms, scope_used, request_id))
    except Exception:               # noqa: BLE001 — never let metering fail the request
        pass
