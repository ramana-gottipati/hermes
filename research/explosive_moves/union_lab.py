"""UNION CANDIDATE LAB — selection-fix + turn-family candidates run BESIDE the sealed union.

Session 2026-07-16 (post-seal). The union spec is SEALED (docs/prereg/union-prereg.md,
sha256 a9a14058f2140e22639b9504ab6d4af9c60fc76144de0f9f5e47f21b1b98d21c) — NOTHING here touches it.
Every variant is a CANDIDATE per the carry-forward's binding rule: it must beat the union's
17.5% CAGR / beta 0.87 / alpha +6.8% on WALK-FORWARD (all three windows reported, not one),
or it is recorded in the ledger as tested-and-rejected.

LEDGER BLOCKS CITED (failure-ledger discipline — blocking until cited):
  * throttle (16W): every exposure throttle made every metric worse (best 16.6% vs 17.5%;
    2012-17 beta 1.42->1.35 only). NOT re-run. The levers below act at SELECTION (which stocks),
    not exposure (how much).
  * inverse-vol SIZING (16X): wash (17.0%/+6.3% vs 17.5%/+6.8%). NOT re-run. s_beta_* below pick
    DIFFERENT stocks (selection); they do not re-weight the same stocks (sizing).
  * AND-intersection (16V): 8.6% CAGR at 9%% invested. NOT re-run. t_mtf below is a different AND
    (same signal across TIMEFRAMES, not the two mutually-exclusive signals ANDed).
  * BE veto + fundamentals veto (16T): falsified / inert. NOT re-run.
  * 6f SOLO (16U): ns (+0.37%% vs base, GEO -0.98%%) — re-enters ONLY as an OR-leg beside 6b
    (catalog lists the combo as genuinely untried), never as a solo selector.
  * 6a/6c/6d/6e/6g/6h (16U): dead or harmful — not re-run in any form.

THE ONE REAL QUESTION (16W/16X): 2012-17 is unreachable by sizing => fix WHICH stocks get picked
in a mid-cycle bull. 16V: in 2012-17 the TREND leg alone was alpha -3.5%% while 6b alone was +2.4%%
— the trend leg's picks are the problem there.

  S-family (selection, on the baseline union's qualifiers):
    s_rank_rsi_desc  the DOCUMENTED rule (union.md says "top 60 by RSI strength"; the sealed code
                     truncates in symbol-load order instead — this row measures the doc's rule)
    s_rank_rsi_asc   least-extended 60 (15P: "best of best" is dominated by "good")
    s_sector_cap8/6  per-sector name caps (the book can't pile into one hot sector)
    s_beta_cap14/12  per-name trailing-250d-beta cap at selection (NOT 16W's book-level lever)
    s_beta_rank_asc  lowest-beta 60 of the qualifiers (selection analog of the LOWVOL_MOM family)
  T-family (turn leg):
    t_6b_25 / t_6b_35 / t_6b_25to30   6b threshold sweep (sealed = <30 -> >=30)
    t_6b_or_6f       third OR-leg: RS drawdown recovery (dim6.i6f params: 126d, -15%%, within 5%%)
    t_weekly_6b      6b computed on the WEEKLY RS line (slower, higher-conviction turn)
    t_mtf_confirm    both legs need weekly agreement (trend: weekly RS > 26wk SMA;
                     turn: weekly RS-RSI not falling vs 2 weeks ago)

Foundation is copied from cash_blend.py byte-for-byte where it matters (CA-adjusted, quarantined,
prior-month ADV >= Rs5cr, PIT sector assign 500d excess-corr, sleeve200, trail-20%% @1%% slip,
0.15%%/side, dead -50%%, fixed 1/60 sizing). u0_base MUST reproduce the sealed 17.5%%/26.04x
within data-refresh noise; if it does not, STOP — investigate before reading any variant row.
"""
import sqlite3, sys, math, bisect, datetime
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH, SLEEVE = "Nifty 500", "Nifty Next 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
IDX = [BENCH, SLEEVE, "Nifty 50", "Nifty 100", "Nifty Midcap 50"]
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
print(f"[precompute] RSI(14)+50SMA for {len(SYMS):,} symbols...", file=sys.stderr, flush=True)
RSI = {s: rsi_series(sclose[s]) for s in SYMS}
RMA = {s: sma(RSI[s], 50) for s in SYMS}

