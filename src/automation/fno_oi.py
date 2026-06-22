"""F&O Open-Interest feed — the IDENTITY channel MEP's price tape can't see.

MEP / DVPT *infer* accumulation from the price tape; this *observes* positioning
directly via NSE F&O open interest. For each underlying we aggregate its STOCK
FUTURES (STF) across expiries and read the day's OI change against the day's price
change — the classic four-quadrant map:

    ↑price ↑OI = LONG_BUILDUP   (fresh longs — accumulation)
    ↓price ↑OI = SHORT_BUILDUP  (fresh shorts — distribution)
    ↓price ↓OI = LONG_UNWIND    (longs exiting)
    ↑price ↓OI = SHORT_COVER    (shorts exiting — short-covering bounce)

Plus a Put/Call OI ratio (PCR) from the stock options (STO) as a sentiment read.

DESCRIPTOR-ONLY (D62 discipline) — like MEP, this characterises/confirms; it does
NOT rank or pick until it passes the purged-walk-forward + Deflated-Sharpe gate.
It is the channel most LIKELY to carry real predictive alpha (it names the strong
hand), but that has to be earned through the gate, not assumed.

Source: NSE UDiFF F&O bhavcopy (the same archive host as the cash bhav) —
    https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip
The UDiFF format starts mid-2024; pre-UDiFF history would need the legacy
DERIVATIVES URL + a second parser (deferred — OI is a near-term signal anyway).
Price change is read from the cash bhav we already store (bhavcopy_rows), so this
must run AFTER the cash bhav for the day.

Stored into fno_oi_signals (its OWN table — never touches the cash/stock_signals
hot tables, nor the parallel-owned deals.py named-flow feed).

Usage:
    python -m src.automation.fno_oi                 # latest cash-bhav date
    python -m src.automation.fno_oi --backfill      # every UDiFF-era trading day
    python -m src.automation.fno_oi --date 2026-06-19
"""

import argparse
import csv
import io
import logging
import time
import zipfile
from datetime import datetime
from typing import Optional

import requests

from src.core.db import DB_PATH, get_conn

log = logging.getLogger("hermes.fno_oi")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
ARCHIVE_DIR = DB_PATH.parent / "fno"
_UDIFF_FIRST = "2024-07-01"        # NSE UDiFF F&O era (pre-that needs the legacy parser)
_FLAT_PRICE = 0.10                 # |price move| < this % ⇒ price treated as flat
_FLAT_OI = 0.50                    # |OI change| < this % ⇒ OI treated as flat


# --- fetch ------------------------------------------------------------------

def _fo_udiff_url(d: datetime) -> str:
    return (f"https://nsearchives.nseindia.com/content/fo/"
            f"BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip")


def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/zip,text/csv,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }, timeout=timeout)
    except requests.RequestException as e:
        log.debug("fetch error %s: %s", url, e)
        return None
    if r.status_code != 200 or len(r.content) < 1000:
        return None
    return r.content


