"""E-03 — insider disclosure-drift event study (post-public), PRE-REGISTERED 2026-07-07 (S83e).

The D89 footprint study proved the PRE-public window is structurally dead in India
(764/947 episodes had no tradeable pre-public window; SEBI PIT T+2). This study tests the
information that IS tradeable: the drift AFTER a conviction-buy cluster becomes public.

PRE-REGISTERED GATE (written before the run; result goes to the ledger win or lose):
  H:        conviction OPEN_MARKET_BUY episodes drift UP after their first public
            disclosure. Event t0 = the episode's first disclosure date (`disc`);
            entry = t0 + ENTRY_LAG sessions (pead convention, no leak).
  Readout:  episode-value quartiles (Σ value_rs, rupee-based per guardrail #5) →
            CAR22 / CAR60 vs Nifty 500 (pead_surface.reaction_row de-marketing),
            quarterly cohort-clustered t (evlib.cohort_t).
  PASS:     top-value-quartile CAR60 t_cohort ≥ 2 AND its observed mean clears the
            evlib date-shuffle placebo null p95 (n=200 shuffles, seed 42).
            → ships as a DESCRIPTIVE insider-drift lens/chip only.
  FAIL:     publish the null in docs/strategy-ledger.md; nothing ships.
  Book leg: NOT run here. Any tradeable wrapper inherits the F6 event-book priors
            (PEAD: every wrapper 0.02–0.10 net, hedged −0.58, vs bench 0.85) and
            requires its own pre-registration citing those numbers.
  Exclusions: episodes with Σ pct_equity ≥ 5% (control-change blocks — the VIPIND
            lesson); future-dated filings (typos) already guarded by the loader.
  Notes:    insider table is AUD-08 supersede-deduped at ingest (d0879bd). Episodes
            here are insider-only clusters (SAST arcs belong to E-04, separate study).

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.insider_drift --run          # writes out/insider_drift.json
  ... --selftest                                      # offline
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .common import RESEARCH_DB, load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "insider_drift.json")
PCT_CONTROL_CHANGE = 5.0          # exclude ≥5% episodes (control-change, not conviction)


def load_episodes(hcon) -> list[dict]:
    rows = hcon.execute(
        "SELECT symbol, transaction_dt, disclosure_dt, value_rs, pct_equity FROM insider_events "
        "WHERE signal_class='conviction' AND txn_class='OPEN_MARKET_BUY'").fetchall()
    eps = evlib.cluster_insider([tuple(r) for r in rows])
    return [e for e in eps if (e.get("pct") or 0.0) < PCT_CONTROL_CHANGE]


def quartile_split(eps: list[dict]) -> None:
    vals = sorted(e["value"] for e in eps)
    if not vals:
        return
    cuts = [vals[int(len(vals) * q)] for q in (0.25, 0.50, 0.75)]
    for e in eps:
        e["vq"] = sum(e["value"] >= c for c in cuts)      # 0..3, 3 = top-value quartile


def run() -> dict:
    hcon = main_conn()
    eps = load_episodes(hcon)
    quartile_split(eps)
    print(f"episodes: {len(eps)} conviction clusters (<{PCT_CONTROL_CHANGE}% equity)", flush=True)

    idx_dates, idx_map = evlib.index_levels(hcon)
    series: dict = {}
    events = []
    for e in eps:
        ss = series.setdefault(e["sym"], load_series(hcon, e["sym"]))
        if ss is None:
            continue
        r = reaction_row(ss, {"sym": e["sym"], "ptype": "I", "pend": e["start"],
                              "t0": e["disc"], "sue": 0.0}, idx_dates, idx_map)
        if r is None:
            continue
        events.append({**e, "t0": e["disc"], "car22": r["car22"], "car60": r["car60"]})

    out: dict = {"study": "E-03 insider disclosure drift (post-public)",
                 "n_episodes": len(eps), "n_usable": len(events),
                 "gate": "Q4 CAR60 t_cohort>=2 AND observed > placebo p95 (n=200, seed 42)"}
    for q in range(4):
        sel = [e for e in events if e.get("vq") == q]
        for h in ("car22", "car60"):
            st = evlib.cohort_t([(e["t0"], e[h]) for e in sel])
            out[f"Q{q + 1}_{h}"] = st
            if st.get("n"):
                print(f"  value-Q{q + 1} {h}: n={st['n']} mean={st['mean']*100:+.2f}% "
                      f"hit={st['hit']*100:.0f}% t={st['t']:.2f} t_cohort={st['t_cohort']:.2f}",
                      flush=True)
    allst = evlib.cohort_t([(e["t0"], e["car60"]) for e in events])
    out["ALL_car60"] = allst

    # placebo on the gated cohort (top-value quartile), same pipeline, shuffled t0
    top = [e for e in events if e.get("vq") == 3 and e["car60"] == e["car60"]]
    observed = float(np.mean([e["car60"] for e in top])) if top else float("nan")
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
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "I", "pend": e["start"],
                                  "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
            if r is not None and r["car60"] == r["car60"]:
                cars.append(r["car60"])
        if cars:
            null_means.append(float(np.mean(cars)))
        if (k + 1) % 50 == 0:
            print(f"  placebo {k + 1}/200", flush=True)
    hcon.close()
    out["placebo"] = evlib.placebo_stats(observed, null_means)

    q4 = out.get("Q4_car60", {})
    passed = (q4.get("t_cohort", 0) == q4.get("t_cohort", 0)          # not NaN
              and q4.get("t_cohort", 0) >= 2.0
              and out["placebo"].get("inflation_x") is not None
              and out["placebo"]["inflation_x"] > 1.0)
    out["verdict"] = "PASS-descriptive" if passed else "FAIL-null-published"
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    eps = [{"sym": "A", "value": v, "pct": 0.1, "start": "2024-01-01",
            "end": "2024-01-05", "disc": "2024-01-08"} for v in (1e5, 2e5, 3e5, 4e5)]
    quartile_split(eps)
    assert [e["vq"] for e in eps] == [0, 1, 2, 3]
    big = dict(eps[0]); big["pct"] = 9.0
    assert all(e["pct"] < PCT_CONTROL_CHANGE for e in eps)   # loader-side rule mirrored
    assert evlib.cohort_t([("2024-01-05", 0.01)] )["n"] == 1
    print("INSIDER_DRIFT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
