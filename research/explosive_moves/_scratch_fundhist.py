"""Prototype: can we extract HISTORICAL fundamentals (time series) from Screener.in?
Validates feasibility + how many periods of history we actually get (free pages)."""
import re
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Hermes Personal Agent; +https://github.com/ramana-gottipati/hermes)"


def fetch(sym):
    for sfx in ("consolidated/", ""):
        r = requests.get(f"https://www.screener.in/company/{sym}/{sfx}", headers={"User-Agent": UA}, timeout=20)
        if r.status_code == 200 and "Stock not found" not in r.text:
            return r.text
    return None


def parse_section(soup, sec_id):
    """Return (periods, {metric: [values]}) for a Screener financial section table."""
    sec = soup.find("section", id=sec_id)
    if not sec:
        return [], {}
    tbl = sec.find("table")
    if not tbl:
        return [], {}
    head = tbl.find("thead")
    periods = [th.get_text(strip=True) for th in head.find_all("th")][1:] if head else []
    out = {}
    for tr in tbl.find("tbody").find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        metric = cells[0].get_text(strip=True).replace("\xa0", " ")
        vals = []
        for c in cells[1:]:
            t = c.get_text(strip=True).replace(",", "").replace("%", "").replace("₹", "")
            m = re.search(r"-?\d+(?:\.\d+)?", t)
            vals.append(float(m.group(0)) if m else None)
        out[metric] = vals
    return periods, out


for sym in ("RELIANCE", "DIXON", "TANLA"):
    html = fetch(sym)
    if not html:
        print(f"{sym}: FETCH FAILED"); continue
    soup = BeautifulSoup(html, "lxml")
    print(f"\n===== {sym} =====")
    for sec in ("quarters", "profit-loss", "ratios", "balance-sheet"):
        periods, data = parse_section(soup, sec)
        print(f"  [{sec}] {len(periods)} periods: {periods[:3]}...{periods[-2:] if len(periods)>2 else ''}  | {len(data)} metrics")
        # show a couple of key rows
        for key in ("Sales", "Sales\xa0+", "Net Profit", "Net Profit\xa0+", "OPM %", "EPS in Rs", "ROCE %", "ROE %"):
            if key in data:
                v = data[key]
                print(f"      {key:16}: {v[:2]} ... {v[-2:]}")
