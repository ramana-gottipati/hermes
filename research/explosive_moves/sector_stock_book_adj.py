"""RAMANA'S ACTUAL STRATEGY, at last: strong SECTORS -> strong STOCKS INSIDE them.

Ramana, 2026-07-15: "Why are you looking at the whole universe? When you identify a sector, you
should select a stock only from that sector. Which stock do you choose? Whenever a stock moves
within the sector, consider both the minor index and the broader index together, and identify a
reasonable percentage that can serve as a starting point."

THE THREE THINGS THIS DOES THAT NOTHING BEFORE IT DID:
  1. SECTOR GATE FIRST  - only sectors beating Nifty 500 on 6m RS qualify (the V24 rule).
  2. STOCKS ONLY FROM QUALIFYING SECTORS - via PIT correlation assignment (validated 85.1% vs
     NSE's own labels, `sector_assign_validate.py`), so NO membership table is needed and DEAD
     companies are included. This is what dissolves the 15i blocker.
  3. THE DOUBLE TEST - a stock must beat BOTH its own sector index AND Nifty 500 ("the minor
     index and the broader index together"). Thresholds swept to find Ramana's "reasonable
     percentage".

Universe: bhavcopy EQ+BE+BZ (ledger 15L - surveillance moves are NOT deaths), liquidity>=bar AT d.
Zero survivorship: dead names are present on every date they were tradeable.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, '/opt/hermes/research/explosive_moves')
from adjust import load_factors, adjust_all

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
LB       = 126        # 6-month RS lookback (trading days)
CORRWIN  = 500        # trailing window for sector assignment
ADV_BAR  = 5e7
COST     = 0.0015
SEC_BAND = 0.08       # a sector qualifies at > +8% RS excess (the V24 hysteresis entry)

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")

iclose = defaultdict(dict)
for nm, d, c in conn.execute("""
    SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)),
    SECTORS + [BENCH]):
    iclose[nm][d] = c

cal = sorted(iclose[BENCH])
ci = {d: i for i, d in enumerate(cal)}

sclose = defaultdict(dict)
for s, d, c in conn.execute("""
    SELECT symbol, trade_date, close FROM bhavcopy_rows
    WHERE series IN ('EQ','BE','BZ') AND close>0"""):
    sclose[s][d] = c

adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""
    SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= 15 and a:
        adv[s][ym] = a

# ---- THE FIX: adjust for splits/bonuses. Raw closes read a 1:2 bonus as -50%; index levels
# ---- ARE adjusted, so every stock-vs-index comparison was rigged against the stock (Guardrail #5).
_fac = load_factors(conn)
_nadj = adjust_all(sclose, _fac)
print(f"[adjust] {_nadj:,} symbols corporate-action adjusted ({sum(len(v) for v in _fac.values()):,} events)", file=sys.stderr)
conn.close()

print(f"[data] {len(sclose):,} symbols | calendar {cal[0]} -> {cal[-1]}", file=sys.stderr)

# ---- daily excess-return series (pure python), aligned to cal[1:] ----
bench_r = []
for i in range(1, len(cal)):
    a, b = iclose[BENCH][cal[i-1]], iclose[BENCH][cal[i]]
    bench_r.append(b/a - 1.0)

sec_ex = {}
for nm in SECTORS:
    out = []
    for i in range(1, len(cal)):
        a, b = iclose[nm].get(cal[i-1]), iclose[nm].get(cal[i])
        out.append((b/a - 1.0) - bench_r[i-1] if (a and b) else None)
    sec_ex[nm] = out

stock_ex = {}
for s_, cl in sclose.items():
    if len(cl) < 300:
        continue
    out = []
    for i in range(1, len(cal)):
        a, b = cl.get(cal[i-1]), cl.get(cal[i])
        out.append((b/a - 1.0) - bench_r[i-1] if (a and b) else None)
    stock_ex[s_] = out

print(f"[data] {len(stock_ex):,} symbols with usable history", file=sys.stderr)

rebal = [d for i, d in enumerate(cal) if i >= CORRWIN + LB and d[5:7] in ("01","04","07","10")
         and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(rebal)} quarterly rebalances {rebal[0]} -> {rebal[-1]}", file=sys.stderr)

_assign_cache = {}


def _corr(x, y, lo, hi):
    n = 0; sx = sy = sxx = syy = sxy = 0.0
    for i in range(lo, hi):
        a = x[i]; b = y[i]
        if a is None or b is None:
            continue
        n += 1; sx += a; sy += b; sxx += a*a; syy += b*b; sxy += a*b
    if n < 100:
        return None
    cx = sxx - sx*sx/n; cy = syy - sy*sy/n
    if cx <= 0 or cy <= 0:
        return None
    return (sxy - sx*sy/n) / math.sqrt(cx*cy)


def assign_sectors(d):
    """PIT: correlate each LIQUID stock's excess returns against each sector's, trailing
    CORRWIN days. Cached per YEAR (industry membership is stable; 21 recomputes not 86)."""
    key = d[:4]
    if key in _assign_cache:
        return _assign_cache[key]
    i = ci[d]
    lo, hi = max(0, i - CORRWIN), i
    ym = d[:7]
    out = {}
    for s_ in stock_ex:
        if adv.get(s_, {}).get(ym, 0) < ADV_BAR:      # liquid-only -> ~430 not 4,471
            continue
        best, bestc = None, -9.0
        for nm in SECTORS:
            c = _corr(stock_ex[s_], sec_ex[nm], lo, hi)
            if c is not None and c > bestc:
                bestc, best = c, nm
        if best:
            out[s_] = best
    _assign_cache[key] = out
    print(f"  [assign {key}] {len(out)} liquid stocks mapped", file=sys.stderr)
    return out


