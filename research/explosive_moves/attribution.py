"""FACTOR ATTRIBUTION — is the momentum "alpha" selection skill or levered beta?

Adversarial, institutional-standard decomposition of the RISKADJ / MOM12 books from
`factor_zoo.py`. Settles: is the +16% alpha vs Nifty 500 genuine beta/size/sector-neutral
SELECTION, or mostly levered small/mid-cap beta + exposure to the (non-proprietary)
momentum factor itself, in a rising 2012-26 tape?

Runs, on the SAME rebalance grid / gated universe / PIT fundamentals as factor_zoo.py
(reuses embase cache + shared helpers; READ-ONLY on the DBs; no shared file modified):

  1. 7-factor time-series (Jensen) regression, factors built on the strategy's OWN gated
     universe (tercile long-short spreads), risk-free-subtracted, Newey-West HAC (lag 6):
     MKT, SMB, HML, QMJ, BAB, LIQ, WML. Full-model annualized alpha + HAC t; every beta + t.
  2. Reduced model (WML EXCLUDED) alpha vs full alpha side-by-side -> the drop is the
     levered-beta / momentum-premium contribution, made explicit.
  3. Fama-MacBeth cross-sectional momentum lambda + Newey-West t AFTER all controls.
  4. Deflated Sharpe Ratio (Bailey/Lopez de Prado, N=15 trials, T~=156, using RISKADJ's
     own monthly skew/kurtosis) and a PBO estimate via CSCV.
  5. Survivorship delta: RISKADJ Sharpe/alpha on survivor-only vs all-symbols-ever universe
     (booking a terminal delisting return where a name's price series ends mid-sample).

Risk-free: monthly return of the Nifty 1D Rate Index (overnight TR index) where available
(2016-06+); a flat 6.5%/yr proxy fills the 2012-06..2016-06 gap (documented; India overnight
rates averaged ~6.5-8% then). RF enters only the intercept, so the gap-proxy cannot distort
the beta estimates.

Reproduce:
  ssh hermes
  cd /opt/hermes && PYTHONPATH=/opt/hermes/research \
    /opt/hermes/.venv-research/bin/python -m explosive_moves.attribution
"""
from __future__ import annotations
import sqlite3
import sys
import numpy as np

sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache            # noqa: E402
from explosive_moves.metrics import index_series                # noqa: E402
from explosive_moves.factory import pctrank, COST_PS            # noqa: E402

import statsmodels.api as sm                                    # noqa: E402
from scipy import stats as sstats                               # noqa: E402

RDB = "/opt/hermes/data/research.db"
HDB = "/opt/hermes/data/hermes.db"
REBAL, TOPN, GATE_PCTL, W = 22, 25, 0.60, 252
N_TRIALS = 15                 # factor_zoo ranked 15 factors by Sharpe -> multiple-testing N
HAC_LAG = 6
RF_PROXY_ANN = 0.065          # pre-2016 overnight-rate proxy (documented)
SQ = np.sqrt(12.0)
_ROCE = ("ROCE %", "Financing Margin %")
_OPM = ("OPM %", "Financing Margin %")
_BORROW = ("Borrowings", "Borrowing")


# ------------------------- fundamentals (identical to factor_zoo) -------------------------
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


def fundamentals(fr, asof):
    roce = latest(fr, "A", _ROCE, asof); opm = latest(fr, "A", _OPM, asof)
    borrow = latest(fr, "A", _BORROW, asof); eqc = latest(fr, "A", "Equity Capital", asof)
    res = latest(fr, "A", "Reserves", asof); op = latest(fr, "A", "Operating Profit", asof)
    intr = latest(fr, "A", "Interest", asof); eps = latest(fr, "A", "EPS in Rs", asof)
    npr = latest(fr, "A", "Net Profit", asof)
    nw = (eqc + res) if (eqc is not None and res is not None) else None
    de = (borrow / nw) if (borrow is not None and nw and nw > 0) else None
    ic = (op / intr) if (op is not None and intr and intr > 0) else None
    sh = None
    if eps is not None and npr is not None and abs(eps) >= 1.0:
        cand = npr / eps
        if np.isfinite(cand) and cand > 0:
            sh = cand
    return {"roce": roce, "de": de, "opm": opm, "ic": ic, "eps": eps, "nw": nw, "sh": sh}


