"""Round 2 — attack the return gap. V8 stays FROZEN as recorded (Sharpe 0.703 / CAGR 10.83%
/ MaxDD -36.2% / Rs 9.13 Cr; bench 0.637 / 12.51% / -62.0% / 12.60 Cr).

New levers (one at a time, then combos):
  KILLs = regime kill-switch: bench < 200DMA at month-start -> scale book x0.5 (soft)
  KILLh = hard version -> full cash
  ASYM  = asymmetric cadence: ENTRIES quarterly, RISK monthly (tapers/RSIRS/RS-break
          recomputed monthly on the held book; freed weight -> CASH, no renormalize)
  FILL  = residual-to-index: uninvested fraction earns the bench return (index ETF)
  MONTH = full V8 logic at MONTHLY cadence (entries monthly too, hysteresis kept)
"""
import sqlite3, math, sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START, LB, CAP, BAND, COST = "2005-01-03", 126, 0.30, 0.08, 0.0015

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

def taper_product(s, d):
    f = 1.0
    f *= _taper(rs_peak_pct(s, d))
    z = stretch_z(s, d)
    f *= _taper(_pctile(z, [-2,-1,0,1,1.5,2,2.5]) if z is not None else None, thr=0.7)
    r = rsi_of_rs(s, d)
    if r is not None:
        if r >= 80: f = 0.0
        elif r >= 70: f *= 0.5
    return f

def _cap_only(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap+1e-9}
        if not over: break
        exc = sum(w[s]-cap for s in over)
        for s in over: w[s] = cap
        und = [s for s in w if w[s] < cap-1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und: w[s] += exc*w[s]/tu
    return w

def qualifying(d, held):
    rs = {}
    for s in SECTORS:
        tr, tb = trailing(s, d), trailing(BENCH, d)
        if tr is not None and tb is not None: rs[s] = tr-tb
    longs = {}
    for s, v in rs.items():
        if s in held:
            if v > -BAND: longs[s] = max(v, 1e-6)
        elif v > BAND: longs[s] = v
    keep = {}; i = idx[d]; dprev = cal[max(0, i-21)]
    for s in longs:
        rn, rp_ = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp_ is None or rn >= rp_)):
            keep[s] = longs[s]
    return keep

def build_v8(d, held):
    """FROZEN V8 build: BAL + cap + tapers, renormalized, re-capped."""
    longs = qualifying(d, held)
    if not longs: return {}
    base = _cap_only({s: 1.0/len(longs) for s in longs})
    adj = {s: base[s]*taper_product(s, d) for s in base}
    tot = sum(adj.values())
    if tot <= 0: return base
    return _cap_only({s: adj[s]/tot for s in adj})

def build_asym(d, held):
    """ASYM quarter build: BAL + cap base, taper applied WITHOUT renormalize (cash)."""
    longs = qualifying(d, held)
    if not longs: return {}, {}
    base = _cap_only({s: 1.0/len(longs) for s in longs})
    w = {s: base[s]*taper_product(s, d) for s in base}
    return {s: v for s, v in w.items() if v > 0}, base

def kill_on(d):
    s = _series(BENCH, d, 200)
    return len(s) >= 200 and s[-1] < sum(s)/len(s)

def rs_excess(s, d):
    tr, tb = trailing(s, d), trailing(BENCH, d)
    return None if (tr is None or tb is None) else tr-tb

