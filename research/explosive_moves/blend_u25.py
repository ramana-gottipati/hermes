"""BLEND LAB — union-beta14 (RS family) ⊕ LOWVOL_MOM (rule-lab family), 50/50 paper blend.

S168 (2026-07-16), part of the 25%-CAGR push. Cross-family diversification is the one blend the
catalog has no row for: the union family (own-sector RS turn/trend, quarterly, 0.15%/side + stop
slip) and the factor-zoo family's ONE participation-fundable corner (LOWVOL_MOM largecap quarterly,
rule-lab NEW-BENCHMARK #602, net retvol 1.19 @Rs75cr).

HONEST PRIOR (stated before the run): both books are long-only Indian equity momentum — expected
return correlation 0.7-0.9, so the blend should land NEAR the average of the two CAGRs with a
slightly shallower drawdown. This run measures whether the diversification is worth more than that.
16V precedent: the union's own two legs were selection-complementary but return-correlated 0.79 —
the number that capped that result.

METHOD: the LOWVOL_MOM book is rebuilt on the UNION'S OWN quarterly rebalance grid (2012-07 onward,
the em_cache era) by passing the union's rebal dates as the calendar with REBAL_STEP patched to 1 —
so both books' period returns align exactly; no lead/lag blur. LOWVOL_MOM runs at the rule-lab's
"real" per-name cost (side_cost(mt, atr)); the union side keeps its own 0.15%/side + 1% stop-slip.
Mixed cost models are disclosed, not hidden. Blend = 50/50 rebalanced every quarter (return =
mean of the two period returns).

Windows: overlap only (2012-07 -> latest complete quarter). Reported: each book, corr, the blend
(CAGR / MaxDD / beta / alpha vs Nifty 500), plus the 2012-2017 sub-window (the union's known weak
regime — does the factor book carry it?).

Foundation byte-copied from cash_blend.py lineage. b14 overlap row must match union_lab3's b14
2012+ behaviour (same engine); LOWVOL_MOM must reproduce the #602 shape (retvol ~1.19 era).
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
sys.path.insert(0, "/opt/hermes/research")
sys.path.insert(0, "/opt/hermes")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH, SLEEVE = "Nifty 500", "Nifty Next 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
IDX = [BENCH, SLEEVE]
LB, QTR, CORRWIN, ADV_BAR, COST, DEAD_VAL = 126, 63, 500, 5e7, 0.0015, -0.50

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
names = list(set(SECTORS + IDX))
iclose = defaultdict(dict)
for nm, d, c in conn.execute("SELECT index_name,trade_date,close_value FROM index_rows WHERE index_name IN (%s) AND close_value>0"
                             % ",".join("?"*len(names)), names):
    iclose[nm][d] = c
sclose = defaultdict(dict)
for s, d, c in conn.execute("SELECT symbol,trade_date,close FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') AND close>0"):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("SELECT symbol,substr(trade_date,1,7),avg(value),count(*) FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"):
    if n >= 15 and a: adv[s][ym] = a
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}; N = len(cal)

b200 = [None]*N
buf = []
for i in range(N):
    buf.append(iclose[BENCH][cal[i]])
    if len(buf) > 200: buf.pop(0)
    b200[i] = sum(buf)/len(buf) if len(buf) >= 200 else None

def rsi_series(px, n=14):
    out = [None]*N; gain = loss = None; prev = None
    for i in range(N):
        p = px.get(cal[i])
        if p is None:
            out[i] = out[i-1] if i else None; continue
        if prev is None: prev = p; continue
        ch = p - prev; prev = p
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if gain is None: gain, loss = g, l
        else:
            gain = (gain*(n-1)+g)/n; loss = (loss*(n-1)+l)/n
        if loss == 0: out[i] = 100.0
        elif gain == 0: out[i] = 0.0
        else: out[i] = 100.0-100.0/(1.0+gain/loss)
    return out

def sma(x, n):
    out = [None]*len(x); buf = []
    for i, v in enumerate(x):
        if v is not None: buf.append(v)
        if len(buf) > n: buf.pop(0)
        out[i] = sum(buf)/len(buf) if len(buf) >= n else None
    return out

SYMS = [s for s, cl in sclose.items() if s not in QUAR and len(cl) >= 400]
print(f"[precompute] RSI for {len(SYMS):,} symbols...", file=sys.stderr, flush=True)
RSI = {s: rsi_series(sclose[s]) for s in SYMS}
RMA = {s: sma(RSI[s], 50) for s in SYMS}

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, N)]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, N)] for nm in SECTORS}
stock_ex = {s: [((sclose[s].get(cal[i]) or 0)/(sclose[s].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                if (sclose[s].get(cal[i]) and sclose[s].get(cal[i-1])) else None
                for i in range(1, N)] for s in SYMS}

def _corr2(x, y, lo, hi):
    n=0; sx=sy=sxx=syy=sxy=0.0
    for i in range(lo, hi):
        a, b = x[i], y[i]
        if a is None or b is None: continue
        n+=1; sx+=a; sy+=b; sxx+=a*a; syy+=b*b; sxy+=a*b
    if n < 100: return None
    cx, cy = sxx-sx*sx/n, syy-sy*sy/n
    if cx <= 0 or cy <= 0: return None
    return (sxy-sx*sy/n)/math.sqrt(cx*cy)

_am = {}
def assign(d):
    k = d[:4]
    if k in _am: return _am[k]
    i = ci[d]; lo = max(0, i-CORRWIN); ym = d[:7]
    out = {}
    for s in SYMS:
        if adv.get(s, {}).get(ym, 0) < ADV_BAR: continue
        best, bc = None, -9.0
        for nm in SECTORS:
            c = _corr2(stock_ex[s], sec_ex[nm], lo, i)
            if c is not None and c > bc: bc, best = c, nm
        if best: out[s] = best
    _am[k] = out
    return out

def pym(d):
    y, m = int(d[:4]), int(d[5:7]); m -= 1
    if m == 0: y, m = y-1, 12
    return "%04d-%02d" % (y, m)

def pxn(s, d, back=10):
    i = ci.get(d)
    if i is None: return None
    for j in range(i, max(-1, i-back), -1):
        v = sclose[s].get(cal[j])
        if v: return v
    return None

def isdead(s, d, fwd=60):
    i = ci.get(d)
    if i is None: return True
    return not any(sclose[s].get(cal[j]) for j in range(i, min(N, i+fwd)))

def rs_at(s, sec, j):
    a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
    return a/b if (a and b) else None

def _rsi_vals(v, n=14):
    if len(v) < n+1: return None
    g=l=0.0
    for k in range(len(v)-n, len(v)):
        ch=v[k]-v[k-1]; g+=max(ch,0); l+=max(-ch,0)
    ag,al=g/n,l/n
    return 100.0 if al==0 else (0.0 if ag==0 else 100.0-100.0/(1.0+ag/al))

def rsi_of_rs_recovery(s, sec, i):
    w = [x for x in (rs_at(s, sec, j) for j in range(max(0, i-60), i+1)) if x is not None]
    if len(w) < 40: return False
    now=_rsi_vals(w); prev=_rsi_vals(w[:-10]) if len(w)>50 else None
    if now is None or prev is None: return False
    return prev < 30 and now >= 30

def consistency(s, sec, i):
    lo = i-QTR
    if lo < 0: return None
    a0, b0 = sclose[s].get(cal[lo]), iclose[sec].get(cal[lo])
    if not (a0 and b0): return None
    ahead = tot = 0
    for j in range(lo+1, i+1):
        a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
        if not (a and b): continue
        tot += 1
        if (a/a0) > (b/b0): ahead += 1
    return ahead/tot if tot >= QTR*0.6 else None

def sig_rsi(s, sec, i):
    r, m = RSI[s][i], RMA[s][i]
    return (r is not None and m is not None and r > m)

def beta_of(s, i, look=250, minn=150):
    lo = max(1, i-look)
    n=0; sx=sy=sxx=sxy=0.0
    for j in range(lo, i+1):
        a0, a1 = sclose[s].get(cal[j-1]), sclose[s].get(cal[j])
        if not (a0 and a1): continue
        x = bench_r[j-1]; y = a1/a0-1.0
        n+=1; sx+=x; sy+=y; sxx+=x*x; sxy+=x*y
    if n >= minn:
        vx = sxx - sx*sx/n
        if vx > 0: return (sxy - sx*sy/n)/vx
    return None

rebal_all = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 250)
             and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

def b14_rets(start, end):
    """the beta14 book's quarterly returns on [start, end] (sealed mechanics)"""
    rb = [d for d in rebal_all if start <= d <= end]
    held, ent, pk = {}, {}, {}
    rets, dates = [], []
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]; amap = assign(d); pm = pym(d)
        q = []
        for s, sec in amap.items():
            if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
            r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
            b_ok = rsi_of_rs_recovery(s, sec, i)
            if r_ok or b_ok:
                b = beta_of(s, i)
                if b is None or b <= 1.4:
                    q.append(s)
        sel = q[:60]
        w = {s: 1.0/60 for s in sel}
        turn = sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))
        r = -COST*turn
        for s in w:
            if s not in held:
                p = pxn(s, d); ent[s] = p; pk[s] = p or 0
        held = w
        inv = sum(held.values())
        for s, x in list(held.items()):
            a, b = pxn(s, d), pxn(s, dn)
            if a and b:
                hit = False
                for j in range(ci[d]+1, ci[dn]+1):
                    q_ = sclose[s].get(cal[j])
                    if not q_: continue
                    if q_ > pk.get(s, 0): pk[s] = q_
                    if q_ <= pk[s]*(1-0.20):
                        r += x*((pk[s]*0.80*0.99)/a-1.0); hit = True; break
                if hit: del held[s]; ent.pop(s, None); pk.pop(s, None)
                else: r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]
        idle = max(0.0, 1.0 - inv)
        if idle > 0 and b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]:
            a, b = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
            if a and b: r += idle*(b/a-1.0)
        rets.append(r); dates.append(d)
    return rets, dates, rb

