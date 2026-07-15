"""Inbox adapters (first producer: tags-review) — hermetic contracts (D134 §4-D).

Every test runs on its own in-memory sqlite; the live DB is never opened
(every adapter function takes an explicit conn — the review_inbox pattern).
The fixture deliberately does NOT set row_factory: the adapter must swap in
sqlite3.Row for its theme_tags read and restore the caller's factory.

Contracts pinned here:
  registry  — KINDS is exactly the canonical closed set {tags, alert-ack,
              brief, rebalance, anomaly}; check_kinds() WARNS (never raises)
              on unregistered legacy kinds and stays silent when clean;
              adapter writes only ever use registered kinds.
  sync      — every pending keyword/LLM proposal becomes ONE pending inbox
              item (ref 'SYMBOL|TAG', payload carries proposer family +
              confidence + matched-keyword note, evidence_url is the legacy
              per-company editor); idempotent across re-runs (first write
              wins); commits PER ITEM so a caller rollback/close never eats
              the batch (the S153 lesson); row_factory restored.
  apply     — approved -> theme_tags.approve (source='ramana' promotion);
              rejected -> theme_tags.reject (DURABLE tombstone: the REAL
              keyword proposer refuses to re-propose the pair afterwards);
              double-run applies nothing (inbox_apply_log guard); a ref-only
              item ('SYMBOL|TAG' with '/' inside the tag) parses via the
              first-'|' split fallback.
  backfill  — pre-inbox ramana approvals + rejected tombstones import as
              DECIDED items with HONEST timestamps (original as_of date,
              payload imported=true); idempotent; imported items are
              pre-logged as applied so tags_apply never re-touches them
              (which would clobber the original company_tags as_of).
  drift     — a decision taken on the LEGACY surface leaves the twin inbox
              item pending; sync REPORTS it (stale_decided_on_legacy) and
              never auto-decides (Q1 recorded interim).
  grace     — a bare DB (no company_tags at all) yields zero-counts, no
              exceptions, from sync/apply/backfill alike.
"""
from __future__ import annotations

import sqlite3
import warnings

import pytest

from src.automation import inbox_adapters as ia
from src.automation import review_inbox as ri
from src.automation import theme_tags as tt


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")  # no row_factory on purpose (see docstring)
    c.executescript(ia._LEGACY_DDL)  # company_tags + company_about mini-schema
    yield c
    c.close()


def _seed_proposal(conn, sym="SOLARCO", tag="Power / Renewables",
                   source="keyword", conf=0.6, as_of="2026-07-01",
                   note="matched: solar, wind"):
    conn.execute(
        "INSERT OR REPLACE INTO company_tags"
        "(symbol, tag, source, confidence, as_of, approved, note) "
        "VALUES (?,?,?,?,?,0,?)", (sym, tag, source, conf, as_of, note))
    conn.commit()


# --- kind registry (Q2) ---------------------------------------------------------

def test_kinds_registry_is_the_canonical_closed_set():
    assert ia.KINDS == frozenset(
        {"tags", "alert-ack", "brief", "rebalance", "anomaly"})
    assert isinstance(ia.KINDS, frozenset)  # closed: extend only in-code
    assert ia.KIND_TAGS in ia.KINDS


def test_check_kinds_warns_on_unregistered_legacy_but_never_raises(conn):
    ri.ensure_schema(conn)
    ri.submit(conn, "tags", "A|B", "t")
    conn.execute(
        "INSERT INTO review_items(kind, ref, title, payload_json, status, created_at) "
        "VALUES ('legacy-x','r1','old row','{}','pending','2026-01-01T00:00:00Z')")
    conn.commit()
    with pytest.warns(UserWarning, match="unregistered"):
        out = ia.check_kinds(conn)
    assert out["registered"] == {"tags": 1}
    assert out["unregistered"] == {"legacy-x": 1}


def test_check_kinds_is_silent_when_clean(conn):
    ri.ensure_schema(conn)
    ri.submit(conn, "brief", "X|1", "t")
    conn.commit()
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning -> test failure
        out = ia.check_kinds(conn)
    assert out == {"registered": {"brief": 1}, "unregistered": {}}


# --- sync -------------------------------------------------------------------------

