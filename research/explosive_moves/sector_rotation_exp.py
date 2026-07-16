"""Sector-Rotation — INCREMENTAL EXPERIMENTS on the frozen Champion base (2026-07-15).

Champion base (FROZEN, do not change): quarterly rebalance · 6mo trailing RS vs Nifty500 ·
RSI-green entry gate · 8% hysteresis hold-band · 30% cap · rank-proportional long-only weights ·
0.15%/side cost. Oldest data (dynamic universe from ~2005). Benchmark = consistent price-index Nifty500.

Each of Ramana's levers is a modular weight-adjuster tested ONE AT A TIME vs base (his "add each
individually"). Levers: VOL (volume confirm) · NEW (newcomer boost, taper the exhausted leader) ·
BAL (balanced/flatter weights) · RSPK (taper at own RS-peak) · STDV (taper on excess stdev vs own
history) · STR (taper when stretched from range) · RSIRS (RSI-of-RS overbought → reduce/exit).

Writes a SHEET (out/sector_rotation_sheet.csv = per-rebalance holdings) + prints a compact table.
"""
import sqlite3, math, sys, csv
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/sector_rotation_sheet.csv"
BENCH, NIFTY50 = "Nifty 500", "Nifty 50"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START = "2005-01-03"   # OLDEST usable (5 sectors live w/ 6mo history; rest join dynamically)
LB = 126               # 6mo RS (frozen)
CAP = 0.30

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = defaultdict(dict); vol = defaultdict(dict)
names = SECTORS + [BENCH, NIFTY50]
q = "SELECT index_name,trade_date,close_value,volume FROM index_rows WHERE index_name IN (%s) AND close_value>0" % ",".join("?" * len(names))
for nm, d, c, v in conn.execute(q, names):
    close[nm][d] = c
    if v:
        vol[nm][d] = v
conn.close()

cal = sorted(d for d in close[BENCH] if d >= START)
idx = {d: i for i, d in enumerate(cal)}
rebal = []
seen = set()
for d in cal:
    if d[:7] not in seen:
        seen.add(d[:7]); rebal.append(d)
SPLIT = rebal[len(rebal) // 2]   # median month = walk-forward halves (full window, not 2019)


def ret(nm, d0, d1):
    a, b = close[nm].get(d0), close[nm].get(d1)
    return (b / a - 1.0) if (a and b) else None


def trailing(nm, d, lb=LB):
    i = idx.get(d)
    if i is None or i - lb < 0:
        return None
    d0 = cal[i - lb]
    if d0 in close[nm] and d in close[nm]:
        return close[nm][d] / close[nm][d0] - 1.0
    return None


def _series(nm, d, win):
    i = idx.get(d)
    if i is None:
        return []
    return [close[nm][cal[k]] for k in range(max(0, i - win + 1), i + 1) if cal[k] in close[nm]]


def rsi(vals, n=14):
    if len(vals) < n + 1:
        return None
    g = l = 0.0
    for k in range(len(vals) - n, len(vals)):
        ch = vals[k] - vals[k - 1]; g += max(ch, 0); l += max(-ch, 0)
    ag, al = g / n, l / n
    return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)


def rsi14_price(nm, d):
    return rsi(_series(nm, d, 40))


def _pctile(x, arr):
    if not arr:
        return None
    return sum(1 for a in arr if a <= x) / len(arr)


# ── per-sector overextension reads (for the taper levers) ────────────────────
def rs_line(nm, d, win):
    """the RS RATIO series sector/bench over trailing `win` days (aligned dates)."""
    i = idx.get(d)
    if i is None:
        return []
    out = []
    for k in range(max(0, i - win + 1), i + 1):
        dd = cal[k]
        if dd in close[nm] and dd in close[BENCH]:
            out.append(close[nm][dd] / close[BENCH][dd])
    return out


def rs_peak_pct(nm, d):
    """where today's RS-ratio sits vs its own trailing 756d (1.0 = at all-time-high RS)."""
    s = rs_line(nm, d, 756)
    return _pctile(s[-1], s) if len(s) > 60 else None


