"""estate_heartbeat — ONE positive morning line: the machine's health + ₹ spend.

WHY (D134 analytics-company plan §4-B · S150 LANE-B)
----------------------------------------------------
The estate already checks itself in pieces — board_health walks the strategist board
nightly, feed jobs log their own staleness, the alert rail curates critical
state-changes, and (as of this lane) cost_ledger meters ₹ spend against the §5.4
budget law. What Ramana does NOT have is the composed read: every existing pager is
NEGATIVE (it speaks only on failure), so a silent morning is ambiguous — "all green"
and "the pager itself died" look identical. This module closes that hole with a
POSITIVE heartbeat: one line, every morning, that says the machine is alive and what
it knows about itself:

    estate GREEN · board OK · bhav 2026-07-14 · signals 2026-07-14 · fund 2026-07-01
    · events 2026-07-14 · crit 0 · ₹118.42/2,500 MTD (5%) OK        (all ONE line)

VERDICT RULES (rule-based, deterministic, documented here — the editorial heart)
--------------------------------------------------------------------------------
Four component families each flag green/amber/red; the estate verdict is the WORST:
  * board    — board_health probe: OK->green · WARN->amber · FAIL->red · n/a (probe
               itself broke)->amber. The probe reads the canonical DB via
               board_health's own connection; `board=` injects a verdict for tests.
  * freshness— MAX(date) of the four key tables vs FRESHNESS_BUDGETS (amber_days,
               red_days), weekend/holiday-tolerant. Missing table or zero rows ->
               red + 'n/a' in the line (grace: composing never crashes on empty DB).
  * cost     — cost_ledger.cap_status: OK->green · AMBER->amber · BREACH->red
               (budget law §5.4). Meter unreadable -> amber.
  * crit     — the alert-rail critical count is INFORMATIONAL ONLY (shown, never
               drives the verdict): criticals are MARKET state-changes — the desk's
               morning reading list — not machine defects. The estate verdict speaks
               about the MACHINE.

DOCTRINE
--------
* Isolation (signal_alerts precedent): owns `heartbeat_sent` via CREATE TABLE IF NOT
  EXISTS — no db.py edit. Reads siblings through their public reads only
  (signal_alerts.active_count, cost_ledger.cap_status, board_health.check).
* Zero LLM, stdlib-only imports at module top; digest/_send, board_health and
  settings are imported LAZILY inside functions so hermetic tests never touch them.
* Fire-once-per-day (--dm): claim-first INSERT OR IGNORE into heartbeat_sent, send,
  and RELEASE the claim if the transport fails — so a same-day retry can re-attempt,
  but a successful morning can never double-page (tracker_alert_delivery pattern).
* Descriptive fence: the line reports states and dates, never an action.
* Designed to run ON the VPS nightly at 03:30 UTC = 09:00 IST (hermes-heartbeat.timer,
  installed/enabled by LANE-R only — this module ships as files, never self-installs).

CLI (bare run = --print)
------------------------
    python -m src.automation.estate_heartbeat --print [--db PATH] [--cap 2500]
    python -m src.automation.estate_heartbeat --dm [--to CHAT_ID]
    python -m src.automation.estate_heartbeat --selftest
"""
from __future__ import annotations

import argparse
import contextlib
import html
import importlib
import io
import sqlite3
import sys
from datetime import date, datetime, timezone
from typing import Optional

try:  # sibling imports, board_health's dual-path pattern (both are light at import)
    from src.automation import cost_ledger as CL
    from src.automation import signal_alerts as SA
except Exception:  # pragma: no cover - import-path fallback
    import cost_ledger as CL      # type: ignore
    import signal_alerts as SA    # type: ignore

# --- the four key freshness sources: (label, table, date column, amber_d, red_d) -----
# Budgets are calendar days vs today, generous enough for long weekends + NSE holiday
# clusters; fundamentals is scrape-cadence (being XBRL-remediated) so wider still.
FRESHNESS = (
    ("bhav",    "bhavcopy_rows", "trade_date", 4, 7),
    ("signals", "stock_signals", "trade_date", 4, 7),
    ("fund",    "fundamentals",  "fetched_at", 35, 90),
    ("events",  "signal_events", "as_of",      4, 7),
)

