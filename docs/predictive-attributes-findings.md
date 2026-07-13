# Predictive attributes — consistency & reliability (deep dive, 2026-07-02)

> **⚠ READ FIRST — the honest headline (updated 2026-07-02 with attribution + participation-cost results).**
> Every Sharpe/alpha below is **GROSS, flat-cost**. Two rigor passes settle what it really is:
> 1. **It's momentum-BETA, not selection alpha — PROVEN, and RE-VALIDATED under no-leak PIT (AUD-22, 2026-07-13).**
>    (`research/explosive_moves/attribution.py`, 7-factor Newey-West.) Controlling for the generic momentum
>    factor (WML)+market, RISKADJ's residual α falls to **+6.69%/yr, HAC t=1.80 → fails the t≥3 selection
>    bar; WML now eats 58% of the raw α.** It is 0.98×market + 0.66×a generic momentum premium + a
>    short-low-vol tilt (BAB −0.53). The momentum premium itself is real (Fama-MacBeth λ t=3.30,
>    Deflated-Sharpe 0.963, PBO 0.357) but **un-proprietary**. Survivorship second-order (Sharpe +0.00).
>    **AUD-22 note:** the original numbers (**+7.3%, t=1.99**, WML 51%) were computed on the leaky +90/+50
>    modeled `report_date` (the house's own PIT layer documents it leaks ~12% for late filers). Re-running
>    the attribution through the provenance **effective-date map** (`fundamentals_asof`; real BSE filing
>    date, else the conservative calibrated lag) LOWERED the residual-α t (1.99 → 1.80) and RAISED WML's
>    share (51% → 58%) — i.e. **correcting the leak strengthened, not weakened, the "beta not skill"
>    verdict.** The conclusion is robust to the fix.
> 2. **Net of realistic cost it's small-capacity, not scalable** (`cost_participation.py`): quarterly
>    large-cap LOWVOL_MOM nets Sharpe **1.02 at ₹50cr (beats Nifty-500), ~breaks even ₹100-150cr, 0.61 at
>    ₹500cr** — a ₹50-100cr DEFENSIVE tilt, not a large-scale edge. (This corrected the earlier AUM-blind
>    "nothing beats the index net.")
> ⇒ Treat everything here as a **GROSS momentum-factor SELECTION lens** — not proprietary alpha, not a
> scalable strategy. The defensible asset is PIT rigor + the data. See `docs/institutional-panel-assessment.md`.

**Question:** which attributes/dimensions actually forecast forward price moves in Indian equities, how *consistent* (holds across time/regimes) and *reliable* (statistically trustworthy, not overfit) are they, benchmarked to the index?

**Method:** live 14-year backtest via `research/explosive_moves/factor_zoo.py` — 157 monthly rebalances (2012-06→2026), 3,515-symbol cache (1,700 with fundamentals), top-25 equal-weight, value-turnover gate, net cost, walk-forward halves (2012-18 vs 2019-26), alpha/beta vs **Nifty 500**. Discussed with Codex (gpt-5.5): methodology `codex-bridge/req/resp-16`, results interpretation `req/resp-17`. Full table `research/explosive_moves/out/factor_zoo.csv`.

## The framework (what "consistency" vs "reliability" mean here)
- **Consistency** = `survives_both_halves` (positive Sharpe in BOTH 2012-18 and 2019-26) + monthly win-rate. Does the edge repeat out-of-sample.
- **Reliability** = Sharpe / profit-factor / alpha — **but haircut** for: (1) multiple-testing (15 factors ranked by Sharpe → the top rank carries a selection premium; trust the *family*, not rank #1), (2) **leveraged beta** (winners run β 1.2-1.33 → part of the "alpha" is levered smallcap beta in a rising tape), (3) survivorship (the 3,515 cache is survivor-tilted).

## Results (ranked by Sharpe; α = annual vs Nifty 500)
| factor | Sharpe | MaxDD | α | β | survives |
|---|--:|--:|--:|--:|:--:|
| RISKADJ (mom6/vol) | 1.29 | -42% | +16.5% | 1.18 | ✓ |
| MOM12 | 1.20 | -50% | +16.8% | 1.33 | ✓ |
| LOWVOL_MOM | 1.11 | -34% | +6.0% | 0.82 | ✓ |
| HI52 (52wk-high) | 1.10 | -39% | +9.6% | 0.99 | ✓ |
| QUAL_MOM | 1.05 | -29% | +8.2% | 1.05 | ✓ |
| RESID_MOM | 1.01 | -51% | +11.3% | 1.32 | ✓ |
| MOM6 | 1.01 | -51% | +11.1% | 1.32 | ✓ |
| VAL_MOM | 0.90 | -64% | +5.6% | 1.33 | ✗ |
| QMV | 0.89 | -52% | +5.1% | 1.16 | ✗ |
| DEFENSIVE | 0.86 | -26% | +1.5% | 0.70 | ✗ |
| LOWVOL | 0.84 | -27% | +1.3% | 0.56 | ✗ |
| QUALITY | 0.76 | -44% | **-0.1%** | 1.03 | ✗ |
| EARN_YIELD | 0.71 | -71% | +0.5% | 1.35 | ✗ |
| LOWBETA (BAB) | 0.69 | -28% | +1.4% | 0.61 | ✗ |
| BOOK_YIELD | 0.63 | **-82%** | **-1.8%** | 1.54 | ✗ |

## Findings
1. **Momentum is the only consistent + reliable forward-price engine.** All 7 survivors are momentum or momentum-adjacent — too coherent to be luck (the *family* is real; the exact best variant is not stable enough to crown).
2. **The production form is RISK-ADJUSTED / low-vol momentum, not raw momentum.** RISKADJ (1.29), LOWVOL_MOM (1.11, β0.82, MaxDD-34%), HI52 (1.10) beat raw MOM6/MOM12 on risk-adjusted terms — raw momentum's β1.3 / MaxDD-51% is a leveraged-beta liability.
3. **Standalone value AND standalone quality do NOT beat the index here.** QUALITY α-0.1%, EARN_YIELD +0.5%, BOOK_YIELD -1.8% (MaxDD-82%). They only add value *attached to momentum* (QUAL_MOM survives, +8.2%; VAL_MOM +5.6% but fails OOS). This is NOT "value is dead" — it's "naive standalone value is not a long-ranker in this universe/period" (survivorship, monthly churn buying traps, no quality guardrail).
4. **The reported alpha is overstated as skill.** Momentum winners' +11-17% α is partly levered small/midcap beta in a structurally rising 2012-26 tape. A true-selection claim needs beta+size+sector+liquidity-neutral residual-alpha attribution (queued).
5. **Our event feeds A/B (insider, credit) are not IC-testable** (4-6 months, event-sparse) → correct treatment is event-study / veto overlay, never a cross-sectional factor, until years accrue.

## Implication for the C/A/B layer (empirically confirms D66)
Three independent lines now agree — the Codex ROI debate, the confluence forward-return test, and this 14-year factor study — that **C (capital-allocation/quality), A (insider), B (credit) are a RISK-FILTER / veto / conviction layer, NOT standalone return-rankers.** The engine is **price strength (momentum/RS/DVPT)**; C/A/B veto (debt stress, pledge, downgrades, dilution, bad allocation) and amplify conviction when they agree. "C is not the engine; it is the braking system, suspension, and confidence score around the engine." (Codex, resp-17.)

## What to stake on (verdict)
- **Primary:** an *ensemble* of momentum definitions (MOM12 + HI52 + RISKADJ + LOWVOL_MOM) — never one lucky lookback.
- **Risk control:** volatility/low-beta as ballast; C/A/B as veto.
- **Never:** standalone value or standalone quality as a long-ranker; a single "best-Sharpe" factor.

## Regime risk & hedges (this ranking is conditioned on a momentum/smallcap-friendly 2012-26)
Breaks in a sustained mean-reversion / liquidity-shock / smallcap de-rating (momentum crash, beta reversal, sector-rotation, valuation reset). Hedges: ensemble the momentum defs; cap portfolio beta & sector concentration; market-regime gates (index vs long MA, breadth, vol spike → shrink book); liquidity buffers beyond modeled cost; keep C/A/B as veto; a valuation "don't-overpay" throttle (not a long signal); track live decay and cut weight if forward hit-rate deteriorates 6-12 months rather than arguing with the tape.

## Honest caveats
Survivorship in the symbol cache; sparse fundamentals (empty-slice warnings on quality/value composites); alpha not yet beta/size/sector/liquidity-decomposed; single macro-regime; the value-turnover gate may contaminate the standalone-value read. These bias toward momentum/quality and against value — treat the value rejection as "not a production ranker," not a universal truth.
