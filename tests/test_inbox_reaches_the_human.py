"""The queue must REACH the human — in the chat, and in the daily DM (S160, Ramana-directed).

Ramana, 2026-07-15: *"I'm surprised that you're still providing it under /inbox. I'm not sure
what it is. I prefer to have communication take place here in the chat; if something isn't
available, it should be linked to the full application itself."*

The audit that followed found the real defect: the Review Inbox was silently accumulating
asks for him while NO channel reported them. Pat had `inbox` in PAT_EXPLAIN — it could define
the words "review inbox" but could not say what sat in it. The heartbeat DM (the one line he
reads daily) never mentioned it. It WAS registered in the Trust nav, so every existing gate
passed — "registered" is not "reaches you", and no test encoded that difference. This file
does, so the regression can't come back quietly:

  1. the chat  — Pat ANSWERS "what's waiting on me" with the real queue (not a definition);
  2. the DM    — the daily line carries the count, and stays one line;
  3. read-only — neither channel can decide anything (judgment is the owner's, on the lens);
  4. plain     — no internal slug ('rule_verdict') ever reaches a human;
  5. neutral   — work waiting on a human is a NORMAL state, never an estate fault.

Hermetic: in-memory DBs, no network, no LLM.
"""
from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import inbox_flow as IF            # noqa: E402
from src.automation import review_inbox         # noqa: E402


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    review_inbox.ensure_schema(c)
    yield c
    c.close()


def _fill(c):
    for kind, ref, title in (
            ("brief", "results:TCS:2026-06-30", "Results brief — TCS Q 2026-06-30"),
            ("brief", "results:INFY:2026-06-30", "Results brief — INFY Q 2026-06-30"),
            ("rule_verdict", "abc123", "Rule-lab: NEW-BENCHMARK [fundable] — SELECT largecap"),
            ("tags", "RELIANCE|Defence", "Tag proposal — RELIANCE · Defence")):
        review_inbox.submit(c, kind, ref, title, {})
    c.commit()


# ── 1. the chat answers ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("q", [
    "what's waiting on me?",
    "anything needing my approval",
    "what needs my sign-off",
    "how many items are pending",
    "is there anything for me to review",
    "what's in my inbox",
])
def test_pat_routes_the_waiting_asks_to_the_inbox_flow(q):
    from src.pat import engine as E
    assert (E.route(q) or {}).get("flow") == "inbox", f"Pat must answer {q!r} with the queue"


def test_a_locational_ask_still_goes_to_navigate_not_the_queue():
    """"where is the review inbox" is a page-find. The queue flow declines it on its own,
    so re-ordering the pre-pass chain can never make it steal a navigate."""
    from src.pat import engine as E
    assert IF.parse_inbox("where is the review inbox") is None
    assert (E.route("where is the review inbox") or {}).get("flow") == "navigate"


def test_pat_reports_the_real_queue_not_a_definition(conn):
    import src.pat.web as PW
    _fill(conn)
    html = PW._inbox_flow(conn)
    assert "4 waiting on you" in html
    assert "AI-drafted event briefs" in html          # real content
    assert "/dash/inbox" in html                      # the full surface is one click away
    assert "results:TCS" in html or "TCS" in html


def test_the_empty_queue_says_so_plainly_and_still_links(conn):
    import src.pat.web as PW
    html = PW._inbox_flow(conn)
    assert "Nothing is waiting on you" in html and "/dash/inbox" in html


def test_the_coverage_gate_now_records_inbox_as_DATA_not_EXPLAIN():
    """The upgrade that closes the hole: EXPLAIN meant 'Pat can define the term'. For a
    queue of things waiting on a human, that is the wrong tier."""
    sys.path.insert(0, os.path.join(_ROOT, "tests"))
    import test_pat_coverage as T
    assert T._classify("inbox") == "DATA"
    assert "inbox" not in T.PAT_EXPLAIN
    assert T.PAT_DATA["inbox"] in T.VALID_FLOWS      # and the flow is really wired


