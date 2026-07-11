"""Point-4 reconciliation (2026-07-11) — Ramana's rule: among waves sharing the same
1-2-3 skeleton, point 4 is the EXTREME high (BULL) / low (BEAR) of the rally into point 5,
NOT the tidiest fractal. Regression fixture for the TARSONS Feb-2022 case, where the later,
lower high (Feb-21 @ 674.5, a clean degree-5 fractal, §B total 13.00) wrongly out-ranked the
true apex (Feb-10 @ 698.8, a degree-2 fractal, §B total 12.67). Pure over Wave-shaped inputs
— no DB or market data needed."""
from types import SimpleNamespace as NS

from src.automation.wolfe import _reconcile_point4


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
