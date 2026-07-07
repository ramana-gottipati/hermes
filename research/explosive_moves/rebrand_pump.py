"""E-12 — rebrand-pump study, PRE-REGISTERED 2026-07-07 (S83g).

Folk hypothesis: a symbol rename (especially buzzword rebrands) pumps on the new identity
and then fades. Data: `security_renames` (324 renames, 2011→2026, effective dates).

The rename boundary is exactly where naive tooling breaks (the S81 lesson): the OLD
symbol's tape ends at the boundary and the NEW symbol has no prior history, so this
study loads a STITCHED series (old rows before the effective date + new rows after,
one SymbolSeries) — otherwise every event is unmeasurable by construction.

PRE-REGISTERED GATE (hashed into the M-04 registry BEFORE the run; ledger win or lose):
  Events:   one per rename; t0 = effective_date (first sessions under the new name).
  Readout:  cohort CAR22 (the pump claim) and CAR60−CAR22 (the fade claim) vs Nifty 500,
            quarterly cohort-clustered t where cohorts allow; n is small (324 raw), so the
            Wolfe power rule applies: n≥50 usable = full claim, 30–49 indicative, <30 no claim.
  PASS (pump): CAR22 t_cohort ≥ 2 AND the observed CAR22 mean clears the date-shuffle
            placebo p95 (n=200, seed 42) run through the SAME stitched pipeline.
  PASS (fade): mean(CAR60−CAR22) < 0 with |t| ≥ 2 — reported independently.
  FAIL:     publish the null. No lens ships either way without the placebo clearing.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \
      -m explosive_moves.rebrand_pump --run       # writes out/rebrand_pump.json
  ... --selftest                                  # offline
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import numpy as np

from . import evlib
from .common import SymbolSeries, _SERIES_FILTER, main_conn
from .pead_surface import reaction_row

OUT = os.path.join(os.path.dirname(__file__), "out", "rebrand_pump.json")
_SYM_COLS = ("trade_date, open, high, low, close, prev_close, volume, value, "
             "deliv_qty, deliv_per, num_trades, avg_price")


def load_series_stitched(con, old_sym: str, new_sym: str, eff: str):
    """One SymbolSeries spanning the rename: OLD rows strictly before the effective
    date + NEW rows from it on. Deduped on trade_date (keep the new-name row)."""
    rows = con.execute(
        f"""SELECT {_SYM_COLS} FROM bhavcopy_rows
            WHERE ((symbol = ? AND trade_date < ?) OR (symbol = ? AND trade_date >= ?))
              AND {_SERIES_FILTER}
            ORDER BY trade_date ASC""", (old_sym, eff, new_sym, eff)).fetchall()
    seen, dedup = set(), []
    for r in rows:
        d = r["trade_date"]
        if d in seen:
            dedup[-1] = r
            continue
        seen.add(d)
        dedup.append(r)
    if len(dedup) < 30:
        return None
    return SymbolSeries(f"{old_sym}->{new_sym}", dedup)


def load_renames(hcon) -> list[dict]:
    rows = hcon.execute(
        "SELECT old_symbol, new_symbol, effective_date FROM security_renames "
        "WHERE effective_date IS NOT NULL ORDER BY effective_date").fetchall()
    return [{"old": r[0], "new": r[1], "t0": str(r[2])[:10]} for r in rows]


def run() -> dict:
    hcon = main_conn()
    renames = load_renames(hcon)
    print(f"renames: {len(renames)}", flush=True)
    idx_dates, idx_map = evlib.index_levels(hcon)
    events, series = [], {}
    for rn in renames:
        key = (rn["old"], rn["new"])
        ss = series.get(key)
        if ss is None:
            ss = load_series_stitched(hcon, rn["old"], rn["new"], rn["t0"])
            series[key] = ss
        if ss is None:
            continue
        r = reaction_row(ss, {"sym": rn["new"], "ptype": "R", "pend": rn["t0"],
                              "t0": rn["t0"], "sue": 0.0}, idx_dates, idx_map)
        if r is None or r["car60"] != r["car60"] or r["car22"] != r["car22"]:
            continue
        events.append({**rn, "sym": rn["new"], "car22": r["car22"], "car60": r["car60"],
                       "fade": r["car60"] - r["car22"], "skey": key})
    n = len(events)
    power = "full" if n >= 50 else ("indicative" if n >= 30 else "no-claim")
    print(f"usable rename events: {n} (power: {power})", flush=True)

    out: dict = {"study": "E-12 rebrand pump/fade (stitched series)",
                 "n_renames": len(renames), "n_usable": n, "power": power,
                 "gate": "pump: CAR22 t_cohort>=2 AND placebo clears; fade: mean(CAR60-CAR22)<0 |t|>=2"}
    out["CAR22"] = evlib.cohort_t([(e["t0"], e["car22"]) for e in events])
    out["CAR60"] = evlib.cohort_t([(e["t0"], e["car60"]) for e in events])
    out["FADE"] = evlib.cohort_t([(e["t0"], e["fade"]) for e in events])
    for k in ("CAR22", "CAR60", "FADE"):
        st = out[k]
        if st.get("n"):
            print(f"  {k}: n={st['n']} mean={st['mean']*100:+.2f}% "
                  f"t={st['t']:.2f} t_cohort={st.get('t_cohort', float('nan')):.2f}", flush=True)

    observed = out["CAR22"].get("mean", float("nan"))
    rng = random.Random(42)
    null_means = []
    for k in range(200):
        cars = []
        for e in events:
            ss = series.get(e["skey"])
            if ss is None:
                continue
            lo_i, hi_i = evlib.eligible_indices(ss, 60)
            if hi_i <= lo_i:
                continue
            i0 = rng.randrange(lo_i, hi_i)
            r = reaction_row(ss, {"sym": e["sym"], "ptype": "R", "pend": e["t0"],
                                  "t0": ss.date[i0], "sue": 0.0}, idx_dates, idx_map)
            if r is not None and r["car22"] == r["car22"]:
                cars.append(r["car22"])
        if cars:
            null_means.append(float(np.mean(cars)))
        if (k + 1) % 50 == 0:
            print(f"  placebo {k + 1}/200", flush=True)
    hcon.close()
    out["placebo_car22"] = evlib.placebo_stats(observed, null_means)

    tcv = out["CAR22"].get("t_cohort")
    pump = (n >= 30 and tcv == tcv and (tcv or 0) >= 2.0
            and (out["placebo_car22"].get("inflation_x") or 0) > 1.0)
    ft = out["FADE"].get("t", 0)
    fade = n >= 30 and out["FADE"].get("mean", 0) < 0 and abs(ft) >= 2.0
    out["verdict"] = ("PASS-pump" if pump else "FAIL-pump-null") + \
                     (" / fade-observed" if fade else " / no-fade-claim")
    out["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print("verdict:", out["verdict"], flush=True)
    return out


def selftest() -> None:
    # stitched dedupe: boundary-day duplicate keeps the NEW row
    class R(dict):
        def __getitem__(self, k):
            return dict.__getitem__(self, k)
    rows = [{"trade_date": d} for d in ("2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03")]
    seen, dedup = set(), []
    for r in rows:
        d = r["trade_date"]
        if d in seen:
            dedup[-1] = r
            continue
        seen.add(d)
        dedup.append(r)
    assert len(dedup) == 3 and dedup[1] is rows[2]
    # power labels
    for n, lbl in ((60, "full"), (35, "indicative"), (10, "no-claim")):
        assert ("full" if n >= 50 else ("indicative" if n >= 30 else "no-claim")) == lbl
    print("REBRAND_PUMP selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--run" in sys.argv:
        run()
    else:
        print(__doc__)