def vol_pct(nm, d):
    """realized 63d vol percentile vs own trailing 756d of 63d-vol readings."""
    i = idx.get(d)
    if i is None or i < 130:
        return None
    def rv(j):
        rs_ = []
        for k in range(j - 63 + 1, j + 1):
            a, b = close[nm].get(cal[k - 1]), close[nm].get(cal[k])
            if a and b:
                rs_.append(b / a - 1)
        if len(rs_) < 40:
            return None
        m = sum(rs_) / len(rs_)
        return math.sqrt(sum((x - m) ** 2 for x in rs_) / (len(rs_) - 1))
    cur = rv(i)
    if cur is None:
        return None
    hist = [rv(j) for j in range(max(130, i - 756), i, 21)]
    hist = [h for h in hist if h is not None]
    return _pctile(cur, hist) if hist else None


def stretch_z(nm, d):
    """z-score of price vs its own 200d mean (how far from typical range)."""
    s = _series(nm, d, 200)
    if len(s) < 150:
        return None
    m = sum(s) / len(s)
    sd = math.sqrt(sum((x - m) ** 2 for x in s) / (len(s) - 1))
    return (s[-1] - m) / sd if sd > 0 else 0.0


def rsi_of_rs(nm, d):
    return rsi(rs_line(nm, d, 40))


def vol_trend(nm, d):
    """recent 21d avg volume vs 63d avg (>1 = rising participation). None if no vol data."""
    i = idx.get(d)
    if i is None:
        return None
    v21 = [vol[nm][cal[k]] for k in range(max(0, i - 21), i + 1) if cal[k] in vol[nm]]
    v63 = [vol[nm][cal[k]] for k in range(max(0, i - 63), i + 1) if cal[k] in vol[nm]]
    if len(v21) < 10 or len(v63) < 30:
        return None
    a63 = sum(v63) / len(v63)
    return (sum(v21) / len(v21)) / a63 if a63 > 0 else None


def _taper(pct, thr=0.85, floor=0.35):
    """1.0 below thr; linearly down to `floor` as pct→1.0."""
    if pct is None or pct <= thr:
        return 1.0
    return max(floor, 1.0 - (pct - thr) / (1 - thr) * (1 - floor))