def test_sync_creates_pending_item_with_payload_note_and_evidence(conn):
    _seed_proposal(conn)
    out = ia.tags_sync(conn)
    assert out["proposals"] == 1 and out["created"] == 1 and out["existing"] == 0
    items = ri.pending(conn, kind="tags")
    assert len(items) == 1
    it = items[0]
    assert it["ref"] == "SOLARCO|Power / Renewables"
    assert it["title"] == "Proposed tag: Power / Renewables for SOLARCO"
    assert it["evidence_url"] == "/dash/tags-review?sym=SOLARCO"
    assert it["payload"]["symbol"] == "SOLARCO"
    assert it["payload"]["tag"] == "Power / Renewables"
    assert it["payload"]["source"] == "keyword"          # proposer family
    assert it["payload"]["confidence"] == 0.6
    assert it["payload"]["note"] == "matched: solar, wind"  # the keyword evidence
    kinds = {r[0] for r in conn.execute("SELECT DISTINCT kind FROM review_items")}
    assert kinds <= ia.KINDS  # adapters write registered kinds only


def test_sync_is_idempotent_first_write_wins(conn):
    _seed_proposal(conn)
    ia.tags_sync(conn)
    again = ia.tags_sync(conn)
    assert again["created"] == 0 and again["existing"] == 1
    items = ri.pending(conn, kind="tags")
    assert len(items) == 1  # no duplicate, no mutation
    assert items[0]["title"] == "Proposed tag: Power / Renewables for SOLARCO"


def test_sync_commits_per_item_so_rollback_cannot_eat_the_batch(conn):
    _seed_proposal(conn, sym="AAA", tag="PSU", note="matched: maharatna")
    _seed_proposal(conn, sym="BBB", tag="Aviation", note="matched: airline")
    out = ia.tags_sync(conn)
    assert out["created"] == 2
    conn.rollback()  # a close()-rollback must not lose the trailing insert
    assert len(ri.pending(conn, kind="tags")) == 2


def test_sync_restores_the_callers_row_factory(conn):
    assert conn.row_factory is None
    _seed_proposal(conn)
    ia.tags_sync(conn)
    assert conn.row_factory is None  # swapped to Row internally, restored


# --- apply ---------------------------------------------------------------------

def test_apply_approved_promotes_to_ramana_and_clears_proposal(conn):
    _seed_proposal(conn)
    ia.tags_sync(conn)
    item = ri.pending(conn, kind="tags")[0]
    ri.decide(conn, item["id"], "approved", note="good catch")
    conn.commit()
    out = ia.tags_apply(conn)
    assert out == {"applied_approved": 1, "applied_rejected": 0,
                   "skipped_unparseable": 0}
    row = conn.execute(
        "SELECT source, approved FROM company_tags "
        "WHERE symbol='SOLARCO' AND tag='Power / Renewables'").fetchall()
    assert row == [("ramana", 1)]  # promoted; keyword proposal row cleared


def test_apply_rejected_writes_a_DURABLE_tombstone(conn):
    # Real-journey durability: the REAL keyword proposer must refuse to
    # re-propose the pair after the inbox rejection is applied.
    conn.execute("INSERT INTO company_about(symbol, about) VALUES "
                 "('PORTCO','Operates ports and provides freight logistics services.')")
    conn.commit()
    n = tt.propose_from_keywords(conn=conn)
    assert n >= 1  # positive control: the proposer DOES propose it today
    assert conn.execute(
        "SELECT COUNT(*) FROM company_tags WHERE symbol='PORTCO' "
        "AND tag='Transport / Logistics' AND source='keyword'").fetchone()[0] == 1
    ia.tags_sync(conn)
    item = next(i for i in ri.pending(conn, kind="tags")
                if i["ref"] == "PORTCO|Transport / Logistics")
    ri.decide(conn, item["id"], "rejected", note="not a logistics company")
    conn.commit()
    out = ia.tags_apply(conn)
    assert out["applied_rejected"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM company_tags WHERE symbol='PORTCO' "
        "AND tag='Transport / Logistics' AND source='rejected'").fetchone()[0] == 1
    tt.propose_from_keywords(conn=conn)  # the weekly reseed
    assert conn.execute(
        "SELECT COUNT(*) FROM company_tags WHERE symbol='PORTCO' "
        "AND tag='Transport / Logistics' AND source='keyword'").fetchone()[0] == 0


def test_apply_double_run_is_a_noop(conn):
    _seed_proposal(conn)
    ia.tags_sync(conn)
    ri.decide(conn, ri.pending(conn, kind="tags")[0]["id"], "approved")
    conn.commit()
    first = ia.tags_apply(conn)
    assert first["applied_approved"] == 1
    second = ia.tags_apply(conn)
    assert second == {"applied_approved": 0, "applied_rejected": 0,
                      "skipped_unparseable": 0}
    assert conn.execute(
        "SELECT COUNT(*) FROM inbox_apply_log").fetchone()[0] == 1


