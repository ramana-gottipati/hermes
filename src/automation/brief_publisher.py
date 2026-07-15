"""Brief publisher — an APPROVED auto-analyst brief reaches a reader (D134 §4-E last mile, L6).

The L6 contract's final clause: `auto_analyst.py` drafts, the Review Inbox judges, and
**only an approved brief publishes**. This module is that last mile — and nothing else:
it never drafts, never decides, never calls an LLM. It moves an item a human already
approved onto the board the brief itself cites, and records that it did so exactly once.

🔴 WHERE BRIEFS PUBLISH — and why NOT "the wire" (a corrected plan wording, S159):
    Plan §4-E said "approved briefs publish to the wire/dossier". The wire (/dash/wire)
    renders `sent_news`, whose feed (`news_feed`) is an **UNCLASSIFIED vendor-ToS source** —
    deliberately held OUT of `feed_manifest.FEEDS` pending Ramana's plan §7.7 enum decision,
    and pinned there by a test. Writing house-authored AI text into that table would fuse our
    content with a vendor-ToS-caveated source and blur both provenance and licence class
    (Guardrail #8). So briefs publish to **our own `published_briefs` table**, rendered on
    `auto_analyst.BOARD_URL` (/dash/results-reactions) — the board the brief already cites as
    the source of every number in it. The reader lands where the evidence lives.

EXACTLY-ONCE: reuses the EXISTING kind-generic `inbox_apply_log` (inbox_adapters, S157) —
its docstring pins `item_id` as "review_items.id (unique across kinds)" and it carries a
`kind` column, i.e. the documented adapter extension point. `tags_apply()` filters on
kind='tags', so the two adapters share the ledger without ever seeing each other's rows.
A second `--publish` run is a no-op (the log's PK is the guard).

DECIDED-REJECTED briefs are logged too (action='skipped-rejected'), so a rejected draft is
never re-scanned and never published — the corpus keeps it as labeled data either way.

RETRACTION: `unpublish()` exists because publishing machine-drafted text to a reader without
an undo is not a defensible position. `review_inbox.decide()` is FINAL (double-decide
guarded), so a retraction is deliberately NOT a re-judgment: it sets `retracted_at`, the
render drops it, and the audit trail keeps both facts (approved then retracted, with a
reason). Re-publishing after a retraction requires a NEW brief (a new ref → a new judgment).

Stdlib-only. No LLM. No network. `db.py` untouched (own DDL, the S138 precedent).
CLI:
    python -m src.automation.brief_publisher --publish [--db PATH] [--dry-run]
    python -m src.automation.brief_publisher --list [--sym TCS] [--include-retracted]
    python -m src.automation.brief_publisher --unpublish <item_id> --reason "..."
    python -m src.automation.brief_publisher --selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Optional

HERMES_DB = "/opt/hermes/data/hermes.db"

KIND_BRIEF = "brief"                       # the kind auto_analyst produces (its KIND constant)
ACTION_PUBLISHED = "published"
ACTION_SKIPPED_REJECTED = "skipped-rejected"
ACTION_SKIPPED_UNPARSEABLE = "skipped-unparseable"

# --- owned table (isolation: db.py untouched) ---------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS published_briefs (
    item_id      INTEGER PRIMARY KEY,   -- review_items.id — one publish per judged item
    ref          TEXT NOT NULL,         -- auto_analyst ref, e.g. results:TCS:2026-06-30
    sym          TEXT,                  -- parsed from the ref; NULL if unparseable
    title        TEXT NOT NULL,
    text         TEXT NOT NULL,         -- the approved brief body, verbatim
    payload_json TEXT,                  -- the full approved payload (numbers + source map)
    label        TEXT,                  -- "AI-drafted, human-reviewed"
    approved_at  TEXT,                  -- review_items.decided_at — WHO/WHEN signed it
    published_at TEXT NOT NULL,
    retracted_at TEXT,                  -- non-NULL = pulled from the render (audit kept)
    retract_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_published_briefs_sym
    ON published_briefs (sym, published_at DESC);
"""


def ensure_schema(conn) -> None:
    """Idempotent creation of the owned publish table."""
    conn.executescript(_SCHEMA)


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _sym_from_ref(ref: str) -> Optional[str]:
    """'results:TCS:2026-06-30' -> 'TCS'. Unknown shapes return None (never guess)."""
    parts = (ref or "").split(":")
    if len(parts) >= 3 and parts[0] == "results" and parts[1].strip():
        return parts[1].strip().upper()
    return None


