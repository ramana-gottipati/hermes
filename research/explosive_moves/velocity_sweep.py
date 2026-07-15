"""VELOCITY-LEVEL SWEEP — find what a turnover/market-cap % bar does, at each level.

Gate = admit a name if velocity (median daily traded value / point-in-time market cap) >= X.
Sweep X from 0.05% to 1.0%/day. Also a self-relative gate (velocity >= 1.5x the name's own
trailing-12m median). Strategy held constant (variant D: RISKADJ + 50/50 PIT-quality blend,
top-25 monthly). Reports, per level: how many names qualify, the strategy metrics, the size mix
of picks, and how often PIXTRANS gets in. CHECK ONLY — prints numbers, draws no conclusion.

Market cap = (NetProfit/EPS) shares x raw close that day (report_date<=date, no look-ahead).

Ratios are mean/sd annualised with NO risk-free rate subtracted — return/vol, not Sharpe, so they
read high vs a textbook Sharpe; every level and the REF row sit on the SAME basis, so the
level-to-level comparison holds (D142).

Writes out/velocity_sweep.csv. Read-only.
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

RDB = "/opt/hermes/data/research.db"; HDB = "/opt/hermes/data/hermes.db"
REBAL, TOPN, BLEND_W = 22, 25, 0.50
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


def size_bucket(m):
    if m is None or not np.isfinite(m):
        return "unknown"
    return "large" if m >= 50000 else "mid" if m >= 10000 else "small" if m >= 1000 else "micro"


def main():
    cache = load_symbol_cache()
    dts, _ = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    ridx = list(range(0, len(cal), REBAL))
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}
    con = sqlite3.connect(RDB)
    frames = {s: fr for s in cache for fr in [load_frame(con, s)] if fr}
    con.close()
    H = sqlite3.connect(HDB)
    rebal_dates = [cal[k] for k in ridx]
    rawclose = {d0: {s: c for s, c in H.execute(
        "SELECT symbol,close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ' AND close IS NOT NULL", (d0,))}
        for d0 in rebal_dates}
    H.close()
    print(f"fundamentals {len(frames)}/{len(cache)}; raw close {len(rebal_dates)} dates", flush=True)

    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rc = rawclose.get(d0, {}); rec = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + REBAL, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            mom6 = ac[i0] / ac[i0 - 126] - 1.0; vol = float(F["vol_66"][i0])
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            turn = float(mt[i0]) if np.isfinite(mt[i0]) else 0.0
            fr = frames.get(s); sh = shares_cr(fr, d0) if fr else None; px = rc.get(s)
            mcap = (px * sh) if (sh is not None and px) else None
            vel = (turn / (mcap * 1e7)) if (mcap and mcap > 0) else np.nan
            roce, de, opm, ic = quality(fr, d0) if fr else (None, None, None, None)
            rec.append({"s": s, "turn": turn, "mcap": mcap, "vel": vel, "riskadj": mom6 / (vol + 1e-6),
                        "roce": roce, "de": de, "opm": opm, "ic": ic, "fwd": ac[i1] / ac[i0] - 1.0})
        if len(rec) >= TOPN + 5:
            tables.append({"d0": d0, "rec": rec})

    # self-relative baseline: each symbol's trailing-median velocity over prior up-to-12 rebalances
    hist = {}
    for ti, t in enumerate(tables):
        for x in t["rec"]:
            if np.isfinite(x["vel"]):
                hist.setdefault(x["s"], []).append((ti, x["vel"]))
    trailing = {}  # (ti, sym) -> trailing median vel
    for s, seq in hist.items():
        for j, (ti, v) in enumerate(seq):
            prev = [vv for (_, vv) in seq[max(0, j - 12):j]]
            if len(prev) >= 6:
                trailing[(ti, s)] = float(np.median(prev))

    print(f"{len(tables)} rebalances; velocity coverage = "
          f"{np.mean([np.mean([np.isfinite(x['vel']) for x in t['rec']]) for t in tables])*100:.0f}% of names have mcap\n", flush=True)

    def select_D(gated):
        if len(gated) < 5:
            return gated
        ra = pctrank(np.array([x["riskadj"] for x in gated]))
        rr = qrank([x["roce"] for x in gated]); dr = qrank([(-x["de"]) if x["de"] is not None else None for x in gated])
        opr = qrank([x["opm"] for x in gated]); icr = qrank([x["ic"] for x in gated])
        for k, x in enumerate(gated):
            comps = [c for c in (rr[k], dr[k], opr[k], icr[k]) if np.isfinite(c)]
            q = float(np.mean(comps)) if comps else 0.5
            x["_sc"] = (1 - BLEND_W) * ra[k] + BLEND_W * q
        return sorted(gated, key=lambda z: -z["_sc"])[:TOPN]

    def run(gate_label, gatefn):
        rets, dates, held, ns, bk, pix, mp = [], [], set(), [], {}, 0, []
        for ti, t in enumerate(tables):
            gated = gatefn(ti, t["rec"])
            ns.append(len(gated))
            picks = select_D(gated)
            if not picks:
                rets.append(0.0); dates.append(t["d0"]); continue
            gross = float(np.mean([p["fwd"] for p in picks])); pset = set(p["s"] for p in picks)
            turn = (len(pset - held) + len(held - pset)) / max(len(pset), 1)
            rets.append(gross - COST_PS * turn); dates.append(t["d0"]); held = pset
            for p in picks:
                bk[size_bucket(p["mcap"])] = bk.get(size_bucket(p["mcap"]), 0) + 1
                if p["mcap"]:
                    mp.append(p["mcap"])
            if "PIXTRANS" in pset:
                pix += 1
        rets = np.array(rets)
        full = eqstats(rets)
        m1 = np.array([d <= "2018-12-31" for d in dates]); m2 = np.array([d >= "2019-01-01" for d in dates])
        a, b = eqstats(rets[m1]), eqstats(rets[m2])
        tot = sum(bk.values()) or 1
        large = 100 * bk.get("large", 0) / tot
        midsm = 100 * (bk.get("mid", 0) + bk.get("small", 0) + bk.get("micro", 0)) / tot
        return {"gate": gate_label, "avg_universe": np.mean(ns),
                "retvol": full["retvol"], "maxdd": full["maxdd"], "cagr": full["cagr"], "calmar": full["calmar"],
                "h1": a["retvol"] if a else 0, "h2": b["retvol"] if b else 0, "totx": full["totx"],
                "large": large, "midsm": midsm, "med_mcap": float(np.median(mp)) if mp else float("nan"), "pix": pix}

    rows = []
    rows.append(run("REF value top-40%", lambda ti, rec: _value_gate(rec)))
    for X in (0.0005, 0.001, 0.002, 0.003, 0.005, 0.0075, 0.01):
        rows.append(run(f"velocity>= {X*100:.2f}%/day", (lambda thr: lambda ti, rec: [x for x in rec if np.isfinite(x["vel"]) and x["vel"] >= thr])(X)))
    rows.append(run("self-rel: vel>=1.5x own 12m-median",
                    lambda ti, rec: [x for x in rec if np.isfinite(x["vel"]) and (ti, x["s"]) in trailing and x["vel"] >= 1.5 * trailing[(ti, x["s"])]]))

    hdr = f"{'gate':34}{'univ':>6}{'ret/vol':>7}{'MaxDD':>8}{'CAGR':>7}{'Calmar':>7}{'H1':>5}{'H2':>5}{'lg%':>5}{'ms%':>5}{'medMcap':>10}{'PIX':>5}"
    print("=" * len(hdr)); print("VELOCITY-LEVEL SWEEP (strategy = variant D held constant). CHECK ONLY.")
    print("=" * len(hdr)); print(hdr)
    for r in rows:
        print(f"{r['gate']:34}{r['avg_universe']:>6.0f}{r['retvol']:>7.2f}{r['maxdd']*100:>7.1f}%{r['cagr']*100:>6.1f}%"
              f"{r['calmar']:>7.2f}{r['h1']:>5.2f}{r['h2']:>5.2f}{r['large']:>5.0f}{r['midsm']:>5.0f}{r['med_mcap']:>10,.0f}{r['pix']:>5}")

    with open(os.path.join(os.path.dirname(__file__), "out", "velocity_sweep.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gate", "avg_universe", "retvol", "maxdd_pct", "cagr_pct", "calmar", "h1_retvol", "h2_retvol",
                    "total_x", "picks_large_pct", "picks_mid_small_pct", "median_pick_mcap_cr", "pixtrans_rebalances"])
        for r in rows:
            w.writerow([r["gate"], round(r["avg_universe"], 0), round(r["retvol"], 2), round(r["maxdd"] * 100, 1),
                        round(r["cagr"] * 100, 1), round(r["calmar"], 2), round(r["h1"], 2), round(r["h2"], 2),
                        round(r["totx"], 1), round(r["large"], 0), round(r["midsm"], 0), round(r["med_mcap"], 0), r["pix"]])
    print("\nsaved -> out/velocity_sweep.csv")


def _value_gate(rec):
    tp = pctrank(np.array([y["turn"] for y in rec]))
    return [x for i, x in enumerate(rec) if tp[i] >= 0.60]


if __name__ == "__main__":
    main()
