"""NSE corporate actions ingestion — splits, bonuses, dividends, rights, demergers.

RESURRECTED 2026-07-06 (data-postmortem: the table sat at 0 rows since ~session 18).
The original source — four nsearchives.nseindia.com CSVs (Bonus_Issue.csv etc.) —
404s permanently; the feed died silently and nothing watched it (now
``data_quality.chk_derived_liveness`` does). The PRIMARY source today (guardrail #8)
is the exchange's own corporate-actions API:

    https://www.nseindia.com/api/corporates-corporateActions?index=equities
        &from_date=DD-MM-YYYY&to_date=DD-MM-YYYY

(NOTE the camelCase: NSE renamed the endpoint — the old hyphenated
``corporates-corporate-actions`` path now 404s uniformly; probed 2026-07-06 with
event-calendar/corporates-pit 200-ing in the same session, so it was the path,
not anti-bot. Dated windows verified serving history back to at least 2006.)
symbol-native (no scrip map), served windowed, with the same anti-bot session
priming the other live NSE feeds use (insider_events / results_calendar pattern).

WHY this table matters even though value-based signals are action-invariant:
``security_master.classify_event`` builds the ``security_events`` continuity-break
spine (demerger/merger/scheme) FROM these rows — 0 rows here meant 0 events there
and an unhonoured trust-page claim; and the authoritative split/bonus tape
cross-validates ``adjust.py``'s prev_close-inferred factors.

Discipline: network happens OUTSIDE any write txn; each window is stored in its
own short transaction (AUD-24 / D82c class); consecutive-failure breaker; the
UNIQUE(symbol, action_type, ex_date, details) key makes every run idempotent.

Usage:
    python -m src.automation.corp_actions                    # trailing 400d window
    python -m src.automation.corp_actions --fetch --days 90  # trailing N days
    python -m src.automation.corp_actions --backfill         # deep history (2004→)
    python -m src.automation.corp_actions --stats | --selftest
"""

import argparse
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.corp_actions")

_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_NSE_HOME = "https://www.nseindia.com"
_NSE_REF = "https://www.nseindia.com/companies-listing/corporate-filings-actions"
_NSE_API = "https://www.nseindia.com/api/corporates-corporateActions"   # camelCase — the hyphenated path is dead

REQUEST_PAUSE = 1.2          # between windows
WINDOW_DAYS = 90             # per-request date window
BREAKER_FAILS = 6            # consecutive fetch FAILURES (not empties) → abort run

# ── parsing (source-agnostic; kept from the CSV era, extended for API subjects) ──

_RATIO_RE = re.compile(r"(\d+)\s*[:to/]+\s*(\d+)", re.IGNORECASE)
# "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share"
_SPLIT_RE = re.compile(
    r"(?:from|of)\s*(?:rs\.?|re\.?|inr)?\s*([\d.]+)\s*(?:/-)?\s*(?:each|per\s+share)?\s*"
    r"(?:to|into)\s*(?:rs\.?|re\.?|inr)?\s*([\d.]+)",
    re.IGNORECASE,
)


def _parse_ratio(action_type: str, purpose_text: str) -> tuple:
    """Best-effort (from, to) ratio.

      "Bonus 1:5"                                             → (1, 5)
      "... From Rs 10/- Per Share To Re 1/- Per Share"        → (10, 1)
      "Rs 2 Per Share Dividend"                               → (None, None)
    """
    if not purpose_text:
        return None, None
    text = purpose_text.strip()
    if action_type in ("SPLIT", "CONSOLIDATION"):
        m = _SPLIT_RE.search(text)
        if m:
            return float(m.group(1)), float(m.group(2))
    m = _RATIO_RE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def _detect_action_type_from_purpose(purpose: str) -> Optional[str]:
    """Classify an NSE `subject` string. Order matters: DEMERGER before MERGER
    ('demerger' contains 'merg' — the classify_event lesson)."""
    p = (purpose or "").upper()
    if "BONUS" in p:
        return "BONUS"
    if "SUB-DIVISION" in p or "SUBDIVISION" in p or "SPLIT" in p:
        return "SPLIT"
    if "CONSOLIDATION" in p:
        return "CONSOLIDATION"
    if "RIGHTS" in p:
        return "RIGHTS"
    if "DIVIDEND" in p:
        return "DIVIDEND"
    if "DEMERG" in p or "SPIN-OFF" in p or "SPIN OFF" in p:
        return "DEMERGER"
    if "AMALGAM" in p:
        return "AMALGAMATION"
    if "MERG" in p:
        return "MERGER"
    if "SCHEME OF ARRANG" in p:
        return "SCHEME"
    if "BUYBACK" in p or "BUY BACK" in p or "BUY-BACK" in p:
        return "BUYBACK"
    if "CAPITAL REDUCTION" in p or "REDUCTION OF CAPITAL" in p:
        return "CAPITAL_REDUCTION"
    return None


