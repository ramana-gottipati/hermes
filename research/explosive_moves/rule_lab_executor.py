"""Rule-lab executor — the gauntlet orchestrator (D134 §4-H build step 2; research venv).

THE GATE (pre-registered; hash the RAW docstring — prereg.gate_hash discipline):

  A compiled RuleSpec (src/automation/rule_lab.py — the vocabulary, wall and verdict law live
  THERE; this module is an orchestrator, not new math) is evaluated by composing the existing
  evidence factory, stages 1-8 of docs/rule-lab-design.md §3:

    1 pre-register  rule_hash recorded in rule_lab_prereg BEFORE the run; first registration
                    wins; verify = recompute sha256(spec_text) == rule_hash.
    2 build tables  the factory.build_tables PIT pattern (same columns, same D5-F1 one-day
                    execution lag: enter i0+1, exit i1+1) + med_turn/atr columns + the
                    universe as a PIT liquidity-PERCENTILE band (never rupee constants).
    3 run           factory.run_strat (flat leg) + this module's cost-real leg; walk-forward
                    halves 2012-18 vs 2019-26 via factory.slice_stats — BOTH or it is noise.
    4 placebo       N random-selection books, same tables/TAKE/HOLD/filters, real cost;
                    evlib.placebo_stats(observed=net full-window Sharpe, null=their Sharpes).
                    Observed must beat null p95 — not merely beat zero.
    5 cost          cost_realism.side_cost per name-side (net reported FIRST; gross a footnote).
    6 capacity      cost_participation.side_costs at an AUM measurement grid (the existing
                    capacity_breakpoint grid); capacity = last AUM whose net Sharpe still
                    beats the bench. No stated capacity => not a result.
    7 benchmark     cost_realism.bench_buyhold (Nifty-500 buy-and-hold, net) on the SAME
                    rebalance dates; synthetic runs must inject bench_rets or the stage is
                    MISSING (a refusal, never a default).
    8 ledger        the verdict ships with rule_lab.ledger_entry — appended to canon only
                    after human approval in the Review Inbox (rule_lab_inbox producer).

  Missing stage = NO verdict (rule_lab.judge invariant 3): thin halves, an unbindable signal
  (value/quality family is v1-unbound: the factor-zoo citation IS the recorded answer), or an
  absent benchmark all refuse rather than partially rule.

Deviation from the design, documented: the prereg REGISTRY TABLE is a sibling
(rule_lab_prereg), not prereg_registry — prereg.verify() importlib-imports every registered
row as a study module, so arbitrary rule rows there would break --verify. The DISCIPLINE
(sha256, first-registration-wins, tamper-evident verify) is prereg.py's, reused verbatim via
prereg.gate_hash.

Run (VPS):  PYTHONPATH=/opt/hermes:/opt/hermes/research \
            /opt/hermes/.venv-research/bin/python -m explosive_moves.rule_lab_executor \
            --run "SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly"
CLI:        --selftest (synthetic, hermetic) | --run "RULE" [--shuffles N] | --grammar
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "/opt/hermes")            # on-box: reach src.automation.* (factor_zoo pattern)
sys.path.insert(0, "/opt/hermes/research")

from explosive_moves import factory
from explosive_moves.cost_realism import side_cost
from explosive_moves.cost_participation import side_costs
from explosive_moves.prereg import gate_hash  # noqa: F401  (the hashing discipline, reused)

from src.automation.rule_lab import (
    RuleSpec, RuleVerdict, UNIVERSES, FILTERS, SIGNALS, compile_rule, build_verdict,
)

RDB = "/opt/hermes/data/research.db"
REBAL_STEP = {"monthly": 22, "quarterly": 66}
PPY = {"monthly": 12, "quarterly": 4}
# AUM measurement GRID (₹cr) — the existing capacity_breakpoint scan grid: measurement
# resolution for the capacity read, not decision thresholds.
AUM_GRID_CR = (25, 50, 75, 100, 150, 200, 300, 500)
CR = 1e7

# v1 token -> factory callable (resolved here, DECLARED in rule_lab.SIGNALS; the value/quality
# family is deliberately absent = unbound, per the SIGNALS declaration).
_SIG_FN = {
    "mom6": factory.sig_mom6, "mom12": factory.sig_mom12, "riskadj": factory.sig_riskadj,
    "accel": factory.sig_accel, "lowvolmom": factory.sig_lowvolmom,
    "delivmom": factory.sig_delivmom, "qualmom": factory.sig_qualmom,
    "pullback": factory.sig_pullback,
}

_PREREG_DDL = """CREATE TABLE IF NOT EXISTS rule_lab_prereg(
    rule_hash     TEXT PRIMARY KEY,
    spec_text     TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    note          TEXT)"""


# ------------------------------------------------------------------ stage 1: pre-register
def register_rule(spec: RuleSpec, db_path: str | None = None, note: str = "") -> str:
    """First registration wins; re-running the same hash is recorded as a repeat.
    Returns the prereg_ref string the verdict carries (tamper-evident: verify_rule)."""
    import sqlite3
    con = sqlite3.connect(db_path or ":memory:", timeout=30)
    try:
        con.execute(_PREREG_DDL)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        cur = con.execute(
            "INSERT OR IGNORE INTO rule_lab_prereg VALUES (?,?,?,?)",
            (spec.rule_hash, spec.text, now, note or "registered before the run"))
        first = cur.rowcount == 1
        at = con.execute("SELECT registered_at FROM rule_lab_prereg WHERE rule_hash=?",
                         (spec.rule_hash,)).fetchone()[0]
        con.commit()
        durable = db_path is not None
        return "rule_lab_prereg:%s@%s(%s%s)" % (
            spec.rule_hash[:12], at, "first" if first else "repeat",
            "" if durable else ",non-durable")
    finally:
        con.close()


def verify_rule(db_path: str = RDB) -> int:
    """Tamper check: recompute sha256(spec_text) for every registered rule. Returns #bad."""
    import hashlib
    import sqlite3
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    bad = 0
    for h, text, at in con.execute(
            "SELECT rule_hash, spec_text, registered_at FROM rule_lab_prereg ORDER BY 3"):
        ok = hashlib.sha256(text.encode("utf-8")).hexdigest() == h
        bad += 0 if ok else 1
        print(("OK " if ok else "!! TAMPERED") + f" {h[:12]}... registered {at}")
    con.close()
    return bad


