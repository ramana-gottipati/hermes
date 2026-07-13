"""NSE named-flow ingestion — bulk deals, block deals, FII/DII flows.

The one feed that names the strong hand: bulk/block deals give CLIENT NAME +
side + qty + price per stock per day. FII/DII gives market-level net flows.

Sources (all FREE, no cookie — the static CDN + the one open API):
  - bulk deals  : https://nsearchives.nseindia.com/content/equities/bulk.csv   (CURRENT day only)
  - block deals : https://nsearchives.nseindia.com/content/equities/block.csv  (CURRENT day only)
  - FII/DII     : https://www.nseindia.com/api/fiidiiTradeReact                (recent)

NOTE — historical backfill of bulk/block is NOT available free: NSE's range API
is bot-walled and there is no dated static archive. So this ingester captures
GOING-FORWARD daily; named-flow history accrues from first run. Schedule it after
market close (≈19:30 IST weekdays). Why this matters: the explosive-move study
found NO stealth-accumulation footprint in the EOD aggregate — named deals are the
data that could reveal the actual buyer, so we start banking it now.

Usage:
    python -m src.automation.deals            # fetch bulk + block + fii/dii for the latest published day
"""
import argparse
import csv
import io
import json
import logging
import time
from datetime import datetime
from typing import Optional

import requests

from src.core.db import get_conn
from src.automation.fetch_retry import RetryableFetchError, raise_if_retryable  # AUD-53/AUD-14

log = logging.getLogger("hermes.deals")
USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"

_NSE_HOME = "https://www.nseindia.com/"
_FETCH_RETRIES = 3        # AUD-53: retry a throttle/block this many times before giving up

BULK_URL = "https://nsearchives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://nsearchives.nseindia.com/content/equities/block.csv"
FIIDII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"

_DDL = """
CREATE TABLE IF NOT EXISTS bulk_block_deals (
    trade_date  TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    deal_type   TEXT NOT NULL,          -- 'bulk' | 'block'
    client_name TEXT NOT NULL,
    side        TEXT NOT NULL,          -- 'BUY' | 'SELL'
    qty         INTEGER,
    price       REAL,
    security    TEXT,
    fetched_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(trade_date, symbol, deal_type, client_name, side, qty, price)
);
CREATE INDEX IF NOT EXISTS idx_deals_sym_date ON bulk_block_deals(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_deals_date ON bulk_block_deals(trade_date);
CREATE TABLE IF NOT EXISTS fii_dii_flows (
    trade_date TEXT NOT NULL,
    category   TEXT NOT NULL,           -- 'FII/FPI' | 'DII'
    buy_value  REAL,
    sell_value REAL,
    net_value  REAL,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(trade_date, category)
);
"""


