# resp-17 - Interpret the REAL factor_zoo results

## 1. Overfitting haircut: what is real vs lucky?

The raw Sharpe table should not be read literally as "RISKADJ is the best factor." With 15 tried factors, monthly rebalance data, overlapping factor definitions, sparse fundamentals, and a survivorship-tilted universe, the top rank has a meaningful selection-bias premium. A deflated-Sharpe lens should haircut the top few names and ask whether the broad economic family survives, not whether rank #1 beats rank #2.

My read:

| Bucket | Factors | Verdict |
|---|---|---|
| Reliable core | RISKADJ, MOM12, HI52, LOWVOL_MOM | Momentum is real. The exact best variant is not stable enough to crown. |
| Reliable as a modifier | QUAL_MOM, LOWVOL_MOM | Quality/low-vol help most when attached to price strength. |
| Probably real but fragile | MOM6, RESID_MOM | Same momentum family, but higher drawdown / higher beta makes implementation riskier. |
| Defensive/risk-control, not alpha engine | LOWVOL, LOWBETA, DEFENSIVE | Useful ballast, weak standalone excess return. |
| Not reliable from this test | VAL_MOM, QMV, QUALITY, EARN_YIELD, BOOK_YIELD | Either failed OOS halves, sparse fundamentals, or unacceptable drawdown. |

The important point: seven of the top seven are momentum or momentum-adjacent, and all seven survive both halves. That is too coherent to dismiss as pure luck. The exact ordering is likely lucky; the family signal is not.

I would not ship a single "best Sharpe" factor. I would ship a composite that treats momentum as the primary predictor and uses volatility/quality/liquidity as risk controls.

## 2. Alpha vs leveraged beta

The +16% alpha for RISKADJ and MOM12 is almost certainly overstated if read as pure stock-selection skill.

The high-beta winners:

| Factor | Alpha | Beta | MaxDD |
|---|---:|---:|---:|
| RISKADJ | +16.5% | 1.18 | -41.9% |
| MOM12 | +16.8% | 1.33 | -49.6% |
| RESID_MOM | +11.3% | 1.32 | -50.7% |
| MOM6 | +11.1% | 1.32 | -51.3% |

In a structurally rising 2012-2026 Indian tape, especially one favorable to mid/smallcaps, beta 1.2-1.3 mechanically helps. A top-25 equal-weight book also likely carries size, liquidity, and cyclicality exposures that are not captured by only benchmarking against Nifty 500.

The honest decomposition should be:

1. Regress monthly portfolio excess returns on Nifty 500 excess returns.
2. Add size exposure: Nifty Midcap / Smallcap minus Nifty 500, or at minimum a smallcap index spread.
3. Add sector exposures, because momentum can become sector concentration.
4. Add liquidity/turnover exposure, because a value-turnover gate can still leave a liquidity premium.
5. Then test residual alpha and t-stat, not just annualized alpha.
6. Repeat by subperiod and by market state: up months, down months, crash months, recovery months.

If RISKADJ still has positive residual alpha after market + size + sector + liquidity controls, then it is true stock selection. If the residual collapses, it is mostly a levered small/midcap risk-on proxy.

Current inference: momentum has real stock-selection content, but the reported +16% alpha should be haircut heavily until beta/size/sector-neutral attribution is run.

## 3. Is value dead in India?

No, this does not prove value is dead in India. It proves this implementation of standalone value is not a reliable long-only monthly top-25 predictor in this universe and period.

Why I would not overgeneralize:

1. The universe is likely survivorship-tilted. Survivorship usually flatters winners that lived long enough to remain in the cache, which tends to flatter momentum and quality more than distressed value.
2. Value often needs longer holding periods than monthly top-25 churn. Cheapness can stay cheap for years; monthly rebalance may repeatedly buy traps before the catalyst arrives.
3. Indian accounting and sector mix make simple book yield especially dangerous. Financials, cyclicals, asset-heavy businesses, public-sector names, and stressed balance sheets can dominate naive book-value screens.
4. EARN_YIELD and BOOK_YIELD need quality and balance-sheet guardrails. Cheap + deteriorating is not value; it is often a bankruptcy/PSU/cyclicality trap.
5. The "value-turnover gate" may contaminate interpretation. If every factor is already liquidity/value-turnover gated, standalone value is not a clean orthogonal test.
6. Sparse fundamentals generated "mean of empty slice" warnings, so the composite value/quality results may include missing-data artifacts.

The empirical result is still useful: naive standalone value is not allowed into Hermes as a long ranker. If value is used, it should be conditional:

- value after quality pass,
- value after price-strength confirmation,
- value as a re-rating/catalyst feature,
- value as a "do not overpay" throttle,
- not value as "buy cheapest top 25."

