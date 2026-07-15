"""Inbox adapters — wiring existing review flows into the Review Inbox (L5).

FIRST PRODUCER (D134 plan §4-D follow-through): tags-review. theme_tags'
keyword/LLM proposals become review-inbox items (kind='tags'); the human
verdict flows BACK through theme_tags' own approve/reject helpers, so the
legacy storage semantics (source='ramana' promotion, DURABLE source='rejected'
tombstones the weekly reseed respects) are reused, never reimplemented.
Every tag decision now lands in the judgment corpus (`review_inbox.corpus`),
and `agreement_stats('tags')` starts measuring which proposer families
(keyword vs llm) earn trust.

SINGLE-WRITER DOCTRINE — the recorded interim (LANE-D open question Q1):
    From this module's landing onward the Review Inbox is the CANONICAL
    decision path for tag proposals. The legacy /dash/tags-review surface
    (cockpit.py — forked-file territory this module must not touch) remains
    fully functional: its buttons still call theme_tags.approve/reject
    directly, but those writes BYPASS the judgment corpus. Bridging or
    retiring the legacy writes happens at the inbox-surface session
    (SURFACE-PLAYBOOK; LANE-R territory). Until then:
      • a legacy-side decision leaves its twin inbox item pending —
        tags_sync() REPORTS these as stale (stale_decided_on_legacy) and
        never auto-decides: a machine must not fabricate a human verdict;
      • if both surfaces decide the same (symbol, tag), the last applied
        write wins in company_tags-land (theme_tags helpers are
        INSERT OR REPLACE by construction) — with tags_apply typically
        running last on the weekly timer, the inbox verdict prevails.

KIND REGISTRY (LANE-D open question Q2): KINDS below is the canonical
closed set. 'tags' (this adapter) and 'brief' (auto_analyst, live since
S153) are producing today; 'alert-ack', 'rebalance', 'anomaly' are declared
extension points from review_inbox's design docstring. Extending the set =
add the kind HERE in the same commit as its producer. check_kinds() is the
census: unregistered kinds in review_items WARN (legacy tolerance) but the
canonical set is what tests pin.

CORPUS BACKFILL (LANE-D open question Q4): tags_backfill() imports the
pre-inbox history — every source='ramana' approved tag and every durable
source='rejected' tombstone — as already-decided items with HONEST
timestamps: created_at/decided_at = the row's original as_of date
(midnight UTC, 'YYYY-MM-DDT00:00:00Z') when present, else the import
moment; payload carries imported=true so the corpus can always separate
lived decisions from imported ones. Because review_inbox.decide() honestly
stamps 'now', the backfill performs the ONE sanctioned direct UPDATE of
review_items (the two timestamp columns only, right after a legal
submit->decide transition) — documented here so it never becomes a pattern.
Imported items are pre-logged as applied: they already ARE the
company_tags state, and re-applying would clobber the original as_of.

WRITE SEMANTICS (the S153 lesson): review_inbox.submit() does NOT commit,
and its ensure_schema() DDL auto-commits mid-batch — so every loop below
commits per item; a crash mid-batch keeps what was queued and the trailing
insert is never lost to close()-rollback. theme_tags.approve/reject commit
themselves, which makes each apply atomic: the apply-log row is inserted
uncommitted first, then the helper's own commit lands both together.

APPLIED-STATE TRACKING: own table `inbox_apply_log` (item_id PK), created
here via CREATE TABLE IF NOT EXISTS — db.py, theme_tags.py and
review_inbox.py are untouched. Payload mutation was rejected for this:
the payload is what the human judged and must stay immutable.

TIMER PIGGYBACK (documented, deliberately NOT wired this round): the weekly
hermes-theme-seed.timer runs `theme_tags --seed --keyword-propose`. When
LANE-R wires this producer, append a second ExecStart line to the oneshot
service (systemd runs them serially):
    ExecStart=/opt/hermes/.venv/bin/python -m src.automation.inbox_adapters --sync --apply
Fresh proposals then flow into the inbox right after each reseed and the
week's verdicts are applied in the same pass. One-pass convergence holds
even when the reseed re-proposes a decided-but-unapplied pair: sync's
re-submit is idempotent-ignored (first write wins on (kind, ref)) and
apply's reject() deletes the transient re-proposal while writing the
tombstone. NO unit edits ship in this commit.

KNOWN LIMIT (by review_inbox contract, recorded): refs are 'SYMBOL|TAG',
so one verdict per (symbol, tag) lives in the corpus. A re-proposal after
unreject() (a rare, deliberate manual act on the legacy surface) will not
re-enter the inbox under the same ref — handle at the inbox-surface
session if it ever matters in practice.

CLI:
    python -m src.automation.inbox_adapters --sync       # proposals -> inbox
    python -m src.automation.inbox_adapters --apply      # inbox verdicts -> theme_tags
    python -m src.automation.inbox_adapters --backfill   # one-shot corpus import
    python -m src.automation.inbox_adapters --kinds      # kind-registry census
    python -m src.automation.inbox_adapters --selftest   # hermetic round-trip (temp db)
Flags combine; execution order is backfill -> sync -> apply -> kinds.
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import warnings
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.automation import review_inbox, theme_tags

log = logging.getLogger("hermes.inbox_adapters")

# --- canonical kind registry (Q2) --------------------------------------------
# Closed set; extend HERE in the same commit as a new producer. 'tags' and
# 'brief' produce today; the rest are review_inbox's declared adapters.
KINDS: frozenset = frozenset({"tags", "alert-ack", "brief", "rebalance", "anomaly"})
KIND_TAGS = "tags"

EVIDENCE_URL_FMT = "/dash/tags-review?sym={sym}"  # legacy per-company editor

# --- owned table (isolation: db.py untouched) ---------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS inbox_apply_log (
    item_id    INTEGER PRIMARY KEY,   -- review_items.id (unique across kinds)
    kind       TEXT NOT NULL,
    ref        TEXT NOT NULL,
    action     TEXT NOT NULL,         -- applied-approved | applied-rejected |
                                      -- imported | skipped-unparseable
    applied_at TEXT NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Idempotent creation of the owned apply-log table."""
    conn.executescript(_SCHEMA)


