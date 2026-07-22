# PRE-REGISTRATION — UNION A2-HOLD, forward test (the SIXTH sibling; the lower-drawdown HOLD variant)

> **Class:** PRE-REGISTERED forward-test spec. It is the A2-composite (the lower-drawdown alternative
> recorded in `docs/strategies/union-ladder.md`, never itself registered) PLUS the one hold-band lever
> "C" — the equal-weight cousin of K30-HOLD (`e6994c19…`). Hashed and committed before any
> forward-window data exists; editing this file after the forward window opens voids it.
> **Registered:** 2026-07-22 (the "improve the R logic" inquiry, ledger 16BD). **Origin:** 🏠 HOUSE
> (the hold-longer lever, its robustness sweep, the Zerodha-gauntlet falsification); the parent A2
> selection is 🧑 RAMANA's union composite.
> **Multiplicity disclosure:** this is the SIXTH spec on the same forward window (union `a9a14058…` ·
> β14 `08b46199…` · C40RA `0715a0d9…` · COMPOSITE-30 `07ef2ef9…` · K30-HOLD `e6994c19…` · this).
> A2-HOLD and K30-HOLD share the SAME hold-band lever and differ only in base (A2 = equal-weight
> top-40, lower drawdown; K30 = drift-weight top-30, higher CAGR/deeper drawdown) — they are NOT
> independent bets. The one frozen family-adjudication rule (highest forward alpha among passers)
> picks AT MOST ONE graduate across all six.

## Why this exists

A2 is the estate's recorded lower-drawdown union alternative (−27 to −33% vs K30's −38%). The
2026-07-22 inquiry showed the hold-winners-longer lever "C" (ledger 16BD) lifts A2 the same way it
lifts K30, net of the exact Zerodha gauntlet (16BC), while leaving the drawdown unchanged. A2-HOLD
seals that combination as the CONSERVATIVE member of the HOLD pair. B-proxy (price-crash filter) was
inert and B (governance blow-up filter) is untestable historically — neither is in this spec
(both recorded in 16BD).

**Epistemic status:** a variant of an in-sample-recorded lead, with ONE added lever whose robustness
is demonstrated but whose forward edge is unproven. Codex 15R applies at maximum force. The forward
window is the only judge.

## THE FROZEN SPEC (complete and self-contained; identical to COMPOSITE-30 except the marked items)

Everything in `docs/prereg/union-composite30-prereg.md`'s frozen spec is inherited VERBATIM —
universe (EQ/BE/BZ, CA-adjusted, era-relative liquidity floor P=0.450, dead −50%), PIT sector
assignment, the UNION signals (TREND ∪ TURN), beta-cap ≤ 1.4, RISKADJ rank, idle→Next-50/rf,
trailing stop −20% @ 1% slip, 0.15%/side, quarterly rebalance, same-close convention (next-day
reported beside) — WITH THESE THREE DIFFERENCES (the A2 base + the C lever):

1. **Selection size: HOLD THE TOP 40** (not 30).
2. **Weights: EQUAL-WEIGHT (1/40 each), re-set every rebalance** — A2 does NOT use K30's
   let-winners-run drift-weight; each held name is returned to its 1/40 slot each quarter.
3. **HOLD / EXIT BAND (the C lever, the only difference from plain A2).** At each quarterly
   rebalance a held name is **RETAINED while it remains within the top 80** by the RISKADJ score
   (twice the 40-name selection — fixed a priori, the SAME 2×-holdings rule as K30-HOLD). The book
   refills to 40 from the highest-ranked non-held survivors. A held name exits only when it drops
   out of the top 80, hits its −20% trailing stop, or dies.

## IN-SAMPLE RECORD (2005–2026, for the record — NOT the test; ledger 16BD)

Measured on the Zerodha per-name gauntlet (16BC), A2-HOLD (band = top-80) vs the A2 baseline on the
identical engine and cost model:

| | flat CAGR | NET CAGR (gauntlet) | ₹1cr → | worst drop | turnover/yr |
|---|---|---|---|---|---|
| A2 baseline | 25.5% | 17.2% | ₹25.0cr | −33% | 274% |
| **A2-HOLD (this spec)** | **26.6%** | **18.6%** | **₹31.5cr** | **−33%** | 260% |

Robustness (net gain vs baseline, same window): band 60 +1.1 · 70 +1.4 · **80 +1.4** · 90 +1.6 —
every value positive, drawdown −33/−34% throughout. Band fixed a priori at 2× holdings (band 80),
mid-plateau (NOT the peak). **All IN-SAMPLE; net-of-cost is NOT net-of-selection — deflate forward.**
Personal-scale only (capacity inherited from the union family's ~₹25–50cr, 16BC). **⚠ Codex caveat
(16BC): equal-weight union books slightly UNDERCHARGE continuing-name reweight drift under this
gauntlet → A2-HOLD's net is mildly OPTIMISTIC relative to the drift-weighted K30-HOLD, which is
charged correctly.** A2-HOLD's real appeal is the shallower drawdown, not a higher net than K30-HOLD.

## PASS / FAIL — frozen criteria, judged ONLY on data after the registration date

Over ≥ 8 forward quarters from 2026-07 (the SAME four criteria as all union siblings):
(1) CAGR > Nifty Next 50 buy-and-hold net of the modelled costs · (2) alpha > 0 with forward beta
reported (excess purely from beta > 1.1 = FAIL) · (3) MaxDD not worse than Nifty Next 50's over the
same window · (4) no single quarter > 60% of the total excess. Miss 1–3 → DESCRIPTIVE-ONLY, never
deployed; criterion 4 → inconclusive, extend.

**FAMILY ADJUDICATION (frozen):** among ALL registered specs that PASS their own criteria over the
same forward window, the one with the highest forward ALPHA graduates; the others retire to
reference status. If none pass → all DESCRIPTIVE-ONLY. A2-HOLD's near-identity to A2 and its shared
lever with K30-HOLD are disclosed above so a joint pass is not read as separate discoveries.

## What is NOT claimed

Not that 18.6% net recurs (selection + one more in-sample lever inflate it, and the EW undercharge
makes it mildly optimistic); not that it beats K30-HOLD net (its case is lower drawdown, not higher
return); not that drawdown stays −33%; not personalized advice; not institutional capacity.

## Canon

Ledger: **2026-07-16BD** (the three findings, K30-HOLD, and this A2-HOLD seal) · 16BC (the gauntlet)
· 16AE (the A2 era-floor base). Repro (additive; sealed engine files untouched):
`research/explosive_moves/gauntlet/build_c_bproxy.py` + `build_band_sweep.py` + `build_a2_sweep.py`.
SHA-256 of this file is recorded in the landing commit and ledger 16BD; on the forward-test day it
runs beside the other five sealed siblings.
