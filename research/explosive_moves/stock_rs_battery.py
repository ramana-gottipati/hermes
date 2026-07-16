"""STOCK-LEVEL RS BATTERY (Ramana, 2026-07-16). Equal-weight only -- explicitly deprioritizing
inverse-vol/volume this round per his instruction: "focus on the RS crossover first."

TERM MAPPING (stated explicitly so it can be corrected):
  "RS exceeds 1 (neutral baseline)"        <=> a stock/sector RATIO > 1 over a stated window
  "RS crosses 0"                            <=> the EXCESS-RETURN form of the SAME signal
                                                (log/simple excess > 0  <=>  ratio > 1). Implemented
                                                as ONE metric: excess_63d = stock's trailing-quarter
                                                return minus its sector's trailing-quarter return.
  "index moves 100pts, stock should mirror it, we want the residual delta"
                                             <=> the SAME excess_63d (this is literally what "excess
                                                vs sector" has meant all session).
  "closed above this threshold, consistent over the last quarter"
                                             <=> CONSISTENCY: % of trading days in the trailing
                                                quarter where the stock was cumulatively ahead of
                                                its sector since that quarter began.
  "50-day MA of the stock's RS vs its own narrow index, and vs the broader index"
                                             <=> two CONTINUOUS ratio lines (stock/sector,
                                                stock/Nifty500), each with a 50-day EMA, tested as
                                                a CROSSOVER (event) and a STATE (above/below), and
                                                combined four ways: sector-only / broad-only / AND /
                                                OR -- so the choice can be seen, not assumed.

Sector gate = the EMA-cross-entry / 8%-stop-exit mechanism just validated (rs_ema_stop.py). Universe:
bhavcopy EQ+BE+BZ, corporate-action adjusted, TEMPORARILY quarantined (quarantine.py, runtime-only,
nothing written to the DB), liquid >= Rs5cr ADV using the PRIOR month.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
LB, EMA_N, QTR, ADV_BAR, COST, CORRWIN = 126, 50, 63, 5e7, 0.0015, 500
DEAD_VAL, STOP_LVL = -0.50, 0.08

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name,trade_date,close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
sclose = defaultdict(dict)
for s, d, c in conn.execute("SELECT symbol,trade_date,close FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') AND close>0"):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("SELECT symbol,substr(trade_date,1,7),avg(value),count(*) FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"):
    if n >= 15 and a: adv[s][ym] = a
_raw = {sym: dict(d) for sym, d in sclose.items()}
fac = load_factors(conn); nadj = adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()
_q.report(QUAR, _qd, universe_size=len(sclose))

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}

# ---- sector RS line + 50-EMA (for the gate) ----
alpha = 2.0/(EMA_N+1)
rs_line, rs_ema = {}, {}
for nm in SECTORS:
    line = [(iclose[nm].get(d)/iclose[BENCH][d]) if iclose[nm].get(d) else None for d in cal]
    rs_line[nm] = line
    e, warm, ema = None, [], []
    for x in line:
        if x is None: ema.append(e); continue
        if e is None:
            warm.append(x)
            if len(warm) >= EMA_N: e = sum(warm)/len(warm)
            ema.append(e); continue
        e = alpha*x + (1-alpha)*e; ema.append(e)
    rs_ema[nm] = ema

def crossed_up(nm, i, within=20):
    l, e = rs_line[nm], rs_ema[nm]
    if l[i] is None or e[i] is None or l[i] <= e[i]: return False
    return any(l[j] is not None and e[j] is not None and l[j] <= e[j] for j in range(max(0,i-within), i))

def excess6m(nm, i):
    if i-LB < 0: return None
    a,b = iclose[nm].get(cal[i-LB]), iclose[nm].get(cal[i])
    ba,bb = iclose[BENCH].get(cal[i-LB]), iclose[BENCH].get(cal[i])
    if not (a and b and ba and bb): return None
    return (b/a-1.0)-(bb/ba-1.0)

held_sec_state = {}   # rebuilt per simulate() run since it's cheap and path-independent enough here

def qualifying(d, i, held):
    for nm in list(held):
        e = excess6m(nm, i)
        if e is not None and e < STOP_LVL: held.discard(nm)
    for nm in SECTORS:
        if nm not in held and crossed_up(nm, i): held.add(nm)
    return held

rebal = [d for i,d in enumerate(cal) if i>=max(CORRWIN,LB,EMA_N*3) and d[5:7] in ('01','04','07','10') and (i==0 or cal[i-1][5:7]!=d[5:7])]
print(f"[data] {len(rebal)} quarterly dates {rebal[0]} -> {rebal[-1]}", file=sys.stderr)

def pym(d):
    y,m = int(d[:4]), int(d[5:7]); m-=1
    if m==0: y,m=y-1,12
    return "%04d-%02d"%(y,m)

def pxn(s,d,back=10):
    i = ci.get(d)
    if i is None: return None
    for j in range(i, max(-1,i-back), -1):
        v = sclose[s].get(cal[j])
        if v: return v
    return None

def isdead(s,d,fwd=60):
    i = ci.get(d)
    if i is None: return True
    return not any(sclose[s].get(cal[j]) for j in range(i, min(len(cal), i+fwd)))

# ---- stock<->sector assignment (PIT correlation), quarantine-aware, cached per year ----
bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1,len(cal))]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1,len(cal))] for nm in SECTORS}
stock_ex = {}
for s_,cl in sclose.items():
    if s_ in QUAR or len(cl) < 300: continue
    stock_ex[s_] = [((cl.get(cal[i]) or 0)/(cl.get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                    if (cl.get(cal[i]) and cl.get(cal[i-1])) else None for i in range(1,len(cal))]

_am = {}
def sector_of_year(d):
    k = d[:4]
    if k in _am: return _am[k]
    i = ci[d]; lo = max(0,i-CORRWIN); pm = pym(d)
    out = {}
    for s_,ex in stock_ex.items():
        if adv.get(s_,{}).get(pm,0) < ADV_BAR: continue
        best,bc = None,-9.0
        for nm in SECTORS:
            y = sec_ex[nm]
            n=0;a1=a2=a11=a22=a12=0.0
            for t in range(lo+1,i+1):
                x=ex[t-1] if t-1<len(ex) else None; yv=y[t-1] if t-1<len(y) else None
                if x is None or yv is None: continue
                n+=1;a1+=x;a2+=yv;a11+=x*x;a22+=yv*yv;a12+=x*yv
            if n<100: continue
            cx,cy = a11-a1*a1/n, a22-a2*a2/n
            if cx<=0 or cy<=0: continue
            c = (a12-a1*a2/n)/math.sqrt(cx*cy)
            if c>bc: bc,best=c,nm
        if best: out[s_]=best
    _am[k]=out
    return out

# ---- stock RS: raw ratio lines (for EMA crossover) + windowed excess (for the "RS>1/crosses 0"
# ---- and consistency criteria). Computed ON DEMAND per rebalance date to bound memory/CPU. ----
def stock_series_window(s, i, lo):
    """close series for stock s over cal[lo..i], None where missing"""
    return [sclose[s].get(cal[j]) for j in range(lo, i+1)]

def excess_qtr(s, sec, i):
    """excess_63d: stock's trailing-quarter return minus its sector's trailing-quarter return"""
    if i-QTR < 0: return None
    a,b = sclose[s].get(cal[i-QTR]), sclose[s].get(cal[i])
    sa,sb = iclose[sec].get(cal[i-QTR]), iclose[sec].get(cal[i])
    if not (a and b and sa and sb): return None
    return (b/a-1.0)-(sb/sa-1.0)

def consistency(s, sec, i):
    """% of the trailing QTR days where the stock was cumulatively ahead of its sector SINCE the
    quarter began (day-by-day, both indexed to 1.0 at the window start)"""
    lo = i-QTR
    if lo < 0: return None
    a0, b0 = sclose[s].get(cal[lo]), iclose[sec].get(cal[lo])
    if not (a0 and b0): return None
    ahead = tot = 0
    for j in range(lo+1, i+1):
        a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
        if not (a and b): continue
        tot += 1
        if (a/a0) > (b/b0): ahead += 1
    return ahead/tot if tot >= QTR*0.6 else None

def ema_state(closes, refcloses, i, n=EMA_N):
    """does the raw ratio (closes/refcloses) sit above its own n-day EMA at i? and did it cross up
    within the last 20 obs? returns (state, crossed)"""
    lo = max(0, i-n*3)
    line = []
    for j in range(lo, i+1):
        a,b = closes.get(cal[j]), refcloses.get(cal[j])
        line.append(a/b if (a and b) else None)
    a_ = 2.0/(n+1); e=None; warm=[]; ema=[]
    for x in line:
        if x is None: ema.append(e); continue
        if e is None:
            warm.append(x)
            if len(warm)>=n: e=sum(warm)/len(warm)
            ema.append(e); continue
        e = a_*x+(1-a_)*e; ema.append(e)
    li, ei = line[-1], ema[-1]
    if li is None or ei is None: return None, False
    st = li > ei
    crossed = False
    for k in range(max(1,len(line)-20), len(line)):
        if line[k-1] is not None and ema[k-1] is not None:
            if line[k-1] <= ema[k-1] and line[k] is not None and ema[k] is not None and line[k] > ema[k]:
                crossed = True
    return st, crossed

RULES = {}
def rule_excess(pos):     return lambda s,sec,i: (excess_qtr(s,sec,i) or -9) > 0
def rule_consist(th):     return lambda s,sec,i: (excess_qtr(s,sec,i) or -9) > 0 and (consistency(s,sec,i) or 0) >= th
def rule_ema_state_sec():  return lambda s,sec,i: (ema_state(sclose[s], iclose[sec], i)[0] or False)
def rule_ema_cross_sec():  return lambda s,sec,i: ema_state(sclose[s], iclose[sec], i)[1]
def rule_ema_state_broad():return lambda s,sec,i: (ema_state(sclose[s], iclose[BENCH], i)[0] or False)
def rule_ema_and():
    def f(s,sec,i):
        a,_ = ema_state(sclose[s], iclose[sec], i); b,_ = ema_state(sclose[s], iclose[BENCH], i)
        return bool(a) and bool(b)
    return f
def rule_ema_or():
    def f(s,sec,i):
        a,_ = ema_state(sclose[s], iclose[sec], i); b,_ = ema_state(sclose[s], iclose[BENCH], i)
        return bool(a) or bool(b)
    return f

def run(rule, topn=40, trail=None, slip=0.0):
    nav = bnav = 1.0; navs, bnavs = [], []
    held_sec = set(); held_stk, ent, pk = {}, {}, {}
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        i = ci[d]
        qualifying(d, i, held_sec)
        if held_sec:
            amap = sector_of_year(d)
            pm = pym(d)
            cands = []
            for s_, sec in amap.items():
                if sec not in held_sec: continue
                if s_ in QUAR: continue
                if adv.get(s_,{}).get(pm,0) < ADV_BAR: continue
                if not rule(s_, sec, i): continue
                cands.append(s_)
            sel = cands[:topn]
            if sel:
                w = {s: 1.0/len(sel) for s in sel}
                turn = sum(abs(w.get(s,0)-held_stk.get(s,0)) for s in set(w)|set(held_stk))
                nav *= (1-COST*turn)
                for s in w:
                    if s not in held_stk:
                        p = pxn(s,d); ent[s]=p; pk[s]=p or 0
                held_stk = w
        r = 0.0
        for s,x in list(held_stk.items()):
            a,b = pxn(s,d), pxn(s,dn)
            if a and b:
                hit=False
                if trail and ent.get(s):
                    i0,i1 = ci[d],ci[dn]
                    for j in range(i0+1,i1+1):
                        q = sclose[s].get(cal[j])
                        if not q: continue
                        if q>pk.get(s,0): pk[s]=q
                        if q<=pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit=True; break
                if hit: del held_stk[s]; ent.pop(s,None); pk.pop(s,None)
                else: r += x*(b/a-1.0)
            elif a and isdead(s,dn):
                r += x*DEAD_VAL; del held_stk[s]
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs

def stat(navs,bnavs):
    r=[navs[i]/navs[i-1]-1 for i in range(1,len(navs))]
    br=[bnavs[i]/bnavs[i-1]-1 for i in range(1,len(bnavs))]
    n=len(r); y=n/4.0
    def dd(v):
        pk,mx=v[0],0.0
        for x in v: pk=max(pk,x); mx=min(mx,x/pk-1)
        return mx
    m,mb=sum(r)/n,sum(br)/n
    vb=sum((x-mb)**2 for x in br)/(n-1)
    cov=sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b=cov/vb if vb else 0.0
    return navs[-1]**(1/y)-1, dd(navs), navs[-1], b

def go(tag, rule, **kw):
    navs,bnavs = run(rule, **kw)
    c,d_,m,b = stat(navs,bnavs)
    print("  %-52s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%7.2fx  beta %.2f" % (tag,c*100,d_*100,m,b), flush=True)

print("\n"+"="*112)
print("STOCK-LEVEL RS BATTERY — equal-weight only, EMA-cross/8%-stop sector gate, quarantined+adjusted")
print("="*112)
d0,d1 = rebal[0], rebal[-1]; y=(len(rebal)-1)/4.0
b = iclose[BENCH][d1]/iclose[BENCH][d0]
print("  %-52s CAGR %5.1f%%  %25s Rs1Cr->%7.2fx" % ("Nifty 500 (bar, same window)", (b**(1/y)-1)*100, "", b))

print("\n--- A. base signal (own-SECTOR RS) ---")
go("excess_63d > 0  ('RS>1'/'crosses 0')", rule_excess(0))
go("+ consistency >=50%", rule_consist(0.50))
go("+ consistency >=60%", rule_consist(0.60))
go("+ consistency >=70%", rule_consist(0.70))
go("+ consistency >=80%", rule_consist(0.80))

print("\n--- B. EMA-of-RS crossover (own sector) ---")
go("state: RS-vs-sector ratio > its 50EMA", rule_ema_state_sec())
go("event: RS-vs-sector crosses 50EMA (last 20d)", rule_ema_cross_sec())

print("\n--- C. narrow (sector) vs broad — how to combine ---")
go("broad-only: RS-vs-Nifty500 > its 50EMA", rule_ema_state_broad())
go("AND: both sector AND broad above their EMAs", rule_ema_and())
go("OR: sector OR broad above its EMA", rule_ema_or())

print("\n--- D. best selection rule + the proven exit (trailing -20%, 1% slip) ---")
go("excess_63d>0 + consist>=60% + trail-20% slip1%", rule_consist(0.60), trail=0.20, slip=0.01)
go("EMA-state-sector + trail-20% slip1%", rule_ema_state_sec(), trail=0.20, slip=0.01)
go("AND(sector,broad) + trail-20% slip1%", rule_ema_and(), trail=0.20, slip=0.01)

print("\n--- E. book size sensitivity on the best config so far ---")
for n in (20, 40, 60):
    go(f"AND(sector,broad) + trail-20% slip1%, top{n}", rule_ema_and(), topn=n, trail=0.20, slip=0.01)
