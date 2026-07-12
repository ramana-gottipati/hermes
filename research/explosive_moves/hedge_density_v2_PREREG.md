# hedge_density_v2 — PRE-REGISTRATION SPEC (frozen 2026-07-13)

Status: **DESIGN / NOT BUILT.** This is the frozen pre-registration for a *successor* study to the
`hedge_density` null (docs/strategy-ledger.md, 2026-07-12/13). It exists so the hypothesis + gate are
fixed **before** any run. When built, this text becomes the `hedge_density_v2.py` module `__doc__` and is
hashed by `prereg.py --register-all` before the first `--run`. **Do NOT edit `hedge_density.py` to add any of
this** — v1 is a frozen recorded null; v2 is a new module with its own hash.

Co-designed by the code+data review (external reviewer Codex + internal panel), 2026-07-13.

## Why v2 (what v1's data review found)
v1 `hedge_density` was **FAIL-null** *and* mis-specified: 64.7% of its "hedge" hits are five ubiquitous
modals (would/should/may/could/maybe), so it measured **modal/conditional-language density**, not conviction
erosion; its SPIKE tercile is **50–59% Q2 FY-end-guidance-season calls** (a calendar confound within-name
differencing does not remove). v2 fixes construct validity **and changes the outcome** to the more plausible
target.

## MANDATORY LEDGER CITATION (do not run without acknowledging)
Every prior event-return wrapper net-failed 0.02–0.10 Sharpe vs 0.85 buy-hold; `concall_intent` was
placebo-killed; v1's return hypothesis failed wrong-sign. v2 is **descriptive-only** — no book, no ranking,
no buy/sell — and is expected to be *likely null*. It ships a descriptive lens only if the gate passes.

## PRIMARY HYPOTHESIS (changed outcome)
Quarter-adjusted, polarity-corrected **management** uncertainty language predicts **higher forward
idiosyncratic realized volatility** (not return alpha). "Management uncertainty → outcome uncertainty" is the
cleaner hypothesis and may pass where the return study failed. CAR60 is reported **only as a secondary null**.

## FEATURE (all changes vs v1 are the point)
1. **Register-split + IDF/cap weighting** — score weak-modal, uncertainty, and confidence registers
   separately; weight each term by corpus document-frequency (IDF) and **cap the weak-modal register** so
   ubiquitous modals cannot dominate. Weights frozen from the transcript corpus only (never from returns).
2. **Net tone** = weighted_uncertainty − weighted_confidence, per 1,000 management-answer tokens. (A confident
   description of external uncertainty must not read as hedging.)
3. **Negation handling** — `no/not/without/never` within 3 tokens before concern/doubt/uncertainty/visibility
   suppresses or flips the hit ("no doubt", "good visibility", "no concerns" are NOT hedges).
4. **Overlap de-dup** — longest-phrase match first; consumed token spans cannot also score as unigrams
   (v1 triple-counted "difficult to say").
5. **Drop standalone "may"** (month-May contamination; ubiquitous anyway).
6. **Q&A / management-answer segmentation** — score management *answers* only (operator/Chorus-Call markers
   segment deterministically); analyst-question tone is a *separate* diagnostic, not the feature.
7. **Numeric specificity** (secondary descriptor) — digits/%/₹-amounts per 1,000 words; low specificity + high
   uncertainty is the sharper state. Lexicon-free, transcription-robust.
8. **Transcript-validity filter** — exclude non-transcript / stub docs (e.g. the v1 zero-hedge rows:
   8 short stubs + INTELLECT/TRACXN mis-filed docs) via a function-word/char-class rule before scoring.

## DIFFERENCING (removes v1's seasonal confound)
**Within-name × within-calendar-quarter double-difference:** residual = call score − prior same-symbol
**same-calendar-quarter** baseline (≥2 prior same-quarter calls, else exclude). Kills the FY-end-guidance
seasonal step that dominated v1's spike tercile.

## COHORTS
Compute v2 score per eligible call; disjoint rank terciles (top = uncertainty spike, bottom =
confidence/clarity control). Require **n ≥ 100** usable spike events. Report distinct spike symbols separately
from event count (v1's honest breadth was 1,097 delta-eligible symbols / ~700–900 spike symbols, not 1,573).

## PLACEBO (M-02, evlib)
Same event set, random eligible dates **within symbol and calendar quarter**, n=500, seed fixed before run.
Primary statistic = mean forward abnormal realized-vol uplift. Report observed · null mean · null p95 ·
empirical p · inflation ratio.

## PASS-DESCRIPTIVE GATE (all must hold)
1. Spike forward abnormal realized vol > 0 **and** spike > drop.
2. Same sign in both halves, split at the **chronological event-count median** (~2023-12), not a fixed date
   (v1's 2021-07-01 sat at the ~20th event-percentile — low power).
3. Placebo clears p95 / inflation_x > 1.
4. Cliff's δ(spike, drop) ≥ +0.10 on the vol uplift.
5. CAR60 remains secondary and cannot create a pass.
FAIL → publish the null to the ledger, citing this spec.

## SEPARATE DIAGNOSTICS (not the feature; descriptive)
Analyst-question skepticism tone; market-wide "hedging tide" (composition-adjusted aggregate vs Nifty
drawdowns); answer evasiveness (non-answer rate). Report only; never ranked.

## GATE TO BUILD (cost discipline)
Build the full module only if the **modal-vs-uncertainty pulse-check** (reuse v1 machinery: re-run the
existing *return* study on uncertainty-only vs modal-only deltas) shows the pure-uncertainty register carries
*any* pulse. If uncertainty-only is also null/wrong-sign on return, the return angle is dead — but the
realized-vol outcome is independent and may still warrant v2.

### PULSE-CHECK RESULT (2026-07-13, run on the box — return angle) → RETURN ANGLE DEAD
Same study, split by register (CAR60 is register-independent, computed once per event; 15,831 events, 1,573
symbols, 11,709 deltas):
- composite (= v1): SPIKE +1.44% / t_cohort +0.41 / DROP +0.37 — reproduces the published null.
- modal-only:       SPIKE +1.94% / t_cohort +0.95 / DROP +0.62 — wrong-sign noise; drives the composite.
- uncertainty-only: SPIKE **+0.60%** / t_cohort **+0.45** / DROP +1.40 — SPIKE sits BELOW DROP (−0.80%
  relative contrast, the predicted direction, absent/reversed in the modal register), so the construct DOES
  carry directional info the composite masks — BUT the spike is still absolutely POSITIVE (wrong sign vs the
  hypothesis) and insignificant.
**Verdict: the RETURN hypothesis is dead** (no absolute underperformance, no significance) — do NOT build a
return study. The register split is a *mild* encouragement that net-tone/register-weighting matters, but the
only genuinely-untested angle is the **realized-VOLATILITY** outcome, which this cheap return pulse-check does
NOT exercise. Recommendation: keep this spec frozen; build the full (vol-outcome) v2 ONLY on an explicit
decision to test volatility, weighed against the failure-ledger (event-wrappers net-fail).