# ------------------------------------------------------------------ stage 2: build tables
def _band_for(spec: RuleSpec) -> tuple:
    lo, hi = UNIVERSES[spec.universe]["band"]
    if "min_liquidity" in spec.filters:
        lo = min(lo + 0.10, hi)                    # percentile tightening (FILTERS declaration)
    return lo, hi


def build_rule_tables(spec: RuleSpec, cache=None, cal=None):
    """factory.build_tables' PIT pattern + med_turn/atr columns + the percentile-band gate.

    Mirrors the audited factory loop byte-for-byte where it matters: features read at i0
    (knowable at that close), transactions at i0+1 / i1+1 (Codex D5-F1 — the same-bar peek
    fix). The universe gate is pctrank(med_turn) within each rebalance cross-section."""
    if cache is None:
        from explosive_moves.embase import load_symbol_cache
        from explosive_moves.metrics import index_series
        cache = load_symbol_cache()
        dts, _ = index_series("Nifty 50")
        cal = [d for d in dts if d >= "2012-06-01"]
    rebal = REBAL_STEP[spec.hold]
    ridx = list(range(0, len(cal), rebal))
    lo, hi = _band_for(spec)
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}
    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rows = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + rebal, len(ac) - 1))
            e0, e1 = i0 + 1, min(i1 + 1, len(ac) - 1)          # D5-F1 execution lag
            if e0 >= len(ac) or e1 <= e0 or not (ac[i0] > 0 and ac[e0] > 0 and ac[e1] > 0):
                continue
            rows.append((
                s,
                ac[i0] / ac[i0 - 126] - 1 if i0 >= 126 else np.nan,          # mom6
                ac[i0] / ac[i0 - 252] - 1 if i0 >= 252 else np.nan,          # mom12
                float(F["vol_66"][i0]), float(F["deliv_qty_trend"][i0]),
                float(F["ret_22d"][i0]), float(F["dist_high_22"][i0]),
                1.0 if F["close_vs_sma200"][i0] > 0 else 0.0,
                ac[i0] / ac[i0 - 1250] - 1 if i0 >= 1250 else np.nan,        # ext5y
                ac[e1] / ac[e0] - 1,                                          # fwd (lagged)
                float(mt[i0]) if np.isfinite(mt[i0]) else 0.0,               # med_turn
                float(F["atr14_pct"][i0]) if np.isfinite(F["atr14_pct"][i0]) else np.nan,
            ))
        if len(rows) < spec.take + 5:
            continue
        arr = list(zip(*rows))
        mt_arr = np.array(arr[10], dtype=float)
        tp = factory.pctrank(mt_arr)
        keep = (tp >= lo) & ((tp < hi) if hi < 1.0 else (tp <= 1.0))
        if keep.sum() < spec.take:
            continue
        k = np.where(keep)[0]
        tables.append({
            "d0": d0, "syms": [arr[0][i] for i in k],
            "mom6": np.array(arr[1], dtype=float)[k], "mom12": np.array(arr[2], dtype=float)[k],
            "vol": np.array(arr[3], dtype=float)[k], "deliv": np.array(arr[4], dtype=float)[k],
            "r22": np.array(arr[5], dtype=float)[k], "disthigh": np.array(arr[6], dtype=float)[k],
            "above200": np.array(arr[7], dtype=float)[k], "ext5y": np.array(arr[8], dtype=float)[k],
            "fwd": np.array(arr[9], dtype=float)[k], "mt": mt_arr[k],
            "atr": np.array(arr[11], dtype=float)[k],
        })
    return tables


