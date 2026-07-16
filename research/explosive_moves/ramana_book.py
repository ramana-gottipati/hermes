"""RAMANA'S DESIGN, RUN: RS-crossed-50DMA sector gate -> stocks from those sectors.

Ramana: "any sector whose RS crossed 50 DMA, lets consider the stocks from them?"

Blocker cleared inline: corporate_actions is ~30% incomplete (1,224 recorded, ~522 missing --
detected by their fingerprint: a one-day drop landing within 4% of an EXACT split ratio, with no
recorded action. Real stocks do not fall exactly 50.0% or 90.0% by coincidence). Those holes were
making TATAMOTORS read 0.0%/yr over 21 years and ITC -0.8%. This script INFERS them from the
price series, then validates the repair before running anything.

Gate comparison is from rs_50dma.py (index data, adjusted, trustworthy):
    NO GATE        mean -0.02%/qtr  sd 9.23%
    V24 +8% gate   mean -0.70%/qtr  sd 9.77%   <- what runs live; WORSE THAN NO GATE
    RS X 50DMA     mean +0.28%/qtr  sd 8.58%   <- Ramana's: best mean, LOWEST vol
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_closes

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
MA, LB, VOLWIN, ADV_BAR, COST, CORRWIN = 50, 126, 126, 5e7, 0.0015, 500
DEAD_VAL, MIN_MOVE_FRAC = -0.50, 0.60

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
sclose = defaultdict(dict)
for s, d, c in conn.execute("""SELECT symbol, trade_date, close FROM bhavcopy_rows
    WHERE series IN ('EQ','BE','BZ') AND close>0"""):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= 15 and a: adv[s][ym] = a
fac = load_factors(conn)
ca = defaultdict(set)
for s, ex in conn.execute("""SELECT symbol, ex_date FROM corporate_actions
       WHERE ex_date IS NOT NULL AND action_type IN ('SPLIT','BONUS')"""):
    ca[s].add(ex)   # ONLY split/bonus. Excluding on dividends masked ITC's real splits.
conn.close()

def _k(d): return int(d[:4])*372 + int(d[5:7])*31 + int(d[8:10])

# ---------- PATCH: infer the missing SPLIT/BONUS events from their fingerprint ----------
TARGETS = (0.500, 0.333, 0.400, 0.200, 0.100, 0.250, 0.667)
inferred = 0
for s, cl in sclose.items():
    ds = sorted(cl)
    add = []
    for i in range(1, len(ds)):
        a, b = cl[ds[i-1]], cl[ds[i]]
        if a <= 0 or b/a > 0.60:
            continue
        if any(abs(_k(x) - _k(ds[i])) <= 5 for x in ca.get(s, ())):
            continue                                    # already recorded -> load_factors has it
        r = b/a
        for t in TARGETS:
            if abs(r - t)/t < 0.04:                     # lands on an EXACT split ratio
                add.append((ds[i], 1.0/t)); inferred += 1
                break
    if add:
        fac.setdefault(s, [])
        fac[s] = sorted(fac[s] + add)
print(f"[patch] {inferred} missing SPLIT/BONUS events inferred from price fingerprints", file=sys.stderr)

for s in list(sclose):
    if s in fac:
        sclose[s] = adjust_closes(sclose[s], fac[s])

# ---------- VALIDATE the repair before trusting anything ----------
print("\n### VALIDATION — do the known-broken names read sanely now?")
print("  %-12s %10s   (was, unpatched)" % ("symbol", "adj CAGR"))
for sym, before in (("TATAMOTORS", "0.0%"), ("ITC", "-0.8%"), ("RELIANCE", "15.1%"),
                    ("HDFCBANK", "18.8%"), ("TCS", "14.0%")):
    cl = sclose.get(sym)
    if not cl: continue
    ds = sorted(cl); d0, d1 = ds[0], ds[-1]
    y = (int(d1[:4])-int(d0[:4])) + (int(d1[5:7])-int(d0[5:7]))/12.0
    print("  %-12s %9.1f%%   (was %s)" % (sym, ((cl[d1]/cl[d0])**(1/y)-1)*100, before))

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}
rs_line, rs_ma = {}, {}
for nm in SECTORS:
    line = [ (iclose[nm].get(d)/iclose[BENCH][d]) if iclose[nm].get(d) else None for d in cal ]
    rs_line[nm] = line
    ma = []
    for i in range(len(cal)):
        w = [x for x in line[max(0,i-MA+1):i+1] if x is not None]
        ma.append(sum(w)/len(w) if len(w) >= MA*0.8 else None)
    rs_ma[nm] = ma

rebal = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

def crossed_up(nm, i, within=20):
    l, m = rs_line[nm], rs_ma[nm]
    if l[i] is None or m[i] is None or l[i] <= m[i]: return False
    return any(l[j] is not None and m[j] is not None and l[j] <= m[j]
               for j in range(max(0,i-within), i))

def prev_ym(d):
    y, m = int(d[:4]), int(d[5:7]); m -= 1
    if m == 0: y, m = y-1, 12
    return f"{y:04d}-{m:02d}"

def px_near(s, d, back=10):
    i = ci.get(d); cl = sclose[s]
    if i is None: return None
    for j in range(i, max(-1, i-back), -1):
        if cl.get(cal[j]): return cl[cal[j]]
    return None

def is_dead(s, d, fwd=60):
    i = ci.get(d)
    if i is None: return True
    return not any(sclose[s].get(cal[j]) for j in range(i, min(len(cal), i+fwd)))

_vol = {}
def vol_at(s, d):
    k = (s, d)
    if k in _vol: return _vol[k]
    i = ci[d]; cl = sclose[s]; r = []
    for j in range(max(0,i-VOLWIN)+1, i+1):
        a, b = cl.get(cal[j-1]), cl.get(cal[j])
        if a and b: r.append(b/a-1.0)
    if len(r) < 60 or sum(1 for x in r if abs(x) > 1e-6)/len(r) < MIN_MOVE_FRAC:
        _vol[k] = None; return None
    m = sum(r)/len(r); v = math.sqrt(sum((x-m)**2 for x in r)/(len(r)-1))
    _vol[k] = v if v > 1e-5 else None
    return _vol[k]

_corr_c = {}
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

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, len(cal))]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, len(cal))] for nm in SECTORS}
stock_ex = {}
for s_, cl in sclose.items():
    if len(cl) < 300: continue
    stock_ex[s_] = [((cl.get(cal[i]) or 0)/(cl.get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                    if (cl.get(cal[i]) and cl.get(cal[i-1])) else None for i in range(1, len(cal))]

_amap = {}
def assign(d):
    k = d[:4]
    if k in _amap: return _amap[k]
    i = ci[d]; lo, hi = max(0, i-CORRWIN), i; pm = prev_ym(d)
    out = {}
    for s_ in stock_ex:
        if adv.get(s_, {}).get(pm, 0) < ADV_BAR: continue
        best, bc = None, -9.0
        for nm in SECTORS:
            c = _corr(stock_ex[s_], sec_ex[nm], lo, hi)
            if c is not None and c > bc: bc, best = c, nm
        if best: out[s_] = best
    _amap[k] = out
    return out

def book(d, gate, topn, weight):
    i = ci[d]; d0 = cal[i-LB]
    if gate == "CROSS":   qs = [nm for nm in SECTORS if crossed_up(nm, i)]
    elif gate == "V24":
        qs = [nm for nm in SECTORS
              if iclose[nm].get(d) and iclose[nm].get(d0)
              and (iclose[nm][d]/iclose[nm][d0]-1.0)-(iclose[BENCH][d]/iclose[BENCH][d0]-1.0) > 0.08]
    else: qs = list(SECTORS)
    if not qs: return {}, qs
    amap = assign(d); pm = prev_ym(d)
    br = iclose[BENCH][d]/iclose[BENCH][d0]-1.0
    cands = []
    for s_, sec in amap.items():
        if sec not in qs: continue
        if adv.get(s_, {}).get(pm, 0) < ADV_BAR: continue
        a, b = sclose[s_].get(d0), sclose[s_].get(d)
        if not (a and b): continue
        cands.append(((b/a-1.0)-br, s_))
    cands.sort(reverse=True)
    sel = [s for e, s in cands[:topn] if e > 0]
    if not sel: return {}, qs
    if weight == "EW":
        w = 1.0/len(sel); return {s: w for s in sel}, qs
    iv = {s: 1.0/vol_at(s, d) for s in sel if vol_at(s, d)}
    if not iv: return {}, qs
    t = sum(iv.values())
    return {s: x/t for s, x in iv.items()}, qs

def run(gate, weight, topn=40):
    nav = bnav = 1.0; navs, bnavs, held, nsec = [], [], {}, []
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        w, qs = book(d, gate, topn, weight)
        nsec.append(len(qs))
        if w:
            turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
            nav *= (1-COST*turn); held = w
        r = 0.0
        for s, x in held.items():
            a, b = px_near(s, d), px_near(s, dn)
            if a and b: r += x*(b/a-1.0)
            elif a and is_dead(s, dn): r += x*DEAD_VAL
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, nsec

def show(tag, gate, weight, topn=40):
    navs, bnavs, nsec = run(gate, weight, topn)
    r  = [navs[i]/navs[i-1]-1 for i in range(1,len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1,len(bnavs))]
    n = len(r); yrs = n/4.0
    def _dd(nv):
        pk, mx = nv[0], 0.0
        for v in nv: pk = max(pk,v); mx = min(mx, v/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((v-mb)**2 for v in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    beta = cov/vb if vb else 0.0
    print("  %-38s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%7.2fx  beta %.2f  alpha %+5.1f%%  sect/q %.1f"
          % (tag, (navs[-1]**(1/yrs)-1)*100, _dd(navs)*100, navs[-1], beta, (m-beta*mb)*4*100,
             sum(nsec)/len(nsec)))
    return navs, bnavs

print("\n" + "="*118)
print("RAMANA'S DESIGN — RS-crossed-50DMA gate -> stocks from those sectors (patched prices)")
print("="*118)
navs, bnavs, _ = run("NONE", "EW")
r = [bnavs[i]/bnavs[i-1]-1 for i in range(1,len(bnavs))]
yrs = len(r)/4.0
def _dd(nv):
    pk, mx = nv[0], 0.0
    for v in nv: pk = max(pk,v); mx = min(mx, v/pk-1)
    return mx
print("  %-38s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%7.2fx" %
      ("NIFTY 500 (benchmark)", (bnavs[-1]**(1/yrs)-1)*100, _dd(bnavs)*100, bnavs[-1]))
print()
show("RAMANA: 50DMA-CROSS gate, inv-vol", "CROSS", "INVVOL")
show("RAMANA: 50DMA-CROSS gate, equal-wt", "CROSS", "EW")
show("V24 gate (+8%), inv-vol  [live rule]", "V24", "INVVOL")
show("NO gate, inv-vol  [no sectors]", "NONE", "INVVOL")
