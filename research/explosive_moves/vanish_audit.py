"""Are my sim's 'deaths' real deaths, or just EQ->BE surveillance moves? (2026-07-15)

15j/15k/15L all filter series='EQ'. NSE moves stocks under surveillance to the BE
(trade-to-trade) series -- 656k rows / 2,554 symbols in our own data. A stock going EQ->BE
VANISHES from an EQ-only query while still trading perfectly well. And BE placement is often
triggered by exactly the sharp run-up that puts a stock in the TOP RS DECILE.

If that is what my 'deaths' are, then '15L: high-RS stocks die 3x more often' is a BUG, not a
finding, and the -100%/-50% death marking is nonsense.
"""
import sqlite3, sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

eq, other = defaultdict(set), defaultdict(set)
for s, ym in conn.execute("SELECT DISTINCT symbol, substr(trade_date,1,7) FROM bhavcopy_rows WHERE series='EQ'"):
    eq[s].add(ym)
for s, ym in conn.execute("SELECT DISTINCT symbol, substr(trade_date,1,7) FROM bhavcopy_rows WHERE series<>'EQ'"):
    other[s].add(ym)
conn.close()

allm = sorted({m for v in eq.values() for m in v})
mi = {m: i for i, m in enumerate(allm)}


def nxt(m, k=1):
    i = mi.get(m)
    return allm[i + k] if i is not None and i + k < len(allm) else None


vanish = 0
in_other = 0
back_12m = 0
truly_gone = 0
for s, mset in eq.items():
    for m in mset:
        n1 = nxt(m)
        if n1 is None or n1 in mset:
            continue
        vanish += 1                                   # what my sim calls DEATH
        if n1 in other.get(s, ()):
            in_other += 1                             # still trading, just another series
        # does it come back to EQ within 12 months?
        i = mi[m]
        if any(allm[j] in mset for j in range(i + 1, min(i + 13, len(allm)))):
            back_12m += 1
        elif n1 not in other.get(s, ()):
            truly_gone += 1

print(f"EQ-vanish events (what my sim calls DEATH):      {vanish:,}")
print(f"  ...still trading in ANOTHER series next month: {in_other:,}  ({in_other/vanish*100:.1f}%)")
print(f"  ...RETURNS to EQ within 12 months (NOT dead):  {back_12m:,}  ({back_12m/vanish*100:.1f}%)")
print(f"  ...no other series AND never returns (real):   {truly_gone:,}  ({truly_gone/vanish*100:.1f}%)")
