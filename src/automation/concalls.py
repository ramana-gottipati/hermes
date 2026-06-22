"""Concall Intelligence (CCI) — corpus fetcher.

The free, no-LLM ingestion layer for the management-credibility strategy. For a
given symbol it:

  1. reads Screener.in's "Concalls" section  (div.documents.concalls > ul.list-links)
  2. for each concall: the date label ("Apr 2026"), the BSE *transcript* PDF URL,
     the PPT URL, the YouTube REC URL, and Screener's free *AI Summary* id
  3. downloads the BSE transcript PDF and extracts its text with pypdf
  4. writes the transcript TEXT to the VPS filesystem (NOT the DB, NOT git):
       <data>/concalls/<SYMBOL>/<period>_<pname8>.txt
  5. upserts the metadata + path into the `concalls` table.

We deliberately do NOT keep the whole PDF — only the rated/structured info
(filled later by concall_extract.py) plus the working transcript text on disk.

Design + the validated DOM/BSE/pypdf contract: docs/concall-intelligence-design.md §8.

Runs under the production .venv (requests/bs4/lxml/pydantic-settings + pypdf).
No LLM here. Idempotent + resumable. Be polite to Screener/BSE (paced requests).

CLI:
    python -m src.automation.concalls RELIANCE TATAMOTORS        # named symbols
    python -m src.automation.concalls --pilot                    # the ~25-name pilot set
    python -m src.automation.concalls RELIANCE --limit 2         # only newest 2 transcripts (smoke test)
    python -m src.automation.concalls RELIANCE --list-only       # metadata only, no PDF downloads
    python -m src.automation.concalls --pilot --min-year 2016    # reach deeper where free
"""

import argparse
import hashlib
import io
import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.core.db import DB_PATH, get_conn
from src.automation.screener import _fetch_company_html, USER_AGENT

log = logging.getLogger("hermes.concalls")

CONCALLS_DIR = DB_PATH.parent / "concalls"
DEFAULT_MIN_YEAR = 2019                 # 2019+ is mandatory (COVID stress test); deeper is opportunistic
REQUEST_PAUSE = 1.5                      # seconds between network hits (politeness)
MIN_TRANSCRIPT_CHARS = 500              # below this = likely a scanned/garbage PDF -> flag for OCR fallback

# BSE wants a browser UA + a Referer or it 403s / serves an interstitial.
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
}

# A diverse pilot universe: large-caps + cyclicals + an NBFC + known loss-makers
# (PAYTM/IDEA/ETERNAL history) so the pipeline meets every shape early.
PILOT = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "HINDALCO", "TATASTEEL", "LT", "MARUTI", "SUNPHARMA",
    "ASIANPAINT", "TITAN", "BAJFINANCE", "ITC", "AXISBANK",
    "ULTRACEMCO", "JSWSTEEL", "ADANIENT", "ETERNAL", "PAYTM",
    "VEDL", "IDEA", "DMART", "PIDILITIND", "DIXON",
]

# Known NSE symbol renames/demergers (Screener 404s the dead symbol). Resolve to
# the live symbol so old references still work; store under the canonical name to
# stay aligned with bhavcopy_rows / stock_signals.
_SYMBOL_ALIASES = {
    "ZOMATO": "ETERNAL",        # renamed 2025
}

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


# --- period derivation (Indian FY, Apr-Mar) ---------------------------------

def _parse_label(label: str):
    """'Apr 2026' -> (month:int, year:int) or (None, None)."""
    m = re.match(r"([A-Za-z]{3,})\s+(\d{4})", label.strip())
    if not m:
        return None, None
    return _MONTHS.get(m.group(1)[:3].lower()), int(m.group(2))


def _derive_period(month: int, year: int):
    """Concall month -> (period_type, fy, quarter). FY named by its Mar-end year.

    Jan-Mar -> Q3 of FY(year); Apr-Jun -> Q4 of FY(year);
    Jul-Sep -> Q1 of FY(year+1); Oct-Dec -> Q2 of FY(year+1).
    Verified vs live Screener (Oct'25=Q2FY26, Jan'26=Q3FY26, Apr'26=Q4FY26).
    """
    if month in (1, 2, 3):
        return "Q", year, 3
    if month in (4, 5, 6):
        return "Q", year, 4
    if month in (7, 8, 9):
        return "Q", year + 1, 1
    return "Q", year + 1, 2


# --- Screener parsing -------------------------------------------------------

