"""COST-REALITY RE-CUT of the C-BLEND champion (pre-registered experiment #1).

WHY
---
The recorded internal champion is C-BLEND 50/50 (0.5*RISKADJ-pctile +
0.5*C(capital-allocation)-pctile) with net Sharpe 1.32 / MaxDD -28.2% /
Calmar 1.15 (strategy-ledger "Experiment 2026-07-03"). BUT that number was
computed under a FLAT cost model (overlay_experiment.run: COST_PS=0.3% per unit
of turnover, + a 1.5x stress proxy). It was NEVER run through the
participation-rate (Almgren sqrt-law) impact model in cost_participation.py, so
its FUNDABLE status is UNPROVEN. Separately cost_participation.py already showed
the quarterly large-cap LOWVOL_MOM corner nets ~1.02 Sharpe @ Rs50cr (beats
Nifty-500 B&H 0.89) and decays with AUM.

WHAT THIS DOES (and does NOT do)
--------------------------------
Re-costs the EXACT champion construction AS BUILT, swapping ONLY the cost model
to participation-impact, across AUM {25,50,100,200,500}cr. NOTHING about the
book shape changes: same MONTHLY rebalance, same relative liquidity gate
(LIQ_PCTL=0.60), same TOPN=25 equal-weight, same sel_c_blend selector, same PIT
C via attach_c. Read-only. Writes ONLY out/cblend_cost_recut.csv.

THREE BOOKS, each on its OWN native construction (NOT homogenised):
  (a) C-BLEND  = overlay_experiment.build_tables() + c_overlay.sel_c_blend (+ attach_c)   [MONTHLY]
  (b) RISKADJ  = overlay_experiment.build_tables() + c_overlay._ra core (sel_riskadj_rel) [MONTHLY]
  (c) LOWVOL_MOM = cost_participation.build()/run() — the KNOWN quarterly large-cap result [QUARTERLY]
      used AS A VALIDATION CROSS-CHECK (must reproduce ~1.02 Sharpe @ Rs50cr).

COST SWAP (the only thing that changes for books a/b)
-----------------------------------------------------
overlay_experiment.run charges  cost = COST_PS * cost_mult * turn   where
turn = (|new|+|exited|)/TOPN. We replace COST_PS*turn with cost_participation's
per-side impact: for each NEW entry charge one side, for each EXIT charge one
side, using side_costs(med_turn=x["mt"], sigma_daily=x["vol"], order_value=AUM/TOPN);
period cost = side_total/TOPN. This is byte-for-byte cost_participation.run's
accounting, applied to the champion's picks. med_turn = the same ADV (x["mt"])
build_tables already carries; sigma_daily = x["vol"] = vol_66 (66d daily-return
stdev), the SAME sigma cost_participation uses.

METRICS reuse factory.eqstats (TD_Y=12, monthly annualization) — identical to how
the champion's recorded 1.32 Sharpe was computed — so any delta is the cost model
ALONE, not an annualization change. LOWVOL_MOM uses cost_participation's own PPY=4
run() (quarterly), reported as its native cross-check.

HALVES: net Sharpe for C-BLEND @Rs50cr and @Rs100cr on H1 (2012-06..2018-12) and
H2 (2019-01..2026) separately. The champion must survive BOTH halves.

CAVEATS (printed): C coverage RAMPS (~3% early -> ~89% late), so the honest window
is H2; survivor-conditioned fundamentals; single 2012-26 path; monthly (books a/b)
vs quarterly (book c) turnover are NOT directly comparable in Rs terms.

Run (VPS, read-only):
  PYTHONPATH=/opt/hermes /opt/hermes/.venv-research/bin/python -m explosive_moves.cblend_cost_recut
Writes out/cblend_cost_recut.csv.
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/opt/hermes")
sys.path.insert(0, "/opt/hermes/research")

from explosive_moves.factory import eqstats            # noqa: E402  (TD_Y=12 monthly stats)
from explosive_moves import overlay_experiment as OX    # noqa: E402  (champion harness)
from explosive_moves import c_overlay as CO             # noqa: E402  (attach_c, sel_c_blend, _ra)
from explosive_moves import cost_participation as CP     # noqa: E402  (side_costs + LOWVOL_MOM build/run)

CR = 1e7
TOPN = OX.TOPN                                          # 25 — the champion's N (assert below)
PPY_M = 12                                              # books a/b are MONTHLY
AUM_LIST_CR = [25, 50, 100, 200, 500]

# Nifty-500 buy-&-hold hurdle (from the ledger; CP uses the same)
BENCH_SHARPE = CP.BENCH_SHARPE                          # 0.89
BENCH_CAGR = CP.BENCH_CAGR                              # 0.153

H1_END = "2018-12-31"
H2_START = "2019-01-01"


# --------------------------------------------------------------------------- #
#  Participation-cost runner for the MONTHLY champion books (a) and (b).       #
#  Mirrors overlay_experiment.run's gross+turnover bookkeeping EXACTLY, but    #
#  swaps the flat COST_PS*turn term for cost_participation.side_costs charged  #
#  one side per new entry + one side per exit, period cost = side_total/TOPN.  #
# --------------------------------------------------------------------------- #
def run_participation(tables, selector, aum):
    """Return (rets, dates, diag) for a monthly book at target `aum` (Rs) under
    participation-impact cost. `diag` collects turnover / participation / fill /
    ADV-of-picks for the reporting + capacity read."""
    order_value = aum / TOPN                             # equal-weight clip (Rs)
    rets, dates = [], []
    turns, costs, days, adv_of_picks = [], [], [], []
    held = {}                                            # s -> record (for exit-side cost)
    for t in tables:
        picks = selector(t)
        if not picks:
            rets.append(0.0)
            dates.append(t["d0"])
            held = {}
            continue
        byname = {p["s"]: p for p in picks}
        pset = set(byname)
        new = pset - set(held)
        exited = set(held) - pset

        gross = float(np.mean([p["fwd"] for p in picks]))

        # --- participation cost: one side on each new entry, one on each exit ---
        side_total = 0.0
        dd = []
        for s in new:
            x = byname[s]
            fx, im, dtf = CP.side_costs(x["mt"], x["vol"], order_value)   # x["vol"]=vol_66=sigma_daily
            side_total += fx + im
            dd.append(dtf)
        for s in exited:
            x = held[s]
            fx, im, dtf = CP.side_costs(x["mt"], x["vol"], order_value)
            side_total += fx + im
            dd.append(dtf)
        c = side_total / TOPN                            # cost as fraction of the whole book

        rets.append(gross - c)
        dates.append(t["d0"])
        costs.append(c)
        turns.append((len(new) + len(exited)) / TOPN)
        if dd:
            days.append(float(np.median(dd)))
        adv_of_picks += [p["mt"] for p in picks]
        held = byname

    diag = {
        "ann_cost_pct": float(np.mean(costs)) * PPY_M * 100 if costs else 0.0,
        "turn": float(np.mean(turns)) if turns else 0.0,
        "med_days_fill": float(np.median(days)) if days else 1.0,
        "adv_of_picks": adv_of_picks,
        "order_value": order_value,
    }
    return np.array(rets), dates, diag


def _cap_and_part(diag):
    """Capacity (AUM where median clip = POV_CAP*ADV) + median participation now."""
    adv = diag["adv_of_picks"]
    adv_med = float(np.median(adv)) if adv else 0.0
    cap_med_cr = (CP.POV_CAP * adv_med * TOPN) / CR
    med_part = (diag["order_value"] / adv_med * 100) if adv_med > 0 else float("inf")
    return cap_med_cr, med_part


def _metrics_row(tag, aum_cr, rets, dates, diag):
    """Assemble the reporting dict for one (monthly book, AUM)."""
    full = eqstats(rets)
    cap_med_cr, med_part = _cap_and_part(diag)
    sh = full["sharpe"] if full else 0.0
    cg = full["cagr"] if full else 0.0
    return {
        "strategy": tag, "aum_cr": aum_cr,
        "sharpe": sh, "cagr": cg,
        "maxdd": full["maxdd"] if full else 0.0,
        "calmar": full["calmar"] if full else 0.0,
        "ann_cost_pct": diag["ann_cost_pct"], "turn": diag["turn"],
        "med_part_pct": med_part, "med_days_fill": diag["med_days_fill"],
        "cap_med_cr": cap_med_cr,
        "beats_index": bool(sh > BENCH_SHARPE and cg > BENCH_CAGR),
    }


def _half_sharpe(rets, dates, lo=None, hi=None):
    rets = np.asarray(rets, float)
    if lo is not None:
        m = np.array([d >= lo for d in dates])
    else:
        m = np.array([d <= hi for d in dates])
    sub = rets[m]
    st = eqstats(sub)
    return (st["sharpe"] if st else None), int(m.sum())


# --------------------------------------------------------------------------- #
#  LOWVOL_MOM cross-check row (native quarterly cost_participation.run).        #
# --------------------------------------------------------------------------- #
def _lowvol_row(cp_tables, aum_cr):
    s = CP.run(cp_tables, aum_cr * CR)                   # PPY=4 inside
    return {
        "strategy": "LOWVOL_MOM(qtr,largecap)", "aum_cr": aum_cr,
        "sharpe": s["sharpe"], "cagr": s["cagr"], "maxdd": s["maxdd"],
        "calmar": (s["cagr"] / abs(s["maxdd"])) if s["maxdd"] < 0 else 0.0,
        "ann_cost_pct": s["ann_cost_pct"], "turn": s["turn"],
        "med_part_pct": s["med_part_pct"], "med_days_fill": s["med_days_fill"],
        "cap_med_cr": s["cap_med_cr"], "beats_index": s["beats_index"],
    }


def main():
    assert TOPN == 25, f"champion TOPN drifted: {TOPN}"
    print("=" * 78)
    print("COST-REALITY RE-CUT of the C-BLEND champion (participation-impact cost)")
    print(f"  k={CP.K_IMPACT} POV_CAP={CP.POV_CAP:.0%} delay_k={CP.DELAY_K}  "
          f"impact=k*sigma*sqrt(order/ADV), cap {CP.POV_CAP:.0%} ADV/day")
    print(f"  hurdle = Nifty-500 B&H: Sharpe {BENCH_SHARPE}, CAGR {BENCH_CAGR*100:.1f}%")
    print("=" * 78, flush=True)

    # --- (1) build the champion tables ONCE (monthly, rel-gate) + attach PIT C ---
    print("\n[1/3] building champion tables (overlay_experiment.build_tables) ...", flush=True)
    tables = OX.build_tables()
    print(f"      {len(tables)} monthly rebalances; avg gated = "
          f"{np.mean([len(t['gated']) for t in tables]):.0f}", flush=True)
    print("[2/3] attaching PIT C (capital-allocation) via c_overlay.attach_c ...", flush=True)
    CO.attach_c(tables)   # prints its own coverage line (mean/min/max)

    # per-rebalance C coverage for the honesty note
    cov = []
    for t in tables:
        fin = np.array([np.isfinite(x.get("c_pr", np.nan)) for x in t["gated"]])
        cov.append(float(fin.mean()) if len(fin) else 0.0)
    cov = np.array(cov)
    h1_cov = cov[np.array([t["d0"] <= H1_END for t in tables])]
    h2_cov = cov[np.array([t["d0"] >= H2_START for t in tables])]

    # --- LOWVOL_MOM quarterly tables (native) for the cross-check ---
    print("[3/3] building LOWVOL_MOM quarterly large-cap tables "
          "(cost_participation.build) ...", flush=True)
    cp_tables = CP.build(rebal=CP.REBAL, gate_pctl=CP.GATE_PCTL)
    print(f"      {len(cp_tables)} quarterly rebalances\n", flush=True)

    # ------------------------------------------------------------------ AUM sweep
    books = [("C-BLEND(mo,50/50)", CO.sel_c_blend),
             ("RISKADJ(mo,core)", OX.sel_riskadj_rel)]
    rows = []
    # keep C-BLEND monthly rets by AUM for the halves table
    cblend_rets = {}

    for tag, sel in books:
        for aum_cr in AUM_LIST_CR:
            rets, dates, diag = run_participation(tables, sel, aum_cr * CR)
            rows.append(_metrics_row(tag, aum_cr, rets, dates, diag))
            if tag.startswith("C-BLEND"):
                cblend_rets[aum_cr] = (rets, dates)

    for aum_cr in AUM_LIST_CR:
        rows.append(_lowvol_row(cp_tables, aum_cr))

    # Nifty-500 B&H reference (quarterly path from CP.bench_buyhold; the ledger hurdle)
    bench = CP.bench_buyhold(cp_tables)

    # ------------------------------------------------------------------ print AUM table
    hdr = (f"{'strategy':22}{'AUM':>7}{'netShrp':>9}{'netCAGR':>9}{'maxDD':>8}"
           f"{'Clmr':>6}{'aCost%':>8}{'turn':>6}{'medPt%':>8}{'fill(d)':>8}"
           f"{'capCr':>8}{'>idx?':>7}")
    print("=" * len(hdr))
    print("AUM x METRICS  (net of participation-impact cost)")
    print("=" * len(hdr))
    print(hdr)

    def _prow(r):
        cap = r["cap_med_cr"]
        cap_s = "inf" if cap == float("inf") else f"{cap:.0f}"
        part = r["med_part_pct"]
        part_s = "inf" if part == float("inf") else f"{part:.1f}"
        print(f"{r['strategy']:22}{r['aum_cr']:>6}c{r['sharpe']:>9.2f}"
              f"{r['cagr']*100:>8.1f}%{r['maxdd']*100:>7.1f}%{r['calmar']:>6.2f}"
              f"{r['ann_cost_pct']:>7.1f}%{r['turn']:>6.2f}{part_s:>8}"
              f"{r['med_days_fill']:>8.1f}{cap_s:>8}"
              f"{('YES' if r['beats_index'] else 'no'):>7}")

    last_strat = None
    for r in rows:
        if last_strat is not None and r["strategy"] != last_strat:
            print("-" * len(hdr))
        _prow(r)
        last_strat = r["strategy"]
    print("-" * len(hdr))
    print(f"{'Nifty500 B&H':22}{'-':>7}{bench['sharpe']:>9.2f}{bench['cagr']*100:>8.1f}%"
          f"{bench['maxdd']*100:>7.1f}%{(bench['cagr']/abs(bench['maxdd'])):>6.2f}"
          f"{0.0:>7.1f}%{0.0:>6.2f}{'-':>8}{'-':>8}{'inf':>8}{'-':>7}")

    # ------------------------------------------------------------------ HALVES table
    print("\n" + "=" * 60)
    print("C-BLEND HALVES — net Sharpe by half (must survive BOTH)")
    print("=" * 60)
    print(f"{'AUM':>7}{'H1 2012-18':>13}{'H2 2019-26':>13}{'full':>9}")
    halves_rows = []
    for aum_cr in (50, 100):
        rets, dates = cblend_rets[aum_cr]
        h1, n1 = _half_sharpe(rets, dates, hi=H1_END)
        h2, n2 = _half_sharpe(rets, dates, lo=H2_START)
        full = eqstats(rets)
        fs = full["sharpe"] if full else float("nan")
        print(f"{aum_cr:>6}c{(h1 if h1 is not None else float('nan')):>13.2f}"
              f"{(h2 if h2 is not None else float('nan')):>13.2f}{fs:>9.2f}")
        halves_rows.append({"aum_cr": aum_cr, "h1_sharpe": h1, "h2_sharpe": h2,
                            "full_sharpe": fs, "h1_n": n1, "h2_n": n2})
    print(f"\n  C coverage: H1 mean {h1_cov.mean():.0%} (min {h1_cov.min():.0%}) | "
          f"H2 mean {h2_cov.mean():.0%} (min {h2_cov.min():.0%})")
    print("  -> honest window is H2; in H1 the C leg often defaults to 0.5 "
          "(=> C-BLEND ~ RISKADJ there).")

    # ------------------------------------------------------------------ write CSV
    out = os.path.join(os.path.dirname(__file__), "out", "cblend_cost_recut.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strategy", "aum_cr", "net_sharpe", "net_cagr_pct", "maxdd_pct",
                    "calmar", "ann_cost_pct", "avg_turnover", "med_participation_pct",
                    "med_days_to_fill", "cap_median_cr", "beats_index"])
        for r in rows:
            cap = r["cap_med_cr"]
            part = r["med_part_pct"]
            w.writerow([r["strategy"], r["aum_cr"], round(r["sharpe"], 2),
                        round(r["cagr"] * 100, 1), round(r["maxdd"] * 100, 1),
                        round(r["calmar"], 2), round(r["ann_cost_pct"], 1),
                        round(r["turn"], 2),
                        ("inf" if part == float("inf") else round(part, 1)),
                        round(r["med_days_fill"], 1),
                        ("inf" if cap == float("inf") else round(cap, 0)),
                        r["beats_index"]])
        w.writerow(["Nifty500_BH", "-", round(bench["sharpe"], 2),
                    round(bench["cagr"] * 100, 1), round(bench["maxdd"] * 100, 1),
                    round(bench["cagr"] / abs(bench["maxdd"]), 2),
                    0.0, 0.0, 0.0, 0.0, "inf", ""])
        # halves block
        w.writerow([])
        w.writerow(["C-BLEND halves", "aum_cr", "h1_2012_18_sharpe",
                    "h2_2019_26_sharpe", "full_sharpe", "h1_n", "h2_n"])
        for h in halves_rows:
            w.writerow(["", h["aum_cr"],
                        (round(h["h1_sharpe"], 2) if h["h1_sharpe"] is not None else ""),
                        (round(h["h2_sharpe"], 2) if h["h2_sharpe"] is not None else ""),
                        round(h["full_sharpe"], 2), h["h1_n"], h["h2_n"]])
        w.writerow([])
        w.writerow(["C_coverage", "H1_mean", round(float(h1_cov.mean()), 3),
                    "H1_min", round(float(h1_cov.min()), 3),
                    "H2_mean", round(float(h2_cov.mean()), 3),
                    "H2_min", round(float(h2_cov.min()), 3)])
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
