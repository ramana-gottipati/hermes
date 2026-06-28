"""PHASE 3 — beta / regime control + placebo on the OOS winner-profile. Isolated, read-only.

Closes the skeptic's last open box from the true-OOS (phase2): the winner-profile SURVIVED
out-of-sample (test 2015-26), but is the edge — especially the beta-neutral BEAR side — genuine
alpha, or just market regime (being short into market dips in a 20-yr bull tape)? And is the
2021-26 bear thinning signal-decay or regime mean-reversion?

Three assumption-light reads on the TEST-window (2015-26) winner-profile trades:
  1. REGIME TELL  — bear medNet CONDITIONED on the market NOT being in the trade's favor
     (signed market return <= 0 over the matched window). If bears still pay there, it isn't
     just riding market falls.
  2. RESIDUAL ALPHA — OLS trade_net ~ a + b*signed_mkt per direction; intercept a (alpha when the
     directional market exposure is flat) with a bootstrap 95% CI. Reported BULL vs BEAR, and BEAR
     by sub-era (2015-20 / 2021-26) — the user's ask.
  3. PLACEBO  — a raw signed H-bar buy/sell-HOLD of the same name (no Wolfe stop/target/zone) over
     the same window. The "placebo gap" = Wolfe medNet - raw-hold medNet; >0 means the Wolfe
     machinery adds over naive directional positioning.

signed_mkt / signed_stk are signed by trade DIRECTION (bull:+ret, bear:-ret), so a positive value =
the trade's directional exposure paid off. Benchmark = Nifty 500 (index_rows; 2012+ covers all of
2015-26). Window H = a FIXED forward horizon from entry (multi-leg re-entries make an exact trade
window ambiguous); primary H=40 (the call/hold window), with H=20/60 as robustness.

Fit/collect REUSE phase2 (same frozen rule, same survivorship-aware inclusive universe). The live
lens, the scanner, and phase1/phase2 are untouched. DESCRIPTIVE-ONLY.

Run:  cd /opt/hermes && python3 research/wolfe_waves/phase3_betacontrol.py
"""
import os
import sys
import random
import bisect

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

import phase1_tradesim as P1                              # noqa: E402
import phase2_oos as P2                                   # noqa: E402
from src.automation import wolfe                          # noqa: E402
from src.core.db import get_conn                          # noqa: E402

BENCH = "Nifty 500"
HS = [20, 40, 60]
H_PRIMARY = 40
BOOT = 10000
SEED = 42
SUBERAS = P2.SUBERAS


def _med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def _fmt(x):
    return "n/a" if x is None else "%+.2f" % x


def ols(xs, ys):
    """pure-stdlib OLS slope+intercept."""
    n = len(xs)
    if n < 3:
        return (None, None)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return (my, 0.0)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return (my - b * mx, b)


def boot_alpha_ci(xs, ys):
    n = len(xs)
    if n < 8:
        return (None, None)
    rnd = random.Random(SEED)
    al = []
    for _ in range(BOOT):
        idx = [rnd.randrange(n) for _ in range(n)]
        a, _b = ols([xs[i] for i in idx], [ys[i] for i in idx])
        if a is not None:
            al.append(a)
    al.sort()
    return (al[int(0.025 * len(al))], al[int(0.975 * len(al))])


def fwd_ret(closes, i, h):
    """signed-unaware forward return from bar i over h bars (bounded at series end)."""
    if i is None or i < 0 or i >= len(closes) or closes[i] in (None, 0):
        return None
    j = min(i + h, len(closes) - 1)
    if closes[j] in (None, 0):
        return None
    return (closes[j] - closes[i]) / closes[i]


def run():
    with get_conn() as conn:
        names = P1.inclusive(conn)
        print("# PHASE 3 — beta/regime control + placebo   (universe: inclusive %d, survivorship-aware)" % len(names))
        # benchmark date -> position
        bs = wolfe.index_series(conn, BENCH)
        if not bs:
            print("** no benchmark series for %s **" % BENCH)
            return
        bdates, _bo, _bh, _bl, bcloses = bs
        print("benchmark: %s  %s..%s (%d bars)" % (BENCH, bdates[0], bdates[-1], len(bdates)))

        rows = P2.collect(conn, names)
        fit_rows = [r for r in rows if P2.FIT[0] <= r["year"] <= P2.FIT[1]]
        thr = P2.fit_profile(fit_rows, "D")
        test_win = [r for r in rows if P2.TEST[0] <= r["year"] <= P2.TEST[1] and P2.passes(r, thr, "D")]

        # attach matched-window stock & market returns (signed by trade direction)
        cache = {}
        attached = []
        for r in test_win:
            sym = r["sym"]
            if sym not in cache:
                cache[sym] = wolfe.stock_series(conn, sym)
            s = cache[sym]
            if not s:
                continue
            sdates, _o, _h, _l, scloses = s
            et = r["entry_t"]
            if et is None or et >= len(sdates):
                continue
            edate = sdates[et]
            bi = bisect.bisect_right(bdates, edate) - 1     # benchmark bar at/just before entry date
            if bi < 0:
                continue
            bull = r["dir"] == "BULL"
            r["net_pct"] = 100 * P1._net(r)
            ok = True
            for h in HS:
                sr = fwd_ret(scloses, et, h)
                mr = fwd_ret(bcloses, bi, h)
                if sr is None or mr is None:
                    ok = False
                    break
                r["sgn_stk_%d" % h] = 100 * (sr if bull else -sr)
                r["sgn_mkt_%d" % h] = 100 * (mr if bull else -mr)
            if ok:
                attached.append(r)
        print("test winner-profile trades with full %d/%d/%d-bar windows: %d\n" % (HS[0], HS[1], HS[2], len(attached)))

        _report(attached, H_PRIMARY)
        _robustness(attached)


