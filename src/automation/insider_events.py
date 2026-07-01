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
OFF_MARKET = "OFF_MARKET"           # off-market, otherwise unclassified
OPEN_MARKET_BUY = "OPEN_MARKET_BUY"
OPEN_MARKET_SELL = "OPEN_MARKET_SELL"
UNKNOWN = "UNKNOWN"

_PLUMBING = {INTER_SE, ESOP, GIFT, INHERITANCE, ALLOTMENT, CONVERSION, OFF_MARKET}
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
        if _has(m, "release", "revoke", "revocation", "satisf", "closure", "removal", "return"):
            return PLEDGE_RELEASE
        if _has(m, "invoc", "invoke"):
            return PLEDGE_INVOKE
        return PLEDGE_CREATE

    # --- named plumbing modes ---
    if _has(m, "inter-se", "inter se", "interse"):
        return INTER_SE
    if _has(m, "esop", "employee stock", "exercise of option", "stock option", "sweat"):
        return ESOP
    if _has(m, "gift", "donat"):
        return GIFT
    if _has(m, "inherit", "transmission", "succession", "will", "demise", "deceased", "bequest"):
        return INHERITANCE
    if _has(m, "prefer", "allotment", "rights issue", "bonus", "qip", "public issue", "ipo"):
        return ALLOTMENT
    if _has(m, "convers", "warrant", "ccd", "fcd", "debenture", "esops conversion"):
        return CONVERSION

    # --- market vs off-market ---
    is_off = _has(m, "off market", "off-market", "offmarket") or ("off" in m and "market" in m)
    is_market = ("market" in m and not is_off) or _has(m, "on market", "on-market", "open market")
    buy_words = _has(m, "purchase", "buy", "acqui") or _has(ad, "acqui", "purchase", "buy")
    sell_words = _has(m, "sale", "sell", "dispos") or _has(ad, "dispos", "sale", "sell")

    if is_market:
        if buy_words and not sell_words:
            return OPEN_MARKET_BUY
        if sell_words and not buy_words:
            return OPEN_MARKET_SELL
    if is_off:
        return OFF_MARKET
    # mode blank but direction known and nothing else matched → still off/unknown, NOT conviction
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


def aggregate(events: list, as_of: str, *, mcap_cr: Optional[float] = None) -> dict:
    """Point-in-time roll-up for one symbol. Only events with disclosure_dt <= as_of count.

    Windows measured in calendar days back from as_of. Conviction/caution use the SIGN of net
    promoter open-market cashflow (relative), not a rupee threshold (Ramana's principle).
    """
    ao = _d(as_of)
    known = [e for e in events if (_d(e.get("disclosure_dt")) and _d(e["disclosure_dt"]) <= ao)]

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

    cluster_buyers_30 = len({e.get("person_name_hash") for e in known
                             if e.get("txn_class") == OPEN_MARKET_BUY
                             and is_principal(e.get("category")) and in_window(e, 30)
                             and e.get("person_name_hash")})

    # symbol-level verdict — pledge distress dominates; else net-flow sign
    if pledge_adverse_pct_90 > 0 or any(
            e.get("txn_class") == PLEDGE_INVOKE and in_window(e, 90) for e in known):
        verdict = "pledge_risk"
    elif net_90 > 0 and buy_30 > 0:
        verdict = "conviction"
    elif net_90 < 0:
        verdict = "caution"
    else:
        verdict = "neutral"

    out = {
        "as_of": as_of,
        "n_events_known": len(known),
        "open_market_buy_value_30d": round(buy_30, 2),
        "open_market_buy_value_90d": round(buy_90, 2),
        "open_market_sell_value_90d": round(sell_90, 2),
        "net_promoter_cashflow_90d": round(net_90, 2),
        "promoter_cluster_buy_30d": cluster_buyers_30,
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
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def _uid(ev: dict) -> str:
    key = "|".join(str(ev.get(k)) for k in
                   ("symbol", "transaction_dt", "person_name_hash", "txn_class", "shares", "value_rs"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def save_events(conn: sqlite3.Connection, events: list) -> int:
    """Idempotent upsert of normalized events. Returns count written/updated."""
    n = 0
    for ev in events:
        if not ev.get("symbol"):
            continue
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
            (_uid(ev), ev["symbol"], ev.get("exchange"), ev.get("disclosure_dt"),
             ev.get("transaction_dt"), ev.get("regulation"), ev.get("person_name_hash"),
             ev.get("category"), ev.get("promoter_group_flag"), ev.get("txn_type_raw"),
             ev.get("txn_class"), ev.get("signal_class"), ev.get("shares"), ev.get("value_rs"),
             ev.get("pct_equity"), ev.get("post_shares"), ev.get("post_pct"), ev.get("mode"),
             ev.get("source_url"), ev.get("attachment_url"), ev.get("amendment_flag")),
        )
        n += 1
    return n


def fetch_disclosures(*args, **kwargs):  # pragma: no cover — VPS wiring step
    """STUB — the exchange fetcher lands in the VPS wiring step, against live formats.

    Confirm the real NSE PIT (Reg 7(2)) CSV/XBRL column names and BSE fallback shape on the
    VPS, emit raw dicts, then pipe through normalize_row → save_events. Deliberately not
    implemented locally: the disclosure formats must be validated against real data, and
    network fetching is an outward action. See module docstring for the source endpoints.
    """
    raise NotImplementedError("fetch_disclosures is a VPS-step stub; see module docstring")


# --- selftest (synthetic, no DB, no network) -------------------------------

def _selftest() -> int:
    # 1) taxonomy: (mode, acq/disp, reg) -> class
    cases = [
        (("Market Purchase", "Acquisition", "7(2)"), OPEN_MARKET_BUY),
        (("Market Sale", "Disposal", "7(2)"), OPEN_MARKET_SELL),
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
    p.print_help()


if __name__ == "__main__":
    main()
