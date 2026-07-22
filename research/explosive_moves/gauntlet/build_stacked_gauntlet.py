# -*- coding: utf-8 -*-
"""STACKED variant: deeper-oversold RSI-of-RS turn (16BE) x hold-winners-longer band (16BD/K30-HOLD),
on the K30 book, through the same Zerodha gauntlet (2005-2026). Both single levers shown for reference.
Baseline (TURN_LO=30, HOLD_BAND=0) MUST reproduce sealed K30 (flat 26.4 / net 17.8) = safety gate."""
import sys
ENGINE = "/opt/hermes/research/explosive_moves/union_ladder_val.py"
orig = open(ENGINE, encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])

head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else pername_cost(w, held, d, i) if COST_MODE=='gauntlet' else COST*turn))")
head = head.replace("def rsi_of_rs_recovery(s, sec, i):", "TURN_LO = 30\ndef rsi_of_rs_recovery(s, sec, i):")
assert "r = prev < 30 and now >= 30" in head
head = head.replace("r = prev < 30 and now >= 30", "r = prev < TURN_LO and now >= 30")
sel_old = "sel = (hook or sel_a2c)(QUAL[fmode][d], d, i, topn)[:topn]"
assert sel_old in head
head = head.replace(sel_old, "sel = sel_cb(hook, QUAL[fmode][d], d, i, topn, held)")

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
        _LOG.append({"spread": sp, "slip": sl, "z": z,
                     "turn1": 0.5*sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))})
    return sp + sl + z
rb_full = list(rebal_all); PPY = 4.0

# --- hold-band selection (K30-HOLD lever) ---
HOLD_BAND = 0
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

# --- deeper-turn (16BE lever): rebuild QUAL per TURN_LO, cached ---
_qcache = {}
def set_qual(turn_lo):
    global TURN_LO, _turn_memo
    if turn_lo not in _qcache:
        TURN_LO = turn_lo; _turn_memo = {}
        _qcache[turn_lo] = {d: qualify(d, "pf1") for d in rebal_all}
    QUAL["pf1"] = _qcache[turn_lo]

CFG = dict(fmode="pf1", topn=30, rf_cash=True, weights="drift")
def measure(turn_lo, hold_band):
    global HOLD_BAND, COST_MODE, COLLECT, _LOG
    set_qual(turn_lo); HOLD_BAND = hold_band; r = {}
    for mode in ("flat", "gauntlet"):
        COST_MODE = mode; COLLECT = (mode == "gauntlet"); _LOG = []
        o = run5(**CFG); nav = o["navs"]; dts = rb_full[1:len(nav)+1]
        yrs = (_date.fromisoformat(dts[-1]) - _date.fromisoformat(dts[0])).days/365.25
        cg = nav[-1]**(1/yrs) - 1 if nav[-1] > 0 else -1.0
        r[mode] = cg*100
        if mode == "gauntlet":
            r["cr"] = nav[-1]; peak = -1e9; mdd = 0.0
            for v in nav: peak = max(peak, v); mdd = min(mdd, v/peak-1)
            r["mdd"] = mdd*100; nreb = len(_LOG)
            r["turn_yr"] = sum(x["turn1"] for x in _LOG)/nreb*PPY*100
    return r

VARIANTS = [
    ("baseline K30 (gate)",              30, 0),
    ("hold-band<=60 only (K30-HOLD)",    30, 60),
    ("deeper-turn<25 only",              25, 0),
    ("deeper-turn<20 only",              20, 0),
    ("STACKED  turn<25 + hold60",        25, 60),
    ("STACKED  turn<20 + hold60",        20, 60),
]
print("\n" + "="*96)
print("STACKED: deeper-turn (16BE) x hold-band (16BD) on K30 — Zerodha gauntlet, 2005-2026")
print("="*96)
print("  %-32s%8s%8s%9s%8s%9s" % ("variant", "flat%", "NET%", "1cr->", "maxDD%", "turn/yr"))
base = None
for nm, tl, hb in VARIANTS:
    r = measure(tl, hb)
    if nm.startswith("baseline"):
        base = r; tag = "  [gate %s]" % ("OK" if abs(r["flat"]-26.4) < 0.7 else "FAIL")
    else:
        tag = "  [dNET %+.1f  dDD %+.1f]" % (r["gauntlet"]-base["gauntlet"], r["mdd"]-base["mdd"])
    print("  %-32s%8.1f%8.1f%9.2f%8.0f%9.0f%s"
          % (nm, r["flat"], r["gauntlet"], r["cr"], r["mdd"], r["turn_yr"], tag))
print("\n  index (same window) ~ +11.7%% net (Rs1cr->9.38cr). Sealed engine files untouched.")
'''
exec(compile(head + "\n" + DRIVER, "stacked_gauntlet", "exec"), {})
