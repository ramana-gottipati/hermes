"""CASH-OUT + BETA CONTROL on the winning stack. Ramana, 2026-07-16:
"If a position fails to meet a specific threshold, we should simply cash out and hold the proceeds
as cash... when an asset is not performing better, we exit and set the money aside."

THE BUG THIS EXPOSES (mine, in every test today): on stop-out I deleted the position, then at the
next rebalance renormalized the survivors back to 100% invested -- so if only 3 names passed the
filter they got 33% EACH. That is not "40 slots, 37 in cash"; it is a concentrated 3-stock bet.
FIXED SIZING (each pick gets exactly 1/N, remainder = CASH) is a different strategy and was never run.

VARIANTS OF "WHERE DOES THE MONEY GO"
  norm      : renormalize to 100% invested          (what every prior test did -- the bug)
  cash      : each pick 1/N, remainder DEAD CASH    (Ramana's literal instruction)
  sleeve    : each pick 1/N, remainder -> NIFTY NEXT 50  (V17's lesson: idle capital should work;
              the same 200DMA-gated sleeve that took V8 9.13x -> V17 19.04x)
  sleeve200 : as above but the sleeve only holds Next-50 while Nifty 500 >= its 200DMA, else cash
              (V17 exactly -- and the ledger records that the SAME signal applied to the whole book
              DESTROYS wealth, so it is used ONLY on the residual)

BETA CONTROL: fixed sizing makes beta an OUTPUT of how many names qualify. Also tested explicitly by
capping max invested fraction.

BENCHMARK RECONCILIATION (owed all session): ONE locked window, ONE script, every benchmark printed
from the same calendar so Nifty 500 / Next 50 / the book are finally comparable. Prior scripts
disagreed (Next 50 = 16.00x vs 20.46x) purely because of different start dates.

WALK-FORWARD: every headline config is re-run on 2006-2011 / 2012-2017 / 2018-2026 because Codex
flagged one-window selection as the live risk (15R), and top60 was picked from 3 sizes on one window.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH, SLEEVE = "Nifty 500", "Nifty Next 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
IDX = [BENCH, SLEEVE, "Nifty 50", "Nifty 100", "Nifty Midcap 50"]
LB, QTR, CORRWIN, ADV_BAR, COST, DEAD_VAL = 126, 63, 500, 5e7, 0.0015, -0.50

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
names = list(set(SECTORS + IDX))
iclose = defaultdict(dict)
for nm, d, c in conn.execute("SELECT index_name,trade_date,close_value FROM index_rows WHERE index_name IN (%s) AND close_value>0"
                             % ",".join("?"*len(names)), names):
    iclose[nm][d] = c
sclose = defaultdict(dict)
for s, d, c in conn.execute("SELECT symbol,trade_date,close FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') AND close>0"):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("SELECT symbol,substr(trade_date,1,7),avg(value),count(*) FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"):
    if n >= 15 and a: adv[s][ym] = a
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}; N = len(cal)

# ---- 200DMA of the benchmark, for the V17-style sleeve gate ----
b200 = [None]*N
buf = []
for i in range(N):
    buf.append(iclose[BENCH][cal[i]])
    if len(buf) > 200: buf.pop(0)
    b200[i] = sum(buf)/len(buf) if len(buf) >= 200 else None

def rsi_series(px, n=14):
    out = [None]*N; gain = loss = None; prev = None
    for i in range(N):
        p = px.get(cal[i])
        if p is None:
            out[i] = out[i-1] if i else None; continue
        if prev is None: prev = p; continue
        ch = p - prev; prev = p
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if gain is None: gain, loss = g, l
        else:
            gain = (gain*(n-1)+g)/n; loss = (loss*(n-1)+l)/n
        if loss == 0: out[i] = 100.0
        elif gain == 0: out[i] = 0.0
        else: out[i] = 100.0-100.0/(1.0+gain/loss)
    return out

def sma(x, n):
    out = [None]*len(x); buf = []
    for i, v in enumerate(x):
        if v is not None: buf.append(v)
        if len(buf) > n: buf.pop(0)
        out[i] = sum(buf)/len(buf) if len(buf) >= n else None
    return out

SYMS = [s for s, cl in sclose.items() if s not in QUAR and len(cl) >= 400]
print(f"[precompute] RSI(14)+50SMA for {len(SYMS):,} symbols...", file=sys.stderr)
RSI = {s: rsi_series(sclose[s]) for s in SYMS}
RMA = {s: sma(RSI[s], 50) for s in SYMS}

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, N)]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, N)] for nm in SECTORS}
stock_ex = {s: [((sclose[s].get(cal[i]) or 0)/(sclose[s].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                if (sclose[s].get(cal[i]) and sclose[s].get(cal[i-1])) else None
                for i in range(1, N)] for s in SYMS}

def _corr(x, y, lo, hi):
    n=0; sx=sy=sxx=syy=sxy=0.0
    for i in range(lo, hi):
        a, b = x[i], y[i]
        if a is None or b is None: continue
        n+=1; sx+=a; sy+=b; sxx+=a*a; syy+=b*b; sxy+=a*b
    if n < 100: return None
    cx, cy = sxx-sx*sx/n, syy-sy*sy/n
    if cx <= 0 or cy <= 0: return None
    return (sxy-sx*sy/n)/math.sqrt(cx*cy)

_am = {}
def assign(d):
    k = d[:4]
    if k in _am: return _am[k]
    i = ci[d]; lo = max(0, i-CORRWIN); ym = d[:7]
    out = {}
    for s in SYMS:
        if adv.get(s, {}).get(ym, 0) < ADV_BAR: continue
        best, bc = None, -9.0
        for nm in SECTORS:
            c = _corr(stock_ex[s], sec_ex[nm], lo, i)
            if c is not None and c > bc: bc, best = c, nm
        if best: out[s] = best
    _am[k] = out
    return out

def pym(d):
    y, m = int(d[:4]), int(d[5:7]); m -= 1
    if m == 0: y, m = y-1, 12
    return "%04d-%02d" % (y, m)

def pxn(s, d, back=10):
    i = ci.get(d)
    if i is None: return None
    for j in range(i, max(-1, i-back), -1):
        v = sclose[s].get(cal[j])
        if v: return v
    return None

def isdead(s, d, fwd=60):
    i = ci.get(d)
    if i is None: return True
    return not any(sclose[s].get(cal[j]) for j in range(i, min(N, i+fwd)))

def consistency(s, sec, i):
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

rebal_all = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 250)
             and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

def candidates(d, consist=0.70):
    i = ci[d]; amap = assign(d); pm = pym(d)
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        r, m = RSI[s][i], RMA[s][i]
        if r is None or m is None or r <= m: continue
        if consist is not None and (consistency(s, sec, i) or 0) < consist: continue
        out.append(s)
    return out

def run(mode="norm", topn=40, trail=0.20, slip=0.01, consist=0.70, max_inv=1.0, start=None, end=None):
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac = [], [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = candidates(d, consist)[:topn]
        if mode == "norm":
            w = {s: 1.0/len(sel) for s in sel} if sel else {}
        else:
            w = {s: min(1.0/topn, max_inv/max(len(sel), 1)) for s in sel} if sel else {}
            tot = sum(w.values())
            if tot > max_inv:
                w = {s: x*max_inv/tot for s, x in w.items()}
        turn = sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))
        nav *= (1-COST*turn)
        for s in w:
            if s not in held:
                p = pxn(s, d); ent[s] = p; pk[s] = p or 0
        held = w
        inv = sum(held.values()); invfrac.append(inv)
        r = 0.0
        for s, x in list(held.items()):
            a, b = pxn(s, d), pxn(s, dn)
            if a and b:
                hit = False
                if trail and ent.get(s):
                    for j in range(ci[d]+1, ci[dn]+1):
                        q = sclose[s].get(cal[j])
                        if not q: continue
                        if q > pk.get(s, 0): pk[s] = q
                        if q <= pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit = True; break
                if hit: del held[s]; ent.pop(s, None); pk.pop(s, None)
                else: r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]
        # ---- where does the idle money go? ----
        idle = max(0.0, 1.0 - inv)
        if idle > 0 and mode in ("sleeve", "sleeve200"):
            ok = True
            if mode == "sleeve200":
                ok = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if ok:
                a, b = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
                if a and b: r += idle*(b/a-1.0)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, invfrac

def stat(navs, bnavs):
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); y = n/4.0
    def dd(v):
        pk, mx = v[0], 0.0
        for x in v: pk = max(pk, x); mx = min(mx, x/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    sd = math.sqrt(sum((x-m)**2 for x in r)/(n-1))
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    alpha = (m - b*mb)*4
    return dict(cagr=navs[-1]**(1/y)-1, dd=dd(navs), mult=navs[-1], beta=b, alpha=alpha,
                sd=sd*2.0, geo_check=m*4 - (sd*sd*4)/2)

def go(tag, **kw):
    navs, bnavs, inv = run(**kw)
    s = stat(navs, bnavs)
    print("  %-44s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%"
          % (tag, s['cagr']*100, s['dd']*100, s['mult'], s['beta'], s['alpha']*100,
             sum(inv)/len(inv)*100), flush=True)
    return s

# ================= THE LOCKED BENCHMARK TABLE =================
print("="*118)
print("BENCHMARK RECONCILIATION — ONE window, ONE calendar, every index. (The 16.00x/20.46x")
print("disagreement in earlier scripts was purely different start dates.)")
print("="*118)
d0, d1 = rebal_all[0], rebal_all[-1]
y = (len(rebal_all)-1)/4.0
print(f"  locked window: {d0} -> {d1}  ({y:.1f}y)")
for nm in IDX:
    a, b = iclose[nm].get(d0), iclose[nm].get(d1)
    if a and b:
        print("  %-44s CAGR %5.1f%%  %26s Rs1Cr->%6.2fx" % (nm+" buy&hold", ((b/a)**(1/y)-1)*100, "", b/a))

print("\n" + "="*118)
print("WHERE DOES THE IDLE MONEY GO? (stack = RSI(14)>50SMA + consistency>=70% + trail-20% @1% slip)")
print("="*118)
go("norm: renormalize to 100% (EVERY prior test)", mode="norm")
go("cash: 1/N each, remainder DEAD CASH", mode="cash")
go("sleeve: remainder -> Nifty Next 50", mode="sleeve")
go("sleeve200: remainder -> Next50 only above 200DMA", mode="sleeve200")

print("\n--- beta control: cap the invested fraction ---")
for mi in (0.50, 0.75, 1.00):
    go(f"cash, max invested {mi*100:.0f}%", mode="cash", max_inv=mi)

print("\n--- book size, on the best sleeve mode ---")
for n in (20, 40, 60):
    go(f"sleeve200, top{n}", mode="sleeve200", topn=n)

print("\n" + "="*118)
print("WALK-FORWARD — Codex flagged one-window selection as the live risk (15R)")
print("="*118)
for tag, st, en in (("2006-2011", "2006-01-01", "2011-12-31"),
                    ("2012-2017", "2012-01-01", "2017-12-31"),
                    ("2018-2026", "2018-01-01", "2026-12-31")):
    print(f"  --- {tag} ---")
    for mode in ("norm", "cash", "sleeve200"):
        navs, bnavs, inv = run(mode=mode, start=st, end=en)
        if len(navs) < 8: print(f"    {mode}: too short"); continue
        s = stat(navs, bnavs)
        bs = bnavs[-1]**(1/(len(navs)/4.0))-1
        print("    %-18s CAGR %5.1f%%  vs bench %5.1f%%  MaxDD %6.1f%%  beta %5.2f  alpha %+5.1f%%"
              % (mode, s['cagr']*100, bs*100, s['dd']*100, s['beta'], s['alpha']*100))
