"""FACTOR ZOO — backtest the well-known market factors on our data, ranked by Sharpe.

Decodes the public factor strategies a quant desk would know and tests each the SAME way:
top-25 monthly, equal-weight, value-relative gate (top-40% turnover), net cost, walk-forward
(2012-18 & 2019-26), no look-ahead. These are NON-PROPRIETARY known factors — recorded as a
separate registry from our proprietary components.

Factors: MOM6, MOM12, RISKADJ(mom/vol), LOWVOL, LOWBETA(BAB), RESID_MOM(idiosyncratic),
HI52(52-wk-high), EARN_YIELD(E/P), BOOK_YIELD(B/P), QUALITY, and blends QUAL_MOM, VAL_MOM,
DEFENSIVE(lowvol+quality), QMV(quality+mom+value), LOWVOL_MOM.

Market cap / earnings / book are point-in-time (report_date<=date). Writes out/factor_zoo.csv.
Read-only.
"""
from __future__ import annotations
import csv
import os
import sqlite3
import numpy as np
import sys
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series
from explosive_moves.factory import eqstats, pctrank, COST_PS

RDB = "/opt/hermes/data/research.db"; HDB = "/opt/hermes/data/hermes.db"
REBAL, TOPN, GATE_PCTL, W = 22, 25, 0.60, 252
_ROCE = ("ROCE %", "Financing Margin %"); _OPM = ("OPM %", "Financing Margin %")
_BORROW = ("Borrowings", "Borrowing")


def load_frame(con, s):
    fr = {}
    for pt, m, pe, rd, v in con.execute(
        "SELECT period_type,metric,period_end,report_date,value FROM fundamentals_history "
        "WHERE symbol=? AND value IS NOT NULL", (s,)):
        fr.setdefault((pt, m), []).append((pe, rd, v))
    return fr


def latest(fr, pt, names, asof):
    for nm in (names if isinstance(names, tuple) else (names,)):
        vals = [(pe, v) for (pe, rd, v) in fr.get((pt, nm), []) if rd <= asof]
        if vals:
            return max(vals, key=lambda t: t[0])[1]
    return None


def roll_mean(x, w):
    n = len(x); out = np.full(n, np.nan)
    if n < w:
        return out
    c = np.concatenate(([0.0], np.cumsum(np.nan_to_num(x, nan=0.0))))
    k = np.concatenate(([0.0], np.cumsum(~np.isnan(x))))
    s = c[w:] - c[:-w]; cnt = k[w:] - k[:-w]
    with np.errstate(invalid="ignore", divide="ignore"):
        out[w - 1:] = np.where(cnt > 0, s / cnt, np.nan)
    return out


def fundamentals(fr, asof):
    roce = latest(fr, "A", _ROCE, asof); opm = latest(fr, "A", _OPM, asof)
    borrow = latest(fr, "A", _BORROW, asof); eqc = latest(fr, "A", "Equity Capital", asof)
    res = latest(fr, "A", "Reserves", asof); op = latest(fr, "A", "Operating Profit", asof)
    intr = latest(fr, "A", "Interest", asof); eps = latest(fr, "A", "EPS in Rs", asof)
    npr = latest(fr, "A", "Net Profit", asof)
    nw = (eqc + res) if (eqc is not None and res is not None) else None
    de = (borrow / nw) if (borrow is not None and nw and nw > 0) else None
    ic = (op / intr) if (op is not None and intr and intr > 0) else None
    # CL-RES-13: PIT share count = NetProfit / EPS is numerically unstable as EPS -> 0:
    # an EPS of Rs 0.11 (or a year of near-break-even earnings) blows the implied share
    # count up by orders of magnitude, which then propagates into mcap -> velocity /
    # book-yield gates as noise. Widen the EPS floor from |eps|>0.1 to |eps|>=1.0 (below
    # Re 1/share the derivation is not trustworthy) and require the result to be finite.
    # Where EPS is too small to trust, leave sh=None so downstream gates treat mcap as
    # missing rather than ingesting a fabricated outlier.
    sh = None
    if eps is not None and npr is not None and abs(eps) >= 1.0:
        cand = npr / eps
        if np.isfinite(cand) and cand > 0:
            sh = cand
    return {"roce": roce, "de": de, "opm": opm, "ic": ic, "eps": eps, "nw": nw, "sh": sh}


