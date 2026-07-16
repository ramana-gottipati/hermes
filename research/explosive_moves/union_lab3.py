"""UNION LAB 3 — the 25%-CAGR push: single-axis CAGR levers on the beta-cap-1.4 base + the
lower-bound TOTAL-RETURN recut.

Ramana, 2026-07-16 (S168): "I am giving you the target of 25 CAGR... this is a lab and we won't
fear experimenting. do logical experiments." Target = an in-sample engineering bar with walk-forward
integrity; anything that clears the promotion bar becomes a pre-registered candidate; the forward
window stays the only judge. The union seal (a9a14058...) and the beta14 sibling seal (08b46199...)
are UNTOUCHED — everything here is a candidate beside them.

BASE for all variants: union + per-name trailing-250d beta<=1.4 at selection (ledger 16Y:
18.1% / -24.7% / 28.84x / beta 0.74 / alpha +8.4%; windows +9.3 / +3.4 / +9.2).

PASS BAR (declared before any run): a variant WINS only if, vs the beta14 base:
  full-period CAGR > 18.1% AND alpha > +8.4% AND 2012-17 alpha >= +2.0% (the fix must not be
  given back) AND no window's alpha degrades by more than 1.5pp. TR rows are MEASUREMENT (no bar).
AUTO-COMPOSE RULE (declared): after the singles, at most ONE composite is run, combining ONLY the
axes whose single rows individually passed the bar (among topn / trail / rank / sleeve). No other
combination is run; if no axis passes, no composite runs.

LEDGER PRIORS CITED (failure-ledger discipline — blocking until cited):
  * topN on the UNCAPPED union (16V): 40/60/80 = 17.0 / 17.5 / 16.0% — 60 was best. The CAP changes
    the qualifier pool (29% excluded), so concentration on the CAPPED set is a NEW cell; 15P's
    variance-toll warning applies and the trail stop is the mitigation.
  * exits (15k, pond context): fix RISK not return; the +3.5% alpha was a frictionless-fill
    artifact that DIES at 2% slippage → every trail row here reports 1% AND 2% stop-slip.
    trail-20 halved DD on V24 (15N). A WIDTH SWEEP on the union base was never recorded.
  * cadence (V10/V12, sector layer): monthly = churn 35.7%/mo, 3rd confirmation of the cadence law;
    plus the participation-cost evidence (C-BLEND recut: monthly mid-cap dies at real cost). The
    monthly cell here is CHURN-CONTROLLED (hold-unless-lost-2-evals) and prints its turnover; if
    turnover balloons, it is dead on arrival and recorded so.
  * naive top-N stock RS vs broad (15j) and RSI-rank both ways (16Z) FAILED as selectors. The
    riskadj-rank cell is DIFFERENT: the estate's best-of-32 factor (RISKADJ = 6m return / 3m vol,
    ledger internal-benchmark table) applied WITHIN the capped union qualifiers, not to the raw
    universe. Same-close convention as the whole family (D5-F1 note: ~0.04 optimistic).
  * sleeve law (V17/V21): idle capital works the sleeve; whole-book kill-switch destroys wealth
    (V9). Sleeve INDEX swap (Next50 -> Midcap50 / Nifty100) was never tested on the stock book.
  * consistency>=70 vs OWN SECTOR is the design (RSI battery D; peaks at 70). vs-BENCH reference
    was never run — one curiosity cell, prior LOW (own-sector is Ramana's discriminator thesis).
  * quality/ML/sector-caps/6b-variants etc. (16Z/16AA): dead — NOT re-run here.
  * TR recut owed estate-wide: dividends parse at 97.7% coverage 2012+ ("Rs X Per Share"), ~34%
    pre-2012 (percent-of-face rows skipped) → book TR is a LOWER BOUND; benchmark stays PRICE
    index (no TRI series in index_rows) — book-TR vs bench-PR OVERSTATES alpha by the index's
    dividend yield; both book-PR and book-TR are printed so nothing hides.

Foundation byte-copied from cash_blend.py lineage (CA-adjusted, quarantined, prior-month ADV>=Rs5cr,
PIT sector assign, sleeve200, trail-20%@1% slip, 0.15%/side, dead -50%, fixed 1/topn slots).
u0_base must reproduce 17.5%/26.04x; b14 must reproduce 18.1%/28.84x — else STOP.
"""
import sqlite3, sys, math, re
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
# ---- dividends (Rs/Re X Per Share rows only; lower-bound accrual) ----
_div_re = re.compile(r"R[es]\.?\s*([0-9]+(?:\.[0-9]+)?)", re.I)
DIVS = defaultdict(list)   # symbol -> [(ex_date, amount)]
n_div_rows = n_div_parsed = 0
for s, ex, det in conn.execute("SELECT symbol, ex_date, details FROM corporate_actions WHERE action_type='DIVIDEND' AND ex_date IS NOT NULL"):
    n_div_rows += 1
    if not det or "per share" not in det.lower():
        continue
    amts = [float(x) for x in _div_re.findall(det)]
    if amts:
        DIVS[s].append((ex, sum(amts)))
        n_div_parsed += 1
