"""Contracts for the brief publisher — L6's last mile (S159, D134 §4-E).

The load-bearing claim of the whole L6 layer is "ONLY an approved brief publishes".
That is a claim about a machine, so it is tested like one:

  1. the gate       — pending/rejected/undecided briefs NEVER reach the render;
  2. exactly-once   — a second --publish is a no-op (the shared kind-generic apply-log);
  3. the signature  — the human's decided_at travels onto the published row;
  4. retraction     — a published brief can leave the render, and the record survives;
  5. the destination— briefs land in OUR table, never in the vendor-ToS news feed;
  6. the band       — the board renders approved briefs, and renders NOTHING otherwise.

Hermetic: temp DBs only, no network, no LLM.
"""
from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.automation import brief_publisher as BP   # noqa: E402
from src.automation import review_inbox            # noqa: E402

_PAYLOAD = {
    "text": "TCS reported (Q period ending 2026-06-30); first tradeable day 2026-07-14.\n"
            "AI-drafted, human-reviewed · generated 2026-07-15 · context, not a signal.",
    "label": "AI-drafted, human-reviewed",
    "numbers": {"sue": {"value": 1.2, "source": "/dash/results-reactions"}},
    "links": {"board": "/dash/results-reactions", "stock": "/dash/stock?sym=TCS"},
}


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    review_inbox.ensure_schema(c)
    yield c
    c.close()


def _brief(c, ref="results:TCS:2026-06-30", payload=None):
    r = review_inbox.submit(c, "brief", ref, f"Results brief — {ref}", payload or _PAYLOAD)
    c.commit()
    return r["id"]


# ── 1. the gate ───────────────────────────────────────────────────────────────────────
def test_a_pending_brief_never_publishes(conn):
    _brief(conn)
    assert BP.publish_approved(conn)["published"] == 0
    assert BP.published(conn) == []


def test_a_rejected_brief_never_publishes_but_is_logged_handled(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "rejected", "not useful")
    conn.commit()
    out = BP.publish_approved(conn)
    assert out["published"] == 0 and out["skipped_rejected"] == 1
    assert BP.published(conn) == []
    # logged as handled -> never re-scanned
    assert BP.publish_approved(conn)["skipped_rejected"] == 0


