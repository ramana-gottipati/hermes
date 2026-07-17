"""Cost realism v2 — participation-rate market-impact, sized by AUM.

Settles institutional-panel gap #4 (docs/institutional-panel-assessment.md):

  "Cost is a DECISION VARIABLE, not a fixed haircut. The flat 0.5xATR assumes
   naive market orders and OVER-penalizes the fundable form; real desks use
   VWAP / participation <=10% ADV. Re-run quarterly large-cap LOWVOL_MOM at
   Rs50 / Rs200 / Rs500cr. PM prior: ~1.0 net Sharpe at Rs50cr only."

WHAT CHANGES vs cost_realism.py
-------------------------------
cost_realism.py charged a FLAT per-name slippage of 0.5 x ATR%(entry), i.e. it
implicitly assumes every position is a single naive marketable order that pays
half a day's range regardless of how big or small the fill is. That is a
worst-case market-order proxy and is AUM-blind: a Rs1cr clip and a Rs50cr clip
pay the same %. A real desk works the order via VWAP/POV at a capped
participation rate, so impact SCALES with the order's footprint in the name's
ADV. We replace the flat term with a square-root participation-impact model and
SIZE every position against a target AUM so impact is charged on the real clip.

PER-NAME ROUND-TRIP COST (fraction of position value)
-----------------------------------------------------
  rt_cost(name) = 2 * [ half_spread(tier) + fees_ps(tier) + impact_ps(name) ]
where the factor 2 is the round trip (enter + exit), and per SIDE:

  half_spread(tier) = COST_TIERS[tier]["spread_rt"] / 2      (catalog spread)
  fees_ps(tier)     = COST_TIERS[tier]["fees_ps"]            (STT+brk+GST+stamp)
  impact_ps(name)   = k * sigma_daily * sqrt(order_value / ADV)      [Almgren sqrt-law]

  k          = 0.6   (impact coefficient; institutional VWAP/POV calibration.
                      Almgren/BARRA temporary-impact constants land ~0.3-1.0 for
                      sigma in daily units and participation as order/ADV. 0.6 is
                      a mid, deliberately conservative for an Indian mid/large-cap
                      book worked at <=10% POV. State it; sweep it below.)
  sigma_daily = per-name daily return vol = vol_66 (66d close-to-close stdev,
                already in embase feats; the SAME vol that drives the LOWVOL tilt).
  order_value = target position value at this AUM = AUM / TOPN (equal weight).
  ADV         = point-in-time trailing-22d median TURNOVER (Rs) = med_turn[i0].

TIERS / SPREAD ASSUMPTIONS (unchanged, from strategies.COST_TIERS)
  T3 25cr+ : spread_rt 0.25%  fees 0.10%/side   (large-cap, top liquidity)
  T2 5-25cr: spread_rt 0.60%  fees 0.12%/side
  T1 1-5cr : spread_rt 1.50%  fees 0.15%/side
Large-cap top-quintile gate means almost all picks sit in T3/T2, so the spread
term is small and IMPACT is the AUM-sensitive lever — exactly gap #4's point.

DAYS-TO-FILL CAP at <=10% ADV/day
  A desk cannot exceed ~10% of ADV/day without moving the market. We cap daily
  participation at POV_CAP=10% and compute days_to_fill = ceil(order/(POV*ADV)).
  When a position needs >1 day the participation model would UNDER-count impact
  (you spread the same clip over more days), so per institutional practice we
  (a) charge the sqrt-impact at the CAPPED 10% participation rate (not the raw
  order/ADV ratio, which could exceed 1.0 for oversized clips), and (b) apply a
  DELAY / timing-risk penalty of 0.5 * sigma_daily * sqrt(days_to_fill - 1) for
  the multi-day names (implementation shortfall from holding unexecuted inventory
  across days). This makes oversized positions in thin names pay for the days
  they take to build, which is precisely where capacity dies.

  Effective participation used in the sqrt term:
     part = min(order_value / ADV, POV_CAP)
     impact_ps = k * sigma * sqrt(part) + (delay penalty if days_to_fill > 1)

CAPACITY READ
  median_position_capacity(AUM) = the AUM at which the MEDIAN pick's equal-weight
  clip = 10% of its ADV = 10% * ADV_median * TOPN. Reported per config.

RATIOS ARE RETURN/VOL, NOT SHARPE (D142)
  Every ratio here — including the BENCH_RETVOL 0.89 index hurdle, computed on the
  SAME basis — is mean/sd annualised with NO risk-free rate subtracted, so it reads
  high against a textbook Sharpe while the beats-index verdicts stay valid.

STRATEGY (as specified): QUARTERLY rebalance, LARGE-CAP (top-quintile liquidity
gate, gate_pctl=0.80), WIDE hold-band (BAND=35), signal = LOWVOL_MOM
(0.5*rank(mom6) + 0.5*rank(-vol)), long-only equal-weight top-25.

Read-only (price cache + index_rows only). No writes to shared files, no git.
Run on VPS:  PYTHONPATH=/opt/hermes /opt/hermes/.venv-research/bin/python \
             -m explosive_moves.cost_participation
Writes out/cost_participation.csv.
"""
from __future__ import annotations
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, "/opt/hermes")
sys.path.insert(0, "/opt/hermes/research")

