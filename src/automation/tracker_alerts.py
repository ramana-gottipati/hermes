"""Nightly Telegram push for the Tracker alerts engine.

The web Tracker (src/web/dashboard.py, Step 5) lets you set per-item alert rules
(stocks_in_play.alerts_json) and shows what is firing in-app. THIS module is the
push half: it evaluates every rule + the automatic "ready to act" read across the
watchlist and open positions, EOD, and pushes what is NEWLY firing to Telegram.

Design (so every aspect is handled even while Telegram is blocked in India):
- EDGE-TRIGGERED — state lives in tracker_alert_state keyed by (sip_id, rule-sig).
  A rule pushes once when it starts firing; it will not re-push while it keeps
  firing. When it stops firing its state row is dropped, so a later re-fire pushes
  again. → no daily spam.
- RETRY-WHILE-BLOCKED — a send that fails (e.g. api.telegram.org unreachable from
  India today) leaves the rows `notified_at IS NULL`; the next run re-attempts. So
  the moment Telegram is reachable again, everything still-firing flushes in one
  digest. Nothing is lost; nothing double-sends.
- SELF-CONTAINED — no web-layer import (a cron job must not depend on FastAPI / the
  dashboard module). The rule logic mirrors dashboard._eval_alerts / _ready_to_act
  one-to-one; keep the two in sync (a future refactor can share one module once the
  parallel CCI edits to dashboard.py land). No LLM. Reuses the proven sender in
  src.automation.digest.

Run:  python -m src.automation.tracker_alerts            (evaluate, dedup, push)
      python -m src.automation.tracker_alerts --dry-run  (evaluate + print only)
Invoked by the hermes-tracker-alerts systemd timer (daily, after the bhav ingest).
"""

import argparse
import json
import logging
from datetime import datetime, timezone

from src.automation.digest import PUBLIC_BASE_URL, _send
from src.automation.signals import is_near_key
from src.core.db import get_conn
from src.core.settings import settings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hermes.tracker_alerts")

# One-time creation of the dedup/queue table (kept here, NOT in db.py, so this
# feature ships without touching the shared schema file). Idempotent.
_STATE_DDL = """
CREATE TABLE IF NOT EXISTS tracker_alert_state (
    sip_id      INTEGER NOT NULL,
    sig         TEXT    NOT NULL,                 -- stable rule key, e.g. 'rs_above:80'
    symbol      TEXT,
    kind        TEXT,                             -- 'alert' | 'ready'
    message     TEXT,                             -- latest human text (live values)
    first_fired TEXT NOT NULL DEFAULT (datetime('now')),
    last_fired  TEXT NOT NULL DEFAULT (datetime('now')),
    notified_at TEXT,                             -- NULL = delivered to ALL dests; else still pending somewhere
    PRIMARY KEY (sip_id, sig)
);
"""

# Per-destination delivery ledger (CL-PROV-10). The parent table's single notified_at can't
# express "delivered to dest A but not dest B"; without it, a partial multi-dest failure marked
# NOTHING notified and re-sent the whole digest to the dest that already got it. This child table
# records each successful (alert, dest) delivery so the next run re-sends ONLY to dests that have
# not yet received that alert. Idempotent; additive (no migration of existing rows needed).
_DELIVERY_DDL = """
CREATE TABLE IF NOT EXISTS tracker_alert_delivery (
    sip_id       INTEGER NOT NULL,
    sig          TEXT    NOT NULL,
    dest         TEXT    NOT NULL,                 -- chat_id as text (dests may be large ints)
    delivered_at TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (sip_id, sig, dest)
);
"""


