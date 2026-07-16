"""RSI BATTERY (Ramana, 2026-07-16): "identify each stock's RSI. For any stock whose RSI has crossed
the 50-day moving average (the RSI's MA, NOT the price MA), assess its strengths... considering volume,
sector performance, and peer movement."

ARCHITECTURE = 2b (his literal reading): RSI-scan FIRST across the whole market; sector performance is
ONE INPUT to a strength score, NOT a hard pre-filter. Architecture 2a (sector-gate-first) is run as a
comparison row so the two are visible side by side.

PERFORMANCE NOTE: the earlier battery recomputed EMA windows per-stock-per-rule and never finished.
This precomputes RSI(n) and its MA ONCE per stock across the whole calendar, then every variant is a
cache lookup. That is the only reason 20+ cells are affordable.

WHAT IS TESTED
  Dim 1 RSI construction : period 9/14/21 x MA type SMA/EMA x signal STATE vs EVENT(crossed <=20d)
  Dim 3 strength index   : volume (turnover_surge_3m) · sector (6m RS excess) · peer (rank within
                           own sector) · BREADTH (% of sector peers also RSI-crossed) <- Codex's Q4
                           "breadth confirmation", never tested
  Dim 4 combination      : z-score average · sequential AND-filter · rank-percentile blend
  Dim 6 reversal-on-RS   : 6a slope inflection (RS below its own average but slope turning UP) and
                           6g cross-sectional rank climb (bottom third -> middle/top third)
                           -- the two Ramana ranked highest-prior; 6c (Bollinger reclaim) deliberately
                           HELD BACK so a failure there is not misread as "reversal is dead"
  Dim 5 construction     : reuse what is already proven -- trailing -20% stop @1% slip, consistency>=70%

FOUNDATION (fixed, not re-litigated): corporate-action adjusted · 156 symbols quarantined (runtime-only)
· prior-month ADV >= Rs5cr (no look-ahead) · PIT · quarterly · equal-weight (inverse-vol deprioritized
per Ramana) · dead names realise -50%, vanished-but-alive are carried.

ALREADY FALSIFIED — NOT re-tested (cite, do not repeat): sign-flip "the turn" (15Q, flat panel) ·
static RS-level gates +8%/RS>50DMA (15N/15Q, worst of five) · BE-surveillance veto (16T, sd falls,
return falls more) · fundamentals veto (16T, inert) · price-band mean reversion (07-13, 07-14b).
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
LB, QTR, CORRWIN, ADV_BAR, COST, DEAD_VAL = 126, 63, 500, 5e7, 0.0015, -0.50

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name,trade_date,close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
sclose = defaultdict(dict)
for s, d, c in conn.execute("SELECT symbol,trade_date,close FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') AND close>0"):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("SELECT symbol,substr(trade_date,1,7),avg(value),count(*) FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"):
    if n >= 15 and a: adv[s][ym] = a
surge = defaultdict(dict)
for s, d, v in conn.execute("SELECT symbol,trade_date,turnover_surge_3m FROM stock_signals WHERE turnover_surge_3m IS NOT NULL"):
    surge[s][d] = v
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()
print(f"[quarantine] {len(QUAR)} excluded | [volume] {len(surge):,} syms have turnover_surge_3m", file=sys.stderr)

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}
N = len(cal)

# ================= PRECOMPUTE: RSI(n) and its MA, once per stock =================
def rsi_series(px, n):
    """Wilder RSI over the full calendar. None until warm."""
    out = [None]*N
    gain = loss = None
    prev = None
    for i in range(N):
        p = px.get(cal[i])
        if p is None:
            out[i] = out[i-1] if i else None
            continue
        if prev is None:
            prev = p; continue
        ch = p - prev; prev = p
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if gain is None:
            gain, loss = g, l
        else:
            gain = (gain*(n-1) + g)/n
            loss = (loss*(n-1) + l)/n
        if loss == 0: out[i] = 100.0
        elif gain == 0: out[i] = 0.0
        else: out[i] = 100.0 - 100.0/(1.0 + gain/loss)
    return out

def ma_series(x, n, kind):
    out = [None]*len(x)
    if kind == "EMA":
        a = 2.0/(n+1); e = None; warm = []
        for i, v in enumerate(x):
            if v is None: out[i] = e; continue
            if e is None:
                warm.append(v)
                if len(warm) >= n: e = sum(warm)/len(warm)
                out[i] = e; continue
            e = a*v + (1-a)*e; out[i] = e
    else:
        buf = []
        for i, v in enumerate(x):
            if v is not None: buf.append(v)
            if len(buf) > n: buf.pop(0)
            out[i] = sum(buf)/len(buf) if len(buf) >= n else None
    return out

SYMS = [s for s, cl in sclose.items() if s not in QUAR and len(cl) >= 400]
print(f"[precompute] RSI+MA for {len(SYMS):,} symbols...", file=sys.stderr)
RSI, RSIMA = {}, {}
for period in (9, 14, 21):
    RSI[period] = {}
    for s in SYMS:
        RSI[period][s] = rsi_series(sclose[s], period)
    for kind in ("SMA", "EMA"):
        RSIMA[(period, kind)] = {s: ma_series(RSI[period][s], 50, kind) for s in SYMS}
    print(f"  RSI({period}) done", file=sys.stderr)

def rsi_state(s, i, period, kind):
    r, m = RSI[period][s][i], RSIMA[(period, kind)][s][i]
    return None if (r is None or m is None) else r > m

def rsi_event(s, i, period, kind, within=20):
    r, m = RSI[period][s], RSIMA[(period, kind)][s]
    if r[i] is None or m[i] is None or r[i] <= m[i]: return False
    for j in range(max(1, i-within), i+1):
        if r[j-1] is not None and m[j-1] is not None and r[j] is not None and m[j] is not None:
            if r[j-1] <= m[j-1] and r[j] > m[j]: return True
    return False

# ================= sector assignment (PIT correlation), cached per year =================
bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, N)]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, N)] for nm in SECTORS}
stock_ex = {}
for s in SYMS:
    cl = sclose[s]
    stock_ex[s] = [((cl.get(cal[i]) or 0)/(cl.get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                   if (cl.get(cal[i]) and cl.get(cal[i-1])) else None for i in range(1, N)]

def _corr(x, y, lo, hi):
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
            c = _corr(stock_ex[s], sec_ex[nm], lo, i)
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

def sec_excess6m(nm, i):
    if i-LB < 0: return None
    a, b = iclose[nm].get(cal[i-LB]), iclose[nm].get(cal[i])
    ba, bb = iclose[BENCH].get(cal[i-LB]), iclose[BENCH].get(cal[i])
    if not (a and b and ba and bb): return None
    return (b/a-1.0)-(bb/ba-1.0)

def stock_ret(s, i, w):
    if i-w < 0: return None
    a, b = sclose[s].get(cal[i-w]), sclose[s].get(cal[i])
    return (b/a-1.0) if (a and b) else None

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

def rs_slope_inflect(s, sec, i):
    """Dim 6a: RS below its own 50d average (a laggard) BUT its short slope has turned UP.
    This is the exact cell 15Q left untested — it tested a sign flip (state), not a derivative."""
    if i-QTR < 0: return False
    def rs(j):
        a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
        return a/b if (a and b) else None
    now, mid, old = rs(i), rs(i-21), rs(i-42)
    if None in (now, mid, old): return False
    win = [rs(j) for j in range(max(0, i-50), i+1)]
    win = [x for x in win if x is not None]
    if len(win) < 30: return False
    avg = sum(win)/len(win)
    below = now < avg                 # still a laggard
    turned = (now - mid) > 0 and (mid - old) <= 0   # slope flipped from falling to rising
    return below and turned

# ================= the run =================
rebal = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 200)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(rebal)} quarterly dates {rebal[0]} -> {rebal[-1]}", file=sys.stderr)

def build_pool(d, period, kind, event, gate_sector):
    """all candidates passing the RSI trigger; returns [(sym, sec)]"""
    i = ci[d]; amap = assign(d); pm = pym(d)
    qs = None
    if gate_sector:
        qs = {nm for nm in SECTORS if (sec_excess6m(nm, i) or -9) > 0.08}
    out = []
    for s, sec in amap.items():
        if gate_sector and sec not in qs: continue
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        ok = rsi_event(s, i, period, kind) if event else rsi_state(s, i, period, kind)
        if not ok: continue
        out.append((s, sec))
    return out

def score(d, pool, method):
    """strength index: volume + sector + peer + breadth"""
    i = ci[d]
    if not pool: return []
    bysec = defaultdict(list)
    for s, sec in pool: bysec[sec].append(s)
    peers_all = defaultdict(list)
    amap = assign(d)
    for s, sec in amap.items(): peers_all[sec].append(s)
    rows = []
    for s, sec in pool:
        vol = surge.get(s, {}).get(d)
        if vol is None:
            for k in range(1, 6):
                vol = surge.get(s, {}).get(cal[i-k])
                if vol is not None: break
        secs = sec_excess6m(sec, i)
        r3 = stock_ret(s, i, QTR)
        peer_rets = [stock_ret(p, i, QTR) for p in peers_all.get(sec, [])]
        peer_rets = [x for x in peer_rets if x is not None]
        peer_rank = (sum(1 for x in peer_rets if x < r3)/len(peer_rets)) if (r3 is not None and peer_rets) else None
        breadth = len(bysec[sec])/max(len(peers_all.get(sec, [])), 1)
        rows.append(dict(s=s, sec=sec, vol=vol, secs=secs, peer=peer_rank, breadth=breadth))
    def z(key):
        vals = [r[key] for r in rows if r[key] is not None]
        if len(vals) < 3: return {r['s']: 0.0 for r in rows}
        m = sum(vals)/len(vals)
        sd = math.sqrt(sum((v-m)**2 for v in vals)/(len(vals)-1)) or 1.0
        return {r['s']: ((r[key]-m)/sd if r[key] is not None else 0.0) for r in rows}
    if method == "zavg":
        zv, zs, zp, zb = z('vol'), z('secs'), z('peer'), z('breadth')
        return sorted(rows, key=lambda r: -(zv[r['s']]+zs[r['s']]+zp[r['s']]+zb[r['s']])/4.0)
    if method == "andfilter":
        keep = [r for r in rows if (r['vol'] or 0) > 1.0 and (r['secs'] or -9) > 0 and (r['peer'] or 0) > 0.5]
        return sorted(keep, key=lambda r: -(r['peer'] or 0))
    if method == "rankblend":
        def pct(key):
            vals = sorted([r[key] for r in rows if r[key] is not None])
            def f(v):
                if v is None or not vals: return 0.5
                return sum(1 for x in vals if x < v)/len(vals)
            return {r['s']: f(r[key]) for r in rows}
        pv, ps, pp, pb = pct('vol'), pct('secs'), pct('peer'), pct('breadth')
        return sorted(rows, key=lambda r: -(pv[r['s']]+ps[r['s']]+pp[r['s']]+pb[r['s']])/4.0)
    if method == "breadth":
        return sorted(rows, key=lambda r: -r['breadth'])
    return rows

def run(period=14, kind="EMA", event=False, gate_sector=False, method="zavg", topn=40,
        trail=None, slip=0.0, consist=None, inflect=False):
    nav = bnav = 1.0; navs, bnavs = [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        i = ci[d]
        pool = build_pool(d, period, kind, event, gate_sector)
        if consist is not None:
            pool = [(s, sec) for s, sec in pool if (consistency(s, sec, i) or 0) >= consist]
        if inflect:
            pool = [(s, sec) for s, sec in pool if rs_slope_inflect(s, sec, i)]
        ranked = score(d, pool, method)
        sel = [r['s'] for r in ranked[:topn]]
        if sel:
            w = {s: 1.0/len(sel) for s in sel}
            turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
            nav *= (1-COST*turn)
            for s in w:
                if s not in held:
                    p = pxn(s, d); ent[s] = p; pk[s] = p or 0
            held = w
        r = 0.0
        for s, x in list(held.items()):
            a, b = pxn(s, d), pxn(s, dn)
            if a and b:
                hit = False
                if trail and ent.get(s):
                    for j in range(ci[d]+1, ci[dn]+1):
                        q = sclose[s].get(cal[j])
                        if not q: continue
                        if q > pk.get(s, 0): pk[s] = q
                        if q <= pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit = True; break
                if hit: del held[s]; ent.pop(s, None); pk.pop(s, None)
                else: r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs

def stat(navs, bnavs):
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); y = n/4.0
    def dd(v):
        pk, mx = v[0], 0.0
        for x in v: pk = max(pk, x); mx = min(mx, x/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    return navs[-1]**(1/y)-1, dd(navs), navs[-1], b

def go(tag, **kw):
    navs, bnavs = run(**kw)
    c, d_, m, b = stat(navs, bnavs)
    print("  %-50s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%7.2fx  beta %.2f" % (tag, c*100, d_*100, m, b), flush=True)
    return c, m

print("\n" + "="*112)
print("RSI BATTERY — architecture 2b (RSI-scan first, sector as a SCORE input not a gate)")
print("="*112)
d0, d1 = rebal[0], rebal[-1]; y = (len(rebal)-1)/4.0
bm = iclose[BENCH][d1]/iclose[BENCH][d0]
print("  %-50s CAGR %5.1f%%  %25s Rs1Cr->%7.2fx" % ("Nifty 500 (bar, same window)", (bm**(1/y)-1)*100, "", bm))

print("\n--- Dim 1: RSI construction (period x MA type x state/event) ---")
for p in (9, 14, 21):
    for kind in ("SMA", "EMA"):
        go(f"RSI({p}) vs its 50-{kind}, STATE", period=p, kind=kind, event=False)
go("RSI(14) vs 50-EMA, EVENT (crossed <=20d)", period=14, kind="EMA", event=True)

print("\n--- Dim 4: strength-index combination (RSI(14)/50-EMA state) ---")
for meth in ("zavg", "andfilter", "rankblend", "breadth"):
    go(f"score = {meth}", method=meth)

print("\n--- Dim 2: architecture 2a vs 2b ---")
go("2b: no sector gate (sector = score input)", gate_sector=False)
go("2a: sector-gate-first (+8%), then RSI", gate_sector=True)

print("\n--- Dim 6: reversal-on-RS (6a slope inflection) ---")
go("6a: RS below own avg BUT slope turning UP", inflect=True)
go("6a + trail-20% slip1%", inflect=True, trail=0.20, slip=0.01)

print("\n--- Dim 5: stack the two things already proven ---")
go("+ consistency>=70%", consist=0.70)
go("+ trail-20% slip1%", trail=0.20, slip=0.01)
go("+ consistency>=70% + trail-20% slip1%", consist=0.70, trail=0.20, slip=0.01)

print("\n--- book size on the stacked config ---")
for n in (20, 40, 60):
    go(f"consist>=70% + trail-20% slip1%, top{n}", consist=0.70, trail=0.20, slip=0.01, topn=n)