# ── 2. the daily DM carries it ────────────────────────────────────────────────────────
def test_the_daily_dm_line_reports_the_count(conn):
    from src.automation import estate_heartbeat as H
    _fill(conn)
    out = H.compose(conn, board="OK", today="2026-07-15")
    assert "4 waiting on you" in out["line"]
    assert out["waiting"] == 4


def test_the_dm_says_clear_when_nothing_waits(conn):
    from src.automation import estate_heartbeat as H
    out = H.compose(conn, board="OK", today="2026-07-15")
    assert "inbox clear" in out["line"] and out["waiting"] == 0


def test_the_dm_is_still_exactly_one_line(conn):
    from src.automation import estate_heartbeat as H
    _fill(conn)
    assert "\n" not in H.compose(conn, board="OK", today="2026-07-15")["line"]


def test_waiting_work_is_a_normal_state_and_never_flags_the_estate(conn):
    """A queue is not a fault. The nudge must not move the estate verdict either way."""
    from src.automation import estate_heartbeat as H
    before = H.compose(conn, board="OK", today="2026-07-15")
    _fill(conn)
    after = H.compose(conn, board="OK", today="2026-07-15")
    assert before["verdict"] == after["verdict"]


def test_the_dm_survives_an_inbox_that_is_absent(tmp_path):
    """The heartbeat must never crash because the L5 layer is missing (grace doctrine)."""
    from src.automation import estate_heartbeat as H
    c = sqlite3.connect(":memory:")              # no review_items table at all
    out = H.compose(c, board="OK", today="2026-07-15")
    assert out["line"] and "\n" not in out["line"]
    c.close()


# ── 3. read-only ──────────────────────────────────────────────────────────────────────
def test_neither_channel_can_decide_anything(conn):
    """Pat REPORTS; judging is a deliberate act on the owner-gated lens. Source-scanned so
    a future edit can't quietly hand the chat a decide() call."""
    _fill(conn)
    import src.pat.web as PW
    PW._inbox_flow(conn)
    from src.automation import estate_heartbeat as H
    H.compose(conn, board="OK", today="2026-07-15")
    rows = conn.execute("SELECT count(*) FROM review_items WHERE status!='pending'").fetchone()[0]
    assert rows == 0, "reporting the queue must never decide an item"
    src = open(os.path.join(_ROOT, "src", "pat", "inbox_flow.py"), encoding="utf-8").read()
    logic = src.split('"""', 2)[2].split("def _selftest")[0]   # the selftest legitimately decides
    for banned in ("decide(", "INSERT", "UPDATE", "DELETE", "commit("):
        assert banned not in logic, f"inbox_flow's logic must stay read-only ({banned})"


# ── 4. plain english ──────────────────────────────────────────────────────────────────
def test_no_internal_slug_ever_reaches_a_human(conn):
    """Scoped to what THIS flow writes: the summary sentence + kind labels. An item's
    TITLE is its producer's contract (S158-b's lens gate covers per-kind display copy);
    the realistic titles in _fill() are what producers actually emit."""
    import src.pat.web as PW
    _fill(conn)
    phrase = IF.summary_phrase(IF.waiting(conn))
    assert "rule_verdict" not in phrase and "a rule-lab verdict" in phrase
    assert "tags" not in phrase and "tag proposal" in phrase
    html = PW._inbox_flow(conn)
    assert "rule_verdict" not in html, "no producer slug should reach the rendered answer"


def test_an_unknown_kind_is_still_counted_rather_than_dropped(conn):
    """A new producer must never make the count silently wrong just because nobody has
    written it a label yet."""
    review_inbox.submit(conn, "anomaly", "x1", "some anomaly", {})
    review_inbox.submit(conn, "brandnew", "x2", "a kind nobody labelled", {})
    conn.commit()
    w = IF.waiting(conn)
    assert w["total"] == 2
    assert "1 × brandnew" in IF.summary_phrase(w)


def test_the_dm_and_the_chat_cannot_describe_the_queue_differently(conn):
    """Both channels count the same pending set — single-sourced, so they can't drift."""
    from src.automation import estate_heartbeat as H
    _fill(conn)
    assert H.compose(conn, board="OK", today="2026-07-15")["waiting"] == IF.waiting(conn)["total"]
