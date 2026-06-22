"""Phase C + D — pattern discovery.

C (univariate): for every precursor feature, how over-represented is it before
explosive moves vs the quiet baseline? Effect size (Cliff's delta), Mann-Whitney
significance, and — the number that matters — a reweighted threshold sweep giving
HIT RATIO (precision = P(move starts | pattern)), LIFT (vs base rate), and COVERAGE.

D (multivariate): a shallow, interpretable decision tree over the high-coverage
features -> human-readable conjunction rules (the "setups"), each scored with the
same reweighted hit ratio / lift / coverage. A random forest ranks feature
importance (discovery only, not a black-box strategy).

All precision/lift uses the baseline reweight factor K (baseline = 1-in-K sample
of non-event liquid days) so numbers are real-world, not sample-relative.

Studies:
  daily / weekly / monthly  : positives vs quiet baseline.
  sustained_vs_faded        : among >=20% monthly thrusts, what makes it HOLD?
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from .common import research_conn, OUT_DIR, cliffs_delta
from .features import RAW_NUM, HOUSE_NUM, HOUSE_TXT, CPR_NUM, CPR_TXT

warnings.filterwarnings("ignore")

NUM_FEATURES = RAW_NUM + ["h_" + c for c in HOUSE_NUM] + ["cpr_" + c for c in CPR_NUM]
TXT_FEATURES = ["h_" + c for c in HOUSE_TXT] + ["cpr_" + c for c in CPR_TXT]
# Discovery rules are built from RAW data ONLY — we do NOT lean on the DVPT/house battery
# (Ramana's call). DVPT features are still scored in the univariate pass for COMPARISON.
TREE_FEATURES = list(RAW_NUM)


def _group(f):
    if f.startswith("h_"):
        return "house(DVPT)"
    if f.startswith("cpr_"):
        return "cpr"
    return "raw"

MIN_COV = 0.03      # a pattern must cover >=3% of events
MIN_POS = 25        # and match at least 25 actual events


def _lift(a, b, kw, tot_pos, tot_ctrl):
    """Reweighted stats. a=#events matching, b=#controls matching, kw=control weight."""
    denom = a + kw * b
    base = tot_pos / (tot_pos + kw * tot_ctrl)
    prec = a / denom if denom > 0 else np.nan
    return {
        "hit_ratio": prec, "lift": prec / base if base > 0 else np.nan,
        "coverage": a / tot_pos if tot_pos else np.nan,
        "n_events_match": int(a), "support_real": float(denom), "base_rate": base,
    }


def load_study(rc, name):
    if name in ("daily", "weekly"):
        pos = pd.read_sql_query(f"SELECT * FROM features WHERE etype='{name}' AND label=1", rc)
        ctrl = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
        kw = float(dict(rc.execute("SELECT k,v FROM feat_meta").fetchall())["baseline_k"])
    elif name == "monthly":
        pos = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly' AND sustained=1", rc)
        ctrl = pd.read_sql_query("SELECT * FROM features WHERE etype='baseline'", rc)
        kw = float(dict(rc.execute("SELECT k,v FROM feat_meta").fetchall())["baseline_k"])
    elif name == "sustained_vs_faded":
        pos = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly' AND sustained=1", rc)
        ctrl = pd.read_sql_query("SELECT * FROM features WHERE etype='monthly' AND sustained=0", rc)
        kw = 1.0
    else:
        raise ValueError(name)
    return pos, ctrl, kw


def univariate(pos, ctrl, kw):
    rows = []
    tot_pos, tot_ctrl = len(pos), len(ctrl)
    for f in NUM_FEATURES:
        p = pos[f].to_numpy(dtype=float); c = ctrl[f].to_numpy(dtype=float)
        p = p[~np.isnan(p)]; c = c[~np.isnan(c)]
        if len(p) < MIN_POS or len(c) < 20:
            continue
        delta = cliffs_delta(p, c)
        pooled = np.concatenate([p, c])
        best = None
        for q in (0.5, 0.6, 0.7, 0.8, 0.9):
            t = np.quantile(pooled, q)
            for direction in (">=", "<="):
                if direction == ">=":
                    a = int(np.sum(pos[f] >= t)); b = int(np.sum(ctrl[f] >= t))
                else:
                    a = int(np.sum(pos[f] <= t)); b = int(np.sum(ctrl[f] <= t))
                st = _lift(a, b, kw, tot_pos, tot_ctrl)
                if st["coverage"] < MIN_COV or st["n_events_match"] < MIN_POS:
                    continue
                if best is None or st["lift"] > best["lift"]:
                    best = {**st, "threshold": float(t), "direction": direction}
        if best is None:
            continue
        rows.append({"feature": f, "group": _group(f), "kind": "numeric", "cliffs_delta": delta,
                     "pos_median": float(np.median(p)), "ctrl_median": float(np.median(c)),
                     **best})
    # categoricals
    for f in TXT_FEATURES:
        cats = pd.concat([pos[f], ctrl[f]]).dropna().unique()
        for cat in cats:
            a = int(np.sum(pos[f] == cat)); b = int(np.sum(ctrl[f] == cat))
            st = _lift(a, b, kw, tot_pos, tot_ctrl)
            if st["coverage"] < MIN_COV or st["n_events_match"] < MIN_POS:
                continue
            rows.append({"feature": f, "group": _group(f), "kind": "categorical", "category": str(cat),
                         "direction": "==", "threshold": np.nan, "cliffs_delta": np.nan,
                         **st})
    df = pd.DataFrame(rows).sort_values("lift", ascending=False)
    return df


