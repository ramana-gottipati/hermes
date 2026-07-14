"""Review Inbox — the L5 judgment-layer primitive (D134 LANE-D, plan §4-D).

ONE queue for every artifact the machine wants the analyst to judge; every
decision persists as the JUDGMENT CORPUS — a labeled dataset of one analyst's
verified calls (plan §2 L5 mandate: nothing counts until it is "checked,
verified, and evaluated with human input"). Over time `agreement_stats()`
answers the commercial question: which generator families EARN trust.

Design intent — the `kind` field is the extension point. Adapters plug in
LATER with NO schema change; each producer picks a kind and a stable ref:

  kind='tags'       theme_tags.py proposals (today: company_tags.approved=0
                    rows; adapter submits one item per proposed (symbol, tag)).
  kind='alert-ack'  signal_alerts.py rail acknowledgements (today: the rail's
                    own acknowledge column).
  kind='brief'      auto-analyst event briefs (plan §4-E) — the draft lands
                    here; ONLY an approved brief publishes, with the AI label.
  kind='rebalance'  model-portfolio rebalance diffs for the private book.
  kind='anomaly'    DQ/fence anomaly flags, study verdict sign-offs, etc.

Absorbing the three existing approve/ack flows is a LATER serialized step
(LANE-R territory); this module deliberately does NOT touch theme_tags /
signal_alerts / tracker_alerts today.

Contract:
  • submit() is IDEMPOTENT on (kind, ref): first write wins. A re-submit never
    duplicates and never mutates what the human saw or already judged. A
    genuinely new version of an artifact = a NEW ref (encode version/date in
    the ref, e.g. 'RELIANCE|2026-07-15').
  • decide() is FINAL: a double-decide raises. The guard is the UPDATE's
    `status='pending'` predicate — atomic, no check-then-write race.
  • pending() is the drain queue (oldest first); corpus() is the judgment
    dataset (decided items, chronological by decided_at, payload parsed back).
  • Descriptive doctrine rides along: an item is "the machine proposes, the
    human judges" — never a recommendation surface.

Isolation (the signal_alerts/tracker_alerts owned-table precedent): owns
`review_items` via ensure_schema() (CREATE TABLE IF NOT EXISTS — db.py is
untouched); stdlib-only; no LLM; every API function takes an explicit `conn`
so hermetic tests inject a temp sqlite; the CLI opens the live DB lazily.
No web surface here — the lens is LANE-R's per docs/SURFACE-PLAYBOOK.md.

CLI:
    python -m src.automation.review_inbox --pending [--kind tags] [--limit 50]
    python -m src.automation.review_inbox --decide 12 --verdict approved [--note "..."]
    python -m src.automation.review_inbox --stats [--kind tags]
    python -m src.automation.review_inbox --submit --kind tags --ref "RELIANCE|Defence" \
        --title "Proposed tag: Defence" [--payload-json '{"conf":0.7}'] [--evidence-url /dash/sym/RELIANCE]
    python -m src.automation.review_inbox --selftest    # hermetic round-trip on a temp db
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("hermes.review_inbox")

# --- owned table (isolation: not in db.py SCHEMA_BASE) -----------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,
    ref          TEXT NOT NULL,
    title        TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    evidence_url TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','approved','rejected')),
    note         TEXT,
    created_at   TEXT NOT NULL,
    decided_at   TEXT,
    UNIQUE (kind, ref)
);
CREATE INDEX IF NOT EXISTS idx_review_items_status_kind
    ON review_items (status, kind, created_at);
"""

_COLS = ("id, kind, ref, title, payload_json, evidence_url, status, note, "
         "created_at, decided_at")

_VERDICTS = {"approve": "approved", "approved": "approved",
             "reject": "rejected", "rejected": "rejected"}


