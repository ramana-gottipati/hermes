"""Hermetic contracts for cost_ledger + estate_heartbeat (D134 plan §4-B/§5.4, S150 LANE-B).

Every test runs against a per-test temp SQLite file (tmp_path) with injected
board/today/send_fn — NO canonical hermes.db, NO settings import, NO network.
These are the contracts LANE-R integrates against:

  cost_ledger:     record arithmetic + prefix/unknown-model rating + month scoping
                   + the §5.4 cap bands (OK / AMBER at 80% / BREACH at 100%).
  estate_heartbeat: ONE-line composition, verdict = worst component, freshness
                   budgets, crit count informational, empty-DB grace, fire-once DM
                   guard + transport-failure release.
"""
from __future__ import annotations

import sqlite3
import sys
import types
from datetime import date, timedelta, timezone, datetime

import pytest

from src.automation import cost_ledger as CL
from src.automation import estate_heartbeat as HB

TODAY = "2026-07-15"  # fixed "today" injected everywhere -> deterministic ages


@pytest.fixture()
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "hermetic.db"))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _seed_fresh(conn, day=TODAY, fund_day=None):
    """Minimal key tables with one fresh row each (only the columns compose reads)."""
    conn.execute("CREATE TABLE IF NOT EXISTS bhavcopy_rows (trade_date TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS stock_signals (trade_date TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS fundamentals (fetched_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS signal_events (as_of TEXT)")
    conn.execute("INSERT INTO bhavcopy_rows VALUES (?)", (day,))
    conn.execute("INSERT INTO stock_signals VALUES (?)", (day,))
    conn.execute("INSERT INTO fundamentals VALUES (?)", (fund_day or day,))
    conn.execute("INSERT INTO signal_events VALUES (?)", (day,))
    conn.commit()


def _days_ago(n, anchor=TODAY):
    return (date.fromisoformat(anchor) - timedelta(days=n)).isoformat()


# ====================================================================== cost_ledger ==

def test_record_computes_inr_from_rates(conn):
    inr = CL.record("job_a", "claude-haiku-4-5", 1_000_000, 1_000_000, note="t", conn=conn)
    ri, ro = CL.RATES_INR_PER_MTOK["claude-haiku-4-5"]
    assert inr == pytest.approx(ri + ro)
    row = conn.execute("SELECT * FROM cost_ledger").fetchone()
    assert row["job"] == "job_a" and row["note"] == "t"
    assert row["inr_estimate"] == pytest.approx(ri + ro)


def test_record_prefix_matches_dated_model_id(conn):
    inr = CL.record("job_a", "claude-haiku-4-5-20251001", 1_000_000, 0, conn=conn)
    assert inr == pytest.approx(CL.RATES_INR_PER_MTOK["claude-haiku-4-5"][0])


def test_record_unknown_model_charged_conservative_default(conn):
    inr = CL.record("job_a", "mystery-llm-9", 1_000_000, 0, conn=conn)
    assert inr == pytest.approx(CL.RATES_INR_PER_MTOK["_default"][0])
    # the guard property: an unknown model can never be metered CHEAPER than known ones
    assert inr >= CL.RATES_INR_PER_MTOK["gemini-2.5-flash-lite"][0]


def test_record_rejects_negative_tokens_and_blank_job(conn):
    with pytest.raises(ValueError):
        CL.record("job_a", "claude-haiku-4-5", -1, 0, conn=conn)
    with pytest.raises(ValueError):
        CL.record("", "claude-haiku-4-5", 1, 0, conn=conn)


def test_month_to_date_scopes_to_month(conn):
    now_month = datetime.now(timezone.utc).strftime("%Y-%m")
    a = CL.record("j", "claude-haiku-4-5", 1_000_000, 0, conn=conn)
    CL.record("j", "claude-haiku-4-5", 9_000_000, 0, ts="2020-01-15 00:00:00", conn=conn)
    assert CL.month_to_date(conn=conn) == pytest.approx(a)
    assert CL.month_to_date(now_month, conn=conn) == pytest.approx(a)
    assert CL.month_to_date("2020-01", conn=conn) == pytest.approx(9 * a)


