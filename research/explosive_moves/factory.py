"""Strategy factory — long-only positional, fresh data-driven SELECTION signals.

Not hand-built TA rules. At each monthly rebalance we score every liquid stock on
cross-sectional ranks + raw data signals, pick the top-N, equal-weight, hold a month,
net of turnover costs. We sweep many DIFFERENT selection signals x universes, walk-forward
(2012-18 vs 2019-26), and keep the ones that beat the broad index in BOTH halves.

Valuation/extension is a first-class variable (Ramana won't chase names already up
500-600%): the *_VAL variants EXCLUDE stocks up >200% over ~5y, so the data tells us
whether respecting valuation helps or hurts.
"""
from __future__ import annotations
import numpy as np
from .embase import load_symbol_cache
from .strategies import CR
from .metrics import index_series

REBAL = 22
COST_PS = 0.003
TD_Y = 12


def pctrank(x):
    r = np.full(len(x), np.nan)
    m = ~np.isnan(x)
    if m.sum() > 1:
        r[m] = np.argsort(np.argsort(x[m])) / (m.sum() - 1)
    return r


def eqstats(rets):
    rets = np.asarray(rets, float)
    eq = np.cumprod(1 + rets)
    if len(eq) < 3:
        return None
    peak = np.maximum.accumulate(eq); dd = eq / peak - 1
    yrs = len(eq) / TD_Y
    cagr = eq[-1] ** (1 / max(yrs, 1e-9)) - 1
    sd = rets.std()
    return {"cagr": cagr, "maxdd": float(dd.min()), "sharpe": rets.mean() / sd * np.sqrt(TD_Y) if sd > 0 else 0,
            "calmar": cagr / abs(dd.min()) if dd.min() < 0 else 0, "totx": float(eq[-1])}


# --- selection signals: each returns (score, extra_mask) over the rebal table ---
def sig_mom6(t):       return t["mom6"], None
def sig_mom12(t):      return t["mom12"], None
def sig_riskadj(t):    return t["mom6"] / (t["vol"] + 1e-6), None
def sig_accel(t):      return t["r22"], None                       # 1-month thrust
def sig_lowvolmom(t):  return 0.5 * pctrank(t["mom6"]) + 0.5 * pctrank(-t["vol"]), None
def sig_delivmom(t):   return 0.5 * pctrank(t["mom6"]) + 0.5 * pctrank(t["deliv"]), None
def sig_qualmom(t):    return (0.4 * pctrank(t["mom6"] / (t["vol"] + 1e-6)) +
                               0.3 * pctrank(t["deliv"]) + 0.3 * pctrank(-t["vol"])), None
def sig_pullback(t):
    up = (t["mom12"] > 0) & (t["above200"] > 0) & (t["disthigh"] > -0.30) & (t["disthigh"] < -0.05)
    return pctrank(t["mom12"]), up                                  # strong uptrends, currently pulled back


def not_extended(t):                                                # valuation guard
    e = t["ext5y"]
    return np.isnan(e) | (e < 2.0)                                  # exclude up >200% in ~5y


SIGNALS = {
    "MOM6": sig_mom6, "MOM12": sig_mom12, "RISKADJ": sig_riskadj, "ACCEL": sig_accel,
    "LOWVOL_MOM": sig_lowvolmom, "DELIV_MOM": sig_delivmom, "QUAL_MOM": sig_qualmom,
    "PULLBACK": sig_pullback,
}


