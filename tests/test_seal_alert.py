"""Regression gate for the autonomous seal-integrity alert path (S202).

These two helpers are the ENTIRE reason a broken pre-registration / frozen-family seal
reaches Ramana at all:
  * data_quality._page_on_seal_break  — the nightly Telegram page (a seal WARN never fails
    the service, so the systemd OnFailure can't cover it),
  * estate_heartbeat._seal_status     — the daily heartbeat line (positive confirmation +
    the stale-check that makes 'no page' != 'all clear').
A silent refactor that stopped either would recreate the exact 'silence looks like
all-clear' failure the lane was built to kill. Lock the behavior. Hermetic: in-memory
sqlite + mocked subprocess — no network, no real DB, no real Telegram send.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation import data_quality as D  # noqa: E402
from src.automation import estate_heartbeat as H  # noqa: E402


def _conn_with(run_at: str, severity):
    """In-memory data_quality_runs with one snapshot. severity=None → a report that carries
    NO prereg.seal_integrity check (the pre-deploy row shape)."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE data_quality_runs (run_at TEXT, status TEXT, "
              "n_critical INT, n_warn INT, report_json TEXT)")
    checks = [] if severity is None else [
        {"check": "prereg.seal_integrity", "severity": severity, "message": "exit_lab --verify exit 1"}]
    c.execute("INSERT INTO data_quality_runs VALUES (?,?,?,?,?)",
              (run_at, "warn", 0, 1, json.dumps({"checks": checks})))
    c.commit()
    return c


# ── _seal_status: the heartbeat line (green=ok · amber=broken · red=stale) ─────────────
def test_seal_status_ok_is_green():
    assert H._seal_status(_conn_with("2026-07-20 06:35", "ok"), "2026-07-20") == ("seals ok", "green")


def test_seal_status_broken_is_amber():
    token, flag = H._seal_status(_conn_with("2026-07-20 06:35", "warn"), "2026-07-20")
    assert flag == "amber" and token.startswith("seals BROKEN")


def test_seal_status_stale_nightly_is_red():
    # snapshot >= 3 days old = the nightly stopped persisting → the silence≠success signal
    token, flag = H._seal_status(_conn_with("2026-07-20 06:35", "ok"), "2026-07-25")
    assert flag == "red" and token.startswith("seals stale")


def test_seal_status_absent_is_soft_green():
    # no seal check in the snapshot (pre-deploy) → n/a, never a fault
    assert H._seal_status(_conn_with("2026-07-20 06:35", None), "2026-07-20") == ("seals n/a", "green")
    # no row at all → still soft-green (bootstrap; other checks cover a dead box)
    empty = sqlite3.connect(":memory:")
    empty.execute("CREATE TABLE data_quality_runs (run_at TEXT, status TEXT, n_critical INT, "
                  "n_warn INT, report_json TEXT)")
    assert H._seal_status(empty, "2026-07-20") == ("seals n/a", "green")


# ── _page_on_seal_break: the Telegram page (fires ONLY on a not-ok seal) ────────────────
def _rep(severity: str) -> dict:
    return {"checks": [{"check": "prereg.seal_integrity", "severity": severity,
                        "message": "exit_lab --verify exit 1"}]}


def test_page_not_sent_when_seal_ok():
    with mock.patch.object(D.subprocess, "run") as m, mock.patch.object(D.Path, "exists", return_value=True):
        D._page_on_seal_break(_rep("ok"))
    assert not m.called


def test_page_sent_via_text_mode_when_seal_broken():
    with mock.patch.object(D.subprocess, "run") as m, mock.patch.object(D.Path, "exists", return_value=True):
        D._page_on_seal_break(_rep("warn"))
    assert m.called
    argv = m.call_args[0][0]
    assert argv[0] == "/bin/bash"
    assert argv[1].endswith("alert-telegram.sh")
    assert argv[2] == "--text"
    assert "SEAL INTEGRITY" in argv[3]


def test_page_never_raises_on_pager_failure():
    # a pager/subprocess failure must NOT abort the nightly (exit-0 contract) — must return, not raise
    with mock.patch.object(D.subprocess, "run", side_effect=OSError("boom")), \
         mock.patch.object(D.Path, "exists", return_value=True):
        D._page_on_seal_break(_rep("warn"))


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
