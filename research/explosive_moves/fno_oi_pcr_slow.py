"""OPTIONS-IMPLIED PHASE 1.6 — SLOWED PCR: does cutting turnover rescue the PCR book? Descriptive
(2026-07-23, the LAST OI test). The monthly-raw PCR book failed ONLY on turnover (815%/yr, net R/V 0.28).
This tests slower variants — quarterly rebalance and/or 3-month-smoothed PCR — vs the 0.89 hurdle + index.
Decision rule: any variant net R/V > 0.89 AND beats index -> a tradeable OI variant exists; none -> the
OI-positioning dimension is priced, stop (and IV won't differ). ⚠ ~2yr window; forward-test-only regardless.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.fno_oi_pcr_slow --run
"""
from __future__ import annotations

import json
import sys

import numpy as np

from .common import OUT_DIR, load_series, main_conn
from .metrics import index_series

RT = 0.005


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
            round((float(eq[-1]) ** (12 / len(r)) - 1) * 100, 1), round(dd * 100, 1))


def run():
    mc = main_conn()
    rows = mc.execute("SELECT symbol,trade_date,pcr FROM fno_oi_signals WHERE pcr IS NOT NULL").fetchall()
    pcr_by = {}; lastd = {}
    for sym, dt, pcr in rows:
        ym = dt[:7]; k = (ym, sym)
        if k not in lastd or dt > lastd[k]:
            lastd[k] = dt; pcr_by.setdefault(ym, {})[sym] = float(pcr)
    syms = sorted({s for v in pcr_by.values() for s in v})
    ret_by = {}
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

    # 3-month-smoothed PCR
    pcr_sm = {}
    for i, m in enumerate(months):
        win = months[max(0, i - 2):i + 1]
        for s in pcr_by[m]:
            vals = [pcr_by[w][s] for w in win if s in pcr_by[w]]
            if vals:
                pcr_sm.setdefault(m, {})[s] = float(np.mean(vals))

    def book(pmap, step):
        held = set(); prev = set(); rets = []; bench = []; turns = []
        for i in range(len(months) - 1):
            m = months[i]; nm = _madd(m, 1)
            if nm not in ret_by or nm not in iret:
                continue
            cost = 0.0
            if i % step == 0 and m in pmap and len(pmap[m]) >= 25:
                ranked = sorted(pmap[m].items(), key=lambda x: x[1])
                k = max(1, len(ranked) // 5)
                top = {s for s, _ in ranked[-k:]}
                turn = len(top - prev) / len(top) if prev else 1.0
                turns.append(turn); prev = top; held = top; cost = turn * RT
            rr = [ret_by[nm][s] for s in held if s in ret_by[nm]]
            if rr:
                rets.append(float(np.mean(rr)) - cost); bench.append(iret[nm])
        st = _st(rets)
        # annualise turnover: mean per-rebalance turn x (rebalances/yr)
        rpy = 12.0 / step
        return {"net": st, "ann_turnover%": round(float(np.mean(turns)) * rpy * 100) if turns else None,
                "beats_index": bool(st and _st(bench) and st[1] > _st(bench)[1]),
                "fundable": bool(st and st[0] > 0.89 and _st(bench) and st[1] > _st(bench)[1])}

    variants = {
        "raw_monthly (baseline)": book(pcr_by, 1),
        "raw_QUARTERLY": book(pcr_by, 3),
        "SMOOTHED_monthly": book(pcr_sm, 1),
        "SMOOTHED_QUARTERLY": book(pcr_sm, 3),
    }
    anyf = any(v["fundable"] for v in variants.values())
    out = {
        "window": "%s..%s" % (months[0], months[-1]), "hurdle": 0.89,
        "index_net": _st([iret[_madd(m, 1)] for m in months[:-1] if _madd(m, 1) in iret]),
        "variants": variants,
        "VERDICT": "a tradeable slow-PCR variant EXISTS" if anyf else
                   "NONE fundable — OI-positioning dimension is PRICED; stop (IV won't differ on a 2yr window)",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fno_oi_pcr_slow.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
