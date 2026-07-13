"""NSE indices ingestion — daily OHLC + valuation per index (D32).

Source file: ind_close_all_DDMMYYYY.csv
URL pattern: https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv

Storage:
  - Raw file archived to /opt/hermes/data/indices/YYYY/MMM/<filename>
  - Parsed rows into `index_rows` table
  - `index_dates` table tracks completion (idempotent)

Usage:
    python -m src.automation.indexes                  # most recent trading day
    python -m src.automation.indexes --backfill 1830  # 5 years
    python -m src.automation.indexes --date 2026-06-05
"""

import argparse
import csv
import io
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from src.core.db import DB_PATH, get_conn
from src.automation.fetch_retry import RetryableFetchError, raise_if_retryable  # AUD-14

log = logging.getLogger("hermes.indexes")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
ARCHIVE_DIR = DB_PATH.parent / "indices"
REQUEST_PAUSE_SECONDS = 1.5


def _ind_close_url(d: datetime) -> str:
    return (
        f"https://nsearchives.nseindia.com/content/indices/"
        f"ind_close_all_{d.strftime('%d%m%Y')}.csv"
    )


def _archive_path(d: datetime, filename: str) -> Path:
    p = ARCHIVE_DIR / d.strftime("%Y") / d.strftime("%b").upper()
    p.mkdir(parents=True, exist_ok=True)
    return p / filename


def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/csv,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            },
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise RetryableFetchError(f"network error fetching {url}: {e}") from e   # AUD-14
    raise_if_retryable(r.status_code, url)   # AUD-14: 403/429/5xx = throttle/block, not no-data
    if r.status_code != 200 or len(r.content) < 100:
        return None
    return r.content


def _f(v) -> Optional[float]:
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def _i(v) -> Optional[int]:
    if v is None or v == "" or v == "-":
        return None
    try:
        return int(float(str(v).replace(",", "").strip()))
    except ValueError:
        return None


def _parse(csv_text: str, fallback_date: str) -> list[dict]:
    """Parse the ind_close_all CSV. Tolerant of NSE column-name variations."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        # NSE has slight variations across years; try multiple key names.
        name = r.get("Index Name") or r.get("IndexName") or r.get("INDEX NAME")
        date_raw = r.get("Index Date") or r.get("Date") or r.get("INDEX DATE")
        if not name:
            continue
        try:
            trade_date = (
                datetime.strptime(date_raw, "%d-%b-%Y").strftime("%Y-%m-%d")
                if date_raw else fallback_date
            )
        except ValueError:
            try:
                trade_date = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                trade_date = fallback_date

        rows.append({
            "index_name":     _canon_index(name.strip()),
            "trade_date":     trade_date,
            "open_value":     _f(r.get("Open Index Value") or r.get("Open")),
            "high_value":     _f(r.get("High Index Value") or r.get("High")),
            "low_value":      _f(r.get("Low Index Value") or r.get("Low")),
            "close_value":    _f(r.get("Closing Index Value") or r.get("Close")
                                or r.get("Close Index Value")),
            "points_change":  _f(r.get("Points Change") or r.get("Change")),
            "change_pct":     _f(r.get("Change(%)") or r.get("% Change")
                                or r.get("Change %")),
            "volume":         _i(r.get("Volume")),
            "turnover_cr":    _f(r.get("Turnover (Rs. Cr.)") or r.get("Turnover")
                                or r.get("Turnover Cr")),
            "pe":             _f(r.get("P/E")),
            "pb":             _f(r.get("P/B")),
            "dividend_yield": _f(r.get("Div Yield") or r.get("Dividend Yield")),
        })
    return rows


# NSE flipped index-name CASING over the years ("NIFTY Midcap 50" 2012-15 → "Nifty Midcap 50"
# 2015-…), silently splitting one index's history across two keys and starving every
# `index_name = ?` consumer (ratio/RS/signals) of the other-cased era. Canonicalise the known
# variant groups to the CURRENT feed casing at ingest (anchor = what the live feed emits, so
# tomorrow's rows are already canonical → zero rename churn). The DQ battery
# (chk_index_name_variants) WARNs if NSE ever mints a NEW variant group.
_NAME_CANON = {
    "nifty midcap 100":     "NIFTY Midcap 100",
    "nifty midcap 50":      "Nifty Midcap 50",
    "nifty smallcap 100":   "NIFTY Smallcap 100",
    "nifty tr 1x inverse":  "NIFTY TR 1X Inverse",
    "nifty tr 2x leverage": "NIFTY TR 2X Leverage",
}


def _canon_index(name: str) -> str:
    return _NAME_CANON.get(" ".join(name.split()).lower(), name)


_COLS = [
    "index_name", "trade_date",
    "open_value", "high_value", "low_value", "close_value",
    "points_change", "change_pct", "volume", "turnover_cr",
    "pe", "pb", "dividend_yield",
]


def _store(rows: list[dict]) -> int:
    """CL-MDC-06: return the actual number of rows written (conn.total_changes
    delta) rather than len(rows). On a silent constraint reject the attempted
    count would overstate what _mark_date records."""
    if not rows:
        return 0
    placeholders = ",".join("?" * len(_COLS))
    sql = (
        f"INSERT OR REPLACE INTO index_rows ({','.join(_COLS)}) "
        f"VALUES ({placeholders})"
    )
    with get_conn() as conn:
        before = conn.total_changes
        conn.executemany(sql, [[r.get(c) for c in _COLS] for r in rows])
        written = conn.total_changes - before
    return written


def _mark_date(trade_date: str, row_count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO index_dates (trade_date, row_count, ingested_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(trade_date) DO UPDATE SET
                 row_count = excluded.row_count,
                 ingested_at = excluded.ingested_at""",
            (trade_date, row_count),
        )


