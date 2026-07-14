"""Pat 'participants' data-flow — FII positioning answered inline (UX audit S-E Phase 2).

Answers "are FIIs buying / FII flows / who's positioned / FII vs retail" with the FII
index-futures net stance: the latest net long-short, where it sits in its ~2.5-year
range (percentile), and a plain read — the same computation behind /dash/participants'
positioning tape (D62, descriptive market positioning).

CONTRACT (mirrors nav_flow.py / news_flow.py):
  * PURE logic here — `parse_participants()` (a ₹0 pre-pass in engine.route) and
    `fii_stance()` (a bounded read over `participant_oi`). Render = web.py:_participants_flow.
  * CONSERVATIVE: needs an FII/participant cue, runs AFTER nav, so "where do I see FII
    flows" stays a navigate. A miss yields None.
  * DESCRIPTIVE / SEBI-safe: index-futures positioning is a recorded stance (D62), never
    a buy/sell call.
"""
from __future__ import annotations

import re

# an FII/participant/positioning cue must be present
_FII_RE = re.compile(r"\b(fii|fiis|dii|diis|foreign (?:investors?|flows?|money|institutions?)|"
                     r"participants?|positioning|positioned|net (?:long|short)|"
                     r"who(?:'?s| is|'?re| are) (?:buying|positioned|selling)|"
                     r"institutional (?:flows?|positioning))\b")
# a plain "are they buying/selling" needs the FII context to be meaningful, so we anchor
# on the cue above; these are just the verbs we tolerate around it.


def fii_stance(conn) -> dict | None:
    """Latest FII index-futures net stance + its 2.5y percentile. Returns
    {as_of, net_lots, ratio, pct, n_days, stance, cli_net} or None on any gap.
    Net = long − short (lots); ratio = long/short; pct = percentile of the latest
    ratio in its own history. Read-only; mirrors participants_view.render_positioning_tape."""
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT trade_date, client_type, fut_idx_long, fut_idx_short FROM participant_oi "
            "WHERE client_type IN ('FII','CLIENT') ORDER BY trade_date").fetchall()
    except Exception:
        return None
    if not rows:
        return None
    fii_net, fii_ratio, cli_net, dates = {}, {}, {}, []
    for r in rows:
        d = r["trade_date"] if hasattr(r, "keys") else r[0]
        ct = r["client_type"] if hasattr(r, "keys") else r[1]
        lo = r["fut_idx_long"] if hasattr(r, "keys") else r[2]
        sh = r["fut_idx_short"] if hasattr(r, "keys") else r[3]
        if ct == "FII":
            if d not in fii_net:
                dates.append(d)
            fii_net[d] = (lo - sh) if (lo is not None and sh is not None) else None
            fii_ratio[d] = (lo / sh) if (lo and sh) else None
        else:
            cli_net[d] = (lo - sh) if (lo is not None and sh is not None) else None
    dates = sorted(set(dates))
    if len(dates) < 20:
        return None
    ratios = [fii_ratio.get(d) for d in dates if fii_ratio.get(d) is not None]
    latest_d = dates[-1]
    latest_ratio = fii_ratio.get(latest_d)
    if latest_ratio is None or not ratios:
        # fall back to the most recent non-null ratio
        for d in reversed(dates):
            if fii_ratio.get(d) is not None:
                latest_d, latest_ratio = d, fii_ratio[d]
                break
    if latest_ratio is None:
        return None
    dist = sorted(ratios)
    below = sum(1 for r in dist if r < latest_ratio)
    pct = 100.0 * below / len(dist) if dist else 50.0
    if pct <= 12:
        stance = "near-record net-SHORT (unusually bearish)"
    elif pct >= 88:
        stance = "near-record net-LONG (unusually bullish)"
    elif latest_ratio >= 1.1:
        stance = "net-long (leaning bullish)"
    elif latest_ratio <= 0.9:
        stance = "net-short (leaning bearish)"
    else:
        stance = "balanced (near even long/short)"
    return {"as_of": latest_d, "net_lots": fii_net.get(latest_d),
            "ratio": latest_ratio, "pct": pct, "n_days": len(dist),
            "stance": stance, "cli_net": cli_net.get(latest_d)}


def parse_participants(query: str) -> dict | None:
    """"are FIIs buying / FII flows / who's positioned" -> {flow:"participants"} | None.
    Needs an FII/participant cue. Conservative — a miss yields to the normal parse."""
    q = (query or "").strip().lower()
    if not q or not _FII_RE.search(q):
        return None
    return {"flow": "participants", "params": {}}


def _selftest() -> int:
    import sqlite3
    # recognition
    for q in ("are FIIs buying", "FII flows", "FII positioning", "who's positioned",
              "foreign flows", "DII vs FII", "net long or short", "institutional flows"):
        r = parse_participants(q)
        assert r and r["flow"] == "participants", q
    # yields — no FII cue
    assert parse_participants("which stocks are accumulating") is None
    assert parse_participants("biggest movers today") is None
    assert parse_participants("") is None
    # stance read on a synthetic 30-day tape (FII net-long climbing to a high)
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE participant_oi(trade_date TEXT, client_type TEXT, "
              "fut_idx_long INTEGER, fut_idx_short INTEGER)")
    rows = []
    for i in range(30):
        d = f"2026-06-{i+1:02d}"
        # FII ratio rises from ~0.8 to ~1.6 over the window; last day is the max
        lo, sh = 800 + i * 30, 1000
        rows.append((d, "FII", lo, sh))
        rows.append((d, "CLIENT", 1000, 900 + i * 5))
    c.executemany("INSERT INTO participant_oi VALUES (?,?,?,?)", rows)
    st = fii_stance(c)
    assert st and st["as_of"] == "2026-06-30", st
    assert st["ratio"] > 1.1 and st["pct"] >= 88, st          # latest = the peak → top percentile
    assert "net-LONG" in st["stance"] or "net-long" in st["stance"], st
    assert fii_stance(None) is None
    assert fii_stance(sqlite3.connect(":memory:")) is None     # no table → None
    c.close()
    print("participants_flow selftest OK — recognition (FII/participant cue; yields w/o it) + "
          "bounded FII net-stance read (net long-short + 2.5y percentile + plain stance).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
