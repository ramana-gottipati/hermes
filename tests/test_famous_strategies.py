"""Classic Screens compute-logic tests (S141) — pure ranking, no DB.

Mirrors src/automation/famous_strategies.selftest() as pytest cases so the scoring
gates for the famous public strategies stay green in CI.
"""
from src.automation import famous_strategies as fs


def _rows():
    return fs._synthetic()


def test_selftest_passes():
    # the module's own end-to-end assertion battery
    fs.selftest()


def test_every_runnable_strategy_scores():
    ros = fs.score_all(_rows())
    assert set(ros) == set(fs.RUNNABLE)
    # acquirers is reference-only and must NOT produce a roster
    assert "acquirers" not in ros
    assert fs.STRATEGIES["acquirers"][3] == "none"


def test_ranks_are_contiguous_and_bounded():
    for strat, picks in fs.score_all(_rows()).items():
        assert len(picks) <= fs.TOPN, strat
        assert [p[1] for p in picks] == list(range(1, len(picks) + 1)), strat


def test_lowvol_prefers_lowest_vol():
    ros = fs.score_all(_rows())
    tops = ros["lowvol"]
    vols = [p[3]["vol"] for p in tops]
    assert vols == sorted(vols), "low-vol roster must be ascending in realised vol"


def test_value_gates_hold():
    ros = fs.score_all(_rows())
    assert all(p[3]["pe"] <= 15 and p[3]["pb"] <= 1.5 for p in ros["graham"])
    assert all(p[3]["roce"] >= 15 and p[3]["sales_g5y"] >= 10 for p in ros["coffeecan"])
    assert all(0 < p[3]["peg"] <= 2 for p in ros["garp"])
    assert all(p[3]["f5"] >= 4 for p in ros["piotroski"])
    assert all(p[3]["range52"] >= 0.85 and p[3]["pg_ttm"] >= 25 for p in ros["canslim"])


def test_empty_universe_is_safe():
    ros = fs.score_all([])
    assert all(v == [] for v in ros.values())


def test_none_fields_never_raise():
    # a universe where fundamentals came back None (laptop / missing archive) must degrade,
    # not crash — only the momentum-only strategy (lowvol) should still populate.
    rows = [{"symbol": f"S{i}", "vol_66": 0.2 + 0.001 * i, "mom12": 0.1,
             "range_pos_252": 0.9, "turnover_cr": 10.0} for i in range(30)]
    ros = fs.score_all(rows)
    assert len(ros["lowvol"]) == fs.TOPN
    assert ros["quality"] == [] and ros["garp"] == [] and ros["graham"] == []