from explosive_moves.embase import load_symbol_cache
from explosive_moves.metrics import index_series
from explosive_moves.factory import pctrank
from explosive_moves.strategies import COST_TIERS, tier_for_turnover

# --- strategy shape (the fundable corner from cost_realism.py) ---
REBAL_M = 22                 # ~1 trading month
REBAL = 3 * REBAL_M          # QUARTERLY
TOPN = 25                    # long-only, equal-weight
BAND = 35                    # WIDE hold-band (keep a name until it drops out of top-35)
GATE_PCTL = 0.80             # LARGE-CAP = top-quintile liquidity
PPY = 4                      # quarterly periods per year
RF_PP = 1.065 ** (1.0 / PPY) - 1.0   # D142 re-cut (16AY): per-period rf, flat 6.5%/yr estate proxy
BENCH_RETVOL_EX = None               # set in main() from the in-run excess-basis bench (16AY)

# --- participation-impact parameters (STATE THESE) ---
K_IMPACT = 0.6               # sqrt-law impact coefficient (VWAP/POV calibration)
POV_CAP = 0.10               # max 10% of ADV/day (days-to-fill cap)
DELAY_K = 0.5                # timing-risk penalty coeff for multi-day fills

# --- AUM scenarios (Rs) ---
CR = 1e7
AUM_SCENARIOS = [("Rs50cr", 50 * CR), ("Rs200cr", 200 * CR), ("Rs500cr", 500 * CR)]

# --- benchmark (Nifty 500 buy & hold), from the ledger ---
BENCH_RETVOL = 0.89
BENCH_CAGR = 0.153


# ------------------------------------------------------------------ cost model
def side_costs(med_turn, sigma_daily, order_value):
    """Return (fixed_ps, impact_ps, days_to_fill) for ONE side of the trade.

    fixed_ps  = half-spread(tier) + fees(tier)          (AUM-independent)
    impact_ps = k*sigma*sqrt(part) + delay-penalty      (AUM/footprint-driven)
    """
    tier = tier_for_turnover(med_turn) or "T1"          # below floor -> most expensive
    c = COST_TIERS[tier]
    fixed_ps = c["spread_rt"] / 2.0 + c["fees_ps"]

    if not (np.isfinite(med_turn) and med_turn > 0):
        return fixed_ps, 0.10, 999                       # untradeable: punish
    if not (np.isfinite(sigma_daily) and sigma_daily > 0):
        sigma_daily = 0.02                               # fallback daily vol

    raw_part = order_value / med_turn                    # order as fraction of ADV
    part = min(raw_part, POV_CAP)                         # capped participation
    days_to_fill = max(1, math.ceil(raw_part / POV_CAP)) # >1 day if oversized

    impact_ps = K_IMPACT * sigma_daily * math.sqrt(part)
    if days_to_fill > 1:                                 # timing risk over the fill horizon
        impact_ps += DELAY_K * sigma_daily * math.sqrt(days_to_fill - 1)
    return fixed_ps, impact_ps, days_to_fill


# ------------------------------------------------------------------ build tables
_CACHE = None
_CAL = None


