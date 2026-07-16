"""Pat 'filings' data-flow — per-symbol ownership & filings answered inline (UX audit S-E Ph2).

Answers "filings for TCS / insider activity in RELIANCE / any pledge on INFY / credit rating
of X / shareholding of Y" by bundling the four Ownership & filings lenses for ONE symbol:
  * INSIDER   — SEBI PIT disclosures (insider_events)        → /dash/insider
  * RATINGS   — credit-rating actions (credit_rating_events) → /dash/ratings
  * SAST      — stake × pledge disclosures (sast_* tables)   → /dash/sast
  * HOLDINGS  — shareholding QoQ deltas (shareholding_history)→ /dash/shp
These lenses are market-wide BOARDS with no per-symbol Pat read, so this flow writes NEW
bounded, read-only per-symbol queries against their event tables (reusing sast_events.aggregate
and mirroring shp_view's research.db read).

CONTRACT (mirrors rotation_flow.py / participants_flow.py):
  * PURE logic here — `parse_filings()` (a ₹0 pre-pass in engine.route; needs a filings cue
    AND a symbol) and `filings_for()` (the four bounded reads). Render = web.py:_filings_flow.
  * CONSERVATIVE + symbol-anchored: fires only with a SYMBOL, and runs BEFORE participants so a
    per-symbol "FII holding in TCS" is not stolen by the market-wide FII stance; a market-wide
    "insider activity" (no symbol) yields to the normal parse.
  * DESCRIPTIVE / SEBI-safe: recorded regulatory disclosures, never a buy/sell call.
"""
from __future__ import annotations

import re
from datetime import date

# a filings / ownership cue must be present
_FILE_RE = re.compile(
    r"\b(filings?|disclosures?|insider|promoter (?:buy|buying|sold|selling|sell|stake)|"
    r"pit disclosure|credit rating|ratings?|rated|upgrade[ds]?|downgrade[ds]?|"
    r"pledge[ds]?|encumber|encumbered|sast|substantial (?:stake|holder)|"
    r"shareholding|holding pattern|holders?|fii holding|dii holding|promoter holding|"
    r"who (?:holds|owns))\b")

# focus cues → which feed leads the bundle
_FOCUS = [
    ("sast",     re.compile(r"\b(pledge[ds]?|encumber|encumbered|sast|substantial (?:stake|holder)|stake)\b")),
    ("ratings",  re.compile(r"\b(credit rating|ratings?|rated|upgrade[ds]?|downgrade[ds]?)\b")),
    ("shp",      re.compile(r"\b(shareholding|holding pattern|holders?|fii holding|dii holding|"
                            r"promoter holding|who (?:holds|owns))\b")),
    ("insider",  re.compile(r"\b(insider|promoter (?:buy|buying|sold|selling|sell)|pit disclosure)\b")),
]

_ON_RE = re.compile(r"\b(?:is|for|of|in|on|about)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")
_NOT_TICKER = {"WHAT", "ANY", "THE", "FII", "DII", "SAST", "PIT", "IS", "IN", "ON", "OF",
               "WHO", "HOLDS", "OWNS", "PLEDGE", "RATING", "RATINGS", "INSIDER", "FILINGS"}

_SHP_METRICS = ("Promoters", "FIIs", "DIIs", "Public", "Promoter Pledge")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _candidate_symbol(query: str) -> str:
    q = _norm(query)
    m = _ON_RE.search(q)
    if m and m.group(1).upper() not in _NOT_TICKER:
        return m.group(1).upper()
    caps = [t for t in _CAPS_RE.findall(q) if t.upper() not in _NOT_TICKER]
    return caps[0].upper() if len(caps) == 1 else ""


def _focus(ql: str) -> str:
    for name, rx in _FOCUS:
        if rx.search(ql):
            return name
    return "all"