BOOK_YIELD at -82.4% MaxDD is a hard rejection for production ranking.

## 4. Implication for C: capital-allocation / quality

Yes. This strongly supports D66: C should be a risk filter, veto, tie-breaker, and conviction amplifier, not a standalone long-ranker.

The key contrast:

| Factor | Sharpe | Alpha | Survives both halves |
|---|---:|---:|---|
| QUALITY | 0.76 | -0.1% | no |
| QUAL_MOM | 1.05 | +8.2% | YES |
| DEFENSIVE | 0.86 | +1.5% | no |
| LOWVOL_MOM | 1.11 | +6.0% | YES |

That pattern is clear: quality alone does not predict enough forward return in this test, but quality attached to momentum improves the trade. This is exactly what we want from C.

Practical doctrine:

- Momentum/RS/DVPT can nominate candidates.
- C can veto fragile balance sheets, fake earnings, bad capital allocation, promoter abuse, debt stress, and low-quality cyclicality.
- C can upgrade a momentum candidate when reinvestment quality, ROE/ROA durability, ratings, pledge behavior, insider/promoter behavior, and capital allocation all agree.
- C should not force a buy just because a business looks high quality.

In short: C is not the engine. C is the braking system, suspension, and confidence score around the engine.

## 5. Verdict: 2-3 dimensions to stake on

### A. Time-series / cross-sectional momentum

Stake on it, but do not overfit the lookback.

Evidence: MOM12, MOM6, HI52, RISKADJ, RESID_MOM all rank near the top, and the family survives both halves. This is the only broad family with repeated confirmation.

Caveat: it is crash-prone, beta-loaded, and can reverse violently after crowded trend regimes. It needs drawdown control, breadth checks, and no blind averaging down.

### B. Risk-adjusted momentum / low-vol momentum

Stake on it as the production form of momentum.

Evidence: RISKADJ has the best Sharpe, LOWVOL_MOM has lower beta and lower MaxDD than raw momentum, and HI52 is also cleaner than the high-beta MOM6/MOM12 variants.

Caveat: lower volatility can become a hidden sector bet, and RISKADJ can over-reward sleepy stocks with stale prices unless liquidity and turnover gates are strict.

### C. Quality / capital allocation as a conditional filter

Stake on it only in combination with price strength.

Evidence: QUALITY standalone has no alpha, but QUAL_MOM survives with +8.2% alpha and a much better MaxDD than raw momentum. That says quality improves candidate reliability but does not create timing by itself.

Caveat: fundamentals are sparse and slower moving. Missing-data handling must be explicit, sector-adapted, and never allowed to produce accidental scores.

If forced to reduce to two: momentum and risk-adjusted momentum. If allowed three: add quality/capital-allocation as a veto/conviction layer.

## 6. Regime risk: what breaks this ranking and how to hedge it?

This ranking can break in a sustained mean-reversion/value regime, a liquidity withdrawal, or a broad smallcap de-rating.

Failure modes:

1. Momentum crash: leaders become crowded, then unwind together.
2. Beta reversal: high-beta winners underperform when the market stops rewarding risk.
3. Smallcap liquidity shock: top-25 equal-weight books gap down and cannot exit at modeled costs.
4. Sector rotation: momentum clusters in one or two sectors, then leadership changes.
5. Valuation reset: expensive quality/momentum de-rates while cheap laggards rebound.
6. Policy/macro shock: rates, credit, INR, or commodity cycles change the factor leadership.

Hedges / controls I would build into Hermes:

1. Do not use one momentum factor. Ensemble MOM12, HI52, RISKADJ, and LOWVOL_MOM so the model is not pinned to a single lucky definition.
2. Cap portfolio beta and sector concentration. A "momentum" book that is really 40% one sector is not diversified.
3. Add market-regime gates: index below long moving average, breadth deterioration, high drawdown, or volatility spike should shrink position count / position size.
4. Require liquidity buffers beyond backtest turnover gates. Modeled transaction cost is not enough in Indian smallcaps.
5. Keep C as a veto: avoid debt stress, pledge risk, bad ratings, weak governance, and deteriorating capital allocation even if price momentum is strong.
6. Include a valuation sanity check, not as a long signal but as an overpay throttle.
7. Evaluate long-short or benchmark-neutral diagnostics even if production remains long-only. This separates selection skill from beta.
8. Track live decay. If the forward hit-rate or residual alpha deteriorates for 6-12 months, reduce weight rather than arguing with the tape.

Bottom line: the live run validates the direction of Hermes' doctrine. Price strength is the only robust forward-return engine shown here. Quality/capital allocation is valuable when it filters and confirms that strength. Naive standalone value and standalone quality should not be promoted to primary rankers from these results.
