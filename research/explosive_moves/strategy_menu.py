"""Best-available strategies — the decision menu, CLEAN universe.

Universe = current Nifty 500 constituents (real, listed equities — no delisted ghosts,
no liquid/ETF funds) that are still trading as of the cache's latest date. For each
surviving candidate, print its current top-25 holdings so a human can choose from real
portfolios. Honest metrics live in docs/strategy-ledger.md. Read-only.
"""
import sqlite3
import sys
import numpy as np
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.factory import pctrank

HDB = "/opt/hermes/data/hermes.db"
TOPN = 25


def nifty500_set():
    c = sqlite3.connect(HDB)
    try:
        snap = c.execute("SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name='Nifty 500'").fetchone()[0]
        rows = c.execute("SELECT DISTINCT symbol FROM stock_index_membership WHERE index_name='Nifty 500' AND snapshot_date=?", (snap,)).fetchall()
        return {r[0] for r in rows}, snap
    finally:
        c.close()


def main():
    cache = load_symbol_cache()
    universe, snap = nifty500_set()
    # global latest trading date across the cache
    maxd = max(A["date"][-1] for A in cache.values())
    rec = []
    for s, A in cache.items():
        if s not in universe:
            continue
        ac, mt, F, dates = A["adj_close"], A["med_turn"], A["feats"], A["date"]
        if dates[-1] < maxd[:8] + "01":          # last bar must be in the latest month -> still trading
            continue
        i0 = len(ac) - 1
        if i0 < 260 or not (ac[i0] > 0):
            continue
        mom6 = ac[i0] / ac[i0 - 126] - 1.0
        vol = float(F["vol_66"][i0])
        if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
            continue
        rec.append({"s": s, "date": dates[i0], "mom6": mom6, "vol": vol,
                    "riskadj": mom6 / (vol + 1e-6), "lowvol": -vol})
    g = rec
    m6 = pctrank(np.array([x["mom6"] for x in g])); lv = pctrank(np.array([x["lowvol"] for x in g]))
    for k, x in enumerate(g):
        x["lowvolmom"] = 0.5 * lv[k] + 0.5 * m6[k]
        x["lowvol_sc"] = lv[k]; x["riskadj_sc"] = x["riskadj"]

    def top(score):
        return [x["s"] for x in sorted(g, key=lambda z: -z[score])[:TOPN]]

    print(f"Universe = Nifty 500 (snapshot {snap}), still-trading: {len(g)} names | as of {max(x['date'] for x in g)}\n")
    menu = [
        ("A. DEFENSIVE — Low-Vol + Momentum (best cost survivor)", "lowvolmom",
         "Sharpe 0.79 / CAGR 13.3% / MaxDD -25% / cost 8.3% / cap Rs190cr"),
        ("B. SMOOTHEST — pure Low-Vol", "lowvol_sc",
         "Sharpe 0.78 / CAGR 9.6% / MaxDD -23% / cost 5.4% / cap Rs168cr"),
        ("C. HIGHEST-MOMENTUM — Risk-Adjusted (aggressive, higher cost)", "riskadj_sc",
         "Sharpe 0.51 / CAGR 10.2% / MaxDD -43% / cost 15.1% / cap Rs97cr"),
    ]
    for name, key, metrics in menu:
        print("=" * 92)
        print(name + "\n  " + metrics)
        names = top(key)
        for i in range(0, TOPN, 5):
            print("   " + "  ".join(f"{n:<13}" for n in names[i:i + 5]))
        print()
    print("=" * 92)
    print("BASELINE the above must beat: Nifty 500 buy & hold = Sharpe 0.89 / CAGR 15.3% / MaxDD -29%")


if __name__ == "__main__":
    main()
