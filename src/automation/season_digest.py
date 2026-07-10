"""Season-ops digest — the daily operate routine as one Telegram DM (S84x).

Automates the results-season morning readout (the ~15-min manual routine): unit health,
pager fires, tape freshness, war-room fresh reporters + the filing→surface MTTR number,
XBRL gate verdicts, surveillance state, DQ battery, today's results calendar, backups.

Design rules:
  * ₹0 and deterministic — pure SQL + log tails + systemd queries; NO LLM (guardrail #3).
  * ALWAYS delivers, even all-green — a silent digest is indistinguishable from a dead
    one (the monitors-never-page audit theme); the daily DM is its own liveness signal.
  * Read-only everywhere (mode=ro URIs; no write txns — the D82c lesson); every section
    is failure-isolated so one broken source degrades to a "n/a" line, never a crash.
  * Recipient = the operator (first TELEGRAM_ALLOWED_USER_IDS — same as the AUD-26 pager),
    NOT patearn_destinations (this is ops, not market content).
  * The unit's own 95-onfailure drop-in pages if the digest itself fails.

CLI:
  python -m src.automation.season_digest --print      # dry-run to stdout (no Telegram)
  python -m src.automation.season_digest --send       # the timer's entry (02:45 UTC daily)
  python -m src.automation.season_digest --selftest   # offline formatting checks
"""
from __future__ import annotations

import ast
import html
import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import requests

from src.core.settings import settings

log = logging.getLogger("hermes.season_digest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

HERMES_DB = "/opt/hermes/data/hermes.db"
RESEARCH_DB = "/opt/hermes/data/research.db"
XBRL_LOG = "/var/log/hermes-fundamentals-xbrl.log"
BACKUP_DIR = "/opt/hermes/backups/db"
MTTR_SEED_CUTOFF = "2026-07-07 02:00"


def _ro(path):
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error:
        return None


def _one(con, sql, params=()):
    try:
        r = con.execute(sql, params).fetchone()
        return r if r is None else tuple(r)
    except sqlite3.Error:
        return None


def _ist_now():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)


# ── sections (each returns ONE short line; never raises) ─────────────────────

