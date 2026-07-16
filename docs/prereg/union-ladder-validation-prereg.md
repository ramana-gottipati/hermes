# UNION LADDER — VALIDATION PRE-REGISTRATION (C1–C3), frozen before any run

> **Class: PRE-REGISTRATION (validation protocol, not a strategy registration).** This does NOT
> register a new book and is NOT a 5th sealed sibling. It freezes THREE adjudication checks on the
> EXISTING union ladder (union · β14 · C40RA · A2 · COMPOSITE-30) so their results cannot be
> reverse-fit. Authored by the coordination session (2026-07-16) paralleling the "Union CAGR
> Optimization Candidates" driving session; hand-off to the lane owner to commit + seal + run.
>
> **Motivation (one line):** the family's CAGR was optimized UP (17.5→26.4%) on a single fixed
> window (2006-2026) in which every sub-window (2006-11 / 2012-17 / 2018-26) is a SELECTION gate
> (`union_lab5.py:585–587`, `p5()`). So there is no clean out-of-sample read today, and the climb
> could be partly noise-chasing. These three checks quantify how much of the climb to trust BEFORE
> the 2026-10-03 forward test adjudicates.
>
> **Estate precedents cited (blocking until cited — failure-ledger discipline):**
> - **D139** — the sector-rotation ladder's top rungs were statistically indistinguishable → V32
>   RETIRED, V21 (simpler) STAYS. The same test is owed here (→ C1).
> - **bug-audit CL-RES-07** — "144-config CAGR grid sorted by the test window, no multiple-testing
>   adjustment → Deflated/Bonferroni; require both-half survival." The union climb is the same
>   shape (→ C3).
> - **explosive-move-research.md:90** — frozen-train / held-test protocol already in estate use;
>   the union family did not apply it (→ C2).
> - **DATA-POSTMORTEM 2026-07-05 (sleeve-orthogonality gate)** — momentum-family books have ~0
>   diversification headroom; conceded up front so C1/ensemble is framed as selection-risk, not
>   diversification.
>
> **Binding rule:** the decision rules in each section are DECLARED HERE, before any number is
> read. On commit, seal by sha256 and record the hash in the carryforward + ledger. Editing the
> file after the seal voids it. Numbers reported pass or fail; nothing is re-tuned to pass.

---

## Shared setup (all three checks)

- **Books under test (as-sealed specs, NOT re-tuned for C1/C3):**
  `U` = the union (`union_lab.py run(mode="base", hook=sel_default, topn=60)`),
  `B14` = union-β14 (`union_lab.py run(hook=sel_beta_cap(1.4))`),
  `C40` = C40RA (`union_lab5.py run(fmode="base", hook=sel_c40ra, topn=40, rf_cash=False)`),
  `A2` = A2-composite (`union_lab5.py run(fmode="pf1", hook=sel_c40ra, topn=40, rf_cash=True)`),
  `K30` = COMPOSITE-30 (`union_lab5.py run5(fmode="pf1", topn=30, weights="drift", rf_cash=True)`).
- **Reproduction gate (MANDATORY, before any C1–C3 read):** each book's control must reproduce its
  ledger headline CAGR to the digit (U 17.5% / 26.04×; B14 18.1% / 28.84×; C40 21.0% / 47.29×;
  A2 25.5% / 99.03×; K30 26.4% / 115.69×). If any control drifts beyond data-refresh noise, **STOP**
  and investigate — do not read a single validation number off a mis-reproduced base.
- **Per-quarter return series:** each `run*()` already returns `navs` (per-rebalance NAV) and `rb`
  (rebalance dates). Define `r_t^X = navs_t / navs_{t-1} − 1` on the COMMON rb grid (all books share
  `rebal_all`, same warmup `max(CORRWIN,LB,250)`, same calendar → identical rb dates; assert this).
- **Harness:** a NEW module in the lane owner's tree (e.g. `research/explosive_moves/union_ladder_val.py`)
  that imports the two labs, runs the five books, aligns `navs` on `rb`, and executes C1/C3. The
  coordination session does NOT write into `research/` (hot lane). This doc is the frozen protocol only.

---

## C1 — D139 PAIRED-SIGNIFICANCE of the ladder increments  *(highest value — most likely to change the graduation decision)*

**Question (frozen):** Are the ladder increments statistically distinguishable, or within the CAGR
noise band? Because the books are nested (share most positions), the test MUST be paired — the
unpaired CAGR SE (≈ 20%/√20 ≈ 4.5 pp) is uninformative here.

**Method:**
1. For each ordered pair `(A→B)` in { U→B14, B14→C40, C40→A2, A2→K30, C40→K30, U→K30 }, form the
   per-quarter difference series `d_t = r_t^B − r_t^A` on the common rb (~80 quarters).
2. **Stationary block bootstrap** of `d_t`: block length **L = 4 quarters** (preserves the trail-stop /
   momentum autocorrelation), **10,000** resamples. For each resample compound the difference into an
   annualized CAGR-gap. Report the **95% CI** of the gap and **p = fraction of resamples with gap ≤ 0**.
3. Cross-check with a **Newey-West-adjusted paired t-stat** on `d_t` (lag = 4).
4. Also report `corr(r^A, r^B)` for each pair (expect ~0.9+) — this is WHY paired is correct.

**Declared decision rule (frozen):**
- **On C40→K30** (the "did the top-30 + let-winners-run axes earn their keep" test):
  - If the 95% CI **includes 0** → per D139 those axes are noise-chasing on this window. The
    graduation candidate **defaults to the simpler, higher-capacity book** (C40, or A2 if the era
    floor is retained). Record COMPOSITE-30 as "in-sample-superior, not distinguishable OOS-relevant."
  - If the 95% CI **excludes 0 AND `p ≤ 0.05`** → the increment is statistically real; it still must
    clear the C-stress (dead-name haircut, below) to graduate on cost grounds.
