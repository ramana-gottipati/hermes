# Ignition picker — champion-vs-challenger build (design + plan)

> **Status:** plan APPROVED-by-default 2026-06-23 (Ramana: "I want all 3 components, plan first"; the
> three decisions below locked to the recommended defaults — he can override any). Building **C → A → B**,
> checkpoint after each. Companion: memory `work-plan-two-lanes`.
>
> **Isolation rule (his single prevailing rule — holds throughout):** every piece is a NEW isolated module
> owning NEW tables; never edit `db.py` or any shipped/contended file; surgical per-file commits; the only
> `DELETE`s are full-recomputes of our own tables. `ranking_history`-style series are upsert-only.

## Context (lane-1 evidence this builds on)
The full-journey backtest + feature study (committed `8531744`, `b1532e1`) found:
- The ignition **setup** is a good screen — 42.1% win (MFE ≥ +25% before MAE ≤ −15%), median winner MFE +109%.
- **Raw intensity is wrong-signed** (−4.5pt; the most extreme DVPT spikes win *less*); `is_ath_dvpt` negative; `rs_rank` flat.
- Real separators: **`rs_vs_broad_slope_12m` (+11pt), `gap_to_key_p12m` (+10), `pct_from_52w_high` (+10)**, `price_vs_hot_avg_pct`, `accum_price_drift_3m`, accumulation character (+3.9). **Sector** is the biggest raw separator (+37pt) but **regime-suspect** (2019–26 pharma boom / chemicals bust).
- Derived target ~+70% (median MFE), stop ~−13% (survives ~90% of winners' pre-peak heat).

## Locked decisions
1. **Sector → excluded from the score** (shown as context only). Avoids baking a period-specific regime into the rank. Revisit only if it survives a sub-period test.
2. **Challenger ML → research-only** (`.venv-research`); wire scores into production *only if* it clearly beats the champion out-of-sample. Production `.venv` stays numpy/sklearn-free (doctrine).
3. **Walk-forward validation mandatory** wherever weights/models are fit (derive on 2019→Y, test on Y+1) — never grade in-sample.

## C — Averaging-zone derivation *(DONE — committed/pushed)*
- **Module:** `src/automation/ignition_zones.py`; owns `averaging_zones`; reads the path-conditional `rec_after_X` flags added to `ignition_backtest`.
- **Metric (corrected):** *after price FALLS −X% from entry in REAL time*, % that still reach +25%. (An earlier `mae_before_peak` cut was CONFOUNDED — it measured the dip vs the FUTURE peak, producing the backwards "deeper dips recover more"; caught and replaced.)
- **AVERAGING DOCTRINE (Ramana, locked):** recover-rate is a *thesis-intact gauge, NOT a buy trigger*. **Never average small dips** (a −5% fall self-corrects; averaging there buys ~2.6pt of breakeven while burning scarce capital). **Average only at DEEP falls (~30%)**, where an equal-share add HALVES a large breakeven (42.9%→21.4%) and ~38% still recover. Applies to the tracker + A's position-sizing too.
- **Result (VPS):** recover −5% 69 / −10% 62 / −15% 54 / −20% 48 / −30% 38 (base 76%); breakeven-pt saved by averaging 2.6 → 21.4 across those depths (the value concentrates deep).

## A — Revised champion ranking + walk-forward proof *(DONE — committed/pushed)*
- **Module:** `src/automation/ignition_rankv2.py` (shipped `ignition.py` untouched). Evidence-weighted composite (z-score × training-window lift; intensity earns ~0/negative, `rs_vs_broad_slope_12m` / `pct_from_52w_high` / `gap_to_key_*` earn the top weights; sector excluded). Owns `ignition_rank_v2`.
- **WALK-FORWARD VERDICT (38,802 OOS events, 2020–25): v2 does NOT beat the base.** v2 top-decile win **43.6%** vs base **45.9%** (−2.3pt) vs intensity top-decile **46.2%** (−2.6pt). The in-sample univariate lifts do NOT compose into an OOS-robust top-decile edge — they overfit the training regime.
- **Conclusion:** the ignition SETUP is a good *screen* (45.9% reach +25%, big payoff skew), but neither intensity NOR this composite ranks it into top-decile alpha. **v2 NOT promoted to production.** The walk-forward caught what in-sample analysis would have missed.

## B — Multivariate challenger *(research venv only; offline)*
- **Package:** `research/ignition/` (run via `/opt/hermes/.venv-research`); reads `hermes.db` read-only (`ignition_outcomes` + `stock_signals`) **+ `fundamentals_asof.as_of_fundamentals(symbol, as_of)`** for point-in-time fundamentals; writes to `research.db`.
- **Method:** logistic regression (interpretable) + gradient boosting (interactions); **walk-forward by year**; report OOS AUC + decile lift + feature importances; head-to-head vs champion (intensity) and the A-rule on identical folds.
- **Output:** does a multivariate model — including fundamentals — beat the simple rule OOS, and which features carry it. Honest verdict (the simple rule is often close). ₹0 at runtime.

## Sequence & checkpoints
C (finishes §5: target/stop/averaging) → A (champion v2 + OOS proof) → B (challenger vs champion). Verify + commit + report after each; nothing pushed without Ramana's word.
