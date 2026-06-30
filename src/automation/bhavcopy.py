"""NSE equity bhav copy ingestion — primary source: sec_bhavdata_full.

Per-day flow:
  1. Try sec_bhavdata_full_DDMMYYYY.csv      ← has DELIV_QTY + DELIV_PER (primary)
  2. Fall back to UDIFF BhavCopy_NSE_CM_*.csv.zip   ← no delivery (post-2024-07)
  3. Fall back to legacy cm*bhav.csv.zip             ← no delivery (pre-2024-07)

Storage:
  - Raw file saved to /opt/hermes/data/bhavcopy/YYYY/MMM/<filename>
  - Parsed rows into bhavcopy_rows table; deliv_qty/deliv_per NULL when source
    is one of the fallbacks
  - bhavcopy_dates table tracks completion (idempotent)

Usage:
    python -m src.automation.bhavcopy                  # most recent trading day
    python -m src.automation.bhavcopy --backfill 1830  # 5 years
    python -m src.automation.bhavcopy --date 2024-01-08
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
REQUEST_PAUSE_SECONDS = 1.5


# --- URL builders -----------------------------------------------------------

def _sec_bhav_full_url(d: datetime) -> str:
    """Primary file — includes delivery."""
    return (
        f"https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"
    )


def _udiff_url(d: datetime) -> str:
    """UDIFF format (post-July-2024). No delivery."""
    return (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"
    )


def _legacy_url(d: datetime) -> str:
    """Legacy bhav copy (pre-July-2024). No delivery."""
    return (
        f"https://nsearchives.nseindia.com/content/historical/EQUITIES/"
        f"{d.strftime('%Y')}/{d.strftime('%b').upper()}/"
        f"cm{d.strftime('%d')}{d.strftime('%b').upper()}{d.strftime('%Y')}bhav.csv.zip"
    )


def _mto_url(d: datetime) -> str:
    """MTO security-wise delivery position — the PRE-2020 delivery source.
    Merged into legacy bhav rows (fills deliv_qty/deliv_per) so DVPT is
    computable back to ~2005. Header: 'Security Wise Delivery Position...'."""
    return (f"https://nsearchives.nseindia.com/archives/equities/mto/"
            f"MTO_{d.strftime('%d%m%Y')}.DAT")


def _archive_path(d: datetime, filename: str) -> Path:
    p = ARCHIVE_DIR / d.strftime("%Y") / d.strftime("%b").upper()
    p.mkdir(parents=True, exist_ok=True)
    return p / filename


# --- HTTP fetch -------------------------------------------------------------

def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/csv,application/zip,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            },
            timeout=timeout,
        )
    except requests.RequestException as e:
        log.debug("fetch error %s: %s", url, e)
        return None
    if r.status_code != 200 or len(r.content) < 100:
        return None
    return r.content


def _looks_like_sec_bhav(raw: bytes) -> bool:
    """CL-MDC-11: robust header sniff for the sec_bhavdata_full CSV. The old
    check read only the first 6 bytes, so a UTF-8 BOM or any leading whitespace
    would make it miss the delivery-bearing source and silently fall through to
    a no-delivery format. Decode a generous prefix, strip a BOM, and look for
    the SYMBOL header token at the start of the first non-empty line."""
    head = raw[:512].decode("utf-8-sig", errors="ignore").lstrip("﻿\r\n\t ")
    return head.upper().startswith("SYMBOL")


def fetch_for_date(d: datetime) -> Optional[tuple[bytes, str, str, bool]]:
    """Return (bytes, filename, format_version, has_delivery) or None.

    Tries sec_bhavdata_full first (has delivery), then format-specific fallbacks.
    """
    # 1. sec_bhavdata_full — preferred, has delivery
    sf_url = _sec_bhav_full_url(d)
    raw = _try_fetch(sf_url)
    if raw and _looks_like_sec_bhav(raw):
        filename = sf_url.rsplit("/", 1)[-1]
        return raw, filename, "sec_bhavdata_full", True

    # 2. UDIFF bhav copy zip — no delivery
    udiff_url = _udiff_url(d)
    raw = _try_fetch(udiff_url)
    if raw and raw[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        filename = udiff_url.rsplit("/", 1)[-1]
        return raw, filename, "udiff", False

    # 3. Legacy bhav copy zip — no delivery
    leg_url = _legacy_url(d)
    raw = _try_fetch(leg_url)
    if raw and raw[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        filename = leg_url.rsplit("/", 1)[-1]
        return raw, filename, "legacy", False

    return None


# --- Archive raw file -------------------------------------------------------

def save_raw(d: datetime, filename: str, content: bytes) -> Path:
    target = _archive_path(d, filename)
    if not target.exists():
        target.write_bytes(content)
        log.info("archived %s (%d bytes)", target, len(content))
    return target


# --- Parsers ---------------------------------------------------------------

def _unzip_csv(zip_bytes: bytes) -> Optional[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_name = next((n for n in zf.namelist() if n.lower().endswith(".csv")), None)
            if not csv_name:
                return None
            return zf.read(csv_name).decode("utf-8", errors="ignore")
    except zipfile.BadZipFile:
        return None


def _parse_sec_bhavdata_full(csv_text: str) -> list[dict]:
    """Parse the rich sec_bhavdata_full CSV. Columns include DELIV_QTY/DELIV_PER."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        symbol = r.get("SYMBOL")
        series = r.get("SERIES")
        if not symbol or not series:
            continue
        try:
            trade_date = datetime.strptime(r.get("DATE1", ""), "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        rows.append({
            "symbol": symbol,
            "trade_date": trade_date,
            "series": series,
            "instrument_type": series,
            "segment": "CM",
            "open": _f(r.get("OPEN_PRICE")),
            "high": _f(r.get("HIGH_PRICE")),
            "low": _f(r.get("LOW_PRICE")),
            "close": _f(r.get("CLOSE_PRICE")),
            "last_price": _f(r.get("LAST_PRICE")),
            "prev_close": _f(r.get("PREV_CLOSE")),
            "avg_price": _f(r.get("AVG_PRICE")),
            "settlement_price": None,
            "volume": _i(r.get("TTL_TRD_QNTY")),
            "value": _f_lakhs(r.get("TURNOVER_LACS")),  # convert lakhs → rupees
            "num_trades": _i(r.get("NO_OF_TRADES")),
            "deliv_qty": _i(r.get("DELIV_QTY")),
            "deliv_per": _f(r.get("DELIV_PER")),
            "open_interest": None,
            "change_in_oi": None,
            "isin": None,  # not in sec_bhavdata_full
            "expiry_date": None,
            "strike_price": None,
            "option_type": None,
            "format_version": "sec_bhavdata_full",
            "raw_json": json.dumps(r, ensure_ascii=False),
        })
    return rows