# ── weighting ────────────────────────────────────────────────────────────────
def _rank_weights(d, cap=CAP, balanced=False):
    if not d:
        return {}
    order = sorted(d, key=lambda s: d[s])
    if balanced:
        raw = {s: 1.0 for s in order}                    # equal weight = "balanced"
    else:
        raw = {s: (r + 1) for r, s in enumerate(order)}  # rank 1..N, strongest = N (Champion)
    tot = sum(raw.values()); w = {s: raw[s] / tot for s in raw}
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap + 1e-9}
        if not over:
            break
        exc = sum(w[s] - cap for s in over)
        for s in over:
            w[s] = cap
        und = [s for s in w if w[s] < cap - 1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und:
            w[s] += exc * w[s] / tu
    return w


def build(d, held, comp, tenure):
    """Champion qualification (RS>0 w/ hysteresis + RSI-green gate) then apply enabled levers."""
    band = 0.08
    rs = {}
    for s in SECTORS:
        tr, tb = trailing(s, d), trailing(BENCH, d)
        if tr is not None and tb is not None:
            rs[s] = tr - tb
    longs = {}
    for s, v in rs.items():
        if s in held:
            if v > -band:
                longs[s] = max(v, 1e-6)
        elif v > band:
            longs[s] = v
    # RSI-green gate on NEW entries only (hold existing)
    keep = {}; i = idx[d]; dprev = cal[max(0, i - 21)]
    for s in longs:
        rn, rp = rsi14_price(s, d), rsi14_price(s, dprev)
        if s in held or (rn is not None and rn >= 50 and (rp is None or rn >= rp)):
            keep[s] = longs[s]
    longs = keep
    base = _rank_weights(longs, balanced=("BAL" in comp))
    if not base:
        return {}
    # multiplicative lever adjustments
    adj = dict(base)
    for s in list(adj):
        f = 1.0
        if "VOL" in comp:
            vt = vol_trend(s, d)
            if vt is not None:
                f *= min(1.4, max(0.7, 0.6 + 0.5 * vt))     # rising vol → up to +40%, falling → −30%
        if "NEW" in comp:
            t = tenure.get(s, 0)
            f *= 1.5 if t <= 1 else (1.15 if t <= 3 else 0.75)  # boost newcomers, taper old leaders
        if "RSPK" in comp:
            f *= _taper(rs_peak_pct(s, d))
        if "STDV" in comp:
            f *= _taper(vol_pct(s, d))
        if "STR" in comp:
            z = stretch_z(s, d)
            f *= _taper(_pctile(z, [-2, -1, 0, 1, 1.5, 2, 2.5]) if z is not None else None, thr=0.7)
        if "RSIRS" in comp:
            r = rsi_of_rs(s, d)
            if r is not None:
                if r >= 80:
                    f *= 0.0            # exit fast (overbought RS)
                elif r >= 70:
                    f *= 0.5
        adj[s] = base[s] * f
    tot = sum(adj.values())
    if tot <= 0:
        return base
    w = {s: adj[s] / tot for s in adj}
    return _cap_only(w)


def _cap_only(w, cap=CAP):
    for _ in range(8):
        over = {s: w[s] for s in w if w[s] > cap + 1e-9}
        if not over:
            break
        exc = sum(w[s] - cap for s in over)
        for s in over:
            w[s] = cap
        und = [s for s in w if w[s] < cap - 1e-9]; tu = sum(w[s] for s in und) or 1
        for s in und:
            w[s] += exc * w[s] / tu
    return w


def simulate(comp=frozenset(), cost=0.0015, freq=3, dump=None):
    prev, tenure = {}, defaultdict(int)
    monthly, sheet = [], []
    for k in range(len(rebal) - 1):
        d, dn = rebal[k], rebal[k + 1]
        if k % freq == 0:
            w = build(d, set(prev), comp, tenure)
            for s in list(tenure):
                tenure[s] = tenure[s] + 1 if s in w else 0
            for s in w:
                if s not in tenure:
                    tenure[s] = 1
            if dump is not None:
                sheet.append((d, {s: round(w[s], 4) for s in sorted(w, key=lambda x: -w[x])}))
        else:
            w = prev
        if not w:
            r = ret(BENCH, d, dn) or 0.0
            monthly.append((dn, r, r)); prev = {}; continue
        rp = sum(x * (ret(s, d, dn) or 0.0) for s, x in w.items())
        turn = 0.0
        if k % freq == 0:
            allk = set(w) | set(prev)
            turn = sum(abs(w.get(s, 0) - prev.get(s, 0)) for s in allk)
            rp -= turn * cost
        monthly.append((dn, rp, ret(BENCH, d, dn) or 0.0))
        prev = w
    if dump is not None:
        with open(dump, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["rebalance_date", "sector", "weight"])
            for dt, wd in sheet:
                for s, wv in wd.items():
                    wr.writerow([dt, s, wv])
    return monthly, (sheet[-1] if sheet else None)


def stats(rs):
    n = len(rs)
    m = sum(rs) / n; sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1))
    sh = m / sd * math.sqrt(12) if sd else 0
    nav = peak = 1.0; mdd = 0
    for x in rs:
        nav *= 1 + x; peak = max(peak, nav); mdd = min(mdd, nav / peak - 1)
    return sh, (nav ** (12 / n) - 1), mdd


def ab(rp, rb):
    n = len(rp); mp, mb = sum(rp) / n, sum(rb) / n
    cov = sum((rp[i] - mp) * (rb[i] - mb) for i in range(n)) / (n - 1)
    vb = sum((x - mb) ** 2 for x in rb) / (n - 1)
    beta = cov / vb if vb else 0
    return beta, (mp - beta * mb) * 12


# benchmark
bm = [(rebal[k + 1], ret(BENCH, rebal[k], rebal[k + 1]) or 0, ret(BENCH, rebal[k], rebal[k + 1]) or 0) for k in range(len(rebal) - 1)]
bsh, bcagr, bmdd = stats([x[1] for x in bm])
print(f"WINDOW {rebal[0]}..{rebal[-1]}  n={len(rebal)-1} months  |  BENCHMARK Nifty500(price): Sharpe {bsh:.2f}  CAGR {bcagr:.1%}  MaxDD {bmdd:.1%}\n")

