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

## C — Averaging-zone derivation *(quick; prod venv, pure Python)*
- **Module:** `src/automation/ignition_zones.py`; owns `averaging_zones`; reads `ignition_outcomes`.
- **Method:** bucket events by `mae_before_peak` (the dip taken on the way up); per band report recovery-rate = P(reached +25% MFE), median final return, n.
- **Output:** "dipped to −X% before running → Y% still reached target" → the averaging-down guidance. Selftest + real run.

## A — Revised champion ranking + rank-aware proof *(prod venv, pure Python)*
- **Module:** `src/automation/ignition_rankv2.py` (shipped `ignition.py` untouched; v2 can replace its rank later if validated).
- **Score:** evidence-weighted composite — standardize each feature, weight by its observed lift from `feature_lift`; **cap/invert intensity**; up-weight `rs_vs_broad_slope_12m` + `gap_to_key_p12m` + `pct_from_52w_high` + accumulation character. Sector excluded (decision 1).
- **Proof (the point):** order historical `ignition_outcomes` by the v2 score; measure **top-decile win-rate vs the 42% base, head-to-head vs ordering by intensity**, done **walk-forward**. If v2 doesn't beat base OOS, say so plainly.

## B — Multivariate challenger *(research venv only; offline)*
- **Package:** `research/ignition/` (run via `/opt/hermes/.venv-research`); reads `hermes.db` read-only (`ignition_outcomes` + `stock_signals`) **+ `fundamentals_asof.as_of_fundamentals(symbol, as_of)`** for point-in-time fundamentals; writes to `research.db`.
- **Method:** logistic regression (interpretable) + gradient boosting (interactions); **walk-forward by year**; report OOS AUC + decile lift + feature importances; head-to-head vs champion (intensity) and the A-rule on identical folds.
- **Output:** does a multivariate model — including fundamentals — beat the simple rule OOS, and which features carry it. Honest verdict (the simple rule is often close). ₹0 at runtime.

## Sequence & checkpoints
C (finishes §5: target/stop/averaging) → A (champion v2 + OOS proof) → B (challenger vs champion). Verify + commit + report after each; nothing pushed without Ramana's word.
