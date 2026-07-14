"""signal_alert_telegram.py — private owner-DM pager for the highest-severity bus alerts.

Why this exists
---------------
The signal-event bus has four *surfaces* (the `signal_events.py` header names them: /v1 API ·
Attention Queue · since-you-last-looked · the **alert rail**). The alert rail (S123) built the
in-app surface — build → dismiss → filter at `/dash/attention`. This module is the missing
**delivery**: it DMs the owner the newest CRITICAL alerts so the bus actually *reaches* him,
exactly the way `digest` (season war-room), `board-health`, and `results-reactions` already
page. It is the carry-forward's named alert-rail follow-on and serves the S127 directive
(Telegram delivery of the desk's highest-severity state-changes).

Scope + honesty boundary
------------------------
- **PRIVATE OWNER DM ONLY.** The recipient is the owner's own chat id
  (`telegram_allowed_user_ids[0]`), the same self-pager channel as the existing digests. This
  is NOT the public, approval-gated channel publish (that is a separate, later program, S-F) —
  do not conflate them.
- **Descriptive fence.** Each line states the state CHANGE + before→after, never
  "buy / sell / act" — the same D106 honesty posture as the rail it mirrors.

Isolation (§0.8) + safety
-------------------------
- Brand-new module. Reuses `signal_alerts.active_alerts()` (the selection substrate) and
  `digest._send()` (the transport). It owns its `signal_alert_delivery` table via
  ``CREATE TABLE IF NOT EXISTS`` — **no `db.py` edit**.
- **Fire-once.** An alert id is DM'd at most once (the delivery ledger is the dedup), so
  re-runs / a windowed re-scan never re-page. Mirrors the `tracker_alert_delivery` pattern.
- **Ships dormant.** The nightly auto-push (piggybacked on `signal_events --detect`) only
  fires when ``HERMES_ALERT_DM=1`` is set on the box, so deploying this code sends nothing
  until it is deliberately enabled. The ``--push`` CLI always works (for a manual run / test).
- **CRITICAL-only by default.** High-severity alerts stay on the rail (viewable); only the
  scarce `critical` state-changes earn a DM, so the pager is high-signal, never noise.

CLI
---
    python -m src.automation.signal_alert_telegram --push [--asof YYYY-MM-DD] \
        [--min-severity critical|high] [--dry-run] [--to CHAT_ID]
"""
from __future__ import annotations

import argparse
import html
import logging
from typing import Optional

from src.automation import signal_alerts as SA
from src.core.settings import settings

log = logging.getLogger("hermes.signal_alert_telegram")

# public site (dismiss link in the DM) — the Caddy hostname (perimeter-closed; never raw :8000)
_SITE = "https://srv1704897.hstgr.cloud"

_SEV_EMOJI = {"critical": "🔴", "high": "🟠"}
_VAL_EMOJI = {"risk": "⚠", "opportunity": "▲", "neutral": "•"}

_DELIVERY_SCHEMA = """
CREATE TABLE IF NOT EXISTS signal_alert_delivery (
    alert_id     INTEGER PRIMARY KEY,          -- signal_alert_state.id (fire-once)
    delivered_at TEXT NOT NULL DEFAULT (datetime('now')),
    severity     TEXT,
    channel      TEXT NOT NULL DEFAULT 'owner_dm'
);
"""


def ensure_schema(conn) -> None:
    """Create the module-owned delivery ledger (idempotent; no db.py coupling)."""
    conn.executescript(_DELIVERY_SCHEMA)


def _owner_chat_id() -> Optional[int]:
    """The owner's DM chat id — the first numeric token of telegram_allowed_user_ids.
    (Same derivation as news_feed._owner_chat_id; replicated to keep this module isolated.)"""
    for tok in (settings.telegram_allowed_user_ids or "").split(","):
        tok = tok.strip()
        if tok.isdigit():
            return int(tok)
    return None


def _undelivered(conn, *, as_of: Optional[str], min_severity: str) -> list[dict]:
    """Active alerts not yet DM'd, newest/highest-priority first. min_severity='critical'
    pages only criticals; 'high' pages critical+high. Reuses the rail's own ranking."""
    ensure_schema(conn)
    rows = SA.active_alerts(conn, as_of=as_of, limit=200)
    keep = {"critical"} if min_severity == "critical" else {"critical", "high"}
    rows = [r for r in rows if r.get("severity") in keep]
    if not rows:
        return []
    ids = [r["id"] for r in rows if r.get("id") is not None]
    sent: set[int] = set()
    if ids:
        qs = ",".join("?" * len(ids))
        sent = {r[0] for r in conn.execute(
            f"SELECT alert_id FROM signal_alert_delivery WHERE alert_id IN ({qs})", ids).fetchall()}
    return [r for r in rows if r.get("id") not in sent]


