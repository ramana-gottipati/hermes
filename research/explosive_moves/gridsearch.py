"""Exit-parameter grid search (per-trade expectancy, no portfolio).

Clones a strategy with overridden exit knobs, runs the per-trade sim over all onset
entries, and ranks configs by expectancy (mean net return per trade) with profit factor,
hit, win/loss-R and MFE-capture shown. Costs are ON (this is net-of-cost expectancy).
"""
from __future__ import annotations

import sys
import time
from dataclasses import replace
from itertools import product
import numpy as np

from .embase import load_symbol_cache
from .backtest import all_trades
from .strategies import build_strategies
from .metrics import trade_stats

GRID = {
    "init_stop_pct": [0.12, 0.15, 0.18],
    "atr_mult": [3.0, 4.0, 6.0],
    "trail_after": [0.12, 0.25],
    "scales": [
        ((0.12, 0.33), (0.30, 0.33)),
        ((0.12, 0.50), (0.40, 0.25)),
        ((0.25, 0.50),),
        ((0.15, 0.25), (0.35, 0.25), (0.70, 0.25)),
    ],
    "time_exit_bars": [66, 132],
}


def run(cache, base, grid):
    keys = list(grid.keys())
    rows = []
    for combo in product(*[grid[k] for k in keys]):
        ov = dict(zip(keys, combo))
        st = replace(base, **ov)
        trades = all_trades(cache, st)
        taken = [(t, 1.0) for t in trades]               # per-trade only (no gate)
        ts = trade_stats(taken)
        rows.append({**ov, **ts})
    return rows


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "S1"
    cache = load_symbol_cache()
    base = build_strategies()[key]
    t0 = time.time()
    rows = run(cache, base, GRID)
    rows.sort(key=lambda r: r["exp_ret"], reverse=True)
    print(f"{key}: {len(rows)} configs, {time.time()-t0:.0f}s. Ranked by expectancy (net/trade):\n")
    hdr = f"{'stop':>5} {'atr':>4} {'trailA':>6} {'texit':>5} {'scales':<26} | {'n':>5} {'exp%':>6} {'PF':>5} {'hit':>5} {'wR':>5} {'lR':>6} {'MFEcap':>6}"
    print(hdr); print("-" * len(hdr))
    for r in rows[:18]:
        sc = "/".join(f"{int(l*100)}:{int(f*100)}" for l, f in r["scales"])
        print(f"{r['init_stop_pct']:>5.2f} {r['atr_mult']:>4.0f} {r['trail_after']:>6.2f} "
              f"{r['time_exit_bars']:>5} {sc:<26} | {r['n']:>5} {r['exp_ret']*100:>6.2f} "
              f"{r['pf']:>5.2f} {r['hit']*100:>5.1f} {r['avg_win_R']:>5.2f} {r['avg_loss_R']:>6.2f} "
              f"{r['mfe_capture']*100:>6.1f}")
    print("\nWORST 3:")
    for r in rows[-3:]:
        sc = "/".join(f"{int(l*100)}:{int(f*100)}" for l, f in r["scales"])
        print(f"{r['init_stop_pct']:>5.2f} {r['atr_mult']:>4.0f} {r['trail_after']:>6.2f} "
              f"{r['time_exit_bars']:>5} {sc:<26} | {r['n']:>5} {r['exp_ret']*100:>6.2f} {r['pf']:>5.2f}")


if __name__ == "__main__":
    main()
