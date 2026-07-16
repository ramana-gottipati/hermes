"""CATCH THE TURN, NOT THE TREND (Ramana, 2026-07-15)

Ramana: "if you keep going behind the first rank, it is already first rank. You will not be able
to participate in the run, so we need to focus on recovery... You should identify the stocks or
sectors BEFORE they have moved significantly. We need to determine when the reversal began."

LEDGER BLOCK CITED (failure-ledger discipline): the REVERSAL FAMILY is falsified at EVERY level
(07-13 timing; 07-14b FRACTAL FENCES -- "every fence fails; the reversal-pair program closes with
ZERO tradeable survivors"). THIS IS A DIFFERENT SIGNAL: those tested PRICE bouncing off a support
band (mean reversion). This tests a RELATIVE-STRENGTH TURN -- was lagging its sector, has just
started leading. Precedent that SUCCEEDED: V19 the recovery-accelerator, live inside V21 today.

WHY 15P PREDICTS THIS COULD WIN: the top RS decile carries 26.63%/qtr vol and pays a 3.55%/qtr
variance toll against a 1.97% edge -- you buy the END of a move at PEAK volatility. A name that
has NOT run yet has not built that volatility. If the turn carries a similar edge at lower vol,
its GEOMETRIC return wins even with a smaller mean.

THE 2x2 (all excess vs Nifty 500, adjusted prices, PIT, stocks inside QUALIFYING sectors):
    PRIOR  = excess over months 6->3 ago     RECENT = excess over the last 3 months
    was BEHIND, now AHEAD  -> THE TURN        (Ramana's idea)
    was AHEAD,  now AHEAD  -> ESTABLISHED LEADER (what the book buys today)
    was AHEAD,  now BEHIND -> FADING
    was BEHIND, now BEHIND -> LAGGARD
Reported with mean, sd AND geometric -- because 15P proved the mean is not what compounds.
Also run at the SECTOR level ("identify the SECTORS before they have moved").
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
H, FWD, CORRWIN, ADV_BAR, SEC_BAND = 63, 63, 500, 5e7, 0.08   # H = 3-month leg

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

rebal = [d for i, d in enumerate(cal) if i >= CORRWIN+2*H and i+FWD < len(cal)
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

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    if len(x) < 2: return float('nan')
    m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))

def report(title, cells, note=""):
    print("\n" + "="*104)
    print(title)
    if note: print(note)
    print("="*104)
    print("  %-40s%8s%10s%10s%9s%11s%9s" % ("cell", "n", "mean/qtr", "sd/qtr", "drag", "GEO/qtr", "-> /yr"))
    rows = []
    for k in ("TURN (was behind, now ahead)", "ESTABLISHED LEADER (behind->no, ahead->ahead)",
              "FADING (was ahead, now behind)", "LAGGARD (behind, still behind)"):
        x = cells.get(k, [])
        if len(x) < 30: continue
        m, s_ = mean(x), sd(x); drag = s_*s_/2; geo = m-drag
        rows.append((geo, k, len(x), m, s_, drag))
        print("  %-40s%8d%9.2f%%%9.2f%%%8.2f%%%10.2f%%%8.1f%%" % (k, len(x), m*100, s_*100, drag*100, geo*100, geo*4*100))
    if rows:
        rows.sort(reverse=True)
        print(f"\n  BEST BY GEOMETRIC: {rows[0][1]}   (mean {rows[0][3]*100:+.2f}%, sd {rows[0][4]*100:.2f}%)")

# ---------------- STOCK level, inside qualifying sectors ----------------
cells = defaultdict(list)
for d in rebal:
    i = ci[d]
    d_prior0, d_mid, d_now, d_fwd = cal[i-2*H], cal[i-H], d, cal[i+FWD]
    qs = [nm for nm in SECTORS if (exc(iclose[nm], cal[i-2*H], d, iclose[BENCH]) or -9) > SEC_BAND]
    if not qs: continue
    amap = assign(d); ym = d[:7]
    bf = iclose[BENCH][d_fwd]/iclose[BENCH][d]-1.0
    for s_, sec in amap.items():
        if sec not in qs: continue
        if adv.get(s_, {}).get(ym, 0) < ADV_BAR: continue
        prior  = exc(sclose[s_], d_prior0, d_mid, iclose[sec])   # vs its OWN sector
        recent = exc(sclose[s_], d_mid, d_now, iclose[sec])
        if prior is None or recent is None: continue
        f, c0 = sclose[s_].get(d_fwd), sclose[s_].get(d)
        if not (f and c0): continue
        fwd = (f/c0-1.0)-bf
        if   prior <= 0 and recent > 0: k = "TURN (was behind, now ahead)"
        elif prior >  0 and recent > 0: k = "ESTABLISHED LEADER (behind->no, ahead->ahead)"
        elif prior >  0 and recent <=0: k = "FADING (was ahead, now behind)"
        else:                           k = "LAGGARD (behind, still behind)"
        cells[k].append(fwd)

report("STOCKS inside qualifying sectors: THE TURN vs THE ESTABLISHED LEADER",
       cells,
       "RS measured vs the stock's OWN sector. Forward 3m excess vs Nifty 500. "
       "15P: the mean is not what compounds -- read the GEO column.")

# ---------------- SECTOR level ----------------
scells = defaultdict(list)
for d in rebal:
    i = ci[d]
    d0, dm, dfw = cal[i-2*H], cal[i-H], cal[i+FWD]
    bf = iclose[BENCH][dfw]/iclose[BENCH][d]-1.0
    for nm in SECTORS:
        prior  = exc(iclose[nm], d0, dm, iclose[BENCH])
        recent = exc(iclose[nm], dm, d, iclose[BENCH])
        if prior is None or recent is None: continue
        a, b = iclose[nm].get(d), iclose[nm].get(dfw)
        if not (a and b): continue
        fwd = (b/a-1.0)-bf
        if   prior <= 0 and recent > 0: k = "TURN (was behind, now ahead)"
        elif prior >  0 and recent > 0: k = "ESTABLISHED LEADER (behind->no, ahead->ahead)"
        elif prior >  0 and recent <=0: k = "FADING (was ahead, now behind)"
        else:                           k = "LAGGARD (behind, still behind)"
        scells[k].append(fwd)

report("SECTORS: THE TURN vs THE ESTABLISHED LEADER  <- 'identify the sectors BEFORE they have moved'",
       scells,
       "Sector excess vs Nifty 500. This is the V24 entry rule's alternative: buy the TURN, not the leader.")
