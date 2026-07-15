"""Consolidated run: Nifty 50 / Nifty 100 / Nifty 500 vs V24 (= V21 + own-percentile
RSI-of-RS, per Ramana's naming). Reuses the SAME validated engine as sector_rotation_exp4.py
(V24 lever unchanged) -- this script only adds the Nifty 100 comparator and emits chart-ready
quarterly series + full stats. No new lever logic; the V24 numbers must match ledger 2026-07-15f
exactly (Sharpe 0.91, MaxDD -37.7%, Rs1Cr->30.35)."""
import sqlite3, math, sys, json
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
N50 = "Nifty 50"
N100 = "Nifty 100"
NEXT50 = "Nifty Next 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START, LB, CAP, BAND, COST = "2005-01-03", 126, 0.30, 0.08, 0.0015

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = defaultdict(dict)
names = SECTORS + [BENCH, N50, N100, NEXT50]
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

def series(nm, d, win):
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

def rsi14_price(nm, d): return rsi(series(nm, d, 40))
def pctile(x, arr): return (sum(1 for a in arr if a<=x)/len(arr)) if arr else None

def rs_line(nm, d, win, vs=BENCH):
    i = idx.get(d)
    if i is None: return []
    return [close[nm][cal[k]]/close[vs][cal[k]] for k in range(max(0,i-win+1), i+1)
            if cal[k] in close[nm] and cal[k] in close[vs]]

def rs_peak_pct(nm, d):
    s = rs_line(nm, d, 756)
    return pctile(s[-1], s) if len(s) > 60 else None

def stretch_z(nm, d):
    s = series(nm, d, 200)
    if len(s) < 150: return None
    m = sum(s)/len(s); sd = math.sqrt(sum((x-m)**2 for x in s)/(len(s)-1))
    return (s[-1]-m)/sd if sd > 0 else 0.0

def rsi_of_rs(nm, d): return rsi(rs_line(nm, d, 40))

def taper(p, thr=0.85, floor=0.35):
    if p is None or p <= thr: return 1.0
    return max(floor, 1.0-(p-thr)/(1-thr)*(1-floor))

_RSIRS_CACHE = {}
def rsirs_series_at(nm, d):
    if nm not in _RSIRS_CACHE:
        vals = []
        for k, dt in enumerate(cal):
            r = rs_line(nm, dt, 40)
            vals.append(rsi(r) if len(r) >= 15 else None)
        _RSIRS_CACHE[nm] = vals
    full = _RSIRS_CACHE[nm]
    i = idx[d]
    return [v for v in full[max(0,i-756):i+1] if v is not None]

def taper_product_v24(s, d):
    hist = rsirs_series_at(s, d)
    r = rsi_of_rs(s, d)
    p = pctile(r, hist) if (r is not None and len(hist) > 60) else None
    trim_now = p is not None and p >= 0.85
    exit_now = p is not None and p >= 0.95
    f_rsirs = 0.0 if exit_now else (0.5 if trim_now else 1.0)
    f = 1.0
    f *= taper(rs_peak_pct(s, d))
    z = stretch_z(s, d)
    f *= taper(pctile(z, [-2,-1,0,1,1.5,2,2.5]) if z is not None else None, thr=0.7)
    f *= f_rsirs
    return f

def cap_only(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap+1e-9}
        if not over: break
        exc = sum(w[s]-cap for s in over)
        for s in over: w[s] = cap
        und = [s for s in w if w[s] < cap-1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und: w[s] += exc*w[s]/tu
    return w

def vol126(s, d):
    ser = series(s, d, 127)
    if len(ser) < 60: return None
    rets = [ser[i]/ser[i-1]-1 for i in range(1, len(ser))]
    m = sum(rets)/len(rets)
    return math.sqrt(sum((x-m)**2 for x in rets)/(len(rets)-1))

def rs_excess(s, d):
    tr, tb = trailing(s, d), trailing(BENCH, d)
    return None if (tr is None or tb is None) else tr-tb

def qualifying(d, held):
    longs = {}
    for s in SECTORS:
        v = rs_excess(s, d)
        if v is None: continue
        if s in held:
            if v > -BAND: longs[s] = max(v, 1e-6)
        elif v > (globals().get("_EB") if globals().get("_EB") is not None else BAND):
            longs[s] = v
    keep = {}; i = idx[d]; dprev = cal[max(0, i-21)]
    for s in longs:
        rn, rp_ = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp_ is None or rn >= rp_)):
            keep[s] = longs[s]
    return keep

def build(d, held, entry_band=None):
    globals()["_EB"] = entry_band
    longs = qualifying(d, held)
    globals()["_EB"] = None
    if not longs: return {}
    iv = {}
    for s in longs:
        v = vol126(s, d)
        iv[s] = 1.0/v if v and v > 0 else 0.0
    tot = sum(iv.values())
    base = cap_only({s: iv[s]/tot for s in iv}) if tot > 0 else cap_only({s: 1.0/len(longs) for s in longs})
    adj = {s: base[s]*taper_product_v24(s, d) for s in base}
    tot = sum(adj.values())
    if tot <= 0: return base
    return cap_only({s: adj[s]/tot for s in adj})

