"""UNION PBO/CSCV — Probability of Backtest Overfitting via Combinatorially-Symmetric
Cross-Validation (Bailey-Borwein-LdP-Zhu 2017), on the union program's searched book configs.

S178-lane (2026-07-16/17, Ramana: "run the PBO/CSCV check as well.. keep recording"). Companion to
the sealed validation (16AL); the estate implementation `attribution.pbo_cscv` (M-03) is mirrored
here VERBATIM in stdlib (deterministic - no RNG - so equivalence is by construction; cited
attribution.py:336). Declared BEFORE the run:

MATRIX (T=81 quarters x N configs; per-period return/vol is the selection metric, D142 vocabulary):
  INCLUDED - every signal-invariant BOOK config the program searched (labs 1/2/3/4/5 S-family +
  ladder): base-floor cash0: U60, rsi_desc, rsi_asc, seccap8, seccap6, bcap12, B14, brank_asc,
  bcap13, bcap15, bcap16, cap14_look125, cap14_look500, C40 (rank+top40),
  b14_top40/30/20, trail15/25/30/none, sleeve_mid, sleeve_n100, capfloor45; pf+rf: A1;
  pf1+rf: A2, a2c_top30/25/20, rankw, K30(drift). N counted at run time and printed.
  EXCLUDED (disclosed): the 6 turn-signal variants (t25/t35/t2530/t6f/tweek/tmtf - different QUAL
  machinery, all generation-0 rejects that never entered the ladder), monthly cadence, the blend,
  the 2 quality-tilt configs (lab2-only machinery, research.db attach; both rejected), and the 4 ML
  models (different machinery/labels); stress/TR rows are re-measurements of the same configs, not
  distinct trials.

METHOD: s=8 contiguous blocks, all C(8,4)=70 IS/OOS splits; per split pick the IS-best config by
per-period return/vol, take its OOS relative rank r in [0,1], lambda = logit(r); PBO = fraction of
splits with lambda <= 0 (IS-best below the OOS median).

DECLARED INTERPRETATION BANDS (before any number): PBO < 0.10 low overfit risk; 0.10-0.50
moderate; > 0.50 severe (the IS-best config typically degrades below median OOS). Companions
reported: the IS-best tally per config, lambda quartiles, and K30's OOS mean relative rank across
splits (is the CHOSEN lead robust when it is not the IS-best picker's job to find it).

REPRODUCTION GATE: the five ladder books must reproduce their headline CAGRs to the digit first.

LEDGER PRIORS CITED (blocking until cited):
  * "wider pond" (15N): ADDING sector indices diluted the SECTOR ladder 17.2->16.6 — a different
    lever (index count, not stock-universe floor). * "raise the liquidity bar -> pond sinks MORE
    and selection collapses" (15h: +1.73%->+0.20%) — RAISING the bar hurt; A LOWERS the early-era
    bar and leaves the modern bar ~unchanged by construction. Genuinely untried.
  * 15L: the unconditioned pond loses to the index because the index self-culls — A widens only
    the pool the union's SIGNALS + beta cap + RISKADJ rank then select from; the book stays 40.
  * 16AC sleeve wall: sleeve INDEX swaps (Midcap50/N100) failed; B1 does not swap the healthy
    sleeve — it prices the CASH state per the documented rf convention. The V9 whole-book
    kill-switch wall and 16W throttle wall are untouched.
  * Cost realism: the 0.15%/side + slip model is optimistic for small names; A-variants print the
    early-era floor values and book-median ADV so the liquidity of what gets picked is visible.

PASS BARS (declared BEFORE any run):
  * A-variants + composite (CANDIDATE bar vs C40RA): full CAGR > 21.0 AND alpha > +10.3 AND
    2012-17 alpha >= +2.0 AND no window alpha more than 1.5pp below C40RA's (+9.2/+4.3/+14.3).
  * B1 (MEASUREMENT bar — it corrects a known 0%-cash mis-measurement, analogous to 16AD
    dividends): full CAGR up vs C40RA, NO window CAGR down by >0.3pp, alpha not down. It is then
    adopted into the REPORTING of any deferred lead (never into a sealed spec).
  * AUTO-COMPOSE RULE: at most ONE composite — the A-winner (A1 if it passes, else A2) + B1 if B1
    met its bar. No other combination. TR rows (16AD accrual) for the composite/winner only.

Foundation byte-copied from the cash_blend.py lineage (CA-adjusted, quarantined, PIT sector
assign, sleeve200, trail-20@1% slip, 0.15%/side, dead -50%, fixed 1/topn). c40ra + b14 controls
must reproduce 21.0%/47.29x and 18.1%/28.84x — else STOP.
"""
import sqlite3, sys, math, re
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all
import quarantine as _q

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH, SLEEVE, RFIDX = "Nifty 500", "Nifty Next 50", "Nifty 1D Rate Index"
RF_PROXY_ANN = 0.065   # attribution.py:76, the documented pre-2016 proxy
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
IDX = [BENCH, SLEEVE, RFIDX]
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
_div_re = re.compile(r"R[es]\.?\s*([0-9]+(?:\.[0-9]+)?)", re.I)
DIVS = defaultdict(list)
for s, ex, det in conn.execute("SELECT symbol, ex_date, details FROM corporate_actions WHERE action_type='DIVIDEND' AND ex_date IS NOT NULL"):
    if not det or "per share" not in det.lower():
        continue
    amts = [float(x) for x in _div_re.findall(det)]
    if amts:
        DIVS[s].append((ex, sum(amts)))
