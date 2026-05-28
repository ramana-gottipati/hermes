"""NSE corporate actions ingestion — splits, bonuses, dividends, rights, mergers.

Pulls CSVs from NSE archives and parses into the corporate_actions table.
Used to safely interpret volume comparisons across action dates (though the
primary patearn signals use VALUE not volume — naturally action-invariant).

Usage:
    python -m src.automation.corp_actions          # fetch all current categories
    python -m src.automation.corp_actions --type SPLIT
"""

import argparse
import csv
import io
import logging
import re
import time
from datetime import datetime
from typing import Optional

import requests

from src.core.db import get_conn

log = logging.getLogger("hermes.corp_actions")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"

# NSE published corporate-action CSVs.
SOURCES = {
    "BONUS":    "https://nsearchives.nseindia.com/content/equities/Bonus_Issue.csv",
    "SPLIT":    "https://nsearchives.nseindia.com/content/equities/Stock_Split.csv",
    "RIGHTS":   "https://nsearchives.nseindia.com/content/equities/Rights_Issue.csv",
    "DIVIDEND": "https://nsearchives.nseindia.com/content/equities/Dividend.csv",
}

REQUEST_PAUSE = 1.0


def _fetch_csv(url: str) -> Optional[str]:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"},
            timeout=30,
        )
    except requests.RequestException as e:
        log.warning("fetch %s failed: %s", url, e)
        return None
    if r.status_code != 200 or len(r.content) < 50:
        log.warning("fetch %s returned HTTP %s len=%s", url, r.status_code, len(r.content))
        return None
    return r.text


_RATIO_RE = re.compile(r"(\d+)\s*[:to/]+\s*(\d+)", re.IGNORECASE)
_SPLIT_RE = re.compile(
    r"(?:from|of)\s*(?:Rs\.?|Re\.?|INR)?\s*([\d.]+)\s*(?:each|/-)?\s*"
    r"(?:to|into)\s*(?:Rs\.?|Re\.?|INR)?\s*([\d.]+)",
    re.IGNORECASE,
)


def _parse_ratio(action_type: str, purpose_text: str) -> tuple[Optional[float], Optional[float]]:
    """Best-effort extraction of (from, to) ratio.

    Examples:
      "Bonus 1:5"                                              → (1, 5)
      "Sub-Division of Equity Shares of Rs.10 each into Rs.1" → (10, 1)
      "Rs/2/-Per Share (20%) Dividend"                        → (None, None)  (dividends use absolute amounts)
    """
    if not purpose_text:
        return None, None
    text = purpose_text.strip()

    if action_type == "SPLIT":
        m = _SPLIT_RE.search(text)
        if m:
            return float(m.group(1)), float(m.group(2))

    m = _RATIO_RE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def _detect_action_type_from_purpose(purpose: str) -> Optional[str]:
    """Some combined feeds have mixed purposes; classify by keyword."""
    p = (purpose or "").upper()
    if "BONUS" in p:
        return "BONUS"
    if "SUB-DIVISION" in p or "SPLIT" in p or "STOCK SPLIT" in p:
        return "SPLIT"
    if "RIGHTS" in p:
        return "RIGHTS"
    if "DIVIDEND" in p:
        return "DIVIDEND"
    return None


def _parse_csv_rows(csv_text: str, default_type: str) -> list[dict]:
    """Parse an NSE corporate-action CSV. Columns vary slightly across files
    but typically include SYMBOL, COMPANY NAME, SERIES, PURPOSE, EX DATE, RECORD DATE."""
    reader = csv.DictReader(io.StringIO(csv_text))
    out = []
    for r in reader:
        r = {(k or "").strip().upper(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        symbol = r.get("SYMBOL") or r.get("TICKER")
        if not symbol:
            continue
        purpose = r.get("PURPOSE") or r.get("DETAILS") or ""
        action_type = _detect_action_type_from_purpose(purpose) or default_type

        ex_date = _normalize_date(r.get("EX DATE") or r.get("EX-DATE") or r.get("EXDATE"))
        record_date = _normalize_date(r.get("RECORD DATE") or r.get("RECORDDATE"))
        ratio_from, ratio_to = _parse_ratio(action_type, purpose)

        out.append({
            "symbol": symbol.upper(),
            "action_type": action_type,
            "ex_date": ex_date,
            "record_date": record_date,
            "ratio_from": ratio_from,
            "ratio_to": ratio_to,
            "details": purpose,
            "source": default_type,
        })
    return out


def _normalize_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def store_actions(rows: list[dict]) -> int:
    if not rows:
        return 0
    sql = (
        "INSERT INTO corporate_actions "
        "(symbol, action_type, ex_date, record_date, ratio_from, ratio_to, details, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(symbol, action_type, ex_date, details) DO NOTHING"
    )
    n = 0
    with get_conn() as conn:
        for r in rows:
            try:
                conn.execute(sql, (
                    r["symbol"], r["action_type"], r["ex_date"], r["record_date"],
                    r["ratio_from"], r["ratio_to"], r["details"], r["source"],
                ))
                n += 1
            except Exception as e:
                log.debug("skip corp action %s: %s", r.get("symbol"), e)
    return n


def fetch_all() -> tuple[int, int]:
    """Pull every category. Returns (rows_inserted, sources_succeeded)."""
    total_inserted = 0
    sources_ok = 0
    for action_type, url in SOURCES.items():
        log.info("fetching %s: %s", action_type, url)
        text = _fetch_csv(url)
        if not text:
            log.warning("skipped %s (fetch failed)", action_type)
            continue
        rows = _parse_csv_rows(text, default_type=action_type)
        n = store_actions(rows)
        log.info("%s: parsed %d, inserted %d", action_type, len(rows), n)
        total_inserted += n
        sources_ok += 1
        time.sleep(REQUEST_PAUSE)
    return total_inserted, sources_ok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--type", choices=list(SOURCES.keys()))
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.type:
        text = _fetch_csv(SOURCES[args.type])
        if text:
            rows = _parse_csv_rows(text, args.type)
            n = store_actions(rows)
            log.info("%s: inserted %d", args.type, n)
    else:
        inserted, sources = fetch_all()
        log.info("done — %d total rows inserted from %d sources", inserted, sources)


if __name__ == "__main__":
    main()
