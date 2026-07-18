# -*- coding: utf-8 -*-
"""Generate union_k30_checks.py: K30 execution-lag check (engine's lagged mode) + AUM ladder
(cost_participation.py square-root participation-impact, sized by AUM). Keeps ALL engine logic."""
import os
orig = open(r"D:\Hermes\research\explosive_moves\union_ladder_val.py", encoding="utf-8").read().split("\n")
cut = next(i for i, l in enumerate(orig) if l.strip() == 'print("=" * 118)')
head = "\n".join(orig[:cut])
head = head.replace(
    "nav *= (1-COST*turn)",
    "nav *= (1 - (0.0 if COST_MODE=='none' else aum_cost(w,held,d,i) if COST_MODE=='aum' "
    "else pername_cost(w,held,d,i) if COST_MODE=='gauntlet' else COST*turn))")

DRIVER = r'''
# ======================= execution-lag + AUM-ladder checks on K30 =======================
from datetime import date as _date
COST_MODE = "flat"; COLLECT2 = False; _DIAG = []; CR = 1e7; AUM = 50*CR
_Z = (0.001+0.00015+0.0000307+0.000001+0.18*(0.0000307+0.000001)
      + 0.001+0.0000307+0.000001+0.18*(0.0000307+0.000001))/2.0
K_IMPACT, POV_CAP, DELAY_K = 0.6, 0.10, 0.5      # cost_participation.py constants

def _adv_at(s, ym):
    dd = adv.get(s)
    if not dd: return 0.0
    a = dd.get(ym)
    if a is None:
        prev = [y for y in dd if y <= ym]; a = dd[max(prev)] if prev else 0.0
    return a or 0.0
def _half_spread(a):
    if a >= 25e7: return 0.00125
    if a >= 5e7:  return 0.0030
    return 0.0075
_atrc = {}
def _atr_proxy(s, i):
    k=(s,i)
    if k in _atrc: return _atrc[k]
    d0=sclose.get(s); v=0.03
    if d0:
        vals=[]
        for j in range(max(1,i-19),i+1):
            a=d0.get(cal[j-1]); b=d0.get(cal[j])
            if a and b and a>0: vals.append(abs(b/a-1.0))
        if vals: v=sum(vals)/len(vals)
    _atrc[k]=v; return v
_sigc = {}
def _sigma66(s, i):
    k=(s,i)
    if k in _sigc: return _sigc[k]
    d0=sclose.get(s); v=0.02
    if d0:
        rs=[]
        for j in range(max(1,i-65),i+1):
            a=d0.get(cal[j-1]); b=d0.get(cal[j])
            if a and b and a>0: rs.append(b/a-1.0)
        if len(rs)>5:
            m=sum(rs)/len(rs); v=(sum((x-m)**2 for x in rs)/len(rs))**0.5
    _sigc[k]=v; return v

def pername_cost(w, held, d, i):    # AUM-blind gauntlet (for the lag check)
    c=0.0
    for s in set(w)|set(held):
        dw=abs(w.get(s,0)-held.get(s,0))
        if dw<=0: continue
        c += dw*(_half_spread(_adv_at(s,d[:7])) + 0.5*_atr_proxy(s,i) + _Z)
    return c

def aum_cost(w, held, d, i):        # AUM-sized square-root participation impact
    cf=0.0
    for s in set(w)|set(held):
        dw=abs(w.get(s,0)-held.get(s,0))
        if dw<=0: continue
        a=_adv_at(s,d[:7]); clip=AUM*dw; hs=_half_spread(a); sig=_sigma66(s,i)
        if a<=0:
            side=hs+_Z+0.10
            if COLLECT2: _DIAG.append((POV_CAP, 999))
        else:
            part=min(clip/a, POV_CAP)
            days=int(clip/(POV_CAP*a)) + (1 if clip % (POV_CAP*a) else 0)
            days=max(days,1)
            impact=K_IMPACT*sig*(part**0.5) + (DELAY_K*sig*((days-1)**0.5) if days>1 else 0.0)
            side=hs+_Z+impact
            if COLLECT2: _DIAG.append((clip/a, days))
        cf += dw*side
    return cf

rb_full = list(rebal_all); PPY=4.0
def _m(navs):
    dts=rb_full[1:len(navs)+1]
    yrs=(_date.fromisoformat(dts[-1])-_date.fromisoformat(dts[0])).days/365.25
    cagr=navs[-1]**(1/yrs)-1 if navs[-1]>0 else -1.0
    peak,mdd=-1e9,0.0
    for v in navs: peak=max(peak,v); mdd=min(mdd,v/peak-1)
    return cagr, navs[-1], mdd, yrs

K30 = BOOKS["K30"]
print("="*92)
print("K30 (COMPOSITE-30) — execution-lag check + AUM ladder.  Reference gauntlet (AUM-blind) = +17.8%")
print("="*92)

print("\n### EXECUTION-LAG CHECK (trade at next session's price instead of signal close) — gauntlet cost")
print("  %-16s %10s %12s %8s" % ("fill", "net CAGR", "Rs1cr->cr", "MaxDD"))
for lag in (False, True):
    COST_MODE="gauntlet"; COLLECT2=False
    o=run5(**{**K30, "lagged": lag})
    c,f,dd,yr=_m(o["navs"])
    print("  %-16s %+9.1f%% %11.2f %7.0f%%" % ("same-bar" if not lag else "next-session (T+1)", c*100, f, dd*100))

print("\n### AUM LADDER (square-root participation impact, 10%% ADV/day cap + days-to-fill penalty)")
print("  %-9s %10s %11s %9s %8s %8s %8s" % ("AUM", "net CAGR", "Rs1cr->cr", "medPart%", "medDays", "%>1day", "MaxDD"))
for label, aum in [("Rs5cr",5*CR),("Rs25cr",25*CR),("Rs50cr",50*CR),("Rs100cr",100*CR),
                   ("Rs200cr",200*CR),("Rs500cr",500*CR),("Rs1000cr",1000*CR)]:
    globals()["AUM"]=aum; COST_MODE="aum"; COLLECT2=True; _DIAG.clear()
    o=run5(**K30)
    c,f,dd,yr=_m(o["navs"])
    parts=sorted(x[0] for x in _DIAG); days=sorted(x[1] for x in _DIAG)
    mp=parts[len(parts)//2]*100; md=days[len(days)//2]
    pc=sum(1 for x in days if x>1)/len(days)*100
    print("  %-9s %+9.1f%% %10.2f %8.1f %8d %7.0f%% %7.0f%%" % (label, c*100, f, mp, md, pc, dd*100))
print("\nNote: participation impact from cost_participation.py (k=0.6, POV_CAP=10%%, sigma=66d vol). Personal")
print("scale = Rs5-50cr; the AUM at which net falls to the index (~11.7%%) is the practical capacity ceiling.")
'''
out = os.path.join(os.path.dirname(__file__), "union_k30_checks.py")
open(out, "w", encoding="utf-8").write(head + "\n\n" + DRIVER)
print("wrote", out)
