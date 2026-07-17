"""B — cost-honest momentum engine. What return/vol survives REAL frictions, and at what AUM?

Replaces the flat COST_PS=0.3%/turnover with a per-NAME realistic cost:
  side_cost(name) = half catalog spread by liquidity tier  (COST_TIERS, strategies.py)
                  + per-side fees                          (fees_ps)
                  + slippage = 0.5 x ATR%(entry)           (calibrate.py basis)
charged on each name actually bought/sold. Plus a CAPACITY read (position <= 10% of the
name's median daily turnover -> max deployable AUM) and a turnover-reduction lever
(hold-band: keep a name until it falls out of the top-35, not the top-25).

Pure price cache (no fundamentals / no raw-close) so it runs fast. Walk-forward, no look-ahead.

Every ratio here is mean/sd annualised with NO risk-free rate subtracted — a return/vol ratio,
not a Sharpe, so it reads high against a textbook Sharpe; the Nifty500 B&H row it is judged
against is computed on the SAME basis, so the comparisons and verdicts hold (D142).

Writes out/cost_realism.csv. Read-only. Run on VPS (.venv-research).
"""
from __future__ import annotations
import csv
import os
import numpy as np
import sys
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series
from explosive_moves.factory import eqstats, pctrank, COST_PS, CR
from explosive_moves.strategies import COST_TIERS, tier_for_turnover

REBAL, TOPN, GATE_PCTL, BAND = 22, 25, 0.60, 35
SQ = np.sqrt(12.0)


def side_cost(med_turn, atr_pct):
    """Realistic one-side cost fraction for trading this name."""
    t = tier_for_turnover(med_turn) or "T1"        # below floor -> treat as most expensive
    c = COST_TIERS[t]
    half_spread = c["spread_rt"] / 2.0
    slip = 0.5 * (atr_pct if np.isfinite(atr_pct) else 0.03)
    return half_spread + c["fees_ps"] + slip


_CACHE = None
_CAL = None


def _load():
    global _CACHE, _CAL
    if _CACHE is None:
        _CACHE = load_symbol_cache()
        dts, _ = index_series("Nifty 50")
        _CAL = [d for d in dts if d >= "2012-06-01"]
    return _CACHE, _CAL


def build(rebal=REBAL, gate_pctl=GATE_PCTL):
    cache, cal = _load()
    ridx = list(range(0, len(cal), rebal))
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}
    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rec = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + rebal, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            mom6 = ac[i0] / ac[i0 - 126] - 1.0
            vol = float(F["vol_66"][i0])
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            rec.append({"s": s, "mt": float(mt[i0]) if np.isfinite(mt[i0]) else 0.0,
                        "atr": float(F["atr14_pct"][i0]), "riskadj": mom6 / (vol + 1e-6),
                        "lowvol": -vol, "mom6": mom6, "fwd": ac[i1] / ac[i0] - 1.0})
        if len(rec) < TOPN + 5:
            continue
        tp = pctrank(np.array([x["mt"] for x in rec]))
        g = [x for i, x in enumerate(rec) if tp[i] >= gate_pctl]
        m6 = pctrank(np.array([x["mom6"] for x in g])); lv = pctrank(np.array([x["lowvol"] for x in g]))
        for k, x in enumerate(g):
            x["riskadj_sc"] = x["riskadj"]
            x["lowvolmom_sc"] = 0.5 * lv[k] + 0.5 * m6[k]
            x["lowvol_sc"] = lv[k]
        tables.append({"d0": d0, "g": g})
    return tables


def bench_buyhold(tables, ppy):
    """Nifty 500 buy-and-hold over the same rebalance dates, for reference."""
    bdts, bcl = index_series("Nifty 500")
    bc = {d: bcl[i] for i, d in enumerate(bdts)}
    ds = sorted(bc)
    import bisect
    def on(d):
        i = bisect.bisect_right(ds, d) - 1
        return bc[ds[i]] if i >= 0 else None
    rets = []
    for j in range(len(tables) - 1):
        a, b = on(tables[j]["d0"]), on(tables[j + 1]["d0"])
        if a and b:
            rets.append(b / a - 1.0)
    rets = np.array(rets)
    eq = np.cumprod(1 + rets); dd = eq / np.maximum.accumulate(eq) - 1
    cagr = eq[-1] ** (ppy / len(rets)) - 1
    _rf = 1.065 ** (1.0 / ppy) - 1.0   # 16AY excess basis
    return {"retvol": (rets - _rf).mean() / (rets - _rf).std() * np.sqrt(ppy) if rets.std() > 0 else 0,
            "cagr": cagr, "maxdd": float(dd.min()),
            "calmar": cagr / abs(dd.min()) if dd.min() < 0 else 0, "ann_cost_pct": 0.0,
            "turn": 0.0, "h1": 0, "h2": 0, "cap_p25_cr": float("inf"), "cap_med_cr": float("inf")}