def _utcnow() -> str:
    """UTC ISO-8601 stamp (module-level so tests can monkeypatch time)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_schema(conn) -> None:
    """Idempotent creation of the owned table (mirrors signal_alerts)."""
    conn.executescript(_SCHEMA)


def _to_dict(row, description) -> dict:
    """Row → plain dict, independent of the caller's row_factory; parses payload."""
    d = {desc[0]: row[i] for i, desc in enumerate(description)}
    try:
        d["payload"] = json.loads(d.pop("payload_json") or "{}")
    except (TypeError, ValueError):
        d["payload"] = {}
    return d


def _get(conn, item_id: int) -> Optional[dict]:
    cur = conn.execute(
        f"SELECT {_COLS} FROM review_items WHERE id=?", (int(item_id),))
    row = cur.fetchone()
    return _to_dict(row, cur.description) if row is not None else None


# --- API (every function takes an explicit conn; callers own commit) ---------

def submit(conn, kind: str, ref: str, title: str, payload=None,
           evidence_url: Optional[str] = None) -> dict:
    """Queue an artifact for human judgment. Idempotent on (kind, ref).

    First write wins: re-submitting an existing (kind, ref) neither duplicates
    nor mutates the stored item (see module docstring — new version = new ref).
    `payload` is any JSON-serializable object (dict preferred); non-JSON leaf
    values are stringified. Returns {"id": int, "created": bool}.
    """
    kind = (kind or "").strip().lower()
    ref = (ref or "").strip()
    title = (title or "").strip()
    if not kind or not ref or not title:
        raise ValueError("submit: kind, ref and title are all required (non-empty)")
    payload_json = json.dumps(payload if payload is not None else {},
                              ensure_ascii=False, sort_keys=True, default=str)
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT OR IGNORE INTO review_items "
        "(kind, ref, title, payload_json, evidence_url, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (kind, ref, title, payload_json, evidence_url, _utcnow()))
    created = cur.rowcount == 1
    if created:
        item_id = cur.lastrowid
    else:
        item_id = conn.execute(
            "SELECT id FROM review_items WHERE kind=? AND ref=?",
            (kind, ref)).fetchone()[0]
    return {"id": int(item_id), "created": created}


def decide(conn, item_id: int, verdict: str, note: Optional[str] = None) -> dict:
    """Record the human verdict (approved|rejected; approve/reject accepted).

    Final: raises ValueError on an unknown id, an invalid verdict, or a
    double-decide (the UPDATE only touches status='pending' rows — atomic).
    Returns the decided item as a dict.
    """
    v = _VERDICTS.get(str(verdict or "").strip().lower())
    if v is None:
        raise ValueError(
            f"decide: verdict must be approved|rejected (got {verdict!r})")
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE review_items SET status=?, note=?, decided_at=? "
        "WHERE id=? AND status='pending'",
        (v, note, _utcnow(), int(item_id)))
    if cur.rowcount == 0:
        row = conn.execute(
            "SELECT status FROM review_items WHERE id=?",
            (int(item_id),)).fetchone()
        if row is None:
            raise ValueError(f"decide: no review item with id={item_id}")
        raise ValueError(
            f"decide: item {item_id} is already decided ({row[0]}) — "
            "double-decide is blocked")
    return _get(conn, int(item_id))


def pending(conn, kind: Optional[str] = None) -> list:
    """The open queue, oldest first (drain order). Optional kind filter."""
    ensure_schema(conn)
    sql = f"SELECT {_COLS} FROM review_items WHERE status='pending'"
    args: list = []
    if kind:
        sql += " AND kind=?"
        args.append(kind.strip().lower())
    sql += " ORDER BY created_at ASC, id ASC"
    cur = conn.execute(sql, args)
    return [_to_dict(r, cur.description) for r in cur.fetchall()]


