"""Fundamentals filing-date backfill — REAL knowable_at from BSE result announcements.

``fundamentals_history`` stamps a MODELED ``report_date = period_end + 90d (annual) / 50d
(quarterly)`` — a synthetic uniform lag parsed only from Screener column headers
(``fundamentals_history._period_to_dates``). A modelled date LEAKS look-ahead for late
filers (the real number wasn't public yet) and is over-conservative for early ones. It is
the only "PIT" date back-history has today.

This module captures the **REAL** date each result was filed with the exchange — BSE
corporate announcements, category=Result, whose ``NEWS_DT`` is the actual filing timestamp.
That is the ONLY way to RETROACTIVELY de-model the existing ~1,983-symbol × 24y archive
(forward-only ``provenance.observe()`` from the ingest path can only de-model data ingested
from switch-on; it can never reach back).

Isolation (the house pattern — see ``provenance.py`` / ``security_master.py``):
  * Writes NOTHING into ``fundamentals_history`` and never edits the collector
    (``fundamentals_history.py`` is parallel-owned). It only feeds ``provenance.observe()``:
    the real date lands in ``provenance_knowable`` under the canonical
    ``provenance.period_key(symbol, period_type, period_end)``, and ``provenance_for()``
    then prefers it over the modelled date automatically.
  * OWNS one table, ``bse_scrip_map`` (NSE symbol → BSE scrip code), via an embedded schema.
  * After a backfill, ``provenance.lag_audit()`` measures ``(real − modelled)`` — exactly the
    look-ahead the modelling was injecting.

Coverage limiter = the symbol→scripcode map (BSE uses numeric scrip codes); BSE's corporate
archive itself reaches back to **2006**, so pre-2006 annual history stays MODELED.

Reuses the proven BSE access pattern from ``concalls.py`` (browser UA + Referer, paced
requests). Pure stdlib + requests + the project's provenance API; NO LLM. Defensive: every
network / research.db path degrades to a graceful no-op when absent (laptop / fresh box), so
the offline ``--selftest`` runs the whole parse+match+observe core with zero I/O.

CLI:
    python -m src.automation.fundamentals_filing_dates --selftest            # offline, synthetic
    python -m src.automation.fundamentals_filing_dates --seed-scrips f.csv   # symbol,scripcode[,isin] CSV
    python -m src.automation.fundamentals_filing_dates --backfill RELIANCE   # one symbol (VPS)
    python -m src.automation.fundamentals_filing_dates --backfill-universe    # all mapped symbols (VPS)
    python -m src.automation.fundamentals_filing_dates --lag-report          # provenance.lag_audit() digest
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from src.automation import provenance

log = logging.getLogger("hermes.filing_dates")

# BSE wants a browser UA + Referer or it 403s (same contract concalls.py proved).
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.bseindia.com/corporates/ann.html",
    "Accept": "application/json, text/plain, */*",
}
ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
BSE_ARCHIVE_FLOOR = "2006-01-01"     # BSE corporate-announcement archive depth (official)
REQUEST_PAUSE = 1.5                   # politeness between BSE hits
DATA_CLASS = "fundamentals_history"
SOURCE_NOTE = "BSE-AnnGetData"

# A result for period_end P is filed at F with F − P in roughly this window (SEBI LODR
# Reg 33: 45d quarterly / 60d annual; plus slack for late filers). Used by the
# date-heuristic fallback ONLY, and only when it is UNAMBIGUOUS.
MIN_LAG_DAYS = 20
MAX_LAG_DAYS = 200

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MONTH_RE = "|".join(_MONTHS)


# ── owned table: NSE symbol → BSE scrip code ──────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS bse_scrip_map (
    symbol      TEXT PRIMARY KEY,
    scripcode   TEXT NOT NULL,
    security_id TEXT,
    isin        TEXT,
    source      TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_scrip_isin ON bse_scrip_map(isin);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


# ── pure parse helpers (fully offline-testable) ───────────────────────────────
def _qend(year: int, month: int) -> str:
    """The calendar period-end date for a (year, month) — last day of the month."""
    import calendar
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def parse_filing_dt(raw: Optional[str]) -> Optional[str]:
    """BSE ``NEWS_DT`` → 'YYYY-MM-DD'. Tolerates the several shapes BSE returns
    ('2024-07-19T18:30:00', '2024-07-19 18:30:00.000', '19 Jul 2024 18:30:00')."""
    if not raw:
        return None
    s = str(raw).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)            # ISO-ish (most common)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\s+(\d{4})", s)   # '19 Jul 2024'
    if m and m.group(2).lower() in _MONTHS:
        return _date_iso(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def _date_iso(y: int, mo: int, d: int) -> Optional[str]:
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def _find_date_in(text: str) -> Optional[str]:
    """First explicit calendar date in a result-announcement subject → 'YYYY-MM-DD'."""
    t = text
    # 'March 31, 2024' | 'June 30 2024'
    m = re.search(rf"({_MONTH_RE})[a-z]*\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})", t, re.I)
    if m:
        return _date_iso(int(m.group(3)), _MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
    # '31st March, 2024' | '30 June 2024'
    m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})[a-z]*\.?,?\s+(\d{{4}})", t, re.I)
    if m:
        return _date_iso(int(m.group(3)), _MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
    # '31.03.2024' | '30/06/2024'
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", t)
    if m:
        return _date_iso(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def _fy_quarter_end(q: int, fy_end_year: int) -> Optional[str]:
    """'Q<q> FY<fy_end_year>' (Indian FY, Apr-Mar; FY named by its Mar-end year) → period_end.
    Q1→Jun(fy-1), Q2→Sep(fy-1), Q3→Dec(fy-1), Q4→Mar(fy)."""
    return {1: lambda: _qend(fy_end_year - 1, 6), 2: lambda: _qend(fy_end_year - 1, 9),
            3: lambda: _qend(fy_end_year - 1, 12), 4: lambda: _qend(fy_end_year, 3)}.get(q, lambda: None)()


def is_results_filing(subject: str) -> bool:
    """True only for an ACTUAL results filing — not a board-meeting intimation
    ('...to consider...', '...will be held...') which precedes the numbers."""
    s = (subject or "").lower()
    if "result" not in s and "financial" not in s:
        return False
    if ("board meeting" in s or "intimation" in s) and \
       ("to consider" in s or "will be held" in s or "scheduled" in s):
        return False
    return True


def period_from_subject(subject: str) -> list:
    """Parse the reporting period(s) a result announcement covers → list of
    (period_type, period_end). 'quarter and year ended <date>' yields BOTH Q and A at
    that period_end (Q4 + annual audited are routinely filed together)."""
    if not subject:
        return []
    s = subject.lower()
    out: list = []

    # 'Q<n> FY<yy(yy)>' or the start-end form 'Q<n> FY2024-25' / 'FY24-25' (the FY is named
    # by its Mar-END year, so the SECOND token wins when a range is given).
    m = re.search(r"\bq([1-4])\s*fy\s*'?(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?", s)
    if m:
        q = int(m.group(1))
        yr = int(m.group(3) or m.group(2)); yr = yr + 2000 if yr < 100 else yr
        pe = _fy_quarter_end(q, yr)
        if pe:
            return [("Q", pe)]

    pe = _find_date_in(subject)
    if pe:
        has_q = "quarter" in s or "qtr" in s
        has_y = "year ended" in s or "annual" in s or "year end" in s or "full year" in s
        if has_q:
            out.append(("Q", pe))
        if has_y:
            out.append(("A", pe))
        if not out:               # date present but neither word — assume quarterly (the common case)
            out.append(("Q", pe))
    return out


def choose_periods(subject: str, filing_date: Optional[str], candidates: set) -> list:
    """Decide which of a symbol's known (period_type, period_end) ``candidates`` this
    announcement settles. Headline-first (precise); a STRICT date-heuristic fallback only
    when exactly one candidate sits in the regulatory window (else leave it MODELED — an
    ambiguous guess would be worse than honest silence). Returns matched candidates."""
    targets = [(pt, pe) for (pt, pe) in period_from_subject(subject) if (pt, pe) in candidates]
    if targets:
        return targets
    if not filing_date:
        return []
    try:
        f = date.fromisoformat(filing_date)
    except ValueError:
        return []
    in_window = [(pt, pe) for (pt, pe) in candidates
                 if (lambda g: MIN_LAG_DAYS <= g <= MAX_LAG_DAYS)((f - date.fromisoformat(pe)).days)]
    distinct_ends = {pe for _, pe in in_window}
    return in_window if len(distinct_ends) == 1 else []   # unambiguous only


# ── candidate periods from the (read-only) fundamentals archive ───────────────
def candidate_periods(symbol: str, research_conn) -> set:
    """The (period_type, period_end) set already stored for ``symbol`` — the universe of
    periods a real filing date could de-model. Empty/None-safe."""
    if research_conn is None:
        return set()
    try:
        return {(r[0], r[1]) for r in research_conn.execute(
            "SELECT DISTINCT period_type, period_end FROM fundamentals_history WHERE symbol=?", (symbol,))}
    except sqlite3.Error:
        return set()


# ── scrip-code map (the coverage limiter) ─────────────────────────────────────
def seed_scrip_map_from_csv(path: str, conn) -> int:
    """Seed bse_scrip_map from a CSV with headers symbol,scripcode[,security_id,isin].
    Robust primary path — BSE publishes downloadable scrip lists, and ISIN lets us join
    even renamed names."""
    ensure_schema(conn)
    n = 0
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("symbol") or row.get("Symbol") or "").strip().upper()
            code = (row.get("scripcode") or row.get("Scrip Code") or row.get("SC_CODE") or "").strip()
            if not sym or not code:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO bse_scrip_map (symbol, scripcode, security_id, isin, source) "
                "VALUES (?,?,?,?, 'csv')",
                (sym, code, (row.get("security_id") or row.get("SC_NAME") or "").strip() or None,
                 (row.get("isin") or row.get("ISIN") or "").strip().upper() or None))
            n += 1
    conn.commit()
    return n


def resolve_scripcode(symbol: str, conn) -> Optional[str]:
    """NSE symbol → BSE scrip code from the owned map (None if unmapped → caller skips +
    counts it; that is the disclosed coverage gap, never a silent wrong match)."""
    try:
        r = conn.execute("SELECT scripcode FROM bse_scrip_map WHERE symbol=?", (symbol.upper(),)).fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None


# ── BSE fetch (network; not exercised by --selftest) ──────────────────────────
def fetch_result_announcements(scripcode: str, from_date: str, to_date: str,
                               session: Optional[requests.Session] = None) -> list:
    """All category=Result announcements for a scrip in [from_date, to_date] (ISO dates).
    Returns the raw row dicts (defensive: [] on any failure). Paginates BSE's response."""
    sess = session or requests
    out: list = []
    f = from_date.replace("-", ""); t = to_date.replace("-", "")
    for page in range(1, 51):                       # hard page cap (safety)
        params = {"strCat": "Result", "strPrevDate": f, "strToDate": t,
                  "strScrip": scripcode, "strSearch": "P", "strType": "C", "pageno": page}
        try:
            r = requests.get(ANN_URL, headers=BSE_HEADERS, params=params, timeout=30) \
                if session is None else sess.get(ANN_URL, headers=BSE_HEADERS, params=params, timeout=30)
            if r.status_code != 200:
                break
            rows = (r.json() or {}).get("Table") or []
        except (requests.RequestException, ValueError) as e:
            log.warning("BSE ann fetch %s p%d: %s", scripcode, page, e)
            break
        if not rows:
            break
        out.extend(rows)
        time.sleep(REQUEST_PAUSE)
    return out


