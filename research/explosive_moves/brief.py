"""Phase H — squeeze a rich, multi-angle DATA BRIEF out of the existing dimensions.

Raw material for the multi-analyst pressure session: many conditional cuts,
mechanism probes (esp. WHY delivery-% dries up), big-winner discriminators,
participation/ticket-size, seasonality, correlations. Compact, agent-readable.
Monthly +10% events vs the quiet baseline. Offline; read-only research.db.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import research_conn

pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40)


def cmp(ev, base, cols):
    rows = []
    for c in cols:
        e = pd.to_numeric(ev[c], errors="coerce"); b = pd.to_numeric(base[c], errors="coerce")
        rows.append({"feature": c, "event_med": round(e.median(), 3), "base_med": round(b.median(), 3),
                     "event_mean": round(e.mean(), 3), "base_mean": round(b.mean(), 3),
                     "e/b_mean": round(e.mean() / b.mean(), 2) if b.mean() else np.nan})
    return pd.DataFrame(rows)


def main():
    rc = research_conn()
    ev = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly'", rc)
    evs = ev[ev.sustained == 1]
    base = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
    print(f"# DATA BRIEF — monthly +10% moves: {len(ev)} events ({len(evs)} sustained, {ev.sustained.mean():.0%}) vs {len(base)} baseline\n")

    print("## 1. DELIVERY MECHANISM — why is delivery-% lower before moves?")
    print(cmp(ev, base, ["deliv_per_s", "deliv_per_22", "deliv_per_pctile", "deliv_qty_trend",
                         "deliv_val_trend", "vol_ratio_22_66", "vol_dryup_5_22", "trades_trend",
                         "avg_trade_val_trend", "n_strong_deliv_22", "big_deliv_days_10"]).to_string(index=False))
    print("  → if vol_ratio_22_66 (volume) rises MORE than deliv_qty_trend (delivered qty), %-falls = churn/rotation, not less holding.")
    # delivery quartile vs outcome (within events)
    ev2 = ev.dropna(subset=["deliv_per_22", "ret_66"]).copy()
    ev2["dq"] = pd.qcut(ev2["deliv_per_22"], 4, labels=["Q1-low", "Q2", "Q3", "Q4-high"])
    print("\n  delivery%-quartile vs outcome (within events):")
    print(ev2.groupby("dq", observed=True).agg(n=("ret_66", "size"), sustain=("sustained", "mean"),
          ret66=("ret_66", "mean"), mfe6m=("mfe_6m", "mean"), big50=("big50_6m", "mean")).round(3).to_string())

    print("\n## 2. PARTICIPATION / TICKET SIZE (institutional vs retail footprint)")
    print(cmp(ev, base, ["avg_trade_val_trend", "trades_trend", "h_avg_trade_qty",
                         "h_avg_deliv_qty_per_trade", "turnover_surge_raw", "vol_z_1d"]).to_string(index=False))

    print("\n## 3. BIG-WINNER DISCRIMINATOR — within events, what separates ≥50%/6mo winners from the rest?")
    d = ev[ev.fwd_complete_132 == 1].copy()
    feats = ["ret_22d", "ret_66d", "ret_132d", "close_vs_sma200", "sma50_slope", "dist_low_252",
             "dist_high_252", "range_pos_252", "vol_66", "range_tight_66", "atr14_pct",
             "turnover_surge_raw", "deliv_per_22", "deliv_qty_trend", "vol_dryup_5_22",
             "close_strength_5", "consec_up", "new_high_22", "log_price", "gap_1d"]
    win = d[d.big50_6m == 1]; los = d[d.big50_6m == 0]
    rows = []
    for c in feats:
        w = pd.to_numeric(win[c], errors="coerce"); l = pd.to_numeric(los[c], errors="coerce")
        sd = pd.concat([w, l]).std()
        rows.append({"feature": c, "winner_med": round(w.median(), 3), "loser_med": round(l.median(), 3),
                     "std_diff": round((w.mean() - l.mean()) / sd, 3) if sd else 0})
    print(pd.DataFrame(rows).reindex(pd.DataFrame(rows).std_diff.abs().sort_values(ascending=False).index).to_string(index=False))

    print("\n## 4. CONDITIONAL SUSTAIN/RETURN")
    for name, col, bins, labs in [
        ("liquidity ₹", "med_turn", [0, 5e7, 2.5e8, 1e12], ["1-5cr", "5-25cr", ">25cr"]),
        ("price ₹ (log10)", "log_price", [-1, 1, 1.7, 2.4, 9], ["<10", "10-50", "50-250", ">250"]),
        ("1-mo momentum", "ret_22d", [-9, 0, 0.1, 0.3, 9], ["down", "0-10%", "10-30%", ">30%"]),
    ]:
        ev3 = ev.dropna(subset=[col]).copy()
        ev3["bk"] = pd.cut(pd.to_numeric(ev3[col]), bins=bins, labels=labs)
        g = ev3.groupby("bk", observed=True).agg(n=("ret_66", "size"), sustain=("sustained", "mean"),
              ret66=("ret_66", "mean"), big50=("big50_6m", "mean")).round(3)
        print(f"\n  by {name}:\n{g.to_string()}")

    print("\n## 5. SEASONALITY of the move (move_date)")
    ev["mo"] = ev["move_date"].str[5:7]
    ev["wd"] = pd.to_datetime(ev["move_date"], errors="coerce").dt.dayofweek
    print("  events by month:", ev.groupby("mo").size().to_dict())
    print("  sustain by weekday(0=Mon):", ev.groupby("wd")["sustained"].mean().round(3).to_dict())

    print("\n## 6. SQUEEZE / COIL before the move (event vs base)")
    print(cmp(ev, base, ["vol_66", "vol_22", "vol_ratio", "atr_contraction", "nr_ratio_10_60",
                         "range_tight_22", "range_tight_66", "turnover_surge_raw"]).to_string(index=False))

    print("\n## 7. CORRELATIONS among key clues (within events)")
    kc = ["ret_22d", "close_vs_sma200", "dist_low_252", "vol_66", "range_tight_66",
          "turnover_surge_raw", "deliv_per_22", "deliv_qty_trend", "new_high_22"]
    print(ev[kc].apply(pd.to_numeric, errors="coerce").corr().round(2).to_string())
    rc.close()


if __name__ == "__main__":
    main()
