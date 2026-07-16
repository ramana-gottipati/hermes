"""Rule-lab executor gate (D134 §4-H) — the gauntlet plumbing on SYNTHETIC tables.

numpy-gated: `pytest.importorskip("numpy")` so the VPS MAIN venv (no numpy — the reason
src/ is stdlib-only) SKIPS this file instead of erroring; the research venv and the laptop
run it for real. The synthetic fixture proves ORCHESTRATION (stage wiring, refusals,
invariants), never evidence — the on-box E2E over the real em_cache is the integration
lane's step and is recorded as such in the executor docstring.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research"))

from explosive_moves import rule_lab_executor as rle          # noqa: E402
from explosive_moves import factory                           # noqa: E402
from src.automation import rule_lab as rl                     # noqa: E402

DEMO = "SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly"


@pytest.fixture(scope="module")
def demo_run():
    spec = rl.compile_rule(DEMO)
    tables, bench = rle.synthetic_tables(spec)
    v = rle.run_gauntlet(spec, tables=tables, bench_rets=bench,
                         n_shuffles=40, env="synthetic")
    return spec, tables, bench, v


# ────────────────────────────────────────────────── the full gauntlet, every stage
def test_gauntlet_populates_every_stage(demo_run):
    _spec, tables, _bench, v = demo_run
    assert not v.verdict.startswith("NO-VERDICT")
    n = v.numbers
    for k in ("net_retvol", "gross_retvol", "flat_retvol", "half1", "half2",
              "placebo_p95", "observed", "emp_p", "bench_net", "ann_cost_pct"):
        assert n.get(k) is not None and n[k] == n[k], f"stage number missing: {k}"
    assert n["observed"] == n["net_retvol"]              # the placebo comparand is NET
    assert v.provenance["n_rebal"] == len(tables)
    assert ".." in v.provenance["window"]


def test_net_is_below_gross_costs_are_real(demo_run):
    """Stage 5 contract: real per-name costs strictly drag the MEAN return (return/vol may
    move either way — cost drag also dampens variance — so mean is the honest check)."""
    spec, tables, _b, v = demo_run
    net, _, _, costs, _ = rle.run_book(tables, factory.sig_mom12, spec.take, True, "real")
    gross, _, _, _, _ = rle.run_book(tables, factory.sig_mom12, spec.take, True, "gross")
    assert net.mean() < gross.mean()
    assert sum(costs) > 0 and v.numbers["ann_cost_pct"] > 0


def test_roster_is_a_bounded_cohort_with_symbols(demo_run):
    spec, _t, _b, v = demo_run
    assert 0 < len(v.roster) <= spec.take
    assert all(s.startswith("SYN") for s in v.roster)


def test_verdict_invariants_hold_end_to_end(demo_run):
    _s, _t, _b, v = demo_run
    base = v.verdict.split("(", 1)[0]
    assert base in rl.VERDICTS and v.qualifier in rl.QUALIFIERS
    if base == "NEW-BENCHMARK":
        assert (v.numbers["half1"] > v.numbers["bench_net"]
                and v.numbers["half2"] > v.numbers["bench_net"]
                and v.numbers["capacity_inr"] > 0
                and v.numbers["observed"] > v.numbers["placebo_p95"])


# ─────────────────────────────────────────────────────────── refusals, never fakes
def test_unbound_value_signal_refuses_with_the_wall_stapled():
    dead = rl.compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    v = rle.run_gauntlet(dead, tables=[], env="synthetic")
    assert v.verdict.startswith("NO-VERDICT")
    assert len(v.ledger_citations) == 2                  # BOOK_YIELD + EARN_YIELD, verbatim
    assert "unbound" in v.provenance.get("unbound_signal", "")


def test_thin_data_refuses(demo_run):
    spec, tables, bench, _v = demo_run
    v = rle.run_gauntlet(spec, tables=tables[:4], bench_rets=bench[:4], env="synthetic")
    assert v.verdict.startswith("NO-VERDICT(missing")
    assert "thin_data" in v.provenance


def test_missing_benchmark_is_a_refusal_not_a_default(demo_run):
    spec, tables, _b, _v = demo_run
    v = rle.run_gauntlet(spec, tables=tables, bench_rets=None,
                         n_shuffles=10, env="synthetic")
    assert v.verdict.startswith("NO-VERDICT") and "bench_net" in v.verdict


def test_no_signal_fixture_fails_the_placebo_or_the_bench():
    """drift=0 synthetic: random-quality picks must never earn a decided PASS."""
    spec = rl.compile_rule("SELECT liquid500 RANK BY mom6 TAKE 25 HOLD monthly")
    tables, bench = rle.synthetic_tables(spec, seed=11)
    rng = np.random.default_rng(3)
    for t in tables:                                     # sever signal->fwd coupling
        rng.shuffle(t["fwd"])
    v = rle.run_gauntlet(spec, tables=tables, bench_rets=bench,
                         n_shuffles=40, env="synthetic")
    assert v.verdict.split("(")[0] in ("REJECTED", "WEAKER-THAN-BENCHMARK", "CONDITIONAL")
    assert v.verdict != "NEW-BENCHMARK"
    # and the momentum-monthly BLOCKING citation rode along regardless of outcome
    assert any("Momentum sold as a FUNDABLE" in c for c in v.ledger_citations)


# ───────────────────────────────────────────────────────── stage mechanics
def test_placebo_null_is_real_and_seeded(demo_run):
    spec, tables, bench, _v = demo_run
    a = rle.run_gauntlet(spec, tables=tables, bench_rets=bench, n_shuffles=15,
                         seed=5, env="synthetic")
    b = rle.run_gauntlet(spec, tables=tables, bench_rets=bench, n_shuffles=15,
                         seed=5, env="synthetic")
    assert a.numbers["placebo_p95"] == b.numbers["placebo_p95"]     # deterministic
    assert a.numbers["emp_p"] is not None


def test_flat_leg_is_factorys_own_run_strat(demo_run):
    """Stage 3 reuse: the flat return/vol must equal a direct factory.run_strat call."""
    spec, tables, _b, v = demo_run
    rets, _ = factory.run_strat(tables, factory.sig_mom12, spec.take, True)
    ppy = rle.PPY[spec.hold]
    assert abs(v.numbers["flat_retvol"] - rle._retvol(rets, ppy)) < 1e-12


def test_build_tables_applies_the_d5f1_execution_lag():
    """Features at i0, transactions at i0+1 / i1+1 — the same-bar peek stays fixed."""
    n = 300
    ac = np.linspace(100.0, 400.0, n) + np.sin(np.arange(n)) * 5
    dates = [f"2013-{1 + i // 250:02d}-{1 + i % 25:02d}" for i in range(n)]  # unique keys
    dates = [f"D{i:04d}" for i in range(n)]
    feats = {k: np.full(n, 0.02) for k in
             ("vol_66", "deliv_qty_trend", "ret_22d", "dist_high_22", "atr14_pct")}
    feats["close_vs_sma200"] = np.full(n, 1.0)
    cache = {f"S{j}": {"date": dates, "adj_close": ac + j, "med_turn": np.full(n, 1e7 * (j + 1)),
                       "feats": feats} for j in range(40)}
    spec = rl.spec_from_params("smallcap", "mom6", 5, "monthly")
    tables = rle.build_rule_tables(spec, cache=cache, cal=list(dates))
    assert tables, "handcrafted cache must yield tables"
    t = tables[0]
    i0 = 132                                             # first rebalance index >= 130: 6*22=132
    sym = t["syms"][0]
    j = int(sym[1:])
    a = ac + j
    expect_fwd = a[min(132 + 22, n - 1) + 1] / a[i0 + 1] - 1     # e0=i0+1, e1=i1+1
    assert abs(t["fwd"][0] - expect_fwd) < 1e-12


def test_universe_band_is_percentile_not_rupee(demo_run):
    """largecap (0.80,1.00) must select a strict liquidity SUBSET of liquid500 (0.60,1.00)."""
    big = rl.spec_from_params("liquid500", "mom12", 5, "quarterly")
    small = rl.spec_from_params("largecap", "mom12", 5, "quarterly")
    tb, _ = rle.synthetic_tables(big, seed=13)
    ts, _ = rle.synthetic_tables(small, seed=13)
    assert tb and ts
    assert set(ts[0]["syms"]) < set(tb[0]["syms"])
    assert min(ts[0]["mt"]) >= min(tb[0]["mt"])


def test_prereg_first_registration_wins_and_verifies(tmp_path):
    import sqlite3
    db = str(tmp_path / "research.db")
    spec = rl.compile_rule(DEMO)
    r1 = rle.register_rule(spec, db_path=db)
    r2 = rle.register_rule(spec, db_path=db)
    assert "(first)" in r1 and "(repeat)" in r2
    assert rle.verify_rule(db) == 0                      # tamper-evident: clean
    con = sqlite3.connect(db)
    con.execute("UPDATE rule_lab_prereg SET spec_text='tampered'")
    con.commit(); con.close()
    assert rle.verify_rule(db) == 1                      # ...and detected


def test_capacity_uses_the_measurement_grid(demo_run):
    _s, _t, _b, v = demo_run
    cap = v.numbers.get("capacity_inr")
    if cap is not None:
        assert cap / rle.CR in rle.AUM_GRID_CR


def test_executor_selftest_is_green(capsys):
    assert rle._selftest() == 0
