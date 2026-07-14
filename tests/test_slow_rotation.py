"""slow_rotation — the quarterly LOWVOL_MOM anchor: rule math + child-route wiring.

Pins the validated rule's mechanics (strategy-ledger 2026-07-02/05c): the top-quintile
turnover gate, the LOWVOL_MOM percentile blend, the keep-while-≤35 hold band, and the
calendar-quarter clock — plus that the view actually registers as a declared child on
the momentum router (the append-only EOF import must never be dropped).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation.slow_rotation import (BAND, TOPN, _qkey, gate_and_rank,
                                          pctrank, rebalance)


def test_pctrank_ties_and_ends():
    pr = pctrank([1.0, 2.0, 2.0, 3.0])
    assert pr[0] == 0.0 and pr[3] == 1.0
    assert abs(pr[1] - 0.5) < 1e-9 and abs(pr[2] - 0.5) < 1e-9


def test_gate_is_top_turnover_quintile_and_score_orders():
    rows = [{"symbol": f"S{i}", "mom6": 0.01 * i, "vol_66": 0.05 - 0.0003 * i,
             "turnover_cr": float(i)} for i in range(1, 101)]
    ranked = gate_and_rank(rows)
    assert all(r["turnover_cr"] >= 80.0 for r in ranked)
    # highest momentum + lowest vol in the gated set must rank first
    assert ranked[0]["symbol"] == "S100" and ranked[0]["rank"] == 1


def test_hold_band_keeps_slippers_and_fills_from_top():
    ranked = [{"symbol": f"R{i}", "rank": i, "score": 1.0 / i} for i in range(1, 60)]
    prev = ["R30", "R40", "R2"]
    holds, entered, exited = rebalance(ranked, prev)
    assert "R30" in holds and "R2" in holds        # inside the band -> kept
    assert "R40" in exited                          # outside the band -> dropped
    assert len(holds) + len(entered) == TOPN
    assert entered[0] == "R1"
    assert BAND > TOPN                              # the band is genuinely wider


def test_quarter_clock():
    assert _qkey("2026-01-15") == _qkey("2026-03-31")
    assert _qkey("2026-03-31") != _qkey("2026-04-01")
    assert _qkey("2026-10-01") != _qkey("2026-09-30")


def test_child_route_registered_on_momentum_router():
    from src.web import momentum_view
    paths = [r.path for r in momentum_view.router.routes]
    assert "/dash/momentum-scan" in paths
    assert "/dash/momentum-scan/slow" in paths


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
