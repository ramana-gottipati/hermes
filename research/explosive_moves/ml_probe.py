"""Let the DATA speak: gradient-boosting over the full ~85-feature matrix to predict
explosive movers (became a +50% mover within 6 months), vs the dumb momentum rule.

Walk-forward: train on launches with year<=2018, test on year>=2019 (no look-ahead;
every feature is as-of the launch day). Reports: test AUC, top-decile lift over base
rate for the ML model vs ranking by momentum (ret_22d) alone, and what the model keys on.
"""
import sqlite3
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.inspection import permutation_importance

rc = sqlite3.connect("file:/opt/hermes/data/research.db?mode=ro", uri=True)
cols = [r[1] for r in rc.execute("PRAGMA table_info(features)")]

# FORWARD/outcome/id columns to exclude from predictors (avoid look-ahead)
EXCL = {"symbol", "etype", "launch_date", "year", "label", "sustained", "magnitude",
        "ret_5", "ret_10", "ret_22", "ret_66", "ret_132", "ret_252",
        "mfe_6m", "mae_6m", "maxrun_12m", "big50_6m", "big100_12m",
        "fwd_complete_132", "fwd_complete_252",
        # text columns
        "h_trigger_rank", "h_accum_character", "h_rs_vs_broad_trend_state",
        "h_rs_vs_sector_trend_state", "h_next_p_above", "cpr_pattern", "cpr_regime"}
feat_cols = [c for c in cols if c not in EXCL]

rows = rc.execute(
    f"SELECT year, big50_6m, ret_22d, {','.join(feat_cols)} FROM features "
    f"WHERE big50_6m IS NOT NULL AND fwd_complete_132=1").fetchall()
rc.close()

year = np.array([int(r[0]) for r in rows])
y = np.array([int(r[1]) for r in rows])
mom = np.array([float(r[2]) if r[2] is not None else np.nan for r in rows])
X = np.array([[float(v) if v is not None else np.nan for v in r[2:]] for r in rows])
print(f"{len(rows)} samples, {len(feat_cols)} features. big50 base rate={y.mean():.1%}")

tr = year <= 2018
te = year >= 2019
print(f"train {tr.sum()} (<=2018), test {te.sum()} (>=2019); test base rate={y[te].mean():.1%}")

clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05,
                                     max_depth=4, l2_regularization=1.0,
                                     random_state=0)
clf.fit(X[tr], y[tr])
p = clf.predict_proba(X[te])[:, 1]
auc = roc_auc_score(y[te], p)
base = y[te].mean()


def decile_lift(score, label, q=0.90):
    thr = np.nanquantile(score, q)
    top = score >= thr
    return label[top].mean(), label[top].mean() / label.mean(), top.sum()


ml_prec, ml_lift, ml_n = decile_lift(p, y[te])
mom_te = mom[te]
mm_prec, mm_lift, mm_n = decile_lift(np.where(np.isnan(mom_te), -1e9, mom_te), y[te])

print(f"\nTEST (2019+):  ML model AUC = {auc:.3f}")
print(f"  ML  top-decile: {ml_prec:.1%} are +50% movers  -> lift {ml_lift:.2f}x base (n={ml_n})")
print(f"  MOM top-decile: {mm_prec:.1%} are +50% movers  -> lift {mm_lift:.2f}x base (n={mm_n})")
print(f"  (base rate {base:.1%}; higher lift = better at finding explosive movers)")

# what does the model key on?
print("\nTop 15 features the MODEL relies on (permutation importance, test sample):")
idx = np.where(te)[0]
samp = np.random.default_rng(0).choice(idx, size=min(4000, len(idx)), replace=False)
pi = permutation_importance(clf, X[samp], y[samp], n_repeats=3, random_state=0,
                            scoring="roc_auc")
order = np.argsort(pi.importances_mean)[::-1][:15]
for j in order:
    print(f"   {feat_cols[j]:24s} {pi.importances_mean[j]:+.4f}")
