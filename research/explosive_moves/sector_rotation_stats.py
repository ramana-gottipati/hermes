"""V8 vs Nifty500 — full statistical dump (JSON). Reuses the frozen Champion + V8 levers
(BAL+RSPK+STR+RSIRS) from sector_rotation_exp.py. Oldest data 2005-2026.

METRIC BASIS (D142): the `retvol` emitted here (V8 and benchmark alike) is mean/sd annualised with
NO risk-free rate subtracted — a return/vol ratio, not a Sharpe; it reads high against a textbook
Sharpe."""
import sqlite3, math, sys, json
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START, LB, CAP = "2005-01-03", 126, 0.30
COMP = {"BAL", "RSPK", "STR", "RSIRS"}          # V8

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = defaultdict(dict)
names = SECTORS + [BENCH]
q = "SELECT index_name,trade_date,close_value FROM index_rows WHERE index_name IN (%s) AND close_value>0" % ",".join("?"*len(names))
for nm, d, c in conn.execute(q, names):
    close[nm][d] = c
conn.close()

cal = sorted(d for d in close[BENCH] if d >= START)
idx = {d: i for i, d in enumerate(cal)}
rebal, seen = [], set()
for d in cal:
    if d[:7] not in seen:
        seen.add(d[:7]); rebal.append(d)

def ret(nm, d0, d1):
    a, b = close[nm].get(d0), close[nm].get(d1)
    return (b/a-1.0) if (a and b) else None

def trailing(nm, d, lb=LB):
    i = idx.get(d)
    if i is None or i-lb < 0: return None
    d0 = cal[i-lb]
    return close[nm][d]/close[nm][d0]-1.0 if (d0 in close[nm] and d in close[nm]) else None

def _series(nm, d, win):
    i = idx.get(d)
    if i is None: return []
    return [close[nm][cal[k]] for k in range(max(0,i-win+1), i+1) if cal[k] in close[nm]]

def rsi(vals, n=14):
    if len(vals) < n+1: return None
    g=l=0.0
    for k in range(len(vals)-n, len(vals)):
        ch = vals[k]-vals[k-1]; g += max(ch,0); l += max(-ch,0)
    ag, al = g/n, l/n
    return 100.0 if al==0 else 100.0-100.0/(1.0+ag/al)

def rsi14_price(nm, d): return rsi(_series(nm, d, 40))
def _pctile(x, arr): return (sum(1 for a in arr if a<=x)/len(arr)) if arr else None

def rs_line(nm, d, win):
    i = idx.get(d)
    if i is None: return []
    return [close[nm][cal[k]]/close[BENCH][cal[k]] for k in range(max(0,i-win+1), i+1)
            if cal[k] in close[nm] and cal[k] in close[BENCH]]

def rs_peak_pct(nm, d):
    s = rs_line(nm, d, 756)
    return _pctile(s[-1], s) if len(s) > 60 else None

def stretch_z(nm, d):
    s = _series(nm, d, 200)
    if len(s) < 150: return None
    m = sum(s)/len(s); sd = math.sqrt(sum((x-m)**2 for x in s)/(len(s)-1))
    return (s[-1]-m)/sd if sd > 0 else 0.0

def rsi_of_rs(nm, d): return rsi(rs_line(nm, d, 40))

def _taper(p, thr=0.85, floor=0.35):
    if p is None or p <= thr: return 1.0
    return max(floor, 1.0-(p-thr)/(1-thr)*(1-floor))

def _cap(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap+1e-9}
        if not over: break
        exc = sum(w[s]-cap for s in over)
        for s in over: w[s] = cap
        und = [s for s in w if w[s] < cap-1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und: w[s] += exc*w[s]/tu
    return w

def build(d, held):
    band = 0.08; rs = {}
    for s in SECTORS:
        tr, tb = trailing(s, d), trailing(BENCH, d)
        if tr is not None and tb is not None: rs[s] = tr-tb
    longs = {}
    for s, v in rs.items():
        if s in held:
            if v > -band: longs[s] = max(v, 1e-6)
        elif v > band: longs[s] = v
    keep = {}; i = idx[d]; dprev = cal[max(0, i-21)]
    for s in longs:
        rn, rp = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp is None or rn >= rp)):
            keep[s] = longs[s]
    longs = keep
    if not longs: return {}
    base = {s: 1.0/len(longs) for s in longs}      # BAL
    base = _cap(base)
    adj = dict(base)
    for s in list(adj):
        f = 1.0
        f *= _taper(rs_peak_pct(s, d))                                        # RSPK
        z = stretch_z(s, d)
        f *= _taper(_pctile(z, [-2,-1,0,1,1.5,2,2.5]) if z is not None else None, thr=0.7)  # STR
        r = rsi_of_rs(s, d)
        if r is not None:
            if r >= 80: f *= 0.0                                              # RSIRS
            elif r >= 70: f *= 0.5
        adj[s] = base[s]*f
    tot = sum(adj.values())
    if tot <= 0: return base
    return _cap({s: adj[s]/tot for s in adj})

