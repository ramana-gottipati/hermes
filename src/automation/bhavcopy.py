"""Daily NSE bhav copy ingestion.

Downloads NSE end-of-day price/volume CSV and loads it into the daily_prices
table. CSV is free, public, no auth.

Schedule: runs once per weekday evening via systemd timer (5:30 PM IST = 12:00 UTC).
"""

import csv
import io
import logging
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from src.core.db import get_conn

log = logging.getLogger("hermes.bhavcopy")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"


def _bhavcopy_url(d: datetime) -> str:
    """NSE archive URL pattern for daily bhav copy."""
    day = d.strftime("%d")
    month = d.strftime("%b").upper()
    year = d.strftime("%Y")
    return f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{day}{month}{year}bhav.csv.zip"


def fetch_for_date(d: datetime) -> Optional[bytes]:
    url = _bhavcopy_url(d)
    log.info("fetching bhav copy for %s: %s", d.date(), url)
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    except requests.RequestException as e:
        log.warning("fetch failed for %s: %s", d.date(), e)
        return None
    if r.status_code != 200:
        log.warning("HTTP %s for %s — likely weekend/holiday/not-yet-published", r.status_code, d.date())
        return None
    return r.content


def parse_zip_csv(zip_bytes: bytes) -> list[dict]:
    """Unzip + parse the bhav copy CSV into rows.

    Columns (NSE format):
      SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, LAST, PREVCLOSE,
      TOTTRDQTY, TOTTRDVAL, TIMESTAMP, TOTALTRADES, ISIN
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        csv_name = next((n for n in names if n.lower().endswith(".csv")), None)
        if not csv_name:
            log.error("no CSV in bhav copy zip: %s", names)
            return []
        raw = zf.read(csv_name).decode("utf-8", errors="ignore")

    reader = csv.DictReader(io.StringIO(raw))
    rows = []
    for r in reader:
        # NSE keys can have trailing spaces; strip
        r = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        rows.append(r)
    return rows


def store(rows: list[dict]) -> int:
    """Insert/replace rows into daily_prices. Returns count inserted."""
    if not rows:
        return 0
    count = 0
    with get_conn() as conn:
        for r in rows:
            symbol = r.get("SYMBOL")
            series = r.get("SERIES")
            if not symbol or series != "EQ":  # focus on equity series; skip BE/BL/etc.
                continue
            ts = r.get("TIMESTAMP", "")  # e.g. "26-MAY-2026"
            try:
                trade_date = datetime.strptime(ts, "%d-%b-%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO daily_prices
                       (symbol, trade_date, open, high, low, close, prev_close, volume, value, series)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol, trade_date,
                        float(r.get("OPEN") or 0),
                        float(r.get("HIGH") or 0),
                        float(r.get("LOW") or 0),
                        float(r.get("CLOSE") or 0),
                        float(r.get("PREVCLOSE") or 0),
                        int(float(r.get("TOTTRDQTY") or 0)),
                        float(r.get("TOTTRDVAL") or 0),
                        series,
                    ),
                )
                count += 1
            except (ValueError, TypeError) as e:
                log.debug("skipping bad row %s: %s", symbol, e)
                continue
    return count


def run_for_today() -> tuple[bool, str]:
    """Fetch + store today's bhav copy.

    If today's isn't published yet (holiday or pre-publish), tries previous
    business day.
    """
    today = datetime.now(timezone.utc).astimezone()
    # NSE publishes bhav copy ~end-of-day IST. Run after 4:30 PM IST = 11:00 UTC.
    for offset in range(0, 5):  # try today, then up to 4 days back
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:  # skip Sat/Sun
            continue
        z = fetch_for_date(d)
        if not z:
            continue
        rows = parse_zip_csv(z)
        if not rows:
            continue
        n = store(rows)
        return True, f"loaded {n} rows for {d.date()}"
    return False, "no bhav copy available in last 5 days"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ok, status = run_for_today()
    log.info("done — ok=%s status=%s", ok, status)


if __name__ == "__main__":
    main()
