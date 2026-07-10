"""Dataset A+ — SAST stake & pledge-flow events from NSE (Codex resp-14/15, queue item).

Two primary-source listing feeds (LISTING-COMPLETE — every field is in the JSON row, no
per-event XML/archive fetch, so no nsearchives throttle exposure):

  * **Reg 29 (`corporate-sast-reg29`)** — SAST threshold disclosures: acquisitions/sales
    crossing 5% or moving ±2%, by ANY substantial holder (promoterType flags which).
    This widens dataset A beyond insiders to every large-stake move. ~570 rows/month.
  * **Reg 31/32 (`corporate-pledgedata-sast3132`)** — promoter pledge FLOW with
    MAGNITUDE: event type (Creation / Release / Invocation), the event's % of equity,
    and the post-event total encumbrance %. The quarterly SHP feed gives the pledge
    STOCK (shareholding_xbrl.py); this gives the flow BETWEEN quarters, and upgrades
    the insider pledge verdict from count-based to magnitude-based. ~110 rows/month.

PIT clock = the exchange broadcast/system timestamp (never the event date). Both tables
are content-hash idempotent (no exchange-native row id; the visible seqId repeats like
AppID — never a dedup key). House hardening: chunked windows, per-chunk commits (the
write lock never spans a fetch — 2026-07-02 outage lesson), one bad chunk never kills a
run. Names are stored as sha1 hashes (person-privacy convention of insider_events).

Run (VPS):
  python -m src.automation.sast_events --selftest
  python -m src.automation.sast_events --ingest 2026-06-01 2026-07-02
  python -m src.automation.sast_events --agg SYMBOL [--as-of ISO]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.sast_events")

_NSE_HOME = "https://www.nseindia.com"
_NSE_REF = "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"
_API_REG29 = "https://www.nseindia.com/api/corporate-sast-reg29"
_API_PLEDGE = "https://www.nseindia.com/api/corporate-pledgedata-sast3132"
_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/122 Safari/537.36")

_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sast_reg29_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT UNIQUE,
    symbol        TEXT NOT NULL,
    broadcast_dt  TEXT,               -- PIT clock (exchange system time)
    txn_from      TEXT,               -- transaction date range (event clock, NOT PIT)
    txn_to        TEXT,
    acquirer_hash TEXT,               -- sha1 of acquirer name (privacy convention)
    promoter_flag INTEGER,            -- promoterType == 'Y'
    acq_sale      TEXT,               -- 'ACQ' | 'SALE' | NULL
    mode          TEXT,               -- acquisitionMode as filed
    reg_type      TEXT,               -- 'Reg29(1)' / 'Reg29(2)'
    shares_acq    REAL,
    shares_sale   REAL,
    shares_after  REAL,
    pct_after     REAL,               -- totAftDiluted (% of diluted capital post-txn)
    pct_acq       REAL,               -- totAcqDiluted (% acquired this txn)
    pct_sale      REAL,               -- totSaleDiluted (% sold this txn)
    attachment    TEXT,
    parsed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sast29_sym ON sast_reg29_events(symbol, broadcast_dt);

CREATE TABLE IF NOT EXISTS sast_pledge_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    uid            TEXT UNIQUE,
    symbol         TEXT NOT NULL,
    broadcast_dt   TEXT,              -- PIT clock
    reporting_dt   TEXT,
    event_from     TEXT,              -- event date range (event clock, NOT PIT)
    event_to       TEXT,
    promoter_hash  TEXT,
    event_type     TEXT,              -- CREATE | RELEASE | INVOKE | OTHER (normalized)
    event_type_raw TEXT,
    event_pct      REAL,              -- magnitude: this event's % of total equity
    pre_pct        REAL,              -- promoter holding % before
    post_pct       REAL,              -- promoter holding % after
    encumb_pct     REAL,              -- post-event TOTAL encumbered % of equity
    counterparty   TEXT,              -- eventDetailsEntity (lender text, as filed)
    attachment     TEXT,
    parsed_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sastpl_sym ON sast_pledge_events(symbol, broadcast_dt);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


# ── parsing helpers ───────────────────────────────────────────────────────────
def _phash(name: Optional[str]) -> Optional[str]:
    if not name or not str(name).strip():
        return None
    return hashlib.sha1(str(name).strip().lower().encode("utf-8")).hexdigest()[:16]


def _num(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in ("", "-", "NA", "nil", "Nil", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _dt(s: Optional[str]) -> Optional[str]:
    """'30-Jun-2026 20:01:59' / '29-JUN-2026' -> ISO. None on failure."""
    if not s:
        return None
    m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?", str(s).strip())
    if not m:
        return None
    dd, mon, yyyy, hms = m.groups()
    mi = _MON.get(mon.title())
    if not mi:
        return None
    iso = f"{yyyy}-{mi:02d}-{dd}"
    return f"{iso} {hms}" if hms else iso


def _dt_range(s: Optional[str]) -> tuple:
    """'23-Jun-2026 - 23-Jun-2026' / '29-JUN-2026 to 29-JUN-2026' -> (from_iso, to_iso)."""
    if not s:
        return None, None
    parts = re.split(r"\s+(?:to|-)\s+", str(s).strip(), maxsplit=1)
    a = _dt(parts[0]) if parts else None
    b = _dt(parts[1]) if len(parts) > 1 else a
    return (a or "")[:10] or None, (b or a or "")[:10] or None


def classify_pledge_event(raw: Optional[str]) -> str:
    """Normalize eventDetailsType. Vocabulary observed live: Release / Creation /
    Invocation (+ free-text variants). Unknown -> OTHER, never guessed."""
    t = (raw or "").lower()
    if any(k in t for k in ("releas", "unpledg", "revoc", "revok", "closure", "satisf")):
        return "RELEASE"
    # INVOKE before CREATE: "Invocation of pledge" contains "pledg" and must not
    # classify as a fresh pledge (caught by the selftest)
    if "invoc" in t or "invok" in t:
        return "INVOKE"
    if any(k in t for k in ("creat", "pledg", "encumb", "fresh")):
        return "CREATE"
    return "OTHER"


def norm_reg29(r: dict) -> Optional[dict]:
    sym = (r.get("symbol") or "").strip().upper()
    if not sym:
        return None
    ast = (r.get("acqSaleType") or "").strip().lower()
    tf, tt = _dt_range(r.get("acquirerDate"))
    return {
        "symbol": sym,
        "broadcast_dt": _dt(r.get("sysTime") or r.get("timestamp") or r.get("time")),
        "txn_from": tf, "txn_to": tt,
        "acquirer_hash": _phash(r.get("acquirerName")),
        "promoter_flag": 1 if (r.get("promoterType") or "").strip().upper() == "Y" else 0,
        "acq_sale": "ACQ" if ast.startswith("acq") else ("SALE" if ast.startswith("sale") else None),
        "mode": r.get("acquisitionMode"),
        "reg_type": r.get("regType"),
        "shares_acq": _num(r.get("noOfShareAcq")),
        "shares_sale": _num(r.get("noOfShareSale")),
        "shares_after": _num(r.get("noOfShareAft")),
        "pct_after": _num(r.get("totAftDiluted")),
        "pct_acq": _num(r.get("totAcqDiluted")),
        "pct_sale": _num(r.get("totSaleDiluted")),
        "attachment": r.get("attachement") or r.get("attachment"),
    }


def norm_pledge(r: dict) -> Optional[dict]:
    sym = (r.get("symbol") or "").strip().upper()
    if not sym:
        return None
    ef, et = _dt_range(r.get("eventDate"))
    raw_type = r.get("eventDetailsType")
    return {
        "symbol": sym,
        "broadcast_dt": _dt(r.get("broadcastdate") or r.get("sysTime")),
        "reporting_dt": (_dt(r.get("reportingDate")) or "")[:10] or None,
        "event_from": ef, "event_to": et,
        "promoter_hash": _phash(r.get("promoterName")),
        "event_type": classify_pledge_event(raw_type),
        "event_type_raw": raw_type,
        "event_pct": _num(r.get("eventDetailsPerc")),
        "pre_pct": _num(r.get("preeventHoldingPerc")),
        "post_pct": _num(r.get("postEventHoldingPerc")),
        "encumb_pct": _num(r.get("encumbPerc")),
        "counterparty": r.get("eventDetailsEntity"),
        "attachment": r.get("attachment"),
    }


def _uid(ev: dict, fields: tuple) -> str:
    return hashlib.sha1("|".join(str(ev.get(k)) for k in fields).encode("utf-8")).hexdigest()[:20]


_UID29 = ("symbol", "txn_from", "txn_to", "acquirer_hash", "acq_sale",
          "shares_acq", "shares_sale", "shares_after")
_UIDPL = ("symbol", "event_from", "event_to", "promoter_hash", "event_type_raw",
          "event_pct", "encumb_pct")


def save_reg29(conn, events: list) -> int:
    n = 0
    for ev in events:
        if not ev:
            continue
        conn.execute(
            """INSERT INTO sast_reg29_events (uid, symbol, broadcast_dt, txn_from, txn_to,
                 acquirer_hash, promoter_flag, acq_sale, mode, reg_type, shares_acq,
                 shares_sale, shares_after, pct_after, pct_acq, pct_sale, attachment)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET broadcast_dt=excluded.broadcast_dt,
                 pct_after=excluded.pct_after, parsed_at=datetime('now')""",
            (_uid(ev, _UID29), ev["symbol"], ev["broadcast_dt"], ev["txn_from"], ev["txn_to"],
             ev["acquirer_hash"], ev["promoter_flag"], ev["acq_sale"], ev["mode"], ev["reg_type"],
             ev["shares_acq"], ev["shares_sale"], ev["shares_after"], ev["pct_after"],
             ev["pct_acq"], ev["pct_sale"], ev["attachment"]))
        n += 1
    return n


def save_pledge(conn, events: list) -> int:
    n = 0
    for ev in events:
        if not ev:
            continue
        conn.execute(
            """INSERT INTO sast_pledge_events (uid, symbol, broadcast_dt, reporting_dt,
                 event_from, event_to, promoter_hash, event_type, event_type_raw, event_pct,
                 pre_pct, post_pct, encumb_pct, counterparty, attachment)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET broadcast_dt=excluded.broadcast_dt,
                 event_type=excluded.event_type, encumb_pct=excluded.encumb_pct,
                 parsed_at=datetime('now')""",
            (_uid(ev, _UIDPL), ev["symbol"], ev["broadcast_dt"], ev["reporting_dt"],
             ev["event_from"], ev["event_to"], ev["promoter_hash"], ev["event_type"],
             ev["event_type_raw"], ev["event_pct"], ev["pre_pct"], ev["post_pct"],
             ev["encumb_pct"], ev["counterparty"], ev["attachment"]))
        n += 1
    return n


# ── fetch + ingest ────────────────────────────────────────────────────────────
def _nse_session():
    import requests
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)
    s.get(_NSE_REF, headers=h, timeout=20)
    return s, h


def _fetch(session, headers, api: str, from_date: str, to_date: str) -> list:
    def ddmmyyyy(iso):
        y, m, d = str(iso)[:10].split("-")
        return f"{d}-{m}-{y}"
    r = session.get(api, params={"index": "equities", "from_date": ddmmyyyy(from_date),
                                 "to_date": ddmmyyyy(to_date)}, headers=headers, timeout=45)
    r.raise_for_status()
    j = r.json()
    return (j.get("data") if isinstance(j, dict) else j) or []


def ingest_range(from_date: str, to_date: str, *, chunk_days: int = 30,
                 pause: float = 1.2) -> dict:
    """Both SAST feeds across a window, chunked; per-chunk commits; idempotent."""
    start = datetime.strptime(from_date, "%Y-%m-%d").date()
    end = datetime.strptime(to_date, "%Y-%m-%d").date()
    session, headers = _nse_session()
    stats = {"reg29_fetched": 0, "reg29_saved": 0, "pledge_fetched": 0, "pledge_saved": 0}
    with get_conn() as conn:
        ensure_schema(conn)
        conn.commit()
        cur = start
        while cur <= end:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
            a, b = cur.isoformat(), chunk_end.isoformat()
            for api, norm, save, key in (
                    (_API_REG29, norm_reg29, save_reg29, "reg29"),
                    (_API_PLEDGE, norm_pledge, save_pledge, "pledge")):
                try:
                    rows = _fetch(session, headers, api, a, b)
                except Exception as e:  # noqa: BLE001 — one bad chunk never kills the run
                    log.warning("SAST %s fetch failed %s..%s: %s", key, a, b, e)
                    time.sleep(pause)
                    continue
                stats[f"{key}_fetched"] += len(rows)
                stats[f"{key}_saved"] += save(conn, [norm(r) for r in rows])
                conn.commit()          # bounded txn — never hold the lock across a fetch
                time.sleep(pause)
            log.info("SAST %s..%s: reg29=%d pledge=%d (running)", a, b,
                     stats["reg29_fetched"], stats["pledge_fetched"])
            cur = chunk_end + timedelta(days=1)
    return stats


# ── PIT aggregation (broadcast-date clock; magnitude-based) ──────────────────
# SEBI takeover-code open-offer trigger — one filing moving >= this % of capital
# is a control event (M&A / promoter restructuring), not an accumulation flow.
CONTROL_PCT = 25.0


def aggregate(symbol: str, as_of: str, *, conn=None) -> dict:
    """Pledge-flow + stake-move roll-up for one symbol, PIT on broadcast_dt.

    Magnitude semantics (the upgrade over insider_events' count-based pledge verdict):
    net_pledge_flow_90d = created% − released% (of total equity) in the window;
    invocation is ALWAYS adverse (forced sale of promoter collateral).
    """
    own = conn is None
    if own:
        conn = get_conn().__enter__()
    try:
        ensure_schema(conn)
        pl = conn.execute(
            "SELECT event_type, event_pct, encumb_pct, broadcast_dt FROM sast_pledge_events "
            "WHERE symbol=? AND substr(broadcast_dt,1,10) <= ? ORDER BY broadcast_dt",
            (symbol.upper(), as_of)).fetchall()
        r29 = conn.execute(
            "SELECT acq_sale, promoter_flag, pct_acq, pct_sale, broadcast_dt, reg_type "
            "FROM sast_reg29_events "
            "WHERE symbol=? AND substr(broadcast_dt,1,10) <= ? ORDER BY broadcast_dt",
            (symbol.upper(), as_of)).fetchall()
    finally:
        if own:
            conn.close()

    ao = datetime.strptime(as_of, "%Y-%m-%d").date()

    def _in(dt_s, days):
        if not dt_s:
            return False
        d = datetime.strptime(str(dt_s)[:10], "%Y-%m-%d").date()
        return (ao - d).days <= days

    created = sum(e[1] or 0.0 for e in pl if e[0] == "CREATE" and _in(e[3], 90))
    released = sum(e[1] or 0.0 for e in pl if e[0] == "RELEASE" and _in(e[3], 90))
    invoked = sum(1 for e in pl if e[0] == "INVOKE" and _in(e[3], 90))
    latest_encumb = next((e[2] for e in reversed(pl) if e[2] is not None), None)
    # FLOW = Reg 29(2) deltas ONLY, below the control threshold. Two live-verified
    # inflation modes (S88):
    #   * Reg 29(1) initial-crossing filings report the whole HOLDING as
    #     totAcqDiluted (PAISALO: pct_acq == pct_after == 35.9%) — a LEVEL, not a
    #     flow; summing them made stake_net ±185% of capital. Counted as
    #     `stake_crossings_90d` instead.
    #   * Control-size transfers (HINDZINC: one ~50.1% block filed by two related
    #     entities; COHANCE: a 56% promoter restructuring) are M&A events, not
    #     accumulation flows — and PAC co-filings double-count them. SEBI's
    #     takeover-code trigger (25%) is the principled line: >=25% of capital in
    #     one filing = a CONTROL TRANSFER, counted + badged, never summed.
    flows = [e for e in r29 if e[5] != "Reg29(1)"]
    stake_acq = sum(e[2] or 0.0 for e in flows
                    if e[0] == "ACQ" and (e[2] or 0.0) < CONTROL_PCT and _in(e[4], 90))
    stake_sale = sum(e[3] or 0.0 for e in flows
                     if e[0] == "SALE" and (e[3] or 0.0) < CONTROL_PCT and _in(e[4], 90))
    control = sum(1 for e in flows
                  if max(e[2] or 0.0, e[3] or 0.0) >= CONTROL_PCT and _in(e[4], 90))
    crossings = sum(1 for e in r29 if e[5] == "Reg29(1)" and _in(e[4], 90))
    return {
        "symbol": symbol.upper(), "as_of": as_of,
        "n_pledge_events_known": len(pl), "n_reg29_known": len(r29),
        "pledge_created_pct_90d": round(created, 2),
        "pledge_released_pct_90d": round(released, 2),
        "net_pledge_flow_90d": round(created - released, 2),   # + = encumbrance rising
        "pledge_invocations_90d": invoked,
        "latest_encumbered_pct": latest_encumb,
        "stake_acquired_pct_90d": round(stake_acq, 2),
        "stake_sold_pct_90d": round(stake_sale, 2),
        "stake_crossings_90d": crossings,
        "control_transfers_90d": control,
        "sast_signal": ("invocation_risk" if invoked else
                        "encumbrance_rising" if created - released > 0.5 else
                        "encumbrance_falling" if released - created > 0.5 else "neutral"),
    }


# ── whole-universe confluence roll-up (S88 board: page+card+pillar+gate) ──────

def _shape(agg: dict) -> str:
    """DESCRIPTIVE shape of a confluence name — a crossing label, never a call
    (footprint detector FAILED its gate: post-disclosure reads only; E-04/E-05
    are armed-not-run, so no arc/velocity claim lives here):
      constructive = holders adding stake while encumbrance falls / stays flat;
      distress     = any invocation, or stake selling while encumbrance rises;
      mixed        = both feeds present, neither pattern."""
    stake_net = agg["stake_acquired_pct_90d"] - agg["stake_sold_pct_90d"]
    if agg["pledge_invocations_90d"] > 0 or (
            stake_net < 0 and agg["sast_signal"] == "encumbrance_rising"):
        return "distress"
    if stake_net > 0 and agg["sast_signal"] in ("encumbrance_falling", "neutral"):
        return "constructive"
    return "mixed"


def universe_confluence(conn, days: int = 90):
    """Per-symbol PIT roll-up for every CONFLUENCE name — a symbol with BOTH a
    Reg-29 stake event AND a Reg-31/32 pledge event inside the trailing `days`
    (broadcast-date anchored). Reuses aggregate() per symbol (indexed reads).
    Returns ({symbol: agg+shape+stake_net}, census, as_of)."""
    ensure_schema(conn)
    r = conn.execute(
        "SELECT MAX(d) FROM (SELECT MAX(substr(broadcast_dt,1,10)) d FROM sast_reg29_events "
        "UNION ALL SELECT MAX(substr(broadcast_dt,1,10)) FROM sast_pledge_events)").fetchone()
    as_of = r[0] if r else None
    if not as_of:
        return {}, {}, None
    lo = (datetime.strptime(as_of, "%Y-%m-%d").date() - timedelta(days=days)).isoformat()
    s29 = {x[0] for x in conn.execute(
        "SELECT DISTINCT symbol FROM sast_reg29_events WHERE substr(broadcast_dt,1,10) >= ?",
        (lo,))}
    spl = {x[0] for x in conn.execute(
        "SELECT DISTINCT symbol FROM sast_pledge_events WHERE substr(broadcast_dt,1,10) >= ?",
        (lo,))}
    confl = sorted(s29 & spl)
    out: dict = {}
    for sym in confl:
        a = aggregate(sym, as_of, conn=conn)
        a["stake_net_pct_90d"] = round(
            a["stake_acquired_pct_90d"] - a["stake_sold_pct_90d"], 2)
        a["shape"] = _shape(a)
        out[sym] = a
    census = {"stake_names": len(s29), "pledge_names": len(spl),
              "confluence_names": len(confl)}
    return out, census, as_of


def flagged_symbols(conn, as_of: Optional[str] = None, days: int = 90):
    """The card/pillar/gate cohort (single source, D94 parity rule): the
    confluence names — both feeds active on the same symbol inside 90 days.
    Sorted by combined magnitude (|stake net %| + |pledge net %|), so the top
    of the card is the loudest crossing, whatever its shape. Returns
    ([(symbol, agg)], as_of)."""
    aggs, _census, got_as_of = universe_confluence(conn, days=days)
    out = sorted(aggs.items(),
                 key=lambda kv: -(abs(kv[1]["stake_net_pct_90d"])
                                  + abs(kv[1]["net_pledge_flow_90d"])))
    return out, (as_of or got_as_of)


# ── selftest (synthetic; no DB, no network) ───────────────────────────────────
def _selftest() -> int:
    assert classify_pledge_event("Release") == "RELEASE"
    assert classify_pledge_event("Shares unpledged by lender") == "RELEASE"
    assert classify_pledge_event("Creation") == "CREATE"
    assert classify_pledge_event("Fresh pledge created") == "CREATE"
    assert classify_pledge_event("Invocation of pledge") == "INVOKE"
    assert classify_pledge_event("something odd") == "OTHER"
    assert _dt_range("23-Jun-2026 - 25-Jun-2026") == ("2026-06-23", "2026-06-25")
    assert _dt_range("29-JUN-2026 to 29-JUN-2026") == ("2026-06-29", "2026-06-29")
    ev = norm_pledge({"symbol": "acme", "broadcastdate": "30-Jun-2026 20:01:59",
                      "eventDate": "23-Jun-2026 - 23-Jun-2026", "promoterName": "P",
                      "eventDetailsType": "Release", "eventDetailsPerc": "3.9",
                      "encumbPerc": "11.42", "preeventHoldingPerc": "60.1",
                      "postEventHoldingPerc": "60.1"})
    assert ev["symbol"] == "ACME" and ev["event_type"] == "RELEASE" and ev["event_pct"] == 3.9
    assert ev["broadcast_dt"] == "2026-06-30 20:01:59"
    r = norm_reg29({"symbol": "acme", "sysTime": "01-Jul-2026 10:00:00",
                    "acquirerDate": "29-JUN-2026 to 29-JUN-2026", "acquirerName": "X",
                    "acqSaleType": "Sale", "promoterType": "Y", "noOfShareSale": "813684",
                    "totSaleDiluted": "2.9", "totAftDiluted": "63.9", "regType": "Reg29(2)"})
    assert r["acq_sale"] == "SALE" and r["promoter_flag"] == 1 and r["pct_sale"] == 2.9
    # uid stability: derived/normalized fields (event_type) must not affect identity
    e2 = dict(ev); e2["event_type"] = "OTHER"
    assert _uid(ev, _UIDPL) == _uid(e2, _UIDPL)
    print("selftest OK  classify + ranges + normalize(reg29/pledge) + uid-stability")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--ingest", nargs=2, metavar=("FROM", "TO"))
    p.add_argument("--chunk-days", type=int, default=30)
    p.add_argument("--agg", metavar="SYMBOL")
    p.add_argument("--as-of", default=None)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    if args.ingest:
        res = ingest_range(args.ingest[0], args.ingest[1], chunk_days=args.chunk_days)
        log.info("SAST ingest: %s", res)
        return
    if args.agg:
        as_of = args.as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with get_conn() as conn:
            print(json.dumps(aggregate(args.agg, as_of, conn=conn), indent=2, default=str))
        return
    p.print_help()


if __name__ == "__main__":
    main()
