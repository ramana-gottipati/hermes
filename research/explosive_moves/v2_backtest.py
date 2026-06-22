"""v2 — layer the improvements onto Risk-Adjusted Momentum and measure each one.

Unified daily engine (25 slots, stop-loss, 0.5%/side cost). Flags:
  score   : 'riskadj' (6m/vol) | 'multi' (0.4 riskadj + 0.3 low-vol + 0.3 delivery)
  exit_top: sell only when a name falls below this rank (buffer; 25=none, 40=buffer)
  vtarget : volatility target (scale exposure down in turbulence) | None
Reports CAGR / MaxDD / Calmar / Sharpe / 2022 & 2025 (the crash years) / turnover.
"""
import numpy as np
from collections import deque
from explosive_moves.embase import load_symbol_cache
from explosive_moves.strategies import CR
from explosive_moves.metrics import index_series

cache = load_symbol_cache()
D2I = {s: {d: i for i, d in enumerate(A["date"])} for s, A in cache.items()}
dts, cl = index_series("Nifty 50")
cal = [d for d in dts if d >= "2012-06-01"]
rebal_idx = list(range(0, len(cal), 22))
rebdates = [cal[r] for r in rebal_idx if cal[r] >= "2019-01-01"]
CPS, N = 0.005, 25


def pr(x):
    r = np.full(len(x), np.nan); m = ~np.isnan(x)
    if m.sum() > 1:
        r[m] = np.argsort(np.argsort(x[m])) / (m.sum() - 1)
    return r


def rankings(score):
    """Per rebalance date -> {sym: rank(1=best)} over eligible >=5cr names."""
    out = {}
    for d0 in [cal[r] for r in rebal_idx]:
        syms, mom6, vol, deliv = [], [], [], []
        for s, A in cache.items():
            i0 = D2I[s].get(d0)
            if i0 is None or i0 < 260:
                continue
            if not (A["med_turn"][i0] >= 5 * CR):
                continue
            m6 = A["adj_close"][i0] / A["adj_close"][i0 - 126] - 1
            v = A["feats"]["vol_66"][i0]
            if m6 != m6 or v != v or v <= 0:
                continue
            syms.append(s); mom6.append(m6); vol.append(v); deliv.append(A["feats"]["deliv_qty_trend"][i0])
        mom6, vol, deliv = np.array(mom6), np.array(vol), np.array(deliv)
        if score == "riskadj":
            sc = mom6 / vol
        else:
            sc = 0.4 * pr(mom6 / vol) + 0.3 * pr(-vol) + 0.3 * pr(deliv)
        order = np.argsort(sc)[::-1]
        out[d0] = {syms[order[k]]: k + 1 for k in range(len(order))}
    return out