def kill_on(d):
    s = series(BENCH, d, 200)
    return len(s) >= 200 and s[-1] < sum(s)/len(s)

def sleeve_ret(asset, d, dn):
    r = ret(asset, d, dn)
    return r if r is not None else (ret(BENCH, d, dn) or 0.0)

def simulate_v24():
    prev = {}; rows = []
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        is_q = (k % 3 == 0)
        if is_q:
            eb = None
            if not kill_on(d):
                lookback = [rebal[k-j] for j in (1, 2, 3) if k-j >= 0]
                if any(kill_on(x) for x in lookback):
                    eb = 0.0
            w = build(d, set(prev), eb)
        else:
            w = dict(prev)
        rb = ret(BENCH, d, dn) or 0.0
        on_index = not kill_on(d)
        inv = sum(w.values())
        if not w:
            rp = sleeve_ret(NEXT50, d, dn) if on_index else 0.0
        else:
            rp = sum(x*(ret(s, d, dn) or 0.0) for s, x in w.items())
            if inv < 1.0 and on_index:
                rp += (1.0-inv)*sleeve_ret(NEXT50, d, dn)
        if is_q:
            allk = set(w)|set(prev)
            t = sum(abs(w.get(s,0)-prev.get(s,0)) for s in allk)
            rp -= t*COST
        rows.append((dn, rp, rb)); prev = w
    return rows

def stats(rows_or_rets, is_pairs=True):
    if is_pairs:
        rp = [r[1] for r in rows_or_rets]
    else:
        rp = rows_or_rets
    n = len(rp)
    m = sum(rp)/n; sd = math.sqrt(sum((x-m)**2 for x in rp)/(n-1))
    sh = m/sd*math.sqrt(12) if sd else 0
    nav = pk = 1.0; mdd = 0.0
    for x in rp:
        nav *= 1+x; pk = max(pk, nav); mdd = min(mdd, nav/pk-1)
    yrs = n/12
    half = n//2
    def sh_(xs):
        mm = sum(xs)/len(xs); s2 = math.sqrt(sum((x-mm)**2 for x in xs)/(len(xs)-1))
        return mm/s2*math.sqrt(12) if s2 else 0
    return dict(sh=round(sh,3), h1=round(sh_(rp[:half]),3), h2=round(sh_(rp[half:]),3),
                cagr=round(nav**(1/yrs)-1,4), mdd=round(mdd,4), cr=round(nav,3))

v24_rows = simulate_v24()
dts = [r[0] for r in v24_rows]
def navdd(rets):
    nav=1.0; pk=1.0; out=[]; dd=[]
    for x in rets:
        nav*=(1+x); pk=max(pk,nav); out.append(nav); dd.append(nav/pk-1)
    return out, dd

n50_rets = [ret(N50, rebal[k], rebal[k+1]) or 0.0 for k in range(len(rebal)-1)]
n100_rets = [ret(N100, rebal[k], rebal[k+1]) or 0.0 for k in range(len(rebal)-1)]
n500_rets = [ret(BENCH, rebal[k], rebal[k+1]) or 0.0 for k in range(len(rebal)-1)]
v24_rets = [r[1] for r in v24_rows]

nav_v24, dd_v24 = navdd(v24_rets)
nav_50, dd_50 = navdd(n50_rets)
nav_100, dd_100 = navdd(n100_rets)
nav_500, dd_500 = navdd(n500_rets)

def alpha_beta(rp, rb):
    n=len(rp); mp=sum(rp)/n; mb=sum(rb)/n
    cov=sum((rp[i]-mp)*(rb[i]-mb) for i in range(n))/(n-1)
    varb=sum((x-mb)**2 for x in rb)/(n-1)
    beta=cov/varb if varb else 0
    return beta, (mp-beta*mb)*12

beta24, alpha24 = alpha_beta(v24_rets, n500_rets)

out = dict(
    v24=stats(v24_rets, False), n50=stats(n50_rets, False),
    n100=stats(n100_rets, False), n500=stats(n500_rets, False),
    v24_alpha=round(alpha24,4), v24_beta=round(beta24,3),
    window=dict(first=dts[0], last=dts[-1], months=len(dts)),
)
keep = sorted(set(list(range(0, len(dts), 3)) +
                  [i for i,d in enumerate(dts) if d[:7] in ("2008-12","2009-03","2020-04","2026-04")] +
                  [len(dts)-1]))
out["L"] = [dts[i][:7] for i in keep]
out["V24"] = [round(nav_v24[i],3) for i in keep]
out["N50"] = [round(nav_50[i],3) for i in keep]
out["N100"] = [round(nav_100[i],3) for i in keep]
out["N500"] = [round(nav_500[i],3) for i in keep]
out["DV24"] = [round(dd_v24[i]*100,1) for i in keep]
out["DN50"] = [round(dd_50[i]*100,1) for i in keep]
out["DN100"] = [round(dd_100[i]*100,1) for i in keep]
out["DN500"] = [round(dd_500[i]*100,1) for i in keep]
print(json.dumps(out))
