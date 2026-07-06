"""Credit-rating events (Dataset "B" — the downside veto/hygiene layer).

D76 roadmap, P2. C (capital-allocation) and A (insider/promoter) are LIVE. B is the
third feed: rating actions as a DOWNSIDE VETO (downgrade / watch-negative / default →
haircut), upgrades weaker. Per the Claude⇄Codex debate B is hygiene-first, not timing-alpha,
and coverage is skewed to rated (larger/debt-heavy) names — so absence is NEUTRAL, never a
positive quality signal.

Source (live-verified on the VPS): NSE credit-rating bulk date-range JSON
  https://www.nseindia.com/api/corporate-credit-rating?index=&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY
Cookie-primed session (like insider_events / equity_list). Fields: CompanyName, Symbol, ISIN,
NameOfCRAgency, CreditRating ("CARE AAA/Stable"), CreditRatingEarlier, Outlook, RatingAction,
DateofCR, BroadcastDateTime (PIT clock), XbrlFileName, AppID (dedup key).

Two hard parts, handled here:
  1. Heterogeneous rating strings across agencies (CARE / [ICRA] / CRISIL / IND / …) with combined
     long-term ; outlook / short-term forms → `parse_rating` → an ORDINAL ladder → `notch_delta`.
  2. Equity linkage: `Symbol` is often "NOT LISTED"/"NOTLISTED"/"000000" (ratings are on DEBT
     instruments) → symbol-first, then a normalised CompanyName → nse_equity_list fallback.

CLI:
  python -m src.automation.credit_ratings --selftest
  python -m src.automation.credit_ratings --parse "CARE BBB-; Stable / CARE A3"
  python -m src.automation.credit_ratings --ingest 2025-11-01 2026-02-28
  python -m src.automation.credit_ratings --agg SUZLON
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.credit_ratings")

# --- ordinal ladders -------------------------------------------------------
# Long-term: AAA (best) → D (default). Investment grade floor = BBB-.
# (Ladder cross-checked with Codex resp-15 — includes C+/C-; contiguous so notch deltas are 1/grade.)
_LT = ["D", "C-", "C", "C+", "B-", "B", "B+", "BB-", "BB", "BB+", "BBB-", "BBB", "BBB+",
       "A-", "A", "A+", "AA-", "AA", "AA+", "AAA"]
_LT_ORD = {g: i + 1 for i, g in enumerate(_LT)}   # D=1 … AAA=20
_INVESTMENT_GRADE_FLOOR = _LT_ORD["BBB-"]         # 8
# Short-term: A1+ (best) → D.
_ST = ["D", "A4", "A4+", "A3", "A3+", "A2", "A2+", "A1", "A1+"]
_ST_ORD = {g: i + 1 for i, g in enumerate(_ST)}

_AGENCY_TOKENS = ["[ICRA]", "ICRA", "CRISIL", "CARE", "IND-RA", "IND RA", "IND",
                  "ACUITE", "ACUITÉ", "ACUITE'", "BWR", "BRICKWORK", "INFOMERICS", "SMERA"]
_OUTLOOKS = ("STABLE", "POSITIVE", "NEGATIVE", "DEVELOPING")


def parse_rating(s: Optional[str]) -> dict:
    """Parse a raw agency rating string → {lt, lt_ord, st, st_ord, outlook, watch}.

    Handles 'CARE AAA/Stable', '[ICRA]A(Negative)', 'CARE BBB-; Stable / CARE A3', etc.
    """
    out = {"lt": None, "lt_ord": None, "st": None, "st_ord": None, "outlook": None, "watch": False}
    if not s:
        return out
    t = " " + s.upper() + " "
    for a in _AGENCY_TOKENS:
        t = t.replace(a.upper(), " ")
    # structured-finance / provisional suffixes are not grade modifiers — strip so they don't
    # corrupt the LT scan (a future enhancement can surface them as flags; Codex resp-15).
    for suf in ("(CE)", "(SO)", "(CBO)", "PP-MLD", "PROVISIONAL", "PROV.", "PROV "):
        t = t.replace(suf, " ")
    if "WATCH" in t or "RWN" in t or "RWP" in t:
        out["watch"] = True
    for o in _OUTLOOKS:
        if o in t:
            out["outlook"] = o.title()
    t = t.replace(";", " ").replace("(", " ").replace(")", " ").replace(",", " ")
    for o in _OUTLOOKS:
        t = t.replace(o, " ")
    t = t.replace("WATCH", " ").replace("RWN", " ").replace("RWP", " ")
    # short-term first (A1..A4 [+]) so the letters don't confuse the LT scan
    mst = re.search(r"\bA\s?([1-4])\s?(\+?)", t)
    if mst:
        out["st"] = ("A" + mst.group(1) + mst.group(2)).strip()
        out["st_ord"] = _ST_ORD.get(out["st"])
    t = re.sub(r"\bA\s?[1-4]\s?\+?", " ", t)
    # long-term — grade must be a WHOLE token: leading \b + a negative lookahead so prose can't
    # yield spurious grades (e.g. "B" from "BANK", "C" from "Commercial", "D" from "Debentures" in
    # withdrawal notices). Suffix consumed before the lookahead so "BBB-" keeps its notch.
    mlt = re.search(r"\b(AAA|AA|BBB|BB|A|B|C|D)\s?([+-]?)(?![A-Za-z0-9])", t)
    if mlt:
        g = mlt.group(1) + mlt.group(2)
        out["lt"] = g
        out["lt_ord"] = _LT_ORD.get(g)
    return out


# --- action classification -------------------------------------------------
UPGRADE, DOWNGRADE, REAFFIRM, NEW, WITHDRAWN, WATCH, DEFAULT, OTHER = (
    "UPGRADE", "DOWNGRADE", "REAFFIRM", "NEW", "WITHDRAWN", "WATCH", "DEFAULT", "OTHER")


def classify_action(action: Optional[str], specify_other: Optional[str],
                    new_ord: Optional[int], old_ord: Optional[int], new_lt: Optional[str]) -> str:
    """Map RatingAction (+ SpecifyOthRatingActn + notch move + grade) to a normalised action."""
    a = ((action or "") + " " + (specify_other or "")).lower()
    if new_lt == "D":
        # a FRESH move into default is the event; reaffirming an already-D instrument is not
        # (else quarterly re-affirmations of distressed debt inflate the default count ~5x).
        if old_ord is None or old_ord > _LT_ORD["D"]:
            return DEFAULT
        return REAFFIRM
    if "withdraw" in a or "suspend" in a:
        return WITHDRAWN
    if "watch" in a:
        return WATCH
    if "downgrade" in a:
        return DOWNGRADE
    if "upgrade" in a:
        return UPGRADE
    if "reaffirm" in a or "reiterat" in a:
        return REAFFIRM
    if "assign" in a or a.strip() == "new":
        return NEW
    # fall back to the notch move when the action text is vague ("Other")
    if new_ord is not None and old_ord is not None:
        if new_ord < old_ord:
            return DOWNGRADE
        if new_ord > old_ord:
            return UPGRADE
        return REAFFIRM
    return OTHER


_BAD_SYMBOLS = {"NOT LISTED", "NOTLISTED", "-", "", "000000", "0", "NA", "N/A"}


def _valid_symbol(sym: Optional[str]) -> Optional[str]:
    s = (sym or "").upper().strip()
    return s if s and s not in _BAD_SYMBOLS else None


def _norm_name(name: Optional[str]) -> str:
    n = (name or "").upper()
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    for w in (" LIMITED", " LTD", " PRIVATE", " PVT", " CORPORATION", " CORP", " COMPANY", " CO",
              " INDIA", " AND ", " & "):
        n = n.replace(w, " ")
    return re.sub(r"\s+", " ", n).strip()


def _load_name_map(conn: sqlite3.Connection) -> dict:
    """Normalised company-name → NSE symbol, from nse_equity_list."""
    m = {}
    try:
        for r in conn.execute("SELECT symbol, company_name FROM nse_equity_list"):
            key = _norm_name(r[1])
            if key and key not in m:
                m[key] = r[0]
    except sqlite3.OperationalError:
        pass
    return m


# --- normalisation of one NSE credit-rating row ----------------------------

def _cr_date(s) -> Optional[str]:
    if not s:
        return None
    part = str(s).strip().split(" ")[0]
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(part, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _num(v):
    if v in (None, "", "-"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def normalize_cr(row: dict, name_map: Optional[dict] = None) -> dict:
    cur = parse_rating(row.get("CreditRating"))
    old = parse_rating(row.get("CreditRatingEarlier"))
    notch = (cur["lt_ord"] - old["lt_ord"]) if (cur["lt_ord"] and old["lt_ord"]) else None
    action = classify_action(row.get("RatingAction"), row.get("SpecifyOthRatingActn"),
                             cur["lt_ord"], old["lt_ord"], cur["lt"])
    sym = _valid_symbol(row.get("Symbol"))
    if not sym and name_map:
        sym = name_map.get(_norm_name(row.get("CompanyName")))
    return {
        "app_id": row.get("AppID"),
        "symbol": sym,
        "issuer_name": row.get("CompanyName"),
        "isin": row.get("ISIN"),
        "agency": row.get("NameOfCRAgency"),
        "rating_raw": row.get("CreditRating"),
        "rating_earlier_raw": row.get("CreditRatingEarlier"),
        "lt_grade": cur["lt"], "lt_ord": cur["lt_ord"], "lt_ord_earlier": old["lt_ord"],
        "st_grade": cur["st"], "outlook": cur["outlook"] or row.get("Outlook"),
        "notch_delta": notch,
        "action_raw": row.get("RatingAction"),
        "action_class": action,
        "watch_flag": 1 if cur["watch"] else 0,
        "below_investment_grade": 1 if (cur["lt_ord"] and cur["lt_ord"] < _INVESTMENT_GRADE_FLOOR) else 0,
        "rating_date": _cr_date(row.get("DateofCR")),
        "broadcast_dt": _cr_date(row.get("BroadcastDateTime")),   # PIT knowable_at
        "attachment_url": row.get("XbrlFileName"),
    }


# --- schema / persistence --------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS credit_rating_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    uid            TEXT UNIQUE,
    app_id         TEXT,
    symbol         TEXT,
    issuer_name    TEXT,
    isin           TEXT,
    agency         TEXT,
    rating_raw     TEXT,
    rating_earlier_raw TEXT,
    lt_grade       TEXT,
    lt_ord         INTEGER,
    lt_ord_earlier INTEGER,
    st_grade       TEXT,
    outlook        TEXT,
    notch_delta    INTEGER,
    action_raw     TEXT,
    action_class   TEXT,
    watch_flag     INTEGER,
    below_investment_grade INTEGER,
    rating_date    TEXT,
    broadcast_dt   TEXT,
    attachment_url TEXT,
    parsed_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cr_symbol_dt ON credit_rating_events(symbol, broadcast_dt);
CREATE INDEX IF NOT EXISTS idx_cr_action ON credit_rating_events(action_class, broadcast_dt);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def _cr_uid(e: dict) -> str:
    """Content hash of the fields that define a distinct rating ACTION (AppID is a batch id, not
    an event id — it repeats hundreds of times, so it cannot be the dedup key)."""
    key = "|".join(str(e.get(k)) for k in
                   ("isin", "agency", "rating_raw", "rating_earlier_raw", "rating_date", "action_raw"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


# Canonical agency names — filings carry typo/variant spellings of the same SEBI-registered
# CRA ("Acute Ratings & Research" is a filing typo of Acuité; there is no such registered
# agency). Normalise ONLY the stored column, NEVER the _cr_uid input: the uid hashes the RAW
# fields, so a re-served filing must keep producing the same uid — normalising before the
# hash would fork duplicates on re-ingest.
_AGENCY_CANON = {
    "acute ratings & research limited": "Acuite Ratings & Research Limited",
}


def _canon_agency(name):
    if not name:
        return name
    return _AGENCY_CANON.get(" ".join(str(name).split()).lower(), name)


def save_events(conn: sqlite3.Connection, events: list) -> int:
    n = 0
    for e in events:
        if not (e.get("isin") or e.get("issuer_name")):
            continue
        conn.execute(
            """INSERT INTO credit_rating_events
                 (uid, app_id, symbol, issuer_name, isin, agency, rating_raw, rating_earlier_raw,
                  lt_grade, lt_ord, lt_ord_earlier, st_grade, outlook, notch_delta, action_raw,
                  action_class, watch_flag, below_investment_grade, rating_date, broadcast_dt,
                  attachment_url)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET
                 symbol=excluded.symbol, action_class=excluded.action_class,
                 notch_delta=excluded.notch_delta, lt_ord=excluded.lt_ord,
                 watch_flag=excluded.watch_flag,
                 below_investment_grade=excluded.below_investment_grade, parsed_at=datetime('now')""",
            (_cr_uid(e), e.get("app_id"), e.get("symbol"), e.get("issuer_name"), e.get("isin"),
             _canon_agency(e.get("agency")),
             e.get("rating_raw"), e.get("rating_earlier_raw"), e.get("lt_grade"), e.get("lt_ord"),
             e.get("lt_ord_earlier"), e.get("st_grade"), e.get("outlook"), e.get("notch_delta"),
             e.get("action_raw"), e.get("action_class"), e.get("watch_flag"),
             e.get("below_investment_grade"), e.get("rating_date"), e.get("broadcast_dt"),
             e.get("attachment_url")),
        )
        n += 1
    return n


# --- fetch -----------------------------------------------------------------

_NSE_HOME = "https://www.nseindia.com"
_CR_REF = "https://www.nseindia.com/companies-listing/debt-centralised-database/crd"
_CR_API = "https://www.nseindia.com/api/corporate-credit-rating"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/122 Safari/537.36")


def _session():
    import requests
    s = requests.Session()
    h = {"User-Agent": _UA, "Accept": "application/json,text/plain,*/*",
         "Accept-Language": "en-US,en;q=0.9", "Referer": _CR_REF}
    s.get(_NSE_HOME, headers=h, timeout=20)
    s.get(_CR_REF, headers=h, timeout=20)
    return s, h


def _d(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def fetch_ratings(from_date: str, to_date: str, *, session=None, headers=None) -> list:
    if session is None:
        session, headers = _session()

    def dmy(iso):
        y, m, d = str(iso)[:10].split("-")
        return "%s-%s-%s" % (d, m, y)

    url = "%s?index=&from_date=%s&to_date=%s" % (_CR_API, dmy(from_date), dmy(to_date))
    r = session.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    j = r.json()
    rows = j.get("data") if isinstance(j, dict) else j
    return rows or []


def ingest_range(from_date: str, to_date: str, *, chunk_days: int = 45, pause: float = 1.2) -> dict:
    start, end = _d(from_date), _d(to_date)
    if not start or not end:
        raise ValueError("dates must be ISO YYYY-MM-DD")
    session, headers = _session()
    fetched = saved = linked = 0
    consec_fail = 0
    aborted = False
    with get_conn() as conn:
        ensure_schema(conn)
        conn.commit()
        name_map = _load_name_map(conn)
        cur = start
        while cur <= end and not aborted:
            ce = min(cur + timedelta(days=chunk_days - 1), end)
            try:
                raw = fetch_ratings(cur.isoformat(), ce.isoformat(), session=session, headers=headers)
            except Exception as e:  # noqa: BLE001
                log.warning("CR fetch failed %s..%s: %s", cur, ce, e)
                consec_fail += 1
                if consec_fail >= 6:
                    # NSE throttling — stop burning timeouts; the run is idempotent,
                    # re-run the same window to resume (AUD-24 / insider_events pattern)
                    log.warning("CR: %d consecutive fetch failures — aborting cleanly", consec_fail)
                    aborted = True
                    break
                cur = ce + timedelta(days=1)
                time.sleep(pause + 5 * consec_fail)
                continue
            consec_fail = 0
            events = [normalize_cr(x, name_map) for x in raw]
            linked += sum(1 for e in events if e.get("symbol"))
            saved += save_events(conn, events)
            # COMMIT PER CHUNK — the write lock must never span a network fetch
            # (the 2026-07-02 outage class, a4f1c21/D82c); a killed run keeps progress.
            conn.commit()
            fetched += len(raw)
            log.info("CR %s..%s: %d rows", cur, ce, len(raw))
            cur = ce + timedelta(days=1)
            time.sleep(pause)
    return {"from": from_date, "to": to_date, "fetched": fetched, "saved": saved,
            "linked_to_symbol": linked, "aborted_throttled": aborted}


# --- PIT aggregation / veto ------------------------------------------------

_ADVERSE = {DOWNGRADE, DEFAULT}


def aggregate(events: list, as_of: str, *, window_days: int = 365) -> dict:
    ao = _d(as_of)
    known = [e for e in events
             if _d(e.get("broadcast_dt")) and _d(e["broadcast_dt"]) <= ao
             and (ao - _d(e["broadcast_dt"])).days <= window_days]
    downgrades = [e for e in known if e.get("action_class") == DOWNGRADE]
    defaults = [e for e in known if e.get("action_class") == DEFAULT]
    upgrades = [e for e in known if e.get("action_class") == UPGRADE]
    watch_neg = [e for e in known if e.get("watch_flag") and (e.get("outlook") == "Negative")]
    latest = max(known, key=lambda e: e.get("broadcast_dt") or "", default=None)
    if defaults:
        verdict = "default"
    elif downgrades:
        verdict = "downgrade_veto"
    elif watch_neg:
        verdict = "watch_negative"
    elif upgrades:
        verdict = "upgrade"
    else:
        verdict = "stable" if known else "unrated"
    return {
        "as_of": as_of, "n_events": len(known),
        "downgrades": len(downgrades), "defaults": len(defaults), "upgrades": len(upgrades),
        "worst_notch_delta": min((e["notch_delta"] for e in known if e.get("notch_delta") is not None),
                                 default=None),
        "current_lt": latest.get("lt_grade") if latest else None,
        "below_investment_grade": latest.get("below_investment_grade") if latest else None,
        "credit_verdict": verdict,
    }


# --- selftest --------------------------------------------------------------

def _selftest() -> int:
    # parser across the real agency formats observed on the VPS
    p = parse_rating("CARE AAA/Stable")
    assert p["lt"] == "AAA" and p["lt_ord"] == _LT_ORD["AAA"] and p["outlook"] == "Stable", p
    p = parse_rating("[ICRA]A(Negative)")
    assert p["lt"] == "A" and p["outlook"] == "Negative", p
    p = parse_rating("CARE BBB-; Stable / CARE A3")
    assert p["lt"] == "BBB-" and p["st"] == "A3" and p["outlook"] == "Stable", p
    p = parse_rating("CRISIL AA+/Positive")
    assert p["lt"] == "AA+" and p["lt_ord"] == _LT_ORD["AA+"], p
    p = parse_rating("CARE A1+")
    assert p["lt"] is None and p["st"] == "A1+", p       # short-term only
    p = parse_rating("IND D")
    assert p["lt"] == "D" and p["lt_ord"] == _LT_ORD["D"], p
    # prose / withdrawal notices must NOT yield a grade ("B" from "BANK" was flagging AAA issuers below-IG)
    assert parse_rating("Withdrawn for Bank Loan facilities")["lt"] is None
    assert parse_rating("Withdrawn for Commercial Paper")["lt"] is None
    evw = normalize_cr({"AppID": "w", "CreditRating": "Withdrawn for Bank Loan facilities",
                        "RatingAction": "Withdrawn for Bank Loan facilities", "CompanyName": "Tata Capital",
                        "BroadcastDateTime": "05-JAN-2026 10:00:00"})
    assert evw["below_investment_grade"] == 0 and evw["action_class"] == WITHDRAWN, evw

    # notch delta + action from the real Dhruv downgrade (BBB- -> BB+)
    ev = normalize_cr({"AppID": "1", "Symbol": "NOTLISTED", "CompanyName": "Dhruv Consultancy",
                       "CreditRating": "CARE BB+; Stable", "CreditRatingEarlier": "CARE BBB-; Stable",
                       "RatingAction": "Downgrade", "BroadcastDateTime": "05-JAN-2026 10:00:00",
                       "NameOfCRAgency": "CARE"})
    assert ev["notch_delta"] == _LT_ORD["BB+"] - _LT_ORD["BBB-"] == -1, ev["notch_delta"]
    assert ev["action_class"] == DOWNGRADE and ev["below_investment_grade"] == 1, ev
    assert ev["symbol"] is None, ev   # not linkable without a name map

    # "Other" action resolved by the notch move
    ev2 = normalize_cr({"AppID": "2", "CreditRating": "CRISIL AA/Stable",
                        "CreditRatingEarlier": "CRISIL AA-/Stable", "RatingAction": "Other",
                        "BroadcastDateTime": "06-JAN-2026 10:00:00"})
    assert ev2["action_class"] == UPGRADE and ev2["notch_delta"] == 1, ev2

    # default detection
    ev3 = normalize_cr({"AppID": "3", "CreditRating": "CARE D", "RatingAction": "Downgrade",
                        "BroadcastDateTime": "07-JAN-2026 10:00:00"})
    assert ev3["action_class"] == DEFAULT, ev3
    # reaffirming an already-D instrument is NOT a fresh default event
    ev3b = normalize_cr({"AppID": "3b", "CreditRating": "CARE D", "CreditRatingEarlier": "CARE D",
                         "RatingAction": "Reaffirm", "BroadcastDateTime": "07-JAN-2026 10:00:00"})
    assert ev3b["action_class"] == REAFFIRM, ev3b

    # aggregation verdict: a downgrade in-window vetoes
    agg = aggregate([ev, ev2], "2026-06-01")
    assert agg["credit_verdict"] == "downgrade_veto" and agg["downgrades"] == 1, agg
    assert aggregate([ev2], "2026-06-01")["credit_verdict"] == "upgrade"
    assert aggregate([], "2026-06-01")["credit_verdict"] == "unrated"

    print("selftest OK  parser(6 formats) + notch/action + default + linkage + aggregation")
    print("  Dhruv downgrade notch_delta=%s below_IG=%s" % (ev["notch_delta"], ev["below_investment_grade"]))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--parse", metavar="RATING", help="parse one rating string")
    p.add_argument("--ingest", nargs=2, metavar=("FROM", "TO"))
    p.add_argument("--chunk-days", type=int, default=45)
    p.add_argument("--agg", metavar="SYMBOL")
    p.add_argument("--as-of", default=None)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.selftest:
        raise SystemExit(_selftest())
    if args.parse:
        print(json.dumps(parse_rating(args.parse), indent=2))
        return
    if args.ingest:
        log.info("credit-rating ingest: %s", ingest_range(args.ingest[0], args.ingest[1],
                                                          chunk_days=args.chunk_days))
        return
    if args.agg:
        as_of = args.as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM credit_rating_events WHERE symbol=? ORDER BY broadcast_dt",
                (args.agg.upper(),))]
        print(json.dumps(aggregate(rows, as_of), indent=2, default=str))
        return
    p.print_help()


if __name__ == "__main__":
    main()