def _block(pop, h, label):
    if not pop:
        print("  %-26s n=    0  (none)" % label)
        return
    net = [r["net_pct"] for r in pop]
    mkt = [r["sgn_mkt_%d" % h] for r in pop]
    stk = [r["sgn_stk_%d" % h] for r in pop]
    a, b = ols(mkt, net)
    aci = boot_alpha_ci(mkt, net)
    # regime tell: trade medNet when the market was NOT in the trade's favor (signed mkt <= 0)
    adverse = [r["net_pct"] for r in pop if r["sgn_mkt_%d" % h] <= 0]
    gap = _med(net) - _med(stk)
    print("  %-26s n=%5d  medNet %+6.2f%%  | signedMkt med %+6.2f%%  | alpha %s CI[%s,%s] beta %+.2f"
          " | medNet|mkt<=0 %s (n=%d)  | placebo-gap %+6.2f%%"
          % (label, len(pop), _med(net), _med(mkt),
             _fmt(a), _fmt(aci[0]), _fmt(aci[1]), (b if b is not None else 0.0),
             ("%+.2f%%" % _med(adverse)) if adverse else "n/a", len(adverse), gap))


def _report(rows, h):
    print("=" * 110)
    print("RESIDUAL ALPHA + REGIME TELL + PLACEBO  (H=%d bars, signed by trade direction)" % h)
    print("  alpha = OLS intercept of trade_net on signed market return (= net when directional market exposure is flat)")
    print("  medNet|mkt<=0 = the regime control: trade medNet in windows where the market was NOT in the trade's favor")
    print("  placebo-gap = Wolfe medNet - raw signed buy/sell-hold medNet of the same name (>0 => the machinery adds)\n")
    _block(rows, h, "ALL winners")
    _block([r for r in rows if r["dir"] == "BULL"], h, "BULL winners")
    bear = [r for r in rows if r["dir"] == "BEAR"]
    _block(bear, h, "BEAR winners")
    print("  -- BEAR by sub-era (the decay question: signal or regime?) --")
    for a, b in SUBERAS:
        _block([r for r in bear if a <= r["year"] <= b], h, "  BEAR %d-%d" % (a, b))
    # interpretation flags
    print("\n  READ:")
    ba, _bb = ols([r["sgn_mkt_%d" % h] for r in bear], [r["net_pct"] for r in bear])
    badv = [r["net_pct"] for r in bear if r["sgn_mkt_%d" % h] <= 0]
    aci = boot_alpha_ci([r["sgn_mkt_%d" % h] for r in bear], [r["net_pct"] for r in bear])
    print("   BEAR alpha %s (CI [%s,%s]); BEAR medNet when market NOT favorable %s on n=%d." % (
        _fmt(ba), _fmt(aci[0]), _fmt(aci[1]),
        ("%+.2f%%" % _med(badv)) if badv else "n/a", len(badv)))
    if aci[0] is not None and aci[0] > 0 and badv and _med(badv) > 0:
        print("   => bear edge has residual alpha AND survives adverse-market windows: SIGNAL, not pure regime.")
    elif badv and _med(badv) <= 0:
        print("   => bear edge largely vanishes when the market isn't falling: REGIME-dependent (short-beta).")
    else:
        print("   => mixed / underpowered — alpha CI straddles 0; treat bear neutrality as not-clean.")


def _robustness(rows):
    print("\n" + "=" * 110)
    print("ROBUSTNESS — BEAR residual alpha across horizons:")
    bear = [r for r in rows if r["dir"] == "BEAR"]
    for h in HS:
        a, b = ols([r["sgn_mkt_%d" % h] for r in bear], [r["net_pct"] for r in bear])
        aci = boot_alpha_ci([r["sgn_mkt_%d" % h] for r in bear], [r["net_pct"] for r in bear])
        print("   H=%2d  BEAR alpha %s  CI[%s,%s]  beta %+.2f" % (
            h, _fmt(a), _fmt(aci[0]), _fmt(aci[1]), (b if b is not None else 0.0)))


if __name__ == "__main__":
    run()
