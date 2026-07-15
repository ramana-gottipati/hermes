"""EXPERIMENT — Dataset-C (capital-allocation) overlay on the RISKADJ momentum core.

The recorded 2026-06-24 experiment (strategy-ledger "Experiment 2026-06-24",
out/overlay_experiment.csv) proved a 4-metric PIT quality lens works as a
DRAWDOWN CONTROLLER (blend 50/50: MaxDD -42% -> -28.7%, return/vol 1.18) and left
"the fuller lenses" untested. This tests the richer capital-allocation
composite (ROIIC, ROCE level+trend, dilution drag, debt-funding share, growth
efficiency — the production src.automation.capital_allocation scorer, on
CALIBRATED PIT knowable-dates via fundamentals_asof) in the SAME harness:
identical top-25 monthly construction, relative liquidity gate, net-of-cost,
walk-forward halves, Nifty500 return/vol-0.89 survival hurdle — results are
directly comparable to the recorded table. D66: C is a veto/filter/overlay
candidate, never a ranker — variants cover veto, filter, blend, and the
quality+C stack, head-to-head against the prior quality-blend winner.
Ratios are mean/sd annualised with NO risk-free rate subtracted — return/vol, not
Sharpe, so they read high vs a textbook Sharpe; the 0.89 hurdle is on the SAME
basis, so the survival verdicts hold (D142).
Read-only (never writes production tables); writes out/c_overlay.csv.

Run (VPS):
  cd /opt/hermes && nohup env PYTHONPATH=/opt/hermes/research:/opt/hermes \
    .venv-research/bin/python research/explosive_moves/c_overlay.py \
    > /var/log/hermes-c-overlay.log 2>&1 &
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/opt/hermes/research")
sys.path.insert(0, "/opt/hermes")
from explosive_moves.factory import pctrank  # noqa: E402
from explosive_moves.overlay_experiment import (  # noqa: E402
    LIQ_PCTL, TOPN, build_tables, qrank, stats_row, topn_by)
from src.automation.capital_allocation import (  # noqa: E402
    _is_financial, compute_metrics, compute_metrics_fin, score_metrics)
from src.automation.fundamentals_asof import load_symbol_history  # noqa: E402

C_VETO_PCTL = 0.20      # veto: drop the bottom quintile of that date's C distribution
C_FILTER = 0.50         # filter: keep top-half C (comparable to the prior QFILTER)
BLEND_W = 0.50


def _c_score(frame, is_fin: bool, as_of: str):
    """Production C composite at as_of (None when the frame can't support one)."""
    try:
        m = compute_metrics_fin(frame, as_of) if is_fin else compute_metrics(frame, as_of)
        return score_metrics(m)["ca_score"]
    except Exception:  # noqa: BLE001 — a data-thin frame must not kill the run
        return None


def attach_c(tables):
    """Join the PIT C composite (cross-sectional pctrank per date) onto each gated set."""
    syms = sorted({x["s"] for t in tables for x in t["gated"]})
    print(f"loading fundamentals_asof frames for {len(syms)} gated symbols ...", flush=True)
    frames, isfin = {}, {}
    for i, s in enumerate(syms):
        try:
            fr = load_symbol_history(s)
        except Exception:  # noqa: BLE001
            fr = None
        if fr:
            frames[s] = fr
            isfin[s] = _is_financial(fr)
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{len(syms)} frames", flush=True)
    print(f"  {len(frames)} symbols have C-computable frames", flush=True)

    cov = []
    for ti, t in enumerate(tables):
        d0 = t["d0"]
        cas = []
        for x in t["gated"]:
            fr = frames.get(x["s"])
            ca = _c_score(fr, isfin[x["s"]], d0) if fr is not None else None
            x["ca"] = ca
            cas.append(ca)
        pr = qrank(cas)
        fin = np.isfinite(pr)
        for k, x in enumerate(t["gated"]):
            x["c_pr"] = float(pr[k]) if fin[k] else np.nan
        cov.append(float(np.mean(fin)) if len(fin) else 0.0)
        if (ti + 1) % 20 == 0:
            print(f"  C attached {ti + 1}/{len(tables)} rebalances (coverage so far "
                  f"{np.mean(cov):.0%})", flush=True)
    print(f"C coverage of gated universe: mean {np.mean(cov):.0%}, "
          f"min {np.min(cov):.0%}, max {np.max(cov):.0%}", flush=True)


# ---- selectors (A and E reuse the prior experiment's shapes for parity) ----
def sel_base(t):
    return topn_by(t["gated"], "riskadj")


def sel_c_veto(t):
    g = [x for x in t["gated"] if not np.isfinite(x["c_pr"]) or x["c_pr"] >= C_VETO_PCTL]
    return topn_by(g if len(g) >= TOPN else t["gated"], "riskadj")


def sel_c_filter(t):
    g = [x for x in t["gated"] if np.isfinite(x["c_pr"]) and x["c_pr"] >= C_FILTER]
    return topn_by(g if len(g) >= TOPN else t["gated"], "riskadj")


def _ra(t):
    return pctrank(np.array([x["riskadj"] for x in t["gated"]]))


def sel_c_blend(t):
    g = t["gated"]
    ra = _ra(t)
    for k, x in enumerate(g):
        c = x["c_pr"] if np.isfinite(x["c_pr"]) else 0.5
        x["_score"] = (1 - BLEND_W) * ra[k] + BLEND_W * c
    return topn_by(g, "_score")


def sel_q_blend(t):
    g = t["gated"]
    ra = _ra(t)
    for k, x in enumerate(g):
        q = x["q"] if np.isfinite(x["q"]) else 0.5
        x["_score"] = (1 - BLEND_W) * ra[k] + BLEND_W * q
    return topn_by(g, "_score")


def sel_stack(t):
    g = t["gated"]
    ra = _ra(t)
    for k, x in enumerate(g):
        q = x["q"] if np.isfinite(x["q"]) else 0.5
        c = x["c_pr"] if np.isfinite(x["c_pr"]) else 0.5
        x["_score"] = 0.50 * ra[k] + 0.25 * q + 0.25 * c
    return topn_by(g, "_score")


def main():
    print("building tables (relative gate + PIT quality join) ...", flush=True)
    tables = build_tables()
    print(f"  {len(tables)} rebalance dates; avg gated = "
          f"{np.mean([len(t['gated']) for t in tables]):.0f}", flush=True)
    attach_c(tables)

    rows = [
        stats_row(tables, "A. RISKADJ rel-gate (baseline)", sel_base),
        stats_row(tables, "B. + C-VETO bottom-quintile", sel_c_veto),
        stats_row(tables, "C. + C-FILTER top-half", sel_c_filter),
        stats_row(tables, "D. + C-BLEND 50/50", sel_c_blend),
        stats_row(tables, "E. + QUALITY-BLEND 50/50 (prior win)", sel_q_blend),
        stats_row(tables, "F. + STACK 50mom/25q/25C", sel_stack),
        stats_row(tables, "G. D (C-blend) @1.5x cost", sel_c_blend, cost_mult=1.5),
        stats_row(tables, "H. F (stack) @1.5x cost", sel_stack, cost_mult=1.5),
    ]

    hdr = (f"{'variant':40}{'CAGR':>7}{'MaxDD':>8}{'retvol':>6}{'Clmr':>6}{'tot':>6}"
           f"{'H1rv':>6}{'H2rv':>6}{'N':>5}  surv")
    print("\n" + "=" * len(hdr))
    print("C-OVERLAY RESULTS (top-25 monthly, net cost; hurdle Nifty500 return/vol 0.89 both halves)")
    print("=" * len(hdr))
    print(hdr)
    for r in rows:
        print(f"{r['name']:40}{r['cagr'] * 100:>6.1f}%{r['maxdd'] * 100:>7.1f}%{r['retvol']:>6.2f}"
              f"{r['calmar']:>6.2f}{r['totx']:>5.1f}x{(r['h1_retvol'] or 0):>6.2f}"
              f"{(r['h2_retvol'] or 0):>6.2f}{r['avg_n']:>5.0f}  {'YES' if r['surv'] else ''}")

    out = os.path.join(os.path.dirname(__file__), "out", "c_overlay.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["variant", "cagr_pct", "maxdd_pct", "retvol", "calmar", "total_x",
                    "h1_2012_18_retvol", "h2_2019_26_retvol", "h2_cagr_pct",
                    "avg_positions", "cost_mult", "survives"])
        for r in rows:
            w.writerow([r["name"], round(r["cagr"] * 100, 1), round(r["maxdd"] * 100, 1),
                        round(r["retvol"], 2), round(r["calmar"], 2), round(r["totx"], 1),
                        round(r["h1_retvol"] or 0, 2), round(r["h2_retvol"] or 0, 2),
                        round((r["h2_cagr"] or 0) * 100, 1), round(r["avg_n"], 0),
                        r["cost_mult"], "YES" if r["surv"] else "NO"])
    print("\nsaved -> out/c_overlay.csv")


if __name__ == "__main__":
    main()