def fetch_fo_for_date(d: datetime) -> Optional[bytes]:
    """The UDiFF F&O zip bytes for date d, or None (holiday / not-yet-posted)."""
    raw = _try_fetch(_fo_udiff_url(d))
    if raw and raw[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        return raw
    return None


def _csv_rows(raw: bytes) -> list:
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = z.namelist()[0]
    text = z.read(name).decode("utf-8", "ignore")
    return list(csv.DictReader(io.StringIO(text)))


# --- aggregate per underlying ----------------------------------------------

def _num(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "NA", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def aggregate_oi(rows: list) -> dict:
    """Per-underlying aggregation of stock FUTURES OI (summed across expiries) and
    stock OPTIONS OI (for PCR). Returns {symbol: {fut_oi, fut_oi_chg, n_fut,
    und_price, call_oi, put_oi}}."""
    agg: dict = {}
    for r in rows:
        tp = r.get("FinInstrmTp")
        sym = r.get("TckrSymb")
        if not sym:
            continue
        a = agg.setdefault(sym, {"fut_oi": 0.0, "fut_oi_chg": 0.0, "n_fut": 0,
                                 "und_price": None, "call_oi": 0.0, "put_oi": 0.0,
                                 "has_fut": False, "has_opt": False})
        oi = _num(r.get("OpnIntrst")) or 0.0
        if tp == "STF":                                  # stock future
            a["fut_oi"] += oi
            a["fut_oi_chg"] += (_num(r.get("ChngInOpnIntrst")) or 0.0)
            a["n_fut"] += 1
            a["has_fut"] = True
            up = _num(r.get("UndrlygPric"))
            if up:
                a["und_price"] = up
        elif tp == "STO":                                # stock option
            a["has_opt"] = True
            if r.get("OptnTp") == "CE":
                a["call_oi"] += oi
            elif r.get("OptnTp") == "PE":
                a["put_oi"] += oi
    return agg


# --- quadrant ---------------------------------------------------------------

def quadrant(price_chg_pct: Optional[float], oi_chg_pct: Optional[float]) -> Optional[str]:
    """The four-quadrant positioning read (signed, descriptor)."""
    if price_chg_pct is None or oi_chg_pct is None:
        return None
    if abs(oi_chg_pct) < _FLAT_OI or abs(price_chg_pct) < _FLAT_PRICE:
        return "FLAT"
    up, oi_up = price_chg_pct > 0, oi_chg_pct > 0
    if up and oi_up:
        return "LONG_BUILDUP"
    if (not up) and oi_up:
        return "SHORT_BUILDUP"
    if (not up) and (not oi_up):
        return "LONG_UNWIND"
    return "SHORT_COVER"


def quadrant_read(q: Optional[str]) -> str:
    return {
        "LONG_BUILDUP": "long buildup — price up on rising OI (fresh longs)",
        "SHORT_BUILDUP": "short buildup — price down on rising OI (fresh shorts)",
        "LONG_UNWIND": "long unwinding — price down on falling OI (longs exiting)",
        "SHORT_COVER": "short covering — price up on falling OI (shorts exiting)",
        "FLAT": "flat — no decisive OI/price move",
    }.get(q or "", "")


# --- storage ----------------------------------------------------------------

_OI_COLS = [
    "symbol", "trade_date",
    "fut_oi", "fut_oi_chg", "fut_oi_chg_pct",
    "und_price", "price_chg_pct", "quadrant",
    "call_oi", "put_oi", "pcr", "n_fut_contracts",
]

_ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS fno_oi_signals (
    symbol TEXT NOT NULL, trade_date TEXT NOT NULL,
    fut_oi REAL, fut_oi_chg REAL, fut_oi_chg_pct REAL,
    und_price REAL, price_chg_pct REAL, quadrant TEXT,
    call_oi REAL, put_oi REAL, pcr REAL, n_fut_contracts INTEGER,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_fnooi_date ON fno_oi_signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_fnooi_quad ON fno_oi_signals(trade_date, quadrant);
"""


def ensure_table() -> None:
    with get_conn() as conn:
        conn.executescript(_ENSURE_SQL)


def _price_chg_for_date(conn, trade_date: str) -> dict:
    """{symbol: price_chg_pct} from the cash bhav we already store (close vs
    prev_close), so the OI quadrant uses the SAME price series as MEP/DVPT."""
    out = {}
    for r in conn.execute(
        """SELECT symbol, close, prev_close FROM bhavcopy_rows
           WHERE trade_date=? AND series='EQ' AND (segment='CM' OR segment IS NULL)""",
        (trade_date,)).fetchall():
        c, p = r["close"], r["prev_close"]
        if c is not None and p and p > 0:
            out[r["symbol"]] = (c / p - 1.0) * 100.0
    return out


def compute_for_date(trade_date: str) -> int:
    """Fetch the F&O bhav for trade_date, aggregate STF OI per underlying, pair
    with the cash price change, store the quadrant. Idempotent (INSERT OR REPLACE)."""
    ensure_table()
    d = datetime.strptime(trade_date, "%Y-%m-%d")
    raw = fetch_fo_for_date(d)
    if not raw:
        log.info("no F&O bhav for %s (holiday / not posted)", trade_date)
        return 0
    agg = aggregate_oi(_csv_rows(raw))
    with get_conn() as conn:
        price_chg = _price_chg_for_date(conn, trade_date)
        out = []
        for sym, a in agg.items():
            if not a["has_fut"]:
                continue
            prior_oi = a["fut_oi"] - a["fut_oi_chg"]
            oi_chg_pct = (a["fut_oi_chg"] / prior_oi * 100.0) if prior_oi > 0 else None
            pc = price_chg.get(sym)
            call_oi, put_oi = a["call_oi"], a["put_oi"]
            pcr = (put_oi / call_oi) if call_oi > 0 else None
            out.append([
                sym, trade_date,
                a["fut_oi"], a["fut_oi_chg"], oi_chg_pct,
                a["und_price"], pc, quadrant(pc, oi_chg_pct),
                (call_oi or None), (put_oi or None), pcr, a["n_fut"],
            ])
        if out:
            ph = ",".join("?" * len(_OI_COLS))
            conn.executemany(
                f"INSERT OR REPLACE INTO fno_oi_signals ({','.join(_OI_COLS)}) VALUES ({ph})", out)
    log.info("F&O OI %s: %d underlyings stored", trade_date, len(out))
    return len(out)


def run_today() -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return False, "no cash bhav found"
    n = compute_for_date(row["d"])
    return True, f"F&O OI: {n} underlyings for {row['d']}"


def run_backfill() -> tuple[int, int]:
    """Walk every cash-bhav trading day in the UDiFF era and pull its F&O OI."""
    ensure_table()
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? ORDER BY trade_date",
            (_UDIFF_FIRST,)).fetchall()]
    log.info("F&O OI backfill: %d trading days from %s", len(dates), _UDIFF_FIRST)
    days = total = 0
    for i, d in enumerate(dates, 1):
        with get_conn() as conn:
            exists = conn.execute(
                "SELECT 1 FROM fno_oi_signals WHERE trade_date=? LIMIT 1", (d,)).fetchone()
        if exists:
            continue
        try:
            n = compute_for_date(d)
            if n:
                days += 1
                total += n
        except Exception as e:
            log.warning("F&O OI failed for %s: %s", d, e)
        if i % 25 == 0:
            log.info("  progress: %d / %d days, %d rows", i, len(dates), total)
        time.sleep(1.0)        # be gentle on the NSE archive
    log.info("F&O OI backfill complete: %d days, %d rows", days, total)
    return days, total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true", help="every UDiFF-era trading day")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.backfill:
        run_backfill()
    elif args.date:
        compute_for_date(args.date)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