def _ann_subject(row: dict) -> str:
    return str(row.get("HEADLINE") or row.get("NEWSSUB") or row.get("News_submission_dt") or "")


def _ann_dt(row: dict) -> Optional[str]:
    return parse_filing_dt(row.get("NEWS_DT") or row.get("DT_TM") or row.get("News_submission_dt"))


# ── apply: matched (period -> filing_date) → provenance.observe() ─────────────
def apply_matches(symbol: str, matches: dict, conn) -> int:
    """Record real filing dates. ``matches`` = {(period_type, period_end): filing_date}.
    Uses provenance.observe() under the canonical period_key so provenance_for() can read
    it back; observe() is INSERT-OR-IGNORE so the EARLIEST date per period is preserved.
    Returns # newly captured."""
    n = 0
    for (ptype, pend), fdate in matches.items():
        key = provenance.period_key(symbol, ptype, pend)
        if provenance.observe(DATA_CLASS, key, conn=conn, symbol=symbol,
                              knowable_at=fdate, source_note=SOURCE_NOTE):
            n += 1
    return n


def match_announcements(symbol: str, anns: list, candidates: set) -> dict:
    """Reduce a symbol's result announcements to {(ptype, period_end): earliest filing_date}
    over its known candidate periods. Pure — no I/O, the offline-tested heart of the module."""
    matches: dict = {}
    for row in anns:
        subj = _ann_subject(row)
        if not is_results_filing(subj):
            continue
        fdate = _ann_dt(row)
        if not fdate:
            continue
        for (pt, pe) in choose_periods(subj, fdate, candidates):
            cur = matches.get((pt, pe))
            if cur is None or fdate < cur:          # keep the earliest filing for the period
                matches[(pt, pe)] = fdate
    return matches