for s in DIVS: DIVS[s].sort()
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()

# ---- era-relative floor calibration (rule in docstring; printed for the record) ----
_bym = defaultdict(list)
for s, dd in adv.items():
    for ym, a in dd.items():
        _bym[ym].append(a)
months = sorted(_bym)
last12 = months[-12:]
fracs = [sum(1 for v in _bym[ym] if v >= ADV_BAR)/len(_bym[ym]) for ym in last12]
P = sum(fracs)/len(fracs)
THR, THR2 = {}, {}
for ym in months:
    vals = sorted(_bym[ym])
    k = min(int(len(vals)*(1.0-P)), len(vals)-1)
    THR[ym] = vals[k]
    THR2[ym] = max(1e7, vals[k])
print(f"[floor] P (modern eligible fraction, last 12 mo) = {P:.3f}", file=sys.stderr, flush=True)
for probe in ("2006-01", "2010-01", "2013-01", "2020-01", "2026-01"):
    if probe in THR:
        print(f"[floor] {probe}: pct-floor Rs{THR[probe]/1e7:.2f}cr (clamped Rs{THR2[probe]/1e7:.2f}cr) vs absolute Rs5cr",
              file=sys.stderr, flush=True)

FLOORS = {"base": (lambda ym: ADV_BAR), "pf": (lambda ym: THR.get(ym, ADV_BAR)),
          "pf1": (lambda ym: THR2.get(ym, ADV_BAR))}

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
def assign(d, fmode="base"):
    k = (d[:4], fmode)
    if k in _am: return _am[k]
    i = ci[d]; lo = max(0, i-CORRWIN); ym = d[:7]
    fl = FLOORS[fmode]
    out = {}
    for s in SYMS:
        if adv.get(s, {}).get(ym, 0) < fl(ym): continue
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

def rawpxn(s, d, back=10):
    i = ci.get(d)
    if i is None: return None
    cl = _raw.get(s) or {}
    for j in range(i, max(-1, i-back), -1):
        v = cl.get(cal[j])
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

def riskadj_of(s, i):
    lo6 = i - 126
    if lo6 < 1: return None
    a0, a1 = pxn(s, cal[lo6]), pxn(s, cal[i])
    if not (a0 and a1): return None
    ret6 = a1/a0 - 1.0
    rets = []
    for j in range(max(1, i-63), i+1):
        p0, p1 = sclose[s].get(cal[j-1]), sclose[s].get(cal[j])
        if p0 and p1: rets.append(p1/p0-1.0)
    if len(rets) < 30: return None
    mu = sum(rets)/len(rets)
    sd = math.sqrt(sum((x-mu)**2 for x in rets)/(len(rets)-1))
    if sd <= 0: return None
    return ret6/sd

rebal_all = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 250)
             and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]

def qualify(d, fmode):
    i = ci[d]; amap = assign(d, fmode); pm = pym(d)
    fl = FLOORS[fmode]
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < fl(pm): continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
        b_ok = rsi_of_rs_recovery(s, sec, i)
        if r_ok or b_ok:
            out.append((s, sec))
    return out

QUAL = {}
for fm in ("base", "pf", "pf1"):
    print(f"[precompute] qualifiers ({fm})...", file=sys.stderr, flush=True)
    QUAL[fm] = {d: qualify(d, fm) for d in rebal_all}

