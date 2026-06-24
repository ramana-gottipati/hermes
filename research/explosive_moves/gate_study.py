"""GATE STUDY — is the liquidity gate large-cap biased, and does a size-neutral
(turnover/market-cap velocity) gate fix it without wrecking the strategy?

Validates two claims, with data:
  (1) "top-X%-by-traded-VALUE" is a large-cap filter (excludes quality midcaps like PIXTRANS).
  (2) a turnover/MARKET-CAP velocity gate is size-neutral and includes them.

Market cap is point-in-time: shares = NetProfit/EPS (latest annual known, report_date<=date;
sign-robust since EPS=NP/shares) x RAW close that day. Turnover = value (Rs), never share count.

Strategy held constant = variant D (RISKADJ + 50/50 PIT-quality blend, top-25 monthly) so only the
GATE changes. Walk-forward, net cost, no look-ahead. Writes out/gate_study.csv. Read-only.
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
from explosive_moves.factory import eqstats, pctrank, COST_PS, CR

RDB = "/opt/hermes/data/research.db"
HDB = "/opt/hermes/data/hermes.db"
REBAL, TOPN, LIQ_PCTL, BLEND_W = 22, 25, 0.60, 0.50
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


def shares_cr(fr, asof):
    np_ = latest(fr, "A", "Net Profit", asof); eps = latest(fr, "A", "EPS in Rs", asof)
    if np_ is not None and eps is not None and abs(eps) > 0.1:
        sh = np_ / eps
        return sh if sh > 0 else None
    return None


def quality(fr, asof):
    roce = latest(fr, "A", _ROCE, asof); opm = latest(fr, "A", _OPM, asof)
    borrow = latest(fr, "A", _BORROW, asof); eqc = latest(fr, "A", "Equity Capital", asof)
    res = latest(fr, "A", "Reserves", asof); op = latest(fr, "A", "Operating Profit", asof)
    intr = latest(fr, "A", "Interest", asof)
    nw = (eqc + res) if (eqc is not None and res is not None) else None
    de = (borrow / nw) if (borrow is not None and nw and nw > 0) else None
    ic = (op / intr) if (op is not None and intr and intr > 0) else None
    return roce, de, opm, ic


def qrank(vals):
    return pctrank(np.array([v if v is not None else np.nan for v in vals], float))


def size_bucket(mcap_cr):
    if mcap_cr is None or not np.isfinite(mcap_cr):
        return "unknown"
    if mcap_cr >= 50000:
        return "large(>50k cr)"
    if mcap_cr >= 10000:
        return "mid(10-50k)"
    if mcap_cr >= 1000:
        return "small(1-10k)"
    return "micro(<1k)"


def main():
    cache = load_symbol_cache()
    dts, _ = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    ridx = list(range(0, len(cal), REBAL))
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}

    con = sqlite3.connect(RDB)
    frames = {s: load_frame(con, s) for s in cache}
    frames = {s: fr for s, fr in frames.items() if fr}
    con.close()
    print(f"fundamentals for {len(frames)}/{len(cache)} symbols", flush=True)

    # bulk raw close at each rebalance date (for point-in-time market cap)
    H = sqlite3.connect(HDB)
    rebal_dates = [cal[k] for k in ridx]
    rawclose = {}
    for d0 in rebal_dates:
        rawclose[d0] = {s: c for s, c in H.execute(
            "SELECT symbol,close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ' AND close IS NOT NULL", (d0,))}
    H.close()
    print(f"raw close loaded for {len(rebal_dates)} rebalance dates", flush=True)

    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rc = rawclose.get(d0, {})
        rec = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + REBAL, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            mom6 = ac[i0] / ac[i0 - 126] - 1.0
            vol = float(F["vol_66"][i0])
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            turn = float(mt[i0]) if np.isfinite(mt[i0]) else 0.0
            fr = frames.get(s)
            sh = shares_cr(fr, d0) if fr else None
            px = rc.get(s)
            mcap = (px * sh) if (sh is not None and px) else None       # Rs cr
            vel = (turn / (mcap * 1e7)) if (mcap and mcap > 0) else np.nan
            roce, de, opm, ic = quality(fr, d0) if fr else (None, None, None, None)
            rec.append({"s": s, "turn": turn, "mcap": mcap, "vel": vel, "riskadj": mom6 / (vol + 1e-6),
                        "roce": roce, "de": de, "opm": opm, "ic": ic, "fwd": ac[i1] / ac[i0] - 1.0})
        if len(rec) < TOPN + 5:
            continue
        # rank helpers across full record this date
        for k, x in enumerate(rec):
            x["turn_pr"] = 0.0
        tp = pctrank(np.array([x["turn"] for x in rec]))
        vp = pctrank(np.array([x["vel"] for x in rec]))
        for k, x in enumerate(rec):
            x["turn_pr"], x["vel_pr"] = tp[k], vp[k]
        tables.append({"d0": d0, "rec": rec})

    print(f"{len(tables)} usable rebalance dates\n", flush=True)

    # ---- gates ----
    def g_static(rec):   return [x for x in rec if x["turn"] >= 5 * CR]
    def g_value(rec):    return [x for x in rec if x["turn_pr"] >= LIQ_PCTL]
    def g_velocity(rec): return [x for x in rec if np.isfinite(x["vel_pr"]) and x["vel_pr"] >= LIQ_PCTL]
    def g_vel_floor(rec):return [x for x in rec if np.isfinite(x["vel_pr"]) and x["vel_pr"] >= LIQ_PCTL and x["turn"] >= 1 * CR]

    GATES = {"static_5cr": g_static, "value_top40": g_value, "velocity_top40": g_velocity,
             "velocity_top40_floor1cr": g_vel_floor}

    # ---- selector: variant D (riskadj + 50/50 quality blend) within a gate ----
    def select_D(gated):
        if len(gated) < TOPN:
            return gated
        ra = pctrank(np.array([x["riskadj"] for x in gated]))
        rr = qrank([x["roce"] for x in gated]); dr = qrank([(-x["de"]) if x["de"] is not None else None for x in gated])
        opr = qrank([x["opm"] for x in gated]); icr = qrank([x["ic"] for x in gated])
        for k, x in enumerate(gated):
            comps = [c for c in (rr[k], dr[k], opr[k], icr[k]) if np.isfinite(c)]
            q = float(np.mean(comps)) if comps else 0.5
            x["_sc"] = (1 - BLEND_W) * ra[k] + BLEND_W * q
        return sorted(gated, key=lambda z: -z["_sc"])[:TOPN]

    def run(gatefn):
        rets, dates, held = [], [], set()
        bucket_counts, pix_hits, mcaps_pick = {}, 0, []
        for t in tables:
            gated = gatefn(t["rec"])
            picks = select_D(gated)
            if not picks:
                rets.append(0.0); dates.append(t["d0"]); continue
            gross = float(np.mean([p["fwd"] for p in picks]))
            pset = set(p["s"] for p in picks)
            turn = (len(pset - held) + len(held - pset)) / max(len(pset), 1)
            rets.append(gross - COST_PS * turn); dates.append(t["d0"]); held = pset
            for p in picks:
                bucket_counts[size_bucket(p["mcap"])] = bucket_counts.get(size_bucket(p["mcap"]), 0) + 1
                if p["mcap"]:
                    mcaps_pick.append(p["mcap"])
            if "PIXTRANS" in pset:
                pix_hits += 1
        return np.array(rets), dates, bucket_counts, pix_hits, mcaps_pick

    out_rows = []
    for gname, gfn in GATES.items():
        rets, dates, bk, pix, mcaps = run(gfn)
        full = eqstats(rets)
        m1 = np.array([d <= "2018-12-31" for d in dates]); m2 = np.array([d >= "2019-01-01" for d in dates])
        a, b = eqstats(rets[m1]), eqstats(rets[m2])
        tot = sum(bk.values()) or 1
        med_mcap = float(np.median(mcaps)) if mcaps else float("nan")
        large_pct = 100 * (bk.get("large(>50k cr)", 0)) / tot
        midsmall_pct = 100 * (bk.get("mid(10-50k)", 0) + bk.get("small(1-10k)", 0) + bk.get("micro(<1k)", 0)) / tot
        print(f"=== GATE: {gname} ===")
        print(f"  strategy(D): CAGR {full['cagr']*100:5.1f}%  MaxDD {full['maxdd']*100:6.1f}%  Sharpe {full['sharpe']:.2f}  "
              f"Calmar {full['calmar']:.2f}  ({full['totx']:.1f}x)  H1 {a['sharpe']:.2f} / H2 {b['sharpe']:.2f}")
        print(f"  picks size mix: large {large_pct:.0f}% | mid+small+micro {midsmall_pct:.0f}% | median pick mcap Rs {med_mcap:,.0f} cr")
        print(f"  bucket counts: {bk}")
        print(f"  PIXTRANS appeared in {pix} / {len(tables)} rebalances\n")
        out_rows.append([gname, round(full["cagr"]*100,1), round(full["maxdd"]*100,1), round(full["sharpe"],2),
                         round(full["calmar"],2), round(full["totx"],1), round(a["sharpe"],2), round(b["sharpe"],2),
                         round(large_pct,0), round(midsmall_pct,0), round(med_mcap,0), pix])

    with open(os.path.join(os.path.dirname(__file__), "out", "gate_study.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gate", "cagr_pct", "maxdd_pct", "sharpe", "calmar", "total_x", "h1_sharpe", "h2_sharpe",
                    "picks_large_pct", "picks_mid_small_micro_pct", "median_pick_mcap_cr", "pixtrans_rebalances"])
        w.writerows(out_rows)
    print("saved -> out/gate_study.csv")


if __name__ == "__main__":
    main()
