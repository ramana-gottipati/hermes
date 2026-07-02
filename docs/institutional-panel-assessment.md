# Institutional panel assessment — would this survive JP Morgan / Barclays? (2026-07-02)

Four world-class adversarial reviewers were run against our *actual* work (not generic), each posing
the questions their real committee would. Full briefs + questions in the session; this is the synthesis.

**Panel:** (1) Systematic Factor Quant (JPM QIS / GS / AQR caliber) · (2) Buy-side Systematic PM —
execution & capacity (Barclays / Millennium caliber) · (3) Risk / Model-Governance & Data-Integrity
(SR 11-7 model-validation caliber, verified against the live DB) · (4) Institutional Data-Product &
Commercial Strategist (MSCI / Bloomberg-QIS caliber).

## The convergent verdict (all four, independently, + our own ledger)
**There is no fundable net-of-cost alpha and momentum-selection is not yet proven vs beta. The
defensible, buyable asset is the PIT-clean, taxonomized, under-covered Indian mid/smallcap EVENT DATA
+ provenance — sold as DATA, never as a signal or strategy. The way to impress this tier is rigor and
honesty; momentum is a free demo of what the data enables, not the product.**

## Scorecard
| Dimension | Grade | Note |
|---|--:|---|
| PIT discipline (price spine) | 8/10 | genuinely survivorship-aware — *better than our own docs claimed* (universe drawn from 5,759 raw symbols incl. 1,722 delisted) |
| Cost realism | 8/10 | per-name ATR slippage + "nothing beats buy-&-hold net" — above sell-side standard |
| Data integrity / PIT overall | **6.5/10** | strong spine; two real leaks remain (below); not yet client-grade |
| Statistical inference (the alpha claim) | **4.5/10** | the hole: single-factor OLS, no controls, no t-stat, no MT haircut |
| Attribution / risk decomposition | 2/10 | "+16% α at β1.2" cannot distinguish selection from levered beta |
| Multiple-testing control | 3/10 | 15 factors ranked by Sharpe; no deflated-Sharpe / PBO quantified |

