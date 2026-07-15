"""Round 4 — V22..V30 batch, each tested against V21 (primary base) AND V17 (secondary
check). V21 = sleeve=Next50 + recovery-accelerator + inverse-vol (Sharpe 0.87, Rs27.02).
V17 = sleeve=N500, no recovery, no invvol (Sharpe 0.79, Rs19.04). Both FROZEN, never edited.

LEVER catalog (each isolated first, tested on both bases; combos only if individually positive):
  V22 ADAPTBAND   entry/exit band = 1.0x the sector's own trailing daily RS-line vol
                  (scaled to 126d), replacing the fixed +-8%.
  V23 TRENDXIT    2-consecutive-quarter RS-excess DIRECTION as an extra early trigger,
                  layered on top of (not replacing) the existing +-8% band.
  V24 OWNPCT      RSI-of-RS taper threshold = that sector's own trailing-756d percentile
                  (85th trims, 95th exits) instead of fixed 70/80.
  V25 LONGRSI     RSI-of-RS computed with n=50 over a 90-day window, instead of n=14/40.
  V26 PERSIST     the RSI-of-RS taper condition (70/80, or OWNPCT if combined) must hold
                  for 2 consecutive quarterly checks before it acts.
  V27 DUALBENCH   RSI-of-RS must ALSO be extended vs Nifty 50 to trigger the taper.
  V28 REGIME      RSI-of-RS taper replaced by a stateful regime: enter "hot" at >=55,
                  exit at <45, full weight while hot regardless of how high it climbs.
  V29 SATELLITE   adds CNX Midcap + Nifty Midcap 50 (2012+) to the sector universe,
                  same gates as any sector.
  V30 VOLTARGET   post-hoc overlay: scale total exposure to hold ~15% annualized vol,
                  using the trailing 6-quarter realized vol of the STRATEGY's own returns.
"""
import sqlite3, math, sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
LEVER = sys.argv[2] if len(sys.argv) > 2 else "SANITY"

BENCH = "Nifty 500"
N50 = "Nifty 50"
NEXT50 = "Nifty Next 50"
CNXMID = "CNX Midcap"
MID50 = "Nifty Midcap 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
SATELLITES = [CNXMID, MID50]
START, LB, CAP, BAND, COST = "2005-01-03", 126, 0.30, 0.08, 0.0015

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = defaultdict(dict)
names = SECTORS + SATELLITES + [BENCH, N50, NEXT50]
q = "SELECT index_name,trade_date,close_value FROM index_rows WHERE index_name IN (%s) AND close_value>0" % ",".join("?"*len(names))
for nm, d, c in conn.execute(q, names):
    close[nm][d] = c
conn.close()

cal = sorted(d for d in close[BENCH] if d >= START)
idx = {d: i for i, d in enumerate(cal)}
rebal, seen = [], set()
for d in cal:
    if d[:7] not in seen:
        seen.add(d[:7]); rebal.append(d)

def universe_for(lever):
    return SECTORS + (SATELLITES if lever == "V29" else [])

def ret(nm, d0, d1):
    a, b = close[nm].get(d0), close[nm].get(d1)
    return (b/a-1.0) if (a and b) else None

def trailing(nm, d, lb=LB):
    i = idx.get(d)
    if i is None or i-lb < 0: return None
    d0 = cal[i-lb]
    return close[nm][d]/close[nm][d0]-1.0 if (d0 in close[nm] and d in close[nm]) else None

def series(nm, d, win):
    i = idx.get(d)
    if i is None: return []
    return [close[nm][cal[k]] for k in range(max(0,i-win+1), i+1) if cal[k] in close[nm]]

def rsi(vals, n=14):
    if len(vals) < n+1: return None
    g=l=0.0
    for k in range(len(vals)-n, len(vals)):
        ch = vals[k]-vals[k-1]; g += max(ch,0); l += max(-ch,0)
    ag, al = g/n, l/n
    return 100.0 if al==0 else 100.0-100.0/(1.0+ag/al)

def rsi14_price(nm, d): return rsi(series(nm, d, 40))
def pctile(x, arr): return (sum(1 for a in arr if a<=x)/len(arr)) if arr else None

