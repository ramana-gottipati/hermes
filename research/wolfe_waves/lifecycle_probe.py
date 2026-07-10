#!/usr/bin/env python3
"""READ-ONLY lifecycle probe (S89 follow-up, Ramana's actionability taxonomy).

States per CONFIRMED wave:
  OPEN   = point 5 printed, EPA line NOT yet touched after 5  -> actionable (his primary need)
  CLOSED = EPA touched at some bar after point 5              -> reference/validation only

Questions answered (Nifty-500):
  1. How many of today's scan-eligible rows (winner+zones+age<=15) are already CLOSED?
  2. How many of today's watch rows (STR>=10, not-on-scan, age<=15) are already CLOSED?
  3. THE HOLE: winner-profile OPEN waves older than 15 bars -> invisible on every actionable surface.
  4. Same hole for strong-structure (STR>=10) non-winners (the watch's blind tail).
  5. Descriptive validation stat: bars from p5 to EPA-touch among CLOSED (by direction).
READ-ONLY: sqlite mode=ro.
"""
import json
import sqlite3
import sys
import time

sys.path.insert(0, "/opt/hermes")
from src.automation import wolfe  # noqa: E402


def epa_touch_idx(w, highs, lows, n):
    """First bar AFTER point 5 where the 1-4 (EPA) line is touched; None = still OPEN."""
    p1 = w.p[0]
    for t in range(w.p5.idx + 1, n):
        epa_t = p1.price + w.epa_slope * (t - p1.idx)
        if (w.direction == 'BULL' and highs[t] >= epa_t) or \
           (w.direction == 'BEAR' and lows[t] <= epa_t):
            return t
    return None


def main():
    uni = sys.argv[1] if len(sys.argv) > 1 else "nifty500"
    conn = sqlite3.connect("file:/opt/hermes/data/hermes.db?mode=ro", uri=True)
    syms = wolfe.scan_universe(conn, uni)
    t0 = time.time()
    agg = {"universe": uni, "symbols": len(syms),
           "conf": 0, "open": 0, "closed": 0,
           "fresh15": 0, "fresh15_open": 0, "fresh15_closed": 0,
           "scan_rows": 0, "scan_rows_closed": 0,
           "watch_rows": 0, "watch_rows_closed": 0,
           "hole_winner_open_stale": 0,      # winner+zones+OPEN but age>15 -> invisible today
           "hole_strong_open_stale": 0,      # STR>=10, non-winner, OPEN, age>15
           "closed_bars_to_epa": {"BULL": [], "BEAR": []}}
    hole_examples = []
    for k, sym in enumerate(syms):
        if k and k % 100 == 0:
            sys.stderr.write("  %d/%d %.0fs\n" % (k, len(syms), time.time() - t0))
        s = wolfe.stock_series(conn, sym)
        if not s:
            continue
        dates, _o, highs, lows, closes = s
        n = len(closes)
        waves, _ = wolfe.detect_waves(highs, lows, closes)
        for w in waves:
            if w.state != "CONFIRMED" or not w.p5:
                continue
            agg["conf"] += 1
            age = n - 1 - w.p5.idx
            ti = epa_touch_idx(w, highs, lows, n)
            is_open = ti is None
            agg["open" if is_open else "closed"] += 1
            if not is_open:
                agg["closed_bars_to_epa"][w.direction].append(ti - w.p5.idx)
            stq, _l = wolfe.score_split(w.score)
            winner = wolfe.is_winner_profile(w.score)
            _e, _e2, zones = wolfe.fib_zones(w.p[0].price, w.p[1].price, w.p[2].price,
                                             w.p[3].price, direction=w.direction)
            scan_row = winner and bool(zones) and age <= 15
            watch_row = (stq is not None and stq >= wolfe._WATCH_MIN_STRUCTURE
                         and age <= 15 and not (winner and zones))
            if age <= 15:
                agg["fresh15"] += 1
                agg["fresh15_open" if is_open else "fresh15_closed"] += 1
            if scan_row:
                agg["scan_rows"] += 1
                if not is_open:
                    agg["scan_rows_closed"] += 1
            if watch_row:
                agg["watch_rows"] += 1
                if not is_open:
                    agg["watch_rows_closed"] += 1
            if is_open and age > 15 and winner and zones:
                agg["hole_winner_open_stale"] += 1
                if len(hole_examples) < 15:
                    hole_examples.append(
                        "%s %s p5=%s age=%d Q=%s STR=%s" %
                        (sym, w.direction, dates[w.p5.idx], age, w.score["total"], stq))
            if is_open and age > 15 and not winner and stq is not None and stq >= 10:
                agg["hole_strong_open_stale"] += 1
    for d in ("BULL", "BEAR"):
        v = sorted(agg["closed_bars_to_epa"][d])
        agg["closed_bars_to_epa"][d] = {
            "n": len(v), "median": (v[len(v) // 2] if v else None),
            "p25": (v[len(v) // 4] if v else None), "p75": (v[3 * len(v) // 4] if v else None)}
    agg["elapsed_s"] = round(time.time() - t0, 1)
    print(json.dumps(agg, indent=1))
    print("HOLE examples (winner-profile, OPEN, aged past the 15-bar window):")
    for e in hole_examples:
        print("  " + e)
    # the TCS wedge itself
    s = wolfe.stock_series(conn, "TCS")
    dates, _o, highs, lows, closes = s
    n = len(closes)
    waves, _ = wolfe.detect_waves(highs, lows, closes)
    for w in waves:
        if w.state == "CONFIRMED" and w.p5 and dates[w.p[3].idx] == "2026-06-02" and w.direction == "BULL":
            ti = epa_touch_idx(w, highs, lows, n)
            print("TCS wedge: state=%s epa_touch=%s" %
                  ("OPEN" if ti is None else "CLOSED", dates[ti] if ti else "-"))


if __name__ == "__main__":
    main()
