"""Round 3 — the V18/V19/V20 batch vs the FROZEN V17 benchmark (Sharpe 0.79 / CAGR 14.7% /
MaxDD -39.2% / Rs 1Cr -> 19.04; bench N500 0.64 / 12.5% / -62.0% / 12.60; 2005-2026 n=257).

  V18a SLEEVE=NEXT50   residual sleeve asset -> Nifty Next 50 (full 2004+ history), same
                       bench-200DMA guard; sector book untouched.
  V18b SLEEVE=MIDCAP50 sensitivity: Midcap 50 (2012+; pre-data months fall back to N500).
  V19  RECOVERY        if the bench RECLAIMED its 200DMA during the last quarter (OFF at any
                       of the prior 3 month-starts, ON at build) -> that build's NEW-entry
                       band = 0 (RSI-green still required). Attacks the measured 2009/2014 miss.
  V20  INVVOL          base weights proportional to 1/sigma126 instead of equal (BAL), then
                       the same cap + tapers + renorm.
  combos of winners.
"""
import sqlite3, math, sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
NEXT50 = "Nifty Next 50"
MID50 = "Nifty Midcap 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START, LB, CAP, BAND, COST = "2005-01-03", 126, 0.30, 0.08, 0.0015

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = defaultdict(dict)
names = SECTORS + [BENCH, NEXT50, MID50]
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

def vol126(s, d):
    ser = _series(s, d, 127)
    if len(ser) < 60: return None
    rets = [ser[i]/ser[i-1]-1 for i in range(1, len(ser))]
    m = sum(rets)/len(rets)
    return math.sqrt(sum((x-m)**2 for x in rets)/(len(rets)-1))

def qualifying(d, held, entry_band):
    rs = {}
    for s in SECTORS:
        tr, tb = trailing(s, d), trailing(BENCH, d)
        if tr is not None and tb is not None: rs[s] = tr-tb
    longs = {}
    for s, v in rs.items():
        if s in held:
            if v > -BAND: longs[s] = max(v, 1e-6)
        elif v > entry_band: longs[s] = v
    keep = {}; i = idx[d]; dprev = cal[max(0, i-21)]
    for s in longs:
        rn, rp_ = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp_ is None or rn >= rp_)):
            keep[s] = longs[s]
    return keep

def build(d, held, entry_band=BAND, invvol=False):
    longs = qualifying(d, held, entry_band)
    if not longs: return {}
    if invvol:
        iv = {}
        for s in longs:
            v = vol126(s, d)
            iv[s] = 1.0/v if v and v > 0 else 0.0
        tot = sum(iv.values())
        base = _cap_only({s: iv[s]/tot for s in iv}) if tot > 0 else _cap_only({s: 1.0/len(longs) for s in longs})
    else:
        base = _cap_only({s: 1.0/len(longs) for s in longs})
    adj = {s: base[s]*taper_product(s, d) for s in base}
    tot = sum(adj.values())
    if tot <= 0: return base
    return _cap_only({s: adj[s]/tot for s in adj})

def kill_on(d):
    s = _series(BENCH, d, 200)
    return len(s) >= 200 and s[-1] < sum(s)/len(s)

def sleeve_ret(asset, d, dn):
    """sleeve earns `asset` if it has data (else bench), guard unchanged (bench 200DMA)."""
    r = ret(asset, d, dn)
    return r if r is not None else (ret(BENCH, d, dn) or 0.0)

def simulate(sleeve=BENCH, recovery=False, invvol=False, lag=0):
    prev = {}; rows = []; turn_sum = 0.0
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        is_q = (k % 3 == 0)
        if is_q:
            eb = BAND
            if recovery and not kill_on(d):
                lookback = [rebal[k-j] for j in (1, 2, 3) if k-j >= 0]
                if any(kill_on(x) for x in lookback):
                    eb = 0.0                     # the reclaim quarter: welcome early leaders
            w = build(d, set(prev), eb, invvol)
        else:
            w = dict(prev)
        rb = ret(BENCH, d, dn) or 0.0
        on_index = not kill_on(d)
        inv = sum(w.values())
        d1 = cal[min(idx[d]+lag, len(cal)-1)] if lag and is_q else d
        if not w:
            rp = sleeve_ret(sleeve, d, dn) if on_index else 0.0
        else:
            if lag and is_q and d1 != d:
                # T+1 realism: the OLD book (and old sleeve state) rides d->d1; trades fill at d1 close
                inv_p = sum(prev.values())
                rp_pre = sum(x*(ret(s, d, d1) or 0.0) for s, x in prev.items())
                if prev and inv_p < 1.0 and on_index:
                    rp_pre += (1.0-inv_p)*sleeve_ret(sleeve, d, d1)
                if not prev:
                    rp_pre = sleeve_ret(sleeve, d, d1) if on_index else 0.0
                rp_post = sum(x*(ret(s, d1, dn) or 0.0) for s, x in w.items())
                if inv < 1.0 and on_index:
                    rp_post += (1.0-inv)*sleeve_ret(sleeve, d1, dn)
                rp = (1+rp_pre)*(1+rp_post)-1
            else:
                rp = sum(x*(ret(s, d, dn) or 0.0) for s, x in w.items())
                if inv < 1.0 and on_index:
                    rp += (1.0-inv)*sleeve_ret(sleeve, d, dn)
        if is_q:
            allk = set(w)|set(prev)
            t = sum(abs(w.get(s,0)-prev.get(s,0)) for s in allk)
            rp -= t*COST; turn_sum += t
        rows.append((dn, rp, rb)); prev = w
    return rows, turn_sum/len(rows)

