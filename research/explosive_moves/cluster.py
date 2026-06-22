"""Phase G — GROUP the clues by similarity (Ramana's ask).

The +10% move is the RESULT, not the trigger. This module takes the pre-move
data fingerprint of every +10% move and clusters them into ARCHETYPES — the
distinct "kinds of setup" that precede a move — so we can see: how many distinct
reasons there are, the data clues that define each, how frequently each occurs,
and how well each one sustains / pays.

Method: standardize each event's pre-move features against the QUIET-baseline
mean/std (so z>0 = "more than a normal day"), KMeans into k groups, then profile
each group by its distinguishing clues (centroid z) + frequency + outcomes.
Monthly +10%-intramonth events (the ride-to-exit move). Offline; raw features only.
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .common import research_conn, OUT_DIR

# interpretable, low-redundancy raw features spanning the themes
CF = ["ret_22d", "close_vs_sma200", "sma50_slope", "dist_low_252", "dist_high_252",
      "vol_66", "range_tight_66", "turnover_surge_raw", "deliv_per_22",
      "deliv_qty_trend", "vol_dryup_5_22", "range_pos_252"]
NICE = {
    "ret_22d": "1-mo momentum", "close_vs_sma200": "above 200-DMA", "sma50_slope": "50-DMA rising",
    "dist_low_252": "off the 52w low", "dist_high_252": "near 52w high", "vol_66": "volatility",
    "range_tight_66": "wide range", "turnover_surge_raw": "turnover surge", "deliv_per_22": "delivery %",
    "deliv_qty_trend": "delivery-qty rising", "vol_dryup_5_22": "recent volume vs base",
    "range_pos_252": "position in 52w range",
}


def main(k=6):
    rc = research_conn()
    ev = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly'", rc)
    base = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
    # standardize vs the quiet baseline (z>0 = more than a normal liquid day)
    mu = base[CF].astype(float).mean()
    sd = base[CF].astype(float).std().replace(0, 1.0)
    Z = ((ev[CF].astype(float) - mu) / sd).clip(-5, 5).fillna(0.0)

    # pick k by silhouette (sampled) across a small range, unless given
    if k is None:
        samp = Z.sample(min(8000, len(Z)), random_state=0)
        best = None
        for kk in range(4, 9):
            lab = KMeans(n_clusters=kk, n_init=4, random_state=0).fit_predict(samp)
            s = silhouette_score(samp, lab)
            print(f"  k={kk} silhouette={s:.3f}")
            if best is None or s > best[1]:
                best = (kk, s)
        k = best[0]
        print(f"  chosen k={k}")

    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
    ev["cluster"] = km.labels_
    Z["cluster"] = km.labels_
    n = len(ev)

    rows = []
    print(f"\n=== {n} monthly +10% moves grouped into {k} archetypes "
          f"(sustain base {ev['sustained'].mean():.0%}) ===")
    order = ev["cluster"].value_counts().index
    for c in order:
        m = ev["cluster"] == c
        sub = ev[m]
        cz = Z[Z["cluster"] == c][CF].mean().sort_values()
        hi = [(f, cz[f]) for f in cz.index[::-1][:5] if cz[f] > 0.25]
        lo = [(f, cz[f]) for f in cz.index[:3] if cz[f] < -0.25]
        prof = {"cluster": int(c), "n": int(m.sum()), "pct": round(100 * m.sum() / n, 1),
                "sustain": round(sub["sustained"].mean(), 3),
                "avg_ret_66": round(sub["ret_66"].mean(), 3),
                "avg_mfe_6m": round(sub["mfe_6m"].mean(), 3),
                "avg_mae_6m": round(sub["mae_6m"].mean(), 3),
                "big50": round(sub[sub.fwd_complete_132 == 1]["big50_6m"].mean(), 3),
                "hi_clues": "; ".join(f"{NICE[f]}(+{z:.1f})" for f, z in hi),
                "lo_clues": "; ".join(f"{NICE[f]}({z:.1f})" for f, z in lo)}
        rows.append(prof)
        print(f"\n  ── Archetype @cluster{c}: {prof['pct']}% of moves (n={prof['n']}) ──")
        print(f"     sustain={prof['sustain']:.0%}  avg_ret_66={prof['avg_ret_66']:+.0%}  "
              f"MFE6m={prof['avg_mfe_6m']:+.0%}  MAE6m={prof['avg_mae_6m']:+.0%}  big50={prof['big50']:.0%}")
        print(f"     ELEVATED clues : {prof['hi_clues']}")
        print(f"     SUPPRESSED     : {prof['lo_clues']}")
    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "clusters_monthly.csv", index=False)
    df.to_sql("clusters_monthly", rc, if_exists="replace", index=False)
    # full centroid table (z vs normal day) for the writeup
    cent = Z.groupby("cluster")[CF].mean().round(2)
    cent.to_csv(OUT_DIR / "cluster_centroids.csv")
    print("\n=== centroid z (vs a normal liquid day) ===")
    print(cent.to_string())
    rc.close()


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    main(k if k > 0 else None)