- **Report ALL six pairwise CIs for the record** regardless of the C40→K30 outcome (e.g. U→B14 tells
  us whether the beta-cap increment — the externally-supported lever — is itself significant).
- **No book is re-tuned on this result.** C1 informs which EXISTING book graduates; it never spawns a new one.

---

## C2 — INTERIM OUT-OF-SAMPLE READ (honest, with its limitation disclosed)

**⚠ Disclosed limitation, stated before any run:** a clean single split is only *partially* possible
retrospectively, because 2018-26 was itself a SELECTION gate for K30 (`p5` requires 2018-26 alpha).
So a 2019-26 "hold-out" is genuinely clean for `U`/`B14` (which predate that gate) but only
semi-clean for `A2`/`K30`. The ONLY fully-clean OOS is 2026-10-03. C2 is an *early estimate*, not a verdict.

**Two variants, both pre-declared:**

**C2a — cheap, levers held (stability, not true OOS):** run all five as-sealed books on rolling
non-overlapping 3-year windows (2006-08, 2009-11, 2012-14, 2015-17, 2018-20, 2021-23, 2024-26).
Report CAGR/α/β per window. **Declared read:** the dispersion of α across windows and whether α > 0
in ≥ 5 of 7 windows. This measures *stability*, not out-of-sample survival — labelled as such.

**C2b — the real (expensive) OOS: full re-search on ≤2018, measured on 2019-26 ONCE.**
- **TRAIN = rb ≤ 2018-12-31; TEST = rb ≥ 2019-01-01.**
- Re-derive EVERY free parameter on TRAIN only, frozen before any TEST read:
  - **P (era floor):** recompute from TRAIN's last 12 months (2018), NOT the full-sample last-12
    (which is 2025-26 — using it leaks modern liquidity into the historical floor; the current
    `union_lab5.py:108–112` uses `months[-12:]` of the full sample. For C2b it MUST be 2018's window).
  - **β-cap, RISKADJ windows, top-N, drift-cap:** re-select by the p5-style gate computed on TRAIN
    sub-windows only (2006-11, 2012-17, 2015-18). Never touch 2019+.
- Freeze the re-derived book, then measure **2019-2026 exactly once, untouched.**
- **Declared output (estimate, no auto-decision):** `survival = TEST_alpha / in-sample_2018-26_alpha`
  for the re-derived book. Report it beside the as-sealed books' 2019-26 numbers. `survival ≈ 1`
  supports the seals; `survival ≲ 0.5` says ~half the edge was window-fitting. Feeds the Oct-3
  adjudication as evidence; triggers nothing automatically.

---

## C3 — DEFLATED FORWARD-CAGR EXPECTATION (a communication fix, per CL-RES-07)

**Question (frozen):** what forward CAGR should be quoted beside the in-sample headline, given the
number of configurations searched on this window?

**Method:**
1. **Enumerate N_trials** — the count of distinct configurations tested across the union program
   (`union_lab.py` 14 rows + `union_lab2` + `union_ml` + `union_lab3/3b` sweeps + `blend_u25` +
   `union_lab4/4b` + `union_lab5` 6 rows + `union_ml2`). Take the count FROM the ledger entries
   16U–16AH; record the exact tally in the result. (Prior estimate: ~40–60.)
2. Apply the estate's **Deflated-Sharpe** framework (already estate-wide; every Deflated-Sharpe is
   an UPPER bound) to each book's return/vol series: compute the expected-maximum in-sample
   return/vol under the null given N_trials and the estimator SE, and the deflation factor
   `φ = (observed − E[max|null]) / observed`.
3. Translate `φ` onto alpha: **forward-expectation band = benchmark_CAGR + φ · in-sample_alpha.**

**Declared output (no pass/fail — it is a reporting standard):** publish the deflated band beside
EVERY headline CAGR in `union-ladder.md` and the compendium. K30's "26.4%" is then shown as, e.g.,
"26.4% in-sample; deflated forward expectation ≈ [band]." **The seals' true deflation protection
remains the 2026-10-03 forward test** — C3 only stops the raw in-sample number being quoted as if it
were a forward expectation.

---

## What C1–C3 collectively decide (and don't)

- **They do NOT create, re-tune, or retire any sealed book.** The four seals + their 2026-10-03
  forward criteria are untouched.
- **They DO inform the graduation choice** the family-adjudication will make: if C1 shows the top
  rungs are indistinguishable and C2b shows low survival, the honest graduate is the simpler,
  higher-capacity book — even though it has the lower in-sample CAGR (the D139 move). If C1 shows
  the increments are real and C2b survival is high, COMPOSITE-30's climb is earned.
- **Capacity is a first-class output, not a footnote:** every C1/C2 result reports median pick-ADV
  alongside CAGR, so "26% at ₹8cr median ADV" is never confused with a scalable book.

## Companion stress (referenced, not part of the frozen C1–C3 bars)

- **Dead-name haircut stress (C5 from the coordination read-out):** re-run A2/K30 with the dead-name
  value at −70% and −90% (vs the sealed −50%) and report the CAGR delta + the actual dead-name rate
  among era-floor picks. If the climb craters, ~+4 pp of the era-floor gain was a haircut artifact.
- **Let-winners-run by window (C4):** report the drift lever's contribution per window; if it is
  concentrated in 2018-26, label it regime-dependent.

*(End of frozen protocol. Seal on commit; record sha256 in carryforward + ledger.)*
