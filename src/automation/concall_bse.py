"""BSE-native concall transcript adapter — de-Screener concall discovery, and reach DELISTED names.

The existing ``concalls.py`` discovers the concall LIST via Screener (the index of which calls exist
+ their transcript URLs) and downloads the PDFs from BSE. That makes Screener a redistribution-
sensitive dependency (docs/data-licensing-decision.md → ``concall_corpus`` = VENDOR_TOS) AND it
**cannot reach delisted names** (Screener drops them), which is exactly the population the
survivorship deterioration-veto re-test needs.

This module discovers transcripts DIRECTLY from BSE corporate announcements (an exchange
PUBLIC-RECORD), so it (a) removes the Screener dependency for discovery and (b) reaches any scrip
code, delisted included. The BSE access pattern is the one ``fundamentals_filing_dates.py`` proved:

  * discover: ``AnnSubCategoryGetData/w`` ``strCat='Company Update'`` → keep rows whose
    ``SUBCATNAME == 'Earnings Call Transcript'`` (each carries ``NEWS_DT`` + ``ATTACHMENTNAME``);
  * download: ``https://www.bseindia.com/xml-data/corpfiling/AttachHis/<ATTACHMENTNAME>`` (with an
    ``AttachLive`` fallback for very recent filings);
  * extract: pypdf → text → the standard on-disk store ``/opt/hermes/data/concalls/<SYM>/*.txt``;
  * record: INSERT-OR-IGNORE a row into the existing ``concalls`` table (``source='bse-ann'``) on its
    ``UNIQUE(symbol, period_label, transcript_url)`` key, so the existing settle→score→series
    pipeline picks the delisted transcripts up unchanged. It only ADDS rows; it never edits
    ``concalls.py`` or rewrites another source's rows.

Scrip codes (incl. delisted) come from ``bse_scrip_map`` — seed it with
``fundamentals_filing_dates --seed-bse --seed-all-statuses`` (Active+Suspended+Delisted, ISIN-joined
to ``security_master``) or this module's ``--seed-delisted-scrips``.

FREE (no LLM). Capture only — extraction (paid Gemini, ``concall_extract``) reads the on-disk .txt
later and is gated separately (the data-capture doctrine: ingestion is free + perishable, extraction
is deferrable). Defensive + offline ``--selftest`` exercises the pure parse/period/url core.

CLI:
    python -m src.automation.concall_bse --selftest
    python -m src.automation.concall_bse --seed-delisted-scrips          # map delisted names → BSE codes
    python -m src.automation.concall_bse --probe 500325                  # list a scrip's transcripts
    python -m src.automation.concall_bse --capture RELIANCE 500325       # one symbol
    python -m src.automation.concall_bse --capture-delisted --limit 50   # the distress-era delisted set
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import time
from datetime import date
from typing import Optional

import requests

from src.automation import provenance
from src.automation.fundamentals_filing_dates import BSE_HEADERS, parse_filing_dt, resolve_scripcode

log = logging.getLogger("hermes.concall_bse")

ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
ATTACH_HIS = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/"
ATTACH_LIVE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
TRANSCRIPT_SUBCAT = "earnings call transcript"
STORE_DIR = "/opt/hermes/data/concalls"
REQUEST_PAUSE = 1.2
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── pure helpers (offline-testable) ───────────────────────────────────────────
def is_transcript(row: dict) -> bool:
    """True for an Earnings Call Transcript announcement (subcat-first, headline fallback)."""
    sub = str(row.get("SUBCATNAME") or "").strip().lower()
    if sub == TRANSCRIPT_SUBCAT:
        return True
    head = f"{row.get('NEWSSUB') or ''} {row.get('HEADLINE') or ''}".lower()
    return "earnings call transcript" in head or "transcript of" in head and "earnings" in head


def period_label(news_dt: Optional[str]) -> Optional[str]:
    """BSE NEWS_DT → 'Mon YYYY' (the concalls.py label convention; the transcript is filed within
    days of the call, so the filing month ≈ the call month)."""
    iso = parse_filing_dt(news_dt)
    if not iso:
        return None
    y, m = int(iso[:4]), int(iso[5:7])
    if not (1 <= m <= 12):
        return None
    return f"{_MONTHS[m - 1]} {y}"


def _derive_period(news_dt: Optional[str]) -> dict:
    """concalls-compatible period fields from the announcement date."""
    iso = parse_filing_dt(news_dt)
    if not iso:
        return {}
    y, m = int(iso[:4]), int(iso[5:7])
    fy = y + 1 if m >= 4 else y                      # Indian FY = year of the Mar-end
    quarter = {4: 4, 5: 1, 6: 1, 7: 1, 8: 1, 9: 2, 10: 2, 11: 2, 12: 3, 1: 3, 2: 3, 3: 4}.get(m)
    return {"concall_month": m, "concall_year": y, "fy": fy, "quarter": quarter, "period_type": "Q"}


def attachment_urls(attachment: str) -> list:
    """The candidate PDF URLs for a BSE attachment (historical first, then live)."""
    a = (attachment or "").strip()
    return [ATTACH_HIS + a, ATTACH_LIVE + a] if a else []


# ── network (not exercised by --selftest) ─────────────────────────────────────
def fetch_transcript_announcements(scripcode: str, from_date: str, to_date: str,
                                   session: Optional[requests.Session] = None) -> list:
    """All Earnings Call Transcript announcements for a scrip in [from_date, to_date] (ISO).
    Returns [{news_dt, attachment, headline, period_label}], defensive [] on failure."""
    sess = session or requests.Session()
    f, t = from_date.replace("-", ""), to_date.replace("-", "")
    out: list = []
    for page in range(1, 51):
        params = {"strCat": "Company Update", "strPrevDate": f, "strToDate": t,
                  "strscrip": scripcode, "strSearch": "P", "strType": "C",
                  "subcategory": "-1", "pageno": page}
        try:
            r = sess.get(ANN_URL, headers=BSE_HEADERS, params=params, timeout=30)
            if r.status_code != 200:
                break
            j = r.json()
            rows = j.get("Table") or [] if isinstance(j, dict) else []
        except (requests.RequestException, ValueError) as e:
            log.warning("BSE ann %s p%d: %s", scripcode, page, e)
            break
        if not rows:
            break
        for row in rows:
            if not is_transcript(row):
                continue
            att = str(row.get("ATTACHMENTNAME") or "").strip()
            nd = row.get("NEWS_DT") or row.get("DT_TM")
            if att and period_label(nd):
                out.append({"news_dt": parse_filing_dt(nd), "attachment": att,
                            "headline": (row.get("NEWSSUB") or row.get("HEADLINE") or "")[:300],
                            "period_label": period_label(nd)})
        time.sleep(REQUEST_PAUSE)
    return out


def download_pdf_text(attachment: str, session: Optional[requests.Session] = None) -> tuple:
    """(text, status) for a BSE attachment. status ∈ OK | FETCH_FAIL | NOT_PDF | EMPTY_TEXT."""
    sess = session or requests.Session()
    raw = None
    for url in attachment_urls(attachment):
        try:
            r = sess.get(url, headers={**BSE_HEADERS, "Referer": "https://www.bseindia.com/"}, timeout=45)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                raw = r.content
                break
        except requests.RequestException as e:
            log.warning("pdf %s: %s", attachment, e)
        time.sleep(REQUEST_PAUSE)
    if raw is None:
        return None, "FETCH_FAIL"
    try:
        import io
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw))
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages).strip()
    except Exception as e:  # noqa: BLE001
        log.warning("pypdf %s: %s", attachment, e)
        return None, "NOT_PDF"
    return (text, "OK") if text else (None, "EMPTY_TEXT")


# ── capture (writes on-disk .txt + a concalls row) ────────────────────────────
def capture_symbol(symbol: str, scripcode: Optional[str], conn, *, from_year: int = 2010,
                   session: Optional[requests.Session] = None, store_dir: str = STORE_DIR) -> dict:
    """Discover + download a symbol's BSE earnings-call transcripts, store text, and INSERT-OR-IGNORE
    a concalls row each (source='bse-ann'). Never raises. Stats dict."""
    symbol = symbol.upper().strip()
    st = {"symbol": symbol, "found": 0, "captured": 0, "skipped": 0, "failed": 0}
    code = scripcode or resolve_scripcode(symbol, conn)
    if not code:
        st["skip"] = "no_scripcode"
        return st
    sess = session or requests.Session()
    anns = fetch_transcript_announcements(code, f"{from_year}-01-01", date.today().isoformat(), session=sess)
    st["found"] = len(anns)
    for a in anns:
        url = ATTACH_HIS + a["attachment"]
        exists = conn.execute(
            "SELECT 1 FROM concalls WHERE symbol=? AND period_label=? AND transcript_url=?",
            (symbol, a["period_label"], url)).fetchone()
        if exists:
            st["skipped"] += 1
            continue
        text, status = download_pdf_text(a["attachment"], session=sess)
        path = None
        if status == "OK" and text:
            d = os.path.join(store_dir, symbol)
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, f"{a['period_label'].replace(' ', '_')}_bse.txt")
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            except OSError as e:
                log.warning("write %s: %s", path, e)
                path = None
        else:
            st["failed"] += 1
        per = _derive_period(a["news_dt"])
        conn.execute(
            "INSERT OR IGNORE INTO concalls (symbol, period_label, period_type, fy, quarter, "
            "concall_month, concall_year, transcript_url, transcript_path, transcript_chars, "
            "source, parse_status, concall_dt) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (symbol, a["period_label"], per.get("period_type"), per.get("fy"), per.get("quarter"),
             per.get("concall_month"), per.get("concall_year"), url, path,
             len(text) if text else None, "bse-ann", status, a["news_dt"]))
        if status == "OK":
            st["captured"] += 1
        conn.commit()
        time.sleep(REQUEST_PAUSE)
    return st


def distress_delisted(conn, *, limit: Optional[int] = None) -> list:
    """The distress-era delisted target set: INACTIVE, delisted 2016–2025, with real trading
    history (≥500 days) — the survivorship re-test's true population."""
    rows = conn.execute(
        "SELECT symbol FROM security_master WHERE status='INACTIVE' AND last_date>='2016-01-01' "
        "AND last_date<'2026-01-01' AND n_days>=500 ORDER BY last_date DESC").fetchall()
    syms = [r[0] for r in rows]
    return syms[:limit] if limit else syms


