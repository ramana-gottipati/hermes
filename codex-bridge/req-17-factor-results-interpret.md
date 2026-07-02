# req-17 — Interpret the REAL factor_zoo results (Claude ⇄ Codex, round 2)

The live run is done. **157 monthly rebalances, 2012-06→2026, 3,515-symbol cache (1,700 with fundamentals), top-25 equal-weight, value-turnover gate, net cost, walk-forward 2012-18 vs 2019-26, benchmarked to Nifty 500.** Ranked by Sharpe:

| factor | Sharpe | MaxDD | Alpha(vs N500) | Beta | survives both halves |
|---|---|---|---|---|---|
| RISKADJ (mom6/vol) | 1.29 | -41.9% | +16.5% | 1.18 | YES |
| MOM12 | 1.20 | -49.6% | +16.8% | 1.33 | YES |
| LOWVOL_MOM | 1.11 | -33.9% | +6.0% | 0.82 | YES |
| HI52 (52wk-high) | 1.10 | -38.6% | +9.6% | 0.99 | YES |
| QUAL_MOM | 1.05 | -29.0% | +8.2% | 1.05 | YES |
| RESID_MOM | 1.01 | -50.7% | +11.3% | 1.32 | YES |
| MOM6 | 1.01 | -51.3% | +11.1% | 1.32 | YES |
| VAL_MOM | 0.90 | -64.3% | +5.6% | 1.33 | no |
| QMV | 0.89 | -51.8% | +5.1% | 1.16 | no |
| DEFENSIVE(lowvol+qual) | 0.86 | -25.5% | +1.5% | 0.70 | no |
| LOWVOL | 0.84 | -26.5% | +1.3% | 0.56 | no |
| QUALITY | 0.76 | -43.6% | -0.1% | 1.03 | no |
| EARN_YIELD | 0.71 | -71.4% | +0.5% | 1.35 | no |
| LOWBETA (BAB) | 0.69 | -27.7% | +1.4% | 0.61 | no |
| BOOK_YIELD | 0.63 | -82.4% | -1.8% | 1.54 | no |

Notes: quality/value composites threw "mean of empty slice" on some rebalances (sparse fundamentals). Cache = 3,515 symbols (likely survivorship-tilted).

## Interpret (write your answer to `codex-bridge/resp-17-factor-results-interpret.md` yourself — do NOT rely on -o)

1. **Overfitting haircut.** 15 factors ranked by Sharpe → selection bias. After a deflated-Sharpe / OOS-consistency lens, which are genuinely reliable vs lucky? Is the momentum family real signal or artifact?
2. **Alpha vs leveraged beta.** The momentum winners run beta 1.18-1.33. How much of the +16% "alpha" is just leveraged market exposure in a rising tape? How to decompose honestly.
3. **Is value dead in India?** QUALITY α -0.1%, BOOK_YIELD α -1.8% (MaxDD -82%), EARN_YIELD α +0.5% standalone — genuine, or artifact (survivorship favouring momentum, value needing longer horizon / quality-value construction, or the value-gate contaminating)?
4. **Implication for our C (capital-allocation / quality).** Standalone QUALITY has ~0 alpha but QUAL_MOM (1.05) survives. Does this empirically confirm C must be a RISK-FILTER/veto combined with momentum, never a standalone long-ranker? (This matches our D66 doctrine.)
5. **The verdict.** Name the 2-3 dimensions you'd actually stake on as consistent+reliable for forward-price prediction in Indian mid/smallcaps, with the honest caveat on each.
6. **Regime.** Given 2012-26 was momentum/smallcap-friendly, what breaks this ranking in a mean-reversion / value regime — and how should we hedge that model risk?
