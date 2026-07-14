"""Pat 'rotation' data-flow — a stock's RS-rotation state answered inline (UX audit S-E Ph2).

Answers "what phase is TCS in / rotation state of INFY / is RELIANCE leading or lagging"
with the stock's latest RS-weather phase + RS rank + trend — the per-symbol read behind
the /dash/rotation weather board. Descriptive, rule-based, ZERO LLM.

CONTRACT (mirrors nav_flow.py / news_flow.py):
  * PURE logic here — `parse_rotation()` (a ₹0 pre-pass in engine.route; needs a
    phase/rotation cue AND a symbol) and `phase_for()` (the latest `stock_signals` row).
    Render = web.py:_rotation_flow.
  * CONSERVATIVE + symbol-anchored: fires only when a SYMBOL is present, so a market-wide
    "where's rotation" stays a navigate and "RS leaders" stays the RS board. A miss yields.
  * DESCRIPTIVE / SEBI-safe: a rotation phase is a read-state, never a buy/sell call.
"""
from __future__ import annotations

import re

_ROT_RE = re.compile(r"\b(rotation|phase|weather|quadrant|leading or lagging|"
                     r"leading or weakening|which quadrant|rrg)\b")
# "is X leading/lagging" also counts — but only WITH a symbol (guarded in parse).
_LEAD_RE = re.compile(r"\b(leading|lagging|improving|weakening|rolling over)\b")

_ON_RE = re.compile(r"\b(?:is|for|of|in|on)\s+([A-Za-z][A-Za-z0-9&.\-]{1,14})\b")
_CAPS_RE = re.compile(r"\b([A-Z][A-Z0-9&.\-]{1,14})\b")
_NOT_TICKER = {"WHAT", "ANY", "THE", "RRG", "RS", "FII", "DII", "NIFTY", "SENSEX", "IS", "IN"}

# phase key → (short label, plain read). The canonical vocabulary from rs_phase.rs_weather.
_PHASE = {
    "TAILWIND":     ("Tailwind 🌤", "leading — RS in an uptrend and still strengthening."),
    "RECOVERY":     ("Recovery 🌅", "improving — longer-horizon RS still weak, but turning up."),
    "HEADWIND":     ("Headwind 🌧", "lagging — RS in a downtrend and still weakening."),
    "ROLLING-OVER": ("Rolling over ⛅", "weakening — a strong longer-term base losing near-term steam."),
    "NEUTRAL":      ("Neutral ☁", "middling — no clear relative-strength lean."),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _candidate_symbol(query: str) -> str:
    q = _norm(query)
    m = _ON_RE.search(q)
    if m:
        tok = m.group(1).upper()
        if tok not in _NOT_TICKER:
            return tok
    caps = [t for t in _CAPS_RE.findall(q) if t.upper() not in _NOT_TICKER]
    return caps[0].upper() if len(caps) == 1 else ""


def parse_rotation(query: str) -> dict | None:
    """"what phase is TCS in / rotation state of INFY / is RELIANCE leading" ->
    {flow:"rotation", params:{symbol}} | None. Needs a rotation/phase cue (or a
    leading/lagging cue) AND a symbol — so market-wide asks and the RS-leaders board are
    never stolen. A miss yields to the normal parse."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    if not (_ROT_RE.search(ql) or _LEAD_RE.search(ql)):
        return None
    sym = _candidate_symbol(q)
    if not sym:
        return None                                    # symbol-anchored: no symbol → not us
    # a bare leading/lagging cue with NO rotation word must still have a symbol AND not be a
    # plural board ask ("leading stocks") — the symbol requirement already excludes those.
    return {"flow": "rotation", "params": {"symbol": sym}}


def phase_for(conn, symbol: str) -> dict | None:
    """The stock's latest RS-rotation snapshot: {symbol, phase, phase_label, read, rank,
    trend, as_of} or None. Reads the newest `stock_signals` row that carries a phase."""
    if conn is None or not symbol:
        return None
    try:
        r = conn.execute(
            "SELECT rs_phase, rs_rank, rs_vs_broad_trend_state, trade_date "
            "FROM stock_signals WHERE symbol=? AND rs_phase IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1", (symbol.strip().upper(),)).fetchone()
    except Exception:
        return None
    if not r:
        return None
    phase = (r["rs_phase"] if hasattr(r, "keys") else r[0]) or "NEUTRAL"
    rank = r["rs_rank"] if hasattr(r, "keys") else r[1]
    trend = r["rs_vs_broad_trend_state"] if hasattr(r, "keys") else r[2]
    as_of = r["trade_date"] if hasattr(r, "keys") else r[3]
    label, read = _PHASE.get(phase, (phase.title(), "a relative-strength rotation state."))
    return {"symbol": symbol.strip().upper(), "phase": phase, "phase_label": label,
            "read": read, "rank": rank, "trend": trend, "as_of": as_of}


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
    # recognition — needs a cue AND a symbol
    assert parse_rotation("what phase is TCS in")["params"]["symbol"] == "TCS"
    assert parse_rotation("rotation state of INFY")["params"]["symbol"] == "INFY"
    assert parse_rotation("is RELIANCE leading or lagging")["params"]["symbol"] == "RELIANCE"
    assert parse_rotation("which quadrant is HDFCBANK in")["params"]["symbol"] == "HDFCBANK"
    # yields — no symbol, or no cue, or a board ask
    assert parse_rotation("rotation") is None, "market-wide → nav, not us"
    assert parse_rotation("what's the rotation") is None
    assert parse_rotation("RS leaders") is None, "board ask, no symbol"
    assert parse_rotation("leading stocks") is None
    assert parse_rotation("TCS news") is None, "no rotation cue"
    assert parse_rotation("") is None
    # read on a synthetic stock_signals (latest-with-phase wins)
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE stock_signals(symbol TEXT, rs_phase TEXT, rs_rank INTEGER, "
              "rs_vs_broad_trend_state TEXT, trade_date TEXT)")
    c.executemany("INSERT INTO stock_signals VALUES (?,?,?,?,?)", [
        ("TCS", "NEUTRAL", 40, "CONSOLIDATING", "2026-07-10"),
        ("TCS", "HEADWIND", 3, "DOWNTREND", "2026-07-14"),      # newest
        ("TCS", None, None, None, "2026-07-15")])               # newer but no phase → skipped
    c.execute("CREATE TABLE security_master(symbol TEXT PRIMARY KEY)")
    c.execute("INSERT INTO security_master VALUES ('TCS')")
    p = phase_for(c, "TCS")
    assert p["phase"] == "HEADWIND" and p["rank"] == 3 and "lagging" in p["read"], p
    assert p["as_of"] == "2026-07-14", "newest row WITH a phase"
    assert is_symbol(c, "TCS") and not is_symbol(c, "ZZ")
    assert phase_for(c, "UNKNOWN") is None and phase_for(None, "TCS") is None
    c.close()
    print("rotation_flow selftest OK — recognition (rotation/phase cue + symbol-anchored; "
          "yields on market-wide/board/no-symbol) + latest-phase read with plain-English map.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
