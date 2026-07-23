"""LOW-VOL SLEEVE v2 — QUARTERLY rebalance + HYSTERESIS hold-band (turnover-cut refinement).
PRE-REGISTERED 2026-07-22d.

Follows the 07-22c fence: the monthly bottom-quintile low-vol sleeve survived to ~₹50cr but its
199%/yr one-way turnover was the cost driver. This rebuilds it LOWVOL_MOM-style to cut turnover and
lift capacity: ENTER the bottom-20% vol names, KEEP a held name until it leaves the wider bottom-40%
band (hysteresis), and only re-select QUARTERLY (every 3 months). Everything else identical to 07-22c
(CA-adjusted; liquid ≥₹5cr, close ≥₹20, trailing-126d vol; equal-weight; monthly returns from the
held set). This is PORTFOLIO CONSTRUCTION, not a momentum/reversal hybrid.

SUCCESS CRITERION (pre-committed, descriptive): LOWER annualised turnover and HIGHER AUM capacity
(net R/V > 0.89 at a larger AUM) than the 07-22c monthly sleeve, WITH the standalone R/V / drawdown
edge and both-halves robustness intact. Capacity via cost_participation.side_costs (Almgren √-impact);
book cost = 0.15%/side on quarterly turnover.

METRIC BASIS (D142): annualised mean/sd return/vol ratios, no risk-free subtracted.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.lowvol_sleeve_q --build   # lowvolq_book + lowvolq_holdings -> research.db
  ... --run     # standalone + both halves + blend + turnover vs 07-22c
  ... --fence   # capacity/cost recut at AUM
  ... --selftest
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from .common import OUT_DIR, eq_symbols, load_series, main_conn, research_conn
from .metrics import index_series

VOL_WIN = 126
ENTER_PCTL = 0.20        # enter the lowest-20% vol
HOLD_PCTL = 0.40         # keep until a name leaves the lowest-40% (hysteresis)
REBAL = 3                # re-select every 3 months (quarterly)
LIQ = 5e7
MIN_CLOSE = 20.0
WARMUP = 126
START = "2012-06"
COST_SIDE = 0.0015
RF = 0.06 / 12.0


def _scan(mc):
    """Per month: list of (symbol, vol_ann, next_month_return, med_turn, sigma_daily) for eligibles."""
    syms = eq_symbols(mc)
    per_month = {}
    n = 0
    for sym in syms:
        n += 1
        S = load_series(mc, sym)
        if S is None or S.n < WARMUP + 25:
            continue
        ac = S.adj_close
        ret = np.full(S.n, np.nan)
        ret[1:] = ac[1:] / ac[:-1] - 1.0
        me = {}
        for i, dt in enumerate(S.date):
            me[dt[:7]] = i
        ms = sorted(me)
        for mi, mo in enumerate(ms):
            if mo < START or mi + 1 >= len(ms):
                continue
            i = me[mo]
            if i < WARMUP or not (S.med_turn[i] >= LIQ and S.close[i] >= MIN_CLOSE):
                continue
            r = ret[i - VOL_WIN + 1:i + 1]
            r = r[~np.isnan(r)]
            if len(r) < 100:
                continue
            j = me[ms[mi + 1]]
            if ac[i] <= 0 or ac[j] <= 0:
                continue
            per_month.setdefault(mo, []).append((sym, float(r.std() * np.sqrt(252)),
                                                 float(ac[j] / ac[i] - 1.0), float(S.med_turn[i]), float(r.std())))
        if n % 800 == 0:
            print(f"  …{n}/{len(syms)} symbols", flush=True)
    return per_month


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn(); rc = research_conn()
    rc.executescript("DROP TABLE IF EXISTS lowvolq_book; "
                     "CREATE TABLE lowvolq_book(month TEXT, gross REAL, net REAL, n INT); "
                     "DROP TABLE IF EXISTS lowvolq_holdings; "
                     "CREATE TABLE lowvolq_holdings(month TEXT, symbol TEXT, med_turn REAL, sigma_daily REAL);")
    per_month = _scan(mc)
    months = sorted(per_month)
    rows = []; hold_rows = []
    held = set(); prev_rebal = set(); turns = []
    for k, mo in enumerate(months):
        cross = {x[0]: x for x in per_month[mo]}
        rebal_cost = 0.0
        if (k % REBAL == 0) or not held:
            elig = sorted(per_month[mo], key=lambda x: x[1])   # lowest vol first
            if len(elig) >= 25:
                enter = {x[0] for x in elig[:max(1, int(len(elig) * ENTER_PCTL))]}
                band = {x[0] for x in elig[:max(1, int(len(elig) * HOLD_PCTL))]}
                newheld = set(enter) | {s for s in held if s in band}
                to = len(newheld - prev_rebal) / len(newheld) if prev_rebal else 1.0
                turns.append(to)
                rebal_cost = to * 2 * COST_SIDE
                held = newheld; prev_rebal = set(newheld)
                for s in held:
                    if s in cross:
                        hold_rows.append((mo, s, float(cross[s][3]), float(cross[s][4])))
        rr = [cross[s][2] for s in held if s in cross]
        if rr:
            gross = float(np.mean(rr))
            rows.append((mo, gross, gross - rebal_cost, int(len(rr))))
    rc.executemany("INSERT INTO lowvolq_book VALUES (?,?,?,?)", rows)
    rc.executemany("INSERT INTO lowvolq_holdings VALUES (?,?,?,?)", hold_rows)
    rc.commit(); rc.close(); mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"LOWVOLQ build: {len(rows)} months, avg {int(np.mean([r[3] for r in rows]))} names, "
          f"quarterly one-way turnover {np.mean(turns)*100:.0f}%/qtr ({np.mean(turns)*4*100:.0f}%/yr) in {dt:.0f}s")


def _st(months, x, lo=None, hi=None):
    idx = [k for k, m in enumerate(months) if (lo is None or m >= lo) and (hi is None or m < hi)]
    x = np.asarray(x, float)[idx]
    eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1)
    return (round(float(x.mean() / x.std() * 12 ** .5), 2), round((float(eq[-1]) ** (12 / len(x)) - 1) * 100, 1), round(float(dd.min()) * 100, 1))


def run():
    rc = research_conn()
    lv = {m: net for m, g, net, n in rc.execute("SELECT month,gross,net,n FROM lowvolq_book")}
    mom = {m: r for m, r in rc.execute("SELECT month,mret FROM mbr_book WHERE key='CELL_B_TREND_STRONG' AND gross_net='net'")}
    rc.close()
    d, c = index_series("Nifty 500"); me = {}
    for dt, cl in zip(d, c): me[dt[:7]] = cl
    allm = sorted(me); iret = {allm[i]: me[allm[i]] / me[allm[i - 1]] - 1 for i in range(1, len(allm))}
    months = sorted(set(lv) & set(mom) & set(iret))
    lvr = np.array([lv[m] for m in months]); mr = np.array([mom[m] for m in months]); ir = np.array([iret[m] for m in months])
    b46 = 0.4 * mr + 0.6 * lvr
    corr = float(np.corrcoef(lvr, mr)[0, 1])
    out = {"months": len(months), "corr_lowvolq_vs_momstack": round(corr, 3),
           "lowvolq_sleeve": {"full": _st(months, lvr), "h1": _st(months, lvr, None, "2019"), "h2": _st(months, lvr, "2019", None)},
           "blend40_60": {"full": _st(months, b46), "h1": _st(months, b46, None, "2019"), "h2": _st(months, b46, "2019", None)},
           "index": {"full": _st(months, ir)}}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lowvol_sleeve_q.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


def fence():
    from .cost_participation import side_costs
    rc = research_conn()
    book = [(m, g) for m, g, net, n in rc.execute("SELECT month,gross,net,n FROM lowvolq_book ORDER BY month")]
    H = {}
    for mo, sym, mt, sig in rc.execute("SELECT month,symbol,med_turn,sigma_daily FROM lowvolq_holdings ORDER BY month"):
        H.setdefault(mo, []).append((sym, mt, sig))
    rc.close()
    bmonths = [m for m, g in book]; gross = {m: g for m, g in book}
    snaps = set(H)
    all_liq = np.array([s[1] for mo in H for s in H[mo]], float)
    med_adv = float(np.median(all_liq)); n_avg = float(np.mean([len(H[mo]) for mo in H]))

    def stt(x):
        x = np.asarray(x, float); eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1)
        return round(x.mean() / x.std() * 12 ** .5, 2), round((eq[-1] ** (12 / len(x)) - 1) * 100, 1), round(dd.min() * 100, 1)

    def netseries(aum):
        prev = {}; r = []
        for m in bmonths:
            g = gross[m]; cost = 0.0
            if m in snaps:
                cur = {s[0]: (s[1], s[2]) for s in H[m]}; N = len(cur); w = 1.0 / N
                if aum > 0:
                    for sym, (mt, sig) in cur.items():
                        if sym not in prev:
                            fx, im, _ = side_costs(mt, sig, w * aum); cost += w * (fx + im)
                    for sym, (mt, sig) in prev.items():
                        if sym not in cur:
                            fx, im, _ = side_costs(mt, sig, w * aum); cost += w * (fx + im)
                prev = cur
            r.append(g - cost)
        return np.array(r)

    print("=== LOW-VOL SLEEVE v2 (quarterly + hysteresis) — CAPACITY/COST FENCE ===")
    print(f"avg {n_avg:.0f} names | median held ADV ₹{med_adv/1e7:.1f}cr | 10th-pct ADV ₹{np.percentile(all_liq,10)/1e7:.1f}cr")
    print(f"{'AUM':<13}{'R/V':>6}{'CAGR%':>7}{'MaxDD%':>8}   soft-capacity(10%ADV x N)")
    for label, aum in [("frictionless", 0), ("Rs25cr", 25e7), ("Rs50cr", 50e7), ("Rs100cr", 100e7), ("Rs250cr", 250e7), ("Rs500cr", 500e7)]:
        rv, cg, dd = stt(netseries(aum))
        print(f"{label:<13}{rv:>6.2f}{cg:>7.1f}{dd:>8.1f}   ₹{0.10*med_adv*n_avg/1e7:.0f}cr")


def selftest():
    # hysteresis keeps an incumbent that sits between the enter and hold bands
    elig = [(f"S{i}", i, 0, 0, 0) for i in range(100)]   # vol = i (sorted asc)
    enter = {x[0] for x in elig[:20]}; band = {x[0] for x in elig[:40]}
    held = {"S30"}                                       # incumbent at rank 30: outside enter(20) but in band(40)
    newheld = set(enter) | {s for s in held if s in band}
    assert "S30" in newheld and "S30" not in enter, "hysteresis must keep the in-band incumbent"
    held2 = {"S55"}                                      # rank 55: outside the hold band -> dropped
    newheld2 = set(enter) | {s for s in held2 if s in band}
    assert "S55" not in newheld2, "a name past the hold band is dropped"
    print("LOWVOL_SLEEVE_Q selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--build" in sys.argv:
        build()
    elif "--run" in sys.argv:
        run()
    elif "--fence" in sys.argv:
        fence()
    else:
        print(__doc__)
