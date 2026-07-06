"""Insider / promoter / pledge events (Dataset "A" — taxonomy-first spike).

The Claude+Codex ROI debate (codex-bridge/DISCUSSION-dataset-roi.md, D76) ranked A as the
flagship first NEW external feed — most orthogonal to the existing stack, densest in the
under-covered smallcap tail where alpha migrated, and carrying BOTH conviction (open-market
promoter buys) AND distress (pledge creation/invocation, promoter selling) in one stream.

Codex's decisive caveat, adopted in full: **raw SEBI PIT/SAST data is cleanly timestamped
NOISY disclosure data — the false-positive classifier IS the product.** "promoter bought =
bullish" is banned. So this module is built taxonomy-first: the event classifier + PIT
aggregation + schema + synthetic tests land HERE, locally; the exchange fetcher is a
documented stub for the VPS wiring step (real disclosure formats must be confirmed on live data).

Two hard rules from the debate:
  1. PIT clock = exchange DISCLOSURE/broadcast date (`disclosure_dt`), never the transaction date.
  2. Never mix plumbing (inter-se transfers, ESOP, gifts, allotments, conversions) or pledge
     mechanics with open-market conviction. Each gets its own class.

Sources for the fetcher (VPS step, all free, all-cap incl. SME):
  - NSE PIT Reg 7(2) (CSV + XBRL); NSE SAST Reg 29/31 + pledged-data pages
  - BSE insider-trading / XBRL pages (fallback; same pipe as concall_bse.py)

CLI:
  python -m src.automation.insider_events --selftest      # taxonomy + aggregation checks, no DB
  python -m src.automation.insider_events --classify "Market Sale" --disp Disposal --cat Promoter
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.insider_events")

# --- transaction taxonomy --------------------------------------------------
# The order of checks matters: pledge/encumbrance and named modes are resolved
# BEFORE the generic market buy/sell fallback.

PLEDGE_CREATE = "PLEDGE_CREATE"     # creation/increase of pledge or encumbrance
PLEDGE_RELEASE = "PLEDGE_RELEASE"   # revocation/release (NOT automatically bullish)
PLEDGE_INVOKE = "PLEDGE_INVOKE"     # invocation — lender sold the pledged shares (strong distress)
INTER_SE = "INTER_SE"               # promoter-to-promoter transfer (plumbing)
ESOP = "ESOP"                       # option exercise / ESOP allotment (plumbing)
GIFT = "GIFT"
INHERITANCE = "INHERITANCE"         # transmission / succession
ALLOTMENT = "ALLOTMENT"            # preferential / rights / bonus / QIP (plumbing)
CONVERSION = "CONVERSION"           # warrants / convertibles
SCHEME = "SCHEME"                   # amalgamation / merger / demerger / arrangement (plumbing)
OFF_MARKET = "OFF_MARKET"           # off-market, otherwise unclassified
OPEN_MARKET_BUY = "OPEN_MARKET_BUY"
OPEN_MARKET_SELL = "OPEN_MARKET_SELL"
UNKNOWN = "UNKNOWN"

_PLUMBING = {INTER_SE, ESOP, GIFT, INHERITANCE, ALLOTMENT, CONVERSION, SCHEME, OFF_MARKET}
_PLEDGE_ADVERSE = {PLEDGE_CREATE, PLEDGE_INVOKE}

_PRINCIPAL_KEYS = ("promoter", "director", "kmp", "key managerial", "chairman",
                   "whole-time", "wholetime", "managing director", " md", "ceo", "cfo",
                   "chief executive", "chief financial")


def _has(s: str, *keys: str) -> bool:
    return any(k in s for k in keys)


def classify_txn(mode: Optional[str], acq_disp: Optional[str] = None,
                 regulation: Optional[str] = None) -> str:
    """Map a raw disclosure (mode + acquisition/disposal + regulation) to a txn_class.

    This is the moat: raw modes are messy free text. Precedence: pledge/encumbrance →
    named plumbing modes → market buy/sell → off-market → UNKNOWN.
    """
    m = (mode or "").lower().strip()
    ad = (acq_disp or "").lower().strip()
    reg = (regulation or "").lower().strip()

    # --- pledge / encumbrance (SAST Reg 31 is the encumbrance disclosure) ---
    pledge_ctx = _has(m, "pledge", "encumbr", "lien", "non-disposal", "ndu") or (" 31" in (" " + reg))
    if pledge_ctx:
        # both stems: "revoc" = revocation (correct); "revok" = revoke / NSE's misspelling "Revokation"
        if _has(m, "release", "revoc", "revok", "satisf", "closure", "removal", "return"):
            return PLEDGE_RELEASE
        if _has(m, "invoc", "invoke"):
            return PLEDGE_INVOKE
        return PLEDGE_CREATE

    # --- named plumbing modes ---
    if _has(m, "inter-se", "inter se", "interse"):
        return INTER_SE
    if _has(m, "esop", "esos", "employee stock", "exercise of option", "stock option", "sweat"):
        return ESOP
    if _has(m, "gift", "donat"):
        return GIFT
    if _has(m, "inherit", "transmission", "succession", "will", "demise", "deceased", "bequest"):
        return INHERITANCE
    if _has(m, "prefer", "allotment", "rights issue", "right", "bonus", "qip", "public issue", "ipo"):
        return ALLOTMENT
    if _has(m, "convers", "warrant", "ccd", "fcd", "debenture", "esops conversion"):
        return CONVERSION
    if _has(m, "amalgamat", "merger", "demerger", "arrangement", "scheme"):
        return SCHEME

    # --- market vs off-market ---
    is_off = _has(m, "off market", "off-market", "offmarket") or ("off" in m and "market" in m)
    # block deals are negotiated ON-exchange trades (PIT-gg vocabulary, 2026-07) —
    # market conviction/caution semantics apply, direction from acq/disp below
    is_market = ("market" in m and not is_off) or _has(m, "on market", "on-market", "open market",
                                                       "block deal", "bulk deal")
    if is_market:
        # Direction from the MODE first (authoritative); acq/disp only when the mode is ambiguous.
        # (A "Market Sale" whose tdpTransactionType says "Buy" must not deadlock to UNKNOWN.)
        m_buy, m_sell = _has(m, "purchase", "buy"), _has(m, "sale", "sell")
        if m_buy and not m_sell:
            return OPEN_MARKET_BUY
        if m_sell and not m_buy:
            return OPEN_MARKET_SELL
        a_buy = _has(ad, "acqui", "purchase", "buy")
        a_sell = _has(ad, "dispos", "sale", "sell")
        if a_buy and not a_sell:
            return OPEN_MARKET_BUY
        if a_sell and not a_buy:
            return OPEN_MARKET_SELL
    if is_off:
        return OFF_MARKET
    # mode blank / "Others" / "-" and nothing matched → NOT conviction
    return UNKNOWN


def is_principal(category: Optional[str]) -> bool:
    """True for promoter / promoter-group / director / KMP — the informed control persons.

    Designated persons / employees / connected persons are NOT principals (lower/plumbing weight).
    """
    return _has((category or "").lower(), *_PRINCIPAL_KEYS)


def signal_class(txn_class: str, category: Optional[str]) -> str:
    """Per-event signal label: conviction / caution / pledge_risk / pledge_relief / plumbing / ignore."""
    principal = is_principal(category)
    if txn_class in _PLEDGE_ADVERSE:
        return "pledge_risk"
    if txn_class == PLEDGE_RELEASE:
        return "pledge_relief"          # NOT auto-bullish — needs context
    if txn_class == OPEN_MARKET_BUY:
        return "conviction" if principal else "buy_other"
    if txn_class == OPEN_MARKET_SELL:
        return "caution" if principal else "sell_other"
    if txn_class in _PLUMBING:
        return "plumbing"
    return "ignore"


# --- raw-row normalisation (the fetcher emits raw dicts; this canonicalises) -

def _phash(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:16]


def _num(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("₹", "").replace("%", "").strip()
    if s in ("", "-", "NA", "N/A", "nil", "Nil"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize_row(raw: dict) -> dict:
    """Map a raw exchange disclosure dict (varied keys) to a canonical insider_event dict.

    Accepts flexible key names. Missing keys degrade to None. Computes txn_class + signal.
    """
    def g(*keys):
        for k in keys:
            if k in raw and raw[k] not in (None, ""):
                return raw[k]
        return None

    mode = g("mode", "mode_of_acquisition", "transaction_type", "typeOfSecurity_mode")
    acq_disp = g("acq_disp", "acquisition_disposal", "buy_sell", "acquisitionOrDisposal")
    regulation = g("regulation", "reg")
    category = g("category", "category_of_person", "personCategory")
    disclosure_dt = g("disclosure_dt", "date_of_intimation", "intimation_date",
                      "broadcast_dt", "receipt_date", "dt_of_receipt")
    transaction_dt = g("transaction_dt", "date_of_transaction", "acquisition_date", "txn_date")
    txn_class = classify_txn(mode, acq_disp, regulation)
    ev = {
        "symbol": (g("symbol", "nse_symbol", "scrip") or "").upper().strip(),
        "exchange": g("exchange") or "NSE",
        "disclosure_dt": str(disclosure_dt)[:10] if disclosure_dt else None,
        "transaction_dt": str(transaction_dt)[:10] if transaction_dt else None,
        "regulation": regulation,
        "person_name_hash": _phash(g("person_name", "name_of_person", "acquirer_name")),
        "category": category,
        "promoter_group_flag": 1 if _has((category or "").lower(), "promoter") else 0,
        "txn_type_raw": mode,
        "txn_class": txn_class,
        "shares": _num(g("shares", "no_of_securities", "securities", "quantity")),
        "value_rs": _num(g("value_rs", "value", "transaction_value")),
        "pct_equity": _num(g("pct_equity", "pct", "percentage", "post_pct_change")),
        "post_shares": _num(g("post_shares", "post_holding_shares")),
        "post_pct": _num(g("post_pct", "post_holding_pct", "holding_post_pct")),
        "mode": mode,
        "source_url": g("source_url", "url"),
        "attachment_url": g("attachment_url", "attachment"),
        "amendment_flag": 1 if _has((g("remarks", "note") or "").lower(), "amend", "revis", "correct") else 0,
    }
    ev["did"] = g("did", "nse_did", "disclosure_id")  # exchange-native id → best dedup key
    ev["signal_class"] = signal_class(txn_class, category)
    return ev


# --- PIT aggregation (disclosure-date clock) -------------------------------

def _d(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _supersede(events: list) -> list:
    """AUD-08: a Revised filing (amendment_flag=1) mints a NEW row with corrected shares/value
    (the _uid hashes value), so without this the original + revision BOTH count — double-counting
    promoter cashflow, cluster-buy and pledge tallies. Collapse each natural-key group that
    contains an amendment down to its latest amendment (by parsed_at). Groups with no amendment
    are left intact — genuinely distinct same-day trades by the same person must NOT be merged.
    Per-symbol input, so the natural key is (person, txn_date, txn_type)."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for e in events:
        nk = (e.get("person_name_hash"), e.get("transaction_dt"), e.get("txn_type_raw"))
        groups[nk].append(e)
    out: list = []
    for grp in groups.values():
        amends = [e for e in grp if e.get("amendment_flag")]
        if amends:
            amends.sort(key=lambda e: e.get("parsed_at") or "")
            out.append(amends[-1])       # the latest amendment supersedes the whole group
        else:
            out.extend(grp)
    return out