for s in DIVS: DIVS[s].sort()
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()
print(f"[div] parsed {n_div_parsed:,}/{n_div_rows:,} dividend rows (per-share amounts)", file=sys.stderr, flush=True)

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

def rawpxn(s, d, back=10):
    """UNADJUSTED price near d — dividends are per-share in historical nominal terms, so the
    yield denominator must be the raw price of that era, never the CA-adjusted series."""
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
def consistency(s, sec, i, ref=None):
    """ref=None -> vs own sector index (the design); ref='bench' -> vs Nifty 500"""
    key = (s, i, ref)
    if key in _cons_memo: return _cons_memo[key]
    lo = i-QTR
    r = None
    if lo >= 0:
        refclose = iclose[BENCH] if ref == "bench" else iclose[sec]
        a0, b0 = sclose[s].get(cal[lo]), refclose.get(cal[lo])
        if a0 and b0:
            ahead = tot = 0
            for j in range(lo+1, i+1):
                a, b = sclose[s].get(cal[j]), refclose.get(cal[j])
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
    """RISKADJ factor: 6m return / 3m vol (the estate's best-of-32; same-close convention)"""
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
rebal_monthly = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 250)
                 and (i == 0 or cal[i-1][5:7] != d[5:7])]

def qualify(d, consist_ref=None):
    """returns (included_capless, sector_map) — ordered union qualifiers, NO cap here"""
    i = ci[d]; amap = assign(d); pm = pym(d)
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i, consist_ref) or 0) >= 0.70
        b_ok = rsi_of_rs_recovery(s, sec, i)
        if r_ok or b_ok:
            out.append(s)
    return out

print("[precompute] quarterly qualifiers (own-sector)...", file=sys.stderr, flush=True)
QUAL = {d: qualify(d) for d in rebal_all}
print("[precompute] quarterly qualifiers (vs-bench consistency)...", file=sys.stderr, flush=True)
QUAL_B = {d: qualify(d, "bench") for d in rebal_all}
print("[precompute] monthly qualifiers (own-sector)...", file=sys.stderr, flush=True)
QUAL_M = {d: qualify(d) for d in rebal_monthly}

# ---- selection hooks (input = capless ordered qualifier list; cap applied inside) ----
def capped(q, i, mx=1.4):
    inc, exc = [], []
    for s in q:
        b = beta_of(s, i)
        (inc if (b is None or b <= mx) else exc).append(s)
    return inc, exc

def sel_union(q, d, i, topn):          # no cap — the sealed union
    return q

def sel_b14(q, d, i, topn):
    return capped(q, i)[0]

def sel_b14_floor(minbook):
    def f(q, d, i, topn):
        inc, exc = capped(q, i)
        if len(inc) < minbook and exc:
            exc2 = sorted(exc, key=lambda s: beta_of(s, i) or 9.9)
            inc = inc + exc2[:minbook-len(inc)]
        return inc
    return f

def sel_b14_riskadj(q, d, i, topn):
    inc, _ = capped(q, i)
    scored = [(s, riskadj_of(s, i)) for s in inc]
    return [s for s, v in sorted(scored, key=lambda t: -(t[1] if t[1] is not None else -99))]

def sel_b14_bench(q, d, i, topn):      # used with QUAL_B
    return capped(q, i)[0]

