"""Alert rail — the FOURTH face of the signal-event bus ("one bus, four faces").

The bus (`src/automation/signal_events.py`, D105) emits every lens's TYPED state-change
into one `signal_events` table. Three faces already read it: the machine `/v1/attention`
(PIT replay), the Attention Queue (`/dash/attention` — the current batch, magnitude-ranked),
and the "since you last looked" brief (per-viewer cookie diff). This module is the fourth:
the **alert rail** — a curated, edge-triggered, multi-day feed of only the HIGHEST-impact
state-changes.

Why a fourth face and not just "filter the queue":
  • The Attention Queue shows a SINGLE batch (`as_of = MAX(as_of)`, today). A big deal
    print or a credibility deterioration three days ago is gone from it. The rail RETAINS
    the recent high-impact alerts across nightly batches (a rolling window).
  • It is CURATED — a strict, rule-based severity gate (§ classify) promotes only events
    that genuinely deserve a notification, not the full tape. The rail stays a short
    notifications list, not a firehose.
  • It is EDGE-TRIGGERED / fire-once — the `signal_alert_state` table's UNIQUE key mirrors
    the event's own identity, so `promote()` records each firing event exactly once
    (INSERT OR IGNORE). This is the tracker_alerts.py dedup pattern applied to the bus.

DOCTRINE (inherited from the bus, non-negotiable):
  • Rule-based, no LLM. Pure-Python severity classification; deterministic.
  • Descriptive-only, NEVER a recommendation. An alert = "a notable state-change fired",
    with the raw before→after beside it — never "buy/sell/act". A `valence` tag
    (risk/opportunity/neutral) is a descriptive read of the CHANGE, not advice. The lenses'
    own fences ride along (CCI descriptive-only, MEP a descriptor D62, deal prints logistics).
    Magnitude ranks attention WITHIN a lens; it is not a return forecast — no study exists
    on event follow-through, and any such claim needs its own pre-registered gate first.
  • No rupee-constant thresholds. Deal severity keys on the within-day value PERCENTILE
    (relative); credibility severity on |Δlevel| (points); nothing on an absolute ₹ cutoff.
  • Isolation (§0.8): brand-new module; owns its `signal_alert_state` table via
    ensure_schema() (no db.py edit). Reads `signal_events` through nothing but plain SQL.
    Promotion runs ONLY in the nightly `signal_events --detect` CLI path (piggybacked, no
    systemd unit change); the web face is READ-ONLY (never writes), so no request ever
    holds a DB write lock (the write-lock-outage class).

CLI:
    python -m src.automation.signal_alerts --promote [--asof YYYY-MM-DD]
    python -m src.automation.signal_alerts --list [--within 7] [--limit 40]
    python -m src.automation.signal_alerts --stats
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

log = logging.getLogger("hermes.signal_alerts")

# --- owned table (isolation: not in db.py SCHEMA_BASE) -----------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS signal_alert_state (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    lens         TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    direction    TEXT,
    from_state   TEXT,
    to_state     TEXT,
    magnitude    REAL,
    severity     TEXT NOT NULL,          -- 'critical' | 'high'
    valence      TEXT,                   -- 'risk' | 'opportunity' | 'neutral' (descriptive)
    as_of        TEXT NOT NULL,          -- the event's PIT date (from signal_events.as_of)
    note         TEXT,
    event_id     INTEGER,                -- the signal_events.id it was promoted from (provenance)
    first_fired  TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged_at TEXT,                -- NULL = active on the rail; set = dismissed by the analyst
    -- edge-triggered / fire-once: one alert per (symbol, lens, type, day), exactly the
    -- uniqueness signal_events itself guarantees, so promote() is INSERT OR IGNORE.
    UNIQUE(symbol, lens, event_type, as_of)
);
CREATE INDEX IF NOT EXISTS idx_sigalert_asof     ON signal_alert_state(as_of DESC);
CREATE INDEX IF NOT EXISTS idx_sigalert_severity ON signal_alert_state(severity, as_of DESC);
"""

SEVERITIES = ("critical", "high")
VALENCES = ("risk", "opportunity", "neutral")

# How alert-worthy each lens is when its magnitude ties (phase/quadrant flips are all
# magnitude 1.0 by construction, so this weight — not magnitude — orders them). deal and
# cci carry their own graded magnitude, so their weight is lower but their events rarely
# tie. Used only for the per-batch cap tiebreak + display ranking, never as a return score.
_LENS_WEIGHT = {"deal": 1.00, "cci": 0.95, "rs": 0.90, "mep": 0.70, "oi": 0.60}