def capped(q, i, mx=1.4):
    return [s for s, _sec in q if (beta_of(s, i) is None or beta_of(s, i) <= mx)]

def sel_b14(q, d, i, topn):
    return capped(q, i)

def sel_c40ra(q, d, i, topn):
    inc = capped(q, i)
    scored = [(s, riskadj_of(s, i)) for s in inc]
    return [s for s, v in sorted(scored, key=lambda t: -(t[1] if t[1] is not None else -99))]

# ---- rf leg (estate convention: 1D Rate Index where present, else flat 6.5%/yr) ----
def _idx_near(nm, d, fwd=7):
    i = ci.get(d)
    if i is None: return None
    for j in range(i, min(N, i+fwd)):
        v = iclose[nm].get(cal[j])
        if v: return v
    return None

def rf_q(d, dn):
    a, b = _idx_near(RFIDX, d), _idx_near(RFIDX, dn)
    if a and b and a > 0:
        return b/a - 1.0
    days = max(ci[dn]-ci[d], 1)
    return (1.0+RF_PROXY_ANN)**(days/252.0) - 1.0

def run(fmode="base", hook=sel_c40ra, topn=40, trail=0.20, slip=0.01, rf_cash=False,
        tr=False, start=None, end=None):
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac, nsel, medadv = [], [], [], [], []
    ndiv = 0
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = hook(QUAL[fmode][d], d, i, topn)[:topn]
        w = {s: 1.0/topn for s in sel}
        nsel.append(len(sel))
        pm = pym(d)
        advs = sorted(adv.get(s, {}).get(pm, 0) for s in sel)
        if advs: medadv.append(advs[len(advs)//2])
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
                hit = False; hit_j = None
                if trail and ent.get(s):
                    for j in range(ci[d]+1, ci[dn]+1):
                        q_ = sclose[s].get(cal[j])
                        if not q_: continue
                        if q_ > pk.get(s, 0): pk[s] = q_
                        if q_ <= pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit = True; hit_j = j; break
                if tr and DIVS.get(s):
                    stop_j = hit_j if hit_j is not None else ci[dn]
                    ra = rawpxn(s, d)
                    if ra:
                        for ex, amt in DIVS[s]:
                            if d < ex <= cal[stop_j]:
                                r += x * amt / ra; ndiv += 1
                if hit:
                    del held[s]; ent.pop(s, None); pk.pop(s, None)
                else:
                    r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]
        idle = max(0.0, 1.0 - inv)
        if idle > 0:
            healthy = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if healthy:
                a, b = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
                if a and b: r += idle*(b/a-1.0)
            elif rf_cash:
                r += idle*(gsec_q(d, dn) if bear_mode == "gsec" else rf_q(d, dn))
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return dict(navs=navs, bnavs=bnavs, inv=invfrac, nsel=nsel, medadv=medadv, ndiv=ndiv)

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

def battery(tag, **kw):
    print("")
    print("### %s" % tag, flush=True)
    rows = {}
    for stt, en, wtag in WIN:
        o = run(start=stt, end=en, **kw)
        if len(o["navs"]) < 8:
            print("  %-14s too short" % wtag); continue
        s = stat(o["navs"], o["bnavs"])
        rows[wtag] = s
        extra = ("  div %d" % o["ndiv"]) if kw.get("tr") else ""
        madv = sorted(o["medadv"])[len(o["medadv"])//2]/1e7 if o["medadv"] else 0
        print("  %-14s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%  n %4.1f  medADV %5.1fcr%s"
              % (wtag, s['cagr']*100, s['dd']*100, s['mult'], s['beta'], s['alpha']*100,
                 sum(o["inv"])/len(o["inv"])*100, sum(o["nsel"])/len(o["nsel"]), madv, extra), flush=True)
    return rows


def sel_a2c(q, d, i, topn):
    inc = capped(q, i)
    scored = [(s, riskadj_of(s, i)) for s in inc]
    return [s for s, v in sorted(scored, key=lambda t: -(t[1] if t[1] is not None else -99))]

def run5(fmode="pf1", topn=40, trail=0.20, slip=0.01, rf_cash=True, tr=False,
         weights="ew", cap=0.05, start=None, end=None, lagged=False, bear_mode="rf", hook=None,
         dead=DEAD_VAL, sleeve=SLEEVE):
    """weights: ew | drift (winners keep drifted weight, capped) | rankw (linear 2:1)."""
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac, nsel = [], [], [], []
    ndiv = 0; ndead = 0
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]; i1 = ci[dn]
        if lagged:
            e0d, e1d = cal[min(i+1, N-1)], cal[min(i1+1, N-1)]
            stop_lo, stop_hi = min(i+2, N-1), min(i1+2, N-1)
        else:
            e0d, e1d = d, dn
            stop_lo, stop_hi = i+1, i1
        sel = (hook or sel_a2c)(QUAL[fmode][d], d, i, topn)[:topn]
        if weights == "ew":
            w = {s: 1.0/topn for s in sel}
        elif weights == "rankw":
            n_ = len(sel)
            if n_ == 0:
                w = {}
            else:
                tot_exp = n_/float(topn)
                ranksum = n_*(n_+1)/2.0
                w = {s: tot_exp*(n_-pos)/ranksum for pos, s in enumerate(sel)}
        else:  # drift
            w = {}
            budget = 1.0
            for s in sel:
                if s in held:
                    w[s] = min(held[s], cap)
            used = sum(w.values())
            slot = 1.0/topn
            for s in [s for s in sel if s not in held]:
                take = min(slot, max(0.0, budget-used))
                if take <= 1e-9: break
                w[s] = take; used += take
        nsel.append(len(sel))
        turn = sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))
        nav *= (1-COST*turn)
        for s in w:
            if s not in held:
                p = pxn(s, e0d); ent[s] = p; pk[s] = p or 0
        held = dict(w)
        inv = sum(held.values()); invfrac.append(inv)
        r = 0.0
        growth = {}
        for s, x in list(held.items()):
            a, b = pxn(s, e0d), pxn(s, e1d)
            if a and b:
                hit = False; hit_j = None
                if trail and ent.get(s):
                    for j in range(stop_lo, stop_hi+1):
                        q_ = sclose[s].get(cal[j])
                        if not q_: continue
                        if q_ > pk.get(s, 0): pk[s] = q_
                        if q_ <= pk[s]*(1-trail):
                            r += x*((pk[s]*(1-trail)*(1-slip))/a-1.0); hit = True; hit_j = j; break
                if tr and DIVS.get(s):
                    stop_j = hit_j if hit_j is not None else min(i1+(1 if lagged else 0), N-1)
                    ra = rawpxn(s, e0d)
                    if ra:
                        for ex, amt in DIVS[s]:
                            if e0d < ex <= cal[stop_j]:
                                r += x * amt / ra; ndiv += 1
                if hit:
                    del held[s]; ent.pop(s, None); pk.pop(s, None)
                else:
                    r += x*(b/a-1.0); growth[s] = b/a
            elif a and isdead(s, e1d):
                r += x*dead; ndead += 1; del held[s]
        idle = max(0.0, 1.0 - inv)
        if idle > 0:
            healthy = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if healthy:
                a2_, b2_ = iclose[sleeve].get(d), iclose[sleeve].get(dn)
                if a2_ and b2_: r += idle*(b2_/a2_-1.0)
            elif rf_cash:
                r += idle*rf_q(d, dn)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
        if weights == "drift" and (1.0+r) > 0:
            held = {s: x*growth.get(s, 1.0)/(1.0+r) for s, x in held.items()}
    return dict(navs=navs, bnavs=bnavs, inv=invfrac, nsel=nsel, ndiv=ndiv, ndead=ndead)