EXPTS = [
    ("V0 Champion (base, FROZEN)", frozenset()),
    ("V1 +VOL (volume confirm)", frozenset({"VOL"})),
    ("V2 +NEW (newcomer boost/leader taper)", frozenset({"NEW"})),
    ("V3 +BAL (balanced/equal weight)", frozenset({"BAL"})),
    ("V4 +RSPK (taper at own RS-peak)", frozenset({"RSPK"})),
    ("V5 +STDV (taper on excess stdev)", frozenset({"STDV"})),
    ("V6 +STR (taper when stretched)", frozenset({"STR"})),
    ("V7 +RSIRS (RSI-of-RS overbought exit)", frozenset({"RSIRS"})),
]
rows = []
last_hold = {}
for label, comp in EXPTS:
    m, hold = simulate(comp, dump=(OUT if comp == frozenset() else None))
    rp, rb = [x[1] for x in m], [x[2] for x in m]
    sh, cagr, mdd = stats(rp)
    dts = [x[0] for x in m]
    h1 = stats([rp[i] for i in range(len(rp)) if dts[i] < SPLIT])[0]
    h2 = stats([rp[i] for i in range(len(rp)) if dts[i] >= SPLIT])[0]
    beta, alpha = ab(rp, rb)
    beat = "YES" if sh > bsh else "no"
    rows.append((label, sh, sh - bsh, alpha, beat, mdd, h1, h2))
    if comp == frozenset():
        last_hold = hold

# combine the individual winners (Sharpe > base)
base_sh = rows[0][1]
winners = [EXPTS[i][1] for i in range(1, len(EXPTS)) if rows[i][1] > base_sh + 0.005]
wnames = [EXPTS[i][0].split()[0] for i in range(1, len(EXPTS)) if rows[i][1] > base_sh + 0.005]
if winners:
    combo = frozenset().union(*winners)
    m, hold = simulate(combo)
    rp, rb = [x[1] for x in m], [x[2] for x in m]
    sh, cagr, mdd = stats(rp); beta, alpha = ab(rp, rb)
    dts = [x[0] for x in m]
    h1 = stats([rp[i] for i in range(len(rp)) if dts[i] < SPLIT])[0]
    h2 = stats([rp[i] for i in range(len(rp)) if dts[i] >= SPLIT])[0]
    rows.append((f"V8 COMBO winners {'+'.join(wnames)}", sh, sh - bsh, alpha, "YES" if sh > bsh else "no", mdd, h1, h2))
# tapers-only cluster (his core profit-booking thesis)
m, _ = simulate(frozenset({"RSPK", "STDV", "STR", "RSIRS"}))
rp, rb = [x[1] for x in m], [x[2] for x in m]
sh, cagr, mdd = stats(rp); beta, alpha = ab(rp, rb)
dts = [x[0] for x in m]
h1 = stats([rp[i] for i in range(len(rp)) if dts[i] < SPLIT])[0]
h2 = stats([rp[i] for i in range(len(rp)) if dts[i] >= SPLIT])[0]
rows.append(("V9 TAPERS-only (RSPK+STDV+STR+RSIRS)", sh, sh - bsh, alpha, "YES" if sh > bsh else "no", mdd, h1, h2))

print(f"{'variant':<42}{'Sharpe':>7}{'Δvsbench':>9}{'alpha':>8}{'beatNifty':>10}{'MaxDD':>8}{'H1':>6}{'H2':>6}")
print("-" * 96)
for r in rows:
    print(f"{r[0]:<42}{r[1]:>7.2f}{r[2]:>+9.2f}{r[3]:>+8.1%}{r[4]:>10}{r[5]:>8.1%}{r[6]:>6.2f}{r[7]:>6.2f}")

print("\n### CURRENT STRONG SECTORS (latest rebalance of the Champion base) — 'participants' ###")
if last_hold:
    dt, wd = last_hold
    print(f"as of {dt}:")
    for s, wv in wd.items():
        print(f"  {s:<28} {wv:>6.1%}")
print(f"\nsheet (per-rebalance holdings) written to {OUT}")
