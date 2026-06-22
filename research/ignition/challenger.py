"""Track B — the ignition challenger: can a multivariate model (incl. point-in-time
FUNDAMENTALS) rank ignitions into a top-decile edge where intensity and the linear
composite (A) both failed out-of-sample?

A tested EOD price/delivery features only. B adds the one untested axis — quality/
growth fundamentals as-of the signal date (via src/automation/fundamentals_asof.py) —
plus a nonlinear model (HistGradientBoosting, which captures interactions and handles
NaN natively). Expanding walk-forward (train years < Y, predict Y), pooled OOS, on the
SAME label + metric as A so it's directly comparable: top-decile win-rate vs the base
AND vs intensity, plus AUC and permutation importance (do fundamentals carry weight?).

Honest by construction: the simple year-split (no purge, matching A) mildly LEAKS via
the 6–24m outcome window, which biases TOWARD finding an edge — so if B still fails OOS,
the negative verdict is robust; if it shows edge, it must be re-tested with an embargo.

Research-only (.venv-research): reads hermes.db read-only + research.db; writes nothing
to production; ₹0 at runtime. Run from /opt/hermes:
    .venv-research/bin/python -m research.ignition.challenger [--limit N]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sqlite3

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

MAIN_DB = os.environ.get("HERMES_MAIN_DB", "/opt/hermes/data/hermes.db")
FUND_PATH = os.environ.get("HERMES_FUND_ASOF", "/opt/hermes/src/automation/fundamentals_asof.py")

WIN_TARGET, WIN_STOP = 25.0, -15.0
MIN_TRAIN, MIN_TEST = 3000, 200

# signal-time features from stock_signals (same set A used)
SIG_S = [
    "gap_to_key_p1m", "gap_to_key_p3m", "gap_to_key_p6m", "gap_to_key_p12m",
    "turnover_surge_1m", "turnover_surge_3m", "turnover_surge_1y",
    "deliv_updown_ratio_3m", "trade_count_ratio_1m_6m", "accum_price_drift_3m",
    "avg_deliv_pct_1m", "avg_deliv_pct_6m", "pct_from_52w_high",
    "rs_vs_broad_slope_3m", "rs_vs_broad_slope_6m", "rs_vs_broad_slope_12m",
    "rs_vs_sector_slope_3m", "price_vs_hot_avg_pct", "deliv_value_ratio_1m_6m",
]
CHAR_NUM = {"ACCUMULATION": 1.0, "NEUTRAL": 0.0, "CONSOLIDATION": -0.5, "DISTRIBUTION": -1.0}


def _num(v):
    return float(v) if isinstance(v, (int, float)) else np.nan


def _load_fund():
    spec = importlib.util.spec_from_file_location("fund_asof", FUND_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def build(limit=None):
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    fund = _load_fund()

    sel = (["o.symbol", "o.signal_date", "o.mfe_pct", "o.mae_before_peak_pct",
            "o.intensity", "o.rs_rank", "s.accum_character", "s.is_ath_dvpt"]
           + [f"s.{c}" for c in SIG_S])
    q = (f"SELECT {', '.join(sel)} FROM ignition_outcomes o "
         f"JOIN stock_signals s ON s.symbol=o.symbol AND s.trade_date=o.signal_date "
         f"WHERE o.break_in_window=0 AND o.ret_6m IS NOT NULL ORDER BY o.signal_date")
    rows = con.execute(q).fetchall()
    con.close()
    if limit:
        rows = rows[:limit]

    # point-in-time fundamentals per event (cache the history frame per symbol)
    cache, recs, fkeys = {}, [], set()
    fund_hit = 0
    for r in rows:
        if r["mfe_pct"] is None or r["mae_before_peak_pct"] is None:
            continue
        win = 1 if (r["mfe_pct"] >= WIN_TARGET and r["mae_before_peak_pct"] > WIN_STOP) else 0
        sym, d = r["symbol"], r["signal_date"]
        if sym not in cache:
            try:
                cache[sym] = fund.load_symbol_history(sym)
            except Exception:
                cache[sym] = None
        fa = fund.as_of_from_frame(cache[sym], d, symbol=sym) if cache[sym] else None
        fnum = {f"f_{k}": float(v) for k, v in (fa or {}).items() if isinstance(v, (int, float))}
        if fnum:
            fund_hit += 1
        fkeys |= set(fnum)
        recs.append((r, fnum, win, d, _num(r["intensity"])))

    fund_cols = sorted(fkeys)
    feat_names = ["intensity", "rs_rank"] + SIG_S + ["char_num", "is_ath"] + fund_cols
    X, y, dates, inten = [], [], [], []
    for r, fnum, win, d, intensity in recs:
        sig = [_num(r["intensity"]), _num(r["rs_rank"])] + [_num(r[c]) for c in SIG_S]
        enc = [CHAR_NUM.get(r["accum_character"], np.nan),
               (1.0 if r["is_ath_dvpt"] else 0.0) if r["is_ath_dvpt"] is not None else np.nan]
        fv = [fnum.get(k, np.nan) for k in fund_cols]
        X.append(sig + enc + fv)
        y.append(win)
        dates.append(d)
        inten.append(intensity if not np.isnan(intensity) else -1e9)
    return (np.array(X, dtype=float), np.array(y), np.array(dates),
            np.array(inten), feat_names, fund_hit, len(fund_cols))


def _topdecile_win(score, y):
    k = max(1, len(score) // 10)
    order = np.argsort(score)[::-1][:k]
    return round(100.0 * y[order].mean(), 1), k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="cap events (smoke test)")
    args = ap.parse_args()

    X, y, dates, inten, feat_names, fund_hit, n_fund = build(limit=args.limit)
    years = np.array([int(d[:4]) for d in dates])
    print(f"events {len(y)} | features {len(feat_names)} ({n_fund} fundamentals) | "
          f"fundamentals present on {fund_hit} ({100*fund_hit/max(len(y),1):.0f}%) | base win {100*y.mean():.1f}%\n")

    oos = np.full(len(y), np.nan)
    for ty in sorted(set(years)):
        tr, te = years < ty, years == ty
        if tr.sum() < MIN_TRAIN or te.sum() < MIN_TEST:
            continue
        m = HistGradientBoostingClassifier(max_iter=300, max_depth=4, learning_rate=0.05,
                                           l2_regularization=1.0, random_state=0)
        m.fit(X[tr], y[tr])
        oos[te] = m.predict_proba(X[te])[:, 1]

    mask = ~np.isnan(oos)
    n = int(mask.sum())
    if n == 0:
        print("no OOS folds (insufficient data)")
        return
    yo, so, io = y[mask], oos[mask], inten[mask]
    base = round(100.0 * yo.mean(), 1)
    ml_top, k = _topdecile_win(so, yo)
    int_top, _ = _topdecile_win(io, yo)
    auc = round(roc_auc_score(yo, so), 3)

    print(f"OUT-OF-SAMPLE ({n} events, walk-forward, decile n={k}):")
    print(f"  base win-rate            {base}%")
    print(f"  intensity top-decile     {int_top}%   ({int_top-base:+.1f} vs base)")
    print(f"  ML top-decile            {ml_top}%   ({ml_top-base:+.1f} vs base)")
    print(f"  ML AUC                   {auc}   (0.5 = no skill)")
    verdict = ("BEATS base OOS — re-test with an embargo before trusting"
               if ml_top - base >= 3.0 and auc >= 0.55 else
               "does NOT beat base OOS — no ranked edge, even with fundamentals + nonlinear ML")
    print(f"  -> ML {verdict}\n")

    # which features does it lean on? (fit on pre-2024, permutation-importance a sample)
    tr = years < 2024
    if tr.sum() > 2000:
        m = HistGradientBoostingClassifier(max_iter=300, max_depth=4, random_state=0).fit(X[tr], y[tr])
        samp = np.where(mask)[0]
        rng = np.random.default_rng(0)
        samp = rng.choice(samp, size=min(4000, len(samp)), replace=False)
        pi = permutation_importance(m, X[samp], y[samp], n_repeats=3, random_state=0, scoring="roc_auc")
        print("  top features by permutation importance (f_ = fundamental):")
        for j in np.argsort(pi.importances_mean)[::-1][:12]:
            print(f"     {feat_names[j]:26} {pi.importances_mean[j]:+.4f}")


if __name__ == "__main__":
    main()
