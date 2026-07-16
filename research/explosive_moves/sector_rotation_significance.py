"""SIGNIFICANCE PASS for the sector-rotation ladder — closes ledger §2026-07-15h owed item ③
(significance half). Ledger record: docs/strategy-ledger.md § 2026-07-15i.

THE QUESTION nobody asked through four rounds of selection: the ladder's arithmetic reproduces
(§15h), but are the DIFFERENCES between V21 / V24 / V32 distinguishable from noise?

ANSWER: no. V24-vs-V32 is UNMEASURABLE on this window (gap 0.013 vs a 0.148 noise floor — 11x
below it). V24-vs-V21 is method-dependent (0.038 percentile / 0.081 analytic / 0.127 studentized;
the pivotal CI spans zero) and dies under a k=9 selection correction that was MEASURED to be fair
(lever difference-series correlations: median +0.000). Ramana's V24 designation therefore stands
on MECHANISM grounds, correctly labelled a priors call, not an evidence result (§15h/§15i).

READ THE FENCES BEFORE QUOTING ANY NUMBER THIS PRINTS:
  * §2026-07-15h SCOPE FLAW — this ladder selects SECTORS, never STOCKS. Every stat here measures
    the sector-selection HALF of an unfinished brief, priced on instruments that in ~6/16 sectors
    do not exist. No number here may be presented as a complete strategy result.
  * The ratios printed are RETURN/VOL RATIOS, not Sharpe ratios — the engine subtracts no
    risk-free rate (§15i). True excess-of-6.5% Sharpes are ~0.51/0.54/0.54, not 0.875/0.911/0.898.
  * Non-significance != no effect. This design is low-power BY CONSTRUCTION (nested books
    correlated 0.97-0.996; V24 and V21 are identical in 80% of months -> ~9 informative blocks).
    It proves the rungs cannot be told apart on 2005-2026. It does NOT prove V24 is no better.

DESIGN NOTE — why this does not re-implement the engine: it exec's the VALIDATED Round-4 engine
(sector_rotation_exp4.py) above its driver line and calls that module's own simulate(). A
reproduction gate then asserts the §15f/§15g record before any test is trusted; the module exits
non-zero if the engine ever stops reproducing it. Stdlib-only (prod venv has no numpy),
deterministic (seed 20260715).

Usage:  python research/explosive_moves/sector_rotation_significance.py [db_path]
"""
import sys, os, math, random

DB = sys.argv[1] if len(sys.argv) > 1 else "data/hermes.db"
_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE = os.path.join(_HERE, "sector_rotation_exp4.py")

N_DRAWS = 20000
MEAN_BLOCK = 6          # months
SEED = 20260715
K_ROUND4 = 9            # V22..V30 — the batch V24 was selected from (the FLOOR, not the true burden)
RF_ASSUMED = 0.065      # only for the labelling reconciliation below; nothing is computed net of it

# ---- load the validated engine, stopping before exp4's own driver ---------------------
_src = open(_ENGINE, encoding="utf-8").read().splitlines(True)
_anchor = next(i for i, l in enumerate(_src) if l.startswith('print(f"{\'variant\''))
_E = {"__name__": "sector_rotation_engine"}
_argv = sys.argv
sys.argv = ["sector_rotation_exp4", DB, "SANITY"]
exec(compile("".join(_src[:_anchor]), _ENGINE, "exec"), _E)
sys.argv = _argv
simulate, stats = _E["simulate"], _E["stats"]

BOOKS = {
    "V21": ("V21", "NONE"),        # the LIVE default on /dash/sector-rotation
    "V24": ("V21", "V24"),         # + own-percentile RSI-of-RS (the designated carry-forward layer)
    "V32": ("V21", "V24+V22"),     # + adaptive hysteresis band (retired as a distinct candidate, §15i)
}
LEDGER = {"V21": (0.875, 27.02), "V24": (0.911, 30.35), "V32": (0.898, 31.15)}   # §15f/§15g
LEVERS_R4 = ["V22", "V23", "V24", "V25", "V26", "V27", "V28", "V29", "V30"]