# Pure shareholder meetings are announcements, not actions ON the security —
# storing them would bloat the action tape with non-events.
_MEETING_RE = re.compile(r"\b(ANNUAL GENERAL MEETING|EXTRA\s?-?ORDINARY GENERAL MEETING|"
                         r"A\.?G\.?M\.?|E\.?G\.?M\.?)\b", re.IGNORECASE)


def _normalize_date(s: Optional[str]) -> Optional[str]:
    if not s or str(s).strip() in ("-", ""):
        return None
    s = str(s).strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_api_row(r: dict) -> Optional[dict]:
    """One NSE corporate-actions API row → a corporate_actions row, or None to skip.
    Tolerant of field-name drift (subject/purpose, exDate/exdate, recDate/recordDate)."""
    symbol = (r.get("symbol") or r.get("SYMBOL") or "").strip().upper()
    if not symbol:
        return None
    purpose = (r.get("subject") or r.get("purpose") or r.get("PURPOSE") or "").strip()
    action_type = _detect_action_type_from_purpose(purpose)
    if action_type is None:
        if _MEETING_RE.search(purpose):
            return None                                  # AGM/EGM — not an action
        action_type = "OTHER"
    ex_date = _normalize_date(r.get("exDate") or r.get("exdate") or r.get("EX DATE"))
    record_date = _normalize_date(r.get("recDate") or r.get("recordDate") or r.get("RECORD DATE"))
    ratio_from, ratio_to = _parse_ratio(action_type, purpose)
    return {"symbol": symbol, "action_type": action_type, "ex_date": ex_date,
            "record_date": record_date, "ratio_from": ratio_from, "ratio_to": ratio_to,
            "details": purpose, "source": "nse-ca-api"}


# ── store (short own transaction; never spans network I/O) ───────────────────

def store_actions(rows: list, conn=None) -> int:
    """Idempotent upsert; returns rows actually INSERTED (conflict-skips excluded)."""
    if not rows:
        return 0
    sql = ("INSERT INTO corporate_actions "
           "(symbol, action_type, ex_date, record_date, ratio_from, ratio_to, details, source) "
           "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
           "ON CONFLICT(symbol, action_type, ex_date, details) DO NOTHING")
    own = conn is None
    cm = get_conn() if own else None
    c = cm.__enter__() if own else conn
    try:
        n = 0
        for r in rows:
            cur = c.execute(sql, (r["symbol"], r["action_type"], r["ex_date"], r["record_date"],
                                  r["ratio_from"], r["ratio_to"], r["details"], r["source"]))
            n += max(cur.rowcount, 0)
        if own:
            c.commit()
        return n
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── the adjustment-tape read side (S85e reconciliation) ──────────────────────

def price_ratios(conn, symbol: str) -> dict:
    """{ex_date: implied PRICE ratio} for a symbol's SPLIT / BONUS / CONSOLIDATION rows
    with parsed ratios — same-day events COMPOUND (a split and a bonus sharing one
    ex-date multiply, e.g. RNBDENIMS 2026-04-02: 2→1 split × 1:2 bonus = 0.5 × 1/3).

      SPLIT / CONSOLIDATION  F→T : price × T/F
      BONUS m:n (m new per n held): price × n/(m+n)

    The consumer (adjust.adjustment_factors ``events=``) tolerance-gates every ratio
    against the observed ex-day move, so an unparsed / mis-dated / suspect tape row can
    never corrupt a series — worst case the inference layers stand alone (legacy)."""
    out: dict = {}
    for at, ex, rf, rt in conn.execute(
            "SELECT action_type, ex_date, ratio_from, ratio_to FROM corporate_actions "
            "WHERE symbol=? AND action_type IN ('SPLIT','BONUS','CONSOLIDATION') "
            "AND ex_date IS NOT NULL", (symbol,)):
        if not rf or not rt or rf <= 0 or rt <= 0:
            continue
        r = (rt / rf) if at in ("SPLIT", "CONSOLIDATION") else (rt / (rf + rt))
        out[ex] = out.get(ex, 1.0) * r
    return {k: v for k, v in out.items() if 0.02 < v < 50 and abs(v - 1) >= 0.001}


