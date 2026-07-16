"""union_ladder_c1.py — INDEPENDENT C1 cross-check of the sealed ladder-validation prereg
(docs/prereg/union-ladder-validation-prereg.md, sha256 37c28824...).

This reproduces the C1 paired-significance result of ledger 16AL / S176 from a SECOND,
independent implementation. Where `union_ladder_val.py` REIMPLEMENTS the backtest engine,
this file EXEC-LOADS `union_lab5.py`'s engine byte-for-byte (everything above its print
battery) and only adds: a `sel_union` config, the reproduction gate, and a paired block
bootstrap (fixed L=4q AND Politis-Romano mean-2q, 20k draws). Because the two harnesses share
no engine code, their agreement is a genuine cross-check — not a shared-bug artifact.

Read-only. Box-only (needs the full archive + the research modules on the sys.path that
union_lab5.py inserts). Run:  python union_ladder_c1.py /opt/hermes/data/hermes.db

Result (2026-07-16, coordination session): 5/5 books reproduce to the digit; the six paired
increments match 16AL to ~2dp (A2->K30 +0.8pp CI [-1.2,+2.9] p=0.22 vs 16AL [-1.11,+2.82]
p=0.214; C40->K30 +5.3pp [+0.4,+10.4] p=0.02 vs [+0.54,+9.90] p=0.014). Confirms 16AL; adds
no new verdict.
"""
import os as _os
_src = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "union_lab5.py")
_c = open(_src, encoding="utf-8").read()
# load the engine only — everything before union_lab5's module-level print battery
exec(compile(_c[:_c.index('\nprint("=" * 118)')], _src, "exec"), globals())

# ================= C1 additions (sel_union + reproduction gate + paired block bootstrap) =========
import random as _rnd
_rnd.seed(12345)

def sel_union(q, d, i, topn):
    # plain sealed union: engine-order, ALL base qualifiers (no beta cap, no riskadj rank)
    return [s for s, _sec in q]

# (name, ledger CAGR%, ledger mult, builder) — each book via the SAME engine
BOOKS = [
    ("UNION",  17.5,  26.04, lambda: run(fmode="base", hook=sel_union, topn=60, rf_cash=False)),
    ("BETA14", 18.1,  28.84, lambda: run(fmode="base", hook=sel_b14,   topn=60, rf_cash=False)),
    ("C40RA",  21.0,  47.29, lambda: run(fmode="base", hook=sel_c40ra, topn=40, rf_cash=False)),
    ("A2",     25.5,  99.03, lambda: run(fmode="pf1",  hook=sel_c40ra, topn=40, rf_cash=True)),
    ("K30",    26.4, 115.69, lambda: run5(fmode="pf1", topn=30, weights="drift", cap=0.05, rf_cash=True)),
]

sys.stderr.write("\n" + "=" * 90 + "\nC1 REPRODUCTION GATE (must match the ledger before any bootstrap is read)\n")
NAVS, BN = {}, None
_fail = False
for name, tgt_c, tgt_m, fn in BOOKS:
    o = fn()
    navs, bnavs = o["navs"], o["bnavs"]
    s = stat(navs, bnavs)
    NAVS[name] = navs
    if BN is None:
        BN = bnavs
    ok = abs(s["cagr"] * 100 - tgt_c) < 1.0 and abs(s["mult"] - tgt_m) / tgt_m < 0.06
    sys.stderr.write("  %-7s CAGR %5.1f%% (tgt %4.1f)  mult %7.2fx (tgt %6.2f)  beta %.2f  %s\n"
                     % (name, s["cagr"] * 100, tgt_c, s["mult"], tgt_m, s["beta"],
                        "OK" if ok else "** MISMATCH **"))
    _fail = _fail or not ok
sys.stderr.flush()
if _fail:
    sys.stderr.write("STOP: a control did not reproduce — not reading the bootstrap.\n")
    sys.exit(1)

# align + per-quarter returns (r[i] = navs[i]/navs[i-1]-1, matching stat())
L = min(len(v) for v in NAVS.values())
RET = {k: [v[i] / v[i - 1] - 1 for i in range(1, L)] for k, v in NAVS.items()}
n = len(next(iter(RET.values())))
YEARS = n / 4.0

def cagr_of(seq):
    p = 1.0
    for r in seq:
        p *= (1.0 + r)
    return p ** (4.0 / len(seq)) - 1.0