# ---- LOWVOL_MOM on the SAME quarterly grid via the rule-lab machinery ----
import numpy as np
import explosive_moves.rule_lab_executor as rlx
from explosive_moves.embase import load_symbol_cache
print("[rule-lab] loading em_cache...", file=sys.stderr, flush=True)
cache = load_symbol_cache()
spec = rlx.compile_rule("SELECT largecap WHERE not_extended RANK BY lowvolmom TAKE 25 HOLD quarterly")
START = "2012-07-01"
union_dates = [d for d in rebal_all if d >= START]
rlx.REBAL_STEP = dict(rlx.REBAL_STEP); rlx.REBAL_STEP["quarterly"] = 1   # grid = the dates we pass
tables = rlx.build_rule_tables(spec, cache=cache, cal=union_dates)
lv_rets_arr, lv_dates, _roster, lv_costs, lv_turns = rlx.run_book(
    tables, rlx._SIG_FN["lowvolmom"], spec.take, val_guard=("not_extended" in spec.filters),
    cost_mode="real")
lv = dict(zip(lv_dates, [float(x) for x in lv_rets_arr]))
print(f"[rule-lab] LOWVOL_MOM periods {len(lv)} on the union grid; ann cost ~{float(np.mean(lv_costs))*4*100:.2f}%",
      file=sys.stderr, flush=True)