def build_tables(cache, cal, rebal_idx, floor):
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}
    tables = []
    for r in range(len(rebal_idx) - 1):
        d0, d1 = cal[rebal_idx[r]], cal[rebal_idx[r + 1]]
        syms, mom6, mom12, vol, deliv, r22, disthigh, above200, ext5y, fwd = ([] for _ in range(10))
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130 or not (mt[i0] >= floor):
                continue
            i1 = d2i.get(d1, min(i0 + REBAL, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            syms.append(s)
            mom6.append(ac[i0] / ac[i0 - 126] - 1 if i0 >= 126 else np.nan)
            mom12.append(ac[i0] / ac[i0 - 252] - 1 if i0 >= 252 else np.nan)
            vol.append(F["vol_66"][i0]); deliv.append(F["deliv_qty_trend"][i0])
            r22.append(F["ret_22d"][i0]); disthigh.append(F["dist_high_22"][i0])
            above200.append(1.0 if F["close_vs_sma200"][i0] > 0 else 0.0)
            ext5y.append(ac[i0] / ac[i0 - 1250] - 1 if i0 >= 1250 else np.nan)
            fwd.append(ac[i1] / ac[i0] - 1)
        # delivery proxy: use deliv_per_22 if present in feats else volume-based; here use feats key
        tables.append({"d0": d0, "syms": syms,
                       "mom6": np.array(mom6), "mom12": np.array(mom12), "vol": np.array(vol),
                       "deliv": np.array(deliv), "r22": np.array(r22), "disthigh": np.array(disthigh),
                       "above200": np.array(above200), "ext5y": np.array(ext5y), "fwd": np.array(fwd)})
    return tables


def run_strat(tables, sigfn, topn, val_guard):
    rets, dates, held = [], [], set()
    for t in tables:
        score, emask = sigfn(t)
        valid = ~np.isnan(score) & ~np.isnan(t["fwd"])
        if emask is not None:
            valid &= emask
        if val_guard:
            valid &= not_extended(t)
        idx = np.where(valid)[0]
        if len(idx) == 0:
            rets.append(0.0); dates.append(t["d0"]); continue
        order = idx[np.argsort(score[idx])[::-1]][:topn]
        picks = set(t["syms"][i] for i in order)
        gross = float(np.mean(t["fwd"][order]))
        turn = (len(picks - held) + len(held - picks)) / max(len(picks), 1)
        rets.append(gross - COST_PS * turn); dates.append(t["d0"]); held = picks
    return np.array(rets), dates


def slice_stats(rets, dates, lo, hi):
    m = np.array([lo <= d <= hi for d in dates])
    return eqstats(rets[m]) if m.sum() > 3 else None


def main():
    cache = load_symbol_cache()
    dts, cl = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    rebal_idx = list(range(0, len(cal), REBAL))

    # baselines (monthly marks)
    print("BASELINES (buy & hold, monthly):")
    base = {}
    for idx in ("Nifty 50", "Nifty 500", "Nifty Midcap 50"):
        di, ci = index_series(idx); mp = {d: ci[i] for i, d in enumerate(di)}
        eqb = [mp[cal[k]] for k in rebal_idx if cal[k] in mp]
        rb = np.array(eqb[1:]) / np.array(eqb[:-1]) - 1
        s = eqstats(rb); base[idx] = s
        print(f"  {idx:16s} full: CAGR={s['cagr']*100:+5.1f}% MaxDD={s['maxdd']*100:6.1f}% "
              f"Sharpe={s['sharpe']:.2f} Calmar={s['calmar']:.2f} ({s['totx']:.1f}x)")
    bench = base["Nifty 500"]["sharpe"]

    rows = []
    for floor, ftag in ((5 * CR, "5cr"), (25 * CR, "25cr")):
        tables = build_tables(cache, cal, rebal_idx, floor)
        for name, fn in SIGNALS.items():
            for vg in (False, True):
                rets, dates = run_strat(tables, fn, 25, vg)
                full = eqstats(rets)
                a = slice_stats(rets, dates, "2012", "2018")
                b = slice_stats(rets, dates, "2019", "2026")
                if full and a and b:
                    surv = (a["sharpe"] > bench and b["sharpe"] > bench and a["cagr"] > 0 and b["cagr"] > 0)
                    rows.append((name + ("+VAL" if vg else ""), ftag, full, a, b, surv))

    rows.sort(key=lambda r: -r[2]["sharpe"])
    print(f"\nSTRATEGY SWEEP (top-25 names, monthly, net of cost). benchmark=Nifty500 Sharpe {bench:.2f}")
    print(f"{'signal':16}{'univ':5}{'FULL cagr/dd/shrp/clmr':>30}{'  19-26 cagr/shrp':>20}  surv")
    for name, ft, f, a, b, surv in rows:
        print(f"{name:16}{ft:5}{f['cagr']*100:>7.1f}%{f['maxdd']*100:>7.1f}%{f['sharpe']:>7.2f}{f['calmar']:>7.2f}"
              f"{b['cagr']*100:>11.1f}%{b['sharpe']:>8.2f}   {'YES' if surv else ''}")


if __name__ == "__main__":
    main()
