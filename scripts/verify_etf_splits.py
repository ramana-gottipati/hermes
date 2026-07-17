"""Verify the back-filled gold-ETF subdivisions adjust correctly (read-only).

Companion to `scripts/backfill_etf_splits.py` — it shares that module's
`GOLD_ETF_SPLITS` source-of-truth and proves, on the LIVE DB, that every event
the seed inserted now flows through the research adjust path
(`research/explosive_moves/adjust.py` `load_factors` + `adjust_closes`) and
leaves the series continuous.

Per event it reports: the loaded factor · the raw ex-day step (the fake
−90%/−99% cliff) · the ADJUSTED ex-day step (must be ~1.0) · the full-window
adjusted CAGR/vol (must be a sane gold-like positive, not the pre-fix artifact) ·
and a scan of the WHOLE adjusted series for any REMAINING cliff — which must be 0
and would also surface any *second* split not in the seed list (KOTAKGOLD has two).

Exit code: 0 if every adjusted series is continuous, 1 if any cliff remains.

Usage (box, app venv, from repo root):
    python scripts/verify_etf_splits.py --selftest   # offline synthetic proof
    python scripts/verify_etf_splits.py              # live-DB verification table
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sqlite3
import sys
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling import
from backfill_etf_splits import GOLD_ETF_SPLITS

CLIFF_LO, CLIFF_HI = 0.5, 2.0   # same detector band the audit used


def _load_research_adjust():
    """Import research/explosive_moves/adjust.py (the load_factors path) by path."""
    path = os.path.join(REPO_ROOT, "research", "explosive_moves", "adjust.py")
    spec = importlib.util.spec_from_file_location("research_adjust", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan(adj: dict) -> tuple:
    """Worst consecutive-day ratio + count of ratios outside the cliff band, on
    an already-adjusted {date: close} series. (0, None) means fully continuous."""
    dates = sorted(adj)
    worst = None
    n = 0
    for i in range(1, len(dates)):
        r = adj[dates[i]] / adj[dates[i - 1]]
        if r < CLIFF_LO or r > CLIFF_HI:
            n += 1
            if worst is None or abs(r - 1) > abs(worst[1] - 1):
                worst = (dates[i], r)
    return n, worst


def stats(adj: dict) -> tuple:
    """(CAGR, annualised vol) over the full adjusted series."""
    dates = sorted(adj)
    p = [adj[d] for d in dates]
    y0 = list(map(int, dates[0].split("-")))
    y1 = list(map(int, dates[-1].split("-")))
    yrs = (date(*y1) - date(*y0)).days / 365.25
    cagr = (p[-1] / p[0]) ** (1 / yrs) - 1
    rets = [p[i] / p[i - 1] - 1 for i in range(1, len(p))]
    m = sum(rets) / len(rets)
    vol = (sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5 * (252 ** 0.5)
    return cagr, vol


def verify_live() -> int:
    from src.core.db import get_conn

    radj = _load_research_adjust()
    ev: dict = {}
    for sym, ex, rf, rt in GOLD_ETF_SPLITS:
        ev.setdefault(sym, []).append((ex, rf, rt))

    hdr = ("%-11s %-11s %-9s %9s %9s   %-23s %7s %6s  %s"
           % ("SYMBOL", "ex_date", "factor", "raw_step", "adj_step", "window", "CAGR", "vol", "cliffs"))
    print(hdr)
    print("-" * len(hdr))

    all_clean = True
    with get_conn() as conn:
        fac_all = radj.load_factors(conn)
        for sym in sorted(ev):
            rows = conn.execute(
                "SELECT trade_date, close FROM bhavcopy_rows WHERE symbol=? "
                "AND series IN ('EQ','BE','BZ') AND close>0 ORDER BY trade_date", (sym,)).fetchall()
            closes = {d: c for d, c in rows}
            dates = sorted(closes)
            idx = {d: i for i, d in enumerate(dates)}
            adj = radj.adjust_closes(closes, fac_all.get(sym))
            cagr, vol = stats(adj)
            ncliff, worst = scan(adj)
            if ncliff:
                all_clean = False
            factxt = "+".join("%g:%g" % (rf, rt) for _, rf, rt in ev[sym])
            cliff_txt = "0" if ncliff == 0 else "%d worst %s r=%.4f" % (ncliff, worst[0], worst[1])
            for j, (ex, rf, rt) in enumerate(ev[sym]):
                i = idx.get(ex)
                raw_step = (closes[ex] / closes[dates[i - 1]]) if i else float("nan")
                adj_step = (adj[ex] / adj[dates[i - 1]]) if i else float("nan")
                if j == 0:
                    print("%-11s %-11s %-9s %9.4f %9.4f   %-23s %+6.1f%% %5.1f%%  %s"
                          % (sym, ex, factxt, raw_step, adj_step,
                             "%s..%s" % (dates[0], dates[-1]), cagr * 100, vol * 100, cliff_txt))
                else:
                    print("%-11s %-11s %-9s %9.4f %9.4f" % ("", ex, "  \"", raw_step, adj_step))

    print("\nALL ADJUSTED SERIES CONTINUOUS (0 remaining cliffs):", all_clean)
    return 0 if all_clean else 1


def _selftest() -> int:
    """Offline proof of the adjust + scan logic on a synthetic 100:1 split."""
    ok = True

    def check(name, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", name))
        ok = ok and bool(cond)

    radj = _load_research_adjust()
    con = sqlite3.connect(":memory:")
    con.executescript(
        "CREATE TABLE corporate_actions (symbol TEXT, action_type TEXT, ex_date TEXT, "
        "record_date TEXT, ratio_from REAL, ratio_to REAL, details TEXT, source TEXT);")
    con.execute("INSERT INTO corporate_actions VALUES ('SYN','SPLIT','2020-01-03',NULL,100,1,'x','x')")

    # raw series with a fake -99% cliff at the split, ~flat gold either side
    raw = {"2020-01-01": 3300.0, "2020-01-02": 3320.0,
           "2020-01-03": 33.1, "2020-01-06": 33.3, "2020-01-07": 33.0}
    fac = radj.load_factors(con)
    check("load_factors picks up the synthetic split (f=100)",
          abs(fac["SYN"][0][1] - 100.0) < 1e-9)

    raw_cliffs, _ = scan(raw)
    check("RAW series has the fake cliff (scan flags it)", raw_cliffs == 1)

    adj = radj.adjust_closes(raw, fac["SYN"])
    adj_cliffs, _ = scan(adj)
    check("ADJUSTED series is continuous (0 cliffs)", adj_cliffs == 0)
    step = adj["2020-01-03"] / adj["2020-01-02"]
    check("adjusted ex-day step ~1.0", abs(step - 1) < 0.03)
    cagr, vol = stats(adj)
    check("adjusted CAGR is finite/sane (not the raw artifact)", -0.5 < cagr < 5.0)
    con.close()

    print("verify_etf_splits selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Verify back-filled gold-ETF subdivisions adjust continuously")
    p.add_argument("--selftest", action="store_true", help="offline synthetic proof (no DB)")
    args = p.parse_args()
    raise SystemExit(_selftest() if args.selftest else verify_live())


if __name__ == "__main__":
    main()
