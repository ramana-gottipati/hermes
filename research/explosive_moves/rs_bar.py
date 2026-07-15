"""WHY did a book of index-beating stocks LOSE to the index? (Ramana, 2026-07-15)

He is right that this is the question, and it was never asked. 15j/15k reported P&L and never
decomposed it. This does not build a book -- it tests the PREDICTIVE STEP underneath every book.

THE DECOMPOSITION. At each quarterly date d, over the liquid universe (bhavcopy, PIT, dead names
included), rank every stock by trailing 6m RS excess vs Nifty 500. Then measure what happened
FORWARD over the next 3 months:

  CONTROL  = every liquid stock, equal-weight, forward 3m   <- the "no selection at all" baseline
  D10      = top RS decile (what we buy), forward 3m
  D1       = worst RS decile, forward 3m
  BENCH    = Nifty 500 forward 3m

That splits the failure into two independent causes:
  (a) CONTROL vs BENCH  -> is the UNIVERSE/WEIGHTING the problem? (equal-weight liquid mid-caps
                           are NOT Nifty 500; this gap is there before any stock-picking)
  (b) D10 vs CONTROL    -> does RS SELECTION add or destroy value vs picking at random?
And (c) D10 vs D1 = the classic momentum spread: is there ANY monotonic signal in RS at all?

If D10 > CONTROL the selection works and the leak is elsewhere (costs/beta/crashes) -> fixable.
If D10 < CONTROL the premise is dead and no portfolio engineering saves it.
"""
import sqlite3, sys, math
from collections import defaultdict

DB       = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH    = "Nifty 500"
LB_M     = 6          # trailing RS window
FWD_M    = 3          # forward horizon (the quarterly holding period)
ADV_BAR  = float(sys.argv[2]) if len(sys.argv) > 2 else 5e7
MIN_DAYS = 15

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

mc = defaultdict(dict)
for s, ym, c in conn.execute("""
    SELECT symbol, ym, close FROM (
      SELECT symbol, substr(trade_date,1,7) ym, close,
             ROW_NUMBER() OVER (PARTITION BY symbol, substr(trade_date,1,7)
                                ORDER BY trade_date DESC) rn
      FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') AND close>0) WHERE rn=1"""):
    mc[s][ym] = c

adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""
    SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= MIN_DAYS and a:
        adv[s][ym] = a

bm = {}
for ym, c in conn.execute("""
    SELECT ym, close_value FROM (
      SELECT substr(trade_date,1,7) ym, close_value,
             ROW_NUMBER() OVER (PARTITION BY substr(trade_date,1,7)
                                ORDER BY trade_date DESC) rn
      FROM index_rows WHERE index_name=? AND close_value>0) WHERE rn=1""", (BENCH,)):
    bm[ym] = c
conn.close()

months = sorted(bm)
mi = {m: i for i, m in enumerate(months)}
rebals = [m for m in months if m[5:7] in ("01", "04", "07", "10")]


DEAD_MODE = "kill"   # "kill" = -100% | "drop" = exclude (survivorship-biased) | "flat" = 0%


def snapshot(d):
    """At month d: trailing RS excess + forward 3m return, for every liquid stock."""
    i = mi[d]
    if i - LB_M < 0 or i + FWD_M >= len(months):
        return None
    m0, mf = months[i - LB_M], months[i + FWD_M]
    bret_t = bm[d] / bm[m0] - 1.0
    bret_f = bm[mf] / bm[d] - 1.0
    rows, ndead = [], 0
    for s, cl in mc.items():
        if d in cl and m0 in cl and adv.get(s, {}).get(d, 0) >= ADV_BAR:
            rs = (cl[d] / cl[m0] - 1.0) - bret_t          # trailing (what we rank on)
            if mf in cl:
                fwd = cl[mf] / cl[d] - 1.0
            else:
                ndead += 1
                if DEAD_MODE == "drop":
                    continue                              # survivorship-biased upper bound
                fwd = -1.0 if DEAD_MODE == "kill" else 0.0
            rows.append((rs, fwd, s))
    if len(rows) < 50:
        return None
    globals()['_DEADRATE'].append(ndead / max(len(rows) + ndead, 1))
    return (rows, bret_f)


_DEADRATE = []


def run(tag, lo_year, hi_year):
    acc = defaultdict(list)
    nper = 0
    for d in rebals:
        if not (lo_year <= int(d[:4]) <= hi_year):
            continue
        snap = snapshot(d)
        if not snap:
            continue
        rows, bret_f = snap
        rows.sort()                                   # ascending by trailing RS
        n = len(rows)
        dec = max(n // 10, 1)
        d1  = rows[:dec]                              # worst RS
        d10 = rows[-dec:]                             # best RS  <- what the book buys
        top40 = rows[-40:]                            # what the book ACTUALLY holds
        allf = [r[1] for r in rows]
        acc['CONTROL'].append(sum(allf) / n - bret_f)
        acc['D1'].append(sum(r[1] for r in d1) / len(d1) - bret_f)
        acc['D10'].append(sum(r[1] for r in d10) / len(d10) - bret_f)
        acc['TOP40'].append(sum(r[1] for r in top40) / len(top40) - bret_f)
        acc['HIT'].append(sum(1 for r in top40 if r[1] > bret_f) / len(top40))
        acc['UNIVERSE'].append(float(n))
        nper += 1
    if not nper:
        print(f"{tag}: no periods"); return

    def mean(k): return sum(acc[k]) / len(acc[k])
    def tstat(k):
        x = acc[k]; mu = sum(x)/len(x)
        sd = math.sqrt(sum((v-mu)**2 for v in x)/(len(x)-1)) if len(x) > 1 else 0
        return mu/(sd/math.sqrt(len(x))) if sd else 0.0

    print(f"\n=== {tag}  ({nper} quarterly snapshots, avg universe {mean('UNIVERSE'):.0f} stocks) ===")
    print(f"  Forward 3-month EXCESS return vs Nifty 500 (annualised in brackets):")
    for k, label in (('CONTROL', 'ALL liquid stocks (no selection)'),
                     ('D1',      'WORST RS decile'),
                     ('D10',     'BEST RS decile  <- we buy here'),
                     ('TOP40',   'TOP-40 (the actual book)')):
        m = mean(k)
        print(f"    {label:<34}{m*100:+7.2f}%  ({(1+m)**4-1:+7.1%}/yr)   t={tstat(k):+5.2f}")
    print(f"    {'momentum spread D10 - D1':<34}{(mean('D10')-mean('D1'))*100:+7.2f}%")
    print(f"    {'selection effect D10 - CONTROL':<34}{(mean('D10')-mean('CONTROL'))*100:+7.2f}%   "
          f"<- does RS beat picking at random?")
    print(f"    {'universe effect CONTROL - bench':<34}{mean('CONTROL')*100:+7.2f}%   "
          f"<- equal-weight liquid vs cap-weight index")
    print(f"    hit rate of the top-40 (% beating the index over the next 3m): {mean('HIT')*100:.1f}%")


DEAD_MODE = "kill"
_DEADRATE = []
print("#"*70)
print("LIQUIDITY BAR = Rs %.0f cr/day" % (ADV_BAR/1e7))
print("#"*70)
run("2005-2026", 2005, 2026)