def _log(conn, item_id: int, ref: str, action: str) -> None:
    """Record into the SHARED kind-generic apply-log (inbox_adapters' owned table)."""
    from src.automation import inbox_adapters
    inbox_adapters.ensure_schema(conn)
    conn.execute(
        "INSERT OR IGNORE INTO inbox_apply_log (item_id, kind, ref, action, applied_at) "
        "VALUES (?,?,?,?,?)", (item_id, KIND_BRIEF, ref, action, _utcnow()))


def publish_approved(conn, *, dry_run: bool = False) -> dict:
    """Publish every APPROVED, not-yet-handled brief; log rejected ones as handled.

    Idempotent: the apply-log PK means a second run publishes nothing. Commits PER ITEM
    (the S153 LANE-E lesson — a crash mid-batch must not strand the batch).
    Returns {"published": n, "skipped_rejected": n, "skipped_unparseable": n}.
    """
    from src.automation import review_inbox
    from src.automation import inbox_adapters
    review_inbox.ensure_schema(conn)
    inbox_adapters.ensure_schema(conn)
    ensure_schema(conn)

    rows = conn.execute(
        "SELECT r.id, r.ref, r.status, r.title, r.payload_json, r.decided_at "
        "FROM review_items r LEFT JOIN inbox_apply_log l ON l.item_id = r.id "
        "WHERE r.kind=? AND r.status IN ('approved','rejected') AND l.item_id IS NULL "
        "ORDER BY r.decided_at ASC, r.id ASC", (KIND_BRIEF,)).fetchall()

    out = {"published": 0, "skipped_rejected": 0, "skipped_unparseable": 0}
    for item_id, ref, status, title, payload_json, decided_at in rows:
        if status == "rejected":
            if not dry_run:
                _log(conn, item_id, ref, ACTION_SKIPPED_REJECTED)
                conn.commit()
            out["skipped_rejected"] += 1
            continue
        try:
            payload = json.loads(payload_json or "{}")
        except ValueError:
            payload = {}
        text = (payload.get("text") or "").strip()
        if not text:
            # An approved item with no body is a data problem, not something to render.
            if not dry_run:
                _log(conn, item_id, ref, ACTION_SKIPPED_UNPARSEABLE)
                conn.commit()
            out["skipped_unparseable"] += 1
            continue
        if not dry_run:
            conn.execute(
                "INSERT OR IGNORE INTO published_briefs "
                "(item_id, ref, sym, title, text, payload_json, label, approved_at, "
                " published_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (item_id, ref, _sym_from_ref(ref), title, text, payload_json,
                 payload.get("label"), decided_at, _utcnow()))
            _log(conn, item_id, ref, ACTION_PUBLISHED)
            conn.commit()
        out["published"] += 1
    return out


def unpublish(conn, item_id: int, note: str = "") -> dict:
    """Retract a published brief: it leaves the render, the record stays (audit).

    Returns {"retracted": bool, "already": bool}. Unknown id raises ValueError — a
    silent no-op on a typo'd retraction is the wrong failure mode for public text.
    """
    ensure_schema(conn)
    row = conn.execute("SELECT retracted_at FROM published_briefs WHERE item_id=?",
                       (int(item_id),)).fetchone()
    if row is None:
        raise ValueError(f"no published brief with item_id={item_id}")
    if row[0]:
        return {"retracted": False, "already": True}
    conn.execute("UPDATE published_briefs SET retracted_at=?, retract_note=? "
                 "WHERE item_id=? AND retracted_at IS NULL",
                 (_utcnow(), (note or "")[:500], int(item_id)))
    conn.commit()
    return {"retracted": True, "already": False}


def published(conn, *, sym: Optional[str] = None, limit: int = 10,
              include_retracted: bool = False) -> list:
    """The render read: live published briefs, newest first. Empty-DB grace."""
    ensure_schema(conn)
    q = ("SELECT item_id, ref, sym, title, text, label, approved_at, published_at, "
         "retracted_at FROM published_briefs")
    where, args = [], []
    if not include_retracted:
        where.append("retracted_at IS NULL")
    if sym:
        where.append("sym = ?")
        args.append(str(sym).strip().upper())
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY published_at DESC, item_id DESC LIMIT ?"
    args.append(int(limit))
    cols = ("item_id", "ref", "sym", "title", "text", "label", "approved_at",
            "published_at", "retracted_at")
    return [dict(zip(cols, r)) for r in conn.execute(q, args).fetchall()]


