"""DOES THE BE-VETO SHRINK THE VOLATILITY TOLL? (Ramana approved, 2026-07-16)

The hypothesis is precise, so the test is precise. 15P measured the top RS decile:
    mean +1.97%/qtr | sd 26.63%/qtr | drag (sd^2/2) 3.55% | GEOMETRIC -1.58%
i.e. the edge is real but the variance toll eats it. 15L found strong-RS stocks are moved to NSE's
BE surveillance series more often than average. IF a meaningful share of that 26.63% sd is
surveillance-flagged speculative names, THEN vetoing BE should cut sd (and the drag) while leaving
the mean roughly intact -> geometric improves. If sd does NOT move, the hypothesis is dead and BE
membership is just noise.

Also runs the fundamentals veto (Ramana: track picks WITHOUT fundamentals too -- so every cell is
reported both ways).

Measures forward 3m excess vs Nifty 500 for the TOP DECILE by own-sector RS, PIT, adjusted prices,
quarantined. Same harness family as why_best_struggles.py so the numbers are comparable to 15P.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q
import vetoes as V

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
RDB = sys.argv[2] if len(sys.argv) > 2 else "data/research.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
LB, FWD, CORRWIN, ADV_BAR, SEC_BAND = 126, 63, 500, 5e7, 0.08

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
QUAR, _qd = _q.build(conn, _raw, sclose)
BE = V.load_be_history(conn)
conn.close()
print(f"[quarantine] {len(QUAR)} symbols excluded", file=sys.stderr)
print(f"[BE] {len(BE):,} symbols have BE history", file=sys.stderr)

rconn = sqlite3.connect(f"file:{RDB}?mode=ro", uri=True)
FUND = V.load_fundamentals(rconn)
rconn.close()
print(f"[fundamentals] {len(FUND):,} symbols (SCREENER-sourced — Guardrail #8 disclosure)", file=sys.stderr)

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}
bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, len(cal))]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, len(cal))] for nm in SECTORS}
stock_ex = {}
for s_, cl in sclose.items():
    if s_ in QUAR or len(cl) < 300: continue
    stock_ex[s_] = [((cl.get(cal[i]) or 0)/(cl.get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                    if (cl.get(cal[i]) and cl.get(cal[i-1])) else None for i in range(1, len(cal))]

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
    i = ci[d]; lo, hi = max(0, i-CORRWIN), i; ym = d[:7]
    out = {}
    for s_ in stock_ex:
        if adv.get(s_, {}).get(ym, 0) < ADV_BAR: continue
        best, bc = None, -9.0
        for nm in SECTORS:
            c = _corr(stock_ex[s_], sec_ex[nm], lo, hi)
            if c is not None and c > bc: bc, best = c, nm
        if best: out[s_] = best
    _am[k] = out
    return out

def exc(px, d0, d1, ref):
    a, b, ra, rb = px.get(d0), px.get(d1), ref.get(d0), ref.get(d1)
    return None if not (a and b and ra and rb) else (b/a-1.0)-(rb/ra-1.0)

rebal = [d for i, d in enumerate(cal) if i >= CORRWIN+LB and i+FWD < len(cal)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

def collect(veto_be, veto_fund, be_lookback=6):
    """forward 3m excess for the TOP DECILE by own-sector RS, under the given vetoes"""
    out, removed_be, removed_fu, total = [], 0, 0, 0
    for d in rebal:
        i = ci[d]; d0, df = cal[i-LB], cal[i+FWD]
        qs = [nm for nm in SECTORS if (exc(iclose[nm], d0, d, iclose[BENCH]) or -9) > SEC_BAND]
        if not qs: continue
        amap = assign(d); ym = d[:7]
        bf = iclose[BENCH][df]/iclose[BENCH][d]-1.0
        pool = []
        for s_, sec in amap.items():
            if sec not in qs: continue
            if adv.get(s_, {}).get(ym, 0) < ADV_BAR: continue
            e = exc(sclose[s_], d0, d, iclose[sec])
            if e is None: continue
            total += 1
            if veto_be and V.be_flagged(BE, s_, d, be_lookback):
                removed_be += 1; continue
            if veto_fund and V.fundamentals_veto(FUND, s_, d):
                removed_fu += 1; continue
            f, c0 = sclose[s_].get(df), sclose[s_].get(d)
            if not (f and c0): continue
            pool.append((e, (f/c0-1.0)-bf))
        if len(pool) < 8: continue
        pool.sort()
        dec = max(len(pool)//10, 1)
        out += [fwd for _, fwd in pool[-dec:]]
    return out, removed_be, removed_fu, total

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1)) if len(x) > 1 else float('nan')

print("\n" + "="*104)
print("DOES THE BE-VETO SHRINK THE VOLATILITY TOLL? (top RS decile, fwd 3m excess vs Nifty 500)")
print("15P baseline for reference:  mean +1.97%  sd 26.63%  drag 3.55%  GEO -1.58%")
print("="*104)
print("  %-40s%7s%10s%9s%8s%10s" % ("config", "n", "mean/qtr", "sd/qtr", "drag", "GEO/qtr"))
rows = []
for tag, vb, vf in (("baseline (no vetoes)", False, False),
                    ("+ BE veto (flagged last 6m)", True, False),
                    ("+ fundamentals veto only", False, True),
                    ("+ BOTH vetoes", True, True)):
    x, rbe, rfu, tot = collect(vb, vf)
    if not x: print("  %-40s  no data" % tag); continue
    m, s_ = mean(x), sd(x); drag = s_*s_/2; geo = m-drag
    rows.append((tag, m, s_, geo, rbe, rfu, tot))
    print("  %-40s%7d%9.2f%%%9.2f%%%8.2f%%%9.2f%%" % (tag, len(x), m*100, s_*100, drag*100, geo*100))

print("\n  how much each veto removed (of all sector-qualified candidate stock-quarters):")
for tag, m, s_, geo, rbe, rfu, tot in rows:
    if tot: print("    %-40s BE removed %5d (%4.1f%%) | fundamentals removed %5d (%4.1f%%)"
                  % (tag, rbe, rbe/tot*100, rfu, rfu/tot*100))

print("\n  BE lookback sensitivity (does 'how recently flagged' matter?):")
for lb in (0, 3, 12, 24):
    x, rbe, _, tot = collect(True, False, be_lookback=lb)
    if not x: continue
    m, s_ = mean(x), sd(x); geo = m - s_*s_/2
    print("    BE flagged within %2dm: n=%5d  mean %+6.2f%%  sd %6.2f%%  GEO %+6.2f%%  (removed %4.1f%%)"
          % (lb, len(x), m*100, s_*100, geo*100, rbe/tot*100 if tot else 0))

if rows:
    base = rows[0]
    print("\n  VERDICT:")
    for tag, m, s_, geo, rbe, rfu, tot in rows[1:]:
        dsd = s_ - base[2]; dgeo = geo - base[3]
        print("    %-40s sd %+6.2f pp | GEO %+6.2f pp  -> %s"
              % (tag, dsd, dgeo*100,
                 "HELPS" if dgeo > 0 and dsd < 0 else ("mixed" if dgeo > 0 or dsd < 0 else "no help")))
    print("\n  Hypothesis lives only if sd FALLS and GEO RISES. If sd is unmoved, BE membership is noise.")
