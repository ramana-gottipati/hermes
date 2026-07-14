"""Review Inbox (L5 judgment primitive) — hermetic contracts (D134 LANE-D).

Every test runs on its own in-memory sqlite; the live DB is never opened
(review_inbox's API takes an explicit conn — the signal_alerts injection
pattern). The fixture deliberately does NOT set row_factory, pinning that the
module is row_factory-independent (dicts are built from cursor.description).

Contracts pinned here:
  submit    — creates pending; idempotent on (kind, ref) with first-write-wins;
              (kind, ref) uniqueness is per-kind (same ref under two kinds is
              two items — the adapter extension point); blank args raise;
              kind normalizes to lowercase so stats families never split.
  payload   — JSON round-trips exactly (nested + unicode); None → {}.
  decide    — stamps verdict/note/decided_at; verdict aliases accepted;
              invalid verdict / unknown id raise; DOUBLE-DECIDE IS BLOCKED and
              the first decision survives untouched.
  pending   — only pending items, oldest-first drain order, kind filter.
  corpus    — only decided items, chronological, kind + since (date-prefix)
              filters; the judgment dataset round-trips payloads.
  stats     — approve-rate math per family; None (not div-by-zero) before any
              decision; unknown kind and empty DB degrade to {} gracefully.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.automation import review_inbox as ri


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")  # no row_factory on purpose (see docstring)
    ri.ensure_schema(c)
    yield c
    c.close()


def _clock(monkeypatch, stamps):
    """Drive review_inbox's clock through a fixed sequence of ISO stamps."""
    seq = iter(stamps)
    monkeypatch.setattr(ri, "_utcnow", lambda: next(seq))


# --- submit -------------------------------------------------------------------

def test_submit_creates_pending_item(conn):
    res = ri.submit(conn, "tags", "RELIANCE|Defence", "Proposed tag: Defence",
                    payload={"conf": 0.7}, evidence_url="/dash/sym/RELIANCE")
    assert res["created"] is True
    assert isinstance(res["id"], int)
    items = ri.pending(conn)
    assert len(items) == 1
    it = items[0]
    assert it["id"] == res["id"]
    assert it["kind"] == "tags"
    assert it["ref"] == "RELIANCE|Defence"
    assert it["title"] == "Proposed tag: Defence"
    assert it["evidence_url"] == "/dash/sym/RELIANCE"
    assert it["status"] == "pending"
    assert it["created_at"]
    assert it["decided_at"] is None
    assert it["note"] is None
    assert "payload_json" not in it  # parsed into 'payload'


def test_submit_idempotent_first_write_wins(conn):
    first = ri.submit(conn, "tags", "TCS|IT", "Original title",
                      payload={"v": 1})
    again = ri.submit(conn, "tags", "TCS|IT", "Mutated title",
                      payload={"v": 2}, evidence_url="/elsewhere")
    assert first["created"] is True
    assert again["created"] is False
    assert again["id"] == first["id"]
    items = ri.pending(conn)
    assert len(items) == 1
    assert items[0]["title"] == "Original title"
    assert items[0]["payload"] == {"v": 1}
    assert items[0]["evidence_url"] is None


def test_same_ref_different_kind_are_distinct(conn):
    a = ri.submit(conn, "tags", "INFY|2026-07-15", "tag proposal")
    b = ri.submit(conn, "brief", "INFY|2026-07-15", "event brief draft")
    assert a["created"] is True and b["created"] is True
    assert a["id"] != b["id"]
    assert len(ri.pending(conn)) == 2


def test_submit_validation_rejects_blanks(conn):
    with pytest.raises(ValueError):
        ri.submit(conn, "", "ref", "title")
    with pytest.raises(ValueError):
        ri.submit(conn, "tags", "   ", "title")
    with pytest.raises(ValueError):
        ri.submit(conn, "tags", "ref", "")
    assert ri.pending(conn) == []


def test_kind_normalized_lowercase(conn):
    a = ri.submit(conn, "Tags", "X|1", "t1")
    b = ri.submit(conn, "  TAGS ", "X|1", "t2")  # same family, same ref
    assert b["created"] is False and b["id"] == a["id"]
    assert ri.pending(conn)[0]["kind"] == "tags"
    assert set(ri.agreement_stats(conn)) == {"tags"}  # family never splits


# --- payload round-trip ---------------------------------------------------------

def test_payload_round_trip_nested_unicode(conn):
    pay = {"why": ["kw:defence", "₹500cr order", "प्रस्ताव"],
           "scores": {"kw": 0.72, "llm": None},
           "n": 3, "hot": True}
    res = ri.submit(conn, "tags", "HAL|Defence", "tag", payload=pay)
    ri.decide(conn, res["id"], "approved")
    got = ri.corpus(conn)[0]["payload"]
    assert got == pay


def test_payload_none_becomes_empty_dict(conn):
    ri.submit(conn, "alert-ack", "TCS|cci", "cci drop")
    assert ri.pending(conn)[0]["payload"] == {}


# --- decide ---------------------------------------------------------------------

def test_decide_stamps_verdict_note_time(conn, monkeypatch):
    res = ri.submit(conn, "tags", "SBIN|PSU", "tag")
    _clock(monkeypatch, ["2026-07-15T09:30:00Z"])
    out = ri.decide(conn, res["id"], "approved", note="clear PSU bank")
    assert out["status"] == "approved"
    assert out["note"] == "clear PSU bank"
    assert out["decided_at"] == "2026-07-15T09:30:00Z"
    assert ri.pending(conn) == []  # decided items leave the queue


