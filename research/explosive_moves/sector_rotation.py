"""Sector-Rotation Relative-Strength backtest (V1 — sector-INDEX level).

Ramana's spec, made testable (2026-07-15):
  * every sector BEATING Nifty (trailing excess return > 0) is a LONG candidate;
  * weight LONG legs by RS rank (strongest = biggest weight, weakest-that-still-beats = smallest),
    with an over-concentration cap;
  * sectors UNDERPERFORMING Nifty are optional SHORT legs (the F&O leg), weighted by |RS|;
  * enter/hold a sector only when its RSI is "green" (>=50 and rising) — the recovery gate;
  * hold while momentum persists; monthly churn; exit when RS<0 or RSI rolls over;
  * turnover-cost ladder (sector rotation is LOW turnover — the crux vs stock momentum).

Isolates whether SECTOR rotation has any edge before the <=40-stock constituent build (V2).
Pure stdlib; read-only against index_rows. Benchmark = Nifty 500 (ledger hurdle return/vol 0.89).

METRIC BASIS (D142): every ratio here is mean/sd annualised with NO risk-free rate subtracted — a
return/vol ratio, not a Sharpe; it reads high against a textbook Sharpe. The 0.89 hurdle is computed
on the SAME basis, so the verdict is unaffected.
"""
import sqlite3, math, sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
BENCH = "Nifty 500"
NIFTY50 = "Nifty 50"
# tradeable NSE sectoral indices (join dynamically once each has >=lookback history)
SECTORS = ["Nifty Auto", "Nifty Bank", "Nifty Energy", "Nifty FMCG", "Nifty IT",
           "Nifty Pharma", "Nifty Infrastructure", "Nifty Media", "Nifty Metal",
           "Nifty PSU Bank", "Nifty Realty", "Nifty Financial Services",
           "Nifty Private Bank", "Nifty Oil & Gas", "Nifty Consumer Durables",
           "Nifty Healthcare Index"]
START = "2012-02-21"   # 11 sectors live; more join as they list
SPLIT = "2019-01-01"   # walk-forward halves 2012-18 / 2019-26

# ── load daily closes ────────────────────────────────────────────────────────
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
names = SECTORS + [BENCH, NIFTY50]
close = defaultdict(dict)   # name -> {date: close}
q = "SELECT index_name, trade_date, close_value FROM index_rows WHERE index_name IN (%s) AND close_value>0" % (
    ",".join("?" * len(names)))
for nm, d, c in conn.execute(q, names):
    close[nm][d] = c
conn.close()

# trading calendar = dates where the benchmark trades, from START
cal = sorted(d for d in close[BENCH] if d >= START)
idx = {d: i for i, d in enumerate(cal)}

# monthly rebalance dates = first trading day of each (year, month)
rebal = []
seen = set()
for d in cal:
    ym = d[:7]
    if ym not in seen:
        seen.add(ym); rebal.append(d)


def ret(name, d0, d1):
    a = close[name].get(d0); b = close[name].get(d1)
    return (b / a - 1.0) if (a and b) else None


def trailing(name, d, lb):
    """trailing return over `lb` trading days ending at d (needs the sector listed then)."""
    i = idx.get(d)
    if i is None or i - lb < 0:
        return None
    d0 = cal[i - lb]
    if d0 not in close[name] or d not in close[name]:
        return None
    return close[name][d] / close[name][d0] - 1.0


def rsi14(name, d, n=14):
    """Wilder RSI(14) on daily closes ending at d."""
    i = idx.get(d)
    if i is None or i - n < 0:
        return None
    gains = losses = 0.0
    ok = 0
    for k in range(i - n + 1, i + 1):
        c1 = close[name].get(cal[k]); c0 = close[name].get(cal[k - 1])
        if not (c1 and c0):
            return None
        ch = c1 - c0
        gains += max(ch, 0.0); losses += max(-ch, 0.0); ok += 1
    if ok < n:
        return None
    ag, al = gains / n, losses / n
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - 100.0 / (1.0 + rs)


