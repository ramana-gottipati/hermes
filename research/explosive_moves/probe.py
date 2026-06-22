"""Phase I — test the analyst panel's 4 surviving surprises on the real data.

Each test carries the controls the adversarial verifiers demanded.
A) CLP-on-flat-days  : close-location (close-low)/(high-low) over [s-20,s-1] on
   |ret|<1.5% days, event vs baseline, STRATIFIED BY LIQUIDITY, robust medians.
B) ticket dispersion : CV / max-over-median of value/num_trades AND price-free
   volume/num_trades over [s-20,s-1] — and the mean too (claim is "mean flat").
C) close-loc × ret_1d: Cliff's delta of close_strength_5 within ret_1d>=0 vs <0,
   and whether the combo beats an equal-coverage ret_1d cut (sustain study).
D) gap × range_pos   : reweighted lift 2x2, gap_1d high × range_pos low vs high,
   inside ret_22d terciles (defeat the momentum-stage confound).
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from .common import (research_conn, main_conn, eq_symbols, load_series, cliffs_delta, LIQ_FLOOR)

W = 20  # pre-window trading days


def _clp(ss):
    hl = ss.adj_high - ss.adj_low
    with np.errstate(divide="ignore", invalid="ignore"):
        clp = np.where(hl > 0, (ss.adj_close - ss.adj_low) / np.where(hl > 0, hl, np.nan), 0.5)
    return np.clip(clp, 0, 1)


def restream(rc):
    """Recompute the new derived features (A,B) for every monthly-event & baseline row."""
    rows = rc.execute("SELECT symbol,launch_date,etype,sustained,med_turn FROM features "
                      "WHERE etype IN ('monthly','baseline')").fetchall()
    bysym = {}
    for r in rows:
        bysym.setdefault(r["symbol"], []).append(dict(r))
    mc = main_conn()
    out = []
    for k, sym in enumerate(bysym):
        ss = load_series(mc, sym)
        if ss is None:
            continue
        dmap = {d: i for i, d in enumerate(ss.date)}
        clp = _clp(ss)
        with np.errstate(divide="ignore", invalid="ignore"):
            atv = np.where(ss.num_trades > 0, ss.value / np.where(ss.num_trades > 0, ss.num_trades, np.nan), np.nan)
            spt = np.where(ss.num_trades > 0, ss.volume / np.where(ss.num_trades > 0, ss.num_trades, np.nan), np.nan)
        for rec in bysym[sym]:
            s = dmap.get(rec["launch_date"])
            if s is None or s < W:
                continue
            sl = slice(s - W, s)
            rr = ss.ret_raw[sl]
            flat = np.abs(rr) < 0.015
            clw = clp[sl]
            d = dict(rec)
            # A: CLP overall + flat-day
            d["clp_all"] = float(np.nanmedian(clw))
            cf = clw[flat]
            d["clp_flat_med"] = float(np.nanmedian(cf)) if cf.size >= 5 else np.nan
            d["n_flat"] = int(np.sum(flat & ~np.isnan(clw)))
            if cf.size >= 5:
                x = np.arange(cf.size)
                good = ~np.isnan(cf)
                d["clp_flat_slope"] = float(np.polyfit(x[good], cf[good], 1)[0]) if good.sum() >= 3 else np.nan
            else:
                d["clp_flat_slope"] = np.nan
            # B: ticket dispersion
            a = atv[sl]; sp = spt[sl]
            am, sm = np.nanmean(a), np.nanmean(sp)
            d["atv_mean"] = float(am)
            d["cv_atv"] = float(np.nanstd(a) / am) if am else np.nan
            d["mdr_atv"] = float(np.nanmax(a) / np.nanmedian(a)) if np.nanmedian(a) else np.nan
            d["cv_spt"] = float(np.nanstd(sp) / sm) if sm else np.nan
            d["mdr_spt"] = float(np.nanmax(sp) / np.nanmedian(sp)) if np.nanmedian(sp) else np.nan
            out.append(d)
        if (k + 1) % 800 == 0:
            print(f"  ...{k+1} symbols", flush=True)
    mc.close()
    return pd.DataFrame(out)


def main():
    rc = research_conn()
    print("restreaming for CLP + ticket-dispersion (A,B)...", flush=True)
    df = restream(rc)
    ev = df[df.etype == "monthly"]; base = df[df.etype == "baseline"]

    print("\n=== A) CLP CLOSE-LOCATION on FLAT days (event vs baseline) ===")
    def med(x, c): return round(np.nanmedian(pd.to_numeric(x[c], errors="coerce")), 3)
    print(f"  CLP all-days   : event {med(ev,'clp_all')}  baseline {med(base,'clp_all')}")
    print(f"  CLP FLAT-days  : event {med(ev,'clp_flat_med')}  baseline {med(base,'clp_flat_med')}  "
          f"(cliffs δ {cliffs_delta(ev.clp_flat_med.to_numpy(float), base.clp_flat_med.to_numpy(float)):+.3f})")
    print(f"  CLP flat slope : event {med(ev,'clp_flat_slope')}  baseline {med(base,'clp_flat_slope')}")
    print("  by liquidity bucket (CLP flat median, event vs baseline):")
    for lo, hi, lab in [(1e7, 5e7, "1-5cr"), (5e7, 2.5e8, "5-25cr"), (2.5e8, 1e12, ">25cr")]:
        e = ev[(ev.med_turn >= lo) & (ev.med_turn < hi)]; b = base[(base.med_turn >= lo) & (base.med_turn < hi)]
        print(f"     {lab:7s} event {med(e,'clp_flat_med')} (n={len(e)})  baseline {med(b,'clp_flat_med')} (n={len(b)})")

    print("\n=== B) TICKET-SIZE DISPERSION (event vs baseline) ===")
    for c in ["atv_mean", "cv_atv", "mdr_atv", "cv_spt", "mdr_spt"]:
        e = pd.to_numeric(ev[c], errors="coerce"); b = pd.to_numeric(base[c], errors="coerce")
        print(f"  {c:9s}: event_med {e.median():.3f}  base_med {b.median():.3f}  e/b_mean {e.mean()/b.mean():.2f}  "
              f"δ {cliffs_delta(e.to_numpy(float), b.to_numpy(float)):+.3f}")
    print("  (claim needs CV up while atv_mean flat, AND price-free cv_spt to confirm)")

    # C + D from the features table directly
    f = pd.read_sql_query("SELECT etype,sustained,label,ret_1d,close_strength_5,gap_1d,range_pos_252,ret_22d,"
                          "med_turn FROM features WHERE etype IN ('monthly','baseline')", rc)
    fm = f[f.etype == "monthly"].copy()
    for c in ["sustained", "ret_1d", "close_strength_5", "gap_1d", "range_pos_252", "ret_22d"]:
        fm[c] = pd.to_numeric(fm[c], errors="coerce")
    print("\n=== C) close_strength_5 × ret_1d interaction for SUSTAIN ===")
    up = fm[fm.ret_1d >= 0]; dn = fm[fm.ret_1d < 0]
    print(f"  cliffs δ of close_strength_5 on sustain | ret_1d>=0 : "
          f"{cliffs_delta(up[up.sustained==1].close_strength_5.to_numpy(float), up[up.sustained==0].close_strength_5.to_numpy(float)):+.3f}")
    print(f"  cliffs δ of close_strength_5 on sustain | ret_1d<0  : "
          f"{cliffs_delta(dn[dn.sustained==1].close_strength_5.to_numpy(float), dn[dn.sustained==0].close_strength_5.to_numpy(float)):+.3f}")
    cs_hi = fm.close_strength_5 >= fm.close_strength_5.median()
    combo = (cs_hi & (fm.ret_1d >= 0))
    cov = combo.mean()
    ret_cut = fm.ret_1d >= fm.ret_1d.quantile(1 - cov)   # equal-coverage pure-ret_1d cut
    print(f"  sustain rate: combo(cs_hi & ret>=0)={fm[combo].sustained.mean():.3f} (cov {cov:.2f}) "
          f"vs equal-cov ret_1d cut={fm[ret_cut].sustained.mean():.3f}  base={fm.sustained.mean():.3f}")

    print("\n=== D) up-GAP × range_pos_252 (sustained-month lift, K=10), within ret_22d terciles ===")
    base_n = (f.etype == "baseline").sum()
    pos = fm[fm.sustained == 1]
    bdf = f[f.etype == "baseline"].copy()
    for c in ["gap_1d", "range_pos_252", "ret_22d"]:
        bdf[c] = pd.to_numeric(bdf[c], errors="coerce")
    K = 10.0
    terc = pos.ret_22d.quantile([1 / 3, 2 / 3]).tolist()
    def lift(mask_pos, mask_base):
        a = int(mask_pos.sum()); b = int(mask_base.sum())
        br = len(pos) / (len(pos) + K * base_n)
        return (a / (a + K * b) / br if (a + K * b) else np.nan), a
    gp = 0.012
    for tlo, thi, tlab in [(-9, terc[0], "lo-mom"), (terc[0], terc[1], "mid-mom"), (terc[1], 9, "hi-mom")]:
        pt = pos[(pos.ret_22d >= tlo) & (pos.ret_22d < thi)]; bt = bdf[(bdf.ret_22d >= tlo) & (bdf.ret_22d < thi)]
        for rlab, rmask_p, rmask_b in [("low-range", (pt.range_pos_252 <= 0.5), (bt.range_pos_252 <= 0.5)),
                                       ("top-range", (pt.range_pos_252 >= 0.94), (bt.range_pos_252 >= 0.94))]:
            l, a = lift((pt.gap_1d >= gp) & rmask_p, (bt.gap_1d >= gp) & rmask_b)
            print(f"  {tlab:7s} up-gap & {rlab:9s}: lift={l:.2f} n={a}")
    rc.close()


if __name__ == "__main__":
    main()
