# PRE-REGISTRATION — walk-forward ML ranker over the UNION's qualifiers

> **Class:** PRE-REGISTERED walk-forward ML experiment. Hashed and committed BEFORE any model was
> trained or any test-window number was seen. If this file is edited after the run, the registration
> is void and the result is in-sample.
> **Registered:** 2026-07-16. **Origin:** 🧑 RAMANA (the directive — "in the AI era, relying on
> manual-only strategies makes no sense"; ML/ensemble explicitly on the table) + 🏠 HOUSE (design,
> falsification discipline).
> **Relation to the sealed union:** the union spec (`union-prereg.md`, seal `a9a14058…`) is UNTOUCHED.
> This is a CANDIDATE beside it, per the carry-forward's binding rule.

## Honest prior (stated before the run)

- The ledger's standing result: stock momentum here is **BETA, not skill** (residual-α t = 1.99,
  re-validated PIT at t = 1.80, AUD-22). A learned ranker over momentum features starts guilty.
- Codex 15R: anything selected after seeing 2005–2026 is a LEAD, not evidence. An ML model trained
  and scored on the same window would be the maximal form of that sin — hence the design below
  never scores in-sample.
- Session context this must beat: the same session's first-declared selection candidate
  (per-name **beta ≤ 1.4** at selection, `union_lab.py`) already flips 2012–17 alpha positive.
  A model that cannot beat one hand-written rule on held-out data adds complexity, not capability.

## THE FROZEN DESIGN (any change voids the registration)

**Machinery.** The sealed union engine, byte-equivalent foundation (`cash_blend.py` lineage:
EQ+BE+BZ corporate-action-adjusted prices, split-ratio quarantine, prior-month ADV ≥ ₹5cr, PIT
sector assignment by trailing-500d excess-correlation, the union signal pair — trend: price-RSI(14)
> its 50-SMA AND ≥70% same-quarter consistency vs own sector; turn "6b": RSI(14)-of-RS < 30 → ≥ 30
within trailing ~60d — fixed 1/60 slots, top-60, idle → Nifty Next 50 sleeve while Nifty 500 ≥
200DMA else cash, −20% trailing stop @1% slip, 0.15%/side). **The model does exactly one thing:
ORDER the union's qualifier list at each rebalance date.** Everything else is untouched.

**Features** (per qualifier per rebalance date; each converted to a within-date percentile rank in
[0,1]; missing → 0.5):
1. leg (trend-only = 0, turn-fired = 1)
2. price RSI(14) level
3. price RSI(14) − its 50-SMA gap
4. consistency fraction vs own sector (trailing quarter)
5. RSI-of-RS level
6. turn age — days since RSI-of-RS last crossed up through 30 (cap 63; 63 if not in window)
7. trailing 250d beta vs Nifty 500 (min 150 obs)
8. trailing 63d excess return vs own sector index
9. trailing 126d RS-line drawdown depth (min RS / max RS − 1)
10. trailing 63d daily-return standard deviation (min 30 obs)

**Label.** Forward rebalance-to-rebalance stock total return minus the same-period Nifty 500
return, converted to a within-date percentile rank. (The label measures selection quality; the
book applies the full mechanics.)

**Models — both declared now, trained once, never tuned:**
- **M1 (PRIMARY):** `sklearn.linear_model.Ridge(alpha=1.0)` on the 10 percentile features.
- **M2 (exploratory, reported only):** `sklearn.ensemble.GradientBoostingRegressor(
  n_estimators=200, learning_rate=0.05, max_depth=2, subsample=0.8, random_state=42)`.

**Split.** TRAIN: every rebalance date whose forward-return window closes ≤ 2016-12-31.
TEST: every rebalance date ≥ 2017-01-01. **One frozen fit** — no expanding-window retraining, no
hyperparameter search, no cross-validation on test, no test-window iteration of any kind.

**Test-time selection.** Sort qualifiers by M1 predicted rank (descending), take the top 60, run
the sealed book mechanics on 2017-01-01 → latest. M2 reported the same way, exploratory.

## PASS / FAIL — frozen before the run

On the 2017-01 → 2026 test window, computed by the same engine in the same script:

1. **M1 book beats the union CONTROL** (engine-order selection, same window) on **CAGR AND alpha**.
2. **M1 book beats the beta-cap-1.4 candidate** (same window) on **CAGR AND alpha**.
3. **M1 book beta ≤ 1.0** over the test window.
4. **M1 book MaxDD not worse than the union control's by more than 3pp.**

Fail ANY of 1–4 → **REJECTED — recorded in the ledger with the numbers, no re-run, no variant
shopping.** A pass earns exactly one thing: CANDIDATE status beside the union, subject to the same
forward-quarter evidence as everything else. The 2012–17 window is TRAINING data here — this
design can make NO out-of-sample claim about the union's known weak regime, and any 2012–17
improvement shown is descriptive only.

## What is NOT claimed

- Not that a pass makes the model deployable (it would be a lead, like everything in-sample-born).
- Not that M2's result counts for anything beyond exploration.
- Not that feature importances are causal.

## Canon

Runner: `research/explosive_moves/union_ml.py` (this design, verbatim). Results: ledger, a
2026-07-16-lettered entry. SHA-256 of this file recorded in the ledger entry and the landing
commit; the run happens only after this file is committed.
