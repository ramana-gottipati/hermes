# §C CCI credibility backtest — methodology of record + review (2026-06-26)

> **Status:** design-of-record + an independent panel review. The backtest itself
> (`src/automation/cci_backtest.py`) is being built in a **parallel session's lane** — this doc
> is isolation-safe input for that lane, NOT a competing module. Authored after a read-only panel
> (quant/backtest · buy-side financial-analyst · adversarial quant-diligence red-team) was convened
> on this exact problem. Fold the durable parts into `docs/concall-intelligence-design.md` when the
> lane stabilises.

## The question
The wedge: *a management-credibility signal that FRONT-RUNS price re-ratings.* Everything is
DESCRIPTIVE-ONLY until this test decides **factor** (ship a measured-edge claim / unlock the gated
`/v1` alpha faces) vs **avoid-overlay only** (the deterioration veto; no performance claim).

## The parallel first-pass (`cci_backtest.py`) — what it gets RIGHT
A genuinely honest directional falsification: returns from the as-of **month-end** (PIT intent);
**de-markets** by subtracting the same-as-of-month cohort mean (cross-sectional excess, not market
beta — kills the rising-tide base-rate); tests **level** (high vs low tercile) AND **momentum**
(rising/flat/**falling**); corporate-action-adjusted via the `prev_close` chain; winsorized; t-stat
+ hit-rate; and a verdict that can return **LONG-REJECTED / INVERSE** or **INCONCLUSIVE** and keep
CCI descriptive — with the survivorship bias **disclosed in the caveats**. This is the right spirit
(don't ship unproven alpha) and a valid v1.

## CRITICAL GAPS (panel) — close these BEFORE any "measured-edge" claim
Ordered by how badly each can manufacture a FALSE positive:

1. **PEAD / earnings-surprise circularity [analyst #1 — the thesis is ~70% likely momentum-in-disguise].**
   Credibility is computed FROM delivered results, so "credibility rose → price followed" can be
   post-earnings-drift twice-named. The de-market step does NOT remove this. **Fix:** orthogonalise
   the signal to a standardized earnings surprise (SUE) + 12–1 price momentum, OR condition on the
   surprise sign (among names that beat/missed consensus by the *same* amount, does higher
   guidance-**calibration** `ga` still predict?). The novel, non-circular kernel is `ga`/`qr`, not the beat.
2. **Dual look-ahead leak [quant #1 — CONFIRMED in code].** (A) settlement timing: `credibility_series.level`
   at T uses promises "resolved-by-T" via fundamentals' **MODELED** `report_date = period_end+90/50d`,
   which can be earlier than the real filing → the signal knows a result before the market. (B) entry
   timing: the first-pass enters at the **fiscal period month-end** (`period_year/period_month`), but a
   "Q4 (Mar)" concall actually happens in late-Apr/May — so a Mar-31 entry is likely **before the call
   was public**. **Fix:** enter at the REAL concall clock `COALESCE(concall_dt, transcript_publish_dt,
   result_filing_dt)` from the `concalls` table (the same columns `provenance.PROVENANCE["concall_corpus"]`
   registers), never the period label; add a `--lag-mode {real|lag30|modeled}` **kill-switch** — if the
   edge survives only under `modeled`, it was look-ahead → force AVOID_OVERLAY. ⚠️ **Verify (B) first:**
   confirm whether `period_month` is the fiscal-period-end or the concall month; if the former, the
   current entry is leaky.
3. **Survivorship via the real spine [red-team].** The first-pass samples *current concall holders*
   (disclosed bias). **Fix:** gate the universe on `security_master.universe_on(as_of)` (delisted
   retained) + `canonical()` rename-stitch + truncate journeys at `has_break_between()`.
4. **No cost model [red-team — the org's own killer].** The org's prior strategies died net-of-cost
   (Sharpe 1.29→0.09; ~₹30cr capacity). A cross-sectional *excess*-return falsification tolerates gross
   for DIRECTION, but any edge claim must report **net** (tier-spread by turnover/mcap proxy: ~1.5%/0.6%/
   0.25% + STT/fees, round-trip) and a **capacity** number.
5. **No placebo / no real OOS split [red-team falsification].** Add a **random-credibility shuffle**
   (must show NO effect — else it's the trend) and a **walk-forward** train/holdout (pass required on the
   holdout, not pooled). The falling-arm should **invert** (it's tested — good; assert the inversion).
6. **Small-sample stats [red-team].** Overlapping forward windows ⇒ autocorrelation ⇒ the parametric
   t-stat overstates. **Fix:** percentile/block bootstrap CI + date/symbol-clustered errors; Wilson
   intervals for hit-rate; a pre-stated **min-n** (the most likely honest first verdict is
   **INCONCLUSIVE_LOW_N** given the paused, thin robust core).
7. **Pre-registration / multiple testing [red-team].** level × momentum × 3 horizons = several cuts.
   **Fix:** pre-register ONE primary cut (the divergence: rising credibility + lagged price, 6m, robust
   core ≥10 resolved, vs a momentum-matched control), hash the thresholds, FDR-correct the rest.

## The pre-registered GATE (lock BEFORE peeking; the panel's accepted criteria)
`FACTOR` requires ALL, on the **OOS** slice, **robust core (n_resolved ≥ 10)**:
- n_oos ≥ 40 (else `INCONCLUSIVE_LOW_N`);
- median(net edge vs **momentum-matched** control, 6m, size-tier-relative) ≥ +4% AND bootstrap 95% CI lower bound > 0;
- lead-time hit-rate ≥ 0.55; median lead ∈ [10, 189] trading days; went-wrong ≤ 0.25;
- placebo null; falling-arm inverts; survives the `lag30` leak kill-switch.
- **STRUCTURAL:** `FACTOR` is unreachable until the **surprise-control (SUE)** is done — until then the
  best verdict is `FACTOR_CANDIDATE_PENDING_SUE`. `FAIL → avoid-overlay only`: the product must NOT
  cite any edge/Sharpe/hit-rate in marketing or imply credibility predicts re-rating; CCI ships only as
  the descriptive deterioration/risk flag.

## Lead-time artifact (the headline visual, prospective — not in the first-pass)
Define the price-strength event PROSPECTIVELY from the as-of-T trigger (fwd return ≥ +10% held 5 days);
measure the lead in trading days over ALL triggers (count the **misses** — never-followed + went-wrong);
compare to a no-signal control lead. Never condition on names that DID re-rate (selection on the outcome).

## Run posture
VPS-only real run (local = 4-symbol stub); READ-ONLY (the module owns only its outcomes table). Run all
three `--lag-mode` values every time so the leak kill-switch is always measured. Stamp the coverage/
robust-core funnel (`provenance.coverage_snapshot`) on every output. Most probable honest first result:
**INCONCLUSIVE_LOW_N** — which is shippable as "not yet proven," not a failure.

— Full panel transcripts: quant `a5cc61fe71453f3da`, analyst `a9830afc0eadad7bf`, red-team `ab102899fe7a243c3`.
