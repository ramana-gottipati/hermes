"""FALSIFICATION GATE (proof-of-mechanism) — does management CREDIBILITY predict returns?

Reads the production credibility scores (`concall_scores.credibility_score` = guidance-accuracy,
computed PRICE-FREE by concall_scores.py) and tests, with NO look-ahead, whether high-credibility
names outperform afterwards. Forward return is measured as EXCESS vs Nifty 500 over the same window
to strip the regime (the sample clusters in 2021-22).

⚠️ DELIBERATELY UNDERPOWERED — ~27 symbols, one narrow window. This is a directional SNIFF TEST to
decide whether widening transcript breadth is worth it, NOT a validated factor. Read-only (no writes
to production tables). Run on VPS (.venv-research).
"""
from __future__ import annotations
import csv
import os
import sqlite3
import statistics as st
import numpy as np
import sys
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series

HDB = "/opt/hermes/data/hermes.db"
MIN_RESOLVED = 5          # need a real track record, not 1 promise
HI, LO = 70.0, 55.0       # credibility bands (GA): "kept promises" vs "broke them"


def concall_anchor(year, month):
    """First calendar date in the month AFTER the concall month (~PIT-safe forward start)."""
    y, m = (year, month + 1) if month < 12 else (year + 1, 1)
    return f"{y:04d}-{m:02d}-01"


def main():
    c = sqlite3.connect(HDB)
    rows = c.execute("""
        SELECT s.symbol, s.as_of_period, s.credibility_score, s.n_promises_resolved,
               cc.concall_year, cc.concall_month
        FROM concall_scores s
        JOIN concalls cc ON cc.symbol=s.symbol AND cc.period_label=s.as_of_period
        WHERE s.credibility_score IS NOT NULL AND s.n_promises_resolved >= ?
        GROUP BY s.symbol, s.as_of_period
    """, (MIN_RESOLVED,)).fetchall()
    c.close()

    cache = load_symbol_cache()
    bdts, bcl = index_series("Nifty 500")
    bclose = {d: bcl[i] for i, d in enumerate(bdts)}
    bdates = sorted(bclose)

    def bench_on(date):
        # nearest Nifty500 close on/before date
        import bisect
        i = bisect.bisect_right(bdates, date) - 1
        return bclose[bdates[i]] if i >= 0 else None

    obs = []
    for sym, period, ga, nres, yr, mo in rows:
        if sym not in cache or yr is None or mo is None:
            continue
        A = cache[sym]; dates = list(A["date"]); ac = A["adj_close"]
        anchor = concall_anchor(yr, mo)
        i0 = next((i for i, d in enumerate(dates) if d >= anchor), None)
        if i0 is None:
            continue
        rec = {"symbol": sym, "period": period, "ga": ga, "nres": nres, "d0": dates[i0]}
        for tag, n in (("6m", 126), ("12m", 252)):
            if i0 + n < len(ac) and ac[i0] > 0:
                fwd = ac[i0 + n] / ac[i0] - 1.0
                b0, b1 = bench_on(dates[i0]), bench_on(dates[i0 + n])
                bench = (b1 / b0 - 1.0) if (b0 and b1) else None
                rec[f"fwd_{tag}"] = fwd
                rec[f"exc_{tag}"] = (fwd - bench) if bench is not None else None
            else:
                rec[f"fwd_{tag}"] = rec[f"exc_{tag}"] = None
        obs.append(rec)

    def summarise(tag):
        ex = [(o["ga"], o[f"exc_{tag}"]) for o in obs if o.get(f"exc_{tag}") is not None]
        if len(ex) < 4:
            print(f"  {tag}: too few ({len(ex)})"); return None
        gas = [g for g, _ in ex]; excs = [e for _, e in ex]
        hi = [e for g, e in ex if g >= HI]; lo = [e for g, e in ex if g < LO]
        # Spearman rank corr (no scipy): corr of ranks
        gr = _rank(gas); er = _rank(excs)
        spear = np.corrcoef(gr, er)[0, 1] if len(gr) > 2 else float("nan")
        print(f"  {tag}: n={len(ex)} | Spearman(GA, excess)={spear:+.2f} | "
              f"HI(GA>={HI:.0f}) n={len(hi)} median excess={st.median(hi)*100:+.1f}% | "
              f"LO(GA<{LO:.0f}) n={len(lo)} median excess={st.median(lo)*100:+.1f}%")
        return {"tag": tag, "n": len(ex), "spearman": round(float(spear), 2),
                "hi_n": len(hi), "hi_med_excess_pct": round(st.median(hi) * 100, 1) if hi else None,
                "lo_n": len(lo), "lo_med_excess_pct": round(st.median(lo) * 100, 1) if lo else None}

    print(f"FALSIFICATION GATE — credibility vs forward EXCESS return (vs Nifty 500). "
          f"obs={len(obs)} symbols (resolved>={MIN_RESOLVED}). UNDERPOWERED — sniff test only.\n")
    res = [r for r in (summarise("6m"), summarise("12m")) if r]

    out = os.path.join(os.path.dirname(__file__), "out", "credibility_falsify.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "period", "credibility_ga", "n_resolved", "anchor_date",
                    "fwd_6m_pct", "excess_6m_pct", "fwd_12m_pct", "excess_12m_pct"])
        for o in sorted(obs, key=lambda z: -z["ga"]):
            w.writerow([o["symbol"], o["period"], o["ga"], o["nres"], o["d0"],
                        _pc(o.get("fwd_6m")), _pc(o.get("exc_6m")), _pc(o.get("fwd_12m")), _pc(o.get("exc_12m"))])
    print(f"\nsaved -> out/credibility_falsify.csv ({len(obs)} obs)")


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0] * len(xs)
    for rank, i in enumerate(order):
        r[i] = rank
    return r


def _pc(v):
    return round(v * 100, 1) if v is not None else None


if __name__ == "__main__":
    main()