def _parse_legacy_bhav(csv_text: str) -> list[dict]:
    """Parse legacy cm*bhav.csv (no delivery)."""
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
            "instrument_type": series,
            "segment": "CM",
            "open": _f(r.get("OPEN")),
            "high": _f(r.get("HIGH")),
            "low": _f(r.get("LOW")),
            "close": _f(r.get("CLOSE")),
            "last_price": _f(r.get("LAST")),
            "prev_close": _f(r.get("PREVCLOSE")),
            "avg_price": None,
            "settlement_price": None,
            "volume": _i(r.get("TOTTRDQTY")),
            "value": _f(r.get("TOTTRDVAL")),
            "num_trades": _i(r.get("TOTALTRADES")),
            "deliv_qty": None,
            "deliv_per": None,
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
    """Parse UDIFF BhavCopy_NSE_CM (post-July-2024, no delivery)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        sgmt = r.get("Sgmt")
        if sgmt and sgmt != "CM":
            continue
        symbol = r.get("TckrSymb")
        if not symbol:
            continue
        # CL-MDC-04/14: normalize TradDt to ISO YYYY-MM-DD like the other two
        # parsers, instead of storing it verbatim. UDIFF emits ISO already, but
        # format drift (or a stray time component) would silently corrupt
        # trade_date — breaking the ON CONFLICT key and every calendar-window
        # string comparison (b[0] >= cutoff) downstream. Skip the row on failure.
        trade_date = _norm_iso_date(r.get("TradDt"))
        if not trade_date:
            continue
        rows.append({
            "symbol": symbol,
            "trade_date": trade_date,
            "series": r.get("SctySrs"),
            "instrument_type": r.get("FinInstrmTp") or r.get("SctySrs"),
            "segment": sgmt or "CM",
            "open": _f(r.get("OpnPric")),
            "high": _f(r.get("HghPric")),
            "low": _f(r.get("LwPric")),
            "close": _f(r.get("ClsPric")),
            "last_price": _f(r.get("LastPric")),
            "prev_close": _f(r.get("PrvsClsgPric")),
            "avg_price": None,
            "settlement_price": _f(r.get("SttlmPric")),
            "volume": _i(r.get("TtlTradgVol")),
            "value": _f(r.get("TtlTrfVal")),
            "num_trades": _i(r.get("TtlNbOfTxsExctd")),
            "deliv_qty": None,
            "deliv_per": None,
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


def _parse_mto(text: str) -> dict:
    """Parse an MTO_*.DAT delivery file → {(symbol, series): {deliv_qty,
    deliv_per, qty_traded}}. Data rows are record-type 20:
    `20,SrNo,Symbol,Series,QtyTraded,DeliverableQty,%Deliv`."""
    out = {}
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 7 or parts[0].strip() != "20":
            continue
        out[(parts[2].strip(), parts[3].strip())] = {
            "qty_traded": _i(parts[4]),
            "deliv_qty": _i(parts[5]),
            "deliv_per": _f(parts[6]),
        }
    return out


def _merge_mto(rows: list[dict], mto: dict) -> tuple[int, int]:
    """Additively fill deliv_qty/deliv_per on parsed bhav rows from the MTO map,
    keyed on (symbol, series). Returns (merged, qty_mismatches) — MTO's traded
    quantity should equal the bhav volume, a built-in join validation."""
    merged = mismatch = 0
    for r in rows:
        m = mto.get((r.get("symbol"), r.get("series")))
        if not m:
            continue
        r["deliv_qty"] = m["deliv_qty"]
        r["deliv_per"] = m["deliv_per"]
        if (m["qty_traded"] is not None and r.get("volume") is not None
                and m["qty_traded"] != r["volume"]):
            mismatch += 1
        merged += 1
    return merged, mismatch


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _f_lakhs(v):
    """Convert a value in lakhs to rupees. TURNOVER_LACS comes as e.g. '1234.56'."""
    f = _f(v)
    if f is None:
        return None
    return f * 100000.0


def _i(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _norm_iso_date(v) -> Optional[str]:
    """Normalize a date string to ISO YYYY-MM-DD. Accepts already-ISO values
    (possibly with a time/zone suffix) and the d-Mon-Y form NSE uses elsewhere.
    Returns None on anything unparseable so the caller can skip the row rather
    than persist a malformed trade_date (CL-MDC-04)."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    head = s.split("T", 1)[0].split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(head, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# --- Storage ---------------------------------------------------------------

