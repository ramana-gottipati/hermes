"""Screener.in HTML scraper for Indian stock fundamentals.

Hits the public company page (e.g. https://www.screener.in/company/RELIANCE/)
and extracts the key ratios used by the patearn 14-pattern framework.

Caching: results are stored in the `fundamentals` table and reused for
SCREENER_CACHE_DAYS (default 7) — Screener.in serves point-in-time ratios that
change at most quarterly, so heavy re-scraping is wasteful and rude.

No API key needed. No LLM. Pure HTTP + BeautifulSoup.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.core.db import get_conn

log = logging.getLogger("hermes.screener")

SCREENER_CACHE_DAYS = 7
USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent; +https://github.com/ramana-gottipati/hermes)"


# --- HTTP fetch -------------------------------------------------------------

def _fetch_url(url: str, *, timeout: int = 20) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        if r.status_code == 200:
            return r.text
        log.warning("screener fetch %s -> HTTP %s", url, r.status_code)
    except requests.RequestException as e:
        log.warning("screener fetch %s raised: %s", url, e)
    return None


def _fetch_company_html(symbol: str) -> Optional[str]:
    """Try consolidated page first, fall back to standalone."""
    for suffix in ("consolidated/", ""):
        url = f"https://www.screener.in/company/{symbol}/{suffix}"
        html = _fetch_url(url)
        if html and "Stock not found" not in html and "404" not in html[:500]:
            return html
    return None


# --- Parsing helpers --------------------------------------------------------

_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _parse_num(text: Optional[str]) -> Optional[float]:
    """Extract first number from a string like '₹2,847' / '24.5 %' / '0.23'."""
    if not text:
        return None
    # Drop commas, currency symbols, percent
    cleaned = text.replace(",", "").replace("₹", "").replace("%", "").strip()
    m = _NUM_RE.search(cleaned)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _extract_top_ratios(soup: BeautifulSoup) -> dict:
    """Top-of-page ratios block: Market Cap, Current Price, P/E, etc."""
    out = {}
    for li in soup.select("#top-ratios li"):
        name_el = li.find("span", class_="name")
        value_el = li.find("span", class_="number")
        if not name_el or not value_el:
            continue
        # Some ratios have the value inside a nested <span class="number">
        # plus optional unit text. Grab the whole label's text after name.
        label = name_el.get_text(strip=True)
        full_text = li.get_text(" ", strip=True).replace(label, "", 1).strip()
        out[label] = full_text
    return out


def _extract_company_name(soup: BeautifulSoup) -> Optional[str]:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def _extract_shareholding(soup: BeautifulSoup) -> dict:
    """Latest quarter shareholding pattern — Promoter / FII / DII / Public."""
    out = {}
    table = soup.find("section", id="shareholding")
    if not table:
        return out
    # Look for the recent quarter column
    rows = table.find_all("tr")
    for tr in rows:
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True).lower()
        # Take the LAST numeric cell as "most recent quarter"
        last_val = None
        for c in cells[1:]:
            v = _parse_num(c.get_text(strip=True))
            if v is not None:
                last_val = v
        if last_val is None:
            continue
        if "promoter" in label and "pledg" not in label:
            out["promoter_holding"] = last_val
        elif "pledg" in label:
            out["promoter_pledge"] = last_val
        elif "fii" in label or "foreign" in label:
            out["fii_holding"] = last_val
        elif "dii" in label or "domestic" in label:
            out["dii_holding"] = last_val
    return out


# --- Public API -------------------------------------------------------------

def fetch_company(symbol: str, *, use_cache: bool = True) -> Optional[dict]:
    """Return a dict of fundamentals for a stock. Caches in DB.

    Returns None if the company couldn't be fetched/parsed.
    """
    symbol = symbol.upper().strip()

    if use_cache:
        cached = _read_cache(symbol)
        if cached:
            return cached

    html = _fetch_company_html(symbol)
    if not html:
        log.warning("could not fetch screener for %s", symbol)
        return None

    soup = BeautifulSoup(html, "lxml")
    ratios = _extract_top_ratios(soup)
    shp = _extract_shareholding(soup)

    data = {
        "symbol": symbol,
        "company_name": _extract_company_name(soup),
        "market_cap_cr": _parse_num(ratios.get("Market Cap")),
        "current_price": _parse_num(ratios.get("Current Price")),
        "pe": _parse_num(ratios.get("Stock P/E")),
        "pb": None,  # not in top-ratios; could parse from another block
        "book_value": _parse_num(ratios.get("Book Value")),
        "dividend_yield": _parse_num(ratios.get("Dividend Yield")),
        "roce": _parse_num(ratios.get("ROCE")),
        "roe": _parse_num(ratios.get("ROE")),
        "debt_to_equity": _parse_num(ratios.get("Debt to equity")),
        "promoter_holding": shp.get("promoter_holding"),
        "promoter_pledge": shp.get("promoter_pledge"),
        "fii_holding": shp.get("fii_holding"),
        "dii_holding": shp.get("dii_holding"),
        # Growth metrics parsed from "Profit growth" / "Sales growth" sections
        # The Screener "Compounded Growth" table has 10Y/5Y/3Y/TTM rows
        **_extract_growth_rates(soup),
        "opm_latest": _extract_opm_latest(soup),
        "eps_ttm": _parse_num(ratios.get("EPS")),
        # Derived P/B if both BV and CP known
    }
    if data["book_value"] and data["current_price"]:
        data["pb"] = data["current_price"] / data["book_value"]

    _write_cache(data)
    return data


def _extract_growth_rates(soup: BeautifulSoup) -> dict:
    """Profit / Sales compounded growth at 5Y / 3Y / TTM horizons.

    Screener structures this as two tables labeled 'Compounded Sales Growth' and
    'Compounded Profit Growth' — each with 10 Years / 5 Years / 3 Years / TTM rows.
    """
    out = {}
    for table in soup.select("table.ranges-table, table[data-type='Compounded']"):
        caption = ""
        prev = table.find_previous(["h2", "h3", "th"])
        if prev:
            caption = prev.get_text(strip=True).lower()
        # Walk rows
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).lower()
            value = _parse_num(cells[1].get_text(strip=True))
            if value is None:
                continue
            if "sales" in caption or "revenue" in caption:
                if "5 year" in label:
                    out["sales_growth_5y"] = value
                elif "3 year" in label:
                    out["sales_growth_3y"] = value
                elif "ttm" in label or "trailing" in label:
                    out["sales_growth_ttm"] = value
            elif "profit" in caption:
                if "5 year" in label:
                    out["profit_growth_5y"] = value
                elif "3 year" in label:
                    out["profit_growth_3y"] = value
                elif "ttm" in label or "trailing" in label:
                    out["profit_growth_ttm"] = value
    return out


def _extract_opm_latest(soup: BeautifulSoup) -> Optional[float]:
    """Most recent OPM% from the quarterly results section."""
    section = soup.find("section", id="quarters")
    if not section:
        section = soup.find("section", id="profit-loss")
    if not section:
        return None
    for tr in section.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True).lower()
        if "opm" not in label and "operating profit margin" not in label:
            continue
        # Take last numeric cell
        for c in reversed(cells[1:]):
            v = _parse_num(c.get_text(strip=True))
            if v is not None:
                return v
    return None


# --- Cache layer ------------------------------------------------------------

def _read_cache(symbol: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fundamentals WHERE symbol = ?", (symbol,)
        ).fetchone()
    if not row:
        return None
    fetched = datetime.fromisoformat(row["fetched_at"].replace(" ", "T"))
    if datetime.utcnow() - fetched > timedelta(days=SCREENER_CACHE_DAYS):
        return None
    return dict(row)


def _write_cache(data: dict) -> None:
    cols = [k for k in data.keys() if k != "symbol"]
    placeholders = ", ".join(["?"] * (1 + len(cols)))
    col_list = ", ".join(["symbol"] + cols + ["fetched_at"])
    update_clauses = ", ".join(f"{c} = excluded.{c}" for c in cols + ["fetched_at"])
    values = [data["symbol"]] + [data.get(c) for c in cols]
    with get_conn() as conn:
        conn.execute(
            f"""INSERT INTO fundamentals ({col_list}) VALUES ({placeholders}, datetime('now'))
                ON CONFLICT(symbol) DO UPDATE SET {update_clauses}""",
            values + [datetime.utcnow().isoformat(sep=' ', timespec='seconds')],
        )