def reconcile(conn, since: Optional[str] = None) -> dict:
    """Adjust-vs-tape reconciliation: classify every SPLIT/BONUS/CONSOLIDATION event-group
    (symbol × ex_date; same-day events compound) against the observed ex-day close move.

      CAUGHT_FALLBACK   move > CC_THRESH → the legacy jump-fallback adjusted it
      MISSED_DEAD_ZONE  3%..30% move, tape+observed agree → NO inferred factor existed
                        (the S85e defect class; tape-wired consumers now adjust these)
      TAPE_SUSPECT      implied vs observed disagree > tape tolerance → parse/NSE quirk,
                        review — the gate refuses these, inference stands
      NO_RATIO_*        tape row lacks a parsed ratio (fallback may still catch)
      NO_BHAV           no trading rows at the ex-date (delisted/SME) — nothing to adjust
      NEGLIGIBLE        implied move < 3% (below detector scale)

    Full-history audit 2026-07-10: 888 CAUGHT / 112 MISSED (92 symbols) / 77 SUSPECT
    / 144 NO_BHAV / 132 NO_RATIO / 1 NEGLIGIBLE — recorded in PROJECT_STATE S85e."""
    from src.automation.adjust import CC_THRESH, _TAPE_TOL
    where = "AND ex_date >= ?" if since else ""
    args = (since,) if since else ()
    evs = conn.execute(
        f"SELECT symbol, action_type, ex_date, ratio_from, ratio_to FROM corporate_actions "
        f"WHERE action_type IN ('SPLIT','BONUS','CONSOLIDATION') AND ex_date IS NOT NULL {where} "
        f"ORDER BY symbol, ex_date", args).fetchall()
    groups: dict = {}
    for sym, at, ex, rf, rt in evs:
        groups.setdefault((sym, ex), []).append((at, rf, rt))
    counts: dict = {}
    detail: dict = {"MISSED_DEAD_ZONE": [], "TAPE_SUSPECT": []}

    def bump(k):
        counts[k] = counts.get(k, 0) + 1

    for (sym, ex), grp in sorted(groups.items()):
        implied, have_ratio = 1.0, True
        for at, rf, rt in grp:
            if not rf or not rt or rf <= 0 or rt <= 0:
                have_ratio = False
                continue
            implied *= (rt / rf) if at in ("SPLIT", "CONSOLIDATION") else (rt / (rf + rt))
        rows = conn.execute(
            "SELECT trade_date, close FROM bhavcopy_rows WHERE symbol=? AND series IN ('EQ','BE','BZ') "
            "AND trade_date<=? ORDER BY trade_date DESC LIMIT 2", (sym, ex)).fetchall()
        if len(rows) < 2 or rows[0][0] != ex or not rows[1][1] or not rows[0][1]:
            bump("NO_BHAV")
            continue
        observed = rows[0][1] / rows[1][1]
        caught = abs(observed - 1) > CC_THRESH and 0.02 < observed < 50
        if not have_ratio:
            bump("NO_RATIO_CAUGHT" if caught else "NO_RATIO_UNCAUGHT")
            continue
        if abs(implied - 1) < 0.03:
            bump("NEGLIGIBLE")
            continue
        if abs(observed / implied - 1) > _TAPE_TOL:
            bump("TAPE_SUSPECT")
            detail["TAPE_SUSPECT"].append((sym, ex, round(implied, 3), round(observed, 3)))
        elif caught:
            bump("CAUGHT_FALLBACK")
        else:
            bump("MISSED_DEAD_ZONE")
            detail["MISSED_DEAD_ZONE"].append((sym, ex, round(implied, 3), round(observed, 3)))
    return {"groups": len(groups), "counts": counts, "detail": detail}


