"""Phase E (cont.) — robustness of the headline monthly setups.

Two honesty checks the writeup must pass:
  1. LIQUIDITY: does the edge survive in genuinely liquid names, or is it a
     microcap-manipulation artifact? Evaluate across med-turnover buckets.
  2. REGIME: is the hit ratio stable year-by-year, or carried by one bull year?

We use the RS-FREE monthly predicates (range/ATR/return only -> computable in
EVERY year, unlike rs_rank which is reliable only ~2021+). Reweighted vs the
1-in-K baseline. Also reports the success ratio (forward path) per cut.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import research_conn, OUT_DIR
from .mine import _lift, load_study

# v3 OOS-validated raw monthly archetypes (corrected rolling +10% definition).
PREDICATES = {
    "momentum_continuation": lambda d: (d.ret_22d > 0.073) & (d.vol_ratio_22_66 <= 1.477) & (d.range_tight_22 > 0.096),
    "pullback_in_vol": lambda d: (d.ret_22d <= 0.073) & (d.vol_66 > 0.0243) & (d.ret_1d <= -0.0219),
}
PREDICATES["either_archetype"] = lambda d: PREDICATES["momentum_continuation"](d) | PREDICATES["pullback_in_vol"](d)

LIQ_BUCKETS = [(1e7, 5e7, "1-5cr"), (5e7, 2.5e8, "5-25cr"), (2.5e8, 1e12, ">25cr")]


def _stats(pos, ctrl, kw, pmask_pos, pmask_ctrl):
    a = int(pmask_pos.sum()); b = int(pmask_ctrl.sum())
    st = _lift(a, b, kw, len(pos), len(ctrl))
    ev = pos[pmask_pos]
    if len(ev):
        st["avg_ret_66"] = float(ev["ret_66"].mean())
        st["big50_6m_rate"] = float(ev[ev.fwd_complete_132 == 1]["big50_6m"].mean()) if (ev.fwd_complete_132 == 1).any() else np.nan
        st["win_rate_66"] = float((ev["ret_66"] > 0).mean())
    return st


def main():
    rc = research_conn()
    pos, ctrl, kw = load_study(rc, "monthly")
    rows = []
    print(f"monthly sustained: {len(pos)} events, base rate "
          f"{len(pos)/(len(pos)+kw*len(ctrl)):.4%}\n")
    for name, pred in PREDICATES.items():
        mp, mc = pred(pos), pred(ctrl)
        st = _stats(pos, ctrl, kw, mp, mc)
        print(f"[{name}] hit={st['hit_ratio']:.3f} lift={st['lift']:.1f} cov={st['coverage']:.2f} "
              f"n={st['n_events_match']}  ret66={st.get('avg_ret_66',float('nan')):.3f} "
              f"big50={st.get('big50_6m_rate',float('nan')):.3f} win={st.get('win_rate_66',float('nan')):.2f}")
        rows.append({"cut": "ALL", "predicate": name, **st})
        # by liquidity bucket
        for lo, hi, lbl in LIQ_BUCKETS:
            bp = (pos.med_turn >= lo) & (pos.med_turn < hi)
            bc = (ctrl.med_turn >= lo) & (ctrl.med_turn < hi)
            stb = _lift(int((mp & bp).sum()), int((mc & bc).sum()), kw, int(bp.sum()), int(bc.sum()))
            ev = pos[mp & bp]
            r66 = float(ev["ret_66"].mean()) if len(ev) else np.nan
            print(f"     liq {lbl:7s}: hit={stb['hit_ratio']:.3f} lift={stb['lift']:.1f} "
                  f"n={stb['n_events_match']:4d} ret66={r66:.3f}")
            rows.append({"cut": f"liq:{lbl}", "predicate": name, "avg_ret_66": r66, **stb})
        print()
    # year-by-year stability for the union setup
    print("Year-by-year (either_archetype): hit ratio & lift")
    pred = PREDICATES["either_archetype"]; mp, mc = pred(pos), pred(ctrl)
    for y in range(2012, 2027):
        yp = pos.year.astype(int) == y; yc = ctrl.year.astype(int) == y
        if yp.sum() == 0:
            continue
        st = _lift(int((mp & yp).sum()), int((mc & yc).sum()), kw, int(yp.sum()), int(yc.sum()))
        ev = pos[mp & yp]
        r66 = float(ev["ret_66"].mean()) if len(ev) else np.nan
        print(f"   {y}: hit={st['hit_ratio']:.3f} lift={st['lift']:5.1f} n={st['n_events_match']:4d} ret66={r66:.3f}")
        rows.append({"cut": f"year:{y}", "predicate": "either_archetype", "avg_ret_66": r66, **st})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_DIR / "sensitivity_monthly.csv", index=False)
    pd.DataFrame(rows).to_sql("sensitivity_monthly", rc, if_exists="replace", index=False)
    rc.close()


if __name__ == "__main__":
    main()