bench_r = [iclose[BENCH][cal[i]]/iclose[BENCH][cal[i-1]]-1.0 for i in range(1, N)]
sec_ex = {nm: [((iclose[nm].get(cal[i]) or 0)/(iclose[nm].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
               if (iclose[nm].get(cal[i]) and iclose[nm].get(cal[i-1])) else None
               for i in range(1, N)] for nm in SECTORS}
stock_ex = {s: [((sclose[s].get(cal[i]) or 0)/(sclose[s].get(cal[i-1]) or 1)-1.0)-bench_r[i-1]
                if (sclose[s].get(cal[i]) and sclose[s].get(cal[i-1])) else None
                for i in range(1, N)] for s in SYMS}

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

_turn_memo = {}
def rsi_of_rs_recovery(s, sec, i, lo=30.0, hi=30.0):
    key = (s, i, lo, hi)
    if key in _turn_memo: return _turn_memo[key]
    w = [x for x in (rs_at(s, sec, j) for j in range(max(0, i-60), i+1)) if x is not None]
    r = False
    if len(w) >= 40:
        now=_rsi_vals(w); prev=_rsi_vals(w[:-10]) if len(w)>50 else None
        if now is not None and prev is not None:
            r = prev < lo and now >= hi
    _turn_memo[key] = r
    return r

_6f_memo = {}
def rs_dd_recovery(s, sec, i):
    key = (s, i)
    if key in _6f_memo: return _6f_memo[key]
    w = [x for x in (rs_at(s, sec, j) for j in range(max(0, i-126), i+1)) if x is not None]
    r = False
    if len(w) >= 80:
        hi = max(w); tr = min(w)
        if hi > 0:
            r = (tr/hi - 1.0) < -0.15 and (w[-1]/hi - 1.0) > -0.05
    _6f_memo[key] = r
    return r

# ---- weekly machinery: last trading day of each ISO week ----
wk_end = []
_pk = None
for j, d in enumerate(cal):
    key = datetime.date.fromisoformat(d).isocalendar()[:2]
    if _pk is not None and key != _pk: wk_end.append(j-1)
    _pk = key
wk_end.append(N-1)

def weekly_rs_vals(s, sec, i, nweeks=60):
    pos = bisect.bisect_left(wk_end, i)
    idxs = wk_end[max(0, pos-nweeks):pos]
    vals = [rs_at(s, sec, j) for j in idxs] + [rs_at(s, sec, i)]
    return [x for x in vals if x is not None]

_wk_memo = {}
def weekly_6b(s, sec, i):
    key = (s, i)
    if key in _wk_memo: return _wk_memo[key]
    w = weekly_rs_vals(s, sec, i, 60)
    r = False
    if len(w) >= 40:
        now = _rsi_vals(w); prev = _rsi_vals(w[:-2]) if len(w) > 20 else None
        if now is not None and prev is not None:
            r = prev < 30 and now >= 30
    _wk_memo[key] = r
    return r

_wt_memo = {}
def weekly_trend_ok(s, sec, i):
    key = (s, i)
    if key in _wt_memo: return _wt_memo[key]
    w = weekly_rs_vals(s, sec, i, 40)
    r = False
    if len(w) >= 27:
        r = w[-1] > sum(w[-26:])/26
    _wt_memo[key] = r
    return r

_wa_memo = {}
def weekly_turn_agrees(s, sec, i):
    key = (s, i)
    if key in _wa_memo: return _wa_memo[key]
    w = weekly_rs_vals(s, sec, i, 60)
    r = False
    if len(w) >= 20:
        a = _rsi_vals(w); b = _rsi_vals(w[:-2])
        if a is not None and b is not None:
            r = a >= b
    _wa_memo[key] = r
    return r

_cons_memo = {}
def consistency(s, sec, i):
    key = (s, i)
    if key in _cons_memo: return _cons_memo[key]
    lo = i-QTR
    r = None
    if lo >= 0:
        a0, b0 = sclose[s].get(cal[lo]), iclose[sec].get(cal[lo])
        if a0 and b0:
            ahead = tot = 0
            for j in range(lo+1, i+1):
                a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
                if not (a and b): continue
                tot += 1
                if (a/a0) > (b/b0): ahead += 1
            r = ahead/tot if tot >= QTR*0.6 else None
    _cons_memo[key] = r
    return r

def sig_rsi(s, sec, i):
    r, m = RSI[s][i], RMA[s][i]
    return (r is not None and m is not None and r > m)

# ---- per-name trailing beta vs Nifty 500 (PIT, 250d, min 150 obs) ----
_beta_memo = {}
def beta_of(s, i, look=250, minn=150):
    key = (s, i)
    if key in _beta_memo: return _beta_memo[key]
    lo = max(1, i-look)
    n=0; sx=sy=sxx=sxy=0.0
    for j in range(lo, i+1):
        a0, a1 = sclose[s].get(cal[j-1]), sclose[s].get(cal[j])
        if not (a0 and a1): continue
        x = bench_r[j-1]; y = a1/a0-1.0
        n+=1; sx+=x; sy+=y; sxx+=x*x; sxy+=x*y
    b = None
    if n >= minn:
        vx = sxx - sx*sx/n
        if vx > 0: b = (sxy - sx*sy/n)/vx
    _beta_memo[key] = b
    return b

rebal_all = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 250)
             and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

# ---- qualifier precompute: MODES x rebalance dates, each entry = ordered [(s, sec), ...] ----
MODES = ("base", "t25", "t35", "t2530", "t6f", "tweek", "tmtf")
def qualify(d, mode):
    i = ci[d]; amap = assign(d); pm = pym(d)
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
        if mode == "tmtf" and r_ok:
            r_ok = weekly_trend_ok(s, sec, i)
        if   mode == "t25":   b_ok = rsi_of_rs_recovery(s, sec, i, 25, 25)
        elif mode == "t35":   b_ok = rsi_of_rs_recovery(s, sec, i, 35, 35)
        elif mode == "t2530": b_ok = rsi_of_rs_recovery(s, sec, i, 25, 30)
        elif mode == "tweek": b_ok = weekly_6b(s, sec, i)
        else:                 b_ok = rsi_of_rs_recovery(s, sec, i, 30, 30)
        if mode == "t6f" and not b_ok:
            b_ok = rs_dd_recovery(s, sec, i)
        if mode == "tmtf" and b_ok:
            b_ok = weekly_turn_agrees(s, sec, i)
        if r_ok or b_ok:
            out.append((s, sec))
    return out

QUAL = {m: {} for m in MODES}
for mi, m in enumerate(MODES):
    print(f"[precompute] qualifiers {m} ({mi+1}/{len(MODES)})...", file=sys.stderr, flush=True)
    for d in rebal_all:
        QUAL[m][d] = qualify(d, m)

# ---- selection hooks (operate on the ordered qualifier list; run() slices [:topn] after) ----
def sel_default(q, d, i, topn):
    return [s for s, _ in q]

def sel_rsi_desc(q, d, i, topn):
    return [s for s, _ in sorted(q, key=lambda t: -(RSI[t[0]][i] if RSI[t[0]][i] is not None else -1))]

def sel_rsi_asc(q, d, i, topn):
    return [s for s, _ in sorted(q, key=lambda t: (RSI[t[0]][i] if RSI[t[0]][i] is not None else 999))]

def sel_sector_cap(cap):
    def f(q, d, i, topn):
        cnt = defaultdict(int); out = []
        for s, sec in q:
            if cnt[sec] >= cap: continue
            cnt[sec] += 1; out.append(s)
            if len(out) >= topn: break
        return out
    return f

def sel_beta_cap(mx):
    def f(q, d, i, topn):
        return [s for s, _ in q if (beta_of(s, i) is None or beta_of(s, i) <= mx)]
    return f

def sel_beta_asc(q, d, i, topn):
    scored = [(s, beta_of(s, i)) for s, _ in q]
    return [s for s, b in sorted(scored, key=lambda t: (t[1] if t[1] is not None else 9.9))]

def run(mode="base", hook=sel_default, topn=60, trail=0.20, slip=0.01, start=None, end=None):
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac, nsel = [], [], [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = hook(QUAL[mode][d], d, i, topn)[:topn]
        w = {s: 1.0/topn for s in sel}
        nsel.append(len(sel))
        turn = sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))
        nav *= (1-COST*turn)
        for s in w:
            if s not in held:
                p = pxn(s, d); ent[s] = p; pk[s] = p or 0
        held = w
        inv = sum(held.values()); invfrac.append(inv)
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
        idle = max(0.0, 1.0 - inv)
        if idle > 0:
            ok = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if ok:
                a, b = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
                if a and b: r += idle*(b/a-1.0)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, invfrac, nsel, rb