def battery5(tag, **kw):
    print("")
    print("### %s" % tag, flush=True)
    rows = {}
    for stt, en, wtag in WIN:
        o = run5(start=stt, end=en, **kw)
        if len(o["navs"]) < 8:
            print("  %-14s too short" % wtag); continue
        s = stat(o["navs"], o["bnavs"])
        rows[wtag] = s
        extra = ("  div %d" % o["ndiv"]) if kw.get("tr") else ""
        print("  %-14s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%  n %4.1f%s"
              % (wtag, s["cagr"]*100, s["dd"]*100, s["mult"], s["beta"], s["alpha"]*100,
                 sum(o["inv"])/len(o["inv"])*100, sum(o["nsel"])/len(o["nsel"]), extra), flush=True)
    return rows


# ---- CSV series (fetched by niftyindices_hist.py; research-side files) ----
import csv as _csv, os as _os
DATA = "/opt/hermes/research/data/niftyindices"
def load_csv(fn, col=1):
    p = _os.path.join(DATA, fn)
    out = {}
    if not _os.path.exists(p):
        print(f"[csv] MISSING {p}", file=sys.stderr, flush=True)
        return out
    with open(p) as f:
        rd = _csv.reader(f); next(rd, None)
        for row in rd:
            try: out[row[0]] = float(row[col])
            except (ValueError, IndexError): pass
    return out