def backfill_symbol(symbol: str, conn, research_conn, *, session=None) -> dict:
    """De-model one symbol: candidate periods (research.db, RO) × BSE result announcements
    → real filing dates → provenance.observe(). Returns a stats dict; never raises."""
    symbol = symbol.upper().strip()
    stats = {"symbol": symbol, "candidates": 0, "announcements": 0, "matched": 0, "captured": 0}
    cands = candidate_periods(symbol, research_conn)
    stats["candidates"] = len(cands)
    if not cands:
        stats["skip"] = "no_archive_periods"
        return stats
    code = resolve_scripcode(symbol, conn)
    if not code:
        stats["skip"] = "no_scripcode"
        return stats
    floor = max(BSE_ARCHIVE_FLOOR, min(pe for _, pe in cands))
    to = max(pe for _, pe in cands)
    to = (date.fromisoformat(to) + timedelta(days=MAX_LAG_DAYS)).isoformat()
    anns = fetch_result_announcements(code, floor, to, session=session)
    stats["announcements"] = len(anns)
    matches = match_announcements(symbol, anns, cands)
    stats["matched"] = len(matches)
    stats["captured"] = apply_matches(symbol, matches, conn)
    return stats


def backfill_universe(limit: Optional[int] = None) -> dict:
    """Backfill every mapped symbol (VPS path). research.db RO + the main DB for the map +
    provenance writes. Degrades to a no-op if research.db is absent."""
    rconn = provenance._research_ro()
    if rconn is None:
        log.warning("research.db absent (%s) — nothing to backfill here.", provenance.RESEARCH_DB)
        return {"status": "research_db_absent"}
    totals = {"symbols": 0, "matched": 0, "captured": 0, "no_scripcode": 0}
    with provenance.get_conn() as conn:
        ensure_schema(conn)
        mapped = [r[0] for r in conn.execute("SELECT symbol FROM bse_scrip_map ORDER BY symbol")]
        if limit:
            mapped = mapped[:limit]
        sess = requests.Session()
        for i, sym in enumerate(mapped, 1):
            st = backfill_symbol(sym, conn, rconn, session=sess)
            totals["symbols"] += 1
            totals["matched"] += st.get("matched", 0)
            totals["captured"] += st.get("captured", 0)
            if st.get("skip") == "no_scripcode":
                totals["no_scripcode"] += 1
            if i % 50 == 0:
                log.info("backfill %d/%d: %s", i, len(mapped), totals)
            time.sleep(REQUEST_PAUSE)
    rconn.close()
    return totals


