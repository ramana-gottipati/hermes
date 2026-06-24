"""EXPERIMENT — relative liquidity gate + proprietary quality overlay on RISKADJ / QUAL_MOM.

Answers three questions, walk-forward (2012-18 & 2019-26), net of cost, NO look-ahead:
  1. Does replacing the static Rs5cr floor with a RELATIVE percentile gate change the edge?
  2. Does layering our point-in-time FUNDAMENTAL QUALITY (research.db, report_date<=as_of)
     onto the momentum rank lift Sharpe or cut the -33% drawdown?
  3. Does it survive a 1.5x cost stress?

Construction matches factory.py (top-25, monthly, equal-weight, enter at d0 close -> next
rebalance, COST_PS per turnover) so results are directly comparable to the recorded benchmark.
Quality is built ONLY from filings known on/before the rebalance date. Writes
out/overlay_experiment.csv. Read-only (never writes production tables).
"""
from __future__ import annotations
import csv
import os
import sqlite3
import numpy as np

import sys
sys.path.insert(0, "/opt/hermes/research")
from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series
from explosive_moves.factory import eqstats, pctrank, COST_PS, CR

RESEARCH_DB = "/opt/hermes/data/research.db"
REBAL = 22
TOPN = 25
LIQ_PCTL = 0.60          # relative gate: keep names in the top 40% of that day's turnover
QFILTER = 0.50           # quality filter: keep top-half-quality names
BLEND_W = 0.50           # quality weight in the blend variant

_SALES = ("Sales", "Revenue"); _OPM = ("OPM %", "Financing Margin %")
_BORROW = ("Borrowings", "Borrowing"); _ROCE = ("ROCE %", "Financing Margin %")


# ---- PIT fundamentals (self-contained; no look-ahead via report_date<=as_of) ----
def load_frame(con, symbol):
    rows = con.execute(
        "SELECT period_type, metric, period_end, report_date, value "
        "FROM fundamentals_history WHERE symbol=? AND value IS NOT NULL", (symbol,)).fetchall()
    frame = {}
    for pt, m, pe, rd, v in rows:
        frame.setdefault((pt, m), []).append((pe, rd, v))
    return frame


def latest_known(frame, ptype, names, as_of):
    for nm in (names if isinstance(names, tuple) else (names,)):
        vals = [(pe, v) for (pe, rd, v) in frame.get((ptype, nm), []) if rd <= as_of]
        if vals:
            return max(vals, key=lambda t: t[0])[1]
    return None


def quality_metrics(frame, as_of):
    """(roce, debt/equity, opm, interest_cover) — latest known annual as of `as_of`."""
    roce = latest_known(frame, "A", _ROCE, as_of)
    opm = latest_known(frame, "A", _OPM, as_of)
    borrow = latest_known(frame, "A", _BORROW, as_of)
    eqcap = latest_known(frame, "A", "Equity Capital", as_of)
    res = latest_known(frame, "A", "Reserves", as_of)
    op = latest_known(frame, "A", "Operating Profit", as_of)
    intr = latest_known(frame, "A", "Interest", as_of)
    nw = (eqcap + res) if (eqcap is not None and res is not None) else None
    de = (borrow / nw) if (borrow is not None and nw and nw > 0) else None
    ic = (op / intr) if (op is not None and intr and intr > 0) else None
    return roce, de, opm, ic


def qrank(vals):
    return pctrank(np.array([v if v is not None else np.nan for v in vals], dtype=float))


