"""union_ladder_c23.py — INDEPENDENT cross-check of C2 (rolling stability + era-floor OOS
anchors) and C3 (Deflated Sharpe) from ledger 16AL / S176. Companion to union_ladder_c1.py;
same exec-load-the-engine approach (union_lab5.py byte-for-byte), a separate implementation
from S176's union_ladder_val.py, so agreement rules out an implementation artifact.

Read-only. Box-only. Run:  python union_ladder_c23.py /opt/hermes/data/hermes.db

Result (2026-07-17, coordination session): reproduces 16AL to the digit/3dp —
  C2a stability  U 4/7 · B14 7/7 · C40 6/7 · A2 7/7 · K30 7/7   (== 16AL)
  C2b            P_full 0.450 → P_train(2018) 0.268 (== 16AL); 2019+ as-sealed slices == 16AL
  C3 DSR(N=69)   0.898 / 0.938 / 0.980 / 0.998 / 0.998   (16AL 0.897/.938/.980/.998/.998)
Confirms 16AL; no new verdict. SCOPE NOTE: this reproduces the DETERMINISTIC anchors of C2b
(P_train + the 2019+ as-sealed slices), not S176's full TRAIN-replay "survival 1.01" (that
carries replay lever-selection choices); and C3's DSR (the method-defined statistic), not the
downstream φ→CAGR band mapping (a reporting transform). Those remain as recorded in 16AL.
"""
import os as _os
_src = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "union_lab5.py")
_c = open(_src, encoding="utf-8").read()
exec(compile(_c[:_c.index('\nprint("=" * 118)')], _src, "exec"), globals())

# ============ C2 + C3 — independent cross-check of 16AL/S176 ============
import numpy as _np
from scipy import stats as _ss

def sel_union(q, d, i, topn):
    return [s for s, _sec in q]

BOOKS = [
    ("UNION",  lambda **k: run(fmode="base", hook=sel_union, topn=60, rf_cash=False, **k)),
    ("BETA14", lambda **k: run(fmode="base", hook=sel_b14,   topn=60, rf_cash=False, **k)),
    ("C40RA",  lambda **k: run(fmode="base", hook=sel_c40ra, topn=40, rf_cash=False, **k)),
    ("A2",     lambda **k: run(fmode="pf1",  hook=sel_c40ra, topn=40, rf_cash=True,  **k)),
    ("K30",    lambda **k: run5(fmode="pf1", topn=30, weights="drift", cap=0.05, rf_cash=True, **k)),
]
GATE = {"UNION": (17.5, 26.04), "BETA14": (18.1, 28.84), "C40RA": (21.0, 47.29),
        "A2": (25.5, 99.03), "K30": (26.4, 115.69)}

sys.stderr.write("\n" + "=" * 90 + "\nREPRODUCTION GATE\n")
FULL = {}
for name, fn in BOOKS:
    o = fn(); s = stat(o["navs"], o["bnavs"]); FULL[name] = (o, s)
    tc, tm = GATE[name]
    ok = abs(s["cagr"] * 100 - tc) < 1.0 and abs(s["mult"] - tm) / tm < 0.06
    sys.stderr.write("  %-7s CAGR %5.1f%% (tgt %4.1f)  mult %7.2fx  %s\n"
                     % (name, s["cagr"] * 100, tc, s["mult"], "OK" if ok else "** MISMATCH **"))
    if not ok:
        sys.stderr.write("STOP: control mismatch.\n"); sys.exit(1)
sys.stderr.flush()

def _alpha(navs, bnavs):
    return stat(navs, bnavs)["alpha"] if len(navs) >= 5 else None

# ---- C2a — rolling 3y stability ----
WINS = [("2006-01-01", "2008-12-31"), ("2009-01-01", "2011-12-31"), ("2012-01-01", "2014-12-31"),
        ("2015-01-01", "2017-12-31"), ("2018-01-01", "2020-12-31"), ("2021-01-01", "2023-12-31"),
        ("2024-01-01", "2026-12-31")]
print("=" * 96)
print("C2a — rolling 3y stability (windows with alpha>0)   [16AL: U 4/7 B14 7/7 C40 6/7 A2 7/7 K30 7/7]")
print("=" * 96)
for name, fn in BOOKS:
    cnt = tot = 0; cells = []
    for st, en in WINS:
        a = _alpha(*[fn(start=st, end=en)[k] for k in ("navs", "bnavs")])
        if a is None:
            cells.append("  n/a"); continue
        tot += 1; cnt += (a > 0); cells.append("%+5.1f" % (a * 100))
    print("  %-7s  %d/%d   [%s]" % (name, cnt, tot, " ".join(cells)))

# ---- C2b — era-floor OOS anchors ----
_m2018 = sorted(ym for ym in _bym if ym.startswith("2018"))
P_train = sum(sum(1 for v in _bym[ym] if v >= ADV_BAR) / len(_bym[ym]) for ym in _m2018) / len(_m2018)
_mfull = sorted(_bym)[-12:]
P_full = sum(sum(1 for v in _bym[ym] if v >= ADV_BAR) / len(_bym[ym]) for ym in _mfull) / len(_mfull)
print("\n" + "=" * 96)
print("C2b — era-floor period-sensitivity (highest window-fit-risk rung)   [16AL: P_train 0.268]")
print("=" * 96)
print("  P_full (last 12 mo)   = %.3f   [sealed calibration ~0.450]" % P_full)
print("  P_train (2018 only)   = %.3f   [16AL 0.268]" % P_train)
print("  as-sealed on UNTOUCHED 2019+  [16AL: U 24.2/12.0 B14 23.8/11.7 C40 30.4/17.2 A2 34.1/21.2 K30 34.6/22.0]")
for name, fn in BOOKS:
    s = stat(*[fn(start="2019-01-01")[k] for k in ("navs", "bnavs")])
    print("  %-7s  CAGR %5.1f%%  alpha %+5.1f%%  beta %.2f" % (name, s["cagr"] * 100, s["alpha"] * 100, s["beta"]))

# ---- C3 — Deflated Sharpe (Bailey-LdP, attribution.py:314) ----
N_TRIALS = 69
def _dsr(rets, n=N_TRIALS):
    r = _np.asarray(rets, float); r = r[_np.isfinite(r)]; T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = _ss.skew(r); g4 = _ss.kurtosis(r, fisher=False)
    emc = 0.5772156649
    z1 = _ss.norm.ppf(1 - 1.0 / n); z2 = _ss.norm.ppf(1 - 1.0 / (n * _np.e))
    sr0 = (1 - emc) * z1 + emc * z2
    var_sr = (1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2) / (T - 1)
    sr_std = _np.sqrt(max(var_sr, 1e-12))
    return float(_ss.norm.cdf((sr - sr0 * sr_std) / sr_std)), sr * 2.0

print("\n" + "=" * 96)
print("C3 — Deflated Sharpe (Bailey-LdP, attribution.py:314, per-quarter, N_trials=%d)" % N_TRIALS)
print("     [16AL DSR: 0.897 / 0.938 / 0.980 / 0.998 / 0.998]")
print("=" * 96)
for name, fn in BOOKS:
    navs = FULL[name][0]["navs"]
    ret = [navs[i] / navs[i - 1] - 1 for i in range(1, len(navs))]
    dsr, sra = _dsr(ret)
    print("  %-7s  DSR(69) %.3f   ann.SR %.2f   [N=50 %.3f · N=100 %.3f]"
          % (name, dsr, sra, _dsr(ret, 50)[0], _dsr(ret, 100)[0]))
print("\ndone.")