TRI500 = load_csv("nifty500_tr.csv")
TRIN50 = load_csv("niftynext50_tr.csv")
GSEC = load_csv("gs10yr.csv")   # 2011+ (longest G-sec history); composite only starts 2018
if not GSEC: GSEC = load_csv("gscomposite.csv")
print(f"[csv] TRI500 {len(TRI500)} rows | TRIN50 {len(TRIN50)} | GSEC {len(GSEC)} "
      f"({min(GSEC) if GSEC else '-'}..)", file=sys.stderr, flush=True)

def series_near(sd, d, back=7):
    i = ci.get(d)
    if i is None: return None
    for j in range(i, max(-1, i-back), -1):
        v = sd.get(cal[j])
        if v: return v
    return None

def gsec_q(d, dn):
    a, b = series_near(GSEC, d), series_near(GSEC, dn)
    if a and b and a > 0:
        return b/a - 1.0
    return rf_q(d, dn)   # rf fallback before the G-sec base date (disclosed)

def stat_vs(navs, rb, bench_series):
    """stat() but benchmark = an external series dict (TRI)"""
    # ALIGNMENT: r[i] = navs[i]/navs[i-1] covers legs 1..N-1 (leg 0 has no prior nav) —
    # the bench series must skip leg 0 the same way, or beta collapses to ~0 (caught 16AJ).
    br = []
    for k in range(1, len(rb)-1):
        a, b = series_near(bench_series, rb[k]), series_near(bench_series, rb[k+1])
        br.append(b/a-1.0 if (a and b) else 0.0)
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    n = min(len(r), len(br)); r, br = r[:n], br[:n]
    y = n/4.0
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b_ = cov/vb if vb else 0.0
    return dict(beta=b_, alpha=(m - b_*mb)*4, bench_cagr=(1+mb)**4-1 if n else 0.0)

def bench_cagr_series(sd, rb):
    a, b = series_near(sd, rb[0]), series_near(sd, rb[-1])
    if not (a and b): return None
    return (b/a)**(1/((len(rb)-1)/4.0))-1

def sel_union6(q, d, i, topn):
    return [s for s, _sec in QUAL_PAIRS[("base", d)]] if False else [s for s in q]

# hooks over the capless qualifier lists (QUAL[fmode][d] = [(s, sec)]) — lab4-head shape
def hook_union(q, d, i, topn):
    return [s for s, _sec in q]
def hook_b14(q, d, i, topn):
    return capped(q, i)
def hook_c40ra(q, d, i, topn):
    return sel_a2c(q, d, i, topn)

WINS = ((None, None, "FULL"), ("2006-01-01", "2011-12-31", "06-11"),
        ("2012-01-01", "2017-12-31", "12-17"), ("2018-01-01", "2026-12-31", "18-26"))

def row6(tag, **kw):
    print("")
    print("### %s" % tag, flush=True)
    for stt, en, wtag in WINS:
        o = run5(start=stt, end=en, **kw)
        if len(o["navs"]) < 8:
            print("  %-6s too short" % wtag); continue
        rb = [d for d in rebal_all if (stt is None or d >= stt) and (en is None or d <= en)]
        s = stat(o["navs"], o["bnavs"])
        st = stat_vs(o["navs"], rb, TRI500) if TRI500 else {"beta": 0, "alpha": 0}
        n50tri = bench_cagr_series(TRIN50, rb) if TRIN50 else None
        extra = ("  div %d" % o["ndiv"]) if kw.get("tr") else ""
        print("  %-6s CAGR %5.1f%%  [bar: N50-PR %5.1f%% | N50-TRI %5.1f%%]  aPR %+5.1f/bPR %4.2f  aTRI %+5.1f/bTRI %4.2f  inv %3.0f%%%s"
              % (wtag, s["cagr"]*100, (bench_cagr_series(iclose[SLEEVE], rb) or 0)*100, (n50tri or 0)*100,
                 s["alpha"]*100, s["beta"], st["alpha"]*100, st["beta"],
                 sum(o["inv"])/len(o["inv"])*100, extra), flush=True)


