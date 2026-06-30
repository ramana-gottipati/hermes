"""Massive systematic search for the highest-CAGR long-only positional config, 2019-2026.

Sweeps signal x universe-floor x concentration (top-N), monthly rebalance, net of cost.
For EACH it also reports the 2012-2018 CAGR (out-of-sample robustness) and the drawdown,
so we can tell a real edge from a bull-run/microcap curve-fit. Prints everything that
clears 50% CAGR 2019-26 and flags whether it survived 2012-2018.
"""
import numpy as np
from explosive_moves.embase import load_symbol_cache
from explosive_moves.strategies import CR
from explosive_moves.metrics import index_series

cache = load_symbol_cache()
D2I = {s: {d: i for i, d in enumerate(A["date"])} for s, A in cache.items()}
dts, cl = index_series("Nifty 50")
cal = [d for d in dts if d >= "2012-06-01"]
rebal_idx = list(range(0, len(cal), 22))
CPS = 0.005


def pr(x):
    r = np.full(len(x), np.nan); m = ~np.isnan(x)
    if m.sum() > 1:
        r[m] = np.argsort(np.argsort(x[m])) / (m.sum() - 1)
    return r


# build per-rebalance tables once (1cr floor = broadest), storing all metrics + fwd
print("building tables...", flush=True)
TBL = []
for r in range(len(rebal_idx) - 1):
    d0, d1 = cal[rebal_idx[r]], cal[rebal_idx[r + 1]]
    rows = {"d0": d0, "sym": [], "mt": [], "mom6": [], "mom12": [], "vol": [], "deliv": [],
            "r22": [], "ext5y": [], "fwd": []}
    for s, A in cache.items():
        i0 = D2I[s].get(d0)
        if i0 is None or i0 < 260:
            continue
        mt = A["med_turn"][i0]
        if not (mt >= 1 * CR):
            continue
        ac = A["adj_close"]; i1 = D2I[s].get(d1, min(i0 + 22, len(ac) - 1))
        if not (ac[i0] > 0 and ac[i1] > 0):
            continue
        F = A["feats"]; v = F["vol_66"][i0]; m6 = ac[i0] / ac[i0 - 126] - 1 if i0 >= 126 else np.nan
        if v != v or v <= 0 or m6 != m6:
            continue
        rows["sym"].append(s); rows["mt"].append(mt); rows["mom6"].append(m6)
        rows["mom12"].append(ac[i0] / ac[i0 - 252] - 1 if i0 >= 252 else np.nan)
        rows["vol"].append(v); rows["deliv"].append(F["deliv_qty_trend"][i0]); rows["r22"].append(F["ret_22d"][i0])
        rows["ext5y"].append(ac[i0] / ac[i0 - 1250] - 1 if i0 >= 1250 else np.nan)
        rows["fwd"].append(ac[i1] / ac[i0] - 1)
    for k in rows:
        if k != "d0":
            rows[k] = np.array(rows[k])
    TBL.append(rows)
print(f"{len(TBL)} rebalances built", flush=True)


def score(t, sig):
    if sig == "mom6":      return t["mom6"]
    if sig == "mom12":     return t["mom12"]
    if sig == "riskadj":   return t["mom6"] / (t["vol"] + 1e-6)
    if sig == "accel":     return t["r22"]
    if sig == "lowvolmom": return 0.5 * pr(t["mom6"]) + 0.5 * pr(-t["vol"])
    if sig == "delivmom":  return 0.5 * pr(t["mom6"]) + 0.5 * pr(t["deliv"])
    if sig == "multi":     return 0.4 * pr(t["mom6"] / (t["vol"] + 1e-6)) + 0.3 * pr(-t["vol"]) + 0.3 * pr(t["deliv"])
    if sig == "mom6_val":  s = t["mom6"].copy(); s[~(np.isnan(t["ext5y"]) | (t["ext5y"] < 2))] = np.nan; return s


