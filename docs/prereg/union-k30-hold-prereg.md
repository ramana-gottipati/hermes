# PRE-REGISTRATION — UNION K30-HOLD, forward test (the FIFTH sibling; one lever off COMPOSITE-30)

> **Class:** PRE-REGISTERED forward-test spec, a variant of the sealed COMPOSITE-30 (`07ef2ef9…`)
> differing in EXACTLY ONE rule (the hold/exit band). Hashed and committed before any forward-window
> data exists; editing this file after the forward window opens voids it.
> **Registered:** 2026-07-22 (the "improve the R logic" inquiry). **Origin:** 🏠 HOUSE (the
> hold-longer lever "C", its robustness sweep, the Zerodha-gauntlet falsification, this registration);
> the parent selection engine is 🧑 RAMANA's COMPOSITE-30.
> **Multiplicity disclosure:** this is the FIFTH spec on the same forward window (union `a9a14058…` ·
> β14 `08b46199…` · C40RA `0715a0d9…` · COMPOSITE-30 `07ef2ef9…` · this). Each added spec raises the
> odds one passes by luck. Mitigations, unchanged: ABSOLUTE criteria vs the benchmark (not a
> tournament), criterion 4 guards single-quarter luck, and ONE frozen family-adjudication rule picks
> at most one graduate. Because K30-HOLD and COMPOSITE-30 are near-identical (one lever), they are
> NOT independent bets — if both pass, adjudication (highest forward alpha) picks one; they do not
> each count as a separate discovery.

## Why this exists

The 2026-07-22 "how do we lift CAGR and cut drawdown" inquiry produced three candidates, tested on
the exact Zerodha real-cost gauntlet (ledger 16BC), all recorded in ledger 16BD:
- **C — hold winners longer (THIS seal):** keep a still-strong name instead of rotating it out at
  the calendar rebalance. Lifted K30 both GROSS and NET (so it is a better-selection effect, not
  merely a turnover cut), and left the worst drawdown unchanged. **Robustness sweep (the reason it
  is sealed, not a lucky threshold):** net-of-gauntlet gain was POSITIVE at every hold-band from 40
  to 60 (+0.6 to +1.2pp), drawdown pinned at −38% throughout, gain monotone-then-plateauing near 2×
  the holding count. The band here is fixed a priori at **2× holdings**, mid-plateau (NOT the peak).
- **B-proxy — price-crash filter:** INERT (removed zero names/rebalance — momentum already avoids
  just-crashed stocks). Buried with that reason (16BD); not in this spec.
- **B (governance blow-up filter — pledge/promoter-sell/surveillance):** UNTESTABLE historically
  (those feeds have no point-in-time history before ~Nov-2025). Forward-only; not in this spec.

**Epistemic status:** a variant of a fifth-generation in-sample-selected lead, with ONE added lever
whose robustness is demonstrated but whose forward edge is unproven. Codex 15R applies at maximum
force. The forward window is the only judge; that is what this registration buys.

## THE FROZEN SPEC (complete and self-contained; identical to COMPOSITE-30 except the HOLD rule)

Everything in `docs/prereg/union-composite30-prereg.md`'s frozen spec is inherited VERBATIM —
universe (EQ/BE/BZ, CA-adjusted, era-relative liquidity floor P=0.450, dead −50%), PIT sector
assignment, the UNION signals (TREND ∪ TURN), beta-cap ≤ 1.4, RISKADJ rank, top-30 selection,
let-winners-run drift-weight capped at 5%, idle→Next-50/rf, trailing stop −20% @ 1% slip, 0.15%/side,
quarterly rebalance, same-close convention (next-day reported beside) — WITH THIS ONE CHANGE:

**HOLD / EXIT BAND (the only difference).** At each quarterly rebalance, a name currently held is
**RETAINED as long as it remains within the top 60** by the RISKADJ score (twice the 30-name
selection count — fixed a priori). The book is refilled to 30 from the highest-ranked non-held
survivors. A held name exits only when it drops out of the top 60, hits its −20% trailing stop, or
dies. (COMPOSITE-30 by contrast re-selects a fresh top-30 each quarter.) Nothing else changes.

## IN-SAMPLE RECORD (2005–2026, for the record — NOT the test; ledger 16BD)

Measured on the Zerodha per-name gauntlet (ledger 16BC), K30-HOLD (band = top-60) vs baseline
COMPOSITE-30 on the identical engine and cost model:

| | flat CAGR | NET CAGR (gauntlet) | ₹1cr → | worst drop | turnover/yr |
|---|---|---|---|---|---|
| COMPOSITE-30 (baseline) | 26.4% | 17.8% | ₹27.6cr | −38% | 281% |
| **K30-HOLD (this spec)** | **27.2%** | **19.0%** | **₹33.6cr** | **−38%** | 267% |

Robustness (net-of-gauntlet gain vs baseline, same window): band 40 +0.7 · 45 +0.6 · 50 +0.9 ·
55 +1.2 · 60 +1.1 — every value positive, drawdown −38% throughout. The gain is ~half cost-saving,
~half better-gross (holding a still-strong name beats swapping for a fresher one). **All in-sample;
net-of-cost is NOT net-of-selection — deflate for the forward view.** Personal-scale only
(capacity ~₹25–50cr, inherited from K30's AUM ladder, 16BC); institutional capacity untested.

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Over ≥ 8 forward quarters from 2026-07 (the SAME four criteria as all union siblings):
(1) CAGR > Nifty Next 50 buy-and-hold net of the modelled costs · (2) alpha > 0 with forward beta
reported (excess purely from beta > 1.1 = FAIL) · (3) MaxDD not worse than Nifty Next 50's over the
same window · (4) no single quarter > 60% of the total excess. Miss 1–3 → DESCRIPTIVE-ONLY, never
deployed; criterion 4 → inconclusive, extend.

**FAMILY ADJUDICATION (frozen):** among ALL registered specs that PASS their own criteria over the
same forward window, the one with the highest forward ALPHA graduates; the others retire to
reference status. If none pass → all DESCRIPTIVE-ONLY. K30-HOLD competes on equal terms; its
near-identity to COMPOSITE-30 is disclosed above so a joint pass is not read as two discoveries.

## What is NOT claimed

Not that 19% net recurs (selection + one more in-sample lever inflate it by an unknown amount); not
that the +1.1pp forward-survives (it is net-of-cost, not net-of-selection); not that drawdown stays
−38%; not personalized advice; not institutional capacity.

## Canon

Ledger: **2026-07-16BD** (the three findings + this seal) · 16BC (the Zerodha gauntlet it is judged
on) · 16AF/16AH (the parent COMPOSITE-30). Repro (additive; sealed engine files untouched):
`research/explosive_moves/gauntlet/build_c_bproxy.py` (the toggled-rule variant runner) +
`build_band_sweep.py` (the robustness sweep). SHA-256 of this file is recorded in the landing commit
and ledger 16BD; on the forward-test day it runs beside the other four sealed siblings.
