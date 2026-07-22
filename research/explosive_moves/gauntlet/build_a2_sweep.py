# -*- coding: utf-8 -*-
"""A2-HOLD extended band sweep to confirm the 2x-holdings value (top-80) before sealing. Same gauntlet."""
import sys
from datetime import date as _date

ENGINE = "/opt/hermes/research/explosive_moves/union_ladder_val.py"
orig = open(ENGINE, encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])
head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else pername_cost(w, held, d, i) if COST_MODE=='gauntlet' else COST*turn))")
sel_old = "sel = (hook or sel_a2c)(QUAL[fmode][d], d, i, topn)[:topn]"
sel_new = "sel = sel_cb(hook, QUAL[fmode][d], d, i, topn, held)"
assert sel_old in head, "selection line not found"
head = head.replace(sel_old, sel_new)

DRIVER = r'''
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
        _LOG.append({"spread": sp, "slip": sl, "z": z, "n_new": len(set(w)-set(held)),
                     "turn1": 0.5*sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))})
    return sp + sl + z
rb_full = list(rebal_all); PPY = 4.0

HOLD_BAND = 0; CRASH_FILTER = False
def sel_cb(hook, q, d, i, topn, held):
    ranked = (hook or sel_a2c)(q, d, i, topn)
    if not HOLD_BAND:
        return ranked[:topn]
    band = set(ranked[:HOLD_BAND]); pos = {s: p for p, s in enumerate(ranked)}
    keep = sorted([s for s in held if s in band], key=lambda s: pos[s])
    out = keep[:topn]
    for s in ranked:
        if len(out) >= topn: break
        if s not in out: out.append(s)
    return out[:topn]

def measure(cfg, hb):
    global HOLD_BAND, COST_MODE, COLLECT, _LOG
    HOLD_BAND = hb; r = {}
    for mode in ("flat", "gauntlet"):
        COST_MODE = mode; COLLECT = (mode == "gauntlet"); _LOG = []
        o = run5(**cfg); nav = o["navs"]; dts = rb_full[1:len(nav)+1]
        yrs = (_date.fromisoformat(dts[-1]) - _date.fromisoformat(dts[0])).days/365.25
        cg = nav[-1]**(1/yrs) - 1 if nav[-1] > 0 else -1.0
        r[mode] = cg*100
        if mode == "gauntlet":
            r["cr"] = nav[-1]; peak = -1e9; mdd = 0.0
            for v in nav: peak = max(peak, v); mdd = min(mdd, v/peak-1)
            r["mdd"] = mdd*100; nreb = len(_LOG)
            r["turn_yr"] = sum(x["turn1"] for x in _LOG)/nreb*PPY*100
    return r

print("\n" + "="*84)
print("A2-HOLD extended band sweep (topn=40; 2x holdings = top-80) — SAME Zerodha gauntlet, 2005-2026")
print("="*84)
seal = GATE["A2"][0]
print("  band     flat%  NET%   1cr->   maxDD%  turn/yr   dNET")
base = None
for hb in (0, 60, 70, 80, 90):
    r = measure(BOOKS["A2"], hb)
    if hb == 0:
        base = r; d = "  [seal %s]" % ("OK" if abs(r["flat"]-seal) < 0.7 else "FAIL")
    else:
        d = "  %+.1f%s" % (r["gauntlet"]-base["gauntlet"], "  <- 2x holdings" if hb == 80 else "")
    print("  %-6s  %5.1f  %5.1f  %6.2f   %5.0f   %6.0f%s"
          % (("base" if hb == 0 else "<=%d" % hb), r["flat"], r["gauntlet"], r["cr"], r["mdd"], r["turn_yr"], d))
print("\ndone.")
'''
exec(compile(head + "\n" + DRIVER, "a2_sweep", "exec"), {})