def _rule_for_leaf(tree, leaf_id, feat_names):
    """Reconstruct the conjunction (feature op threshold) along the path to a leaf."""
    L, R = tree.children_left, tree.children_right
    feat, thr = tree.feature, tree.threshold
    # find path from root to leaf
    parent = {0: (None, None)}
    stack = [0]
    while stack:
        nid = stack.pop()
        if L[nid] != R[nid]:
            parent[L[nid]] = (nid, "L"); parent[R[nid]] = (nid, "R")
            stack += [L[nid], R[nid]]
    conds, cur = [], leaf_id
    while parent.get(cur, (None, None))[0] is not None:
        p, side = parent[cur]
        op = "<=" if side == "L" else ">"
        conds.append(f"{feat_names[feat[p]]} {op} {thr[p]:.4g}")
        cur = p
    return " AND ".join(reversed(conds))


def multivariate(pos, ctrl, kw, study):
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    X = pd.concat([pos[TREE_FEATURES], ctrl[TREE_FEATURES]], ignore_index=True).astype(float)
    med = X.median()
    X = X.fillna(med)
    y = np.r_[np.ones(len(pos)), np.zeros(len(ctrl))]
    sw = np.r_[np.ones(len(pos)), np.full(len(ctrl), kw)]
    tot_pos, tot_ctrl = len(pos), len(ctrl)

    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=200, random_state=0)
    clf.fit(X, y, sample_weight=sw)
    leaves = clf.apply(X)
    is_pos = y == 1
    rules = []
    for leaf in np.unique(leaves):
        m = leaves == leaf
        a = int(np.sum(m & is_pos)); b = int(np.sum(m & ~is_pos))
        st = _lift(a, b, kw, tot_pos, tot_ctrl)
        if st["coverage"] < MIN_COV or st["n_events_match"] < MIN_POS:
            continue
        rules.append({"rule": _rule_for_leaf(clf.tree_, leaf, TREE_FEATURES), **st})
    rules = pd.DataFrame(rules).sort_values("lift", ascending=False) if rules else pd.DataFrame()

    rf = RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=100,
                                random_state=0, n_jobs=-1)
    rf.fit(X, y, sample_weight=sw)
    imp = pd.DataFrame({"feature": TREE_FEATURES, "importance": rf.feature_importances_}) \
        .sort_values("importance", ascending=False)
    return rules, imp


def run_study(rc, name):
    pos, ctrl, kw = load_study(rc, name)
    print(f"\n=== STUDY {name}: {len(pos)} positives vs {len(ctrl)} controls (kw={kw}) ===")
    base = len(pos) / (len(pos) + kw * len(ctrl))
    print(f"  base rate = {base:.4%}")
    uni = univariate(pos, ctrl, kw)
    rules, imp = multivariate(pos, ctrl, kw, name)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    uni.to_csv(OUT_DIR / f"univariate_{name}.csv", index=False)
    if len(rules):
        rules.to_csv(OUT_DIR / f"rules_{name}.csv", index=False)
    imp.to_csv(OUT_DIR / f"importance_{name}.csv", index=False)
    uni.to_sql(f"uni_{name}", rc, if_exists="replace", index=False)
    if len(rules):
        rules.to_sql(f"rules_{name}", rc, if_exists="replace", index=False)
    def _show(df, n):
        for _, r in df.head(n).iterrows():
            val = r["category"] if r["kind"] == "categorical" else round(r["threshold"], 4)
            print(f"    lift={r['lift']:.2f} hit={r['hit_ratio']:.3f} cov={r['coverage']:.2f} "
                  f"n={r['n_events_match']:5d}  {r['feature']} {r['direction']} {val}")
    print("  RAW-data precursors (PRIMARY discovery, by lift):")
    _show(uni[uni.group == "raw"], 12)
    print("  DVPT/house battery (COMPARISON only — how Ramana's hand-made signals rank):")
    _show(uni[uni.group == "house(DVPT)"], 6)
    if len(rules):
        print("  TOP multivariate rules (by lift):")
        for _, r in rules.head(6).iterrows():
            print(f"    lift={r['lift']:.2f} hit={r['hit_ratio']:.3f} cov={r['coverage']:.2f} "
                  f"n={r['n_events_match']:5d}  IF {r['rule']}")
    print("  TOP forest importances:", ", ".join(imp.head(8)["feature"]))


def main():
    rc = research_conn()
    for name in ("daily", "weekly", "monthly", "sustained_vs_faded"):
        run_study(rc, name)
    rc.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        rc = research_conn(); run_study(rc, sys.argv[1]); rc.close()
    else:
        main()
