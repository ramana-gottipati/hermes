"""Master results table — per clue/pattern: sample, hit, lift, and post-trigger
MFE (max high = opportunity) / MAE (max low = worst dip), in %, over 6 months.

MFE/MAE are measured on the monthly EVENTS the pattern caught (i.e. "when a move
followed, how far it ran / dipped from the launch"), using only events with a
full 6-month forward path. Hit/lift are reweighted (K=10) vs the quiet baseline.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import research_conn

K = 10.0
# (name, predicate) — lens attribution added in the writeup
PATTERNS = [
    ("Momentum-continuation (Launchpad)", "ret_22d>0.07 & vol_ratio_22_66<=1.48 & range_tight_22>0.096"),
    ("Pullback-in-vol (Launchpad)", "ret_22d<=0.07 & vol_66>0.024 & ret_1d<=-0.022"),
    ("Coiled-momentum (#22)", "vol_ratio<1 & ret_22d>=0.10"),
    ("Either-Launchpad (union)", "(ret_22d>0.07 & vol_ratio_22_66<=1.48 & range_tight_22>0.096) | (ret_22d<=0.07 & vol_66>0.024 & ret_1d<=-0.022)"),
    ("High volatility vol_66>=3.6%", "vol_66>=0.0356"),
    ("Strong trend >30% above 200DMA", "close_vs_sma200>=0.30"),
    ("Off the lows >=130% above 52wL", "dist_low_252>=1.30"),
    ("1-mo momentum ret_22d>=9.4%", "ret_22d>=0.094"),
    ("Wide range range_tight_66>=0.49", "range_tight_66>=0.49"),
    ("Low delivery% (<=44) [counter-DVPT]", "deliv_per_22<=44"),
    ("Big-bite churn (bites in low-deliv)", "big_deliv_days_10>=2 & deliv_per_22<=45"),
    ("Delivery up-skew, no-surge", "deliv_qty_trend<=1.5 & deliv_updown_22>=2.5"),
    ("Coiled-spring / vol dry-up [REFUTED]", "range_tight_22<=0.10 & vol_dryup_5_22<=0.8"),
    ("Big-tickets + flat-crowd [REFUTED]", "avg_trade_val_trend>=1.05 & trades_trend<=1.0"),
]


def main():
    rc = research_conn()
    ev = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly'", rc)
    base = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
    for df in (ev, base):
        for c in ("ret_22d", "vol_ratio_22_66", "range_tight_22", "vol_66", "ret_1d", "vol_ratio",
                  "close_vs_sma200", "dist_low_252", "range_tight_66", "deliv_per_22", "big_deliv_days_10",
                  "deliv_qty_trend", "deliv_updown_22", "vol_dryup_5_22", "avg_trade_val_trend",
                  "trades_trend", "mfe_6m", "mae_6m", "sustained", "fwd_complete_132", "big50_6m"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    pos = ev[ev.sustained == 1]
    base_rate = len(pos) / (len(pos) + K * len(base))
    # CL-RES-10: several PATTERNS thresholds above (e.g. vol_66>=0.0356, dist_low_252>=1.30,
    # ret_22d>=0.094, range_tight_66>=0.49) were DERIVED from this same event table, so the
    # hit/lift printed for them is IN-SAMPLE — it describes how the data was carved, not an
    # out-of-sample edge. Patterns marked [REFUTED] failed validation and are kept only as a
    # negative record. Read lift here as descriptive (which clues co-occur with sustained
    # moves in-sample); for held-out lift, re-evaluate the frozen predicates on a window not
    # used to choose the cuts (the walk-forward split in run_backtests.py).
    print("NOTE (CL-RES-10): data-derived thresholds -> hit/lift below are IN-SAMPLE "
          "(descriptive provenance), not held-out edge.")
    print(f"monthly events={len(ev)} sustained={len(pos)} baseline={len(base)} (K={K}) base_rate={base_rate:.3f}")
    print(f"\n{'pattern':38s} {'n_ev':>6} {'base%':>6} {'hit':>5} {'lift':>5} "
          f"{'MFEavg':>7} {'MFEmed':>7} {'MAEavg':>7} {'MAEmed':>7} {'>=50%':>6} {'sust':>5}")
    print("-" * 118)
    rows = []
    for name, pred in PATTERNS:
        em = ev.eval(pred); bm = base.eval(pred); pm = pos.eval(pred)
        a = int(pm.sum()); b = int(bm.sum())
        hit = a / (a + K * b) if (a + K * b) else np.nan
        lift = hit / base_rate if base_rate else np.nan
        m = ev[em & (ev.fwd_complete_132 == 1)]
        mfe = m.mfe_6m * 100; mae = m.mae_6m * 100
        r = dict(pattern=name, n_ev=int(em.sum()), base_pct=100 * bm.mean(), hit=hit, lift=lift,
                 mfe_avg=mfe.mean(), mfe_med=mfe.median(), mae_avg=mae.mean(), mae_med=mae.median(),
                 pct50=100 * (m.big50_6m == 1).mean(), sustain=100 * ev[em].sustained.mean())
        rows.append(r)
        print(f"{name:38s} {r['n_ev']:>6} {r['base_pct']:>5.1f} {r['hit']:>5.2f} {r['lift']:>5.2f} "
              f"{r['mfe_avg']:>6.0f}% {r['mfe_med']:>6.0f}% {r['mae_avg']:>6.0f}% {r['mae_med']:>6.0f}% "
              f"{r['pct50']:>5.0f}% {r['sustain']:>4.0f}%")
    pd.DataFrame(rows).to_csv("/opt/hermes/research/explosive_moves/out/results_table.csv", index=False)
    rc.close()


if __name__ == "__main__":
    main()
