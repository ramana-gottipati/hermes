"""One-off diagnostic — how far back can Patearn actually pull each dataset?

Probes NSE reachability for the three datasets the DVPT backtest needs and
prints the EARLIEST date each is available. Answers the question definitively
instead of guessing archive depth.

  1. sec_bhavdata_full (DELIVERY)  <- the FLOOR for DVPT. Delivery exists ONLY
     in this file; the legacy/UDIFF fallbacks have price but deliv_qty = NULL.
     So whatever this probe reports is the hard floor for the whole DVPT study.
  2. ind_close_all (INDICES)
  3. bulk deals / block deals (NEW table; the only feed that names the
     buyer/seller + BUY/SELL side = ground-truth direction).

RUN ON THE VPS (Mumbai IP — where NSE fetches are proven to work):
    cd /opt/hermes && .venv/bin/python scripts/probe_data_reachability.py

Polite: coarse year-by-year scan with small delays (~5-10 min). Reports back a
summary you can paste to finalise the backfill plan.
"""
import sys
import time
from datetime import datetime, timedelta

try:
    # Reuse the working, header-correct fetchers from our ingestion code.
    from src.automation.bhavcopy import fetch_for_date          # (bytes, fn, fmt, has_delivery)
    from src.automation.indexes import _ind_close_url, _try_fetch as _idx_fetch
except Exception as e:  # pragma: no cover
    print("Run from the repo root so 'src' is importable:", e)
    sys.exit(1)

try:
    import requests
except Exception:
    requests = None

NSE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _weekday(d: datetime) -> datetime:
    while d.weekday() >= 5:           # Sat/Sun -> step back to Friday
        d -= timedelta(days=1)
    return d


def probe_delivery() -> None:
    print("\n=== sec_bhavdata_full (DELIVERY — the DVPT floor) ===")
    earliest_year = None
    for year in range(datetime.now().year, 2009, -1):
        d = _weekday(datetime(year, 2, 15))
        res = fetch_for_date(d)                     # tries delivery -> UDIFF -> legacy
        has_deliv = bool(res and res[3])
        tag = "DELIVERY ok" if has_deliv else ("price only (no delivery)" if res else "no file")
        print(f"  {d:%Y-%m-%d}: {tag}")
        if has_deliv:
            earliest_year = year
        time.sleep(1.0)
    if earliest_year:
        print(f"  -> delivery present at least back to {earliest_year}; refining the month...")
        for m in range(1, 13):
            d = _weekday(datetime(earliest_year, m, 15))
            res = fetch_for_date(d)
            if res and res[3]:
                print(f"  EARLIEST DELIVERY ~ {d:%Y-%m}")
                break
            time.sleep(0.8)
    else:
        print("  !! no delivery found in probed range — DVPT floor is unknown/limited")


def probe_indices() -> None:
    print("\n=== ind_close_all (INDICES) ===")
    for year in range(datetime.now().year, 2009, -1):
        d = _weekday(datetime(year, 2, 15))
        raw = _idx_fetch(_ind_close_url(d))
        print(f"  {d:%Y-%m-%d}: {'OK' if raw else 'no file'}")
        time.sleep(1.0)


def probe_deals() -> None:
    print("\n=== bulk / block deals (NEW — named buyer/seller + side) ===")
    if requests is None:
        print("  requests not available; skipping"); return
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=10)          # seed cookies
        time.sleep(1.0)
    except Exception as e:
        print("  cookie seed failed (API may return blank):", e)
    for kind in ("bulk-deals", "block-deals"):
        print(f"  -- {kind} --")
        for year in range(datetime.now().year, 2004, -1):
            url = (f"https://www.nseindia.com/api/historical/{kind}"
                   f"?from=01-01-{year}&to=08-01-{year}")
            try:
                r = s.get(url, timeout=20)
                data = r.json().get("data", []) if r.ok else []
                n = len(data)
            except Exception:
                n = -1
            extra = f"   fields: {list(data[0].keys())}" if n > 0 else ""
            print(f"    {year}: {n if n >= 0 else 'err'} rows{extra}")
            time.sleep(1.3)


if __name__ == "__main__":
    probe_delivery()
    probe_indices()
    probe_deals()
    print("\nDone. Paste the earliest dates back so we can finalise the backfill plan.")