# ---- build rebalance tables (relative gate + momentum + quality) ----
def build_tables():
    cache = load_symbol_cache()
    dts, _ = index_series("Nifty 50")
    cal = [d for d in dts if d >= "2012-06-01"]
    rebal_idx = list(range(0, len(cal), REBAL))
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}

    print(f"loading PIT fundamentals for {len(cache)} symbols ...", flush=True)
    con = sqlite3.connect(RESEARCH_DB)
    frames = {}
    for s in cache:
        fr = load_frame(con, s)
        if fr:
            frames[s] = fr
    con.close()
    print(f"  {len(frames)} symbols have fundamentals", flush=True)

    tables = []
    for r in range(len(rebal_idx) - 1):
        d0, d1 = cal[rebal_idx[r]], cal[rebal_idx[r + 1]]
        rec = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130 or i0 < 126:
                continue
            i1 = d2i.get(d1, min(i0 + REBAL, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            mom6 = ac[i0] / ac[i0 - 126] - 1.0
            vol = float(F["vol_66"][i0])
            dlv = float(F["deliv_qty_trend"][i0]) if np.isfinite(F["deliv_qty_trend"][i0]) else np.nan
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            rec.append({"s": s, "mt": float(mt[i0]) if np.isfinite(mt[i0]) else 0.0,
                        "riskadj": mom6 / (vol + 1e-6), "vol": vol, "dlv": dlv,
                        "fwd": ac[i1] / ac[i0] - 1.0})
        if len(rec) < TOPN + 5:
            continue
        # relative liquidity gate (cross-sectional this date)
        liq_pr = pctrank(np.array([x["mt"] for x in rec]))
        for k, x in enumerate(rec):
            x["liq_pr"] = liq_pr[k]
        gated = [x for x in rec if x["liq_pr"] >= LIQ_PCTL]
        # quality only for the gated set (cheap)
        for x in gated:
            fr = frames.get(x["s"])
            x["roce"], x["de"], x["opm"], x["ic"] = quality_metrics(fr, d0) if fr else (None, None, None, None)
        rr = qrank([x["roce"] for x in gated]); dr = qrank([(-x["de"]) if x["de"] is not None else None for x in gated])
        opr = qrank([x["opm"] for x in gated]); icr = qrank([x["ic"] for x in gated])
        for k, x in enumerate(gated):
            comps = [c for c in (rr[k], dr[k], opr[k], icr[k]) if np.isfinite(c)]
            x["q"] = float(np.mean(comps)) if comps else np.nan
        tables.append({"d0": d0, "all": rec, "gated": gated})
    return tables


# ---- portfolio runner ----
def run(tables, selector, cost_mult=1.0):
    rets, dates, held = [], [], set()
    for t in tables:
        picks = selector(t)
        if not picks:
            rets.append(0.0); dates.append(t["d0"]); continue
        fwds = [p["fwd"] for p in picks]
        gross = float(np.mean(fwds))
        pset = set(p["s"] for p in picks)
        turn = (len(pset - held) + len(held - pset)) / max(len(pset), 1)
        rets.append(gross - COST_PS * cost_mult * turn)
        dates.append(t["d0"]); held = pset
    return np.array(rets), dates


def topn_by(items, key, n=TOPN):
    return sorted(items, key=lambda x: -x[key])[:n]


# selectors
def sel_riskadj_static(t):
    g = [x for x in t["all"] if x["mt"] >= 5 * CR]
    return topn_by(g, "riskadj")


def sel_riskadj_rel(t):
    return topn_by(t["gated"], "riskadj")


def sel_riskadj_qfilter(t):
    g = [x for x in t["gated"] if np.isfinite(x["q"]) and x["q"] >= QFILTER]
    return topn_by(g if len(g) >= TOPN else t["gated"], "riskadj")


def sel_riskadj_qblend(t):
    g = t["gated"]
    ra = pctrank(np.array([x["riskadj"] for x in g]))
    for k, x in enumerate(g):
        q = x["q"] if np.isfinite(x["q"]) else 0.5
        x["_score"] = (1 - BLEND_W) * ra[k] + BLEND_W * q
    return topn_by(g, "_score")


def sel_qualmom_rel(t):
    g = t["gated"]
    ra = pctrank(np.array([x["riskadj"] for x in g]))
    dl = pctrank(np.array([x["dlv"] for x in g]))
    nv = pctrank(np.array([-x["vol"] for x in g]))
    for k, x in enumerate(g):
        x["_score"] = 0.4 * ra[k] + 0.3 * (dl[k] if np.isfinite(dl[k]) else 0.5) + 0.3 * nv[k]
    return topn_by(g, "_score")


def stats_row(tables, name, selector, cost_mult=1.0):
    rets, dates = run(tables, selector, cost_mult)
    full = eqstats(rets)
    da = np.array(dates)
    m1 = np.array([d <= "2018-12-31" for d in dates]); m2 = np.array([d >= "2019-01-01" for d in dates])
    a = eqstats(rets[m1]); b = eqstats(rets[m2])
    avg_n = np.mean([len(selector(t)) for t in tables])
    surv = bool(a and b and a["sharpe"] > 0.89 and b["sharpe"] > 0.89 and a["cagr"] > 0 and b["cagr"] > 0)
    return {"name": name, "cagr": full["cagr"], "maxdd": full["maxdd"], "sharpe": full["sharpe"],
            "calmar": full["calmar"], "totx": full["totx"], "h1_sharpe": a["sharpe"] if a else None,
            "h2_sharpe": b["sharpe"] if b else None, "h2_cagr": b["cagr"] if b else None,
            "avg_n": avg_n, "surv": surv, "cost_mult": cost_mult}


def main():
    print("building tables (relative gate + PIT quality join) ...", flush=True)
    tables = build_tables()
    print(f"  {len(tables)} rebalance dates; avg gated universe = "
          f"{np.mean([len(t['gated']) for t in tables]):.0f}, avg full = {np.mean([len(t['all']) for t in tables]):.0f}", flush=True)

    rows = []
    rows.append(stats_row(tables, "A. RISKADJ static-5cr (benchmark)", sel_riskadj_static))
    rows.append(stats_row(tables, "B. RISKADJ relative-gate", sel_riskadj_rel))
    rows.append(stats_row(tables, "C. RISKADJ rel + QUALITY-FILTER", sel_riskadj_qfilter))
    rows.append(stats_row(tables, "D. RISKADJ rel + QUALITY-BLEND 50/50", sel_riskadj_qblend))
    rows.append(stats_row(tables, "E. QUAL_MOM relative-gate", sel_qualmom_rel))
    rows.append(stats_row(tables, "F. D (blend) @ 1.5x cost stress", sel_riskadj_qblend, cost_mult=1.5))
    rows.append(stats_row(tables, "G. B (riskadj-rel) @ 1.5x cost stress", sel_riskadj_rel, cost_mult=1.5))

    hdr = f"{'variant':40}{'CAGR':>7}{'MaxDD':>8}{'Shrp':>6}{'Clmr':>6}{'tot':>6}{'H1sh':>6}{'H2sh':>6}{'N':>5}  surv"
    print("\n" + "=" * len(hdr)); print("EXPERIMENT RESULTS (top-25 monthly, net cost; hurdle Nifty500 Sharpe 0.89)")
    print("=" * len(hdr)); print(hdr)
    for r in rows:
        print(f"{r['name']:40}{r['cagr']*100:>6.1f}%{r['maxdd']*100:>7.1f}%{r['sharpe']:>6.2f}"
              f"{r['calmar']:>6.2f}{r['totx']:>5.1f}x{(r['h1_sharpe'] or 0):>6.2f}{(r['h2_sharpe'] or 0):>6.2f}"
              f"{r['avg_n']:>5.0f}  {'YES' if r['surv'] else ''}")

    out = os.path.join(os.path.dirname(__file__), "out", "overlay_experiment.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["variant", "cagr_pct", "maxdd_pct", "sharpe", "calmar", "total_x",
                    "h1_2012_18_sharpe", "h2_2019_26_sharpe", "h2_cagr_pct", "avg_positions",
                    "cost_mult", "survives"])
        for r in rows:
            w.writerow([r["name"], round(r["cagr"] * 100, 1), round(r["maxdd"] * 100, 1),
                        round(r["sharpe"], 2), round(r["calmar"], 2), round(r["totx"], 1),
                        round(r["h1_sharpe"] or 0, 2), round(r["h2_sharpe"] or 0, 2),
                        round((r["h2_cagr"] or 0) * 100, 1), round(r["avg_n"], 0),
                        r["cost_mult"], "YES" if r["surv"] else "NO"])
    print(f"\nsaved -> out/overlay_experiment.csv")


if __name__ == "__main__":
    main()
