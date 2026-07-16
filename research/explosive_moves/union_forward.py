"""UNION FORWARD — the forward-test-day runner for the union sibling family (S181).

WHAT THIS IS. One command that makes the 2026-10-03+ forward-test day mechanical. It
exec-loads `union_ladder_val.py`'s engine byte-for-byte (the S176 sealed-validation
implementation whose reproduction gate ran 5/5 to the digit, ledger 16AL) — everything
above that module's print battery — and adds ONLY reporting: no new selection logic, no
new levers, no spec change. Sealed files untouched.

Run (box, read-only):
    /opt/hermes/.venv-research/bin/python union_forward.py /opt/hermes/data/hermes.db
    ... union_forward.py /opt/hermes/data/hermes.db --asof 2026-10-03
(plain python works too — the engine is stdlib-only). Before an official checkpoint,
refresh the TRI/G-sec CSVs via `niftyindices_hist.py` (manifest `indexes_tri`,
pull-on-demand) — this runner warns if they look stale but does not fetch.

WHAT IT PRINTS, in order:
  1. REPRODUCTION GATE (mandatory): all SIX ladder rows re-run full-period and matched
     to their recorded numbers to the digit (U/B14/C40/A2/K30 per the 16AL gate +
     A1-composite per union-ladder.md §4). Any miss -> STOP, exactly like the val runner.
  2. THE FORWARD WINDOW: every completed engine leg from the 2026-07 quarter onward
     (see BOUNDARY below), per-leg returns for each book beside Nifty 500 PR, Next 50 PR,
     and the TRI twins; cumulative + annualized when >=4 legs; alpha/beta vs N500 PR and
     vs N500 TRI (>=6 legs); MaxDD (quarterly marks, same convention both sides);
     inv%; and the two prints this runner owes the estate:
       - MEDIAN PICK-ADV per forward rebalance + overall (owed since 16AJ; run5 never
         computed it — recomputed here from the same QUAL/hook/topn selection line).
       - A2-COMPOSITE CLEAN-TR (full-period tr=True run — union-ladder.md §5 carries
         "not separately run" until this prints; K30's tr=True run beside it must
         reproduce the recorded 27.3%/16AF as the same-code-path cross-check).
  3. THE FOUR FROZEN CRITERIA per SEALED spec (verbatim from the four preregs, all four
     specs carry the same criteria; A1/A2 are RECORDED leads, reported beside but
     excluded from adjudication):
       C1 forward CAGR > Nifty Next 50 buy-and-hold (PR, as frozen; TRI printed beside),
       C2 forward alpha > 0 (vs Nifty 500, quarterly regression x4; beta reported;
          excess that is purely beta > 1.1 = FAIL),
       C3 forward MaxDD not worse than Next 50's over the same window,
       C4 no single quarter > 60% of the total excess (fail -> INCONCLUSIVE, extend).
     With < 8 completed forward quarters the verdict line is INTERIM (n/8) — the preregs
     judge only at >= 8. At >= 8 the FAMILY ADJUDICATION fires mechanically: among sealed
     passers the highest forward ALPHA graduates, the rest retire; none pass -> all
     DESCRIPTIVE-ONLY. Seals: union a9a14058 / b14 08b46199 / c40ra 0715a0d9 /
     composite30 07ef2ef9 (docs/prereg/*.md).
  4. THE PORTFOLIO DIAL on the forward window (16AN fold): K30 and A2 mixed with the
     long G-sec leg at 100/0 / 90/10 / 80/20 / 70/30, quarterly-rebalanced fixed weights
     — the measured CAGR<->survivability dial rides into every checkpoint until Ramana
     picks the policy point (docs/portfolio-layer-design.md).

BOUNDARY (encoded once so no future session re-derives it). All four preregs freeze
"every NEW quarter from 2026-07 onward", registered 2026-07-16. The engine's own
rebalance calendar defines the quarters. Two cuts are printed:
  - PREREG CUT (the judged one): legs starting at the LAST rebalance <= 2026-07-16 —
    that leg IS the 2026-07 quarter; its picks were fixed by the frozen rule before the
    seal, its return accrues almost entirely after it.
  - STRICT CUT (audit twin): legs starting at the FIRST rebalance AFTER 2026-07-16 —
    zero pre-seal overlap of any kind. Printed beside so nobody has to argue about the
    few pre-seal days inside the boundary leg.
Criteria are judged on the PREREG cut per the preregs' own wording.

CAVEATS THAT RIDE INTO THE JUDGMENT (printed with the rows):
  - era-floor flag (16AL C2b): the floor rung failed the <=2018 re-derivation
    (P_train 0.268 vs sealed 0.450) — the family's highest window-fit risk; first
    suspect if A1/A2/K30 forward rows disappoint.
  - deflated forward expectations (16AL C3, Bailey-LdP deflation at N_trials=69):
    U 15.7 / B14 16.6 / C40 18.1 / A2 21.0 / K30 21.6 — the honest priors, printed
    beside every headline until the forward window speaks.
  - sealed criteria stay PR-vs-PR as frozen; TRI columns are measurement beside them
    (16AJ). Book TR accrual is a LOWER bound (16AD: ~34% pre-2012 dividend parse).
Descriptive research on paper portfolios; not advice; nothing here deploys anything.
"""
import os as _os, sys

