"""NSE index constituent membership ingestion (D33b).

Populates `stock_index_membership` (symbol, index_name, snapshot_date, weight_pct)
from niftyindices.com constituent CSVs, so the dashboard can drill from a sector
(index_signals / index_rows) down to its member stocks.

Source : https://niftyindices.com/IndexConstituent/<slug>.csv
Columns: Company Name, Industry, Symbol, Series, ISIN Code   (no weights provided)

IMPORTANT: the index_name keys below MUST exactly match `index_rows.index_name`
(NSE title-case) or the dashboard's sector->stock JOIN silently misses. Each key
was verified present in index_rows and each slug verified reachable (D33b build).

Usage:
    python -m src.automation.membership                  # all curated indices
    python -m src.automation.membership --index "Nifty Bank"
"""

import argparse
import csv
import io
import logging
from datetime import datetime
from typing import Optional

import requests

from src.core.db import get_conn

log = logging.getLogger("hermes.membership")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
BASE_URL = "https://niftyindices.com/IndexConstituent"

# index_name (must match index_rows exactly) -> constituent CSV slug.
INDEX_CONSTITUENTS: dict[str, str] = {
    # --- Broad / size ---
    "Nifty 50":                 "ind_nifty50list",
    "Nifty Next 50":            "ind_niftynext50list",
    "Nifty Midcap 150":         "ind_niftymidcap150list",
    "Nifty Smallcap 250":       "ind_niftysmallcap250list",
    "Nifty 500":                "ind_nifty500list",
    # --- Core sectors ---
    "Nifty Bank":               "ind_niftybanklist",
    "Nifty Financial Services": "ind_niftyfinancelist",
    "Nifty IT":                 "ind_niftyitlist",
    "Nifty Auto":               "ind_niftyautolist",
    "Nifty Pharma":             "ind_niftypharmalist",
    "Nifty FMCG":               "ind_niftyfmcglist",
    "Nifty Metal":              "ind_niftymetallist",
    "Nifty Energy":             "ind_niftyenergylist",
    "Nifty Realty":             "ind_niftyrealtylist",
    "Nifty Media":              "ind_niftymedialist",
    "Nifty Infrastructure":     "ind_niftyinfralist",
    "Nifty Commodities":        "ind_niftycommoditieslist",
    "Nifty Healthcare Index":   "ind_niftyhealthcarelist",
    "Nifty Consumer Durables":  "ind_niftyconsumerdurableslist",
    "Nifty Oil & Gas":          "ind_niftyoilgaslist",
    "Nifty PSU Bank":           "ind_niftypsubanklist",
    # --- D41 Phase 2: the "real sectors" that were whitelisted in rotation but
    # whose constituents were never loaded (so sector->stock drill came up empty).
    # Slugs verified reachable; member counts noted at add-time.
    "Nifty India Defence":      "ind_niftyindiadefence_list",   # ~19 members
    "Nifty Private Bank":       "ind_nifty_privatebanklist",    # ~10 members
    "Nifty Chemicals":          "ind_niftychemicals_list",      # ~20 members
}


def _fetch_csv(slug: str, *, timeout: int = 25) -> Optional[str]:
    url = f"{BASE_URL}/{slug}.csv"
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
        log.warning("fetch error %s: %s", url, e)
        return None
    if r.status_code != 200 or "Company Name" not in r.text[:200]:
        log.warning("bad response %s: status=%s", url, r.status_code)
        return None
    return r.text


def _parse_symbols(csv_text: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(csv_text))
    out: list[str] = []
    seen: set[str] = set()
    for r in reader:
        r = {(k or "").strip(): (v.strip() if isinstance(v, str) else v)
             for k, v in r.items()}
        sym = (r.get("Symbol") or "").strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def store_membership(index_name: str, symbols: list[str], snapshot_date: str) -> int:
    if not symbols:
        return 0
    rows = [(s, index_name, snapshot_date, None) for s in symbols]
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO stock_index_membership
                 (symbol, index_name, snapshot_date, weight_pct)
               VALUES (?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def run(only_index: Optional[str] = None) -> tuple[int, int]:
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    if only_index:
        if only_index not in INDEX_CONSTITUENTS:
            log.error("unknown index %r (not in mapping)", only_index)
            return 0, 0
        items = [(only_index, INDEX_CONSTITUENTS[only_index])]
    else:
        items = list(INDEX_CONSTITUENTS.items())

    n_ok = 0
    n_sym = 0
    for index_name, slug in items:
        csv_text = _fetch_csv(slug)
        if not csv_text:
            log.warning("SKIP %s (%s) — no data", index_name, slug)
            continue
        syms = _parse_symbols(csv_text)
        stored = store_membership(index_name, syms, snapshot_date)
        n_ok += 1
        n_sym += stored
        log.info("  %-26s %3d members", index_name, stored)
    log.info("membership done: %d/%d indices, %d rows @ %s",
             n_ok, len(items), n_sym, snapshot_date)
    return n_ok, n_sym


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=str, help="single index_name to fetch")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run(only_index=args.index)


if __name__ == "__main__":
    main()