u_rets, u_dates, rb = b14_rets(START, "2026-12-31")
common = [d for d in u_dates if d in lv]
U = [u_rets[u_dates.index(d)] for d in common]
V = [lv[d] for d in common]
BR = []
for d in common:
    dn = rb[rb.index(d)+1]
    BR.append(iclose[BENCH][dn]/iclose[BENCH][d]-1.0)

def stats(r, br, ppy=4.0, tag=""):
    n = len(r); y = n/ppy
    nav = 1.0; navs=[1.0]
    for x in r: nav *= (1+x); navs.append(nav)
    def dd(v):
        pk_, mx = v[0], 0.0
        for x in v: pk_ = max(pk_, x); mx = min(mx, x/pk_-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    alpha = (m - b*mb)*ppy
    print("  %-34s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%"
          % (tag, (nav**(1/y)-1)*100, dd(navs)*100, nav, b, alpha*100), flush=True)
    return nav**(1/y)-1

print("=" * 110)
print("BLEND — union-beta14 ⊕ LOWVOL_MOM largecap quarterly, 50/50, union grid, overlap %s -> %s (%d qtrs)"
      % (common[0], common[-1], len(common)))
print("=" * 110)
mu, mv = sum(U)/len(U), sum(V)/len(V)
su = math.sqrt(sum((x-mu)**2 for x in U)/(len(U)-1))
sv = math.sqrt(sum((x-mv)**2 for x in V)/(len(V)-1))
cuv = sum((U[i]-mu)*(V[i]-mv) for i in range(len(U)))/(len(U)-1)
print("  return correlation (quarterly): %.2f" % (cuv/(su*sv)))
stats(U, BR, tag="union-beta14 (overlap)")
stats(V, BR, tag="LOWVOL_MOM largecap q (real cost)")
stats([(U[i]+V[i])/2 for i in range(len(U))], BR, tag="BLEND 50/50")
sub = [i for i, d in enumerate(common) if d <= "2017-12-31"]
if len(sub) >= 8:
    print("  --- 2012-2017 sub-window ---")
    stats([U[i] for i in sub], [BR[i] for i in sub], tag="union-beta14")
    stats([V[i] for i in sub], [BR[i] for i in sub], tag="LOWVOL_MOM")
    stats([(U[i]+V[i])/2 for i in sub], [BR[i] for i in sub], tag="BLEND 50/50")
print("done.", flush=True)
