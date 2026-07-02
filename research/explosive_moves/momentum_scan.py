"""Risk-adjusted momentum SCANNER — an early-generation candidate shortlister.

HONEST FRAME (see docs/predictive-attributes-findings.md + institutional-panel-assessment.md):
RISKADJ = 6-mo return / 3-mo volatility is momentum-BETA, not proprietary alpha, and NOT a
net-of-cost buy-basket. Its legitimate use is exactly this: a **gross cross-sectional selection
lens** that ranks the liquid universe so a human researches the top slice manually — a workload
reducer, not an execution signal. Ratio/return factors are anchor-invariant (anchor_audit.py), so
the split-adjusted-close inputs are clean.

Outputs the current top names by RISKADJ and by the decided equal-weight ensemble
(MOM12 + HI52 + RISKADJ + LOWVOL_MOM, 0.25 each on percentile ranks — see
docs/calculations-and-weights.md §2), with the raw components shown (data-first). Writes a
`momentum_scan` table (hermes.db) so a live surface can read it later; also prints the shortlist.

Run:
  ssh hermes && cd /opt/hermes && PYTHONPATH=/opt/hermes:/opt/hermes/research \
    /opt/hermes/.venv-research/bin/python -m explosive_moves.momentum_scan
"""
from __future__ import annotations
import sqlite3
import numpy as np
from explosive_moves.embase import load_symbol_cache
from explosive_moves.factory import pctrank

HDB = "/opt/hermes/data/hermes.db"
TOPN = 25
LIQ_GATE = 0.60          # relative: keep names with turnover >= 60th pctile of the active set (no rupee floor)


def _rankpct(vals):
    return pctrank(np.array([v if v is not None else np.nan for v in vals], float))


def build():
    cache = load_symbol_cache()
    # EQUITY-ONLY allowlist (D42): excludes ETFs / liquid-cash funds that trivially win a
    # low-vol screen (LIQUIDBEES/CASHIETF etc. have ~0 vol → mom/vol explodes). Mandatory.
    con = sqlite3.connect(HDB)
    eq = set(r[0] for r in con.execute("SELECT symbol FROM nse_equity_list"))
    con.close()
    maxd = max(A["date"][-1] for A in cache.values())
    rows = []
    for s, A in cache.items():
        if eq and s not in eq:         # equity-only
            continue
        d, ac, F, mt = A["date"], A["adj_close"], A["feats"], A["med_turn"]
        if d[-1] != maxd:              # only names trading on the latest session (drops delisted/stale)
            continue
        if len(ac) < 253:
            continue
        mom6 = ac[-1] / ac[-127] - 1.0
        mom12 = ac[-1] / ac[-253] - 1.0
        vol = float(F["vol_66"][-1]); rp = float(F["range_pos_252"][-1]); turn = float(mt[-1])
        if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0 and np.isfinite(turn)):
            continue
        rows.append({"s": s, "mom6": mom6, "mom12": mom12, "vol": vol,
                     "riskadj": mom6 / vol, "hi52": rp if np.isfinite(rp) else np.nan, "turn": turn})
    if not rows:
        print("no rows"); return [], maxd

    # relative liquidity gate
    tp = pctrank(np.array([r["turn"] for r in rows]))
    rows = [r for i, r in enumerate(rows) if tp[i] >= LIQ_GATE]

    # cross-sectional percentile ranks + equal-weight ensemble
    r_mom12 = _rankpct([r["mom12"] for r in rows])
    r_hi52 = _rankpct([r["hi52"] for r in rows])
    r_riskadj = _rankpct([r["riskadj"] for r in rows])
    r_mom6 = _rankpct([r["mom6"] for r in rows])
    r_lowvol = _rankpct([-r["vol"] for r in rows])
    lowvol_mom = 0.5 * r_lowvol + 0.5 * r_mom6
    ensemble = np.nanmean(np.vstack([r_mom12, r_hi52, r_riskadj, lowvol_mom]), axis=0)
    for i, r in enumerate(rows):
        r["riskadj_pct"] = round(float(r_riskadj[i]) * 100, 1)
        r["ens_pct"] = round(float(ensemble[i]) * 100, 1)
    return rows, maxd


def save(rows, as_of):
    con = sqlite3.connect(HDB)
    con.execute("""CREATE TABLE IF NOT EXISTS momentum_scan(
        symbol TEXT, as_of TEXT, mom6 REAL, mom12 REAL, vol_66 REAL, riskadj REAL,
        range_pos_252 REAL, turnover_cr REAL, riskadj_pctile REAL, ensemble_pctile REAL,
        computed_at TEXT DEFAULT (datetime('now')), PRIMARY KEY(symbol, as_of))""")
    con.execute("DELETE FROM momentum_scan WHERE as_of=?", (as_of,))
    con.executemany(
        "INSERT INTO momentum_scan(symbol,as_of,mom6,mom12,vol_66,riskadj,range_pos_252,"
        "turnover_cr,riskadj_pctile,ensemble_pctile) VALUES (?,?,?,?,?,?,?,?,?,?)",
        # cast every numeric to native float — numpy float64 gets stored by sqlite as an 8-byte
        # BLOB and reads back as `bytes`, which 500s any consumer doing arithmetic on it.
        [(r["s"], as_of, float(r["mom6"]), float(r["mom12"]), float(r["vol"]), float(r["riskadj"]),
          float(r["hi52"]) if r["hi52"] == r["hi52"] else None, float(r["turn"]) / 1e7,
          float(r["riskadj_pct"]), float(r["ens_pct"])) for r in rows])
    con.commit(); con.close()


def _table(rows, key, title):
    top = sorted(rows, key=lambda r: -r[key])[:TOPN]
    print("\n=== %s (top %d) ===" % (title, TOPN))
    print("%-12s %7s %7s %6s %8s %6s %8s %6s %6s" %
          ("symbol", "mom6%", "mom12%", "vol%", "RISKADJ", "HI52", "turn₹cr", "RApct", "ENSpct"))
    for r in top:
        print("%-12s %7.1f %7.1f %6.1f %8.2f %6.2f %8.1f %6.1f %6.1f" % (
            r["s"], r["mom6"] * 100, r["mom12"] * 100, r["vol"] * 100, r["riskadj"],
            r["hi52"], r["turn"] / 1e7, r["riskadj_pct"], r["ens_pct"]))


def main():
    rows, as_of = build()
    if not rows:
        return
    save(rows, as_of)
    print("as_of %s — %d liquid names scanned (RISKADJ = 6mo-return / 3mo-vol; SELECTION lens, not alpha)" %
          (as_of, len(rows)))
    _table(rows, "riskadj", "RISK-ADJUSTED MOMENTUM")
    _table(rows, "ens_pct", "EQUAL-WEIGHT ENSEMBLE (MOM12+HI52+RISKADJ+LOWVOL_MOM)")


if __name__ == "__main__":
    main()
