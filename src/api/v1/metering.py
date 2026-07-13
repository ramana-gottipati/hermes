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

import logging
from datetime import datetime, timedelta, timezone

from src.core.db import get_conn
from src.api.v1.schema import ensure_schema

log = logging.getLogger("hermes.v1.metering")

# Keep only the last few minute-windows — only the current window is ever read, so older
# rows are dead weight; without this the table grows one row per (key, minute) forever.
_RATELIMIT_RETAIN_MIN = 5


def _minute_window() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def rate_check(key_id: str, limit_per_min: int) -> tuple[bool, int]:
    """Atomically increment this key's current-minute counter; return (within_limit, n)."""
    win = _minute_window()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=_RATELIMIT_RETAIN_MIN)).strftime("%Y-%m-%dT%H:%M")
    with get_conn() as conn:
        ensure_schema(conn)
        conn.execute("DELETE FROM v1_ratelimit WHERE window_start < ?", (cutoff,))  # bound table growth
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


def quota_check(tenant_id, *, daily_quota=None, monthly_quota=None) -> tuple[bool, int | None, int | None]:
    """Enforce per-tenant daily/monthly quotas beside the per-minute rate limit (AUD-37 follow-on
    — the entitlement substrate for tiered data plans). Returns (within_quota, used_today,
    used_month) over the append-only usage log, counting only SERVED requests (status < 400 —
    4xx/5xx are not billable data). A NULL quota is unlimited → early-returns with NO db read, so
    tenants without a quota set pay zero cost and keep exactly their current behaviour. FAIL-OPEN:
    any error → allowed (a metering glitch must never block a paying tenant)."""
    if not tenant_id or (daily_quota is None and monthly_quota is None):
        return (True, None, None)
    try:
        now = datetime.now(timezone.utc)
        day_start = now.strftime("%Y-%m-%d 00:00:00")     # sargable on idx_v1_usage_bill(tenant_id, ts)
        month_start = now.strftime("%Y-%m-01 00:00:00")
        with get_conn() as conn:
            ensure_schema(conn)
            used_today = conn.execute(
                "SELECT COUNT(*) FROM v1_usage WHERE tenant_id=? AND ts >= ? AND status < 400",
                (tenant_id, day_start)).fetchone()[0]
            used_month = conn.execute(
                "SELECT COUNT(*) FROM v1_usage WHERE tenant_id=? AND ts >= ? AND status < 400",
                (tenant_id, month_start)).fetchone()[0]
        within = not ((daily_quota is not None and used_today >= daily_quota)
                      or (monthly_quota is not None and used_month >= monthly_quota))
        return (within, used_today, used_month)
    except Exception as exc:    # noqa: BLE001 — fail-open, but log so a silent glitch is visible
        log.warning("v1 quota_check failed (fail-open) tenant=%s: %s", tenant_id, exc)
        return (True, None, None)


def record_usage(*, tenant_id, key_id, endpoint, path, status, bytes_out=None,
                 latency_ms=None, scope_used=None, request_id=None) -> None:
    """Append one usage event. Best-effort: metering must never break a response — but a
    DROPPED row is now LOGGED, never silent (AUD-37). A transient write-lock (the documented
    lock class) gets ONE retry before the row is recorded as dropped, so a billing dispute
    can at least see it happened."""
    for attempt in range(2):
        try:
            with get_conn() as conn:
                ensure_schema(conn)
                conn.execute(
                    "INSERT INTO v1_usage(tenant_id,key_id,endpoint,path,status,bytes_out,latency_ms,scope_used,request_id) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (tenant_id, key_id, endpoint, path, status, bytes_out, latency_ms, scope_used, request_id))
            return
        except Exception as exc:    # noqa: BLE001 — never let metering fail the request
            if attempt == 0 and "lock" in str(exc).lower():
                continue            # one quick retry on a transient lock
            log.warning("v1 metering DROPPED a usage row (request_id=%s endpoint=%s status=%s): %s",
                        request_id, endpoint, status, exc)
            return