def corpus(conn, kind: Optional[str] = None, since: Optional[str] = None) -> list:
    """The judgment dataset: decided items, chronological by decided_at.

    `since` filters decided_at >= since; ISO prefix compare, so a date-only
    '2026-07-15' includes every decision made on/after that day.
    """
    ensure_schema(conn)
    sql = (f"SELECT {_COLS} FROM review_items "
           "WHERE status IN ('approved','rejected')")
    args: list = []
    if kind:
        sql += " AND kind=?"
        args.append(kind.strip().lower())
    if since:
        sql += " AND decided_at >= ?"
        args.append(str(since))
    sql += " ORDER BY decided_at ASC, id ASC"
    cur = conn.execute(sql, args)
    return [_to_dict(r, cur.description) for r in cur.fetchall()]


def agreement_stats(conn, kind: Optional[str] = None) -> dict:
    """Approve-rate per generator family (which machine outputs earn trust).

    Returns {kind: {pending, approved, rejected, decided, approve_rate}};
    approve_rate is None while a family has no decisions (never div-by-zero).
    Unknown/absent kind → {} (empty-DB grace).
    """
    ensure_schema(conn)
    sql = ("SELECT kind, "
           "SUM(status='pending')  AS p, "
           "SUM(status='approved') AS a, "
           "SUM(status='rejected') AS r "
           "FROM review_items")
    args: list = []
    if kind:
        sql += " WHERE kind=?"
        args.append(kind.strip().lower())
    sql += " GROUP BY kind ORDER BY kind"
    out = {}
    for row in conn.execute(sql, args).fetchall():
        k = row[0]
        p, a, r = int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)
        decided = a + r
        out[k] = {"pending": p, "approved": a, "rejected": r,
                  "decided": decided,
                  "approve_rate": (a / decided) if decided else None}
    return out


# --- selftest (hermetic: its own temp-file db; never opens the live DB) ------

def _selftest() -> int:
    import os
    import shutil
    import sqlite3
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="review_inbox_selftest_")
    path = os.path.join(tmpdir, "selftest.db")
    conn = sqlite3.connect(path)
    try:
        ensure_schema(conn)
        ensure_schema(conn)  # idempotent
        print(f"ok: schema created twice (idempotent) on temp db {path}")

        pay = {"conf": 0.72, "why": ["kw:defence", "₹-order"], "n": 3}
        s1 = submit(conn, "tags", "RELIANCE|Defence", "Proposed tag: Defence",
                    payload=pay, evidence_url="/dash/sym/RELIANCE")
        assert s1["created"] is True and isinstance(s1["id"], int)
        s1b = submit(conn, "tags", "RELIANCE|Defence", "DIFFERENT title",
                     payload={"conf": 0.99})
        assert s1b["created"] is False and s1b["id"] == s1["id"]
        assert len(pending(conn)) == 1, "re-submit must not duplicate"
        assert pending(conn)[0]["title"] == "Proposed tag: Defence", \
            "first write wins"
        print("ok: submit idempotent on (kind, ref) - first write wins")

        s2 = submit(conn, "alert-ack", "TCS|cci|2026-07-14", "CCI drop 55→30")
        assert s2["created"] is True
        assert len(pending(conn)) == 2
        assert len(pending(conn, kind="tags")) == 1
        print("ok: pending() lists the queue; kind filter works")

        d1 = decide(conn, s1["id"], "approved", note="good catch")
        assert d1["status"] == "approved" and d1["decided_at"]
        assert d1["note"] == "good catch"
        try:
            decide(conn, s1["id"], "rejected")
            raise AssertionError("double-decide must raise")
        except ValueError as e:
            assert "already decided" in str(e)
        print("ok: decide() records verdict; double-decide blocked")

        try:
            decide(conn, 99999, "approved")
            raise AssertionError("unknown id must raise")
        except ValueError:
            pass
        try:
            decide(conn, s2["id"], "maybe")
            raise AssertionError("invalid verdict must raise")
        except ValueError:
            pass
        print("ok: unknown id + invalid verdict raise ValueError")

        decide(conn, s2["id"], "reject")  # alias accepted
        assert pending(conn) == []
        rows = corpus(conn)
        assert len(rows) == 2
        got = next(r for r in rows if r["kind"] == "tags")
        assert got["payload"] == pay, "payload must round-trip exactly"
        assert len(corpus(conn, kind="alert-ack")) == 1
        assert corpus(conn, since="2999-01-01") == []
        print("ok: corpus() = decided items; payload round-trip; filters work")

        st = agreement_stats(conn)
        assert st["tags"]["approve_rate"] == 1.0
        assert st["alert-ack"]["approve_rate"] == 0.0
        assert st["tags"]["decided"] == 1 and st["tags"]["pending"] == 0
        assert agreement_stats(conn, kind="tags").keys() == {"tags"}
        assert agreement_stats(conn, kind="nope") == {}
        print("ok: agreement_stats() math + kind filter + unknown-kind grace")

        print("selftest: ALL PASS (submit -> pending -> decide -> corpus -> stats)")
        return 0
    finally:
        conn.close()
        shutil.rmtree(tmpdir, ignore_errors=True)


