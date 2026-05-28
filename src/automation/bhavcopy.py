"""NSE equity bhav copy ingestion.

Handles both NSE formats:
  - Legacy (pre-July-2024): cm08JAN2024bhav.csv.zip  — columns SYMBOL/SERIES/OPEN...
  - UDIFF (current):        BhavCopy_NSE_CM_0_0_0_20260528_F_0000.csv.zip — columns TradDt/TckrSymb/...

Storage:
  1. Raw ZIP saved to /opt/hermes/data/bhavcopy/YYYY/MMM/<filename>
  2. Parsed rows inserted into bhavcopy_rows table (all columns + raw_json fallback)
  3. Successful day recorded in bhavcopy_dates table for idempotent backfill

Usage:
    python -m src.automation.bhavcopy                 # fetch most recent trading day
    python -m src.automation.bhavcopy --backfill 730  # fill last 730 calendar days
    python -m src.automation.bhavcopy --date 2024-01-08  # specific date
"""

import argparse
import csv
import io
import json
import logging
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from src.core.db import DB_PATH, get_conn

log = logging.getLogger("hermes.bhavcopy")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
ARCHIVE_DIR = DB_PATH.parent / "bhavcopy"
REQUEST_PAUSE_SECONDS = 1.5  # polite throttling

# UDIFF format switched around mid-2024. If both URL patterns work for a date,
# we prefer UDIFF since it has more columns (open interest etc., though for CM
# segment it's still equity).
UDIFF_SWITCH_DATE = datetime(2024, 7, 8)  # approximate; we try both URLs anyway


# --- URL helpers -----------------------------------------------------------

def _legacy_url(d: datetime) -> str:
    return (
        f"https://nsearchives.nseindia.com/content/historical/EQUITIES/"
        f"{d.strftime('%Y')}/{d.strftime('%b').upper()}/"
        f"cm{d.strftime('%d')}{d.strftime('%b').upper()}{d.strftime('%Y')}bhav.csv.zip"
    )


def _udiff_url(d: datetime) -> str:
    return (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"
    )


def _archive_path(d: datetime, filename: str) -> Path:
    p = ARCHIVE_DIR / d.strftime("%Y") / d.strftime("%b").upper()
    p.mkdir(parents=True, exist_ok=True)
    return p / filename


# --- HTTP fetch -------------------------------------------------------------

