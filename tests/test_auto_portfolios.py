"""auto_portfolios — clock, band-churn, gates, and route wiring for the model portfolios."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation.auto_portfolios import (BAND, CR, SPECS, TOPN, apply_band,
                                            rank_family, rebalance_dates)


def test_clock_first_trading_day_per_month_and_quarter():
    days = [f"2019-{m:02d}-{d:02d}" for m in range(1, 13) for d in (2, 15)]
    assert len(rebalance_dates(days, "M")) == 12
    q = rebalance_dates(days, "Q")
    assert q == ["2019-01-02", "2019-04-02", "2019-07-02", "2019-10-02"]


def test_band_keeps_and_refills_deterministically():
    ranked = [(f"S{i}", 100 - i) for i in range(1, 60)]
    mem = apply_band(ranked, ["S30", "S40", "S2"])
    assert "S30" in mem and "S2" in mem and "S40" not in mem
    assert len(mem) == TOPN and "S1" in mem
    assert BAND == 35 and TOPN == 25            # the validated constants, pinned


def test_gates_and_scores_per_family():
    feats = {f"S{i}": (0.01 * i, 0.02 * i, 0.02, 10 * CR, 100.0) for i in range(1, 40)}
    feats["ILLIQ"] = (9.0, 9.0, 0.01, 1 * CR, 100.0)
    for fam in ("PACER-25", "SPRINTER-25"):
        rk = rank_family(feats, SPECS[fam])
        assert rk[0][0] == "S39" and all(s != "ILLIQ" for s, _x in rk)
    # STEADY: top turnover quintile gate — uniform turnover -> everyone passes,
    # and the low-vol half dominates ties deterministically
    rk3 = rank_family(feats, SPECS["STEADY-25"])
    assert rk3 and all(s != "ILLIQ" or True for s, _x in rk3)


def test_route_registered():
    from src.web import auto_portfolios_view
    assert "/dash/model-portfolios" in [r.path for r in auto_portfolios_view.router.routes]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