## The ranked gaps to close (converged across reviewers)
1. **Residual-alpha attribution (BOTH quant & risk name it #1).** The "+16% alpha" is a single-factor
   OLS vs Nifty-500 only. Run a 7-factor time-series (MKT/SMB/HML/QMJ/BAB/LIQ/**WML**) with Newey-West
   HAC errors + a Fama-MacBeth cross-sectional check + Deflated Sharpe + PBO, with pass/fail stated up
   front (α HAC t ≥ 3.0; DSR ≥ 0.95; PBO < 0.5). **Prediction (quant): full-model α drops below t=2 and
   reallocates to SMB + WML → it's levered beta, not selection.** → build `research/explosive_moves/attribution.py`.
2. **Terminal-anchor back-adjustment leak — AUDITED & DISPROVEN for deployed factors (2026-07-02).**
   The risk agent hypothesized `adjust.py`'s terminal-price anchor biases level factors. Audited via
   `research/explosive_moves/anchor_audit.py` (429 PIT obs, 25 delisted + 29 survivors): the terminal vs
   as-of anchors DO differ (mean ~20-24%, up to 2.7×), **but the difference is a pure multiplicative
   scalar that cancels exactly in every ratio-form factor** — range_pos_252 / dist_high_252 / HI52 are
   anchor-invariant to machine epsilon (4.4e-16), same as pure-return momentum. **No code change needed;
   the panel's "flag level factors anchor-sensitive" recommendation would be a false warning.** Only a
   *raw un-normalized rupee-level* factor (or a fixed-rupee threshold) would carry the bias — none
   deployed. **Guardrail added instead:** any NEW factor must be a pure return or a within-window ratio,
   never a raw adjusted-price level (aligns with the existing "no static rupee thresholds" rule).
3. **Survivorship — finish it properly.** Price spine is already survivorship-correct (good), BUT:
   (a) delisted names silently drop out of the return series without **booking the delisting return**
   (−100% insolvency / M&A price) → a return-series leak even with a complete symbol list;
   (b) fundamentals are asymmetric — **1,706 of 1,722 delisted names have no fundamentals** → quality/value
   factors are effectively scored on a listed-today set (must be labeled, not reported as survivorship-free);
   (c) left-censoring: **773 names truncated at the 2004-07-23 archive floor** — disclose as a number; keep
   the headline window 2012+.
4. **Cost is a DECISION VARIABLE, not a fixed haircut (PM).** The flat 0.5×ATR assumes naïve market
   orders and *over-penalizes* the fundable form; real desks use VWAP/participation ≤10% ADV (~0.1–0.2×ATR).
   Replace the flat ATR in `cost_realism.py` with a participation-rate impact model; re-run quarterly
   large-cap LOWVOL_MOM at ₹50 / ₹200 / ₹500cr. PM prior: ~1.0 net Sharpe *at ₹50cr only* — fundable but
   not scalable (breakpoint ₹50cr→₹500cr; alpha lives where capacity dies).
5. **Doc honesty fix.** Move the net-reality + β-caveat to the TOP of `docs/predictive-attributes-findings.md`
   (a committee reading it beside the ledger's "0.09 net" would flag the inconsistency). Fold the
   never-claim list into any pitch material.
6. **Client-grade governance (risk).** Independent replication of the factor Sharpes; a written validation
   memo (lineage, PIT method, the anchor finding, survivorship spec, limitations, owner/validator split);
   monitoring + kill-switches (momentum-crash guard, β>1.3 cap, sector>25%, live-IC decay, data-freshness,
   restatement-spike, universe-drift); reconciliation (bhav-vs-index, CA correctness, ISIN/rename identity).

## The product (data-product strategist)
- **Value prop (honest):** PIT-provenanced, exchange-sourced event data on the ~2,500 under-covered
  mid/smallcap names their terminal barely touches — insider/promoter/pledge, credit actions,
  capital-allocation — each with a verifiable `knowable_at` and a taxonomy they'd otherwise pay analysts
  to build; delivered as a feed for their own stack. **No "alpha," no Sharpe, no "front-runs re-ratings."**
- **Shape:** DATA FEED (the `insider_events` / `credit_rating_events` tables + derived cols) with a thin
  `/v1` API/SDK/MCP delivery — NOT a signal, screener, or dashboard (they own that layer). Audit/provenance
  = a separate low-risk **door-opener SKU** (compliance buyer, no performance claim).
- **"NEVER claim" list:** alpha/Sharpe/edge on any signal · a backtest as a track record (esp. the gross
  1.29) · CCI predicts anything (falsified) · "fully PIT" when fundamentals are *modeled* (period_end+90d) ·
  survivorship-free until the 1,722 delisted are wired · "promoter bought = bullish" · gloss the
  **data-licensing/redistribution** question (the real procurement deal-killer — settle before pricing) ·
  oversell coverage (volunteer the limit; a coverage ledger IS the credibility).
- **Minimum viable institutional offering:** dataset **A (insider/promoter/pledge)** to diligence standard
  on a ~500-name sample over multi-year history + data dictionary + taxonomy methodology + coverage ledger.
  **3 proof points for the first meeting:** (1) PIT "replay-the-tape" (on date T expose only what was
  disclosed by T, with restatement log), (2) coverage-of-the-tail ledger with honest funnel, (3) a worked
  taxonomy example (one promoter sequence decomposed buy vs pledge-release vs inter-se, with a liquidity
  sanity check).
- **Pricing (anchor to their build cost, not our ₹300/mo ops):** paid POC (low-mid 5-fig USD) → single-
  dataset feed (mid-5-to-low-6-fig/yr) → full A+B+C suite (low-mid-6-fig/yr) → audit/provenance add-on
  (5-fig, the wedge SKU). Annual entity licenses; metering for entitlement/audit, not the revenue model.

## What happens next (agent-built)
The two questions that actually gate credibility are scientific, and both are now commissioned as
world-class-agent work: **(1) the residual-alpha attribution** (settles selection-vs-beta — the single
most important number), then **(2) the anchor-leak + delisting-return survivorship completion.** The
product path (MVIO dataset-A to diligence standard + 3 proof points) is the commercial track that runs
in parallel and does not depend on the momentum question resolving.
