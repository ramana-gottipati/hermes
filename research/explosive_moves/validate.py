"""Phase E — walk-forward out-of-sample validation + success ratio.

The in-sample lifts mean nothing until they hold out-of-sample. For each study we:

  1. Fit the depth-3 rule tree on a TRAIN period only, then apply the FROZEN tree
     to the TEST period and report train-vs-test hit ratio / lift per rule. Done
     both directions (2012-19 -> 2020-26 and reverse). A rule SURVIVES only if its
     test lift stays high. Non-survivors are reported and discarded (no silent
     lucky-pattern survivorship).

  2. SUCCESS RATIO / expectancy: for the event rows a surviving rule catches, the
     forward path (avg ret_22/66/132, win rate, MFE/MAE, big-winner rates) vs the
     baseline "random liquid day" benchmark — the real economic edge.

  3. By-year hit-ratio stability for the headline rule (regime robustness).

Median imputation is fit on TRAIN only (no leakage).
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from .common import research_conn, OUT_DIR
from .mine import _lift, load_study, TREE_FEATURES, _rule_for_leaf, MIN_COV, MIN_POS

warnings.filterwarnings("ignore")
OUTCOLS = ["ret_22", "ret_66", "ret_132", "mfe_6m", "mae_6m", "big50_6m", "big100_12m"]


def _yr(df):
    return df["year"].astype(int).to_numpy()


def _expectancy(ev_df):
    """Forward-path summary for a set of event rows (the success ratio)."""
    if len(ev_df) == 0:
        return {}
    out = {"n": len(ev_df)}
    out["avg_ret_22"] = float(ev_df["ret_22"].mean())
    out["avg_ret_66"] = float(ev_df["ret_66"].mean())
    out["avg_ret_132"] = float(ev_df["ret_132"].mean())
    out["median_ret_66"] = float(ev_df["ret_66"].median())
    out["win_rate_66"] = float((ev_df["ret_66"] > 0).mean())
    out["avg_mfe_6m"] = float(ev_df["mfe_6m"].mean())
    out["avg_mae_6m"] = float(ev_df["mae_6m"].mean())
    c132 = ev_df[ev_df["fwd_complete_132"] == 1]
    c252 = ev_df[ev_df["fwd_complete_252"] == 1]
    out["big50_6m_rate"] = float(c132["big50_6m"].mean()) if len(c132) else np.nan
    out["big100_12m_rate"] = float(c252["big100_12m"].mean()) if len(c252) else np.nan
    return out


def fit_eval(pos, ctrl, kw, train_rng, test_rng):
    from sklearn.tree import DecisionTreeClassifier
    alldf = pd.concat([pos, ctrl], ignore_index=True)
    is_pos = np.r_[np.ones(len(pos), bool), np.zeros(len(ctrl), bool)]
    yr = _yr(alldf)
    tr = (yr >= train_rng[0]) & (yr <= train_rng[1])
    te = (yr >= test_rng[0]) & (yr <= test_rng[1])
    X = alldf[TREE_FEATURES].astype(float)
    med = X[tr].median()
    X = X.fillna(med)
    y = is_pos.astype(float)
    sw = np.where(is_pos, 1.0, kw)
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=200, random_state=0)
    clf.fit(X[tr], y[tr], sample_weight=sw[tr])
    lv_tr = clf.apply(X[tr].to_numpy())
    lv_te = clf.apply(X[te].to_numpy())
    pos_tr, pos_te = is_pos[tr], is_pos[te]
    tot_pos_tr, tot_ctrl_tr = int(pos_tr.sum()), int((~pos_tr).sum())
    tot_pos_te, tot_ctrl_te = int(pos_te.sum()), int((~pos_te).sum())
    ev_te = alldf[te].reset_index(drop=True)          # for expectancy on test events
    rows = []
    for leaf in np.unique(lv_tr):
        a_tr = int(((lv_tr == leaf) & pos_tr).sum()); b_tr = int(((lv_tr == leaf) & ~pos_tr).sum())
        st_tr = _lift(a_tr, b_tr, kw, tot_pos_tr, tot_ctrl_tr)
        if st_tr["coverage"] < MIN_COV or st_tr["n_events_match"] < MIN_POS:
            continue
        a_te = int(((lv_te == leaf) & pos_te).sum()); b_te = int(((lv_te == leaf) & ~pos_te).sum())
        st_te = _lift(a_te, b_te, kw, tot_pos_te, tot_ctrl_te)
        exp = _expectancy(ev_te[(lv_te == leaf) & pos_te])
        rows.append({
            "rule": _rule_for_leaf(clf.tree_, leaf, TREE_FEATURES),
            "train_lift": st_tr["lift"], "train_hit": st_tr["hit_ratio"], "train_cov": st_tr["coverage"],
            "train_n": st_tr["n_events_match"],
            "test_lift": st_te["lift"], "test_hit": st_te["hit_ratio"], "test_cov": st_te["coverage"],
            "test_n": st_te["n_events_match"],
            **{f"te_{k}": v for k, v in exp.items()},
        })
    return pd.DataFrame(rows).sort_values("train_lift", ascending=False)


def baseline_expectancy(ctrl):
    return _expectancy(ctrl.rename(columns={}))


def run_study(rc, study):
    pos, ctrl, kw = load_study(rc, study)
    print(f"\n=== OOS VALIDATION: {study}  (pos={len(pos)}, ctrl={len(ctrl)}, kw={kw}) ===")
    base = baseline_expectancy(ctrl)
    print(f"  baseline random-day fwd: ret66={base.get('avg_ret_66'):.3f} "
          f"win66={base.get('win_rate_66'):.2f} big50={base.get('big50_6m_rate'):.3f}")
    frames = []
    for tr, te, tag in [((2012, 2019), (2020, 2026), "T12-19→2020-26"),
                        ((2020, 2026), (2012, 2019), "T20-26→2012-19")]:
        df = fit_eval(pos, ctrl, kw, tr, te)
        df.insert(0, "split", tag)
        frames.append(df)
        print(f"\n  [{tag}] rules (train_lift → test_lift):")
        for _, r in df.head(6).iterrows():
            print(f"    train: lift={r['train_lift']:.2f} hit={r['train_hit']:.3f} cov={r['train_cov']:.2f}"
                  f"  |  TEST: lift={r['test_lift']:.2f} hit={r['test_hit']:.3f} n={r['test_n']}  "
                  f"|  succ: ret66={r.get('te_avg_ret_66', float('nan')):.3f} "
                  f"big50={r.get('te_big50_6m_rate', float('nan')):.3f}")
            print(f"        IF {r['rule']}")
    out = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_DIR / f"oos_{study}.csv", index=False)
    out.to_sql(f"oos_{study}", rc, if_exists="replace", index=False)
    return out


def main():
    rc = research_conn()
    for s in ("daily", "weekly", "monthly", "sustained_vs_faded"):
        run_study(rc, s)
    rc.close()


if __name__ == "__main__":
    rc = research_conn()
    if len(sys.argv) > 1:
        run_study(rc, sys.argv[1])
    else:
        main()
    rc.close()
