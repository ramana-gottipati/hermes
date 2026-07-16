"""DIMENSION 6 — FINISHED. All eight reversal-on-RS indicators, including 6c.

Ramana, 2026-07-16: "finish dimension 6 properly."

Status coming in: only 6a was run (slope inflection, CAGR -1.1% — lost money). 6g was ranked SECOND
highest prior and never run. 6b/6d/6e/6f/6h never run. 6c was held back deliberately so a failure
there could not be misread as "reversal is dead" — with 6a already failed and the rest now running,
holding it back no longer serves a purpose, so it is included and marked.

LEDGER BLOCKS CITED (failure-ledger discipline — these are BLOCKING until cited):
  * price-band mean reversion is FALSIFIED AT EVERY LEVEL — 07-13 (timing); 07-14b FRACTAL FENCES:
    "every fence fails; the reversal-pair program closes with ZERO tradeable survivors."
  * the crude RS SIGN-FLIP is falsified — 15Q: flat panel, all four cells within ONE standard error.
  * 6a slope inflection is falsified — the RSI battery: CAGR -1.1%, Rs1Cr -> 0.80x over 20 years.
WHY THESE DO NOT BLOCK 6b/6d/6e/6f/6g/6h: those tested PRICE bouncing off a support band, and a
sign-flip STATE. The indicators below are different constructs (momentum-of-momentum, MA crossovers,
MACD, drawdown-recovery magnitude, cross-sectional RANK). 6c is the one genuine adjacency — it is the
same band+mean-reversion MECHANISM as the falsified family, only applied to RS instead of price — and
is flagged as such rather than presented as new.

HONEST PRIOR (from today, stated before the run): every reversal/turn construct tested so far has
failed, and the only things that ever worked were PERSISTENCE (consistency>=70%) and the TRAILING
STOP. A "catch the turn" family that keeps failing is evidence about the family, not just each cell.
Expect these to fail. Run them anyway, because 6g was never given its chance.

Each indicator is tested as a SELECTOR (does it pick winners?) via forward 3m excess vs Nifty 500 --
the same cheap decomposition as 15P/15Q, so results are comparable and one run covers all eight.
Foundation: corporate-action adjusted · 156 quarantined · prior-month ADV >= Rs5cr · PIT.
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
LB, FWD, CORRWIN, ADV_BAR = 126, 63, 500, 5e7

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
_raw = {sym: dict(dd) for sym, dd in sclose.items()}
fac = load_factors(conn); adjust_all(sclose, fac)
QUAR, _qd = _q.build(conn, _raw, sclose)
conn.close()

cal = sorted(iclose[BENCH]); ci = {d: i for i, d in enumerate(cal)}; N = len(cal)
SYMS = [s for s, cl in sclose.items() if s not in QUAR and len(cl) >= 400]
print(f"[data] {len(SYMS):,} symbols after quarantine", file=sys.stderr)

# ---- sector assignment (PIT correlation, cached per year) ----
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

def rs_at(s, sec, j):
    """the RS ratio line: stock / its own sector index"""
    a, b = sclose[s].get(cal[j]), iclose[sec].get(cal[j])
    return a/b if (a and b) else None

def rs_window(s, sec, i, w):
    return [x for x in (rs_at(s, sec, j) for j in range(max(0, i-w), i+1)) if x is not None]

def _ema(vals, n):
    if len(vals) < n: return None
    a = 2.0/(n+1); e = sum(vals[:n])/n
    for v in vals[n:]: e = a*v + (1-a)*e
    return e

def _rsi_of(vals, n=14):
    if len(vals) < n+1: return None
    g = l = 0.0
    for k in range(len(vals)-n, len(vals)):
        ch = vals[k]-vals[k-1]; g += max(ch, 0); l += max(-ch, 0)
    ag, al = g/n, l/n
    if al == 0: return 100.0
    if ag == 0: return 0.0
    return 100.0 - 100.0/(1.0+ag/al)

# ================= THE EIGHT INDICATORS =================
def i6a(s, sec, i):
    """6a slope inflection — ALREADY FAILED (-1.1%). Re-run here as the control."""
    now, mid, old = rs_at(s, sec, i), rs_at(s, sec, i-21), rs_at(s, sec, i-42)
    if None in (now, mid, old): return False
    w = rs_window(s, sec, i, 50)
    if len(w) < 30: return False
    return now < sum(w)/len(w) and (now-mid) > 0 and (mid-old) <= 0

def i6b(s, sec, i):
    """6b RSI-of-RS oversold recovery: RSI(RS line) was <30, now crossed back above 30"""
    w = rs_window(s, sec, i, 60)
    if len(w) < 40: return False
    now = _rsi_of(w)
    prev = _rsi_of(w[:-10]) if len(w) > 50 else None
    if now is None or prev is None: return False
    return prev < 30 and now >= 30

def i6c(s, sec, i):
    """6c RS Bollinger reclaim — ADJACENT to the falsified price-band family. Flagged, not new."""
    w = rs_window(s, sec, i, 50)
    if len(w) < 40: return False
    m = sum(w)/len(w)
    sd = math.sqrt(sum((x-m)**2 for x in w)/(len(w)-1))
    if sd == 0: return False
    lower = m - 2*sd
    touched = any(x <= lower for x in w[:-5])
    now = w[-1]
    return touched and now > lower and now < m

def i6d(s, sec, i):
    """6d dual-MA crossover on RS: 20d MA of RS crosses above its 50d MA"""
    w = rs_window(s, sec, i, 60)
    if len(w) < 55: return False
    def sma(v, n): return sum(v[-n:])/n if len(v) >= n else None
    f_now, s_now = sma(w, 20), sma(w, 50)
    f_prev, s_prev = sma(w[:-5], 20), sma(w[:-5], 50)
    if None in (f_now, s_now, f_prev, s_prev): return False
    return f_prev <= s_prev and f_now > s_now

def i6e(s, sec, i):
    """6e MACD-of-RS: MACD(12,26) of the RS line crosses above its 9-period signal"""
    w = rs_window(s, sec, i, 80)
    if len(w) < 45: return False
    def macd_at(v):
        e12, e26 = _ema(v, 12), _ema(v, 26)
        return (e12-e26) if (e12 is not None and e26 is not None) else None
    line = []
    for k in range(len(w)-12, len(w)+1):
        m = macd_at(w[:k])
        if m is not None: line.append(m)
    if len(line) < 10: return False
    sig = sum(line[-9:])/9
    prev_sig = sum(line[-10:-1])/9
    return line[-2] <= prev_sig and line[-1] > sig

def i6f(s, sec, i):
    """6f RS drawdown recovery: RS was >15% below its trailing high, now within 5% of a new high"""
    w = rs_window(s, sec, i, 126)
    if len(w) < 80: return False
    hi = max(w)
    trough = min(w)
    if hi <= 0: return False
    fell = (trough/hi - 1.0) < -0.15
    now = w[-1]
    recovered = (now/hi - 1.0) > -0.05
    return fell and recovered

def i6h(s, sec, i):
    """6h price/RS divergence: price makes a new 60d low, RS line does NOT"""
    lo = max(0, i-60)
    px = [sclose[s].get(cal[j]) for j in range(lo, i+1)]
    px = [x for x in px if x is not None]
    w = rs_window(s, sec, i, 60)
    if len(px) < 40 or len(w) < 40: return False
    price_new_low = px[-1] <= min(px)*1.01
    rs_new_low = w[-1] <= min(w)*1.01
    return price_new_low and not rs_new_low

def i6g_pool(d, amap, i):
    """6g cross-sectional RANK CLIMB — needs the whole sector pool, so it is computed per-sector.
    Was in the bottom third of its sector's RS ranking a month ago, now in the middle/top third."""
    bysec = defaultdict(list)
    for s, sec in amap.items(): bysec[sec].append(s)
    picked = set()
    for sec, members in bysec.items():
        now, then = [], []
        for s in members:
            a, b = rs_at(s, sec, i), rs_at(s, sec, i-21)
            if a is None or b is None: continue
            now.append((a, s)); then.append((b, s))
        if len(now) < 8: continue
        now.sort(); then.sort()
        n = len(now)
        rank_now = {s: k/n for k, (_, s) in enumerate(now)}
        rank_then = {s: k/n for k, (_, s) in enumerate(then)}
        for s in rank_now:
            if s in rank_then and rank_then[s] < 0.33 and rank_now[s] >= 0.50:
                picked.add(s)
    return picked