def test_decide_verdict_aliases_and_invalid(conn):
    a = ri.submit(conn, "tags", "A|1", "t")
    b = ri.submit(conn, "tags", "B|1", "t")
    assert ri.decide(conn, a["id"], "approve")["status"] == "approved"
    assert ri.decide(conn, b["id"], "REJECT")["status"] == "rejected"
    c = ri.submit(conn, "tags", "C|1", "t")
    with pytest.raises(ValueError):
        ri.decide(conn, c["id"], "maybe")
    with pytest.raises(ValueError):
        ri.decide(conn, c["id"], None)
    assert ri.pending(conn, kind="tags")[0]["id"] == c["id"]  # still pending


def test_double_decide_guard(conn):
    res = ri.submit(conn, "brief", "TCS|q1-results", "draft brief")
    first = ri.decide(conn, res["id"], "approved", note="ship it")
    with pytest.raises(ValueError, match="already decided"):
        ri.decide(conn, res["id"], "rejected", note="changed my mind")
    # the first decision is immutable
    row = ri.corpus(conn, kind="brief")[0]
    assert row["status"] == "approved"
    assert row["note"] == "ship it"
    assert row["decided_at"] == first["decided_at"]


def test_decide_unknown_id_raises(conn):
    with pytest.raises(ValueError, match="no review item"):
        ri.decide(conn, 424242, "approved")


# --- pending queue ---------------------------------------------------------------

def test_pending_kind_filter_and_drain_order(conn, monkeypatch):
    _clock(monkeypatch, ["2026-07-15T00:00:01Z",
                         "2026-07-15T00:00:02Z",
                         "2026-07-15T00:00:03Z"])
    ri.submit(conn, "tags", "OLD|1", "oldest")
    ri.submit(conn, "brief", "MID|1", "middle")
    ri.submit(conn, "tags", "NEW|1", "newest")
    all_items = ri.pending(conn)
    assert [i["title"] for i in all_items] == ["oldest", "middle", "newest"]
    tags_only = ri.pending(conn, kind="tags")
    assert [i["title"] for i in tags_only] == ["oldest", "newest"]


# --- corpus ----------------------------------------------------------------------

def test_corpus_only_decided_items(conn):
    a = ri.submit(conn, "tags", "A|1", "a")
    b = ri.submit(conn, "tags", "B|1", "b")
    ri.submit(conn, "tags", "C|1", "c")  # stays pending
    ri.decide(conn, a["id"], "approved")
    ri.decide(conn, b["id"], "rejected")
    rows = ri.corpus(conn)
    assert {r["status"] for r in rows} == {"approved", "rejected"}
    assert len(rows) == 2
    assert all(r["decided_at"] for r in rows)


def test_corpus_kind_and_since_filters(conn, monkeypatch):
    a = ri.submit(conn, "tags", "A|1", "early tag")
    b = ri.submit(conn, "brief", "B|1", "late brief")
    _clock(monkeypatch, ["2026-07-10T10:00:00Z", "2026-07-20T09:00:00Z"])
    ri.decide(conn, a["id"], "approved")
    ri.decide(conn, b["id"], "rejected")
    assert [r["title"] for r in ri.corpus(conn)] == ["early tag", "late brief"]
    assert [r["title"] for r in ri.corpus(conn, kind="brief")] == ["late brief"]
    # since: strictly-later decision only
    assert [r["title"] for r in ri.corpus(conn, since="2026-07-15")] == ["late brief"]
    # date-only 'since' includes a same-day decision (ISO prefix compare)
    assert [r["title"] for r in ri.corpus(conn, since="2026-07-20")] == ["late brief"]
    assert ri.corpus(conn, since="2026-07-21") == []


# --- agreement stats ----------------------------------------------------------------

def test_agreement_stats_math(conn):
    ids = [ri.submit(conn, "tags", f"S{i}|t", f"t{i}")["id"] for i in range(4)]
    ri.decide(conn, ids[0], "approved")
    ri.decide(conn, ids[1], "approved")
    ri.decide(conn, ids[2], "rejected")          # ids[3] stays pending
    ri.submit(conn, "alert-ack", "X|1", "undecided family")
    st = ri.agreement_stats(conn)
    assert st["tags"] == {"pending": 1, "approved": 2, "rejected": 1,
                          "decided": 3,
                          "approve_rate": pytest.approx(2 / 3)}
    assert st["alert-ack"]["decided"] == 0
    assert st["alert-ack"]["approve_rate"] is None  # no div-by-zero


def test_agreement_stats_kind_filter_and_unknown(conn):
    a = ri.submit(conn, "tags", "A|1", "a")
    ri.decide(conn, a["id"], "approved")
    ri.submit(conn, "brief", "B|1", "b")
    only = ri.agreement_stats(conn, kind="tags")
    assert set(only) == {"tags"}
    assert only["tags"]["approve_rate"] == 1.0
    assert ri.agreement_stats(conn, kind="does-not-exist") == {}


# --- grace + schema ------------------------------------------------------------------

def test_empty_db_grace(conn):
    assert ri.pending(conn) == []
    assert ri.corpus(conn) == []
    assert ri.corpus(conn, kind="tags", since="2026-01-01") == []
    assert ri.agreement_stats(conn) == {}
    assert ri.agreement_stats(conn, kind="tags") == {}


def test_ensure_schema_idempotent(conn):
    ri.ensure_schema(conn)
    ri.ensure_schema(conn)  # third call overall — must not raise
    res = ri.submit(conn, "tags", "A|1", "still works")
    assert res["created"] is True