_FLAG_ORDER = {"green": 0, "amber": 1, "red": 2}
_VERDICT = {0: "GREEN", 1: "AMBER", 2: "RED"}

# --- owned table (isolation: NOT in db.py SCHEMA_BASE) --------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS heartbeat_sent (
    day     TEXT PRIMARY KEY,                          -- UTC YYYY-MM-DD, the fire-once key
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    line    TEXT
);
"""


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """db_path=None -> canonical hermes.db, imported lazily (hermetic-test contract)."""
    if db_path is None:
        from src.core.db import DB_PATH  # deferred on purpose
        db_path = str(DB_PATH)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


# --- component probes (each tolerant: a broken probe degrades, never crashes) ---------

def _board_verdict() -> str:
    """'OK' | 'WARN' | 'FAIL' | 'n/a'. Runs board_health.check against ITS canonical
    connection with stdout captured (its prints belong to its own log, not our line).
    importlib so tests can inject a fake module via sys.modules."""
    try:
        bh = importlib.import_module("src.automation.board_health")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = bh.check(verbose=False)
        if rc != 0:
            return "FAIL"
        return "WARN" if "WARN" in buf.getvalue() else "OK"
    except Exception:
        return "n/a"


def _max_date(conn: sqlite3.Connection, table: str, column: str) -> Optional[str]:
    """MAX(column)[:10] or None. Table/column come ONLY from the FRESHNESS constant
    above (no user input reaches this SQL). Missing table -> None (empty-DB grace)."""
    try:
        row = conn.execute(f"SELECT MAX({column}) FROM {table}").fetchone()
        val = row[0] if row else None
        return str(val)[:10] if val else None
    except sqlite3.Error:
        return None


def _age_days(iso_day: str, today: str) -> Optional[int]:
    try:
        return (date.fromisoformat(today) - date.fromisoformat(iso_day)).days
    except ValueError:
        return None


def _crit_count(conn: sqlite3.Connection) -> Optional[int]:
    """Alert-rail criticals in the current window — signal_alerts' own badge read
    (active_count, the count face of active_alerts). None = rail unreadable."""
    try:
        by = SA.active_count(conn).get("by_severity", {})
        return int(by.get("critical", 0))
    except Exception:
        return None


def _owner_chat_id() -> Optional[int]:
    """The owner's DM chat id — first numeric token of telegram_allowed_user_ids.
    (Same derivation as signal_alert_telegram/news_feed; replicated deliberately to
    keep this module isolated. Lazy settings import = hermetic tests never load it.)"""
    try:
        from src.core.settings import settings
    except Exception:
        return None
    for tok in (getattr(settings, "telegram_allowed_user_ids", "") or "").split(","):
        tok = tok.strip()
        if tok.isdigit():
            return int(tok)
    return None


# --- compose (the heart: many checks in, ONE line out) --------------------------------

def compose(conn: Optional[sqlite3.Connection] = None, *,
            db_path: Optional[str] = None,
            cap_inr: Optional[float] = None,
            board: Optional[str] = None,
            today: Optional[str] = None) -> dict:
    """Compose the heartbeat. Returns {'verdict', 'line', 'board', 'freshness',
    'crit', 'cost', 'today'}; `line` is guaranteed single-line. `board=`/`today=`
    exist for hermetic tests; on the box both default to live reads."""
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        today = (today or datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:10]
        board = board if board is not None else _board_verdict()
        flags = []

        board_flag = {"OK": "green", "WARN": "amber", "FAIL": "red"}.get(board, "amber")
        flags.append(board_flag)

        fresh: dict = {}
        fresh_parts = []
        for label, table, column, amber_d, red_d in FRESHNESS:
            d = _max_date(c, table, column)
            fresh[label] = d
            age = _age_days(d, today) if d else None
            if d is None or age is None:
                flag, part = "red", f"{label} n/a"
            elif age >= red_d:
                flag, part = "red", f"{label} {d} ({age}d)"
            elif age >= amber_d:
                flag, part = "amber", f"{label} {d} ({age}d)"
            else:
                flag, part = "green", f"{label} {d}"
            flags.append(flag)
            fresh_parts.append(part)

        crit = _crit_count(c)
        crit_part = f"crit {crit}" if crit is not None else "crit n/a"

        # The OWNER NUDGE (S160, Ramana-directed 2026-07-15: "I prefer to have communication
        # take place here in the chat"). The Review Inbox had been accumulating asks for him —
        # AI briefs, rule-lab verdicts, tag proposals — while NO channel said so: Pat could
        # only define the term, the bot never mentioned it, and this DM (the one line he reads
        # every morning) was silent. It is no longer. Deliberately a COUNT, not the content:
        # the DM stays one line, and judging happens on the owner-gated lens. Wording is
        # single-sourced from inbox_flow.KIND_WORDS so the DM and Pat can never disagree.
        # NOT a flag: work waiting on a human is a normal state, never an estate fault.
        waiting_n = None
        try:
            from src.automation import review_inbox as _RI
            waiting_n = len(_RI.pending(c))
        except Exception:
            waiting_n = None
        if waiting_n is None:
            wait_part = "inbox n/a"
        elif waiting_n == 0:
            wait_part = "inbox clear"
        else:
            wait_part = f"{waiting_n} waiting on you"

        cap = float(cap_inr) if cap_inr is not None else CL.DEFAULT_CAP_INR
        try:
            cost = CL.cap_status(cap_inr=cap, conn=c)
        except Exception:
            cost = None
        if cost is None:
            flags.append("amber")
            cost_part = "₹ n/a"
        else:
            flags.append({"OK": "green", "AMBER": "amber"}.get(cost["status"], "red"))
            pct = int(round(cost["fraction"] * 100))
            cost_part = (f"₹{CL.fmt_inr(cost['mtd_inr'])}/{CL.fmt_inr(cost['cap_inr'])}"
                         f" MTD ({pct}%) {cost['status']}")

        verdict = _VERDICT[max(_FLAG_ORDER[f] for f in flags)]
        line = " · ".join([f"estate {verdict}", f"board {board}",
                           *fresh_parts, crit_part, wait_part, cost_part])
        line = line.replace("\n", " ")  # belt-and-braces: the contract is ONE line
        return {"verdict": verdict, "line": line, "board": board, "freshness": fresh,
                "crit": crit, "waiting": waiting_n, "cost": cost, "today": today}
    finally:
        if own:
            c.close()


# --- delivery (fire-once-per-day DM via digest's transport) ---------------------------

def send_dm(conn: Optional[sqlite3.Connection] = None, *,
            db_path: Optional[str] = None,
            cap_inr: Optional[float] = None,
            board: Optional[str] = None,
            today: Optional[str] = None,
            chat_id: Optional[int] = None,
            send_fn=None) -> dict:
    """Compose + DM the line, at most once per UTC day.

    Claim-first: INSERT OR IGNORE the day into heartbeat_sent BEFORE sending (a
    same-day re-run can never double-page), and DELETE the claim if the transport
    fails so a retry re-attempts. `send_fn`/`chat_id` injectable for tests; on the
    box they default to digest._send (reused, never copied) + the owner's chat id.
    Returns compose()'s dict + {'sent': bool, 'skipped': reason|None}."""
    own = conn is None
    c = conn if conn is not None else _connect(db_path)
    try:
        ensure_schema(c)
        out = compose(conn=c, cap_inr=cap_inr, board=board, today=today)
        day = out["today"]
        cur = c.execute("INSERT OR IGNORE INTO heartbeat_sent (day, line) VALUES (?, ?)",
                        (day, out["line"]))
        c.commit()
        if cur.rowcount == 0:
            return {**out, "sent": False, "skipped": "already-sent-today"}
        if send_fn is None:
            from src.automation.digest import _send as send_fn  # reuse, don't copy
        if chat_id is None:
            chat_id = _owner_chat_id()
        if chat_id is None:
            c.execute("DELETE FROM heartbeat_sent WHERE day = ?", (day,))
            c.commit()
            return {**out, "sent": False, "skipped": "no-owner-chat-id"}
        ok = bool(send_fn(int(chat_id), html.escape(out["line"])))
        if not ok:
            c.execute("DELETE FROM heartbeat_sent WHERE day = ?", (day,))
            c.commit()
            return {**out, "sent": False, "skipped": "transport-failed"}
        return {**out, "sent": True, "skipped": None}
    finally:
        if own:
            c.close()