# ------------------------------------------------------------------ stages 3/5/6: the book
def run_book(tables, sigfn, topn, val_guard, cost_mode="real", aum=None, rng=None):
    """One pass over the rebalance tables. cost_mode: gross | flat | real | participation.
    rng (np.random.Generator) replaces the signal with random scores — the placebo book.
    Returns (rets, dates, roster, ann_cost_pct_accumulator, turns)."""
    rets, dates, costs, turns = [], [], [], []
    held: dict = {}
    roster: list = []
    for t in tables:
        if rng is not None:
            score, emask = rng.random(len(t["fwd"])), None
        else:
            score, emask = sigfn(t)
        valid = ~np.isnan(score) & ~np.isnan(t["fwd"])
        if emask is not None:
            valid &= emask
        if val_guard:
            valid &= factory.not_extended(t)
        idx = np.where(valid)[0]
        if len(idx) == 0:
            rets.append(0.0); dates.append(t["d0"]); costs.append(0.0); turns.append(0.0)
            continue
        order = idx[np.argsort(score[idx])[::-1]][:topn]
        picks = {t["syms"][i]: {"mt": float(t["mt"][i]), "atr": float(t["atr"][i]),
                                "vol": float(t["vol"][i])} for i in order}
        gross = float(np.mean(t["fwd"][order]))
        new = set(picks) - set(held)
        exited = set(held) - set(picks)
        if cost_mode == "gross":
            c = 0.0
        elif cost_mode == "flat":
            c = factory.COST_PS * (len(new) + len(exited)) / max(len(picks), 1)
        elif cost_mode == "real":
            buy = sum(side_cost(picks[s]["mt"], picks[s]["atr"]) for s in new)
            sell = sum(side_cost(held[s]["mt"], held[s]["atr"]) for s in exited)
            c = (buy + sell) / max(len(picks), 1)
        elif cost_mode == "participation":
            order_value = float(aum) / max(topn, 1)
            buy = sum(sum(side_costs(picks[s]["mt"], picks[s]["vol"] if np.isfinite(picks[s]["vol"])
                                     else 0.02, order_value)[:2]) for s in new)
            sell = sum(sum(side_costs(held[s]["mt"], held[s]["vol"] if np.isfinite(held[s]["vol"])
                                      else 0.02, order_value)[:2]) for s in exited)
            c = (buy + sell) / max(len(picks), 1)
        else:
            raise ValueError(f"unknown cost_mode {cost_mode}")
        rets.append(gross - c); dates.append(t["d0"]); costs.append(c)
        turns.append((len(new) + len(exited)) / max(len(picks), 1))
        held = picks
        roster = list(picks)
    return np.array(rets), dates, roster, costs, turns