def capture_delisted(*, limit: Optional[int] = None, from_year: int = 2010) -> dict:
    """Capture transcripts for the distress-era delisted set (VPS). FREE; perishable → run early."""
    totals = {"symbols": 0, "with_transcripts": 0, "captured": 0, "no_scripcode": 0}
    sess = requests.Session()
    with provenance.get_conn() as conn:
        targets = distress_delisted(conn, limit=limit)
        log.info("capture-delisted: %d distress-era delisted targets", len(targets))
        for i, sym in enumerate(targets, 1):
            stt = capture_symbol(sym, None, conn, from_year=from_year, session=sess)
            totals["symbols"] += 1
            totals["captured"] += stt.get("captured", 0)
            if stt.get("skip") == "no_scripcode":
                totals["no_scripcode"] += 1
            elif stt.get("found", 0) > 0:
                totals["with_transcripts"] += 1
            if i % 25 == 0:
                log.info("capture-delisted %d/%d: %s", i, len(targets), totals)
    return totals


def seed_delisted_scrips() -> dict:
    """Map delisted names → BSE codes: BSE all-status scrip master ⋈ security_master on ISIN."""
    from src.automation import fundamentals_filing_dates as ffd
    with provenance.get_conn() as conn:
        return ffd.seed_scrip_map_from_bse(conn, statuses=("Active", "Suspended", "Delisted"),
                                           only_archived=False)


