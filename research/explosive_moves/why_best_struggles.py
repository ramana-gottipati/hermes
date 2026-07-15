"""WHY does "the best of the best of the best" STRUGGLE? (Ramana, 2026-07-15)

The paradox: V24 holding the sector INDICES gets 17.3% CAGR. Picking the best STOCKS inside those
same qualifying sectors gets 7.1%. Buying the whole sector beats cherry-picking its champions by
~10pp. That should be impossible if selection works.

HYPOTHESIS (mechanical, not behavioural): "beat your OWN sector index by X%" is a SMALL-CAP FILTER
IN DISGUISE. If Reliance is ~40% of Nifty Energy and rises 30%, the index rises ~12% too, so
Reliance's EXCESS over its own index is small BY CONSTRUCTION. A dominant constituent cannot beat
the index it dominates. Only small tail members can post a big excess. So the filter does not
select quality -- it selects SMALLNESS, and small Indian mid-caps mean-revert.

TESTS (all on corporate-action-ADJUSTED prices, EQ+BE+BZ, PIT):
  1. Is a stock's excess-vs-own-sector NEGATIVELY related to its size (ADV rank in the sector)?
     -> if yes, the filter is an inverse-size screen.
  2. Forward 3m return by excess-vs-sector decile WITHIN qualifying sectors
     -> where does "best of best" actually land vs the sector's own average?
  3. What does the SECTOR INDEX return over the same forward window?
     -> the honest yardstick the stock picks must beat.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
LB, FWD, CORRWIN, ADV_BAR, SEC_BAND = 126, 63, 500, 5e7, 0.08

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}
sclose = defaultdict(dict)
for s, d, c in conn.execute("""SELECT symbol, trade_date, close FROM bhavcopy_rows
    WHERE series IN ('EQ','BE','BZ') AND close>0"""):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= 15 and a:
        adv[s][ym] = a
fac = load_factors(conn); nadj = adjust_all(sclose, fac); conn.close()
print(f"[adjust] {nadj:,} symbols adjusted", file=sys.stderr)

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, len(cal))]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, len(cal))] for nm in SECTORS}
stock_ex = {}
for s_, cl in sclose.items():
    if len(cl) < 300: continue
    stock_ex[s_] = [((cl.get(cal[i]) or 0)/(cl.get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                    if (cl.get(cal[i]) and cl.get(cal[i-1])) else None for i in range(1, len(cal))]

rebal = [d for i, d in enumerate(cal) if i >= CORRWIN+LB and i+FWD < len(cal)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

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

_cache = {}
def assign(d):
    k = d[:4]
    if k in _cache: return _cache[k]
    i = ci[d]; lo, hi = max(0, i-CORRWIN), i; ym = d[:7]
    out = {}
    for s_ in stock_ex:
        if adv.get(s_, {}).get(ym, 0) < ADV_BAR: continue
        best, bc = None, -9.0
        for nm in SECTORS:
            c = _corr(stock_ex[s_], sec_ex[nm], lo, hi)
            if c is not None and c > bc: bc, best = c, nm
        if best: out[s_] = best
    _cache[k] = out
    return out

def exc(px, d0, d1, ref):
    a, b, ra, rb = px.get(d0), px.get(d1), ref.get(d0), ref.get(d1)
    return None if not (a and b and ra and rb) else (b/a-1.0)-(rb/ra-1.0)

# ---- collect ----
size_pairs = []                       # (adv_pctile_in_sector, excess_vs_sector)
dec_fwd = defaultdict(list)           # decile -> forward 3m excess vs BENCH
pool_fwd, idx_fwd = [], []
for d in rebal:
    i = ci[d]; d0, df = cal[i-LB], cal[i+FWD]
    qs = [nm for nm in SECTORS if (exc(iclose[nm], d0, d, iclose[BENCH]) or -9) > SEC_BAND]
    if not qs: continue
    amap = assign(d); ym = d[:7]
    bf = iclose[BENCH][df]/iclose[BENCH][d]-1.0
    for nm in qs:
        pool = []
        for s_, sec in amap.items():
            if sec != nm: continue
            a = adv.get(s_, {}).get(ym, 0)
            if a < ADV_BAR: continue
            e_sec = exc(sclose[s_], d0, d, iclose[nm])
            if e_sec is None: continue
            f = sclose[s_].get(df)
            c0 = sclose[s_].get(d)
            fwd = (f/c0-1.0)-bf if (f and c0) else None
            pool.append((e_sec, a, fwd, s_))
        if len(pool) < 8: continue
        pool.sort(key=lambda t: t[1])                       # by ADV
        rank = {t[3]: (j+0.5)/len(pool) for j, t in enumerate(pool)}
        for e_sec, a, fwd, s_ in pool:
            size_pairs.append((rank[s_], e_sec))
            if fwd is not None: pool_fwd.append(fwd)
        ordered = sorted(pool, key=lambda t: t[0])          # by excess-vs-sector
        n = len(ordered)
        for j, (e_sec, a, fwd, s_) in enumerate(ordered):
            if fwd is None: continue
            dec_fwd[min(int(j/n*10), 9)].append(fwd)
        fi = (iclose[nm][df]/iclose[nm][d]-1.0)-bf
        idx_fwd.append(fi)

def mean(x): return sum(x)/len(x) if x else float('nan')
def pcorr(pairs):
    n = len(pairs)
    sx = sum(a for a,_ in pairs); sy = sum(b for _,b in pairs)
    sxx = sum(a*a for a,_ in pairs); syy = sum(b*b for _,b in pairs)
    sxy = sum(a*b for a,b in pairs)
    cx, cy = sxx-sx*sx/n, syy-sy*sy/n
    return (sxy-sx*sy/n)/math.sqrt(cx*cy)

print("="*94)
print("WHY DOES 'BEST OF BEST OF BEST' STRUGGLE?  (adjusted prices, stocks inside QUALIFYING sectors)")
print("="*94)

print(f"\n### TEST 1 — is 'beat your own sector' really an INVERSE-SIZE screen?")
print(f"  corr(ADV percentile within sector, excess-vs-own-sector) = {pcorr(size_pairs):+.3f}")
print(f"  (n={len(size_pairs):,} stock-quarters.  NEGATIVE => the bigger you are, the less you can")
print(f"   beat the index you dominate => the filter selects SMALLNESS, not quality)")
lo = [e for r, e in size_pairs if r <= 0.2]; hi = [e for r, e in size_pairs if r >= 0.8]
print(f"  mean excess-vs-sector | smallest 20% by ADV: {mean(lo)*100:+6.2f}%")
print(f"  mean excess-vs-sector | largest  20% by ADV: {mean(hi)*100:+6.2f}%")

print(f"\n### TEST 2 — forward 3m excess (vs Nifty 500) by excess-vs-sector decile, WITHIN qualifying sectors")
for j in range(10):
    tag = "  <- we buy here" if j == 9 else ("  <- worst in sector" if j == 0 else "")
    print(f"  decile {j+1:2d} (n={len(dec_fwd[j]):5d}): {mean(dec_fwd[j])*100:+6.2f}%{tag}")

print(f"\n### TEST 3 — the yardstick")
print(f"  ALL stocks in qualifying sectors (equal-weight): {mean(pool_fwd)*100:+6.2f}%")
print(f"  the SECTOR INDEX itself                        : {mean(idx_fwd)*100:+6.2f}%   <- what V24 buys")
print(f"  top decile (what the stock book buys)          : {mean(dec_fwd[9])*100:+6.2f}%")
print(f"\n  index minus top-decile = {(mean(idx_fwd)-mean(dec_fwd[9]))*100:+.2f}%/quarter")
print(f"  index minus equal-weight pool = {(mean(idx_fwd)-mean(pool_fwd))*100:+.2f}%/quarter  <- the CAP-WEIGHT effect")


def sd(x):
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


print("\n" + "=" * 94)
print("### TEST 4 - VOLATILITY DRAG: is the positive EDGE being eaten by variance?")
print("=" * 94)
print("  arithmetic mean is NOT what compounds. Geometric ~ mean - sd^2/2.")
print("  %-34s%10s%10s%9s%10s%9s" % ("", "mean/qtr", "sd/qtr", "drag", "geo/qtr", "-> /yr"))
for tag, x in (("SECTOR INDEX (what V24 buys)", idx_fwd),
               ("stock pool, equal-weight", pool_fwd),
               ("TOP DECILE (the stock book)", dec_fwd[9]),
               ("mid decile 6", dec_fwd[5])):
    m, s_ = mean(x), sd(x)
    drag = s_ * s_ / 2
    geo = m - drag
    print("  %-34s%9.2f%%%9.2f%%%8.2f%%%9.2f%%%8.1f%%" %
          (tag, m*100, s_*100, drag*100, geo*100, geo*4*100))
print("\n  If GEO flips the ranking that MEAN implied, the edge is REAL but the SIZING is wrong:")
print("  the cure is not better selection -- it is inverse-vol weighting + wider diversification.")
