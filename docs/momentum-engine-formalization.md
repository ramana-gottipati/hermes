# Momentum engine — formalization (living spec, built slowly, step by step)

**Purpose.** Formalize how we turn the empirical finding (momentum is the only consistent+reliable
gross forward-price signal in Indian equities — `docs/predictive-attributes-findings.md`) into a
precise, production selection engine — the daily "surface the relevant stocks" run of the
[[primary-intent-north-star]]. Built incrementally; each step is confirmed with Ramana before the next.

## The two-layer truth (must be stated on every surface — non-negotiable)
1. **GROSS selection edge — REAL.** Ranking by risk-adjusted / low-vol momentum has out-selected the
   index over 14 years, walk-forward, both halves (RISKADJ Sharpe 1.29, LOWVOL_MOM 1.11, HI52 1.10).
2. **NET-of-cost alpha — DOES NOT EXIST here.** Under realistic slippage (~0.5×ATR, ~100%/mo turnover
   → ~36%/yr) that 1.29 collapses to ~0.09; nothing beats Nifty-500 buy-&-hold net of cost
   (`docs/strategy-ledger.md` § cost realism, § BLOCKING FAILURE MODELS).

⇒ **The engine is an analytical SELECTION / ranking lens that surfaces stocks for research, NOT a
fundable "buy this basket" alpha claim.** Any tradable form must be low-turnover and is defensive, not
alpha. This caveat travels with every number we show.

---

## Step 1 (DONE) — exact definitions + the role decision

The precise variant formulas and every internal weight live in the single source of truth —
**`docs/calculations-and-weights.md` §1** (canonical code: `research/explosive_moves/factor_zoo.py`).
Not restated here, by the no-repetition rule.

**Role decision (confirmed by the data):** the production form is **risk-adjusted / low-vol
momentum**, NOT raw MOM6/MOM12 (their β≈1.3 and −51% drawdowns are a leveraged-beta liability). Raw
momentum stays as an input to the ensemble, never the sole ranker. Value/quality are **never** a
standalone ranker (see BLOCKING FAILURE MODELS); C/A/B ride on top as veto/confirmation.

---

## Roadmap (the slow build — one step per session, Ramana steers each)

- **Step 2 — the canonical ensemble. DECIDED 2026-07-02: EQUAL-WEIGHT** MOM12 + HI52 + RISKADJ +
  LOWVOL_MOM (0.25 each, on cross-sectional percentile ranks). Rationale + the maintained numbers live
  in `docs/calculations-and-weights.md` §2 (the un-overfit prior; risk-awareness already inside the
  members; a risk-adjusted tilt is a recorded alternative to test, not the default). Size/sector-
  neutralisation deferred to the attribution study.
- **Step 3 — regime gates.** When to shrink/expand the surfaced set: index vs long MA, breadth
  (% above 200DMA), vol spike, drawdown state. Momentum crashes are the main failure mode.
- **Step 4 — the veto/confirmation layer.** Wire C (capital-allocation) + A (insider/pledge) + B
  (credit) as filters/amplifiers on the momentum selection (the confluence board), never as the ranker.
- **Step 5 — cost/turnover-aware form.** Hold-band + rebalance cadence for any fundable expression
  (the only form that survives cost — and honestly label it defensive, not alpha).
- **Step 6 — productionize the daily surface.** Materialize a momentum-ensemble score on
  `stock_signals` (which already carries RS/momentum columns) → the daily "one-click index-component +
  stock insights" run of the north-star intent, with the two-layer caveat + glossary (explain the term,
  never leak the formula).
- **Step 7 — live tracking + decay monitor.** Record forward hit-rate / residual alpha; cut weight if
  it deteriorates 6-12 months rather than arguing with the tape. Every run recorded in the ledger.

**Adjacent analysis that would sharpen Step 2 (queued):** beta/size/sector/liquidity-neutral
residual-alpha attribution — to see how much of momentum's edge is genuine selection vs levered
small/midcap beta. Until run, treat momentum's *direction* as reliable and its *magnitude* as
provisional.

---
*Status: Steps 1-2 recorded (ensemble = EQUAL-WEIGHT of the 4 survivors; all formulas/weights in
`docs/calculations-and-weights.md`). Next: Step 3 (regime gates) — or run the beta/size/sector-neutral
attribution first to confirm the edge is real selection before productionising.*