_COLS = [
    "symbol", "trade_date", "series", "instrument_type", "segment",
    "open", "high", "low", "close", "last_price", "prev_close", "avg_price",
    "settlement_price", "volume", "value", "num_trades",
    "deliv_qty", "deliv_per",
    "open_interest", "change_in_oi", "isin", "expiry_date",
    "strike_price", "option_type", "format_version", "raw_json",
]


def store_rows(rows: list[dict]) -> int:
    if not rows:
        return 0
    placeholders = ",".join("?" * len(_COLS))
    sql = (
        f"INSERT INTO bhavcopy_rows ({','.join(_COLS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(symbol, trade_date, series, instrument_type) DO NOTHING"
    )
    n = 0
    failures = 0
    with get_conn() as conn:
        for r in rows:
            try:
                conn.execute(sql, [r.get(c) for c in _COLS])
                n += 1
            except Exception as e:
                failures += 1
                log.debug("skip row %s/%s: %s", r.get("symbol"), r.get("trade_date"), e)
    # CL-MDC-15: a handful of bad rows is tolerable, but losing a meaningful
    # fraction of a day silently is not — surface it at WARNING when >1%.
    if failures and failures > max(1, len(rows) // 100):
        log.warning("store_rows: %d/%d rows failed to insert (%.1f%%)",
                    failures, len(rows), 100.0 * failures / len(rows))
    return n


def mark_date_done(trade_date: str, format_version: str, row_count: int, has_delivery: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO bhavcopy_dates
               (trade_date, format_version, row_count, has_delivery)
               VALUES (?, ?, ?, ?)""",
            (trade_date, format_version, row_count, 1 if has_delivery else 0),
        )


def date_already_done(trade_date: str, *, require_delivery: bool = False) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT has_delivery FROM bhavcopy_dates WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()
    if not row:
        return False
    if require_delivery and not row["has_delivery"]:
        return False
    return True


# --- Per-date ingestion -----------------------------------------------------

def ingest_date(d: datetime) -> tuple[bool, str, int]:
    """Ingest one date. Returns (ok, msg, inserted) where `inserted` is the
    number of rows actually written this call (CL-MDC-07: callers test the
    structured count instead of sniffing the message for the substring "rows",
    which also matched "no rows parsed"). already-ingested / no-data → 0."""
    iso_date = d.strftime("%Y-%m-%d")
    if date_already_done(iso_date):
        return True, f"{iso_date} already ingested", 0

    fetched = fetch_for_date(d)
    if not fetched:
        return False, f"{iso_date} no data (holiday/weekend/not-published)", 0

    content, filename, fmt, has_delivery = fetched
    save_raw(d, filename, content)

    if fmt == "sec_bhavdata_full":
        csv_text = content.decode("utf-8", errors="ignore")
        rows = _parse_sec_bhavdata_full(csv_text)
    elif fmt == "udiff":
        csv_text = _unzip_csv(content)
        rows = _parse_udiff(csv_text) if csv_text else []
    elif fmt == "legacy":
        csv_text = _unzip_csv(content)
        rows = _parse_legacy_bhav(csv_text) if csv_text else []
    else:
        rows = []

    # Pre-2020 (or any no-delivery) date: enrich with the MTO delivery file so
    # DVPT is computable historically (back to ~2005). Additive — fills only
    # deliv_qty/deliv_per on the already-parsed rows. The 2020+ delivery path is
    # untouched: it already has has_delivery=True and skips this block.
    if rows and not has_delivery:
        mto_raw = _try_fetch(_mto_url(d))
        if mto_raw:
            save_raw(d, f"MTO_{d.strftime('%d%m%Y')}.DAT", mto_raw)
            merged, mismatch = _merge_mto(
                rows, _parse_mto(mto_raw.decode("latin-1", errors="ignore")))
            if merged:
                has_delivery = True
                fmt = f"{fmt}+mto"
                if mismatch:
                    log.warning("%s: MTO qty mismatch on %d/%d rows",
                                iso_date, mismatch, merged)

    if not rows:
        return False, f"{iso_date} no rows parsed ({fmt})", 0

    inserted = store_rows(rows)
    mark_date_done(iso_date, fmt, len(rows), has_delivery)
    tag = "✓delivery" if has_delivery else "no-delivery"
    return True, f"{iso_date} {inserted}/{len(rows)} rows ({fmt}, {tag})", inserted


# --- Modes -----------------------------------------------------------------

def run_recent() -> tuple[bool, str]:
    today = datetime.now(timezone.utc).astimezone()
    for offset in range(0, 7):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        ok, msg, inserted = ingest_date(d)
        log.info(msg)
        if ok and inserted > 0:
            return True, msg
    return False, "no recent bhav copy found"


def run_backfill(days: int) -> tuple[int, int]:
    log.info("backfill starting: %d calendar days", days)
    today = datetime.now(timezone.utc).astimezone()
    success = 0
    attempts = 0
    for offset in range(days, 0, -1):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        attempts += 1
        ok, msg, _inserted = ingest_date(d)
        if ok:
            success += 1
        log.info(msg)
        time.sleep(REQUEST_PAUSE_SECONDS)
    log.info("backfill done: %d/%d weekdays ingested", success, attempts)
    return success, attempts


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", type=int, metavar="DAYS")
    p.add_argument("--date", type=str, metavar="YYYY-MM-DD")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.backfill:
        run_backfill(args.backfill)
    elif args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d")
        ok, msg, _inserted = ingest_date(d)
        log.info(msg)
    else:
        ok, msg = run_recent()
        log.info(msg)


if __name__ == "__main__":
    main()
