"""Rule-lab -> Review Inbox producer (D134 §4-H build step 3; reuses LANE-D, plan §2 L5).

Every machine-produced RuleVerdict lands in the Review Inbox (kind='rule_verdict') so a human
judges it before it becomes canon: the design's open-question default is adopted — a
NEW-BENCHMARK (or any decided verdict) never auto-appends to docs/strategy-ledger.md; the
paste-ready block (rule_lab.ledger_entry) rides in the payload and is appended by Ramana after
an APPROVE. Rejections stay in the corpus as labeled data (agreement_stats per family).

Commit discipline (the S153 LANE-E lesson, binding): review_inbox.submit() does NOT commit the
caller's connection, and mid-batch DDL auto-commits can strand partial state — so this producer
COMMITS PER ITEM, immediately after each submit. tests/test_rule_lab.py proves durability by
reading the row back over a SECOND connection.

Idempotency: ref = the rule_hash. Re-running the same frozen rule cannot spam the inbox — the
first verdict for a hash wins (a legitimately amended rule is a NEW canonical text, hence a new
hash, hence a new item — the prereg first-registration-wins discipline carried through).

Stdlib-only. No LLM. No network. Never edits db.py (review_inbox owns its own DDL).
CLI:  python -m src.automation.rule_lab_inbox --selftest
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from src.automation import review_inbox
from src.automation.rule_lab import RuleVerdict, ledger_entry

KIND = "rule_verdict"


def _title(v: RuleVerdict) -> str:
    q = f" [{v.qualifier}]" if v.qualifier else ""
    return f"Rule-lab: {v.verdict}{q} — {v.rule_text}"[:200]


def submit_verdict(conn, v: RuleVerdict, evidence_url: str = "") -> dict:
    """Queue ONE verdict for human judgment; COMMITS the connection (per-item).

    Payload = the full verdict object + the paste-ready ledger block, so the reviewer
    approves exactly what would enter canon. Returns review_inbox.submit's
    {"id": int, "created": bool}."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {"verdict": v.to_dict(),
               "ledger_block": ledger_entry(v, today),
               "producer": "rule_lab", "produced_at": today}
    out = review_inbox.submit(conn, KIND, v.rule_hash, _title(v), payload,
                              evidence_url or None)
    conn.commit()                      # per-item durability (S153 lesson — submit never commits)
    return out


def latest_verdict(conn, status: str | None = None) -> dict | None:
    """The most recent rule_verdict item (any status by default) — the surface/Pat read.
    Returns {id, status, title, created_at, decided_at, verdict: <RuleVerdict dict>} or None."""
    review_inbox.ensure_schema(conn)
    q = ("SELECT id, status, title, payload_json, created_at, decided_at FROM review_items "
         "WHERE kind=?" + (" AND status=?" if status else "") + " ORDER BY id DESC LIMIT 1")
    row = conn.execute(q, (KIND, status) if status else (KIND,)).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row[3] or "{}")
    except ValueError:
        payload = {}
    return {"id": row[0], "status": row[1], "title": row[2],
            "created_at": row[4], "decided_at": row[5],
            "verdict": payload.get("verdict") or {},
            "ledger_block": payload.get("ledger_block", "")}


# --------------------------------------------------------------------------- run queue
# The design §7 run-cost note: a full gauntlet is a heavy compute pass, not a page render —
# POST /dash/rule-lab/run only QUEUES. This table is the queue; the drain is the research-venv
# CLI (`python -m explosive_moves.rule_lab_executor --work`), run by the owner (personal-first
# v1 — NO timer, AUD-95). The runner is a human-invoked CLI, not a job daemon, exactly so the
# L5 inbox stays the only machine→human seam. Owned here (module-owned DDL, never db.py —
# the S138 signal_alert_delivery precedent).

_QUEUE_DDL = """CREATE TABLE IF NOT EXISTS rule_lab_queue(
    rule_hash    TEXT PRIMARY KEY,
    spec_text    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'queued',   -- queued | done | error
    note         TEXT,
    requested_by TEXT,
    requested_at TEXT NOT NULL,
    updated_at   TEXT)"""


