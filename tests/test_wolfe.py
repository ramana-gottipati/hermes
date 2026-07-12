"""Point-4 reconciliation (2026-07-11) — Ramana's rule: among waves sharing the same
1-2-3 skeleton, point 4 is the EXTREME high (BULL) / low (BEAR) of the rally into point 5,
NOT the tidiest fractal. Regression fixture for the TARSONS Feb-2022 case, where the later,
lower high (Feb-21 @ 674.5, a clean degree-5 fractal, §B total 13.00) wrongly out-ranked the
true apex (Feb-10 @ 698.8, a degree-2 fractal, §B total 12.67). Pure over Wave-shaped inputs
— no DB or market data needed."""
from types import SimpleNamespace as NS

from src.automation.wolfe import _reconcile_point4, _classify


def _p(idx, price):
    return NS(idx=idx, price=price)


def _wave(direction, p1, p2, p3, p4, total):
    return NS(direction=direction, p=[_p(*p1), _p(*p2), _p(*p3), _p(*p4)],
              score={"total": total})


def test_bull_keeps_higher_point4_over_cleaner_fractal():
    # the TARSONS case in miniature: the later, LOWER high carries the higher §B total
    # (tidier fractal) — reconciliation must still pick the earlier, HIGHER high as point 4.
    apex = _wave("BULL", (0, 631.5), (6, 720.7), (11, 627.0), (13, 698.8), 12.67)   # Feb-10 (true)
    later = _wave("BULL", (0, 631.5), (6, 720.7), (11, 627.0), (20, 674.5), 13.00)  # Feb-21 (higher Q)
    for order in ([apex, later], [later, apex]):        # iteration order must not matter
        out = _reconcile_point4(order)
        assert len(out) == 1
        assert out[0].p[3].idx == 13 and out[0].p[3].price == 698.8


def test_bear_keeps_lower_point4():
    apex = _wave("BEAR", (0, 100.0), (6, 60.0), (11, 110.0), (13, 70.0), 10.0)   # lower low = true apex
    later = _wave("BEAR", (0, 100.0), (6, 60.0), (11, 110.0), (20, 80.0), 12.0)  # higher low, higher Q
    out = _reconcile_point4([later, apex])
    assert len(out) == 1 and out[0].p[3].price == 70.0


def test_distinct_waves_are_both_kept():
    # different 1-2-3 skeletons must never be merged.
    a = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (13, 698.0), 12.0)
    b = _wave("BULL", (50, 500.0), (56, 600.0), (61, 490.0), (63, 560.0), 11.0)
    assert len(_reconcile_point4([a, b])) == 2


def test_equal_point4_price_breaks_deterministically():
    # equal point-4 price → higher §B total wins (then earliest bar); stable regardless of order.
    lowq = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (13, 698.0), 12.0)
    highq = _wave("BULL", (0, 631.0), (6, 720.0), (11, 627.0), (18, 698.0), 14.0)
    for order in ([lowq, highq], [highq, lowq]):
        out = _reconcile_point4(order)
        assert len(out) == 1 and out[0].score["total"] == 14.0


# --- convergence rule (2026-07-11): rails 1-3 and 2-4 must cross forward of point 4 ---
def _pv(idx, price, kind):
    return NS(idx=idx, price=price, kind=kind)


def test_crossing_admits_converging_bear_the_leg_ratio_killed():
    # rising wedge: leg 3-4 (10) out-prices leg 1-2 (6) -> the OLD cap rejected it; but rail 2-4
    # is steep (point 2 parked late) and out-angles rail 1-3 -> they meet forward -> now valid.
    a = _pv(0, 50.0, "H"); b = _pv(40, 44.0, "L"); c = _pv(50, 62.0, "H"); d = _pv(54, 52.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) == "BEAR"


def test_crossing_rejects_diverging_bear():
    # valid ordering, but rail 1-3 steeper than 2-4 -> they cross in the PAST -> diverge -> reject.
    a = _pv(0, 50.0, "H"); b = _pv(10, 44.0, "L"); c = _pv(50, 80.0, "H"); d = _pv(52, 46.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) is None


def test_crossing_rejects_parallel_rails():
    # rails exactly parallel (both slope 0.4) -> never intersect -> reject.
    a = _pv(0, 50.0, "H"); b = _pv(10, 45.0, "L"); c = _pv(50, 70.0, "H"); d = _pv(60, 65.0, "L")
    assert _classify(a, b, c, d, 0.2, 1.0) is None


def test_crossing_admits_converging_bull():
    # falling-wedge mirror: rails 1-3 (lows) & 2-4 (highs) both fall, 2-4 steeper down -> meet ahead.
    a = _pv(0, 60.0, "L"); b = _pv(40, 66.0, "H"); c = _pv(50, 48.0, "L"); d = _pv(54, 58.0, "H")
    assert _classify(a, b, c, d, 0.2, 1.0) == "BULL"