def run(score="riskadj", exit_top=25, vtarget=None, use_sl=True, dd_brake=None, brake_floor=0.4):
    rk = rankings(score)
    slots = [None] * N
    daily, gross_hist = [], deque(maxlen=22)
    start_i = cal.index(rebdates[0])
    buys = sells = 0
    eq_run, peak_run = 1.0, 1.0
    for di in range(start_i, len(cal)):
        d = cal[di]
        rets, cost = [], 0.0
        for k, st in enumerate(slots):
            if st is None:
                rets.append(0.0); continue
            idx = D2I[st["sym"]].get(d)
            if idx is None:
                rets.append(0.0); continue
            A = cache[st["sym"]]; lo = A["adj_low"][idx]; hi = A["adj_high"][idx]; c = A["adj_close"][idx]
            if use_sl and lo <= st["sl"]:
                rets.append(st["sl"] / st["prev"] - 1); cost += CPS / N; slots[k] = None; sells += 1; continue
            rets.append(c / st["prev"] - 1); st["prev"] = c; st["peak"] = max(st["peak"], hi)
            g = st["peak"] / st["entry"] - 1
            if g >= 0.15:
                st["sl"] = max(st["sl"], st["entry"])
            if g >= 0.30:
                st["sl"] = max(st["sl"], st["peak"] * 0.80)
        gross = np.mean(rets)
        expo = 1.0
        if vtarget and len(gross_hist) >= 15:
            rv = np.std(gross_hist) * np.sqrt(252)
            expo = min(1.0, max(0.2, vtarget / rv)) if rv > 0 else 1.0
        if dd_brake is not None and (eq_run / peak_run - 1) < -dd_brake:   # de-risk in a drawdown
            expo = min(expo, brake_floor)
        daily.append(expo * gross - cost)
        gross_hist.append(gross)
        if d in rk:                                    # rebalance
            ranks = rk[d]; top = [s for s, r in sorted(ranks.items(), key=lambda x: x[1])[:N]]
            held = {s["sym"]: k for k, s in enumerate(slots) if s}
            for sym, k in held.items():
                if ranks.get(sym, 999) > exit_top:     # buffer: only sell if rank worse than exit_top
                    cost = CPS / N; daily[-1] -= cost; slots[k] = None; sells += 1
            held = {s["sym"] for s in slots if s}
            ni = 0; newcomers = [s for s in top if s not in held]
            for k in range(N):
                if slots[k] is None and ni < len(newcomers):
                    sym = newcomers[ni]; ni += 1; idx = D2I[sym].get(d)
                    if idx is not None:
                        px = float(cache[sym]["adj_close"][idx])
                        slots[k] = {"sym": sym, "entry": px, "prev": px, "peak": px, "sl": px * 0.82}
                        daily[-1] -= CPS / N; buys += 1
        eq_run *= (1 + daily[-1]); peak_run = max(peak_run, eq_run)
    eq = np.cumprod(1 + np.array(daily)); peak = np.maximum.accumulate(eq)
    dd = (eq / peak - 1).min(); yrs = len(eq) / 252
    cagr = eq[-1] ** (1 / yrs) - 1
    rr = np.array(daily); sh = rr.mean() / rr.std() * np.sqrt(252)
    # by-year
    yr = {}
    for i, di in enumerate(range(start_i, len(cal))):
        yr.setdefault(cal[di][:4], []).append(daily[i])
    y22 = np.prod([1 + x for x in yr.get("2022", [0])]) - 1
    y25 = np.prod([1 + x for x in yr.get("2025", [0])]) - 1
    return {"cagr": cagr, "maxdd": dd, "calmar": cagr / abs(dd), "sharpe": sh,
            "totx": eq[-1], "y22": y22, "y25": y25, "trades": buys + sells,
            "daily": np.array(daily), "dates": [cal[di] for di in range(start_i, len(cal))]}


configs = [
    ("BASE  riskadj+buffer, no stop", dict(score="riskadj", exit_top=40, vtarget=None, use_sl=False)),
    ("--- + VOLATILITY TARGET (tame the drawdown) ---", None),
    ("riskadj+buffer + VT0.35", dict(score="riskadj", exit_top=40, vtarget=0.35, use_sl=False)),
    ("riskadj+buffer + VT0.30", dict(score="riskadj", exit_top=40, vtarget=0.30, use_sl=False)),
    ("riskadj+buffer + VT0.25", dict(score="riskadj", exit_top=40, vtarget=0.25, use_sl=False)),
    ("riskadj+buffer + VT0.20", dict(score="riskadj", exit_top=40, vtarget=0.20, use_sl=False)),
    ("--- SMOOTH (multi-factor) for contrast ---", None),
    ("multi+buffer + VT0.20", dict(score="multi", exit_top=40, vtarget=0.20, use_sl=False)),
]
print(f"{'config':34}{'CAGR':>7}{'MaxDD':>8}{'Calmar':>7}{'Sharpe':>7}{'2022':>7}{'2025':>7}{'trades':>7}")
for name, kw in configs:
    if kw is None:
        print(name); continue
    r = run(**kw)
    print(f"{name:34}{r['cagr']*100:>6.1f}%{r['maxdd']*100:>7.1f}%{r['calmar']:>7.2f}{r['sharpe']:>7.2f}"
          f"{r['y22']*100:>6.0f}%{r['y25']*100:>6.0f}%{r['trades']:>7}")

di, ci = index_series("Nifty Midcap 50"); mp = {d: ci[i] for i, d in enumerate(di)}
mb = [mp[d] for d in rebdates if d in mp]; mr = np.array(mb[1:]) / np.array(mb[:-1]) - 1
me = np.cumprod(1 + mr); mpk = np.maximum.accumulate(me); mdd = (me / mpk - 1).min()
print(f"\n{'Nifty Midcap 50 (ref)':34}{(me[-1]**(12/len(me))-1)*100:>6.1f}%{mdd*100:>7.1f}%")
