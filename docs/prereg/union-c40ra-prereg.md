# PRE-REGISTRATION — UNION-C40RA (β14 + top-40 + RISKADJ rank), forward test

> **Class:** PRE-REGISTERED forward-test spec, the THIRD member of the union sibling family
> (`union-prereg.md` seal `a9a14058…` · `union-beta14-prereg.md` seal `08b46199…` — both UNTOUCHED).
> Hashed and committed before any forward-window data exists; editing this file after the forward
> window opens voids it.
> **Registered:** 2026-07-16 (S168; ledger 2026-07-16AB). **Origin:** 🧑 RAMANA (the 25%-CAGR
> directive and the RS theses) + 🏠 HOUSE (the levers, falsification, this registration).
> **Multiplicity disclosure (stated plainly):** registering a THIRD sibling raises the odds that one
> passes its forward test by luck. Mitigations: each spec is judged on ABSOLUTE criteria vs the
> benchmark (not a tournament), criterion 4 guards single-quarter luck, and the family adjudication
> below is frozen now. The family stops at three — no fourth registration without a forward result.

## Why this exists

Ramana's S168 directive: target 25% CAGR; "this is a lab... do logical experiments." The S168
battery (`union_lab3.py`) swept the remaining single-axis levers on the β14 base under a
pre-declared pass bar. Two axes passed independently — concentration at **top-40** and ranking the
capped qualifiers by the estate's best-of-32 factor (**RISKADJ = 6-month return ÷ 3-month daily
volatility**) — and the pre-declared auto-compose rule combined exactly those two. Everything else
failed and is walled in the ledger (16AC): trail widths, sleeve swaps, cap-floor, vs-bench
consistency, monthly cadence (4th confirmation of the cadence law), and the cross-family
LOWVOL_MOM blend (correlation 0.83 — dilution, not diversification).

**Epistemic status: an in-sample-selected lead, third generation** — selected from a sweep on the
same 2006–2026 history (Codex 15R applies with extra force at generation three). The honest
conversion is the same as its siblings': freeze the spec, judge only on data that did not exist
when it was built.

## THE FROZEN SPEC (any change voids the registration)

Identical to the sealed union-β14 spec (union machinery: EQ+BE+BZ CA-adjusted, split-ratio
quarantine, prior-month ADV ≥ ₹5cr, PIT 500d excess-correlation sector assignment; signals — trend:
price-RSI(14) > its 50-SMA AND ≥70% trailing-quarter consistency vs own sector; turn 6b:
RSI(14)-of-RS < 30 → ≥ 30 in trailing ~60d; union by OR; per-name trailing-250d beta vs Nifty 500
> 1.4 excluded at selection, min 150 obs, missing kept; idle → Nifty Next 50 while Nifty 500 ≥
200DMA else cash; trailing stop −20% from peak close @1% slip; 0.15%/side; quarterly), **plus
exactly two rules:**

> 1. **Rank the capped qualifiers by RISKADJ score, descending** — score = (adjusted close today ÷
>    adjusted close 126 trading days ago − 1) ÷ (standard deviation of daily returns over the
>    trailing 63 trading days, minimum 30 observations). A qualifier whose score cannot be computed
>    ranks LAST. Same-close feature/execution convention as the whole family (the D5-F1 lagged
>    variant is reported beside it as the honesty check).
> 2. **Hold the top 40** (fixed 1/40 slots; idle fraction to the sleeve as usual).

Repro: `research/explosive_moves/union_lab3.py` (the COMPOSITE row; auto-composed by the
pre-declared rule, not hand-picked) · honesty passes in `union_lab3b.py`.

## IN-SAMPLE RESULT (2006–2026, for the record — NOT the test)

Price-return: **CAGR 21.0% · MaxDD −28.4% · ₹1 Cr → ₹47.29 Cr · beta 0.81 · alpha +10.3%** (vs
β14's 18.1%/−24.7%/28.84×/0.74/+8.4 and the union's 17.5%/−30.5%/26.04×/0.87/+6.8). Walk-forward
alpha: 2006–11 +9.2% · 2012–17 +4.3% · 2018–26 +14.3%. Total-return (dividend accrual, lower
bound): **CAGR 21.8%**, windows 18.3% / 22.1% / 25.7%.

Honesty passes (union_lab3b.py, run before this registration was committed):
- @2% stop-slip: CAGR 19.7% · alpha +9.2% — the edge is not a slippage artifact.
- **D5-F1 next-day execution (signals at close d, trades at close d+1): CAGR 20.0% · alpha +9.5%**
  (total-return 20.8%) — the edge is not the same-close peek.
- Worst honest case (lagged + 2% slip, total-return): **CAGR 19.5% · alpha +9.1% · MaxDD −29.0%**
  — the floor of the in-sample estimate range; its 2018–26 window still prints 23.7%.

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Same forward window and cadence as the siblings (every new quarter from 2026-07, ≥ 8 forward
quarters), same four absolute criteria: (1) CAGR > Nifty Next 50 net of modelled costs ·
(2) alpha > 0 with forward beta reported (excess purely from beta > 1.1 = FAIL) · (3) MaxDD not
worse than Next-50's · (4) no single quarter > 60% of the excess.

**FAMILY ADJUDICATION (frozen now, supersedes the two-way rule in the β14 registration for the
three-way case):** among the specs that PASS their own criteria over the same forward window, the
one with the highest forward ALPHA graduates; the others retire to reference status. If none pass →
all DESCRIPTIVE-ONLY, never deployed.

## What is NOT claimed

- Not that 21–22% recurs, and NOT that 25% is achieved. In-sample selection (three generations of
  it) inflates these numbers by an unknown amount; the recorded 2018–26 TR window (25.7%) touches
  Ramana's target, the full period does not, and only forward quarters count.
- Not that capacity is large: 40 mid/large-cap names at ADV ≥ ₹5cr — participation cost at
  institutional AUM is untested for this book and the estate's precedent (C-BLEND recut) says it
  bites. Personal-scale capital only until a participation recut is run.
- Not personalized advice. Descriptive research on a paper portfolio; dividends are a parsed
  lower bound (97.7% coverage 2012+, ~34% before); benchmark remains price-index (TRI unavailable
  in the DB — book-TR vs bench-PR is printed beside book-PR vs bench-PR so neither hides).

## Canon

Ledger: 2026-07-16AB (wins + composite + honesty passes) · 16AC (the S168 kills incl. the blend) ·
16AD (the TR measurement) · 16Y (the β14 base) · 16U→X (the union arc). Ruleset prose:
`docs/strategies/union.md` §4. Repro: `research/explosive_moves/union_lab3.py` / `union_lab3b.py` /
`blend_u25.py`. SHA-256 of this file is recorded in the landing commit and ledger 16AB; the
forward test runs `union_lab3.py`'s composite row beside the two siblings.