def parse_concall_list(html: str) -> list[dict]:
    """Extract the concall entries from a Screener company page."""
    soup = BeautifulSoup(html, "lxml")
    h3 = next((t for t in soup.find_all("h3")
               if t.get_text(strip=True).lower().startswith("concall")), None)
    if not h3:
        return []
    cont = h3.find_parent(["div", "section"])
    cont = (cont.find_parent(["div", "section"]) or cont) if cont else None
    ul = cont.find("ul") if cont else None
    if not ul:
        return []

    out: list[dict] = []
    for li in ul.find_all("li", recursive=False):
        date_div = li.find("div")
        label = date_div.get_text(strip=True) if date_div else ""
        if not label:
            continue
        entry = {"period_label": label, "transcript_url": "",
                 "ppt_url": None, "rec_url": None, "ai_summary_id": None}
        for el in li.find_all(["a", "button"]):
            txt = el.get_text(strip=True).lower()
            if "transcript" in txt:
                entry["transcript_url"] = (el.get("href") or "").strip()
            elif "ppt" in txt:
                entry["ppt_url"] = el.get("href")
            elif "rec" in txt:
                entry["rec_url"] = el.get("href")
            elif "summary" in txt or "notes" in txt:
                m = re.search(r"/concalls/summary/(\d+)/", el.get("data-url") or "")
                if m:
                    entry["ai_summary_id"] = m.group(1)
        out.append(entry)
    return out


def _fetch_ai_summary(summary_id: str) -> Optional[str]:
    """Screener's free AI digest for a concall (a cheap seed for extraction)."""
    url = f"https://www.screener.in/concalls/summary/{summary_id}/"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200:
            return None
        txt = BeautifulSoup(r.text, "lxml").get_text("\n", strip=True)
        return txt[:8000] if txt else None
    except requests.RequestException as e:
        log.warning("ai-summary %s failed: %s", summary_id, e)
        return None


# --- BSE transcript download + text extraction ------------------------------

def _pname(url: str) -> str:
    m = re.search(r"Pname=([0-9A-Za-z._-]+)", url or "")
    return (m.group(1).split(".")[0] if m else "")


def download_transcript_text(url: str):
    """Download a BSE transcript PDF -> (text, status). text is None on failure."""
    try:
        r = requests.get(url, headers=BSE_HEADERS, timeout=45)
    except requests.RequestException as e:
        log.warning("transcript fetch raised: %s", e)
        return None, "FETCH_FAIL"
    if r.status_code != 200:
        return None, f"FETCH_FAIL_{r.status_code}"
    data = r.content
    if data[:4] != b"%PDF":
        return None, "NOT_PDF"
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages).strip()
    except Exception as e:  # noqa: BLE001 - pypdf raises many shapes
        log.warning("pdf parse failed: %s", e)
        return None, "PDF_ERR"
    if len(text) < MIN_TRANSCRIPT_CHARS:
        return None, "EMPTY_TEXT"           # scanned/image PDF -> OCR fallback (deferred)
    return text, "OK"


def _store_text(symbol: str, label: str, pname: str, text: str) -> str:
    d = CONCALLS_DIR / symbol
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_") or "concall"
    fn = f"{safe}_{pname[:8]}.txt" if pname else f"{safe}.txt"
    path = d / fn
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- DB upsert --------------------------------------------------------------

_UPSERT = """
INSERT INTO concalls
    (symbol, period_label, period_type, fy, quarter, concall_month, concall_year,
     transcript_url, ppt_url, rec_url, ai_summary_id, ai_summary,
     transcript_path, transcript_chars, transcript_sha, parse_status)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(symbol, period_label, transcript_url) DO UPDATE SET
    period_type      = excluded.period_type,
    fy               = excluded.fy,
    quarter          = excluded.quarter,
    concall_month    = excluded.concall_month,
    concall_year     = excluded.concall_year,
    ppt_url          = excluded.ppt_url,
    rec_url          = excluded.rec_url,
    ai_summary_id    = excluded.ai_summary_id,
    ai_summary       = COALESCE(excluded.ai_summary, concalls.ai_summary),
    transcript_path  = COALESCE(excluded.transcript_path, concalls.transcript_path),
    transcript_chars = COALESCE(excluded.transcript_chars, concalls.transcript_chars),
    transcript_sha   = COALESCE(excluded.transcript_sha, concalls.transcript_sha),
    parse_status     = COALESCE(excluded.parse_status, concalls.parse_status),
    fetched_at       = datetime('now')
"""


