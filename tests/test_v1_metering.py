"""AUD-37 — /v1 metering must be audit-grade: one row per request incl. 5xx, real bytes_out,
no silently-dropped rows, and X-Request-ID on error responses.

These pin the four defects the audit named (api/v1/__init__.py + metering.py):
  1. bytes_out was 0 on EVERY row (BaseHTTPMiddleware wrapper has no `.body`);
  2. an unhandled 500 propagated to ServerErrorMiddleware OUTSIDE the metering middleware,
     so it was never logged (broke "one row per request incl. 5xx");
  3. the 500's response lacked X-Request-ID / RateLimit headers (produced above _observe);
  4. a failed metering INSERT was silently swallowed — now it is retried once on a lock and
     LOGGED if it still drops.
"""
from __future__ import annotations

import logging

import pytest

from src.core.db import get_conn
from src.api.v1 import build_app, metering
from src.api.v1.keys import seed_dev_key
from src.api.v1.selftest import _teardown


@pytest.fixture()
def client_key():
    _teardown()                                   # start clean (dev/comp tenants + pk_* rows)
    key = seed_dev_key()
    app = build_app()

    @app.get("/_boom")                            # a deliberate 500 (added to app → no router auth)
    def _boom():
        raise RuntimeError("boom for the metering test")

    from fastapi.testclient import TestClient
    c = TestClient(app, raise_server_exceptions=False)
    yield c, key
    _teardown()


def _last_usage(key_id="pk_dev"):
    with get_conn() as conn:
        return conn.execute("SELECT status, bytes_out FROM v1_usage WHERE key_id=? "
                            "ORDER BY id DESC LIMIT 1", (key_id,)).fetchone()


def test_bytes_out_is_recorded_not_zero(client_key):
    c, key = client_key
    r = c.get("/coverage", headers={"X-API-Key": key})
    assert r.status_code == 200
    row = _last_usage()
    assert row is not None and (row["bytes_out"] or 0) > 0     # was 0 on EVERY row before AUD-37


def test_500_is_metered_and_stamped(client_key):
    c, _key = client_key
    rid = "test-aud37-500"
    r = c.get("/_boom", headers={"X-Request-ID": rid})
    assert r.status_code == 500
    assert r.headers.get("X-Request-ID") == rid                # the 500 now carries the id
    assert r.headers.get("content-type", "").startswith("application/problem+json")
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM v1_usage WHERE request_id=?", (rid,)).fetchone()
        assert row is not None and row["status"] == 500        # the 500 WAS metered (was skipped)
        conn.execute("DELETE FROM v1_usage WHERE request_id=?", (rid,))  # scoped cleanup


def test_record_usage_logs_a_drop_never_silent(monkeypatch, caplog):
    # a failing INSERT must be logged (audit-grade), retried once on a lock, and never raise.
    calls = {"n": 0}

    def _boom_conn():
        calls["n"] += 1
        raise RuntimeError("database is locked")

    monkeypatch.setattr(metering, "get_conn", _boom_conn)
    with caplog.at_level(logging.WARNING, logger="hermes.v1.metering"):
        metering.record_usage(tenant_id="t", key_id="k", endpoint="/x", path="/x",
                              status=200, bytes_out=10, request_id="drop-test")   # must not raise
    assert calls["n"] == 2                                      # one retry on the lock, then give up
    assert any("DROPPED" in r.getMessage() for r in caplog.records)
