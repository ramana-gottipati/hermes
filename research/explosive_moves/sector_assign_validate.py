"""CAN WE READ A STOCK'S SECTOR FROM HOW IT MOVES? (Ramana, 2026-07-15)

Ramana: "When you identify a sector, you should select a stock only from that sector."
15i declared this BLOCKED: stock_index_membership holds only 4 weeks, so we cannot know who was
in Nifty Auto in 2011. But membership may not be needed -- a real auto company CO-MOVES with
Nifty Auto. That is computable from prices we already own, point-in-time, and it covers DEAD
companies too (they have returns right up to their last day).

METHOD: at date d, for each liquid stock, correlate its EXCESS return (vs Nifty 500) against each
sector index's EXCESS return (vs Nifty 500) over the trailing window. Assign to argmax.
Excess-vs-excess is the point: raw correlation would just measure shared market beta and hand
every large-cap to whichever sector index is biggest. Excess isolates SECTOR-SPECIFIC co-movement.

THIS SCRIPT DOES NOT ASSUME IT WORKS -- it VALIDATES against the 4 weeks of real membership we do
have (stock_index_membership). If correlation-assignment reproduces NSE's actual sector labels at
a useful hit rate, it is a usable proxy for the 21-year backtest. If it does not, the blocker is
real and this dies here.
"""
import sqlite3, sys, math
from collections import defaultdict

DB    = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
WIN   = int(sys.argv[2]) if len(sys.argv) > 2 else 500   # trailing trading days
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

# ---- known truth: NSE's own membership (the 4 weeks we have) ----
truth = {}
for sym, idx in conn.execute("""
    SELECT symbol, index_name FROM stock_index_membership
    WHERE index_name IN (%s)
      AND snapshot_date = (SELECT MAX(snapshot_date) FROM stock_index_membership)
""" % ",".join("?" * len(SECTORS)), SECTORS):
    truth.setdefault(sym, set()).add(idx)
print(f"[truth] {len(truth)} symbols carry a real NSE sector label today")

# ---- index closes ----
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""
    SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value > 0
""" % ",".join("?" * (len(SECTORS) + 1)), SECTORS + [BENCH]):
    iclose[nm][d] = c

cal = sorted(iclose[BENCH])[-(WIN + 5):]
print(f"[window] {cal[0]} -> {cal[-1]}  ({len(cal)} trading days)")

# ---- stock closes over the same window (EQ+BE+BZ per ledger 15L) ----
syms = tuple(truth)
sclose = defaultdict(dict)
q = """SELECT symbol, trade_date, close FROM bhavcopy_rows
       WHERE series IN ('EQ','BE','BZ') AND close > 0 AND trade_date >= ?
         AND symbol IN (%s)""" % ",".join("?" * len(syms))
for s, d, c in conn.execute(q, (cal[0],) + syms):
    sclose[s][d] = c
conn.close()


def excess_rets(closes, days):
    """excess daily return vs the benchmark, aligned on `days`"""
    out = []
    for i in range(1, len(days)):
        a, b = days[i-1], days[i]
        if a in closes and b in closes and a in iclose[BENCH] and b in iclose[BENCH]:
            out.append((closes[b]/closes[a] - 1.0) - (iclose[BENCH][b]/iclose[BENCH][a] - 1.0))
        else:
            out.append(None)
    return out


def corr(x, y):
    p = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(p) < 100:
        return None
    n = len(p)
    mx = sum(a for a, _ in p)/n; my = sum(b for _, b in p)/n
    sx = math.sqrt(sum((a-mx)**2 for a, _ in p)); sy = math.sqrt(sum((b-my)**2 for _, b in p))
    if not sx or not sy:
        return None
    return sum((a-mx)*(b-my) for a, b in p) / (sx*sy)


sec_ex = {nm: excess_rets(iclose[nm], cal) for nm in SECTORS}

hit = miss = skip = 0
top3hit = 0
per_sector = defaultdict(lambda: [0, 0])
for s, real in truth.items():
    ex = excess_rets(sclose.get(s, {}), cal)
    scores = []
    for nm in SECTORS:
        c = corr(ex, sec_ex[nm])
        if c is not None:
            scores.append((c, nm))
    if len(scores) < 5:
        skip += 1
        continue
    scores.sort(reverse=True)
    pred = scores[0][1]
    if pred in real:
        hit += 1; per_sector[pred][0] += 1
    else:
        miss += 1
        for r in real:
            per_sector[r][1] += 1
    if any(nm in real for _, nm in scores[:3]):
        top3hit += 1

tot = hit + miss
print(f"\n=== CAN CO-MOVEMENT RECOVER NSE'S OWN SECTOR LABEL? (window {WIN}d) ===")
print(f"  tested {tot} symbols ({skip} skipped for thin history)")
print(f"  TOP-1 hit: {hit}/{tot} = {hit/tot*100:.1f}%   (random would be ~{100/len(SECTORS):.1f}%)")
print(f"  TOP-3 hit: {top3hit}/{tot} = {top3hit/tot*100:.1f}%")
print(f"\n  per-sector top-1 hits (hit/miss):")
for nm in SECTORS:
    h, m = per_sector[nm]
    if h + m:
        print(f"    {nm:<28} {h:3d} hit / {m:3d} miss")