def stats(conn) -> dict:
    """{'live': n, 'retracted': n} — the board's honest counter + ops read."""
    ensure_schema(conn)
    live = conn.execute("SELECT count(*) FROM published_briefs "
                        "WHERE retracted_at IS NULL").fetchone()[0]
    ret = conn.execute("SELECT count(*) FROM published_briefs "
                       "WHERE retracted_at IS NOT NULL").fetchone()[0]
    return {"live": int(live), "retracted": int(ret)}


# ------------------------------------------------------------------------ selftest
def _selftest() -> int:
    from src.automation import review_inbox
    conn = sqlite3.connect(":memory:")
    review_inbox.ensure_schema(conn)

    payload = {"text": "TCS reported (Q period ending 2026-06-30).\nAI-drafted, "
                       "human-reviewed · context, not a signal.",
               "label": "AI-drafted, human-reviewed",
               "numbers": {"sue": {"value": 1.2, "source": "/dash/results-reactions"}}}
    a = review_inbox.submit(conn, "brief", "results:TCS:2026-06-30",
                            "Results brief — TCS Q 2026-06-30", payload)
    b = review_inbox.submit(conn, "brief", "results:INFY:2026-06-30",
                            "Results brief — INFY Q 2026-06-30", payload)
    c = review_inbox.submit(conn, "brief", "results:WIPRO:2026-06-30",
                            "Results brief — WIPRO Q 2026-06-30", {"text": ""})
    conn.commit()

    # nothing is published while nothing is decided — the whole point of the gate
    assert publish_approved(conn) == {"published": 0, "skipped_rejected": 0,
                                      "skipped_unparseable": 0}
    assert published(conn) == []

    review_inbox.decide(conn, a["id"], "approved", "reads fine")
    review_inbox.decide(conn, b["id"], "rejected", "not useful")
    review_inbox.decide(conn, c["id"], "approved", "body is empty though")
    conn.commit()

    dry = publish_approved(conn, dry_run=True)
    assert dry == {"published": 1, "skipped_rejected": 1, "skipped_unparseable": 1}, dry
    assert published(conn) == [], "dry-run must not write"

    r1 = publish_approved(conn)
    assert r1 == {"published": 1, "skipped_rejected": 1, "skipped_unparseable": 1}, r1
    r2 = publish_approved(conn)                     # idempotent: the log is the guard
    assert r2 == {"published": 0, "skipped_rejected": 0, "skipped_unparseable": 0}, r2

    live = published(conn)
    assert len(live) == 1 and live[0]["sym"] == "TCS", live
    assert live[0]["approved_at"], "the human signature (decided_at) must travel"
    assert published(conn, sym="INFY") == [], "a rejected brief never publishes"
    assert stats(conn) == {"live": 1, "retracted": 0}

    # durability across a second connection is the real test (per-item commit)
    assert _sym_from_ref("results:TCS:2026-06-30") == "TCS"
    assert _sym_from_ref("nonsense") is None

    u = unpublish(conn, live[0]["item_id"], note="selftest retraction")
    assert u == {"retracted": True, "already": False}
    assert published(conn) == [], "a retracted brief leaves the render"
    assert len(published(conn, include_retracted=True)) == 1, "the record stays (audit)"
    assert unpublish(conn, live[0]["item_id"])["already"] is True
    assert stats(conn) == {"live": 0, "retracted": 1}
    try:
        unpublish(conn, 999999)
        raise AssertionError("unknown id must raise")
    except ValueError:
        pass
    conn.close()
    print("BRIEF_PUBLISHER selftest OK")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Publish APPROVED auto-analyst briefs.")
    p.add_argument("--publish", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--unpublish", type=int, metavar="ITEM_ID")
    p.add_argument("--reason", default="")
    p.add_argument("--sym", default="")
    p.add_argument("--include-retracted", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--db", default=HERMES_DB)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return _selftest()
    conn = sqlite3.connect(a.db, timeout=30)
    try:
        if a.publish:
            out = publish_approved(conn, dry_run=a.dry_run)
            print(("DRY-RUN " if a.dry_run else "") +
                  "published=%(published)d skipped_rejected=%(skipped_rejected)d "
                  "skipped_unparseable=%(skipped_unparseable)d" % out)
            print("stats:", stats(conn))
            return 0
        if a.unpublish:
            print(unpublish(conn, a.unpublish, note=a.reason))
            return 0
        if a.list:
            rows = published(conn, sym=a.sym or None, limit=50,
                             include_retracted=a.include_retracted)
            for r in rows:
                mark = " [RETRACTED]" if r["retracted_at"] else ""
                print(f"{r['item_id']:>5}  {r['published_at']}  {r['ref']}{mark}")
            print(f"({len(rows)} shown) stats: {stats(conn)}")
            return 0
        print(__doc__)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
