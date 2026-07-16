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

# D142 relabelled the estate's return/vol ratio, renaming every `*_sharpe` number key to
# `*_retvol` (the honest name — no risk-free rate is subtracted). Verdicts stored BEFORE
# that rename (S157-b) still carry the legacy `net_sharpe`/`gross_sharpe`/`flat_sharpe`
# keys, so the post-D142 renderers — which read `net_retvol` — showed "—" for the one live
# NEW-BENCHMARK verdict. `CREATE TABLE IF NOT EXISTS` can't migrate rows and neither can it
# touch a JSON payload; this maps the keys on READ so every surface renders the number under
# the honest name, for this payload and any future pre-D142 one. The value is byte-identical
# — the relabel changed the name, not the number.
_LEGACY_NUM_KEYS = {"net_sharpe": "net_retvol",
                    "gross_sharpe": "gross_retvol",
                    "flat_sharpe": "flat_retvol"}


def normalize_numbers(nums: dict) -> dict:
    """Map any legacy `*_sharpe` number key to its `*_retvol` name (D142). Non-destructive
    (returns a new dict); the new key wins if both are somehow present, and a lingering
    legacy key is dropped so it can never shadow the honest one downstream."""
    if not isinstance(nums, dict):
        return nums
    out = dict(nums)
    for old, new in _LEGACY_NUM_KEYS.items():
        if old not in out:
            continue
        if out.get(new) is None:
            out[new] = out[old]
        out.pop(old, None)
    return out


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
    verdict = payload.get("verdict") or {}
    if isinstance(verdict, dict) and isinstance(verdict.get("numbers"), dict):
        verdict = {**verdict, "numbers": normalize_numbers(verdict["numbers"])}
    return {"id": row[0], "status": row[1], "title": row[2],
            "created_at": row[4], "decided_at": row[5],
            "verdict": verdict,
            "ledger_block": payload.get("ledger_block", "")}


def backfill_legacy_payloads(conn) -> dict:
    """One-time cleanup: rewrite pre-D142 `rule_verdict` payloads onto the honest number
    keys AND regenerate their `ledger_block` from current code — so an approved verdict
    carries the current return/vol vocabulary into canon, never the pre-D142 label.

    A row is migrated when it still holds a legacy `*_sharpe` key OR its stored block
    differs from a freshly regenerated one; regenerate-and-compare makes it naturally
    idempotent (a clean row reproduces its own block and is skipped). Commits per row
    (the S153 durability lesson). Returns {"scanned", "migrated", "skipped"}.
    """
    review_inbox.ensure_schema(conn)
    out = {"scanned": 0, "migrated": 0, "skipped": 0}
    rows = conn.execute(
        "SELECT id, payload_json FROM review_items WHERE kind=?", (KIND,)).fetchall()
    for item_id, payload_json in rows:
        out["scanned"] += 1
        try:
            payload = json.loads(payload_json or "{}")
        except ValueError:
            out["skipped"] += 1
            continue
        verdict = payload.get("verdict") or {}
        nums = verdict.get("numbers") if isinstance(verdict, dict) else None
        has_legacy = isinstance(nums, dict) and any(k in nums for k in _LEGACY_NUM_KEYS)
        if has_legacy:
            verdict = {**verdict, "numbers": normalize_numbers(nums)}
        # regenerate the paste-ready block from the (normalized) verdict with current code
        fresh_block = payload.get("ledger_block", "") or ""
        try:
            v = RuleVerdict.from_dict(verdict)
            fresh_block = ledger_entry(v, payload.get("produced_at") or "")
        except Exception:                      # a malformed row must not abort the batch
            pass
        block_changed = fresh_block != (payload.get("ledger_block", "") or "")
        if not has_legacy and not block_changed:
            out["skipped"] += 1
            continue
        payload["verdict"] = verdict
        payload["ledger_block"] = fresh_block
        conn.execute("UPDATE review_items SET payload_json=? WHERE id=?",
                     (json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
                      item_id))
        conn.commit()                          # per-row durability
        out["migrated"] += 1
    return out


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
    nums = {"net_retvol": 0.61, "gross_retvol": 1.0, "half1": 0.55, "half2": 0.66,
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

    # D142 legacy-payload path: a pre-rename verdict must still render its number and
    # backfill onto the honest keys + vocabulary.
    import json as _json
    assert normalize_numbers({"net_sharpe": 1.19})["net_retvol"] == 1.19    # read maps it
    assert "net_sharpe" not in normalize_numbers({"net_sharpe": 1.19})      # legacy dropped
    # Build with the CURRENT keys so judge() returns NEW-BENCHMARK, then LEGACY-ify the
    # stored copy (rename *_retvol -> *_sharpe) — exactly the shape a pre-D142 row carries.
    lspec = compile_rule("SELECT largecap RANK BY lowvolmom TAKE 25 HOLD quarterly")
    lv = build_verdict(lspec, {"net_retvol": 1.19, "gross_retvol": 1.4, "flat_retvol": 1.5,
                               "half1": 1.2, "half2": 1.42, "placebo_p95": 0.35,
                               "observed": 1.19, "bench_net": 0.89, "capacity_inr": 75e7,
                               "maxdd": -0.3, "ann_cost_pct": 8.0}, "s", {"env": "s"})
    assert lv.verdict == "NEW-BENCHMARK"
    vd = lv.to_dict()
    vd["numbers"] = {("net_sharpe" if k == "net_retvol" else
                      "gross_sharpe" if k == "gross_retvol" else
                      "flat_sharpe" if k == "flat_retvol" else k): val
                     for k, val in vd["numbers"].items()}          # → legacy keys
    row = review_inbox.submit(conn, KIND, lv.rule_hash, _title(lv),
                              {"verdict": vd,
                               "ledger_block": "stale pre-relabel block", "produced_at": "2026-07-15"})
    conn.commit()
    got = latest_verdict(conn)                          # the number renders via the normalizer
    assert got["verdict"]["numbers"]["net_retvol"] == 1.19
    assert "net_sharpe" not in got["verdict"]["numbers"]
    bf = backfill_legacy_payloads(conn)                 # the data itself is made honest
    assert bf["migrated"] >= 1
    raw = _json.loads(conn.execute("SELECT payload_json FROM review_items WHERE id=?",
                                   (row["id"],)).fetchone()[0])
    assert "net_retvol" in raw["verdict"]["numbers"] and "net_sharpe" not in raw["verdict"]["numbers"]
    assert "return/vol" in raw["ledger_block"].lower()  # block regenerated from current code
    assert backfill_legacy_payloads(conn)["migrated"] == 0   # idempotent
    conn.close()
    print("RULE_LAB_INBOX selftest OK")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--backfill" in sys.argv:
        import sqlite3
        db = (sys.argv[sys.argv.index("--db") + 1] if "--db" in sys.argv
              else "/opt/hermes/data/hermes.db")
        con = sqlite3.connect(db, timeout=30)
        try:
            print("backfill:", backfill_legacy_payloads(con))
        finally:
            con.close()
        sys.exit(0)
    print(__doc__)