def px_at(s, d):
    return sclose[s].get(d)


def rs_excess(px_series, d0, d1, ref):
    a, b = px_series.get(d0), px_series.get(d1)
    ra, rb = ref.get(d0), ref.get(d1)
    if not (a and b and ra and rb):
        return None
    return (b/a - 1.0) - (rb/ra - 1.0)


def qualifying_sectors(d):
    i = ci[d]; d0 = cal[i-LB]
    out = []
    for nm in SECTORS:
        e = rs_excess(iclose[nm], d0, d, iclose[BENCH])
        if e is not None and e > SEC_BAND:
            out.append(nm)
    return out


def pick(d, sec_thr, broad_thr, topn, per_sector_cap):
    """Ramana's rule: sector qualifies -> stock beats its OWN sector by sec_thr AND beats
    Nifty 500 by broad_thr. Rank by the sum of the two edges."""
    qs = qualifying_sectors(d)
    if not qs:
        return {}, qs
    amap = assign_sectors(d)
    i = ci[d]; d0 = cal[i-LB]
    ym = d[:7]
    cands = defaultdict(list)
    for s, sec in amap.items():
        if sec not in qs:
            continue                                   # <- ONLY stocks from qualifying sectors
        if adv.get(s, {}).get(ym, 0) < ADV_BAR:
            continue
        pxs = sclose[s]
        e_broad = rs_excess(pxs, d0, d, iclose[BENCH])
        e_sec   = rs_excess(pxs, d0, d, iclose[sec])
        if e_broad is None or e_sec is None:
            continue
        if e_sec > sec_thr and e_broad > broad_thr:    # <- BOTH tests, together
            cands[sec].append((e_sec + e_broad, s))
    picked = []
    for sec, lst in cands.items():
        lst.sort(reverse=True)
        picked += [(v, s) for v, s in lst[:per_sector_cap]]
    picked.sort(reverse=True)
    picked = picked[:topn]
    if not picked:
        return {}, qs
    w = 1.0/len(picked)
    return {s: w for _, s in picked}, qs


def simulate(sec_thr, broad_thr, topn=40, per_sector_cap=8, start="2005-01-01"):
    rb = [d for d in rebal if d >= start]
    nav = bnav = 1.0
    navs, bnavs, held, nsec, nheld = [], [], {}, [], []
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        w, qs = pick(d, sec_thr, broad_thr, topn, per_sector_cap)
        nsec.append(len(qs)); nheld.append(len(w))
        turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
        nav *= (1 - COST*turn)
        r = 0.0
        for s, x in w.items():
            a, b = px_at(s, d), px_at(s, dn)
            r += x * ((b/a - 1.0) if (a and b) else 0.0)
        if not w:                                       # nothing qualifies -> cash
            r = 0.0
        nav *= (1 + r)
        bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        held = w
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, rb, nsec, nheld


def stats(navs, bnavs, nper_year=4):
    r  = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); yrs = n/nper_year
    def _sh(x):
        m = sum(x)/len(x); sd = math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
        return (m*nper_year)/(sd*math.sqrt(nper_year)) if sd else 0.0
    def _dd(nv):
        pk, mx = nv[0], 0.0
        for v in nv:
            pk = max(pk, v); mx = min(mx, v/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((v-mb)**2 for v in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    beta = cov/vb if vb else 0.0
    return dict(cagr=navs[-1]**(1/yrs)-1, bcagr=bnavs[-1]**(1/yrs)-1, sh=_sh(r), bsh=_sh(br),
                dd=_dd(navs), bdd=_dd(bnavs), mult=navs[-1], bmult=bnavs[-1],
                beta=beta, alpha=(m-beta*mb)*nper_year, yrs=yrs)


def show(tag, sec_thr, broad_thr, topn=40, cap=8, start="2005-01-01"):
    navs, bnavs, rb, nsec, nheld = simulate(sec_thr, broad_thr, topn, cap, start)
    if len(navs) < 12:
        print(f"{tag}: too short"); return None
    s = stats(navs, bnavs)
    v = "BEATS" if s['sh'] > s['bsh'] else "loses"
    print(f"{tag:<34} CAGR {s['cagr']*100:5.1f}% vs {s['bcagr']*100:4.1f}% | "
          f"retvol {s['sh']:.2f} vs {s['bsh']:.2f} | DD {s['dd']*100:6.1f}% | "
          f"b {s['beta']:.2f} | a {s['alpha']*100:+5.1f}% | {s['mult']:6.2f}x vs {s['bmult']:5.2f}x | "
          f"sec {sum(nsec)/len(nsec):.1f} held {sum(nheld)/len(nheld):.0f} | {v}")
    return s


print("="*150)
print("RAMANA'S STRATEGY: sector gate -> stocks ONLY from qualifying sectors -> beat BOTH the sector AND the broad index")
print("="*150)
print("\n--- sweep the 'reasonable percentage': stock must beat its OWN SECTOR by X ---")
for sec_thr in (0.0, 0.05, 0.10, 0.20, 0.30):
    show(f"sector+{sec_thr*100:.0f}% / broad+0%", sec_thr, 0.0)

print("\n--- and beat the BROAD index by Y (both tests together) ---")
for broad_thr in (0.05, 0.10, 0.20, 0.30):
    show(f"sector+10% / broad+{broad_thr*100:.0f}%", 0.10, broad_thr)

print("\n--- book size / per-sector concentration ---")
for topn, cap in ((20, 4), (40, 8), (40, 4), (60, 10)):
    show(f"top{topn} cap{cap}/sector", 0.10, 0.10, topn=topn, cap=cap)