import random

# ================= stats primitives (15i machinery, quarterly annualization) =================
def retvol_q(x):
    m = sum(x)/len(x)
    sd = math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
    return m/sd if sd else 0.0

def corr2(a, b):
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))
    den = math.sqrt(sum((v-ma)**2 for v in a)*sum((v-mb)**2 for v in b))
    return num/den if den else 0.0

def norm_cdf(z):
    return 0.5*(1+math.erf(z/math.sqrt(2)))

def cagr_of(rets):
    nav = 1.0
    for r in rets: nav *= (1+r)
    y = len(rets)/4.0
    return nav**(1/y)-1 if y > 0 and nav > 0 else float("nan")

def nw_t(d, lag=4):
    n = len(d); m = sum(d)/n
    e = [x-m for x in d]
    g0 = sum(v*v for v in e)/n
    var = g0
    for l in range(1, lag+1):
        gl = sum(e[i]*e[i-l] for i in range(l, n))/n
        var += 2*(1-l/(lag+1))*gl
    se = math.sqrt(var/n)
    return m/se if se else float("nan")

def jk_z(a, b):
    s1, s2, rho = retvol_q(a), retvol_q(b), corr2(a, b)
    th = (1.0/len(a))*(2*(1-rho) + 0.5*(s1**2 + s2**2 - 2*s1*s2*rho**2))
    return (s1-s2)/math.sqrt(th) if th > 0 else float("nan")

def paired_boot_cagr(a, b, draws=10000, mean_block=4, seed=42):
    """joint stationary bootstrap; returns (obs_gap, sorted gap draws)"""
    rng = random.Random(seed)
    n = len(a); p = 1.0/mean_block
    obs = cagr_of(b) - cagr_of(a)
    gaps = []
    for _ in range(draws):
        ia, ib = [], []
        while len(ia) < n:
            i = rng.randrange(n)
            while True:
                ia.append(a[i]); ib.append(b[i])
                if len(ia) >= n or rng.random() < p:
                    break
                i = (i+1) % n
        gaps.append(cagr_of(ib) - cagr_of(ia))
    gaps.sort()
    return obs, gaps

def qtile(xs, p):
    return xs[min(len(xs)-1, max(0, int(p*len(xs))))]

def deflated_rv(rets, n_trials):
    """Bailey-LdP deflated return/vol (attribution.py:314 formula), quarterly units."""
    r = [x for x in rets if x == x]
    T = len(r)
    m = sum(r)/T
    sd = math.sqrt(sum((v-m)**2 for v in r)/(T-1))
    sr = m/sd if sd else 0.0
    mu3 = sum((v-m)**3 for v in r)/T
    mu4 = sum((v-m)**4 for v in r)/T
    g3 = mu3/sd**3 if sd else 0.0
    g4 = mu4/sd**4 if sd else 3.0
    emc = 0.5772156649
    import statistics
    from math import e as _e
    def ppf(q):
        lo, hi = -8.0, 8.0
        for _ in range(80):
            mid = (lo+hi)/2
            if norm_cdf(mid) < q: lo = mid
            else: hi = mid
        return (lo+hi)/2
    z1, z2 = ppf(1-1.0/n_trials), ppf(1-1.0/(n_trials*_e))
    sr0 = (1-emc)*z1 + emc*z2
    var_sr = (1 - g3*sr + (g4-1)/4.0*sr**2)/(T-1)
    sr_std = math.sqrt(max(var_sr, 1e-12))
    sr0_scaled = sr0*sr_std
    dsr = norm_cdf((sr - sr0_scaled)/sr_std)
    phi = (sr - sr0_scaled)/sr if sr > 0 else 0.0
    return dsr, phi, sr*2.0, sr0_scaled*2.0   # x2 = sqrt(4) annualization for display

# ================= the five books (as-sealed configs) =================
BOOKS = {
    "U":   dict(fmode="base", topn=60, rf_cash=False, hook=hook_union),
    "B14": dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14),
    "C40": dict(fmode="base", topn=40, rf_cash=False),
    "A2":  dict(fmode="pf1",  topn=40, rf_cash=True),
    "K30": dict(fmode="pf1",  topn=30, rf_cash=True, weights="drift"),
}
GATE = {"U": (17.5, 26.04), "B14": (18.1, 28.84), "C40": (21.0, 47.29),
        "A2": (25.5, 99.03), "K30": (26.4, 115.69)}


