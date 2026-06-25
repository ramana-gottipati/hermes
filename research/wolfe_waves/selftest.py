"""Deterministic correctness test for the Wolfe detector.

Validates src/automation/wolfe.py against synthetic textbook waves:
  bullish = 1·3·5 descending lows, 2·4 highs, 5 overshoots the 1-3 line (reverse up)
  bearish = the mirror (1·3·5 ascending highs, H,L,H,L).
Also pins the Fib-extension formula on Ramana's exact Fyers PARAS swings — projected
toward the overshoot (up) → the strong zone 1226.2.
No DB, no numpy. Exit 0 = PASS.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))  # repo root
from src.automation import wolfe  # noqa: E402


def _ohlc(anchors, band=1.5):
    close = []
    for k in range(len(anchors) - 1):
        i0, p0 = anchors[k]
        i1, p1 = anchors[k + 1]
        for i in range(i0, i1):
            f = (i - i0) / (i1 - i0)
            close.append(p0 + (p1 - p0) * f)   # clean linear so fractal pivots land on the anchors
    close.append(anchors[-1][1])
    high = [c + band for c in close]
    low = [c - band for c in close]
    return high, low, close


def _check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    return bool(cond)


def test_bull():
    print("\n[bullish Wolfe — 1·3·5 lows]")
    # preamble high@10 -> 1(L)@20 2(H)@34 3(L)@48 4(H)@62 5(L overshoot)@78 -> bounce
    high, low, close = _ohlc([(0, 50), (10, 62), (20, 50), (34, 70), (48, 42),
                              (62, 60), (78, 30), (90, 46)])   # leg34<leg12, 4 between 3&2
    waves, _ = wolfe.detect_waves(high, low, close)
    bull = [w for w in waves if w.direction == "BULL"]
    ok = _check(len(bull) >= 1, f"detected a BULL wave (got {len(waves)} total)")
    if not ok:
        return False
    w = bull[0]
    k = [p.kind for p in w.p]
    ok &= _check(k == ["L", "H", "L", "H"], f"pivot kinds 1·2·3·4 = L,H,L,H (got {k})")
    ok &= _check(w.p[2].price < w.p[0].price, f"3<1 lower low ({w.p[2].price:.0f}<{w.p[0].price:.0f})")
    ok &= _check(w.epa_slope > 0, f"1-4 EPA slopes UP ({w.epa_slope:+.2f}/bar)")
    ok &= _check(w.line13_slope < 0, f"1-3 lows descend ({w.line13_slope:+.2f}/bar)")
    ok &= _check(w.p[1].price > w.p[0].price, f"2>1 ({w.p[1].price:.0f}>{w.p[0].price:.0f})")
    ok &= _check(w.p[2].price < w.p[3].price < w.p[1].price,
                 f"4 between 3 and 2 — lower high ({w.p[2].price:.0f}<{w.p[3].price:.0f}<{w.p[1].price:.0f})")
    ok &= _check(w.leg12_price >= w.leg34_price,
                 f"leg 1-2 >= leg 3-4 ({w.leg12_price:.0f}>={w.leg34_price:.0f})")
    ok &= _check(0.5 <= w.sym_price <= 1.0, f"leg34/leg12 ratio in tol ({w.sym_price:.2f})")
    ok &= _check(w.p5 is not None and w.state == "CONFIRMED",
                 f"point 5 confirmed (overshoot @ {w.p5.price:.0f})" if w.p5 else "no point 5")
    ok &= _check(isinstance(w.score, dict) and "total" in w.score,
                 f"§B quality score attached ({w.score})")
    print(f"    -> tier={w.tier} q={w.quality:.2f}  src={w.source}  §B={w.score}")
    return ok


def test_bear():
    print("\n[bearish Wolfe — 1·3·5 highs]")
    high, low, close = _ohlc([(0, 70), (10, 58), (20, 70), (34, 50), (48, 78),
                              (62, 60), (78, 90), (90, 74)])   # leg34<leg12, 4 between 2&3
    waves, _ = wolfe.detect_waves(high, low, close)
    bear = [w for w in waves if w.direction == "BEAR"]
    ok = _check(len(bear) >= 1, f"detected a BEAR wave (got {len(waves)} total)")
    if not ok:
        return False
    w = bear[0]
    k = [p.kind for p in w.p]
    ok &= _check(k == ["H", "L", "H", "L"], f"pivot kinds 1·2·3·4 = H,L,H,L (got {k})")
    ok &= _check(w.p[2].price > w.p[0].price, f"3>1 higher high ({w.p[2].price:.0f}>{w.p[0].price:.0f})")
    ok &= _check(w.epa_slope < 0, f"1-4 EPA slopes DOWN ({w.epa_slope:+.2f}/bar)")
    ok &= _check(w.line13_slope > 0, f"1-3 highs ascend ({w.line13_slope:+.2f}/bar)")
    ok &= _check(w.p[1].price < w.p[0].price, f"2<1 ({w.p[1].price:.0f}<{w.p[0].price:.0f})")
    ok &= _check(w.p[1].price < w.p[3].price < w.p[2].price,
                 f"4 between 2 and 3 — higher low ({w.p[1].price:.0f}<{w.p[3].price:.0f}<{w.p[2].price:.0f})")
    ok &= _check(w.leg12_price >= w.leg34_price,
                 f"leg 1-2 >= leg 3-4 ({w.leg12_price:.0f}>={w.leg34_price:.0f})")
    ok &= _check(w.p5 is not None and w.state == "CONFIRMED",
                 f"point 5 confirmed (overshoot @ {w.p5.price:.0f})" if w.p5 else "no point 5")
    print(f"    -> tier={w.tier} q={w.quality:.2f}")
    return ok


def test_paras_formula():
    print("\n[Fib-extension formula pin — Ramana's Fyers PARAS swings]")
    e12, e34, zones = wolfe.fib_zones(968.1, 1066.75, 1075.5, 1133)
    ok = _check(bool(zones) and abs(zones[0]["price"] - 1226.2) < 0.1,
                f"strong zone = 1226.2 (got {zones[0]['price'] if zones else None})")
    ok &= _check(zones[0]["r12"] == 2.618 and zones[0]["r34"] == 2.618,
                 f"from 2.618 x 2.618 overlap (got {zones[0]['r12']} x {zones[0]['r34']})")
    return ok


def test_reject_trend():
    print("\n[noise rejection]")
    high, low, close = _ohlc([(0, 100), (60, 160)])
    waves, _ = wolfe.detect_waves(high, low, close)
    return _check(len(waves) == 0, f"no waves in a clean trend (got {len(waves)})")


def main():
    results = [test_bull(), test_bear(), test_paras_formula(), test_reject_trend()]
    print("\n" + ("ALL PASS" if all(results) else "FAILURES PRESENT"))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
