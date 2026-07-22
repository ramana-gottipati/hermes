# PRE-REGISTRATION — UNION K30-DEEP-HOLD, forward test (the SEVENTH sibling; TWO levers stacked)

> **Class:** PRE-REGISTERED forward-test spec. COMPOSITE-30 (`07ef2ef9…`) with TWO stacked lever
> changes, each individually gauntlet-tested and robustness-checked: the **deeper-oversold turn**
> (16BE) and the **hold-winners-longer band** (16BD, = K30-HOLD `e6994c19…`). Hashed and committed
> before any forward-window data exists; editing this file after the forward window opens voids it.
> **Registered:** 2026-07-22 (the "improve the R logic" inquiry). **Origin:** 🏠 HOUSE (both levers,
> their falsification on the Zerodha gauntlet, this registration); parent selection is 🧑 RAMANA's
> COMPOSITE-30.
> **Multiplicity disclosure:** this is the SEVENTH spec on the same forward window (union `a9a14058…`
> · β14 `08b46199…` · C40RA `0715a0d9…` · COMPOSITE-30 `07ef2ef9…` · K30-HOLD `e6994c19…` ·
> A2-HOLD `17e0dd1a…` · this). K30-DEEP-HOLD shares the hold-band lever with K30-HOLD and the base
> with COMPOSITE-30 — these are NOT independent bets. The one frozen family-adjudication rule
> (highest forward alpha among passers) picks AT MOST ONE graduate across all seven.

## Why this exists

The 2026-07-22 inquiry (lift CAGR / cut drawdown) produced two independent levers that each survived
the Zerodha gauntlet (16BC) and their own robustness sweeps:
- **Hold-winners-longer (16BD):** +1.1pp net, drawdown unchanged. Robust across bands 40–90.
- **Deeper-oversold turn (16BE):** +0.8–0.9pp net AND −5 to −9pp drawdown. Robust across floors <25/<20.

They are ORTHOGONAL (one changes the exit/hold rule, the other changes the entry/turn quality), so
this spec STACKS them. Measured on the gauntlet, the stack captures the hold-band's return boost AND
the deeper-turn's drawdown cut — the best of every variant tested. This is the lift-CAGR-**AND**-cut-
drawdown result the whole inquiry was chasing, in one book.

**Epistemic status:** a variant of a fifth-generation in-sample-selected lead with TWO added in-sample
levers. The stacking inflates the in-sample edge and raises overfit risk beyond a single lever — Codex
15R applies at maximum force. The forward window is the only judge.

## THE FROZEN SPEC (complete and self-contained; identical to COMPOSITE-30 except TWO marked rules)

Everything in `docs/prereg/union-composite30-prereg.md`'s frozen spec is inherited VERBATIM —
universe (EQ/BE/BZ, CA-adjusted, era-relative liquidity floor P=0.450, dead −50%), PIT sector
assignment, the TREND signal (price RSI(14) > 50-SMA AND beat-own-sector ≥70% of the quarter),
beta-cap ≤ 1.4, RISKADJ rank, top-30 selection, let-winners-run drift-weight capped at 5%,
idle→Next-50/rf, trailing stop −20% @ 1% slip, 0.15%/side, quarterly rebalance, same-close
convention (next-day reported beside) — WITH THESE TWO CHANGES:

1. **DEEPER-OVERSOLD TURN (lever from 16BE).** The TURN leg fires only when the RSI(14) of the RS
   line (stock ÷ its sector) was **below 20** (not 30) within the trailing ~60 days and has crossed
   back to ≥ 30. (A stock still qualifies on the unchanged TREND leg OR this deeper TURN leg.)
2. **HOLD / EXIT BAND (lever from 16BD, = K30-HOLD).** A held name is RETAINED while it remains
   within the top **60** by the RISKADJ score (2× the 30-name selection, fixed a priori); the book
   refills to 30 from the highest-ranked non-held survivors. A held name exits only when it drops out
   of the top 60, hits its −20% trailing stop, or dies.

## IN-SAMPLE RECORD (2005–2026, for the record — NOT the test; ledger 16BF)

Measured on the Zerodha per-name gauntlet (16BC), K30-DEEP-HOLD (turn<20 + hold-band top-60) vs the
COMPOSITE-30 baseline and each single lever, identical engine and cost model:

| Book | flat CAGR | NET (gauntlet) | ₹1cr → | worst drop |
|---|---|---|---|---|
| COMPOSITE-30 (baseline) | 26.4% | 17.8% | ₹27.6cr | −38% |
| + hold-band only (K30-HOLD) | 27.2% | 19.0% | ₹33.6cr | −38% |
| + deeper-turn<20 only | 27.1% | 18.6% | ₹31.8cr | −29% |
| **+ BOTH (this spec)** | **27.5%** | **19.2%** | **₹34.8cr** | **−29%** |

The stack is the best net (19.2%) AND the lowest drawdown (−29%) of all variants — it keeps the
hold-band's return and the deeper-turn's drawdown cut. The turn<25 stack (19.1% / −33%) confirms the
effect is not a single-threshold artifact. **All IN-SAMPLE; net-of-cost is NOT net-of-selection, and
two stacked in-sample levers inflate the edge more than one — deflate hard for the forward view.**
Personal-scale only (capacity ~₹25–50cr, inherited from K30's AUM ladder, 16BC).

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Over ≥ 8 forward quarters from 2026-07 (the SAME four criteria as all union siblings):
(1) CAGR > Nifty Next 50 buy-and-hold net of the modelled costs · (2) alpha > 0 with forward beta
reported (excess purely from beta > 1.1 = FAIL) · (3) MaxDD not worse than Nifty Next 50's over the
same window · (4) no single quarter > 60% of the total excess. Miss 1–3 → DESCRIPTIVE-ONLY, never
deployed; criterion 4 → inconclusive, extend.

**FAMILY ADJUDICATION (frozen):** among ALL registered specs that PASS their own criteria over the
same forward window, the one with the highest forward ALPHA graduates; the others retire to reference
status. If none pass → all DESCRIPTIVE-ONLY. K30-DEEP-HOLD's shared levers with K30-HOLD and its
COMPOSITE-30 base are disclosed above so a joint pass is not read as separate discoveries.

## What is NOT claimed

Not that 19.2% net recurs (selection + TWO stacked in-sample levers inflate it by an unknown, larger
amount than a single lever); not that drawdown stays −29% (a lower in-sample drawdown from a deeper
filter is exactly the kind of thing that can regress); not personalized advice; not institutional
capacity. The stack has the HIGHEST overfit risk of the seven siblings — that is disclosed, not hidden.

## Canon

Ledger: **2026-07-16BF** (the stack test + this seal) · 16BE (the deeper-turn) · 16BD (the hold-band /
K30-HOLD) · 16BC (the gauntlet) · 16AF/16AH (COMPOSITE-30). Repro (additive; sealed engine files
untouched): `research/explosive_moves/gauntlet/build_stacked_gauntlet.py` (+ `build_c_bproxy.py`,
`build_reversal_gauntlet.py` for the single levers). SHA-256 of this file is recorded in the landing
commit and ledger 16BF; on the forward-test day it runs beside the other six sealed siblings.