def circular_blocks(m, Lb):
    idx = []
    while len(idx) < m:
        st = _rnd.randrange(m)
        for k in range(Lb):
            idx.append((st + k) % m)
    return idx[:m]

def pr_blocks(m, mean_len):
    p = 1.0 / mean_len
    idx = []
    while len(idx) < m:
        st = _rnd.randrange(m)
        idx.append(st)
        while _rnd.random() > p and len(idx) < m:
            st = (st + 1) % m
            idx.append(st)
    return idx[:m]

def boot_gap(rA, rB, blockfn, B=20000):
    gaps = []
    for _ in range(B):
        idx = blockfn(n)
        a = [rA[j] for j in idx]
        b = [rB[j] for j in idx]
        gaps.append(cagr_of(b) - cagr_of(a))
    gaps.sort()
    return gaps[int(0.025 * B)], gaps[int(0.975 * B)], sum(1 for g in gaps if g <= 0) / B

def corr(a, b):
    m = len(a); ma = sum(a) / m; mb = sum(b) / m
    ca = sum((x - ma) ** 2 for x in a); cb = sum((x - mb) ** 2 for x in b)
    cab = sum((a[i] - ma) * (b[i] - mb) for i in range(m))
    return cab / math.sqrt(ca * cb) if ca > 0 and cb > 0 else 0.0

def nw_t(d, lag=4):
    m = len(d); mu = sum(d) / m; dd = [x - mu for x in d]
    var = sum(x * x for x in dd) / m
    for Lg in range(1, lag + 1):
        w = 1 - Lg / (lag + 1)
        g = sum(dd[t] * dd[t - Lg] for t in range(Lg, m)) / m
        var += 2 * w * g
    se = math.sqrt(var / m) if var > 0 else 0.0
    return (mu / se) if se > 0 else 0.0

PAIRS = [("UNION", "BETA14"), ("BETA14", "C40RA"), ("C40RA", "A2"),
         ("A2", "K30"), ("C40RA", "K30"), ("UNION", "K30")]

print("=" * 104)
print("C1 — UNION LADDER PAIRED-SIGNIFICANCE  (block bootstrap on PAIRED per-quarter return diffs)")
print("n = %d quarters (~%.1fy) | resamples B=20000 | blocks: fixed L=4q [declared] + Politis-Romano mean-2q [15i]"
      % (n, YEARS))
print("=" * 104)
print("%-14s %7s %7s %7s | %-15s %5s | %-15s %5s | %5s %6s"
      % ("pair", "CAGR_A", "CAGR_B", "gap", "L4 95% CI", "p<=0", "PR 95% CI", "p<=0", "corr", "NW_t"))
for A, Bk in PAIRS:
    rA, rB = RET[A], RET[Bk]
    ca, cb = cagr_of(rA), cagr_of(rB)
    lo4, hi4, p4 = boot_gap(rA, rB, lambda mm: circular_blocks(mm, 4))
    lop, hip, pp = boot_gap(rA, rB, lambda mm: pr_blocks(mm, 2))
    d = [rB[i] - rA[i] for i in range(n)]
    print("%-14s %6.1f%% %6.1f%% %+6.1f%% | [%+5.1f,%+5.1f]  %4.2f | [%+5.1f,%+5.1f]  %4.2f | %5.2f %+6.2f"
          % (A + "->" + Bk, ca * 100, cb * 100, (cb - ca) * 100,
             lo4 * 100, hi4 * 100, p4, lop * 100, hip * 100, pp, corr(rA, rB), nw_t(d, 4)))

print("")
rA, rB = RET["C40RA"], RET["K30"]
lo4, hi4, p4 = boot_gap(rA, rB, lambda mm: circular_blocks(mm, 4))
inc0 = lo4 <= 0 <= hi4
print("DECISION (frozen prereg C1) — the C40RA->COMPOSITE-30 increment (top-30 + let-winners-run):")
print("  L4 95%% CI = [%+.1f%%, %+.1f%%], p(gap<=0)=%.2f  ->  %s"
      % (lo4 * 100, hi4 * 100, p4,
         ("INCLUDES 0: NOT distinguishable -> D139 says graduate the SIMPLER, higher-capacity book (C40RA / A2)"
          if inc0 else
          "EXCLUDES 0: distinguishable -> K30's increment is real (must still clear the cost/dead-name stress)")))
print("done.")
