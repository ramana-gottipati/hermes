"""evlib — the ONE import surface for event studies (M-01) + the placebo-date harness (M-02).

M-01 shape decision (S83d): a FACADE, not a rewrite. `pead.py` stays the source of truth —
the nightly results_reactions snapshot (the war-room path, season-frozen) imports it
directly, so moving functions mid-season would put the Jul-09 surface at refactor risk for
zero analytical gain. New studies (E-03 / E-04 / E-06 / E-11 …) import THIS module; if
pead.py is ever split for real, only evlib's import lines move and no study changes.

M-02 placebo convention (pre-registered HERE, binding for every study that cites it):
  * Null = the SAME events with t0 reassigned to a uniformly-random ELIGIBLE session of the
    same symbol (eligibility = enough prior rows for features + enough forward rows for the
    horizon), run through the SAME pipeline, same cohort statistic.
  * Report four numbers: observed cohort mean · null mean · null p95 (one-sided) · the
    INFLATION ratio observed/null_p95. An observed effect inside the null band is dead on
    arrival regardless of its t-stat.
  * Deterministic: seed is a parameter (default 42); a PUBLISHED number needs n_shuffles ≥ 200.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.evlib --pead-placebo 200        # writes out/placebo_pead.json
  ... -m explosive_moves.evlib --selftest                # offline
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import numpy as np

from . import footprint, pead
from .common import LIQ_FLOOR, RESEARCH_DB, load_series, main_conn
from .pead_surface import reaction_row

OUT_DIR = os.path.join(os.path.dirname(__file__), "out")

# ── M-01 façade: the event-study API (source of truth unchanged) ──────────────
# time / alignment
plausible = pead.plausible
load_real_dates = pead.load_real_dates
assemble_events = pead.assemble_events
build_events = pead.build_events
cohort_of = pead.cohort_of
# surprise + features
sue_series = pead.sue_series
load_np = pead.load_np
tape_features = pead.tape_features
trailing_pct = pead.trailing_pct
# returns / benchmark / costs
car_path = pead.car_path
side_cost = pead.side_cost
index_levels = pead.index_levels
idx_level_asof = pead.idx_level_asof
# episode clustering + case/control machinery (footprint)
cluster_insider = footprint.cluster_insider
sast_episodes = footprint.sast_episodes
merge_episodes = footprint.merge_episodes
window_features = footprint.window_features
case_indices = footprint.case_indices
# M-03: the Deflated-Sharpe + PBO stages, one import away for every study/factory run
try:
    from .attribution import deflated_sharpe, pbo_cscv          # noqa: F401
except Exception:                                               # pragma: no cover
    deflated_sharpe = pbo_cscv = None                           # scipy-less env degrades


# ── shared cohort statistics (the bucket_table pattern, reusable) ─────────────

def cohort_t(pairs: list, min_per_cohort: int = 5, min_cohorts: int = 4) -> dict:
    """Cohort-clustered stats for [(t0, x), ...]: plain t + quarterly-cohort t
    (mean of cohort means over their dispersion — the pead bucket_table pattern,
    robust to same-quarter cross-correlation). NaNs dropped."""
    xs = np.array([x for _t, x in pairs if x == x], dtype=float)
    if len(xs) < 3:
        return {"n": int(len(xs))}
    t_plain = float(xs.mean() / (xs.std(ddof=1) / np.sqrt(len(xs))))
    cm: dict[str, list[float]] = {}
    for t0, x in pairs:
        if x == x:
            cm.setdefault(cohort_of(str(t0)), []).append(float(x))
    cmeans = np.array([np.mean(v) for v in cm.values() if len(v) >= min_per_cohort])
    t_c = (float(cmeans.mean() / (cmeans.std(ddof=1) / np.sqrt(len(cmeans))))
           if len(cmeans) > min_cohorts - 1 else float("nan"))
    return {"n": int(len(xs)), "mean": float(xs.mean()), "median": float(np.median(xs)),
            "hit": float((xs > 0).mean()), "t": t_plain, "t_cohort": t_c,
            "n_cohorts": int(len(cmeans))}


# ── M-02: placebo-date machinery ──────────────────────────────────────────────

def placebo_stats(observed: float, null_means: list) -> dict:
    """Pure summary of a placebo run: observed vs the null distribution of cohort means."""
    null = sorted(float(x) for x in null_means if x == x)
    if not null:
        return {"n_null": 0}
    arr = np.array(null)
    null_mean = float(arr.mean())
    null_p95 = float(np.quantile(arr, 0.95))
    emp_p = float((arr >= observed).mean())          # one-sided: chance the null beats us
    inflation = (observed / null_p95) if null_p95 > 0 else None
    return {"n_null": len(null), "observed": float(observed), "null_mean": null_mean,
            "null_p95": null_p95, "emp_p_one_sided": emp_p, "inflation_x": inflation}


def eligible_indices(ss, horizon: int) -> tuple[int, int]:
    """[lo, hi) index range of valid placebo t0 positions for one SymbolSeries."""
    lo = pead.MIN_PRIOR_ROWS
    hi = ss.n - pead.ENTRY_LAG - horizon - 2
    return lo, max(lo, hi)


def run_pead_placebo(n_shuffles: int = 200, seed: int = 42,
                     out_path: str | None = None) -> dict:
    """M-02 applied to the PEAD descriptive cell (SUE-Q5 × DELIV-T3, the +7.6%/60d claim).

    Same-pipeline null: every settled cell event gets a random eligible t0 in its own
    series, `pead_surface.reaction_row` recomputes CAR60 exactly as the real number was
    computed, and the cohort mean per shuffle forms the null distribution."""
    hcon = main_conn()
    import sqlite3
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    print("building settled population (real dates, no leak)...", flush=True)
    settled, idx_dates, idx_map = pead.build_events(hcon, rcon, progress=True)
    rcon.close()
    sues = np.array([e["sue"] for e in settled if e.get("sue") == e.get("sue")])
    dlvs = np.array([e["deliv_x"] for e in settled if e.get("deliv_x") == e.get("deliv_x")])
    sue_hi, dlv_hi = float(np.quantile(sues, 0.80)), float(np.quantile(dlvs, 2.0 / 3.0))
    cell = [e for e in settled
            if e.get("sue") is not None and e["sue"] >= sue_hi
            and e.get("deliv_x") is not None and e["deliv_x"] >= dlv_hi
            and e.get("car60") == e.get("car60")]
    observed = float(np.mean([e["car60"] for e in cell]))
    print(f"cell: n={len(cell)} observed mean CAR60 {observed*100:+.2f}% "
          f"(cuts sue>={sue_hi:.2f}, deliv>={dlv_hi:.2f})", flush=True)

    # cache series once per symbol in the cell
    series = {}
    for e in cell:
        if e["sym"] not in series:
            series[e["sym"]] = load_series(hcon, e["sym"])
    rng = random.Random(seed)
    null_means = []
    for k in range(n_shuffles):
        cars = []
        for e in cell:
            ss = series.get(e["sym"])
            if ss is None:
                continue
            lo, hi = eligible_indices(ss, 60)
            if hi <= lo:
                continue
            i0 = rng.randrange(lo, hi)
            r = reaction_row(ss, {"sym": e["sym"], "ptype": e["ptype"], "pend": e["pend"],
                                  "t0": ss.date[i0], "sue": e["sue"]}, idx_dates, idx_map)
            if r is not None and r["car60"] == r["car60"]:
                cars.append(r["car60"])
        if cars:
            null_means.append(float(np.mean(cars)))
        if (k + 1) % 25 == 0:
            print(f"  placebo shuffle {k + 1}/{n_shuffles}", flush=True)
    hcon.close()

    stats = placebo_stats(observed, null_means)
    stats.update({"study": "PEAD SUE-Q5 x DELIV-T3 CAR60", "n_events": len(cell),
                  "n_shuffles": n_shuffles, "seed": seed,
                  "sue_cut": sue_hi, "deliv_cut": dlv_hi,
                  "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")})
    out_path = out_path or os.path.join(OUT_DIR, "placebo_pead.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=1)
    print("placebo:", json.dumps(stats, indent=1), flush=True)
    return stats


# ── selftest (offline, no DB) ─────────────────────────────────────────────────

def selftest() -> None:
    # façade identity — the import surface IS pead/footprint, not a copy
    assert build_events is pead.build_events and car_path is pead.car_path
    assert window_features is footprint.window_features
    # cohort_t: 8 quarters x 6 events of +1% -> huge t, zero dispersion handled by ddof guard
    pairs = [(f"20{18 + q // 4}-{(q % 4) * 3 + 1:02d}-15", 0.01 + 0.001 * (i % 3))
             for q in range(8) for i in range(6)]
    ct = cohort_t(pairs)
    assert ct["n"] == 48 and ct["n_cohorts"] == 8 and ct["mean"] > 0 and ct["t_cohort"] > 2
    assert cohort_t([("2024-01-01", float("nan"))])["n"] == 0
    # placebo_stats arithmetic
    s = placebo_stats(0.08, [0.01, 0.02, -0.01, 0.00, 0.03])
    assert s["n_null"] == 5 and abs(s["observed"] - 0.08) < 1e-12
    assert s["emp_p_one_sided"] == 0.0 and s["inflation_x"] > 1.0
    s2 = placebo_stats(0.00, [0.01, 0.02, 0.03])
    assert s2["emp_p_one_sided"] == 1.0
    assert placebo_stats(0.05, [])["n_null"] == 0
    # eligibility window arithmetic on a stub
    class _SS:
        n = 500
    lo, hi = eligible_indices(_SS(), 60)
    assert lo == pead.MIN_PRIOR_ROWS and hi == 500 - pead.ENTRY_LAG - 62
    print("EVLIB selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--pead-placebo" in sys.argv:
        rest = [a for a in sys.argv[1:] if a.isdigit()]
        run_pead_placebo(n_shuffles=int(rest[0]) if rest else 200)
    else:
        print(__doc__)