def rs_line(nm, d, win, vs=BENCH):
    i = idx.get(d)
    if i is None: return []
    return [close[nm][cal[k]]/close[vs][cal[k]] for k in range(max(0,i-win+1), i+1)
            if cal[k] in close[nm] and cal[k] in close[vs]]

def rs_peak_pct(nm, d):
    s = rs_line(nm, d, 756)
    return pctile(s[-1], s) if len(s) > 60 else None

def stretch_z(nm, d):
    s = series(nm, d, 200)
    if len(s) < 150: return None
    m = sum(s)/len(s); sd = math.sqrt(sum((x-m)**2 for x in s)/(len(s)-1))
    return (s[-1]-m)/sd if sd > 0 else 0.0

def rsi_of_rs(nm, d, n=14, win=40, vs=BENCH):
    return rsi(rs_line(nm, d, win, vs), n=n)

def rs_daily_vol(nm, d, win=126):
    """stdev of the RS-line's own daily % changes -> scaled to a 126d horizon (adaptive band)."""
    s = rs_line(nm, d, win + 1)
    if len(s) < 60: return None
    rets = [s[i]/s[i-1]-1 for i in range(1, len(s))]
    m = sum(rets)/len(rets)
    dvol = math.sqrt(sum((x-m)**2 for x in rets)/(len(rets)-1))
    return dvol * math.sqrt(win)

def taper(p, thr=0.85, floor=0.35):
    if p is None or p <= thr: return 1.0
    return max(floor, 1.0-(p-thr)/(1-thr)*(1-floor))

# ---- precomputed daily RSI-of-RS series per sector (for V24 own-percentile + V26 persist) ----
_RSIRS_CACHE = {}
def rsirs_series_at(nm, d):
    """trailing-756d slice of the DAILY RSI-of-RS series for nm, ending at d (cached full series)."""
    if nm not in _RSIRS_CACHE:
        full = []
        i = idx[d] if d in idx else len(cal)-1
        # build once, lazily, for the whole calendar (cheap: one rsi() call/day using a rolling window)
        vals = []
        for k, dt in enumerate(cal):
            r = rs_line(nm, dt, 40)
            vals.append(rsi(r) if len(r) >= 15 else None)
        _RSIRS_CACHE[nm] = vals
    full = _RSIRS_CACHE[nm]
    i = idx[d]
    win = [v for v in full[max(0,i-756):i+1] if v is not None]
    return win

# ---- state carried across quarters (persistence / trend / regime) ----
_STATE = {}

def taper_product(s, d, lever):
    parts = lever.split("+")
    if "V25" in parts:
        r = rsi_of_rs(s, d, n=50, win=90)
        trim_now = r is not None and r >= 70
        exit_now = r is not None and r >= 80
    elif "V24" in parts:
        hist = rsirs_series_at(s, d)
        r = rsi_of_rs(s, d)
        p = pctile(r, hist) if (r is not None and len(hist) > 60) else None
        trim_now = p is not None and p >= 0.85
        exit_now = p is not None and p >= 0.95
    elif "V27" in parts:
        r500 = rsi_of_rs(s, d, vs=BENCH); r50 = rsi_of_rs(s, d, vs=N50)
        trim_now = r500 is not None and r50 is not None and r500 >= 70 and r50 >= 70
        exit_now = r500 is not None and r50 is not None and r500 >= 80 and r50 >= 80
    elif "V28" in parts:
        r = rsi_of_rs(s, d)
        reg = _STATE.setdefault("v28_regime", {})
        cur = reg.get(s, False)
        if r is not None:
            if not cur and r >= 55: cur = True
            elif cur and r < 45: cur = False
        reg[s] = cur
        f = 1.0 if cur else 0.3
        f *= taper(rs_peak_pct(s, d))
        z = stretch_z(s, d)
        f *= taper(pctile(z, [-2,-1,0,1,1.5,2,2.5]) if z is not None else None, thr=0.7)
        return f
    else:
        r = rsi_of_rs(s, d)
        trim_now = r is not None and r >= 70
        exit_now = r is not None and r >= 80

    if "V26" in parts:
        prev = _STATE.setdefault("v26_prev", {}).get(s, False)
        exit_now = exit_now and prev
        trim_now = trim_now and prev
        _STATE["v26_prev"][s] = (r is not None and r >= 70) if "V24" not in parts else bool(p and p >= 0.85)

    f_rsirs = 0.0 if exit_now else (0.5 if trim_now else 1.0)
    f = 1.0
    f *= taper(rs_peak_pct(s, d))
    z = stretch_z(s, d)
    f *= taper(pctile(z, [-2,-1,0,1,1.5,2,2.5]) if z is not None else None, thr=0.7)
    f *= f_rsirs
    return f

