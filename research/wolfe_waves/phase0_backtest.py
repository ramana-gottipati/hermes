"""PHASE 0 — §C backtest probe: does the §B quality score STRATIFY forward outcomes?

Read-only, isolated (like fractal_proto.py) — NOT a prod change. Detects every CONFIRMED
Wolfe setup across a liquid, SURVIVORSHIP-INCLUSIVE universe (top-N by turnover among all
names with enough history, including ones later delisted), then measures the forward
return from point 5 (SIGNED by direction: bull wants up, bear wants down) at two entry
lags and two horizons, bucketed by quality Q.

  • lag 0  = REPAINT reference — entered at the exact overshoot extreme. Inflated; this is
             the mirage the earlier naive probe hit. Shown ONLY for contrast.
  • lag 5  = realistic — entered 5 bars after the overshoot, once a reversal is visible.

The takeaway is RELATIVE: does a higher-Q bucket beat a lower-Q bucket (and the pooled
ALL row), ESPECIALLY at lag 5? Monotonic Q→outcome = the §B score earns its keep. An
absolute tradeable-edge claim still needs the full §B5 trade-sim + as-of replay (Phase 1).
(Markets drift up, so bull setups carry a tailwind and bear a headwind — a constant offset
across Q buckets, so the Q-monotonicity is what's interpretable, not the absolute sign.)

Run on the VPS:  cd /opt/hermes && python3 research/wolfe_waves/phase0_backtest.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from src.automation import wolfe          # noqa: E402
from src.core.db import get_conn          # noqa: E402

TOPN = 150
MINBARS = 500
LAGS = [0, 5]
HORIZONS = [20, 40]
BUCKETS = [(0, 10), (10, 13), (13, 16), (16, 99)]   # quality-Q ranges


def universe(conn):
    """Top-N EQ names by mean daily traded value, >=MINBARS bars. Survivorship-inclusive:
    no 'still trading today' filter, so names later delisted are kept (their history is in
    the archive — 38% of EQ names are delisted/suspended)."""
    rows = conn.execute(
        """SELECT symbol, AVG(value) av, COUNT(*) c FROM bhavcopy_rows
           WHERE series='EQ' AND (segment='CM' OR segment IS NULL) AND value > 0
           GROUP BY symbol HAVING c >= ? ORDER BY av DESC LIMIT ?""",
        (MINBARS, TOPN)).fetchall()
    return [r[0] for r in rows]


def signed_fwd(closes, t, lag, h, direction):
    """Signed forward return: enter at close[t+lag], exit at close[t+lag+h]; +raw for a
    BULL (reversal up is good), -raw for a BEAR (reversal down is good)."""
    e, x = t + lag, t + lag + h
    if x >= len(closes) or closes[e] <= 0:
        return None
    raw = (closes[x] - closes[e]) / closes[e]
    return raw if direction == "BULL" else -raw


def pit_spotcheck(conn, names):
    """Component-#1 invariant spot-check: a setup found on the FULL series must also be
    found when detection is run AS-OF its point-5 date (series truncated to bars <= p5).
    Proves the as-of plumbing = a plain input truncation (the design is PIT-honest)."""
    for sym in names[:20]:
        s = wolfe.stock_series(conn, sym)
        if not s:
            continue
        _d, _o, highs, lows, closes = s
        waves, _ = wolfe.detect_waves(highs, lows, closes)
        conf = [w for w in waves if w.state == "CONFIRMED" and w.p5 and w.p5.idx < len(closes) - 50]
        if not conf:
            continue
        w = conf[len(conf) // 2]
        t = w.p5.idx
        asof, _ = wolfe.detect_waves(highs[:t + 1], lows[:t + 1], closes[:t + 1])   # bars <= p5 only
        hit = any(a.direction == w.direction and abs(a.p[3].idx - w.p[3].idx) <= 2 and a.p5 for a in asof)
        return "PIT spot-check on %s: setup (%s, p4@%d, p5@%d) re-found as-of p5 = %s" % (
            sym, w.direction, w.p[3].idx, t, "OK" if hit else "MISS")
    return "PIT spot-check: no eligible setup"


def main():
    with get_conn() as conn:
        names = universe(conn)
        print("universe: top %d EQ by turnover, >=%d bars (survivorship-inclusive)" % (len(names), MINBARS))
        rows = []            # (Q, direction, {(lag,h): signed_ret})
        nsetup = nname = 0
        for sym in names:
            s = wolfe.stock_series(conn, sym)
            if not s:
                continue
            nname += 1
            _d, _o, highs, lows, closes = s
            waves, _ = wolfe.detect_waves(highs, lows, closes)
            for w in waves:
                if w.state != "CONFIRMED" or not w.p5 or not w.score:
                    continue
                t = w.p5.idx
                rr = {}
                for lag in LAGS:
                    for h in HORIZONS:
                        v = signed_fwd(closes, t, lag, h, w.direction)
                        if v is not None:
                            rr[(lag, h)] = v
                if rr:
                    rows.append((w.score["total"], w.direction, rr))
                    nsetup += 1
        print("names with data: %d   CONFIRMED setups measured: %d\n" % (nname, nsetup))
        print(pit_spotcheck(conn, names) + "\n")

        def line(lo, hi, lag, h):
            vals = [r[2][(lag, h)] for r in rows if (lag, h) in r[2] and lo <= r[0] < hi]
            if not vals:
                return "    Q[%2d-%2d): (none)" % (lo, hi)
            mean = 100.0 * sum(vals) / len(vals)
            hitr = 100.0 * sum(1 for v in vals if v > 0) / len(vals)
            return "    Q[%2d-%2d): mean %+6.2f%%  hit %4.1f%%  n=%d" % (lo, hi, mean, hitr, len(vals))

        for lag in LAGS:
            tag = "REPAINT (lag 0 — entered at the extreme)" if lag == 0 else "realistic (lag %d)" % lag
            print("=== entry %s ===" % tag)
            for h in HORIZONS:
                print("  horizon %d bars:" % h)
                allv = [r[2][(lag, h)] for r in rows if (lag, h) in r[2]]
                if allv:
                    print("    ALL setups : mean %+6.2f%%  hit %4.1f%%  n=%d  <-- pooled baseline" % (
                        100.0 * sum(allv) / len(allv),
                        100.0 * sum(1 for v in allv if v > 0) / len(allv), len(allv)))
                for lo, hi in BUCKETS:
                    print(line(lo, hi, lag, h))
            print()


if __name__ == "__main__":
    main()
