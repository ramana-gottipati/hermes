"""factor_league — roster math, churn semantics, and the league page's honesty pins."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation.factor_league import MIN_TURN_CR, TOPN, rosters


def _rows():
    rows = [{"symbol": f"S{i}", "mom6": 0.01 * i, "mom12": 0.02 * (100 - i),
             "vol_66": 0.02, "riskadj": float(i), "turnover_cr": 10.0}
            for i in range(1, 61)]
    rows.append({"symbol": "ILLIQ", "mom6": 9, "mom12": 9, "vol_66": 0.01,
                 "riskadj": 999.0, "turnover_cr": MIN_TURN_CR - 1})
    return rows


def test_rosters_exact_formulas_and_gate():
    ros = rosters(_rows())
    assert len(ros["PACER"]) == TOPN and len(ros["SPRINTER"]) == TOPN
    assert ros["PACER"][0][0] == "S60"          # top riskadj wins PACER
    assert ros["SPRINTER"][0][0] == "S1"        # top mom12 wins SPRINTER
    assert all(s != "ILLIQ" for s, _r, _sc in ros["PACER"])   # ₹5cr gate held
    assert [rk for _s, rk, _sc in ros["SPRINTER"]] == list(range(1, TOPN + 1))


def test_league_table_matches_frozen_ledger_numbers():
    from src.web.factor_league_view import _LEAGUE
    by = {fam: (sh, status) for _n, fam, sh, _c, _d, _note, status, _rk in [
        (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in _LEAGUE]}
    # champion + hurdle pins (any drift from the ledger fails loudly)
    steady = [r for r in _LEAGUE if r[0] == "STEADY-25"][0]
    assert steady[6] == "champion" and "1.02" in steady[5]
    bench = [r for r in _LEAGUE if r[0] == "Nifty 500"][0]
    assert bench[2] == 0.89
    pacer = [r for r in _LEAGUE if r[0] == "PACER-25"][0]
    assert pacer[2] == 1.13
    reject = [r for r in _LEAGUE if "book yield" in r[1]][0]
    assert reject[6] == "reject"


def test_route_registered():
    from src.web import factor_league_view
    assert "/dash/factor-league" in [r.path for r in factor_league_view.router.routes]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
