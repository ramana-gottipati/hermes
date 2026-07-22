# -*- coding: utf-8 -*-
"""RSI-of-RS reversal — SECTOR-relative vs INDEX-relative denominator (the untested fork).
Reuses dim6.py's proven data-loading + PIT sector assignment + the forward-3m-excess selector
decomposition (so results are directly comparable to the recorded sector-relative 6b), and adds an
INDEX-relative (stock / Nifty 500) version + a few reversal-trigger variants. Read-only research."""
import sys
src = open("/opt/hermes/research/explosive_moves/dim6.py", encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(src) if l.strip() == "res = defaultdict(list)")
head = "\n".join(src[:cut])   # loading + PIT assignment + rs_at(sector) + _rsi_of + i6b(sector) + rebal

TAIL = r'''
# ---------- INDEX-relative RS (the untested fork: stock / Nifty 500) ----------
def rs_at_idx(s, j):
    a, b = sclose[s].get(cal[j]), iclose[BENCH].get(cal[j])
    return a/b if (a and b) else None
def rs_window_idx(s, i, w):
    return [x for x in (rs_at_idx(s, j) for j in range(max(0, i-w), i+1)) if x is not None]
def i6b_idx(s, sec, i):
    """6b reversal but on the stock/INDEX ratio instead of stock/sector"""
    w = rs_window_idx(s, i, 60)
    if len(w) < 40: return False
    now = _rsi_of(w); prev = _rsi_of(w[:-10]) if len(w) > 50 else None
    if now is None or prev is None: return False
    return prev < 30 and now >= 30
def i6b_both(s, sec, i):   return i6b(s, sec, i) and i6b_idx(s, sec, i)
def i6b_either(s, sec, i): return i6b(s, sec, i) or i6b_idx(s, sec, i)
def _thr_sec(lo, hi):
    def f(s, sec, i):
        w = rs_window(s, sec, i, 60)
        if len(w) < 40: return False
        now = _rsi_of(w); prev = _rsi_of(w[:-10]) if len(w) > 50 else None
        if now is None or prev is None: return False
        return prev < lo and now >= hi
    return f

FNS = [
    ("6b SECTOR-relative (baseline = sealed 6b)", i6b),
    ("6b INDEX-relative  stock/Nifty500  [NEW]", i6b_idx),
    ("6b BOTH fire (sector AND index)",           i6b_both),
    ("6b EITHER fires (sector OR index)",         i6b_either),
    ("6b SECTOR thr 25->35 (looser)",             _thr_sec(25, 35)),
    ("6b SECTOR thr 20->30 (deeper)",             _thr_sec(20, 30)),
]

import math as _m
res = {t: [] for t, _ in FNS}; base = []
for d in rebal:
    i = ci[d]; df = cal[i+FWD]; ym = d[:7]
    amap = assign(d)
    bf = iclose[BENCH][df]/iclose[BENCH][d]-1.0
    universe = [(s, sec) for s, sec in amap.items() if adv.get(s, {}).get(ym, 0) >= ADV_BAR]
    if len(universe) < 20: continue
    def fwd(s):
        a, b = sclose[s].get(d), sclose[s].get(df)
        return (b/a-1.0)-bf if (a and b) else None
    for s, sec in universe:
        f = fwd(s)
        if f is not None: base.append(f)
    for tag, fn in FNS:
        for s, sec in universe:
            try:
                if not fn(s, sec, i): continue
            except Exception:
                continue
            f = fwd(s)
            if f is not None: res[tag].append(f)

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    mm = mean(x); return _m.sqrt(sum((v-mm)**2 for v in x)/(len(x)-1)) if len(x) > 1 else float('nan')

print("\n" + "="*104)
print("RSI-OF-RS REVERSAL: SECTOR-relative vs INDEX-relative denominator (forward 3m excess vs Nifty 500)")
print("="*104)
m0, s0 = mean(base), sd(base); se0 = s0/_m.sqrt(len(base))
print("  %-44s%8s%9s%9s%9s%9s" % ("variant", "n", "mean/q", "sd/q", "GEO/q", "vs base"))
print("  %-44s%8d%8.2f%%%8.2f%%%8.2f%%%9s   <- NO-SELECTION baseline (SE +/-%.2f%%)"
      % ("(every liquid stock)", len(base), m0*100, s0*100, (m0-s0*s0/2)*100, "--", se0*100))
for tag, _fn in FNS:
    x = res[tag]
    if len(x) < 30:
        print("  %-44s%8d  too few" % (tag, len(x))); continue
    m, s_ = mean(x), sd(x); geo = m - s_*s_/2; se = s_/_m.sqrt(len(x)); delta = m - m0
    sig = "SIG" if abs(delta) > 2*_m.sqrt(se**2 + se0**2) else "ns"
    print("  %-44s%8d%8.2f%%%8.2f%%%8.2f%%%+8.2f%% %s" % (tag, len(x), m*100, s_*100, geo*100, delta*100, sig))
print("\n  GEO/q = geometric mean (mean - variance/2) — the positive-geometric bar 6b had to clear.")
print("  SIG = beats the no-selection baseline beyond 2 SE of the difference. Selector test, not a full book.")
'''
exec(compile(head + "\n" + TAIL, "rsirs_denom", "exec"), {})
