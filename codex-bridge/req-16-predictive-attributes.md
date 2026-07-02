# req-16 — Predictive attributes: consistency & reliability (Claude ⇄ Codex)

**Goal (Ramana):** a deep dive on which attributes/dimensions actually forecast future price moves in Indian equities, assessed for **consistency** (holds across time/regimes) and **reliability** (statistically trustworthy, not overfit), **benchmarked to the index**. Then discuss.

We have a mature factor engine: `research/explosive_moves/factor_zoo.py` — monthly top-25, value-turnover gate, net cost, walk-forward **2012-18 vs 2019-26**, alpha/beta vs **Nifty 500**, MFE/MAE capture, `survives_both_halves`. I'm running it live on the VPS now (`out/factor_zoo.csv`). Plus we just built C (capital-allocation), A (insider/promoter), B (credit-rating) feeds.

## What I want from you (methodology + interpretation — read-only)

1. **The right metrics.** For "consistency" vs "reliability", what should we actually trust? Rank-IC + IC-IR (mean/σ), IC hit-rate, decile monotonicity, walk-forward half survival, alpha net of beta AND cost, turnover/capacity. Which of these is "consistency" and which is "reliability"? What thresholds are credible for Indian mid/smallcaps (not US large-cap numbers)?

2. **Overfitting / multiple-testing guards.** factor_zoo tests ~15 factors and ranks by Sharpe — that's a selection bias. What corrections (deflated Sharpe, Bonferroni, PBO, strict OOS)? How much should a top-ranked in-sample Sharpe be haircut?

3. **Sparse event feeds.** A (insider, ~4mo history) and B (credit, ~6mo) CANNOT be walk-forward IC-tested — too little history, event-sparse. Is the correct treatment an **event-study / conditional overlay** (forward return conditioned on the event) rather than a cross-sectional factor? Or are they descriptive/veto-only until years accrue? Be specific about what claim is even *permissible* on 4-6 months.

4. **"Based on the index."** Proper benchmarking: cross-sectional excess vs Nifty 500, beta-neutral alpha, and **regime-conditioning** (does the attribute's edge flip in bull vs bear / high-vol vs low-vol / smallcap-leadership vs largecap)? How to test regime-consistency without shredding sample size.

5. **Critique factor_zoo's design** for hidden bias: symbol-cache survivorship, the value-gate interacting with the factor, 22-day rebal, top-25 concentration, cost model. What would make its "survives_both_halves" flag misleading?

6. **Your prior.** In Indian equities specifically, which single dimension has historically been the most consistent+reliable, and which famous factors are fragile here? I'll bring the real numbers to the next round.

Reply as `codex-bridge/resp-16-predictive-attributes.md`. Round 2 will feed you the actual factor_zoo results for interpretation.