# --- data lookups ----------------------------------------------------------
def _latest_sig(conn, sym):
    r = conn.execute("SELECT * FROM stock_signals WHERE symbol=? "
                     "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    return dict(r) if r else {}


def _latest_close(conn, sym):
    r = conn.execute("SELECT close FROM bhavcopy_rows WHERE symbol=? AND series='EQ' "
                     "AND (segment='CM' OR segment IS NULL) ORDER BY trade_date DESC LIMIT 1",
                     (sym,)).fetchone()
    return r["close"] if r else None


def _f52(conn, sym, cache):
    if sym in cache:
        return cache[sym]
    r = conn.execute(
        "SELECT MAX(close) hi, MIN(close) lo FROM (SELECT close FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
        "ORDER BY trade_date DESC LIMIT 252)", (sym,)).fetchone()
    out = (r["hi"], r["lo"]) if r else (None, None)
    cache[sym] = out
    return out


# --- rule evaluation (mirror of dashboard._eval_alerts / _ready_to_act) ----
def _eval_rules(rules, sig, cmp_, then, target, stop, f52):
    """[(sig_key, message)] for the rules firing now. sig_key is the STABLE rule
    identity (no live values) so dedup survives daily price drift."""
    out = []
    sig = sig or {}
    for rule in rules or []:
        t, v = rule.get("t"), rule.get("v")
        key = f"{t}:{'' if v is None else v}"
        try:
            if t == "cross_up" and cmp_ and v is not None and cmp_ >= v:
                out.append((key, f"price ₹{cmp_:.1f} ≥ ₹{v:g}"))
            elif t == "cross_down" and cmp_ and v is not None and cmp_ <= v:
                out.append((key, f"price ₹{cmp_:.1f} ≤ ₹{v:g}"))
            elif t == "pct_since" and cmp_ and then and v is not None:
                ch = (cmp_ - then) / then * 100.0
                if abs(ch) >= v:
                    out.append((key, f"{ch:+.1f}% since add"))
            elif t == "near_52h" and cmp_ and v is not None:
                hi = f52[0]
                if hi and (hi - cmp_) / hi * 100.0 <= v:
                    out.append((key, f"within {v:g}% of 52w high ₹{hi:.0f}"))
            elif t == "near_52l" and cmp_ and v is not None:
                lo = f52[1]
                if lo and (cmp_ - lo) / lo * 100.0 <= v:
                    out.append((key, f"within {v:g}% of 52w low ₹{lo:.0f}"))
            elif t == "rs_above" and v is not None and (sig.get("rs_rank") or 0) >= v:
                out.append((key, f"RS rank {sig.get('rs_rank')} ≥ {v:g}"))
            elif t == "char_accum" and sig.get("accum_character") == "ACCUMULATION":
                out.append((key, "character flipped to ACCUM"))
            elif t == "dvpt_trigger" and sig.get("trigger_rank") in ("SS", "S", "A"):
                out.append((key, f"DVPT trigger {sig.get('trigger_rank')}"))
            elif t == "near_target" and cmp_ and v is not None and target:
                if cmp_ >= target or (target - cmp_) / cmp_ * 100.0 <= v:
                    out.append((key, f"within {v:g}% of target ₹{target:g}"))
            elif t == "near_stop" and cmp_ and v is not None and stop:
                if cmp_ <= stop or (cmp_ - stop) / cmp_ * 100.0 <= v:
                    out.append((key, f"near/below stop ₹{stop:g}"))
        except Exception:
            continue
    return out


def _ready(sig):
    """('ready', reason) when a strong setup is live now, else None."""
    if not sig:
        return None
    char = sig.get("accum_character")
    rs = sig.get("rs_rank") or 0
    tr = sig.get("trigger_rank")
    reasons = []
    if tr in ("SS", "S"):
        reasons.append(f"DVPT trigger {tr}")
    if char == "ACCUMULATION" and is_near_key(sig.get("gap_to_key_p3m")):
        reasons.append("ACCUM near key price")
    if char == "ACCUMULATION" and rs >= 70:
        reasons.append(f"ACCUM + RS {rs}")
    if rs >= 85 and char != "DISTRIBUTION":
        reasons.append(f"RS leader {rs}")
    seen = list(dict.fromkeys(reasons))
    return ("ready", " · ".join(seen)) if seen else None


def evaluate(conn):
    """Current firing set: list of dicts {sip_id, sig, symbol, kind, message}."""
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM stocks_in_play WHERE status IN ('watch','open')").fetchall()]
    f52cache = {}
    out = []
    for r in rows:
        sym = r["symbol"]
        sig = _latest_sig(conn, sym)
        cmp_ = _latest_close(conn, sym)
        try:
            snap = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
        except Exception:
            snap = {}
        try:
            rules = json.loads(r["alerts_json"]) if r.get("alerts_json") else []
        except Exception:
            rules = []
        f52 = _f52(conn, sym, f52cache) if any(
            ru.get("t") in ("near_52h", "near_52l") for ru in rules) else (None, None)
        for key, msg in _eval_rules(rules, sig, cmp_, snap.get("close"),
                                    r.get("price_target"), r.get("stop_loss"), f52):
            out.append({"sip_id": r["id"], "sig": key, "symbol": sym,
                        "kind": "alert", "message": msg})
        # "ready to act" only for watch items (matches the in-app surfacing)
        if r["status"] == "watch":
            rd = _ready(sig)
            if rd:
                out.append({"sip_id": r["id"], "sig": rd[0], "symbol": sym,
                            "kind": "ready", "message": rd[1]})
    return out


# --- destinations + message ------------------------------------------------
def _already_delivered(conn, sip_id, sig, dest: str) -> bool:
    """True if this exact alert (sip_id, sig) has already been delivered to ``dest`` — so we never
    re-send it to a destination that already received it after a partial multi-dest failure (CL-PROV-10)."""
    return conn.execute(
        "SELECT 1 FROM tracker_alert_delivery WHERE sip_id=? AND sig=? AND dest=? LIMIT 1",
        (sip_id, sig, dest)).fetchone() is not None


def _destinations():
    """Prefer a registered patearn group; else DM the owner(s) from
    telegram_allowed_user_ids — ideal for private portfolio alerts when no group
    is set (and works the moment Telegram is reachable again)."""
    with get_conn() as conn:
        dests = [int(r["chat_id"]) for r in conn.execute(
            "SELECT chat_id FROM patearn_destinations").fetchall()]
    if dests:
        return dests
    ids = [x.strip() for x in (settings.telegram_allowed_user_ids or "").split(",") if x.strip()]
    return [int(x) for x in ids if x.lstrip("-").isdigit()]


def format_alerts(items):
    """Telegram HTML digest for the newly-firing items [(symbol, kind, message)]."""
    now = datetime.now(timezone.utc).astimezone()
    ready = [i for i in items if i[1] == "ready"]
    alerts = [i for i in items if i[1] == "alert"]
    lines = [f"🔔 <b>patearn Tracker — alerts ({now.strftime('%d %b, %I:%M %p')})</b>", "",
             f"<b>{len(items)} new</b> since the last push.", ""]
    if ready:
        lines.append("⚡ <b>Ready to act</b>")
        for sym, _k, msg in ready:
            lines.append(f"• <code>{sym}</code> — {msg}")
        lines.append("")
    if alerts:
        lines.append("🔔 <b>Alerts firing</b>")
        for sym, _k, msg in alerts:
            lines.append(f"• <code>{sym}</code> — {msg}")
        lines.append("")
    lines.append(f"Manage: {PUBLIC_BASE_URL}/dash/watchlists")
    return "\n".join(lines)


# --- run -------------------------------------------------------------------
def run(dry_run=False):
    with get_conn() as conn:
        conn.execute(_STATE_DDL)
        conn.execute(_DELIVERY_DDL)
        current = evaluate(conn)
        cur_keys = {(c["sip_id"], c["sig"]) for c in current}

        if dry_run:
            log.info("DRY RUN — %d firing now:", len(current))
            for c in current:
                log.info("  [%s] %s — %s", c["kind"], c["symbol"], c["message"])
            return current

        existing = {(r["sip_id"], r["sig"]): dict(r) for r in conn.execute(
            "SELECT * FROM tracker_alert_state").fetchall()}
        pending = []   # dicts {sip_id, sig, symbol, kind, message} still owed to ≥1 dest
        for c in current:
            k = (c["sip_id"], c["sig"])
            if k in existing:
                conn.execute("UPDATE tracker_alert_state SET last_fired=datetime('now'), "
                             "message=?, symbol=?, kind=? WHERE sip_id=? AND sig=?",
                             (c["message"], c["symbol"], c["kind"], c["sip_id"], c["sig"]))
                if existing[k]["notified_at"] is None:      # not yet delivered to all dests → still owed
                    pending.append(c)
            else:
                conn.execute("INSERT INTO tracker_alert_state(sip_id,sig,symbol,kind,message) "
                             "VALUES(?,?,?,?,?)",
                             (c["sip_id"], c["sig"], c["symbol"], c["kind"], c["message"]))
                pending.append(c)                            # newly firing
        # drop states that stopped firing (so a later re-fire re-notifies); clear their per-dest
        # delivery ledger too so a re-fire is treated as fresh.
        for k in existing:
            if k not in cur_keys:
                conn.execute("DELETE FROM tracker_alert_state WHERE sip_id=? AND sig=?", k)
                conn.execute("DELETE FROM tracker_alert_delivery WHERE sip_id=? AND sig=?", k)

        if not pending:
            log.info("nothing new to push (%d firing, all already notified)", len(current))
            return current

        if not settings.telegram_bot_token:
            log.warning("TELEGRAM_BOT_TOKEN not set — %d alerts left pending", len(pending))
            return current
        dests = _destinations()
        if not dests:
            log.warning("no destination (empty patearn_destinations + no allowed user IDs) "
                        "— %d alerts left pending for retry", len(pending))
            return current

        # Per-destination delivery (CL-PROV-10). For EACH dest, push only the alerts that dest has
        # not already received (from the delivery ledger), so the dest that already got an alert is
        # never re-sent it. Every dest is attempted independently — one dest failing does not block
        # the others, and on failure only the un-delivered alerts for THAT dest are retried next run.
        failed_dests = []
        for d in dests:
            ds = str(d)
            owed = [p for p in pending if not _already_delivered(conn, p["sip_id"], p["sig"], ds)]
            if not owed:
                continue
            msg = format_alerts([(p["symbol"], p["kind"], p["message"]) for p in owed])
            if _send(d, msg):
                for p in owed:
                    conn.execute(
                        "INSERT OR IGNORE INTO tracker_alert_delivery(sip_id,sig,dest) VALUES(?,?,?)",
                        (p["sip_id"], p["sig"], ds))
                log.info("pushed %d alerts to destination %s", len(owed), ds)
            else:
                failed_dests.append(ds)
                log.error("Telegram send to destination %s failed — %d alerts left pending for "
                          "that dest only (other dests unaffected); will retry next run",
                          ds, len(owed))

        # Mark the parent row notified_at only when an alert has reached EVERY current dest, so the
        # "all already notified" fast-path and the legacy flag stay meaningful.
        ndests = len(dests)
        for p in pending:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM tracker_alert_delivery WHERE sip_id=? AND sig=? AND dest IN "
                "(" + ",".join("?" * ndests) + ")",
                [p["sip_id"], p["sig"]] + [str(x) for x in dests]).fetchone()[0]
            if cnt >= ndests:
                conn.execute("UPDATE tracker_alert_state SET notified_at=datetime('now') "
                             "WHERE sip_id=? AND sig=? AND notified_at IS NULL",
                             (p["sip_id"], p["sig"]))
        if failed_dests:
            log.error("partial delivery: %d/%d destination(s) failed %s — affected alerts retry "
                      "next run (succeeded dests will NOT be re-sent)",
                      len(failed_dests), ndests, failed_dests)
        return current


def main():
    ap = argparse.ArgumentParser(description="Tracker alerts → Telegram push")
    ap.add_argument("--dry-run", action="store_true", help="evaluate + print, no send / no state writes")
    args = ap.parse_args()
    try:
        run(dry_run=args.dry_run)
    except Exception:
        log.exception("tracker_alerts run failed")


if __name__ == "__main__":
    main()