# --- CLI ----------------------------------------------------------------------

def _print_items(items: list) -> None:
    if not items:
        print("(none)")
        return
    for it in items:
        ev = f"  {it['evidence_url']}" if it.get("evidence_url") else ""
        print(f"[{it['id']:>4}] {it['kind']:<12} {it['ref']:<28} "
              f"{it['title']}  ({it['created_at']}){ev}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Review Inbox — one queue for everything the machine "
                    "wants a human to judge (L5).")
    ap.add_argument("--pending", action="store_true", help="list the open queue")
    ap.add_argument("--decide", type=int, metavar="ID",
                    help="decide an item (needs --verdict)")
    ap.add_argument("--verdict", choices=sorted(_VERDICTS),
                    help="approved|rejected (approve/reject accepted)")
    ap.add_argument("--note", default=None, help="annotation stored with the verdict")
    ap.add_argument("--stats", action="store_true",
                    help="approve-rate per generator family")
    ap.add_argument("--submit", action="store_true",
                    help="manually queue an item (needs --kind/--ref/--title)")
    ap.add_argument("--kind", default=None)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--payload-json", default=None, metavar="JSON")
    ap.add_argument("--evidence-url", default=None)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--selftest", action="store_true",
                    help="hermetic round-trip on a temp db (never the live DB)")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    from src.core.db import get_conn  # lazy: only the live paths need it
    with get_conn() as conn:
        if args.pending:
            items = pending(conn, kind=args.kind)[: args.limit]
            _print_items(items)
        elif args.decide is not None:
            if not args.verdict:
                print("error: --decide needs --verdict approved|rejected")
                return 2
            item = decide(conn, args.decide, args.verdict, note=args.note)
            print(json.dumps(item, ensure_ascii=False, indent=2))
        elif args.submit:
            if not (args.kind and args.ref and args.title):
                print("error: --submit needs --kind, --ref and --title")
                return 2
            payload = None
            if args.payload_json:
                try:
                    payload = json.loads(args.payload_json)
                except ValueError as e:
                    print(f"error: --payload-json is not valid JSON: {e}")
                    return 2
            res = submit(conn, args.kind, args.ref, args.title,
                         payload=payload, evidence_url=args.evidence_url)
            print(json.dumps(res, ensure_ascii=False))
        elif args.stats:
            st = agreement_stats(conn, kind=args.kind)
            if not st:
                print("(no review items yet)")
            for k, s in st.items():
                rate = ("n/a" if s["approve_rate"] is None
                        else f"{100.0 * s['approve_rate']:.0f}%")
                print(f"{k:<14} pending={s['pending']:<4} approved={s['approved']:<4} "
                      f"rejected={s['rejected']:<4} approve-rate={rate}")
        else:
            ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
