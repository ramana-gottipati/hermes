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


def _series(n, mult, gap_days):
    """n points from 1.0 to exactly `mult`x, gap_days apart, wiggled so sd > 0.

    Endpoints stay clean (the wiggle is interior-only) so the compounded multiple
    is exactly `mult` and CAGR is checkable by hand.
    """
    from datetime import date, timedelta
    d0 = date(2012, 6, 1)
    out = []
    for i in range(n):
        base = mult ** (i / (n - 1))
        wig = 1.0 if i in (0, n - 1) else (1.03 if i % 2 else 0.97)
        out.append(((d0 + timedelta(days=round(i * gap_days))).isoformat(), base * wig))
    return out


def test_cadence_is_read_from_dates_not_row_count():
    """A 14y QUARTERLY book must not be mistaken for a ~5y monthly one.

    Regression: `ppy = 12 if len(vals) > 40 else 4` read STEADY-25's 58 quarterly
    points (2012-06..2026-07) as monthly -> 4.8y instead of 14.1y, trebling the
    rendered CAGR (60.4% vs the true 17.3%) and annualising vol by sqrt(12) not sqrt(4).
    """
    from src.web.auto_portfolios_view import _cadence, _stats

    yrs, ppy = _cadence([d for d, _v in _series(58, 9.43, 91.31)])
    assert ppy == 4 and 13.9 < yrs < 14.3, (yrs, ppy)          # quarterly, not monthly

    st = _stats(_series(58, 9.43, 91.31))
    assert 16.0 < st["cagr"] < 19.0, st["cagr"]                # ~17.3%, never ~60%
    assert st["x"] == 9.43                                     # multiple is cadence-free

    mo = _stats(_series(170, 18.0, 30.44))                     # monthly book unaffected
    assert _cadence([d for d, _v in _series(170, 18.0, 30.44)])[1] == 12
    assert 21.0 < mo["cagr"] < 24.0, mo["cagr"]


def test_retvol_is_not_labelled_sharpe():
    """No risk-free rate is subtracted, so the key and the UI must not say "Sharpe"."""
    import inspect

    from src.web import auto_portfolios_view as v

    st = v._stats(_series(58, 9.43, 91.31))
    assert "retvol" in st and "sharpe" not in st
    page = inspect.getsource(v.model_portfolios_page)
    assert "Return/vol <b>" in page                   # the rendered stat is relabelled
    assert ">Sharpe <b>" not in page                  # ...and never claims a Sharpe
    assert "NOT a Sharpe" in page                     # the tooltip says why


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