def _sharpe(rets, ppy) -> float:
    r = np.asarray(rets, float)
    if len(r) < 3 or r.std() == 0:
        return float("nan")
    return float(r.mean() / r.std() * np.sqrt(ppy))


# ------------------------------------------------------------------ the gauntlet
def run_gauntlet(spec: RuleSpec, tables=None, bench_rets=None, db_path: str | None = None,
                 n_shuffles: int = 120, seed: int = 42, env: str = "em_cache") -> RuleVerdict:
    """Stages 1-8. Every missing stage flows into judge() as a missing number -> NO-VERDICT."""
    ppy = PPY[spec.hold]
    prereg_ref = register_rule(spec, db_path=db_path)              # stage 1 — BEFORE the run
    provenance = {"module": "explosive_moves.rule_lab_executor", "env": env,
                  "seed": seed, "n_shuffles": n_shuffles,
                  "pit_membership": ("security_master.universe_on via the on-box cache build "
                                     "(D2-F1)" if env == "em_cache" else "synthetic fixture")
                  if "listed_on_asof" in spec.filters else "n/a (filter not requested)"}
    numbers: dict = {"bench_net": None}
    roster: list = []

    sigfn = _SIG_FN.get(spec.signal)
    if sigfn is None:                                              # value/quality family: v1-unbound
        numbers.update({k: None for k in ("net_sharpe", "half1", "half2",
                                          "placebo_p95", "observed")})
        provenance["unbound_signal"] = SIGNALS[spec.signal].get(
            "executor_v1", "unbound in executor v1")
        return build_verdict(spec, numbers, prereg_ref, provenance)

    if tables is None:                                             # stage 2
        tables = build_rule_tables(spec)
    provenance["n_rebal"] = len(tables)
    if tables:
        provenance["window"] = f"{tables[0]['d0']}..{tables[-1]['d0']}"

    val_guard = "not_extended" in spec.filters
    if len(tables) >= 8:
        # stage 3 — flat leg via factory.run_strat itself (reuse, not a copy)
        flat_rets, _ = factory.run_strat(tables, sigfn, spec.take, val_guard)
        numbers["flat_sharpe"] = _sharpe(flat_rets, ppy)
        # stage 5 — cost-real leg (net FIRST)
        rets, dates, roster, costs, turns = run_book(tables, sigfn, spec.take, val_guard, "real")
        gross_rets, _, _, _, _ = run_book(tables, sigfn, spec.take, val_guard, "gross")
        st = factory.eqstats(rets)
        numbers["net_sharpe"] = st["sharpe"] if st else None
        numbers["maxdd"] = st["maxdd"] if st else None
        numbers["gross_sharpe"] = _sharpe(gross_rets, ppy)
        numbers["ann_cost_pct"] = float(np.mean(costs)) * ppy * 100
        numbers["turnover"] = float(np.mean(turns))
        h1 = factory.slice_stats(rets, dates, "2012", "2018")
        h2 = factory.slice_stats(rets, dates, "2019", "2026")
        numbers["half1"] = h1["sharpe"] if h1 else None
        numbers["half2"] = h2["sharpe"] if h2 else None
        numbers["observed"] = numbers["net_sharpe"]
        # stage 4 — placebo (random-selection null, real cost, same tables)
        rng = np.random.default_rng(seed)
        nulls = []
        for _ in range(n_shuffles):
            nr, _, _, _, _ = run_book(tables, sigfn, spec.take, val_guard, "real", rng=rng)
            s = _sharpe(nr, ppy)
            if s == s:
                nulls.append(s)
        if nulls and numbers["observed"] is not None:
            from explosive_moves.evlib import placebo_stats
            ps = placebo_stats(float(numbers["observed"]), nulls)
            numbers["placebo_p95"] = ps.get("null_p95")
            numbers["emp_p"] = ps.get("emp_p_one_sided")
        else:
            numbers["placebo_p95"] = None
        # stage 7 — benchmark on the SAME dates
        if bench_rets is None and env == "em_cache":
            try:
                from explosive_moves.cost_realism import bench_buyhold
                numbers["bench_net"] = bench_buyhold(tables, ppy)["sharpe"]
            except Exception as e:                                  # noqa: BLE001
                provenance["bench_error"] = f"{type(e).__name__}: {e}"
        elif bench_rets is not None:
            b = np.asarray(bench_rets, float)[:len(rets)]
            numbers["bench_net"] = _sharpe(b, ppy)
            if len(b) == len(rets) and b.std() > 0:
                beta = float(np.cov(rets, b)[0, 1] / b.var())
                numbers["beta"] = beta
                numbers["alpha"] = float((rets.mean() - beta * b.mean()) * ppy)
        # stage 6 — capacity breakpoint (largest AUM still beating the bench, net)
        if numbers.get("bench_net") is not None:
            last_ok = 0.0
            for cr_aum in AUM_GRID_CR:
                pr, _, _, _, _ = run_book(tables, sigfn, spec.take, val_guard,
                                          "participation", aum=cr_aum * CR)
                if _sharpe(pr, ppy) > numbers["bench_net"]:
                    last_ok = cr_aum * CR
                else:
                    break
            numbers["capacity_inr"] = last_ok if last_ok > 0 else None
    else:
        numbers.update({k: None for k in ("net_sharpe", "half1", "half2",
                                          "placebo_p95", "observed")})
        provenance["thin_data"] = f"only {len(tables)} rebalances — refusing to rule"

    return build_verdict(spec, numbers, prereg_ref, provenance, roster=roster)  # stage 8 via inbox