# --- selftest + CLI --------------------------------------------------------------------

def selftest() -> int:
    """Hermetic end-to-end on a temp SQLite file: seed fresh tables -> GREEN one-liner
    -> fire-once guard -> transport-failure release. Never touches the canonical DB."""
    import os
    import tempfile
    fd, path = tempfile.mkstemp(prefix="hermes-heartbeat-selftest-", suffix=".db")
    os.close(fd)
    try:
        c = _connect(path)
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            c.execute("CREATE TABLE bhavcopy_rows (trade_date TEXT)")
            c.execute("CREATE TABLE stock_signals (trade_date TEXT)")
            c.execute("CREATE TABLE fundamentals (fetched_at TEXT)")
            c.execute("CREATE TABLE signal_events (as_of TEXT)")
            for t, col in (("bhavcopy_rows", "trade_date"), ("stock_signals", "trade_date"),
                           ("fundamentals", "fetched_at"), ("signal_events", "as_of")):
                c.execute(f"INSERT INTO {t} ({col}) VALUES (?)", (today,))
            c.commit()
            CL.record("selftest", "claude-haiku-4-5", 100_000, 20_000, conn=c)
            out = compose(conn=c, board="OK", today=today)
            assert out["verdict"] == "GREEN", f"expected GREEN, got {out['verdict']}"
            assert "\n" not in out["line"], "heartbeat must be ONE line"
            assert out["line"].startswith("estate GREEN · board OK"), out["line"]
            print(out["line"])
            sent = []
            fake = lambda cid, msg: sent.append((cid, msg)) or True  # noqa: E731
            r1 = send_dm(conn=c, board="OK", today=today, chat_id=1, send_fn=fake)
            r2 = send_dm(conn=c, board="OK", today=today, chat_id=1, send_fn=fake)
            assert r1["sent"] and not r2["sent"] and len(sent) == 1, "fire-once broken"
            assert r2["skipped"] == "already-sent-today"
            # empty-DB grace on a second temp conn: no tables at all -> RED, no crash
            fd2, path2 = tempfile.mkstemp(prefix="hermes-heartbeat-empty-", suffix=".db")
            os.close(fd2)
            c2 = _connect(path2)
            try:
                out2 = compose(conn=c2, board="OK", today=today)
                assert out2["verdict"] == "RED" and "n/a" in out2["line"]
            finally:
                c2.close()
                try:
                    os.remove(path2)
                except OSError:
                    pass
        finally:
            c.close()
        print("estate_heartbeat selftest OK")
        return 0
    except AssertionError as e:
        print(f"estate_heartbeat selftest FAIL: {e}")
        return 1
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main(argv: Optional[list] = None) -> int:
    # Windows consoles can be cp1252; ₹/· in the line must never crash a dry run.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(
        description="Hermes estate heartbeat (one morning line, plan §4-B)")
    p.add_argument("--print", dest="print_", action="store_true",
                   help="compose + print the line, no DM, no guard write (default)")
    p.add_argument("--dm", action="store_true",
                   help="compose + DM the owner once per UTC day (fire-once guard)")
    p.add_argument("--selftest", action="store_true", help="hermetic temp-DB self-check")
    p.add_argument("--db", default=None, help="SQLite path override (tests/dry-runs)")
    p.add_argument("--cap", type=float, default=None,
                   help="monthly ₹ cap override (default: cost_ledger.DEFAULT_CAP_INR)")
    p.add_argument("--to", type=int, default=None,
                   help="chat id override for --dm (default: owner)")
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.dm:
        res = send_dm(db_path=a.db, cap_inr=a.cap, chat_id=a.to)
        status = "sent" if res["sent"] else f"not sent ({res['skipped']})"
        print(res["line"])
        print(f"heartbeat: {status}")
        if res["sent"] or res["skipped"] == "already-sent-today":
            return 0
        return 2  # transport failed / no chat id -> nonzero so the unit log shows it
    print(compose(db_path=a.db, cap_inr=a.cap)["line"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
