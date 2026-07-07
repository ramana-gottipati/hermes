"""Filing-latency tell — event study, PRE-REGISTERED 2026-07-07 (S83e).

Folk hypothesis (S79 idea queue): companies that file their results LATER than their own
historical norm are hiding something — the lateness itself is a tell, visible before any
number is read.

PRE-REGISTERED GATE (written before the run; result goes to the ledger win or lose):
  Population: the pead.build_events settled population (real BSE dates, no leak,
            liquidity/CA-gated, CAR60 finite).
  Treatment: latency = (t0 − period_end) days; per-(symbol, ptype) trailing MEDIAN
            over ≥3 PRIOR filings (strictly earlier period_end — no leak);
            late_score = latency − own trailing median. Events without 3 priors drop.
  Readout:  population quintiles of late_score → mean SUE (the surprise mix) and
            CAR60, quarterly cohort-clustered t (evlib.cohort_t) on Q5 − Q1.
  PASS:     |t_cohort| of the Q5−Q1 CAR60 gap ≥ 2 AND the observed |gap| exceeds the
            label-permutation p95 (500 permutations of late_score labels across
            events, seed 42 — the placebo variant for CROSS-SECTIONAL splits: the
            dates themselves are the treatment, so date-shuffling does not apply).
            → ships as a DESCRIPTIVE "files late vs own norm" flag on the war room.
  FAIL:     publish the null in docs/strategy-ledger.md; no flag ships.
  Book leg: NOT run — F3/F6 priors (calendar-time ranking closed; every PEAD wrapper
            0.02–0.10 net vs 0.85); would need its own pre-registration.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.filing_latency --run       # writes out/filing_latency.json
  ... --selftest                                    # offline
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
from datetime import date, datetime

import numpy as np

from . import evlib
from .common import RESEARCH_DB, main_conn

OUT = os.path.join(os.path.dirname(__file__), "out", "filing_latency.json")
MIN_PRIORS = 3


def late_scores(events: list[dict]) -> list[dict]:
    """Attach latency + no-leak trailing-median late_score; drop events w/o 3 priors."""
    by_key: dict = {}
    for e in events:
        try:
            lat = (date.fromisoformat(e["t0"][:10]) - date.fromisoformat(e["pend"][:10])).days
        except ValueError:
            continue
        e["latency"] = lat
        by_key.setdefault((e["sym"], e["ptype"]), []).append(e)
    out = []
    for evs in by_key.values():
        evs.sort(key=lambda x: x["pend"])
        for i, e in enumerate(evs):
            priors = [x["latency"] for x in evs[:i]]
            if len(priors) >= MIN_PRIORS:
                e["late_score"] = e["latency"] - float(np.median(priors))
                out.append(e)
    return out


def quintiles(events: list[dict], key: str = "late_score") -> None:
    vals = sorted(e[key] for e in events)
    cuts = [vals[int(len(vals) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
    for e in events:
        e["lq"] = sum(e[key] >= c for c in cuts)          # 0..4; 4 = latest vs own norm


def run() -> dict:
    hcon = main_conn()
    rcon = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True, timeout=30)
    print("building settled event population...", flush=True)
    settled, _idx_dates, _idx_map = evlib.build_events(hcon, rcon, progress=True)
    rcon.close()
    hcon.close()
    pool = [e for e in settled if e.get("car60") == e.get("car60")]
    scored = late_scores(pool)
    if not scored:
        raise SystemExit("no events with >=3 prior filings")
    quintiles(scored)
    print(f"scored events: {len(scored)} (of {len(pool)} settled)", flush=True)

    out: dict = {"study": "Filing-latency tell (late vs own norm)",
                 "n_scored": len(scored),
                 "gate": "|t_cohort(Q5-Q1 CAR60)|>=2 AND |gap| > label-permutation p95 (500, seed 42)"}
    for q in range(5):
        sel = [e for e in scored if e["lq"] == q]
        st = evlib.cohort_t([(e["t0"], e["car60"]) for e in sel])
        sues = np.array([e["sue"] for e in sel if e.get("sue") == e.get("sue")])
        st["mean_sue"] = float(sues.mean()) if len(sues) else None
        st["mean_late_days"] = float(np.mean([e["late_score"] for e in sel]))
        out[f"L{q + 1}"] = st
        if st.get("n"):
            print(f"  late-Q{q + 1}: n={st['n']} late={st['mean_late_days']:+.1f}d "
                  f"SUE={st['mean_sue']:+.2f} CAR60={st['mean']*100:+.2f}% "
                  f"t_cohort={st['t_cohort']:.2f}", flush=True)

    q5 = [e["car60"] for e in scored if e["lq"] == 4]
    q1 = [e["car60"] for e in scored if e["lq"] == 0]
    gap = float(np.mean(q5) - np.mean(q1))
    # gap t via cohort machinery on the signed union (Q5 as-is, Q1 negated)
    gap_pairs = ([(e["t0"], e["car60"]) for e in scored if e["lq"] == 4]
                 + [(e["t0"], -e["car60"]) for e in scored if e["lq"] == 0])
    # note: the union's mean equals (Q5 − Q1)/2-ish only when group sizes match;
    # `gap` (difference of means) is the headline, the union t is the clustered test
    gap_t = evlib.cohort_t(gap_pairs)
    out["gap_q5_minus_q1"] = {"gap": gap, "union_stats": gap_t}
    print(f"  GAP Q5−Q1 CAR60 = {gap*100:+.2f}% (union t_cohort={gap_t.get('t_cohort')})", flush=True)

    # label-permutation placebo: shuffle late_score labels, recompute the gap
    rng = random.Random(42)
    cars = [e["car60"] for e in scored]
    lqs = [e["lq"] for e in scored]
    null_gaps = []
    for _ in range(500):
        rng.shuffle(lqs)
        g5 = [c for c, q in zip(cars, lqs) if q == 4]
        g1 = [c for c, q in zip(cars, lqs) if q == 0]
        if g5 and g1:
            null_gaps.append(float(np.mean(g5) - np.mean(g1)))
    null_abs = sorted(abs(x) for x in null_gaps)
    p95 = null_abs[int(len(null_abs) * 0.95)] if null_abs else float("nan")
    out["permutation"] = {"n_perms": len(null_gaps), "abs_gap_p95": p95,
                          "observed_abs_gap": abs(gap),
                          "clears": bool(abs(gap) > p95)}

    tcv = gap_t.get("t_cohort")
    passed = (tcv == tcv and abs(tcv or 0) >= 2.0 and abs(gap) > p95)
    out["verdict"] = "PASS-descriptive" if passed else "FAIL-null-published"
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    evs = []
    for i, (pend, t0) in enumerate([("2022-03-31", "2022-05-15"), ("2022-06-30", "2022-08-14"),
                                    ("2022-09-30", "2022-11-14"), ("2022-12-31", "2023-02-13"),
                                    ("2023-03-31", "2023-06-29")]):   # last one files LATE (+90 vs ~45)
        evs.append({"sym": "A", "ptype": "Q", "pend": pend, "t0": t0, "sue": 0.0, "car60": 0.0})
    scored = late_scores(evs)
    assert len(scored) == 2                       # events 4 and 5 have >=3 priors
    late = scored[-1]
    assert late["pend"] == "2023-03-31" and late["late_score"] > 40   # ~+45d late vs norm
    quintiles(scored)
    assert all("lq" in e for e in scored)
    print("FILING_LATENCY selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
