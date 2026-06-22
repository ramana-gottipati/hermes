"""Step 1 — empirical stop/target calibration from the per-trade forward path.

For each strategy's ONSET entries (the same signals the backtest takes), hold with NO
management to a 132d horizon and record the corporate-action-clean forward path from the
s+1 OPEN:
   ret_22/66/132, MFE (peak high), MAE (whole-window trough),
   pre-peak MAE  = the deepest low BEFORE the MFE peak (the heat a would-be winner
                   must survive — the correct basis for an INITIAL stop),
   day the +X% target is first hit.

Then report, per strategy:
  * winners' (MFE >= target) pre-peak MAE percentiles  -> set the stop to clear ~85%
  * the MFE distribution (p25/50/75/90)                 -> trail wide, do not cap
  * hit-rate to +10/+25/+50% and median days-to-+10%

Stops MUST come from these per-trade quantiles, NOT the cohort-mean mae in oos_*.csv.
"""
from __future__ import annotations

import sys
import numpy as np

from .embase import load_symbol_cache
from .backtest import signals
from .strategies import build_strategies

HZN = 132


def forward_path(A, e, hzn=HZN):
    o, h, l, c = A["adj_open"], A["adj_high"], A["adj_low"], A["adj_close"]
    n = len(c)
    entry = float(o[e])
    if not (entry > 0) or e + 1 >= n:
        return None
    j = min(e + hzn, n - 1)
    hi = h[e:j + 1]; lo = l[e:j + 1]; cl = c[e:j + 1]
    mfe = float(np.nanmax(hi) / entry - 1.0)
    mae = float(np.nanmin(lo) / entry - 1.0)
    peak_k = int(np.nanargmax(hi))                       # index of the MFE peak
    pre_mae = float(np.nanmin(lo[:peak_k + 1]) / entry - 1.0) if peak_k >= 0 else mae
    def ret_at(d):
        k = e + d
        return float(c[k] / entry - 1.0) if k < n else np.nan
    # first day each target is hit (high basis)
    def first_hit(tp):
        idx = np.where(hi / entry - 1.0 >= tp)[0]
        return int(idx[0]) if len(idx) else None
    return {"mfe": mfe, "mae": mae, "pre_mae": pre_mae,
            "ret22": ret_at(22), "ret66": ret_at(66), "ret132": ret_at(132),
            "d10": first_hit(0.10), "d12": first_hit(0.12), "d25": first_hit(0.25)}


def pct(a, q):
    a = np.array([x for x in a if x == x])
    return float(np.percentile(a, q)) if len(a) else float("nan")


def calibrate(cache, strat):
    sigs = signals(cache, strat)
    paths = []
    for sg in sigs:
        fp = forward_path(cache[sg["sym"]], sg["e"])
        if fp:
            fp["tier"] = sg["mt"]
            paths.append(fp)
    n = len(paths)
    if n == 0:
        return None
    mfe = [p["mfe"] for p in paths]
    pre = [p["pre_mae"] for p in paths]
    r66 = [p["ret66"] for p in paths]
    # winner cohorts
    win12 = [p for p in paths if p["mfe"] >= 0.12]       # touched +12%
    win25 = [p for p in paths if p["mfe"] >= 0.25]
    up66 = [p for p in paths if (p["ret66"] == p["ret66"] and p["ret66"] > 0)]
    return {
        "n": n,
        "mfe_p25": pct(mfe, 25), "mfe_p50": pct(mfe, 50), "mfe_p75": pct(mfe, 75), "mfe_p90": pct(mfe, 90),
        "premae_p10_all": pct(pre, 10), "premae_p25_all": pct(pre, 25), "premae_p50_all": pct(pre, 50),
        # winners' (touched +12%) pre-peak MAE deep percentiles -> the stop basis
        "w12_n": len(win12), "w12_frac": len(win12) / n,
        "w12_premae_p5": pct([p["pre_mae"] for p in win12], 5),
        "w12_premae_p10": pct([p["pre_mae"] for p in win12], 10),
        "w12_premae_p20": pct([p["pre_mae"] for p in win12], 20),
        "w12_premae_p25": pct([p["pre_mae"] for p in win12], 25),
        "w12_premae_p50": pct([p["pre_mae"] for p in win12], 50),
        "w25_n": len(win25),
        "w25_premae_p10": pct([p["pre_mae"] for p in win25], 10),
        "w25_premae_p20": pct([p["pre_mae"] for p in win25], 20),
        "hit_10": np.mean([p["mfe"] >= 0.10 for p in paths]),
        "hit_25": np.mean([p["mfe"] >= 0.25 for p in paths]),
        "hit_50": np.mean([p["mfe"] >= 0.50 for p in paths]),
        "up66_frac": len(up66) / n,
        "med_ret66": pct(r66, 50),
        "med_d10": np.median([p["d10"] for p in paths if p["d10"] is not None]),
        "med_d12": np.median([p["d12"] for p in paths if p["d12"] is not None]),
    }


def main():
    cache = load_symbol_cache()
    S = build_strategies()
    keys = sys.argv[1:] or ["S1", "S2", "S3", "S4"]
    for k in keys:
        st = S[k]
        r = calibrate(cache, st)
        if r is None:
            print(f"{k}: no signals"); continue
        print(f"\n=== {k}: {st.desc} ===")
        print(f"  onset entries: {r['n']}")
        print(f"  MFE dist:  p25={r['mfe_p25']:+.1%}  p50={r['mfe_p50']:+.1%}  "
              f"p75={r['mfe_p75']:+.1%}  p90={r['mfe_p90']:+.1%}")
        print(f"  reach +10%={r['hit_10']:.0%}  +25%={r['hit_25']:.0%}  +50%={r['hit_50']:.0%}  "
              f"| up@66d={r['up66_frac']:.0%}  medRet66={r['med_ret66']:+.1%}")
        print(f"  median days to +10%={r['med_d10']:.0f}  to +12%={r['med_d12']:.0f}")
        print(f"  WINNERS (touched +12%, n={r['w12_n']}, {r['w12_frac']:.0%}) pre-peak MAE percentiles:")
        print(f"     p5={r['w12_premae_p5']:+.1%}  p10={r['w12_premae_p10']:+.1%}  "
              f"p20={r['w12_premae_p20']:+.1%}  p25={r['w12_premae_p25']:+.1%}  p50={r['w12_premae_p50']:+.1%}")
        print(f"     => a stop below p10 ({r['w12_premae_p10']:+.1%}) clears ~90% of +12% winners")
        print(f"  bigger winners (+25%, n={r['w25_n']}) pre-peak MAE: p10={r['w25_premae_p10']:+.1%} "
              f"p20={r['w25_premae_p20']:+.1%}")
        print(f"  all-entry pre-peak MAE: p10={r['premae_p10_all']:+.1%} p25={r['premae_p25_all']:+.1%} "
              f"p50={r['premae_p50_all']:+.1%}")


if __name__ == "__main__":
    main()
