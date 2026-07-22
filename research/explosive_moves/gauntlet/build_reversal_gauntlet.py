# -*- coding: utf-8 -*-
"""Full-book gauntlet test of the DEEPER-oversold RSI-of-RS reversal (sector-relative), 2005-2026.
Reuses the sealed union engine's book+cost mechanics with two toggles:
  TURN_LO       — the RSI-of-RS oversold floor (sealed = 30; deeper = 25/20/15)
  REVERSAL_ONLY — qualify on the TURN leg ALONE (the fresh standalone reversal book) vs the union (TREND OR TURN)
Baseline (TURN_LO=30, REVERSAL_ONLY=False) MUST reproduce sealed K30 (flat 26.4 / net 17.8) = safety gate.
Same per-name Zerodha gauntlet as 16BC."""
import sys
ENGINE = "/opt/hermes/research/explosive_moves/union_ladder_val.py"
orig = open(ENGINE, encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])

# --- patches ---
head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else pername_cost(w, held, d, i) if COST_MODE=='gauntlet' else COST*turn))")
head = head.replace("TURN_LO = 30\nREVERSAL_ONLY = False\n", "")  # guard against double
head = head.replace("def rsi_of_rs_recovery(s, sec, i):",
                    "TURN_LO = 30\nREVERSAL_ONLY = False\ndef rsi_of_rs_recovery(s, sec, i):")
assert "r = prev < 30 and now >= 30" in head, "turn threshold line not found"
head = head.replace("r = prev < 30 and now >= 30", "r = prev < TURN_LO and now >= 30")
assert "if r_ok or b_ok:" in head, "qualify combine line not found"
head = head.replace("if r_ok or b_ok:", "if (b_ok if REVERSAL_ONLY else (r_ok or b_ok)):")

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

def rebuild(turn_lo, rev_only):
    global TURN_LO, REVERSAL_ONLY, _turn_memo
    TURN_LO, REVERSAL_ONLY = turn_lo, rev_only
    _turn_memo = {}
    QUAL["pf1"] = {d: qualify(d, "pf1") for d in rebal_all}
    return sum(len(QUAL["pf1"][d]) for d in rebal_all)/len(rebal_all)   # avg qualifiers/quarter

CFG = dict(fmode="pf1", topn=30, rf_cash=True, weights="drift")   # the K30 book config
def measure(turn_lo, rev_only):
    global COST_MODE, COLLECT, _LOG
    avgq = rebuild(turn_lo, rev_only); r = {"avgq": avgq}
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
            r["invsel"] = sum(o["nsel"])/len(o["nsel"])   # avg names actually held
    return r

VARIANTS = [
    ("UNION baseline TURN<30 (gate)", 30, False),
    ("UNION deeper  TURN<25",         25, False),
    ("UNION deeper  TURN<20",         20, False),
    ("REVERSAL-ONLY TURN<30 (pure 6b book)", 30, True),
    ("REVERSAL-ONLY TURN<25",         25, True),
    ("REVERSAL-ONLY TURN<20",         20, True),
]
print("\n" + "="*108)
print("DEEPER-OVERSOLD RSI-of-RS REVERSAL — full book through the Zerodha gauntlet (2005-2026, K30 config)")
print("="*108)
print("  %-38s%7s%8s%8s%8s%8s%8s%8s" % ("variant", "qual/q", "held", "flat%", "NET%", "1cr->", "maxDD%", "turn/yr"))
base = None
for nm, tl, ro in VARIANTS:
    r = measure(tl, ro)
    tag = ""
    if nm.startswith("UNION baseline"):
        base = r; tag = "  [gate %s]" % ("OK" if abs(r["flat"]-26.4) < 0.7 else "FAIL")
    else:
        tag = "  [dNET %+.1f]" % (r["gauntlet"]-base["gauntlet"])
    print("  %-38s%7.0f%8.1f%8.1f%8.1f%8.2f%8.0f%8.0f%s"
          % (nm, r["avgq"], r["invsel"], r["flat"], r["gauntlet"], r["cr"], r["mdd"], r["turn_yr"], tag))
print("\n  index (same window) ~ +11.7%% net (Rs1cr->9.38cr). 'held' = avg names actually in the book/quarter.")
print("  Reversal-only books hold only what fires (thin); union = TREND OR TURN. Sealed files untouched.")
'''
exec(compile(head + "\n" + DRIVER, "reversal_gauntlet", "exec"), {})
