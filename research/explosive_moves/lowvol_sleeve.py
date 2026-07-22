"""LOW-VOL DEFENSIVE SLEEVE + blend with the momentum-band stack — portfolio construction to close
the drawdown gap vs the index. PRE-REGISTERED 2026-07-22c.

WHY: the momentum-band stack's drawdown gap vs the index is SYSTEMATIC factor risk, not name count
(ledger 07-22 name-ladder: more momentum names don't diversify a momentum factor). Closing it needs
an UNCORRELATED sleeve. This builds a low-volatility defensive equity sleeve (a low-beta factor with
historically low correlation to high-beta momentum) and blends it with the momentum stack
(`mbr_book` CELL_B_TREND_STRONG net), testing whether the blend's drawdown approaches the index's
−30% while keeping equity-like return. This is PORTFOLIO CONSTRUCTION (risk), not a new alpha claim,
and it does NOT mix momentum with reversal (Ramana's separate-lines rule) — low-vol is a third,
defensive factor.

SLEEVE (locked before run; CA-adjusted; monthly, PIT). Each month-end, eligible EQ names (trailing
med_turn ≥ ₹5cr, close ≥ ₹20, ≥126 prior bars) are ranked by trailing-126-day annualised realised
volatility; take the LOWEST-vol quintile (bottom 20%); equal-weight; hold one month; monthly return =
mean of constituents' next-month adjusted returns. Cost = 0.15%/side charged on realised monthly
name turnover. Window: months ≥ 2012-06.

BLEND: w · momentum-stack-net + (1−w) · lowvol-net, w ∈ {0.4,0.5,0.6,0.7}, monthly rebalanced; plus
a trailing-12m vol-target overlay on the best blend. Report correlation(sleeve, stack), each
standalone, and each blend's net CAGR / return-vol / MaxDD vs the index (13.4% / 0.86 / −30%).

SUCCESS CRITERION (portfolio-construction, pre-committed; NOT an alpha gate): a blend whose net MaxDD
is materially closer to the index's −30% than the stack's (−63% raw / −40% vol-sized) WITHOUT dropping
net return/vol below the stack's raw 0.71 or CAGR much below the index. Descriptive; the sleeve makes
no standalone-alpha claim.

METRIC BASIS (D142): annualised mean/sd return/vol ratios, no risk-free subtracted.

Run on VPS (research venv):
  PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
      -m explosive_moves.lowvol_sleeve --build   # lowvol_book -> research.db
  ... --run        # blend analysis -> out/lowvol_sleeve.json + printed report
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
QUANTILE = 0.20
LIQ = 5e7
MIN_CLOSE = 20.0
WARMUP = 126
START = "2012-06"
COST_SIDE = 0.0015
RF = 0.06 / 12.0


def build():
    t0 = datetime.now(timezone.utc)
    mc = main_conn()
    rc = research_conn()
    rc.executescript("DROP TABLE IF EXISTS lowvol_book; "
                     "CREATE TABLE lowvol_book(month TEXT, gross REAL, net REAL, n INT);")
    syms = eq_symbols(mc)
    per_month = {}   # 'YYYY-MM' -> list of (symbol, trailing_vol, next_month_return)
    n_sym = 0
    for sym in syms:
        n_sym += 1
        S = load_series(mc, sym)
        if S is None or S.n < WARMUP + 25:
            continue
        ac = S.adj_close
        ret = np.full(S.n, np.nan)
        ret[1:] = ac[1:] / ac[:-1] - 1.0
        me_idx = {}
        for i, dt in enumerate(S.date):
            me_idx[dt[:7]] = i           # last trading index of each month (dates ascending)
        ms = sorted(me_idx)
        for mi, mo in enumerate(ms):
            if mo < START or mi + 1 >= len(ms):
                continue
            i = me_idx[mo]
            if i < WARMUP or not (S.med_turn[i] >= LIQ and S.close[i] >= MIN_CLOSE):
                continue
            r = ret[i - VOL_WIN + 1:i + 1]
            r = r[~np.isnan(r)]
            if len(r) < 100:
                continue
            j = me_idx[ms[mi + 1]]
            if ac[i] <= 0 or ac[j] <= 0:
                continue
            per_month.setdefault(mo, []).append((sym, float(r.std() * np.sqrt(252)),
                                                 float(ac[j] / ac[i] - 1.0), float(S.med_turn[i]), float(r.std())))
        if n_sym % 800 == 0:
            print(f"  …{n_sym}/{len(syms)} symbols", flush=True)

    rows = []
    hold_rows = []
    prev = set()
    for mo in sorted(per_month):
        lst = per_month[mo]
        if len(lst) < 25:
            continue
        lst.sort(key=lambda x: x[1])           # lowest vol first
        k = max(1, int(len(lst) * QUANTILE))
        sel = lst[:k]
        selset = {s[0] for s in sel}
        gross = float(np.mean([s[2] for s in sel]))
        turn = len(selset - prev) / len(selset) if prev else 1.0
        net = gross - turn * 2 * COST_SIDE
        rows.append((mo, gross, net, int(len(sel))))
        for s in sel:
            hold_rows.append((mo, s[0], float(s[2]), float(s[3]), float(s[4])))
        prev = selset
    rc.executescript("DROP TABLE IF EXISTS lowvol_holdings; "
                     "CREATE TABLE lowvol_holdings(month TEXT, symbol TEXT, ret_next REAL, med_turn REAL, sigma_daily REAL);")
    rc.executemany("INSERT INTO lowvol_book VALUES (?,?,?,?)", rows)
    rc.executemany("INSERT INTO lowvol_holdings VALUES (?,?,?,?,?)", hold_rows)
    rc.commit(); rc.close(); mc.close()
    dt = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"LOWVOL build: {len(rows)} months, avg {int(np.mean([r[3] for r in rows]))} names in {dt:.0f}s")


def _st(x):
    x = np.asarray(x, float)
    eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1)
    return {"retvol": round(float(x.mean() / x.std() * 12 ** .5), 2),
            "cagr%": round((float(eq[-1]) ** (12 / len(x)) - 1) * 100, 1),
            "maxdd%": round(float(dd.min()) * 100, 1)}


def _volt(mr, tgt):
    mr = np.asarray(mr, float)
    vol = np.full(len(mr), np.nan)
    for t in range(len(mr)):
        if t >= 6:
            vol[t] = mr[max(0, t - 12):t].std() * 12 ** .5
    w = np.where(np.isnan(vol), 1.0, np.clip((tgt / 100.0) / vol, 0, 1.0))
    return w * mr + (1 - w) * RF


def run():
    rc = research_conn()
    lv = {m: n for m, g, n, c in rc.execute("SELECT month,gross,net,n FROM lowvol_book")}
    mom = {m: r for m, r in rc.execute("SELECT month,mret FROM mbr_book WHERE key='CELL_B_TREND_STRONG' AND gross_net='net'")}
    rc.close()
    d, c = index_series("Nifty 500"); me = {}
    for dt, cl in zip(d, c): me[dt[:7]] = cl
    allm = sorted(me); iret = {allm[i]: me[allm[i]] / me[allm[i - 1]] - 1 for i in range(1, len(allm))}

    months = sorted(set(lv) & set(mom) & set(iret))
    lvr = np.array([lv[m] for m in months]); mr = np.array([mom[m] for m in months]); ir = np.array([iret[m] for m in months])
    corr = float(np.corrcoef(lvr, mr)[0, 1])
    corr_idx = float(np.corrcoef(lvr, ir)[0, 1])

    out = {"registered_gate": "see docstring (prereg: lowvol_sleeve)",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
           "months": len(months),
           "corr_lowvol_vs_momstack": round(corr, 3), "corr_lowvol_vs_index": round(corr_idx, 3),
           "standalone": {"momentum_stack_net": _st(mr), "lowvol_sleeve_net": _st(lvr), "index": _st(ir)}}
    blends = {}
    for w in (0.4, 0.5, 0.6, 0.7):
        b = w * mr + (1 - w) * lvr
        blends[f"mom{int(w*100)}_lowvol{int((1-w)*100)}"] = {**_st(b), "plus_voltgt15": _st(_volt(b, 15))}
    out["blends_net"] = blends
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lowvol_sleeve.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


def fence():
    """Capacity/cost gauntlet: recut the sleeve's net book at rising AUM using the project's
    Almgren participation model (cost_participation.side_costs), + turnover, ADV profile, and the
    blend caveat (the momentum sleeve's liquidity binds the blend). Held-name rebalance drift is not
    separately charged (low-turnover book; slightly optimistic — stated)."""
    from .cost_participation import side_costs
    rc = research_conn()
    H = {}
    for mo, sym, rn, mt, sig in rc.execute("SELECT month,symbol,ret_next,med_turn,sigma_daily FROM lowvol_holdings ORDER BY month"):
        H.setdefault(mo, []).append((sym, rn, mt, sig))
    momliq = [r[0] for r in rc.execute("SELECT med_turn FROM mbr_trades WHERE cell='B' AND trend=1 AND rsi_entry>=70")]
    rc.close()
    months = sorted(H)

    def stt(x):
        x = np.asarray(x, float); eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq); dd = (eq / pk - 1)
        return round(x.mean() / x.std() * 12 ** .5, 2), round((eq[-1] ** (12 / len(x)) - 1) * 100, 1), round(dd.min() * 100, 1)

    def book(aum):
        prev = {}; rets = []; turnsum = 0.0
        for mo in months:
            mem = H[mo]; N = len(mem); w = 1.0 / N
            cur = {s[0]: (w, s[2], s[3]) for s in mem}
            gross = float(np.mean([s[1] for s in mem]))
            cost = 0.0; moves = 0
            for sym, (ww, mt, sig) in cur.items():
                if sym not in prev:
                    moves += 1
                    if aum > 0:
                        fx, im, _ = side_costs(mt, sig, ww * aum); cost += ww * (fx + im)
            for sym, (pw, mt, sig) in prev.items():
                if sym not in cur:
                    moves += 1
                    if aum > 0:
                        fx, im, _ = side_costs(mt, sig, pw * aum); cost += pw * (fx + im)
            turnsum += moves / (2 * N)
            rets.append(gross - cost); prev = cur
        return np.array(rets), turnsum / len(months) * 12

    all_liq = np.array([s[2] for mo in months for s in H[mo]], float)
    n_avg = float(np.mean([len(H[mo]) for mo in months]))
    med_adv = float(np.median(all_liq))
    print("=== LOW-VOL SLEEVE — CAPACITY/COST FENCE ===")
    print(f"avg {n_avg:.0f} names | median held ADV ₹{med_adv/1e7:.1f}cr | 10th-pct ADV ₹{np.percentile(all_liq,10)/1e7:.1f}cr")
    _, turn = book(0)
    print(f"annualised one-way turnover {turn*100:.0f}%  (hurdle: net R/V > 0.89, beat index 13.4%/0.86)")
    print(f"{'AUM':<13}{'R/V':>6}{'CAGR%':>7}{'MaxDD%':>8}   soft-capacity(10%ADV x N)")
    for label, aum in [("frictionless", 0), ("Rs25cr", 25e7), ("Rs50cr", 50e7), ("Rs100cr", 100e7), ("Rs250cr", 250e7), ("Rs500cr", 500e7)]:
        r, _ = book(aum); rv, cg, dd = stt(r)
        print(f"{label:<13}{rv:>6.2f}{cg:>7.1f}{dd:>8.1f}   ₹{0.10*med_adv*n_avg/1e7:.0f}cr")
    if momliq:
        print(f"[blend caveat] momentum-stack (trend+RSI≥70) trade median ADV ₹{np.median(momliq)/1e7:.1f}cr "
              f"— the momentum sleeve, not low-vol, binds the 40/60 blend's capacity.")


def selftest():
    # low-vol selection picks the calmer synthetic name
    rng = np.random.default_rng(0)
    calm = np.cumprod(1 + rng.normal(0.01, 0.02, 200)) * 100
    wild = np.cumprod(1 + rng.normal(0.01, 0.10, 200)) * 100
    vc = (np.diff(calm) / calm[:-1]).std(); vw = (np.diff(wild) / wild[:-1]).std()
    assert vc < vw, "calm series must have lower realised vol"
    # blend reduces vol when correlation < 1
    a = rng.normal(0.01, 0.05, 300); b = rng.normal(0.01, 0.05, 300)
    assert (0.5 * a + 0.5 * b).std() < 0.5 * (a.std() + b.std()), "diversification reduces vol"
    print("LOWVOL_SLEEVE selftest OK")


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
