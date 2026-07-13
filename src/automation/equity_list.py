"""NSE equity universe ingestion (D42) + the ETF allowlist (data-postmortem 2026-07-07).

Fetches EQUITY_L.csv — the canonical list of NSE-listed EQUITY securities — into
`nse_equity_list`. This is the allowlist that keeps the scanners EQUITY-ONLY:
ETFs and mutual-fund units are NOT in EQUITY_L, and our bhav source
(sec_bhavdata_full) carries NO ISIN, so a symbol allowlist is the robust
equity-vs-ETF separator (name patterns leak — e.g. ALPHA / BFSI / DEFENCE / IT /
MAFANG ETFs slip through — and also wrongly drop real equities like GOLDIAM).

ALSO fetches the exchange's ETF list (`www.nseindia.com/api/etf`, ~328 funds) into
`nse_etf_list` — the POSITIVE identification the equity allowlist cannot give:
"not in EQUITY_L" conflates fund-ness with delisted-ness (a delisted COMPANY also
drops out), which is wrong for research that wants delisted companies but no funds.
`security_master.instrument_class` combines this list + INF-prefix ISINs + a
conservative name net into the named FUND/EQUITY class.

Each table is refreshed only on a SUCCESSFUL, non-empty fetch — a failed fetch
leaves the previous list intact, so no scanner filter ever silently empties; the
two fetches fail independently.

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
from src.automation.fetch_retry import RetryableFetchError, raise_if_retryable  # AUD-14

log = logging.getLogger("hermes.equity_list")

URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Hermes Personal Agent)",
    "Accept": "text/csv,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

_ETF_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_ETF_REF = "https://www.nseindia.com/market-data/exchange-traded-funds-etf"
_ETF_API = "https://www.nseindia.com/api/etf"

_ETF_DDL = """
CREATE TABLE IF NOT EXISTS nse_etf_list (
    symbol        TEXT PRIMARY KEY,
    name          TEXT,
    assets        TEXT,
    snapshot_date TEXT
);
"""


def fetch_equities() -> list[dict]:
    """Return [{symbol, name, isin, listing}], or [] on any failure."""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
        raise_if_retryable(r.status_code, URL)   # AUD-14: label a 403/429/5xx as a throttle
    except RetryableFetchError as e:
        # A throttle/block is transient — keep the existing universe (run() does not wipe on []).
        # Log it DISTINCTLY so a persistently-stale allowlist is diagnosable as rate-limiting.
        log.warning("EQUITY_L BLOCKED/throttled — keeping existing list, retry next run: %s", e)
        return []
    except requests.RequestException as e:
        log.warning("EQUITY_L network error — keeping existing list, retry next run: %s", e)
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


def fetch_etfs() -> list:
    """[{symbol, name, assets}] from the NSE ETF page API, or [] on any failure.
    Needs the www.nseindia.com anti-bot priming (the nsearchives CSV above does not)."""
    try:
        s = requests.Session()
        h = {"User-Agent": _ETF_UA, "Accept": "application/json,text/plain,*/*",
             "Accept-Language": "en-US,en;q=0.9", "Referer": _ETF_REF}
        s.get("https://www.nseindia.com", headers=h, timeout=20)
        s.get(_ETF_REF, headers=h, timeout=20)
        r = s.get(_ETF_API, headers=h, timeout=45)
        raise_if_retryable(r.status_code, _ETF_API)  # AUD-14: label a 403/429/5xx as a throttle
        if r.status_code != 200:
            log.warning("ETF list bad response: status=%s", r.status_code)
            return []
        data = r.json()
        rows = data.get("data") if isinstance(data, dict) else data
        out, seen = [], set()
        for x in rows or []:
            sym = (x.get("symbol") or "").strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                meta = x.get("meta") or {}
                out.append({"symbol": sym,
                            "name": (meta.get("companyName") or "").strip() or None,
                            "assets": (x.get("assets") or "").strip() or None})
        return out
    except RetryableFetchError as e:                 # AUD-14: a throttle → keep existing (run_etfs)
        log.warning("ETF list BLOCKED/throttled — keeping existing list, retry next run: %s", e)
        return []
    except Exception as e:  # noqa: BLE001 — the ETF leg must never break the equity refresh
        log.warning("ETF list fetch error: %s", e)
        return []


def run_etfs() -> int:
    """Refresh nse_etf_list (same contract as run(): non-empty fetch only, shrink guard)."""
    etfs = fetch_etfs()
    with get_conn() as conn:
        conn.executescript(_ETF_DDL)
        existing = conn.execute("SELECT COUNT(*) n FROM nse_etf_list").fetchone()["n"]
        if not etfs:
            log.warning("ETF list fetch failed/empty — keeping existing %d rows", existing)
            return existing
        if existing and len(etfs) < 0.9 * existing:
            log.critical("nse_etf_list REFUSED: fetched %d < 90%% of existing %d — keeping the "
                         "current list (suspected truncated feed)", len(etfs), existing)
            return existing
        snap = datetime.now().strftime("%Y-%m-%d")
        conn.execute("DELETE FROM nse_etf_list")
        conn.executemany(
            "INSERT OR REPLACE INTO nse_etf_list (symbol, name, assets, snapshot_date) "
            "VALUES (?, ?, ?, ?)",
            [(e["symbol"], e["name"], e["assets"], snap) for e in etfs])
    log.info("nse_etf_list refreshed: %d ETFs @ %s", len(etfs), snap)
    return len(etfs)


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
        # AUD-43: refuse a suspicious shrink. A truncated feed would replace the full allowlist
        # with a stub and silently gate every equity scanner; real delisting churn is a few %,
        # never a cliff. Keep the current table if the new list is < 90% of it.
        existing = conn.execute("SELECT COUNT(*) n FROM nse_equity_list").fetchone()["n"]
        if existing and len(rows) < 0.9 * existing:
            log.critical("nse_equity_list REFUSED: fetched %d < 90%% of existing %d — keeping the "
                         "current allowlist (suspected truncated feed)", len(rows), existing)
            return existing
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
    # Independent leg, and it must never fail the CALLER either: this main() is an ExecStart
    # step of the nightly bhavcopy chain (hermes-bhavcopy.service.d/10-signals.conf) — a
    # transient lock/network error on the ETF list must not fail the signals step.
    try:
        run_etfs()
    except Exception as e:  # noqa: BLE001
        log.warning("nse_etf_list refresh failed (non-fatal): %s", e)


if __name__ == "__main__":
    main()