def stats(rows):
    rp = [r[1] for r in rows]; rb = [r[2] for r in rows]; n = len(rp)
    m = sum(rp)/n; sd = math.sqrt(sum((x-m)**2 for x in rp)/(n-1))
    sh = m/sd*math.sqrt(12) if sd else 0
    nav = pk = 1.0; mdd = 0.0
    for x in rp:
        nav *= 1+x; pk = max(pk, nav); mdd = min(mdd, nav/pk-1)
    yrs = n/12
    mb = sum(rb)/n
    covv = sum((rp[i]-m)*(rb[i]-mb) for i in range(n))/(n-1)
    varb = sum((x-mb)**2 for x in rb)/(n-1)
    beta = covv/varb; alpha = (m-beta*mb)*12
    half = n//2
    def sh_(xs):
        mm = sum(xs)/len(xs); s2 = math.sqrt(sum((x-mm)**2 for x in xs)/(len(xs)-1))
        return mm/s2*math.sqrt(12) if s2 else 0
    return dict(sh=sh, h1=sh_(rp[:half]), h2=sh_(rp[half:]), cagr=nav**(1/yrs)-1,
                mdd=mdd, beta=beta, alpha=alpha, cr=nav)

variants = [
    ("V17 baseline (sleeve=N500)",      dict()),
    ("V18a sleeve=NEXT50",              dict(sleeve=NEXT50)),
    ("V18b sleeve=MIDCAP50 (2012+)",    dict(sleeve=MID50)),
    ("V19 recovery-accelerator",        dict(recovery=True)),
    ("V20 inverse-vol weights",         dict(invvol=True)),
    ("V18a+V19",                        dict(sleeve=NEXT50, recovery=True)),
    ("V18a+V19+V20",                    dict(sleeve=NEXT50, recovery=True, invvol=True)),
    ("V17 T+1 execution lag",           dict(lag=1)),
    ("V21 T+1 execution lag",           dict(sleeve=NEXT50, recovery=True, invvol=True, lag=1)),
]
print(f"{'variant':<30} {'Sharpe':>6} {'H1/H2':>11} {'CAGR':>6} {'MaxDD':>6} {'beta':>5} {'alpha':>6} {'Rs1Cr':>6} {'turn':>5}")
for label, kw in variants:
    rows, turn = simulate(**kw)
    st = stats(rows)
    print(f"{label:<30} {st['sh']:>6.2f} {st['h1']:>5.2f}/{st['h2']:<5.2f} {st['cagr']:>6.1%} {st['mdd']:>6.1%} {st['beta']:>5.2f} {st['alpha']:>+6.1%} {st['cr']:>6.2f} {turn:>5.1%}")
# reference: the sleeve assets alone
for nm in (NEXT50, MID50):
    rows = [(rebal[k+1], ret(nm, rebal[k], rebal[k+1]) if ret(nm, rebal[k], rebal[k+1]) is not None else (ret(BENCH, rebal[k], rebal[k+1]) or 0.0), ret(BENCH, rebal[k], rebal[k+1]) or 0.0) for k in range(len(rebal)-1)]
    st = stats(rows)
    print(f"{'[ref] '+nm+' B&H':<30} {st['sh']:>6.2f} {st['h1']:>5.2f}/{st['h2']:<5.2f} {st['cagr']:>6.1%} {st['mdd']:>6.1%} {st['beta']:>5.2f} {st['alpha']:>+6.1%} {st['cr']:>6.2f}")