# ── portfolio construction at a rebalance date ───────────────────────────────
def weights(d, lb, use_short, rsi_gate, cap):
    """returns (long_weights dict, short_weights dict) for rebalance date d."""
    rs = {}
    for s in SECTORS:
        tr = trailing(s, d, lb); tb = trailing(BENCH, d, lb)
        if tr is None or tb is None:
            continue
        rs[s] = tr - tb          # excess trailing return vs Nifty 500
    if not rs:
        return {}, {}
    longs = {s: v for s, v in rs.items() if v > 0}
    shorts = {s: v for s, v in rs.items() if v < 0}
    # RSI-green gate on the LONG leg (>=50 and rising vs ~1 month ago)
    if rsi_gate:
        keep = {}
        i = idx[d]; dprev = cal[max(0, i - 21)]
        for s in longs:
            r_now = rsi14(s, d); r_prev = rsi14(s, dprev)
            if r_now is not None and r_now >= 50 and (r_prev is None or r_now >= r_prev):
                keep[s] = longs[s]
        longs = keep
    # LONG weights: rank-proportional (strongest highest), capped, renormalized
    lw = _rank_weights(longs, cap)
    sw = {}
    if use_short and shorts:
        # short weight proportional to |RS| (weakest = biggest short), capped
        sw = _rank_weights({s: -v for s, v in shorts.items()}, cap)
    return lw, sw


def _rank_weights(d, cap):
    """rank-proportional weights (biggest value -> rank N), capped at `cap`, renormalized."""
    if not d:
        return {}
    order = sorted(d, key=lambda s: d[s])   # ascending; strongest last
    raw = {s: (r + 1) for r, s in enumerate(order)}   # rank 1..N, strongest = N
    tot = sum(raw.values())
    w = {s: raw[s] / tot for s in raw}
    # cap + redistribute (one pass is enough for our N<=16, small caps)
    for _ in range(6):
        over = {s: w[s] for s in w if w[s] > cap + 1e-9}
        if not over:
            break
        excess = sum(w[s] - cap for s in over)
        for s in over:
            w[s] = cap
        under = [s for s in w if w[s] < cap - 1e-9]
        tot_u = sum(w[s] for s in under) or 1.0
        for s in under:
            w[s] += excess * w[s] / tot_u
    return w


# hysteresis: a HELD sector stays long until RS < -band; a NEW sector enters only if RS > +band
def weights_hyst(d, lb, rsi_gate, cap, held, band):
    rs = {}
    for s in SECTORS:
        tr = trailing(s, d, lb); tb = trailing(BENCH, d, lb)
        if tr is not None and tb is not None:
            rs[s] = tr - tb
    longs = {}
    for s, v in rs.items():
        if s in held:                      # keep unless it clearly breaks
            if v > -band:
                longs[s] = max(v, 1e-6)
        else:                              # enter only on a clear lead
            if v > band:
                longs[s] = v
    if rsi_gate:
        keep = {}; i = idx[d]; dprev = cal[max(0, i - 21)]
        for s in longs:
            r_now = rsi14(s, d); r_prev = rsi14(s, dprev)
            gate_ok = r_now is not None and r_now >= 50 and (r_prev is None or r_now >= r_prev)
            if s in held or gate_ok:        # gate only NEW entries; hold existing while RS ok
                keep[s] = longs[s]
        longs = keep
    return _rank_weights(longs, cap)


