"""Phase I.2 — the two highest-novelty recovered hypotheses that need a re-stream.

#21 (conf 68) close-vs-VWAP gap: mean (close - avg_price)/avg_price over [s-22,s-1],
    event vs baseline, AND conditioned on the low-delivery regime (avg_price = NSE
    VWAP, populated ~2020+ only → smaller sample).
#16 (conf 62) trade-fragmentation decomposition: TFR = num_trades/volume (trades per
    share). Is pre-move delivery-dryup driven by fragmentation rising? event vs base.
#27 (conf 64) delivered-shares-per-trade (deliv_qty/num_trades) falling vs own 60d.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import research_conn, main_conn, load_series, cliffs_delta

W = 22


def main():
    rc = research_conn()
    rows = rc.execute("SELECT symbol,launch_date,etype,sustained,med_turn,deliv_per_22 "
                      "FROM features WHERE etype IN ('monthly','baseline')").fetchall()
    bysym = {}
    for r in rows:
        bysym.setdefault(r["symbol"], []).append(dict(r))
    mc = main_conn()
    out = []
    for sym in bysym:
        ss = load_series(mc, sym)
        if ss is None:
            continue
        dmap = {d: i for i, d in enumerate(ss.date)}
        ap = ss.avg_price
        with np.errstate(divide="ignore", invalid="ignore"):
            cvwap = np.where(ap > 0, (ss.close - ap) / ap, np.nan)          # #21
            tfr = np.where(ss.volume > 0, ss.num_trades / ss.volume, np.nan)  # #16
            dpt = np.where(ss.num_trades > 0, ss.deliv_qty / ss.num_trades, np.nan)  # #27
        for rec in bysym[sym]:
            s = dmap.get(rec["launch_date"])
            if s is None or s < 66:
                continue
            d = dict(rec)
            d["cvwap_22"] = float(np.nanmean(cvwap[s - W:s]))
            d["n_vwap"] = int(np.sum(~np.isnan(cvwap[s - W:s])))
            tr_recent = np.nanmean(tfr[s - W:s]); tr_prior = np.nanmean(tfr[s - 2 * W:s - W])
            d["tfr_trend"] = float(tr_recent / tr_prior) if tr_prior else np.nan
            d["tfr_recent"] = float(tr_recent)
            dpt_recent = np.nanmean(dpt[s - 10:s]); dpt_base = np.nanmedian(dpt[s - 60:s - 10])
            d["dpt_ratio"] = float(dpt_recent / dpt_base) if dpt_base else np.nan
            out.append(d)
    mc.close()
    df = pd.DataFrame(out)
    ev = df[df.etype == "monthly"]; base = df[df.etype == "baseline"]

    def cmp(c, sub_ev=None, sub_base=None):
        e = pd.to_numeric((sub_ev if sub_ev is not None else ev)[c], errors="coerce")
        b = pd.to_numeric((sub_base if sub_base is not None else base)[c], errors="coerce")
        return (f"event_med {e.median():.4f}  base_med {b.median():.4f}  "
                f"e/b_mean {e.mean()/b.mean():.2f}  δ {cliffs_delta(e.to_numpy(float), b.to_numpy(float)):+.3f}")

    print(f"\n=== #21 CLOSE-vs-VWAP gap (avg_price, 2020+; event n_vwap>0={int((ev.n_vwap>0).sum())}) ===")
    evv = ev[ev.n_vwap >= 10]; basev = base[base.n_vwap >= 10]
    print("  cvwap_22 (all):", cmp("cvwap_22", evv, basev))
    med_dp = pd.to_numeric(base["deliv_per_22"], errors="coerce").median()
    loE = evv[pd.to_numeric(evv.deliv_per_22, errors="coerce") <= med_dp]
    loB = basev[pd.to_numeric(basev.deliv_per_22, errors="coerce") <= med_dp]
    print(f"  cvwap_22 | LOW-delivery regime (deliv_per_22<= {med_dp:.0f}): {cmp('cvwap_22', loE, loB)}")
    print(f"     (predicted: event closes ABOVE vwap → cvwap_22 > 0 and > baseline)")

    print("\n=== #16 trade-fragmentation TFR=num_trades/volume ===")
    print("  tfr_trend (recent/prior):", cmp("tfr_trend"))
    print("  tfr_recent (level):", cmp("tfr_recent"))

    print("\n=== #27 delivered-shares-per-trade ratio (recent10 / own 60d median) ===")
    print("  dpt_ratio:", cmp("dpt_ratio"))
    print("     (predicted: FALLING → dpt_ratio < 1 and < baseline)")
    rc.close()


if __name__ == "__main__":
    main()