def pr(vals):
    return pctrank(np.array([v if v is not None else np.nan for v in vals], float))


def main():
    cache = load_symbol_cache()
    dts, icl = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    ridx = list(range(0, len(cal), REBAL))
    # index daily returns + close, by date
    idx_close = {d: icl[i] for i, d in enumerate(dts)}
    idx_ret = {dts[i]: (icl[i] / icl[i - 1] - 1.0) for i in range(1, len(dts)) if icl[i - 1] > 0}
    idx_pos = {d: i for i, d in enumerate(dts)}

    con = sqlite3.connect(RDB)
    frames = {s: fr for s in cache for fr in [load_frame(con, s)] if fr}
    con.close()
    H = sqlite3.connect(HDB)
    rebal_dates = [cal[k] for k in ridx]
    rawclose = {d0: {s: c for s, c in H.execute(
        "SELECT symbol,close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ' AND close IS NOT NULL", (d0,))}
        for d0 in rebal_dates}
    H.close()

    # precompute per-symbol beta arrays (trailing-W vs Nifty 50)
    P = {}
    for s, A in cache.items():
        dates = A["date"]; ac = A["adj_close"]; n = len(ac)
        g = np.full(n, np.nan); g[1:] = ac[1:] / np.clip(ac[:-1], 1e-9, None) - 1.0
        ig = np.array([idx_ret.get(d, np.nan) for d in dates])
        mx, my = roll_mean(g, W), roll_mean(ig, W)
        mxy, myy = roll_mean(g * ig, W), roll_mean(ig * ig, W)
        cov = mxy - mx * my; var = myy - my * my
        with np.errstate(invalid="ignore", divide="ignore"):
            beta = np.where(var > 1e-12, cov / var, np.nan)
        P[s] = ({d: i for i, d in enumerate(dates)}, ac, A["med_turn"], A["feats"], beta,
                A["adj_high"], A["adj_low"])
    print(f"cache {len(cache)}, fundamentals {len(frames)}, betas built", flush=True)

    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rc = rawclose.get(d0, {}); rec = []
        j = idx_pos.get(d0)
        idx_mom6 = (idx_close[d0] / icl[j - 126] - 1.0) if (j is not None and j >= 126) else np.nan
        for s, (d2i, ac, mt, F, beta, ah, al) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + REBAL, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0 and i1 > i0):
                continue
            entry = ac[i0]
            hw_hi, hw_lo = ah[i0 + 1:i1 + 1], al[i0 + 1:i1 + 1]
            mfe = (float(np.max(hw_hi)) / entry - 1.0) if len(hw_hi) else np.nan      # peak favourable move while held
            mae = (float(np.min(hw_lo)) / entry - 1.0) if len(hw_lo) else np.nan      # worst dip while held
            mom6 = ac[i0] / ac[i0 - 126] - 1.0
            mom12 = ac[i0] / ac[i0 - 252] - 1.0 if i0 >= 252 else np.nan
            vol = float(F["vol_66"][i0]); bt = float(beta[i0]) if np.isfinite(beta[i0]) else np.nan
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            fr = frames.get(s); fd = fundamentals(fr, d0) if fr else None
            px = rc.get(s)
            ey = (fd["eps"] / px) if (fd and fd["eps"] is not None and px) else None
            mcap = (px * fd["sh"]) if (fd and fd["sh"] and px) else None
            by = (fd["nw"] / mcap) if (fd and fd["nw"] is not None and mcap and mcap > 0) else None
            resid = (mom6 - bt * idx_mom6) if (np.isfinite(bt) and np.isfinite(idx_mom6)) else np.nan
            rec.append({
                "s": s, "turn": float(mt[i0]) if np.isfinite(mt[i0]) else 0.0, "fwd": ac[i1] / ac[i0] - 1.0,
                "mom6": mom6, "mom12": mom12, "riskadj": mom6 / (vol + 1e-6), "lowvol": -vol,
                "lowbeta": (-bt) if np.isfinite(bt) else np.nan, "resid": resid,
                "hi52": float(F["range_pos_252"][i0]) if np.isfinite(F["range_pos_252"][i0]) else np.nan,
                "ey": ey, "by": by,
                "roce": fd["roce"] if fd else None, "de": fd["de"] if fd else None,
                "opm": fd["opm"] if fd else None, "ic": fd["ic"] if fd else None,
                "mfe": mfe, "mae": mae})
        if len(rec) < TOPN + 5:
            continue
        tp = pctrank(np.array([x["turn"] for x in rec]))
        gated = [x for i, x in enumerate(rec) if tp[i] >= GATE_PCTL]
        # precompute cross-sectional ranks within the gate
        qn = np.array([np.nanmean([a, b, c, d]) for a, b, c, d in zip(
            pr([x["roce"] for x in gated]), pr([(-x["de"]) if x["de"] is not None else None for x in gated]),
            pr([x["opm"] for x in gated]), pr([x["ic"] for x in gated]))])
        val = np.array([np.nanmean([a, b]) for a, b in zip(pr([x["ey"] for x in gated]), pr([x["by"] for x in gated]))])
        m6 = pr([x["mom6"] for x in gated])
        lv = pr([x["lowvol"] for x in gated])
        for k, x in enumerate(gated):
            x["q"] = qn[k] if np.isfinite(qn[k]) else 0.5
            x["val"] = val[k] if np.isfinite(val[k]) else 0.5
            x["m6r"] = m6[k]; x["lvr"] = lv[k]
        tables.append({"d0": d0, "d1": d1, "gated": gated})

    print(f"{len(tables)} rebalances\n", flush=True)

    FACTORS = {
        "MOM6": lambda x: x["mom6"], "MOM12": lambda x: x["mom12"], "RISKADJ": lambda x: x["riskadj"],
        "LOWVOL": lambda x: x["lowvol"], "LOWBETA(BAB)": lambda x: x["lowbeta"], "RESID_MOM": lambda x: x["resid"],
        "HI52": lambda x: x["hi52"], "EARN_YIELD": lambda x: x["ey"], "BOOK_YIELD": lambda x: x["by"],
        "QUALITY": lambda x: x["q"],
        "QUAL_MOM": lambda x: 0.5 * x["q"] + 0.5 * x["m6r"],
        "VAL_MOM": lambda x: 0.5 * x["val"] + 0.5 * x["m6r"],
        "DEFENSIVE(lowvol+qual)": lambda x: 0.5 * x["lvr"] + 0.5 * x["q"],
        "QMV(qual+mom+val)": lambda x: (x["q"] + x["m6r"] + x["val"]) / 3.0,
        "LOWVOL_MOM": lambda x: 0.5 * x["lvr"] + 0.5 * x["m6r"],
    }

    # benchmark (Nifty 500) return for each rebalance period, aligned to `tables`
    bdts, bcl = index_series("Nifty 500")
    bclose = {d: bcl[i] for i, d in enumerate(bdts)}
    bench = np.array([((bclose.get(t["d1"], np.nan) / bclose[t["d0"]] - 1.0)
                       if (t["d0"] in bclose and t["d1"] in bclose and bclose[t["d0"]] > 0) else np.nan)
                      for t in tables])
    SQ = np.sqrt(12.0)

    def run(scorefn):
        rets, turns, allpf, allmfe, allmae, dates, held = [], [], [], [], [], [], set()
        for t in tables:
            g = [x for x in t["gated"] if (lambda v: v is not None and np.isfinite(v))(scorefn(x))]
            dates.append(t["d0"])
            if len(g) < 5:
                rets.append(0.0); turns.append(0.0); continue
            picks = sorted(g, key=lambda x: -scorefn(x))[:TOPN]
            gross = float(np.mean([p["fwd"] for p in picks])); pset = set(p["s"] for p in picks)
            turn = (len(pset - held) + len(held - pset)) / max(len(pset), 1)
            rets.append(gross - COST_PS * turn); turns.append(turn); held = pset
            allpf.extend(p["fwd"] for p in picks)
            allmfe.extend(p["mfe"] for p in picks); allmae.extend(p["mae"] for p in picks)
        return np.array(rets), np.array(turns), np.array(allpf), np.array(allmfe), np.array(allmae), dates

    def tearsheet(rets, turns, allpf, allmfe, allmae, dates):
        n = len(rets); eq = np.cumprod(1 + rets); dd = eq / np.maximum.accumulate(eq) - 1
        sd = rets.std(); dn = rets[rets < 0]; dsd = dn.std() if len(dn) > 1 else 0.0
        pos, neg = rets[rets > 0], rets[rets < 0]
        maxdd = float(dd.min()); cagr = eq[-1] ** (12.0 / n) - 1
        m = np.isfinite(bench) & np.isfinite(rets)
        if m.sum() > 3 and bench[m].std() > 0:
            rc = rets[m] - rets[m].mean(); bc = bench[m] - bench[m].mean()
            beta = float((rc * bc).mean() / (bc * bc).mean())
            alpha = float((rets[m].mean() - beta * bench[m].mean()) * 12)
        else:
            beta = alpha = float("nan")
        h1 = np.array([d <= "2018-12-31" for d in dates]); h2 = np.array([d >= "2019-01-01" for d in dates])
        sh = lambda r: (r.mean() / r.std() * SQ) if r.std() > 0 else 0.0
        s1, s2 = sh(rets[h1]), sh(rets[h2])
        # trade-quality: peak move available (MFE), worst dip (MAE), and % of the peak we kept
        mfe_f = np.isfinite(allmfe); mae_f = np.isfinite(allmae)
        avg_mfe = float(allmfe[mfe_f].mean()) if mfe_f.any() else float("nan")
        avg_mae = float(allmae[mae_f].mean()) if mae_f.any() else float("nan")
        fin = np.isfinite(allmfe) & np.isfinite(allpf)
        # aggregate capture: total realised return as a fraction of the total peak move available
        capture = float(allpf[fin].mean() / allmfe[fin].mean()) if (fin.any() and allmfe[fin].mean() > 0) else float("nan")
        # winner capture: among positions that ended UP, what % of their own peak did they keep
        wm = fin & (allmfe > 0.005) & (allpf > 0)
        wcapture = float(np.mean(np.clip(allpf[wm] / allmfe[wm], 0, 1))) if wm.any() else float("nan")
        edge = (avg_mfe / abs(avg_mae)) if (np.isfinite(avg_mae) and avg_mae < 0) else float("nan")
        return {
            "sharpe": sh(rets), "sortino": (rets.mean() / dsd * SQ) if dsd > 0 else 0.0,
            "cagr": cagr, "vol": sd * SQ, "maxdd": maxdd, "calmar": cagr / abs(maxdd) if maxdd < 0 else 0.0,
            "win": len(pos) / n, "pf": (pos.sum() / abs(neg.sum())) if neg.sum() != 0 else float("inf"),
            "payoff": (pos.mean() / abs(neg.mean())) if (len(pos) and len(neg)) else float("nan"),
            "poshit": float(np.mean(allpf > 0)) if len(allpf) else float("nan"),
            "pos_payoff": (allpf[allpf > 0].mean() / abs(allpf[allpf < 0].mean()))
            if (np.any(allpf > 0) and np.any(allpf < 0)) else float("nan"),
            "beta": beta, "alpha": alpha, "best": float(rets.max()), "worst": float(rets.min()),
            "turn": float(np.mean(turns)), "h1": s1, "h2": s2,
            "mfe": avg_mfe, "mae": avg_mae, "capture": capture, "wcapture": wcapture, "edge": edge,
            "surv": bool(s1 > 0.89 and s2 > 0.89)}

    rows = []
    for name, fn in FACTORS.items():
        rets, turns, allpf, allmfe, allmae, dates = run(fn)
        rows.append((name, tearsheet(rets, turns, allpf, allmfe, allmae, dates)))
    rows.sort(key=lambda r: -r[1]["sharpe"])

    hdr = (f"{'factor':24}{'Shrp':>6}{'Sort':>6}{'MaxDD':>8}{'Win%':>6}{'PF':>6}{'PosHit':>8}"
           f"{'MFE%':>6}{'Cap%':>6}{'WCap%':>7}{'MAE%':>7}{'Beta':>6}{'Alpha':>7}  surv")
    print("=" * len(hdr))
    print("FACTOR ZOO — institutional tearsheet (top-25 monthly, value-gate, net cost, walk-forward).")
    print("Win%=positive months | PF=profit factor | PosHit=% winning positions | MFE%=avg peak move available while held |")
    print("Cap%=realised ÷ peak (aggregate) | WCap%=winners' capture of own peak | MAE%=avg worst dip | Alpha=ann vs Nifty500")
    print("=" * len(hdr)); print(hdr)
    for name, s in rows:
        pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
        print(f"{name:24}{s['sharpe']:>6.2f}{s['sortino']:>6.2f}{s['maxdd']*100:>7.1f}%"
              f"{s['win']*100:>5.0f}%{pf:>6}{s['poshit']*100:>7.0f}%"
              f"{s['mfe']*100:>6.1f}{s['capture']*100:>6.0f}{s['wcapture']*100:>7.0f}{s['mae']*100:>7.1f}"
              f"{s['beta']:>6.2f}{s['alpha']*100:>6.1f}%   {'YES' if s['surv'] else ''}")

    with open(os.path.join(os.path.dirname(__file__), "out", "factor_zoo.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["factor", "sharpe", "sortino", "cagr_pct", "vol_ann_pct", "maxdd_pct", "calmar",
                    "win_rate_months_pct", "profit_factor", "payoff_win_over_loss", "position_hit_rate_pct",
                    "position_payoff", "avg_mfe_pct", "capture_pct_aggregate", "winner_capture_pct",
                    "avg_mae_pct", "edge_ratio_mfe_over_mae",
                    "beta_nifty500", "alpha_ann_pct", "best_month_pct", "worst_month_pct",
                    "avg_turnover", "h1_sharpe", "h2_sharpe", "survives_both_halves"])
        for name, s in rows:
            w.writerow([name, round(s["sharpe"], 2), round(s["sortino"], 2), round(s["cagr"] * 100, 1),
                        round(s["vol"] * 100, 1), round(s["maxdd"] * 100, 1), round(s["calmar"], 2),
                        round(s["win"] * 100, 0), ("inf" if s["pf"] == float("inf") else round(s["pf"], 2)),
                        round(s["payoff"], 2), round(s["poshit"] * 100, 0), round(s["pos_payoff"], 2),
                        round(s["mfe"] * 100, 1), round(s["capture"] * 100, 0), round(s["wcapture"] * 100, 0),
                        round(s["mae"] * 100, 1), round(s["edge"], 2), round(s["beta"], 2), round(s["alpha"] * 100, 1),
                        round(s["best"] * 100, 1), round(s["worst"] * 100, 1), round(s["turn"], 2),
                        round(s["h1"], 2), round(s["h2"], 2), "YES" if s["surv"] else "NO"])
    print("\nsaved -> out/factor_zoo.csv")


if __name__ == "__main__":
    main()
