"""Track A — rigorous ML alpha study on the full existing feature library.

Expanding walk-forward (train on all prior years with a 1-month embargo, predict the next
year) -> a genuinely out-of-sample monthly track record. Build a top-20 equal-weight book
from the model's predicted next-month return, net of cost. Compare to simple momentum and
the index. Report the DEFLATED SHARPE RATIO (Bailey & Lopez de Prado), which haircuts the
Sharpe for the ~150 strategy trials we've run — the honest test of 'is this real or luck'.
"""
import sqlite3
import numpy as np
import scipy.stats as st
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from explosive_moves.metrics import index_series

rc = sqlite3.connect("file:/opt/hermes/data/research.db?mode=ro", uri=True)
cols = [r[1] for r in rc.execute("PRAGMA table_info(ml_panel)")]
data = rc.execute(f"SELECT {','.join(cols)} FROM ml_panel").fetchall()
rc.close()
ci = {c: i for i, c in enumerate(cols)}
feat_cols = [c for c in cols if c not in ("symbol", "date", "fwd_22", "fwd_66")]
rows = [r for r in data if r[ci["fwd_22"]] is not None]
dates = np.array([r[ci["date"]] for r in rows])
years = np.array([int(d[:4]) for d in dates])
X = np.array([[float(r[ci[c]]) if r[ci[c]] is not None else np.nan for c in feat_cols] for r in rows])
y = np.array([float(r[ci["fwd_22"]]) for r in rows])
mom12 = np.array([float(r[ci["mom12"]]) if r[ci["mom12"]] is not None else -9 for r in rows])
print(f"panel: {len(rows)} obs, {len(feat_cols)} features\n")

CPS = 0.005


def book(scores, mask_year, topn=20):
    """OOS monthly returns: each test month take top-N by score, realize fwd_22 - cost."""
    rets, prev = [], set()
    for d in sorted(set(dates[mask_year])):
        dm = (dates == d)
        sc = scores[dm]; fwd = y[dm]; idx = np.where(~np.isnan(sc))[0]
        if len(idx) < topn:
            continue
        top = idx[np.argsort(sc[idx])[::-1]][:topn]
        ids = set(np.where(dm)[0][top])
        g = float(np.mean(fwd[top]))
        turn = (len(ids - prev) + len(prev - ids)) / max(len(ids), 1)
        rets.append(g - CPS * turn); prev = ids
    return rets


# expanding walk-forward
ml_scores = np.full(len(rows), np.nan)
for ty in range(2016, 2027):
    tr = years < ty
    # embargo: drop the last ~1 month of training (target overlaps test)
    cut = f"{ty-1}-11-30"
    tr = tr & (dates <= cut)
    te = years == ty
    if tr.sum() < 5000 or te.sum() == 0:
        continue
    m = HistGradientBoostingRegressor(max_iter=300, max_depth=4, learning_rate=0.05,
                                      l2_regularization=1.0, random_state=0)
    m.fit(X[tr], y[tr])
    ml_scores[te] = m.predict(X[te])

oos = years >= 2016
ml_rets = np.array(book(ml_scores, oos))
mom_rets = np.array(book(mom12, oos))


def stats(r):
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1).min()
    cagr = eq[-1] ** (12 / len(r)) - 1; sh = r.mean() / r.std() * np.sqrt(12)
    return cagr, dd, sh, eq[-1]


def deflated_sharpe(r, n_trials=150, trial_sr_std_ann=0.30):
    n = len(r); sr = r.mean() / r.std()  # monthly
    sk = float(st.skew(r)); ku = float(st.kurtosis(r, fisher=False))
    g = 0.5772156649
    emax = (1 - g) * st.norm.ppf(1 - 1 / n_trials) + g * st.norm.ppf(1 - 1 / (n_trials * np.e))
    sr0 = (trial_sr_std_ann / np.sqrt(12)) * emax           # expected max Sharpe under null (monthly)
    dsr = st.norm.cdf((sr - sr0) * np.sqrt(n - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return dsr, sr0 * np.sqrt(12)


print("OUT-OF-SAMPLE (2016-2026, walk-forward, net of cost), top-20 monthly:")
for name, r in (("ML (full feature library)", ml_rets), ("Simple momentum (mom12)", mom_rets)):
    c, dd, sh, tx = stats(r)
    print(f"  {name:28} CAGR {c*100:5.1f}%  MaxDD {dd*100:6.1f}%  Sharpe {sh:.2f}  ({tx:.1f}x)")
dsr, sr0 = deflated_sharpe(ml_rets)
print(f"\n  Deflated Sharpe (ML, ~150 trials): DSR={dsr:.2f}  (deflation threshold Sharpe~{sr0:.2f})")
print(f"  -> {'PASSES (>0.95): edge is likely real' if dsr > 0.95 else 'FAILS (<0.95): not distinguishable from luck'}")

di, ci2 = index_series("Nifty 500"); mp = {d: ci2[i] for i, d in enumerate(di)}
md = sorted(set(dates[oos])); mb = [mp[d] for d in md if d in mp]
mr = np.array(mb[1:]) / np.array(mb[:-1]) - 1
c, dd, sh, tx = stats(mr)
print(f"\n  Nifty 500 (same window):     CAGR {c*100:5.1f}%  MaxDD {dd*100:6.1f}%  Sharpe {sh:.2f}")

# does ML beat simple momentum? feature importance
samp = np.where(oos & ~np.isnan(ml_scores))[0]
samp = np.random.default_rng(0).choice(samp, size=min(5000, len(samp)), replace=False)
mfull = HistGradientBoostingRegressor(max_iter=300, max_depth=4, random_state=0).fit(X[years < 2024], y[years < 2024])
pi = permutation_importance(mfull, X[samp], y[samp], n_repeats=3, random_state=0)
print("\n  Top features the model relies on:")
for j in np.argsort(pi.importances_mean)[::-1][:10]:
    print(f"     {feat_cols[j]:26} {pi.importances_mean[j]:+.5f}")