# ---- stats primitives ----------------------------------------------------------------
def retvol_m(x):
    """PER-PERIOD return/vol ratio. The JK/Memmel statistic is defined on per-period ratios;
    feeding it annualised ones inflates z ~3.5x (z=4.56 vs 1.747 for V24-V21) and manufactures
    significance. The DIFFERENCE is annualised for display only, after the test."""
    m = sum(x) / len(x)
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
    return m / sd if sd else 0.0


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(len(a)))
    den = math.sqrt(sum((v - ma) ** 2 for v in a) * sum((v - mb) ** 2 for v in b))
    return num / den if den else 0.0


def norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def jk_theta(a, b):
    """Jobson-Korkie (1981) variance of the Sharpe difference, Memmel (2003) correction."""
    s1, s2, rho = retvol_m(a), retvol_m(b), corr(a, b)
    return (1.0 / len(a)) * (2 * (1 - rho) + 0.5 * (s1 ** 2 + s2 ** 2 - 2 * s1 * s2 * rho ** 2))


def jk_test(a, b):
    th = jk_theta(a, b)
    d_ann = (retvol_m(a) - retvol_m(b)) * math.sqrt(12)
    if th <= 0:
        return d_ann, corr(a, b), float("nan"), float("nan"), float("nan")
    se_ann = math.sqrt(th) * math.sqrt(12)
    z = (retvol_m(a) - retvol_m(b)) / math.sqrt(th)
    return d_ann, corr(a, b), se_ann, z, 2 * (1 - norm_cdf(abs(z)))


def block_boot(a, b, draws=N_DRAWS, mean_block=MEAN_BLOCK, seed=SEED):
    """Paired stationary bootstrap (Politis-Romano): geometric block lengths, wrap-around, the two
    books' months resampled JOINTLY so cross- and auto-correlation survive. Returns the annualised
    difference draws and the studentized t draws."""
    rng = random.Random(seed)
    n = len(a)
    p = 1.0 / mean_block
    d_hat = (retvol_m(a) - retvol_m(b)) * math.sqrt(12)
    ds, ts = [], []
    for _ in range(draws):
        ia, ib = [], []
        while len(ia) < n:
            i = rng.randrange(n)
            while True:
                ia.append(a[i]); ib.append(b[i])
                if len(ia) >= n or rng.random() < p:
                    break
                i = (i + 1) % n
        d = (retvol_m(ia) - retvol_m(ib)) * math.sqrt(12)
        ds.append(d)
        th = jk_theta(ia, ib)
        if th > 0:
            ts.append((d - d_hat) / (math.sqrt(th) * math.sqrt(12)))
    ds.sort(); ts.sort()
    return d_hat, ds, ts


def q(xs, p):
    return xs[min(len(xs) - 1, max(0, int(p * len(xs))))]


def sidak(p, k):
    return 1 - (1 - p) ** k


# ---- run the books + the reproduction gate -------------------------------------------
rets, S = {}, {}
for k, (base, lev) in BOOKS.items():
    rows, _turn = simulate(base, lev)
    rets[k] = [x[1] for x in rows]
    S[k] = stats(rows)

print("=" * 84)
print("REPRODUCTION GATE — engine vs ledger §15f/§15g (no test is trusted until this passes)")
print("=" * 84)
ok = True
for k in BOOKS:
    got, want = (S[k]["sh"], S[k]["cr"]), LEDGER[k]
    m = abs(got[0] - want[0]) < 0.006 and abs(got[1] - want[1]) < 0.06
    ok &= m
    print(f"  {k:<4} ret/vol {got[0]:.3f} (ledger {want[0]})  Rs1Cr->{got[1]:6.2f} (ledger {want[1]})"
          f"  halves {S[k]['h1']:.2f}/{S[k]['h2']:.2f}  MaxDD {S[k]['mdd']:+.1%}  "
          f"{'MATCH' if m else '*** MISMATCH ***'}")
if not ok:
    print("\n  GATE FAIL — the engine no longer reproduces the ledger. Every number below is void.")
    sys.exit(1)
n = len(rets["V21"])
print(f"\n  GATE PASS.  n = {n} monthly observations ({n/12:.1f} years)")

