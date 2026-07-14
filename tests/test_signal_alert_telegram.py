"""Owner-DM pager (signal_alert_telegram) regressions — hermetic, no network.

Pins the contract that makes the pager safe: CRITICAL-only by default, fire-once (an alert is
DM'd at most once), acknowledged alerts are never paged, dry-run/no-token/no-owner degrade
without sending, and the message carries the descriptive fence (never an action verb).
`digest._send` is monkeypatched to a recorder — nothing leaves the process.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.automation import signal_alerts as sa
from src.automation import signal_alert_telegram as sat


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    sa.ensure_schema(c)
    sat.ensure_schema(c)
    yield c
    c.close()


def _seed(c, *, symbol, lens, etype, as_of, severity, valence="risk",
          from_state=None, to_state=None, note="", ack=None):
    c.execute(
        "INSERT INTO signal_alert_state "
        "(symbol, lens, event_type, direction, from_state, to_state, magnitude, severity, "
        " valence, as_of, note, acknowledged_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol, lens, etype, None, from_state, to_state, 1.0, severity, valence, as_of, note, ack))
    c.commit()
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


@pytest.fixture()
def recorder(monkeypatch):
    """Replace the Telegram transport with an in-memory recorder + a live token."""
    sent = []
    monkeypatch.setattr("src.automation.digest._send", lambda chat_id, msg: sent.append((chat_id, msg)) or True)
    monkeypatch.setattr(sat.settings, "telegram_bot_token", "test-token", raising=False)
    return sent


# --- selection --------------------------------------------------------------

def test_default_selects_only_critical(conn):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14",
          severity="critical", to_state="STRONG_DISTRIB")
    _seed(conn, symbol="BBB", lens="oi", etype="oi_flip", as_of="2026-07-14", severity="high")
    got = sat._undelivered(conn, as_of="2026-07-14", min_severity="critical")
    assert [r["symbol"] for r in got] == ["AAA"]


def test_high_severity_includes_high(conn):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14", severity="critical")
    _seed(conn, symbol="BBB", lens="oi", etype="oi_flip", as_of="2026-07-14", severity="high")
    got = {r["symbol"] for r in sat._undelivered(conn, as_of="2026-07-14", min_severity="high")}
    assert got == {"AAA", "BBB"}


def test_acknowledged_alert_is_never_paged(conn):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14",
          severity="critical", ack="2026-07-14 10:00:00")
    assert sat._undelivered(conn, as_of="2026-07-14", min_severity="critical") == []


# --- delivery: send once, record, never re-page -----------------------------

def test_push_sends_and_records(conn, recorder):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14",
          severity="critical", from_state="DISTRIB", to_state="STRONG_DISTRIB")
    res = sat.push(conn, as_of="2026-07-14", chat_id=42)
    assert res["sent"] == 1 and len(recorder) == 1
    chat, msg = recorder[0]
    assert chat == 42 and "AAA" in msg
    # delivery ledger recorded the id
    assert conn.execute("SELECT COUNT(*) FROM signal_alert_delivery").fetchone()[0] == 1


def test_fire_once_second_push_sends_nothing(conn, recorder):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14", severity="critical")
    first = sat.push(conn, as_of="2026-07-14", chat_id=42)
    second = sat.push(conn, as_of="2026-07-14", chat_id=42)
    assert first["sent"] == 1 and second["sent"] == 0
    assert len(recorder) == 1  # only the first send happened


def test_new_alert_after_delivery_still_pages(conn, recorder):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14", severity="critical")
    sat.push(conn, as_of="2026-07-14", chat_id=42)
    _seed(conn, symbol="CCC", lens="cci", etype="cci_drop", as_of="2026-07-14", severity="critical")
    res = sat.push(conn, as_of="2026-07-14", chat_id=42)
    assert res["sent"] == 1 and recorder[-1][1].count("CCC") == 1


# --- safe degradation -------------------------------------------------------

def test_dry_run_sends_nothing_but_previews(conn, recorder):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14", severity="critical")
    res = sat.push(conn, as_of="2026-07-14", chat_id=42, dry_run=True)
    assert res["sent"] == 0 and res["reason"] == "dry-run" and "AAA" in res["preview"]
    assert len(recorder) == 0
    assert conn.execute("SELECT COUNT(*) FROM signal_alert_delivery").fetchone()[0] == 0


def test_no_owner_chat_id_degrades(conn, monkeypatch):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14", severity="critical")
    monkeypatch.setattr(sat.settings, "telegram_allowed_user_ids", "", raising=False)
    res = sat.push(conn, as_of="2026-07-14")   # no chat_id override, no configured owner
    assert res["sent"] == 0 and res["reason"] == "no owner chat id"


def test_nothing_new_is_clean(conn, recorder):
    assert sat.push(conn, as_of="2026-07-14", chat_id=42) == {"selected": 0, "sent": 0, "reason": "nothing new"}


# --- honesty fence ----------------------------------------------------------

def test_message_carries_fence_and_no_action_verbs(conn):
    _seed(conn, symbol="AAA", lens="mep", etype="phase_flip", as_of="2026-07-14",
          severity="critical", from_state="DISTRIB", to_state="STRONG_DISTRIB", note="effort up")
    msg = sat.format_message(sat._undelivered(conn, as_of="2026-07-14", min_severity="critical"),
                             as_of="2026-07-14")
    low = msg.lower()
    assert "context, not a buy/sell/act" in low          # the fence is present
    assert "/dash/attention" in msg                       # dismiss link
    # no imperative action verb as an instruction (buy/sell/trim/add appear only inside the fence clause)
    assert "buy now" not in low and "sell now" not in low and "trim " not in low
