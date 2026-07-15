"""DIAGNOSTIC ONLY — isolates the RSI-of-RS overbought EXIT mechanism on ONE sector
(Nifty India Defence, the strongest real-world trend example, 2022-01-19 -> today) to
answer: how much of a sustained structural trend does the CURRENT fixed 70/80 rule give
up, vs a regime-band rule (ride while RSI-of-RS stays >=45, having crossed above 55; exit
below 45)? Read-only, standalone. Does NOT touch V21, sector_book, or any recorded module.
Uses the EXACT same rsi()/rs_line() math as the recorded strategy for consistency.
"""
import sqlite3, math, sys

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
SEC = "Nifty India Defence"
BENCH = "Nifty 500"

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
close = {SEC: {}, BENCH: {}}
for nm in (SEC, BENCH):
    for d, c in conn.execute("SELECT trade_date, close_value FROM index_rows WHERE index_name=? AND close_value>0", (nm,)):
        close[nm][d] = c
conn.close()

cal = sorted(d for d in close[SEC] if d in close[BENCH])
idx = {d: i for i, d in enumerate(cal)}
# quarterly checkpoints: every 3rd calendar-month-start, matching the live engine's cadence
monthly, seen = [], set()
for d in cal:
    if d[:7] not in seen:
        seen.add(d[:7]); monthly.append(d)
quarters = monthly[::3]

def series(nm, d, win):
    i = idx[d]
    return [close[nm][cal[k]] for k in range(max(0, i-win+1), i+1)]

def rsi(vals, n=14):
    if len(vals) < n+1: return None
    g=l=0.0
    for k in range(len(vals)-n, len(vals)):
        ch = vals[k]-vals[k-1]; g += max(ch,0); l += max(-ch,0)
    ag, al = g/n, l/n
    return 100.0 if al==0 else 100.0-100.0/(1.0+ag/al)

def rs_line(d, win=40):
    i = idx[d]
    return [close[SEC][cal[k]]/close[BENCH][cal[k]] for k in range(max(0,i-win+1), i+1)]

def rsirs(d):
    return rsi(rs_line(d))

def ret(nm, d0, d1):
    return close[nm][d1]/close[nm][d0]-1.0

print(f"Nifty India Defence: {cal[0]} -> {cal[-1]}  ({len(cal)} trading days, {len(quarters)} quarterly checkpoints)")
print(f"{'date':<12} {'RSI-of-RS':>10} {'zone':<8} {'ruleA(70/80)':<14} {'ruleB(45/55 regime)':<20} {'qtr RS-excess'}")

wA_cap = wB_cap = hold_cap = 0.0    # cumulative captured RS-relative return (compounded)
navA, navB, navHold = 1.0, 1.0, 1.0
in_bull = False                       # Rule B's persistent regime state
eventsA = eventsB = 0
prevA_w = prevB_w = None
rows = []
for k in range(len(quarters)-1):
    d, dn = quarters[k], quarters[k+1]
    r = rsirs(d)
    zone = "-" if r is None else ("<45" if r < 45 else "45-55" if r < 55 else "55-70" if r < 70 else "70-80" if r < 80 else "80+")
    # Rule A (current V21 mechanism): stateless, recomputed fresh each quarter
    wA = 1.0 if (r is None or r < 70) else (0.5 if r < 80 else 0.0)
    # Rule B (regime-band): stateful — enter bull on crossing 55, stay until below 45
    if r is not None:
        if not in_bull and r >= 55: in_bull = True
        elif in_bull and r < 45: in_bull = False
    wB = 1.0 if in_bull else 0.0
    rs_excess_q = ret(SEC, d, dn) - ret(BENCH, d, dn)
    navA *= (1 + wA * ret(SEC, d, dn) + (1-wA) * ret(BENCH, d, dn))
    navB *= (1 + wB * ret(SEC, d, dn) + (1-wB) * ret(BENCH, d, dn))
    navHold *= (1 + ret(SEC, d, dn))
    if prevA_w is not None and wA != prevA_w: eventsA += 1
    if prevB_w is not None and wB != prevB_w: eventsB += 1
    prevA_w, prevB_w = wA, wB
    print(f"{d:<12} {('--' if r is None else f'{r:5.1f}'):>10} {zone:<8} {'FULL' if wA==1 else 'HALF' if wA==0.5 else 'exit':<14} {'IN (ride)' if wB==1 else 'out':<20} {rs_excess_q:+.1%}")

print(f"\n=== Over {len(quarters)-1} quarters ===")
print(f"Buy & hold Defence 100% (the ceiling, ignoring risk):      {navHold:.2f}x")
print(f"Rule A — current fixed 70/80 taper:                        {navA:.2f}x   ({eventsA} weight changes)")
print(f"Rule B — regime-band (ride>=45 after crossing 55, else out): {navB:.2f}x   ({eventsB} weight changes)")
print(f"Nifty 500 alone over the same window:                       {navHold/(navHold/1):.2f}x [see below]")
b500 = 1.0
for k in range(len(quarters)-1):
    b500 *= (1 + ret(BENCH, quarters[k], quarters[k+1]))
print(f"(corrected) Nifty 500 buy&hold:                             {b500:.2f}x")
