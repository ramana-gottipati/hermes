# -*- coding: utf-8 -*-
"""Build union_gauntlet.py from the sealed engine: keep ALL logic, swap flat cost for the SAME per-name
Zerodha gauntlet, and emit union_gauntlet.json with the full 42-field record + year-by-year + rosters per book."""
import os
orig = open(r"D:\Hermes\research\explosive_moves\union_ladder_val.py", encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])
head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else pername_cost(w, held, d, i) if COST_MODE=='gauntlet' else COST*turn))")

DRIVER = r'''
# ======================= ZERODHA PER-NAME COST GAUNTLET + full record =======================
import json as _json
from collections import OrderedDict as _OD
from datetime import date as _date

COST_MODE = "flat"; COLLECT = False; _LOG = []
_Z_BUY  = 0.001 + 0.00015 + 0.0000307 + 0.000001 + 0.18*(0.0000307+0.000001)
_Z_SELL = 0.001 +           0.0000307 + 0.000001 + 0.18*(0.0000307+0.000001)
Z_SIDE  = (_Z_BUY + _Z_SELL) / 2.0
_atrc = {}
def _atr_proxy(s, i):
    k = (s, i)
    if k in _atrc: return _atrc[k]
    d0 = sclose.get(s); v = 0.03
    if d0:
        vals = []
        for j in range(max(1, i-19), i+1):
            a = d0.get(cal[j-1]); b = d0.get(cal[j])
            if a and b and a > 0: vals.append(abs(b/a - 1.0))
        if vals: v = sum(vals)/len(vals)
    _atrc[k] = v; return v
def _adv_at(s, ym):
    dd = adv.get(s)
    if not dd: return 0.0
    a = dd.get(ym)
    if a is None:
        prev = [y for y in dd if y <= ym]
        a = dd[max(prev)] if prev else 0.0
    return a or 0.0
def _half_spread(a):
    if a >= 25e7: return 0.00125
    if a >= 5e7:  return 0.0030
    return 0.0075
def pername_cost(w, held, d, i):
    sp = sl = z = 0.0
    for s in set(w) | set(held):
        dw = abs(w.get(s, 0) - held.get(s, 0))
        if dw <= 0: continue
        sp += dw*_half_spread(_adv_at(s, d[:7])); sl += dw*0.5*_atr_proxy(s, i); z += dw*Z_SIDE
    if COLLECT:
        _LOG.append({"date": d, "symbols": sorted(w, key=lambda s:-w.get(s, 0)),
                     "n_new": len(set(w)-set(held)), "n_exit": len(set(held)-set(w)),
                     "spread": sp, "slip": sl, "z": z,
                     "turn1": 0.5*sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))})
    return sp + sl + z

rb_full = list(rebal_all)
PPY = 4.0
RF = 1.065**(1/PPY) - 1

META = {  # book -> (display, risk_tier, factor, universe)
 "U":   ("Union (RS turn OR RS trend)",              "8-UNION",  "RS-turn UNION RS-trend, top-60 EW",        "broad (era-floor)"),
 "B14": ("Union + beta-cap 1.4",                     "9-UNION",  "+ trailing beta <=1.4 at selection, top-60","broad (era-floor)"),
 "C40": ("Union C40 (risk-adj, top-40)",             "10-UNION", "+ RISKADJ rank, top-40",                    "broad (era-floor)"),
 "A2":  ("Union A2-composite (top-40 + sleeve)",     "11-UNION", "composite + rf-cash sleeve, top-40",        "broad (era-floor)"),
 "K30": ("Union COMPOSITE-30 (LEAD)",                "12-UNION", "composite, drift-weight top-30 + sleeve",   "broad (era-floor)"),
}

def record(k, cfg):
    global COST_MODE, COLLECT, _LOG
    cagr = {}; navs_g = dates = log = bnavs = None
    for mode in ("none", "flat", "gauntlet"):
        COST_MODE = mode; COLLECT = (mode == "gauntlet"); _LOG = []
        o = run5(**cfg)
        nav = o["navs"]; dts = rb_full[1:len(nav)+1]
        yrs = (_date.fromisoformat(dts[-1]) - _date.fromisoformat(dts[0])).days/365.25
        cagr[mode] = nav[-1]**(1/yrs) - 1 if nav[-1] > 0 else -1.0
        if mode == "gauntlet":
            navs_g, dates, log, bnavs = nav, dts, list(_LOG), o["bnavs"]
    yrs = (_date.fromisoformat(dates[-1]) - _date.fromisoformat(dates[0])).days/365.25
    rets = [navs_g[0]-1.0] + [navs_g[j]/navs_g[j-1]-1 for j in range(1, len(navs_g))]
    import statistics as _st
    vol = _st.pstdev(rets) * PPY**0.5
    sd = _st.pstdev(rets)
    retvol = ((sum(rets)/len(rets) - RF)/sd * PPY**0.5) if sd else 0.0
    peak = -1e9; mdd = 0.0
    for v in navs_g:
        peak = max(peak, v); mdd = min(mdd, v/peak-1)
    by = _OD()
    for dt, r in zip(dates, rets): by.setdefault(dt[:4], []).append(r)
    yby = _OD()
    for y in sorted(by):
        p = 1.0
        for r in by[y]: p *= (1+r)
        yby[y] = round(p-1, 4)
    posy = sum(1 for v in yby.values() if v > 0)/len(yby)*100
    good = max(yby.items(), key=lambda kv: kv[1]); bad = min(yby.items(), key=lambda kv: kv[1])
    runat = 1.0
    for v in yby.values(): runat *= (1 + (v*0.8 if v > 0 else v))
    at_cagr = runat**(1/yrs) - 1
    nreb = len(log)
    ann_sp = sum(x["spread"] for x in log)/nreb*PPY*100
    ann_sl = sum(x["slip"] for x in log)/nreb*PPY*100
    ann_z = sum(x["z"] for x in log)/nreb*PPY*100
    ann_cost = ann_sp + ann_sl + ann_z
    turn1_yr = sum(x["turn1"] for x in log)/nreb*PPY
    hold = (1/turn1_yr) if turn1_yr > 0 else 99.0
    allnames = set(); tot_trades = 0
    for x in log: allnames |= set(x["symbols"]); tot_trades += x["n_new"] + x["n_exit"]
    recent = log[-8:]
    advs = [_adv_at(s, x["date"][:7]) for x in recent for s in x["symbols"]]
    med_adv = sorted(advs)[len(advs)//2] if advs else 0.0
    topn = cfg["topn"]
    cap_med = med_adv * 0.10 * topn / 1e7
    disp, tier, factor, uni = META[k]
    return _OD([
        ("strategy", disp), ("risk_tier", tier), ("factor", factor),
        ("rebalance_cadence", "quarterly"), ("universe", uni),
        ("hold_band", "trailing-stop 20% + let-winners"),
        ("stocks_held_at_all_times", topn),
        ("period_start", dates[0]), ("period_end", dates[-1]), ("years", round(yrs, 1)),
        ("num_rebalances", nreb), ("distinct_stocks_ever_used", len(allnames)),
        ("avg_stocks_swapped_per_rebalance", round(sum(x["n_new"] for x in log[1:])/max(1, nreb-1), 1)),
        ("churn_turnover_pct_per_rebalance", round(sum(x["n_new"] for x in log[1:])/max(1, nreb-1)/topn*100, 1)),
        ("churn_turnover_pct_per_year", round(sum(x["n_new"] for x in log[1:])/max(1, nreb-1)/topn*100*PPY, 0)),
        ("total_trades_buys_plus_sells", tot_trades),
        ("avg_holding_period_years", round(hold, 2)),
        ("gross_cagr_pct", round(cagr["none"]*100, 1)),
        ("net_cagr_flat_paper_pct", round(cagr["flat"]*100, 1)),
        ("net_cagr_zerodha_pct", round(cagr["gauntlet"]*100, 1)),
        ("illustrative_after_tax_cagr_pct", round(at_cagr*100, 1)),
        ("volatility_ann_pct", round(vol*100, 1)), ("return_over_vol", round(retvol, 2)),
        ("max_drawdown_pct", round(mdd*100, 0)),
        ("calmar_cagr_over_maxdd", round(cagr["gauntlet"]/abs(mdd), 2) if mdd < 0 else None),
        ("pct_positive_years", round(posy, 0)),
        ("best_year", good[0]), ("best_year_return_pct", round(good[1]*100, 1)),
        ("worst_year", bad[0]), ("worst_year_return_pct", round(bad[1]*100, 1)),
        ("ann_total_cost_pct", round(ann_cost, 2)),
        ("ann_cost_market_spread_pct", round(ann_sp, 2)),
        ("ann_cost_slippage_pct", round(ann_sl, 2)),
        ("ann_cost_zerodha_charges_pct", round(ann_z, 3)),
        ("ann_cost_rupees_on_1cr", round(ann_cost/100*1e7, 0)),
        ("tax_treatment", "mostly SHORT-term (<1yr) -> 20% STCG"),
        ("median_pick_daily_liquidity_cr", round(med_adv/1e7, 1)),
        ("capacity_max_aum_cr_median", round(cap_med, 0)),
        ("rs1cr_becomes_cr", round(navs_g[-1], 2)),
        ("illustrative_after_tax_1cr_becomes_cr", round(runat, 2)),
        ("wealth_multiple", round(navs_g[-1], 2)),
        ("_year_by_year", yby),
        ("_rosters", [{"date": x["date"], "symbols": x["symbols"], "n_new": x["n_new"], "n_exit": x["n_exit"]} for x in log]),
        ("_bench_final", bnavs[-1]), ("_bench_years", round(yrs, 1)),
    ])

books = _OD()
for k in ("U", "B14", "C40", "A2", "K30"):
    books[k] = record(k, BOOKS[k])
bf = books["K30"]["_bench_final"]; byr = books["K30"]["_bench_years"]
out = {"strategies": list(books.values()),
       "benchmark": {"strategy": "Nifty 500 buy & hold", "risk_tier": "0-REFERENCE",
                     "net_cagr_zerodha_pct": round((bf**(1/byr)-1)*100, 1),
                     "rs1cr_becomes_cr": round(bf, 2), "years": byr,
                     "note": "PR index, dividends excluded"},
       "validation": {k: {"seal": GATE[k][0], "flat": books[k]["net_cagr_flat_paper_pct"]} for k in books}}
open("/tmp/union_gauntlet.json", "w").write(_json.dumps(out, indent=1))
print("VALIDATION seal vs flat:", {k: (GATE[k][0], books[k]["net_cagr_flat_paper_pct"]) for k in books})
print("wrote /tmp/union_gauntlet.json")
for k in books:
    m = books[k]
    print("  %-34s net=%+5.1f%%  gross=%+5.1f%%  DD=%s%%  cost=%.1f%%/yr  1cr->%.2fcr"
          % (m["strategy"], m["net_cagr_zerodha_pct"], m["gross_cagr_pct"],
             m["max_drawdown_pct"], m["ann_total_cost_pct"], m["rs1cr_becomes_cr"]))
'''
out = os.path.join(os.path.dirname(__file__), "union_gauntlet.py")
open(out, "w", encoding="utf-8").write(head + "\n\n" + DRIVER)
print("wrote", out)