def test_an_approved_brief_publishes(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved", "reads fine")
    conn.commit()
    assert BP.publish_approved(conn)["published"] == 1
    live = BP.published(conn)
    assert len(live) == 1 and live[0]["sym"] == "TCS"
    assert "AI-drafted, human-reviewed" in live[0]["text"]


def test_dry_run_reports_without_writing(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    assert BP.publish_approved(conn, dry_run=True)["published"] == 1
    assert BP.published(conn) == []          # nothing written
    assert BP.publish_approved(conn)["published"] == 1   # still publishable after


def test_an_approved_but_empty_brief_is_skipped_not_rendered_blank(conn):
    i = _brief(conn, ref="results:WIPRO:2026-06-30", payload={"text": "   "})
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    out = BP.publish_approved(conn)
    assert out["published"] == 0 and out["skipped_unparseable"] == 1
    assert BP.published(conn) == []


# ── 2. exactly-once ───────────────────────────────────────────────────────────────────
def test_publishing_is_exactly_once_across_runs_and_connections(tmp_path):
    db = tmp_path / "h.db"
    c1 = sqlite3.connect(db)
    review_inbox.ensure_schema(c1)
    i = _brief(c1)
    review_inbox.decide(c1, i, "approved")
    c1.commit()
    assert BP.publish_approved(c1)["published"] == 1
    c1.close()
    c2 = sqlite3.connect(db)                      # a fresh connection sees it (committed)
    assert len(BP.published(c2)) == 1
    assert BP.publish_approved(c2)["published"] == 0, "second run must publish nothing"
    assert len(BP.published(c2)) == 1
    c2.close()


def test_it_uses_the_shared_kind_generic_apply_log_not_a_second_ledger(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    BP.publish_approved(conn)
    rows = conn.execute("SELECT kind, action FROM inbox_apply_log WHERE item_id=?",
                        (i,)).fetchall()
    assert rows == [("brief", "published")]


def test_the_tags_adapter_and_the_publisher_never_see_each_others_rows(conn):
    from src.automation import inbox_adapters as IA
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    BP.publish_approved(conn)
    # tags_apply scans kind='tags' only -> a published brief is invisible to it
    out = IA.tags_apply(conn)
    assert out["applied_approved"] == 0 and out["applied_rejected"] == 0


# ── 3. the human signature ────────────────────────────────────────────────────────────
def test_the_humans_decision_timestamp_travels_onto_the_published_row(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved", "signed off")
    conn.commit()
    BP.publish_approved(conn)
    row = BP.published(conn)[0]
    decided = conn.execute("SELECT decided_at FROM review_items WHERE id=?", (i,)).fetchone()[0]
    assert row["approved_at"] == decided and decided


# ── 4. retraction ─────────────────────────────────────────────────────────────────────
def test_retraction_removes_from_render_but_keeps_the_record(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    BP.publish_approved(conn)
    assert BP.unpublish(conn, i, note="wrong period")["retracted"] is True
    assert BP.published(conn) == []
    kept = BP.published(conn, include_retracted=True)
    assert len(kept) == 1 and kept[0]["retracted_at"]
    assert BP.stats(conn) == {"live": 0, "retracted": 1}


def test_retracting_twice_is_a_no_op_and_an_unknown_id_raises(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    BP.publish_approved(conn)
    BP.unpublish(conn, i)
    assert BP.unpublish(conn, i)["already"] is True
    with pytest.raises(ValueError):
        BP.unpublish(conn, 424242)


def test_a_retracted_brief_is_not_silently_republished(conn):
    i = _brief(conn)
    review_inbox.decide(conn, i, "approved")
    conn.commit()
    BP.publish_approved(conn)
    BP.unpublish(conn, i, note="retracted")
    assert BP.publish_approved(conn)["published"] == 0   # apply-log still holds it
    assert BP.published(conn) == []


# ── 5. the destination (Guardrail #8) ─────────────────────────────────────────────────
def test_briefs_never_write_to_the_vendor_tos_news_feed():
    """The wire renders `sent_news` (feed `news_feed` = UNCLASSIFIED vendor-ToS, held out
    of feed_manifest.FEEDS pending plan §7.7). House AI text must never land there."""
    src = open(os.path.join(_ROOT, "src", "automation", "brief_publisher.py"),
               encoding="utf-8").read()
    body = src.split('"""', 2)[2]        # skip the module docstring (it explains the ban)
    for forbidden in ("sent_news", "news_feed", "news_symbol_tags"):
        assert forbidden not in body, (
            f"brief_publisher writes/reads {forbidden!r} — briefs publish to our OWN "
            "published_briefs table, never into the vendor-ToS news feed (Guardrail #8)")


def test_the_news_feed_is_still_unclassified_so_the_ban_still_has_a_reason():
    """If this fails, Ramana decided §7.7 — re-read the destination rationale before
    assuming it still holds (the ban's premise, not the ban, is what expires)."""
    from src.automation import feed_manifest as FM
    assert "news_feed" not in FM.FEEDS, "news_feed entered FEEDS — revisit brief_publisher's §7.7 note"


# ── 6. the band on the board ──────────────────────────────────────────────────────────
def test_the_board_renders_nothing_when_no_brief_is_published():
    from src.web import results_reactions as RR
    assert RR._render_briefs([]) == "", "an empty band must not render an empty shell"


def test_the_board_band_shows_the_ai_label_and_links_the_symbol():
    from src.web import results_reactions as RR
    html = RR._render_briefs([("TCS", "Results brief — TCS", "line one\nline two",
                               "AI-drafted, human-reviewed", "2026-07-15 10:00:00Z")])
    assert "AI-drafted, human-reviewed" in html
    assert '/dash/stock?sym=TCS' in html            # sym, never symbol
    assert "line one" in html and "line two" in html
    assert "approved 2026-07-15" in html


def test_the_band_read_is_defensive_when_the_table_is_absent(tmp_path, monkeypatch):
    from src.web import results_reactions as RR
    monkeypatch.setattr(RR, "HERMES_DB", str(tmp_path / "nope.db"))
    assert RR._published_briefs(3) == []            # never raises -> the board still renders