# At most this many alerts per (batch, lens) — bounds the flood from mep/oi phase flips
# (~130/night each), where every flip has magnitude 1.0. deal/cci/rs are naturally few.
_PER_LENS_CAP = 6

# Deal-print value-percentile bar (relative, within the day's printed names — NOT a ₹
# constant). Only top-decile prints alert. NO 'critical' tier for deals: the bus magnitude
# is a WITHIN-DAY percentile, so the day's largest print is always exactly 1.0 — a 'critical'
# cut would fire on every quiet single-deal day. Rarity lives in the ≥0.90 gate, not a tier.
_DEAL_HIGH = 0.90
# Credibility DROP (points) that makes a deterioration step 'critical' (the one legit CCI use).
_CCI_CRIT_DROP = 15.0

# Ordered band scales (higher = stronger / more bullish). Valence is the SIGN of the from→to
# move on the scale — so STRONG_ACCUM→ACCUM reads as *weakening* (not a fresh opportunity) and
# STRONG_DISTRIB→DISTRIB as *easing* (not a fresh risk) — and only a move that strengthens INTO
# a non-neutral band (sign(move)==sign(destination)) is promoted, so hysteresis wobbles and
# returns-to-neutral are filtered. Token sets are the LIVE stored vocabularies (verified against
# signal_events / rsband_signals on prod), extended with the fuller rsband tokens for headroom.
_MEP_SCALE = {"STRONG_DISTRIB": -2, "DISTRIB": -1, "NEUTRAL": 0, "ACCUM": 1, "STRONG_ACCUM": 2}
_RS_SCALE = {"BREAKDOWN_DN": -2, "TOUCH_SUP": -1, "INSIDE": 0, "TOUCH_RES": 1, "BREAKOUT_UP": 2}


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
    # Idempotent migration for tables created before the acknowledge feature (SQLite has no
    # ADD COLUMN IF NOT EXISTS): try to add it, swallow the "duplicate column" on re-run.
    try:
        conn.execute("ALTER TABLE signal_alert_state ADD COLUMN acknowledged_at TEXT")
    except Exception:  # noqa: BLE001 — column already present
        pass


# --- severity classification (pure; the editorial heart) ---------------------

def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ordinal_move(scale: dict, from_state, to_state):
    """For an ordinal band flip, return (valence, to_rank) when it is a genuine strengthening
    INTO a non-neutral band, else None. valence = sign of the from→to move on the scale."""
    fr = scale.get((from_state or "").strip().upper())
    to = scale.get((to_state or "").strip().upper())
    if fr is None or to is None or to == 0 or to == fr:
        return None
    move = to - fr
    if (move > 0) != (to > 0):          # the move must head toward the destination band's side
        return None
    return ("opportunity" if to > 0 else "risk", to)