def sec_units() -> str:
    try:
        out = subprocess.run(["systemctl", "list-units", "--failed", "--no-legend", "hermes-*"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        n = len([l for l in out.splitlines() if l.strip()])
        pager = subprocess.run(["journalctl", "--since", "-24 hours", "--no-pager",
                                "-g", "hermes-alert: paged"],
                               capture_output=True, text=True, timeout=20).stdout
        fires = len([l for l in pager.splitlines() if "paged" in l])
        mark = "✅" if (n == 0 and fires == 0) else "⚠"
        return f"{mark} units: {n} failed · pager: {fires} fire(s) 24h"
    except Exception as e:                                     # noqa: BLE001
        return f"· units: n/a ({type(e).__name__})"


def sec_tape() -> str:
    con = _ro(HERMES_DB)
    if not con:
        return "· tape: hermes.db n/a"
    r = _one(con, "SELECT MAX(trade_date) FROM bhavcopy_rows")
    con.close()
    mx = (r or [None])[0] or "?"
    # weekday-lag vs the last completed IST session (the AUD-29 anchor)
    ist = _ist_now()
    anchor = ist.date()
    if ist.weekday() >= 5 or ist.hour < 20:
        anchor -= timedelta(days=1)
    while anchor.weekday() >= 5:
        anchor -= timedelta(days=1)
    lag = 0
    try:
        from datetime import date as _d
        cur = _d.fromisoformat(str(mx)[:10]) + timedelta(days=1)
        while cur <= anchor:
            if cur.weekday() < 5:
                lag += 1
            cur += timedelta(days=1)
    except ValueError:
        lag = -1
    mark = "✅" if lag == 0 else "⚠"
    return f"{mark} tape: {mx} (lag {lag})"


def sec_board() -> str:
    con = _ro(RESEARCH_DB)
    if not con:
        return "· board: research.db n/a"
    week_ago = (_ist_now().date() - timedelta(days=7)).isoformat()
    fresh = _one(con, "SELECT COUNT(*), COALESCE(SUM(sue_high*deliv_high),0) "
                      "FROM results_reactions WHERE t0 >= ?", (week_ago,)) or (0, 0)
    names = []
    try:
        names = [r[0] for r in con.execute(
            "SELECT sym FROM results_reactions WHERE t0 >= ? "
            "ORDER BY t0 DESC, deliv_x DESC LIMIT 5", (week_ago,))]
    except sqlite3.Error:
        pass
    lags = []
    try:
        for t0, seen in con.execute(
                "SELECT t0, first_seen_utc FROM reaction_mttr WHERE first_seen_utc > ?",
                (MTTR_SEED_CUTOFF,)):
            from datetime import date as _d
            lags.append((_d.fromisoformat(str(seen)[:10]) - _d.fromisoformat(str(t0)[:10])).days)
    except (sqlite3.Error, ValueError):
        pass
    con.close()
    mttr = (f"MTTR med {sorted(lags)[len(lags)//2]}d (n={len(lags)})" if lags
            else "MTTR: collecting")
    chip = (" · " + " ".join(names)) if names else ""
    return f"📊 board 7d: {fresh[0]} fresh · {fresh[1]} deliv-confirmed · {mttr}{chip}"


def parse_xbrl_tail(text: str) -> dict | None:
    """Last 'ingest done: {...}' dict + the same night's continuity-FAIL count."""
    lines = text.splitlines()
    done_i = None
    for i in range(len(lines) - 1, -1, -1):
        if "ingest done:" in lines[i]:
            done_i = i
            break
    if done_i is None:
        return None
    try:
        stats = ast.literal_eval(lines[done_i].split("ingest done:", 1)[1].strip())
    except (ValueError, SyntaxError):
        return None
    start_i = 0
    for i in range(done_i, -1, -1):
        if "ingest window" in lines[i]:
            start_i = i
            break
    fails = sum(1 for l in lines[start_i:done_i] if "continuity gate FAIL" in l)
    stats["_gate_fail_lines"] = fails
    return stats


def sec_xbrl() -> str:
    try:
        with open(XBRL_LOG, encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-80:]
    except OSError:
        return "· xbrl: log n/a"
    s = parse_xbrl_tail("".join(tail))
    if not s:
        return "· xbrl: no ingest-done line"
    mark = "⚠" if (s.get("aborted_throttled") or s.get("fetch_fail", 0) > 3) else "✅"
    return (f"{mark} xbrl: {s.get('if_filings', 0)} integrated · rows {s.get('rows', 0)} · "
            f"gate defer {s.get('gate_deferred', 0)} / fail-syms {s.get('gate_fail_syms', 0)} "
            f"({s.get('_gate_fail_lines', 0)} lines) · banks {s.get('bank_flagged', 0)}")


def sec_surveillance() -> str:
    con = _ro(HERMES_DB)
    if not con:
        return "· surveillance: n/a"
    r = _one(con, "SELECT MAX(as_of) FROM surveillance_flags")
    mx = (r or [None])[0]
    if not mx:
        con.close()
        return "· surveillance: no data yet"
    counts = {}
    try:
        counts = dict(con.execute(
            "SELECT framework, COUNT(*) FROM surveillance_flags WHERE as_of=? GROUP BY 1", (mx,)))
    except sqlite3.Error:
        pass
    b = _one(con, "SELECT COUNT(*) FROM price_band_events WHERE as_of="
                  "(SELECT MAX(as_of) FROM price_band_events)") or (0,)
    con.close()
    return (f"🛰 asm {counts.get('ASM-LT', 0)}/{counts.get('ASM-ST', 0)} · "
            f"gsm {counts.get('GSM', 0)} · band Δ {b[0]} ({mx})")


def sec_dq() -> str:
    con = _ro(HERMES_DB)
    if not con:
        return "· dq: n/a"
    row = _one(con, "SELECT run_at, status, n_critical, n_warn, report_json "
                    "FROM data_quality_runs ORDER BY run_at DESC LIMIT 1")
    con.close()
    if not row:
        return "· dq: no runs"
    run_at, status, nc, nw, rj = row
    warns = []
    try:
        for c in json.loads(rj).get("checks", []):
            if c.get("severity") in ("warn", "critical"):
                warns.append(c.get("check", "?"))
    except (ValueError, TypeError, AttributeError):
        pass
    mark = "✅" if not nc else "🔴"
    extra = (" — " + ", ".join(warns[:2])) if warns else ""
    return f"{mark} dq: crit {nc} warn {nw}{extra} ({str(run_at)[5:16]})"


def sec_calendar() -> str:
    con = _ro(HERMES_DB)
    if not con:
        return "· calendar: n/a"
    today = _ist_now().date().isoformat()
    tomo = (_ist_now().date() + timedelta(days=1)).isoformat()
    out = []
    for lbl, d in (("today", today), ("tomorrow", tomo)):
        try:
            syms = [r[0] for r in con.execute(
                "SELECT symbol FROM board_meetings WHERE is_results=1 AND meeting_date=? "
                "ORDER BY symbol LIMIT 30", (d,))]
        except sqlite3.Error:
            syms = []
        chip = (" " + " ".join(syms[:5]) + (f" +{len(syms)-5}" if len(syms) > 5 else "")) \
            if syms else ""
        out.append(f"{lbl} {len(syms)}{chip}")
    con.close()
    return "📅 results: " + " · ".join(out)


def sec_backup() -> str:
    try:
        files = sorted((os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)),
                       key=os.path.getmtime)
        if not files:
            return "⚠ backup: none found"
        age_h = (datetime.now().timestamp() - os.path.getmtime(files[-1])) / 3600.0
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True,
                              timeout=10).stdout.splitlines()
        use = disk[-1].split()[4] if len(disk) > 1 else "?"
        mark = "✅" if age_h < 30 else "⚠"
        return f"{mark} backup {age_h:.0f}h ago · disk {use}"
    except Exception as e:                                     # noqa: BLE001
        return f"· backup: n/a ({type(e).__name__})"