# ---- CLI: [DB] [--asof YYYY-MM-DD]; strip --asof before the engine reads sys.argv ----
ASOF = None
_argv = [sys.argv[0]]
_it = iter(sys.argv[1:])
for _a in _it:
    if _a == "--asof":
        ASOF = next(_it, None)
    elif _a.startswith("--asof="):
        ASOF = _a.split("=", 1)[1]
    else:
        _argv.append(_a)
sys.argv = _argv

# ---- exec-load the sealed-validation engine (everything above its print battery) ----
_src = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "union_ladder_val.py")
_c = open(_src, encoding="utf-8").read()
exec(compile(_c[:_c.index('\nprint("=" * 118)')], _src, "exec"), globals())
# in scope now: run5/stat/stat_vs/bench_cagr_series/hook_union/hook_b14/sel_a2c/QUAL/adv/
# pym/ci/cal/N/rebal_all/iclose/BENCH/SLEEVE/TRI500/TRIN50/GSEC/gsec_q/BOOKS/GATE

REG = "2026-07-16"          # all four registrations sealed this day
MIN_Q = 8                    # preregs: judged only at >= 8 forward quarters
SEALS = {"U": "a9a14058", "B14": "08b46199", "C40": "0715a0d9", "K30": "07ef2ef9"}
DEFLATED = {"U": 15.7, "B14": 16.6, "C40": 18.1, "A2": 21.0, "K30": 21.6}   # 16AL C3
ERA_FLOOR_ROWS = ("A1", "A2", "K30")

# the sixth ladder row (union-ladder.md §4; recorded 16AE, unregistered) + its gate
BOOKS = dict(BOOKS)
BOOKS["A1"] = dict(fmode="pf", topn=40, rf_cash=True)
GATE = dict(GATE)
GATE["A1"] = (25.6, 100.43)
ORDER = ["U", "B14", "C40", "A1", "A2", "K30"]

if ASOF is None:
    ASOF = cal[-1]

print("=" * 118)
print("UNION FORWARD — checkpoint as of %s (registrations sealed %s; judgment at >= %d forward quarters)"
      % (ASOF, REG, MIN_Q))
print("=" * 118)

# ---- data freshness (warn, never fetch) ----
def _gap_days(d1, d2):
    from datetime import date
    a = date(*map(int, d1.split("-"))); b = date(*map(int, d2.split("-")))
    return (b - a).days

if _gap_days(cal[-1], ASOF) > 7:
    print("!! index_rows (PR benches) end %s — %d days before asof; check the nightly bhavcopy ingest"
          % (cal[-1], _gap_days(cal[-1], ASOF)), flush=True)
for _nm, _sd in (("TRI500", TRI500), ("TRIN50", TRIN50), ("GSEC", GSEC)):
    if _sd and _gap_days(max(_sd), ASOF) > 10:
        print("!! %s CSV ends %s — refresh via niftyindices_hist.py before an official checkpoint"
              % (_nm, max(_sd)), flush=True)
    elif not _sd:
        print("!! %s CSV missing — TRI columns will be blank" % _nm, flush=True)

# ---- 1. reproduction gate (six rows, to the digit, else STOP — the 16AL discipline) ----
print("")
print("### 1. REPRODUCTION GATE (full period; must match the recorded ladder before anything forward is read)")
RUNS = {}
for k in ORDER:
    o = run5(**BOOKS[k])
    RUNS[k] = o
    s = stat(o["navs"], o["bnavs"])
    g_c, g_m = GATE[k]
    ok = abs(s["cagr"] * 100 - g_c) < 0.05 and abs(s["mult"] - g_m) < 0.05
    # A1 is SOFT-gated: its recorded row (union-ladder.md §4) came from union_lab4.py, a
    # different harness never reproduced through this engine — a divergence is flagged
    # loudly for reconciliation but does not invalidate the five 16AL-gated books.
    soft = (k == "A1")
    print("  repro %-4s CAGR %5.1f%% (gate %.1f)  Rs1Cr->%7.2fx (gate %.2f)  %s"
          % (k, s["cagr"] * 100, g_c, s["mult"], g_m,
             ("OK" if ok else ("DIVERGES from the lab4 record — reconcile before quoting A1; sealed rows unaffected"
                               if soft else "FAIL"))), flush=True)
    if not ok and not soft:
        print("REPRODUCTION GATE FAILED — STOP (fix the archive/engine drift before reading any forward number)")
        sys.exit(1)

