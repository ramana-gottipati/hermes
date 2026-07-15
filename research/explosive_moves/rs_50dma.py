"""RAMANA'S GATE: "any sector whose RS crossed 50 DMA, let's consider the stocks from them"

WHY THIS IS TRUSTWORTHY TODAY: the corporate-action holes (30% of SPLIT/BONUS missing, ~522
detected) corrupt STOCK prices only. `index_rows` is already adjusted -- indices handle splits
internally. So a SECTOR-level test needs no data fix.

THE IDEA: V24's gate waits for a sector to be +8% ahead on 6m RS -- by then the move has happened
(15P: you buy the END of the move at PEAK volatility). The RS LINE (sector / Nifty 500) crossing
its own 50-day average turns MUCH earlier. Ramana: "identify the sectors BEFORE they have moved."

GATES COMPARED (forward 3m excess vs Nifty 500, per sector-quarter):
  NO GATE        every sector, always                      <- the do-nothing baseline
  V24 GATE       6m RS excess > +8%                        <- what the live engine uses
  RS > 50DMA     the RS line is above its own 50DMA        <- a STATE
  RS X 50DMA     the RS line CROSSED above in the last N d <- an EVENT (Ramana's words)
  RS < 50DMA     below (the mirror -- if this wins, the whole premise inverts)
Reported with mean, sd AND geometric, because 15P proved the mean is not what compounds.
"""
import sqlite3, sys, math
from collections import defaultdict

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
MA, LB, FWD, BAND = 50, 126, 63, 0.08

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
conn.close()

cal = sorted(iclose[BENCH])
ci = {d: i for i, d in enumerate(cal)}

# ---- the RS LINE per sector: sector / benchmark (the ratio Ramana means) ----
rs_line, rs_ma = {}, {}
for nm in SECTORS:
    line = []
    for d in cal:
        a, b = iclose[nm].get(d), iclose[BENCH].get(d)
        line.append(a/b if (a and b) else None)
    rs_line[nm] = line
    ma = []
    for i in range(len(cal)):
        w = [x for x in line[max(0, i-MA+1):i+1] if x is not None]
        ma.append(sum(w)/len(w) if len(w) >= MA*0.8 else None)
    rs_ma[nm] = ma

rebal = [d for i, d in enumerate(cal) if i >= max(MA, LB) and i+FWD < len(cal)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(rebal)} quarterly dates {rebal[0]} -> {rebal[-1]}", file=sys.stderr)


def crossed_up(nm, i, within=20):
    """the RS line closed ABOVE its 50DMA at i, having been BELOW at some point in the last
    `within` trading days -> a fresh cross, Ramana's EVENT."""
    l, m = rs_line[nm], rs_ma[nm]
    if l[i] is None or m[i] is None or l[i] <= m[i]:
        return False
    for j in range(max(0, i-within), i):
        if l[j] is not None and m[j] is not None and l[j] <= m[j]:
            return True
    return False


cells = defaultdict(list)
counts = defaultdict(int)
for d in rebal:
    i = ci[d]
    d0, df = cal[i-LB], cal[i+FWD]
    bf = iclose[BENCH][df]/iclose[BENCH][d] - 1.0
    for nm in SECTORS:
        a, b = iclose[nm].get(d), iclose[nm].get(df)
        a0 = iclose[nm].get(d0)
        if not (a and b and a0):
            continue
        fwd = (b/a - 1.0) - bf
        ex6 = (a/a0 - 1.0) - (iclose[BENCH][d]/iclose[BENCH][d0] - 1.0)
        l, m = rs_line[nm][i], rs_ma[nm][i]
        cells["NO GATE (every sector)"].append(fwd); counts["NO GATE (every sector)"] += 1
        if ex6 > BAND:
            cells["V24 GATE (6m RS excess > +8%)"].append(fwd); counts["V24 GATE (6m RS excess > +8%)"] += 1
        if l is not None and m is not None:
            if l > m:
                cells["RS > 50DMA (state)"].append(fwd); counts["RS > 50DMA (state)"] += 1
            else:
                cells["RS < 50DMA (the mirror)"].append(fwd); counts["RS < 50DMA (the mirror)"] += 1
        if crossed_up(nm, i):
            cells["RS CROSSED 50DMA (Ramana)"].append(fwd); counts["RS CROSSED 50DMA (Ramana)"] += 1

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    if len(x) < 2: return float('nan')
    m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))

print("="*112)
print("SECTOR GATES COMPARED — forward 3m excess vs Nifty 500 (index data: adjusted, trustworthy)")
print("="*112)
print("  %-34s%7s%7s%10s%10s%9s%10s%9s" % ("gate", "n", "sect/q", "mean/qtr", "sd/qtr", "drag", "GEO/qtr", "-> /yr"))
rows = []
nq = len(rebal)
for k in ("NO GATE (every sector)", "V24 GATE (6m RS excess > +8%)", "RS > 50DMA (state)",
          "RS CROSSED 50DMA (Ramana)", "RS < 50DMA (the mirror)"):
    x = cells.get(k, [])
    if len(x) < 30:
        print(f"  {k:<34}  too few"); continue
    m, s_ = mean(x), sd(x); drag = s_*s_/2; geo = m-drag
    se = s_/math.sqrt(len(x))
    rows.append((geo, k, m, s_, se))
    print("  %-34s%7d%7.1f%9.2f%%%9.2f%%%8.2f%%%9.2f%%%8.1f%%" %
          (k, len(x), len(x)/nq, m*100, s_*100, drag*100, geo*100, geo*4*100))

print("\n  standard error on each mean (is any of this even distinguishable?):")
for geo, k, m, s_, se in rows:
    print(f"    {k:<34} mean {m*100:+6.2f}%  +/- {se*100:.2f}%  ->  {'SIGNIFICANT' if abs(m) > 2*se else 'not distinguishable from zero'}")

rows.sort(reverse=True)
print(f"\n  BEST BY GEOMETRIC: {rows[0][1]}")
base = [r for r in rows if r[1].startswith("NO GATE")][0]
print(f"  vs NO GATE: {(rows[0][0]-base[0])*100:+.2f}%/qtr")
print("\n  READ: a gate is only worth having if it BEATS 'NO GATE' by more than the standard error.")
