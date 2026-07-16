# D142 rf re-cut — PRE-REGISTRATION (predicted verdict-diff, hash-frozen before the box run)

> **Lifecycle: TRANSIENT (SEALED PREREG).** The frozen predicted verdict-diff for the D142 rf
> re-cut, registered BEFORE the full-precision box run so the result can only CONFIRM or SURPRISE
> it — never be rationalised after the fact. **HASH-FROZEN:** this file's SHA-256 is recorded in
> `docs/d142-rf-recut-plan.md` + PROJECT_STATE; ANY edit voids the seal. Retire with the plan doc
> once the re-cut LANDS and the verdict-diff is recorded. Registered in `docs/DOC_INDEX.md` §D.
> Authored 2026-07-17 (S169-cont, Opus strong-tier) — **laptop prep, ZERO numbers moved, no shared
> research module touched.**

## What this seals

The re-cut subtracts a real per-period rf at every §1 ratio/DSR input, in ONE commit, re-run on the
VPS `.venv-research`. This doc freezes the PREDICTED direction of the verdict-diff — computed
first-order on the laptop from the committed `research/explosive_moves/out/factor_zoo.csv` (per-book
`vol_ann_pct`) — so the box run is an adjudication, not an exploration. It does NOT run the re-cut
(both plan preconditions — tree-quiet + the VPS research env — are still unmet, verified 2026-07-17).

## THE FROZEN PREDICTION (plan §3: a true Sharpe deducts `rf/σ`, not a constant)

A true Sharpe `= (μ − rf)/σ = R − rf/σ`, where `R` is today's return/vol. The deduction is **`rf/σ`
per book** (lower-vol books penalised MORE). Because the **Nifty-500 hurdle is itself low-vol
(σ ≈ 16.4%)**, the bar takes one of the largest penalties (0.89 → ~0.49), so the re-cut **LOOSENS
most comparisons**:

1. **Higher-vol books' margins over the bar WIDEN** — RISKADJ +0.40→+0.55, QUAL_MOM +0.15→+0.26,
   MOM12/HI52 similar. No flip.
2. **LOWVOL_MOM ≈ NEUTRAL** (σ 16.7% ≈ hurdle σ → penalties cancel; Δmargin +0.01). **The S163
   human-signed NEW-BENCHMARK canon (#602, 1.19 vs 0.89) does NOT move.**
3. **QMV (quality+mom+value) is the ONE predicted CROSSING: −0.03 → +0.11 (fail→pass at the bar)** —
   the single expected flip. It is a factor-zoo leaderboard book, not a signed strategy.
4. **Already-rejected low-vol books fail HARDER** (LOWVOL σ11.7%, DEFENSIVE σ14.3%, LOWBETA σ15.6%) —
   more decisive rejection, no flip.
5. **NO DSR / Deflated-Sharpe pass↔fail flip** — the null is rf-free while the observed input is
   inflated today, so every DSR FAIL can only get STRONGER.
6. **rf-INVARIANT (cost-dominated) verdicts unchanged** — C-BLEND (1.32) and momentum (gross 1.29)
   stay rejected-on-cost (net < 0.89 at realistic AUM); cost dominates rf, so the re-cut can neither
   resurrect nor newly-kill them.

**Net predicted:** verdict-neutral on the factor estate bar the single marginal QMV crossing; the one
signed verdict (LOWVOL_MOM) is safe.

## FALSIFICATION (what a SURPRISE looks like — escalate, do NOT rationalise)

The box run FALSIFIES this prereg if ANY of:
- a book **NOT named above** (nor in plan §4's watch-list) crosses the bar in EITHER direction;
- any **DSR / Deflated-Sharpe** verdict flips pass↔fail;
- the **direction reverses** — a clear-margin higher-vol book's margin NARROWS, or the measured hurdle
  penalty is materially smaller than predicted so most comparisons TIGHTEN instead of loosen;
- **QMV does NOT cross** (a mild surprise — re-check the measured hurdle σ vs the ~16.4% implied here).

Any flip — the predicted QMV crossing included, and any unpredicted one especially — is **Ramana-only
per plan §4 #2**: escalate with the before/after and the σ that drove it; retire/re-sign NOTHING
autonomously.

## RE-VERIFIED §1 SITE INVENTORY (confirmed against current code 2026-07-17; line-drift from S170 noted)

All sites still compute raw `mean/sd × √periods` with NO rf subtracted, each still carrying its D142
disown comment. The re-cut subtracts the SAME per-period rf at each ratio/DSR input, in ONE commit.

| File (`research/explosive_moves/`) | Site (current line) | S170→now drift |
|---|---|---|
| `metrics.py` | `equity_stats` retvol/sortino :44-45 | unchanged |
| `factory.py` | `eqstats` retvol :45 · hurdle `bench` :153 · survivor-flag :165 — **highest fan-out** | unchanged |
| `factor_zoo.py` | `tearsheet` retvol/sortino :252 | unchanged |
| `attribution.py` | `deflated_sharpe` :314 · `retvol_ann` :368 · `rf_monthly` :277 · **`strat_ex = strat − rf` already in scope (:31/:38) — "the one-liner"** | :321→:314, :459-note→:38 |
| `cost_realism.py` | retvol :109, :148 | :144→:148 |
| `cost_participation.py` | retvol across the AUM grid :250, :287 (per plan) | to box-confirm |
| `cblend_cost_recut.py` | `BENCH_RETVOL = CP.BENCH_RETVOL` 0.89 :83 · D142 basis note :45 — **re-cut BOTH sides** | :211→:83 |
| `exit_lab.py`, `c_overlay.py` | descriptive ratio prints · exit_lab survivor `>0.89` :289-295 | unchanged |

**The hurdle moves too:** the `Nifty 500 = 0.89` bar is itself a return/vol ratio; its rf-adjusted
value must be recomputed on the identical basis or every comparison desyncs.

## rf SOURCE (plan §2) — box-verify before the run

`index_series("Nifty 1D Rate Index")` — NSE overnight TR rate index, Guardrail-#8 clean;
`attribution.rf_monthly()` already consumes it. Pre-2016 gap-fill: flat `RF_PROXY_ANN = 0.065` (rf is
a mean shift only, so the proxy cannot distort dispersion). **⚠ Box-verify** `index_rows` carries the
rate index, its first date (~2016), and that the proxy window is exactly pre-first-date.

## EXECUTION (plan §5) — still GATED, not run here

Runs only when BOTH clear: (1) **tree-quiet** — the union lane out of `research/` (as of 2026-07-17
still landing cross-checks, though its robustness suite is COMPLETE) — and (2) the **VPS
`.venv-research` + full `research.db`** (the laptop `data/research.db` is a 12 KB schema shell). Then:
re-cut ALL §1 sites in ONE commit + the hurdle on the identical basis; **fold in the S167 Sortino
downside-deviation correction** (same numbers move); diff every ratio + hurdle-comparison old→new;
escalate every flip. Carve-outs stay (D142): the `sharpe`/`sortino` DB columns + CSV-seed headers keep
legacy names; `rule_lab.py` BLOCKING rows are verbatim ledger quotes.
