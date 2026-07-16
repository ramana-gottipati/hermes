"""SECTOR LAYER (Ramana, 2026-07-16): "consider using [the 8%] as a sector-level stop-loss... would
you also factor in a crossover of the 50-EMA of the RS... if RS crosses that average from below, it
can serve as an entry point."

Reading, stated explicitly (correct me if wrong): ENTRY = the sector's RS LINE (sector/Nifty 500)
crosses ABOVE its own 50-day EMA (was below, now above) -- a fresh cross, not a static level.
Two EXIT rules compared:
  EXIT-A ("8% as a STOP", his framing): once held, drop the sector if its 6m RS excess vs Nifty 500
          falls below +8% -- i.e. +8% moves from an ENTRY gate (this morning's V24 rule) to an EXIT
          trigger.
  EXIT-B (symmetric control): once held, drop the sector when its RS line crosses back BELOW its own
          50-EMA -- the natural trend-following partner to the entry rule, tested as a comparison.

Distinct from the earlier "RS > 50DMA" test (ledger 15Q, `rs_50dma.py`): that used a 50-day SIMPLE
average (SMA) and only entry-side variants. This uses a true EMA (alpha = 2/(50+1), weights recent
days more) and ADDS the exit-rule question. Not directly comparable to 15Q's numbers.

Same forward-return decomposition method as 15Q: cheap, index-only (index_rows is adjusted, the
corporate-action bug never touched it), reports mean / sd / geometric per gate.
"""
import sqlite3, sys, math
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
EMA_N, LB, FWD, STOP_LVL = 50, 126, 63, 0.08

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
iclose = defaultdict(dict)
for nm, d, c in conn.execute("""SELECT index_name, trade_date, close_value FROM index_rows
    WHERE index_name IN (%s) AND close_value>0""" % ",".join("?"*(len(SECTORS)+1)), SECTORS+[BENCH]):
    iclose[nm][d] = c
conn.close()

cal = sorted(iclose[BENCH])
ci = {d: i for i, d in enumerate(cal)}

rs_line, rs_ema = {}, {}
alpha = 2.0 / (EMA_N + 1)
for nm in SECTORS:
    line = [ (iclose[nm].get(d)/iclose[BENCH][d]) if iclose[nm].get(d) else None for d in cal ]
    rs_line[nm] = line
    ema, e, warm = [], None, []
    for x in line:
        if x is None:
            ema.append(e); continue
        if e is None:
            warm.append(x)
            if len(warm) >= EMA_N:
                e = sum(warm) / len(warm)          # seed with an SMA
            ema.append(e); continue
        e = alpha * x + (1 - alpha) * e
        ema.append(e)
    rs_ema[nm] = ema

rebal = [d for i, d in enumerate(cal) if i >= max(EMA_N * 3, LB) and i + FWD < len(cal)
         and d[5:7] in ("01", "04", "07", "10") and (i == 0 or cal[i-1][5:7] != d[5:7])]
print(f"[data] {len(rebal)} quarterly dates {rebal[0]} -> {rebal[-1]}", file=sys.stderr)


def crossed_up(nm, i, within=20):
    l, e = rs_line[nm], rs_ema[nm]
    if l[i] is None or e[i] is None or l[i] <= e[i]:
        return False
    return any(l[j] is not None and e[j] is not None and l[j] <= e[j]
               for j in range(max(0, i - within), i))


def excess6m(nm, i):
    if i - LB < 0: return None
    a, b = iclose[nm].get(cal[i-LB]), iclose[nm].get(cal[i])
    ba, bb = iclose[BENCH].get(cal[i-LB]), iclose[BENCH].get(cal[i])
    if not (a and b and ba and bb): return None
    return (b/a - 1.0) - (bb/ba - 1.0)


def simulate(exit_rule):
    """Actually HOLD sectors quarter to quarter (not just a per-quarter label), so exit rules that
    depend on state-since-entry (EXIT-A) are modeled correctly."""
    held = set()
    nav = bnav = 1.0
    navs, bnavs, nsec = [], [], []
    for k in range(len(rebal) - 1):
        d, dn = rebal[k], rebal[k+1]
        i = ci[d]
        # 1. drop by the exit rule
        for nm in list(held):
            if exit_rule == "8pct":
                e = excess6m(nm, i)
                if e is not None and e < STOP_LVL:
                    held.discard(nm)
            else:  # "ema_cross_down"
                l, m = rs_line[nm][i], rs_ema[nm][i]
                if l is not None and m is not None and l < m:
                    held.discard(nm)
        # 2. add by the entry rule (EMA cross-up)
        for nm in SECTORS:
            if nm not in held and crossed_up(nm, i):
                held.add(nm)
        nsec.append(len(held))
        if held:
            w = 1.0 / len(held)
            r = sum(w * ((iclose[nm][dn]/iclose[nm][d] - 1.0) if (iclose[nm].get(d) and iclose[nm].get(dn)) else 0.0)
                    for nm in held)
        else:
            r = 0.0
        nav *= (1 + r)
        bnav *= iclose[BENCH][dn] / iclose[BENCH][d]
        navs.append(nav); bnavs.append(bnav)
    return navs, bnavs, nsec


def stats(navs, bnavs):
    r = [navs[i]/navs[i-1]-1 for i in range(1, len(navs))]
    br = [bnavs[i]/bnavs[i-1]-1 for i in range(1, len(bnavs))]
    n = len(r); y = n / 4.0
    def dd(v):
        pk, mx = v[0], 0.0
        for x in v: pk = max(pk, x); mx = min(mx, x/pk-1)
        return mx
    m, mb = sum(r)/n, sum(br)/n
    vb = sum((x-mb)**2 for x in br)/(n-1)
    cov = sum((r[i]-m)*(br[i]-mb) for i in range(n))/(n-1)
    b = cov/vb if vb else 0.0
    return navs[-1]**(1/y)-1, dd(navs), navs[-1], b, (m-b*mb)*4


def show(tag, exit_rule):
    navs, bnavs, nsec = simulate(exit_rule)
    c, d_, m, b, a = stats(navs, bnavs)
    print("  %-42s CAGR %5.1f%%  MaxDD %6.1f%%  Rs1Cr->%7.2fx  beta %.2f  alpha %+5.1f%%  sect/q %.1f"
          % (tag, c*100, d_*100, m, b, a*100, sum(nsec)/len(nsec)))


print("=" * 108)
print("SECTOR LAYER — ENTRY = RS-line crosses its 50-EMA from below (state HELD, not per-quarter label)")
print("=" * 108)
show("EXIT = 6m RS excess < +8%  (your 'stop-loss' reading)", "8pct")
show("EXIT = RS crosses back below its 50-EMA  (control)", "ema_cross_down")

d0, d1 = rebal[0], rebal[-1]
y = (len(rebal)-1)/4.0
b = iclose[BENCH][d1]/iclose[BENCH][d0]
print("\n  %-42s CAGR %5.1f%%  %27s Rs1Cr->%7.2fx" % ("Nifty 500 (bar, same window)", (b**(1/y)-1)*100, "", b))
