"""GET THE CORRECT NUMBERS. Fix the 3 confirmed defects, then settle the +7pp control gap.

Ramana: "how to get the correct numbers then?"

The last run printed TOP40 inverse-vol = Rs 121 Cr / MaxDD -51.5%. Untrustworthy because:
  D1 STALE-PRICE VOL (confirmed): a barely-traded stock shows fake-low vol -> inverse-vol hands it
     a huge weight. Proof: the inverse-vol CONTROL collapsed to 1.71x at beta 0.38.
  D2 DEAD NAMES GET 0% (confirmed): a delisted position was credited a flat zero, not its loss.
  D3 LIQUIDITY LOOK-AHEAD (confirmed): adv[symbol][ym] averages the WHOLE month of the buy date,
     including days AFTER it.
  A? THE +7pp GAP (unexplained): no-selection equal-weight = 19.7% vs the index's 12.7%. But
     Nifty Midcap 50 buy-and-hold = 9.7%, so a mid-cap tilt should make it WORSE, not better.

THE TWO CONTROLS THAT SETTLE IT:
  SIZE-WEIGHTED universe (turnover as the size proxy) -> should land near Nifty 500's 12.7%.
     If it does, the ADJUSTMENT IS SANE and the 7pp is a weighting effect.
     If it prints ~19%, the adjustment inflates EVERYTHING and every number today dies.
  EQUAL-WEIGHT BUY-AND-HOLD (no rebalance) vs EQUAL-WEIGHT REBALANCED -> the gap IS the
     rebalancing premium (volatility harvesting), real or absent.
"""
import sqlite3, sys, math
from collections import defaultdict
sys.path.insert(0, "/opt/hermes/research/explosive_moves")
from adjust import load_factors, adjust_all

DB      = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH   = "Nifty 500"
LB, VOLWIN, ADV_BAR, COST = 126, 126, 5e7, 0.0015
MIN_MOVE_FRAC = 0.60      # D1 FIX: >=60% of days in the vol window must have a real price change
DEAD_VAL      = -0.50     # D2 FIX: a vanished position realises this (0.47%/qtr of names)

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.execute("PRAGMA temp_store=MEMORY")
bench = dict(conn.execute(
    "SELECT trade_date, close_value FROM index_rows WHERE index_name=? AND close_value>0", (BENCH,)))
sclose = defaultdict(dict)
for s, d, c in conn.execute("""SELECT symbol, trade_date, close FROM bhavcopy_rows
    WHERE series IN ('EQ','BE','BZ') AND close>0"""):
    sclose[s][d] = c
adv = defaultdict(dict)
for s, ym, a, n in conn.execute("""SELECT symbol, substr(trade_date,1,7), avg(value), count(*)
    FROM bhavcopy_rows WHERE series IN ('EQ','BE','BZ') GROUP BY 1,2"""):
    if n >= 15 and a:
        adv[s][ym] = a
fac = load_factors(conn); nadj = adjust_all(sclose, fac); conn.close()
print(f"[adjust] {nadj:,} symbols adjusted", file=sys.stderr)

cal = sorted(bench); ci = {d: i for i, d in enumerate(cal)}
rebal = [d for i, d in enumerate(cal) if i >= max(LB, VOLWIN)
         and d[5:7] in ("01","04","07","10") and (i == 0 or cal[i-1][5:7] != d[5:7])]


def px_near(s_, d, back=10):
    """D2 PROPER FIX: a MISSING price is NOT a delisting. Look back up to `back` trading days
    for this stock's last real print. Only if it has genuinely stopped trading is it dead."""
    cl = sclose[s_]
    i = ci.get(d)
    if i is None:
        return None
    for j in range(i, max(-1, i-back), -1):
        v = cl.get(cal[j])
        if v:
            return v
    return None


def is_dead(s_, d, fwd=60):
    """genuinely gone: no print at all in the NEXT `fwd` trading days"""
    i = ci.get(d)
    if i is None:
        return True
    cl = sclose[s_]
    for j in range(i, min(len(cal), i+fwd)):
        if cl.get(cal[j]):
            return False
    return True


def prev_ym(d):
    """D3 FIX: liquidity from the PRIOR month -- never the month we are buying in."""
    y, m = int(d[:4]), int(d[5:7])
    m -= 1
    if m == 0: y, m = y-1, 12
    return f"{y:04d}-{m:02d}"


_vol = {}
def vol_at(s, d):
    """D1 FIX: reject stale series. A stock must actually MOVE on >=MIN_MOVE_FRAC of days,
    otherwise its low measured vol is an artefact of not trading and inverse-vol would
    overweight junk."""
    k = (s, d)
    if k in _vol: return _vol[k]
    i = ci[d]; cl = sclose[s]; r = []
    for j in range(max(0, i-VOLWIN)+1, i+1):
        a, b = cl.get(cal[j-1]), cl.get(cal[j])
        if a and b: r.append(b/a - 1.0)
    if len(r) < 60:
        _vol[k] = None; return None
    moved = sum(1 for x in r if abs(x) > 1e-6)
    if moved / len(r) < MIN_MOVE_FRAC:          # <- the stale-price rejection
        _vol[k] = None; return None
    m = sum(r)/len(r)
    v = math.sqrt(sum((x-m)**2 for x in r)/(len(r)-1))
    _vol[k] = v if v > 1e-5 else None
    return _vol[k]


