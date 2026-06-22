"""CCI — reported quarterly numbers (FREE, no LLM). Parse Screener's quarterly
results table → `concall_results` + the negative-EBITDA ledger `concall_ebitda_watch`.

Keyed by (fy, quarter) so it joins to the promise ledger at settlement: a concall
"May 2026" (→ FY2026 Q4) is graded against the result quarter-ending "Mar 2026"
(also FY2026 Q4). period_label here is the QUARTER-END label ("Mar 2026"); the
(fy, quarter) pair is the bridge. Value-based ₹cr, per the data doctrine.

CLI: python -m src.automation.concall_results --symbol RELIANCE | --pilot [--min-year 2019]
"""

import argparse
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from src.core.db import get_conn
from src.automation.screener import _fetch_company_html
from src.automation.concalls import _SYMBOL_ALIASES, PILOT

log = logging.getLogger("hermes.concall_results")

DEFAULT_MIN_YEAR = 2019
_MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _num(s) -> Optional[float]:
    if s is None:
        return None
    s = str(s).replace(",", "").replace("%", "").replace("₹", "").strip()
    if not s or s in ("-", "—", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_label(lbl: str):
    m = re.match(r"([A-Za-z]{3,})\s+(\d{4})", (lbl or "").strip())
    return (_MON.get(m.group(1)[:3].lower()), int(m.group(2))) if m else (None, None)


def _fy_q(month: int, year: int):
    """Quarter-END month → (fy, quarter), Indian FY (Apr-Mar; FY named by Mar-end year)."""
    if month in (1, 2, 3):
        return year, 4
    if month in (4, 5, 6):
        return year + 1, 1
    if month in (7, 8, 9):
        return year + 1, 2
    return year + 1, 3


def parse_quarters(html: str):
    soup = BeautifulSoup(html, "lxml")
    sec = soup.find("section", id="quarters")
    t = sec.find("table") if sec else None
    if not t or not t.find("thead") or not t.find("tbody"):
        return [], {}
    cols = [th.get_text(strip=True) for th in t.find("thead").find_all("th")][1:]
    rows: dict[str, list] = {}
    for tr in t.find("tbody").find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        label = cells[0].get_text(strip=True).rstrip("+").strip().lower()
        rows[label] = [c.get_text(strip=True) for c in cells[1:]]
    return cols, rows


def _row(rows: dict, key: str):
    for k, v in rows.items():
        if k.startswith(key):
            return v
    return None


def _delta(series, i, back):
    if not series or i - back < 0:
        return None
    a, b = _num(series[i]), _num(series[i - back])
    if a is None or b in (None, 0):
        return None
    return round(100.0 * (a - b) / abs(b), 1)


_UPSERT = """
INSERT INTO concall_results
  (symbol, period_label, fy, quarter, revenue, ebitda, ebitda_margin, pat, eps,
   rev_qoq_pct, rev_yoy_pct, ebitda_qoq_pct, ebitda_yoy_pct, pat_qoq_pct, pat_yoy_pct, fetched_at)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
ON CONFLICT(symbol, period_label) DO UPDATE SET
  fy=excluded.fy, quarter=excluded.quarter, revenue=excluded.revenue, ebitda=excluded.ebitda,
  ebitda_margin=excluded.ebitda_margin, pat=excluded.pat, eps=excluded.eps,
  rev_qoq_pct=excluded.rev_qoq_pct, rev_yoy_pct=excluded.rev_yoy_pct,
  ebitda_qoq_pct=excluded.ebitda_qoq_pct, ebitda_yoy_pct=excluded.ebitda_yoy_pct,
  pat_qoq_pct=excluded.pat_qoq_pct, pat_yoy_pct=excluded.pat_yoy_pct, fetched_at=datetime('now')
"""

_EBITDA_WATCH = """
INSERT INTO concall_ebitda_watch (symbol, period_label, ebitda, ebitda_margin, magnitude, periods_in_red, created_at)
VALUES (?,?,?,?,?,?,datetime('now'))
ON CONFLICT(symbol, period_label) DO UPDATE SET
  ebitda=excluded.ebitda, ebitda_margin=excluded.ebitda_margin, magnitude=excluded.magnitude,
  periods_in_red=excluded.periods_in_red
"""


def ingest_symbol(symbol: str, *, min_year: int = DEFAULT_MIN_YEAR) -> dict:
    symbol = _SYMBOL_ALIASES.get(symbol.upper().strip(), symbol.upper().strip())
    html = _fetch_company_html(symbol)
    if not html:
        log.warning("%s: no Screener page", symbol)
        return {"symbol": symbol, "error": "no_page"}
    cols, rows = parse_quarters(html)
    if not cols:
        return {"symbol": symbol, "error": "no_quarters_table"}
    # Banks/NBFCs label the top line "Revenue" (not "Sales") and report
    # "Financing Profit / Financing Margin %" instead of "Operating Profit / OPM".
    # EBITDA is meaningless for a lender (the game is NIM / credit-cost / GNPA / AUM),
    # so we capture revenue + PAT (both settleable) but DELIBERATELY leave ebitda /
    # margin NULL and never put a lender on the negative-EBITDA ledger — storing a
    # financing line as "EBITDA" would mis-fire flags and mislead the dossier.
    # (Debate India must-do #7; the full sector rubric is deferred — debate #10.)
    is_financial = any(k.startswith("financing") for k in rows)
    sales = _row(rows, "sales") or _row(rows, "revenue")
    op = None if is_financial else _row(rows, "operating profit")
    opm = None if is_financial else _row(rows, "opm")
    npf, eps = _row(rows, "net profit"), _row(rows, "eps")

    ingested, red = 0, 0
    with get_conn() as conn:
        for i, lbl in enumerate(cols):
            mon, yr = _parse_label(lbl)
            if not mon or not yr or yr < min_year:
                continue
            fy, q = _fy_q(mon, yr)
            ebitda = _num(op[i]) if op else None
            margin = _num(opm[i]) if opm else None
            conn.execute(_UPSERT, (
                symbol, lbl, fy, q, _num(sales[i]) if sales else None, ebitda, margin,
                _num(npf[i]) if npf else None, _num(eps[i]) if eps else None,
                _delta(sales, i, 1), _delta(sales, i, 4), _delta(op, i, 1), _delta(op, i, 4),
                _delta(npf, i, 1), _delta(npf, i, 4)))
            ingested += 1
            if not is_financial and ebitda is not None and ebitda <= 0:
                streak, j = 0, i
                while j >= 0 and op and (_num(op[j]) is not None) and _num(op[j]) <= 0:
                    streak += 1
                    j -= 1
                conn.execute(_EBITDA_WATCH, (symbol, lbl, ebitda, margin, ebitda, streak))
                red += 1
    log.info("%s: %d quarters ingested (%d in EBITDA-red)%s", symbol, ingested, red,
             " [financial: EBITDA n/a]" if is_financial else "")
    return {"symbol": symbol, "ingested": ingested, "red": red, "financial": is_financial}


def main() -> None:
    ap = argparse.ArgumentParser(description="CCI quarterly results ingestion (free, no LLM)")
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--min-year", type=int, default=DEFAULT_MIN_YEAR)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    syms = PILOT if args.pilot else [s.upper() for s in args.symbols]
    if not syms:
        ap.error("give symbols or --pilot")
    tot = 0
    for s in syms:
        tot += ingest_symbol(s, min_year=args.min_year).get("ingested", 0)
    log.info("TOTAL quarters ingested: %d", tot)


if __name__ == "__main__":
    main()