# ── network (VPS; not exercised by --selftest) ───────────────────────────────

def _nse_session():
    import requests
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)              # prime anti-bot cookies
    s.get(_NSE_REF, headers=h, timeout=20)
    return s, h


def fetch_window(from_iso: str, to_iso: str, *, session=None, headers=None) -> Optional[list]:
    """Raw API rows for [from_iso, to_iso]. None = FETCH FAILURE (feeds the breaker);
    [] = a genuine 200-but-empty window."""
    if session is None:
        session, headers = _nse_session()

    def ddmmyyyy(iso):
        y, m, d = str(iso)[:10].split("-")
        return "%s-%s-%s" % (d, m, y)

    url = "%s?index=equities&from_date=%s&to_date=%s" % (
        _NSE_API, ddmmyyyy(from_iso), ddmmyyyy(to_iso))
    try:
        r = session.get(url, headers=headers, timeout=45)
        if r.status_code != 200:
            log.warning("corp-actions window %s..%s HTTP %s", from_iso, to_iso, r.status_code)
            return None
        data = r.json()
        rows = data.get("data") if isinstance(data, dict) else data
        return rows if isinstance(rows, list) else []
    except Exception as e:  # noqa: BLE001
        log.warning("corp-actions window %s..%s failed: %s", from_iso, to_iso, e)
        return None


def ingest_range(from_iso: str, to_iso: str) -> dict:
    """Windowed fetch+store over [from_iso, to_iso]. Per-window commits; breaker on
    consecutive FAILURES (empty windows are legitimate and do not trip it)."""
    session, headers = _nse_session()
    stats = {"windows": 0, "rows_seen": 0, "inserted": 0, "skipped_meetings_or_blank": 0,
             "failed_windows": 0, "aborted_breaker": False}
    fails = 0
    lo = date.fromisoformat(from_iso[:10])
    hi = date.fromisoformat(to_iso[:10])
    while lo <= hi:
        wend = min(lo + timedelta(days=WINDOW_DAYS - 1), hi)
        raw = fetch_window(lo.isoformat(), wend.isoformat(), session=session, headers=headers)
        stats["windows"] += 1
        if raw is None:
            stats["failed_windows"] += 1
            fails += 1
            if fails >= BREAKER_FAILS:
                stats["aborted_breaker"] = True
                log.warning("breaker: %d consecutive failed windows — aborting at %s", fails, lo)
                break
        else:
            fails = 0
            rows = []
            for x in raw:
                n = normalize_api_row(x)
                if n is None:
                    stats["skipped_meetings_or_blank"] += 1
                else:
                    rows.append(n)
            stats["rows_seen"] += len(raw)
            stats["inserted"] += store_actions(rows)     # short txn AFTER the network call
        lo = wend + timedelta(days=1)
        time.sleep(REQUEST_PAUSE)
    log.info("corp-actions ingest %s..%s: %s", from_iso, to_iso, stats)
    return stats


def table_stats() -> dict:
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
        by = conn.execute("SELECT action_type, COUNT(*) FROM corporate_actions "
                          "GROUP BY action_type ORDER BY 2 DESC").fetchall()
        rng = conn.execute("SELECT MIN(ex_date), MAX(ex_date) FROM corporate_actions "
                           "WHERE ex_date IS NOT NULL").fetchone()
        return {"rows": n, "by_type": {r[0]: r[1] for r in by},
                "ex_date_range": (rng[0], rng[1])}


# ── forward calendar roll-up (S91 actions lens: page+card+pillar+gate) ────────

FLAG_DAYS = 14      # the card window: an ex-date inside the next 2 weeks