def _utcnow() -> str:
    """UTC ISO-8601 stamp (same format as review_inbox; patchable in tests)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_table(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def _sym_tag(payload, ref) -> Tuple[str, str]:
    """(symbol, tag) for an item — payload first, 'SYMBOL|TAG' ref fallback.

    Accepts the parsed payload dict (pending()/corpus() shape) or the raw
    payload_json string (direct SQL shape). The ref splits on the FIRST '|'
    only, so vocab labels containing '/' (e.g. 'Power / Renewables') survive.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload or "{}")
        except ValueError:
            payload = {}
    payload = payload if isinstance(payload, dict) else {}
    sym = str(payload.get("symbol") or "").strip().upper()
    tag = str(payload.get("tag") or "").strip()
    if (not sym or not tag) and ref and "|" in ref:
        s, t = str(ref).split("|", 1)
        sym = sym or s.strip().upper()
        tag = tag or t.strip()
    return sym, tag


def check_kinds(conn) -> dict:
    """Kind census over review_items vs the canonical registry (Q2).

    Returns {"registered": {kind: n}, "unregistered": {kind: n}}.
    Unregistered kinds WARN (legacy tolerance) — never raise: an old row must
    not brick the queue, but the warning keeps drift visible.
    """
    review_inbox.ensure_schema(conn)
    registered: dict = {}
    unregistered: dict = {}
    for k, n in conn.execute(
            "SELECT kind, COUNT(*) FROM review_items GROUP BY kind").fetchall():
        (registered if k in KINDS else unregistered)[k] = int(n)
    if unregistered:
        warnings.warn(
            "review_items carries unregistered kinds (legacy?): "
            f"{sorted(unregistered)} — canonical registry: {sorted(KINDS)}",
            stacklevel=2)
    return {"registered": registered, "unregistered": unregistered}


# --- producer: theme-tag proposals -> inbox -----------------------------------

def _pending_proposals(conn) -> list:
    """theme_tags.proposals_pending via a row_factory-safe window.

    proposals_pending() builds dicts with dict(row), which needs sqlite3.Row;
    the live get_conn() sets it, an injected test conn may not — swap it in
    for the read and ALWAYS restore the caller's factory.
    """
    prior = conn.row_factory
    try:
        conn.row_factory = sqlite3.Row
        return theme_tags.proposals_pending(conn, limit=1_000_000)
    finally:
        conn.row_factory = prior


