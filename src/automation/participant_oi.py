"""Participant-wise Open Interest — the MARKET-LEVEL "who is positioned" feed.

The per-stock F&O OI tape (fno_oi.py) tells you positioning per name; THIS tells
you which class of player is net long or net short the market as a whole. NSE
publishes it daily (~5–6 PM IST) as one small file with four participant rows —
Client (retail+HNI), DII, FII, Pro — across index/stock futures & options, each
split Long vs Short. It is MARKET-AGGREGATE (not per-stock), so it drives a
market-sentiment overlay, not the per-stock tab.

The classic reads:
  • FII index-futures long:short — THE foreign-money sentiment gauge (net short =
    bearish, net long = bullish). Watch the swing, not the level.
  • FII vs Client divergence — smart money vs retail on the opposite side.
  • Index option call/put long-short — the institutional options stance.

Source: https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_<DDMMYYYY>.csv
Stored into participant_oi (its OWN table; one row per (date, client_type)).
DESCRIPTOR-ONLY (D62) — sentiment context, not a ranking/timing signal by itself.

Usage:
    python -m src.automation.participant_oi                 # latest cash-bhav date
    python -m src.automation.participant_oi --backfill      # from _BACKFILL_FROM
    python -m src.automation.participant_oi --date 2026-06-19
"""

import argparse
import csv
import io
import logging
import time
from datetime import datetime
from typing import Optional

import requests

from src.core.db import get_conn
from src.automation.fetch_retry import RetryableFetchError, raise_if_retryable  # AUD-14

log = logging.getLogger("hermes.participant_oi")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
_BACKFILL_FROM = "2024-01-01"      # ~1.5y of FII-positioning history (files are tiny)

# CSV column header → our short field (headers carry stray spaces; we strip + match).
_COLMAP = {
    "future index long": "fut_idx_long", "future index short": "fut_idx_short",
    "future stock long": "fut_stk_long", "future stock short": "fut_stk_short",
    "option index call long": "opt_idx_call_long", "option index put long": "opt_idx_put_long",
    "option index call short": "opt_idx_call_short", "option index put short": "opt_idx_put_short",
    "option stock call long": "opt_stk_call_long", "option stock put long": "opt_stk_put_long",
    "option stock call short": "opt_stk_call_short", "option stock put short": "opt_stk_put_short",
    "total long contracts": "total_long", "total short contracts": "total_short",
}

_OI_COLS = [
    "trade_date", "client_type",
    "fut_idx_long", "fut_idx_short", "fut_stk_long", "fut_stk_short",
    "opt_idx_call_long", "opt_idx_put_long", "opt_idx_call_short", "opt_idx_put_short",
    "opt_stk_call_long", "opt_stk_put_long", "opt_stk_call_short", "opt_stk_put_short",
    "total_long", "total_short",
]

_ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS participant_oi (
    trade_date TEXT NOT NULL, client_type TEXT NOT NULL,
    fut_idx_long REAL, fut_idx_short REAL, fut_stk_long REAL, fut_stk_short REAL,
    opt_idx_call_long REAL, opt_idx_put_long REAL, opt_idx_call_short REAL, opt_idx_put_short REAL,
    opt_stk_call_long REAL, opt_stk_put_long REAL, opt_stk_call_short REAL, opt_stk_put_short REAL,
    total_long REAL, total_short REAL,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (trade_date, client_type)
);
CREATE INDEX IF NOT EXISTS idx_participant_date ON participant_oi(trade_date);
"""


def ensure_table() -> None:
    with get_conn() as conn:
        conn.executescript(_ENSURE_SQL)


def _url(d: datetime) -> str:
    return (f"https://nsearchives.nseindia.com/content/nsccl/"
            f"fao_participant_oi_{d.strftime('%d%m%Y')}.csv")


def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(url, headers={
            "User-Agent": USER_AGENT, "Accept": "text/csv,*/*",
            "Accept-Language": "en-US,en;q=0.9", "Connection": "keep-alive",
        }, timeout=timeout)
    except requests.RequestException as e:
        raise RetryableFetchError(f"network error fetching {url}: {e}") from e   # AUD-14
    raise_if_retryable(r.status_code, url)   # AUD-14: 403/429/5xx = throttle/block, not no-data
    if r.status_code != 200 or len(r.content) < 200:
        return None
    return r.content


def _num(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_participant(raw: bytes) -> list:
    """Parse the participant-OI CSV → list of {client_type, <fields>} for the four
    real categories (Client/DII/FII/Pro; TOTAL is skipped — derivable)."""
    text = raw.decode("utf-8", "ignore")
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r and any(c.strip() for c in r)]
    # find the header row (has "Client Type")
    hdr_i = next((i for i, r in enumerate(rows)
                  if r and r[0].strip().lower().startswith("client type")), None)
    if hdr_i is None:
        return []
    header = [c.strip().strip('"').lower() for c in rows[hdr_i]]
    idx = {_COLMAP[h]: j for j, h in enumerate(header) if h in _COLMAP}
    out = []
    for r in rows[hdr_i + 1:]:
        ct = r[0].strip().strip('"')
        if ct.upper() not in ("CLIENT", "DII", "FII", "PRO"):
            continue
        rec = {"client_type": ct.upper()}
        for field, j in idx.items():
            rec[field] = _num(r[j]) if j < len(r) else None
        out.append(rec)
    return out


def store(trade_date: str, recs: list) -> int:
    if not recs:
        return 0
    ensure_table()
    ph = ",".join("?" * len(_OI_COLS))
    data = [[trade_date if c == "trade_date" else r.get(c) for c in _OI_COLS] for r in recs]
    with get_conn() as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO participant_oi ({','.join(_OI_COLS)}) VALUES ({ph})", data)
    return len(recs)


def compute_for_date(trade_date: str) -> int:
    d = datetime.strptime(trade_date, "%Y-%m-%d")
    raw = _try_fetch(_url(d))
    if not raw:
        log.info("no participant-OI for %s (holiday / not posted)", trade_date)
        return 0
    recs = parse_participant(raw)
    n = store(trade_date, recs)
    log.info("participant-OI %s: %d categories stored", trade_date, n)
    return n


def run_today() -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return False, "no cash bhav found"
    try:
        n = compute_for_date(row["d"])
    except RetryableFetchError as e:        # AUD-14: report a block as a FAILURE, not a 0-row holiday
        return False, f"participant-OI blocked/throttled for {row['d']}: {e}"
    return True, f"participant-OI: {n} rows for {row['d']}"


def run_backfill() -> tuple[int, int]:
    ensure_table()
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? ORDER BY trade_date",
            (_BACKFILL_FROM,)).fetchall()]
    log.info("participant-OI backfill: %d trading days from %s", len(dates), _BACKFILL_FROM)
    days = total = 0
    for i, d in enumerate(dates, 1):
        with get_conn() as conn:
            if conn.execute("SELECT 1 FROM participant_oi WHERE trade_date=? LIMIT 1", (d,)).fetchone():
                continue
        try:
            n = compute_for_date(d)
            if n:
                days += 1
                total += n
        except Exception as e:
            log.warning("participant-OI failed for %s: %s", d, e)
        if i % 25 == 0:
            log.info("  progress: %d / %d days", i, len(dates))
        time.sleep(0.8)
    log.info("participant-OI backfill complete: %d days, %d rows", days, total)
    return days, total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--date", type=str)
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
