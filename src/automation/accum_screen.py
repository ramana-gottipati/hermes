"""Live ACCUMULATION × FUNDAMENTAL-QUALITY screen (D66 follow-up — operationalizes the finding).

The D66 backtest showed: RETURNS come from accumulation/RS, the patearn fundamental score is a
RISK FILTER, and the sweet spot is accumulation-strong AND fundamentally-good. This turns that into
a live screen: for the LATEST trading date it ranks the liquid universe by 3-month accumulation
drift (the validated return driver), overlays relative strength + the SHAREHOLDING-ENRICHED
point-in-time patearn tier (via `fundamentals_asof.score_asof`), and flags the sweet spot
(top-tercile accumulation AND non-disqualified AND above-median NS).

LANE-SAFE: reads production `hermes.db` READ-ONLY + `research.db`, writes ONLY
`research.db.accum_screen` (a precomputed table a `/dash` or Telegram surface can read later).
Does NOT touch the live web tree. Pure stdlib (+ fundamentals_asof, which is stdlib-chain) → runs
under the production venv; wire as a nightly job after the bhav/signals chain when ready.

Run: cd /opt/hermes && .venv/bin/python -m src.automation.accum_screen [top_n]
"""
from __future__ import annotations

import csv
import os
import sqlite3
import statistics
import sys

from src.automation.fundamentals_asof import score_asof, RESEARCH_DB

MAIN_DB = os.environ.get("HERMES_MAIN_DB", "/opt/hermes/data/hermes.db")
CSV_PATH = os.environ.get("HERMES_SCREEN_CSV", "/opt/hermes/data/accum_screen.csv")

# Mirrors stock_rs._LIQUID_FILTER (D42/D33) — real EQ, traded value > Rs1cr, price > Rs20,
# in the NSE equity allowlist. INLINED (not imported) so this module stays numpy-free
# (stock_rs pulls in rrg/rs_phase → numpy) and runs under the production venv.
_LIQUID_FILTER = """
      b.series = 'EQ' AND (b.segment = 'CM' OR b.segment IS NULL)
      AND b.value > 10000000 AND b.close > 20
      AND s.symbol IN (SELECT symbol FROM nse_equity_list)
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS accum_screen(
    trade_date TEXT, symbol TEXT, close REAL,
    accum_drift_3m REAL, accum_character TEXT, rs_rank REAL,
    deliv_value_ratio_1m_6m REAL, p_score REAL, pct_from_52w_high REAL,
    tier TEXT, ns_base REAL, qg_pass INTEGER, hard_disq INTEGER,
    accum_strong INTEGER, fund_good INTEGER, sweet_spot INTEGER,
    PRIMARY KEY(trade_date, symbol));
CREATE INDEX IF NOT EXISTS idx_accum_screen ON accum_screen(trade_date, sweet_spot, accum_drift_3m DESC);
"""


def _main_conn():
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def build(top_n: int = 300) -> None:
    mc = _main_conn()
    trade_date = mc.execute("SELECT MAX(trade_date) FROM stock_signals").fetchone()[0]
    rows = mc.execute(f"""
        SELECT s.symbol, b.close,
               s.accum_price_drift_3m AS drift, s.accum_character AS character,
               s.rs_rank, s.deliv_value_ratio_1m_6m AS deliv, s.p_score,
               s.pct_from_52w_high AS pfh
        FROM stock_signals s
        JOIN bhavcopy_rows b ON b.symbol = s.symbol AND b.trade_date = s.trade_date
        WHERE s.trade_date = ? AND {_LIQUID_FILTER}
          AND s.accum_price_drift_3m IS NOT NULL
        ORDER BY s.accum_price_drift_3m DESC
    """, (trade_date,)).fetchall()
    mc.close()
    if len(rows) < 10:
        print(f"only {len(rows)} liquid rows on {trade_date} — aborting"); return

    drifts = [r["drift"] for r in rows]
    cutoff = statistics.quantiles(drifts, n=3)[1]          # top-tercile accumulation cutoff
    print(f"date={trade_date}  liquid={len(rows)}  accum top-tercile cutoff(drift)={cutoff:.4f}", flush=True)

    strong = [r for r in rows if r["drift"] >= cutoff]     # accumulation-strong cohort
    to_score = strong[:top_n]                              # bound the per-symbol PIT scoring
    print(f"accum-strong={len(strong)}; scoring top {len(to_score)} via score_asof ...", flush=True)

    scored = {}
    for r in to_score:
        s = score_asof(r["symbol"], trade_date, price=r["close"], db_path=RESEARCH_DB)
        if s and "tier" in s:
            scored[r["symbol"]] = s

    ns_vals = [s["ns_base"] for s in scored.values() if not s["hard_disqualified"]]
    ns_med = statistics.median(ns_vals) if ns_vals else 0.0
    print(f"scored={len(scored)}  cohort median NS={ns_med:.1f}", flush=True)

    out = []
    for r in rows:
        s = scored.get(r["symbol"])
        accum_strong = 1 if r["drift"] >= cutoff else 0
        if s:
            disq = 1 if s["hard_disqualified"] else 0
            fund_good = 1 if (not s["hard_disqualified"] and s["ns_base"] >= ns_med) else 0
            tier, ns, qg = s["tier"], s["ns_base"], (1 if s["qg_pass"] else 0)
        else:
            disq = fund_good = qg = None
            tier = ns = None
        sweet = 1 if (accum_strong and fund_good == 1) else 0
        out.append((trade_date, r["symbol"], r["close"], r["drift"], r["character"],
                    r["rs_rank"], r["deliv"], r["p_score"], r["pfh"],
                    tier, ns, qg, disq, accum_strong, fund_good, sweet))

    rc = sqlite3.connect(RESEARCH_DB, timeout=60)
    rc.execute("PRAGMA busy_timeout=30000")
    rc.executescript(SCHEMA)
    rc.execute("DELETE FROM accum_screen WHERE trade_date=?", (trade_date,))
    rc.executemany("INSERT OR REPLACE INTO accum_screen VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    rc.commit()
    rc.close()

    # CSV for Excel / download-from-vps (data-first): full screen, sweet-spot first.
    cols = ["trade_date", "symbol", "close", "accum_drift_3m", "accum_character", "rs_rank",
            "deliv_value_ratio_1m_6m", "p_score", "pct_from_52w_high", "tier", "ns_base",
            "qg_pass", "hard_disq", "accum_strong", "fund_good", "sweet_spot"]
    csv_rows = sorted(out, key=lambda o: (-(o[15] or 0), -(o[13] or 0), -(o[3] or 0)))
    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(csv_rows)
    print(f"CSV -> {CSV_PATH} ({len(csv_rows)} rows)")

    sweet = sorted((o for o in out if o[15] == 1), key=lambda o: -(o[3] or 0))
    print(f"\nDONE accum_screen: {len(out)} rows written, {len(sweet)} sweet-spot (accum-strong + fund-good)")
    print(f"\n=== TOP SWEET-SPOT (accumulation-strong + fundamentally-good) @ {trade_date} ===")
    print(f"{'symbol':14}{'close':>9}{'drift3m':>9}{'rs':>5}{'tier':>6}{'NS':>6}  character")
    for o in sweet[:25]:
        print(f"{o[1]:14}{o[2]:>9.1f}{o[3]:>9.3f}{(o[5] or 0):>5.0f}{(o[9] or '-'):>6}{(o[10] or 0):>6.1f}  {o[4] or ''}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    build(top_n=n)
