"""Wolfe SCANNER — the OOS-validated reachable-EPA winner-profile setups, as of today.

The Phase-1 backtest + walk-forward (2026-06-25) showed the RAW Wolfe trade has no edge,
but the WINNER-PROFILE selection — reachable EPA (D<=1) + strong point-1 (p1>=2) + not-
narrowest zone (F<=2) — is a robust, two-sided, BETA-NEUTRAL edge, consistent across three
independent eras (median +1.5..2.5% net; bears +0.8..1.3% median, positive every era). This
scanner applies that filter to the CURRENT universe and lists names with a FRESH, actionable
setup: the entry zone, the stop (zone edge ∓0.3%), T1 (the 0.618∩0.618 confluence) and the
EPA target. DESCRIPTIVE — it surfaces candidates; it does not trade.

PIT-honest: pass --asof YYYY-MM-DD to see exactly what the scanner would have shown then
(bars truncated to <= as-of; the fractal/point-5 design is naturally point-in-time).

Run:  cd /opt/hermes && python3 research/wolfe_waves/scanner.py [--universe nifty500|inclusive] [--asof YYYY-MM-DD] [--fresh N]
"""
import bisect
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from src.automation import wolfe                                                       # noqa: E402
from src.core.db import get_conn                                                       # noqa: E402
from research.wolfe_waves.phase1_tradesim import entry_zones, t1_level, nifty500, inclusive  # noqa: E402

FRESH = 15      # point 5 within the last N bars = a current / still-actionable setup
SLB = 0.003     # 0.3% stop buffer beyond the zone far edge (his anti-stop-hunt rule)


def is_winner(score):
    """The OOS-validated winner-profile filter (the edge): reachable EPA + strong point-1
    + not-narrowest zone. NOTE this is the OPPOSITE of ranking by the §B quality total —
    the backtest showed §B's far-EPA (D) preference selects the no-edge lottery."""
    return bool(score) and score.get("D", 9) <= 1 and score.get("p1", 0) >= 2 and score.get("F", 9) <= 2


def scan(conn, names, asof=None, fresh=FRESH):
    out = []
    for sym in names:
        s = wolfe.stock_series(conn, sym)
        if not s:
            continue
        dates, _o, highs, lows, closes = s
        if asof:                                            # PIT truncation: only bars <= as-of
            k = bisect.bisect_right(dates, asof)
            if k < 60:
                continue
            dates, highs, lows, closes = dates[:k], highs[:k], lows[:k], closes[:k]
        n = len(closes)
        cmp_ = closes[-1]
        waves, _ = wolfe.detect_waves(highs, lows, closes)
        for w in waves:
            if w.state != "CONFIRMED" or not w.p5 or not is_winner(w.score):
                continue
            age = n - 1 - w.p5.idx
            if age > fresh:                                 # only fresh / still-actionable setups
                continue
            zones = entry_zones(w.p, w.direction)
            if not zones:
                continue
            z = zones[0]                                    # first-reached entry zone
            bull = w.direction == "BULL"
            sl = z["low"] * (1 - SLB) if bull else z["high"] * (1 + SLB)
            t1 = t1_level(w.p, w.direction, 0.02)
            epa = w.p[0].price + w.epa_slope * (n - 1 - w.p[0].idx)    # the EPA target line, at now
            up = abs(epa - z["price"]) / z["price"] * 100.0
            in_zone = z["low"] * 0.995 <= cmp_ <= z["high"] * 1.005    # actionable now (price in the zone ±0.5%)
            out.append({"sym": sym, "dir": w.direction, "cmp": cmp_, "zlo": z["low"], "zhi": z["high"],
                        "zp": z["price"], "sl": sl, "t1": t1, "epa": epa, "up": up, "age": age,
                        "in_zone": in_zone, "Q": w.score["total"], "p5date": dates[w.p5.idx]})
    return out


def main():
    asof = None
    uni = "nifty500"
    fresh = FRESH
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--asof" and i + 1 < len(a):
            asof = a[i + 1]
        if x == "--universe" and i + 1 < len(a):
            uni = a[i + 1]
        if x == "--fresh" and i + 1 < len(a):
            fresh = int(a[i + 1])
    with get_conn() as conn:
        names = nifty500(conn) if uni == "nifty500" else inclusive(conn)
        res = scan(conn, names, asof, fresh)
    res.sort(key=lambda r: (not r["in_zone"], r["age"]))    # actionable-now first, then freshest
    print("WOLFE SCANNER — reachable-EPA winner-profile (%s · as-of %s · fresh<=%d bars) — %d candidates"
          % (uni, asof or "latest", fresh, len(res)))
    print("  %-12s %-4s %3s %9s  %-19s %9s %9s %9s %5s %4s" %
          ("symbol", "dir", "age", "CMP", "entry zone", "stop", "T1", "EPA", "up%", "now"))
    for r in res:
        t1s = "%.1f" % r["t1"] if r["t1"] else "   -   "
        print("  %-12s %-4s %3d %9.1f  %8.1f - %-8.1f %9.1f %9s %9.1f %4.0f%% %4s" %
              (r["sym"], r["dir"], r["age"], r["cmp"], r["zlo"], r["zhi"], r["sl"], t1s, r["epa"], r["up"],
               "IN" if r["in_zone"] else ""))


if __name__ == "__main__":
    main()
