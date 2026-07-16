"""Long-only POSITIONAL portfolio backtest — the right test for a cash-market investor.

Not a trading system (no churn/short). A monthly-rebalanced, fully-invested, equal-weight
basket of the strongest names, held for the month, optionally stepping to CASH when Nifty is
below its 200-DMA (a long-only trend-timing overlay to cut drawdowns). Compared apples-to-apples
(monthly frequency) against buy-and-hold Nifty / Nifty 500 / Midcap.

Selection variants:
  MOM      : top-N liquid by 6-month return (classic momentum factor)
  LAUNCH   : top-N liquid that are ALSO in a Launchpad setup, ranked by 6-month return
Each run with regime overlay OFF (always invested) and ON (cash when Nifty<200DMA).
Costs charged on monthly turnover. Survivorship-safe (universe from the raw archive each month).

equity_stats_m() emits mean/sd annualised under the `retvol` key with NO risk-free rate
subtracted — a return/vol ratio, not a Sharpe, and it reads high against a textbook one;
every consumer inherits that. A true Sharpe needs a primary-source rf ingest (Guardrail #8),
queued with the TR-benchmark re-cut. (D142)
"""
from __future__ import annotations
import numpy as np
from .embase import load_symbol_cache, market_regime, _roll_mean
from .strategies import build_strategies, CR
from .metrics import index_series

REBAL = 22                     # trading days between rebalances (~1 month)
COST_PS = 0.003                # per-side cost for liquid names (spread+fees), on turnover
TD_Y = 12                      # monthly periods/year


def _date2idx(A):
    return {d: i for i, d in enumerate(A["date"])}


def equity_stats_m(eq):
    eq = np.asarray(eq, float)
    ret = eq[1:] / eq[:-1] - 1.0
    peak = np.maximum.accumulate(eq); dd = eq / peak - 1.0
    yrs = len(eq) / TD_Y
    cagr = (eq[-1] / eq[0]) ** (1 / max(yrs, 1e-9)) - 1
    sd = ret.std()
    return {"cagr": cagr, "maxdd": float(dd.min()),
            "calmar": cagr / abs(dd.min()) if dd.min() < 0 else 0,
            "retvol": float(ret.mean() / sd * np.sqrt(TD_Y)) if sd > 0 else 0,
            "totx": eq[-1] / eq[0]}


def run(cache, regime_close, regime_ma, cal, rebal_idx, floor, topn, mode, use_regime, params):
    S = build_strategies()
    st = S["S1"]
    # precompute per-symbol maps + masks
    info = {}
    for sym, A in cache.items():
        info[sym] = (_date2idx(A), A["adj_close"], A["med_turn"], A["feats"],
                     st.entry_mask(A["feats"], params) if mode == "LAUNCH" else None)
    eq = [1.0]
    held = set()
    inmkt_frac = 0
    for r in range(len(rebal_idx) - 1):
        d0, d1 = cal[rebal_idx[r]], cal[rebal_idx[r + 1]]
        regime_ok = (not use_regime) or (regime_close[rebal_idx[r]] > regime_ma[rebal_idx[r]])
        if not regime_ok:
            # to cash: pay exit cost on whatever we held, hold cash this period
            if held:
                eq.append(eq[-1] * (1 - COST_PS * 1.0))
                held = set()
            else:
                eq.append(eq[-1])
            continue
        # rank eligible names
        cands = []
        for sym, (d2i, ac, mt, F, mask) in info.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 >= len(ac):
                continue
            if not (mt[i0] >= floor):
                continue
            r66 = F["ret_66d"][i0]
            if r66 != r66:
                continue
            if mode == "LAUNCH" and not mask[i0]:
                continue
            cands.append((r66, sym, i0))
        cands.sort(reverse=True)
        pick = cands[:topn]
        newset = set(s for _, s, _ in pick)
        # period return = equal-weight mean of constituent forward returns to d1
        rets = []
        for _, sym, i0 in pick:
            d2i, ac = info[sym][0], info[sym][1]
            i1 = d2i.get(d1)
            if i1 is None:                                  # delisted/suspended mid-period
                i1 = min(i0 + REBAL, len(ac) - 1)           # use last available ~ a month out
            if ac[i0] > 0 and ac[i1] > 0:
                rets.append(ac[i1] / ac[i0] - 1.0)
        if not rets:
            eq.append(eq[-1]); continue
        gross = float(np.mean(rets))
        turn = (len(newset - held) + len(held - newset)) / max(len(newset), 1)
        cost = COST_PS * turn                               # one-way turnover cost approx
        eq.append(eq[-1] * (1 + gross - cost))
        held = newset
        inmkt_frac += 1
    return eq, inmkt_frac / max(len(rebal_idx) - 1, 1)


def main():
    cache = load_symbol_cache()
    dts, cl = index_series("Nifty 50")
    ma200 = _roll_mean(cl, 200)
    # calendar restricted to study period
    cal = [d for d in dts if d >= "2012-06-01"]
    off = len(dts) - len(cal)
    rc = cl[off:]; rma = ma200[off:]
    rebal_idx = list(range(0, len(cal), REBAL))
    params = build_strategies()["S1"].params

    print("Long-only POSITIONAL backtest (monthly rebalance, equal-weight, net of turnover cost)")
    print(f"window {cal[0]}..{cal[-1]}, {len(rebal_idx)} rebalances\n")

    # baselines at monthly frequency
    print("BASELINES (buy & hold, monthly marks):")
    for idx in ("Nifty 50", "Nifty 500", "Nifty Midcap 50"):
        di, ci = index_series(idx)
        m = {d: ci[i] for i, d in enumerate(di)}
        eqb = [m[cal[rebal_idx[k]]] for k in range(len(rebal_idx)) if cal[rebal_idx[k]] in m]
        if len(eqb) > 2:
            s = equity_stats_m(np.array(eqb) / eqb[0])
            print(f"  {idx:16s} CAGR={s['cagr']*100:+6.1f}% MaxDD={s['maxdd']*100:6.1f}% "
                  f"Calmar={s['calmar']:5.2f} ret/vol={s['retvol']:5.2f} tot={s['totx']:.1f}x")

    print("\nSTRATEGIES:")
    for mode in ("MOM", "LAUNCH"):
        for floor, ftag in ((5 * CR, "5cr+"), (25 * CR, "25cr+")):
            for use_reg in (False, True):
                for topn in (20,):
                    eq, frac = run(cache, rc, rma, cal, rebal_idx, floor, topn, mode, use_reg, params)
                    s = equity_stats_m(eq)
                    rtag = "regime" if use_reg else "always"
                    print(f"  {mode:6s} {ftag:5s} N={topn} {rtag:6s}: CAGR={s['cagr']*100:+6.1f}% "
                          f"MaxDD={s['maxdd']*100:6.1f}% Calmar={s['calmar']:5.2f} ret/vol={s['retvol']:5.2f} "
                          f"tot={s['totx']:5.1f}x  invested={frac*100:.0f}%")


if __name__ == "__main__":
    main()