def _fmt_row(r: dict) -> str:
    sev = _SEV_EMOJI.get(r.get("severity"), "•")
    val = _VAL_EMOJI.get(r.get("valence") or "", "")
    sym = html.escape(str(r.get("symbol") or "?"))
    lens = html.escape(str(r.get("lens") or ""))
    etype = html.escape(str(r.get("event_type") or "").replace("_", " "))
    frm, to = r.get("from_state"), r.get("to_state")
    move = ""
    if frm or to:
        move = f" — {html.escape(str(frm or '·'))} → <b>{html.escape(str(to or '·'))}</b>"
    note = html.escape(str(r.get("note") or "")).strip()
    note = f"  <i>{note}</i>" if note else ""
    return f"{sev}{val} <b>{sym}</b> · {lens}/{etype}{move}{note}"


def format_message(rows: list[dict], *, as_of: Optional[str] = None) -> str:
    """The owner-DM digest — descriptive state-changes, NEVER an action instruction."""
    n = len(rows)
    day = (rows[0].get("as_of") if rows else as_of) or ""
    head = (f"🔔 <b>Patearn — {n} new critical alert{'s' if n != 1 else ''}</b>"
            f"{(' · ' + html.escape(str(day)[:10])) if day else ''}")
    body = "\n".join(_fmt_row(r) for r in rows)
    fence = ("\nDescriptive state-changes from the signal bus — <b>context, not a "
             "buy/sell/act instruction</b>. Review &amp; dismiss on the rail: "
             f"{_SITE}/dash/attention")
    return f"{head}\n\n{body}\n{fence}"


def push(conn, *, as_of: Optional[str] = None, min_severity: str = "critical",
         dry_run: bool = False, chat_id: Optional[int] = None) -> dict:
    """Select undelivered high-severity alerts, DM the owner once, record delivery (fire-once).

    Returns a summary dict. Sends nothing (and records nothing) on dry_run or with no owner
    chat id / no token — degrades safely, never raises into the caller (the nightly --detect
    step must never fail on a paging error)."""
    rows = _undelivered(conn, as_of=as_of, min_severity=min_severity)
    if not rows:
        return {"selected": 0, "sent": 0, "reason": "nothing new"}

    dest = chat_id if chat_id is not None else _owner_chat_id()
    if dest is None:
        return {"selected": len(rows), "sent": 0, "reason": "no owner chat id"}
    if dry_run:
        return {"selected": len(rows), "sent": 0, "reason": "dry-run", "preview": format_message(rows, as_of=as_of)}
    if not settings.telegram_bot_token:
        return {"selected": len(rows), "sent": 0, "reason": "no telegram token"}

    from src.automation.digest import _send  # transport (reuse; imported late to keep isolation)
    ok = _send(int(dest), format_message(rows, as_of=as_of))
    if not ok:
        return {"selected": len(rows), "sent": 0, "reason": "send failed"}

    ensure_schema(conn)
    conn.executemany(
        "INSERT OR IGNORE INTO signal_alert_delivery (alert_id, severity) VALUES (?, ?)",
        [(r["id"], r.get("severity")) for r in rows if r.get("id") is not None])
    conn.commit()
    log.info("signal_alert_telegram: DM'd %d alert(s) to owner", len(rows))
    return {"selected": len(rows), "sent": len(rows), "reason": "ok"}


def run_push(*, as_of: Optional[str] = None, min_severity: str = "critical",
             dry_run: bool = False, chat_id: Optional[int] = None) -> dict:
    """Convenience wrapper that opens its own connection."""
    from src.core.db import get_conn
    with get_conn() as conn:
        return push(conn, as_of=as_of, min_severity=min_severity, dry_run=dry_run, chat_id=chat_id)


def main() -> int:
    ap = argparse.ArgumentParser(description="Owner-DM pager for critical bus alerts")
    ap.add_argument("--push", action="store_true", help="select + DM undelivered critical alerts")
    ap.add_argument("--asof", default=None, help="PIT anchor date (default: newest batch)")
    ap.add_argument("--min-severity", default="critical", choices=["critical", "high"],
                    help="lowest severity to page (default: critical)")
    ap.add_argument("--dry-run", action="store_true", help="select + render, send nothing")
    ap.add_argument("--to", type=int, default=None, help="override chat id (testing)")
    args = ap.parse_args()
    if not args.push:
        ap.print_help()
        return 0
    res = run_push(as_of=args.asof, min_severity=args.min_severity,
                   dry_run=args.dry_run, chat_id=args.to)
    if args.dry_run and res.get("preview"):
        print(res["preview"])
    print({k: v for k, v in res.items() if k != "preview"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