def _load():
    global _CACHE, _CAL
    if _CACHE is None:
        _CACHE = load_symbol_cache()
        dts, _ = index_series("Nifty 50")
        _CAL = [d for d in dts if d >= "2012-06-01"]
    return _CACHE, _CAL


def build(rebal=REBAL, gate_pctl=GATE_PCTL):
    """Quarterly, large-cap gated rebalance tables with mom6 / vol / ADV per name."""
    cache, cal = _load()
    ridx = list(range(0, len(cal), rebal))
    P = {s: ({d: i for i, d in enumerate(A["date"])}, A["adj_close"], A["med_turn"], A["feats"])
         for s, A in cache.items()}
    tables = []
    for r in range(len(ridx) - 1):
        d0, d1 = cal[ridx[r]], cal[ridx[r + 1]]
        rec = []
        for s, (d2i, ac, mt, F) in P.items():
            i0 = d2i.get(d0)
            if i0 is None or i0 < 130:
                continue
            i1 = d2i.get(d1, min(i0 + rebal, len(ac) - 1))
            if not (ac[i0] > 0 and ac[i1] > 0):
                continue
            mom6 = ac[i0] / ac[i0 - 126] - 1.0
            vol = float(F["vol_66"][i0])                 # daily return vol (sigma)
            if not (np.isfinite(mom6) and np.isfinite(vol) and vol > 0):
                continue
            rec.append({"s": s,
                        "mt": float(mt[i0]) if np.isfinite(mt[i0]) else 0.0,   # ADV (Rs)
                        "sigma": vol,                                          # daily vol
                        "lowvol": -vol, "mom6": mom6,
                        "fwd": ac[i1] / ac[i0] - 1.0})
        if len(rec) < TOPN + 5:
            continue
        tp = pctrank(np.array([x["mt"] for x in rec]))
        g = [x for i, x in enumerate(rec) if tp[i] >= gate_pctl]   # large-cap gate
        m6 = pctrank(np.array([x["mom6"] for x in g]))
        lv = pctrank(np.array([x["lowvol"] for x in g]))
        for k, x in enumerate(g):
            x["lowvolmom_sc"] = 0.5 * lv[k] + 0.5 * m6[k]           # LOWVOL_MOM
        tables.append({"d0": d0, "g": g})
    return tables


# ------------------------------------------------------------------ sim per AUM
def run(tables, aum, scorekey="lowvolmom_sc", band=True):
    """Simulate the LOWVOL_MOM book at a target AUM with participation-impact cost."""
    order_value = aum / TOPN                              # equal-weight clip
    rets, turns, costs, days, adv_of_picks = [], [], [], [], []
    held = {}
    for t in tables:
        g = t["g"]
        ranked = sorted(g, key=lambda x: -x[scorekey])
        if band and held:
            top_band = set(x["s"] for x in ranked[:BAND])
            keep = [x for x in ranked if x["s"] in held and x["s"] in top_band][:TOPN]
            ks = set(x["s"] for x in keep)
            picks = keep + [x for x in ranked if x["s"] not in ks][:TOPN - len(keep)]
        else:
            picks = ranked[:TOPN]
        byname = {x["s"]: x for x in picks}
        pset = set(byname)
        new = pset - set(held)
        exited = set(held) - pset

        gross = float(np.mean([x["fwd"] for x in picks]))

        # charge ONE side (buy) on new entries, ONE side (sell) on exits.
        side_total = 0.0
        dd = []
        for s in new:
            x = byname[s]
            fx, im, dtf = side_costs(x["mt"], x["sigma"], order_value)
            side_total += fx + im
            dd.append(dtf)
        for s in exited:
            if s in held:
                x = held[s]
                fx, im, dtf = side_costs(x["mt"], x["sigma"], order_value)
                side_total += fx + im
                dd.append(dtf)
        # cost as fraction of the WHOLE book this period (side cost on the traded
        # fraction). Each traded name is order_value = 1/TOPN of the book.
        c = side_total / TOPN

        rets.append(gross - c)
        costs.append(c)
        turns.append((len(new) + len(exited)) / TOPN)
        if dd:
            days.append(float(np.median(dd)))
        adv_of_picks += [x["mt"] for x in picks]
        held = byname

    rets = np.array(rets)
    eq = np.cumprod(1 + rets)
    dd_eq = eq / np.maximum.accumulate(eq) - 1
    cagr = eq[-1] ** (PPY / len(rets)) - 1 if len(rets) else 0.0
    retvol = (rets - RF_PP).mean() / (rets - RF_PP).std() * np.sqrt(PPY) if rets.std() > 0 else 0.0  # 16AY excess

    adv_med = float(np.median(adv_of_picks)) if adv_of_picks else 0.0
    # capacity: AUM at which the MEDIAN pick's clip = 10% of its ADV.
    #   order_value = AUM/TOPN <= POV_CAP * ADV_median  ->  AUM <= POV_CAP*ADV_med*TOPN
    cap_med_cr = (POV_CAP * adv_med * TOPN) / CR
    # actual participation of the median pick at THIS aum (sanity):
    med_part = (order_value / adv_med) if adv_med > 0 else float("inf")

    return {
        "retvol": retvol, "cagr": cagr, "maxdd": float(dd_eq.min()),
        "ann_cost_pct": float(np.mean(costs)) * PPY * 100,
        "turn": float(np.mean(turns)),
        "cap_med_cr": cap_med_cr,
        "med_part_pct": med_part * 100,
        "med_days_fill": float(np.median(days)) if days else 1.0,
        "beats_index": bool(retvol > (BENCH_RETVOL_EX if BENCH_RETVOL_EX is not None else BENCH_RETVOL) and cagr > BENCH_CAGR),  # 16AY
    }


