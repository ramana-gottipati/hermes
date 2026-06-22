"""Ignition ranking v2 — evidence-weighted champion + walk-forward OOS proof (design §A / §7 champion).

The backtest showed raw intensity is wrong-signed and no single feature dominates.
v2 is a transparent, data-derived composite: standardise each signal-time feature,
weight it by its observed win-rate lift (so intensity earns a NEGATIVE weight, and
the real separators — 12m RS-slope, gap-to-key, proximity-to-52w-high, accumulation
character — earn the positive ones), then sum the clipped z-scores. Sector is
EXCLUDED (regime-suspect; locked decision). No hand-picked weights, no ML black box.

The proof is WALK-FORWARD (no in-sample cheating): for each test year Y, derive the
weights + standardisation on events BEFORE Y, score year Y, and compare the top-decile
win-rate against the ~42% base AND against ranking by intensity. If v2's top decile
doesn't beat both out-of-sample, the report says so plainly.

Self-contained: OWNS `ignition_rank_v2`, never edits db.py or the shipped ignition.py.
Reads ignition_outcomes ⋈ stock_signals. Pure Python.

Run:        python -m src.automation.ignition_rankv2           # walk-forward proof + score today
Proof only: python -m src.automation.ignition_rankv2 --walkforward
Self-check: python -m src.automation.ignition_rankv2 --selftest
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from src.core.db import get_conn
from src.automation.ignition_features import NUMERIC_S, _is_win, _buckets

log = logging.getLogger("hermes.ignition_rankv2")

# encoded categoricals (sector deliberately excluded)
CHAR_NUM = {"ACCUMULATION": 1.0, "NEUTRAL": 0.0, "CONSOLIDATION": -0.5, "DISTRIBUTION": -1.0}
# the score's numeric feature set
FEATURES = ["intensity", "rs_rank", "is_ath_num", "char_num"] + NUMERIC_S
MIN_TRAIN, MIN_TEST = 2000, 300
Z_CLIP = 3.0


def _feat(row: dict) -> dict:
    f = {
        "intensity": row.get("intensity"),
        "rs_rank": row.get("rs_rank"),
        "is_ath_num": (1.0 if row.get("is_ath_dvpt") else 0.0) if row.get("is_ath_dvpt") is not None else None,
        "char_num": CHAR_NUM.get(row.get("accum_character")),
    }
    for c in NUMERIC_S:
        f[c] = row.get(c)
    return f


def _mean_std(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    n = len(xs)
    if n < 2:
        return None
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / n
    return (mu, var ** 0.5)


def _weights(events: list) -> dict:
    """Per feature: (signed win-rate lift as weight, mean, std), learned on `events`."""
    w = {}
    for f in FEATURES:
        pairs = [(e["feat"][f], e["win"]) for e in events
                 if isinstance(e["feat"].get(f), (int, float)) and e["win"] is not None]
        if len(pairs) < 150:
            continue
        bk = _buckets(pairs)
        if bk[0][1] is None or bk[-1][1] is None:
            continue
        lift = (bk[-1][1] - bk[0][1]) / 100.0
        ms = _mean_std([p[0] for p in pairs])
        if not ms or ms[1] == 0:
            continue
        w[f] = (lift, ms[0], ms[1])
    return w


def _score(feat: dict, w: dict) -> float:
    s = 0.0
    for f, (lift, mu, sd) in w.items():
        v = feat.get(f)
        if not isinstance(v, (int, float)):
            continue
        z = max(-Z_CLIP, min(Z_CLIP, (v - mu) / sd))
        s += lift * z
    return s


def _load(conn) -> list:
    sel = (["o.symbol", "o.signal_date", "o.mfe_pct", "o.mae_before_peak_pct",
            "o.intensity", "o.rs_rank", "s.accum_character", "s.is_ath_dvpt"]
           + [f"s.{c}" for c in NUMERIC_S])
    rows = conn.execute(
        f"SELECT {', '.join(sel)} FROM ignition_outcomes o "
        f"JOIN stock_signals s ON s.symbol=o.symbol AND s.trade_date=o.signal_date "
        f"WHERE o.break_in_window=0 AND o.ret_6m IS NOT NULL").fetchall()
    out = []
    for r in rows:
        rd = dict(r)
        w = _is_win(rd["mfe_pct"], rd["mae_before_peak_pct"])
        if w is None:
            continue
        out.append({"symbol": rd["symbol"], "year": rd["signal_date"][:4], "win": w,
                    "intensity": rd["intensity"] if rd["intensity"] is not None else -1e9,
                    "feat": _feat(rd)})
    return out


def _topdecile_win(pool: list, keyfn) -> tuple:
    s = sorted(pool, key=keyfn, reverse=True)
    k = max(1, len(s) // 10)
    return round(100.0 * sum(1 for e in s[:k] if e["win"]) / k, 1), k


def walk_forward(conn, min_train=MIN_TRAIN, min_test=MIN_TEST) -> dict:
    """Honest OOS: weights from years < Y, scored on year Y, pooled. Compares v2's
    top decile vs intensity's vs the base win-rate."""
    events = _load(conn)
    years = sorted({e["year"] for e in events})
    pool, folds = [], []
    for Y in years:
        train = [e for e in events if e["year"] < Y]
        test = [e for e in events if e["year"] == Y]
        if len(train) < min_train or len(test) < min_test:
            continue
        w = _weights(train)
        if not w:
            continue
        for e in test:
            pool.append({"win": e["win"], "intensity": e["intensity"], "v2": _score(e["feat"], w)})
        folds.append(Y)
    if not pool:
        return {"oos_events": 0}
    base = round(100.0 * sum(1 for e in pool if e["win"]) / len(pool), 1)
    v2_top, k = _topdecile_win(pool, lambda e: e["v2"])
    int_top, _ = _topdecile_win(pool, lambda e: e["intensity"])
    return {"oos_events": len(pool), "test_years": folds, "decile_n": k,
            "base_win": base, "v2_top_decile_win": v2_top,
            "intensity_top_decile_win": int_top,
            "v2_edge_vs_base": round(v2_top - base, 1),
            "v2_edge_vs_intensity": round(v2_top - int_top, 1)}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS ignition_rank_v2 (
    symbol      TEXT PRIMARY KEY,
    trade_date  TEXT,
    v2_score    REAL,
    v2_rank     INTEGER,
    intensity   REAL,
    character   TEXT,
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rv2 ON ignition_rank_v2(v2_rank);
"""


def compute_and_store(conn=None) -> dict:
    """Run the walk-forward proof, then score TODAY's ignitions with full-sample
    weights into ignition_rank_v2 (the live v2 ranking, for comparison with ignition.py)."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        wf = walk_forward(conn)

        # full-sample weights → score today's ignition_ranking events
        w = _weights(_load(conn))
        scored = 0
        has_rank = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ignition_ranking'").fetchone()
        latest = conn.execute("SELECT MAX(trade_date) m FROM ignition_ranking").fetchone() if has_rank else None
        if latest and latest["m"] and w:
            d = latest["m"]
            sel = (["r.symbol", "r.intensity", "r.character AS accum_character",
                    "r.rs_rank", "r.is_ath_dvpt"] + [f"s.{c}" for c in NUMERIC_S])
            rows = conn.execute(
                f"SELECT {', '.join(sel)} FROM ignition_ranking r "
                f"JOIN stock_signals s ON s.symbol=r.symbol AND s.trade_date=r.trade_date "
                f"WHERE r.trade_date=?", (d,)).fetchall()
            scoredrows = [(dict(r)["symbol"], _score(_feat(dict(r)), w),
                           dict(r)["intensity"], dict(r)["accum_character"]) for r in rows]
            scoredrows.sort(key=lambda t: t[1], reverse=True)
            conn.execute("DELETE FROM ignition_rank_v2")
            conn.executemany(
                "INSERT OR REPLACE INTO ignition_rank_v2 (symbol, trade_date, v2_score, v2_rank, intensity, character) "
                "VALUES (?,?,?,?,?,?)",
                [(sym, d, sc, i + 1, inten, ch) for i, (sym, sc, inten, ch) in enumerate(scoredrows)])
            scored = len(scoredrows)
        if own:
            conn.commit()
        stats = {"walk_forward": wf, "scored_today": scored,
                 "weights_top": sorted(((round(v[0], 3), f) for f, v in w.items()), reverse=True)[:6]}
        log.info("ignition_rankv2: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


def top(limit: int = 20, conn=None) -> list:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM ignition_rank_v2 ORDER BY v2_rank LIMIT ?", (limit,)).fetchall()]
    finally:
        if own:
            cm.__exit__(None, None, None)


def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    scols = ", ".join(f"{c} REAL" for c in NUMERIC_S)
    conn.executescript(f"""
        CREATE TABLE ignition_outcomes (symbol TEXT, signal_date TEXT, mfe_pct REAL,
            mae_before_peak_pct REAL, intensity REAL, rs_rank INTEGER, break_in_window INTEGER, ret_6m REAL);
        CREATE TABLE stock_signals (symbol TEXT, trade_date TEXT, accum_character TEXT,
            is_ath_dvpt INTEGER, {scols});
    """)
    # gap_to_key_p12m separates winners; intensity is noise. 2 years × 200 events.
    def add(year, i, winner):
        d = f"{year}-03-{(i % 27) + 1:02d}"
        sym = f"S{year}_{i}"
        conn.execute("INSERT INTO ignition_outcomes VALUES (?,?,?,?,?,?,0,5.0)",
                     (sym, d, 50.0 if winner else 10.0, -5.0, float(i % 5), 50))
        gap = (100.0 + i) if winner else (-100.0 + i)     # the real separator
        conn.execute(
            "INSERT INTO stock_signals (symbol, trade_date, accum_character, is_ath_dvpt, gap_to_key_p12m) VALUES (?,?,?,?,?)",
            (sym, d, "ACCUMULATION" if winner else "DISTRIBUTION", 0, gap))
    for yr in ("2019", "2020"):
        for i in range(200):
            add(yr, i, winner=(i % 2 == 0))

    wf = walk_forward(conn, min_train=150, min_test=50)
    assert wf["oos_events"] >= 150, wf
    assert wf["v2_top_decile_win"] > wf["base_win"], wf            # v2 beats base OOS
    assert wf["v2_top_decile_win"] > wf["intensity_top_decile_win"], wf  # and beats intensity
    stats = compute_and_store(conn=conn)
    print(f"ignition_rankv2 selftest: OK  v2_top={wf['v2_top_decile_win']}% "
          f"base={wf['base_win']}% intensity_top={wf['intensity_top_decile_win']}%")


def main() -> None:
    import json
    p = argparse.ArgumentParser(description="Evidence-weighted ignition ranking v2 + walk-forward proof.")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--walkforward", action="store_true", help="just the OOS proof")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    if args.walkforward:
        with get_conn() as conn:
            print(json.dumps(walk_forward(conn), indent=2))
        return
    print(json.dumps(compute_and_store(), indent=2))


if __name__ == "__main__":
    main()
