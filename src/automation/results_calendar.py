"""Results calendar (Dataset D-01) — forward "who reports next" from the NSE event calendar.

The results-season war room needs the FORWARD half that the Results-Reaction scanner can't give:
which companies have called a board meeting to consider financial results, and when. That is a
board-meeting INTIMATION (filed in advance, "…will meet on DATE to consider results") — distinct from
the actual result filing (backward-looking, already covered by fundamentals_filing_dates.py, whose
is_results_filing() deliberately REJECTS these intimations). Here we CAPTURE them.

PRIMARY SOURCE (guardrail #8): NSE event calendar — `nseindia.com/api/event-calendar` — the exchange's
own forward corporate-events feed (symbol-native, no scrip-code mapping). Reuses the proven NSE
anti-bot session priming from insider_events.py (hit home + a corporate-filings referer for cookies,
then the JSON API). Pure stdlib + requests (production venv). NO LLM.

OWNS one table, `board_meetings`, via an embedded schema (the concall_bse.py / insider_events.py
house pattern). Idempotent upsert keyed (symbol, meeting_date, purpose). Defensive: every network /
DB path degrades to a graceful no-op when absent, so the offline `--selftest` runs the parse +
classify + normalize core with zero I/O.

CLI:
    python -m src.automation.results_calendar --selftest              # offline, synthetic
    python -m src.automation.results_calendar --fetch                 # next 30d (VPS)
    python -m src.automation.results_calendar --fetch --days 45       # custom horizon
    python -m src.automation.results_calendar --upcoming 14           # print next 14d results BMs
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta

log = logging.getLogger("hermes.results_calendar")

_NSE_HOME = "https://www.nseindia.com"
_NSE_REF = "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"
_NSE_API = "https://www.nseindia.com/api/event-calendar"
_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120 Safari/537.36")

SCHEMA = """
CREATE TABLE IF NOT EXISTS board_meetings (
    symbol       TEXT NOT NULL,
    company      TEXT,
    meeting_date TEXT NOT NULL,              -- ISO YYYY-MM-DD (the board-meeting date)
    purpose      TEXT,                        -- as filed ("Financial Results", ...)
    is_results   INTEGER DEFAULT 0,           -- 1 = a results/financial board meeting
    source       TEXT DEFAULT 'NSE-event-calendar',
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(symbol, meeting_date, purpose)
);
CREATE INDEX IF NOT EXISTS idx_bm_date ON board_meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_bm_sym  ON board_meetings(symbol, meeting_date);
"""

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_date(s: str) -> str | None:
    """NSE dates come as '18-Jul-2026' (also tolerate ISO / '18 Jul 2026'). -> ISO, else None."""
    if not s:
        return None
    t = str(s).strip().replace(",", "")
    # already ISO?
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        try:
            date.fromisoformat(t[:10]); return t[:10]
        except ValueError:
            pass
    for sep in ("-", " "):
        parts = t.split(sep)
        if len(parts) == 3 and parts[1][:3].lower() in _MONTHS:
            try:
                d, mon, y = int(parts[0]), _MONTHS[parts[1][:3].lower()], int(parts[2])
                return date(y, mon, d).isoformat()
            except (ValueError, KeyError):
                return None
    return None


def is_results_purpose(purpose: str) -> bool:
    """A results/financial board meeting (the thing the war room cares about). Buyback/dividend/
    fund-raising-only meetings are NOT flagged (dividend usually rides WITH results and is caught by
    'result'/'financial'; a standalone 'Dividend' or 'Fund Raising' intimation is not a results date)."""
    p = (purpose or "").lower()
    return ("result" in p) or ("financial" in p and "year" not in p[:4])


def normalize_row(r: dict) -> dict | None:
    """NSE event-calendar row -> canonical board_meeting dict. None if unusable."""
    sym = (r.get("symbol") or "").strip().upper()
    mdate = parse_date(r.get("bm_date") or r.get("date") or r.get("meetingDate"))
    if not sym or not mdate:
        return None
    purpose = (r.get("purpose") or r.get("bm_purpose") or "").strip()
    return {"symbol": sym, "company": (r.get("company") or r.get("companyName") or "").strip(),
            "meeting_date": mdate, "purpose": purpose,
            "is_results": 1 if is_results_purpose(purpose) else 0}


# ---- network (VPS) ---------------------------------------------------------

def _nse_session():
    import requests
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)          # prime anti-bot cookies
    s.get(_NSE_REF, headers=h, timeout=20)
    return s, h


def fetch(from_date: str, to_date: str, *, session=None, headers=None) -> list:
    """Fetch NSE event-calendar rows for [from_date, to_date] (ISO). NSE wants DD-MM-YYYY;
    falls back to the param-less feed if the dated form 400s."""
    if session is None:
        session, headers = _nse_session()

    def ddmmyyyy(iso):
        y, m, d = str(iso)[:10].split("-")
        return "%s-%s-%s" % (d, m, y)

    for url in ("%s?index=equities&from_date=%s&to_date=%s" % (_NSE_API, ddmmyyyy(from_date), ddmmyyyy(to_date)),
                "%s?index=equities" % _NSE_API, _NSE_API):
        try:
            r = session.get(url, headers=headers, timeout=45)
            if r.status_code != 200:
                continue
            data = r.json()
            rows = data.get("data") if isinstance(data, dict) else data
            if rows:
                return rows
        except Exception as e:  # noqa: BLE001 — try the next URL form
            log.warning("event-calendar fetch failed (%s): %s", url[:60], e)
    return []


def ingest(days: int = 30) -> dict:
    """Fetch the next ``days`` and upsert into board_meetings. Returns counts."""
    from src.core.db import get_conn
    today = date.today()
    horizon = (today + timedelta(days=days)).isoformat()
    rows = fetch(today.isoformat(), horizon)
    seen, saved, results_bm = 0, 0, 0
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for raw in rows:
            n = normalize_row(raw)
            if n is None:
                continue
            seen += 1
            results_bm += n["is_results"]
            cur = conn.execute(
                """INSERT OR IGNORE INTO board_meetings
                   (symbol, company, meeting_date, purpose, is_results, source)
                   VALUES (?,?,?,?,?,?)""",
                (n["symbol"], n["company"], n["meeting_date"], n["purpose"],
                 n["is_results"], "NSE-event-calendar"))
            saved += cur.rowcount
        conn.commit()
    log.info("board_meetings: %d rows seen, %d new, %d results-BMs", seen, saved, results_bm)
    return {"seen": seen, "saved": saved, "results_bm": results_bm, "horizon": horizon}


def upcoming_results(days: int = 14) -> list:
    """Read helper — the next ``days`` of results board meetings, soonest first."""
    from src.core.db import get_conn
    lo = date.today().isoformat()
    hi = (date.today() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        return conn.execute(
            """SELECT symbol, company, meeting_date, purpose FROM board_meetings
               WHERE is_results=1 AND meeting_date>=? AND meeting_date<=?
               ORDER BY meeting_date ASC, symbol ASC""", (lo, hi)).fetchall()


# ---- selftest (offline) ----------------------------------------------------

def selftest() -> None:
    assert parse_date("18-Jul-2026") == "2026-07-18"
    assert parse_date("09 Jul 2026") == "2026-07-09"
    assert parse_date("2026-07-09 00:00") == "2026-07-09"
    assert parse_date("garbage") is None and parse_date("") is None
    assert is_results_purpose("Financial Results")
    assert is_results_purpose("Board Meeting to consider Un-Audited Results & Dividend")
    assert not is_results_purpose("Buy Back")
    assert not is_results_purpose("Fund Raising")
    assert not is_results_purpose("Dividend")
    n = normalize_row({"symbol": "reliance", "company": "Reliance Industries Limited",
                       "bm_date": "18-Jul-2026", "purpose": "Financial Results"})
    assert n["symbol"] == "RELIANCE" and n["meeting_date"] == "2026-07-18" and n["is_results"] == 1, n
    assert normalize_row({"symbol": "", "bm_date": "18-Jul-2026"}) is None       # no symbol
    assert normalize_row({"symbol": "X", "bm_date": "bad"}) is None              # no date
    b = normalize_row({"symbol": "TCS", "bm_date": "10-Jul-2026", "purpose": "Buy Back"})
    assert b["is_results"] == 0, b
    print("results_calendar selftest OK")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--upcoming", type=int, metavar="DAYS")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.fetch:
        out = ingest(days=a.days)
        print(f"board_meetings: seen={out['seen']} new={out['saved']} "
              f"results-BMs={out['results_bm']} horizon={out['horizon']}")
    elif a.upcoming is not None:
        for sym, co, md, pu in upcoming_results(a.upcoming):
            print(f"  {md}  {sym:<14} {pu}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