rebal = [d for i, d in enumerate(cal) if i >= max(CORRWIN, LB, 130) and i+FWD < len(cal)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(rebal)} quarterly dates {rebal[0]} -> {rebal[-1]}", file=sys.stderr)

FNS = [("6a slope inflection (control — already failed)", i6a),
       ("6b RSI-of-RS oversold recovery (<30 -> >30)", i6b),
       ("6c RS Bollinger reclaim  [ADJACENT to dead family]", i6c),
       ("6d dual-MA crossover on RS (20d over 50d)", i6d),
       ("6e MACD-of-RS signal crossover", i6e),
       ("6f RS drawdown recovery (-15% then within 5%)", i6f),
       ("6h price/RS divergence (price low, RS not)", i6h)]

res = defaultdict(list)
base = []
g_res = []
for d in rebal:
    i = ci[d]; df = cal[i+FWD]
    amap = assign(d); ym = d[:7]
    bf = iclose[BENCH][df]/iclose[BENCH][d]-1.0
    universe = [(s, sec) for s, sec in amap.items() if adv.get(s, {}).get(ym, 0) >= ADV_BAR]
    if len(universe) < 20: continue
    def fwd(s):
        a, b = sclose[s].get(d), sclose[s].get(df)
        return (b/a-1.0)-bf if (a and b) else None
    for s, sec in universe:
        f = fwd(s)
        if f is not None: base.append(f)
    for tag, fn in FNS:
        for s, sec in universe:
            try:
                if not fn(s, sec, i): continue
            except Exception:
                continue
            f = fwd(s)
            if f is not None: res[tag].append(f)
    for s in i6g_pool(d, dict(universe), i):
        f = fwd(s)
        if f is not None: g_res.append(f)

