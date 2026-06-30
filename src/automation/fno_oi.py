"""F&O Open-Interest feed — the IDENTITY channel MEP's price tape can't see.

MEP / DVPT *infer* accumulation from the price tape; this *observes* positioning
directly via NSE F&O open interest. For each underlying we aggregate its STOCK
FUTURES (STF) across expiries and read the day's OI change against the day's price
change — the classic four-quadrant map:

    ↑price ↑OI = LONG_BUILDUP   (fresh longs — accumulation)
    ↓price ↑OI = SHORT_BUILDUP  (fresh shorts — distribution)
    ↓price ↓OI = LONG_UNWIND    (longs exiting)
    ↑price ↓OI = SHORT_COVER    (shorts exiting — short-covering bounce)

Plus a Put/Call OI ratio (PCR) from the stock options (STO) as a sentiment read.

DESCRIPTOR-ONLY (D62 discipline) — like MEP, this characterises/confirms; it does
NOT rank or pick until it passes the purged-walk-forward + Deflated-Sharpe gate.
It is the channel most LIKELY to carry real predictive alpha (it names the strong
hand), but that has to be earned through the gate, not assumed.

Source: NSE UDiFF F&O bhavcopy (the same archive host as the cash bhav) —
    https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip
The UDiFF format starts mid-2024; pre-UDiFF history would need the legacy
DERIVATIVES URL + a second parser (deferred — OI is a near-term signal anyway).
Price change is read from the cash bhav we already store (bhavcopy_rows), so this
must run AFTER the cash bhav for the day.

Stored into fno_oi_signals (its OWN table — never touches the cash/stock_signals
hot tables, nor the parallel-owned deals.py named-flow feed).

Usage:
    python -m src.automation.fno_oi                 # latest cash-bhav date
    python -m src.automation.fno_oi --backfill      # every UDiFF-era trading day
    python -m src.automation.fno_oi --date 2026-06-19
"""

import argparse
import csv
import io
import logging
import time
import zipfile
from datetime import datetime
from typing import Optional

import requests

from src.core.db import DB_PATH, get_conn

log = logging.getLogger("hermes.fno_oi")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
ARCHIVE_DIR = DB_PATH.parent / "fno"
# CL-RS-13: HTTP statuses that mean "NSE blocked/throttled us / server hiccup",
# NOT "no data exists for this date". These must surface as a retryable error so a
# rate-limit isn't silently recorded as a market holiday (a 0-row gap).
_RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}


class RetryableFetchError(Exception):
    """A transient/blocking fetch failure (e.g. NSE 403/429/5xx) — distinct from a
    genuine 'no F&O bhav for this date' (holiday / not-yet-posted)."""
_UDIFF_FIRST = "2024-07-01"        # NSE UDiFF F&O era (pre-that needs the legacy parser)
_FLAT_PRICE = 0.10                 # |price move| < this % ⇒ price treated as flat
_FLAT_OI = 0.50                    # |OI change| < this % ⇒ OI treated as flat


# --- fetch ------------------------------------------------------------------

def _fo_udiff_url(d: datetime) -> str:
    return (f"https://nsearchives.nseindia.com/content/fo/"
            f"BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip")


def _try_fetch(url: str, *, timeout: int = 30) -> Optional[bytes]:
    try:
        r = requests.get(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/zip,text/csv,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }, timeout=timeout)
    except requests.RequestException as e:
        # CL-RS-13: a network-level failure is transient, not a holiday.
        raise RetryableFetchError(f"network error fetching {url}: {e}") from e
    if r.status_code in _RETRYABLE_STATUS:
        raise RetryableFetchError(f"HTTP {r.status_code} fetching {url} (blocked/throttled)")
    if r.status_code != 200 or len(r.content) < 1000:
        return None                       # genuine no-data (404 / tiny body) = holiday/not-posted
    return r.content


