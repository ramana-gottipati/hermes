"""LOW-VOL × ACCUMULATION TILT — does the institutional-flow signal LIFT the fundable low-vol book?
Descriptive conditioner test (2026-07-23). Reuses the sealed low-vol holdings (`lowvolq_holdings`) — NO
re-selection. Each rebalance quarter, split the held low-vol names by PIT Δ(DII+FII) into an ACCUM half
(institutions buying) and a DISTRIB half (selling), and compare both vs the equal-weight BASE — all on the
flow-overlap window (2019+). The LIFT = ACCUM − BASE. Honest limits: ~7-year window; the base flow signal
was weak (δ +0.07). Gross isolates the signal's value; a flat net is reported beside it.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.lowvol_flow_tilt --run
"""
from __future__ import annotations

import json
import sys

import numpy as np

from .common import OUT_DIR, load_series, main_conn, research_conn


def _madd(m, k):
    y, mm = int(m[:4]), int(m[5:7]) + k
    y += (mm - 1) // 12
    mm = (mm - 1) % 12 + 1
    return f"{y:04d}-{mm:02d}"


def _st(store, lo=None, hi=None):
    ms = sorted(m for m in store if (lo is None or m >= lo) and (hi is None or m < hi))
    if len(ms) < 12:
        return None
    r = np.array([store[m][0] / store[m][1] for m in ms])
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
    return (round(float(r.mean() / r.std() * 12 ** .5), 2),
            round((float(eq[-1]) ** (12 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(ms))


def run():
    rc = research_conn()
    snaps = {}
    for m, sym in rc.execute("SELECT month,symbol FROM lowvolq_holdings ORDER BY month"):
        snaps.setdefault(m, []).append(sym)
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

    def dinst_at(sym, m):
        if sym not in persym:
            return None
        cut = m + "-31"
        av = [t for (pe, rd, t) in persym[sym] if rd <= cut]
        return (av[-1] - av[-2]) if len(av) >= 2 else None

    # monthly returns per held name (adj_close, month-end), loaded once
    mc = main_conn()
    allnames = sorted({s for v in snaps.values() for s in v})
    mret = {}
    for s in allnames:
        S = load_series(mc, s)
        if S is None:
            continue
        me = {}
        for i, dt in enumerate(S.date):
            me[dt[:7]] = S.adj_close[i]
        mm = sorted(me)
        d = {}
        for i in range(1, len(mm)):
            if me[mm[i - 1]] > 0:
                d[mm[i]] = me[mm[i]] / me[mm[i - 1]] - 1.0
        mret[s] = d
    mc.close()

    base = {}; acc = {}; dis = {}; turn_acc = 0; turn_n = 0
    prev_acc = set()
    for m in sorted(snaps):
        held = snaps[m]
        di = {s: dinst_at(s, m) for s in held}
        valid = {s: v for s, v in di.items() if v is not None}
        accum = distrib = set()
        if len(valid) >= 6:
            med = float(np.median(list(valid.values())))
            accum = {s for s, v in valid.items() if v >= med}
            distrib = {s for s, v in valid.items() if v < med}
            if prev_acc:
                turn_acc += len(accum - prev_acc) / max(1, len(accum)); turn_n += 1
            prev_acc = set(accum)
        for off in (1, 2, 3):
            fm = _madd(m, off)
            for grp, store in ((held, base), (accum, acc), (distrib, dis)):
                rr = [mret[s][fm] for s in grp if s in mret and fm in mret[s]]
                if rr:
                    st = store.setdefault(fm, [0.0, 0]); st[0] += float(np.mean(rr)); st[1] += 1

    common = sorted(set(acc) & set(dis) & set(base))

    def st_on(store):
        ms = [m for m in common if m in store]
        if len(ms) < 12:
            return None
        r = np.array([store[m][0] / store[m][1] for m in ms])
        eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
        return (round(float(r.mean() / r.std() * 12 ** .5), 2),
                round((float(eq[-1]) ** (12 / len(r)) - 1) * 100, 1), round(dd * 100, 1), len(ms))

    ann_turn = (turn_acc / turn_n * 4) if turn_n else 0.0
    out = {
        "flow_split_window": (common[0] + " .. " + common[-1]) if common else "none",
        "n_common_months": len(common),
        "note": "ALL THREE on the SAME (flow-split) window — fair comparison. GROSS, equal-weight within bucket. "
                "Window shrank because PIT report_date is well-populated only in recent years -> the split is effectively recent-only.",
        "BASE_lowvol (all held, same window)": st_on(base),
        "ACCUM_half (institutions buying)": st_on(acc),
        "DISTRIB_half (institutions selling)": st_on(dis),
        "base_full_2019window_for_reference": _st(base, "2019-09"),
        "accum_annual_turnover~pct": round(ann_turn * 100),
        "LIFT_read": "tilt HELPS only if ACCUM > BASE and ACCUM > DISTRIB on the SAME window, beyond the extra turnover cost",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lowvol_flow_tilt.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