# ── simulate ─────────────────────────────────────────────────────────────────
def simulate(lb=126, use_short=False, rsi_gate=True, cap=0.30,
             short_gross=0.30, cost_side=0.0015, freq=1, band=0.0):
    """Monthly NAV. Rebalance every `freq` months; `band`>0 = hysteresis (low churn).
    Long leg fully invested (net ~1.0); optional short leg `short_gross`."""
    prev_lw, prev_sw = {}, {}
    monthly = []
    for k in range(len(rebal) - 1):
        d, dn = rebal[k], rebal[k + 1]
        is_rebal = (k % freq == 0)
        if is_rebal:
            if band > 0:
                lw = weights_hyst(d, lb, rsi_gate, cap, set(prev_lw), band); sw = {}
            else:
                lw, sw = weights(d, lb, use_short, rsi_gate, cap)
        else:
            lw, sw = prev_lw, prev_sw       # hold (drift ignored — flat weights between rebalances)
        if not lw:
            r = ret(BENCH, d, dn) or 0.0
            monthly.append((dn, r, r, 0.0)); prev_lw, prev_sw = {}, {}; continue
        rl = sum(w * (ret(s, d, dn) or 0.0) for s, w in lw.items())
        rs_short = sum(w * (ret(s, d, dn) or 0.0) for s, w in sw.items()) if sw else 0.0
        port = rl - short_gross * rs_short
        turn = 0.0
        if is_rebal:
            allk = set(lw) | set(prev_lw) | set(sw) | set(prev_sw)
            for s in allk:
                turn += abs(lw.get(s, 0.0) - prev_lw.get(s, 0.0))
                turn += short_gross * abs(sw.get(s, 0.0) - prev_sw.get(s, 0.0))
            port -= turn * cost_side
        monthly.append((dn, port, ret(BENCH, d, dn) or 0.0, turn))
        prev_lw, prev_sw = lw, sw
    return monthly


# ── metrics ──────────────────────────────────────────────────────────────────
def _stats(rs):
    n = len(rs)
    if n < 6:
        return None
    m = sum(rs) / n
    var = sum((x - m) ** 2 for x in rs) / (n - 1)
    sd = math.sqrt(var)
    retvol = (m / sd) * math.sqrt(12) if sd > 0 else 0.0
    nav = 1.0
    peak = 1.0; mdd = 0.0
    for x in rs:
        nav *= (1 + x); peak = max(peak, nav); mdd = min(mdd, nav / peak - 1)
    yrs = n / 12.0
    cagr = nav ** (1 / yrs) - 1 if yrs > 0 else 0.0
    return dict(n=n, retvol=retvol, cagr=cagr, mdd=mdd, mean=m, sd=sd)


def _alpha_beta(rp, rb):
    n = len(rp)
    mp, mb = sum(rp) / n, sum(rb) / n
    cov = sum((rp[i] - mp) * (rb[i] - mb) for i in range(n)) / (n - 1)
    varb = sum((x - mb) ** 2 for x in rb) / (n - 1)
    beta = cov / varb if varb > 0 else 0.0
    alpha_m = mp - beta * mb
    return beta, alpha_m * 12    # annualized alpha


def report(label, monthly):
    rp = [x[1] for x in monthly]; rb = [x[2] for x in monthly]
    dts = [x[0] for x in monthly]; turns = [x[3] for x in monthly]
    full = _stats(rp)
    if not full:
        print(f"{label}: too few months"); return
    beta, alpha = _alpha_beta(rp, rb)
    h1 = _stats([rp[i] for i in range(len(rp)) if dts[i] < SPLIT])
    h2 = _stats([rp[i] for i in range(len(rp)) if dts[i] >= SPLIT])
    avg_turn = sum(turns) / len(turns)
    print(f"\n=== {label} ===")
    print(f"  months {full['n']}  |  avg 1-way turnover/mo {avg_turn:.1%}")
    print(f"  ret/vol FULL {full['retvol']:.2f}   (H1 {h1['retvol']:.2f} / H2 {h2['retvol']:.2f})")
    print(f"  CAGR {full['cagr']:.1%}   MaxDD {full['mdd']:.1%}   beta {beta:.2f}")
    print(f"  ALPHA vs Nifty500 (ann.) {alpha:+.2%}")
    print(f"  ret/vol DELTA vs 0.89 hurdle: {full['retvol']-0.89:+.2f}   "
          f"beats both halves? {'YES' if h1['retvol']>0.89 and h2['retvol']>0.89 else 'NO'}")


