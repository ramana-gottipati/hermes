"""M-04 — pre-registration registry: tamper-evident hashes of study gates (S83g).

Every study module carries its hypothesis + pass/fail gate in its module DOCSTRING,
written before the run (charter §2.1). This registry stores sha256(docstring) at
registration time in research.db; `--verify` recomputes each hash and flags any
post-hoc gate edit. First registration wins — legitimately amending a gate means a
NEW study module (or `--force`, which records the override note, which is itself
the audit trail). The spec-sheets Trust page renders the hash chips.

Honesty note baked into the data: the five studies that predate this registry
(pead, footprint, insider_drift, filing_latency, concall_intent) are registered
retroactively — their gates were written before their runs (verifiable in git
history), but the HASH postdates them; their note says so. dividend_drift and
rebrand_pump are the first studies hashed BEFORE their first run.

CLI (research venv):
  python -m explosive_moves.prereg --register-all [--note "..."]
  python -m explosive_moves.prereg --verify
  python -m explosive_moves.prereg --list
  python -m explosive_moves.prereg --selftest
"""
from __future__ import annotations

import hashlib
import importlib
import sqlite3
import sys
from datetime import datetime, timezone

RDB = "/opt/hermes/data/research.db"
STUDIES = ["pead", "footprint", "insider_drift", "filing_latency", "concall_intent",
           "dividend_drift", "rebrand_pump", "campaign_arcs", "rating_drift", "evlib"]
RETRO = {"pead", "footprint", "insider_drift", "filing_latency", "concall_intent", "evlib"}

_DDL = """CREATE TABLE IF NOT EXISTS prereg_registry(
    module        TEXT PRIMARY KEY,
    gate_sha256   TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    note          TEXT)"""


def gate_hash(doc: str) -> str:
    return hashlib.sha256((doc or "").encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def register_all(note: str = "", force: bool = False, db_path: str = RDB) -> None:
    con = sqlite3.connect(db_path, timeout=30)
    con.execute(_DDL)
    for name in STUDIES:
        mod = importlib.import_module(f"explosive_moves.{name}")
        h = gate_hash(mod.__doc__)
        n = note or ("retro-hashed 2026-07-07: gate text predates the registry; "
                     "runs predate the hash (git history is the witness)"
                     if name in RETRO else "hashed BEFORE first run")
        row = con.execute("SELECT gate_sha256 FROM prereg_registry WHERE module=?",
                          (name,)).fetchone()
        if row is None:
            con.execute("INSERT INTO prereg_registry VALUES (?,?,?,?)",
                        (name, h, _now(), n))
            print(f"registered {name}: {h[:12]}…")
        elif row[0] != h:
            if force:
                con.execute("UPDATE prereg_registry SET gate_sha256=?, registered_at=?, "
                            "note=? WHERE module=?", (h, _now(), f"FORCED re-register: {note}", name))
                print(f"FORCED re-register {name}: {h[:12]}… (note recorded)")
            else:
                print(f"⚠ TAMPER-CHECK {name}: stored {row[0][:12]}… != current {h[:12]}… "
                      f"(gate text changed after registration — use --force WITH a note "
                      f"only for a legitimate new version)")
        else:
            print(f"unchanged {name}: {h[:12]}…")
    con.commit()
    con.close()


def verify(db_path: str = RDB) -> int:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    bad = 0
    for name, stored, at, note in con.execute(
            "SELECT module, gate_sha256, registered_at, note FROM prereg_registry ORDER BY 1"):
        try:
            mod = importlib.import_module(f"explosive_moves.{name}")
            cur = gate_hash(mod.__doc__)
        except Exception as e:                                  # noqa: BLE001
            print(f"?? {name}: import failed ({type(e).__name__})")
            bad += 1
            continue
        ok = cur == stored
        bad += 0 if ok else 1
        print(f"{'OK ' if ok else '!! TAMPERED'} {name:<16} {stored[:12]}… "
              f"registered {at}" + ("" if ok else f" — current {cur[:12]}…"))
    con.close()
    return bad


def hashes(db_path: str = RDB) -> dict:
    """module -> sha256, for surface rendering. Empty dict when absent."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        out = dict(con.execute("SELECT module, gate_sha256 FROM prereg_registry"))
        con.close()
        return out
    except sqlite3.Error:
        return {}


def selftest() -> None:
    assert gate_hash("abc") == hashlib.sha256(b"abc").hexdigest()
    assert gate_hash("") == gate_hash(None)
    con = sqlite3.connect(":memory:")
    con.execute(_DDL)
    con.execute("INSERT INTO prereg_registry VALUES ('x', ?, ?, 'n')", (gate_hash("g1"), _now()))
    stored = con.execute("SELECT gate_sha256 FROM prereg_registry WHERE module='x'").fetchone()[0]
    assert stored == gate_hash("g1") and stored != gate_hash("g2")   # tamper detectable
    print("PREREG selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--register-all" in sys.argv:
        note = ""
        if "--note" in sys.argv:
            note = sys.argv[sys.argv.index("--note") + 1]
        register_all(note=note, force="--force" in sys.argv)
    elif "--verify" in sys.argv:
        sys.exit(1 if verify() else 0)
    elif "--list" in sys.argv:
        for m, h in sorted(hashes().items()):
            print(f"{m:<16} {h}")
    else:
        print(__doc__)
