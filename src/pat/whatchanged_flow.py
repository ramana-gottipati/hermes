"""Pat 'whatchanged' data-flow — the attention bus answered inline (UX audit S-E Phase 2).

Answers "what changed today / what's new / any alerts / what changed for TCS" with the
signal-event bus's edge-triggered state-changes (the same data behind /dash/attention's
alert rail), newest + most-severe first:

  · a SYMBOL named → that name's recent state-changes,
  · none          → the market-wide rail (critical first).

CONTRACT (mirrors nav_flow.py / news_flow.py):
  * PURE logic here — `parse_whatchanged()` (recognition + optional ticker; a ₹0
    pre-pass in engine.route) and `changes()` (a bounded read over `signal_alerts`).
    The HTML render lives in web.py:_whatchanged_flow.
  * CONSERVATIVE: needs a change cue ("changed/new/happened/alerts"), and runs after
    news so "TCS news" stays news. A miss yields None.
  * DESCRIPTIVE / SEBI-safe: a state-change is a recorded fact (X went from A → B on a
    date), never a buy/sell call. Same D106 honesty posture as the rail.
"""
from __future__ import annotations

import re

_CHANGE_RE = re.compile(r"\b(what'?s? changed|what changed|whats changed|anything changed|"
                        r"any changes?|recent changes?|what happened|what'?s new|whats new|"
                        r"any alerts?|alerts? (?:today|now)|signal events?|state changes?|"
                        r"what'?s moved|anything new)\b")

_ON_RE = re.compile(r"\b(?:for|on|with|about|in)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")
_NOT_TICKER = {"WHAT", "ANY", "THE", "TODAY", "NOW", "NEW", "FII", "DII", "NIFTY", "SENSEX",
               "AGM", "IPO", "CEO", "GST", "RBI", "SEBI"}
_MARKET_RE = re.compile(r"\b(market|overall|general|everything|anywhere|nifty|sensex)\b")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _candidate_symbol(query: str) -> str:
    q = _norm(query)
    m = _ON_RE.search(q)
    if m:
        tok = m.group(1).upper()
        return tok if tok not in _NOT_TICKER else ""
    caps = [t for t in _CAPS_RE.findall(q) if t.upper() not in _NOT_TICKER]
    return caps[0].upper() if len(caps) == 1 else ""


def parse_whatchanged(query: str) -> dict | None:
    """"what changed today" / "what's new with INFY" / "any alerts" ->
    {flow:"whatchanged", params:{symbol}} | None. Needs a change cue; extracts a ticker
    when named. Conservative — a miss yields to the normal parse."""
    q = (query or "").strip()
    if not q or not _CHANGE_RE.search(q.lower()):
        return None
    sym = _candidate_symbol(q)
    if sym and _MARKET_RE.search(q.lower()) and not _ON_RE.search(_norm(q)):
        sym = ""
    return {"flow": "whatchanged", "params": {"symbol": sym}}


def changes(conn, symbol: str = "", *, within_days: int = 7, limit: int = 15) -> list[dict]:
    """Recent bus state-changes (the alert rail), optionally for one symbol. Newest +
    most-severe first. Read-only; [] on any gap. Reuses signal_alerts.active_alerts so
    ranking/windowing stays single-sourced."""
    if conn is None:
        return []
    try:
        from src.automation import signal_alerts as _SA
        rows = _SA.active_alerts(conn, within_days=within_days,
                                 limit=200 if symbol else limit)
    except Exception:
        return []
    sym = (symbol or "").strip().upper()
    if sym:
        rows = [r for r in rows if (r.get("symbol") or "").upper() == sym][:limit]
    return rows[:limit]


def is_symbol(conn, symbol: str) -> bool:
    if conn is None or not symbol:
        return False
    try:
        return conn.execute("SELECT 1 FROM security_master WHERE symbol=? LIMIT 1",
                            (symbol.strip().upper(),)).fetchone() is not None
    except Exception:
        return False


def _selftest() -> int:
    import sqlite3
    # recognition
    assert parse_whatchanged("what changed today")["params"]["symbol"] == ""
    assert parse_whatchanged("what's new with INFY")["params"]["symbol"] == "INFY"
    assert parse_whatchanged("what changed for TCS")["params"]["symbol"] == "TCS"
    assert parse_whatchanged("any alerts")["flow"] == "whatchanged"
    assert parse_whatchanged("recent changes in the market")["params"]["symbol"] == ""
    assert parse_whatchanged("anything changed")["flow"] == "whatchanged"
    # yields
    assert parse_whatchanged("biggest movers today") is None, "movers is not whatchanged"
    assert parse_whatchanged("TCS news") is None, "news is not whatchanged"
    assert parse_whatchanged("strong stocks") is None
    assert parse_whatchanged("") is None
    # bounded read on a synthetic rail
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    from src.automation import signal_alerts as SA
    SA.ensure_schema(c)
    c.execute("INSERT INTO signal_alert_state(symbol,lens,event_type,from_state,to_state,"
              "magnitude,severity,valence,as_of) VALUES "
              "('TCS','mep','state','DISTRIB','STRONG_DISTRIB',1.0,'critical','risk','2026-07-14'),"
              "('INFY','rs','state','INSIDE','TOUCH_RES',1.0,'high','opportunity','2026-07-14')")
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.executemany("INSERT INTO security_master VALUES (?)", [("TCS",), ("INFY",)])
    allc = changes(c)
    assert {r["symbol"] for r in allc} == {"TCS", "INFY"}, allc
    assert allc[0]["symbol"] == "TCS", "critical first"
    tcs = changes(c, "TCS")
    assert [r["symbol"] for r in tcs] == ["TCS"] and tcs[0]["to_state"] == "STRONG_DISTRIB"
    assert is_symbol(c, "TCS") and not is_symbol(c, "ZZZZ")
    assert changes(None) == []
    c.close()
    print("whatchanged_flow selftest OK — recognition (change cue; symbol extract; yields "
          "on movers/news/screen) + bounded rail read (market + symbol-filtered, critical-first).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