def _q_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def enqueue(conn, spec, requested_by: str = "owner") -> dict:
    """Queue a compiled RuleSpec for the next drain. Idempotent on rule_hash (first request
    wins — same frozen text, same hash, same run). COMMITS per item (S153 discipline).
    Returns {"created": bool, "status": str}."""
    conn.execute(_QUEUE_DDL)
    cur = conn.execute(
        "INSERT OR IGNORE INTO rule_lab_queue "
        "(rule_hash, spec_text, status, requested_by, requested_at) VALUES (?,?,?,?,?)",
        (spec.rule_hash, spec.text, "queued", requested_by, _q_now()))
    created = cur.rowcount == 1
    status = conn.execute("SELECT status FROM rule_lab_queue WHERE rule_hash=?",
                          (spec.rule_hash,)).fetchone()[0]
    conn.commit()
    return {"created": created, "status": status}


def queue_pending(conn) -> list:
    """Queued rows oldest-first: [{rule_hash, spec_text, requested_at}, ...]."""
    conn.execute(_QUEUE_DDL)
    return [{"rule_hash": r[0], "spec_text": r[1], "requested_at": r[2]}
            for r in conn.execute(
                "SELECT rule_hash, spec_text, requested_at FROM rule_lab_queue "
                "WHERE status='queued' ORDER BY requested_at, rule_hash")]


def queue_mark(conn, rule_hash: str, status: str, note: str = "") -> None:
    """done|error (queued only re-arms via a fresh enqueue of a NEW hash). COMMITS."""
    if status not in ("done", "error", "queued"):
        raise ValueError(f"queue_mark: bad status {status!r}")
    conn.execute("UPDATE rule_lab_queue SET status=?, note=?, updated_at=? WHERE rule_hash=?",
                 (status, note[:500], _q_now(), rule_hash))
    conn.commit()


def queue_status(conn, rule_hash: str) -> str | None:
    """'queued'|'done'|'error'|None — the page's queued-badge read."""
    conn.execute(_QUEUE_DDL)
    row = conn.execute("SELECT status FROM rule_lab_queue WHERE rule_hash=?",
                       (rule_hash,)).fetchone()
    return row[0] if row else None


def _selftest() -> int:
    import sqlite3
    from src.automation.rule_lab import compile_rule, build_verdict
    conn = sqlite3.connect(":memory:")
    spec = compile_rule("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly")
    nums = {"net_sharpe": 0.61, "gross_sharpe": 1.0, "half1": 0.55, "half2": 0.66,
            "placebo_p95": 0.40, "observed": 0.61, "emp_p": 0.02, "bench_net": 0.89,
            "capacity_inr": None, "maxdd": -0.41, "ann_cost_pct": 6.0}
    v = build_verdict(spec, nums, prereg_ref="selftest", provenance={"env": "selftest"})
    assert v.verdict == "WEAKER-THAN-BENCHMARK"
    r1 = submit_verdict(conn, v, evidence_url="/dash/rule-lab")
    r2 = submit_verdict(conn, v)                       # idempotent on rule_hash
    assert r1["created"] is True and r2["created"] is False and r1["id"] == r2["id"]
    got = latest_verdict(conn)
    assert got and got["verdict"]["rule_hash"] == v.rule_hash
    assert "Rule-lab run" in got["ledger_block"]
    assert latest_verdict(conn, status="approved") is None
    # queue: idempotent enqueue -> pending -> mark done -> status reads
    q1 = enqueue(conn, spec)
    q2 = enqueue(conn, spec)
    assert q1["created"] is True and q2["created"] is False and q2["status"] == "queued"
    pend = queue_pending(conn)
    assert len(pend) == 1 and pend[0]["rule_hash"] == spec.rule_hash
    queue_mark(conn, spec.rule_hash, "done", note="selftest drain")
    assert queue_pending(conn) == [] and queue_status(conn, spec.rule_hash) == "done"
    conn.close()
    print("RULE_LAB_INBOX selftest OK")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