def universe(d):
    """every liquid stock AT d, with its RS excess and prior-month turnover"""
    i = ci[d]; d0 = cal[i-LB]
    br = bench[d]/bench[d0] - 1.0
    pm = prev_ym(d)
    out = []
    for s, cl in sclose.items():
        a, b = cl.get(d0), cl.get(d)
        if not (a and b): continue
        a_ = adv.get(s, {}).get(pm, 0)          # D3: prior month
        if a_ < ADV_BAR: continue
        out.append(((b/a - 1.0) - br, s, a_))
    out.sort(reverse=True)
    return out


def weights(sel, d, scheme, advmap):
    if not sel: return {}
    if scheme == "EW":
        w = 1.0/len(sel); return {s: w for s in sel}
    if scheme == "SIZE":                          # turnover as the size proxy
        t = sum(advmap[s] for s in sel)
        return {s: advmap[s]/t for s in sel}
    iv = {}
    for s in sel:
        v = vol_at(s, d)
        if v: iv[s] = 1.0/v
    if not iv: return {}
    t = sum(iv.values())
    return {s: x/t for s, x in iv.items()}


def run(mode, scheme, topn=40, rebalance=True, start="2005-01-01"):
    rb = [d for d in rebal if d >= start]
    nav = bnav = 1.0; navs, bnavs = [], []
    held = {}
    for k in range(len(rb)-1):
        d, dn = rb[k], rb[k+1]
        do_rb = rebalance or not held
        if do_rb:
            u = universe(d)
            advmap = {s: a for _, s, a in u}
            if mode == "ALL":   sel = [s for _, s, _ in u]
            elif mode == "TOP": sel = [s for e, s, _ in u[:topn] if e > 0]
            else:
                n = len(u); sel = [s for e, s, _ in u[int(n*0.20):int(n*0.50)] if e > 0][:topn]
            w = weights(sel, d, scheme, advmap)
            if w:
                turn = sum(abs(w.get(s,0)-held.get(s,0)) for s in set(w)|set(held))
                nav *= (1 - COST*turn); held = w
        r = 0.0
        drift = {}
        for s, x in held.items():
            a, b = px_near(s, d), px_near(s, dn)
            if a and b:
                g = b/a - 1.0
                r += x*g; drift[s] = x*(1+g)
            elif a and is_dead(s, dn):
                r += x*DEAD_VAL                   # genuinely delisted -> real loss
            else:
                drift[s] = x                      # no print but alive -> carry, do not punish
        nav *= (1 + r)
        if not rebalance and drift:               # buy-and-hold: let weights drift
            t = sum(drift.values())
            held = {s: v/t for s, v in drift.items()}
        bnav *= bench[dn]/bench[d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs


def stats(navs, bnavs):
    r  = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); yrs = n/4.0
    def _dd(nv):
        pk, mx = nv[0], 0.0
        for v in nv:
            pk = max(pk, v); mx = min(mx, v/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((v-mb)**2 for v in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    beta = cov/vb if vb else 0.0
    return (navs[-1]**(1/yrs)-1, _dd(navs), navs[-1], beta, (m-beta*mb)*4,
            bnavs[-1]**(1/yrs)-1, _dd(bnavs), bnavs[-1])


def show(tag, mode, scheme, topn=40, rebalance=True, start="2005-01-01"):
    navs, bnavs = run(mode, scheme, topn, rebalance, start)
    c, dd, m, b, a, bc, bdd, bm = stats(navs, bnavs)
    print(f"  {tag:<40} CAGR {c*100:5.1f}%  MaxDD {dd*100:6.1f}%  Rs1Cr->{m:7.2f}x  "
          f"beta {b:.2f}  alpha {a*100:+5.1f}%")
    return c, m


print("="*118)
print("CORRECTED RUN — D1 stale-vol rejected | D2 dead names at -50% | D3 liquidity from the PRIOR month")
print("="*118)
navs, bnavs = run("ALL", "EW")
_, _, _, _, _, bc, bdd, bm = stats(navs, bnavs)
print(f"  {'NIFTY 500 (the benchmark)':<40} CAGR {bc*100:5.1f}%  MaxDD {bdd*100:6.1f}%  Rs1Cr->{bm:7.2f}x")

print("\n### THE DECIDING CONTROL — is the adjustment sane?")
print("### size-weighting the same universe MUST land near the index. If it prints ~19%, everything dies.")
cs, _ = show("SIZE-weighted universe, no selection", "ALL", "SIZE")

print("\n### the rebalancing premium — how much of the gap is just equal-weight + rebalance?")
ce, _ = show("EW universe, REBALANCED quarterly", "ALL", "EW")
cb, _ = show("EW universe, BUY-AND-HOLD (no rebal)", "ALL", "EW", rebalance=False)
print(f"      -> rebalancing premium = {(ce-cb)*100:+.1f}pp/yr")

print("\n### the books, on the corrected harness")
show("TOP40 equal-weight", "TOP", "EW")
show("TOP40 INVERSE-VOL (stale rejected)", "TOP", "INVVOL")
show("BAND INVERSE-VOL", "BAND", "INVVOL")
print("\n### control INVVOL (was 1.71x -- the D1 canary)")
show("INVVOL universe, no selection", "ALL", "INVVOL")

print("\n" + "="*118)
print("READ IT LIKE THIS:")
print("  SIZE-weighted ~= index  -> adjustment SANE. Anything above it is weighting + selection.")
print("  SELECTION VALUE = TOP40 minus the EW control. THAT is the only number that is about the strategy.")