def cap_only(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap+1e-9}
        if not over: break
        exc = sum(w[s]-cap for s in over)
        for s in over: w[s] = cap
        und = [s for s in w if w[s] < cap-1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und: w[s] += exc*w[s]/tu
    return w

def vol126(s, d):
    ser = series(s, d, 127)
    if len(ser) < 60: return None
    rets = [ser[i]/ser[i-1]-1 for i in range(1, len(ser))]
    m = sum(rets)/len(rets)
    return math.sqrt(sum((x-m)**2 for x in rets)/(len(rets)-1))

def rs_excess(s, d):
    tr, tb = trailing(s, d), trailing(BENCH, d)
    return None if (tr is None or tb is None) else tr-tb

def entry_exit_band(s, d, lever):
    """returns (enter_threshold, exit_threshold) — both positive numbers; exit uses -exit_threshold."""
    if "V22" in lever.split("+"):
        v = rs_daily_vol(s, d)
        b = v if v is not None else BAND
        b = max(0.02, min(0.30, b))    # sane bounds
        return b, b
    return BAND, BAND

def qualifying(d, held, lever, entry_band_override=None):
    longs = {}
    trend = _STATE.setdefault("rs_hist", {})
    for s in universe_for(lever):
        v = rs_excess(s, d)
        if v is None: continue
        eb, xb = entry_exit_band(s, d, lever)
        if entry_band_override is not None: eb = entry_band_override
        h = trend.setdefault(s, [])
        h.append(v); trend[s] = h[-3:]     # keep last 3 quarterly readings
        improving2 = len(h) >= 3 and h[-1] > h[-2] > h[-3]
        worsening2 = len(h) >= 3 and h[-1] < h[-2] < h[-3]
        if s in held:
            keep = v > -xb
            if lever == "V23" and worsening2 and v < 0:
                keep = False              # early exit on confirmed 2-quarter deterioration
            if keep: longs[s] = max(v, 1e-6)
        else:
            enter = v > eb
            if lever == "V23" and not enter and improving2 and v > 0:
                enter = True              # early entry on confirmed 2-quarter improvement
            if enter: longs[s] = v
    keep = {}; i = idx[d]; dprev = cal[max(0, i-21)]
    for s in longs:
        rn, rp_ = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp_ is None or rn >= rp_)):
            keep[s] = longs[s]
    return keep

def build(d, held, lever, entry_band=None, invvol=False):
    longs = qualifying(d, held, lever, entry_band)
    if not longs: return {}
    if invvol:
        iv = {}
        for s in longs:
            v = vol126(s, d)
            iv[s] = 1.0/v if v and v > 0 else 0.0
        tot = sum(iv.values())
        base = cap_only({s: iv[s]/tot for s in iv}) if tot > 0 else cap_only({s: 1.0/len(longs) for s in longs})
    else:
        base = cap_only({s: 1.0/len(longs) for s in longs})
    adj = {s: base[s]*taper_product(s, d, lever) for s in base}
    tot = sum(adj.values())
    if tot <= 0: return base
    return cap_only({s: adj[s]/tot for s in adj})

def kill_on(d):
    s = series(BENCH, d, 200)
    return len(s) >= 200 and s[-1] < sum(s)/len(s)

def sleeve_ret(asset, d, dn):
    r = ret(asset, d, dn)
    return r if r is not None else (ret(BENCH, d, dn) or 0.0)

