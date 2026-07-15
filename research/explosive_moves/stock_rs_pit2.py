"""PIT-clean stock RS book, v2 -- adds HYSTERESIS. Zero survivorship, no membership needed.

v1 finding (ledger 2026-07-15j): the NAIVE top-N RS book LOSES to Nifty 500 on return/vol at
every size (0.49-0.58 vs 0.66) with deeper drawdowns, and churns ~330%/yr. The sector engine's
single biggest lesson was that LOW CHURN is what made it work (hysteresis band, ledger 15b/15c).
v2 asks: does the same medicine rescue the stock book? Needs no blocked classification data.

Universe = the bhavcopy itself: every EQ stock actually trading that month with real liquidity
that month. Companies that later delisted ARE included on the dates they were tradeable.
"""
import sqlite3, sys, math
from collections import defaultdict

DB       = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH    = "Nifty 500"
LB_M     = 6            # 6-month RS lookback (~126 trading days, matches the sector engine)
ADV_BAR  = 5e7          # Rs 5 crore/day
MIN_DAYS = 15
COST     = 0.0015

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

mc = defaultdict(dict)
for s, ym, c in conn.execute("""
    SELECT symbol, ym, close FROM (
      SELECT symbol, substr(trade_date,1,7) ym, close,
             ROW_NUMBER() OVER (PARTITION BY symbol, substr(trade_date,1,7)
                                ORDER BY trade_date DESC) rn
      FROM bhavcopy_rows WHERE series='EQ' AND close > 0)
    WHERE rn=1"""):
    mc[s][ym] = c

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
      FROM index_rows WHERE index_name=? AND close_value>0)
    WHERE rn=1""", (BENCH,)):
    bm[ym] = c
conn.close()

months = sorted(bm)
mi = {m: i for i, m in enumerate(months)}
print(f"[data] {len(mc):,} EQ symbols | bench {months[0]} -> {months[-1]} ({len(months)} months)")


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


def qualify(m, topn, held, band):
    ex = excess_at(m)
    if not ex:
        return held or []
    if band is None or not held:
        return [k for k, v in sorted(ex.items(), key=lambda kv: -kv[1]) if v > 0][:topn]
    keep = [x for x in held if ex.get(x, -9.0) >= band]      # hysteresis: hold until it breaks
    slots = topn - len(keep)
    if slots > 0:
        cands = sorted(((v, k) for k, v in ex.items() if v > 0 and k not in keep), reverse=True)
        keep += [k for _, k in cands[:slots]]
    return keep


def simulate(start_ym, topn=40, cost=COST, band=None):
    ms = [m for m in months if m >= start_ym]
    nav = bnav = 1.0
    navs, bnavs, held, stale, turns = [], [], [], 0, []
    for k in range(len(ms) - 1):
        m, nxt = ms[k], ms[k + 1]
        if m[5:7] in ("01", "04", "07", "10") or not held:
            new = qualify(m, topn, held, band)
            if new:
                churn = len(set(new) ^ set(held)) / max(len(set(new) | set(held)), 1)
                turns.append(churn)
                nav *= (1 - cost * churn)
                held = new
        if held:
            rs = []
            for x in held:
                cl = mc[x]
                if m in cl and nxt in cl:
                    rs.append(cl[nxt] / cl[m] - 1.0)
                elif m in cl:
                    rs.append(0.0); stale += 1
            if rs:
                nav *= (1 + sum(rs) / len(rs))
        bnav *= bm[nxt] / bm[m]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, ms, stale, turns


def stats(navs, bnavs):
    r  = [navs[i] / navs[i-1] - 1 for i in range(1, len(navs))]
    br = [bnavs[i] / bnavs[i-1] - 1 for i in range(1, len(bnavs))]
    n, yrs = len(r), len(r) / 12.0
    def _sh(x):
        mu = sum(x) / len(x)
        sd = math.sqrt(sum((v - mu) ** 2 for v in x) / (len(x) - 1))
        return (mu * 12) / (sd * math.sqrt(12)) if sd else 0.0
    def _dd(nv):
        pk, mx = nv[0], 0.0
        for v in nv:
            pk = max(pk, v); mx = min(mx, v / pk - 1)
        return mx
    mu, mub = sum(r) / n, sum(br) / n
    varb = sum((v - mub) ** 2 for v in br) / (n - 1)
    cov  = sum((r[i] - mu) * (br[i] - mub) for i in range(n)) / (n - 1)
    beta = cov / varb if varb else 0.0
    return dict(mult=navs[-1], bmult=bnavs[-1], cagr=navs[-1] ** (1/yrs) - 1,
                bcagr=bnavs[-1] ** (1/yrs) - 1, sharpe=_sh(r), bsharpe=_sh(br),
                dd=_dd(navs), bdd=_dd(bnavs), beta=beta,
                alpha=(mu - beta * mub) * 12, yrs=yrs)


def show(tag, start, topn=40, cost=COST, band=None):
    navs, bnavs, ms, stale, turns = simulate(start, topn, cost, band)
    if len(navs) < 24:
        print(f"{tag}: too short"); return
    s = stats(navs, bnavs)
    at = sum(turns) / len(turns) * 4 if turns else 0
    win = "BEATS" if s['sharpe'] > s['bsharpe'] else "loses"
    print(f"\n=== {tag}  ({ms[0]}->{ms[-1]}, {s['yrs']:.1f}y, top{topn}, {cost*100:.2f}%/side) ===")
    print(f"  {'':<18}{'BOOK':>10}{'Nifty500':>10}   -> {win} on return/vol")
    print(f"  {'Return/vol':<18}{s['sharpe']:>10.2f}{s['bsharpe']:>10.2f}")
    print(f"  {'CAGR':<18}{s['cagr']*100:>9.1f}%{s['bcagr']*100:>9.1f}%")
    print(f"  {'MaxDD':<18}{s['dd']*100:>9.1f}%{s['bdd']*100:>9.1f}%")
    print(f"  {'Rs1Cr ->':<18}{s['mult']:>9.2f}x{s['bmult']:>9.2f}x")
    print(f"  beta {s['beta']:.2f} | alpha {s['alpha']*100:+.1f}%/yr | "
          f"turnover ~{at*100:.0f}%/yr | delisted-flat {stale}")
    return s


print("\n" + "=" * 74)
print("PIT-CLEAN STOCK RS BOOK v2 — bhavcopy universe, dead companies INCLUDED")
print("=" * 74)

print("\n##### A. NAIVE — rebuild top-40 every quarter (v1 baseline, for reference) #####")
show("NAIVE from 2005", "2005-01")

print("\n##### B. + HYSTERESIS — hold a winner until its RS excess breaks the band #####")
for bd in (-0.05, -0.10, -0.20, -0.35):
    show(f"BAND {bd*100:.0f}% from 2005", "2005-01", band=bd)

print("\n##### C. does the best band survive time + realistic stock costs? #####")
for bd in (-0.20, -0.35):
    for st in ("2011-01", "2017-01"):
        show(f"BAND {bd*100:.0f}% from {st[:4]} @0.30%/side", st, cost=0.0030, band=bd)