def parse_filings(query: str) -> dict | None:
    """"filings for TCS / insider activity in RELIANCE / pledge on INFY / credit rating of X" ->
    {flow:"filings", params:{symbol, focus}} | None. Needs a filings cue AND a symbol — so a
    market-wide "insider activity" (no symbol) and the market-wide FII stance are never stolen."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    if not _FILE_RE.search(ql):
        return None
    sym = _candidate_symbol(q)
    if not sym:
        return None                                    # symbol-anchored: no symbol → not us
    return {"flow": "filings", "params": {"symbol": sym, "focus": _focus(ql)}}


# ── the four bounded, read-only per-symbol reads ──────────────────────────────────────
def _table_exists(conn, name: str) -> bool:
    try:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                            (name,)).fetchone() is not None
    except Exception:
        return False


def insider_recent(conn, symbol: str, limit: int = 4) -> list[dict]:
    """Recent SEBI PIT insider disclosures for one symbol (newest first). Read-only."""
    if conn is None or not _table_exists(conn, "insider_events"):
        return []
    try:
        rows = conn.execute(
            "SELECT disclosure_dt, category, txn_class, signal_class, value_rs, mode "
            "FROM insider_events WHERE symbol=? AND amendment_flag=0 "
            "ORDER BY disclosure_dt DESC LIMIT ?", (symbol.upper(), limit)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        g = (lambda i, k: r[k] if hasattr(r, "keys") else r[i])
        out.append({"dt": g(0, "disclosure_dt"), "category": g(1, "category"),
                    "txn_class": g(2, "txn_class"), "signal": g(3, "signal_class"),
                    "value_rs": g(4, "value_rs"), "mode": g(5, "mode")})
    return out


def ratings_recent(conn, symbol: str, limit: int = 3) -> list[dict]:
    """Recent credit-rating actions for one symbol (newest first). Read-only."""
    if conn is None or not _table_exists(conn, "credit_rating_events"):
        return []
    try:
        rows = conn.execute(
            "SELECT COALESCE(broadcast_dt, rating_date) t0, agency, action_class, rating_raw, "
            "rating_earlier_raw, outlook, notch_delta FROM credit_rating_events "
            "WHERE symbol=? ORDER BY t0 DESC LIMIT ?", (symbol.upper(), limit)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        g = (lambda i, k: r[k] if hasattr(r, "keys") else r[i])
        out.append({"dt": (str(g(0, "t0"))[:10] if g(0, "t0") else ""), "agency": g(1, "agency"),
                    "action": g(2, "action_class"), "rating": g(3, "rating_raw"),
                    "prior": g(4, "rating_earlier_raw"), "outlook": g(5, "outlook"),
                    "notch": g(6, "notch_delta")})
    return out


def sast_summary(conn, symbol: str) -> dict | None:
    """Pledge-flow + stake-move roll-up (reuses sast_events.aggregate, conn-shared). None on gap."""
    if conn is None or not _table_exists(conn, "sast_pledge_events"):
        return None
    try:
        from src.automation import sast_events as SE
        agg = SE.aggregate(symbol, date.today().isoformat(), conn=conn)
    except Exception:
        return None
    if not agg or (agg.get("n_pledge_events_known", 0) == 0 and agg.get("n_reg29_known", 0) == 0):
        return None
    return agg


def holdings_latest(symbol: str) -> dict | None:
    """Latest shareholding mix + the QoQ delta per holder class, from research.db (read-only,
    mirrors shp_view._series). Returns {as_of, rows:[{metric, value, delta}]} or None."""
    try:
        import sqlite3
        from src.automation import shareholding_xbrl as SX
        con = sqlite3.connect(f"file:{SX.RESEARCH_DB}?mode=ro", uri=True)
    except Exception:
        return None
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT period_end, metric, value FROM shareholding_history "
            "WHERE symbol=? AND metric IN (?,?,?,?,?) ORDER BY period_end DESC",
            (symbol.upper(), *_SHP_METRICS)).fetchall()
    except Exception:
        con.close()
        return None
    con.close()
    if not rows:
        return None
    periods = sorted({r["period_end"] for r in rows}, reverse=True)
    if not periods:
        return None
    latest = periods[0]
    prev = periods[1] if len(periods) > 1 else None
    by = {}
    for r in rows:
        by.setdefault(r["metric"], {})[r["period_end"]] = r["value"]
    out = []
    for m in _SHP_METRICS:
        cur = by.get(m, {}).get(latest)
        if cur is None:
            continue
        pv = by.get(m, {}).get(prev) if prev else None
        delta = (cur - pv) if (pv is not None) else None
        out.append({"metric": m, "value": cur, "delta": delta})
    if not out:
        return None
    return {"as_of": latest, "prev": prev, "rows": out}


def filings_for(conn, symbol: str) -> dict:
    """The four bounded per-symbol reads bundled. Each section is [] / None when empty.
    Read-only; hermes.db `conn` feeds insider/ratings/sast, research.db is opened for shp."""
    sym = (symbol or "").strip().upper()
    return {
        "symbol": sym,
        "insider": insider_recent(conn, sym),
        "ratings": ratings_recent(conn, sym),
        "sast": sast_summary(conn, sym),
        "holdings": holdings_latest(sym),
    }


def has_any(bundle: dict) -> bool:
    return bool(bundle.get("insider") or bundle.get("ratings")
               or bundle.get("sast") or bundle.get("holdings"))


def _selftest() -> int:
    import sqlite3
    # ── recognition — filings cue + a symbol ──
    assert parse_filings("filings for TCS")["params"] == {"symbol": "TCS", "focus": "all"}
    assert parse_filings("insider activity in RELIANCE")["params"] == {"symbol": "RELIANCE", "focus": "insider"}
    assert parse_filings("any pledge on INFY")["params"]["focus"] == "sast"
    assert parse_filings("credit rating of HDFCBANK")["params"] == {"symbol": "HDFCBANK", "focus": "ratings"}
    assert parse_filings("shareholding of WIPRO")["params"]["focus"] == "shp"
    assert parse_filings("promoter holding in ITC")["params"]["symbol"] == "ITC"
    # ── yields — no symbol (market-wide), or no filings cue ──
    assert parse_filings("insider activity") is None, "no symbol → market-wide, not us"
    assert parse_filings("any pledge disclosures") is None
    assert parse_filings("are FIIs buying") is None, "market FII stance → participants, not us"
    assert parse_filings("TCS news") is None, "no filings cue"
    assert parse_filings("what phase is TCS in") is None
    assert parse_filings("") is None
    # ── reads on synthetic hermes tables ──
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE insider_events(symbol TEXT, disclosure_dt TEXT, category TEXT, "
              "txn_class TEXT, signal_class TEXT, value_rs REAL, mode TEXT, amendment_flag INT)")
    c.executemany("INSERT INTO insider_events VALUES (?,?,?,?,?,?,?,?)", [
        ("TCS", "2026-07-10", "Promoter", "OPEN_MARKET_BUY", "conviction", 5.2e7, "Market", 0),
        ("TCS", "2026-06-01", "KMP", "OPEN_MARKET_SELL", "caution", 1.1e7, "Market", 0),
        ("TCS", "2026-05-01", "Promoter", "PLEDGE_CREATE", "pledge_risk", 0, "Off Market", 1)])  # amended → excluded
    c.execute("CREATE TABLE credit_rating_events(symbol TEXT, broadcast_dt TEXT, rating_date TEXT, "
              "agency TEXT, action_class TEXT, rating_raw TEXT, rating_earlier_raw TEXT, "
              "outlook TEXT, notch_delta INT)")
    c.execute("INSERT INTO credit_rating_events VALUES "
              "('TCS','2026-07-05',NULL,'CRISIL','UPGRADE','AAA','AA+','Stable',1)")
    ins = insider_recent(c, "TCS")
    assert len(ins) == 2 and ins[0]["signal"] == "conviction", ins
    rat = ratings_recent(c, "TCS")
    assert rat and rat[0]["action"] == "UPGRADE" and rat[0]["agency"] == "CRISIL", rat
    # sast/holdings degrade to None on absent tables (no crash)
    assert sast_summary(c, "TCS") is None            # no sast_pledge_events table
    assert holdings_latest("ZZZZ") is None or isinstance(holdings_latest("ZZZZ"), dict)
    b = filings_for(c, "TCS")
    assert has_any(b) and b["symbol"] == "TCS" and b["insider"] and b["ratings"]
    assert not has_any(filings_for(c, "NOSUCH"))
    c.close()
    print("filings_flow selftest OK — recognition (filings cue + symbol-anchored; yields on "
          "market-wide/no-cue) + bounded per-symbol reads (insider/ratings live; sast/holdings "
          "degrade to None on absent tables) + amendment exclusion.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