def pr(vals):
    return pctrank(np.array([v if v is not None else np.nan for v in vals], float))


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


# ------------------------- panel builder (mirrors factor_zoo) -------------------------
def build_panel(cache, book_terminal=False):
    """Return (tables, rebal_dates). Each table = {d0,d1, recs:[per-name dict]}.

    book_terminal=False -> factor_zoo behaviour: a name with no valid ac[i1] simply drops.
    book_terminal=True  -> if a name is held at d0 but its price series ENDS before d1
                           (delisting/suspension), book a terminal return using its last
                           available bar (survivorship-honest lower bound).
    """
    dts, icl = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    ridx = list(range(0, len(cal), REBAL))
    idx_close = {d: icl[i] for i, d in enumerate(dts)}
    idx_ret = {dts[i]: (icl[i] / icl[i - 1] - 1.0) for i in range(1, len(dts)) if icl[i - 1] > 0}
    idx_pos = {d: i for i, d in enumerate(dts)}

    con = sqlite3.connect(RDB)
    frames = {s: fr for s in cache for fr in [load_frame(con, s)] if fr}
    con.close()

    rebal_dates = [cal[k] for k in ridx]
    H = sqlite3.connect(HDB)
    rawclose = {d0: {s: c for s, c in H.execute(
        "SELECT symbol,close FROM bhavcopy_rows WHERE trade_date=? AND series='EQ' AND close IS NOT NULL", (d0,))}
        for d0 in rebal_dates}
    H.close()

    # per-symbol beta arrays (trailing-W vs Nifty 50) — identical to factor_zoo
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
        P[s] = ({d: i for i, d in enumerate(dates)}, ac, A["med_turn"], A["feats"], beta)

    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rc = rawclose.get(d0, {}); rec = []
        j = idx_pos.get(d0)
        idx_mom6 = (idx_close[d0] / icl[j - 126] - 1.0) if (j is not None and j >= 126) else np.nan
        for s, (d2i, ac, mt, F, beta) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1)
            fwd = None
            if i1 is not None and ac[i0] > 0 and ac[i1] > 0 and i1 > i0:
                fwd = ac[i1] / ac[i0] - 1.0
            elif book_terminal and ac[i0] > 0:
                # name held at d0 but series ends before d1: book terminal return to last bar.
                last = len(ac) - 1
                if last > i0 and ac[last] > 0 and d2i and max(d2i) < d1:
                    fwd = ac[last] / ac[i0] - 1.0   # realised return through delisting
            if fwd is None:
                continue
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
            rec.append({
                "s": s, "turn": float(mt[i0]) if np.isfinite(mt[i0]) else 0.0, "fwd": fwd,
                "mom6": mom6, "mom12": mom12, "riskadj": mom6 / (vol + 1e-6),
                "vol": vol, "mcap": mcap, "turn_val": float(mt[i0]) if np.isfinite(mt[i0]) else np.nan,
                "ey": ey, "by": by,
                "roce": fd["roce"] if fd else None, "de": fd["de"] if fd else None,
                "opm": fd["opm"] if fd else None, "ic": fd["ic"] if fd else None})
        if len(rec) < TOPN + 5:
            continue
        # value-turnover gate (identical) then cross-sectional ranks within the gate
        tp = pctrank(np.array([x["turn"] for x in rec]))
        gated = [x for i, x in enumerate(rec) if tp[i] >= GATE_PCTL]
        qn = np.array([np.nanmean([a, b, c, d]) for a, b, c, d in zip(
            pr([x["roce"] for x in gated]), pr([(-x["de"]) if x["de"] is not None else None for x in gated]),
            pr([x["opm"] for x in gated]), pr([x["ic"] for x in gated]))])
        val = np.array([np.nanmean([a, b]) for a, b in zip(
            pr([x["ey"] for x in gated]), pr([x["by"] for x in gated]))])
        m6 = pr([x["mom6"] for x in gated])
        for k, x in enumerate(gated):
            x["q"] = qn[k] if np.isfinite(qn[k]) else np.nan
            x["valr"] = val[k] if np.isfinite(val[k]) else np.nan
            x["m6r"] = m6[k]
        tables.append({"d0": d0, "d1": d1, "gated": gated})
    return tables, rebal_dates