from itertools import combinations

def retvol_q2(x):
    xs = [v for v in x if v == v]
    if len(xs) < 3: return float("nan")
    m = sum(xs)/len(xs)
    sd = math.sqrt(sum((v-m)**2 for v in xs)/(len(xs)-1))
    return m/sd if sd > 0 else float("nan")

# ---- ported selection hooks (lab1/lab3 shapes, over (s,sec) qualifier pairs) ----
def sel_rsi_desc(q, d, i, topn):
    return [s for s, _ in sorted(q, key=lambda t: -(RSI[t[0]][i] if RSI[t[0]][i] is not None else -1))]
def sel_rsi_asc(q, d, i, topn):
    return [s for s, _ in sorted(q, key=lambda t: (RSI[t[0]][i] if RSI[t[0]][i] is not None else 999))]
def sel_seccap(cap):
    def f(q, d, i, topn):
        cnt, out = {}, []
        for s, sec in q:
            if cnt.get(sec, 0) >= cap: continue
            cnt[sec] = cnt.get(sec, 0) + 1; out.append(s)
            if len(out) >= topn: break
        return out
    return f
def sel_beta_rank_asc(q, d, i, topn):
    scored = [(s, beta_of(s, i)) for s, _ in q]
    return [s for s, b in sorted(scored, key=lambda t: (t[1] if t[1] is not None else 9.9))]
def sel_capfloor(minbook):
    def f(q, d, i, topn):
        inc, exc = [], []
        for s, _sec in q:
            b = beta_of(s, i)
            (inc if (b is None or b <= 1.4) else exc).append(s)
        if len(inc) < minbook and exc:
            inc = inc + sorted(exc, key=lambda s: beta_of(s, i) or 9.9)[:minbook-len(inc)]
        return inc
    return f
def sel_bcap(mx, look=250, minn=150):
    def f(q, d, i, topn):
        return [s for s, _ in q if (beta_of(s, i, look, minn) is None or beta_of(s, i, look, minn) <= mx)]
    return f

CONFIGS = [
    ("U60",          dict(fmode="base", topn=60, rf_cash=False, hook=hook_union)),
    ("rsi_desc",     dict(fmode="base", topn=60, rf_cash=False, hook=sel_rsi_desc)),
    ("rsi_asc",      dict(fmode="base", topn=60, rf_cash=False, hook=sel_rsi_asc)),
    ("seccap8",      dict(fmode="base", topn=60, rf_cash=False, hook=sel_seccap(8))),
    ("seccap6",      dict(fmode="base", topn=60, rf_cash=False, hook=sel_seccap(6))),
    ("bcap12",       dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.2))),
    ("B14",          dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14)),
    ("brank_asc",    dict(fmode="base", topn=60, rf_cash=False, hook=sel_beta_rank_asc)),
    ("bcap13",       dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.3))),
    ("bcap15",       dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.5))),
    ("bcap16",       dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.6))),
    ("cap14_l125",   dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.4, 125, 75))),
    ("cap14_l500",   dict(fmode="base", topn=60, rf_cash=False, hook=sel_bcap(1.4, 500, 300))),
    ("C40",          dict(fmode="base", topn=40, rf_cash=False)),
    ("b14_top40",    dict(fmode="base", topn=40, rf_cash=False, hook=hook_b14)),
    ("b14_top30",    dict(fmode="base", topn=30, rf_cash=False, hook=hook_b14)),
    ("b14_top20",    dict(fmode="base", topn=20, rf_cash=False, hook=hook_b14)),
    ("trail15",      dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, trail=0.15)),
    ("trail25",      dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, trail=0.25)),
    ("trail30",      dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, trail=0.30)),
    ("trail_none",   dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, trail=0.0)),
    ("sleeve_mid",   dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, sleeve="Nifty Midcap 50")),
    ("sleeve_n100",  dict(fmode="base", topn=60, rf_cash=False, hook=hook_b14, sleeve="Nifty 100")),
    ("capfloor45",   dict(fmode="base", topn=60, rf_cash=False, hook=sel_capfloor(45))),
    ("A1",           dict(fmode="pf",   topn=40, rf_cash=True)),
    ("A2",           dict(fmode="pf1",  topn=40, rf_cash=True)),
    ("a2c_top30",    dict(fmode="pf1",  topn=30, rf_cash=True)),
    ("a2c_top25",    dict(fmode="pf1",  topn=25, rf_cash=True)),
    ("a2c_top20",    dict(fmode="pf1",  topn=20, rf_cash=True)),
    ("rankw",        dict(fmode="pf1",  topn=40, rf_cash=True, weights="rankw")),
    ("K30",          dict(fmode="pf1",  topn=30, rf_cash=True, weights="drift")),
]

