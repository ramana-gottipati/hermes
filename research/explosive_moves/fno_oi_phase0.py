"""OPTIONS-IMPLIED PHASE 0 — event-study gate on the OI signals ALREADY on the box (fno_oi_signals),
no new data. Descriptive (2026-07-23). For each signal (PCR, max-pain distance, basis, futures OI change),
rank the F&O universe cross-sectionally each week, form top vs bottom quintile, measure 1-month (22d)
forward excess vs Nifty-500, Cliff's δ (top vs bottom), both halves. GATE: any signal δ>=+0.05 both halves
+ monotone spread -> proceed to Phase 1 (IV build); none -> OI dimension is priced, record + stop.
⚠ ~2yr window only (2024-07+) -> low power; forward-test-only regardless.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.fno_oi_phase0 --run
"""
from __future__ import annotations

import bisect
import json
import sys

import numpy as np

from .common import OUT_DIR, load_series, main_conn
from .metrics import index_series

FWD = 22
STEP = 5           # weekly sampling (de-overlap)
HALF = "2025-08"   # ~midpoint of the 2024-07..2026-07 window


def _cliffs(a, b):
    b = np.sort(np.asarray(b, float)); nb = len(b)
    if nb == 0 or len(a) == 0:
        return float("nan")
    tot = 0
    for x in a:
        tot += int(np.searchsorted(b, x, "left")) - (nb - int(np.searchsorted(b, x, "right")))
    return tot / (len(a) * nb)


def run():
    mc = main_conn()
    rows = mc.execute("SELECT symbol,trade_date,pcr,max_pain,und_price,basis_pct,fut_oi_chg_pct "
                      "FROM fno_oi_signals").fetchall()
    d, c = index_series("Nifty 500")
    idx_d = list(d); idx_c = np.asarray(c, float)

    def idx_ret(d0, d1):
        i0 = bisect.bisect_right(idx_d, d0) - 1; i1 = bisect.bisect_right(idx_d, d1) - 1
        return idx_c[i1] / idx_c[i0] - 1.0 if i0 >= 0 and i1 >= 0 else np.nan

    syms = sorted({r[0] for r in rows})
    px = {}
    for s in syms:
        S = load_series(mc, s)
        if S is not None:
            px[s] = ({dt: i for i, dt in enumerate(S.date)}, S.date, S.adj_close)
    mc.close()

    def fwd_exc(sym, dt):
        if sym not in px:
            return None
        pos, dates, ac = px[sym]
        j = pos.get(dt)
        if j is None or j + FWD >= len(ac) or ac[j] <= 0 or ac[j + FWD] <= 0:
            return None
        e = ac[j + FWD] / ac[j] - 1.0 - idx_ret(dt, dates[j + FWD])
        return e if np.isfinite(e) else None

    SIG = {
        "PCR": lambda r: r[2],
        "maxpain_dist": lambda r: (r[4] / r[3] - 1.0) if (r[3] and r[4]) else None,
        "basis_pct": lambda r: r[5],
        "fut_oi_chg_pct": lambda r: r[6],
    }
    bydate = {}
    for r in rows:
        bydate.setdefault(r[1], []).append(r)
    alldates = sorted(bydate)
    sampled = alldates[::STEP]

    out = {"window": "%s..%s" % (alldates[0], alldates[-1]), "n_dates_sampled": len(sampled),
           "note": "cross-sectional quintiles per week; 22d fwd excess vs N500; δ = top-Q vs bottom-Q", "signals": {}}
    for name, fn in SIG.items():
        topE = {"all": [], "h1": [], "h2": []}; botE = {"all": [], "h1": [], "h2": []}
        for dt in sampled:
            vals = []
            for r in bydate[dt]:
                v = fn(r)
                if v is None or not np.isfinite(v):
                    continue
                e = fwd_exc(r[0], dt)
                if e is not None:
                    vals.append((v, e))
            if len(vals) < 25:
                continue
            vals.sort(key=lambda x: x[0])
            k = max(1, len(vals) // 5)
            hk = "h1" if dt < HALF else "h2"
            for v, e in vals[-k:]:
                topE["all"].append(e); topE[hk].append(e)
            for v, e in vals[:k]:
                botE["all"].append(e); botE[hk].append(e)

        def m(x):
            return round(float(np.mean(x)) * 100, 2) if x else None

        dlt = _cliffs(topE["all"], botE["all"]) if topE["all"] and botE["all"] else float("nan")
        d1 = _cliffs(topE["h1"], botE["h1"]) if topE["h1"] and botE["h1"] else float("nan")
        d2 = _cliffs(topE["h2"], botE["h2"]) if topE["h2"] and botE["h2"] else float("nan")
        passes = (np.isfinite(dlt) and abs(dlt) >= 0.05 and np.isfinite(d1) and np.isfinite(d2)
                  and np.sign(d1) == np.sign(d2) and abs(d1) >= 0.03 and abs(d2) >= 0.03)
        out["signals"][name] = {
            "n_top": len(topE["all"]), "topQ_fwd_exc%": m(topE["all"]), "botQ_fwd_exc%": m(botE["all"]),
            "cliffs_top_vs_bot": round(dlt, 4) if np.isfinite(dlt) else None,
            "delta_h1": round(d1, 4) if np.isfinite(d1) else None, "delta_h2": round(d2, 4) if np.isfinite(d2) else None,
            "SELECTS": bool(passes),
        }
    anyp = any(v["SELECTS"] for v in out["signals"].values())
    out["PHASE0_VERDICT"] = "PROCEED to Phase 1 (a signal selects)" if anyp else "STOP — OI dimension priced; no signal selects (record cheap negative)"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fno_oi_phase0.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
