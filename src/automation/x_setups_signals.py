"""x_setups_signals — nightly pre-compute of the charter X-compute research scans (S205).

The four X-compute research modules — overnight_split (X-04), volume_shelves (X-07),
base_breakout (X-09), calendar_conditioning (X-10) — each expose a ``scan(con)`` that walks
the liquid EQ universe on the latest bhavcopy: O(universe) per scan, seconds each. Running
them render-time would repeat the Launchpad mistake (CLAUDE.md guardrail #6, pre-compute).
This module gives them the ``launchpad_signals`` treatment — one nightly

    python -m src.automation.x_setups_signals --persist-scan

materialises all four into ONE render-agnostic table ``x_setups_signals`` (module · symbol ·
asof · rank · payload JSON) plus an ``x_setups_meta`` k/v so a genuinely zero-hit run is still
a VALID, instant snapshot. A future surface (owner/redesign-gated — the render-lens spec is the
S205 hand-off) reads ``latest(conn, module=...)`` in milliseconds instead of recomputing.

Isolation: NEW module; both tables are created here with IF NOT EXISTS (db.py untouched). The
scans are READ-ONLY over bhavcopy and NEVER write. Payloads are DESCRIPTIVE metrics only.
"""
from __future__ import annotations

import json
import logging

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore

log = logging.getLogger("hermes.x_setups")

# module key == research.explosive_moves.<key>; each exposes scan(con, ...) -> list[dict]
_MODULES = ("overnight_split", "volume_shelves", "base_breakout", "calendar_conditioning")


def ensure_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS x_setups_signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            module      TEXT NOT NULL,      -- overnight_split|volume_shelves|base_breakout|calendar_conditioning
            symbol      TEXT NOT NULL,
            asof        TEXT,               -- the bhav trade date the row reflects
            rank        INTEGER,            -- position within the module's ranked scan (1 = top)
            payload     TEXT NOT NULL,      -- the scan row dict, JSON (descriptive metrics)
            computed_at TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_xsetups ON x_setups_signals(module, rank ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS x_setups_meta (k TEXT PRIMARY KEY, v TEXT)")


def compute_all(conn, asof=None, liq_floor=None) -> dict:
    """Run all four X-scans over the prod bhavcopy (box; needs a populated DB). Read-only.
    Returns {module: [rows]}; a single scan failing must not lose the others."""
    import importlib
    out = {}
    for name in _MODULES:
        try:
            mod = importlib.import_module(f"research.explosive_moves.{name}")
            kw = {}
            if asof is not None:
                kw["asof"] = asof
            if liq_floor is not None:
                kw["liq_floor"] = liq_floor
            out[name] = mod.scan(conn, **kw)
        except Exception as e:  # noqa: BLE001
            log.warning("x_setups scan %s failed: %s", name, e)
            out[name] = []
    return out


def persist_scan(conn, computed=None, computed_at=None):
    """Materialise the four scans into ``x_setups_signals`` (DELETE + INSERT, idempotent).
    Pass ``computed`` (a {module: rows} dict) to persist without recomputing (tests)."""
    ensure_table(conn)
    if computed is None:
        computed = compute_all(conn)
    conn.execute("DELETE FROM x_setups_signals")
    n = 0
    asof_seen = None
    for module, rows in computed.items():
        for i, row in enumerate(rows or []):
            asof_seen = asof_seen or row.get("asof")
            conn.execute(
                "INSERT INTO x_setups_signals (module, symbol, asof, rank, payload, computed_at) "
                "VALUES (?,?,?,?,?,?)",
                (module, row.get("symbol"), row.get("asof"), i + 1, json.dumps(row), computed_at))
            n += 1
    for module in _MODULES:
        conn.execute("INSERT INTO x_setups_meta (k, v) VALUES (?, ?) "
                     "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                     (f"count::{module}", str(len(computed.get(module, []) or []))))
    for k, v in (("computed_at", computed_at or ""), ("asof", asof_seen or "")):
        conn.execute("INSERT INTO x_setups_meta (k, v) VALUES (?, ?) "
                     "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    return n, asof_seen


def latest(conn, module=None, limit=None):
    """Read the persisted snapshot (optionally one module), rank-ordered, payloads decoded."""
    ensure_table(conn)
    q = "SELECT payload FROM x_setups_signals"
    args = []
    if module:
        q += " WHERE module=?"
        args.append(module)
    q += " ORDER BY module, rank ASC"
    if limit:
        q += f" LIMIT {int(limit)}"
    return [json.loads(r["payload"]) for r in conn.execute(q, args).fetchall()]


def selftest() -> int:
    """Hermetic persist/read/meta round-trip on an in-memory DB (no bhavcopy needed)."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    computed = {
        "base_breakout": [{"symbol": "AAA", "asof": "2026-07-20", "x09_score": 1.2},
                          {"symbol": "BBB", "asof": "2026-07-20", "x09_score": 0.5}],
        "volume_shelves": [{"symbol": "AAA", "asof": "2026-07-20", "n_shelves": 3}],
        "overnight_split": [],                       # a zero-hit module still yields a valid snapshot
        "calendar_conditioning": [{"symbol": "CCC", "asof": "2026-07-20", "expiry_ret_delta": -0.01}],
    }
    n, asof = persist_scan(conn, computed=computed, computed_at="2026-07-20 18:00:00")
    assert n == 4 and asof == "2026-07-20", (n, asof)
    bb = latest(conn, module="base_breakout")
    assert len(bb) == 2 and bb[0]["symbol"] == "AAA" and bb[0]["x09_score"] == 1.2, bb
    assert latest(conn, module="overnight_split") == []                 # zero-hit reads clean
    counts = {r["k"]: r["v"] for r in conn.execute("SELECT k, v FROM x_setups_meta").fetchall()}
    assert counts["count::overnight_split"] == "0" and counts["count::base_breakout"] == "2", counts
    assert counts["asof"] == "2026-07-20"
    n2, _ = persist_scan(conn, computed=computed, computed_at="2026-07-20 18:05:00")   # idempotent
    assert n2 == 4 and conn.execute("SELECT COUNT(*) FROM x_setups_signals").fetchone()[0] == 4
    print("X_SETUPS_SIGNALS selftest OK")
    return 0


def _cli():
    import argparse
    import datetime as _dt
    ap = argparse.ArgumentParser(description="X-compute setups — persist the nightly snapshot")
    ap.add_argument("--persist-scan", action="store_true",
                    help="materialise the 4 X-scans into x_setups_signals")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    elif args.persist_scan:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_conn() as conn:
            n, asof = persist_scan(conn, computed_at=stamp)
        print(f"persisted {n} x-setups rows (as-of {asof}, computed {stamp})")
    else:
        ap.print_help()


if __name__ == "__main__":
    _cli()
