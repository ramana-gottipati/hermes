"""Concall growth-intent walk-forward — PRE-REGISTERED 2026-07-07 (S83e).

The ledger-sanctioned next thread (ledger:194-204): the OLD month-granular panel showed
3m de-marketed tilts by guidance statement-type (debt_reduction +2.8%, volume +2.3%,
capex +1.5%, cost_savings −1.0%). Those numbers were computed WITHOUT real event dates.
The concall PIT clocks now exist (`3297a50`: concall_dt for 16.2K calls, 2015→2026), so
the claim can finally face a real-date, walk-forward test.

DESIGN CORRECTION recorded before the run: the treatment is the STATEMENT AT THE CALL —
so the cohort is "calls containing ≥1 guidance row of type X" (any status), NOT settled
rows only. The settled×dated cells for the old headline types are thin (volume 42,
new_product 16, debt_reduction <16 on real dates) — thinness is itself a finding and is
reported, not hidden.

PRE-REGISTERED GATE (result to the ledger win or lose):
  Events:   one per (call, statement_type present); t0 = concall_dt (the call IS the
            public event); entry = t0 + ENTRY_LAG sessions; CAR60 vs Nifty 500 via
            pead_surface.reaction_row (same no-leak plumbing as PEAD).
  Readout:  per type with n ≥ 100 dated events: mean CAR60, quarterly cohort-clustered
            t (evlib.cohort_t), and the same stat split at 2021-07-01 (halves).
  PASS (per type, descriptive lens ships): t_cohort ≥ 2 on the full sample AND the
            same SIGN of the mean in both halves AND (for the single largest passing
            type) the evlib date-shuffle placebo clears (n=200, seed 42).
  FAIL:     publish the null. The old panel tilts are then recorded as
            not-reproducible-on-real-dates.
  Book leg: NOT run — F3 (net momentum 0.09) + F6 (every event wrapper 0.02–0.10 vs
            0.85) priors; any book needs its own pre-registration citing them.
  Caveats:  multi-type calls put one call in several cohorts (non-independence across
            type cohorts — cohort-clustered t handles time clustering, not cross-type
            overlap; stated on any surface). `commitment_strength`/`speaker_role`/
            `is_qa` are 100% NULL (postmortem) and are NOT used.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.concall_intent --run       # writes out/concall_intent.json
  ... --selftest                                    # offline
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .common import load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "concall_intent.json")
MIN_N = 100
HALF_SPLIT = "2021-07-01"


def load_call_types(hcon) -> list[dict]:
    """One row per (dated call, statement_type present in its guidance)."""
    rows = hcon.execute(
        "SELECT DISTINCT c.symbol, c.concall_dt, g.statement_type "
        "FROM concalls c JOIN concall_guidance g "
        "  ON g.symbol = c.symbol AND g.source_period = c.period_label "
        "WHERE c.concall_dt IS NOT NULL AND g.statement_type IS NOT NULL").fetchall()
    return [{"sym": r[0], "t0": str(r[1])[:10], "stype": r[2]} for r in rows]


def run() -> dict:
    hcon = main_conn()
    calls = load_call_types(hcon)
    print(f"(call, type) events: {len(calls)}", flush=True)
    idx_dates, idx_map = evlib.index_levels(hcon)
    series: dict = {}
    events = []
    for c in calls:
        ss = series.setdefault(c["sym"], load_series(hcon, c["sym"]))
        if ss is None:
            continue
        r = reaction_row(ss, {"sym": c["sym"], "ptype": "C", "pend": c["t0"],
                              "t0": c["t0"], "sue": 0.0}, idx_dates, idx_map)
        if r is None or r["car60"] != r["car60"]:
            continue
        events.append({**c, "car60": r["car60"]})
    print(f"usable settled events: {len(events)}", flush=True)

    out: dict = {"study": "Concall growth-intent walk-forward (real call dates)",
                 "n_events": len(events),
                 "gate": "per-type t_cohort>=2 full-sample AND same-sign halves AND placebo "
                         "clears on the largest passing type (n=200, seed 42)"}
    by_type: dict = {}
    for e in events:
        by_type.setdefault(e["stype"], []).append(e)
    passing = []
    for stype, evs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        if len(evs) < MIN_N:
            out[f"type_{stype}"] = {"n": len(evs), "note": "below MIN_N — reported, not gated"}
            continue
        full = evlib.cohort_t([(e["t0"], e["car60"]) for e in evs])
        h1 = evlib.cohort_t([(e["t0"], e["car60"]) for e in evs if e["t0"] < HALF_SPLIT])
        h2 = evlib.cohort_t([(e["t0"], e["car60"]) for e in evs if e["t0"] >= HALF_SPLIT])
        same_sign = (h1.get("mean") is not None and h2.get("mean") is not None
                     and (h1["mean"] > 0) == (h2["mean"] > 0))
        rec = {"full": full, "h1": h1, "h2": h2, "same_sign_halves": bool(same_sign)}
        tcv = full.get("t_cohort")
        if tcv == tcv and (tcv or 0) >= 2.0 and same_sign:
            passing.append((stype, len(evs)))
            rec["gate_full_and_halves"] = "PASS"
        else:
            rec["gate_full_and_halves"] = "fail"
        out[f"type_{stype}"] = rec
        print(f"  {stype:<16} n={full.get('n', 0):>5} mean={100*(full.get('mean') or 0):+.2f}% "
              f"t_cohort={full.get('t_cohort', float('nan')):.2f} "
              f"halves {100*(h1.get('mean') or 0):+.2f}/{100*(h2.get('mean') or 0):+.2f} "
              f"-> {rec['gate_full_and_halves']}", flush=True)

    # placebo on the largest type that passed full+halves (if any)
    if passing:
        stype = max(passing, key=lambda x: x[1])[0]
        top = [e for e in by_type[stype]]
        observed = float(np.mean([e["car60"] for e in top]))
        rng = random.Random(42)
        null_means = []
        for k in range(200):
            cars = []
            for e in top:
                ss = series.get(e["sym"])
                if ss is None:
                    continue
                lo, hi = evlib.eligible_indices(ss, 60)
                if hi <= lo:
                    continue
                i0 = rng.randrange(lo, hi)
                r = reaction_row(ss, {"sym": e["sym"], "ptype": "C", "pend": e["t0"],
                                      "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
                if r is not None and r["car60"] == r["car60"]:
                    cars.append(r["car60"])
            if cars:
                null_means.append(float(np.mean(cars)))
            if (k + 1) % 50 == 0:
                print(f"  placebo {k + 1}/200 ({stype})", flush=True)
        out["placebo"] = {"type": stype, **evlib.placebo_stats(observed, null_means)}
        cleared = (out["placebo"].get("inflation_x") or 0) > 1.0
        out["verdict"] = ("PASS-descriptive" if cleared else "FAIL-null-published")
        out["passing_types_pre_placebo"] = [s for s, _n in passing]
    else:
        out["verdict"] = "FAIL-null-published"
        out["passing_types_pre_placebo"] = []
    hcon.close()

    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    # gate arithmetic: same-sign halves detection
    evs = ([{"t0": f"2019-{m:02d}-15", "car60": 0.01} for m in range(1, 13)]
           + [{"t0": f"2023-{m:02d}-15", "car60": 0.02} for m in range(1, 13)])
    h1 = evlib.cohort_t([(e["t0"], e["car60"]) for e in evs if e["t0"] < HALF_SPLIT])
    h2 = evlib.cohort_t([(e["t0"], e["car60"]) for e in evs if e["t0"] >= HALF_SPLIT])
    assert h1["mean"] > 0 and h2["mean"] > 0
    assert (h1["mean"] > 0) == (h2["mean"] > 0)
    print("CONCALL_INTENT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
