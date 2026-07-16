"""WALK-FORWARD ML RANKER over the union's qualifiers — runner for docs/prereg/union-ml-prereg.md.

PRE-REGISTERED. sha256(docs/prereg/union-ml-prereg.md) =
187c6aa4963e9fe13247b85cce958a006be901d439cc25253356030a8c1d2266 — committed & pushed (c252a21)
BEFORE this module was first run. Design is verbatim from that file; any deviation voids it.

- TRAIN: rebalance dates whose forward window closes <= 2016-12-31. TEST: dates >= 2017-01-01.
- One frozen fit. M1 = Ridge(alpha=1.0) PRIMARY; M2 = GBM(200, 0.05, depth2, sub 0.8, seed 42)
  exploratory. Features/label = within-date MIDRANK percentiles (ties get the mean rank), missing
  -> 0.5. The model only re-orders the union's qualifier list; all book mechanics are the sealed
  union's (fixed 1/60, top60, sleeve200, trail-20% @1% slip, 0.15%/side, dead -50%).
- Label rows: forward stock return minus Nifty 500 over the same rebalance window; a name that
  dies inside the window labels at -50% (engine convention); missing-but-alive endpoints drop the
  row (carried, not punished).
- PASS bar (frozen): on 2017+ the M1 book must beat BOTH the union control AND beta-cap-1.4 on
  CAGR AND alpha, with beta <= 1.0 and MaxDD not worse than control by > 3pp. Else REJECTED.
- 2012-17 is TRAINING data here — no OOS claim about that regime is possible from this design.

Foundation byte-copied from cash_blend.py lineage (same as union_lab.py / union_lab2.py).
"""
import sqlite3, sys, math
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

def qualify(d):
    """ordered union qualifiers with leg tag: (s, sec, turn_fired)"""
    i = ci[d]; amap = assign(d); pm = pym(d)
    out = []
    for s, sec in amap.items():
        if adv.get(s, {}).get(pm, 0) < ADV_BAR: continue
        r_ok = sig_rsi(s, sec, i) and (consistency(s, sec, i) or 0) >= 0.70
        b_ok = rsi_of_rs_recovery(s, sec, i)
        if r_ok or b_ok:
            out.append((s, sec, 1.0 if b_ok else 0.0))
    return out

QUAL = {}
print("[precompute] union qualifiers...", file=sys.stderr, flush=True)
for d in rebal_all:
    QUAL[d] = qualify(d)

# ---- feature construction (prereg list, verbatim order) ----
def rs_rsi_series_window(s, sec, i, back=130, n=14):
    """rolling Wilder RSI over the trailing RS window; returns (values, cal_indices)"""
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
    """pairs = [(s, value-or-None)]; -> {s: pct in [0,1]}, ties get mean rank, None -> 0.5"""
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

print("[features] building train/test matrices...", file=sys.stderr, flush=True)
X_train, y_train, X_test_by_date = [], [], {}
n_train_dates = n_test_dates = 0
for k in range(len(rebal_all)-1):
    d, dn = rebal_all[k], rebal_all[k+1]
    q = QUAL[d]
    if not q: continue
    raw = {s: features_of(s, sec, turn, d) for s, sec, turn in q}
    cols = {c: midrank_pct([(s, raw[s][c]) for s in raw]) for c in FEATS}
    is_train = dn <= "2016-12-31"
    is_test = d >= "2017-01-01"
    if is_train:
        labs = [(s, fwd_label(s, d, dn)) for s, _sec, _t in q]
        labs = [(s, v) for s, v in labs if v is not None]
        if not labs: continue
        lp = midrank_pct(labs)
        n_train_dates += 1
        for s, _v in labs:
            X_train.append([cols[c][s] for c in FEATS])
            y_train.append(lp[s])
    elif is_test:
        n_test_dates += 1
        X_test_by_date[d] = {s: [cols[c][s] for c in FEATS] for s, _sec, _t in q}
print(f"[features] train rows {len(X_train):,} over {n_train_dates} dates; test dates {n_test_dates}",
      file=sys.stderr, flush=True)

