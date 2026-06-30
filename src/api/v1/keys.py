"""API-key minting + hashing + dev seeding.

Keys are random 32-byte secrets, format ``pk_<env>_<token>``; only the SHA-256 hash is
stored (plaintext shown once at mint). Lookup is by hash; the auth path uses
``hmac.compare_digest`` (constant-time) against the stored hash. Stdlib only — no new dep.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import logging
import os
import secrets

from src.core.db import get_conn
from src.api.v1.schema import ensure_schema

_log = logging.getLogger(__name__)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_key(raw: str, stored_hash: str) -> bool:
    """Constant-time comparison (no timing oracle)."""
    return hmac.compare_digest(hash_key(raw), stored_hash)


def new_key(env: str = "live") -> tuple[str, str]:
    """Mint a key. Returns (full_secret, key_id). The full secret is shown ONCE."""
    token = secrets.token_urlsafe(32)
    full = f"pk_{env}_{token}"
    key_id = f"pk_{env}_{token[:8]}"     # public, greppable; not the secret
    return full, key_id


def _seed(tenant_id: str, name: str, scopes, *, rate=120, key_env: str = "dev",
          fixed_secret: str | None = None, key_id: str | None = None) -> str:
    """Idempotently create a tenant + scopes + one key. Returns the full key secret.
    A fixed_secret makes the dev key stable across restarts (so tests can reuse it)."""
    full = fixed_secret or new_key(key_env)[0]
    kid = key_id or f"pk_{tenant_id}"
    with get_conn() as conn:                       # auto-commits on success
        ensure_schema(conn)
        conn.execute("INSERT OR IGNORE INTO v1_tenants(tenant_id,name,tier,rate_limit_per_min) "
                     "VALUES(?,?,?,?)", (tenant_id, name, next(iter(scopes)), rate))
        for s in scopes:
            conn.execute("INSERT OR IGNORE INTO v1_api_scopes(tenant_id,scope) VALUES(?,?)", (tenant_id, s))
        conn.execute("INSERT OR IGNORE INTO v1_api_keys(key_id,tenant_id,key_hash,label) "
                     "VALUES(?,?,?,?)", (kid, tenant_id, hash_key(full), f"seeded {tenant_id}"))
    return full


def _dev_secret(env_var: str, prefix: str) -> str:
    """Dev-seed secret: from env if set, else a freshly MINTED random secret (never a
    predictable hardcoded constant). An unconfigured/exposed instance must not be reachable
    with a known key. Set the env var for a key that is stable across restarts."""
    secret = os.environ.get(env_var)
    if not secret:
        secret = new_key(prefix)[0]
        _log.warning("%s unset — seeded an EPHEMERAL random dev key (set the env var "
                     "for a stable key across restarts).", env_var)
    return secret


def seed_dev_key() -> str:
    """A local dev key with ALL scopes + a high rate limit. Secret from HERMES_V1_DEV_KEY,
    else an ephemeral random one (no hardcoded constant)."""
    secret = _dev_secret("HERMES_V1_DEV_KEY", "dev")
    return _seed("dev", "Local Dev", ("research", "compliance", "data-feed"),
                 rate=100000, fixed_secret=secret, key_id="pk_dev")


def seed_compliance_key() -> str:
    """A compliance-only tenant (audit/provenance, NO alpha) — proves the two-buyer split."""
    secret = _dev_secret("HERMES_V1_COMPLIANCE_KEY", "comp")
    return _seed("compliance-demo", "Compliance Demo", ("compliance",),
                 rate=100000, fixed_secret=secret, key_id="pk_comp")


def _main() -> None:
    ap = argparse.ArgumentParser(description="/v1 API-key admin")
    ap.add_argument("--seed-dev", action="store_true", help="seed the all-scopes dev key + print it once")
    ap.add_argument("--seed-compliance", action="store_true", help="seed the compliance-only demo key")
    ap.add_argument("--mint", metavar="TENANT", help="mint a fresh key for an existing tenant")
    args = ap.parse_args()
    if args.seed_dev:
        print("dev key (all scopes):", seed_dev_key())
    if args.seed_compliance:
        print("compliance-only key:", seed_compliance_key())
    if args.mint:
        full, kid = new_key()
        with get_conn() as conn:
            ensure_schema(conn)
            conn.execute("INSERT INTO v1_api_keys(key_id,tenant_id,key_hash,label) VALUES(?,?,?,?)",
                         (kid, args.mint, hash_key(full), "minted"))
        print(f"minted key_id={kid} (store the secret now, shown once):", full)


if __name__ == "__main__":
    _main()