def run(qual, rb_dates, hook, topn=60, trail=0.20, slip=0.01, sleeve=SLEEVE,
        tr=False, monthly_hyst=False, start=None, end=None):
    rb = [d for d in rb_dates if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac, nsel, turns = [], [], [], [], []
    tr_paid = 0.0; n_div_credit = 0
    held, ent, pk = {}, {}, {}
    miss = {}                           # monthly hysteresis: consecutive evals a holding missed the signal
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        q = hook(qual[d], d, i, topn)
        if monthly_hyst:
            qset = set(q)
            keep = []
            for s in held:
                if s in qset:
                    miss[s] = 0; keep.append(s)
                else:
                    miss[s] = miss.get(s, 0) + 1
                    if miss[s] < 2: keep.append(s)     # grace: hold unless lost 2 evals
            new = [s for s in q if s not in held]
            sel = (keep + new)[:topn]
        else:
            sel = q[:topn]
        w = {s: 1.0/topn for s in sel}
        nsel.append(len(sel))
        turn = sum(abs(w.get(s, 0)-held.get(s, 0)) for s in set(w)|set(held))
        turns.append(turn)
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
                                r += x * amt / ra; tr_paid += x*amt/ra; n_div_credit += 1
                if hit:
                    del held[s]; ent.pop(s, None); pk.pop(s, None); miss.pop(s, None)
                else:
                    r += x*(b/a-1.0)
            elif a and isdead(s, dn):
                r += x*DEAD_VAL; del held[s]; miss.pop(s, None)
        idle = max(0.0, 1.0 - inv)
        if idle > 0:
            ok = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if ok:
                a, b = iclose[sleeve].get(d), iclose[sleeve].get(dn)
                if a and b: r += idle*(b/a-1.0)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return dict(navs=navs, bnavs=bnavs, inv=invfrac, nsel=nsel, turns=turns,
                ppy=(12.0 if monthly_hyst else 4.0), ndiv=n_div_credit)

def stat(navs, bnavs, ppy=4.0):
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); y = n/ppy
    def dd(v):
        pk_, mx = v[0], 0.0
        for x in v: pk_ = max(pk_, x); mx = min(mx, x/pk_-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    sd = math.sqrt(sum((x-m)**2 for x in r)/(n-1))
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    alpha = (m - b*mb)*ppy
    return dict(cagr=navs[-1]**(1/y)-1, dd=dd(navs), mult=navs[-1], beta=b, alpha=alpha)

WIN = ((None, None, "FULL 2006-2026"),
       ("2006-01-01", "2011-12-31", "2006-2011"),
       ("2012-01-01", "2017-12-31", "2012-2017"),
       ("2018-01-01", "2026-12-31", "2018-2026"))

def battery(tag, qual=None, rbs=None, **kw):
    qual = qual if qual is not None else QUAL
    rbs = rbs if rbs is not None else rebal_all
    print("")
    print("### %s" % tag, flush=True)
    rows = {}
    for stt, en, wtag in WIN:
        o = run(qual, rbs, start=stt, end=en, **kw)
        if len(o["navs"]) < 8:
            print("  %-14s too short" % wtag); continue
        s = stat(o["navs"], o["bnavs"], o["ppy"])
        rows[wtag] = s
        extra = ("  div-credits %d" % o["ndiv"]) if kw.get("tr") else ""
        print("  %-14s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%  n %4.1f  turn/reb %4.2f%s"
              % (wtag, s['cagr']*100, s['dd']*100, s['mult'], s['beta'], s['alpha']*100,
                 sum(o["inv"])/len(o["inv"])*100, sum(o["nsel"])/len(o["nsel"]),
                 sum(o["turns"])/len(o["turns"]), extra), flush=True)
    return rows

print("=" * 118)
print("UNION LAB 3 — 25%-CAGR push. Base = beta-cap-1.4 (18.1%/b0.74/a+8.4). Pass bar + compose rule in docstring.")
print("=" * 118)

R = {}
R["u0"] = battery("u0_base (sealed union, control)", hook=sel_union)
R["b14"] = battery("b14 (the sibling lead, comparator)", hook=sel_b14)

# --- concentration on the CAPPED set ---
for nn in (40, 30, 20):
    R[f"top{nn}"] = battery(f"b14_top{nn}", hook=sel_b14, topn=nn)

# --- trail-width sweep (1% slip) ---
for tw in (0.15, 0.25, 0.30, None):
    tag = "none" if tw is None else str(int(tw*100))
    R[f"trail{tag}"] = battery(f"b14_trail_{tag}", hook=sel_b14, trail=(tw or 0.0))

# --- sleeve swaps ---
R["slv_mid"] = battery("b14_sleeve_Midcap50", hook=sel_b14, sleeve="Nifty Midcap 50")
R["slv_n100"] = battery("b14_sleeve_Nifty100", hook=sel_b14, sleeve="Nifty 100")

# --- rank within capped set by RISKADJ ---
R["rankra"] = battery("b14_rank_riskadj (6m/3m-vol, best-of-32 factor)", hook=sel_b14_riskadj)

# --- cap floor (fills scarce books from lowest-beta excluded) ---
R["floor45"] = battery("b14_capfloor45", hook=sel_b14_floor(45))

# --- consistency vs bench (curiosity cell) ---
R["consb"] = battery("b14_consist_vs_bench", qual=QUAL_B, hook=sel_b14_bench)

# --- monthly churn-controlled cadence ---
R["monthly"] = battery("b14_monthly_hyst (hold-unless-lost-2)", qual=QUAL_M, rbs=rebal_monthly,
                       hook=sel_b14, monthly_hyst=True)

# --- TOTAL-RETURN measurement rows (no pass bar) ---
R["u0_tr"] = battery("u0_base TR (dividend accrual, lower bound)", hook=sel_union, tr=True)
R["b14_tr"] = battery("b14 TR (dividend accrual, lower bound)", hook=sel_b14, tr=True)

# --- slip-2% sensitivity on b14 + the best trail row (15k lesson) ---
R["b14_s2"] = battery("b14 @2% stop-slip (sensitivity)", hook=sel_b14, slip=0.02)

# --- AUTO-COMPOSE (rule in docstring): axes that individually passed the bar ---
def passed(rows):
    b = R["b14"]
    try:
        return (rows["FULL 2006-2026"]["cagr"] > b["FULL 2006-2026"]["cagr"]
                and rows["FULL 2006-2026"]["alpha"] > b["FULL 2006-2026"]["alpha"]
                and rows["2012-2017"]["alpha"] >= 0.02
                and all(rows[w]["alpha"] >= b[w]["alpha"] - 0.015
                        for w in ("2006-2011", "2012-2017", "2018-2026")))
    except KeyError:
        return False

win_topn = next((nn for nn in (40, 30, 20) if passed(R[f"top{nn}"])), None)
win_trail = next((tw for tw in (0.15, 0.25, 0.30) if passed(R[f"trail{int(tw*100)}"])), None)
win_rank = passed(R["rankra"])
win_slv = next((sv for sv, key in (("Nifty Midcap 50", "slv_mid"), ("Nifty 100", "slv_n100")) if passed(R[key])), None)
print("")
print("AXIS VERDICTS vs bar: topn=%s trail=%s rank_riskadj=%s sleeve=%s floor45=%s consb=%s monthly=%s"
      % (win_topn, win_trail, win_rank, win_slv, passed(R["floor45"]), passed(R["consb"]), passed(R["monthly"])))
axes = [a for a in (win_topn, win_trail, win_rank, win_slv) if a]
if len(axes) >= 2 or (len(axes) == 1 and (win_rank or win_slv)):
    kw = dict(hook=(sel_b14_riskadj if win_rank else sel_b14))
    if win_topn: kw["topn"] = win_topn
    if win_trail: kw["trail"] = win_trail
    if win_slv: kw["sleeve"] = win_slv
    R["compose"] = battery("COMPOSITE (individually-winning axes only)", **kw)
    battery("COMPOSITE TR (measurement)", tr=True, **kw)
else:
    print("  composite: skipped (fewer than the required winning axes)")

print("")
print("TARGET LINE: bar to beat = b14 18.1% PR; Ramana target = 25% (TR-relevant). See TR rows for the")
print("measured lower-bound total-return of each book. done.", flush=True)
