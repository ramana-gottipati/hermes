"""INSTITUTIONAL FLOW — LONG-SHORT — does the weak-but-real flow signal (inst_flow δ+0.07) become a
fundable MARKET-NEUTRAL book once beta is removed? Descriptive test (2026-07-23), built on the sealed
inst_flow signal. Broad universe, quarterly: LONG top-quintile Δ(DII+FII), SHORT bottom-quintile — the
spread is dollar-neutral (removes the market factor that dragged the long-only Q5). PIT via report_date.

REALISM (this is where India long-shorts usually die, so it's priced in): the SHORT leg is restricted to
liquid/shortable names (med_turn >= Rs 25cr proxy for SLB/F&O availability) and charged a borrow cost
(~4%/yr = 1%/quarter) on top of transaction cost; the LONG leg needs med_turn >= Rs 1cr. Gross spread and
NET (post-borrow) both reported. Honest limits: ~28 quarters (2019+); signal is weak (δ +0.07). Metric
basis D142; descriptive-only, SEBI-safe. If NET spread R/V > 0.89 -> pre-register properly; else record.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.inst_flow_ls --run
"""
from __future__ import annotations

import bisect
import json
import sys

import numpy as np

from .common import OUT_DIR, load_series, main_conn, research_conn
from .metrics import index_series

LIQ_LONG = 1e7
LIQ_SHORT = 25e7          # shortable proxy (SLB/F&O liquidity)
FWD = 63                  # ~1 quarter
LONG_RT = 0.005
SHORT_RT = 0.006
BORROW_Q = 0.010          # ~4%/yr stock-borrow, per quarter


def _bk(qseries):
    qs = sorted(qseries)
    if len(qs) < 8:
        return None
    r = np.array([qseries[q] for q in qs])
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
    return (round(float(r.mean() / r.std() * 4 ** .5), 2),
            round((float(eq[-1]) ** (4 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(r))


def run():
    rc = research_conn()
    tmp = {}
    for sym, pe, rd, metric, val in rc.execute(
            "SELECT symbol,period_end,report_date,metric,value FROM shareholding_history "
            "WHERE metric IN ('DIIs','FIIs') AND value IS NOT NULL AND report_date IS NOT NULL"):
        tmp.setdefault((sym, pe), {})[metric] = float(val)
        tmp[(sym, pe)]["rd"] = rd
    rc.close()
    persym = {}
    for (sym, pe), d in tmp.items():
        if "DIIs" in d and "FIIs" in d:
            persym.setdefault(sym, []).append((pe, d["rd"], d["DIIs"] + d["FIIs"]))
    for s in persym:
        persym[s].sort()

    d, c = index_series("Nifty 500")
    idx_d = list(d); idx_c = np.asarray(c, float)

    def idx_ret(d0, d1):
        i0 = bisect.bisect_right(idx_d, d0) - 1; i1 = bisect.bisect_right(idx_d, d1) - 1
        return idx_c[i1] / idx_c[i0] - 1.0 if i0 >= 0 and i1 >= 0 else np.nan

    mc = main_conn()
    ev = []            # (period_end, dinst, ret63, excess63, mt)
    for sym in sorted(persym):
        qs = persym[sym]
        if len(qs) < 2:
            continue
        S = load_series(mc, sym)
        if S is None or S.n < 80:
            continue
        dates = S.date; ac = S.adj_close
        for k in range(1, len(qs)):
            pe, rd, tot = qs[k]
            j = bisect.bisect_left(dates, rd)
            if j >= S.n or ac[j] <= 0 or j + FWD >= S.n or ac[j + FWD] <= 0 or S.med_turn[j] < LIQ_LONG:
                continue
            r = ac[j + FWD] / ac[j] - 1.0
            ev.append((pe, tot - qs[k - 1][2], r, r - idx_ret(dates[j], dates[j + FWD]), float(S.med_turn[j])))
    mc.close()

    byq = {}
    for e in ev:
        byq.setdefault(e[0], []).append(e)
    spread_g = {}; spread_n = {}; longleg = {}; longleg_exc = {}; shortleg = {}
    for pe, es in byq.items():
        longu = sorted([e for e in es if e[4] >= LIQ_LONG], key=lambda x: x[1])
        shortu = sorted([e for e in es if e[4] >= LIQ_SHORT], key=lambda x: x[1])
        if len(longu) < 25 or len(shortu) < 25:
            continue
        kL = max(1, len(longu) // 5); kS = max(1, len(shortu) // 5)
        Lret = float(np.mean([e[2] for e in longu[-kL:]]))          # top-quintile Δinst (accumulation)
        Lexc = float(np.mean([e[3] for e in longu[-kL:]]))
        Sret = float(np.mean([e[2] for e in shortu[:kS]]))          # bottom-quintile (distribution), liquid only
        spread_g[pe] = Lret - Sret
        spread_n[pe] = (Lret - LONG_RT) - (Sret + SHORT_RT + BORROW_Q)
        longleg[pe] = Lret - LONG_RT; longleg_exc[pe] = Lexc; shortleg[pe] = Sret

    def halves(dic):
        return {"h1": _bk({q: v for q, v in dic.items() if q < "2023-01"}),
                "h2": _bk({q: v for q, v in dic.items() if q >= "2023-01"})}

    out = {
        "quarters": len(spread_g), "signal": "Δ(DII+FII), long top-quintile / short bottom-quintile, PIT",
        "costs": {"long_rt": LONG_RT, "short_rt": SHORT_RT, "borrow_per_qtr": BORROW_Q},
        "SPREAD_gross(L-S)": _bk(spread_g),
        "SPREAD_net(post-borrow)": _bk(spread_n), "SPREAD_net_halves": halves(spread_n),
        "long_leg_net(top-quintile)": _bk(longleg),
        "long_leg_mean_excess_vs_N500_per_qtr%": round(float(np.mean(list(longleg_exc.values()))) * 100, 2) if longleg_exc else None,
        "short_leg_gross(bottom, liquid)": _bk(shortleg),
        "hurdle": 0.89,
        "FUNDABLE_market_neutral": bool(_bk(spread_n) and _bk(spread_n)[0] > 0.89),
        "read": "market-neutral REMOVES beta -> spread R/V can beat either leg IF the signal is real; the borrow cost is the killer",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "inst_flow_ls.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
