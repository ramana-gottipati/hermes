"""NSE surveillance-state ingest — ASM/GSM lists (D-02) + security-wise price bands (D-03).

Charter D88 wave-1 feeds, both primary-source and ₹0:
  - ASM  : https://www.nseindia.com/api/reportASM   (JSON: longterm + shortterm stages)
  - GSM  : https://www.nseindia.com/api/reportGSM   (JSON array of stages)
  - Bands: https://nsearchives.nseindia.com/content/equities/sec_list.csv (daily full file)

What this unlocks (postmortem / charter): surveillance STATE as veto-context on scans and the
war room ("this reaction name is in ASM Stage II"), forced-flow EVENT streams (entering/leaving
a stage moves flows mechanically), and the X-05 band-lock study (close==band for N days needs
per-day band state). Everything DESCRIPTIVE — boards and context chips, never a gate (the
distress-composite coverage-cliff lesson: n is small; label, don't filter).

Storage (space doctrine — bounded, transitions are the signal):
  - surveillance_flags : APPEND one row per (day, framework, symbol) — the raw daily state.
    ~400 rows/day; transitions derivable by self-join, history stays honest.
  - price_bands_current: today's full file, DELETE+rewrite (one snapshot, ~3.3K rows).
  - price_band_events  : APPEND only band CHANGES vs the previous current snapshot —
    per-day band state for any past date reconstructs from events + current.

Ops discipline: fetch EVERYTHING into memory first, then write in short transactions —
never hold a write txn across network I/O (the D82c site-wide-000 outage lesson).

CLI:
  python -m src.automation.surveillance --ingest     # the nightly unit's entry
  python -m src.automation.surveillance --selftest   # offline parser checks
"""
from __future__ import annotations

import csv
import io
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

import requests

from src.core.db import get_conn

log = logging.getLogger("hermes.surveillance")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

USER_AGENT = "Mozilla/5.0 (Hermes Personal Agent)"
ASM_URL = "https://www.nseindia.com/api/reportASM"
GSM_URL = "https://www.nseindia.com/api/reportGSM"
BANDS_URL = "https://nsearchives.nseindia.com/content/equities/sec_list.csv"

_DDL = """
CREATE TABLE IF NOT EXISTS surveillance_flags (
    as_of      TEXT NOT NULL,           -- list date (from the feed's own timestamp)
    framework  TEXT NOT NULL,           -- 'ASM-LT' | 'ASM-ST' | 'GSM'
    symbol     TEXT NOT NULL,
    stage      TEXT,                    -- 'Stage I' … / GSM stage code
    surv_code  TEXT,
    surv_desc  TEXT,
    isin       TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(as_of, framework, symbol)
);
CREATE INDEX IF NOT EXISTS idx_surv_sym ON surveillance_flags(symbol, as_of);
CREATE INDEX IF NOT EXISTS idx_surv_asof ON surveillance_flags(as_of, framework);
CREATE TABLE IF NOT EXISTS price_bands_current (
    as_of   TEXT NOT NULL,
    symbol  TEXT NOT NULL,
    series  TEXT,
    band    TEXT,                       -- '2' | '5' | '10' | '20' | 'No Band' (text, as published)
    remarks TEXT,
    UNIQUE(symbol, series)
);
CREATE TABLE IF NOT EXISTS price_band_events (
    as_of    TEXT NOT NULL,             -- day the CHANGE was observed
    symbol   TEXT NOT NULL,
    series   TEXT,
    old_band TEXT,                      -- NULL = first appearance
    new_band TEXT,                      -- NULL = dropped from the file
    UNIQUE(as_of, symbol, series)
);
CREATE INDEX IF NOT EXISTS idx_pbe_sym ON price_band_events(symbol, as_of);
"""


def _ist_today() -> str:
    return (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")


def _norm_date(s: Optional[str]) -> Optional[str]:
    """'07-Jul-2026' or '07-Jul-2026 08:07:02' -> '2026-07-07'."""
    if not s:
        return None
    s = str(s).strip().split(" ")[0]
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _fetch(url: str, json_: bool = False):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT,
                                       "Accept": "application/json,text/csv,*/*",
                                       "Referer": "https://www.nseindia.com/"}, timeout=30)
    except requests.RequestException as e:
        log.warning("fetch %s failed: %s", url, e)
        return None
    if r.status_code != 200 or len(r.content) < 20:
        log.warning("fetch %s HTTP %s len=%s", url, r.status_code, len(r.content))
        return None
    return r.json() if json_ else r.text


# ── parsers (pure; selftest-covered) ─────────────────────────────────────────

def parse_asm(payload: dict) -> list[dict]:
    """reportASM -> rows for BOTH longterm ('ASM-LT') and shortterm ('ASM-ST')."""
    out = []
    for key, fw in (("longterm", "ASM-LT"), ("shortterm", "ASM-ST")):
        data = ((payload or {}).get(key) or {}).get("data") or []
        for e in data:
            sym = (e.get("symbol") or "").strip().upper()
            if not sym:
                continue
            out.append({
                "as_of": _norm_date(e.get("asmTime")) or _ist_today(),
                "framework": fw, "symbol": sym,
                "stage": (e.get("asmSurvIndicator") or "").strip() or None,
                "surv_code": (e.get("survCode") or "").strip() or None,
                "surv_desc": (e.get("survDesc") or "").strip() or None,
                "isin": (e.get("isin") or "").strip() or None,
            })
    return out


