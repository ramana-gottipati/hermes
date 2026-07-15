"""PIT-clean stock RS book v3 -- EXIT DISCIPLINE (Ramana, 2026-07-15).

Ramana: "even if the companies actually died in 2011 or earlier, it doesn't really matter
because the strategy should address all of those problems. If we selected something that then
fell dramatically, we need to understand that we must have proper exit strategies written."

He is right, and he exposed a real hole: v1/v2 (ledger 15j) had NO EXIT RULE. The only way out
was dropping off the top-40 at the NEXT QUARTERLY rebalance -- a stock could collapse 50% in
month 1 and be held for 3 months. The -68.1% MaxDD may be that negligence, not the verdict.

Note the sector engine REJECTED a monthly risk pass (V10 ASYM, 0.59 vs 0.70, ledger 15c) -- but
15j established that sector-layer results do NOT transfer to the stock layer, so that rejection
does not bind here. Exits get a fresh test.

HONESTY OF THE STOP TEST: stops are checked against each month's LOW (min of daily lows), so a
stop fires when price actually reached it intramonth, not politely at month-end. Fill is assumed
AT the stop price -- real gaps would fill worse. Disclosed, not hidden.
Universe is still the bhavcopy itself -> dead companies included, zero survivorship.
"""
import sqlite3, sys, math
from collections import defaultdict

DB       = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH    = "Nifty 500"
LB_M     = 6
ADV_BAR  = 5e7
MIN_DAYS = 15
COST     = 0.0015
TOPN     = 40

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

# monthly close AND monthly low (low = for honest stop checking)
mc, ml = defaultdict(dict), defaultdict(dict)
for s, ym, c in conn.execute("""
    SELECT symbol, ym, close FROM (
      SELECT symbol, substr(trade_date,1,7) ym, close,
             ROW_NUMBER() OVER (PARTITION BY symbol, substr(trade_date,1,7)
                                ORDER BY trade_date DESC) rn
      FROM bhavcopy_rows WHERE series='EQ' AND close>0) WHERE rn=1"""):
    mc[s][ym] = c
for s, ym, lo in conn.execute("""
    SELECT symbol, substr(trade_date,1,7), min(low)
    FROM bhavcopy_rows WHERE series='EQ' AND low>0 GROUP BY 1,2"""):
    ml[s][ym] = lo

adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""
    SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series='EQ' GROUP BY 1,2"""):
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
print(f"[data] {len(mc):,} EQ symbols | {months[0]} -> {months[-1]}")


def excess_at(m):
    i = mi[m]
    if i - LB_M < 0:
        return {}
    m0 = months[i - LB_M]
    bret = bm[m] / bm[m0] - 1.0
    out = {}
    for sym, cl in mc.items():
        if m in cl and m0 in cl and adv.get(sym, {}).get(m, 0) >= ADV_BAR:
            out[sym] = (cl[m] / cl[m0] - 1.0) - bret
    return out


def simulate(start_ym, stop=None, trail=None, rs_exit=False, cost=COST, topn=TOPN, slip=0.0):
    """stop    = hard stop-loss from ENTRY price (e.g. 0.20 = -20%)
       trail   = trailing stop from the position's PEAK close
       rs_exit = monthly check: drop the name the month its 6m RS excess turns negative"""
    ms = [m for m in months if m >= start_ym]
    nav = bnav = 1.0
    navs, bnavs = [], []
    pos = {}                      # sym -> {'entry':px, 'peak':px, 'w':weight}
    fired = defaultdict(int)
    for k in range(len(ms) - 1):
        m, nxt = ms[k], ms[k + 1]

        # ---- quarterly rebalance: refill to topn equal-weight ----
        if m[5:7] in ("01", "04", "07", "10") or not pos:
            ex = excess_at(m)
            if ex:
                want = [s for s, v in sorted(ex.items(), key=lambda kv: -kv[1]) if v > 0][:topn]
                if want:
                    churn = len(set(want) ^ set(pos)) / max(len(set(want) | set(pos)), 1)
                    nav *= (1 - cost * churn)
                    newpos = {}
                    for s in want:
                        p = mc[s][m]
                        newpos[s] = pos.get(s) or {'entry': p, 'peak': p}
                        newpos[s]['w'] = 1.0 / len(want)
                    pos = newpos

        # ---- monthly RS risk pass (optional) ----
        if rs_exit and pos:
            ex = excess_at(m)
            for s in list(pos):
                if ex.get(s, 0.0) < 0:
                    del pos[s]; fired['rs'] += 1

        # ---- hold one month, applying stops against the month's LOW ----
        if pos:
            tot_w = sum(p['w'] for p in pos.values())
            contrib = 0.0
            for s in list(pos):
                p = pos[s]
                c0 = mc[s].get(m)
                c1 = mc[s].get(nxt)
                lo = ml[s].get(nxt)
                if c0 is None:
                    continue
                r = None
                if stop and lo is not None and lo <= p['entry'] * (1 - stop):
                    r = (p['entry'] * (1 - stop) * (1 - slip)) / c0 - 1.0   # gap slippage
                    fired['stop'] += 1; del pos[s]
                elif trail and lo is not None and lo <= p['peak'] * (1 - trail):
                    r = (p['peak'] * (1 - trail) * (1 - slip)) / c0 - 1.0
                    fired['trail'] += 1; del pos[s]
                elif c1 is not None:
                    r = c1 / c0 - 1.0
                    p['peak'] = max(p['peak'], c1)
                else:
                    r = 0.0; fired['stale'] += 1              # delisted: carried flat (generous)
                    del pos[s]
                contrib += (p['w'] / tot_w) * r * tot_w        # exited names -> proceeds to cash
            nav *= (1 + contrib)
        bnav *= bm[nxt] / bm[m]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, ms, fired


def stats(navs, bnavs):
    r  = [navs[i] / navs[i-1] - 1 for i in range(1, len(navs))]
    br = [bnavs[i] / bnavs[i-1] - 1 for i in range(1, len(bnavs))]
    n, yrs = len(r), len(r) / 12.0
    def _sh(x):
        mu = sum(x)/len(x); sd = math.sqrt(sum((v-mu)**2 for v in x)/(len(x)-1))
        return (mu*12)/(sd*math.sqrt(12)) if sd else 0.0
    def _dd(nv):
        pk, mx = nv[0], 0.0
        for v in nv:
            pk = max(pk, v); mx = min(mx, v/pk-1)
        return mx
    mu, mub = sum(r)/n, sum(br)/n
    varb = sum((v-mub)**2 for v in br)/(n-1)
    cov  = sum((r[i]-mu)*(br[i]-mub) for i in range(n))/(n-1)
    beta = cov/varb if varb else 0.0
    return dict(mult=navs[-1], bmult=bnavs[-1], cagr=navs[-1]**(1/yrs)-1,
                bcagr=bnavs[-1]**(1/yrs)-1, sharpe=_sh(r), bsharpe=_sh(br),
                dd=_dd(navs), bdd=_dd(bnavs), beta=beta, alpha=(mu-beta*mub)*12, yrs=yrs)


def show(tag, start, **kw):
    navs, bnavs, ms, fired = simulate(start, **kw)
    if len(navs) < 24:
        print(f"{tag}: too short"); return
    s = stats(navs, bnavs)
    v = "BEATS" if s['sharpe'] > s['bsharpe'] else "loses"
    print(f"\n=== {tag}  ({ms[0]}->{ms[-1]}, {s['yrs']:.1f}y) -> {v} the index on return/vol ===")
    print(f"  return/vol {s['sharpe']:.2f} vs {s['bsharpe']:.2f} | CAGR {s['cagr']*100:.1f}% vs "
          f"{s['bcagr']*100:.1f}% | MaxDD {s['dd']*100:.1f}% vs {s['bdd']*100:.1f}%")
    print(f"  Rs1Cr -> {s['mult']:.2f}x vs {s['bmult']:.2f}x | beta {s['beta']:.2f} | "
          f"alpha {s['alpha']*100:+.1f}%/yr")
    print(f"  exits fired: {dict(fired)}")
    return s


print("\n" + "="*78)
print("EXIT DISCIPLINE ON THE STOCK BOOK — Ramana: 'we must have proper exit strategies'")
print("stops checked against each month's LOW; fill assumed AT the stop (gaps would fill worse)")
print("="*78)

print("\n##### 1. WINDOW STABILITY — same rules, different start dates #####")
for st in ("2005-01", "2011-01", "2017-01"):
    show(f"HARD -15% from {st[:4]}", st, stop=0.15)
for st in ("2005-01", "2011-01", "2017-01"):
    show(f"TRAIL -20% from {st[:4]}", st, trail=0.20)

print("\n##### 2. GAP SLIPPAGE — stops do NOT fill at the stop price in real life #####")
for sl in (0.0, 0.01, 0.02, 0.04):
    show(f"HARD -15% from 2005, slip {sl*100:.0f}%", "2005-01", stop=0.15, slip=sl)

print("\n##### 3. slippage + realistic stock costs TOGETHER (the honest configuration) #####")
show("HARD -15% 2005, slip 2% @0.30%/side", "2005-01", stop=0.15, slip=0.02, cost=0.0030)
show("TRAIL -20% 2005, slip 2% @0.30%/side", "2005-01", trail=0.20, slip=0.02, cost=0.0030)
show("HARD -15% 2011, slip 2% @0.30%/side", "2011-01", stop=0.15, slip=0.02, cost=0.0030)
show("HARD -15% 2017, slip 2% @0.30%/side", "2017-01", stop=0.15, slip=0.02, cost=0.0030)