def upcoming(conn, days: int = 60):
    """FORWARD corporate actions: rows with ex_date from today out `days` days,
    soonest first. Pure read; the nightly hermes-corp-actions ingest owns the
    data. DESCRIPTIVE/LOGISTICAL ONLY — the ledger closed both event-drift
    stories on this feed (E-11 dividend drift: placebo-caught NULL, 'no chip
    ships'; E-12 rebrand pump: dead) — this calendar tells you WHAT happens
    WHEN, never what to do about it. Returns (rows, as_of) where as_of =
    the feed's latest ingest stamp."""
    rows = [dict(zip(("symbol", "action_type", "ex_date", "record_date",
                      "ratio_from", "ratio_to", "details"), tuple(r)))
            for r in conn.execute(
                "SELECT symbol, action_type, ex_date, record_date, ratio_from, "
                "ratio_to, details FROM corporate_actions "
                "WHERE ex_date >= date('now') AND ex_date <= date('now', ?) "
                "ORDER BY ex_date ASC, symbol ASC", (f"+{int(days)} days",))]
    r = conn.execute("SELECT MAX(fetched_at) FROM corporate_actions").fetchone()
    as_of = str(r[0])[:10] if r and r[0] else None
    return rows, as_of


def flagged_symbols(conn):
    """The card/pillar/gate cohort (single source, D94 parity rule): distinct
    symbols with a corporate action going ex inside the next FLAG_DAYS days,
    soonest ex-date first. Returns ([(symbol, row)], as_of)."""
    rows, as_of = upcoming(conn, days=FLAG_DAYS)
    per: dict = {}
    for r in rows:
        per.setdefault(r["symbol"], r)          # rows are soonest-first already
    out = sorted(per.items(), key=lambda kv: (kv[1]["ex_date"], kv[0]))
    return out, as_of


# ── selftest (offline, synthetic — no network, no real DB) ───────────────────

