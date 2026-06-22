"""Averaging-zone derivation — do ignitions that dip recover? (design §5, component C)

The honest version. An earlier cut bucketed by `mae_before_peak` and found
"deeper dips recover MORE" — a confound: that dip is measured relative to the
FUTURE peak, so a deep pre-peak dip can only exist when there was a big eventual
run. Useless (worse: misleading) as averaging guidance.

This reads the PATH-CONDITIONAL flags `rec_after_X` (computed in ignition_backtest
during the price walk): after price first FALLS −X% from entry in REAL time, did a
later high still reach +25%? recover_rate(−X%) is a "thesis still intact" gauge.

AVERAGING DOCTRINE (Ramana, 2026-06-23): recover-rate is NOT an averaging trigger.
**Never average small dips; reserve capital for DEEP falls (~30%).** A 5% fall
self-corrects (one up-day erases it); after an equal-share average at −5% you need
just +2.6% to break even, so averaging there buys nothing while burning capital you'd
want at a real dislocation. Averaging's leverage scales with depth — an equal-share
add HALVES the breakeven move: trivial at −5% (5.3%→2.6%), large at −30% (42.9%→21.4%).
So the table shows recover-rate AND the breakeven cut; the case for averaging is the
combination, and it only stacks up deep.

Self-contained (capture.py pattern): OWNS `averaging_zones`, never edits db.py.
Reads `ignition_outcomes` (the rec_after_* columns). Pure arithmetic.

Run:        python -m src.automation.ignition_zones
Self-check: python -m src.automation.ignition_zones --selftest
"""

from __future__ import annotations

import argparse
import logging

from src.core.db import get_conn
from src.automation.ignition_backtest import AVG_THRESH

log = logging.getLogger("hermes.ignition_zones")

WIN_TARGET = 25.0   # MFE % that counts as reaching target (matches the backtest)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS averaging_zones (
    x            INTEGER PRIMARY KEY,   -- drawdown level (5 = "-5% from entry")
    label        TEXT,
    n_touched    INTEGER,               -- events that actually fell this far
    recover_rate REAL,                  -- % of those that still reached +25%
    base_rate    REAL,                  -- overall reach-+25% rate, for reference
    computed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_COLS = ["x", "label", "n_touched", "recover_rate", "base_rate"]


def compute_and_store(conn=None) -> dict:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.execute("DROP TABLE IF EXISTS averaging_zones")  # schema changed from the earlier confounded cut; safe — our own recomputed derived table
        conn.executescript(_SCHEMA)
        cols = ", ".join(f"rec_after_{x}" for x in AVG_THRESH)
        rows = [dict(r) for r in conn.execute(
            f"SELECT {cols}, mfe_pct FROM ignition_outcomes "
            f"WHERE break_in_window=0 AND ret_6m IS NOT NULL").fetchall()]
        n_all = len(rows)
        base = (100.0 * sum(1 for r in rows if (r["mfe_pct"] or -1e9) >= WIN_TARGET) / n_all) if n_all else 0.0

        out = []
        for x in AVG_THRESH:
            touched = [r[f"rec_after_{x}"] for r in rows if r[f"rec_after_{x}"] is not None]
            n = len(touched)
            rec = round(100.0 * sum(touched) / n, 1) if n else None
            out.append((x, f"-{x}%", n, rec, round(base, 1)))

        conn.execute("DELETE FROM averaging_zones")
        conn.executemany(
            f"INSERT OR REPLACE INTO averaging_zones ({','.join(_COLS)}) "
            f"VALUES ({','.join('?'*len(_COLS))})", out)
        if own:
            conn.commit()

        stats = {"events": n_all, "base_rate": round(base, 1),
                 "zones": [(o[1], o[2], o[3]) for o in out]}
        log.info("ignition_zones: %s", stats)
        return stats
    finally:
        if own:
            cm.__exit__(None, None, None)


def zones(conn=None) -> list:
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM averaging_zones ORDER BY x").fetchall()]
    finally:
        if own:
            cm.__exit__(None, None, None)


def _selftest() -> None:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    rcols = ", ".join(f"rec_after_{x} INTEGER" for x in AVG_THRESH)
    conn.execute(f"CREATE TABLE ignition_outcomes (mfe_pct REAL, break_in_window INTEGER, ret_6m REAL, {rcols})")
    # -10%: 100 touched, 70 recovered.  -20%: 80 touched (20 never fell that far), 40 recovered.
    for i in range(100):
        r10 = 1 if i < 70 else 0
        if i < 80:
            r20 = 1 if i < 40 else 0
        else:
            r20 = None
        conn.execute(
            "INSERT INTO ignition_outcomes (mfe_pct, break_in_window, ret_6m, rec_after_5, rec_after_10, rec_after_15, rec_after_20, rec_after_30) "
            "VALUES (?,0,5.0,?,?,?,?,?)",
            (60.0 if i < 60 else 5.0, None, r10, None, r20, None))

    stats = compute_and_store(conn=conn)
    z = {r["x"]: r for r in zones(conn=conn)}
    assert z[10]["n_touched"] == 100 and abs(z[10]["recover_rate"] - 70.0) < 0.1, z[10]
    assert z[20]["n_touched"] == 80 and abs(z[20]["recover_rate"] - 50.0) < 0.1, z[20]
    assert abs(stats["base_rate"] - 60.0) < 0.1, stats
    print(f"ignition_zones selftest: OK  -10%={z[10]['recover_rate']}% (n{z[10]['n_touched']})  "
          f"-20%={z[20]['recover_rate']}% (n{z[20]['n_touched']})  base={stats['base_rate']}%")


def main() -> None:
    p = argparse.ArgumentParser(description="Averaging zones: real-time recovery-rate by dip depth.")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    stats = compute_and_store()
    print(f"\naveraging zones — after price falls −X% from entry (events {stats['events']}, base reach-+25% {stats['base_rate']}%)")
    print("DOCTRINE: never average small dips (they self-correct); reserve capital for DEEP falls (~30%).")
    print("  recover% = thesis-intact gauge (NOT a buy trigger).  BE = up-move to break even; avg halves it.\n")
    print(f"{'fell to':<9}{'n':>8}{'recover%':>10}{'BE no-avg':>12}{'BE w/ avg':>11}{'pt saved':>10}")
    print("-" * 60)
    for r in zones():
        x = r["x"]
        be_no = x / (100.0 - x) * 100.0          # equal-share averaging halves this
        rr = str(r["recover_rate"]) if r["recover_rate"] is not None else "—"
        print(f"{r['label']:<9}{r['n_touched']:>8}{rr:>10}{be_no:>11.1f}%{be_no/2:>10.1f}%{be_no/2:>10.1f}")


if __name__ == "__main__":
    main()