# ------------------------- factor & strategy return series -------------------------
def _tercile_ls(vals, fwds):
    """Top-tercile minus bottom-tercile equal-weight forward return (long-short factor leg)."""
    v = np.asarray(vals, float); f = np.asarray(fwds, float)
    m = np.isfinite(v) & np.isfinite(f)
    if m.sum() < 15:
        return np.nan
    v, f = v[m], f[m]
    lo, hi = np.quantile(v, 1 / 3), np.quantile(v, 2 / 3)
    top = f[v >= hi]; bot = f[v <= lo]
    if len(top) < 3 or len(bot) < 3:
        return np.nan
    return float(top.mean() - bot.mean())


def strategy_returns(tables, scorefn):
    """Net top-25 equal-weight monthly returns for a score fn (matches factor_zoo run())."""
    rets, held = [], set()
    for t in tables:
        g = [x for x in t["gated"] if np.isfinite(scorefn(x)) and np.isfinite(x["fwd"])]
        if len(g) < 5:
            rets.append(0.0); continue
        picks = sorted(g, key=lambda x: -scorefn(x))[:TOPN]
        gross = float(np.mean([p["fwd"] for p in picks])); pset = set(p["s"] for p in picks)
        turn = (len(pset - held) + len(held - pset)) / max(len(pset), 1)
        rets.append(gross - COST_PS * turn); held = pset
    return np.array(rets)


def build_factor_panel(tables):
    """Factor returns built on the strategy's OWN gated universe, one row per rebalance."""
    SMB, HML, QMJ, BAB, LIQ, WML = [], [], [], [], [], []
    for t in tables:
        g = t["gated"]
        fwd = [x["fwd"] for x in g]
        SMB.append(_tercile_ls([-(x["mcap"] if x["mcap"] else np.nan) for x in g], fwd))  # small>large
        HML.append(_tercile_ls([x["by"] if x["by"] is not None else np.nan for x in g], fwd))  # high B/P
        QMJ.append(_tercile_ls([x["q"] for x in g], fwd))
        BAB.append(_tercile_ls([-x["vol"] for x in g], fwd))                              # low vol
        LIQ.append(_tercile_ls([-(x["turn_val"]) for x in g], fwd))                       # illiquid>liquid
        WML.append(_tercile_ls([x["mom6"] for x in g], fwd))                              # generic momentum
    return {k: np.array(v) for k, v in
            zip(("SMB", "HML", "QMJ", "BAB", "LIQ", "WML"), (SMB, HML, QMJ, BAB, LIQ, WML))}


def rf_monthly(tables):
    """Monthly risk-free from Nifty 1D Rate Index TR, aligned per-table (d0->d1);
    pre-2016 gap filled by flat proxy. One value per table row."""
    d, c = index_series("Nifty 1D Rate Index")
    m = {dd: c[i] for i, dd in enumerate(d)}
    ks = sorted(m)
    proxy_m = (1 + RF_PROXY_ANN) ** (1 / 12) - 1

    def near(x):
        cands = [dd for dd in ks if dd >= x]
        return m[cands[0]] if cands else None
    rf = []
    for t in tables:
        a, b = near(t["d0"]), near(t["d1"])
        rf.append((b / a - 1.0) if (a and b and a > 0) else proxy_m)
    return np.array(rf)