# simulate V8 (quarterly, cost 15bps/side)
prev = {}; rows = []
for k in range(len(rebal)-1):
    d, dn = rebal[k], rebal[k+1]
    if k % 3 == 0:
        w = build(d, set(prev))
    else:
        w = prev
    rb = ret(BENCH, d, dn) or 0.0
    if not w:
        rows.append((dn, rb, rb)); prev = {}; continue
    rp = sum(x*(ret(s, d, dn) or 0.0) for s, x in w.items())
    if k % 3 == 0:
        allk = set(w)|set(prev)
        rp -= sum(abs(w.get(s,0)-prev.get(s,0)) for s in allk)*0.0015
    rows.append((dn, rp, rb)); prev = w

dts = [r[0] for r in rows]; rp = [r[1] for r in rows]; rb = [r[2] for r in rows]
n = len(rp)

def navser(rs_):
    nav = 1.0; out = []
    for x in rs_: nav *= (1+x); out.append(nav)
    return out
nav_p, nav_b = navser(rp), navser(rb)

def ddser(nav):
    pk = 0.0; out = []
    for v in nav:
        pk = max(pk, v); out.append(v/pk-1)
    return out
dd_p, dd_b = ddser(nav_p), ddser(nav_b)

def maxdd_info(nav, dts_):
    pk, pkd, mdd, mtr, mpk = nav[0], dts_[0], 0.0, dts_[0], dts_[0]
    for i, v in enumerate(nav):
        if v > pk: pk, pkd = v, dts_[i]
        d_ = v/pk-1
        if d_ < mdd: mdd, mtr, mpk = d_, dts_[i], pkd
    # recovery
    rec = None; seenpk = False
    pkval = None
    for i, dtx in enumerate(dts_):
        if dtx == mpk: pkval = nav[i]
    for i, dtx in enumerate(dts_):
        if dtx > mtr and pkval and nav[i] >= pkval:
            rec = dtx; break
    return dict(depth=mdd, peak=mpk, trough=mtr, recovery=rec)

def stats(rs_):
    m = sum(rs_)/len(rs_); sd = math.sqrt(sum((x-m)**2 for x in rs_)/(len(rs_)-1))
    sh = m/sd*math.sqrt(12) if sd else 0
    nav = 1.0
    for x in rs_: nav *= 1+x
    yrs = len(rs_)/12
    return dict(retvol=round(sh,3), cagr=round(nav**(1/yrs)-1,4), vol=round(sd*math.sqrt(12),4), nav=round(nav,3))

# alpha regression + t-stats
mp, mb = sum(rp)/n, sum(rb)/n
covv = sum((rp[i]-mp)*(rb[i]-mb) for i in range(n))/(n-1)
varb = sum((x-mb)**2 for x in rb)/(n-1)
beta = covv/varb
alpha_m = mp-beta*mb
resid = [rp[i]-(alpha_m+beta*rb[i]) for i in range(n)]
s_e = math.sqrt(sum(e*e for e in resid)/(n-2))
se_a = s_e*math.sqrt(1.0/n + mb*mb/((n-1)*varb))
t_alpha = alpha_m/se_a
act = [rp[i]-rb[i] for i in range(n)]
ma = sum(act)/n; sa = math.sqrt(sum((x-ma)**2 for x in act)/(n-1))
t_act = ma/(sa/math.sqrt(n))
ir = ma*12/(sa*math.sqrt(12))
hit = sum(1 for x in act if x > 0)/n
upm = [i for i in range(n) if rb[i] > 0]; dnm = [i for i in range(n) if rb[i] < 0]
upcap = (sum(rp[i] for i in upm)/len(upm))/(sum(rb[i] for i in upm)/len(upm))
dncap = (sum(rp[i] for i in dnm)/len(dnm))/(sum(rb[i] for i in dnm)/len(dnm))

# yearly returns
def yearly(rs_):
    out = {}
    for i, dtx in enumerate(dts):
        y = dtx[:4]
        out[y] = out.get(y, 1.0)*(1+rs_[i])
    return {y: round(v-1, 4) for y, v in sorted(out.items())}

worst = sorted(range(n), key=lambda i: rp[i])[:5]

out = dict(
    window=dict(first=dts[0], last=dts[-1], months=n),
    v8=stats(rp), bench=stats(rb),
    one_cr=dict(v8=round(nav_p[-1]*1.0, 2), bench=round(nav_b[-1]*1.0, 2)),   # in Cr
    alpha=dict(annual=round(alpha_m*12, 4), t_stat=round(t_alpha, 2), beta=round(beta, 3),
               active_ann=round(ma*12, 4), t_active=round(t_act, 2), IR=round(ir, 2),
               hit_rate=round(hit, 3), up_capture=round(upcap, 2), down_capture=round(dncap, 2)),
    maxdd=dict(v8=maxdd_info(nav_p, dts), bench=maxdd_info(nav_b, dts)),
    covid=dict(v8=round(min(dd_p[i] for i in range(n) if "2020-01" <= dts[i] <= "2020-12"), 4),
               bench=round(min(dd_b[i] for i in range(n) if "2020-01" <= dts[i] <= "2020-12"), 4)),
    yearly=dict(v8=yearly(rp), bench=yearly(rb)),
    worst_months=[dict(d=dts[i], v8=round(rp[i], 4), bench=round(rb[i], 4)) for i in worst],
    series=[dict(d=dts[i], p=round(nav_p[i], 3), b=round(nav_b[i], 3),
                 dp=round(dd_p[i], 3), db=round(dd_b[i], 3)) for i in range(n)],
)
print(json.dumps(out))