def fetch_fo_for_date(d: datetime) -> Optional[bytes]:
    """The UDiFF F&O zip bytes for date d, or None (holiday / not-yet-posted).
    Raises RetryableFetchError (CL-RS-13) on a transient/blocking failure so callers
    don't misrecord an NSE block as a market holiday."""
    raw = _try_fetch(_fo_udiff_url(d))
    if raw and raw[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        return raw
    return None


def _csv_rows(raw: bytes) -> list:
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = z.namelist()[0]
    text = z.read(name).decode("utf-8", "ignore")
    return list(csv.DictReader(io.StringIO(text)))


# --- aggregate per underlying ----------------------------------------------

def _num(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "NA", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# CL-RS-06: choose the near-month expiry by a parsed DATE, never by a raw string
# min/<. The current UDiFF feed prints ISO (YYYY-MM-DD, which happens to sort
# chronologically), but if NSE ever reverts to DD-MMM-YYYY a lexical min() would
# pick the wrong chain. _exp_key returns a sortable (date) key with a far-future
# fallback so an unparseable expiry never wins "earliest".
_FAR_FUTURE = datetime(9999, 12, 31)


def _exp_key(xp) -> datetime:
    """Sortable date key for an expiry string (ISO or DD-MMM-YYYY)."""
    if not xp:
        return _FAR_FUTURE
    s = str(xp).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return _FAR_FUTURE


def aggregate_oi(rows: list) -> dict:
    """Per-underlying aggregation of stock FUTURES OI (summed across expiries) +
    the near-month futures price (for basis) + stock OPTIONS OI (PCR) + the
    near-month option chain by strike (for max-pain / support / resistance).
    Returns {symbol: {fut_oi, fut_oi_chg, n_fut, und_price, fut_price, near_exp,
    call_oi, put_oi, opt: {expiry: {strike: [call_oi, put_oi]}}}}."""
    agg: dict = {}
    for r in rows:
        tp = r.get("FinInstrmTp")
        sym = r.get("TckrSymb")
        if not sym:
            continue
        a = agg.setdefault(sym, {"fut_oi": 0.0, "fut_oi_chg": 0.0, "n_fut": 0,
                                 "und_price": None, "call_oi": 0.0, "put_oi": 0.0,
                                 "has_fut": False, "has_opt": False,
                                 "near_exp": None, "fut_price": None, "opt": {}})
        oi = _num(r.get("OpnIntrst")) or 0.0
        xp = r.get("XpryDt")
        if tp == "STF":                                  # stock future
            a["fut_oi"] += oi
            a["fut_oi_chg"] += (_num(r.get("ChngInOpnIntrst")) or 0.0)
            a["n_fut"] += 1
            a["has_fut"] = True
            up = _num(r.get("UndrlygPric"))
            if up:
                a["und_price"] = up
            # near-month future = earliest expiry; capture its close for the basis
            # (CL-RS-06: compare parsed dates, not raw expiry strings).
            if xp and (a["near_exp"] is None or _exp_key(xp) < _exp_key(a["near_exp"])):
                a["near_exp"] = xp
                a["fut_price"] = _num(r.get("ClsPric"))
        elif tp == "STO":                                # stock option
            a["has_opt"] = True
            ot = r.get("OptnTp")
            if ot == "CE":
                a["call_oi"] += oi
            elif ot == "PE":
                a["put_oi"] += oi
            k = _num(r.get("StrkPric"))
            if xp and k is not None:
                cell = a["opt"].setdefault(xp, {}).setdefault(k, [0.0, 0.0])
                if ot == "CE":
                    cell[0] += oi
                elif ot == "PE":
                    cell[1] += oi
    return agg


def _option_levels(strikes: dict) -> tuple:
    """From {strike: [call_oi, put_oi]} → (max_pain, support_strike, resistance_strike).
    Support = strike with the most PUT OI (the put wall buyers defend); resistance =
    strike with the most CALL OI (the call wall sellers cap); max-pain = the expiry
    price that minimises total in-the-money option payout (writers' least pain)."""
    if not strikes:
        return None, None, None
    ks = sorted(strikes)
    res = max(ks, key=lambda k: strikes[k][0]) if any(strikes[k][0] for k in ks) else None
    sup = max(ks, key=lambda k: strikes[k][1]) if any(strikes[k][1] for k in ks) else None
    best_k, best_pain = None, None
    for K in ks:
        pain = 0.0
        for kc in ks:
            co, po = strikes[kc]
            if kc < K:
                pain += co * (K - kc)        # ITM calls the writer pays out
            elif kc > K:
                pain += po * (kc - K)        # ITM puts the writer pays out
        if best_pain is None or pain < best_pain:
            best_pain, best_k = pain, K
    return best_k, sup, res


# --- quadrant ---------------------------------------------------------------

def quadrant(price_chg_pct: Optional[float], oi_chg_pct: Optional[float]) -> Optional[str]:
    """The four-quadrant positioning read (signed, descriptor)."""
    if price_chg_pct is None or oi_chg_pct is None:
        return None
    if abs(oi_chg_pct) < _FLAT_OI or abs(price_chg_pct) < _FLAT_PRICE:
        return "FLAT"
    up, oi_up = price_chg_pct > 0, oi_chg_pct > 0
    if up and oi_up:
        return "LONG_BUILDUP"
    if (not up) and oi_up:
        return "SHORT_BUILDUP"
    if (not up) and (not oi_up):
        return "LONG_UNWIND"
    return "SHORT_COVER"


def quadrant_read(q: Optional[str]) -> str:
    return {
        "LONG_BUILDUP": "long buildup — price up on rising OI (fresh longs)",
        "SHORT_BUILDUP": "short buildup — price down on rising OI (fresh shorts)",
        "LONG_UNWIND": "long unwinding — price down on falling OI (longs exiting)",
        "SHORT_COVER": "short covering — price up on falling OI (shorts exiting)",
        "FLAT": "flat — no decisive OI/price move",
    }.get(q or "", "")


# --- storage ----------------------------------------------------------------

_OI_COLS = [
    "symbol", "trade_date",
    "fut_oi", "fut_oi_chg", "fut_oi_chg_pct",
    "und_price", "price_chg_pct", "quadrant",
    "call_oi", "put_oi", "pcr", "n_fut_contracts",
    "fut_price", "basis_pct", "max_pain", "sup_strike", "res_strike",
]

_ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS fno_oi_signals (
    symbol TEXT NOT NULL, trade_date TEXT NOT NULL,
    fut_oi REAL, fut_oi_chg REAL, fut_oi_chg_pct REAL,
    und_price REAL, price_chg_pct REAL, quadrant TEXT,
    call_oi REAL, put_oi REAL, pcr REAL, n_fut_contracts INTEGER,
    fut_price REAL, basis_pct REAL, max_pain REAL, sup_strike REAL, res_strike REAL,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_fnooi_date ON fno_oi_signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_fnooi_quad ON fno_oi_signals(trade_date, quadrant);
"""

_NEW_COLS = {"fut_price": "REAL", "basis_pct": "REAL", "max_pain": "REAL",
             "sup_strike": "REAL", "res_strike": "REAL"}


def ensure_table() -> None:
    """Create + idempotently forward-migrate (basis / option-level columns were
    added after the first ship, so ADD COLUMN guards the existing VPS table)."""
    with get_conn() as conn:
        conn.executescript(_ENSURE_SQL)
        have = {r["name"] for r in conn.execute("PRAGMA table_info(fno_oi_signals)").fetchall()}
        for col, typ in _NEW_COLS.items():
            if col not in have:
                conn.execute(f"ALTER TABLE fno_oi_signals ADD COLUMN {col} {typ}")


def _price_chg_for_date(conn, trade_date: str) -> dict:
    """{symbol: price_chg_pct} from the cash bhav we already store (close vs
    prev_close), so the OI quadrant uses the SAME price series as MEP/DVPT."""
    out = {}
    for r in conn.execute(
        """SELECT symbol, close, prev_close FROM bhavcopy_rows
           WHERE trade_date=? AND series='EQ' AND (segment='CM' OR segment IS NULL)""",
        (trade_date,)).fetchall():
        c, p = r["close"], r["prev_close"]
        if c is not None and p and p > 0:
            out[r["symbol"]] = (c / p - 1.0) * 100.0
    return out


# CL-RS-02: a real one-day move in a name's WHOLE futures book is bounded; a
# day-over-day aggregate OI ratio outside this band is a corporate-action / lot-
# size / units discontinuity (e.g. BAJFINANCE 1:10 split 2025-06-16 decupled the
# stored aggregate), NOT a tradeable LONG/SHORT buildup. Outside the band we mark
# the OI-change % indeterminate (NULL) rather than emitting a fabricated +900%.
# Ordinary monthly expiry rolls keep the aggregate continuous (verified: the
# summed STF book glides across roll days), so they pass the band cleanly.
_OI_JUMP_MAX = 3.0   # fut_oi may be at most 3x the prior day's aggregate
_OI_DROP_MIN = 1.0 / 3.0   # ...and at least 1/3 of it


def _prior_fut_oi_for_date(conn, trade_date: str) -> dict:
    """{symbol: prior-day stored aggregate fut_oi} — the most recent fno_oi_signals
    row strictly before trade_date. This is the TRUE prior-day OI (per the audit),
    used in preference to the within-day reconstruction fut_oi - fut_oi_chg."""
    row = conn.execute(
        "SELECT MAX(trade_date) d FROM fno_oi_signals WHERE trade_date < ?",
        (trade_date,)).fetchone()
    if not row or not row["d"]:
        return {}
    return {r["symbol"]: r["fut_oi"] for r in conn.execute(
        "SELECT symbol, fut_oi FROM fno_oi_signals WHERE trade_date = ?",
        (row["d"],)).fetchall() if r["fut_oi"] is not None}


def _oi_chg_pct(fut_oi: float, fut_oi_chg: float, prior_stored) -> Optional[float]:
    """Day-over-day OI change %, made robust to roll / corporate-action breaks.

    Prefer the TRUE prior-day stored aggregate; fall back to the within-day
    reconstruction (fut_oi - fut_oi_chg) only when no prior row exists. Return
    None (indeterminate) when the prior base is non-positive OR the day-over-day
    aggregate ratio is implausible (a units / corporate-action discontinuity)."""
    prior_oi = (prior_stored if (prior_stored is not None and prior_stored > 0)
                else (fut_oi - fut_oi_chg))
    if prior_oi is None or prior_oi <= 0:
        return None
    # Plausibility band on the whole-book day-over-day ratio.
    if fut_oi is not None and fut_oi > 0:
        ratio = fut_oi / prior_oi
        if ratio > _OI_JUMP_MAX or ratio < _OI_DROP_MIN:
            return None
    return fut_oi_chg / prior_oi * 100.0


def compute_for_date(trade_date: str) -> int:
    """Fetch the F&O bhav for trade_date, aggregate STF OI per underlying, pair
    with the cash price change, store the quadrant. Idempotent (INSERT OR REPLACE)."""
    ensure_table()
    d = datetime.strptime(trade_date, "%Y-%m-%d")
    raw = fetch_fo_for_date(d)
    if not raw:
        log.info("no F&O bhav for %s (holiday / not posted)", trade_date)
        return 0
    agg = aggregate_oi(_csv_rows(raw))
    with get_conn() as conn:
        price_chg = _price_chg_for_date(conn, trade_date)
        prior_oi_map = _prior_fut_oi_for_date(conn, trade_date)
        out = []
        for sym, a in agg.items():
            if not a["has_fut"]:
                continue
            # CL-RS-02: robust OI-change % — true prior-day OI + corp-action guard.
            oi_chg_pct = _oi_chg_pct(a["fut_oi"], a["fut_oi_chg"], prior_oi_map.get(sym))
            pc = price_chg.get(sym)
            call_oi, put_oi = a["call_oi"], a["put_oi"]
            pcr = (put_oi / call_oi) if call_oi > 0 else None
            # basis = near-month future vs spot (premium = bullish carry)
            fp, up = a["fut_price"], a["und_price"]
            basis = ((fp - up) / up * 100.0) if (fp and up and up > 0) else None
            # option-chain levels from the near-month expiry
            # (CL-RS-06: earliest by parsed date, not lexical min of strings).
            near_opt = a["opt"].get(a["near_exp"])
            if near_opt is None and a["opt"]:
                near_opt = a["opt"][min(a["opt"], key=_exp_key)]
            mp, sup, res = _option_levels(near_opt) if near_opt else (None, None, None)
            out.append([
                sym, trade_date,
                a["fut_oi"], a["fut_oi_chg"], oi_chg_pct,
                a["und_price"], pc, quadrant(pc, oi_chg_pct),
                (call_oi or None), (put_oi or None), pcr, a["n_fut"],
                fp, basis, mp, sup, res,
            ])
        if out:
            ph = ",".join("?" * len(_OI_COLS))
            conn.executemany(
                f"INSERT OR REPLACE INTO fno_oi_signals ({','.join(_OI_COLS)}) VALUES ({ph})", out)
    log.info("F&O OI %s: %d underlyings stored", trade_date, len(out))
    return len(out)


def run_today() -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return False, "no cash bhav found"
    try:
        n = compute_for_date(row["d"])
    except RetryableFetchError as e:        # CL-RS-13: report a block as a FAILURE, not a 0-row holiday
        return False, f"F&O OI fetch blocked/throttled for {row['d']}: {e}"
    return True, f"F&O OI: {n} underlyings for {row['d']}"


def run_backfill() -> tuple[int, int]:
    """Walk every cash-bhav trading day in the UDiFF era and pull its F&O OI."""
    ensure_table()
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? ORDER BY trade_date",
            (_UDIFF_FIRST,)).fetchall()]
    log.info("F&O OI backfill: %d trading days from %s", len(dates), _UDIFF_FIRST)
    days = total = 0
    for i, d in enumerate(dates, 1):
        with get_conn() as conn:
            exists = conn.execute(
                "SELECT 1 FROM fno_oi_signals WHERE trade_date=? LIMIT 1", (d,)).fetchone()
        if exists:
            continue
        try:
            n = compute_for_date(d)
            if n:
                days += 1
                total += n
        except Exception as e:
            log.warning("F&O OI failed for %s: %s", d, e)
        if i % 25 == 0:
            log.info("  progress: %d / %d days, %d rows", i, len(dates), total)
        time.sleep(1.0)        # be gentle on the NSE archive
    log.info("F&O OI backfill complete: %d days, %d rows", days, total)
    return days, total


def run_recent(n: int) -> tuple[int, int]:
    """Recompute the last n trading days (re-fetch + INSERT OR REPLACE), so newly
    added columns (basis / option levels) get populated without a full re-backfill."""
    ensure_table()
    with get_conn() as conn:
        dates = [r["trade_date"] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM bhavcopy_rows WHERE trade_date>=? "
            "ORDER BY trade_date DESC LIMIT ?", (_UDIFF_FIRST, n)).fetchall()]
    log.info("F&O OI recompute: last %d trading days", len(dates))
    days = total = 0
    for d in reversed(dates):
        try:
            k = compute_for_date(d)
            if k:
                days += 1
                total += k
        except Exception as e:
            log.warning("F&O OI recompute failed for %s: %s", d, e)
        time.sleep(1.0)
    log.info("F&O OI recompute complete: %d days, %d rows", days, total)
    return days, total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true", help="every UDiFF-era trading day")
    p.add_argument("--recent", type=int, help="recompute the last N trading days (repopulate new cols)")
    p.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.backfill:
        run_backfill()
    elif args.recent:
        run_recent(args.recent)
    elif args.date:
        compute_for_date(args.date)
    else:
        ok, msg = run_today()
        log.info(msg)


if __name__ == "__main__":
    main()