def aggregate(events: list, as_of: str, *, mcap_cr: Optional[float] = None) -> dict:
    """Point-in-time roll-up for one symbol. Only events with disclosure_dt <= as_of count.

    Windows measured in calendar days back from as_of. Conviction/caution use the SIGN of net
    promoter open-market cashflow (relative), not a rupee threshold (Ramana's principle).
    """
    ao = _d(as_of)
    known = [e for e in events if (_d(e.get("disclosure_dt")) and _d(e["disclosure_dt"]) <= ao)]
    known = _supersede(known)  # AUD-08: collapse revised filings so flow isn't double-counted

    def in_window(e, days):
        dd = _d(e.get("disclosure_dt"))
        return dd is not None and (ao - dd).days <= days

    def sum_val(cls, days, principal_only=True):
        tot = 0.0
        for e in known:
            if e.get("txn_class") != cls:
                continue
            if principal_only and not is_principal(e.get("category")):
                continue
            if in_window(e, days):
                tot += (e.get("value_rs") or 0.0)
        return tot

    buy_30 = sum_val(OPEN_MARKET_BUY, 30)
    buy_90 = sum_val(OPEN_MARKET_BUY, 90)
    sell_90 = sum_val(OPEN_MARKET_SELL, 90)
    net_90 = buy_90 - sell_90

    def pledge_pct(days, classes):
        tot = 0.0
        for e in known:
            if e.get("txn_class") in classes and in_window(e, days):
                tot += (e.get("pct_equity") or 0.0)
        return tot

    pledge_adverse_pct_90 = pledge_pct(90, _PLEDGE_ADVERSE)
    pledge_release_pct_90 = pledge_pct(90, {PLEDGE_RELEASE})
    # Count, not just %, because NSE pledge rows often carry a 0% holding-change (a pledge doesn't
    # transfer ownership) — the distress signal is the EVENT existing, not a holding delta.
    pledge_adverse_ct_90 = sum(1 for e in known
                               if e.get("txn_class") in _PLEDGE_ADVERSE and in_window(e, 90))

    cluster_buyers_30 = len({e.get("person_name_hash") for e in known
                             if e.get("txn_class") == OPEN_MARKET_BUY
                             and is_principal(e.get("category")) and in_window(e, 30)
                             and e.get("person_name_hash")})

    # symbol-level verdict — pledge distress dominates; else net-flow sign
    if pledge_adverse_ct_90 > 0:
        verdict = "pledge_risk"
    elif net_90 > 0:
        verdict = "conviction"      # principals net-bought on the open market over 90d
    elif net_90 < 0:
        verdict = "caution"
    else:
        verdict = "neutral"
    # (buy_30 / promoter_cluster_buy_30d remain exposed as a FRESHNESS sub-signal on top.)

    out = {
        "as_of": as_of,
        "n_events_known": len(known),
        "open_market_buy_value_30d": round(buy_30, 2),
        "open_market_buy_value_90d": round(buy_90, 2),
        "open_market_sell_value_90d": round(sell_90, 2),
        "net_promoter_cashflow_90d": round(net_90, 2),
        "promoter_cluster_buy_30d": cluster_buyers_30,
        "pledge_adverse_events_90d": pledge_adverse_ct_90,
        "pledge_adverse_pct_90d": round(pledge_adverse_pct_90, 3),
        "pledge_release_pct_90d": round(pledge_release_pct_90, 3),
        "insider_signal_class": verdict,
    }
    if mcap_cr and mcap_cr > 0:
        out["buy_value_to_mcap_30d"] = round(100.0 * (buy_30 / 1e7) / mcap_cr, 4)  # value_rs → cr
        out["net_cashflow_to_mcap_90d"] = round(100.0 * (net_90 / 1e7) / mcap_cr, 4)
    return out