def _stale_pending_census(conn, live_pairs: set) -> dict:
    """Report inbox-pending tag items whose underlying proposal is gone (Q1).

    Two honest buckets, NEVER auto-decided:
      stale_decided_on_legacy — company_tags now shows a ramana/rejected row
        for the pair: the human decided on the legacy surface, bypassing the
        corpus (the interim drift this module's docstring records).
      stale_proposal_gone — the proposal simply evaporated (a reseed under a
        changed description); the item stays for the human to judge or the
        inbox surface to garbage-collect later.
    """
    out = {"stale_decided_on_legacy": [], "stale_proposal_gone": []}
    if not _has_table(conn, "company_tags"):
        return out
    for it in review_inbox.pending(conn, kind=KIND_TAGS):
        sym, tag = _sym_tag(it.get("payload"), it.get("ref"))
        if not sym or not tag or (sym, tag) in live_pairs:
            continue
        row = conn.execute(
            "SELECT MAX(source='ramana'), MAX(source='rejected') "
            "FROM company_tags WHERE symbol=? AND tag=?", (sym, tag)).fetchone()
        legacy = bool(row and (row[0] or row[1]))
        key = "stale_decided_on_legacy" if legacy else "stale_proposal_gone"
        out[key].append(it["ref"])
    return out


def tags_sync(conn) -> dict:
    """Queue every pending keyword/LLM tag proposal as a review-inbox item.

    Idempotent end to end: review_inbox.submit is first-write-wins on
    (kind='tags', ref='SYMBOL|TAG'), so weekly re-runs never duplicate and a
    decided item is never resurrected. Payload carries the proposer family
    (source), confidence and the matched-keyword note — the evidence the
    judgment corpus keeps. Commits per item (see module docstring).
    """
    review_inbox.ensure_schema(conn)
    ensure_schema(conn)
    if not _has_table(conn, "company_tags"):  # bare-DB grace: nothing to sync
        return {"proposals": 0, "created": 0, "existing": 0,
                "stale_decided_on_legacy": [], "stale_proposal_gone": []}
    props = _pending_proposals(conn)
    created = 0
    live_pairs = set()
    for p in props:
        sym = str(p.get("symbol") or "").strip().upper()
        tag = str(p.get("tag") or "").strip()
        if not sym or not tag:
            continue
        live_pairs.add((sym, tag))
        res = review_inbox.submit(
            conn, KIND_TAGS, f"{sym}|{tag}",
            f"Proposed tag: {tag} for {sym}",
            payload={"symbol": sym, "tag": tag,
                     "source": p.get("source"),
                     "confidence": p.get("confidence"),
                     "proposed_as_of": p.get("as_of"),
                     "note": p.get("note")},
            evidence_url=EVIDENCE_URL_FMT.format(sym=sym))
        conn.commit()  # per item — S153 lesson (DDL auto-commits mid-batch)
        if res.get("created"):
            created += 1
    out = {"proposals": len(props), "created": created,
           "existing": len(props) - created}
    out.update(_stale_pending_census(conn, live_pairs))
    if out["stale_decided_on_legacy"]:
        log.warning("tags_sync: %d inbox item(s) decided on the LEGACY surface "
                    "(corpus bypassed): %s", len(out["stale_decided_on_legacy"]),
                    out["stale_decided_on_legacy"])
    return out


# --- consumer: inbox verdicts -> theme_tags -----------------------------------

def tags_apply(conn) -> dict:
    """Apply every decided-but-unapplied kind='tags' verdict to company_tags.

    approved -> theme_tags.approve (durable source='ramana' promotion);
    rejected -> theme_tags.reject (the DURABLE tombstone path — the weekly
    reseed will never re-propose the pair). Both helpers commit themselves,
    and the apply-log row is inserted uncommitted just before the call, so
    log + tag mutation land in ONE transaction: exactly-once by construction,
    and a second run is a no-op (double-apply guard = inbox_apply_log PK).
    Unparseable items are logged as skipped so they can't wedge the queue.
    """
    review_inbox.ensure_schema(conn)
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT r.id, r.ref, r.status, r.payload_json "
        "FROM review_items r LEFT JOIN inbox_apply_log l ON l.item_id = r.id "
        "WHERE r.kind=? AND r.status IN ('approved','rejected') "
        "AND l.item_id IS NULL ORDER BY r.decided_at ASC, r.id ASC",
        (KIND_TAGS,)).fetchall()
    out = {"applied_approved": 0, "applied_rejected": 0, "skipped_unparseable": 0}
    for item_id, ref, status, payload_json in rows:
        sym, tag = _sym_tag(payload_json, ref)
        if not sym or not tag:
            conn.execute(
                "INSERT OR IGNORE INTO inbox_apply_log"
                "(item_id, kind, ref, action, applied_at) VALUES (?,?,?,?,?)",
                (item_id, KIND_TAGS, ref, "skipped-unparseable", _utcnow()))
            conn.commit()
            out["skipped_unparseable"] += 1
            log.warning("tags_apply: item %s ref %r has no parseable "
                        "(symbol, tag) — logged and skipped", item_id, ref)
            continue
        conn.execute(
            "INSERT OR IGNORE INTO inbox_apply_log"
            "(item_id, kind, ref, action, applied_at) VALUES (?,?,?,?,?)",
            (item_id, KIND_TAGS, ref, f"applied-{status}", _utcnow()))
        if status == "approved":
            theme_tags.approve(conn, sym, tag)   # commits log row + ramana row
            out["applied_approved"] += 1
        else:
            theme_tags.reject(conn, sym, tag)    # commits log row + tombstone
            out["applied_rejected"] += 1
    return out


