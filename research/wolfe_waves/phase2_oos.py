"""PHASE 2 — TRUE out-of-sample derivation of the Wolfe winner-profile. Isolated, read-only.

Fit the winner-profile thresholds on 2004-2014, FREEZE them, test on UNTOUCHED 2015-2026.
The prior "3-era consistency" used thresholds derived from the WHOLE sample (in-sample); this
is the clean fit-on-A / test-on-untouched-B proof Ramana asked for (2026-06-26).

Panel-locked methodology (Wolfe-quant · skeptic-QA · Ramana-proxy, 2026-06-26):
  FIT       decode-median on 2004-14 ENTERED trades: winners=rode-to-EPA, losers=stopped-out.
            Threshold = winner-side median per feature; MONOTONE single cut (D<=, p1>=, F<=);
            cut directions pre-registered from the mechanism, NEVER data-flipped. 3 DoF, no grid.
  FREEZE    print the fit medians + frozen thresholds (auditable), then never refit.
  TEST      apply the frozen rule to 2015-26 ONLY. Primary metric = median NET (ALL + BEAR);
            secondaries = EPA-reach %, hit %, N. The filter must BEAT the unfiltered OOS baseline.
  THE FILTER tests the DEPLOYED rule = the §B scorer's comp['D'] (EPA-distance from the reversal
            point-5 — a scan-time-knowable setup-quality signal: "is the target reachable"), plus
            p1 (point-1 fractal strength) and F (zone narrowness). All three are structural / fixed
            at point-5, verified entry-knowable EXCEPT one narrow look-ahead inside D: the pierce-
            and-return branch reads post-p5 bars to decide entry=zone-edge vs entry=p5.price.
  LEAK-GATE D_pit = the SAME D recomputed with that return-check forced off (no post-p5 peek). The
            OOS is reported for BOTH D (deployed) and D_pit (leak-neutralized); the edge must hold
            under D_pit too, else it rode the look-ahead. Their agreement is printed.
            (A 3rd 'trade-R' D from the actual fill->EPA is shown as a sensitivity — it measures a
            DIFFERENT thing, post-fill, so it is NOT a valid scan-time selector; reported for honesty.)
  UNIVERSE  PRIMARY = inclusive top-300-by-turnover (delisted/suspended RETAINED -> survivorship-
            aware). Nifty500-CURRENT is survivorship-biased ASYMMETRICALLY across the split and is
            shown ONLY as a labelled sensitivity, never the headline.
  POWER     full verdict needs N_BEAR>=50 in the test bear-winner cell; 30-49 = indicative; <30 = none.
            Bootstrap 95% CI (10k) on the test median-net; CI straddling 0 = not distinguishable.
  SUB-ERA   the bear-side median must hold in BOTH 2015-20 and 2021-26 (one era carrying it = mirage).

PRE-REGISTERED PRIMARY = inclusive universe, deployed-D frozen rule, median-net, the bear cell.
Everything else is a labelled sensitivity. DESCRIPTIVE-ONLY; nothing here makes it a product.

Run:  cd /opt/hermes && python3 research/wolfe_waves/phase2_oos.py [--universe inclusive|nifty500|both]
"""
import os
import sys
import random

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                          # sibling phase1_tradesim
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))  # repo root -> src.*

import phase1_tradesim as P1                              # noqa: E402  (reuse simulate/CFG/_net/universe)
from src.automation import wolfe                          # noqa: E402
from src.core.db import get_conn                          # noqa: E402

FIT = (2004, 2014)
TEST = (2015, 2026)
SUBERAS = [(2015, 2020), (2021, 2026)]
N_MIN_VERDICT = 50      # bear-winner test cell needed for a FULL verdict
N_MIN_INDIC = 30        # below this -> indicative only; below -> no verdict
BOOT = 10000
SEED = 42


def _med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def _bucket(up_pct):
    a = abs(up_pct)
    return 0 if a < 10 else 1 if a < 20 else 2 if a < 35 else 3