def stats(rets):
    rets = np.array(rets)
    if len(rets) < 6:
        return None
    eq = np.cumprod(1 + rets); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1).min()
    yrs = len(eq) / 12; cagr = eq[-1] ** (1 / yrs) - 1
    sd = rets.std()
    return cagr, dd, (rets.mean() / sd * np.sqrt(12) if sd > 0 else 0)


def backtest(sig, floor, topn, lo, hi):
    rets, prev = [], set()
    for t in TBL:
        if not (lo <= t["d0"] <= hi):
            continue
        mask = t["mt"] >= floor
        sc = score(t, sig); sc = np.where(mask, sc, np.nan)
        valid = ~np.isnan(sc) & ~np.isnan(t["fwd"])
        idx = np.where(valid)[0]
        if len(idx) < topn:
            rets.append(0.0); continue
        top = idx[np.argsort(sc[idx])[::-1]][:topn]
        picks = set(t["sym"][i] for i in top)
        g = float(np.mean(t["fwd"][top]))
        turn = (len(picks - prev) + len(prev - picks)) / max(len(picks), 1)
        rets.append(g - CPS * turn); prev = picks
    return stats(rets)


SIGS = ["mom6", "mom12", "riskadj", "accel", "lowvolmom", "delivmom", "multi", "mom6_val"]
FLOORS = [(1 * CR, "1cr"), (5 * CR, "5cr"), (25 * CR, "25cr")]
TOPN = [5, 8, 10, 15, 25, 40]
results = []
for sig in SIGS:
    for floor, ft in FLOORS:
        for n in TOPN:
            s19 = backtest(sig, floor, n, "2019-01-01", "2026-12-31")
            s12 = backtest(sig, floor, n, "2012-06-01", "2018-12-31")
            if s19 and s12:
                results.append((sig, ft, n, s19[0], s19[1], s19[2], s12[0], s12[1]))

results.sort(key=lambda r: -r[3])
# CL-RES-07: this ranks 144 = 8 signals x 3 floors x 6 topN configs by ONE window's CAGR
# with NO multiple-testing adjustment, so the top line is the best-of-144 order statistic
# (upward biased) — it is NOT an estimate of the edge you would have earned out-of-sample.
# Treat the table as a HYPOTHESIS-GENERATOR, not a result. The only column that carries
# evidential weight is both-half survival (positive in 2019-2026 AND 2012-2018); a config
# that tops the 2019-26 sort but is weak in 2012-18 is flagged OVERFIT below. For a real
# significance read, deflate by the trial count (e.g. Bonferroni / deflated-Sharpe) — see
# ml_alpha.deflated_sharpe — rather than reading the rank-1 CAGR at face value.
print(f"\nTOP 30 by 2019-2026 CAGR (net of cost) — IN-SAMPLE RANK of 144 configs, best-of "
      f"order statistic, NOT an OOS edge. robust = also positive 2012-2018 (the real test)\n")
print(f"{'signal':11}{'univ':5}{'topN':>5}{'CAGR19':>8}{'MaxDD19':>9}{'Sharpe':>7}{'CAGR12-18':>10}{'DD12-18':>9}  flag")
for sig, ft, n, c19, dd19, sh, c12, dd12 in results[:30]:
    flag = ""
    if c19 >= 0.50:
        flag += "50%+ "
    if c12 < 0.10:
        flag += "OVERFIT(weak 12-18) "
    if ft == "1cr":
        flag += "microcap "
    print(f"{sig:11}{ft:5}{n:>5}{c19*100:>7.1f}%{dd19*100:>8.1f}%{sh:>7.2f}{c12*100:>9.1f}%{dd12*100:>8.1f}%  {flag}")
n50 = sum(1 for r in results if r[3] >= 0.50)
print(f"\n{n50} configs cleared 50% CAGR 2019-26. "
      f"{sum(1 for r in results if r[3]>=0.50 and r[6]>=0.15)} of them ALSO did >15% in 2012-18 (robust).")