def classify(lens: str, event_type: str, direction: Optional[str],
             to_state: Optional[str], magnitude,
             from_state: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Decide whether a bus event deserves the alert rail, and how loud.

    Returns ``(severity, valence)`` where severity ∈ {'critical','high'} or ``(None, None)``
    when the event is NOT alert-worthy (it still lives in the Attention Queue — the rail is a
    strict subset). ``valence`` ∈ {'risk','opportunity','neutral'} is a DESCRIPTIVE read of the
    change, for scannability only — never advice, never a filter on what the analyst should do.

    Editorial rule (deliberately strict so the rail stays a notifications list):
      • deal — a top-decile within-day value print (percentile). Always 'high' (no critical tier).
      • cci  — keyed on the numeric level DELTA (robust to the bus forcing direction='down' on a
               NULL-level trend-only flip): a drop is 'risk' (critical if ≥15pt); a ≥15pt
               improvement is a 'high' opportunity; a small move is not alert-worthy.
      • mep  — an ordinal band flip that STRENGTHENS into accumulation (opportunity) or
               distribution (risk); into STRONG_DISTRIB = critical. Easing / →neutral is skipped.
      • oi   — a positioning flip INTO short-buildup/long-unwind (risk) or long-buildup/
               short-cover (opportunity). (FLAT and unrecognized destinations are skipped.)
      • rs   — an index/sector RS-band flip that strengthens toward resistance/breakout
               (opportunity) or support/breakdown (risk); INSIDE / easing is skipped.
    """
    et = event_type or ""

    if lens == "deal" and et == "deal_print":
        if float(magnitude or 0.0) < _DEAL_HIGH:
            return None, None
        val = ("opportunity" if direction == "up"
               else "risk" if direction == "down" else "neutral")
        return "high", val

    if lens == "cci" and et == "credibility_step":
        fr, to = _num(from_state), _num(to_state)
        if fr is not None and to is not None:
            d = to - fr
            if d < 0:
                return ("critical" if -d >= _CCI_CRIT_DROP else "high"), "risk"
            return ("high", "opportunity") if d >= _CCI_CRIT_DROP else (None, None)
        # pure trend-token flip (no numeric levels): read the trend word, don't trust direction
        tw = (to_state or "").upper()
        if "IMPROV" in tw:
            return "high", "opportunity"
        if "DETER" in tw or "WORSEN" in tw or "DECLIN" in tw:
            return "high", "risk"
        return None, None

    if lens == "mep" and et == "phase_flip":
        mv = _ordinal_move(_MEP_SCALE, from_state, to_state)
        if mv is None:
            return None, None
        val, to_rank = mv
        return ("critical" if to_rank == -2 else "high"), val   # into STRONG_DISTRIB = alarm

    if lens == "rs" and et == "phase_flip":
        mv = _ordinal_move(_RS_SCALE, from_state, to_state)
        return ("high", mv[0]) if mv else (None, None)

    if lens == "oi" and et == "oi_flip":
        to = (to_state or "").upper()
        if "SHORT_BUILDUP" in to or "LONG_UNWIND" in to:
            return "high", "risk"
        if "LONG_BUILDUP" in to or "SHORT_COVER" in to:
            return "high", "opportunity"
        return None, None

    return None, None


def _priority(lens: str, magnitude) -> float:
    """Display/cap ordering only (never a return score): magnitude × lens weight."""
    return float(magnitude or 0.0) * _LENS_WEIGHT.get(lens, 0.5)


# --- promotion (nightly; the only writer) ------------------------------------

def promote(conn, as_of: Optional[str] = None) -> dict:
    """Promote the highest-impact events of the latest (or a given) batch into the rail.

    Edge-triggered / idempotent: each event maps to at most one alert row (UNIQUE key), so a
    re-run promotes nothing new. Per-(batch, lens) capped so a night of ~130 mep/oi flips
    cannot flood the rail. Returns a per-severity count of NEW alerts.
    """
    ensure_schema(conn)
    batch = str(as_of).strip()[:10] if as_of else None
    if not batch:
        row = conn.execute("SELECT MAX(as_of) FROM signal_events").fetchone()
        batch = row[0] if row and row[0] else None
    if not batch:
        return {"batch": None, "promoted": 0, "by_severity": {}}

    try:
        events = [dict(r) for r in conn.execute(
            "SELECT id, symbol, lens, event_type, direction, from_state, to_state, "
            "magnitude, as_of, note FROM signal_events WHERE as_of = ?", (batch,)).fetchall()]
    except Exception:  # noqa: BLE001 — a missing table/column degrades to "no alerts"
        return {"batch": batch, "promoted": 0, "by_severity": {}}

    # classify, then keep at most _PER_LENS_CAP per lens (strongest by priority first)
    candidates: list[tuple[float, dict, str, str]] = []
    for e in events:
        sev, val = classify(e.get("lens") or "", e.get("event_type") or "",
                            e.get("direction"), e.get("to_state"), e.get("magnitude"),
                            from_state=e.get("from_state"))
        if sev is None:
            continue
        candidates.append((_priority(e.get("lens") or "", e.get("magnitude")), e, sev, val))
    candidates.sort(key=lambda t: t[0], reverse=True)

    per_lens: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    promoted = 0
    for _prio, e, sev, val in candidates:
        lens = e.get("lens") or ""
        if per_lens.get(lens, 0) >= _PER_LENS_CAP:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO signal_alert_state "
            "(symbol, lens, event_type, direction, from_state, to_state, magnitude, "
            " severity, valence, as_of, note, event_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (e.get("symbol"), lens, e.get("event_type"), e.get("direction"),
             e.get("from_state"), e.get("to_state"), e.get("magnitude"),
             sev, val, e.get("as_of"), e.get("note"), e.get("id")))
        # Count the SLOT whether or not the row was newly inserted: signal_events rows are
        # immutable (idempotent by key), so the candidate set + priority order are stable
        # across re-runs → the SAME strongest-_PER_LENS_CAP are (re)selected, keeping promote
        # idempotent. (A batch that later GROWS could exceed the cap by a row; benign — the
        # read side caps the display, and the extra row is still a real, lower-ranked change.)
        per_lens[lens] = per_lens.get(lens, 0) + 1
        if cur.rowcount:
            promoted += cur.rowcount
            by_sev[sev] = by_sev.get(sev, 0) + 1
    conn.commit()
    log.info("signal_alerts.promote batch=%s promoted=%d by_severity=%s",
             batch, promoted, by_sev)
    return {"batch": batch, "promoted": promoted, "by_severity": by_sev}


# --- read API (the web face reads through this; never writes) ----------------

def active_alerts(conn, *, within_days: int = 7, limit: int = 40,
                  as_of: Optional[str] = None, sev: Optional[str] = None,
                  val: Optional[str] = None) -> list[dict]:
    """The rail: alerts whose as_of is within `within_days` of the newest batch (or of
    `as_of` when replaying), severity-critical first then priority then recency. Optional
    `sev` (severity) / `val` (valence) narrow the rail for triage.

    Windowed on the BATCH clock (as_of), not wall-clock, so a replay is coherent and a
    quiet stretch never drops a still-recent alert on a real-world gap.
    """
    ensure_schema(conn)
    anchor = str(as_of).strip()[:10] if as_of else None
    if not anchor:
        row = conn.execute("SELECT MAX(as_of) FROM signal_alert_state").fetchone()
        anchor = row[0] if row and row[0] else None
    if not anchor:
        return []
    # Fetch the WHOLE window (bounded: ≤ _PER_LENS_CAP × lenses × within_days rows) and
    # rank in Python with the single source of truth _priority (magnitude × lens weight),
    # then truncate. A SQL `ORDER BY magnitude LIMIT n` would disagree with the priority
    # key (weight ≤ 1, so a high-magnitude low-weight row can outrank a higher-PRIORITY row
    # in raw magnitude) and could drop a top-priority alert before the Python re-sort.
    # date(anchor, '-N days') — SQLite date math on the ISO as_of strings. SQL orders by
    # recency (as_of/id DESC); the STABLE Python sort then lifts critical-first + priority
    # while PRESERVING that recency within ties — one ranking, no double-sort divergence.
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM signal_alert_state WHERE acknowledged_at IS NULL "
        "AND as_of <= ? AND as_of >= date(?, ?) ORDER BY as_of DESC, id DESC",
        (anchor, anchor, f"-{max(0, int(within_days) - 1)} days")).fetchall()]
    if sev in SEVERITIES:
        rows = [r for r in rows if r.get("severity") == sev]
    if val in VALENCES:
        rows = [r for r in rows if r.get("valence") == val]
    rows.sort(key=lambda r: (r.get("severity") != "critical",
                             -_priority(r.get("lens") or "", r.get("magnitude"))))
    return rows[:int(limit)]


def active_count(conn, *, within_days: int = 7, as_of: Optional[str] = None) -> dict:
    """Active-alert totals for the window (the UNFILTERED picture, for the badge + filter
    chip counts): total + per-severity + per-valence breakdowns."""
    ensure_schema(conn)
    anchor = str(as_of).strip()[:10] if as_of else None
    if not anchor:
        row = conn.execute("SELECT MAX(as_of) FROM signal_alert_state").fetchone()
        anchor = row[0] if row and row[0] else None
    if not anchor:
        return {"total": 0, "by_severity": {}, "by_valence": {}}
    where = ("WHERE acknowledged_at IS NULL AND as_of <= ? AND as_of >= date(?, ?)")
    params = (anchor, anchor, f"-{max(0, int(within_days) - 1)} days")
    by = {r["severity"]: r["c"] for r in conn.execute(
        f"SELECT severity, COUNT(*) c FROM signal_alert_state {where} GROUP BY severity",
        params).fetchall()}
    byv = {r["valence"]: r["c"] for r in conn.execute(
        f"SELECT valence, COUNT(*) c FROM signal_alert_state {where} GROUP BY valence",
        params).fetchall()}
    return {"total": sum(by.values()), "by_severity": by, "by_valence": byv}


def acknowledge(conn, alert_id: int) -> int:
    """Dismiss one alert by id (analyst reviewed it). Returns rows updated (0 if already
    dismissed / unknown id). Only the web ack endpoint + the CLI write here."""
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE signal_alert_state SET acknowledged_at = datetime('now') "
        "WHERE id = ? AND acknowledged_at IS NULL", (int(alert_id),))
    conn.commit()
    return cur.rowcount or 0


def acknowledge_all(conn, *, within_days: int = 7, as_of: Optional[str] = None) -> int:
    """Dismiss every active alert in the current rail window (the 'dismiss all' action).
    Scoped to the same window the rail shows so a replay/older tail is never silently cleared."""
    ensure_schema(conn)
    anchor = str(as_of).strip()[:10] if as_of else None
    if not anchor:
        row = conn.execute("SELECT MAX(as_of) FROM signal_alert_state").fetchone()
        anchor = row[0] if row and row[0] else None
    if not anchor:
        return 0
    cur = conn.execute(
        "UPDATE signal_alert_state SET acknowledged_at = datetime('now') "
        "WHERE acknowledged_at IS NULL AND as_of <= ? AND as_of >= date(?, ?)",
        (anchor, anchor, f"-{max(0, int(within_days) - 1)} days"))
    conn.commit()
    return cur.rowcount or 0


def backfill(conn, *, batches: int = 10) -> dict:
    """Seed the rail from the last `batches` distinct signal_events days (deploy / re-seed).
    Edge-triggered promote() is idempotent, so this is safe to re-run. Returns the roll-up."""
    ensure_schema(conn)
    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT as_of FROM signal_events ORDER BY as_of DESC LIMIT ?",
        (int(batches),)).fetchall()]
    promoted = 0
    for d in days:
        promoted += promote(conn, as_of=d).get("promoted", 0)
    log.info("signal_alerts.backfill: %d batch(es), %d alerts promoted", len(days), promoted)
    return {"batches": len(days), "promoted": promoted}


def stats(conn) -> dict:
    ensure_schema(conn)
    total = conn.execute("SELECT COUNT(*) c FROM signal_alert_state").fetchone()["c"]
    by_sev = {r["severity"]: r["c"] for r in conn.execute(
        "SELECT severity, COUNT(*) c FROM signal_alert_state GROUP BY severity")}
    by_lens = {r["lens"]: r["c"] for r in conn.execute(
        "SELECT lens, COUNT(*) c FROM signal_alert_state GROUP BY lens ORDER BY c DESC")}
    latest = conn.execute("SELECT MAX(as_of) m FROM signal_alert_state").fetchone()["m"]
    return {"alerts": total, "by_severity": by_sev, "by_lens": by_lens, "latest_as_of": latest}


# --- CLI ---------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Alert rail — the 4th face of the signal-event bus.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--promote", action="store_true", help="promote the latest batch's top events")
    g.add_argument("--backfill", action="store_true", help="seed the rail from the last N batches")
    g.add_argument("--list", action="store_true", help="print the active rail")
    g.add_argument("--stats", action="store_true", help="rail coverage summary")
    g.add_argument("--ack", type=int, metavar="ID", help="dismiss one alert by id")
    g.add_argument("--ack-all", action="store_true", help="dismiss every active alert in the window")
    ap.add_argument("--asof", default=None)
    ap.add_argument("--batches", type=int, default=10, help="--backfill: how many recent batches")
    ap.add_argument("--within", type=int, default=7)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    from src.core.db import get_conn
    with get_conn() as conn:
        if args.promote:
            log.info("done: %s", promote(conn, as_of=args.asof))
        elif args.backfill:
            log.info("done: %s", backfill(conn, batches=args.batches))
        elif args.stats:
            import json
            print(json.dumps(stats(conn), indent=2))
        elif args.ack is not None:
            log.info("dismissed %d alert(s)", acknowledge(conn, args.ack))
        elif args.ack_all:
            log.info("dismissed %d alert(s)", acknowledge_all(conn, within_days=args.within,
                                                              as_of=args.asof))
        else:
            for a in active_alerts(conn, within_days=args.within, limit=args.limit):
                print(f"  {a['as_of']}  {a['severity']:8} {a['valence'] or '-':11} "
                      f"{a['lens']:5} {a['note'] or ''}")


if __name__ == "__main__":
    main()