def _normalize_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _num(s, cast):
    try:
        return cast(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _warm_session() -> requests.Session:
    """AUD-53: a cookie-warmed NSE session. The bulk/block CDN + the bot-walled /api endpoint
    403 a COLD client under load; priming the homepage seeds the anti-bot cookies (the same
    trick insider_events._nse_session uses). Never raises — a failed warm-up just runs cold."""
    s = requests.Session()
    try:
        s.get(_NSE_HOME, headers={"User-Agent": USER_AGENT,
                                  "Accept": "text/html,application/json,*/*",
                                  "Accept-Language": "en-US,en;q=0.9"}, timeout=20)
    except requests.RequestException as e:
        log.warning("NSE session warm-up failed (continuing cold): %s", e)
    return s


def _fetch(url: str, *, json_: bool = False, session=None, retries: int = _FETCH_RETRIES):
    """AUD-53: fetch with resilience — a (warmed) session + up to `retries` exponential-backoff
    retries on a throttle/block (403/429/5xx/network). Returns the parsed body, or None on a
    GENUINE no-data response OR after every retry is exhausted (a real, now-VISIBLE failure —
    `bulk_block_deals` is in the data_quality feed_freshness check, so a lost day surfaces)."""
    getter = session or requests
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/csv,*/*",
               "Referer": _NSE_HOME}
    last_block = None
    for attempt in range(retries):
        try:
            r = getter.get(url, headers=headers, timeout=30)
            raise_if_retryable(r.status_code, url)     # 403/429/5xx → RetryableFetchError
        except requests.RequestException as e:
            last_block = RetryableFetchError(f"network error fetching {url}: {e}")
        except RetryableFetchError as e:
            last_block = e
        else:
            if r.status_code != 200 or len(r.content) < 20:
                log.warning("fetch %s HTTP %s len=%s — no data", url, r.status_code, len(r.content))
                return None                            # genuine no-data (not a block) → no retry
            return r.json() if json_ else r.text
        if attempt < retries - 1:
            wait = 2 ** (attempt + 1)                  # 2s, 4s, ...
            log.warning("fetch %s blocked (%s) — retry %d/%d in %ds",
                        url, last_block, attempt + 1, retries, wait)
            time.sleep(wait)
    log.error("fetch %s FAILED after %d retries: %s — today's deals may be lost (feed_freshness "
              "will flag the gap; the late-evening timer re-attempts)", url, retries, last_block)
    return None


def parse_deals(text: str, deal_type: str) -> list[dict]:
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {(k or "").strip().upper(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        sym = r.get("SYMBOL")
        if not sym or sym.upper() == "NO RECORDS":
            continue
        d = _normalize_date(r.get("DATE"))
        side = (r.get("BUY/SELL") or "").upper()
        out.append({
            "trade_date": d, "symbol": sym.upper(), "deal_type": deal_type,
            "client_name": r.get("CLIENT NAME") or "",
            "side": "BUY" if side.startswith("B") else ("SELL" if side.startswith("S") else side),
            "qty": _num(r.get("QUANTITY TRADED"), int),
            "price": _num(r.get("TRADE PRICE / WGHT. AVG. PRICE") or r.get("TRADE PRICE / WGHT.AVG.PRICE"), float),
            "security": r.get("SECURITY NAME"),
        })
    return out


def parse_fiidii(data) -> list[dict]:
    out = []
    for r in (data or []):
        out.append({
            "trade_date": _normalize_date(r.get("date")),
            "category": r.get("category"),
            "buy_value": _num(r.get("buyValue"), float),
            "sell_value": _num(r.get("sellValue"), float),
            "net_value": _num(r.get("netValue"), float),
        })
    return out


def store_deals(rows: list[dict]) -> int:
    rows = [r for r in rows if r.get("trade_date") and r.get("client_name")]
    if not rows:
        return 0
    n = 0
    with get_conn() as conn:
        conn.executescript(_DDL)
        for r in rows:
            cur = conn.execute(
                "INSERT INTO bulk_block_deals (trade_date,symbol,deal_type,client_name,side,qty,price,security) "
                "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                (r["trade_date"], r["symbol"], r["deal_type"], r["client_name"], r["side"],
                 r["qty"], r["price"], r["security"]))
            n += cur.rowcount
    return n


def store_fiidii(rows: list[dict]) -> int:
    rows = [r for r in rows if r.get("trade_date") and r.get("category")]
    if not rows:
        return 0
    n = 0
    with get_conn() as conn:
        conn.executescript(_DDL)
        for r in rows:
            cur = conn.execute(
                "INSERT INTO fii_dii_flows (trade_date,category,buy_value,sell_value,net_value) "
                "VALUES (?,?,?,?,?) ON CONFLICT(trade_date,category) DO UPDATE SET "
                "buy_value=excluded.buy_value, sell_value=excluded.sell_value, net_value=excluded.net_value",
                (r["trade_date"], r["category"], r["buy_value"], r["sell_value"], r["net_value"]))
            n += 1
    return n


def fetch_all(session=None) -> dict:
    s = session or _warm_session()      # AUD-53: ONE warmed session shared across all 3 sources
    res = {}
    for url, dt in ((BULK_URL, "bulk"), (BLOCK_URL, "block")):
        txt = _fetch(url, session=s)
        res[dt] = store_deals(parse_deals(txt, dt)) if txt else 0
    fd = _fetch(FIIDII_URL, json_=True, session=s)
    res["fiidii"] = store_fiidii(parse_fiidii(fd)) if fd else 0
    return res


def main() -> None:
    argparse.ArgumentParser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    res = fetch_all()
    log.info("ingested — bulk=%s block=%s fiidii=%s", res["bulk"], res["block"], res["fiidii"])


if __name__ == "__main__":
    main()