def test_apply_parses_ref_fallback_including_slash_in_tag(conn):
    # A manually submitted item (empty payload) must still apply: the ref
    # splits on the FIRST '|' only, so '/' inside the vocab label survives.
    res = ri.submit(conn, "tags", "ACME|Power / Renewables", "manual submit",
                    payload={})
    conn.commit()
    ri.decide(conn, res["id"], "approved")
    conn.commit()
    out = ia.tags_apply(conn)
    assert out["applied_approved"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM company_tags WHERE symbol='ACME' "
        "AND tag='Power / Renewables' AND source='ramana' AND approved=1"
    ).fetchone()[0] == 1


# --- backfill (Q4) ----------------------------------------------------------------

def _seed_history(conn):
    conn.execute(
        "INSERT INTO company_tags(symbol, tag, source, confidence, as_of, approved) "
        "VALUES ('OLDCO','PSU','ramana',1.0,'2026-01-05',1)")
    conn.execute(
        "INSERT INTO company_tags(symbol, tag, source, as_of, approved, note) "
        "VALUES ('OLDCO','Aviation','rejected','2026-02-10',0,'dismissed')")
    conn.commit()


def test_backfill_imports_history_with_honest_timestamps(conn):
    _seed_history(conn)
    out = ia.tags_backfill(conn)
    assert out == {"imported_approved": 1, "imported_rejected": 1,
                   "skipped_existing": 0}
    hist = ri.corpus(conn, kind="tags")
    assert [h["status"] for h in hist] == ["approved", "rejected"]
    appr, rej = hist
    assert appr["ref"] == "OLDCO|PSU"
    assert appr["created_at"] == "2026-01-05T00:00:00Z"   # original date, honest
    assert appr["decided_at"] == "2026-01-05T00:00:00Z"
    assert appr["payload"]["imported"] is True
    assert appr["payload"]["origin"] == "ramana-approved"
    assert appr["payload"]["original_as_of"] == "2026-01-05"
    assert rej["decided_at"] == "2026-02-10T00:00:00Z"
    assert rej["payload"]["origin"] == "tombstone"
    st = ri.agreement_stats(conn, kind="tags")["tags"]
    assert st["decided"] == 2 and st["approve_rate"] == 0.5


def test_backfill_is_idempotent_and_apply_never_retouches_imports(conn):
    _seed_history(conn)
    ia.tags_backfill(conn)
    again = ia.tags_backfill(conn)
    assert again == {"imported_approved": 0, "imported_rejected": 0,
                     "skipped_existing": 2}
    # imported items are pre-logged as applied: tags_apply must not re-run
    # approve() over them (INSERT OR REPLACE would clobber the original as_of)
    out = ia.tags_apply(conn)
    assert sum(out.values()) == 0
    assert conn.execute(
        "SELECT as_of FROM company_tags WHERE symbol='OLDCO' AND tag='PSU' "
        "AND source='ramana'").fetchone()[0] == "2026-01-05"


# --- single-writer drift reporting (Q1) --------------------------------------------

def test_sync_reports_a_legacy_surface_decision_as_stale_never_autodecides(conn):
    _seed_proposal(conn)
    ia.tags_sync(conn)
    # Ramana clicks approve on the LEGACY /dash/tags-review surface instead:
    tt.approve(conn, "SOLARCO", "Power / Renewables")
    out = ia.tags_sync(conn)
    assert out["proposals"] == 0
    assert out["stale_decided_on_legacy"] == ["SOLARCO|Power / Renewables"]
    assert out["stale_proposal_gone"] == []
    # NOT auto-decided: the machine never fabricates a human verdict
    assert len(ri.pending(conn, kind="tags")) == 1


def test_sync_reports_an_evaporated_proposal_separately(conn):
    _seed_proposal(conn)
    ia.tags_sync(conn)
    # a reseed under a changed description clears the proposal — no decision
    conn.execute("DELETE FROM company_tags WHERE source='keyword'")
    conn.commit()
    out = ia.tags_sync(conn)
    assert out["stale_proposal_gone"] == ["SOLARCO|Power / Renewables"]
    assert out["stale_decided_on_legacy"] == []


# --- bare-DB grace ------------------------------------------------------------------

def test_bare_db_grace_zero_counts_no_exceptions():
    c = sqlite3.connect(":memory:")  # no company_tags/company_about at all
    try:
        s = ia.tags_sync(c)
        assert s["proposals"] == 0 and s["created"] == 0
        b = ia.tags_backfill(c)
        assert b == {"imported_approved": 0, "imported_rejected": 0,
                     "skipped_existing": 0}
        a = ia.tags_apply(c)
        assert sum(a.values()) == 0
        assert ia.check_kinds(c) == {"registered": {}, "unregistered": {}}
    finally:
        c.close()


# --- the whole journey ---------------------------------------------------------------

def test_selftest_round_trip_is_green():
    assert ia._selftest() == 0