# --- corpus backfill (Q4) ------------------------------------------------------

def _honest_stamp(as_of, fallback: str) -> str:
    """Original decision date -> ISO stamp; the import moment when absent."""
    s = str(as_of or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10] + "T00:00:00Z"
    return fallback


def tags_backfill(conn) -> dict:
    """Import the pre-inbox judgment history so agreement_stats starts honest.

    source='ramana' rows -> decided approved; source='rejected' tombstones ->
    decided rejected. Timestamps are the original as_of date (see module
    docstring — the one sanctioned direct UPDATE); payload flags imported=true.
    Imported items are pre-logged in inbox_apply_log: they already ARE the
    company_tags state — re-applying would clobber the original as_of.
    Idempotent: an existing (kind, ref) is counted skipped, never re-decided.
    """
    review_inbox.ensure_schema(conn)
    ensure_schema(conn)
    out = {"imported_approved": 0, "imported_rejected": 0, "skipped_existing": 0}
    if not _has_table(conn, "company_tags"):  # bare-DB grace
        return out
    rows = conn.execute(
        "SELECT symbol, tag, source, as_of, note FROM company_tags "
        "WHERE source IN ('ramana','rejected') "
        "ORDER BY as_of ASC, symbol ASC, tag ASC").fetchall()
    for sym, tag, source, as_of, note in rows:
        sym = str(sym or "").strip().upper()
        tag = str(tag or "").strip()
        if not sym or not tag:
            continue
        verdict = "approved" if source == "ramana" else "rejected"
        origin = "ramana-approved" if source == "ramana" else "tombstone"
        now = _utcnow()
        stamp = _honest_stamp(as_of, now)
        res = review_inbox.submit(
            conn, KIND_TAGS, f"{sym}|{tag}",
            f"[imported] Tag decision: {tag} for {sym}",
            payload={"symbol": sym, "tag": tag, "imported": True,
                     "origin": origin, "original_as_of": as_of, "note": note},
            evidence_url=EVIDENCE_URL_FMT.format(sym=sym))
        if not res.get("created"):
            out["skipped_existing"] += 1
            conn.commit()
            continue
        review_inbox.decide(
            conn, res["id"], verdict,
            note="imported from company_tags (pre-inbox history)")
        # honest timestamps — the ONE sanctioned direct write (module docstring)
        conn.execute(
            "UPDATE review_items SET created_at=?, decided_at=? WHERE id=?",
            (stamp, stamp, res["id"]))
        conn.execute(
            "INSERT OR IGNORE INTO inbox_apply_log"
            "(item_id, kind, ref, action, applied_at) VALUES (?,?,?,?,?)",
            (res["id"], KIND_TAGS, f"{sym}|{tag}", "imported", now))
        conn.commit()  # per item
        out["imported_" + verdict] += 1
    return out


# --- selftest (hermetic: its own temp-file db; never opens the live DB) --------