def run(tables, scorekey, cost="real", band=False, ppy=12):
    rets, turns, held, costs, caps = [], [], {}, [], []
    for t in tables:
        g = t["g"]
        ranked = sorted(g, key=lambda x: -x[scorekey])
        if band and held:
            top_band = set(x["s"] for x in ranked[:BAND])
            keep = [x for x in ranked if x["s"] in held and x["s"] in top_band][:TOPN]
            ks = set(x["s"] for x in keep)
            picks = keep + [x for x in ranked if x["s"] not in ks][:TOPN - len(keep)]
        else:
            picks = ranked[:TOPN]
        byname = {x["s"]: x for x in picks}
        pset = set(byname)
        new, exited = pset - set(held), set(held) - pset
        gross = float(np.mean([x["fwd"] for x in picks]))
        if cost == "flat":
            c = COST_PS * (len(new) + len(exited)) / TOPN
        else:
            buy = sum(side_cost(byname[s]["mt"], byname[s]["atr"]) for s in new)
            sell = sum(side_cost(held[s]["mt"], held[s]["atr"]) for s in exited if s in held)
            c = (buy + sell) / TOPN
        rets.append(gross - c); costs.append(c)
        turns.append((len(new) + len(exited)) / TOPN)
        caps += [2.5 * x["mt"] for x in picks]          # AUM at which weight = 10% of this name's ADV
        held = byname
    rets = np.array(rets)
    eq = np.cumprod(1 + rets); dd = eq / np.maximum.accumulate(eq) - 1
    cagr = eq[-1] ** (ppy / len(rets)) - 1
    _rf = 1.065 ** (1.0 / ppy) - 1.0   # 16AY excess basis
    sh = lambda r: ((r - _rf).mean() / (r - _rf).std() * np.sqrt(ppy)) if r.std() > 0 else 0.0
    dates = [t["d0"] for t in tables]
    h1 = np.array([d <= "2018-12-31" for d in dates]); h2 = np.array([d >= "2019-01-01" for d in dates])
    cap_arr = np.array(sorted(caps))
    return {"retvol": sh(rets), "cagr": cagr, "maxdd": float(dd.min()),
            "calmar": cagr / abs(dd.min()) if dd.min() < 0 else 0,
            "ann_cost_pct": float(np.mean(costs)) * ppy * 100, "turn": float(np.mean(turns)),
            "h1": sh(rets[h1]), "h2": sh(rets[h2]),
            "cap_p25_cr": float(np.percentile(cap_arr, 25)) / 1e7,
            "cap_med_cr": float(np.percentile(cap_arr, 50)) / 1e7}


def main():
    print("building monthly (top-40% gate) + quarterly large-cap (top-20% gate) ...", flush=True)
    tbl_m = build(rebal=REBAL, gate_pctl=0.60)            # monthly, broad
    tbl_q = build(rebal=3 * REBAL, gate_pctl=0.80)        # quarterly, most-liquid (large-cap)
    print(f"monthly {len(tbl_m)} rebalances, quarterly {len(tbl_q)} rebalances\n", flush=True)
    cfgs = [
        # name, tables, scorekey, cost, band, ppy
        ("RISKADJ monthly flat-cost (the headline)", tbl_m, "riskadj_sc", "flat", False, 12),
        ("RISKADJ monthly realistic", tbl_m, "riskadj_sc", "real", False, 12),
        ("LOWVOL_MOM monthly realistic + band", tbl_m, "lowvolmom_sc", "real", True, 12),
        ("RISKADJ quarterly largecap realistic", tbl_q, "riskadj_sc", "real", False, 4),
        ("LOWVOL_MOM quarterly largecap realistic+band", tbl_q, "lowvolmom_sc", "real", True, 4),
        ("LOWVOL quarterly largecap realistic+band", tbl_q, "lowvol_sc", "real", True, 4),
        ("Nifty500 buy & hold (quarterly marks)", tbl_q, None, None, False, 4),
    ]
    rows = []
    for name, tbl, k, c, b, ppy in cfgs:
        if k is None:
            rows.append((name, bench_buyhold(tbl, ppy)))
        else:
            rows.append((name, run(tbl, k, c, b, ppy)))
    hdr = f"{'config':46}{'ret/vol':>7}{'CAGR':>7}{'MaxDD':>8}{'Calmar':>7}{'annCost':>8}{'turn':>6}{'H1':>6}{'H2':>6}{'capMedCr':>9}"
    print("=" * len(hdr))
    print("COST REALISM — does ANY config survive real cost? capMedCr = max AUM (Rs cr) before median position > 10% of its ADV")
    print("=" * len(hdr)); print(hdr)
    for name, s in rows:
        print(f"{name:38}{s['retvol']:>7.2f}{s['cagr']*100:>6.1f}%{s['maxdd']*100:>7.1f}%{s['calmar']:>7.2f}"
              f"{s['ann_cost_pct']:>7.1f}%{s['turn']:>6.2f}{s['h1']:>6.2f}{s['h2']:>6.2f}{s['cap_med_cr']:>9.0f}")
    out = os.path.join(os.path.dirname(__file__), "out", "cost_realism.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["config", "retvol", "cagr_pct", "maxdd_pct", "calmar", "ann_cost_pct", "avg_turnover",
                    "h1_retvol", "h2_retvol", "cap_p25_cr", "cap_med_cr"])
        for name, s in rows:
            w.writerow([name, round(s["retvol"], 2), round(s["cagr"]*100, 1), round(s["maxdd"]*100, 1),
                        round(s["calmar"], 2), round(s["ann_cost_pct"], 1), round(s["turn"], 2),
                        round(s["h1"], 2), round(s["h2"], 2), round(s["cap_p25_cr"], 0), round(s["cap_med_cr"], 0)])
    print("\nsaved -> out/cost_realism.csv")


if __name__ == "__main__":
    main()
