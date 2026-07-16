# D142 rf re-cut — the executable, pre-registered plan (the one owed numbers-moving lane)

> **Lifecycle: TRANSIENT** (DOC_INDEX class RUN-BOOK(active)). The execution plan for D142's
> deferred risk-free-rate re-cut. **Retire** (git rm; fold the result into `docs/strategy-ledger.md` + the affected
> `docs/strategies/*` pages + PROJECT_STATE) once the re-cut has LANDED and its verdict-diff is
> recorded. Registered in `docs/DOC_INDEX.md` §D. Authored S170 (Opus, strong-tier) — **planning
> only, zero numbers moved.**

## Why this doc exists

D142 relabelled every "Sharpe" in the estate to "return/vol" (the numbers were never
risk-free-adjusted) and **deferred the actual re-cut** — subtracting a real rf — as one coherent
lane, because it MOVES NUMBERS on live hurdles and can flip verdicts (FABLE §4 stop #2: a number
that flips a verdict is STRONG-tier to ratify, and a live-strategy kill is Ramana-only). This doc
is the strong-tier prep so that lane executes cleanly and mechanically when the tree is quiet.

**It is NOT yet runnable, for two reasons, both current (S170):** (1) every re-cut site lives in
`research/explosive_moves/`, where the **union lane is actively building** (S168 pushed minutes
before this doc) — a mid-flight change to shared `metrics.py`/`factory.py` would corrupt their live
backtests (FABLE §0.4 / §4 #6); (2) the re-run needs the VPS research environment
(`.venv-research` + the full `research.db`/archive) — not reproducible on the laptop
(local `research.db` is a 12 KB schema shell). **Do not start until both clear.**

## §1 — The re-cut sites (grep'd inventory, read-only)

Every site computes `mean/sd × √periods` (or hands RAW returns to the Deflated-Sharpe) with **no rf
subtracted**. Each already carries a D142 disown comment; the re-cut is the mechanical
"subtract rf, once, at the ratio/DSR input."

| File | Site | What it computes now | Re-cut |
|---|---|---|---|
| `metrics.py` | `equity_stats` :44-45 | `retvol`, `sortino` = raw mean / (sd \| downside-sd) × √252 | subtract per-period rf from `ret` before the ratio |
| `factory.py` | `eqstats` (`retvol` key) | same, the strategy factory's core | same; **highest fan-out — every backtest imports it** |
| `factor_zoo.py` | `tearsheet` :252 | `retvol`, `sortino` over the factor books | same |
| `attribution.py` | `deflated_sharpe` :321, `retvol_ann` | RAW `strat` → ratio + DSR; **`strat_ex = strat - rf` already in scope at :459** | swap `strat`→`strat_ex` (D142 called this "the one-liner"; deliberately deferred to land WITH the rest) |
| `cost_realism.py` | :109, :144 | `retvol` at realistic cost | same (rf per-period) |
| `cost_participation.py` | :250, :287 | `retvol` across the AUM grid | same |
| `cblend_cost_recut.py` | :211 hurdle | compares to the `BENCH_RETVOL` 0.89 bar | re-cut BOTH sides (strategy + hurdle) coherently |
| `exit_lab.py`, `c_overlay.py` | ratio prints | descriptive | same |

**The hurdle moves too.** The `Nifty 500 = 0.89` bar (ledger §leaderboard) is a return/vol ratio;
its rf-adjusted value must be recomputed on the identical basis, or every comparison desyncs.

## §2 — The rf source (already primary-source-clean; verify coverage on the box)

- **Series:** `index_series("Nifty 1D Rate Index")` — NSE overnight TR rate index, Guardrail-#8
  clean. `attribution.rf_monthly()` (:277) already consumes it today.
- **Pre-2016 gap-fill:** flat `RF_PROXY_ANN = 0.065` (documented in `attribution.py`; overnight
  rates averaged ~6.5–8% then). RF enters only a mean shift, so the proxy cannot distort dispersion.
- **⚠ Box-verify before the run (not checkable on the laptop — the rate index is absent from the
  local `hermes.db`):** confirm `index_rows` carries "Nifty 1D Rate Index", its first date (expect
  ~2016), and that the proxy window is exactly pre-first-date. `sqlite3 -readonly` on the VPS.

## §3 — THE FINDING: the rf shift is `rf/σ`, and it mostly LOOSENS the bar (the hurdle is low-vol)

A true Sharpe = `(μ − rf)/σ = R − rf/σ`, where `R` is today's return/vol. **The deduction per book is
`rf/σ`, not a constant** — a lower-vol book is penalised MORE. So D142's standing line, *"every
RELATIVE claim stands exactly as written,"* is an **approximation** that holds only when the two
books compared share σ.

**First-order re-cut computed on the laptop from the committed `research/explosive_moves/out/factor_zoo.csv`**
(it records `vol_ann_pct` per book) — `true = return/vol − 0.065/σ`; hurdle σ ≈ 16.4% implied from
Nifty-500's 14.6% CAGR ÷ 0.89 (rough — the box run uses the measured σ):

```
HURDLE Nifty500:  return/vol 0.89   σ≈16.4%   penalty 0.40   ->  true ≈ 0.49
book            ret/vol   σ%   rf/σ   true   nowVs.89  trueVsBar   Δmargin
RISKADJ (champ)   1.29   26.7  0.24   1.05     +0.40      +0.55      +0.15  widens
LOWVOL_MOM        1.12   16.7  0.39   0.73     +0.23      +0.24      +0.01  ~neutral
QUAL_MOM          1.04   23.1  0.28   0.76     +0.15      +0.26      +0.11  widens
QMV               0.86   25.8  0.25   0.61     -0.03      +0.11      +0.14  CROSSES fail→pass
DEFENSIVE(lv+q)   0.87   14.3  0.45   0.42     -0.02      -0.08      -0.06  fails harder
LOWVOL            0.84   11.7  0.56   0.28     -0.05      -0.21      -0.16  fails harder
LOWBETA(BAB)      0.70   15.6  0.42   0.28     -0.19      -0.21      -0.02  fails harder
```

**The counter-intuitive result (the actual finding):** because the **HURDLE is itself low-vol
(16.4%)**, the bar takes one of the *biggest* penalties (0.40, 0.89→~0.49). So the re-cut **loosens
most comparisons** — every higher-vol book's margin over the bar *widens* (RISKADJ +0.40→+0.55). The
books that lose ground are the genuinely low-vol ones (LOWVOL σ11.7%, DEFENSIVE σ14.3%), and **they
were already below the bar** — the re-cut makes a rejected book fail *harder*, flipping nothing. This
is confirmed independently on the rotation ladder, where the recorded true Sharpes
(`sector_rotation_significance.py:58`, §15i) show V24 0.911/V32 0.898 → **tied at 0.54** (the 0.013
lead — inside D139's 0.148 noise floor — vanishes; V32 already retired, no live flip).

## §4 — Verdict watch-list (what the box run must re-check; a flip is Ramana-only per §4 #2)

Ordered by the computed risk above — **not** by book name (the "low-vol ⇒ at-risk" intuition was
FALSIFIED for the hurdle-relative question: the low-vol hurdle absorbs the penalty).

1. **🟠 The one CROSSING — QMV (quality+mom+value): −0.03 → +0.11, fail→pass at the bar.** A book
   marginally below 0.89 on return/vol lands above the rf-adjusted bar. Re-check whether QMV's
   *both-halves* survive-flag flips (it's a factor-zoo leaderboard book, not a signed strategy — a
   position change, likely not a Ramana call, but verify it's not sold anywhere as "rejected").
2. **🟢 LOWVOL_MOM — the SIGNED NEW-BENCHMARK verdict (S163 item #602, 1.19 vs 0.89) is SAFE, not
   at-risk.** Δmargin +0.01: its σ (16.7%) matches the benchmark's, so the penalties cancel. The
   human-signed canon does **not** move. (This corrects the naive "low-vol ⇒ compresses" reading —
   grounded, not assumed.)
3. **🟢 The champion + all clear-margin books widen** (RISKADJ, MOM12, HI52, QUAL_MOM…) — the re-cut
   *strengthens* their standing vs the bar. No risk.
4. **🟢 Already-rejected low-vol books fail harder** (LOWVOL, DEFENSIVE, LOWBETA) — more decisive
   rejection, no flip.
5. **rf-INVARIANT verdicts — do not re-open:** C-BLEND (1.32) and momentum (gross 1.29) are rejected
   as fundable on *cost* (net < 0.89 at realistic AUM); cost dominates rf, so the re-cut cannot
   resurrect or newly-kill them. Every **DSR/Deflated-Sharpe FAIL gets STRONGER** (D142: the null is
   rf-free, the observed input is inflated today) — no DSR failure can flip to a pass.

**Net:** on the factor estate the re-cut is verdict-neutral bar the marginal QMV crossing, and the
one signed verdict is safe. The box run must (a) confirm at full precision with the measured hurdle
σ, and (b) repeat on the estates NOT in factor_zoo.csv (the sector→stock books, the union, the
portfolios), where the σ profile — and thus the direction — must be measured, not assumed.

## §5 — Execution protocol (when the tree is quiet + on the VPS research env)

1. **Pre-register the direction** (hash-freeze, per the battery), from the §3 first-order result:
   "the low-vol 0.89 hurdle absorbs a ~0.40 penalty, so most (higher-vol) books' margins WIDEN;
   LOWVOL_MOM is ~neutral (σ≈hurdle); QMV is the one fail→pass crossing to confirm; no DSR
   pass→fail." The full-precision run can only confirm or surprise this — not be rationalised after.
2. **Re-cut ALL §1 sites in ONE commit** — never piecemeal (D142's standing instruction; a half-cut
   estate has some ratios rf-adjusted and some not, and every cross-comparison desyncs). Subtract the
   SAME per-period rf everywhere; re-cut the hurdle on the identical basis.
3. **Re-run on the VPS** (`.venv-research`), regenerate `strategy_runs` / `out/*.csv`, and **diff
   every ratio + every hurdle-comparison** old→new.
4. **Escalate every flip** (§4 list) to Ramana with the before/after and the σ that drove it — do not
   retire/re-sign any book autonomously (§4 #2). Non-flipping re-cuts land as honest numbers.
5. **Carve-outs stay** (D142): the `sharpe`/`sortino` **DB columns** and the CSV-seed headers keep
   their legacy names (CREATE TABLE IF NOT EXISTS can't migrate); the `rule_lab.py` BLOCKING rows are
   verbatim ledger quotes (the ledger wins). Also fold in the **S167 downside-deviation observation**
   (Sortino's denominator is `std(negatives)`, not textbook `sqrt(mean(min(r−MAR,0)²))`) — a second
   correction that moves the same numbers, so land it in THIS run, not separately.

## Retirement

Retire this doc (git rm) once the re-cut has landed and the verdict-diff is recorded in
`docs/strategy-ledger.md` + the affected `docs/strategies/*` pages + PROJECT_STATE. Until then it is
the single source for what the re-cut must touch and what it must not break.