# ── offline selftest (no network, no research.db) ─────────────────────────────
def _selftest() -> None:
    # 1. filing-date parsing across BSE shapes
    assert parse_filing_dt("2024-07-19T18:30:00") == "2024-07-19"
    assert parse_filing_dt("2024-07-19 18:30:00.000") == "2024-07-19"
    assert parse_filing_dt("19 Jul 2024 18:30:00") == "2024-07-19"
    assert parse_filing_dt(None) is None and parse_filing_dt("garbage") is None

    # 2. subject → period(s)
    assert period_from_subject("Financial Results for the Quarter ended June 30, 2024") == [("Q", "2024-06-30")]
    assert set(period_from_subject("Audited Financial Results for the Quarter and Year Ended March 31, 2024")) == \
        {("Q", "2024-03-31"), ("A", "2024-03-31")}
    assert period_from_subject("Audited Financial Results for the year ended 31st March, 2023") == [("A", "2023-03-31")]
    assert period_from_subject("Outcome of Board Meeting - Results for Q1 FY2024-25") == [("Q", "2024-06-30")]
    assert period_from_subject("Results for the quarter ended 30.06.2024") == [("Q", "2024-06-30")]
    assert period_from_subject("Notice of Board Meeting") == []

    # 3. is_results_filing rejects the pre-announcement intimation
    assert is_results_filing("Financial Results for quarter ended June 30, 2024") is True
    assert is_results_filing("Board Meeting Intimation to consider unaudited results") is False

    # 4. choose_periods: headline match, dual Q4+annual, strict date-heuristic
    cands = {("Q", "2024-06-30"), ("Q", "2024-03-31"), ("A", "2024-03-31"), ("Q", "2023-12-31")}
    assert choose_periods("Results for the Quarter ended June 30, 2024", "2024-07-19", cands) == [("Q", "2024-06-30")]
    assert set(choose_periods("Quarter and Year Ended March 31, 2024", "2024-05-10", cands)) == \
        {("Q", "2024-03-31"), ("A", "2024-03-31")}
    # unparseable subject, filing ~45d after a single in-window quarter-end → heuristic fires
    assert choose_periods("Outcome of Board Meeting", "2024-08-14", {("Q", "2024-06-30")}) == [("Q", "2024-06-30")]
    # ambiguous (two distinct ends in window) → leave MODELED
    assert choose_periods("Outcome of Board Meeting", "2024-08-14",
                          {("Q", "2024-06-30"), ("Q", "2024-05-31")}) == []

    # 5. match_announcements keeps the EARLIEST filing per period and skips intimations
    anns = [
        {"HEADLINE": "Board Meeting Intimation to consider results", "NEWS_DT": "2024-07-01T10:00:00"},
        {"HEADLINE": "Financial Results for the Quarter ended June 30, 2024", "NEWS_DT": "2024-07-25T18:00:00"},
        {"HEADLINE": "Revised Financial Results for the Quarter ended June 30, 2024", "NEWS_DT": "2024-07-19T18:00:00"},
    ]
    m = match_announcements("RELIANCE", anns, {("Q", "2024-06-30")})
    assert m == {("Q", "2024-06-30"): "2024-07-19"}, m   # earliest of the two real filings, intimation ignored

    # 6. end-to-end: apply_matches → provenance_knowable, and provenance_for() flips to REAL
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    provenance.ensure_schema(conn)
    ensure_schema(conn)
    assert seed_via_rows([("RELIANCE", "500325", "INE002A01018")], conn) == 1
    assert resolve_scripcode("reliance", conn) == "500325"
    assert apply_matches("RELIANCE", {("Q", "2024-06-30"): "2024-07-19",
                                      ("A", "2024-03-31"): "2024-04-22"}, conn) == 2
    # canonical key round-trips through provenance_for (reader builds the SAME period_key)
    p = provenance.provenance_for(DATA_CLASS, symbol="RELIANCE", period_type="Q",
                                  as_of="2024-06-30", conn=conn)
    assert p["basis"] == provenance.INGESTED and p["as_of"] == "2024-07-19", p
    # annual vs quarterly at a shared period_end do NOT collide
    pa = provenance.provenance_for(DATA_CLASS, symbol="RELIANCE", period_type="A",
                                   as_of="2024-03-31", conn=conn)
    assert pa["as_of"] == "2024-04-22", pa
    # idempotent: re-applying a LATER date does not overwrite the earliest
    assert apply_matches("RELIANCE", {("Q", "2024-06-30"): "2099-01-01"}, conn) == 0
    assert provenance.provenance_for(DATA_CLASS, symbol="RELIANCE", period_type="Q",
                                     as_of="2024-06-30", conn=conn)["as_of"] == "2024-07-19"

    # 7. candidate_periods / backfill degrade gracefully with no research.db
    assert candidate_periods("X", None) == set()
    assert backfill_symbol("RELIANCE", conn, None)["skip"] == "no_archive_periods"

    print("filing-dates selftest: OK  (parse + match + observe round-trip; ptype-keyed, idempotent)")