# --- DB layer (hermes.db) --------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS insider_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT UNIQUE,
    symbol          TEXT NOT NULL,
    exchange        TEXT,
    disclosure_dt   TEXT,
    transaction_dt  TEXT,
    regulation      TEXT,
    person_name_hash TEXT,
    category        TEXT,
    promoter_group_flag INTEGER,
    txn_type_raw    TEXT,
    txn_class       TEXT,
    signal_class    TEXT,
    shares          REAL,
    value_rs        REAL,
    pct_equity      REAL,
    post_shares     REAL,
    post_pct        REAL,
    mode            TEXT,
    source_url      TEXT,
    attachment_url  TEXT,
    amendment_flag  INTEGER,
    parsed_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_insider_symbol_disc ON insider_events(symbol, disclosure_dt);
CREATE INDEX IF NOT EXISTS idx_insider_class ON insider_events(txn_class, disclosure_dt);
CREATE TABLE IF NOT EXISTS insider_gg_seen (
    xml_url      TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def _uid(ev: dict) -> str:
    # Identity must be built from RAW fields only — txn_class is derived, and hashing it
    # meant every classifier improvement changed the uid and DUPLICATED old rows instead
    # of reclassifying them via the upsert (caught live on the 2026-07-02 gg re-ingest).
    key = "|".join(str(ev.get(k)) for k in
                   ("symbol", "transaction_dt", "person_name_hash", "txn_type_raw", "shares", "value_rs"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def save_events(conn: sqlite3.Connection, events: list) -> int:
    """Idempotent upsert of normalized events. Returns count written/updated."""
    n = 0
    for ev in events:
        if not ev.get("symbol"):
            continue
        uid = ("NSE:" + str(ev["did"])) if ev.get("did") else _uid(ev)
        conn.execute(
            """INSERT INTO insider_events
                 (uid, symbol, exchange, disclosure_dt, transaction_dt, regulation,
                  person_name_hash, category, promoter_group_flag, txn_type_raw, txn_class,
                  signal_class, shares, value_rs, pct_equity, post_shares, post_pct, mode,
                  source_url, attachment_url, amendment_flag)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET
                 disclosure_dt=excluded.disclosure_dt, txn_class=excluded.txn_class,
                 signal_class=excluded.signal_class, post_pct=excluded.post_pct,
                 amendment_flag=excluded.amendment_flag, parsed_at=datetime('now')""",
            (uid, ev["symbol"], ev.get("exchange"), ev.get("disclosure_dt"),
             ev.get("transaction_dt"), ev.get("regulation"), ev.get("person_name_hash"),
             ev.get("category"), ev.get("promoter_group_flag"), ev.get("txn_type_raw"),
             ev.get("txn_class"), ev.get("signal_class"), ev.get("shares"), ev.get("value_rs"),
             ev.get("pct_equity"), ev.get("post_shares"), ev.get("post_pct"), ev.get("mode"),
             ev.get("source_url"), ev.get("attachment_url"), ev.get("amendment_flag")),
        )
        n += 1
    return n


import time  # noqa: E402

_NSE_HOME = "https://www.nseindia.com"
_NSE_PIT_REF = "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"
_NSE_PIT_API = "https://www.nseindia.com/api/corporates-pit"
_NSE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/122 Safari/537.36")
_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _nse_date(s) -> Optional[str]:
    """'18-Feb-2026 19:06' or '16-Feb-2026' -> '2026-02-18' (ISO). None on failure."""
    if not s:
        return None
    part = str(s).strip().split(" ")[0]
    bits = part.split("-")
    if len(bits) != 3:
        return None
    dd, mon, yyyy = bits
    mi = _MON.get(mon[:3].title())
    if not mi:
        return None
    try:
        return "%04d-%02d-%02d" % (int(yyyy), mi, int(dd))
    except ValueError:
        return None


def _nse_to_raw(r: dict) -> dict:
    """Map one NSE corporates-pit row → the raw dict normalize_row understands."""
    bef = _num(r.get("befAcqSharesPer"))
    aft = _num(r.get("afterAcqSharesPer"))
    pct = (aft - bef) if (bef is not None and aft is not None) else None
    return {
        "symbol": r.get("symbol"), "exchange": "NSE",
        "mode": r.get("acqMode"), "acquisition_disposal": r.get("tdpTransactionType"),
        "regulation": r.get("anex"), "category": r.get("personCategory"),
        "person_name": r.get("acqName"),
        # PIT clock = exchange broadcast datetime ('date'); fall back to intimation date
        "date_of_intimation": _nse_date(r.get("date")) or _nse_date(r.get("intimDt")),
        "date_of_transaction": _nse_date(r.get("acqtoDt")) or _nse_date(r.get("acqfromDt")),
        "shares": r.get("secAcq"), "value": r.get("secVal"),
        "pct_equity": pct, "post_shares": r.get("afterAcqSharesNo"),
        "post_pct": r.get("afterAcqSharesPer"),
        "source_url": r.get("xbrl"), "attachment_url": r.get("xbrl"),
        "remarks": r.get("remarks"), "did": r.get("did"),
    }


def _nse_session():
    import requests
    s = requests.Session()
    h = {"User-Agent": _NSE_UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _NSE_PIT_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)          # prime anti-bot cookies
    s.get(_NSE_PIT_REF, headers=h, timeout=20)
    return s, h


def fetch_disclosures(from_date: str, to_date: str, *, session=None,
                      headers=None) -> list:
    """Fetch NSE PIT (insider/promoter/pledge) disclosures for a date range.

    Dates are ISO (YYYY-MM-DD); the NSE API wants DD-MM-YYYY. Returns raw NSE rows.
    The bulk date-range form is one call per range (no per-symbol fan-out).
    """
    if session is None:
        session, headers = _nse_session()

    def ddmmyyyy(iso):
        y, m, d = str(iso)[:10].split("-")
        return "%s-%s-%s" % (d, m, y)

    url = "%s?from_date=%s&to_date=%s" % (_NSE_PIT_API, ddmmyyyy(from_date), ddmmyyyy(to_date))
    r = session.get(url, headers=headers, timeout=45)
    r.raise_for_status()
    data = r.json()
    rows = data.get("data") if isinstance(data, dict) else data
    return rows or []


def ingest_range(from_date: str, to_date: str, *, chunk_days: int = 30,
                 pause: float = 1.2) -> dict:
    """Fetch → normalize → save NSE PIT disclosures across a date range, chunked.

    Since ~Mar-2026 this is the ``corporates-pit-gg`` XBRL-per-disclosure feed — NSE
    retired the legacy ``corporates-pit`` JSON API (it returns empty-200s; verified
    2026-07-02). The legacy fetcher below is kept for the record only.
    """
    return ingest_range_gg(from_date, to_date, chunk_days=min(chunk_days, 7), pause=pause)


def _legacy_ingest_range(from_date: str, to_date: str, *, chunk_days: int = 30,
                         pause: float = 1.2) -> dict:
    """The pre-Mar-2026 JSON-API path (DEAD upstream; kept for provenance/re-testing)."""
    start = _d(from_date)
    end = _d(to_date)
    if not start or not end:
        raise ValueError("from_date/to_date must be ISO YYYY-MM-DD")
    session, headers = _nse_session()
    fetched = saved = 0
    with get_conn() as conn:
        ensure_schema(conn)
        cur = start
        while cur <= end:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
            try:
                raw = fetch_disclosures(cur.isoformat(), chunk_end.isoformat(),
                                        session=session, headers=headers)
            except Exception as e:  # noqa: BLE001 — one bad chunk shouldn't kill the backfill
                log.warning("PIT fetch failed %s..%s: %s", cur, chunk_end, e)
                cur = chunk_end + timedelta(days=1)
                time.sleep(pause)
                continue
            events = [normalize_row(_nse_to_raw(x)) for x in raw]
            saved += save_events(conn, events)
            conn.commit()          # bounded transactions (see ingest_range_gg note)
            fetched += len(raw)
            log.info("PIT %s..%s: %d rows", cur, chunk_end, len(raw))
            cur = chunk_end + timedelta(days=1)
            time.sleep(pause)
    return {"from": from_date, "to": to_date, "fetched": fetched, "saved": saved}


# --- corporates-pit-gg: the post-Mar-2026 XBRL-per-disclosure feed ----------
# Listing rows are filing-level (appId = BATCH id, never a dedup key) and point at a
# per-disclosure XBRL instance (flat `in-bse-co` taxonomy). One instance can carry
# multiple transactions (one per XBRL context), so the mapper emits one raw dict per
# transaction context and save_events dedups on the content-hash uid (no `did` here).
_NSE_PIT_GG_API = "https://www.nseindia.com/api/corporates-pit-gg"

_GG_DOC_TAGS = ("Symbol", "DisclosureUnderRegulation", "DateOfIntimationToCompany",
                "NameOfTheCompany", "RevisedFilling", "TypeOfInstrument")
_GG_TXN_TAGS = ("NameOfThePerson", "CategoryOfPerson", "ModeOfAcquisitionOrDisposal",
                "SecuritiesAcquiredOrDisposedNumberOfSecurity",
                "SecuritiesAcquiredOrDisposedTransactionType",
                "SecuritiesAcquiredOrDisposedValueOfSecurity",
                "SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity",
                "SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding",
                "SecuritiesHeldPriorToAcquisitionOrDisposalNumberOfSecurity",
                "SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding",
                "DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate",
                "DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyToDate")


def fetch_filings_gg(from_date: str, to_date: str, *, session=None, headers=None) -> list:
    """Listing rows (appId, symbol, regulation, broadcastDateTime, xmlFileName, …)."""
    if session is None:
        session, headers = _nse_session()

    def ddmmyyyy(iso):
        y, m, d = str(iso)[:10].split("-")
        return "%s-%s-%s" % (d, m, y)

    url = "%s?index=equities&from_date=%s&to_date=%s" % (
        _NSE_PIT_GG_API, ddmmyyyy(from_date), ddmmyyyy(to_date))
    r = session.get(url, headers=headers, timeout=45)
    r.raise_for_status()
    data = r.json()
    rows = data.get("data") if isinstance(data, dict) else data
    return rows or []


def _gg_xml_to_raws(xml_text: str, listing: dict) -> list:
    """One PIT XBRL instance -> raw dicts normalize_row understands (one per txn context)."""
    from src.automation.fundamentals_xbrl import parse_instance  # generic XBRL parse
    parsed = parse_instance(xml_text)
    doc: dict = {}
    ctx_facts: dict = {}
    for name, ctx, val in parsed["facts"]:
        if name in _GG_DOC_TAGS and val not in (None, ""):
            doc.setdefault(name, val)
        if name in _GG_TXN_TAGS:
            ctx_facts.setdefault(ctx, {})[name] = val
    # transaction contexts = those actually naming a person or a security movement
    txn_ctxs = [c for c, f in ctx_facts.items()
                if f.get("NameOfThePerson") or
                f.get("SecuritiesAcquiredOrDisposedNumberOfSecurity") is not None]
    broadcast = _nse_date(listing.get("broadcastDateTime"))
    regulation = (doc.get("DisclosureUnderRegulation")
                  or str(listing.get("regulation") or "").replace("Regulation", "").strip())
    revised = (str(doc.get("RevisedFilling") or "").strip().lower() == "yes"
               or (listing.get("typeOfSubmission") or "") not in ("", "Original"))
    raws = []
    for ctx in txn_ctxs:
        f = ctx_facts[ctx]
        prior_pct = _num(f.get("SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding"))
        post_pct = _num(f.get("SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding"))
        pct = (post_pct - prior_pct) if (prior_pct is not None and post_pct is not None) else None
        raws.append({
            "symbol": doc.get("Symbol") or listing.get("symbol"), "exchange": "NSE",
            "mode": f.get("ModeOfAcquisitionOrDisposal"),
            "acquisition_disposal": f.get("SecuritiesAcquiredOrDisposedTransactionType"),
            "regulation": regulation, "category": f.get("CategoryOfPerson"),
            "person_name": f.get("NameOfThePerson"),
            # PIT clock = the exchange broadcast; intimation date is the fallback
            "date_of_intimation": broadcast or _nse_date(doc.get("DateOfIntimationToCompany")),
            "date_of_transaction":
                _nse_date(f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyToDate"))
                or f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyToDate")
                or _nse_date(f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate"))
                or f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate"),
            "shares": f.get("SecuritiesAcquiredOrDisposedNumberOfSecurity"),
            "value": f.get("SecuritiesAcquiredOrDisposedValueOfSecurity"),
            "pct_equity": pct,
            "post_shares": f.get("SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity"),
            "post_pct": post_pct,
            "source_url": listing.get("xmlFileName"),
            "attachment_url": listing.get("ixbrl"),
            "remarks": "Revised filing" if revised else None,
            "did": None,     # no exchange-native id in this feed -> content-hash uid
        })
    return raws


def ingest_range_gg(from_date: str, to_date: str, *, chunk_days: int = 7,
                    pause: float = 1.2) -> dict:
    """Fetch corporates-pit-gg filings + their XBRL instances → normalize → save.

    Each filing costs one XML fetch (paced), so backfills are slow-but-bounded;
    idempotent via the content-hash uid (re-runs update, never duplicate).
    """
    start = _d(from_date)
    end = _d(to_date)
    if not start or not end:
        raise ValueError("from_date/to_date must be ISO YYYY-MM-DD")
    session, headers = _nse_session()
    filings = xml_fail = fetched = saved = skipped = 0
    consec_fail = 0
    aborted = False
    with get_conn() as conn:
        ensure_schema(conn)
        conn.commit()
        cur = start
        while cur <= end and not aborted:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
            try:
                rows = fetch_filings_gg(cur.isoformat(), chunk_end.isoformat(),
                                        session=session, headers=headers)
            except Exception as e:  # noqa: BLE001
                log.warning("PIT-gg listing failed %s..%s: %s", cur, chunk_end, e)
                cur = chunk_end + timedelta(days=1)
                time.sleep(pause)
                continue
            filings += len(rows)
            for row in rows:
                url = (row.get("xmlFileName") or "").strip()
                if not url.lower().endswith(".xml"):
                    xml_fail += 1
                    continue
                # cheap resume: instances already parsed in a previous (partial) run are
                # skipped WITHOUT a re-fetch — the fetch is the expensive/throttled part
                if conn.execute("SELECT 1 FROM insider_gg_seen WHERE xml_url=?", (url,)).fetchone():
                    skipped += 1
                    continue
                try:
                    xr = session.get(url, headers=headers, timeout=45)
                    if xr.status_code != 200:
                        raise RuntimeError("HTTP %s" % xr.status_code)
                    raws = _gg_xml_to_raws(xr.text, row)
                except Exception as e:  # noqa: BLE001 — one bad instance shouldn't kill the run
                    xml_fail += 1
                    consec_fail += 1
                    log.warning("PIT-gg xml failed %s (%s): %s", row.get("symbol"), url[-40:], e)
                    if consec_fail >= 6:
                        # nsearchives throttling detected (observed 2026-07-02: every fetch
                        # timing out after ~1.5k downloads) — stop burning 45s per miss;
                        # the run is idempotent + seen-table-resumable, so exit CLEANLY.
                        log.warning("PIT-gg: %d consecutive fetch failures — throttled; "
                                    "aborting cleanly (resume by re-running the same window)",
                                    consec_fail)
                        aborted = True
                        break
                    time.sleep(pause + 5 * consec_fail)   # gentle backoff
                    continue
                consec_fail = 0
                events = [normalize_row(r) for r in raws]
                saved += save_events(conn, events)
                conn.execute("INSERT OR IGNORE INTO insider_gg_seen (xml_url) VALUES (?)", (url,))
                # COMMIT PER FILING — the write lock must NEVER span a network fetch.
                # The 2026-07-02 backfill held one giant txn across paced fetches, starved
                # hermes-api's startup schema-init (db._init), crash-looped prod to 000,
                # got pkill'ed, and rolled back everything. WAL commits are cheap; the
                # lock window is now microseconds per filing.
                conn.commit()
                fetched += len(raws)
                time.sleep(pause)
            log.info("PIT-gg %s..%s: %d filings -> %d txns (saved=%d, skipped=%d)",
                     cur, chunk_end, len(rows), fetched, saved, skipped)
            cur = chunk_end + timedelta(days=1)
    return {"from": from_date, "to": to_date, "filings": filings, "fetched": fetched,
            "saved": saved, "skipped_seen": skipped, "xml_failed": xml_fail,
            "aborted_throttled": aborted}


# --- selftest (synthetic, no DB, no network) -------------------------------

def _selftest() -> int:
    # 1) taxonomy: (mode, acq/disp, reg) -> class
    cases = [
        (("Market Purchase", "Acquisition", "7(2)"), OPEN_MARKET_BUY),
        (("Market Sale", "Disposal", "7(2)"), OPEN_MARKET_SELL),
        # PIT-gg (post-Mar-2026 XBRL feed) vocabulary
        (("Block Deal", "Acquisition", "7(2)"), OPEN_MARKET_BUY),
        (("Block Deal", "Disposal", "7(2)"), OPEN_MARKET_SELL),
        (("ESOS", None, None), ESOP),
        (("Off Market Sale", "Disposal", None), OFF_MARKET),
        (("Inter-se Transfer", "Acquisition", None), INTER_SE),
        (("Creation of Pledge", None, "31"), PLEDGE_CREATE),
        (("Revocation of Pledge", None, "31"), PLEDGE_RELEASE),
        (("Invocation of Pledge", None, "31"), PLEDGE_INVOKE),
        (("Allotment under ESOP", "Acquisition", None), ESOP),
        (("Preferential Allotment", "Acquisition", None), ALLOTMENT),
        (("Gift", "Disposal", None), GIFT),
        (("Conversion of Warrants", "Acquisition", None), CONVERSION),
        ((None, None, "31"), PLEDGE_CREATE),          # reg-31 with blank mode → encumbrance
        (("", "Acquisition", "7(2)"), UNKNOWN),        # blank mode, no market word → NOT conviction
        # real NSE strings observed in the live feed:
        (("Pledge Creation", None, None), PLEDGE_CREATE),
        (("Revokation of Pledge", None, None), PLEDGE_RELEASE),   # NSE's actual misspelling
        (("Conversion of security", "Acquisition", None), CONVERSION),
        (("Preferential Offer", "Acquisition", None), ALLOTMENT),
        (("Scheme of Amalgamation/Merger/Demerger/Arrangement", "Acquisition", None), SCHEME),
        (("Market Sale", "Buy", None), OPEN_MARKET_SELL),  # mode wins over contradictory acq/disp
        (("Public Right", "Acquisition", None), ALLOTMENT),
    ]
    for (mode, ad, reg), want in cases:
        got = classify_txn(mode, ad, reg)
        assert got == want, "classify(%r,%r,%r)=%s want %s" % (mode, ad, reg, got, want)

    # 2) signal_class gates on principal category
    assert signal_class(OPEN_MARKET_BUY, "Promoter") == "conviction"
    assert signal_class(OPEN_MARKET_BUY, "Designated Person") == "buy_other"
    assert signal_class(OPEN_MARKET_SELL, "Promoter Group") == "caution"
    assert signal_class(PLEDGE_INVOKE, "Promoter") == "pledge_risk"
    assert signal_class(PLEDGE_RELEASE, "Promoter") == "pledge_relief"
    assert signal_class(ESOP, "Director") == "plumbing"

    # 3) normalize_row end-to-end
    ev = normalize_row({"symbol": "acme", "mode": "Market Purchase",
                        "acquisition_disposal": "Acquisition", "category": "Promoter",
                        "value": "1,50,00,000", "date_of_intimation": "2026-05-10",
                        "date_of_transaction": "2026-05-08", "person_name": "A B Patel"})
    assert ev["symbol"] == "ACME" and ev["txn_class"] == OPEN_MARKET_BUY
    assert ev["signal_class"] == "conviction" and ev["value_rs"] == 15000000.0
    assert ev["promoter_group_flag"] == 1 and ev["person_name_hash"]

    # 4) PIT aggregation: disclosure-date clock + verdict logic
    def mk(cls_mode, cat, val, disc, pct=None):
        return normalize_row({"symbol": "ACME", "mode": cls_mode, "category": cat,
                              "value": val, "pct_equity": pct,
                              "date_of_intimation": disc, "person_name": cat + val})
    conv = [
        mk("Market Purchase", "Promoter", "20000000", "2026-05-01"),
        mk("Market Purchase", "Promoter Group", "10000000", "2026-05-20"),  # 2nd buyer → cluster
        mk("Market Sale", "Promoter", "5000000", "2026-04-15"),
        mk("Market Purchase", "Promoter", "9999999", "2026-07-01"),  # AFTER as_of → excluded
    ]
    agg = aggregate(conv, "2026-06-01", mcap_cr=1000.0)
    assert agg["n_events_known"] == 3, agg
    assert agg["net_promoter_cashflow_90d"] == 25000000.0, agg  # 30M buy - 5M sell
    assert agg["promoter_cluster_buy_30d"] == 1, agg            # only the 05-20 buy within 30d of 06-01
    assert agg["insider_signal_class"] == "conviction", agg
    assert agg["buy_value_to_mcap_30d"] is not None

    pledged = [mk("Creation of Pledge", "Promoter", "0", "2026-05-25", pct=8.5),
               mk("Market Purchase", "Promoter", "30000000", "2026-05-26")]
    aggp = aggregate(pledged, "2026-06-01")
    assert aggp["insider_signal_class"] == "pledge_risk", aggp  # pledge dominates even with a buy
    assert aggp["pledge_adverse_pct_90d"] == 8.5, aggp
    # NSE reality: a pledge row often has 0% holding-change → verdict must fire on COUNT, not %
    zero_pct = [mk("Pledge Creation", "Promoter", "1000000", "2026-05-25")]
    azp = aggregate(zero_pct, "2026-06-01")
    assert azp["insider_signal_class"] == "pledge_risk" and azp["pledge_adverse_events_90d"] == 1, azp

    selling = [mk("Market Sale", "Promoter", "40000000", "2026-05-10")]
    assert aggregate(selling, "2026-06-01")["insider_signal_class"] == "caution"

    print("selftest OK  taxonomy(%d cases) + signal-gating + normalize + PIT-aggregation" % len(cases))
    print("  conviction agg:", {k: agg[k] for k in
          ("net_promoter_cashflow_90d", "promoter_cluster_buy_30d", "insider_signal_class")})
    print("  pledge agg    :", {k: aggp[k] for k in ("pledge_adverse_pct_90d", "insider_signal_class")})
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true", help="taxonomy + aggregation checks (no DB)")
    p.add_argument("--classify", metavar="MODE", help="classify a single raw mode string")
    p.add_argument("--disp", default=None, help="acquisition/disposal (with --classify)")
    p.add_argument("--reg", default=None, help="regulation (with --classify)")
    p.add_argument("--cat", default=None, help="category of person (with --classify)")
    p.add_argument("--init-schema", action="store_true", help="create the insider_events table")
    p.add_argument("--ingest", nargs=2, metavar=("FROM", "TO"),
                   help="fetch+save NSE PIT disclosures for an ISO date range")
    p.add_argument("--legacy", action="store_true",
                   help="use the pre-Mar-2026 corporates-pit JSON API (only for the "
                        "pre-cutover archive — it still serves 2026-03/04; empty after)")
    p.add_argument("--chunk-days", type=int, default=30, help="ingest chunk size (days)")
    p.add_argument("--agg", metavar="SYMBOL", help="aggregate stored events for a symbol")
    p.add_argument("--as-of", default=None, help="ISO date for --agg (default today)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    if args.classify:
        cls = classify_txn(args.classify, args.disp, args.reg)
        print(json.dumps({"mode": args.classify, "txn_class": cls,
                          "signal_class": signal_class(cls, args.cat)}, indent=2))
        return
    if args.init_schema:
        with get_conn() as conn:
            ensure_schema(conn)
        log.info("insider_events schema ensured")
        return
    if args.ingest:
        fn = _legacy_ingest_range if args.legacy else ingest_range
        res = fn(args.ingest[0], args.ingest[1], chunk_days=args.chunk_days)
        log.info("insider ingest: %s", res)
        return
    if args.agg:
        as_of = args.as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM insider_events WHERE symbol=? ORDER BY disclosure_dt", (args.agg.upper(),))]
        print(json.dumps(aggregate(rows, as_of), indent=2, default=str))
        return
    p.print_help()


if __name__ == "__main__":
    main()