def bench_buyhold(tables):
    bdts, bcl = index_series("Nifty 500")
    bc = {d: bcl[i] for i, d in enumerate(bdts)}
    ds = sorted(bc)
    import bisect
    def on(d):
        i = bisect.bisect_right(ds, d) - 1
        return bc[ds[i]] if i >= 0 else None
    rets = []
    for j in range(len(tables) - 1):
        a, b = on(tables[j]["d0"]), on(tables[j + 1]["d0"])
        if a and b:
            rets.append(b / a - 1.0)
    rets = np.array(rets)
    eq = np.cumprod(1 + rets)
    dd = eq / np.maximum.accumulate(eq) - 1
    cagr = eq[-1] ** (PPY / len(rets)) - 1
    return {"retvol": (rets - RF_PP).mean() / (rets - RF_PP).std() * np.sqrt(PPY) if rets.std() > 0 else 0,  # 16AY excess
            "cagr": cagr, "maxdd": float(dd.min()), "ann_cost_pct": 0.0,
            "turn": 0.0, "cap_med_cr": float("inf"), "med_part_pct": 0.0,
            "med_days_fill": 0.0, "beats_index": None}


# ------------------------------------------------------------------ capacity scan
def capacity_breakpoint(tables):
    """Finest AUM (Rs cr) grid at which net return/vol stops beating the index."""
    grid = [25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000]
    last_ok = None
    first_fail = None
    for cr_aum in grid:
        s = run(tables, cr_aum * CR)
        ok = s["retvol"] > (BENCH_RETVOL_EX if BENCH_RETVOL_EX is not None else BENCH_RETVOL) and s["cagr"] > BENCH_CAGR  # 16AY
        if ok:
            last_ok = (cr_aum, s["retvol"], s["cagr"])
        elif first_fail is None:
            first_fail = (cr_aum, s["retvol"], s["cagr"])
    return grid, last_ok, first_fail