print("=" * 118)
print("UNION PBO/CSCV — matrix + bands declared in the docstring; attribution.py:336 logic mirrored (deterministic).")
print("=" * 118)

GATE = {"U60": (17.5, 26.04), "B14": (18.1, 28.84), "C40": (21.0, 47.29),
        "A2": (25.5, 99.03), "K30": (26.4, 115.69)}
SERIES, names = {}, []
for name, cfg in CONFIGS:
    o = run5(**cfg)
    navs = o["navs"]
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    SERIES[name] = r; names.append(name)
    if name in GATE:
        s = stat(navs, o["bnavs"])
        g_c, g_m = GATE[name]
        ok = abs(s["cagr"]*100 - g_c) < 0.05 and abs(s["mult"] - g_m) < 0.05
        print("  repro %-4s CAGR %5.1f%% (gate %.1f) %s" % (name, s["cagr"]*100, g_c, "OK" if ok else "FAIL"), flush=True)
        if not ok:
            print("REPRODUCTION GATE FAILED — STOP"); sys.exit(1)
T = min(len(v) for v in SERIES.values())
N = len(names)
assert all(len(v) == T for v in SERIES.values()), "grid mismatch"
print("  matrix: T=%d quarters x N=%d configs" % (T, N), flush=True)

# ---- CSCV (attribution.py:336 verbatim logic, stdlib) ----
S_BLOCKS = 8
idx_blocks = []
base_len, rem = divmod(T, S_BLOCKS)
start = 0
for b in range(S_BLOCKS):
    ln = base_len + (1 if b < rem else 0)
    idx_blocks.append(list(range(start, start+ln)))
    start += ln
half = S_BLOCKS // 2
logits, best_tally, k30_ranks = [], {}, []
for combo in combinations(range(S_BLOCKS), half):
    is_rows = [i for b in combo for i in idx_blocks[b]]
    oos_rows = [i for b in range(S_BLOCKS) if b not in combo for i in idx_blocks[b]]
    is_sr = [retvol_q2([SERIES[n][i] for i in is_rows]) for n in names]
    oos_sr = [retvol_q2([SERIES[n][i] for i in oos_rows]) for n in names]
    best = max(range(N), key=lambda k: (is_sr[k] if is_sr[k] == is_sr[k] else -9e9))
    best_tally[names[best]] = best_tally.get(names[best], 0) + 1
    rank = sum(1 for v in oos_sr if v == v and v < oos_sr[best]) / (N - 1)
    w = max(min(rank, 1 - 1e-6), 1e-6)
    logits.append(math.log(w / (1 - w)))
    k30_oos = oos_sr[names.index("K30")]
    k30_ranks.append(sum(1 for v in oos_sr if v == v and v < k30_oos) / (N - 1))
logits.sort()
pbo = sum(1 for l in logits if l <= 0) / len(logits)
print("")
print("### PBO/CSCV result (s=%d, %d splits)" % (S_BLOCKS, len(logits)))
print("  PBO = %.3f   (declared bands: <0.10 low | 0.10-0.50 moderate | >0.50 severe)" % pbo)
print("  lambda quartiles: Q1 %+.2f | median %+.2f | Q3 %+.2f"
      % (logits[len(logits)//4], logits[len(logits)//2], logits[3*len(logits)//4]))
print("  IS-best tally: %s" % ", ".join(f"{k}:{v}" for k, v in sorted(best_tally.items(), key=lambda t: -t[1])))
print("  K30 OOS relative rank across splits: mean %.3f | min %.3f  (1.0 = best of the %d)"
      % (sum(k30_ranks)/len(k30_ranks), min(k30_ranks), N))
band = "LOW overfit risk" if pbo < 0.10 else ("MODERATE" if pbo <= 0.50 else "SEVERE")
print("  VERDICT (declared bands): %s" % band)
print("")
print("done.", flush=True)