def stat(navs, bnavs):
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); y = n/4.0
    def dd(v):
        pk, mx = v[0], 0.0
        for x in v: pk = max(pk, x); mx = min(mx, x/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    sd = math.sqrt(sum((x-m)**2 for x in r)/(n-1))
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    alpha = (m - b*mb)*4
    return dict(cagr=navs[-1]**(1/y)-1, dd=dd(navs), mult=navs[-1], beta=b, alpha=alpha)

def bench_cagr(nm, rb):
    a, b = iclose[nm].get(rb[0]), iclose[nm].get(rb[-1])
    if not (a and b): return None
    yy = (len(rb)-1)/4.0
    return (b/a)**(1/yy)-1

WIN = ((None, None, "FULL 2006-2026"),
       ("2006-01-01", "2011-12-31", "2006-2011"),
       ("2012-01-01", "2017-12-31", "2012-2017"),
       ("2018-01-01", "2026-12-31", "2018-2026"))

print("=" * 118)
print("UNION CANDIDATE LAB — every row = sealed union + ONE change; bar = 17.5%/beta0.87/alpha+6.8% ON WALK-FORWARD")
print("=" * 118)
for stt, en, wtag in WIN:
    rb = [d for d in rebal_all if (stt is None or d >= stt) and (en is None or d <= en)]
    n5 = bench_cagr(BENCH, rb); nn = bench_cagr(SLEEVE, rb)
    print("  bench %-14s  Nifty500 %5.1f%%   Next50 %5.1f%%" % (wtag, (n5 or 0)*100, (nn or 0)*100))

ROWS = [
    ("u0_base (sealed union, repro)",          "base",  sel_default),
    ("s_rank_rsi_desc (documented rule)",      "base",  sel_rsi_desc),
    ("s_rank_rsi_asc (least-extended 60)",     "base",  sel_rsi_asc),
    ("s_sector_cap8",                          "base",  sel_sector_cap(8)),
    ("s_sector_cap6",                          "base",  sel_sector_cap(6)),
    ("s_beta_cap_1.4",                         "base",  sel_beta_cap(1.4)),
    ("s_beta_cap_1.2",                         "base",  sel_beta_cap(1.2)),
    ("s_beta_rank_asc (lowest-beta 60)",       "base",  sel_beta_asc),
    ("t_6b_25 (<25 -> >=25)",                  "t25",   sel_default),
    ("t_6b_35 (<35 -> >=35)",                  "t35",   sel_default),
    ("t_6b_25to30 (deep dip, confirm 30)",     "t2530", sel_default),
    ("t_6b_or_6f (third OR-leg)",              "t6f",   sel_default),
    ("t_weekly_6b (weekly RS turn)",           "tweek", sel_default),
    ("t_mtf_confirm (daily AND weekly)",       "tmtf",  sel_default),
]

for tag, mode, hook in ROWS:
    print("")
    print("### %s" % tag, flush=True)
    for stt, en, wtag in WIN:
        navs, bnavs, inv, nsel, rb = run(mode=mode, hook=hook, start=stt, end=en)
        if len(navs) < 8:
            print("  %-14s too short" % wtag); continue
        s = stat(navs, bnavs)
        nn = bench_cagr(SLEEVE, rb)
        print("  %-14s CAGR %5.1f%% (Next50 %5.1f%%)  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%  n %4.1f"
              % (wtag, s['cagr']*100, (nn or 0)*100, s['dd']*100, s['mult'], s['beta'],
                 s['alpha']*100, sum(inv)/len(inv)*100, sum(nsel)/len(nsel)), flush=True)

print("")
print("done.", flush=True)