def test_cap_status_ok_band(conn):
    CL.record("j", "claude-haiku-4-5", 1_000_000, 0, conn=conn)  # Rs 88
    st = CL.cap_status(conn=conn)  # default cap 2500
    assert st["status"] == "OK"
    assert st["mtd_inr"] == pytest.approx(88.0)
    assert st["cap_inr"] == 2500.0


def test_cap_status_amber_band_starts_at_80pct(conn):
    CL.record("j", "x", 0, 0, inr_override=80.0, conn=conn)
    assert CL.cap_status(cap_inr=100.0, conn=conn)["status"] == "AMBER"   # exactly 80%
    assert CL.cap_status(cap_inr=101.0, conn=conn)["status"] == "OK"      # just under


def test_cap_status_breach_at_and_over_cap(conn):
    CL.record("j", "x", 0, 0, inr_override=100.0, conn=conn)
    assert CL.cap_status(cap_inr=100.0, conn=conn)["status"] == "BREACH"  # exactly 100%
    assert CL.cap_status(cap_inr=99.0, conn=conn)["status"] == "BREACH"
    with pytest.raises(ValueError):
        CL.cap_status(cap_inr=0, conn=conn)


def test_default_cap_is_plan_5_4_value():
    assert CL.DEFAULT_CAP_INR == 2500.0
    assert CL.AMBER_AT == pytest.approx(0.80)


def test_rates_table_covers_repo_models():
    # keys must track the ids the repo configures (settings.py + enrich.py); if a
    # model id changes there, this test forces the RATES row to follow.
    for key in ("claude-haiku-4-5", "claude-sonnet-4-6",
                "gemini-2.5-flash-lite", "gemini-2.5-flash", "_default"):
        assert key in CL.RATES_INR_PER_MTOK


# ================================================================= estate_heartbeat ==

def test_compose_one_line_green_when_all_fresh(conn):
    _seed_fresh(conn)
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out["verdict"] == "GREEN"
    line = out["line"]
    assert "\n" not in line, "the heartbeat contract is ONE line"
    assert line.startswith("estate GREEN · board OK")
    for token in ("bhav 2026-07-15", "signals 2026-07-15", "fund 2026-07-15",
                  "events 2026-07-15", "crit 0", "MTD", "OK"):
        assert token in line, f"missing {token!r} in {line!r}"


def test_compose_amber_on_cost_amber(conn):
    _seed_fresh(conn)
    CL.record("j", "x", 0, 0, inr_override=2100.0, conn=conn)  # 84% of 2500
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out["verdict"] == "AMBER"
    assert "AMBER" in out["line"] and "(84%)" in out["line"]


def test_compose_red_on_cost_breach(conn):
    _seed_fresh(conn)
    CL.record("j", "x", 0, 0, inr_override=2600.0, conn=conn)
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out["verdict"] == "RED"
    assert "BREACH" in out["line"]


def test_compose_freshness_bands_amber_then_red(conn):
    _seed_fresh(conn, day=_days_ago(5))  # bhav/signals/events 5d old -> amber band (4..6)
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out["verdict"] == "AMBER"
    assert "bhav 2026-07-10 (5d)" in out["line"]

    conn.execute("INSERT INTO bhavcopy_rows VALUES (?)", (_days_ago(7),))
    conn.execute("DELETE FROM bhavcopy_rows WHERE trade_date = ?", (_days_ago(5),))
    conn.commit()
    out2 = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out2["verdict"] == "RED"  # 7d = red threshold for bhav


def test_compose_red_on_board_fail_and_amber_on_warn(conn):
    _seed_fresh(conn)
    assert HB.compose(conn=conn, board="FAIL", today=TODAY)["verdict"] == "RED"
    assert HB.compose(conn=conn, board="WARN", today=TODAY)["verdict"] == "AMBER"
    assert HB.compose(conn=conn, board="n/a", today=TODAY)["verdict"] == "AMBER"


def test_compose_empty_db_grace(conn):
    # brand-new DB, zero tables: must compose (never crash), report n/a, flag RED
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert out["verdict"] == "RED"
    assert "bhav n/a" in out["line"] and "crit 0" in out["line"]
    assert "\n" not in out["line"]


