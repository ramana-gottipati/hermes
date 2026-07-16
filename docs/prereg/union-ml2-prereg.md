# PRE-REGISTRATION — walk-forward ML ranker v2, over the ERA-FLOOR qualifier pool

> **Class:** PRE-REGISTERED walk-forward ML experiment, the declared successor to
> `union-ml-prereg.md` (16AA: M1 Ridge REJECTED; "any future ML attempt is a NEW pre-registration —
> an M2-shaped shallow GBM is the declared starting point"). Hashed and committed BEFORE any
> training run; edits after the run void it.
> **Registered:** 2026-07-16 (S172-lane; Ramana: "Raise the CAGR target to 30... Let us make it").
> **Origin:** 🧑 RAMANA (the 30% directive, the AI mandate) + 🏠 HOUSE (design, discipline).
> **Governance:** the sibling family is CLOSED at three seals — a PASS here earns DEFERRED-LEAD
> status beside ledger 16AE's, never a registration, pending the 2026-10-03 forward verdict or
> Ramana reopening the family.

## What changed since 16AA (why a v2 is legitimate)

1. **The qualifier pool changed materially:** the era-relative ADV floor (ledger 16AE, A2 variant)
   roughly doubles the early-era union qualifier cross-section. 16AA trained on 1,988 rows; this
   pool is substantially larger — more data is the one honest new ingredient.
2. **The declared model shape rotates in:** 16AA's exploratory M2 (shallow GBM) becomes PRIMARY,
   exactly as 16AA pre-committed. Ridge becomes the exploratory reference.
3. **The bar rises:** the comparator is no longer the plain union — it is the A2-composite
   machinery itself (RISKADJ-rank on the capped era-floor pool), the current deferred lead.

## Honest prior (stated before the run)

Momentum here is beta-not-skill (t = 1.99 → 1.80 PIT, AUD-22). 16AA's primary failed its bar, and
its one durable output was that beta is the #1 feature — already exploited by the β-cap. The GBM
must now beat a hand rule (RISKADJ-rank) that the 16AA models themselves helped validate. A loss
is the EXPECTED outcome and will be recorded as such.

## THE FROZEN DESIGN (any change voids the registration)

**Machinery.** The A2-composite base exactly (ledger 16AE): union signals → era-relative floor
(monthly percentile, P = 0.450, clamped ≥ ₹1cr) → per-name trailing-250d beta ≤ 1.4 cap → **the
model ORDERS the capped qualifiers** (replacing RISKADJ-rank; everything else identical: top-40,
1/40 slots, Next-50 sleeve @200DMA with rf-earning bear-cash, trail −20% @1% slip, 0.15%/side,
quarterly, same-close convention with the D5-F1 lagged variant reported).

**Features:** the identical 10 of `union-ml-prereg.md` (leg, RSI, RSI-gap, consistency, RSI-of-RS,
turn-age, 250d beta, 63d sector-excess, 126d RS-drawdown, 63d vol), within-date midrank
percentiles, missing → 0.5. **Label:** within-date midrank percentile of forward rebalance-window
excess return vs Nifty 500 (dead names at −50% per the engine convention).

**Models — declared now, trained once, never tuned:**
- **M1 (PRIMARY): GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=2,
  subsample=0.8, random_state=42).**
- M2 (exploratory, reported only): Ridge(alpha=1.0).

**Split.** TRAIN: rebalance dates whose label window closes ≤ 2016-12-31, over the capped
era-floor qualifiers. TEST: rebalance dates ≥ 2017-01-01. ONE frozen fit; no expanding window, no
hyperparameter search, no test iteration.

## PASS / FAIL — frozen before the run (judged on the 2017-01 → 2026 test window)

1. **M1 book beats the A2-COMPOSITE (RISKADJ-rank, same window, same engine) on CAGR AND alpha.**
2. **M1 book beats the engine-order CONTROL (capped era-floor top-40, no rank) on CAGR AND alpha.**
3. **M1 book beta ≤ 1.0.**
4. **M1 book MaxDD not worse than the A2-composite's by more than 3pp.**
5. **@2% stop-slip, the M1 book still beats the A2-composite's same-window CAGR** (stress is
   first-class on this small-cap-tilted base).

Fail ANY → **REJECTED — recorded with the numbers, no re-run, no variant shopping.** A pass earns
DEFERRED-LEAD status only. 2012–17 is TRAINING data — no OOS claim about that regime, restated.

## What is NOT claimed

Not that a pass reaches 30% (that is a target, not a promise); not that feature importances are
causal; not that institutional capacity exists (personal-scale, per 16AE's character disclosure).

## Canon

Runner: `research/explosive_moves/union_ml2.py` (this design verbatim). Results: a
2026-07-16-lettered ledger entry. Predecessor: `union-ml-prereg.md` (`187c6aa4…`, 16AA). SHA-256
of this file recorded in the landing commit and the ledger; the run happens only after this file
is committed and pushed.
