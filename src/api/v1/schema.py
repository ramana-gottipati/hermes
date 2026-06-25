"""`/v1` owned tables — tenants, API keys (hashed), entitlement scopes, append-only
usage log, and an atomic rate-limit counter.

Owns its own tables via an embedded `_SCHEMA` + idempotent `ensure_schema(conn)` — the
`security_master.py` / `provenance.py` house pattern. NEVER edits `db.py`. The `/v1`
layer is the FIRST authenticated surface in this codebase (the rest of the app is open
on the LAN), so these tables are the entire access-control + metering substrate.
"""
from __future__ import annotations

_SCHEMA = """
-- tenants (a buyer org). `tier` is informational; the authoritative grants live in v1_api_scopes.
CREATE TABLE IF NOT EXISTS v1_tenants (
    tenant_id          TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    tier               TEXT NOT NULL DEFAULT 'alpha',
    rate_limit_per_min INTEGER NOT NULL DEFAULT 120,
    active             INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- API keys — only the SHA-256 HASH is stored; the plaintext is shown once at mint.
-- Multiple active keys per tenant are supported from day one (rotation without a breaking change).
CREATE TABLE IF NOT EXISTS v1_api_keys (
    key_id       TEXT PRIMARY KEY,            -- public, greppable prefix (NOT secret), e.g. 'pk_dev'
    tenant_id    TEXT NOT NULL,
    key_hash     TEXT NOT NULL UNIQUE,        -- sha256(full secret) — the lookup column
    label        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at TEXT,
    revoked      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_v1_keys_hash ON v1_api_keys(key_hash);

-- entitlement scopes per tenant (a key inherits its tenant's scopes). Fail-closed: a
-- scope absent here is denied.
CREATE TABLE IF NOT EXISTS v1_api_scopes (
    tenant_id  TEXT NOT NULL,
    scope      TEXT NOT NULL,                 -- 'alpha' | 'compliance' | 'data-feed'
    granted_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (tenant_id, scope)
);

-- APPEND-ONLY usage event log — one row per request (incl. 4xx/5xx). The billing/audit
-- substrate; never UPDATEd (a mutable counter would not survive a billing dispute).
CREATE TABLE IF NOT EXISTS v1_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    tenant_id   TEXT,
    key_id      TEXT,
    endpoint    TEXT NOT NULL,
    path        TEXT,
    status      INTEGER,
    bytes_out   INTEGER,
    latency_ms  INTEGER,
    scope_used  TEXT,
    request_id  TEXT
);
CREATE INDEX IF NOT EXISTS idx_v1_usage_key_ts ON v1_usage(key_id, ts);
CREATE INDEX IF NOT EXISTS idx_v1_usage_bill   ON v1_usage(tenant_id, ts);

-- atomic rate-limit counter: one row per (key, minute-window). The increment is a single
-- statement (INSERT .. ON CONFLICT DO UPDATE .. RETURNING) so there is no read-modify-write
-- race. Correct at --workers 1 (the current prod posture); multi-worker needs a shared store.
CREATE TABLE IF NOT EXISTS v1_ratelimit (
    key_id       TEXT NOT NULL,
    window_start TEXT NOT NULL,               -- 'YYYY-MM-DDTHH:MM' (minute bucket)
    n            INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (key_id, window_start)
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