# ---- test 1: analytic ----------------------------------------------------------------
PAIRS = [("V24", "V32"), ("V24", "V21"), ("V32", "V21")]
print()
print("=" * 84)
print("TEST 1 — Jobson-Korkie / Memmel difference-of-Sharpe (correlated series)")
print("=" * 84)
print(f"  {'pair':<12} {'dRatio/yr':>10} {'corr':>8} {'z':>8} {'p':>8}  verdict")
print("  " + "-" * 70)
jk = {}
for x, y in PAIRS:
    d, rho, se, z, p = jk_test(rets[x], rets[y])
    jk[(x, y)] = (d, rho, se, z, p)
    print(f"  {x+' - '+y:<12} {d:>+10.3f} {rho:>8.4f} {z:>+8.3f} {p:>8.3f}  "
          f"{'DISTINGUISHABLE' if p < 0.05 else 'NOT distinguishable'}")

# ---- test 2: bootstrap ---------------------------------------------------------------
print()
print("=" * 84)
print(f"TEST 2 — paired stationary block bootstrap ({N_DRAWS:,} draws, mean block {MEAN_BLOCK}m)")
print("=" * 84)
print("  The headline is METHOD-DEPENDENT — that IS the result. Percentile is not defensible for")
print("  a skewed ratio statistic; the studentized p is the one to quote.")
boot_p = {}
for x, y in PAIRS:
    d_hat, ds, ts = block_boot(rets[x], rets[y])
    q025, q975 = q(ds, 0.025), q(ds, 0.975)
    frac_le = sum(1 for v in ds if v <= 0) / len(ds)
    p_pct = 2 * min(frac_le, 1 - frac_le)
    b_lo, b_hi = 2 * d_hat - q975, 2 * d_hat - q025          # basic / pivotal
    se_hat = jk[(x, y)][2]
    t_hat = d_hat / se_hat
    p_stud = sum(1 for t in ts if abs(t) >= abs(t_hat)) / len(ts)
    boot_p[(x, y)] = (p_pct, p_stud)
    mean_d = sum(ds) / len(ds)
    print(f"\n  {x} - {y}:  d_hat {d_hat:+.4f}   SE {se_hat:.4f}   t_hat {t_hat:+.3f}")
    print(f"    centering check: boot mean {mean_d:+.4f} vs d_hat {d_hat:+.4f} "
          f"(offset {mean_d-d_hat:+.4f}) -> {'CENTRED' if abs(mean_d-d_hat) < 0.002 else 'MIS-CENTRED'}")
    print(f"    percentile   CI [{q025:+.4f}, {q975:+.4f}]  p {p_pct:.3f}"
          f"   {'excludes 0' if not (q025 <= 0 <= q975) else 'spans 0'}")
    print(f"    basic/pivot  CI [{b_lo:+.4f}, {b_hi:+.4f}]"
          f"              {'excludes 0' if not (b_lo <= 0 <= b_hi) else 'SPANS 0'}")
    print(f"    STUDENTIZED  p {p_stud:.3f}"
          f"   <- quote this one")

# ---- power ---------------------------------------------------------------------------
print()
print("=" * 84)
print("POWER — what gap COULD be detected? (a null is uninterpretable without this)")
print("=" * 84)
print(f"  {'pair':<12} {'corr':>8} {'SE/yr':>9} {'MDE @80% power':>16} {'observed':>10}  read")
print("  " + "-" * 76)
for x, y in PAIRS:
    d, rho, se, z, p = jk[(x, y)]
    mde = 2.802 * se           # z(0.975)+z(0.80) = 1.96+0.842
    read = "UNMEASURABLE" if abs(d) < mde / 3 else ("under-powered" if abs(d) < mde else "resolvable")
    print(f"  {x+' vs '+y:<12} {rho:>8.4f} {se:>9.4f} {mde:>16.3f} {d:>+10.3f}  {read}")

# ---- effective sample size -----------------------------------------------------------
print()
print("=" * 84)
print("EFFECTIVE SAMPLE — how much information is actually in the window?")
print("=" * 84)
for x, y in PAIRS:
    d = [rets[x][i] - rets[y][i] for i in range(n)]
    same = sum(1 for v in d if abs(v) < 1e-12)
    inf_m = n - same
    print(f"  {x} vs {y}: identical in {same:>3}/{n} months ({same/n:>3.0%}) -> only {inf_m:>3} informative "
          f"months ~= {inf_m/MEAN_BLOCK:>4.0f} blocks; mean |gap| {sum(abs(v) for v in d)/n:.4%}")
