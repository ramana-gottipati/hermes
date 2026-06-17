"""NSE equity universe ingestion (D42).

Fetches EQUITY_L.csv — the canonical list of NSE-listed EQUITY securities — into
`nse_equity_list`. This is the allowlist that keeps the scanners EQUITY-ONLY:
ETFs and mutual-fund units are NOT in EQUITY_L, and our bhav source
(sec_bhavdata_full) carries NO ISIN, so a symbol allowlist is the robust
equity-vs-ETF separator (name patterns leak — e.g. ALPHA / BFSI / DEFENCE / IT /
MAFANG ETFs slip through — and also wrongly drop real equities like GOLDIAM).

The table is refreshed only on a SUCCESSFUL, non-empty fetch — a failed fetch
leaves the previous list intact, so the scanner filter never silently empties.

Source : https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv
Columns: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,
         MARKET LOT, ISIN NUMBER, FACE VALUE

Usage:
    python -m src.automation.equity_list
"""

import csv
import io
import logging
from datetime import datetime

import requests

from src.core.db import get_conn

log = logging.getLogger("hermes.equity_list")

URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Hermes Personal Agent)",
    "Accept": "text/csv,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def fetch_equities() -> list[dict]:
    """Return [{symbol, name, isin, listing}], or [] on any failure."""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
    except requests.RequestException as e:
        log.warning("EQUITY_L fetch error: %s", e)
        return []
    if r.status_code != 200 or "SYMBOL" not in r.text[:200]:
        log.warning("EQUITY_L bad response: status=%s", r.status_code)
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for raw in csv.DictReader(io.StringIO(r.text)):
        row = {(k or "").strip(): (v.strip() if isinstance(v, str) else v)
               for k, v in raw.items()}
        sym = (row.get("SYMBOL") or "").upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append({
                "symbol": sym,
                "name": row.get("NAME OF COMPANY"),
                "isin": row.get("ISIN NUMBER"),
                "listing": row.get("DATE OF LISTING"),
            })
    return out


def run() -> int:
    """Refresh nse_equity_list. Returns the new row count, or the unchanged
    existing count if the fetch failed (table left intact)."""
    equities = fetch_equities()
    if not equities:
        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) n FROM nse_equity_list").fetchone()["n"]
        log.warning("equity list fetch failed/empty — keeping existing %d rows", n)
        return n
    snap = datetime.now().strftime("%Y-%m-%d")
    rows = [(e["symbol"], e["name"], e["isin"], e["listing"], snap) for e in equities]
    # Atomic within one transaction (get_conn commits on success, rolls back on
    # error) — so the table is never left empty by a mid-write failure.
    with get_conn() as conn:
        conn.execute("DELETE FROM nse_equity_list")
        conn.executemany(
            """INSERT OR REPLACE INTO nse_equity_list
                 (symbol, company_name, isin, listing_date, snapshot_date)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )
    log.info("nse_equity_list refreshed: %d equities @ %s", len(rows), snap)
    return len(rows)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run()


if __name__ == "__main__":
    main()