from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
m1 = Ridge(alpha=1.0).fit(X_train, y_train)
m2 = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=2,
                               subsample=0.8, random_state=42).fit(X_train, y_train)

SCORE1, SCORE2 = {}, {}
for d, feats in X_test_by_date.items():
    syms = list(feats)
    if not syms: continue
    p1 = m1.predict([feats[s] for s in syms])
    p2 = m2.predict([feats[s] for s in syms])
    SCORE1[d] = dict(zip(syms, p1))
    SCORE2[d] = dict(zip(syms, p2))

# ---- books on the TEST window ----
def sel_default(q, d, i, topn):
    return [s for s, _sec, _t in q]

def sel_beta_cap(mx):
    def f(q, d, i, topn):
        return [s for s, _sec, _t in q if (beta_of(s, i) is None or beta_of(s, i) <= mx)]
    return f

def sel_ml(score):
    def f(q, d, i, topn):
        sc = score.get(d, {})
        return [s for s, _sec, _t in sorted(q, key=lambda t: -sc.get(t[0], -9.9))]
    return f

def run(hook, topn=60, trail=0.20, slip=0.01, start=None, end=None):
    rb = [d for d in rebal_all if (start is None or d >= start) and (end is None or d <= end)]
    nav = bnav = 1.0
    navs, bnavs, invfrac = [], [], []
    held, ent, pk = {}, {}, {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        i = ci[d]
        sel = hook(QUAL[d], d, i, topn)[:topn]
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
            ok = b200[i] is not None and iclose[BENCH][cal[i]] >= b200[i]
            if ok:
                a, b = iclose[SLEEVE].get(d), iclose[SLEEVE].get(dn)
                if a and b: r += idle*(b/a-1.0)
        nav *= (1+r); bnav *= iclose[BENCH][dn]/iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, invfrac

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

print("=" * 118)
print("UNION-ML (pre-registered 187c6aa4...): TEST WINDOW 2017-01 -> 2026. One frozen fit, no iteration.")
print("=" * 118)
print("  Ridge coefficients (percentile features):")
for c, w in zip(FEATS, m1.coef_):
    print("    %-9s %+7.4f" % (c, w))
print("  GBM importances:")
for c, w in zip(FEATS, m2.feature_importances_):
    print("    %-9s %6.3f" % (c, w))

results = {}
for tag, hook in (("control (union, engine order)", sel_default),
                  ("beta_cap_1.4", sel_beta_cap(1.4)),
                  ("M1 Ridge-ranked (PRIMARY)", sel_ml(SCORE1)),
                  ("M2 GBM-ranked (exploratory)", sel_ml(SCORE2))):
    navs, bnavs, inv = run(hook, start="2017-01-01")
    s = stat(navs, bnavs)
    results[tag] = s
    print("  %-32s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%6.2fx  beta %5.2f  alpha %+5.1f%%  inv %3.0f%%"
          % (tag, s['cagr']*100, s['dd']*100, s['mult'], s['beta'], s['alpha']*100,
             sum(inv)/len(inv)*100), flush=True)

c_, b_, m_ = results["control (union, engine order)"], results["beta_cap_1.4"], results["M1 Ridge-ranked (PRIMARY)"]
p1 = m_['cagr'] > c_['cagr'] and m_['alpha'] > c_['alpha']
p2 = m_['cagr'] > b_['cagr'] and m_['alpha'] > b_['alpha']
p3 = m_['beta'] <= 1.0
p4 = m_['dd'] >= c_['dd'] - 0.03
print("")
print("  PASS BAR: 1(beat control C+A)=%s  2(beat beta-cap C+A)=%s  3(beta<=1.0)=%s  4(DD within 3pp)=%s"
      % (p1, p2, p3, p4))
print("  VERDICT: %s" % ("PASS -> candidate status only" if (p1 and p2 and p3 and p4) else "REJECTED (recorded, no re-run)"))
print("")
print("done.", flush=True)
