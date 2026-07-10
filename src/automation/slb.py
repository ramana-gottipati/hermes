"""Dataset D-04 — SLB (Securities Lending & Borrowing) daily volumes + open
positions from the NSE archives (charter §8 data sprint; S94).

India's only short-interest proxy: borrow demand and outstanding lent stock.
Two official EOD files per trading day (the deals.py-class channel — static
primary-source archives, no cookie dance, no throttle exposure):

  * ``SLBM_BC_ddmmyyyy.DAT``   (archives/slbs/bhavcopy/)  — per security ×
    tenure series: lending-FEE quotes (prev/open/high/low/close, ₹/share),
    matched quantity and traded value. Headerless CSV, zero-padded floats.
  * ``slb_openpos_ddmmyyyy.csv`` (archives/slbs/open_pos/) — per security ×
    series: outstanding lent quantity at end of day (the short-interest STOCK
    where the bhavcopy is the FLOW).

DESCRIPTIVE DATA ONLY — no study has been run on this feed; the charter's
"squeeze + crowding flags" are future research consumers, not this module.
House hardening: per-day commits (a write never spans a fetch — the 2026-07-02
outage lesson), a 404 = holiday/not-published = clean skip, one bad day never
kills a run.

Run (VPS):
  python -m src.automation.slb --selftest
  python -m src.automation.slb --ingest                 # today (IST)
  python -m src.automation.slb --ingest --date 2026-07-09
  python -m src.automation.slb --ingest --window 2026-06-09 2026-07-09
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta

import requests

try:
    from src.core.db import get_conn
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore

log = logging.getLogger("hermes.slb")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "Chrome/122 Safari/537.36",
      "Referer": "https://www.nseindia.com/"}

_BHAV_URL = "https://nsearchives.nseindia.com/archives/slbs/bhavcopy/SLBM_BC_{d}.DAT"
_OPOS_URL = "https://nsearchives.nseindia.com/archives/slbs/open_pos/slb_openpos_{d}.csv"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS slb_volumes (
    as_of     TEXT NOT NULL,          -- trade date (from the file's own date stamp)
    symbol    TEXT NOT NULL,
    series    TEXT,                   -- SLB tenure series (G1 / X1..XN — expiry buckets)
    expiry    TEXT,                   -- contract expiry, ISO
    fee_prev  REAL, fee_open REAL, fee_high REAL, fee_low REAL, fee_close REAL,
    qty       REAL,                   -- matched (lent = borrowed) shares
    value     REAL,                   -- traded value
    UNIQUE(as_of, symbol, series)
);
CREATE INDEX IF NOT EXISTS idx_slbv_sym ON slb_volumes(symbol, as_of);
CREATE TABLE IF NOT EXISTS slb_open_positions (
    as_of    TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    series   TEXT,
    open_qty REAL,                    -- outstanding lent shares at end of day
    UNIQUE(as_of, symbol, series)
);
CREATE INDEX IF NOT EXISTS idx_slbop_sym ON slb_open_positions(symbol, as_of);
"""

_MONTHS = {m: i for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)


def _num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _expiry_iso(s):
    """'04-AUG-2026' -> '2026-08-04' (None when unparseable)."""
    try:
        dd, mon, yyyy = (s or "").strip().split("-")
        return f"{int(yyyy):04d}-{_MONTHS[mon.upper()]:02d}-{int(dd):02d}"
    except Exception:  # noqa: BLE001
        return None


def parse_bhav(text: str, as_of: str) -> list[dict]:
    """The headerless SLBM_BC file: name, symbol, series, expiry, flag,
    fee prev/open/high/low/close, <blank>, qty, value."""
    out = []
    for ln in text.splitlines():
        parts = ln.split(",")
        if len(parts) < 13:
            continue
        sym = parts[1].strip()
        if not sym:
            continue
        out.append({
            "as_of": as_of, "symbol": sym, "series": parts[2].strip() or None,
            "expiry": _expiry_iso(parts[3]),
            "fee_prev": _num(parts[5]), "fee_open": _num(parts[6]),
            "fee_high": _num(parts[7]), "fee_low": _num(parts[8]),
            "fee_close": _num(parts[9]),
            "qty": _num(parts[11]), "value": _num(parts[12]),
        })
    return out


def parse_openpos(text: str, as_of: str) -> list[dict]:
    """Headered CSV: Sr no, Security, Series, Outstanding Quantity…"""
    out = []
    for i, ln in enumerate(text.splitlines()):
        parts = ln.split(",")
        if len(parts) < 4 or (i == 0 and parts[0].strip().lower().startswith("sr")):
            continue
        sym = parts[1].strip()
        if not sym:
            continue
        out.append({"as_of": as_of, "symbol": sym,
                    "series": parts[2].strip() or None,
                    "open_qty": _num(parts[3])})
    return out


