"""seasonal_events — standalone event-cadence engine (descriptive-factual, OUTSIDE the two frozen
seasonal_tape z-families). NOT part of the 'seasonal_tape' / 'seasonal_tape_stock' pre-registered
statistical families: no prereg, no MECHANISMS/GATES import, no z-score, no COLORED/greyed
certification. This module answers a plain factual question per entity —

    "when did RESULTS/DIVIDEND/BONUS/SPLIT/AGM/other-corp-action events actually happen, what is
     this entity's own historical cadence for each, and is the next one on-time / overdue?"

— using only TIME (weeks), never price or forward-return. Descriptive-only fence: no
expected-move/forward-return column is computed or stored anywhere in this module.

SOURCES (every read is table-exists-guarded — a missing table degrades to [], never an exception;
these tables are 0-row on a laptop dev box, populated only on the VPS):
  * concalls               — RESULTS clock = COALESCE(result_filing_dt, concall_dt,
                              transcript_publish_dt); the REAL public clock when captured (S84 BSE
                              calibration). When none of those three parse, falls back to the
                              calendar month-end of period_label (e.g. "Apr 2026" -> 2026-04-30),
                              FLAGGED modeled=1 — never silently treated as real.
  * corporate_actions      — DIVIDEND / BONUS / SPLIT by action_type; ex_date is the clock (this
                              table's own EVENT-basis real column per provenance.py's 'corp_action'
                              descriptor). Everything else (DEMERGER/CONSOLIDATION/OTHER/...) buckets
                              into OTHER_CA.
  * security_events        — a second, independent record of the same kinds of actions; merged with
                              corporate_actions and DEDUPED by (bucket, ex_date) so a single real
                              action is never double-counted.
  * board_meetings         — (a) is_results=1 rows are BOARD-DECLARED results dates (an exchange
                              intimation filed ahead of the meeting — the single most reliable
                              forward anchor when present); (b) rows whose purpose mentions
                              AGM/Annual General Meeting feed the AGM event type (NSE event-calendar
                              coverage of AGMs is sparse/inconsistent — flagged low_coverage, never
                              faked as complete).

PIT / leak-free discipline: every occurrence carries a `knowable_at` (defaults to its own real
clock date; optionally tightened via research.db.provenance_knowable when research_conn is passed
and a stricter capture timestamp has accrued there — a no-op when no such row exists, which is the
common case since these are already EVENT-basis tables with real clock columns per provenance.py).
compute_events() is MANDATORY-gated: an occurrence only counts toward the cadence fit / the overdue
read when knowable_at < asof. A `declared` board-meeting anchor is itself gated on fetched_at < asof
(the intimation must have been public knowledge as-of the query date, not merely dated in the past).

CADENCE MODEL: circular (day-of-year for annual events; day-of-quarter for quarterly RESULTS) mean
+ MAD*1.4826 sigma (floored), fit on strictly-PAST occurrences only. The next window is placed
chronologically after the most recent occurrence. expected_vs_actual() then classifies that window
against real occurrences (and an optional declared date) into ON_TIME / EARLY / LATE / OVERDUE /
PENDING / NO_HISTORY, with a SIGNED weeks variance (negative = late/overdue, positive = early).

Run:
  python -m src.automation.seasonal_events                 # offline synthetic selftest
  python -m src.automation.seasonal_events --backfill SYM [SYM...]   # persist summary (VPS)
  python -m src.automation.seasonal_events --stats
"""
from __future__ import annotations

import argparse
import calendar
import math
import os
import sqlite3
import statistics
from datetime import date, timedelta

EVENT_TYPES = ["RESULTS", "DIVIDEND", "BONUS", "SPLIT", "AGM", "OTHER_CA"]