def _selftest() -> int:
    import sqlite3

    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    # classification + ratio + dates on REAL NSE subject shapes
    div = normalize_api_row({"symbol": "RELIANCE", "subject": "Dividend - Rs 5.50 Per Share",
                             "exDate": "19-Aug-2024", "recDate": "19-Aug-2024"})
    check("dividend row", div and div["action_type"] == "DIVIDEND" and div["ex_date"] == "2024-08-19"
          and div["ratio_from"] is None)
    spl = normalize_api_row({"symbol": "SIKKO", "subject":
                             "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share",
                             "exDate": "05-Sep-2025"})
    check("face-value split ratio 10→1", spl and spl["action_type"] == "SPLIT"
          and spl["ratio_from"] == 10.0 and spl["ratio_to"] == 1.0)
    bon = normalize_api_row({"symbol": "ACME", "subject": "Bonus 1:1", "exDate": "02-Jun-2025"})
    check("bonus 1:1", bon and bon["action_type"] == "BONUS" and (bon["ratio_from"], bon["ratio_to"]) == (1.0, 1.0))
    dem = normalize_api_row({"symbol": "RELIANCE", "subject":
                             "Demerger of Financial Services Business", "exDate": "20-Jul-2023"})
    check("demerger classified", dem and dem["action_type"] == "DEMERGER")
    agm = normalize_api_row({"symbol": "ACME", "subject": "Annual General Meeting", "exDate": "01-Jun-2025"})
    check("AGM skipped", agm is None)
    check("blank symbol skipped", normalize_api_row({"subject": "Dividend"}) is None)
    check("dash date -> None", _normalize_date("-") is None)

    # classify_event integration: a stored demerger row must yield a continuity break
    from src.automation.security_master import classify_event
    check("classify_event(DEMERGER row) -> DEMERGER",
          classify_event(dem["action_type"], dem["details"]) == "DEMERGER")
    check("classify_event(DIVIDEND row) -> None (not a break)",
          classify_event(div["action_type"], div["details"]) is None)

    # store round-trip + idempotence on the real schema shape
    con = sqlite3.connect(":memory:")
    con.executescript("""
      CREATE TABLE corporate_actions (id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, action_type TEXT NOT NULL, ex_date TEXT, record_date TEXT,
        ratio_from REAL, ratio_to REAL, details TEXT, source TEXT,
        fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(symbol, action_type, ex_date, details));
    """)
    n1 = store_actions([div, spl, bon, dem], conn=con)
    n2 = store_actions([div, spl, bon, dem], conn=con)   # identical re-run
    check("store inserts 4 then 0 (idempotent)", n1 == 4 and n2 == 0)
    check("rowcount counts real inserts only",
          con.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0] == 4)

    # price_ratios: the adjustment-tape read side (S85e)
    con.execute("CREATE TABLE bhavcopy_rows (symbol TEXT, trade_date TEXT, series TEXT, close REAL)")
    cub = normalize_api_row({"symbol": "CUB", "subject": "Bonus 1:3", "exDate": "12-Jun-2026"})
    rnb_s = normalize_api_row({"symbol": "RNB", "subject":
                               "Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 1/- Per Share",
                               "exDate": "02-Apr-2026"})
    rnb_b = normalize_api_row({"symbol": "RNB", "subject": "Bonus 1:2", "exDate": "02-Apr-2026"})
    store_actions([cub, rnb_s, rnb_b], conn=con)
    pr = price_ratios(con, "CUB")
    check("bonus 1:3 -> price x 0.75", abs(pr["2026-06-12"] - 0.75) < 1e-9)
    pr2 = price_ratios(con, "RNB")
    # split 2→1 = ×0.5; bonus 1:2 (1 new per 2 held) = ×2/3 → compound exactly 1/3
    check("same-day split x bonus COMPOUND (0.5 x 2/3 = 1/3)", abs(pr2["2026-04-02"] - (1.0 / 3)) < 1e-9)
    check("dividend/demerger never in the ratio tape", price_ratios(con, "RELIANCE") == {})

    # reconcile: dead-zone vs caught vs suspect classification on synthetic bhav
    con.executemany("INSERT INTO bhavcopy_rows VALUES (?,?,?,?)", [
        ("CUB", "2026-06-11", "EQ", 256.8), ("CUB", "2026-06-12", "EQ", 201.7),   # -21.5% agree -> MISSED
        ("RNB", "2026-04-01", "EQ", 100.0), ("RNB", "2026-04-02", "EQ", 33.5),    # ~1/3, agrees -> CAUGHT
        ("SIKKO", "2026-05-02", "EQ", 100.0), ("SIKKO", "2026-05-05", "EQ", 99.0)])
    sik = normalize_api_row({"symbol": "SIKKO", "subject": "Bonus 1:1", "exDate": "05-May-2026"})
    store_actions([sik], conn=con)                        # tape says -50%, market says flat -> SUSPECT
    rec = reconcile(con)
    check("reconcile classes", rec["counts"].get("MISSED_DEAD_ZONE") == 1
          and rec["counts"].get("CAUGHT_FALLBACK") == 1 and rec["counts"].get("TAPE_SUSPECT") == 1)
    con.close()

    print("corp_actions selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="NSE corporate-actions ingest (live API, primary source)")
    p.add_argument("--fetch", action="store_true", help="trailing window (default when no mode given)")
    p.add_argument("--days", type=int, default=400, help="trailing window size for --fetch")
    p.add_argument("--backfill", action="store_true", help="deep history from --from-year")
    p.add_argument("--from-year", type=int, default=2004)
    p.add_argument("--window", nargs=2, metavar=("FROM", "TO"), help="explicit ISO range")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--reconcile", metavar="SINCE", nargs="?", const="2004-01-01",
                   help="adjust-vs-tape reconciliation audit from SINCE (default: full history)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    if args.stats:
        log.info("corporate_actions: %s", table_stats())
        return
    if args.reconcile:
        with get_conn() as conn:
            rec = reconcile(conn, since=args.reconcile)
        print("reconcile since %s: %d groups -> %s" % (args.reconcile, rec["groups"], rec["counts"]))
        for k in ("MISSED_DEAD_ZONE", "TAPE_SUSPECT"):
            if rec["detail"][k]:
                print("  %s (%d): %s" % (k, len(rec["detail"][k]), rec["detail"][k][:12]))
        return
    today = date.today().isoformat()
    if args.window:
        ingest_range(args.window[0], args.window[1])
    elif args.backfill:
        ingest_range("%d-01-01" % args.from_year, today)
    else:                                               # bare call == --fetch (full-backfill.sh compat)
        ingest_range((date.today() - timedelta(days=args.days)).isoformat(), today)
    log.info("corporate_actions: %s", table_stats())


if __name__ == "__main__":
    main()