print("  At n_eff ~ 10 blocks both the JK normal approximation and the percentile bootstrap have")
print("  poor coverage. The window cannot support the V24-over-V21 claim on ANY method.")

# ---- selection deflation -------------------------------------------------------------
print()
print("=" * 84)
print(f"SELECTION DEFLATION — V24 was the WINNER of a k={K_ROUND4} batch, not a lone hypothesis")
print("=" * 84)
print("  Bonferroni assumes independence and would be UNFAIR if the levers were redundant.")
print("  So measure it: pairwise corr of the nine levers' excess-over-V21 series.\n")
r21 = rets["V21"]
diffs = {}
for lv in LEVERS_R4:
    try:
        rl = [x[1] for x in simulate("V21", lv)[0]]
        dd = [rl[i] - r21[i] for i in range(n)]
        if sum(abs(v) for v in dd) < 1e-9:
            print(f"    note: {lv} is IDENTICAL to V21 on this extract (its indices are likely absent)"
                  f" -> excluded; k measured = {len(LEVERS_R4)-1}")
            continue
        diffs[lv] = dd
    except Exception as ex:
        print(f"    note: {lv} SKIPPED ({type(ex).__name__})")
ks = sorted(diffs)
if ks:
    print("\n        " + " ".join(f"{k:>6}" for k in ks))
    for a in ks:
        print(f"  {a:<5} " + " ".join(f"{corr(diffs[a], diffs[b]):>6.2f}" if a != b else f"{'  1.00':>6}"
                                     for b in ks))
    off = [corr(diffs[a], diffs[b]) for i, a in enumerate(ks) for b in ks[i + 1:]]
    off_s = sorted(off)
    med = off_s[len(off_s) // 2]
    print(f"\n  off-diagonal: mean {sum(off)/len(off):+.3f}  median {med:+.3f}  "
          f"min {min(off):+.3f}  max {max(off):+.3f}")
    if abs(med) < 0.5:
        print("  -> levers are GENUINELY DISTINCT tests: a k~9 burden is real, Bonferroni ~ fair.")
    else:
        print("  -> levers are REDUNDANT: 'best of 9' was never a real selection; rethink the batch.")

print(f"\n  {'comparison':<12} {'test':<14} {'raw p':>8} {'Bonferroni':>11} {'Sidak':>8}  verdict")
print("  " + "-" * 66)
for (x, y), tag, p in [(("V24", "V21"), "percentile", boot_p[("V24", "V21")][0]),
                       (("V24", "V21"), "studentized", boot_p[("V24", "V21")][1]),
                       (("V24", "V21"), "JK/Memmel", jk[("V24", "V21")][4])]:
    b, s = min(1.0, p * K_ROUND4), sidak(p, K_ROUND4)
    print(f"  {x+' - '+y:<12} {tag:<14} {p:>8.3f} {b:>11.3f} {s:>8.3f}  "
          f"{'survives' if b < 0.05 else 'does NOT survive'}")
print(f"\n  k={K_ROUND4} is the FLOOR — selection is FOUR rounds deep on the SAME 2005-2026 window.")

# ---- the labelling defect ------------------------------------------------------------
print()
print("=" * 84)
print('THE "SHARPE" LABEL — reconciliation proving no risk-free is subtracted (§15i)')
print("=" * 84)
for k in BOOKS:
    r = rets[k]
    m = sum(r) / len(r)
    sd = math.sqrt(sum((v - m) ** 2 for v in r) / (len(r) - 1))
    vol = sd * math.sqrt(12)
    nav = 1.0
    for x in r:
        nav *= 1 + x
    cagr = nav ** (12 / len(r)) - 1
    print(f"  {k}: CAGR {cagr:6.2%}  ann vol {vol:6.2%}  raw return/vol {m/sd*math.sqrt(12):.3f}"
          f"   | true excess-of-{RF_ASSUMED:.1%} Sharpe would be {(cagr-RF_ASSUMED)/vol:.3f}")
print("  -> the engine computes m/sd with NO rf subtracted. These are RETURN/VOL RATIOS.")
print("     Benchmarks use the identical basis, so RELATIVE claims hold; ABSOLUTE ones were")
print("     overstated ~1.7x by the label alone. Ramana 2026-07-15i: relabel, numbers unchanged.")
