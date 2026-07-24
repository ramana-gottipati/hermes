"""OPTIONS-IMPLIED PHASE 1.5 — is the Phase-0 PCR signal a FUNDABLE NET BOOK? Descriptive (2026-07-23).
Long the top-PCR quintile (the contrarian-bullish leg that selected), F&O universe, monthly rebalance,
NET of cost. Compare vs index + bottom-quintile + the long-short spread. This is the decisive cheap test
BEFORE the multi-day IV build: selection (δ+0.06) ≠ fundability (the flow lesson).
⚠ ~2yr / ~24 monthly points only -> very low power; forward-test-only regardless of result.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.fno_oi_pcr_book --run
"""
from __future__ import annotations

import json
import sys

import numpy as np

from .common import OUT_DIR, load_series, main_conn
from .metrics import index_series

RT = 0.005          # round-trip cost, liquid F&O names


def _madd(m, k):
    y, mm = int(m[:4]), int(m[5:7]) + k
    y += (mm - 1) // 12
    return f"{y:04d}-{(mm - 1) % 12 + 1:02d}"


def _st(r):
    r = np.asarray(r, float)
    if len(r) < 6:
        return None
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
    return (round(float(r.mean() / r.std() * 12 ** .5), 2),
            round((float(eq[-1]) ** (12 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(r))


def run():
    mc = main_conn()
    rows = mc.execute("SELECT symbol,trade_date,pcr FROM fno_oi_signals WHERE pcr IS NOT NULL").fetchall()
    pcr_by = {}          # month -> {sym: month-end pcr}
    lastd = {}
    for sym, dt, pcr in rows:
        ym = dt[:7]; k = (ym, sym)
        if k not in lastd or dt > lastd[k]:
            lastd[k] = dt; pcr_by.setdefault(ym, {})[sym] = float(pcr)

    syms = sorted({s for v in pcr_by.values() for s in v})
    ret_by = {}          # month -> {sym: return earned that month}
    for s in syms:
        S = load_series(mc, s)
        if S is None:
            continue
        me = {}
        for i, dt in enumerate(S.date):
            me[dt[:7]] = S.adj_close[i]
        mm = sorted(me)
        for i in range(1, len(mm)):
            if me[mm[i - 1]] > 0:
                ret_by.setdefault(mm[i], {})[s] = me[mm[i]] / me[mm[i - 1]] - 1.0
    mc.close()

    d, c = index_series("Nifty 500")
    ime = {}
    for dt, cl in zip(d, c):
        ime[dt[:7]] = cl
    im = sorted(ime); iret = {im[i]: ime[im[i]] / ime[im[i - 1]] - 1 for i in range(1, len(im))}

    months = sorted(pcr_by)
    topN = []; topG = []; botN = []; spread = []; bench = []; prev_top = set(); turns = []
    for i in range(len(months) - 1):
        m = months[i]; nm = _madd(m, 1)
        if nm not in ret_by or nm not in iret:
            continue
        ranked = sorted(pcr_by[m].items(), key=lambda x: x[1])   # ascending PCR
        if len(ranked) < 25:
            continue
        k = max(1, len(ranked) // 5)
        top = [s for s, _ in ranked[-k:]]                        # HIGH pcr (contrarian long)
        bot = [s for s, _ in ranked[:k]]
        rt = [ret_by[nm][s] for s in top if s in ret_by[nm]]
        rb = [ret_by[nm][s] for s in bot if s in ret_by[nm]]
        if not rt or not rb:
            continue
        tset = set(top); turn = len(tset - prev_top) / len(tset) if prev_top else 1.0
        turns.append(turn); prev_top = tset
        g = float(np.mean(rt))
        topG.append(g); topN.append(g - turn * RT)
        botN.append(float(np.mean(rb)))
        spread.append(g - float(np.mean(rb)))
        bench.append(iret[nm])

    out = {
        "window": "%s..%s" % (months[0], months[-1]), "months": len(topN),
        "annual_turnover~pct": round(float(np.mean(turns)) * 12 * 100) if turns else None,
        "TOP_PCR_quintile_net": _st(topN), "TOP_PCR_gross": _st(topG),
        "BOTTOM_PCR_quintile_net": _st(botN),
        "LONG_SHORT_spread_gross": _st(spread),
        "Nifty500_same_window": _st(bench),
        "hurdle": 0.89,
        "FUNDABLE_long_only": bool(_st(topN) and _st(topN)[0] > 0.89 and _st(bench) and _st(topN)[1] > _st(bench)[1]),
        "read": "fundable if TOP net R/V > 0.89 AND CAGR > index; else selection did not survive cost (flow lesson repeats)",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fno_oi_pcr_book.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