def _fmt(x):
    return "n/a" if x is None else "%+.2f" % x


def pit_D(w):
    """The §B-D bucket recomputed WITHOUT the pierce-and-return look-ahead: entry = the zone
    price when point-5 lands inside a confluence band, else point-5's own price (the deep-break
    default). Never consults post-p5 bars. Everything used (points 1-4 zone, p5, the 1-4 EPA line)
    is fixed at the reversal bar. This isolates the only forward-peek in the deployed comp['D']."""
    a, b, c, d = w.p
    p5 = w.p5
    _e12, _e34, zones = wolfe.fib_zones(a.price, b.price, c.price, d.price, direction=w.direction, tol_frac=0.02)
    entry = p5.price
    if zones:
        z = min(zones, key=lambda zz: abs(p5.price - zz["price"]))
        lo, hi = min(z["low"], z["high"]), max(z["low"], z["high"])
        if lo <= p5.price <= hi:
            entry = z["price"]
        # else: deep/pierce -> NO return-check -> entry stays p5.price (look-ahead removed)
    tgt = wolfe.epa_at(w, p5.idx)
    up = abs(tgt - entry) / entry * 100.0 if entry else 0.0
    return _bucket(up)


# --------------------------------------------------------------------------- #
# collect: detect + simulate, keep ENTERED rows + the three D variants        #
# --------------------------------------------------------------------------- #
def collect(conn, names):
    rows = []
    for sym in names:
        s = wolfe.stock_series(conn, sym)
        if not s:
            continue
        _d, _o, highs, lows, closes = s
        n = len(closes)
        waves, _ = wolfe.detect_waves(highs, lows, closes)
        for w in waves:
            if w.state != "CONFIRMED" or not w.p5 or not w.score:
                continue
            r = P1.simulate(w, highs, lows, closes, n, P1.CFG)
            if not (r["entered"] and r["entry_t"] is not None):
                continue
            r["sym"] = sym
            r["year"] = int(_d[r["entry_t"]][:4])
            r["D"] = r["comp"].get("D", 9)                  # DEPLOYED scorer D (the validated rule)
            r["D_pit"] = pit_D(w)                           # same D, look-ahead neutralized
            r["D_tradeR"] = _bucket(100 * r["epa_pot"]) if r["epa_pot"] is not None else 9  # post-fill, sensitivity only
            rows.append(r)
    return rows


# --------------------------------------------------------------------------- #
# fit: decode-median thresholds on the FIT window only (on the deployed D)     #
# --------------------------------------------------------------------------- #
def fit_profile(fit_rows, dfield="D"):
    won = [r for r in fit_rows if r["epa"]]                  # rode to the EPA
    lost = [r for r in fit_rows if r["stopped"] and not r["epa"]]
    dw = [r[dfield] for r in won]
    p1w = [r["comp"].get("p1", 0) for r in won]
    fw = [r["comp"].get("F", 0) for r in won]
    thr = {"D": int(_med(dw)), "p1": int(_med(p1w)), "F": int(_med(fw))}
    dl = [r[dfield] for r in lost]
    p1l = [r["comp"].get("p1", 0) for r in lost]
    fl = [r["comp"].get("F", 0) for r in lost]
    print("  FIT %d-%d  winners(EPA)=%d  losers(stop)=%d   [%s]" % (FIT[0], FIT[1], len(won), len(lost), dfield))
    print("    feature       winnerMed  loserMed   -> FROZEN cut")
    print("    D               %5.1f      %5.1f       D  <= %d" % (_med(dw), _med(dl), thr["D"]))
    print("    p1 (point-1)    %5.1f      %5.1f       p1 >= %d" % (_med(p1w), _med(p1l), thr["p1"]))
    print("    F  (zone)       %5.1f      %5.1f       F  <= %d" % (_med(fw), _med(fl), thr["F"]))
    return thr


