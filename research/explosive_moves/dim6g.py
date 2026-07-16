"""6g CROSS-SECTIONAL RANK CLIMB — clean standalone, threshold swept.

Prior attempts emitted ~0 picks. Diagnosis (measured): on a representative date there are 309
assigned stocks across 11 sectors of 6+ members, ALL with valid RS at i and i-21. So the universe
is fine -- the emission logic in the patched file was crossed (g_res vs g_multi). This is a clean
rewrite: rank each stock WITHIN its sector by RS today vs ~21 trading days ago, pick those whose
percentile RANK rose across a swept set of thresholds. Same forward-3m-excess decomposition and
no-selection baseline as dim6.py so numbers compare directly.
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
FWD, CORRWIN, ADV_BAR, LOOKBACK = 63, 500, 5e7, 21

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
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _ = _q.build(conn, _raw, sclose)
conn.close()

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}; N = len(cal)
SYMS = [s for s, cl in sclose.items() if s not in QUAR and len(cl) >= 400]

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, N)]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, N)] for nm in SECTORS}
stock_ex = {s: [((sclose[s].get(cal[i]) or 0)/(sclose[s].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                if (sclose[s].get(cal[i]) and sclose[s].get(cal[i-1])) else None for i in range(1, N)] for s in SYMS}

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

def rs(s, sec, j):
    a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
    return a/b if (a and b) else None

rebal = [d for i, d in enumerate(cal) if i >= max(CORRWIN, 130) and i+FWD < len(cal)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(SYMS):,} symbols | {len(rebal)} quarterly dates", file=sys.stderr)

# variants: (then_below, now_above, min_climb)
VARIANTS = [("bottom-half -> top-half", 0.50, 0.50, None),
            ("bottom-third -> top-half", 0.33, 0.50, None),
            ("bottom-40% -> top-40%", 0.40, 0.60, None),
            ("climb >= +30 pctile", None, None, 0.30),
            ("climb >= +20 pctile", None, None, 0.20)]

res = defaultdict(list); base = []
for d in rebal:
    i = ci[d]; df = cal[i+FWD]
    amap = assign(d); ym = d[:7]
    bf = iclose[BENCH][df]/iclose[BENCH][d]-1.0
    def fwd(s):
        a, b = sclose[s].get(d), sclose[s].get(df)
        return (b/a-1.0)-bf if (a and b) else None
    bysec = defaultdict(list)
    for s, sec in amap.items():
        if adv.get(s, {}).get(ym, 0) >= ADV_BAR:
            bysec[sec].append(s)
    for sec, mem in bysec.items():
        now, then = [], []
        for s in mem:
            a, b = rs(s, sec, i), rs(s, sec, i-LOOKBACK)
            if a is None or b is None: continue
            now.append((a, s)); then.append((b, s))
        if len(now) < 6: continue
        now.sort(); then.sort(); nn = len(now)
        rn = {s: k/nn for k, (_, s) in enumerate(now)}
        rt = {s: k/nn for k, (_, s) in enumerate(then)}
        for s in rn:
            if s not in rt: continue
            f = fwd(s)
            if f is None: continue
            base.append(f)   # every ranked stock is a baseline obs (dup across sectors is fine; it's the pool)
            for label, tb, na, mc in VARIANTS:
                if mc is not None:
                    if (rn[s]-rt[s]) >= mc: res[label].append(f)
                else:
                    if rt[s] < tb and rn[s] >= na: res[label].append(f)

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1)) if len(x) > 1 else float('nan')

m0, s0 = mean(base), sd(base); se0 = s0/math.sqrt(len(base))
print("\n" + "="*100)
print("6g CROSS-SECTIONAL RANK CLIMB — threshold sweep (forward 3m excess vs Nifty 500)")
print("="*100)
print("  %-40s%8s%10s%9s%10s%9s" % ("variant", "n", "mean/qtr", "sd/qtr", "GEO/qtr", "vs base"))
print("  %-40s%8d%9.2f%%%9.2f%%%9.2f%%%9s   <- ranked-pool baseline (+/-%.2f%%)"
      % ("(all ranked stocks)", len(base), m0*100, s0*100, (m0-s0*s0/2)*100, "--", se0*100))
for label, *_ in VARIANTS:
    x = res[label]
    if len(x) < 30:
        print("  %-40s%8d   too few" % (label, len(x))); continue
    m, s_ = mean(x), sd(x); geo = m - s_*s_/2; delta = m - m0
    se = s_/math.sqrt(len(x))
    sig = "SIG" if abs(delta) > 2*math.sqrt(se**2+se0**2) else "ns"
    print("  %-40s%8d%9.2f%%%9.2f%%%9.2f%%%+8.2f%% %s" % (label, len(x), m*100, s_*100, geo*100, delta*100, sig))
