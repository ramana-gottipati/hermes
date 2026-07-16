"""Pat 'internals' data-flow — market breadth answered inline (UX audit S-E Phase 2).

Answers "how's the breadth / market internals / advance-decline / how many stocks are
up" with the latest market-internals snapshot: the % of the cash universe advancing
(with adv/dec counts), the MEP effort tape, and where each sits in its 22-year range —
the numbers behind /dash/market-internals (bounded `market_internals_daily`, D62-style
descriptive market-state).

CONTRACT (mirrors nav_flow.py / participants_flow.py):
  * PURE logic here — `parse_internals()` (a ₹0 pre-pass in engine.route) and
    `breadth_now()` (a bounded read over `market_internals_daily`). Render =
    web.py:_internals_flow.
  * CONSERVATIVE: needs a breadth/internals cue, runs AFTER nav, so "where do I see
    breadth" stays a navigate. A miss yields None.
  * DESCRIPTIVE / SEBI-safe: breadth + the effort tape are market-state reads, never a
    buy/sell call.
"""
from __future__ import annotations

import re

# a breadth / internals cue must be present
_INT_RE = re.compile(r"\b(breadth|market internals?|internals|advance[- ]?decline|adv[- ]?dec|"
                     r"how many stocks (?:are )?(?:up|down|advancing|declining|rising|falling|"
                     r"above)|how'?s the (?:market )?(?:breadth|tape|internals)|"
                     r"market (?:health|tape)|how broad|effort tape)\b")
# an entity-ranking ask ("which stocks are advancing") is a screen, not this market read
_ENTITY_RE = re.compile(r"\bwhich (?:stocks?|names?|companies)\b")


def breadth_now(conn) -> dict | None:
    """Latest market-internals snapshot + 22y percentiles. Returns
    {as_of, n_eq, adv, dec, unch, pct_adv, pct_adv_pctile, mep_net, mep_pctile,
     disp, coil} or None on any gap. Percentile = fraction of history <= today.
    Read-only; mirrors market_internals_view."""
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT d, n_eq, adv, dec, unch, pct_adv, mep_net, disp, avg_comp "
            "FROM market_internals_daily ORDER BY d").fetchall()
    except Exception:
        return None
    if not rows:
        return None
    last = rows[-1]

    def _col(r, i, k):
        return (r[k] if hasattr(r, "keys") else r[i])

    pct_adv_hist = sorted(_col(r, 5, "pct_adv") for r in rows if _col(r, 5, "pct_adv") is not None)
    mep_hist = sorted(_col(r, 6, "mep_net") for r in rows if _col(r, 6, "mep_net") is not None)

    def _pctile(dist, v):
        if not dist or v is None:
            return None
        below = sum(1 for x in dist if x <= v)
        return 100.0 * below / len(dist)

    pa = _col(last, 5, "pct_adv")
    mn = _col(last, 6, "mep_net")
    return {
        "as_of": _col(last, 0, "d"),
        "n_eq": _col(last, 1, "n_eq"),
        "adv": _col(last, 2, "adv"),
        "dec": _col(last, 3, "dec"),
        "unch": _col(last, 4, "unch"),
        "pct_adv": pa,
        "pct_adv_pctile": _pctile(pct_adv_hist, pa),
        "mep_net": mn,
        "mep_pctile": _pctile(mep_hist, mn),
        "disp": _col(last, 7, "disp"),
        "coil": _col(last, 8, "avg_comp"),
        "n_hist": len(pct_adv_hist),
    }


def read_word(pctile: float, low: str, high: str) -> str:
    """A plain read for a percentile (mirrors market_internals_view._phrase, condensed)."""
    if pctile is None:
        return "no history"
    if pctile <= 8:
        return f"a multi-year low — deeply {low}"
    if pctile <= 25:
        return f"{low} ({int(round(pctile))}th pctile of its range)"
    if pctile >= 92:
        return f"a multi-year high — broadly {high}"
    if pctile >= 75:
        return f"{high} ({int(round(pctile))}th pctile)"
    return f"middling ({int(round(pctile))}th pctile)"


def parse_internals(query: str) -> dict | None:
    """"how's the breadth / market internals / how many stocks are up" ->
    {flow:"internals"} | None. Needs a breadth/internals cue and NOT an entity-ranking
    ask. Conservative — a miss yields to the normal parse."""
    q = (query or "").strip().lower()
    if not q or not _INT_RE.search(q):
        return None
    if _ENTITY_RE.search(q):
        return None                                    # "which stocks are advancing" = a screen
    return {"flow": "internals", "params": {}}


def _selftest() -> int:
    import sqlite3
    # recognition
    for q in ("how's the breadth", "market breadth", "market internals", "advance decline",
              "how many stocks are up", "how broad is the market", "how's the tape"):
        r = parse_internals(q)
        assert r and r["flow"] == "internals", q
    # yields
    assert parse_internals("which stocks are advancing") is None, "entity ranking = screen"
    assert parse_internals("biggest movers today") is None
    assert parse_internals("are FIIs buying") is None
    assert parse_internals("") is None
    # read on a synthetic snapshot (today = broad advance at the top of range)
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE market_internals_daily(d TEXT, n_eq INT, adv INT, dec INT, unch INT, "
              "pct_adv REAL, mep_net REAL, disp REAL, avg_comp REAL)")
    hist = []
    for i in range(40):
        hist.append((f"2026-05-{i+1:02d}", 2000, 900 + i * 5, 1100 - i * 5, 0,
                     45.0 + i * 0.7, -10.0 + i * 0.5, 2.0, 1.0))
    hist.append(("2026-07-10", 2370, 1758, 592, 20, 74.18, 16.92, 2.263, 0.9448))  # latest = high
    c.executemany("INSERT INTO market_internals_daily VALUES (?,?,?,?,?,?,?,?,?)", hist)
    b = breadth_now(c)
    assert b and b["as_of"] == "2026-07-10" and b["adv"] == 1758, b
    assert b["pct_adv"] == 74.18 and b["pct_adv_pctile"] >= 92, b   # latest = top of range
    assert b["mep_net"] == 16.92 and b["mep_pctile"] >= 92, b
    assert "broadly" in read_word(b["pct_adv_pctile"], "narrow", "broad")
    assert breadth_now(None) is None
    assert breadth_now(sqlite3.connect(":memory:")) is None         # no table → None
    c.close()
    print("internals_flow selftest OK — recognition (breadth/internals cue; yields on "
          "entity-ranking/off-topic) + bounded breadth read (pct_adv + adv/dec + MEP tape + "
          "22y percentiles).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