# ------------------------------------------------------------------ synthetic fixture
def synthetic_tables(spec: RuleSpec, n_syms: int = 90, seed: int = 7,
                     start_year: int = 2012, end_year: int = 2026):
    """Deterministic synthetic rebalance tables + a synthetic benchmark return stream.

    Honest fixture, clearly labeled: persistent per-symbol drift (so momentum ranks carry
    mild signal), lognormal turnover (so the percentile bands and cost tiers bite), dates
    spanning BOTH walk-forward halves. Proves plumbing; never quoted as evidence."""
    rng = np.random.default_rng(seed)
    step_m = 1 if spec.hold == "monthly" else 3
    dates = []
    y, m = start_year, 6
    while y < end_year or (y == end_year and m <= 6):
        dates.append(f"{y:04d}-{m:02d}-28")
        m += step_m
        if m > 12:
            m -= 12; y += 1
    drift = rng.normal(0.008, 0.011, n_syms)                     # persistent cross-section
    mt_base = np.exp(rng.normal(17.5, 1.6, n_syms))              # turnover levels (wide spread)
    lo, hi = _band_for(spec)
    tables = []
    mom12_state = rng.normal(0.10, 0.25, n_syms)
    for d in dates:
        shock = rng.normal(0, 0.10, n_syms)
        fwd = drift * step_m + shock
        mom12_state = 0.8 * mom12_state + drift * 3 + rng.normal(0, 0.15, n_syms)
        mom6 = 0.55 * mom12_state + rng.normal(0, 0.08, n_syms)
        vol = np.abs(rng.normal(0.02, 0.006, n_syms)) + 0.008
        tp = factory.pctrank(mt_base * np.exp(rng.normal(0, 0.05, n_syms)))
        keep = (tp >= lo) & ((tp < hi) if hi < 1.0 else (tp <= 1.0))
        k = np.where(keep)[0]
        if len(k) < spec.take:
            continue
        tables.append({
            "d0": d, "syms": [f"SYN{i:03d}" for i in k],
            "mom6": mom6[k], "mom12": mom12_state[k], "vol": vol[k],
            "deliv": rng.normal(0, 1, len(k)), "r22": rng.normal(0.01, 0.04, len(k)),
            "disthigh": -np.abs(rng.normal(0.12, 0.08, len(k))),
            "above200": (rng.random(len(k)) > 0.35).astype(float),
            "ext5y": np.abs(rng.normal(0.8, 0.7, len(k))),
            "fwd": fwd[k], "mt": mt_base[k], "atr": np.abs(rng.normal(0.025, 0.008, len(k))),
        })
    ppy = PPY[spec.hold]
    bench = rng.normal(0.145 / ppy, 0.16 / np.sqrt(ppy), len(tables))
    return tables, bench


