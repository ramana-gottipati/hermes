"""Phase 2 — refine around the winner (mom12 top-10 5cr, 48% CAGR / -36% DD).
Add volatility-targeting (cut the drawdown), a mom12+riskadj blend, a valuation filter,
and finer concentration. Caches the rebalance tables to disk for fast overnight reuse.

The risk-adjusted column is mean/sd annualised with NO risk-free rate subtracted — a
return/vol ratio, not a Sharpe, and it reads high against a textbook one. A true Sharpe
needs a primary-source rf ingest (Guardrail #8), queued with the TR-benchmark re-cut. (D142)"""
import os, pickle
import numpy as np
from collections import deque
from explosive_moves.embase import load_symbol_cache
from explosive_moves.strategies import CR
from explosive_moves.metrics import index_series

CPS = 0.005
TBL_PKL = "/opt/hermes/data/search_tbl.pkl"


def pr(x):
    r = np.full(len(x), np.nan); m = ~np.isnan(x)
    if m.sum() > 1:
        r[m] = np.argsort(np.argsort(x[m])) / (m.sum() - 1)
    return r


def build_tbl():
    if os.path.exists(TBL_PKL):
        return pickle.load(open(TBL_PKL, "rb"))
    cache = load_symbol_cache()
    D2I = {s: {d: i for i, d in enumerate(A["date"])} for s, A in cache.items()}
    dts, _ = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]; ri = list(range(0, len(cal), 22))
    TBL = []
    for r in range(len(ri) - 1):
        d0, d1 = cal[ri[r]], cal[ri[r + 1]]
        R = {"d0": d0, "sym": [], "mt": [], "mom6": [], "mom12": [], "vol": [], "deliv": [], "ext5y": [], "fwd": []}
        for s, A in cache.items():
            i0 = D2I[s].get(d0)
            if i0 is None or i0 < 260 or not (A["med_turn"][i0] >= 1 * CR):
                continue
            ac = A["adj_close"]; i1 = D2I[s].get(d1, min(i0 + 22, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            F = A["feats"]; v = F["vol_66"][i0]; m6 = ac[i0] / ac[i0 - 126] - 1 if i0 >= 126 else np.nan
            if v != v or v <= 0 or m6 != m6:
                continue
            R["sym"].append(s); R["mt"].append(A["med_turn"][i0]); R["mom6"].append(m6)
            R["mom12"].append(ac[i0] / ac[i0 - 252] - 1 if i0 >= 252 else np.nan)
            R["vol"].append(v); R["deliv"].append(F["deliv_qty_trend"][i0])
            R["ext5y"].append(ac[i0] / ac[i0 - 1250] - 1 if i0 >= 1250 else np.nan)
            R["fwd"].append(ac[i1] / ac[i0] - 1)
        for k in R:
            if k != "d0":
                R[k] = np.array(R[k])
        TBL.append(R)
    pickle.dump(TBL, open(TBL_PKL, "wb"))
    return TBL


TBL = build_tbl()


def score(t, sig):
    if sig == "mom12":   return t["mom12"]
    if sig == "riskadj": return t["mom6"] / (t["vol"] + 1e-6)
    if sig == "blend":   return 0.5 * pr(t["mom12"]) + 0.5 * pr(t["mom6"] / (t["vol"] + 1e-6))


def stats(rets):
    rets = np.array(rets)
    eq = np.cumprod(1 + rets); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1).min()
    yrs = len(eq) / 12; cagr = eq[-1] ** (1 / yrs) - 1; sd = rets.std()
    return cagr, dd, (rets.mean() / sd * np.sqrt(12) if sd > 0 else 0)


def bt(sig, floor, topn, lo, hi, vt=None, valfilt=False):
    rets, prev, vh = [], set(), deque(maxlen=6)
    for t in TBL:
        if not (lo <= t["d0"] <= hi):
            continue
        sc = score(t, sig)
        mask = t["mt"] >= floor
        if valfilt:
            mask = mask & (np.isnan(t["ext5y"]) | (t["ext5y"] < 2))
        sc = np.where(mask, sc, np.nan)
        valid = ~np.isnan(sc) & ~np.isnan(t["fwd"]); idx = np.where(valid)[0]
        if len(idx) < topn:
            rets.append(0.0); continue
        top = idx[np.argsort(sc[idx])[::-1]][:topn]; picks = set(t["sym"][i] for i in top)
        g = float(np.mean(t["fwd"][top])); turn = (len(picks - prev) + len(prev - picks)) / max(len(picks), 1)
        net = g - CPS * turn
        if vt and len(vh) >= 3:
            rv = np.std(vh) * np.sqrt(12)
            net *= min(1.0, max(0.3, vt / rv)) if rv > 0 else 1.0
        rets.append(net); vh.append(g); prev = picks
    return stats(rets)


configs = [
    ("mom12 top10 (base)", dict(sig="mom12", topn=10)),
    ("mom12 top8", dict(sig="mom12", topn=8)),
    ("mom12 top12", dict(sig="mom12", topn=12)),
    ("mom12 top10 +VT0.30", dict(sig="mom12", topn=10, vt=0.30)),
    ("mom12 top10 +VT0.25", dict(sig="mom12", topn=10, vt=0.25)),
    ("mom12 top10 +VT0.20", dict(sig="mom12", topn=10, vt=0.20)),
    ("blend top10", dict(sig="blend", topn=10)),
    ("blend top10 +VT0.25", dict(sig="blend", topn=10, vt=0.25)),
    ("mom12 top10 +valuation", dict(sig="mom12", topn=10, valfilt=True)),
    ("mom12 top10 +val +VT0.25", dict(sig="mom12", topn=10, vt=0.25, valfilt=True)),
]
print(f"{'config':28}{'CAGR19':>8}{'MaxDD19':>9}{'ret/vol':>7}{'CAGR12-18':>10}")
for name, kw in configs:
    c19, dd19, sh = bt(floor=5 * CR, lo="2019-01-01", hi="2026-12-31", **kw)
    c12, _, _ = bt(floor=5 * CR, lo="2012-06-01", hi="2018-12-31", **kw)
    print(f"{name:28}{c19*100:>7.1f}%{dd19*100:>8.1f}%{sh:>7.2f}{c12*100:>9.1f}%")
