"""UNION ML2 — pre-registered walk-forward GBM ranker over the ERA-FLOOR capped qualifiers.

PRE-REGISTERED: docs/prereg/union-ml2-prereg.md, sha256 =
bf74a7a5dd79b69826f01e359245cb3c8e22b2e3442d87166f592d73e0aa3c0e, committed & pushed (a18a2d5)
BEFORE this module first ran. Design verbatim from that file: GBM(200, 0.05, depth2, sub 0.8,
seed 42) PRIMARY / Ridge(1.0) exploratory; the identical 10 features and label of 16AA; TRAIN =
label windows closed <= 2016-12-31 over the CAPPED (beta<=1.4) era-floor (pf1) qualifiers; TEST =
rebalances >= 2017-01-01; ONE frozen fit. The model only re-orders the capped qualifiers; book
mechanics = A2-composite (top-40, 1/40 slots, sleeve200 + rf-earning bear-cash, trail-20@1%).

FROZEN BAR (all five, on 2017+): (1) beat the A2-COMPOSITE (RISKADJ-rank) on CAGR AND alpha;
(2) beat the engine-order CONTROL on CAGR AND alpha; (3) beta <= 1.0; (4) MaxDD within 3pp of the
A2-composite; (5) @2% stop-slip still beats the A2-composite CAGR. Fail any -> REJECTED, recorded,
no variant shopping. A pass earns DEFERRED-LEAD status only (family closed at three seals).
2012-17 is TRAINING data — no OOS claim about that regime.

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


def qualify3(d):
    """pf1-floor union qualifiers WITH the leg tag: (s, sec, turn_fired)"""
    i = ci[d]; amap = assign(d, "pf1"); pm = pym(d)
    fl = FLOORS["pf1"]
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < fl(pm): continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
        b_ok = rsi_of_rs_recovery(s, sec, i)
        if r_ok or b_ok:
            out.append((s, sec, 1.0 if b_ok else 0.0))
    return out

QUAL3 = {}
print("[precompute] pf1 qualifiers (with leg tag)...", file=sys.stderr, flush=True)
for d in rebal_all:
    QUAL3[d] = qualify3(d)

def capped3(q, i, mx=1.4):
    return [(s, sec, t) for s, sec, t in q if (beta_of(s, i) is None or beta_of(s, i) <= mx)]

# ---- features/label (verbatim 16AA constructions) ----
def rs_rsi_series_window(s, sec, i, back=130, n=14):
    pts = [(j, rs_at(s, sec, j)) for j in range(max(0, i-back), i+1)]
    pts = [(j, v) for j, v in pts if v is not None]
    if len(pts) < n+2: return [], []
    vals = [v for _, v in pts]; idxs = [j for j, _ in pts]
    gain = loss = None; out = [None]*len(vals)
    for k in range(1, len(vals)):
        ch = vals[k]-vals[k-1]
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if gain is None: gain, loss = g, l
        else:
            gain = (gain*(n-1)+g)/n; loss = (loss*(n-1)+l)/n
        if k >= n:
            if loss == 0: out[k] = 100.0
            elif gain == 0: out[k] = 0.0
            else: out[k] = 100.0-100.0/(1.0+gain/loss)
    return out, idxs

def features_of(s, sec, turn, d):
    i = ci[d]
    f = {}
    f["leg"] = turn
    f["rsi"] = RSI[s][i]
    f["rsi_gap"] = (RSI[s][i]-RMA[s][i]) if (RSI[s][i] is not None and RMA[s][i] is not None) else None
    f["consist"] = consistency(s, sec, i)
    rr, idxs = rs_rsi_series_window(s, sec, i)
    f["rsrsi"] = rr[-1] if rr and rr[-1] is not None else None
    age = None
    if rr:
        last_cross = None
        for k in range(1, len(rr)):
            if rr[k-1] is not None and rr[k] is not None and rr[k-1] < 30 <= rr[k]:
                last_cross = idxs[k]
        if last_cross is not None:
            age = min(i - last_cross, 63)
    f["turn_age"] = age if age is not None else 63
    f["beta"] = beta_of(s, i)
    a0, a1 = pxn(s, cal[max(0, i-63)]), pxn(s, d)
    sc0, sc1 = iclose[sec].get(cal[max(0, i-63)]), iclose[sec].get(d)
    f["ex63"] = (a1/a0 - sc1/sc0) if (a0 and a1 and sc0 and sc1) else None
    w = [x for x in (rs_at(s, sec, j) for j in range(max(0, i-126), i+1)) if x is not None]
    f["rsdd"] = (min(w)/max(w)-1.0) if len(w) >= 60 and max(w) > 0 else None
    rets = []
    for j in range(max(1, i-63), i+1):
        p0, p1 = sclose[s].get(cal[j-1]), sclose[s].get(cal[j])
        if p0 and p1: rets.append(p1/p0-1.0)
    if len(rets) >= 30:
        mu = sum(rets)/len(rets)
        f["sd63"] = math.sqrt(sum((x-mu)**2 for x in rets)/(len(rets)-1))
    else:
        f["sd63"] = None
    return f

FEATS = ["leg", "rsi", "rsi_gap", "consist", "rsrsi", "turn_age", "beta", "ex63", "rsdd", "sd63"]

def midrank_pct(pairs):
    known = sorted((v, s) for s, v in pairs if v is not None)
    n = len(known)
    out = {}
    k = 0
    while k < n:
        j = k
        while j+1 < n and known[j+1][0] == known[k][0]:
            j += 1
        mean_rank = (k + j)/2.0 + 0.5
        for t in range(k, j+1):
            out[known[t][1]] = mean_rank/n
        k = j+1
    for s, v in pairs:
        if v is None: out[s] = 0.5
    return out

def fwd_label(s, d, dn):
    a, b = pxn(s, d), pxn(s, dn)
    if a and b:
        return (b/a-1.0) - (iclose[BENCH][dn]/iclose[BENCH][d]-1.0)
    if a and isdead(s, dn):
        return DEAD_VAL - (iclose[BENCH][dn]/iclose[BENCH][d]-1.0)
    return None

print("[features] building matrices over CAPPED pf1 qualifiers...", file=sys.stderr, flush=True)
X_train, y_train, X_test_by_date = [], [], {}
n_train_dates = n_test_dates = 0
for k in range(len(rebal_all)-1):
    d, dn = rebal_all[k], rebal_all[k+1]
    i = ci[d]
    q = capped3(QUAL3[d], i)
    if not q: continue
    raw = {s: features_of(s, sec, turn, d) for s, sec, turn in q}
    cols = {c: midrank_pct([(s, raw[s][c]) for s in raw]) for c in FEATS}
    if dn <= "2016-12-31":
        labs = [(s, fwd_label(s, d, dn)) for s, _sec, _t in q]
        labs = [(s, v) for s, v in labs if v is not None]
        if not labs: continue
        lp = midrank_pct(labs)
        n_train_dates += 1
        for s, _v in labs:
            X_train.append([cols[c][s] for c in FEATS])
            y_train.append(lp[s])
    elif d >= "2017-01-01":
        n_test_dates += 1
        X_test_by_date[d] = {s: [cols[c][s] for c in FEATS] for s, _sec, _t in q}
print(f"[features] train rows {len(X_train):,} over {n_train_dates} dates; test dates {n_test_dates}",
      file=sys.stderr, flush=True)

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
m1 = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=2,
                               subsample=0.8, random_state=42).fit(X_train, y_train)
m2 = Ridge(alpha=1.0).fit(X_train, y_train)
SCORE1, SCORE2 = {}, {}
for d, feats in X_test_by_date.items():
    syms = list(feats)
    if not syms: continue
    SCORE1[d] = dict(zip(syms, m1.predict([feats[s] for s in syms])))
    SCORE2[d] = dict(zip(syms, m2.predict([feats[s] for s in syms])))

# ---- books on the TEST window (A2-composite mechanics: top-40, rf-cash) ----
def hook_control(q, d, i, topn):
    return [s for s, _sec, _t in capped3(q, i)]

def hook_riskadj(q, d, i, topn):
    inc = capped3(q, i)
    scored = [(s, riskadj_of(s, i)) for s, _sec, _t in inc]
    return [s for s, v in sorted(scored, key=lambda t: -(t[1] if t[1] is not None else -99))]

def hook_ml(score):
    def f(q, d, i, topn):
        sc = score.get(d, {})
        return [s for s, _sec, _t in sorted(q, key=lambda t: -sc.get(t[0], -9.9))
                if (beta_of(s, i) is None or beta_of(s, i) <= 1.4)]
    return f

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

def run_ml(hook, topn=40, trail=0.20, slip=0.01, start="2017-01-01", end=None):
    rb = [d for d in rebal_all if d >= start and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac = [], [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = hook(QUAL3[d], d, i, topn)[:topn]
        w = {s: 1.0/topn for s in sel}
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
        if idle > 0:
            healthy = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if healthy:
                a2_, b2_ = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
                if a2_ and b2_: r += idle*(b2_/a2_-1.0)
            else:
                r += idle*rf_q(d, dn)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, invfrac

print("=" * 118)
print("UNION-ML2 (prereg bf74a7a5..., pushed a18a2d5): TEST 2017-01 -> 2026. One frozen GBM fit.")
print("=" * 118)
print("  GBM importances:")
for c, wgt in zip(FEATS, m1.feature_importances_):
    print("    %-9s %6.3f" % (c, wgt))

results = {}
for tag, hook, slp in (("control (engine order)", hook_control, 0.01),
                       ("A2-composite (RISKADJ-rank)", hook_riskadj, 0.01),
                       ("M1 GBM-ranked (PRIMARY)", hook_ml(SCORE1), 0.01),
                       ("M2 Ridge-ranked (exploratory)", hook_ml(SCORE2), 0.01),
                       ("A2-composite @2% slip", hook_riskadj, 0.02),
                       ("M1 GBM @2% slip", hook_ml(SCORE1), 0.02)):
    navs, bnavs, inv = run_ml(hook, slip=slp)
    s = stat(navs, bnavs)
    results[tag] = s
    print("  %-34s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%"
          % (tag, s["cagr"]*100, s["dd"]*100, s["mult"], s["beta"], s["alpha"]*100,
             sum(inv)/len(inv)*100), flush=True)

a2, ct, m1r = results["A2-composite (RISKADJ-rank)"], results["control (engine order)"], results["M1 GBM-ranked (PRIMARY)"]
c1 = m1r["cagr"] > a2["cagr"] and m1r["alpha"] > a2["alpha"]
c2 = m1r["cagr"] > ct["cagr"] and m1r["alpha"] > ct["alpha"]
c3 = m1r["beta"] <= 1.0
c4 = m1r["dd"] >= a2["dd"] - 0.03
c5 = results["M1 GBM @2% slip"]["cagr"] > results["A2-composite @2% slip"]["cagr"]
print("")
print("  BAR: 1(beat A2 C+A)=%s 2(beat control C+A)=%s 3(beta<=1)=%s 4(DD within 3pp)=%s 5(slip2 beats A2)=%s"
      % (c1, c2, c3, c4, c5))
print("  VERDICT: %s" % ("PASS -> DEFERRED-LEAD status only" if all((c1, c2, c3, c4, c5)) else "REJECTED (recorded, no re-run)"))
print("")
print("done.", flush=True)
