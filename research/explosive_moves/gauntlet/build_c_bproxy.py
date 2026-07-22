# -*- coding: utf-8 -*-
"""C (hold-band) + B-proxy (price-crash filter) on the sealed union engine, judged on the SAME Zerodha gauntlet.
Reuses union_ladder_val.py byte-for-byte; injects two TOGGLED rules at the selection line. OFF/OFF must reproduce
the seals (K30 26.4 / A2 25.5 flat) AND the recorded gauntlet net (K30 17.8 / A2 17.2) — the safety gate.

FROZEN RULES:
  C  (HOLD_BAND=50): keep a currently-held name while it is still ranked <= 50; refill to topn with best newcomers.
  B-proxy (CRASH_FILTER): drop any name with a single-day ADJUSTED-close fall <= -25% in the trailing 63 sessions.
"""
import sys, statistics as _st
from collections import OrderedDict as _OD
from datetime import date as _date

ENGINE = "/opt/hermes/research/explosive_moves/union_ladder_val.py"
orig = open(ENGINE, encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])

# 1) swap flat cost for the per-name Zerodha gauntlet (identical to build_gauntlet.py)
head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else pername_cost(w, held, d, i) if COST_MODE=='gauntlet' else COST*turn))")
# 2) route selection through sel_cb (adds C + B-proxy when their flags are on; identical to baseline when off)
sel_old = "sel = (hook or sel_a2c)(QUAL[fmode][d], d, i, topn)[:topn]"
sel_new = "sel = sel_cb(hook, QUAL[fmode][d], d, i, topn, held)"
assert sel_old in head, "selection line not found — engine changed"
head = head.replace(sel_old, sel_new)

DRIVER = r'''
from datetime import date as _date
# ================= Zerodha per-name cost (verbatim from build_gauntlet.py) =================
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
        _LOG.append({"spread": sp, "slip": sl, "z": z,
                     "n_new": len(set(w)-set(held)),
                     "turn1": 0.5*sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))})
    return sp + sl + z
rb_full = list(rebal_all); PPY = 4.0

# ================= the two frozen rules =================
HOLD_BAND = 0; CRASH_FILTER = False
_crashc = {}; _CRASHLOG = []
def _crashed(s, i):
    k = (s, i)
    if k in _crashc: return _crashc[k]
    dd = sclose.get(s); bad = False
    if dd:
        for j in range(max(1, i-62), i+1):
            a = dd.get(cal[j-1]); b = dd.get(cal[j])
            if a and b and a > 0 and (b/a - 1.0) <= -0.25:
                bad = True; break
    _crashc[k] = bad; return bad
def sel_cb(hook, q, d, i, topn, held):
    if CRASH_FILTER:
        n0 = len(q); q = [s for s in q if not _crashed(s, i)]; _CRASHLOG.append(n0 - len(q))
    ranked = (hook or sel_a2c)(q, d, i, topn)          # full ranked list
    if not HOLD_BAND:
        return ranked[:topn]
    band = set(ranked[:HOLD_BAND]); pos = {s: p for p, s in enumerate(ranked)}
    keep = sorted([s for s in held if s in band], key=lambda s: pos[s])
    out = keep[:topn]
    for s in ranked:
        if len(out) >= topn: break
        if s not in out: out.append(s)
    return out[:topn]

# ================= run baseline / C / C+B / B-only for A2 and K30 =================
def measure(cfg, hb, cf):
    global HOLD_BAND, CRASH_FILTER, COST_MODE, COLLECT, _LOG, _CRASHLOG
    HOLD_BAND, CRASH_FILTER, _CRASHLOG = hb, cf, []
    r = {}
    for mode in ("none", "flat", "gauntlet"):
        COST_MODE = mode; COLLECT = (mode == "gauntlet"); _LOG = []
        o = run5(**cfg); nav = o["navs"]; dts = rb_full[1:len(nav)+1]
        yrs = (_date.fromisoformat(dts[-1]) - _date.fromisoformat(dts[0])).days/365.25
        cg = nav[-1]**(1/yrs) - 1 if nav[-1] > 0 else -1.0
        r[mode] = cg*100
        if mode == "gauntlet":
            r["cr"] = nav[-1]
            peak = -1e9; mdd = 0.0
            for v in nav: peak = max(peak, v); mdd = min(mdd, v/peak-1)
            r["mdd"] = mdd*100
            nreb = len(_LOG)
            r["turn_yr"] = sum(x["turn1"] for x in _LOG)/nreb*PPY*100
            r["cost_yr"] = sum(x["spread"]+x["slip"]+x["z"] for x in _LOG)/nreb*PPY*100
            r["swap"] = sum(x["n_new"] for x in _LOG[1:])/max(1, nreb-1)
            r["ncrash"] = (sum(_CRASHLOG)/len(_CRASHLOG)) if _CRASHLOG else 0.0
    return r

print("\n" + "="*100)
print("HOLD-BAND STRESS TEST — C's gain across band widths (crash filter OFF; SAME Zerodha gauntlet, 2005-2026)")
print("If dNET is stable/monotonic across widenings, C is robust; if it spikes at one band only, it is noise.")
print("="*100)
for k in ("A2", "K30"):
    topn = BOOKS[k]["topn"]; seal = GATE[k][0]
    print("\n==== %s  (topn=%d, sealed flat %.1f) ====" % (k, topn, seal))
    print("  hold-band       widening  flat%  NET%   1cr->   maxDD%  swap/reb   dNET   dDD")
    base = measure(BOOKS[k], 0, False)
    print("  %-14s  %8s  %5.1f  %5.1f  %6.2f   %5.0f   %6.1f      -      -   [seal %s]"
          % ("baseline(=topn)", "-", base["flat"], base["gauntlet"], base["cr"], base["mdd"], base["swap"],
             "OK" if abs(base["flat"]-seal) < 0.7 else "FAIL"))
    for band in (topn+5, topn+10, topn+15, topn+20, topn+30, topn+45):
        r = measure(BOOKS[k], band, False)
        print("  <= %-11d  %8d  %5.1f  %5.1f  %6.2f   %5.0f   %6.1f   %+5.1f  %+5.1f"
              % (band, band-topn, r["flat"], r["gauntlet"], r["cr"], r["mdd"], r["swap"],
                 r["gauntlet"]-base["gauntlet"], r["mdd"]-base["mdd"]))
print("\ndone. (research; sealed files untouched; hold-band is a toggled variant, not a spec change)")
'''

exec(compile(head + "\n" + DRIVER, "union_cb", "exec"), {})