# ── selftest ────────────────────────────────────────────────────────────────
def _selftest() -> None:
    assert is_transcript({"SUBCATNAME": "Earnings Call Transcript"}) is True
    assert is_transcript({"SUBCATNAME": "Credit Rating"}) is False
    assert is_transcript({"SUBCATNAME": "General", "NEWSSUB": "Transcript of the earnings call held"}) is True
    assert period_label("2025-08-14T18:30:00") == "Aug 2025"
    assert period_label("19 Jul 2024 10:00:00") == "Jul 2024"
    assert period_label(None) is None
    assert _derive_period("2025-08-14T00:00:00") == {"concall_month": 8, "concall_year": 2025,
                                                     "fy": 2026, "quarter": 1, "period_type": "Q"}
    assert attachment_urls("x.pdf")[0].endswith("AttachHis/x.pdf")
    assert attachment_urls("") == []

    # capture path round-trips into a stub concalls table with an injected fetch/download
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE concalls (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
        period_label TEXT NOT NULL, period_type TEXT, fy INT, quarter INT, concall_month INT,
        concall_year INT, transcript_url TEXT NOT NULL DEFAULT '', transcript_path TEXT,
        transcript_chars INT, source TEXT, parse_status TEXT, concall_dt TEXT,
        UNIQUE(symbol, period_label, transcript_url))""")
    conn.execute("CREATE TABLE bse_scrip_map (symbol TEXT PRIMARY KEY, scripcode TEXT)")
    conn.execute("INSERT INTO bse_scrip_map VALUES ('ZZ','999999')")
    import sys
    mod = sys.modules[__name__]          # patch the RUNNING module ('__main__' under -m), not a re-import
    _f, _d = mod.fetch_transcript_announcements, mod.download_pdf_text
    mod.fetch_transcript_announcements = lambda code, a, b, session=None: [
        {"news_dt": "2025-08-14", "attachment": "x.pdf", "headline": "Earnings Call Transcript",
         "period_label": "Aug 2025"}]
    mod.download_pdf_text = lambda att, session=None: ("hello transcript world", "OK")
    try:
        st = capture_symbol("ZZ", None, conn, store_dir="/tmp/_cbse_selftest")
    finally:
        mod.fetch_transcript_announcements, mod.download_pdf_text = _f, _d
    assert st["found"] == 1 and st["captured"] == 1, st
    row = conn.execute("SELECT symbol, period_label, source, parse_status, transcript_chars FROM concalls").fetchone()
    assert row == ("ZZ", "Aug 2025", "bse-ann", "OK", 22), row
    # idempotent: re-capturing the same announcement is skipped
    mod.fetch_transcript_announcements = lambda code, a, b, session=None: [
        {"news_dt": "2025-08-14", "attachment": "x.pdf", "headline": "x", "period_label": "Aug 2025"}]
    try:
        st2 = capture_symbol("ZZ", None, conn, store_dir="/tmp/_cbse_selftest")
    finally:
        mod.fetch_transcript_announcements = _f
    assert st2["skipped"] == 1 and st2["captured"] == 0, st2
    print("concall_bse selftest: OK  (transcript filter + period + attachment urls + capture round-trip, idempotent)")


def main() -> None:
    ap = argparse.ArgumentParser(description="BSE-native concall transcript adapter (de-Screener + delisted reach).")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed-delisted-scrips", action="store_true", help="map delisted names → BSE codes (ISIN join)")
    ap.add_argument("--probe", metavar="SCRIPCODE", help="list a scrip's transcript announcements")
    ap.add_argument("--capture", nargs="+", metavar="ARG", help="SYMBOL [SCRIPCODE] — capture one symbol")
    ap.add_argument("--capture-delisted", action="store_true", help="capture the distress-era delisted set (VPS)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--from-year", type=int, default=2010)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.selftest:
        _selftest(); return
    if args.seed_delisted_scrips:
        import json
        print(json.dumps(seed_delisted_scrips(), indent=2)); return
    if args.probe:
        anns = fetch_transcript_announcements(args.probe, f"{args.from_year}-01-01", date.today().isoformat())
        print(f"{len(anns)} transcript announcements")
        for a in anns[:20]:
            print(f"  {a['period_label']:9} {a['news_dt']}  {a['attachment']}")
        return
    if args.capture:
        sym = args.capture[0]
        code = args.capture[1] if len(args.capture) > 1 else None
        with provenance.get_conn() as conn:
            print(capture_symbol(sym, code, conn, from_year=args.from_year))
        return
    if args.capture_delisted:
        print(capture_delisted(limit=args.limit, from_year=args.from_year)); return
    ap.print_help()


if __name__ == "__main__":
    main()