# ------------------------------------------------------------------ selftest / CLI
def _abridged(v: RuleVerdict) -> str:
    n = v.numbers
    f = lambda k: ("None" if n.get(k) is None or n.get(k) != n.get(k)
                   else f"{float(n[k]):.2f}")
    return ("verdict=%s qualifier=%s net=%s halves=%s/%s placebo_p95=%s bench=%s "
            "capacity=%s cites=%d prereg=%s" % (
                v.verdict, v.qualifier, f("net_sharpe"), f("half1"), f("half2"),
                f("placebo_p95"), f("bench_net"),
                ("None" if n.get("capacity_inr") in (None,) else
                 f"Rs{float(n['capacity_inr']) / CR:.0f}cr"),
                len(v.ledger_citations), v.prereg_ref.split("@")[0]))


def _selftest() -> int:
    # 1) full synthetic gauntlet on the demo rule — every stage populated, invariants hold
    spec = compile_rule("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly")
    tables, bench = synthetic_tables(spec)
    v = run_gauntlet(spec, tables=tables, bench_rets=bench, n_shuffles=40, env="synthetic")
    assert not v.verdict.startswith("NO-VERDICT"), v.verdict
    for k in ("net_sharpe", "half1", "half2", "placebo_p95", "observed", "bench_net"):
        assert v.numbers.get(k) is not None, f"stage number missing: {k}"
    assert v.roster and len(v.roster) <= spec.take
    print("demo rule:", _abridged(v))
    # 2) BOOK_YIELD-shaped rule — unbound signal => NO-VERDICT, wall citations stapled
    dead = compile_rule("SELECT liquid500 RANK BY bookyield TAKE 25 HOLD monthly")
    dv = run_gauntlet(dead, tables=[], env="synthetic")
    assert dv.verdict.startswith("NO-VERDICT") and len(dv.ledger_citations) == 2
    print("dead-shape rule:", _abridged(dv))
    # 3) thin data — refusal, never a partial verdict
    thin = run_gauntlet(spec, tables=tables[:4], bench_rets=bench[:4], env="synthetic")
    assert thin.verdict.startswith("NO-VERDICT(missing")
    # 4) prereg is tamper-evident and first-registration-wins
    ref1 = register_rule(spec)
    assert "first" in ref1
    print("RULE_LAB_EXECUTOR selftest OK (%d rebalances, %d placebo nulls)"
          % (len(tables), 40))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    elif "--run" in sys.argv:
        rule = sys.argv[sys.argv.index("--run") + 1]
        sh = int(sys.argv[sys.argv.index("--shuffles") + 1]) if "--shuffles" in sys.argv else 120
        spec = compile_rule(rule)
        v = run_gauntlet(spec, db_path=RDB, n_shuffles=sh)
        print(_abridged(v))
        for c in v.ledger_citations:
            print("BLOCKING:", c.encode("ascii", "backslashreplace").decode())
        if v.survivor_note:
            print(v.survivor_note.encode("ascii", "backslashreplace").decode())
    elif "--verify" in sys.argv:
        sys.exit(1 if verify_rule() else 0)
    else:
        print(__doc__)