def build_digest() -> str:
    ist = _ist_now()
    head = f"🌅 <b>Patearn season ops</b> — {ist.strftime('%a %d %b %H:%M')} IST"
    body = [head]
    for fn in (sec_units, sec_tape, sec_board, sec_xbrl, sec_surveillance,
               sec_dq, sec_calendar, sec_backup):
        try:
            body.append(html.escape(fn(), quote=False)
                        .replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>"))
        except Exception as e:                                 # noqa: BLE001
            body.append(f"· {fn.__name__}: crashed ({type(e).__name__})")
    return "\n".join(body)


def send(text: str) -> bool:
    token = settings.telegram_bot_token
    ids = (settings.telegram_allowed_user_ids or "").replace(" ", "")
    chat = ids.split(",")[0] if ids else ""
    if not token or not chat:
        log.error("digest: missing bot token / allowed user id")
        return False
    for attempt in (1, 2):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": chat, "text": text, "parse_mode": "HTML"},
                              timeout=15)
            if r.status_code == 200:
                log.info("digest sent to %s", chat)
                return True
            log.warning("digest send HTTP %s (attempt %d): %s",
                        r.status_code, attempt, r.text[:120])
        except requests.RequestException as e:
            log.warning("digest send failed (attempt %d): %s", attempt, e)
    return False


def selftest() -> None:
    s = parse_xbrl_tail(
        "2026-07-09 16:30 INFO ingest window 2026-07-02..2026-07-09: 0 filings\n"
        "2026-07-09 16:30 WARNING continuity gate FAIL AAA: x\n"
        "2026-07-09 16:31 INFO ingest done: {'filings': 0, 'rows': 10, 'if_filings': 7, "
        "'gate_fail_syms': 3, 'gate_deferred': 0, 'bank_flagged': 0, "
        "'aborted_throttled': False, 'fetch_fail': 0}\n")
    assert s and s["if_filings"] == 7 and s["_gate_fail_lines"] == 1
    assert parse_xbrl_tail("no dict here") is None
    d = build_digest()                       # degrades on the laptop stub, must not raise
    assert d.startswith("🌅") and len(d.splitlines()) == 9
    print("SEASON_DIGEST selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--print" in sys.argv:
        print(build_digest())
    elif "--send" in sys.argv:
        ok = send(build_digest())
        sys.exit(0 if ok else 1)
    else:
        print(__doc__)