def passes(r, thr, dfield="D"):
    return r[dfield] <= thr["D"] and r["comp"].get("p1", 0) >= thr["p1"] and r["comp"].get("F", 0) <= thr["F"]


def _stat(pop):
    n = len(pop)
    if not n:
        return "n=    0  (none)"
    nets = [100 * P1._net(r) for r in pop]
    hit = 100 * sum(1 for r in pop if r["ret"] > 0) / n
    epa = 100 * sum(1 for r in pop if r["epa"]) / n
    return "n=%5d  hit %3.0f%%  EPA %3.0f%%  net %+6.2f%%  medNet %+6.2f%%" % (
        n, hit, epa, sum(nets) / n, _med(nets))


def boot_ci(xs):
    n = len(xs)
    if n < 5:
        return (None, None)
    rnd = random.Random(SEED)
    st = []
    for _ in range(BOOT):
        st.append(_med([xs[rnd.randrange(n)] for _ in range(n)]))
    st.sort()
    return (st[int(0.025 * BOOT)], st[int(0.975 * BOOT)])


# --------------------------------------------------------------------------- #
# evaluate the FROZEN rule on the untouched TEST window                       #
# --------------------------------------------------------------------------- #
def evaluate(rows, thr, label):
    whole = rows
    test = [r for r in rows if TEST[0] <= r["year"] <= TEST[1]]
    print("\n" + "=" * 92)
    print("FROZEN rule (fit on %d-%d): D<=%d & p1>=%d & F<=%d   [%s]" % (
        FIT[0], FIT[1], thr["D"], thr["p1"], thr["F"], label))

    # reconciliation: whole-sample deployed-D winner-profile must == phase1.winner_report
    print("  -- reconciliation (WHOLE sample, deployed D) — should match phase1 winner_report --")
    print("     winner ALL  %s" % _stat([r for r in whole if passes(r, thr, "D")]))

    print("  -- TEST %d-%d (untouched) --" % (TEST[0], TEST[1]))
    base = test
    win = [r for r in test if passes(r, thr, "D")]            # PRIMARY: deployed D
    win_pit = [r for r in test if passes(r, thr, "D_pit")]    # leak-neutralized D
    win_tr = [r for r in test if passes(r, thr, "D_tradeR")]  # post-fill trade-R (sensitivity)
    bear = [r for r in win if r["dir"] == "BEAR"]
    print("  unfiltered baseline      ALL  %s" % _stat(base))
    print("  winner (deployed D)      ALL  %s   <- PRIMARY" % _stat(win))
    print("  winner (deployed D)      BULL %s" % _stat([r for r in win if r["dir"] == "BULL"]))
    print("  winner (deployed D)      BEAR %s" % _stat(bear))
    print("  winner (D_pit no-peek)   ALL  %s   <- leak-robustness" % _stat(win_pit))
    print("  winner (D_pit no-peek)   BEAR %s" % _stat([r for r in win_pit if r["dir"] == "BEAR"]))
    print("  winner (trade-R D)       ALL  %s   <- sensitivity (post-fill, not a scan selector)" % _stat(win_tr))

    a_ci, b_ci = boot_ci([100 * P1._net(r) for r in win]), boot_ci([100 * P1._net(r) for r in bear])
    print("    medNet 95%% CI (10k boot)  ALL [%s, %s]   BEAR [%s, %s]" % (
        _fmt(a_ci[0]), _fmt(a_ci[1]), _fmt(b_ci[0]), _fmt(b_ci[1])))
    print("    BEAR by sub-era (each must hold, the one-era-carry test):")
    for a, b in SUBERAS:
        se = [r for r in bear if a <= r["year"] <= b]
        print("       %d-%d  %s" % (a, b, _stat(se)))
    sd, sp = set(id(r) for r in win), set(id(r) for r in win_pit)
    print("    leak-check: deployed-D vs D_pit filter agreement (Jaccard) %.0f%%  (D n=%d, D_pit n=%d)" % (
        100 * len(sd & sp) / max(1, len(sd | sp)), len(win), len(win_pit)))

    return _verdict(base, win, win_pit, bear, b_ci)


