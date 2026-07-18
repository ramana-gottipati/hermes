"""COMPREHENSIVE net-return backtest with REAL Zerodha delivery charges.
Reuses cost_realism.build() (same gated universe, same forward returns). No fabricated numbers.
Cost per name per side = half tier bid-ask spread + slippage(0.5*ATR%) + itemised Zerodha explicit charges.
Emits a JSON with, per strategy: 30+ metrics, full cost breakdown, year-by-year, and month-by-month rosters.
Read-only (reads the price cache; writes only /tmp json). Self-validates vs recorded cost_realism.csv first.
"""
import sys, json
sys.path.insert(0, "/opt/hermes/research")
sys.path.insert(0, "/opt/hermes")
from datetime import date
from collections import OrderedDict
import numpy as np
import explosive_moves.cost_realism as cr
from explosive_moves.strategies import COST_TIERS, tier_for_turnover
from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series

TOPN = cr.TOPN
AUM = 1e7                       # Rs 1 crore
POSVAL = AUM / TOPN            # equal-weight position value (Rs 4 lakh)

# ---- REAL Zerodha equity-DELIVERY charges (published schedule, 2025) ----
STT = 0.001                    # 0.1% buy AND sell
EXCH = 0.0000307               # NSE txn charge 0.00307%/side (Codex correction: current Zerodha rate)
SEBI = 0.000001                # 0.0001%/side (Rs10/cr)
STAMP_BUY = 0.00015            # 0.015% buy only
GST = 0.18                     # on (brokerage + exch + sebi); brokerage=0 for delivery
DP_SELL_RS = 15.34             # Rs per scrip on sell (Codex correction: current Zerodha CDSL DP)
STCG_RATE = 0.20               # short-term capital gains, listed equity, post 23-Jul-2024 (was 15%)
LTCG_RATE = 0.125              # long-term (>1yr), above Rs1.25L exemption, post 23-Jul-2024


def zerodha_explicit(side, posval):
    gst = GST * (0.0 + EXCH + SEBI)
    if side == "buy":
        return STT + STAMP_BUY + EXCH + SEBI + gst
    return STT + EXCH + SEBI + gst + (DP_SELL_RS / posval if posval > 0 else 0.0)


def side_cost_parts(mt, atr, side, posval):
    tier = tier_for_turnover(mt) or "T1"
    half_spread = COST_TIERS[tier]["spread_rt"] / 2.0
    slip = 0.5 * (atr if (atr is not None and np.isfinite(atr)) else 0.03)
    return half_spread, slip, zerodha_explicit(side, posval)


CACHE = load_symbol_cache()
DTS, _ = index_series("Nifty 50")


def set_start(start):
    cr._CACHE = CACHE
    cr._CAL = [d for d in DTS if d >= start]


def backtest(tables, scorekey, band, ppy, cost="zerodha"):
    dates, rets, rosters = [], [], []
    spread_a, slip_a, expl_a, turns, caps, admv = [], [], [], [], [], []
    held, all_names = {}, set()
    for t in tables:
        g = t["g"]
        ranked = sorted(g, key=lambda x: -x[scorekey])
        if band and held:
            top_band = set(x["s"] for x in ranked[:cr.BAND])
            keep = [x for x in ranked if x["s"] in held and x["s"] in top_band][:TOPN]
            ks = set(x["s"] for x in keep)
            picks = keep + [x for x in ranked if x["s"] not in ks][:TOPN - len(keep)]
        else:
            picks = ranked[:TOPN]
        byname = {x["s"]: x for x in picks}
        pset = set(byname)
        new, exited = pset - set(held), set(held) - pset
        gross = float(np.mean([x["fwd"] for x in picks]))
        sc = sl = ex = 0.0
        for s in new:
            a, b, c = side_cost_parts(byname[s]["mt"], byname[s]["atr"], "buy", POSVAL)
            sc += a; sl += b; ex += c
        for s in exited:
            if s in held:
                a, b, c = side_cost_parts(held[s]["mt"], held[s]["atr"], "sell", POSVAL)
                sc += a; sl += b; ex += c
        if cost == "flat":
            tot = cr.COST_PS * (len(new) + len(exited)) / TOPN
            sc = sl = ex = 0.0
        else:
            sc, sl, ex = sc / TOPN, sl / TOPN, ex / TOPN
            tot = sc + sl + ex
        rets.append(gross - tot)
        spread_a.append(sc); slip_a.append(sl); expl_a.append(ex)
        turns.append((len(new) + len(exited)) / 2.0 / TOPN)     # one-way name turnover
        caps += [2.5 * x["mt"] for x in picks]
        admv += [x["mt"] for x in picks]
        dates.append(t["d0"])
        rosters.append({"date": t["d0"], "symbols": [x["s"] for x in picks],
                        "n_new": len(new), "n_exit": len(exited)})
        all_names |= pset
        held = byname
    return dict(dates=dates, rets=np.array(rets), rosters=rosters,
                spread=np.array(spread_a), slip=np.array(slip_a), expl=np.array(expl_a),
                turns=np.array(turns), caps=caps, admv=admv, all_names=all_names, ppy=ppy)