def mean(x): return sum(x)/len(x) if x else float('nan')
def sd(x):
    m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1)) if len(x) > 1 else float('nan')

print("\n" + "="*110)
print("DIMENSION 6 — ALL EIGHT REVERSAL-ON-RS INDICATORS (forward 3m excess vs Nifty 500)")
print("="*110)
m0, s0 = mean(base), sd(base)
se0 = s0/math.sqrt(len(base))
print("  %-52s%7s%10s%9s%10s%9s" % ("indicator", "n", "mean/qtr", "sd/qtr", "GEO/qtr", "vs base"))
print("  %-52s%7d%9.2f%%%9.2f%%%9.2f%%%9s   <- NO SELECTION baseline (+/-%.2f%%)"
      % ("(every liquid stock, no filter)", len(base), m0*100, s0*100, (m0-s0*s0/2)*100, "--", se0*100))
rows = []
allr = list(res.items()) + [("6g cross-sectional RANK CLIMB (bottom->mid/top)", None)]
for tag, _ in allr:
    x = g_res if tag.startswith("6g") else res[tag]
    if len(x) < 30:
        print("  %-52s%7d   too few" % (tag, len(x))); continue
    m, s_ = mean(x), sd(x); geo = m - s_*s_/2
    se = s_/math.sqrt(len(x))
    delta = m - m0
    sig = "SIG" if abs(delta) > 2*math.sqrt(se**2 + se0**2) else "ns"
    rows.append((geo, tag, m, s_, len(x), delta, sig))
    print("  %-52s%7d%9.2f%%%9.2f%%%9.2f%%%+8.2f%% %s" % (tag, len(x), m*100, s_*100, geo*100, delta*100, sig))

print("\n  'vs base' = mean minus the no-selection baseline. SIG = beyond 2 standard errors of the")
print("  difference. An indicator is only worth anything if it beats the baseline SIGNIFICANTLY.")
if rows:
    rows.sort(reverse=True)
    print("\n  BEST BY GEOMETRIC: %s" % rows[0][1])
    winners = [r for r in rows if r[6] == "SIG" and r[5] > 0]
    print("  INDICATORS BEATING THE NO-SELECTION BASELINE SIGNIFICANTLY: %s"
          % (", ".join(r[1].split()[0] for r in winners) if winners else "NONE"))