def seed_via_rows(rows, conn) -> int:
    """Tiny in-memory seeder (symbol, scripcode[, isin]) — used by --selftest and handy
    for ad-hoc seeding without a CSV file."""
    ensure_schema(conn)
    n = 0
    for r in rows:
        sym, code = r[0].upper(), str(r[1])
        isin = r[2] if len(r) > 2 else None
        conn.execute("INSERT OR REPLACE INTO bse_scrip_map (symbol, scripcode, isin, source) "
                     "VALUES (?,?,?, 'rows')", (sym, code, isin))
        n += 1
    conn.commit()
    return n


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill REAL fundamentals filing dates from BSE (de-models the archive).")
    ap.add_argument("--selftest", action="store_true", help="offline synthetic validation (no network / research.db)")
    ap.add_argument("--seed-scrips", metavar="CSV", help="seed bse_scrip_map from a symbol,scripcode[,isin] CSV")
    ap.add_argument("--backfill", metavar="SYMBOL", help="backfill one symbol (needs research.db + network)")
    ap.add_argument("--backfill-universe", action="store_true", help="backfill all mapped symbols (VPS)")
    ap.add_argument("--limit", type=int, help="cap symbols for --backfill-universe")
    ap.add_argument("--lag-report", action="store_true", help="print provenance.lag_audit() after capture")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.seed_scrips:
        with provenance.get_conn() as conn:
            print(f"seeded {seed_scrip_map_from_csv(args.seed_scrips, conn)} scrip codes")
        return
    if args.backfill:
        rconn = provenance._research_ro()
        with provenance.get_conn() as conn:
            ensure_schema(conn)
            print(backfill_symbol(args.backfill, conn, rconn))
        if rconn:
            rconn.close()
        return
    if args.backfill_universe:
        print(backfill_universe(limit=args.limit)); return
    if args.lag_report:
        import json
        print(json.dumps(provenance.lag_audit(), indent=2, default=str)); return
    ap.print_help()


if __name__ == "__main__":
    main()