# ---- the boundary ----
rb = list(rebal_all)
j_pre = max(i for i, d in enumerate(rb) if d <= REG)            # prereg cut: last rebalance <= REG
j_strict = j_pre + 1                                            # strict cut: first rebalance after REG
legs_end = [i for i in range(len(rb) - 1) if rb[i + 1] <= ASOF] # completed legs by asof
fwd_pre = [i for i in legs_end if i >= j_pre]
fwd_strict = [i for i in legs_end if i >= j_strict]
print("")
print("### 2. THE FORWARD WINDOW")
print("  engine rebalances around the seal: ... %s | %s(=boundary) | %s"
      % (rb[j_pre - 1], rb[j_pre], rb[j_strict] if j_strict < len(rb) else "(next: not yet in data)"))
print("  PREREG cut (judged): legs from %s   -> %d completed forward quarter(s) by %s"
      % (rb[j_pre], len(fwd_pre), ASOF))
print("  STRICT cut (audit) : legs from %s -> %d completed forward quarter(s)"
      % (rb[j_strict] if j_strict < len(rb) else "(pending)", len(fwd_strict)))
if not fwd_pre:
    nxt = rb[j_pre + 1] if j_pre + 1 < len(rb) else None
    if nxt:
        print("  boundary leg IN PROGRESS: started %s, completes at the next rebalance %s" % (rb[j_pre], nxt))
    else:
        elapsed = ci.get(ASOF, N - 1) - ci[rb[j_pre]] if ASOF in ci else (N - 1) - ci[rb[j_pre]]
        print("  boundary leg IN PROGRESS: started %s, ~%d of %d trading days elapsed — first checkpoint lands when the engine's next rebalance enters the data (~%d more sessions)"
              % (rb[j_pre], elapsed, QTR, max(0, QTR - elapsed)))

def _near(sd, d):
    return series_near(sd, d) if sd else None

def _inear(nm, d):
    v = iclose[nm].get(d)
    return v if v else _idx_near(nm, d)

