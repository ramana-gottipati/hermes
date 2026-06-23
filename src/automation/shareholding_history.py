"""Quarterly SHAREHOLDING history collector — Screener.in 'shareholding' section.

Companion to fundamentals_history.py (kept as a SEPARATE table, different cadence/shape). Screener's
company page carries ~12-13 quarters of shareholding: Promoters / FIIs / DIIs / Government / Public /
Others / No. of Shareholders. Storing them point-in-time makes the patearn scorer's promoter-conviction
(P6) and institutional-neglect (P8) patterns REAL — and lets a live screen use promoter/FII/DII TRENDS,
not just the latest snapshot.

LIMITS (honest):
  * The free page shows only ~3 years of quarters → SHALLOW vs the 24y financials. Enriches the LIVE
    score + recent (2023+) backtest, NOT the deep 2012-2026 backtest.
  * PLEDGE is NOT in this section (needs BSE filings) → the pledge disqualifier stays estimated.

Point-in-time: SEBI LODR requires the shareholding pattern within 21 days of quarter-end →
report_date = period_end + 30d (safe). Writes research.db.shareholding_history.

Pure stdlib + requests + bs4. Resumable (shareholding_done) + rate-limited → safe over the universe
in the background. Run: cd /opt/hermes && .venv/bin/python -m src.automation.shareholding_history [limit]
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
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
LAG_DAYS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS shareholding_history(
    symbol TEXT, period_type TEXT, period_end TEXT, report_date TEXT,
    metric TEXT, value REAL, PRIMARY KEY(symbol, period_end, metric));
CREATE INDEX IF NOT EXISTS idx_sh ON shareholding_history(symbol, metric, report_date);
CREATE TABLE IF NOT EXISTS shareholding_done(symbol TEXT PRIMARY KEY, n INTEGER, done_at TEXT);
"""


def _period(label: str):
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})", label.strip())
    if not m or m.group(1) not in MONTHS:
        return None
    mo, yr = MONTHS[m.group(1)], int(m.group(2))
    end = date(yr, mo, calendar.monthrange(yr, mo)[1])
    return end.isoformat(), (end + timedelta(days=LAG_DAYS)).isoformat()


def _num(t: str):
    t = t.replace("\xa0", " ").replace("%", "").strip()
    m = _NUM.search(t)
    return float(m.group(0).replace(",", "")) if m else None


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


def _parse(html: str):
    """Return [(period_end, report_date, metric, value), ...] from the shareholding section."""
    soup = BeautifulSoup(html, "lxml")
    sec = soup.find("section", id="shareholding")
    tbl = sec.find("table") if sec else None
    if not tbl or not tbl.find("thead") or not tbl.find("tbody"):
        return []
    periods = [_period(th.get_text(strip=True))
               for th in tbl.find("thead").find_all("th")][1:]
    out = []
    for tr in tbl.find("tbody").find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        metric = cells[0].get_text(strip=True).replace("\xa0", " ").rstrip("+").strip()
        for c, per in zip(cells[1:], periods):
            if per is None:
                continue
            v = _num(c.get_text(strip=True))
            if v is not None:
                out.append((per[0], per[1], metric, v))
    return out


def build(limit=None, sleep_s: float = 0.8, skip_existing: bool = True):
    con = sqlite3.connect(RESEARCH_DB, timeout=60)
    con.executescript(SCHEMA)
    syms = [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM fundamentals_history ORDER BY symbol").fetchall()]
    if skip_existing:
        done = {r[0] for r in con.execute("SELECT symbol FROM shareholding_done").fetchall()}
        syms = [s for s in syms if s not in done]
    if limit:
        syms = syms[:limit]
    print(f"{len(syms)} symbols to scrape (skip_existing={skip_existing})", flush=True)
    ok = miss = 0
    for k, sym in enumerate(syms):
        html = _fetch(sym)
        rows = _parse(html) if html else []
        if rows:
            con.executemany(
                "INSERT OR REPLACE INTO shareholding_history VALUES (?,?,?,?,?,?)",
                [(sym, "Q", pe, rd, m, v) for pe, rd, m, v in rows])
            ok += 1
        else:
            miss += 1
        con.execute("INSERT OR REPLACE INTO shareholding_done VALUES (?,?,datetime('now'))",
                    (sym, len(rows)))
        con.commit()
        if (k + 1) % 200 == 0:
            print(f"  {k+1}/{len(syms)}  ok={ok} miss={miss}", flush=True)
        if sleep_s:
            time.sleep(sleep_s)
    con.close()
    print(f"DONE shareholding_history: ok={ok} miss={miss}")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    build(limit=lim)