# benchmark self-check (must land ~0.89 to validate the method vs the ledger)
bench_monthly = [(rebal[k + 1], ret(BENCH, rebal[k], rebal[k + 1]) or 0.0,
                  ret(BENCH, rebal[k], rebal[k + 1]) or 0.0, 0.0) for k in range(len(rebal) - 1)]
n50_monthly = [(rebal[k + 1], ret(NIFTY50, rebal[k], rebal[k + 1]) or 0.0,
                ret(BENCH, rebal[k], rebal[k + 1]) or 0.0, 0.0) for k in range(len(rebal) - 1)]
print("### METHOD VALIDATION (should match ledger: Nifty500 return/vol ~0.89) ###")
report("Nifty 500 buy&hold (self-check)", bench_monthly)
report("Nifty 50 buy&hold", n50_monthly)

print("\n\n############ SECTOR ROTATION VARIANTS ############")
# primary: long-only, 6mo lookback, RSI gate on, 30% cap, realistic-ish cost
report("LONG-ONLY 6mo-RS, RSI-gate, cap30, cost0.15%", simulate(126, False, True, 0.30, 0, 0.0015))
report("LONG-ONLY 6mo-RS, RSI-gate, cap30, ZERO cost", simulate(126, False, True, 0.30, 0, 0.0))
report("LONG-ONLY 6mo-RS, RSI-gate, cap30, cost0.50%", simulate(126, False, True, 0.30, 0, 0.0050))
report("LONG-ONLY 3mo-RS, RSI-gate, cap30, cost0.15%", simulate(63, False, True, 0.30, 0, 0.0015))
report("LONG-ONLY 6mo-RS, NO gate,  cap30, cost0.15%", simulate(126, False, False, 0.30, 0, 0.0015))
report("LONG-ONLY 12mo-RS, RSI-gate, cap30, cost0.15%", simulate(252, False, True, 0.30, 0, 0.0015))
# short leg (the F&O leg the ledger warns fights drift)
report("LONG-SHORT 6mo-RS, +30% short, RSI-gate, cost0.15%", simulate(126, True, True, 0.30, 0.30, 0.0015))
report("LONG-SHORT 6mo-RS, +50% short, RSI-gate, cost0.15%", simulate(126, True, True, 0.30, 0.50, 0.0015))

print("\n\n############ LOW-TURNOVER (hysteresis + slower cadence — his 'stay while momentum persists') ############")
# hold-band hysteresis (a held sector stays until RS<-band; new enters only if RS>+band)
report("HYST band4% 6mo, monthly, RSI-gate, cost0.15%", simulate(126, False, True, 0.30, 0, 0.0015, freq=1, band=0.04))
report("HYST band8% 6mo, monthly, RSI-gate, cost0.15%", simulate(126, False, True, 0.30, 0, 0.0015, freq=1, band=0.08))
report("HYST band8% 6mo, monthly, RSI-gate, ZERO cost", simulate(126, False, True, 0.30, 0, 0.0,   freq=1, band=0.08))
# quarterly cadence (LOWVOL_MOM lesson — the one net-survivor was low-turnover quarterly)
report("QUARTERLY 6mo-RS, RSI-gate, cap30, cost0.15%", simulate(126, False, True, 0.30, 0, 0.0015, freq=3, band=0.0))
report("QUARTERLY + HYST band8% 6mo, RSI-gate, cost0.15%", simulate(126, False, True, 0.30, 0, 0.0015, freq=3, band=0.08))
report("QUARTERLY + HYST band8% 6mo, RSI-gate, ZERO cost", simulate(126, False, True, 0.30, 0, 0.0,   freq=3, band=0.08))
report("QUARTERLY + HYST band8% 12mo, RSI-gate, cost0.15%", simulate(252, False, True, 0.30, 0, 0.0015, freq=3, band=0.08))