def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    except requests.RequestException as e:
        log.debug("fetch error %s: %s", url, e)
        return None
    if r.status_code == 200 and r.content[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        return r.content
    return None


def fetch_for_date(d: datetime) -> Optional[tuple[bytes, str, str]]:
    """Return (zip_bytes, filename, format_version) or None if no data published."""
    # Try UDIFF first if date is in/after the switch window
    candidates: list[tuple[str, str]] = []
    if d >= UDIFF_SWITCH_DATE:
        candidates.append((_udiff_url(d), "udiff"))
        candidates.append((_legacy_url(d), "legacy"))
    else:
        candidates.append((_legacy_url(d), "legacy"))
        candidates.append((_udiff_url(d), "udiff"))

    for url, fmt in candidates:
        z = _try_fetch(url)
        if z:
            filename = url.rsplit("/", 1)[-1]
            return z, filename, fmt
    return None


# --- Archive raw zip --------------------------------------------------------

def save_raw_zip(d: datetime, filename: str, zip_bytes: bytes) -> Path:
    target = _archive_path(d, filename)
    if not target.exists():
        target.write_bytes(zip_bytes)
        log.info("archived raw zip %s (%d bytes)", target, len(zip_bytes))
    return target


# --- CSV parsing ------------------------------------------------------------

def _unzip_csv(zip_bytes: bytes) -> Optional[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_name = next((n for n in zf.namelist() if n.lower().endswith(".csv")), None)
            if not csv_name:
                return None
            return zf.read(csv_name).decode("utf-8", errors="ignore")
    except zipfile.BadZipFile:
        log.warning("bad zip file")
        return None


def _parse_legacy(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        symbol = r.get("SYMBOL")
        series = r.get("SERIES")
        if not symbol:
            continue
        try:
            trade_date = datetime.strptime(r.get("TIMESTAMP", ""), "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            continue

        rows.append({
            "symbol": symbol,
            "trade_date": trade_date,
            "series": series,
            "instrument_type": "EQ" if series == "EQ" else series,
            "segment": "CM",
            "open": _f(r.get("OPEN")),
            "high": _f(r.get("HIGH")),
            "low": _f(r.get("LOW")),
            "close": _f(r.get("CLOSE")),
            "last_price": _f(r.get("LAST")),
            "prev_close": _f(r.get("PREVCLOSE")),
            "settlement_price": None,
            "volume": _i(r.get("TOTTRDQTY")),
            "value": _f(r.get("TOTTRDVAL")),
            "num_trades": _i(r.get("TOTALTRADES")),
            "open_interest": None,
            "change_in_oi": None,
            "isin": r.get("ISIN"),
            "expiry_date": None,
            "strike_price": None,
            "option_type": None,
            "format_version": "legacy",
            "raw_json": json.dumps(r, ensure_ascii=False),
        })
    return rows


def _parse_udiff(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        sgmt = r.get("Sgmt")
        if sgmt and sgmt != "CM":
            # UDIFF can include derivatives; equity-only per user spec
            continue
        symbol = r.get("TckrSymb")
        if not symbol:
            continue
        # TradDt is YYYY-MM-DD already
        trade_date = (r.get("TradDt") or "").strip()
        if not trade_date:
            continue

        rows.append({
            "symbol": symbol,
            "trade_date": trade_date,
            "series": r.get("SctySrs"),
            "instrument_type": r.get("FinInstrmTp"),
            "segment": sgmt or "CM",
            "open": _f(r.get("OpnPric")),
            "high": _f(r.get("HghPric")),
            "low": _f(r.get("LwPric")),
            "close": _f(r.get("ClsPric")),
            "last_price": _f(r.get("LastPric")),
            "prev_close": _f(r.get("PrvsClsgPric")),
            "settlement_price": _f(r.get("SttlmPric")),
            "volume": _i(r.get("TtlTradgVol")),
            "value": _f(r.get("TtlTrfVal")),
            "num_trades": _i(r.get("TtlNbOfTxsExctd")),
            "open_interest": _i(r.get("OpnIntrst")),
            "change_in_oi": _i(r.get("ChngInOpnIntrst")),
            "isin": r.get("ISIN"),
            "expiry_date": r.get("XpryDt"),
            "strike_price": _f(r.get("StrkPric")),
            "option_type": r.get("OptnTp"),
            "format_version": "udiff",
            "raw_json": json.dumps(r, ensure_ascii=False),
        })
    return rows


def _f(v: Optional[str]) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _i(v: Optional[str]) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


# --- Storage ---------------------------------------------------------------

def store_rows(rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = [
        "symbol", "trade_date", "series", "instrument_type", "segment",
        "open", "high", "low", "close", "last_price", "prev_close",
        "settlement_price", "volume", "value", "num_trades",
        "open_interest", "change_in_oi", "isin", "expiry_date",
        "strike_price", "option_type", "format_version", "raw_json",
    ]
    placeholders = ",".join("?" * len(cols))
    col_list = ",".join(cols)
    sql = (
        f"INSERT INTO bhavcopy_rows ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT(symbol, trade_date, series, instrument_type) DO NOTHING"
    )
    inserted = 0
    with get_conn() as conn:
        for r in rows:
            try:
                conn.execute(sql, [r.get(c) for c in cols])
                inserted += 1
            except Exception as e:
                log.debug("skipped row %s: %s", r.get("symbol"), e)
    return inserted


def mark_date_done(trade_date: str, format_version: str, row_count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO bhavcopy_dates
               (trade_date, format_version, row_count) VALUES (?, ?, ?)""",
            (trade_date, format_version, row_count),
        )


def date_already_done(trade_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM bhavcopy_dates WHERE trade_date = ?", (trade_date,)
        ).fetchone()
        return row is not None


# --- Public flow per date ---------------------------------------------------

def ingest_date(d: datetime) -> tuple[bool, str]:
    """Fetch + archive + parse + store for a single date. Idempotent.

    Returns (ok, status_message).
    """
    iso_date = d.strftime("%Y-%m-%d")
    if date_already_done(iso_date):
        return True, f"{iso_date} already ingested"

    fetched = fetch_for_date(d)
    if not fetched:
        return False, f"{iso_date} no data (holiday/weekend/not-published)"

    zip_bytes, filename, fmt = fetched
    save_raw_zip(d, filename, zip_bytes)

    csv_text = _unzip_csv(zip_bytes)
    if not csv_text:
        return False, f"{iso_date} bad zip"

    rows = _parse_udiff(csv_text) if fmt == "udiff" else _parse_legacy(csv_text)
    if not rows:
        return False, f"{iso_date} no rows parsed"

    inserted = store_rows(rows)
    mark_date_done(iso_date, fmt, len(rows))
    return True, f"{iso_date} ok: {inserted}/{len(rows)} rows ({fmt})"


# --- Modes -----------------------------------------------------------------

def run_recent() -> tuple[bool, str]:
    """Fetch the most recent published trading day (today, or walk back up to 5 days)."""
    today = datetime.now(timezone.utc).astimezone()
    for offset in range(0, 5):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        ok, msg = ingest_date(d)
        log.info(msg)
        if ok and "ok" in msg:
            return True, msg
    return False, "no recent bhav copy found"


def run_backfill(days: int) -> tuple[int, int]:
    """Iterate from N days ago up to yesterday, ingesting each weekday.

    Returns (success_count, attempt_count).
    """
    log.info("starting backfill: %d days", days)
    today = datetime.now(timezone.utc).astimezone()
    success = 0
    attempts = 0
    for offset in range(days, 0, -1):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        attempts += 1
        ok, msg = ingest_date(d)
        log.info(msg)
        if ok:
            success += 1
        time.sleep(REQUEST_PAUSE_SECONDS)
    log.info("backfill complete: %d/%d weekdays ingested", success, attempts)
    return success, attempts


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE equity bhav copy ingestion")
    parser.add_argument("--backfill", type=int, metavar="DAYS",
                        help="Backfill last N calendar days")
    parser.add_argument("--date", type=str, metavar="YYYY-MM-DD",
                        help="Ingest a specific date")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.backfill:
        run_backfill(args.backfill)
    elif args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d")
        ok, msg = ingest_date(d)
        log.info(msg)
    else:
        ok, msg = run_recent()
        log.info(msg)


if __name__ == "__main__":
    main()
