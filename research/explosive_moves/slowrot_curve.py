"""slowrot_curve — equity-curve RE-RENDER of the recorded slow-rotation validation.

NOT a new study (no new hypothesis, no new gate): this re-runs the EXACT recorded
configuration of `cost_participation.py` (quarterly · large-cap gate GATE_PCTL=0.80 ·
LOWVOL_MOM 0.5/0.5 · TOPN=25 · BAND=35 · Almgren side_costs) — the run behind the
ledger's "net ~1.02 @ ₹50cr" verdict (§§ 2026-07-02 / 07-05c) and the /dash/
momentum-scan/slow surface — and dumps the per-quarter equity SERIES (net @₹50cr,
zero-cost gross, Nifty-500 buy&hold on the same rebalance dates) for charting.
The period loop is copied from cost_participation.run verbatim with curve capture;
any divergence from the recorded summary stats is a red flag, so both are printed.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.slowrot_curve      # -> out/slowrot_curve.json
"""
from __future__ import annotations

import json

import numpy as np

from . import cost_participation as cp


def run_curve(tables, aum):
    order_value = aum / cp.TOPN
    dates, rets, gross_rets = [], [], []
    held = {}
    for t in tables:
        ranked = sorted(t["g"], key=lambda x: -x["lowvolmom_sc"])
        if held:
            top_band = set(x["s"] for x in ranked[:cp.BAND])
            keep = [x for x in ranked if x["s"] in held and x["s"] in top_band][:cp.TOPN]
            ks = set(x["s"] for x in keep)
            picks = keep + [x for x in ranked if x["s"] not in ks][:cp.TOPN - len(keep)]
        else:
            picks = ranked[:cp.TOPN]
        byname = {x["s"]: x for x in picks}
        new = set(byname) - set(held)
        exited = set(held) - set(byname)
        gross = float(np.mean([x["fwd"] for x in picks]))
        side_total = 0.0
        for s in new:
            x = byname[s]
            fx, im, _ = cp.side_costs(x["mt"], x["sigma"], order_value)
            side_total += fx + im
        for s in exited:
            x = held[s]
            fx, im, _ = cp.side_costs(x["mt"], x["sigma"], order_value)
            side_total += fx + im
        dates.append(t["d0"])
        gross_rets.append(gross)
        rets.append(gross - side_total / cp.TOPN)
        held = byname
    return dates, np.array(rets), np.array(gross_rets)


def stats(rets):
    eq = np.cumprod(1 + rets)
    dd = eq / np.maximum.accumulate(eq) - 1
    return {"sharpe": round(float(rets.mean() / rets.std() * np.sqrt(cp.PPY)), 2),
            "cagr%": round((float(eq[-1]) ** (cp.PPY / len(rets)) - 1) * 100, 1),
            "maxdd%": round(float(dd.min()) * 100, 1),
            "total_x": round(float(eq[-1]), 2)}


def main():
    tables = cp.build()
    dates, net, gross = run_curve(tables, 50 * cp.CR)
    recorded = cp.run(tables, 50 * cp.CR)          # cross-check vs the frozen study loop
    bench = cp.bench_buyhold(tables)

    bdts, bcl = cp.index_series("Nifty 500")
    bmap = {d: float(bcl[i]) for i, d in enumerate(bdts)}
    ds = sorted(bmap)
    import bisect

    def on(d):
        i = bisect.bisect_right(ds, d) - 1
        return bmap[ds[i]] if i >= 0 else None

    b0 = on(dates[0])
    eq_b = [on(d) / b0 if on(d) else None for d in dates]
    out = {
        "dates": dates,
        "eq_net50": [round(float(x), 4) for x in np.cumprod(1 + net)],
        "eq_gross": [round(float(x), 4) for x in np.cumprod(1 + gross)],
        "eq_n500": [round(x, 4) if x else None for x in eq_b],
        "stats_net50": stats(net), "stats_gross": stats(gross),
        "stats_n500": {"sharpe": round(bench["sharpe"], 2),
                       "cagr%": round(bench["cagr"] * 100, 1),
                       "maxdd%": round(bench["maxdd"] * 100, 1)},
        "crosscheck_recorded_run": {"sharpe": round(recorded["sharpe"], 2),
                                    "cagr%": round(recorded["cagr"] * 100, 1),
                                    "ann_cost%": round(recorded["ann_cost_pct"], 1)},
    }
    cp_dir = __import__("pathlib").Path(__file__).resolve().parent / "out"
    cp_dir.mkdir(exist_ok=True)
    (cp_dir / "slowrot_curve.json").write_text(json.dumps(out))
    print(json.dumps({k: v for k, v in out.items() if k.startswith("stats")
                      or k == "crosscheck_recorded_run"}, indent=1))
    print(f"curve points: {len(dates)} quarters {dates[0]} -> {dates[-1]}")


if __name__ == "__main__":
    main()
