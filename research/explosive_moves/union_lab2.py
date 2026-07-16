"""UNION LAB 2 — adversarial diagnostics on the beta-cap-1.4 lead + the quality TILT candidate.

Session 2026-07-16 (post-seal). union_lab.py found s_beta_cap_1.4 (per-name trailing-250d beta <= 1.4
at SELECTION) beats the sealed union on every headline metric AND flips 2012-17 alpha -4.6% -> +3.4%.
Before any promotion claim, this module attacks that result. PROTOCOL DECLARED UP FRONT:
  * The candidate REMAINS beta<=1.4/250d as first-declared in union_lab.py. The sweeps below test
    STABILITY only — a smoother/better-looking neighbor does NOT replace the candidate (that would
    be re-optimizing in-sample, the exact 15R sin).
  * KILL conditions (any one kills the promotion): (a) the 1.4 result is an isolated spike vs
    1.3/1.5/1.6 neighbors; (b) the result dies when the beta window changes (125d/500d);
    (c) the 2012-17 fix disappears in CASH money-mode (i.e. the "fix" was just more sleeve time
    in a Next-50-friendly window — the way the 16W throttle failed); (d) the cap turns out to be
    mostly a missing-data filter (large kept-because-missing or excluded-for-missing counts).

QUALITY TILT (direction 1c, the last untried non-ML lever): fundamentals_history (research.db,
SCREENER-sourced — Guardrail #8: read-only, disclosed, any result inherits the caveat; 16T precedent).
NOT the 16T veto (inert): a within-date percentile RANK. Score declared BEFORE seeing results:
  mean of within-rebalance-date percentiles of (1) OPM%%, (2) interest coverage = OperatingProfit /
  max(Interest, 0.01) capped at 20, (3) Net Profit > 0 as {0,1}. Missing component -> 0.5 neutral;
  no filing <= d -> overall 0.5 (absence != red flag, the 16T convention). PIT via report_date.
  Doctrine tension recorded: 16T grounded "fundamentals stay veto-only, never a ranker" in
  momentum-is-beta(t=1.99); the carry-forward's untried list explicitly sanctions a SELECTION tilt.
  This run adjudicates with numbers; a null REAFFIRMS the veto-only doctrine.
  Variants: q_rank_top60 (top 60 by score) · q_drop_worst25 (drop score<0.25, engine order).

Foundation byte-copied from cash_blend.py (CA-adjusted, quarantined, prior-month ADV >= Rs5cr, PIT
sector assign, sleeve200, trail-20%% @1%% slip, 0.15%%/side, dead -50%%, fixed 1/60). u0_base must
reproduce 17.5%%/26.04x again as the in-module control.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
RDB = sys.argv[2] if len(sys.argv) > 2 else "data/research.db"
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

# ---- fundamentals (research.db, read-only; Guardrail #8 disclosed) ----
FUND = {}
try:
    rconn = sqlite3.connect(f"file:{RDB}?mode=ro", uri=True)
    rows = defaultdict(lambda: defaultdict(dict))
    q = """SELECT symbol, report_date, metric, value FROM fundamentals_history
           WHERE report_date IS NOT NULL AND value IS NOT NULL
             AND metric IN ('Net Profit','Interest','Operating Profit','OPM %')"""
    for sym, rd, metric, val in rconn.execute(q):
        try:
            rows[sym][rd][metric] = float(val)
        except (TypeError, ValueError):
            continue
    for sym, byrd in rows.items():
        FUND[sym] = sorted(byrd.items())
    rconn.close()
    print(f"[fund] {len(FUND):,} symbols with filings", file=sys.stderr, flush=True)
except Exception as e:
    print(f"[fund] UNAVAILABLE ({e}) — quality rows will be skipped", file=sys.stderr, flush=True)

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
def rsi_of_rs_recovery(s, sec, i):
    key = (s, i)
    if key in _turn_memo: return _turn_memo[key]
    w = [x for x in (rs_at(s, sec, j) for j in range(max(0, i-60), i+1)) if x is not None]
    r = False
    if len(w) >= 40:
        now=_rsi_vals(w); prev=_rsi_vals(w[:-10]) if len(w)>50 else None
        if now is not None and prev is not None:
            r = prev < 30 and now >= 30
    _turn_memo[key] = r
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

_beta_memo = {}
def beta_of(s, i, look=250, minn=150):
    key = (s, i, look)
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

def qualify(d):
    i = ci[d]; amap = assign(d); pm = pym(d)
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
        b_ok = rsi_of_rs_recovery(s, sec, i)
        if r_ok or b_ok:
            out.append((s, sec))
    return out

QUAL = {}
print("[precompute] union qualifiers...", file=sys.stderr, flush=True)
for d in rebal_all:
    QUAL[d] = qualify(d)

# ---- quality score (within-date percentile ranks; declared in the docstring) ----
def _latest_filing(s, d):
    hist = FUND.get(s)
    if not hist: return None
    latest = None
    for rd, metrics in hist:
        if rd <= d: latest = metrics
        else: break
    return latest

def quality_scores(q, d):
    """within-date percentile-mean score per symbol; missing component 0.5; no filing 0.5"""
    comp = {}
    for s, _sec in q:
        f = _latest_filing(s, d)
        if f is None:
            comp[s] = (None, None, None); continue
        opm = f.get("OPM %")
        op, it = f.get("Operating Profit"), f.get("Interest")
        cov = None
        if op is not None and it is not None:
            cov = min(op/max(it, 0.01), 20.0)
        npos = None
        np_ = f.get("Net Profit")
        if np_ is not None: npos = 1.0 if np_ > 0 else 0.0
        comp[s] = (opm, cov, npos)
    def pct_ranks(idx):
        vals = sorted((v[idx], s) for s, v in comp.items() if v[idx] is not None)
        n = len(vals)
        pr = {}
        for rank, (_val, s) in enumerate(vals):
            pr[s] = (rank + 0.5)/n if n else 0.5
        return pr
    p0, p1, p2 = pct_ranks(0), pct_ranks(1), pct_ranks(2)
    out = {}
    for s, v in comp.items():
        parts = [p0.get(s, 0.5) if v[0] is not None else 0.5,
                 p1.get(s, 0.5) if v[1] is not None else 0.5,
                 p2.get(s, 0.5) if v[2] is not None else 0.5]
        out[s] = sum(parts)/3.0
    return out

# ---- selection hooks ----
def sel_default(q, d, i, topn):
    return [s for s, _ in q]

def sel_beta_cap(mx, look=250, minn=150):
    def f(q, d, i, topn):
        return [s for s, _ in q if (beta_of(s, i, look, minn) is None or beta_of(s, i, look, minn) <= mx)]
    return f

def sel_q_rank(q, d, i, topn):
    if not FUND: return [s for s, _ in q]
    sc = quality_scores(q, d)
    return [s for s, _ in sorted(q, key=lambda t: -sc.get(t[0], 0.5))]

def sel_q_drop(q, d, i, topn):
    if not FUND: return [s for s, _ in q]
    sc = quality_scores(q, d)
    return [s for s, _ in q if sc.get(s, 0.5) >= 0.25]

def run(hook=sel_default, money="sleeve200", topn=60, trail=0.20, slip=0.01, start=None, end=None):
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac, nsel = [], [], [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = hook(QUAL[d], d, i, topn)[:topn]
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
                        q_ = sclose[s].get(cal[j])
                        if not q_: continue
                        if q_ > pk.get(s, 0): pk[s] = q_
                        if q_ <= pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit = True; break
                if hit: del held[s]; ent.pop(s, None); pk.pop(s, None)
                else: r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]
        idle = max(0.0, 1.0 - inv)
        if idle > 0 and money == "sleeve200":
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
        pk_, mx = v[0], 0.0
        for x in v: pk_ = max(pk_, x); mx = min(mx, x/pk_-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    sd = math.sqrt(sum((x-m)**2 for x in r)/(n-1))
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    alpha = (m - b*mb)*4
    return dict(cagr=navs[-1]**(1/y)-1, dd=dd(navs), mult=navs[-1], beta=b, alpha=alpha)

WIN = ((None, None, "FULL 2006-2026"),
       ("2006-01-01", "2011-12-31", "2006-2011"),
       ("2012-01-01", "2017-12-31", "2012-2017"),
       ("2018-01-01", "2026-12-31", "2018-2026"))

def battery(tag, hook, money="sleeve200"):
    print("")
    print("### %s" % tag, flush=True)
    for stt, en, wtag in WIN:
        navs, bnavs, inv, nsel, rb = run(hook=hook, money=money, start=stt, end=en)
        if len(navs) < 8:
            print("  %-14s too short" % wtag); continue
        s = stat(navs, bnavs)
        print("  %-14s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%  n %4.1f"
              % (wtag, s['cagr']*100, s['dd']*100, s['mult'], s['beta'],
                 s['alpha']*100, sum(inv)/len(inv)*100, sum(nsel)/len(nsel)), flush=True)

print("=" * 118)
print("LAB 2 — beta-cap-1.4 diagnostics + quality tilt. Candidate stays beta<=1.4/250d; sweeps test STABILITY only.")
print("=" * 118)

battery("u0_base (control repro)", sel_default)

# 1. cap-threshold plateau
for cap in (1.3, 1.5, 1.6):
    battery("diag_beta_cap_%.1f" % cap, sel_beta_cap(cap))

# 2. beta-window sensitivity at the declared cap
battery("diag_cap1.4_look125", sel_beta_cap(1.4, look=125, minn=75))
battery("diag_cap1.4_look500", sel_beta_cap(1.4, look=500, minn=300))

# 3. money-mode decomposition: does the 2012-17 fix survive with DEAD-CASH idle?
battery("decomp_base_cash (union, idle=cash)", sel_default, money="cash")
battery("decomp_cap1.4_cash (idle=cash)", sel_beta_cap(1.4), money="cash")

# 4. missing/excluded diagnostics for the declared cap
print("")
print("### missing-beta diagnostics (cap 1.4/250d)")
tot_q = tot_excl = tot_miss = 0
for d in rebal_all:
    i = ci[d]
    for s, _sec in QUAL[d]:
        b = beta_of(s, i, 250, 150)
        tot_q += 1
        if b is None: tot_miss += 1
        elif b > 1.4: tot_excl += 1
print("  qualifier-quarters %d | excluded by cap %d (%.1f%%) | kept-missing-beta %d (%.2f%%)"
      % (tot_q, tot_excl, 100.0*tot_excl/max(tot_q,1), tot_miss, 100.0*tot_miss/max(tot_q,1)), flush=True)

# 5. quality tilt (Guardrail #8 disclosed; doctrine test)
battery("q_rank_top60 (quality-ranked)", sel_q_rank)
battery("q_drop_worst25 (drop score<0.25)", sel_q_drop)

print("")
print("done.", flush=True)