def med_pick_adv(k, d):
    """median ADV (Rs) of the book's selection at rebalance d — the same selection line run5 uses."""
    cfg = BOOKS[k]
    i = ci[d]
    hook = cfg.get("hook") or sel_a2c
    sel = hook(QUAL[cfg["fmode"]][d], d, i, cfg["topn"])[:cfg["topn"]]
    pm = pym(d)
    a = sorted(adv.get(s, {}).get(pm, 0) for s in sel)
    return (a[len(a) // 2] if a else None), len(sel)

def leg_rets(navs, idxs):
    out = []
    for i in idxs:
        prev = navs[i - 1] if i > 0 else 1.0
        out.append(navs[i] / prev - 1.0)
    return out

def dd_of(rets):
    nav, pk, mx = 1.0, 1.0, 0.0
    for r in rets:
        nav *= (1 + r); pk = max(pk, nav); mx = min(mx, nav / pk - 1)
    return mx

def ab(r, br):
    n = min(len(r), len(br))
    if n < 2: return None, None
    r, br = r[:n], br[:n]
    m, mb = sum(r) / n, sum(br) / n
    vb = sum((x - mb) ** 2 for x in br) / (n - 1)
    cov = sum((r[i] - m) * (br[i] - mb) for i in range(n)) / (n - 1)
    b = cov / vb if vb else 0.0
    return (m - b * mb) * 4, b

def idx_leg(nm, i):
    a, b = _inear(nm, rb[i]), _inear(nm, rb[i + 1])
    return b / a - 1.0 if (a and b) else 0.0

def tri_leg(sd, i):
    a, b = _near(sd, rb[i]), _near(sd, rb[i + 1])
    return b / a - 1.0 if (a and b) else None

def cum(rets):
    nav = 1.0
    for r in rets: nav *= (1 + r)
    return nav - 1.0

def annualize(rets):
    nav = 1.0
    for r in rets: nav *= (1 + r)
    y = len(rets) / 4.0
    return nav ** (1 / y) - 1 if y > 0 and nav > 0 else float("nan")

if fwd_pre:
    n500 = [idx_leg(BENCH, i) for i in fwd_pre]
    n50 = [idx_leg(SLEEVE, i) for i in fwd_pre]
    tri5 = [tri_leg(TRI500, i) for i in fwd_pre]
    trin = [tri_leg(TRIN50, i) for i in fwd_pre]
    print("")
    print("  per-quarter (PREREG cut): leg end | N500 PR | N50 PR | N500 TRI | N50 TRI | " + " | ".join(ORDER))
    for row_i, i in enumerate(fwd_pre):
        cols = " | ".join("%+6.1f%%" % (leg_rets(RUNS[k]["navs"], [i])[0] * 100) for k in ORDER)
        print("    %s | %+6.1f%% | %+6.1f%% | %s | %s | %s"
              % (rb[i + 1], n500[row_i] * 100, n50[row_i] * 100,
                 ("%+6.1f%%" % (tri5[row_i] * 100)) if tri5[row_i] is not None else "   n/a ",
                 ("%+6.1f%%" % (trin[row_i] * 100)) if trin[row_i] is not None else "   n/a ",
                 cols), flush=True)

    print("")
    print("  book summaries (PREREG cut, %d quarter(s)):" % len(fwd_pre))
    SUMM = {}
    for k in ORDER:
        r = leg_rets(RUNS[k]["navs"], fwd_pre)
        c = cum(r)
        a_pr, b_pr = ab(r, n500)
        tri_ok = all(x is not None for x in tri5)
        a_tri, b_tri = ab(r, [x for x in tri5]) if tri_ok else (None, None)
        madv = [med_pick_adv(k, rb[i]) for i in fwd_pre]
        mm = sorted(v for v, _n in madv if v is not None)
        med = mm[len(mm) // 2] / 1e7 if mm else 0.0
        inv = RUNS[k]["inv"]
        inv_f = sum(inv[i] for i in fwd_pre) / len(fwd_pre)
        SUMM[k] = dict(rets=r, cum=c, alpha=a_pr, beta=b_pr, dd=dd_of(r))
        tag = "SEALED %s" % SEALS[k] if k in SEALS else "recorded lead (unregistered)"
        line = "    %-4s cum %+7.2f%%" % (k, c * 100)
        if len(r) >= 4:
            line += "  ann %5.1f%%" % (annualize(r) * 100)
        if a_pr is not None and len(r) >= 6:
            line += "  aPR %+5.1f/bPR %4.2f" % (a_pr * 100, b_pr)
            if a_tri is not None:
                line += "  aTRI %+5.1f/bTRI %4.2f" % (a_tri * 100, b_tri)
        elif a_pr is not None:
            line += "  (a/b at <6 legs: unstable, not printed)"
        line += "  MaxDD %5.1f%%  inv %3.0f%%  medADV %5.1fcr   [%s]" % (SUMM[k]["dd"] * 100, inv_f * 100, med, tag)
        print(line, flush=True)
        if k in DEFLATED:
            print("           deflated prior (16AL C3): ~%.1f%%/yr expected forward" % DEFLATED[k])
    print("    N50 PR  cum %+7.2f%%  MaxDD %5.1f%%   (criterion benches; N50 TRI cum %s)"
          % (cum(n50) * 100, dd_of(n50) * 100,
             ("%+.2f%%" % (cum([x for x in trin]) * 100)) if all(x is not None for x in trin) else "n/a"))
    if fwd_strict:
        print("  STRICT-cut cums: " + "  ".join(
            "%s %+.2f%%" % (k, cum(leg_rets(RUNS[k]["navs"], fwd_strict)) * 100) for k in ORDER))

    # ---- 3. frozen criteria per sealed spec ----
    print("")
    print("### 3. FROZEN CRITERIA (sealed specs only; %d/%d forward quarters -> %s)"
          % (len(fwd_pre), MIN_Q, "JUDGMENT" if len(fwd_pre) >= MIN_Q else "INTERIM — no verdict before %d" % MIN_Q))
    passers = []
    for k in [x for x in ORDER if x in SEALS]:
        r = SUMM[k]["rets"]
        exc = [r[i] - n50[i] for i in range(len(r))]
        tot = sum(exc)
        c1 = cum(r) > cum(n50)
        c2 = SUMM[k]["alpha"] is not None and SUMM[k]["alpha"] > 0
        c3 = SUMM[k]["dd"] >= dd_of(n50)
        c4ok = not (tot > 0 and max(exc) / tot > 0.60)
        beta_note = ""
        if SUMM[k]["beta"] is not None and SUMM[k]["beta"] > 1.1 and c1 and not c2:
            beta_note = "  << excess is beta, not alpha (prereg: FAIL)"
        verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
        if c1 and c2 and c3 and not c4ok:
            verdict = "INCONCLUSIVE (C4) — extend window"
        if len(fwd_pre) < MIN_Q:
            alpha_moot = SUMM[k]["alpha"] is None      # < 2 legs: alpha not computable yet
            verdict = "on track" if (c1 and c3 and (c2 or alpha_moot)) else "behind"
        print("  %-4s C1 beat-N50 %-5s  C2 alpha>0 %-5s  C3 dd-not-worse %-5s  C4 concentration %-5s  -> %s%s"
              % (k, c1, ("n/a" if SUMM[k]["alpha"] is None else bool(c2)), c3, c4ok, verdict, beta_note))
        if len(fwd_pre) >= MIN_Q and verdict == "PASS":
            passers.append((SUMM[k]["alpha"] or -9, k))
    if len(fwd_pre) >= MIN_Q:
        if passers:
            passers.sort(reverse=True)
            print("  FAMILY ADJUDICATION (frozen): GRADUATE = %s (highest forward alpha among passers); the rest retire to reference."
                  % passers[0][1])
        else:
            print("  FAMILY ADJUDICATION (frozen): no sealed spec passed — ALL DESCRIPTIVE-ONLY, never deployed.")
    print("  era-floor flag rides in (16AL C2b): P_train 0.268 vs sealed 0.450 — %s carry the family's highest window-fit risk."
          % "/".join(ERA_FLOOR_ROWS))

    # ---- 4. the portfolio dial on the forward window (16AN fold) ----
    print("")
    print("### 4. PORTFOLIO DIAL (forward window; fixed mix, quarterly rebalance; G-sec leg = gsec_q)")
    gs = [gsec_q(rb[i], rb[i + 1]) for i in fwd_pre]
    for k in ("K30", "A2"):
        for w in (1.0, 0.9, 0.8, 0.7):
            mix = [w * SUMM[k]["rets"][i] + (1 - w) * gs[i] for i in range(len(gs))]
            line = "  %s %3.0f/%2.0f  cum %+7.2f%%  MaxDD %5.1f%%" % (k, w * 100, (1 - w) * 100, cum(mix) * 100, dd_of(mix) * 100)
            if len(mix) >= 4:
                m = sum(mix) / len(mix)
                sd = (sum((x - m) ** 2 for x in mix) / (len(mix) - 1)) ** 0.5
                line += "  ann %5.1f%%  ret/vol %4.2f" % (annualize(mix) * 100, (m / sd * 2 if sd else 0))
            print(line, flush=True)
    print("  (policy point = Ramana's pick on the measured 16AN curve; design default 80/20 per"
          " docs/portfolio-layer-design.md §4; the sealed specs themselves stay 100/0)")

# ---- 5. the owed TR prints (full period; cross-check anchored) ----
print("")
print("### 5. TOTAL-RETURN prints (16AD accrual, lower bound; full period)")
o = run5(tr=True, **BOOKS["K30"])
s = stat(o["navs"], o["bnavs"])
anchor_ok = abs(s["cagr"] * 100 - 27.3) < 0.1
print("  K30 TR %5.1f%% (Rs1Cr->%7.2fx, div %d)  [16AF anchor 27.3%% -> %s]"
      % (s["cagr"] * 100, s["mult"], o["ndiv"], "OK" if anchor_ok else "MISMATCH — investigate before trusting the A2 line"), flush=True)
o = run5(tr=True, **BOOKS["A2"])
s = stat(o["navs"], o["bnavs"])
print("  A2 CLEAN-TR %5.1f%% (Rs1Cr->%7.2fx, div %d, MaxDD %5.1f%%)  << the owed print: union-ladder.md §5 'FULL TR' row"
      % (s["cagr"] * 100, s["mult"], o["ndiv"], s["dd"] * 100), flush=True)

# ---- 6. full-period median pick-ADV (the other owed print; per book, all rebalances) ----
print("")
print("### 6. MEDIAN PICK-ADV (full period + last-4-rebalance recent view; Rs cr)")
for k in ORDER:
    vals = []
    for d in rb[:-1]:
        v, _n = med_pick_adv(k, d)
        if v is not None: vals.append(v)
    if not vals:
        print("  %-4s no selections" % k); continue
    med_all = sorted(vals)[len(vals) // 2] / 1e7
    recent = sorted(vals[-4:])[len(vals[-4:]) // 2] / 1e7
    print("  %-4s full-period median %6.1fcr   recent(4 rebals) %6.1fcr" % (k, med_all, recent), flush=True)

print("")
print("done. (descriptive research; sealed criteria judged only per the preregs; nothing here deploys anything)")