def simulate(base="V21", lever="NONE"):
    sleeve = NEXT50 if base == "V21" else BENCH
    recovery = (base == "V21")
    invvol = (base == "V21")
    _STATE.clear()
    prev = {}; rows = []; turn_sum = 0.0
    for k in range(len(rebal)-1):
        d, dn = rebal[k], rebal[k+1]
        is_q = (k % 3 == 0)
        if is_q:
            eb = None
            if recovery and not kill_on(d):
                lookback = [rebal[k-j] for j in (1, 2, 3) if k-j >= 0]
                if any(kill_on(x) for x in lookback):
                    eb = 0.0
            w = build(d, set(prev), lever, eb, invvol)
        else:
            w = dict(prev)
        rb = ret(BENCH, d, dn) or 0.0
        on_index = not kill_on(d)
        inv = sum(w.values())
        if not w:
            rp = sleeve_ret(sleeve, d, dn) if on_index else 0.0
        else:
            rp = sum(x*(ret(s, d, dn) or 0.0) for s, x in w.items())
            if inv < 1.0 and on_index:
                rp += (1.0-inv)*sleeve_ret(sleeve, d, dn)
        if is_q:
            allk = set(w)|set(prev)
            t = sum(abs(w.get(s,0)-prev.get(s,0)) for s in allk)
            rp -= t*COST; turn_sum += t
        rows.append((dn, rp, rb)); prev = w
    if lever == "V30":
        rows = _voltarget(rows)
    return rows, turn_sum/max(1,len(rows))

def _voltarget(rows, target=0.15, lookback_q=6, lo=0.5, hi=1.5):
    """post-hoc: scale each quarter's return by target_vol / trailing realized vol."""
    out = []; hist = []
    for d, rp, rb in rows:
        if len(hist) >= lookback_q:
            m = sum(hist)/len(hist)
            sd = math.sqrt(sum((x-m)**2 for x in hist)/(len(hist)-1)) if len(hist) > 1 else 0.0
            realized_ann = sd*math.sqrt(4) if sd > 0 else target
            scale = max(lo, min(hi, target/realized_ann)) if realized_ann > 0 else 1.0
        else:
            scale = 1.0
        out.append((d, rp*scale, rb))
        hist.append(rp); hist = hist[-lookback_q:]
    return out

def stats(rows):
    rp = [r[1] for r in rows]; rb = [r[2] for r in rows]; n = len(rp)
    m = sum(rp)/n; sd = math.sqrt(sum((x-m)**2 for x in rp)/(n-1))
    sh = m/sd*math.sqrt(12) if sd else 0
    nav = pk = 1.0; mdd = 0.0
    for x in rp:
        nav *= 1+x; pk = max(pk, nav); mdd = min(mdd, nav/pk-1)
    yrs = n/12
    mb = sum(rb)/n
    covv = sum((rp[i]-m)*(rb[i]-mb) for i in range(n))/(n-1)
    varb = sum((x-mb)**2 for x in rb)/(n-1)
    beta = covv/varb if varb else 0; alpha = (m-beta*mb)*12
    half = n//2
    def sh_(xs):
        mm = sum(xs)/len(xs); s2 = math.sqrt(sum((x-mm)**2 for x in xs)/(len(xs)-1))
        return mm/s2*math.sqrt(12) if s2 else 0
    return dict(sh=sh, h1=sh_(rp[:half]), h2=sh_(rp[half:]), cagr=nav**(1/yrs)-1,
                mdd=mdd, beta=beta, alpha=alpha, cr=nav)

def report(label, rows, turn):
    st = stats(rows)
    print(f"{label:<28} {st['sh']:>6.2f} {st['h1']:>5.2f}/{st['h2']:<5.2f} {st['cagr']:>6.1%} {st['mdd']:>6.1%} {st['alpha']:>+6.1%} {st['cr']:>6.2f} {turn:>5.1%}")

print(f"{'variant':<28} {'Sharpe':>6} {'H1/H2':>11} {'CAGR':>6} {'MaxDD':>6} {'alpha':>6} {'Rs1Cr':>6} {'turn':>5}")

if LEVER == "SANITY":
    r, t = simulate("V21", "NONE"); report("V21 SANITY (want 0.87/27.02)", r, t)
    r, t = simulate("V17", "NONE"); report("V17 SANITY (want 0.79/19.04)", r, t)
else:
    r, t = simulate("V21", "NONE"); report("V21 base (unchanged)", r, t)
    r, t = simulate("V21", LEVER); report(f"V21 + {LEVER}", r, t)
    r, t = simulate("V17", "NONE"); report("V17 base (unchanged)", r, t)
    r, t = simulate("V17", LEVER); report(f"V17 + {LEVER}", r, t)