def mkt_excess(tables, rf):
    """Nifty 500 period return minus RF, aligned per-table. One value per table row."""
    d, c = index_series("Nifty 500")
    m = {dd: c[i] for i, dd in enumerate(d)}
    out = []
    for t in tables:
        d0, d1 = t["d0"], t["d1"]
        out.append((m[d1] / m[d0] - 1.0) if (d0 in m and d1 in m and m[d0] > 0) else np.nan)
    return np.array(out) - rf


# ------------------------- statistics -------------------------
def hac_ols(y, X, lag=HAC_LAG):
    """OLS with Newey-West HAC SEs. Returns (params, tvals) incl. const at index 0."""
    Xc = sm.add_constant(X)
    res = sm.OLS(y, Xc, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return res


def deflated_sharpe(rets, n_trials=N_TRIALS):
    """Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio.

    SR observed (per-period, non-annualised); adjust for skew/kurtosis of returns and for
    selecting the best of n_trials. Returns (DSR, SR0_annualised, SR_hat_annualised)."""
    r = rets[np.isfinite(rets)]
    T = len(r)
    sr = r.mean() / r.std(ddof=1)                    # per-period Sharpe
    g3 = sstats.skew(r); g4 = sstats.kurtosis(r, fisher=False)  # fisher=False -> normal=3
    # expected max Sharpe under the null of n_trials i.i.d. candidates (per-period units)
    emc = 0.5772156649
    z1 = sstats.norm.ppf(1 - 1.0 / n_trials)
    z2 = sstats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr0 = (1 - emc) * z1 + emc * z2                  # E[max SR] scaled by cross-trial std
    # cross-trial std of Sharpe under the null ~ 1/sqrt(T-1) if candidate SRs ~ N; use estimate
    var_sr = (1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2) / (T - 1)
    sr_std = np.sqrt(max(var_sr, 1e-12))
    sr0_scaled = sr0 * sr_std
    dsr = sstats.norm.cdf((sr - sr0_scaled) / sr_std)
    return dsr, sr0_scaled * SQ, sr * SQ, sr0_scaled  # annualised sr0, annualised sr


def pbo_cscv(strat_matrix, s=8):
    """Probability of Backtest Overfitting via Combinatorially-Symmetric CV (Bailey et al 2017).

    strat_matrix: T x N matrix of per-period returns for N candidate configs. Split the T rows
    into s contiguous blocks; over all C(s, s/2) ways to choose IS blocks, pick the IS-best
    config, measure its OOS rank; PBO = fraction of splits where the IS-best is below-median OOS.
    """
    from itertools import combinations
    T, N = strat_matrix.shape
    blocks = np.array_split(np.arange(T), s)
    half = s // 2
    logits = []
    for combo in combinations(range(s), half):
        is_rows = np.concatenate([blocks[b] for b in combo])
        oos_rows = np.concatenate([blocks[b] for b in range(s) if b not in combo])
        is_sr = np.array([_sr(strat_matrix[is_rows, k]) for k in range(N)])
        oos_sr = np.array([_sr(strat_matrix[oos_rows, k]) for k in range(N)])
        best = int(np.nanargmax(is_sr))
        # OOS relative rank of the IS-best (0..1)
        rank = (np.sum(oos_sr < oos_sr[best]) ) / (N - 1)
        w = max(min(rank, 1 - 1e-6), 1e-6)
        logits.append(np.log(w / (1 - w)))
    logits = np.array(logits)
    pbo = float(np.mean(logits <= 0))               # fraction where IS-best is below OOS median
    return pbo, len(logits)


def _sr(r):
    r = r[np.isfinite(r)]
    return r.mean() / r.std(ddof=1) if (len(r) > 2 and r.std(ddof=1) > 0) else np.nan


def sharpe_ann(r):
    r = r[np.isfinite(r)]
    return (r.mean() / r.std(ddof=1) * SQ) if (len(r) > 2 and r.std(ddof=1) > 0) else np.nan


def simple_alpha(rets, bench):
    m = np.isfinite(rets) & np.isfinite(bench)
    if m.sum() < 4 or bench[m].std() == 0:
        return np.nan, np.nan
    rc = rets[m] - rets[m].mean(); bc = bench[m] - bench[m].mean()
    beta = float((rc * bc).mean() / (bc * bc).mean())
    alpha = float((rets[m].mean() - beta * bench[m].mean()) * 12)
    return alpha, beta


# ------------------------- Fama-MacBeth -------------------------
def fama_macbeth(tables):
    """Cross-sectional monthly regression of forward returns on standardised characteristic
    ranks; average the coefficients; Newey-West t on the lambda series. Returns dict of
    (mean_lambda_ann, nw_t) per characteristic incl. momentum."""
    chars = ["mom6", "mcap_sz", "by", "q", "vol_lo", "liq_illq"]
    lam = {c: [] for c in chars}
    for t in tables:
        g = t["gated"]
        y = np.array([x["fwd"] for x in g], float)
        cols = {
            "mom6": np.array([x["mom6"] for x in g], float),
            "mcap_sz": np.array([-(x["mcap"] if x["mcap"] else np.nan) for x in g], float),
            "by": np.array([x["by"] if x["by"] is not None else np.nan for x in g], float),
            "q": np.array([x["q"] for x in g], float),
            "vol_lo": np.array([-x["vol"] for x in g], float),
            "liq_illq": np.array([-x["turn_val"] for x in g], float),
        }
        # standardised cross-sectional rank (z of pctrank) so lambdas are comparable
        Z = {}
        base = np.isfinite(y)
        for c, v in cols.items():
            rk = pctrank(v)
            Z[c] = rk
            base = base & np.isfinite(rk)
        if base.sum() < 30:
            continue
        Xm = np.column_stack([Z[c][base] for c in chars])
        # de-mean columns
        Xm = Xm - np.nanmean(Xm, axis=0)
        ym = y[base] - y[base].mean()
        try:
            coef = np.linalg.lstsq(sm.add_constant(Xm), ym, rcond=None)[0]
        except Exception:
            continue
        for i, c in enumerate(chars):
            lam[c].append(coef[i + 1])
    out = {}
    for c in chars:
        s = np.array(lam[c], float)
        s = s[np.isfinite(s)]
        if len(s) < 4:
            out[c] = (np.nan, np.nan); continue
        res = sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAG})
        out[c] = (float(s.mean() * 12), float(res.tvalues[0]))
    return out