def test_compose_counts_critical_alerts_informational_only(conn):
    _seed_fresh(conn)
    from src.automation import signal_alerts as SA
    SA.ensure_schema(conn)
    conn.execute(
        "INSERT INTO signal_alert_state (symbol, lens, event_type, severity, valence,"
        " magnitude, as_of) VALUES ('TCS', 'rs', 'phase_flip', 'critical', 'risk', 1.0, ?)",
        (TODAY,))
    conn.commit()
    out = HB.compose(conn=conn, board="OK", today=TODAY)
    assert "crit 1" in out["line"]
    # doctrine: criticals are MARKET reading, not machine defects -> verdict stays GREEN
    assert out["verdict"] == "GREEN"


def test_board_verdict_probe_mapping(monkeypatch):
    # hermetic: inject a fake board_health module -> no db.py/settings import ever
    def probe(rc, out_text=""):
        fake = types.ModuleType("src.automation.board_health")

        def check(verbose=True):
            if out_text:
                print(out_text)
            return rc

        fake.check = check
        monkeypatch.setitem(sys.modules, "src.automation.board_health", fake)
        return HB._board_verdict()

    assert probe(0) == "OK"
    assert probe(0, "board-health WARN (not fatal): x") == "WARN"
    assert probe(2, "BOARD-HEALTH FAIL: y") == "FAIL"

    broken = types.ModuleType("src.automation.board_health")  # no .check at all
    monkeypatch.setitem(sys.modules, "src.automation.board_health", broken)
    assert HB._board_verdict() == "n/a"


def test_send_dm_fires_once_per_day(conn):
    _seed_fresh(conn)
    sent = []

    def fake(chat_id, msg):
        sent.append((chat_id, msg))
        return True

    r1 = HB.send_dm(conn=conn, board="OK", today=TODAY, chat_id=42, send_fn=fake)
    r2 = HB.send_dm(conn=conn, board="OK", today=TODAY, chat_id=42, send_fn=fake)
    assert r1["sent"] is True and r1["skipped"] is None
    assert r2["sent"] is False and r2["skipped"] == "already-sent-today"
    assert len(sent) == 1 and sent[0][0] == 42
    assert "estate GREEN" in sent[0][1]
    day_rows = conn.execute("SELECT COUNT(*) FROM heartbeat_sent").fetchone()[0]
    assert day_rows == 1


def test_send_dm_transport_failure_releases_guard(conn):
    _seed_fresh(conn)
    r1 = HB.send_dm(conn=conn, board="OK", today=TODAY, chat_id=42,
                    send_fn=lambda cid, msg: False)
    assert r1["sent"] is False and r1["skipped"] == "transport-failed"
    assert conn.execute("SELECT COUNT(*) FROM heartbeat_sent").fetchone()[0] == 0
    # a retry the same day now goes through
    r2 = HB.send_dm(conn=conn, board="OK", today=TODAY, chat_id=42,
                    send_fn=lambda cid, msg: True)
    assert r2["sent"] is True


def test_send_dm_next_day_fires_again(conn):
    _seed_fresh(conn)
    ok = lambda cid, msg: True  # noqa: E731
    r1 = HB.send_dm(conn=conn, board="OK", today=TODAY, chat_id=1, send_fn=ok)
    tomorrow = _days_ago(-1)
    r2 = HB.send_dm(conn=conn, board="OK", today=tomorrow, chat_id=1, send_fn=ok)
    assert r1["sent"] is True and r2["sent"] is True
    assert conn.execute("SELECT COUNT(*) FROM heartbeat_sent").fetchone()[0] == 2


def test_send_dm_without_chat_id_releases_guard(conn, monkeypatch):
    _seed_fresh(conn)
    monkeypatch.setattr(HB, "_owner_chat_id", lambda: None)
    r = HB.send_dm(conn=conn, board="OK", today=TODAY, send_fn=lambda c, m: True)
    assert r["sent"] is False and r["skipped"] == "no-owner-chat-id"
    assert conn.execute("SELECT COUNT(*) FROM heartbeat_sent").fetchone()[0] == 0
