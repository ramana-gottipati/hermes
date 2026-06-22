"""Track A — build a clean cross-sectional ML panel from our FULL existing feature library.

For each monthly rebalance date, snapshot every liquid stock's stock_signals features
(relative-strength vs market & sector, accumulation, delivery battery, RS-rank, turnover
surges) + price momentum/vol from the cache, plus forward 1m/3m returns as targets.
Point-in-time, no look-ahead. Writes research.db table `ml_panel` for the rigorous model.
"""
import sqlite3
import numpy as np
from explosive_moves.embase import load_symbol_cache
from explosive_moves.common import main_conn, research_conn
from explosive_moves.metrics import index_series

# meaningful predictive features from stock_signals (skip raw intermediates)
SS_FEATS = ["p_score", "r_score", "rs_rank", "rs_vs_broad_slope_1m", "rs_vs_broad_slope_3m",
            "rs_vs_broad_slope_6m", "rs_vs_broad_slope_12m", "rs_vs_broad_above_50ma",
            "rs_vs_broad_above_200ma", "rs_vs_sector_slope_3m", "rs_vs_sector_slope_6m",
            "accum_price_drift_3m", "deliv_value_ratio_1m_6m", "trade_count_ratio_1m_6m",
            "avg_deliv_pct_1m", "avg_deliv_pct_6m", "deliv_updown_ratio_3m", "pct_from_52w_high",
            "turnover_surge_1m", "turnover_surge_3m", "turnover_surge_1y", "is_ath_dvpt"]
CACHE_FEATS = ["mom6", "mom12", "vol_66", "ret_22d"]

cache = load_symbol_cache()
D2I = {s: {d: i for i, d in enumerate(A["date"])} for s, A in cache.items()}
dts, _ = index_series("Nifty 50")
cal = [d for d in dts if d >= "2012-06-01"]
rebal = [cal[i] for i in range(0, len(cal), 22)]
CR = 1e7

mc = main_conn()
rc = research_conn()
allcols = ["symbol", "date"] + SS_FEATS + CACHE_FEATS + ["fwd_22", "fwd_66"]
rc.execute("DROP TABLE IF EXISTS ml_panel")
rc.execute(f"CREATE TABLE ml_panel ({','.join(c+(' TEXT' if c in ('symbol','date') else ' REAL') for c in allcols)})")

n = 0
for d0 in rebal:
    rows = mc.execute(f"SELECT symbol,{','.join(SS_FEATS)} FROM stock_signals WHERE trade_date=?", (d0,)).fetchall()
    if not rows:
        continue
    buf = []
    for r in rows:
        sym = r[0]
        A = cache.get(sym)
        if A is None:
            continue
        i0 = D2I[sym].get(d0)
        if i0 is None or i0 < 260 or not (A["med_turn"][i0] >= 1 * CR):
            continue
        ac = A["adj_close"]
        f22 = float(ac[i0 + 22] / ac[i0] - 1) if i0 + 22 < len(ac) and ac[i0] > 0 else None
        f66 = float(ac[i0 + 66] / ac[i0] - 1) if i0 + 66 < len(ac) and ac[i0] > 0 else None
        if f22 is None:
            continue
        F = A["feats"]
        cf = [float(ac[i0] / ac[i0 - 126] - 1) if i0 >= 126 else None,
              float(ac[i0] / ac[i0 - 252] - 1) if i0 >= 252 else None,
              float(F["vol_66"][i0]) if F["vol_66"][i0] == F["vol_66"][i0] else None,
              float(F["ret_22d"][i0]) if F["ret_22d"][i0] == F["ret_22d"][i0] else None]
        ssv = [float(r[k + 1]) if isinstance(r[k + 1], (int, float)) else None for k in range(len(SS_FEATS))]
        buf.append([sym, d0] + ssv + cf + [f22, f66])
    if buf:
        rc.executemany(f"INSERT INTO ml_panel VALUES ({','.join('?' for _ in allcols)})", buf)
        rc.commit(); n += len(buf)
    print(f"  {d0}: panel rows so far {n}", flush=True)

print(f"DONE. ml_panel rows={n}, features={len(SS_FEATS)+len(CACHE_FEATS)}")
mc.close(); rc.close()
