"""Ignition feature discrimination — what ACTUALLY separates winners (design §7, champion side).

The backtest's honest verdict: raw intensity (and RS rank) barely separate winning
ignitions from losing ones. So before training any challenger model, answer the
prior question transparently — for each signal-time feature, how far apart are the
win-rates of its TOP vs BOTTOM quintile? A feature with a big spread is a real
separator; a flat one is noise. Pure Python, fully interpretable, no overfit, no
ML libs (the production venv bans numpy/sklearn; a black box would also hide the
answer this is meant to surface).

Label = the backtest's default win: MFE ≥ +25% reached BEFORE MAE ≤ −15% (path-aware,
from ignition_outcomes). Only clean events (no continuity break, ≥6m forward).

Self-contained (capture.py pattern): OWNS `feature_lift`, never edits db.py. Reads
ignition_outcomes ⋈ stock_signals (the features at the signal date). Output = a
ranked table of features by |win-rate lift|, so the next step (a challenger model,
or a smarter rule) starts from evidence, not a hunch.

Run:        python -m src.automation.ignition_features
Self-check: python -m src.automation.ignition_features --selftest
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.ignition_features")

WIN_TARGET = 25.0      # MFE % — must match ignition_backtest.DEFAULT_WIN
WIN_STOP = -15.0       # MAE-before-peak %
MIN_PER_BUCKET = 30    # need this many events per quintile to trust a number
N_BUCKETS = 5

# numeric features carried on ignition_outcomes itself
NUMERIC_O = ["intensity", "rs_rank"]
# numeric features read from stock_signals at the signal date
NUMERIC_S = [
    "gap_to_key_p1m", "gap_to_key_p3m", "gap_to_key_p6m", "gap_to_key_p12m",
    "turnover_surge_1m", "turnover_surge_3m", "turnover_surge_1y",
    "deliv_updown_ratio_3m", "trade_count_ratio_1m_6m", "accum_price_drift_3m",
    "avg_deliv_pct_1m", "avg_deliv_pct_6m", "pct_from_52w_high",
    "rs_vs_broad_slope_3m", "rs_vs_broad_slope_6m", "rs_vs_broad_slope_12m",
    "rs_vs_sector_slope_3m", "price_vs_hot_avg_pct", "deliv_value_ratio_1m_6m",
]
CATEGORICAL_S = ["accum_character", "primary_sector", "is_ath_dvpt"]


def _is_win(mfe, mae_pre) -> Optional[bool]:
    if mfe is None or mae_pre is None:
        return None
    return (mfe >= WIN_TARGET) and (mae_pre > WIN_STOP)


def _buckets(pairs, k=N_BUCKETS):
    """pairs = [(value, win_bool)] for non-null values. Sort by value, split into
    k near-equal slices, return [(n, win_rate)] lowest→highest."""
    pairs = sorted(pairs, key=lambda t: t[0])
    n = len(pairs)
    out = []
    for b in range(k):
        lo = (b * n) // k
        hi = ((b + 1) * n) // k
        sl = pairs[lo:hi]
        wr = (100.0 * sum(1 for _, w in sl if w) / len(sl)) if sl else None
        out.append((len(sl), wr))
    return out


def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return (sum(xs) / len(xs)) if xs else None


# ── storage ───────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS feature_lift (
    feature      TEXT PRIMARY KEY,
    kind         TEXT,        -- 'num' | 'cat'
    n            INTEGER,
    lift         REAL,        -- num: Q5_win - Q1_win ; cat: best_cat_win - worst_cat_win
    lo_label     TEXT,        -- 'Q1' or worst category
    lo_win       REAL,
    hi_label     TEXT,        -- 'Q5' or best category
    hi_win       REAL,
    winner_mean  REAL,        -- num only
    loser_mean   REAL,        -- num only
    computed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_COLS = ["feature", "kind", "n", "lift", "lo_label", "lo_win", "hi_label", "hi_win",
         "winner_mean", "loser_mean"]


def compute_and_store(conn=None) -> dict:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        sel = (["o.symbol", "o.mfe_pct", "o.mae_before_peak_pct"]
               + [f"o.{c}" for c in NUMERIC_O]
               + [f"s.{c}" for c in NUMERIC_S + CATEGORICAL_S])
        rows = [dict(r) for r in conn.execute(
            f"SELECT {', '.join(sel)} FROM ignition_outcomes o "
            f"JOIN stock_signals s ON s.symbol=o.symbol AND s.trade_date=o.signal_date "
            f"WHERE o.break_in_window=0 AND o.ret_6m IS NOT NULL").fetchall()]

        labelled = [(r, _is_win(r["mfe_pct"], r["mae_before_peak_pct"])) for r in rows]
        labelled = [(r, w) for r, w in labelled if w is not None]
        n_all = len(labelled)
        base = (100.0 * sum(1 for _, w in labelled if w) / n_all) if n_all else 0.0

        results = []
        for f in NUMERIC_O + NUMERIC_S:
            pairs = [(r[f], w) for r, w in labelled if isinstance(r.get(f), (int, float))]
            if len(pairs) < MIN_PER_BUCKET * N_BUCKETS:
                continue
            bk = _buckets(pairs)
            q1, q5 = bk[0][1], bk[-1][1]
            if q1 is None or q5 is None:
                continue
            wmean = _mean([r[f] for r, w in labelled if w and isinstance(r.get(f), (int, float))])
            lmean = _mean([r[f] for r, w in labelled if not w and isinstance(r.get(f), (int, float))])
            results.append({"feature": f, "kind": "num", "n": len(pairs),
                            "lift": round(q5 - q1, 1), "lo_label": "Q1", "lo_win": round(q1, 1),
                            "hi_label": "Q5", "hi_win": round(q5, 1),
                            "winner_mean": round(wmean, 3) if wmean is not None else None,
                            "loser_mean": round(lmean, 3) if lmean is not None else None})

        for f in CATEGORICAL_S:
            cats: dict = {}
            for r, w in labelled:
                v = r.get(f)
                if v is None:
                    continue
                cats.setdefault(str(v), []).append(w)
            cat_wr = {c: (100.0 * sum(1 for w in ws if w) / len(ws), len(ws))
                      for c, ws in cats.items() if len(ws) >= MIN_PER_BUCKET}
            if len(cat_wr) < 2:
                continue
            best = max(cat_wr, key=lambda c: cat_wr[c][0])
            worst = min(cat_wr, key=lambda c: cat_wr[c][0])
            results.append({"feature": f, "kind": "cat",
                            "n": sum(v[1] for v in cat_wr.values()),
                            "lift": round(cat_wr[best][0] - cat_wr[worst][0], 1),
                            "lo_label": f"{worst} (n{cat_wr[worst][1]})", "lo_win": round(cat_wr[worst][0], 1),
                            "hi_label": f"{best} (n{cat_wr[best][1]})", "hi_win": round(cat_wr[best][0], 1),
                            "winner_mean": None, "loser_mean": None})

        results.sort(key=lambda d: abs(d["lift"]), reverse=True)
        conn.execute("DELETE FROM feature_lift")
        conn.executemany(
            f"INSERT OR REPLACE INTO feature_lift ({','.join(_COLS)}) "
            f"VALUES ({','.join('?'*len(_COLS))})", [[r.get(c) for c in _COLS] for r in results])
        if own:
            conn.commit()

        stats = {"events": n_all, "base_win_rate": round(base, 1),
                 "features_scored": len(results),
                 "top": [(r["feature"], r["lift"]) for r in results[:6]]}
        log.info("ignition_features: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


def ranked(conn=None) -> list:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM feature_lift ORDER BY ABS(lift) DESC").fetchall()]
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── self-check (synthetic — a known separator + a known noise feature) ────────
def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # ignition_outcomes (minimal) + stock_signals (all referenced feature cols)
    scols = ", ".join(f"{c} REAL" for c in NUMERIC_S) + ", " + \
            ", ".join(f"{c} TEXT" for c in CATEGORICAL_S)
    conn.executescript(f"""
        CREATE TABLE ignition_outcomes (symbol TEXT, signal_date TEXT, mfe_pct REAL,
            mae_before_peak_pct REAL, intensity REAL, rs_rank INTEGER,
            break_in_window INTEGER, ret_6m REAL);
        CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, {scols});
    """)
    d = "2020-06-01"
    n = 300
    for i in range(n):
        winner = (i % 2 == 0)                         # half winners
        mfe = 50.0 if winner else 10.0
        # GOOD separator: gap_to_key_p3m high for winners, low for losers
        good = (100.0 + i) if winner else (0.0 + i % 10)
        noise = float(i % 7)                          # unrelated to outcome
        conn.execute("INSERT INTO ignition_outcomes VALUES (?,?,?,?,?,?,0,5.0)",
                     (f"S{i}", d, mfe, -5.0, 2.0, 50))
        conn.execute(
            "INSERT INTO stock_signals (symbol, trade_date, gap_to_key_p3m, turnover_surge_3m, accum_character) "
            "VALUES (?,?,?,?,?)",
            (f"S{i}", d, good, noise, "ACCUMULATION" if winner else "DISTRIBUTION"))

    stats = compute_and_store(conn=conn)
    rk = ranked(conn=conn)
    by = {r["feature"]: r for r in rk}
    assert "gap_to_key_p3m" in by, "separator feature must be scored"
    assert by["gap_to_key_p3m"]["lift"] > 50, by["gap_to_key_p3m"]      # near-perfect separation
    assert abs(by["turnover_surge_3m"]["lift"]) < 25, by["turnover_surge_3m"]  # noise ~flat
    assert rk[0]["feature"] in ("gap_to_key_p3m", "accum_character"), rk[0]
    # categorical: ACCUMULATION (all winners) vs DISTRIBUTION (all losers) → huge lift
    assert by["accum_character"]["lift"] > 50, by["accum_character"]
    print(f"ignition_features selftest: OK  base={stats['base_win_rate']}% top={stats['top'][:3]}")


def main() -> None:
    p = argparse.ArgumentParser(description="Which signal-time features separate winning ignitions?")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    stats = compute_and_store()
    print(f"\nbase win-rate: {stats['base_win_rate']}%   events: {stats['events']}\n")
    print(f"{'feature':<26}{'kind':<5}{'n':>6}{'lift':>8}   low → high win-rate")
    print("-" * 78)
    for r in ranked():
        print(f"{r['feature']:<26}{r['kind']:<5}{r['n']:>6}{r['lift']:>8}   "
              f"{r['lo_label']} {r['lo_win']}% → {r['hi_label']} {r['hi_win']}%")


if __name__ == "__main__":
    main()
