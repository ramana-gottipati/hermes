"""E-11 — dividend-surprise drift, PRE-REGISTERED 2026-07-07 (S83g).

Data: the resurrected `corporate_actions` DIVIDEND stream (22,561 rows, 2004→2026) with
per-share amounts parsed from the details text ("Dividend Rs.1.50 Per Share" …).

PRE-REGISTERED GATE (hashed into the M-04 registry BEFORE the run; ledger win or lose):
  Events:   one per (symbol, ex_date); amount = Σ parsed per-share dividends that day.
            surprise_ratio = amount ÷ trailing MEDIAN of the symbol's own prior parsed
            amounts (≥2 priors, strictly earlier ex_dates — no leak). Interim and final
            dividends are pooled (stated limitation: the ratio mixes cadences).
  Clock:    t0 = ex_date. PIT note: the ANNOUNCEMENT precedes ex-date by days-to-weeks,
            so the announcement pop is EXCLUDED by construction — this tests post-ex
            drift only, the conservative claim.
  Readout:  surprise-ratio quintiles → CAR22/CAR60 vs Nifty 500 (reaction_row), quarterly
            cohort-clustered t (evlib.cohort_t). HIKE (ratio ≥ 1.5) and CUT (≤ 0.5)
            cohorts reported alongside.
  PASS:     Q5 CAR60 t_cohort ≥ 2 AND the Q5 observed mean clears the evlib date-shuffle
            placebo p95 (n=200 shuffles, seed 42; placebo cohort subsampled to ≤1,000
            events for compute, stated). → ships as a descriptive dividend-surprise chip.
  FAIL:     publish the null. Book leg: NOT run (F3/F6 priors; own pre-registration needed).

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.dividend_drift --run     # writes out/dividend_drift.json
  ... --selftest                                  # offline
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .common import load_series, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "dividend_drift.json")
_AMT = re.compile(r"R[se]\.?\s*([0-9]+(?:\.[0-9]+)?)\s*/?-?\s*(?:Per\s+Share|Per\s+Equity)", re.I)
PLACEBO_CAP = 1000


def parse_amount(details: str) -> float | None:
    m = _AMT.search(details or "")
    return float(m.group(1)) if m else None


def load_events(hcon) -> list[dict]:
    """(symbol, ex_date) events with amount + no-leak surprise_ratio (needs ≥2 priors)."""
    raw = hcon.execute(
        "SELECT symbol, ex_date, details FROM corporate_actions "
        "WHERE action_type='DIVIDEND' AND ex_date IS NOT NULL ORDER BY symbol, ex_date").fetchall()
    per_day: dict = {}
    for sym, exd, det in raw:
        amt = parse_amount(det)
        if amt is None or amt <= 0:
            continue
        k = (sym, str(exd)[:10])
        per_day[k] = per_day.get(k, 0.0) + amt
    by_sym: dict = {}
    for (sym, exd), amt in sorted(per_day.items()):
        by_sym.setdefault(sym, []).append({"sym": sym, "t0": exd, "amount": amt})
    out = []
    for evs in by_sym.values():
        for i, e in enumerate(evs):
            priors = [x["amount"] for x in evs[:i]]
            if len(priors) >= 2:
                med = float(np.median(priors))
                if med > 0:
                    e["surprise_ratio"] = e["amount"] / med
                    out.append(e)
    return out


def quintiles(events: list[dict]) -> None:
    vals = sorted(e["surprise_ratio"] for e in events)
    cuts = [vals[int(len(vals) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
    for e in events:
        e["sq"] = sum(e["surprise_ratio"] >= c for c in cuts)


def run() -> dict:
    hcon = main_conn()
    events = load_events(hcon)
    print(f"dividend events with >=2 priors: {len(events)}", flush=True)
    idx_dates, idx_map = evlib.index_levels(hcon)
    series: dict = {}
    usable = []
    for e in events:
        ss = series.setdefault(e["sym"], load_series(hcon, e["sym"]))
        if ss is None:
            continue
        r = reaction_row(ss, {"sym": e["sym"], "ptype": "D", "pend": e["t0"],
                              "t0": e["t0"], "sue": 0.0}, idx_dates, idx_map)
        if r is None or r["car60"] != r["car60"]:
            continue
        usable.append({**e, "car22": r["car22"], "car60": r["car60"]})
    print(f"usable settled events: {len(usable)}", flush=True)
    quintiles(usable)

    out: dict = {"study": "E-11 dividend-surprise drift (post-ex)",
                 "n_events": len(events), "n_usable": len(usable),
                 "gate": "Q5 CAR60 t_cohort>=2 AND placebo clears (n=200, seed 42, cap 1000)"}
    for q in range(5):
        sel = [e for e in usable if e["sq"] == q]
        st = evlib.cohort_t([(e["t0"], e["car60"]) for e in sel])
        st["mean_ratio"] = float(np.mean([e["surprise_ratio"] for e in sel])) if sel else None
        out[f"S{q + 1}"] = st
        if st.get("n"):
            print(f"  surprise-Q{q + 1}: n={st['n']} ratio~{st['mean_ratio']:.2f} "
                  f"CAR60={st['mean']*100:+.2f}% t_cohort={st['t_cohort']:.2f}", flush=True)
    for name, lo, hi in (("HIKE", 1.5, float("inf")), ("CUT", 0.0, 0.5)):
        sel = [e for e in usable if lo <= e["surprise_ratio"] <= hi]
        out[name] = evlib.cohort_t([(e["t0"], e["car60"]) for e in sel])
        if out[name].get("n"):
            print(f"  {name}: n={out[name]['n']} CAR60={out[name]['mean']*100:+.2f}% "
                  f"t_cohort={out[name]['t_cohort']:.2f}", flush=True)

    top = [e for e in usable if e["sq"] == 4]
    rng = random.Random(42)
    if len(top) > PLACEBO_CAP:
        top = rng.sample(top, PLACEBO_CAP)
    observed = float(np.mean([e["car60"] for e in top])) if top else float("nan")
    null_means = []
    for k in range(200):
        cars = []
        for e in top:
            ss = series.get(e["sym"])
            if ss is None:
                continue
            lo_i, hi_i = evlib.eligible_indices(ss, 60)
            if hi_i <= lo_i:
                continue
            i0 = rng.randrange(lo_i, hi_i)
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "D", "pend": e["t0"],
                                  "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
            if r is not None and r["car60"] == r["car60"]:
                cars.append(r["car60"])
        if cars:
            null_means.append(float(np.mean(cars)))
        if (k + 1) % 50 == 0:
            print(f"  placebo {k + 1}/200", flush=True)
    hcon.close()
    out["placebo"] = evlib.placebo_stats(observed, null_means)

    q5 = out.get("S5", {})
    tcv = q5.get("t_cohort")
    passed = (tcv == tcv and (tcv or 0) >= 2.0
              and (out["placebo"].get("inflation_x") or 0) > 1.0)
    out["verdict"] = "PASS-descriptive" if passed else "FAIL-null-published"
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    assert parse_amount("Annual General Meeting And Dividend Re.1/- Per Share") == 1.0
    assert parse_amount("Dividend Rs.1.50 Per Share") == 1.5
    assert parse_amount("Dividend Rs 1.80 Per Share") == 1.8
    assert parse_amount("Dividend Re 0.50 Per Share") == 0.5
    assert parse_amount("Annual General Meeting") is None
    evs = [{"sym": "A", "t0": f"202{i}-01-05", "amount": a}
           for i, a in enumerate((1.0, 1.0, 2.0, 3.0))]
    # simulate load_events' prior logic on the amount stream
    priors_ok = []
    for i, e in enumerate(evs):
        priors = [x["amount"] for x in evs[:i]]
        if len(priors) >= 2:
            e["surprise_ratio"] = e["amount"] / float(np.median(priors))
            priors_ok.append(e)
    assert len(priors_ok) == 2 and priors_ok[0]["surprise_ratio"] == 2.0
    assert priors_ok[1]["surprise_ratio"] == 3.0
    quintiles(priors_ok + [dict(e, surprise_ratio=r) for e, r in
                           zip([evs[0]] * 3, (0.5, 0.9, 1.1))])
    print("DIVIDEND_DRIFT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