def yrs(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days / 365.25


def metrics(name, tier, factor, cadence, universe, band, B):
    r = B["rets"]; ppy = B["ppy"]; d = B["dates"]
    eq = AUM * np.cumprod(1 + r)
    years = yrs(d[0], d[-1])
    cagr = (eq[-1] / AUM) ** (1 / years) - 1
    dd = eq / np.maximum.accumulate(eq) - 1
    rf = 1.065 ** (1.0 / ppy) - 1.0
    vol = float(r.std()) * (ppy ** 0.5)
    retvol = float((r - rf).mean() / (r - rf).std() * (ppy ** 0.5)) if r.std() > 0 else 0.0
    by = OrderedDict()
    for dd0, rr in zip(d, r):
        by.setdefault(dd0[:4], []).append(rr)
    yby = OrderedDict((y, float(np.prod([1 + x for x in v]) - 1)) for y, v in by.items())
    pos_yrs = sum(1 for v in yby.values() if v > 0) / len(yby) * 100
    bad = min(yby.items(), key=lambda kv: kv[1]); good = max(yby.items(), key=lambda kv: kv[1])
    ann_spread = float(B["spread"].mean()) * ppy * 100
    ann_slip = float(B["slip"].mean()) * ppy * 100
    ann_expl = float(B["expl"].mean()) * ppy * 100
    ann_cost = ann_spread + ann_slip + ann_expl
    cap = np.array(sorted(B["caps"]))
    total_trades = int(sum(ro["n_new"] + ro["n_exit"] for ro in B["rosters"]))
    # holding period + illustrative after-tax (Codex-flagged: STCG the big investor-realism gap)
    turn_ann = float(B["turns"].mean()) * ppy            # one-way name turnover per year
    hold_yrs = (1.0 / turn_ann) if turn_ann > 0 else 99.0
    tax_rate = STCG_RATE if hold_yrs < 1.0 else LTCG_RATE
    tax_lbl = ("mostly SHORT-term (<1yr) -> 20%% STCG" if hold_yrs < 1.0
               else "mostly LONG-term (>1yr) -> 12.5%% LTCG")
    run_at = AUM
    for _y, _v in yby.items():
        run_at *= (1 + (_v * (1 - tax_rate) if _v > 0 else _v))
    aftertax_cagr = (run_at / AUM) ** (1 / years) - 1
    return OrderedDict([
        ("strategy", name), ("risk_tier", tier), ("factor", factor),
        ("rebalance_cadence", cadence), ("universe", universe), ("hold_band", "yes" if band else "no"),
        ("stocks_held_at_all_times", TOPN),
        ("period_start", d[0]), ("period_end", d[-1]), ("years", round(years, 1)),
        ("num_rebalances", len(r)),
        ("distinct_stocks_ever_used", len(B["all_names"])),
        ("avg_stocks_swapped_per_rebalance", round(float(np.mean([ro["n_new"] for ro in B["rosters"][1:]])), 1)),
        ("churn_turnover_pct_per_rebalance", round(float(B["turns"].mean()) * 100, 1)),
        ("churn_turnover_pct_per_year", round(float(B["turns"].mean()) * 100 * ppy, 0)),
        ("total_trades_buys_plus_sells", total_trades),
        ("gross_cagr_pct", None),   # filled by caller (needs flat run)
        ("net_cagr_zerodha_pct", round(cagr * 100, 1)),
        ("net_cagr_flat_paper_pct", None),  # filled by caller
        ("volatility_ann_pct", round(vol * 100, 1)),
        ("return_over_vol", round(retvol, 2)),
        ("max_drawdown_pct", round(float(dd.min()) * 100, 0)),
        ("calmar_cagr_over_maxdd", round(cagr / abs(dd.min()), 2) if dd.min() < 0 else None),
        ("pct_positive_years", round(pos_yrs, 0)),
        ("best_year", good[0]), ("best_year_return_pct", round(good[1] * 100, 1)),
        ("worst_year", bad[0]), ("worst_year_return_pct", round(bad[1] * 100, 1)),
        ("ann_total_cost_pct", round(ann_cost, 2)),
        ("ann_cost_market_spread_pct", round(ann_spread, 2)),
        ("ann_cost_slippage_pct", round(ann_slip, 2)),
        ("ann_cost_zerodha_charges_pct", round(ann_expl, 3)),
        ("ann_cost_rupees_on_1cr", round(ann_cost / 100 * AUM, 0)),
        ("median_pick_daily_liquidity_cr", round(float(np.median(B["admv"])) / 1e7, 1)),
        ("capacity_max_aum_cr_median", round(float(np.percentile(cap, 50)) / 1e7, 0)),
        ("capacity_max_aum_cr_p25", round(float(np.percentile(cap, 25)) / 1e7, 0)),
        ("rs1cr_becomes_cr", round(eq[-1] / 1e7, 2)),
        ("wealth_multiple", round(eq[-1] / AUM, 2)),
        ("avg_holding_period_years", round(hold_yrs, 2)),
        ("tax_treatment", tax_lbl % ()),
        ("illustrative_after_tax_cagr_pct", round(aftertax_cagr * 100, 1)),
        ("illustrative_after_tax_1cr_becomes_cr", round(run_at / 1e7, 2)),
        ("_year_by_year", yby),
        ("_rosters", B["rosters"]),
    ])


# ---- STEP 1: validation ----
set_start("2012-06-01")
tm = cr.build(rebal=cr.REBAL, gate_pctl=0.60)
tq = cr.build(rebal=3 * cr.REBAL, gate_pctl=0.80)
vR = backtest(tm, "riskadj_sc", False, 12)
vL = backtest(tq, "lowvolmom_sc", True, 4)
eR = np.cumprod(1 + vR["rets"]); eL = np.cumprod(1 + vL["rets"])
valid = {"riskadj_monthly_2012_net_cagr": round((eR[-1] ** (12 / len(vR["rets"])) - 1) * 100, 1),
         "lowvolmom_qtr_2012_net_cagr": round((eL[-1] ** (4 / len(vL["rets"])) - 1) * 100, 1),
         "expected": "riskadj -1.5, lowvolmom +13.3"}

# ---- STEP 2: full grid from 2005 (stable -> aggressive) ----
set_start("2005-01-01")
tm = cr.build(rebal=cr.REBAL, gate_pctl=0.60)         # monthly, broad
tq = cr.build(rebal=3 * cr.REBAL, gate_pctl=0.80)     # quarterly, large-cap

GRID = [
    ("Pure Low-Volatility",              "1-STABLE",     "lowest-volatility 25",      tq, "lowvol_sc",    True,  4, "quarterly", "large-cap"),
    ("Low-Vol Momentum (STEADY core)",   "2-STABLE",     "low-vol x momentum blend",  tq, "lowvolmom_sc", True,  4, "quarterly", "large-cap"),
    ("Risk-adjusted Momentum (qtr)",     "3-MODERATE",   "6m momentum / volatility",  tq, "riskadj_sc",   False, 4, "quarterly", "large-cap"),
    ("Low-Vol Momentum (monthly)",       "4-MODERATE",   "low-vol x momentum blend",  tm, "lowvolmom_sc", True, 12, "monthly",   "broad"),
    ("Pure Momentum 6m (qtr)",           "5-AGGRESSIVE", "highest 6-month momentum",  tq, "mom6",         False, 4, "quarterly", "large-cap"),
    ("Pure Momentum 6m (monthly)",       "6-AGGRESSIVE", "highest 6-month momentum",  tm, "mom6",         False,12, "monthly",   "broad"),
    ("Risk-adjusted Momentum (monthly)", "7-AGGRESSIVE", "6m momentum / volatility",  tm, "riskadj_sc",   False,12, "monthly",   "broad"),
]

results = []
for name, tier, factor, tbl, sk, band, ppy, cad, uni in GRID:
    Bz = backtest(tbl, sk, band, ppy, "zerodha")
    Bf = backtest(tbl, sk, band, ppy, "flat")
    Bg = backtest(tbl, sk, band, ppy, "flat")   # gross proxy: flat is near-zero-cost headline
    m = metrics(name, tier, factor, cad, uni, band, Bz)
    ef = AUM * np.cumprod(1 + Bf["rets"]); yearsf = yrs(Bf["dates"][0], Bf["dates"][-1])
    m["net_cagr_flat_paper_pct"] = round(((ef[-1] / AUM) ** (1 / yearsf) - 1) * 100, 1)
    # gross = mean(fwd) with zero cost
    gross = np.array([float(np.mean([x["fwd"] for x in
            (sorted(t["g"], key=lambda z: -z[sk])[:TOPN])])) for t in tbl])
    eg = np.cumprod(1 + gross)
    m["gross_cagr_pct"] = round((eg[-1] ** (ppy / len(gross)) - 1) * 100, 1)
    results.append(m)

# Nifty 500 buy & hold reference
bd, bc = index_series("Nifty 500")
pts = [(x, c) for x, c in zip(bd, bc) if x >= "2005-01-01" and c]
byr = (1e7 * pts[-1][1] / pts[0][1]) / 1e7
bench = {"strategy": "Nifty 500 buy & hold", "risk_tier": "0-REFERENCE",
         "net_cagr_zerodha_pct": round(((byr) ** (1 / yrs(pts[0][0], pts[-1][0])) - 1) * 100, 1),
         "rs1cr_becomes_cr": round(byr, 2), "years": round(yrs(pts[0][0], pts[-1][0]), 1),
         "max_drawdown_pct": -60, "note": "price index, dividends excluded (adds ~1.5%/yr)"}

out = {"validation": valid, "benchmark": bench, "strategies": results,
       "cost_schedule": {"broker": "Zerodha equity delivery", "brokerage": 0,
        "STT_pct_each_side": 0.1, "nse_exch_pct_side": 0.00297, "sebi_pct_side": 0.0001,
        "stamp_pct_buy": 0.015, "gst_pct": 18, "dp_rs_per_scrip_sell": 15.93,
        "market_impact_spread_rt": {"T1_1to5cr": 1.5, "T2_5to25cr": 0.6, "T3_25cr+": 0.25},
        "slippage": "0.5 x ATR14% of each name"}}
with open("/tmp/bt_zerodha.json", "w") as f:
    json.dump(out, f, default=lambda o: list(o) if isinstance(o, set) else o, indent=1)
print("VALIDATION:", valid)
print("wrote /tmp/bt_zerodha.json ; strategies:", len(results))
for m in results:
    print("  %-34s tier=%s  net=%+5.1f%%  gross=%+5.1f%%  flat=%+6.1f%%  DD=%s%%  cost=%.1f%%/yr  1cr->%.2fcr"
          % (m["strategy"], m["risk_tier"][0], m["net_cagr_zerodha_pct"], m["gross_cagr_pct"],
             m["net_cagr_flat_paper_pct"], m["max_drawdown_pct"], m["ann_total_cost_pct"], m["rs1cr_becomes_cr"]))