def simulate(mode):
    """mode in V8, KILLs, KILLh, ASYM, FILL, MONTH, and combos like ASYM+FILL."""
    monthly_entries = "MONTH" in mode
    dfill = "DFILL" in mode or "DFILLB" in mode
    asym = "ASYM" in mode
    fill = ("FILL" in mode) and not dfill
    kill = "KILLs" in mode or "KILLh" in mode
    kfac = 0.5 if "KILLs" in mode else 0.0
    prev, qbase = {}, {}
    rows = []; expo_sum = 0.0; turn_sum = 0.0
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        is_q = (k % 3 == 0) or monthly_entries
        if asym:
            if is_q:
                w, qbase = build_asym(d, set(qbase))
            else:
                w = {}
                for s in qbase:
                    v = rs_excess(s, d)
                    if v is None or v <= -BAND: continue
                    f = taper_product(s, d)
                    if f > 0: w[s] = qbase[s]*f
        else:
            w = build_v8(d, set(prev)) if is_q else dict(prev)
        if kill and kill_on(d):
            w = {s: v*kfac for s, v in w.items()}
        rb = ret(BENCH, d, dn) or 0.0
        if not w:
            if dfill:
                r = 0.0 if kill_on(d) else rb   # defensive residual, uniformly
            elif fill:
                r = rb
            elif kill and kill_on(d):
                r = 0.0
            else:
                r = rb                      # frozen V8 empty-book behavior
            rows.append((dn, r, rb)); prev = {}; expo_sum += (1.0 if r == rb else 0.0)
            continue
        inv = sum(w.values())
        rp_ = sum(x*(ret(s, d, dn) or 0.0) for s, x in w.items())
        if fill and inv < 1.0:
            rp_ += (1.0-inv)*rb
        if dfill and inv < 1.0 and not kill_on(d):
            rp_ += (1.0-inv)*rb
        allk = set(w)|set(prev)
        turn = sum(abs(w.get(s,0)-prev.get(s,0)) for s in allk)
        rp_ -= turn*COST
        rows.append((dn, rp_, rb)); prev = w
        expo_sum += (1.0 if fill else inv); turn_sum += turn
    return rows, expo_sum/len(rows), turn_sum/len(rows)

def stats(rows):
    rp = [r[1] for r in rows]; rb = [r[2] for r in rows]; n = len(rp)
    m = sum(rp)/n; sd = math.sqrt(sum((x-m)**2 for x in rp)/(n-1))
    sh = m/sd*math.sqrt(12) if sd else 0
    nav = 1.0; pk = 1.0; mdd = 0.0
    for x in rp:
        nav *= 1+x; pk = max(pk, nav); mdd = min(mdd, nav/pk-1)
    yrs = n/12
    cagr = nav**(1/yrs)-1
    mb = sum(rb)/n
    covv = sum((rp[i]-m)*(rb[i]-mb) for i in range(n))/(n-1)
    varb = sum((x-mb)**2 for x in rb)/(n-1)
    beta = covv/varb; alpha = (m-beta*mb)*12
    # halves
    half = n//2
    def sh_(xs):
        mm = sum(xs)/len(xs); s2 = math.sqrt(sum((x-mm)**2 for x in xs)/(len(xs)-1))
        return mm/s2*math.sqrt(12) if s2 else 0
    return dict(sh=sh, h1=sh_(rp[:half]), h2=sh_(rp[half:]), cagr=cagr, mdd=mdd,
                beta=beta, alpha=alpha, cr=nav)

variants = [
    ("V8 frozen",        "V8"),
    ("V9a KILL soft x0.5","KILLs"),
    ("V9b KILL hard cash","KILLh"),
    ("V10 ASYM risk-mo",  "ASYM"),
    ("V11 FILL residual", "FILL"),
    ("V12 MONTHLY entries","MONTH"),
    ("V13 ASYM+FILL",     "ASYM+FILL"),
    ("V14 ASYM+FILL+KILLs","ASYM+FILL+KILLs"),
    ("V15 MONTH+FILL",    "MONTH+FILL"),
    ("V16 MONTH+ASYM+FILL","MONTH+ASYM+FILL"),
    ("V17 DFILL defensive","DFILL"),
    ("V17b DFILL uniform","DFILLB"),
]
print(f"{'variant':<22} {'Sharpe':>6} {'H1/H2':>11} {'CAGR':>6} {'MaxDD':>6} {'beta':>5} {'alpha':>6} {'Rs1Cr':>6} {'expo':>5} {'turn':>5}")
for label, mode in variants:
    rows, expo, turn = simulate(mode)
    st = stats(rows)
    print(f"{label:<22} {st['sh']:>6.2f} {st['h1']:>5.2f}/{st['h2']:<5.2f} {st['cagr']:>6.1%} {st['mdd']:>6.1%} {st['beta']:>5.2f} {st['alpha']:>+6.1%} {st['cr']:>6.2f} {expo:>5.1%} {turn:>5.1%}")
print("\nbench: Sharpe 0.64  CAGR 12.5%  MaxDD -62.0%  Rs1Cr 12.60")
