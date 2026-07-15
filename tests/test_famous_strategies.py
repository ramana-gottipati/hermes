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


def test_in_page_links_use_the_canonical_nested_path():
    """D80 (BINDING): sub-pages live at /dash/<workspace>/<page>. Every link the Classic
    Screens page renders must use the canonical NESTED path derived from lens_registry
    (/dash/strategies/classics) — never a bare /dash/classics orphan URL, which throws the
    reader out of the Strategies workspace and breaks nav highlight/breadcrumbs.
    Regression gate: the first build shipped hardcoded flat links (Ramana caught it)."""
    import re

    from src.web import classics_view as cv

    assert cv._SELF == "/dash/strategies/classics", cv._SELF
    assert cv._FACTOR_LEAGUE == "/dash/strategies/factor-league", cv._FACTOR_LEAGUE
    html = cv.classics_page().body.decode() + cv.classics_page(s="coffeecan").body.decode()
    flat = sorted(set(re.findall(r"href=['\"](/dash/classics[^'\"]*)", html)))
    assert not flat, f"flat orphan link(s) — must be {cv._SELF}: {flat}"
    flat_fl = sorted(set(re.findall(r"href=['\"](/dash/factor-league[^'\"]*)", html)))
    assert not flat_fl, f"flat factor-league link(s) — must be {cv._FACTOR_LEAGUE}: {flat_fl}"


def test_none_fields_never_raise():
    # a universe where fundamentals came back None (laptop / missing archive) must degrade,
    # not crash — only the momentum-only strategy (lowvol) should still populate.
    rows = [{"symbol": f"S{i}", "vol_66": 0.2 + 0.001 * i, "mom12": 0.1,
             "range_pos_252": 0.9, "turnover_cr": 10.0} for i in range(30)]
    ros = fs.score_all(rows)
    assert len(ros["lowvol"]) == fs.TOPN
    assert ros["quality"] == [] and ros["garp"] == [] and ros["graham"] == []