def _verdict(base, win, win_pit, bear, bear_ci):
    bm = _med([100 * P1._net(r) for r in base])
    wm = _med([100 * P1._net(r) for r in win])
    pm = _med([100 * P1._net(r) for r in win_pit])
    brm = _med([100 * P1._net(r) for r in bear])
    nbear = len(bear)
    clauses = [
        ("ALL medNet > 0 (deployed D)", wm > 0, "%+.2f%%" % wm),
        ("filter beats unfiltered baseline", wm > bm, "win %+.2f%% vs base %+.2f%%" % (wm, bm)),
        ("BEAR medNet >= 0", brm >= 0, "%+.2f%%" % brm),
        ("survives leak-neutralized D_pit", pm > 0, "D_pit ALL medNet %+.2f%%" % pm),
        ("BEAR power N >= %d" % N_MIN_VERDICT, nbear >= N_MIN_VERDICT, "n=%d" % nbear),
        ("BEAR CI excludes 0", bear_ci[0] is not None and bear_ci[0] > 0, "lo=%s" % _fmt(bear_ci[0])),
    ]
    print("\n  VERDICT clauses:")
    for name, ok, val in clauses:
        print("    [%s] %-36s %s" % ("PASS" if ok else "FAIL", name, val))
    hard = clauses[0][1] and clauses[1][1] and clauses[2][1] and clauses[3][1]
    if nbear < N_MIN_INDIC:
        tag = "NO VERDICT — bear cell underpowered (n=%d < %d)" % (nbear, N_MIN_INDIC)
    elif hard and nbear >= N_MIN_VERDICT:
        tag = "OOS: SURVIVED" + ("" if clauses[5][1] else "  (point estimate; bear CI straddles 0)")
    elif hard:
        tag = "OOS: INDICATIVE (point estimates hold; bear cell %d in [%d,%d))" % (nbear, N_MIN_INDIC, N_MIN_VERDICT)
    else:
        fails = [c[0] for c in clauses[:4] if not c[1]]
        tag = "OOS: IN-SAMPLE-ONLY  (failed: %s)" % "; ".join(fails)
    print("\n  >>> %s <<<" % tag)
    return tag


def run_oos(universe_name):
    with get_conn() as conn:
        names = P1.nifty500(conn) if universe_name == "nifty500" else P1.inclusive(conn)
        prim = "PRIMARY (survivorship-aware)" if universe_name == "inclusive" \
            else "SENSITIVITY (survivorship-biased, current-membership only)"
        print("\n" + "#" * 92)
        print("# UNIVERSE: %s  (%d names)   %s" % (universe_name, len(names), prim))
        print("#" * 92)
        rows = collect(conn, names)
        fit_rows = [r for r in rows if FIT[0] <= r["year"] <= FIT[1]]
        test_rows = [r for r in rows if TEST[0] <= r["year"] <= TEST[1]]
        print("entered setups: %d total  |  FIT %d-%d: %d  |  TEST %d-%d: %d" % (
            len(rows), FIT[0], FIT[1], len(fit_rows), TEST[0], TEST[1], len(test_rows)))
        if len(fit_rows) < N_MIN_INDIC:
            print("** fit window too thin (%d) — cannot derive **" % len(fit_rows))
            return None
        thr = fit_profile(fit_rows, "D")
        return evaluate(rows, thr, universe_name)


if __name__ == "__main__":
    uni = "inclusive"
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--universe" and i + 1 < len(args):
            uni = args[i + 1]
    if uni == "both":
        run_oos("inclusive")     # PRIMARY first (pre-registered headline)
        run_oos("nifty500")      # labelled sensitivity
    else:
        run_oos(uni)
