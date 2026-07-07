"""Historical fundamentals collector — Screener.in time-series (Track B).

The existing screener.py grabs only a CURRENT snapshot (one row/stock), which is useless
for a backtest. This collector extracts the HISTORICAL financial tables (12y annual + ~3y
quarterly: Sales, Net Profit, OPM, EPS, ROCE, ROE, borrowings, ...) and stores them as a
point-in-time time series so we can build fundamental features with NO look-ahead.

Point-in-time: each period gets a report_date = period_end + a reporting lag (annual +90d,
quarterly +50d) — a number isn't "known" to the market until results are filed. Backtests
must use a fundamental only on/after its report_date.

Pure stdlib + requests + bs4 (production venv). Writes research.db.fundamentals_history.
Resumable + polite rate-limiting -> safe to run over the full universe in the background.
"""
from __future__ import annotations
import calendar
import re
import sqlite3
import sys
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

RESEARCH_DB = "/opt/hermes/data/research.db"
UA = "Mozilla/5.0 (Hermes Personal Agent; +https://github.com/ramana-gottipati/hermes)"
SECTIONS = {"quarters": "Q", "profit-loss": "A", "ratios": "A", "balance-sheet": "A"}
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _period_to_dates(label: str, period_type: str):
    """'Mar 2023' -> (period_end 2023-03-31, report_date with lag). None if not a date."""
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})", label.strip())
    if not m or m.group(1) not in MONTHS:
        return None
    mo, yr = MONTHS[m.group(1)], int(m.group(2))
    end = date(yr, mo, calendar.monthrange(yr, mo)[1])
    lag = 90 if period_type == "A" else 50
    return end.isoformat(), (end + timedelta(days=lag)).isoformat()


def _fetch(sym: str):
    for sfx in ("consolidated/", ""):
        try:
            r = requests.get(f"https://www.screener.in/company/{sym}/{sfx}",
                             headers={"User-Agent": UA}, timeout=20)
            if r.status_code == 200 and "Stock not found" not in r.text:
                return r.text
        except requests.RequestException:
            pass
    return None


def _parse_section(soup, sec_id, ptype):
    sec = soup.find("section", id=sec_id)
    tbl = sec.find("table") if sec else None
    if not tbl or not tbl.find("thead") or not tbl.find("tbody"):
        return []
    heads = [th.get_text(strip=True) for th in tbl.find("thead").find_all("th")][1:]
    dates = [_period_to_dates(h, ptype) for h in heads]
    rows = []
    for tr in tbl.find("tbody").find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        metric = cells[0].get_text(strip=True).replace("\xa0", " ").rstrip("+").strip()
        for c, dt in zip(cells[1:], dates):
            if dt is None:
                continue
            t = c.get_text(strip=True).replace(",", "").replace("%", "").replace("₹", "")
            mm = _NUM.search(t)
            if mm:
                rows.append((ptype, dt[0], dt[1], metric, float(mm.group(0))))
    return rows


def _init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS fundamentals_history(
        symbol TEXT, period_type TEXT, period_end TEXT, report_date TEXT,
        metric TEXT, value REAL, PRIMARY KEY(symbol,period_type,period_end,metric))""")
    con.execute("CREATE TABLE IF NOT EXISTS fundamentals_done(symbol TEXT PRIMARY KEY, n INT, at TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_fh ON fundamentals_history(symbol, metric, report_date)")


def collect(symbol: str, con) -> int:
    html = _fetch(symbol)
    if not html:
        return -1
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for sec, ptype in SECTIONS.items():
        rows += [(symbol,) + r for r in _parse_section(soup, sec, ptype)]
    if rows:
        # Columns MUST be named: D78 added a 7th column (source, fundamentals_xbrl.py) and a
        # positional 6-value insert now throws. source stays NULL here — NULL marks a
        # Screener-era row; the XBRL writer's forward-only guard keys on `source IS NULL`.
        con.executemany(
            "INSERT OR REPLACE INTO fundamentals_history"
            "(symbol, period_type, period_end, report_date, metric, value) VALUES (?,?,?,?,?,?)",
            rows)
    con.execute("INSERT OR REPLACE INTO fundamentals_done VALUES (?,?,datetime('now'))", (symbol, len(rows)))
    con.commit()
    return len(rows)


def collect_universe(symbols, delay=2.5):
    con = sqlite3.connect(RESEARCH_DB, timeout=60)
    _init(con)
    done = {r[0] for r in con.execute("SELECT symbol FROM fundamentals_done")}
    todo = [s for s in symbols if s not in done]
    print(f"{len(symbols)} symbols, {len(done)} already done, {len(todo)} to collect", flush=True)
    ok = fail = 0
    for i, s in enumerate(todo):
        n = collect(s, con)
        if n >= 0:
            ok += 1
        else:
            fail += 1
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(todo)}  ok={ok} fail={fail}  (last {s}={n} rows)", flush=True)
        time.sleep(delay)
    print(f"DONE. ok={ok} fail={fail}", flush=True)
    con.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        con = sqlite3.connect(RESEARCH_DB, timeout=60); _init(con)
        for s in ("RELIANCE", "DIXON", "TANLA", "APLAPOLLO", "CDSL"):
            n = collect(s, con); print(f"{s}: {n} rows")
            time.sleep(2.5)
        # show coverage
        for r in con.execute("""SELECT period_type, COUNT(DISTINCT period_end), MIN(period_end), MAX(period_end)
                                FROM fundamentals_history GROUP BY period_type"""):
            print("coverage:", tuple(r))
        print("sample metrics:", [r[0] for r in con.execute(
            "SELECT DISTINCT metric FROM fundamentals_history LIMIT 25")])
        con.close()
    else:
        # full universe from the liquid set (bhavcopy EQ symbols with recent turnover)
        mc = sqlite3.connect("file:/opt/hermes/data/hermes.db?mode=ro", uri=True)
        syms = [r[0] for r in mc.execute(
            "SELECT DISTINCT symbol FROM bhavcopy_rows WHERE series='EQ' AND trade_date>='2025-01-01'")]
        mc.close()
        collect_universe(sorted(syms))