def _fetch(url: str):
    r = requests.get(url, headers=UA, timeout=30)
    if r.status_code == 404:
        return None                     # holiday / not published — clean skip
    r.raise_for_status()
    return r.text


def ingest_day(conn, day: date) -> dict:
    """Fetch + upsert both files for one date. Per-day commit is the CALLER's
    job (the CLI commits after each day so a lock never spans a fetch)."""
    d = day.strftime("%d%m%Y")
    iso = day.isoformat()
    stats = {"date": iso, "vol_rows": 0, "opos_rows": 0, "skipped": False}
    bhav = _fetch(_BHAV_URL.format(d=d))
    opos = _fetch(_OPOS_URL.format(d=d))
    if bhav is None and opos is None:
        stats["skipped"] = True
        return stats
    ensure_schema(conn)
    if bhav:
        rows = parse_bhav(bhav, iso)
        conn.executemany(
            "INSERT OR REPLACE INTO slb_volumes "
            "(as_of,symbol,series,expiry,fee_prev,fee_open,fee_high,fee_low,"
            " fee_close,qty,value) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(r["as_of"], r["symbol"], r["series"], r["expiry"], r["fee_prev"],
              r["fee_open"], r["fee_high"], r["fee_low"], r["fee_close"],
              r["qty"], r["value"]) for r in rows])
        stats["vol_rows"] = len(rows)
    if opos:
        rows = parse_openpos(opos, iso)
        conn.executemany(
            "INSERT OR REPLACE INTO slb_open_positions "
            "(as_of,symbol,series,open_qty) VALUES (?,?,?,?)",
            [(r["as_of"], r["symbol"], r["series"], r["open_qty"]) for r in rows])
        stats["opos_rows"] = len(rows)
    return stats


def table_stats() -> dict:
    with get_conn() as conn:
        ensure_schema(conn)
        v = conn.execute("SELECT COUNT(*), COUNT(DISTINCT symbol), MIN(as_of), "
                         "MAX(as_of) FROM slb_volumes").fetchone()
        o = conn.execute("SELECT COUNT(*), MAX(as_of) FROM slb_open_positions").fetchone()
        return {"volumes": {"rows": v[0], "symbols": v[1], "range": (v[2], v[3])},
                "open_positions": {"rows": o[0], "latest": o[1]}}


def _selftest() -> int:
    bh = ("ABB INDIA LIMITED             ,ABB       ,G1,04-AUG-2026,N,0000031.75,"
          "0000031.75,0000034.95,0000025.00,0000032.95,    ,         39660,"
          "        1065606.")
    rows = parse_bhav(bh, "2026-07-09")
    assert len(rows) == 1, rows
    r = rows[0]
    assert r["symbol"] == "ABB" and r["series"] == "G1"
    assert r["expiry"] == "2026-08-04", r["expiry"]
    assert r["fee_close"] == 32.95 and r["qty"] == 39660 and r["value"] == 1065606.0
    op = "Sr no,Security,Series,Outstanding Quantity at the end of the day\n1,360ONE,X1,2\n2,ABB,X2,10"
    rows = parse_openpos(op, "2026-07-09")
    assert len(rows) == 2 and rows[0]["symbol"] == "360ONE" and rows[1]["open_qty"] == 10.0
    print("slb selftest OK — bhav + openpos parsers, expiry ISO, zero-pad floats")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--date", help="single ISO date")
    ap.add_argument("--window", nargs=2, metavar=("FROM", "TO"), help="ISO range inclusive")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.selftest:
        raise SystemExit(_selftest())
    if not args.ingest:
        ap.print_help()
        return
    if args.window:
        d0, d1 = (date.fromisoformat(x) for x in args.window)
    elif args.date:
        d0 = d1 = date.fromisoformat(args.date)
    else:
        # default = today IST (files publish EOD IST; the 15:15 UTC timer is post-publish)
        d0 = d1 = (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()
    day, done = d0, 0
    while day <= d1:
        if day.weekday() < 5:           # Mon-Fri only
            try:
                with get_conn() as conn:      # one txn per day — never spans a fetch
                    st = ingest_day(conn, day)
                log.info("slb %s: vol=%d opos=%d%s", st["date"], st["vol_rows"],
                         st["opos_rows"], " (skipped — no files)" if st["skipped"] else "")
                done += 0 if st["skipped"] else 1
            except Exception as e:  # noqa: BLE001 — one bad day never kills the run
                log.warning("slb %s FAILED: %s", day, e)
        day += timedelta(days=1)
    log.info("slb ingest complete: %d trading day(s) written · %s", done, table_stats())


if __name__ == "__main__":
    main()