def _already_ingested(trade_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM index_dates WHERE trade_date = ?", (trade_date,)
        ).fetchone()
        return row is not None


def fetch_and_store(d: datetime) -> tuple[bool, str, int]:
    """Fetch index file for one date and store. Returns (ok, message, stored)
    where `stored` is the row count actually written this call (CL-MDC-07:
    callers test the structured count instead of sniffing "rows" out of the
    message). already-ingested / fetch-fail / parse-fail → 0."""
    trade_date = d.strftime("%Y-%m-%d")
    if _already_ingested(trade_date):
        log.info("%s already ingested", trade_date)
        return True, "already ingested", 0

    url = _ind_close_url(d)
    try:
        raw = _try_fetch(url)
    except RetryableFetchError as e:
        # AUD-14: a block/throttle is NOT a holiday — leave the date un-marked (never _mark_date
        # here) so run_today / run_backfill re-attempt it instead of a silent index-feed hole.
        return False, f"{trade_date} BLOCKED/throttled — left for retry: {e}", 0
    if not raw:
        return False, f"fetch failed for {trade_date}", 0

    # Archive raw
    fn = url.rsplit("/", 1)[-1]
    archive = _archive_path(d, fn)
    if not archive.exists():
        archive.write_bytes(raw)
        log.info("archived %s (%d bytes)", archive, len(raw))

    try:
        text = raw.decode("utf-8-sig", errors="ignore")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")

    rows = _parse(text, fallback_date=trade_date)
    if not rows:
        return False, f"parse failed for {trade_date}", 0

    n = _store(rows)
    _mark_date(trade_date, n)
    log.info("%s %d/%d index rows stored", trade_date, n, len(rows))
    return True, f"{n} rows", n


def _latest_likely_trading_day(today: Optional[datetime] = None) -> datetime:
    """Walk back from today (or given date) to the most recent weekday."""
    d = (today or datetime.now(timezone.utc)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= timedelta(days=1)
    return d


def run_today() -> tuple[bool, str]:
    """Try the last 5 trading days; ingest any that aren't already in."""
    today = _latest_likely_trading_day()
    any_new = False
    for back in range(0, 5):
        d = today - timedelta(days=back)
        # Skip weekends in walk-back
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        ok, msg, stored = fetch_and_store(d)
        if ok and stored > 0:
            any_new = True
        time.sleep(REQUEST_PAUSE_SECONDS)
    return any_new, "done"


def run_backfill(days_back: int) -> tuple[int, int]:
    """Walk back N calendar days, fetch each weekday's index file."""
    today = _latest_likely_trading_day()
    fetched = 0
    skipped = 0
    for back in range(0, days_back):
        d = today - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        if _already_ingested(d.strftime("%Y-%m-%d")):
            skipped += 1
            continue
        ok, msg, stored = fetch_and_store(d)
        if ok and stored > 0:
            fetched += 1
        time.sleep(REQUEST_PAUSE_SECONDS)
    return fetched, skipped


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", type=int, help="number of calendar days back")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d")
        ok, msg, _stored = fetch_and_store(d)
        log.info("%s: %s", args.date, msg)
    elif args.backfill:
        n, sk = run_backfill(args.backfill)
        log.info("backfill done: %d new, %d skipped", n, sk)
    else:
        ok, msg = run_today()
        log.info("today run: %s", msg)


if __name__ == "__main__":
    main()