def parse_gsm(payload: list) -> list[dict]:
    out = []
    for e in payload or []:
        sym = (e.get("symbol") or "").strip().upper()
        if not sym:
            continue
        out.append({
            "as_of": _norm_date(e.get("gsmTime")) or _ist_today(),
            "framework": "GSM", "symbol": sym,
            "stage": (str(e.get("gsmStage")) or "").strip() or None,
            "surv_code": (e.get("survCode") or "").strip() or None,
            "surv_desc": (e.get("survDesc") or "").strip() or None,
            "isin": (e.get("isin") or "").strip() or None,
        })
    return out


def parse_bands(text: str) -> list[dict]:
    """sec_list.csv: Symbol,Series,Security Name,Band,Remarks."""
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else v)
             for k, v in r.items()}
        sym = (r.get("symbol") or "").upper()
        if not sym:
            continue
        out.append({"symbol": sym, "series": (r.get("series") or "").upper() or None,
                    "band": (r.get("band") or "").strip() or None,
                    "remarks": (r.get("remarks") or "").strip().strip('"') or None})
    return out


# ── ingest ────────────────────────────────────────────────────────────────────

def ingest() -> dict:
    """Fetch all three feeds (network FIRST, no open txn), then write short txns."""
    asm_raw = _fetch(ASM_URL, json_=True)
    gsm_raw = _fetch(GSM_URL, json_=True)
    bands_raw = _fetch(BANDS_URL)

    flags = (parse_asm(asm_raw) if asm_raw else []) + (parse_gsm(gsm_raw) if gsm_raw else [])
    bands = parse_bands(bands_raw) if bands_raw else []
    today = _ist_today()
    stats = {"asm_lt": sum(1 for f in flags if f["framework"] == "ASM-LT"),
             "asm_st": sum(1 for f in flags if f["framework"] == "ASM-ST"),
             "gsm": sum(1 for f in flags if f["framework"] == "GSM"),
             "bands": len(bands), "band_events": 0}

    with get_conn() as conn:
        conn.executescript(_DDL)
        if flags:
            conn.executemany(
                "INSERT OR IGNORE INTO surveillance_flags"
                "(as_of, framework, symbol, stage, surv_code, surv_desc, isin) "
                "VALUES (:as_of, :framework, :symbol, :stage, :surv_code, :surv_desc, :isin)",
                flags)
        conn.commit()

    if bands:
        with get_conn() as conn:
            prev = {(r["symbol"], r["series"]): r["band"] for r in conn.execute(
                "SELECT symbol, series, band FROM price_bands_current")}
            had_baseline = bool(prev)
            cur = {(b["symbol"], b["series"]): b["band"] for b in bands}
            events = []
            if had_baseline:                       # first run just establishes the baseline
                for k, new in cur.items():
                    old = prev.get(k)
                    if old != new:
                        events.append((today, k[0], k[1], old, new))
                for k, old in prev.items():
                    if k not in cur:
                        events.append((today, k[0], k[1], old, None))
            conn.execute("DELETE FROM price_bands_current")
            conn.executemany(
                "INSERT OR REPLACE INTO price_bands_current(as_of, symbol, series, band, remarks) "
                "VALUES (?,?,?,?,?)",
                [(today, b["symbol"], b["series"], b["band"], b["remarks"]) for b in bands])
            if events:
                conn.executemany(
                    "INSERT OR IGNORE INTO price_band_events"
                    "(as_of, symbol, series, old_band, new_band) VALUES (?,?,?,?,?)", events)
            conn.commit()
            stats["band_events"] = len(events)
            if not had_baseline:
                log.info("price bands: baseline established (%d rows, no events)", len(bands))

    log.info("surveillance ingest: ASM-LT %(asm_lt)d · ASM-ST %(asm_st)d · GSM %(gsm)d · "
             "bands %(bands)d (%(band_events)d changes)", stats)
    return stats


# ── selftest (offline) ───────────────────────────────────────────────────────

def selftest() -> None:
    asm = {"longterm": {"data": [{"symbol": "aaa", "asmSurvIndicator": "Stage I",
                                  "asmTime": "07-Jul-2026", "survCode": "LTASM - I (13)",
                                  "survDesc": "d", "isin": "INE1"}]},
           "shortterm": {"data": [{"symbol": "BBB", "asmSurvIndicator": "Stage II",
                                   "asmTime": "07-Jul-2026"}]}}
    rows = parse_asm(asm)
    assert len(rows) == 2 and rows[0]["symbol"] == "AAA" and rows[0]["framework"] == "ASM-LT"
    assert rows[0]["as_of"] == "2026-07-07" and rows[1]["framework"] == "ASM-ST"
    gsm = [{"symbol": "ccc", "gsmStage": "IV", "gsmTime": "07-Jul-2026 08:07:02"}]
    g = parse_gsm(gsm)
    assert g[0]["symbol"] == "CCC" and g[0]["stage"] == "IV" and g[0]["as_of"] == "2026-07-07"
    b = parse_bands('Symbol,Series,Security Name,Band,Remarks\n'
                    'XYZ,EQ,X Y Z LTD,2,"-"\nPQR,BE,P Q R LTD,No Band,"-"\n')
    assert len(b) == 2 and b[0]["band"] == "2" and b[1]["band"] == "No Band"
    assert _norm_date("07-Jul-2026 08:07:02") == "2026-07-07"
    assert parse_asm({}) == [] and parse_gsm([]) == [] and parse_bands("Symbol\n") == []
    print("SURVEILLANCE selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--ingest" in sys.argv:
        ingest()
    else:
        print(__doc__)
