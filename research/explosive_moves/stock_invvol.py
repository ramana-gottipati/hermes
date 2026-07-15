"""THE EXPERIMENT: remove Level 1 (the broken sector gate), fix Level 3 (the sizing).

Diagnosis (15P/15Q + the V8-vs-buy-and-hold check):
  L1 sector selection  = FAILING (qualifying sectors -0.67%/qtr fwd; V8 9.13x vs 12.68x buy-and-hold)
  L2 stock selection   = WORKING (top decile +1.97%/qtr excess vs Nifty 500)
  L3 portfolio sizing  = FAILING (26.63%/qtr vol -> 3.55% toll eats the 1.97% edge)

So: drop the sector gate, keep the stock selection, and size by INVERSE VOL instead of equal weight.
This exact combination has NEVER been run: 15j was equal-weight AND on RAW prices (the corporate-
action bug, worth ~16pp, ledger 15O). Inverse-vol exists in V21 but only at the SECTOR layer.

Also tests 15P's other finding: the top decile is DOMINATED by decile 6 (higher mean, lower vol).
So a BAND (percentile 50-80) is tested against TOP-N.

Universe: bhavcopy EQ+BE+BZ, corporate-action adjusted, liquid AT d, dead names included -> zero
survivorship, no membership needed.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
LB      = 126      # 6-month RS lookback
VOLWIN  = 126      # trailing window for the vol estimate
ADV_BAR = 5e7
COST    = 0.0015

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
bench = dict(conn.execute(
    "SELECT trade_date, close_value FROM index_rows WHERE index_name=? AND close_value>0", (BENCH,)))
sclose = defaultdict(dict)
for s, d, c in conn.execute("""SELECT symbol, trade_date, close FROM bhavcopy_rows
    WHERE series IN ('EQ','BE','BZ') AND close>0"""):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= 15 and a:
        adv[s][ym] = a
fac = load_factors(conn)
nadj = adjust_all(sclose, fac)
conn.close()
print(f"[adjust] {nadj:,} symbols corporate-action adjusted", file=sys.stderr)

cal = sorted(bench)
ci = {d: i for i, d in enumerate(cal)}
rebal = [d for i, d in enumerate(cal) if i >= max(LB, VOLWIN)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(sclose):,} symbols | {len(rebal)} rebalances {rebal[0]} -> {rebal[-1]}", file=sys.stderr)

_vol_cache = {}
def vol_at(s, d):
    """trailing daily-return stdev over VOLWIN. Cached per (symbol, quarter)."""
    k = (s, d)
    if k in _vol_cache:
        return _vol_cache[k]
    i = ci[d]
    cl = sclose[s]
    r = []
    for j in range(max(0, i-VOLWIN)+1, i+1):
        a, b = cl.get(cal[j-1]), cl.get(cal[j])
        if a and b:
            r.append(b/a - 1.0)
    if len(r) < 40:
        _vol_cache[k] = None; return None
    m = sum(r)/len(r)
    v = math.sqrt(sum((x-m)**2 for x in r)/(len(r)-1))
    _vol_cache[k] = v if v > 0 else None
    return _vol_cache[k]


def rs_at(d):
    i = ci[d]; d0 = cal[i-LB]
    br = bench[d]/bench[d0] - 1.0
    ym = d[:7]
    out = []
    for s, cl in sclose.items():
        a, b = cl.get(d0), cl.get(d)
        if not (a and b):
            continue
        if adv.get(s, {}).get(ym, 0) < ADV_BAR:
            continue
        out.append(((b/a - 1.0) - br, s))
    out.sort(reverse=True)
    return out


def build(d, mode, weight, topn):
    ranked = rs_at(d)
    if len(ranked) < 40:
        return {}
    if mode == "TOP":
        sel = [s for e, s in ranked[:topn] if e > 0]
    else:                                   # BAND: percentile 50-80 (15P's D6-D8), best-first
        n = len(ranked)
        lo, hi = int(n*0.20), int(n*0.50)   # ranked is descending -> 20th..50th pct from the top
        sl = [(e, s) for e, s in ranked[lo:hi] if e > 0]
        sel = [s for e, s in sl[:topn]]
    if not sel:
        return {}
    if weight == "EW":
        w = 1.0/len(sel)
        return {s: w for s in sel}
    iv = {}
    for s in sel:
        v = vol_at(s, d)
        if v:
            iv[s] = 1.0/v
    if not iv:
        return {}
    tot = sum(iv.values())
    return {s: x/tot for s, x in iv.items()}


def simulate(mode, weight, topn=40, start="2005-01-01"):
    rb = [d for d in rebal if d >= start]
    nav = bnav = 1.0
    navs, bnavs, held = [], [], {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        w = build(d, mode, weight, topn)
        if w:
            turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
            nav *= (1 - COST*turn)
            held = w
        r = 0.0
        for s, x in held.items():
            a, b = sclose[s].get(d), sclose[s].get(dn)
            r += x * ((b/a - 1.0) if (a and b) else 0.0)
        nav *= (1 + r)
        bnav *= bench[dn]/bench[d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, rb


def stats(navs, bnavs):
    r  = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); yrs = n/4.0
    def _sh(x):
        m = sum(x)/len(x); s = math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
        return (m*4)/(s*2.0) if s else 0.0
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
                beta=beta, alpha=(m-beta*mb)*4, yrs=yrs)


def show(tag, mode, weight, topn=40, start="2005-01-01"):
    navs, bnavs, rb = simulate(mode, weight, topn, start)
    if len(navs) < 12:
        print(f"{tag}: too short"); return
    s = stats(navs, bnavs)
    v = "BEATS" if s['sh'] > s['bsh'] else "loses"
    print(f"  {tag:<30} CAGR {s['cagr']*100:5.1f}% vs {s['bcagr']*100:4.1f}% | retvol {s['sh']:5.2f} vs {s['bsh']:.2f} | "
          f"DD {s['dd']*100:6.1f}% vs {s['bdd']*100:.1f}% | b {s['beta']:.2f} | a {s['alpha']*100:+5.1f}% | "
          f"{s['mult']:6.2f}x vs {s['bmult']:5.2f}x | {v}")


print("="*140)
print("THE EXPERIMENT — drop the sector gate (L1, broken). Fix the sizing (L3). Adjusted prices.")
print("="*140)
print("\n### A. the 15j baseline, but on ADJUSTED prices (never run before)")
show("TOP40 equal-weight", "TOP", "EW")
print("\n### B. FIX L3 — inverse-vol sizing")
show("TOP40 INVERSE-VOL", "TOP", "INVVOL")
print("\n### C. 15P — the extreme is the wrong target. Use the BAND (20th-50th pctile).")
show("BAND equal-weight", "BAND", "EW")
show("BAND INVERSE-VOL", "BAND", "INVVOL")
print("\n### D. book size, best config")
for n in (20, 40, 80, 150):
    show(f"BAND INVVOL top{n}", "BAND", "INVVOL", topn=n)
print("\n### E. window check")
for st in ("2011-01-01", "2017-01-01"):
    show(f"BAND INVVOL from {st[:4]}", "BAND", "INVVOL", start=st)
    show(f"TOP40 INVVOL from {st[:4]}", "TOP", "INVVOL", start=st)


# ================= THE CONTROL: no selection at all =================
def build_all(d, weight):
    """EVERY liquid stock. No RS, no ranking, no selection. If THIS prints ~12-13% the
    adjustment is sane; if it prints ~25% the adjustment is inflating everything."""
    ranked = rs_at(d)
    sel = [s for _, s in ranked]
    if not sel:
        return {}
    if weight == "EW":
        w = 1.0/len(sel)
        return {s: w for s in sel}
    iv = {}
    for s in sel:
        v = vol_at(s, d)
        if v: iv[s] = 1.0/v
    if not iv: return {}
    t = sum(iv.values())
    return {s: x/t for s, x in iv.items()}


def sim_all(weight, start="2005-01-01"):
    rb = [d for d in rebal if d >= start]
    nav = bnav = 1.0; navs, bnavs, held = [], [], {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        w = build_all(d, weight)
        if w:
            turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
            nav *= (1 - COST*turn); held = w
        r = 0.0
        for s, x in held.items():
            a, b = sclose[s].get(d), sclose[s].get(dn)
            r += x * ((b/a - 1.0) if (a and b) else 0.0)
        nav *= (1 + r); bnav *= bench[dn]/bench[d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs

print("\n" + "="*140)
print("### CONTROL — NO SELECTION. Every liquid stock, equal-weight. Sanity check on the adjustment.")
print("="*140)
for wt in ("EW", "INVVOL"):
    navs, bnavs = sim_all(wt)
    s = stats(navs, bnavs)
    print(f"  {'ALL liquid stocks, '+wt:<30} CAGR {s['cagr']*100:5.1f}% vs {s['bcagr']*100:4.1f}% | "
          f"DD {s['dd']*100:6.1f}% | b {s['beta']:.2f} | a {s['alpha']*100:+5.1f}% | "
          f"{s['mult']:6.2f}x vs {s['bmult']:5.2f}x")
print("\n  If CONTROL ~= the index -> adjustment sane, selection real.")
print("  If CONTROL ~= 25%       -> the adjustment is inflating EVERYTHING and the result is a bug.")