def _existing(symbol: str, label: str, url: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT transcript_path, transcript_chars FROM concalls "
            "WHERE symbol=? AND period_label=? AND transcript_url=?",
            (symbol, label, url),
        ).fetchone()


# --- per-symbol ingest ------------------------------------------------------

def ingest_symbol(symbol: str, *, min_year: int = DEFAULT_MIN_YEAR,
                  fetch_transcripts: bool = True, fetch_ai: bool = True,
                  force: bool = False, limit: Optional[int] = None) -> dict:
    """Ingest one company's concalls. Returns a summary-stats dict."""
    symbol = _SYMBOL_ALIASES.get(symbol.upper().strip(), symbol.upper().strip())
    stats = {"symbol": symbol, "entries": 0, "with_transcript": 0,
             "downloaded": 0, "skipped_old": 0, "failed": 0, "ai": 0}

    html = _fetch_company_html(symbol)
    if not html:
        log.warning("%s: no Screener company page", symbol)
        stats["error"] = "no_company_page"
        return stats

    entries = parse_concall_list(html)
    stats["entries"] = len(entries)
    downloaded = 0

    for e in entries:
        month, year = _parse_label(e["period_label"])
        ptype, fy, quarter = _derive_period(month, year) if month else (None, None, None)
        has_url = bool(e["transcript_url"])
        if has_url:
            stats["with_transcript"] += 1

        # Screener's free AI summary (cheap seed). Always recorded id; text optional.
        ai_text = None
        if fetch_ai and e["ai_summary_id"]:
            ai_text = _fetch_ai_summary(e["ai_summary_id"])
            if ai_text:
                stats["ai"] += 1
            time.sleep(REQUEST_PAUSE)

        path = chars = sha = None
        if not has_url:
            status = "NO_TRANSCRIPT"
        elif not fetch_transcripts:
            status = None                                   # --list-only: metadata only
        elif year and year < min_year:
            status = "SKIPPED_OLD"
            stats["skipped_old"] += 1
        elif limit is not None and downloaded >= limit:
            status = None                                   # under the per-symbol cap
        else:
            prev = _existing(symbol, e["period_label"], e["transcript_url"])
            if prev and prev["transcript_path"] and Path(prev["transcript_path"]).exists() and not force:
                status, path, chars = "OK", prev["transcript_path"], prev["transcript_chars"]
            else:
                text, status = download_transcript_text(e["transcript_url"])
                time.sleep(REQUEST_PAUSE)
                if text:
                    pn = _pname(e["transcript_url"])
                    path = _store_text(symbol, e["period_label"], pn, text)
                    chars = len(text)
                    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
                    downloaded += 1
                    stats["downloaded"] += 1
                else:
                    stats["failed"] += 1

        with get_conn() as conn:
            conn.execute(_UPSERT, (
                symbol, e["period_label"], ptype, fy, quarter, month, year,
                e["transcript_url"], e["ppt_url"], e["rec_url"], e["ai_summary_id"],
                ai_text, path, chars, sha, status,
            ))

    log.info("%s: %s", symbol, stats)
    return stats


# --- CLI --------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="CCI concall corpus fetcher")
    ap.add_argument("symbols", nargs="*", help="NSE symbols (omit with --pilot)")
    ap.add_argument("--pilot", action="store_true", help="use the built-in ~25-name pilot set")
    ap.add_argument("--min-year", type=int, default=DEFAULT_MIN_YEAR,
                    help=f"download transcripts only for concall year >= this (default {DEFAULT_MIN_YEAR})")
    ap.add_argument("--list-only", action="store_true", help="record metadata, do not download transcripts")
    ap.add_argument("--no-ai", action="store_true", help="skip fetching Screener AI summaries")
    ap.add_argument("--force", action="store_true", help="re-download even if the text file exists")
    ap.add_argument("--limit", type=int, help="max transcripts to download per symbol (smoke testing)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    symbols = PILOT if args.pilot else [s.upper() for s in args.symbols]
    if not symbols:
        ap.error("give symbols or --pilot")

    totals = {"entries": 0, "with_transcript": 0, "downloaded": 0, "skipped_old": 0, "failed": 0, "ai": 0}
    for sym in symbols:
        res = ingest_symbol(sym, min_year=args.min_year, fetch_transcripts=not args.list_only,
                            fetch_ai=not args.no_ai, force=args.force, limit=args.limit)
        for k in totals:
            totals[k] += res.get(k, 0)
        time.sleep(REQUEST_PAUSE)
    log.info("TOTALS over %d symbols: %s", len(symbols), totals)


if __name__ == "__main__":
    main()