_CA_BUCKET = {"DIVIDEND": "DIVIDEND", "BONUS": "BONUS", "SPLIT": "SPLIT"}   # else -> OTHER_CA

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# best-effort research.db.provenance_knowable data-class candidates per event type (used ONLY to
# TIGHTEN knowable_at further when such a row has accrued there; every source table here is already
# EVENT-basis with its own real clock column, so this is usually a no-op — kept defensive per spec).
_PROV_CANDIDATES = {
    "RESULTS": ("concall_corpus", "concall_results"),
    "DIVIDEND": ("corp_action",), "BONUS": ("corp_action",), "SPLIT": ("corp_action",),
    "OTHER_CA": ("corp_action",), "AGM": ("board_meetings",),
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seasonal_events (
  symbol         TEXT NOT NULL,
  event_type     TEXT NOT NULL,
  asof           TEXT NOT NULL,
  status         TEXT,
  variance_weeks REAL,
  anchor         TEXT,
  anchor_basis   TEXT,
  lo             TEXT,
  hi             TEXT,
  mu_date        TEXT,
  sigma_days     REAL,
  k              INTEGER,
  n              INTEGER,
  n_history      INTEGER,
  modeled        INTEGER DEFAULT 0,
  computed_at    TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (symbol, event_type, asof)
);
CREATE INDEX IF NOT EXISTS idx_sev_sym ON seasonal_events(symbol, event_type);
"""


# --------------------------------------------------------------------------- #
#  defensive DB helpers (table-exists-guarded: any sqlite error -> [])         #
# --------------------------------------------------------------------------- #

def _dictrows(conn, sql: str, params: tuple = ()) -> list:
    """SELECT -> list[dict], regardless of the caller's row_factory. Any sqlite error (missing
    table/column on a stub/local DB) degrades to [] — never raises."""
    try:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except sqlite3.Error:
        return []


def _table_exists(conn, name: str) -> bool:
    try:
        return bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())
    except sqlite3.Error:
        return False


def _iso(s) -> str | None:
    if not s:
        return None
    t = str(s).strip()[:10]
    try:
        date.fromisoformat(t)
        return t
    except ValueError:
        return None


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _month_end_from_label(label) -> str | None:
    """'Apr 2026' -> '2026-04-30' (Screener-style period_label). None if unparseable."""
    parts = str(label or "").strip().split()
    if len(parts) != 2:
        return None
    mon = _MONTHS.get(parts[0][:3].lower())
    if not mon:
        return None
    try:
        yr = int(parts[1])
    except ValueError:
        return None
    return date(yr, mon, calendar.monthrange(yr, mon)[1]).isoformat()


def _tighter_knowable(research_conn, event_type: str, symbol: str, occ_date: str) -> str:
    """Best-effort extra PIT tightening via research.db.provenance_knowable — returns occ_date
    unchanged (the natural EVENT-basis clock) unless a stricter capture row is found there."""
    if research_conn is None:
        return occ_date
    if not _table_exists(research_conn, "provenance_knowable"):
        return occ_date
    best = occ_date
    for dc in _PROV_CANDIDATES.get(event_type, ()):
        rows = _dictrows(research_conn,
                          "SELECT knowable_at FROM provenance_knowable WHERE data_class=? AND key LIKE ?",
                          (dc, f"{symbol}|%"))
        for r in rows:
            k = _iso(r.get("knowable_at"))
            if k and k > best:
                best = k
    return best


# --------------------------------------------------------------------------- #
#  per-source loaders (table-exists-guarded)                                  #
# --------------------------------------------------------------------------- #

def _load_results(rconn, symbol: str) -> list:
    rows = _dictrows(rconn,
        "SELECT period_label, result_filing_dt, concall_dt, transcript_publish_dt "
        "FROM concalls WHERE symbol=?", (symbol,))
    out, seen = [], set()
    for r in rows:
        real = _iso(r.get("result_filing_dt")) or _iso(r.get("concall_dt")) or _iso(r.get("transcript_publish_dt"))
        modeled = 0
        occ = real
        if occ is None:
            occ = _month_end_from_label(r.get("period_label"))
            modeled = 1
        if occ is None or occ in seen:
            continue
        seen.add(occ)
        out.append({"occ_date": occ, "modeled": modeled, "source": "concalls",
                    "period_label": r.get("period_label")})
    out.sort(key=lambda d: d["occ_date"])
    return out


def _load_corp_actions(rconn, symbol: str) -> dict:
    """DIVIDEND/BONUS/SPLIT/OTHER_CA from corporate_actions.ex_date by action_type, MERGED with
    security_events and DEDUPED by (bucket, ex_date) — a single real action never double-counted
    across the two independently-sourced tables."""
    buckets = {"DIVIDEND": [], "BONUS": [], "SPLIT": [], "OTHER_CA": []}
    seen = set()
    ca_rows = _dictrows(rconn,
        "SELECT action_type, ex_date FROM corporate_actions WHERE symbol=? AND ex_date IS NOT NULL",
        (symbol,))
    for r in ca_rows:
        ex = _iso(r.get("ex_date"))
        if not ex:
            continue
        bucket = _CA_BUCKET.get(str(r.get("action_type") or "").upper(), "OTHER_CA")
        key = (bucket, ex)
        if key in seen:
            continue
        seen.add(key)
        buckets[bucket].append({"occ_date": ex, "modeled": 0, "source": "corporate_actions"})

    se_rows = _dictrows(rconn,
        "SELECT event_type, ex_date FROM security_events WHERE symbol=? AND ex_date IS NOT NULL",
        (symbol,))
    for r in se_rows:
        ex = _iso(r.get("ex_date"))
        if not ex:
            continue
        bucket = _CA_BUCKET.get(str(r.get("event_type") or "").upper(), "OTHER_CA")
        key = (bucket, ex)
        if key in seen:      # already captured via corporate_actions
            continue
        seen.add(key)
        buckets[bucket].append({"occ_date": ex, "modeled": 0, "source": "security_events"})

    for b in buckets.values():
        b.sort(key=lambda d: d["occ_date"])
    return buckets


def _load_agm(rconn, symbol: str) -> list:
    """AGM occurrences from board_meetings whose purpose mentions AGM/Annual General Meeting.
    NSE event-calendar coverage of AGMs (vs results BMs) is thin/inconsistent — LOW_COVERAGE
    flagged on every row, never treated as a complete record."""
    rows = _dictrows(rconn, "SELECT meeting_date, purpose FROM board_meetings WHERE symbol=?", (symbol,))
    out = []
    for r in rows:
        purpose = str(r.get("purpose") or "").upper()
        if "AGM" not in purpose and "ANNUAL GENERAL MEETING" not in purpose:
            continue
        d = _iso(r.get("meeting_date"))
        if not d:
            continue
        out.append({"occ_date": d, "modeled": 0, "source": "board_meetings", "coverage": "low_coverage"})
    out.sort(key=lambda d: d["occ_date"])
    return out


def _next_declared_results(rconn, symbol: str, asof: str) -> str | None:
    """The board-declared results date (board_meetings.is_results=1) nearest ``asof`` — gated on
    fetched_at < asof (the intimation must have been public knowledge as-of the query date)."""
    rows = _dictrows(rconn,
        "SELECT meeting_date, fetched_at FROM board_meetings WHERE symbol=? AND is_results=1",
        (symbol,))
    cands = []
    for r in rows:
        d = _iso(r.get("meeting_date"))
        if not d:
            continue
        fa = _iso(r.get("fetched_at")) or d
        if fa >= asof:
            continue
        cands.append(d)
    if not cands:
        return None
    try:
        asof_d = date.fromisoformat(asof)
    except ValueError:
        return sorted(cands)[-1]
    return min(cands, key=lambda d: abs((date.fromisoformat(d) - asof_d).days))


def load_event_history(rconn, symbol: str, *, research_conn=None) -> dict:
    """{event_type: [occurrence dict, ...]} ascending by occ_date, each carrying `knowable_at`
    (>= occ_date; the PIT gate used downstream by compute_events)."""
    symbol = str(symbol or "").strip().upper()
    out = {et: [] for et in EVENT_TYPES}
    out["RESULTS"] = _load_results(rconn, symbol)
    ca = _load_corp_actions(rconn, symbol)
    out["DIVIDEND"], out["BONUS"], out["SPLIT"], out["OTHER_CA"] = (
        ca["DIVIDEND"], ca["BONUS"], ca["SPLIT"], ca["OTHER_CA"])
    out["AGM"] = _load_agm(rconn, symbol)
    for et, occs in out.items():
        for o in occs:
            o["knowable_at"] = _tighter_knowable(research_conn, et, symbol, o["occ_date"])
    return out


# --------------------------------------------------------------------------- #
#  pure-Python cadence core (no DB; selftested offline)                       #
# --------------------------------------------------------------------------- #

def _cycle_len(cadence: str) -> float:
    return 365.25 / 4.0 if cadence == "quarterly" else 365.25


def _phase(d: date, cadence: str) -> float:
    if cadence == "quarterly":
        q_start_month = ((d.month - 1) // 3) * 3 + 1
        q_start = date(d.year, q_start_month, 1)
        return float((d - q_start).days)
    return float((d - date(d.year, 1, 1)).days)


def _circular_stats(values: list, cycle_len: float) -> tuple:
    n = len(values)
    sin_s = sum(math.sin(2 * math.pi * v / cycle_len) for v in values)
    cos_s = sum(math.cos(2 * math.pi * v / cycle_len) for v in values)
    mean_angle = math.atan2(sin_s, cos_s)
    mu = (mean_angle / (2 * math.pi)) * cycle_len
    if mu < 0:
        mu += cycle_len
    devs = []
    for v in values:
        diff = abs(v - mu) % cycle_len
        devs.append(min(diff, cycle_len - diff))
    mad = statistics.median(devs) if devs else 0.0
    sigma = max(mad * 1.4826, 1.0)          # floored: a single day of slop is always plausible
    return mu, sigma


def _place_after(anchor: date, mu_phase: float, cadence: str, cycle_len: float) -> date | None:
    """The first calendar date strictly after ``anchor`` whose cycle-phase == mu_phase (bounded
    search, a few years of cycles)."""
    if cadence == "quarterly":
        q_idx = (anchor.month - 1) // 3
        yr, q = anchor.year, q_idx
        for _ in range(32):                  # 8 years of quarters
            q_start = date(yr, q * 3 + 1, 1)
            cand = q_start + timedelta(days=mu_phase)
            if cand > anchor:
                return cand
            q += 1
            if q > 3:
                q = 0
                yr += 1
        return None
    yr = anchor.year
    for _ in range(8):
        cand = date(yr, 1, 1) + timedelta(days=mu_phase)
        if cand > anchor:
            return cand
        yr += 1
    return None


def project_next_window(occurrences: list, asof: str, cadence: str, *,
                         min_hist: int = 3, grace_days: int = 9) -> dict | None:
    """PAST-ONLY circular (day-of-year annual / day-of-quarter quarterly) mean + MAD*1.4826 sigma
    (floored) over ``occurrences`` (ISO date strings, already knowable_at < asof by the caller).
    Returns {mu_date, sigma_days, lo, hi, k, n} for the FIRST window strictly after the most recent
    occurrence, or None when fewer than ``min_hist`` occurrences exist."""
    dates = sorted({_iso(o) for o in occurrences if _iso(o)})
    if len(dates) < min_hist:
        return None
    d_objs = [date.fromisoformat(d) for d in dates]
    cycle_len = _cycle_len(cadence)
    phases = [_phase(d, cadence) for d in d_objs]
    mu_phase, sigma_days = _circular_stats(phases, cycle_len)
    mu_date = _place_after(d_objs[-1], mu_phase, cadence, cycle_len)
    if mu_date is None:
        return None
    span = timedelta(days=sigma_days + grace_days)
    lo, hi = mu_date - span, mu_date + span
    n = len(dates)
    return {"mu_date": mu_date.isoformat(), "sigma_days": round(sigma_days, 2),
            "lo": lo.isoformat(), "hi": hi.isoformat(), "k": n, "n": n}


def _weeks(days: int) -> float:
    return round(days / 7.0, 2)


def expected_vs_actual(projection: dict | None, actuals: list, asof: str, *,
                        declared: str | None = None) -> dict:
    """Classify the next expected window against real occurrences (+ an optional board-declared
    anchor, which takes precedence). Search for a matching actual is bounded to a neighbourhood
    around [lo, hi] (radius derived from sigma, else a fixed 45d) so unrelated OLDER cycles already
    folded into the cadence fit can never masquerade as this cycle's EARLY/LATE actual.

    Statuses: ON_TIME (actual inside [lo,hi]) / EARLY (actual just before lo, positive weeks) /
    LATE (actual just after hi, negative weeks) / OVERDUE (window passed, nothing found in
    [lo,asof], negative weeks) / PENDING (window still open, nothing found yet) / NO_HISTORY
    (neither a declared anchor nor a projection exists)."""
    if not declared and not projection:
        return {"status": "NO_HISTORY", "variance_weeks": None, "anchor": None,
                "lo": None, "hi": None, "anchor_basis": "none"}

    if declared:
        anchor_basis = "declared"
        sigma = float(projection.get("sigma_days", 0.0)) if projection else 0.0
        anchor_d = date.fromisoformat(declared)
        lo_d, hi_d = anchor_d - timedelta(days=sigma), anchor_d + timedelta(days=sigma)
        radius = max(sigma * 4, 45.0)
    else:
        anchor_basis = "projection"
        anchor_d = date.fromisoformat(projection["mu_date"])
        lo_d = date.fromisoformat(projection["lo"])
        hi_d = date.fromisoformat(projection["hi"])
        radius = max(float(projection.get("sigma_days", 0.0)) * 4, 30.0)

    asof_d = date.fromisoformat(str(asof)[:10])
    before, after, in_window = None, None, None
    for a in sorted({_iso(x) for x in (actuals or []) if _iso(x)}):
        ad = date.fromisoformat(a)
        if lo_d <= ad <= hi_d:
            in_window = ad
        elif (lo_d - timedelta(days=radius)) <= ad < lo_d:
            if before is None or ad > before:
                before = ad
        elif hi_d < ad <= (hi_d + timedelta(days=radius)):
            if after is None or ad < after:
                after = ad

    base = {"anchor": anchor_d.isoformat(), "lo": lo_d.isoformat(), "hi": hi_d.isoformat(),
            "anchor_basis": anchor_basis}
    if in_window is not None:
        base.update(status="ON_TIME", variance_weeks=_weeks((in_window - anchor_d).days))
    elif after is not None:
        base.update(status="LATE", variance_weeks=-_weeks((after - hi_d).days))
    elif before is not None:
        base.update(status="EARLY", variance_weeks=_weeks((lo_d - before).days))
    elif asof_d > hi_d:
        base.update(status="OVERDUE", variance_weeks=-_weeks((asof_d - hi_d).days))
    else:
        base.update(status="PENDING", variance_weeks=None)
    return base


# --------------------------------------------------------------------------- #
#  compute + bounded persistence                                              #
# --------------------------------------------------------------------------- #

def compute_events(rconn, symbol: str, asof: str, *, research_conn=None) -> dict:
    """{symbol, asof, events: {event_type: expected_vs_actual()-shaped dict + event_type/n_history/
    modeled}}. knowable_at gating is MANDATORY here: an occurrence only feeds the cadence fit / the
    overdue read when its knowable_at < asof (leak-free for any historical asof, not just 'today')."""
    symbol = str(symbol or "").strip().upper()
    asof = str(asof)[:10]
    hist = load_event_history(rconn, symbol, research_conn=research_conn)
    declared = _next_declared_results(rconn, symbol, asof)
    out = {"symbol": symbol, "asof": asof, "events": {}}
    for et in EVENT_TYPES:
        raw = hist.get(et, [])
        occs = sorted({o["knowable_at"] for o in raw if o.get("knowable_at") and o["knowable_at"] < asof})
        cadence = "quarterly" if et == "RESULTS" else "annual"
        proj = project_next_window(occs, asof, cadence)
        decl = declared if et == "RESULTS" else None
        ev = expected_vs_actual(proj, occs, asof, declared=decl)
        ev["event_type"] = et
        ev["n_history"] = len(occs)
        ev["modeled"] = 1 if any(o.get("modeled") and o["knowable_at"] in occs for o in raw) else 0
        out["events"][et] = ev
    return out


def backfill_events(read_path: str, write_path: str, symbols: list, asof: str | None = None) -> dict:
    """Compute + persist the bounded PROJECTION+VARIANCE SUMMARY only (per-occurrence tape is
    derivable from the source tables and is NEVER persisted — space mandate). Self-creating schema;
    per-symbol commit keeps the write-lock short (writer-safe, matches the seasonal_tape house
    pattern). Read-only on the archive."""
    asof = str(asof)[:10] if asof else date.today().isoformat()
    rconn = _ro(read_path)
    research_conn = None
    try:
        rdb = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")
        if os.path.exists(rdb):
            research_conn = _ro(rdb)
    except sqlite3.Error:
        research_conn = None
    wconn = sqlite3.connect(write_path, timeout=60)
    wconn.executescript(_SCHEMA)
    wconn.commit()
    counts = {"symbols": 0, "rows": 0, "overdue": 0}
    try:
        for sym in symbols:
            payload = compute_events(rconn, sym, asof, research_conn=research_conn)
            rows = []
            for et, ev in payload["events"].items():
                rows.append((payload["symbol"], et, asof, ev.get("status"), ev.get("variance_weeks"),
                             ev.get("anchor"), ev.get("anchor_basis"), ev.get("lo"), ev.get("hi"),
                             (ev.get("mu_date") if ev.get("anchor_basis") == "projection" else None),
                             None, None, ev.get("n_history"), ev.get("n_history"), ev.get("modeled", 0)))
                if ev.get("status") == "OVERDUE":
                    counts["overdue"] += 1
            wconn.executemany(
                "INSERT OR REPLACE INTO seasonal_events (symbol,event_type,asof,status,"
                "variance_weeks,anchor,anchor_basis,lo,hi,mu_date,sigma_days,k,n,n_history,modeled) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            wconn.commit()
            counts["symbols"] += 1
            counts["rows"] += len(rows)
    finally:
        rconn.close(); wconn.close()
        if research_conn is not None:
            research_conn.close()
    return counts


def stats(path: str) -> dict:
    con = _ro(path)
    try:
        if not _table_exists(con, "seasonal_events"):
            return {"present": False}
        row = con.execute(
            "SELECT COUNT(DISTINCT symbol), COUNT(*), SUM(status='OVERDUE') FROM seasonal_events").fetchone()
        by_status = {r[0]: r[1] for r in con.execute(
            "SELECT status, COUNT(*) FROM seasonal_events GROUP BY status")}
        return {"present": True, "symbols": row[0], "rows": row[1], "overdue": row[2] or 0,
                "by_status": by_status}
    finally:
        con.close()


# --------------------------------------------------------------------------- #
#  offline synthetic selftest                                                 #
# --------------------------------------------------------------------------- #

def _selftest() -> int:
    def check(label, cond):
        status = "OK" if cond else "FAIL"
        print(f"  [{status}] {label}")
        if not cond:
            raise AssertionError(label)

    # ---- synthetic quarterly RESULTS cadence: files ~45 days into each quarter, 4y history ----
    hist = []
    for yr in range(2022, 2026):
        for q_start_month in (1, 4, 7, 10):
            hist.append((date(yr, q_start_month, 1) + timedelta(days=45)).isoformat())
    hist.sort()
    last = date.fromisoformat(hist[-1])
    asof = (last + timedelta(days=140)).isoformat()      # well past the next expected window

    proj = project_next_window(hist, asof, "quarterly", min_hist=3)
    check("quarterly projection built from 16 quarters", proj is not None)
    check("sigma floored at >=1 day (near-zero jitter)", proj["sigma_days"] >= 1.0)

    ev = expected_vs_actual(proj, hist, asof)
    check("passed window + no actual -> OVERDUE", ev["status"] == "OVERDUE")
    check("OVERDUE variance_weeks is negative", ev["variance_weeks"] is not None and ev["variance_weeks"] < 0)

    # ---- NO_HISTORY: fewer than min_hist occurrences, no declared anchor ----
    proj2 = project_next_window(hist[:2], asof, "annual", min_hist=3)
    check("insufficient history -> no projection", proj2 is None)
    ev2 = expected_vs_actual(proj2, hist[:2], asof)
    check("no projection + no declared -> NO_HISTORY", ev2["status"] == "NO_HISTORY")
    check("NO_HISTORY carries no variance", ev2["variance_weeks"] is None)

    # ---- month-end label fallback (modeled=1, never faked as real) ----
    check("period_label month-end parse", _month_end_from_label("Apr 2026") == "2026-04-30")
    check("bad label -> None (no fake date)", _month_end_from_label("garbage") is None)

    # ---- ON_TIME via a declared anchor with a matching actual ----
    ev3 = expected_vs_actual(None, ["2026-07-18"], "2026-07-20", declared="2026-07-18")
    check("declared anchor + matching actual -> ON_TIME", ev3["status"] == "ON_TIME")

    print("seasonal_events selftest: OK (OVERDUE negative-variance + NO_HISTORY + label-fallback + declared ON_TIME)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--backfill", nargs="+", metavar="SYMBOL")
    ap.add_argument("--backfill-all", action="store_true",
                    help="refresh the event cadence for the ENTIRE all-EQ universe "
                         "(stock_universe_all — the seasonal_tape_stock_all cohort); the nightly path")
    ap.add_argument("--asof")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    if a.backfill_all:
        # Derive the universe internally so the systemd ExecStart never has to pass ~2,400 argv
        # (matches the seasonal_tape_stock_all cohort exactly — same read-only liquidity rank).
        from src.core.db import DB_PATH
        from src.automation.seasonal_tape import stock_universe_all
        rc = _ro(str(DB_PATH))
        try:
            syms = stock_universe_all(rc)
        finally:
            rc.close()
        print({"universe": len(syms), **backfill_events(str(DB_PATH), str(DB_PATH), syms, asof=a.asof)})
    elif a.backfill:
        from src.core.db import DB_PATH
        print(backfill_events(str(DB_PATH), str(DB_PATH), a.backfill, asof=a.asof))
    elif a.stats:
        from src.core.db import DB_PATH
        print(stats(str(DB_PATH)))
    else:
        raise SystemExit(_selftest())


if __name__ == "__main__":
    main()
