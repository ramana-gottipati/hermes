"""/inbox — the queue answers in the bot, on demand (S161, Ramana-directed).

Ramana asked for this by name after S160: *"do the telegram /inbox command too"*. S160 put
the queue in Pat and in the morning DM; the bot — the surface he actually types into — still
could not say what was waiting. This closes the third channel.

Contracts:
  1. auth      — the queue is owner-private; a non-allowed user gets NOTHING (not even a hint);
  2. reports   — the real queue, with the same words Pat and the DM use (single-sourced);
  3. read-only — /inbox can never decide an item;
  4. filter    — /inbox briefs narrows by kind, tolerant of plurals;
  5. grace     — an empty queue says so; a DB failure apologises rather than crashing.

Hermetic: a fake Update/Message, an in-memory DB, no network, no Telegram.
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from contextlib import contextmanager

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

TB = pytest.importorskip("src.assistant.telegram_bot",
                         reason="python-telegram-bot not installed in this venv")
from src.automation import review_inbox            # noqa: E402


class _Msg:
    def __init__(self):
        self.sent: list = []

    async def reply_text(self, text, **kw):
        self.sent.append(text)


class _Update:
    def __init__(self, uid=42):
        self.effective_user = type("U", (), {"id": uid})()
        self.message = _Msg()


class _Ctx:
    def __init__(self, args=None):
        self.args = args or []


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """A real on-disk queue wired into the bot's get_conn + an authorized owner.

    NOT :memory:, and not a shared connection. on_inbox reads the queue inside
    loop.run_in_executor(None, ...) — a WORKER thread — whereas the fixture runs
    on the test thread. A single sqlite connection cannot cross threads (the
    check_same_thread guard raises ProgrammingError), and waiting() swallows that
    into an empty queue — so a shared-:memory:-connection fixture silently seeds
    nothing the handler can see (the queue reads back as "nothing is waiting on
    you" and every content assertion fails). Bind get_conn to a FILE PATH and
    open a fresh connection per call — exactly what production get_conn does — so
    each thread gets its own connection to the same database (the S163-b "capture
    the path string, not the connection object" lesson)."""
    db_path = str(tmp_path / "review_inbox.db")

    @contextmanager
    def _fake_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(TB, "get_conn", _fake_get_conn)
    monkeypatch.setattr(TB, "_is_authorized", lambda uid: uid == 42)

    # The test-thread handle used by _fill() and the direct-query assertions.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    review_inbox.ensure_schema(conn)
    conn.commit()
    yield conn
    conn.close()


def _fill(c):
    for kind, ref, title in (
            ("brief", "results:TCS:2026-06-30", "Results brief — TCS Q 2026-06-30"),
            ("brief", "results:INFY:2026-06-30", "Results brief — INFY Q 2026-06-30"),
            ("rule_verdict", "abc123", "Rule-lab: NEW-BENCHMARK [fundable] — SELECT largecap"),
            ("tags", "RELIANCE|Defence", "Tag proposal — RELIANCE · Defence")):
        review_inbox.submit(c, kind, ref, title, {})
    c.commit()


def _run(update, ctx):
    asyncio.run(TB.on_inbox(update, ctx))
    return "\n".join(update.message.sent)


# ── 1. auth ───────────────────────────────────────────────────────────────────────────
def test_a_stranger_gets_nothing_at_all(db):
    """The queue is owner-private: an unauthorized id must not even learn it exists."""
    _fill(db)
    u = _Update(uid=999)
    out = _run(u, _Ctx())
    assert out == "" and u.message.sent == []


# ── 2. it reports the real queue, in the shared words ─────────────────────────────────
def test_it_reports_the_queue_with_the_same_words_pat_uses(db):
    from src.pat.inbox_flow import waiting, summary_phrase
    _fill(db)
    out = _run(_Update(), _Ctx())
    from src.pat.inbox_flow import format_telegram_reply
    expected = format_telegram_reply(waiting(db))    # single-sourced -> byte-identical
    assert out == expected, "the /inbox command must render through the shared formatter"
    assert "4 waiting on you" in out
    assert "Results brief — TCS Q 2026-06-30" in out
    assert "srv1704897.hstgr.cloud/dash/inbox" in out   # the LIVE public link, not raw IP:8000


def test_no_internal_slug_reaches_the_chat(db):
    _fill(db)
    out = _run(_Update(), _Ctx())
    assert "rule_verdict" not in out
    assert "a rule-lab verdict" in out or "rule-lab verdict" in out


# ── 3. read-only ──────────────────────────────────────────────────────────────────────
def test_the_command_can_never_decide_an_item(db):
    _fill(db)
    _run(_Update(), _Ctx())
    undecided = db.execute(
        "SELECT count(*) FROM review_items WHERE status!='pending'").fetchone()[0]
    assert undecided == 0, "/inbox must report, never judge"


# ── 4. the kind filter ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("arg", ["briefs", "brief"])
def test_the_filter_narrows_by_kind_and_tolerates_plurals(db, arg):
    _fill(db)
    out = _run(_Update(), _Ctx([arg]))
    assert "Results brief — TCS" in out and "Results brief — INFY" in out
    assert "NEW-BENCHMARK" not in out               # the rule verdict is filtered out


def test_a_filter_with_no_hits_says_so_and_still_gives_the_total(db):
    _fill(db)
    out = _run(_Update(), _Ctx(["rebalance"]))
    assert "Nothing waiting under" in out and "4 waiting on you" in out.lower()


def test_an_unknown_filter_word_does_not_crash(db):
    _fill(db)
    out = _run(_Update(), _Ctx(["banana"]))
    assert "Nothing waiting under" in out


# ── 5. grace ──────────────────────────────────────────────────────────────────────────
def test_an_empty_queue_says_so_plainly(db):
    out = _run(_Update(), _Ctx())
    assert "nothing is waiting on you" in out.lower()


def test_a_db_failure_apologises_instead_of_crashing(db, monkeypatch):
    @contextmanager
    def _boom():
        raise sqlite3.OperationalError("database is locked")
        yield

    monkeypatch.setattr(TB, "get_conn", _boom)
    out = _run(_Update(), _Ctx())
    assert "Couldn't read the review queue" in out


# ── registration ──────────────────────────────────────────────────────────────────────
def test_the_link_is_the_live_public_domain_not_the_dead_raw_ip(db):
    """S77b closed :8000 to the outside — a raw-IP link would be dead on the phone, in the
    one place the command sends Ramana to go approve something."""
    _fill(db)
    out = _run(_Update(), _Ctx())
    assert "srv1704897.hstgr.cloud" in out
    assert ":8000" not in out and "187.127.173.149" not in out


def test_the_command_is_registered_on_the_app():
    src = open(os.path.join(_ROOT, "src", "assistant", "telegram_bot.py"),
               encoding="utf-8").read()
    assert 'CommandHandler("inbox", on_inbox)' in src


# ── 6. the link must actually be reachable (S160-b) ────────────────────────────────────
# digest.PUBLIC_BASE_URL resolves to the raw IP:8000 the S77b perimeter closure took OFF
# the public internet (ufw allows only 22/80/443/9443) — confirmed dead live (a bare curl
# to it from outside hangs with no response). The one link this command gives Ramana to go
# act on the queue must not be the one thing on the page that doesn't work on his phone.
def test_the_approve_link_uses_the_real_public_domain_not_the_dead_raw_ip(db):
    _fill(db)
    out = _run(_Update(), _Ctx())
    assert "hstgr.cloud/dash/inbox" in out
    assert "187.127.173.149" not in out, "a raw-IP link is dead through the closed perimeter"
