"""PRIMARY-SOURCE shareholding ingest — NSE shareholding-pattern XBRL (Guardrail #8, Phase 2c).

Replaces the Screener.in dependency for NEW ``shareholding_history`` periods (promoter /
FII / DII / public %), the companion of ``fundamentals_xbrl.py``. Source: the NSE
``corporate-share-holdings-master`` listing (quarterly SEBI Reg 31 shareholding-pattern
submissions; ``broadcastDate`` = the true PIT knowable_at, revision fields included) +
the per-filing ``in-bse-shp`` XBRL instance.

Category mapping (verified live on RELIANCE 2026-03-31, values are FRACTIONS ×100):
  Promoters   = ShareholdingAsAPercentageOfTotalNumberOfShares @ ShareholdingOfPromoterAndPromoterGroup_ContextI
  Public      = … @ PublicShareholding_ContextI
  FIIs        = … @ InstitutionsForeign_ContextI        (the whole foreign-institutions block)
  DIIs        = … @ InstitutionsDomestic_ContextI
  Government  = … @ CentralGovernmentOrStateGovernments_ContextI (absent -> NULL, never zero)
  Promoter Pledge (NEW metric — Screener era never had it; fundamentals_asof returns
  promoter_pledge=None today, so this is additive and fills the PIT gap for patearn's
  >20%-pledge hard disqualifier):
    boolean WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged[ForPromoterAndPromoterGroup]
    == false -> 0.0 (a filed "No" is a REAL zero); == true -> the pledged-% fact at the
    promoter context (fail-loud NULL if the fact can't be resolved).

Same rules as the fundamentals migration: per-row ``source`` column (NULL = Screener era,
never overwritten), commit-per-filing (the write lock must never span a network fetch —
2026-07-02 outage lesson), ``shareholding_gg_seen`` resume table + a consecutive-failure
circuit breaker (nsearchives throttles after ~1k downloads), provenance.observe with the
real broadcast, and a light per-symbol continuity gate on Promoters (should match the
Screener series near-exactly for the same period; >1pp divergence = skip + log).

Run (VPS):
  python -m src.automation.shareholding_xbrl --probe RELIANCE
  python -m src.automation.shareholding_xbrl --ingest --since 2026-04-01 --symbols RELIANCE,TCS
  python -m src.automation.shareholding_xbrl --ingest --since 2026-06-25       # global window
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from src.automation import provenance

log = logging.getLogger("hermes.shareholding_xbrl")

RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

_NSE_HOME = "https://www.nseindia.com"
_NSE_REF = "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern"
_NSE_API = "https://www.nseindia.com/api/corporate-share-holdings-master"
_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/122 Safari/537.36")
REQUEST_PAUSE = 1.5
SOURCE = "NSE-XBRL-SHP"

_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# metric -> the instant-context id carrying its ShareholdingAsAPercentageOfTotalNumberOfShares
_CATEGORY_CTX = {
    "Promoters": "ShareholdingOfPromoterAndPromoterGroup_ContextI",
    "Public": "PublicShareholding_ContextI",
    "FIIs": "InstitutionsForeign_ContextI",
    "DIIs": "InstitutionsDomestic_ContextI",
    "Government": "CentralGovernmentOrStateGovernments_ContextI",
}
_PCT_TAG = "ShareholdingAsAPercentageOfTotalNumberOfShares"
_PLEDGE_BOOLS = (
    "WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup",
    "WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged",
)


def _nse_session():
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)
    s.get(_NSE_REF, headers=h, timeout=20)
    return s, h


def _parse_dt(s: Optional[str]) -> Optional[str]:
    """'21-APR-2026 13:25:14' / '31-MAR-2026' -> ISO."""
    if not s:
        return None
    m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?", s.strip())
    if not m:
        return None
    dd, mon, yyyy, hms = m.groups()
    mi = _MON.get(mon.title())
    if not mi:
        return None
    iso = f"{yyyy}-{mi:02d}-{dd}"
    return f"{iso} {hms}" if hms else iso


def list_shp(*, symbol: Optional[str] = None, from_date: Optional[str] = None,
             to_date: Optional[str] = None, session=None, headers=None) -> list:
    """Shareholding-pattern submissions. Rows: symbol, period_end (ISO quarter end),
    broadcast (ISO datetime), revised (bool), xbrl_url, promoter_pct/public_pct (listing-level)."""
    if session is None:
        session, headers = _nse_session()
    params = {"index": "equities"}
    if symbol:
        params["symbol"] = symbol
    if from_date:
        params["from_date"] = datetime.strptime(from_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    if to_date:
        params["to_date"] = datetime.strptime(to_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    r = session.get(_NSE_API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    items = j if isinstance(j, list) else (j.get("data") or [])
    out = []
    for it in items:
        xbrl = (it.get("xbrl") or "").strip()
        pend = _parse_dt((it.get("date") or "").title())
        if not xbrl.lower().endswith(".xml") or not pend:
            continue

        def _pct(v):
            try:
                return float(str(v).replace(",", ""))
            except (TypeError, ValueError):
                return None
        out.append({
            "symbol": (it.get("symbol") or "").strip(),
            "period_end": pend[:10],
            "broadcast": _parse_dt((it.get("broadcastDate") or it.get("submissionDate") or "").title()),
            "revised": (it.get("revisedData") or "N").strip().upper() == "Y",
            "xbrl_url": xbrl,
            "promoter_pct": _pct(it.get("pr_and_prgrp")),
            "public_pct": _pct(it.get("public_val")),
        })
    return out


# ── minimal XBRL instance parse (deliberately local — fundamentals_xbrl.py is a
#    parallel-session hot file right now; this 25-line subset decouples the modules) ──
def parse_facts(xml_text: str) -> list:
    """[(localname, contextRef, value_or_None)] — xsi:nil / empty -> None."""
    root = ET.fromstring(xml_text)
    nil = "{http://www.w3.org/2001/XMLSchema-instance}nil"
    facts = []
    for el in root.iter():
        ctx = el.get("contextRef")
        if ctx is None:
            continue
        val = None if el.get(nil) == "true" else ((el.text or "").strip() or None)
        facts.append((el.tag.rsplit("}", 1)[-1], ctx, val))
    return facts


def _num(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def extract_shp(xml_text: str) -> dict:
    """(metric -> percent 0-100) from one SHP instance; missing category -> absent (never 0)."""
    facts = parse_facts(xml_text)
    by = {}
    for name, ctx, val in facts:
        by.setdefault((name, ctx), val)
    m: dict = {}
    for metric, ctx in _CATEGORY_CTX.items():
        v = _num(by.get((_PCT_TAG, ctx)))
        if v is not None:
            m[metric] = round(v * 100.0, 2)          # instances carry fractions (0.5 = 50%)
    # promoter pledge: a filed "No" is a real zero; a "Yes" needs the pledged-% fact
    pledged = None
    for b in _PLEDGE_BOOLS:
        bv = by.get((b, "MainI"))
        if bv is not None:
            pledged = str(bv).strip().lower() == "true"
            break
    if pledged is False:
        m["Promoter Pledge"] = 0.0
    elif pledged is True:
        # % of the promoter group's OWN holding that is pledged (the Screener/patearn
        # >20%-disqualifier convention) = EncumberedShareUnderPledged…% at the
        # promoter-group context. Verified live: VIKRAMSOLR 6.77 / JPPOWER 72.99 /
        # SAGCEM 29.99 (per-individual and whole-company contexts must NOT win).
        exact = [_num(v) for (name, ctx, v) in facts
                 if name.startswith("EncumberedShareUnderPledgedAsPercentage")
                 and ctx == "ShareholdingOfPromoterAndPromoterGroup_ContextI" and _num(v) is not None]
        fallback = [_num(v) for (name, ctx, v) in facts
                    if "pledg" in name.lower() and "percentage" in name.lower()
                    and ctx.startswith("ShareholdingOfPromoterAndPromoterGroup") and _num(v) is not None]
        cand = exact or fallback
        if cand:
            m["Promoter Pledge"] = round(cand[0] * 100.0, 2)
        else:
            log.warning("pledge=Yes but no pledged-%% fact resolved (fail-loud NULL)")
    # shareholder count (total public+promoter contexts vary; keep the two headline ones)
    n_sh = _num(by.get(("NumberOfShareholders", "MainI")))
    if n_sh is not None:
        m["No. of Shareholders"] = n_sh
    return m


# ── persistence (same forward-only + source-column contract as fundamentals) ─
def _ensure_schema(con: sqlite3.Connection) -> None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(shareholding_history)")]
    if "source" not in cols:
        con.execute("ALTER TABLE shareholding_history ADD COLUMN source TEXT")
    con.execute("""CREATE TABLE IF NOT EXISTS shareholding_gg_seen (
        xml_url TEXT PRIMARY KEY, processed_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    con.execute("""CREATE TABLE IF NOT EXISTS shareholding_xbrl_gate (
        symbol TEXT PRIMARY KEY, checked_at TEXT, pass INTEGER, detail TEXT)""")


def _gate(con: sqlite3.Connection, sym: str, period_end: str, promoters_xbrl: Optional[float]) -> bool:
    """Light continuity gate: for the symbol's FIRST XBRL write, if a Screener-era
    Promoters row exists for the same period it must agree within 1pp (same SEBI filing
    underneath -> near-exact expected). Cached; no overlap -> auto-pass."""
    row = con.execute("SELECT pass FROM shareholding_xbrl_gate WHERE symbol=?", (sym,)).fetchone()
    if row is not None:
        return bool(row[0])
    if promoters_xbrl is None:
        return False                       # can't judge yet; retry next filing (no cache)
    prior = con.execute(
        "SELECT value FROM shareholding_history WHERE symbol=? AND period_end=? "
        "AND metric='Promoters' AND source IS NULL", (sym, period_end)).fetchone()
    if prior is None or prior[0] is None:
        verdict, detail = True, "no Screener overlap (auto-pass)"
    else:
        diff = abs(float(prior[0]) - promoters_xbrl)
        verdict = diff <= 1.0
        detail = f"Promoters@{period_end}: xbrl={promoters_xbrl} screener={prior[0]} diff={diff:.2f}pp"
    con.execute("INSERT OR REPLACE INTO shareholding_xbrl_gate VALUES (?,datetime('now'),?,?)",
                (sym, int(verdict), detail))
    if not verdict:
        log.warning("shareholding gate FAIL %s: %s", sym, detail)
    return verdict


def write_rows(con: sqlite3.Connection, filing: dict, metrics: dict) -> int:
    sym, pend = filing["symbol"], filing["period_end"]
    rdate = (filing["broadcast"] or "")[:10] or None
    if not metrics or not rdate:
        return 0
    n = 0
    for metric, value in metrics.items():
        cur = con.execute(
            "SELECT source FROM shareholding_history WHERE symbol=? AND period_end=? AND metric=?",
            (sym, pend, metric)).fetchone()
        if cur is not None and cur[0] is None:
            continue                      # never replace a Screener-era row
        con.execute(
            "INSERT OR REPLACE INTO shareholding_history"
            "(symbol,period_type,period_end,report_date,metric,value,source) "
            "VALUES (?,?,?,?,?,?,?)", (sym, "Q", pend, rdate, metric, value, SOURCE))
        n += 1
    if n:
        provenance.observe("shareholding_history", provenance.period_key(sym, "Q", pend),
                           symbol=sym, knowable_at=filing["broadcast"],
                           source_note="NSE SHP XBRL (corporate-share-holdings-master)")
    return n


def ingest(*, since: str, until: Optional[str] = None, symbols: Optional[list] = None,
           research_db: str = RESEARCH_DB, pause: float = REQUEST_PAUSE) -> dict:
    """Forward ingest of shareholding patterns broadcast in [since, until]."""
    until = until or date.today().isoformat()
    session, headers = _nse_session()
    rows: list = []
    if symbols:
        for s in symbols:
            rows += list_shp(symbol=s, session=session, headers=headers)
            time.sleep(pause)
    else:
        rows = list_shp(from_date=since, to_date=until, session=session, headers=headers)
    rows = [r for r in rows if r["broadcast"] and since <= r["broadcast"][:10] <= until]
    # revisions: keep the LAST broadcast per (symbol, period_end)
    best: dict = {}
    for r in rows:
        k = (r["symbol"], r["period_end"])
        if k not in best or (r["broadcast"] or "") > (best[k]["broadcast"] or ""):
            best[k] = r
    work = sorted(best.values(), key=lambda x: (x["symbol"], x["period_end"]))
    log.info("shp ingest window %s..%s: %d submissions, %d after revision-dedup",
             since, until, len(rows), len(work))

    stats = {"submissions": len(rows), "to_parse": len(work), "parsed": 0, "rows": 0,
             "fetch_fail": 0, "gate_fail_syms": 0, "skipped_seen": 0, "aborted_throttled": False}
    con = sqlite3.connect(research_db)
    _ensure_schema(con)
    con.commit()
    consec_fail = 0
    gate_ok: dict = {}
    for f in work:
        if gate_ok.get(f["symbol"]) is False:
            continue
        if con.execute("SELECT 1 FROM shareholding_gg_seen WHERE xml_url=?",
                       (f["xbrl_url"],)).fetchone():
            stats["skipped_seen"] += 1
            continue
        try:
            xr = session.get(f["xbrl_url"], headers=headers, timeout=45)
            if xr.status_code != 200:
                raise RuntimeError("HTTP %s" % xr.status_code)
            metrics = extract_shp(xr.text)
        except ET.ParseError as e:
            log.warning("shp parse failed %s %s: %s", f["symbol"], f["period_end"], e)
            time.sleep(pause)
            continue
        except Exception as e:  # noqa: BLE001
            consec_fail += 1
            stats["fetch_fail"] += 1
            log.warning("shp xml failed %s (%s): %s", f["symbol"], f["xbrl_url"][-36:], e)
            if consec_fail >= 6:
                log.warning("shp: %d consecutive failures — throttled; aborting cleanly", consec_fail)
                stats["aborted_throttled"] = True
                break
            time.sleep(pause + 5 * consec_fail)
            continue
        consec_fail = 0
        if f["symbol"] not in gate_ok:
            gate_ok[f["symbol"]] = _gate(con, f["symbol"], f["period_end"], metrics.get("Promoters"))
            if not gate_ok[f["symbol"]]:
                stats["gate_fail_syms"] += 1
        if gate_ok[f["symbol"]]:
            stats["parsed"] += 1
            stats["rows"] += write_rows(con, f, metrics)
            con.execute("INSERT OR IGNORE INTO shareholding_gg_seen (xml_url) VALUES (?)",
                        (f["xbrl_url"],))
        # commit per filing — the write lock must never span a network fetch
        con.commit()
        time.sleep(pause)
    con.close()
    log.info("shp ingest done: %s", stats)
    return stats


def sync_pledge_to_fundamentals(*, research_db: str = RESEARCH_DB, hermes_conn=None) -> dict:
    """S77b class-fix: refresh hermes.db ``fundamentals.promoter_pledge`` from the SHP feed.

    The frozen Screener-era ``fundamentals`` table is still read by pat/flows.py (the
    NULL-tolerant "clean: Pledge < 5%" screen filter), pat/web.py + dashboard.py (dossier
    facts) and concall_veto's fallback — all of which saw NULL/stale pledge (the same
    false-clean class as the S76 veto gap). Rather than rewiring three readers onto a
    cross-DB join, sync the ONE column from the primary source (guardrail #8-compliant):
    UPDATE-only for symbols that already have a fundamentals row (never inserts — the Pat
    screen universe is unchanged), never NULLs an existing value, value-diff writes only.
    Bounded local txn (no network inside — D82c class). Non-fatal by contract: callers
    wrap in try/except; a sync failure must never fail the nightly ingest."""
    latest: dict = {}
    rcon = sqlite3.connect(f"file:{research_db}?mode=ro", uri=True, timeout=20)
    try:
        for sym, val in rcon.execute(
                "SELECT symbol, value FROM shareholding_history "
                "WHERE metric='Promoter Pledge' AND value IS NOT NULL ORDER BY period_end"):
            latest[sym] = val          # ordered by period_end -> latest wins
    finally:
        rcon.close()

    stats = {"shp_symbols": len(latest), "fund_rows": 0, "updated": 0, "unchanged": 0}
    own = hermes_conn is None
    if own:
        from src.core.db import get_conn
        ctx = get_conn()
        conn = ctx.__enter__()
    else:
        ctx, conn = None, hermes_conn
    try:
        rows = conn.execute("SELECT symbol, promoter_pledge FROM fundamentals").fetchall()
        stats["fund_rows"] = len(rows)
        for r in rows:
            sym, old = r["symbol"], r["promoter_pledge"]
            new = latest.get(sym)
            if new is None:
                continue                                   # no SHP data -> keep legacy value
            if old is not None and abs(old - new) < 1e-9:
                stats["unchanged"] += 1
                continue
            conn.execute("UPDATE fundamentals SET promoter_pledge=? WHERE symbol=?", (new, sym))
            stats["updated"] += 1
        conn.commit()
    finally:
        if own:
            ctx.__exit__(None, None, None)
    log.info("pledge->fundamentals sync: %s", stats)
    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", metavar="SYMBOL")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--sync-pledge", action="store_true",
                    help="refresh fundamentals.promoter_pledge from the SHP feed (also runs after --ingest)")
    ap.add_argument("--since", default=(date.today() - timedelta(days=7)).isoformat())
    ap.add_argument("--until", default=None)
    ap.add_argument("--symbols", default=None, help="comma-separated (default: global window)")
    ap.add_argument("--db", default=RESEARCH_DB)
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None

    if args.probe:
        session, headers = _nse_session()
        rows = list_shp(symbol=args.probe.upper(), session=session, headers=headers)
        for f in rows[:2]:
            xml = session.get(f["xbrl_url"], headers=headers, timeout=45).text
            print(f"\n{f['symbol']} {f['period_end']} broadcast={f['broadcast']} "
                  f"revised={f['revised']} listing: promoter={f['promoter_pct']} public={f['public_pct']}")
            for k, v in sorted(extract_shp(xml).items()):
                print(f"  {k:20s} {v}")
            time.sleep(REQUEST_PAUSE)
    elif args.ingest:
        ingest(since=args.since, until=args.until, symbols=syms, research_db=args.db)
        try:
            sync_pledge_to_fundamentals(research_db=args.db)
        except Exception:  # noqa: BLE001 — the sync must never fail the nightly ingest
            log.exception("pledge->fundamentals sync failed (non-fatal)")
    elif args.sync_pledge:
        sync_pledge_to_fundamentals(research_db=args.db)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
