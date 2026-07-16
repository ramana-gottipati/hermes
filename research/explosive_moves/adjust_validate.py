"""Does the corporate-action adjustment actually work? Validate BEFORE trusting any result.

The test: unadjusted EQ closes contain 1,489 one-day drops worse than -40%, of which 973 (65%)
sit within 3 days of a corporate action. If the adjustment is correct, those artefact cliffs
should largely VANISH while genuine crashes survive.
"""
import sqlite3, sys
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_closes

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

fac = load_factors(conn)
print(f"[factors] {len(fac):,} symbols carry SPLIT/BONUS factors "
      f"({sum(len(v) for v in fac.values()):,} events)")

# corporate-action dates for attribution
ca = defaultdict(set)
for s, ex in conn.execute("SELECT symbol, ex_date FROM corporate_actions WHERE ex_date IS NOT NULL"):
    ca[s].add(ex)

sclose = defaultdict(dict)
for s, d, c in conn.execute("""SELECT symbol, trade_date, close FROM bhavcopy_rows
                               WHERE series='EQ' AND close>0"""):
    sclose[s][d] = c
conn.close()

def count_cliffs(book, tag):
    raw40 = raw60 = near = 0
    for s, cl in book.items():
        ds = sorted(cl)
        for i in range(1, len(ds)):
            a, b = cl[ds[i-1]], cl[ds[i]]
            if a <= 0:
                continue
            r = b/a - 1.0
            if r < -0.40:
                raw40 += 1
                if r < -0.60:
                    raw60 += 1
                if any(abs((_d2n(x) - _d2n(ds[i]))) <= 3 for x in ca.get(s, ())):
                    near += 1
    print(f"  {tag:<12} drops<-40%: {raw40:5d}   drops<-60%: {raw60:5d}   "
          f"of the -40% ones, {near:4d} sit within 3d of a corporate action")
    return raw40, near

def _d2n(d):
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    return y*372 + m*31 + dd            # cheap monotone day-ish key

print("\n=== BEFORE vs AFTER adjustment (EQ series) ===")
b40, bnear = count_cliffs(sclose, "UNADJUSTED")
for s in list(sclose):
    if s in fac:
        sclose[s] = adjust_closes(sclose[s], fac[s])
a40, anear = count_cliffs(sclose, "ADJUSTED")

print(f"\n  artefact cliffs removed: {b40-a40:,} of {b40:,}  ({(b40-a40)/max(b40,1)*100:.1f}%)")
print(f"  corporate-action-linked cliffs remaining: {anear} (was {bnear})")
