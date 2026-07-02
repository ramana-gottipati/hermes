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

The variants, precisely as implemented in `research/explosive_moves/factor_zoo.py` (i0 = rebalance
bar; ac = split-adjusted close; 126≈6mo, 252≈12mo, 66≈3mo trading days):

| Name | Formula | Reading |
|---|---|---|
| **MOM6** | `ac[i0]/ac[i0-126] − 1` | 6-month total return |
| **MOM12** | `ac[i0]/ac[i0-252] − 1` | 12-month total return (the classic) |
| **RISKADJ** | `MOM6 ÷ vol_66` | return per unit of recent (3-mo) volatility — **best Sharpe** |
| **LOWVOL** | `−vol_66` | prefers calm names (ballast, weak alone) |
| **LOWBETA (BAB)** | `−beta` (trailing 252 vs Nifty 50) | prefers low market sensitivity |
| **RESID_MOM** | `MOM6 − beta·idx_MOM6` | idiosyncratic (market-stripped) momentum |
| **HI52** | `range_pos_252` (position in the 52-wk high-low band) | proximity to 52-week high |
| **LOWVOL_MOM** | `0.5·rank(−vol) + 0.5·rank(MOM6)` | momentum with a low-vol tilt — **best drawdown/beta** |
| **QUAL_MOM** | `0.5·quality + 0.5·rank(MOM6)` | momentum filtered by capital-allocation quality (C) |

**Role decision (confirmed by the data):** the production form is **risk-adjusted / low-vol
momentum**, NOT raw MOM6/MOM12 (their β≈1.3 and −51% drawdowns are a leveraged-beta liability). Raw
momentum stays as an input to the ensemble, never the sole ranker. Value/quality are **never** a
standalone ranker (see BLOCKING FAILURE MODELS); C/A/B ride on top as veto/confirmation.

---

## Roadmap (the slow build — one step per session, Ramana steers each)

- **Step 2 — the canonical ensemble.** Decide the members + weights (candidate: MOM12 + HI52 +
  RISKADJ + LOWVOL_MOM, equal-rank-blend) and the normalization (cross-sectional percentile, size/
  sector-neutral?). *Open question for Ramana: equal-weight the 4, or tilt toward the risk-adjusted pair?*
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
*Status: Step 1 recorded. Awaiting Ramana's call on Step 2 (ensemble membership + weighting).*