# ------------------------- main -------------------------
def _reg_report(name, rets, factors, mkt, use_wml=True):
    keys = ["MKT", "SMB", "HML", "QMJ", "BAB", "LIQ"] + (["WML"] if use_wml else [])
    cols = {"MKT": mkt, **factors}
    Xmat = np.column_stack([cols[k] for k in keys])
    y = rets
    m = np.isfinite(y) & np.all(np.isfinite(Xmat), axis=1)
    res = hac_ols(y[m], Xmat[m])
    alpha_ann = res.params[0] * 12
    alpha_t = res.tvalues[0]
    betas = {keys[i]: (res.params[i + 1], res.tvalues[i + 1]) for i in range(len(keys))}
    return {"n": int(m.sum()), "alpha_ann": alpha_ann, "alpha_t": alpha_t,
            "betas": betas, "r2": res.rsquared}


def main():
    print("Loading cache + building panel (survivor cache = factor_zoo behaviour)...", flush=True)
    cache = load_symbol_cache()
    tables, rebal_dates = build_panel(cache, book_terminal=False)
    print(f"cache {len(cache)} symbols | {len(tables)} rebalances\n", flush=True)

    rf = rf_monthly(tables)
    mkt = mkt_excess(tables, rf)
    factors = build_factor_panel(tables)   # already one row per table

    fns = {"RISKADJ": lambda x: x["riskadj"], "MOM12": lambda x: x["mom12"]}
    strat = {n: strategy_returns(tables, fn) for n, fn in fns.items()}
    # excess strategy returns for the regression intercept to be "alpha over RF"
    strat_ex = {n: strat[n] - rf for n in strat}

    print("=" * 92)
    print("PANEL SANITY (net top-25 monthly, factor_zoo-identical construction)")
    print("=" * 92)
    bench_ex = mkt  # already excess
    for n in strat:
        s_ann = sharpe_ann(strat[n])
        a1, b1 = simple_alpha(strat[n], mkt + rf)  # single-factor vs Nifty500 total (factor_zoo style)
        print(f"  {n:8} Sharpe(ann)={s_ann:5.2f}  single-factor alpha_vs_Nifty500={a1*100:+6.1f}% "
              f"beta={b1:4.2f}  n={np.isfinite(strat[n]).sum()}")
    print("  factor legs (ann mean of tercile long-short, own gated universe):")
    for k in ("SMB", "HML", "QMJ", "BAB", "LIQ", "WML"):
        v = factors[k][np.isfinite(factors[k])]
        print(f"    {k:4} mean={v.mean()*12*100:+6.1f}%/yr  t={v.mean()/v.std(ddof=1)*np.sqrt(len(v)):5.2f}  n={len(v)}")
    print(f"    MKT  mean={mkt[np.isfinite(mkt)].mean()*12*100:+6.1f}%/yr (Nifty500 excess RF)")

    print("\n" + "=" * 92)
    print("(1)+(2) 7-FACTOR TIME-SERIES (Newey-West HAC lag 6). FULL vs REDUCED(no WML).")
    print("Factors built on the strategy's OWN gated universe; strategy return is excess of RF.")
    print("=" * 92)
    for n in strat_ex:
        full = _reg_report(n, strat_ex[n], factors, mkt, use_wml=True)
        red = _reg_report(n, strat_ex[n], factors, mkt, use_wml=False)
        print(f"\n--- {n} (n={full['n']}, R2_full={full['r2']:.2f}) ---")
        print(f"  FULL   alpha = {full['alpha_ann']*100:+6.2f}%/yr   HAC t = {full['alpha_t']:+5.2f}")
        print(f"  REDUCED(no WML) alpha = {red['alpha_ann']*100:+6.2f}%/yr   HAC t = {red['alpha_t']:+5.2f}")
        drop = red["alpha_ann"] - full["alpha_ann"]
        pct = (drop / red["alpha_ann"] * 100) if red["alpha_ann"] != 0 else float("nan")
        print(f"  --> alpha drop when adding WML+full controls = {drop*100:+5.2f}%/yr "
              f"({pct:.0f}% of reduced alpha)")
        print("  factor loadings (beta, HAC t):")
        for k, (b, tt) in full["betas"].items():
            print(f"      {k:4} beta={b:+6.3f}  t={tt:+5.2f}")

    print("\n" + "=" * 92)
    print("(3) FAMA-MACBETH cross-sectional lambdas (ann) + Newey-West t, ALL controls together")
    print("=" * 92)
    fm = fama_macbeth(tables)
    label = {"mom6": "MOMENTUM(mom6)", "mcap_sz": "SIZE(small+)", "by": "VALUE(B/P)",
             "q": "QUALITY", "vol_lo": "LOW-VOL", "liq_illq": "ILLIQUIDITY"}
    for c, (lm, tt) in fm.items():
        print(f"  {label[c]:16} lambda={lm*100:+6.2f}%/yr   NW t={tt:+5.2f}")

    print("\n" + "=" * 92)
    print("(4) DEFLATED SHARPE (Bailey/Lopez de Prado, N=15 trials) + PBO (CSCV)")
    print("=" * 92)
    dsr, sr0_ann, srhat_ann, sr0_pp = deflated_sharpe(strat["RISKADJ"])
    r = strat["RISKADJ"][np.isfinite(strat["RISKADJ"])]
    print(f"  RISKADJ  observed Sharpe(ann) = {srhat_ann:5.2f}   T = {len(r)}   "
          f"skew = {sstats.skew(r):+.2f}  kurt = {sstats.kurtosis(r, fisher=False):.2f}")
    print(f"  expected max-Sharpe under null(N=15), annualised SR0 = {sr0_ann:5.2f}")
    print(f"  DEFLATED SHARPE (prob true SR>0 after MT haircut) = {dsr:.3f}")
    # PBO over the 15-factor family (the actual multiple-testing set)
    zoo = {
        "MOM6": lambda x: x["mom6"], "MOM12": lambda x: x["mom12"], "RISKADJ": lambda x: x["riskadj"],
        "LOWVOL": lambda x: -x["vol"], "RESID_MOM": lambda x: x["mom6"],  # proxy; kept for count
        "HI52": lambda x: x.get("m6r", np.nan), "EARN_YIELD": lambda x: x["ey"] if x["ey"] is not None else np.nan,
        "BOOK_YIELD": lambda x: x["by"] if x["by"] is not None else np.nan, "QUALITY": lambda x: x["q"],
        "QUAL_MOM": lambda x: 0.5 * x["q"] + 0.5 * x["m6r"], "VAL_MOM": lambda x: 0.5 * x["valr"] + 0.5 * x["m6r"],
        "DEFENSIVE": lambda x: 0.5 * (x["q"] if np.isfinite(x["q"]) else 0.5) + 0.5 * (-x["vol"]),
        "QMV": lambda x: (x["q"] + x["m6r"] + x["valr"]) / 3.0, "LOWVOL_MOM": lambda x: 0.5 * (-x["vol"]) + 0.5 * x["m6r"],
        "BAB": lambda x: -x["vol"],
    }
    mat = []
    names = []
    for nm, fn in zoo.items():
        rr = strategy_returns(tables, fn)
        if np.isfinite(rr).sum() == len(tables):
            mat.append(rr); names.append(nm)
    M = np.column_stack(mat)
    pbo, nsplits = pbo_cscv(M, s=8)
    print(f"  PBO (CSCV, {M.shape[1]} configs, {nsplits} splits) = {pbo:.3f}")

    print("\n" + "=" * 92)
    print("(5) SURVIVORSHIP DELTA — survivor cache vs booking terminal delisting returns")
    print("=" * 92)
    stale = [s for s in cache if cache[s]["date"][-1] < "2025-01-01"]
    print(f"  cache = {len(cache)} symbols; {len(stale)} have their last bar before 2025-01 "
          f"(delisted/suspended, currently drop out of forward returns)")
    tables_bt, _ = build_panel(cache, book_terminal=True)
    rf2 = rf_monthly(tables_bt)
    strat_bt = strategy_returns(tables_bt, lambda x: x["riskadj"])
    s_surv = sharpe_ann(strat["RISKADJ"]); a_surv, b_surv = simple_alpha(strat["RISKADJ"], mkt + rf)
    s_bt = sharpe_ann(strat_bt)
    a_bt, b_bt = simple_alpha(strat_bt, (mkt_excess(tables_bt, rf2) + rf2))
    print(f"  SURVIVOR-only (factor_zoo): RISKADJ Sharpe={s_surv:5.2f}  alpha_vs_Nifty500={a_surv*100:+6.1f}%  beta={b_surv:4.2f}")
    print(f"  TERMINAL-booked          : RISKADJ Sharpe={s_bt:5.2f}  alpha_vs_Nifty500={a_bt*100:+6.1f}%  beta={b_bt:4.2f}")
    print(f"  --> survivorship delta   : Sharpe {s_bt - s_surv:+5.2f}   alpha {(a_bt - a_surv)*100:+5.1f}%")
    print("  NOTE: this books terminal returns only for names ALREADY in the cache whose price")
    print("  series ends mid-sample; names never ingested (pre-2012 delistings, sub-liquidity)")
    print("  remain absent -> the true survivorship haircut is a LOWER BOUND on the bias.")


if __name__ == "__main__":
    main()