def main():
    print("PARTICIPATION-IMPACT COST MODEL — quarterly large-cap LOWVOL_MOM (+wide band)", flush=True)
    print(f"  k={K_IMPACT}  POV_CAP={POV_CAP:.0%}  delay_k={DELAY_K}  "
          f"impact = k*sigma*sqrt(order/ADV), cap {POV_CAP:.0%} ADV/day\n", flush=True)
    print("building quarterly large-cap (top-20% liquidity) tables ...", flush=True)
    tbl = build(rebal=REBAL, gate_pctl=GATE_PCTL)
    print(f"  {len(tbl)} quarterly rebalances\n", flush=True)

    bench = bench_buyhold(tbl)
    global BENCH_RETVOL_EX
    BENCH_RETVOL_EX = bench["retvol"]   # 16AY: the rf-adjusted hurdle, same in-run basis as the books
    print(f"  [bar] excess-basis bench hurdle (in-run) = {BENCH_RETVOL_EX:.3f}  (raw ledger bar {BENCH_RETVOL})", flush=True)

    rows = []
    for tag, aum in AUM_SCENARIOS:
        rows.append((tag, run(tbl, aum)))

    hdr = (f"{'AUM':>8}{'netRetVol':>11}{'netCAGR':>10}{'maxDD':>9}"
           f"{'annCost%':>10}{'turn':>7}{'medFill(d)':>11}{'medPart%':>10}"
           f"{'capMedCr':>10}{'>index?':>9}")
    print("=" * len(hdr))
    print(f"AUM x METRICS  (index hurdle: rf-adj {BENCH_RETVOL_EX:.3f} in-run [raw ledger 0.89] / CAGR ~15.3%, Nifty500 B&H)  [16AY]")
    print("=" * len(hdr))
    print(hdr)
    for tag, s in rows:
        print(f"{tag:>8}{s['retvol']:>11.2f}{s['cagr']*100:>9.1f}%{s['maxdd']*100:>8.1f}%"
              f"{s['ann_cost_pct']:>9.1f}%{s['turn']:>7.2f}{s['med_days_fill']:>11.1f}"
              f"{s['med_part_pct']:>9.1f}%{s['cap_med_cr']:>10.0f}"
              f"{('YES' if s['beats_index'] else 'no'):>9}")
    print(f"{'Nifty500':>8}{bench['retvol']:>11.2f}{bench['cagr']*100:>9.1f}%"
          f"{bench['maxdd']*100:>8.1f}%{0.0:>9.1f}%{0.0:>7.2f}{'-':>11}{'-':>10}{'inf':>10}{'-':>9}")

    # breakpoint scan
    grid, last_ok, first_fail = capacity_breakpoint(tbl)
    print("\nCAPACITY BREAKPOINT SCAN (net return/vol vs index across AUM):")
    for cr_aum in grid:
        s = run(tbl, cr_aum * CR)
        flag = "  <-- last beats index" if last_ok and cr_aum == last_ok[0] else (
               "  <-- first fails" if first_fail and cr_aum == first_fail[0] else "")
        print(f"  Rs{cr_aum:>4}cr : ret/vol {s['retvol']:>5.2f}  CAGR {s['cagr']*100:>5.1f}%"
              f"  cost {s['ann_cost_pct']:>4.1f}%{flag}")
    if last_ok:
        print(f"\n  Highest AUM still beating the index: ~Rs{last_ok[0]}cr "
              f"(return/vol {last_ok[1]:.2f}, CAGR {last_ok[2]*100:.1f}%)")
    if first_fail:
        print(f"  Breakpoint (stops beating index) at: ~Rs{first_fail[0]}cr "
              f"(return/vol {first_fail[1]:.2f}, CAGR {first_fail[2]*100:.1f}%)")
    if not last_ok:
        print("\n  Does NOT beat the index at ANY tested AUM (incl. Rs25cr).")

    # write csv
    out = os.path.join(os.path.dirname(__file__), "out", "cost_participation.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["aum", "net_retvol", "net_cagr_pct", "maxdd_pct", "ann_cost_pct",
                    "avg_turnover", "med_days_to_fill", "med_participation_pct",
                    "cap_median_cr", "beats_index"])
        for tag, s in rows:
            w.writerow([tag, round(s["retvol"], 2), round(s["cagr"] * 100, 1),
                        round(s["maxdd"] * 100, 1), round(s["ann_cost_pct"], 1),
                        round(s["turn"], 2), round(s["med_days_fill"], 1),
                        round(s["med_part_pct"], 1), round(s["cap_med_cr"], 0),
                        s["beats_index"]])
        w.writerow(["Nifty500_BH", round(bench["retvol"], 2), round(bench["cagr"] * 100, 1),
                    round(bench["maxdd"] * 100, 1), 0.0, 0.0, 0.0, 0.0, "inf", ""])
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