_LEGACY_DDL = """
CREATE TABLE IF NOT EXISTS company_tags (
    symbol      TEXT NOT NULL,
    tag         TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'index',
    confidence  REAL,
    as_of       TEXT NOT NULL DEFAULT (date('now')),
    approved    INTEGER NOT NULL DEFAULT 1,
    note        TEXT,
    PRIMARY KEY (symbol, tag, source)
);
CREATE TABLE IF NOT EXISTS company_about (
    symbol            TEXT PRIMARY KEY,
    about             TEXT,
    screener_industry TEXT,
    fetched_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _selftest() -> int:
    import os
    import shutil
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="inbox_adapters_selftest_")
    path = os.path.join(tmpdir, "selftest.db")
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_LEGACY_DDL)
        # pre-inbox history for the backfill: one lived approval, one dismissal
        conn.execute("INSERT INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
                     "VALUES ('OLDCO','PSU','ramana',1.0,'2026-01-05',1)")
        conn.execute("INSERT INTO company_tags(symbol, tag, source, as_of, approved, note) "
                     "VALUES ('OLDCO','Aviation','rejected','2026-02-10',0,'dismissed')")
        # live descriptions for the REAL keyword proposer
        conn.execute("INSERT INTO company_about(symbol, about) VALUES "
                     "('SOLARCO','Develops solar and wind power generation projects across India.')")
        conn.execute("INSERT INTO company_about(symbol, about) VALUES "
                     "('PORTCO','Operates ports and provides freight logistics services.')")
        conn.commit()

        n = theme_tags.propose_from_keywords(conn=conn)
        print(f"ok: keyword proposer wrote {n} proposals (real rules, temp db)")
        assert n >= 2

        bf = tags_backfill(conn)
        assert bf["imported_approved"] == 1 and bf["imported_rejected"] == 1
        hist = review_inbox.corpus(conn, kind=KIND_TAGS)
        assert hist[0]["decided_at"] == "2026-01-05T00:00:00Z"
        assert hist[0]["payload"]["imported"] is True
        print(f"ok: backfill imported {bf} with honest original-date stamps")
        assert tags_backfill(conn)["skipped_existing"] == 2  # idempotent

        s = tags_sync(conn)
        assert s["created"] == n and s["existing"] == 0
        s2 = tags_sync(conn)
        assert s2["created"] == 0 and s2["existing"] == n
        print(f"ok: sync queued {s['created']} proposals; re-run created 0 (idempotent)")

        pend = review_inbox.pending(conn, kind=KIND_TAGS)
        solar = next(i for i in pend if i["ref"].startswith("SOLARCO|"))
        port = next(i for i in pend if i["ref"].startswith("PORTCO|Transport"))
        assert solar["payload"]["note"].startswith("matched:")
        assert solar["evidence_url"] == "/dash/tags-review?sym=SOLARCO"
        review_inbox.decide(conn, solar["id"], "approved", note="good catch")
        review_inbox.decide(conn, port["id"], "rejected", note="not a logistics co")
        print("ok: human decided in the inbox (1 approve, 1 reject)")

        ap = tags_apply(conn)
        assert ap["applied_approved"] == 1 and ap["applied_rejected"] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM company_tags WHERE symbol='SOLARCO' "
            "AND source='ramana' AND approved=1").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM company_tags WHERE symbol='PORTCO' "
            "AND tag LIKE 'Transport%' AND source='rejected'").fetchone()[0] == 1
        ap2 = tags_apply(conn)
        assert sum(ap2.values()) == 0
        print(f"ok: apply -> ramana promotion + durable tombstone; re-run applied 0")

        n2 = theme_tags.propose_from_keywords(conn=conn)
        gone = conn.execute(
            "SELECT COUNT(*) FROM company_tags WHERE symbol='PORTCO' "
            "AND tag LIKE 'Transport%' AND approved=0 AND source='keyword'").fetchone()[0]
        assert gone == 0, "tombstoned pair must never be re-proposed"
        print(f"ok: reseed wrote {n2} proposals; tombstoned pair NOT re-proposed (durable)")

        st = review_inbox.agreement_stats(conn, kind=KIND_TAGS)[KIND_TAGS]
        kc = check_kinds(conn)
        assert kc["unregistered"] == {} and set(kc["registered"]) == {KIND_TAGS}
        print(f"ok: agreement_stats tags = {st}")
        print("selftest: ALL PASS (propose -> backfill -> sync -> decide -> "
              "apply -> durable tombstone -> stats)")
        return 0
    finally:
        conn.close()
        shutil.rmtree(tmpdir, ignore_errors=True)


# --- CLI ------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Inbox adapters — tags-review wired into the Review Inbox "
                    "(first producer, D134 plan §4-D).")
    ap.add_argument("--sync", action="store_true",
                    help="queue pending tag proposals as inbox items")
    ap.add_argument("--apply", action="store_true",
                    help="apply decided inbox verdicts via theme_tags helpers")
    ap.add_argument("--backfill", action="store_true",
                    help="one-shot import of pre-inbox ramana/tombstone history")
    ap.add_argument("--kinds", action="store_true",
                    help="kind-registry census (warns on unregistered kinds)")
    ap.add_argument("--selftest", action="store_true",
                    help="hermetic round-trip on a temp db (never the live DB)")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not (args.sync or args.apply or args.backfill or args.kinds):
        ap.print_help()
        return 0

    from src.core.db import get_conn  # lazy: only the live paths need it
    with get_conn() as conn:
        if args.backfill:
            print("backfill:", json.dumps(tags_backfill(conn)))
        if args.sync:
            print("sync:", json.dumps(tags_sync(conn)))
        if args.apply:
            print("apply:", json.dumps(tags_apply(conn)))
        if args.kinds:
            print("kinds:", json.dumps(check_kinds(conn)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
