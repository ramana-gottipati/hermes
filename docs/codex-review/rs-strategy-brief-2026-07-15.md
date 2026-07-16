# EXTERNAL REVIEW BRIEF — Indian equity RS strategy. Everything tested, everything broken.

You are reviewing a full day's failed research. **Do NOT redo the work.** Read the evidence,
then answer ONE question: **which logic, if any, is most likely to actually work — or is the
honest answer "hold the index"?** Argue from the numbers below. Say "insufficient evidence"
where that is the truth.

Author's warning about himself: I retracted **six** headline findings today, every one because
I asserted something I had not checked. Treat every claim below as suspect unless it is marked
MEASURED. Please attack the reasoning, not just the arithmetic.

---

## 1. THE GOAL (the user's design, his words)

Ramana, a financial analyst in Vizag. His strategy, stated by him:
- Use **relative strength (a ratio)** to find the **best-performing sectors** vs a broad index
- Inside those sectors, pick the **best-performing companies** — "we must invest through the stocks"
- A **portfolio**, not one name: *"we can't rely entirely on one stock, nor can we diversify excessively"*
- **≤40 stocks**, RS-weighted, per-sector stops, exit on reversal
- Discriminator he insisted on: *"if a stock is performing well within its NARROW index, we target it"*
  = stock RS vs **its own sector**, not vs the broad index
- Later: *"identify the stocks or sectors BEFORE they have moved significantly"* (catch the turn)
- Later: *"any sector whose RS crossed 50 DMA, let's consider the stocks from them"*
- Target he set after an arithmetic correction: floor 17.3%, **aim 20–22% CAGR**

## 2. DATA (all MEASURED)

- `index_rows`: 205 NSE indices, 2004→2026. **Adjusted** (indices handle corporate actions). TRUSTWORTHY.
- `bhavcopy_rows`: 9.39M rows, 2004-07→2026-07. Series EQ (7.76M/4,230 syms), **BE (656k/2,554)**,
  SM, GB, BZ, ST, GS, N2. **RAW prices — NOT split/bonus adjusted.**
- `corporate_actions`: 26,891 rows / 2,546 syms. DIVIDEND 22,622 · OTHER 1,948 · **BONUS 716** ·
  **SPLIT 669** · RIGHTS 368 · BUYBACK 345. Ratios usable: BONUS 712/716, SPLIT 512/669.
  Dividend **amounts are only in free text** (`"Dividend - Rs 12 Per Share"`), 62.5% parseable.
- `stock_index_membership`: **FOUR WEEKS ONLY** (2026-06-17→07-14). No history.
- `stock_signals`: 5.97M rows, 2011→2026. Has `rs_vs_sector_today`, `rs_vs_broad_*`, `rsi_of_rs`,
  `rs_phase`, `primary_sector` — but `primary_sector` covers only **246 of 3,558** symbols
  (derived from the 4-week membership snapshot).
- **Universe churn (MEASURED):** 1,650 symbols traded in 2011 → only **895 still trade in 2026**
  (**46% dead**). At a ₹5cr ADV floor: 1,973 symbols ever mattered (1,693 live + **280 dead**).

## 3. BENCHMARKS — buy and hold, 2005-01→2026-07, 21.5y (MEASURED)

| index | ₹1 Cr → | CAGR |
|---|---|---|
| **Nifty Next 50** | **16.00×** | **13.8%** |
| Nifty 500 | 12.68× | 12.5% |
| Nifty 100 | 11.96× | 12.2% |
| Nifty 50 | 11.38× | 12.0% |
| Nifty Midcap 50 | 7.33× | 9.7% |

**Nothing built today beat 13.8%.**

## 4. THE SECTOR LADDER (index-level, TRUSTWORTHY — index data is adjusted)

| config | ₹1 Cr → | CAGR | retvol | MaxDD |
|---|---|---|---|---|
| **V8** pure sector rotation, no sleeve | **9.13×** | ~11.0% | 0.70 | −36.2% |
| V17 = V8 + defensive sleeve (residual→index above 200DMA, else cash) | 19.04× | | 0.79 | −39.2% |
| V21 = V17 + Next50 sleeve + recovery-accel + inverse-vol | 27.02× | | 0.87 | −40.8% |
| **V24** = V21 + own-percentile RSI-of-RS (LIVE candidate) | **30.35×** | **17.3%** | 0.911 | −37.7% |
| V32 = V24 + adaptive hysteresis band | 31.15× | | 0.90 | |
| V24 + trail−20% cull | 30.78× | 17.28% | **0.987** (0.993/0.999) | **−30.2%** |
| V24 + wider pond (+MNC/PSE/Commodities/Midcap50) | 26.97× | 16.6% | 0.883 | −36.9% |

**🔴 THE KILLER (MEASURED): V8 = 9.13× vs buy-and-hold Nifty 500 = 12.68×. Pure sector rotation
LOSES to doing nothing.** All of V24's outperformance appears when the **sleeve** is added — and
the sleeve is Nifty Next 50, which alone returns 16.00×/13.8%.

**Interpretation offered (ATTACK THIS): V24 is a Next-50 holding with a defensive sector overlay.
The sector selection contributes lower drawdown, NOT return.**

## 5. SECTOR GATES COMPARED (MEASURED, index data, 910 sector-quarters, forward 3m excess vs Nifty 500)

| gate | n | sectors/qtr | mean/qtr | **sd/qtr** | geo/qtr | SE on mean |
|---|---|---|---|---|---|---|
| NO GATE (every sector) | 910 | 10.5 | −0.02% | 9.23% | −0.45% | ±0.31% |
| **V24's LIVE gate (6m RS excess > +8%)** | 215 | 2.5 | **−0.70%** | 9.77% | **−1.18%** | ±0.67% |
| RS > 50DMA (state) | 434 | 5.0 | −0.10% | 9.23% | −0.53% | ±0.44% |
| **RS CROSSED 50DMA (Ramana's)** | 230 | 2.6 | **+0.28%** | **8.58%** | **−0.08%** | ±0.57% |
| RS < 50DMA (mirror) | 476 | 5.5 | +0.05% | 9.24% | −0.37% | ±0.42% |

**No mean is significant.** But the vol difference (8.58 vs 9.77, n≈220 each) is ~1.9 SE.
**V24's live gate is the WORST of five — worse than no gate.**

## 6. THE TURN (Ramana's recovery idea) — MEASURED, NO SIGNAL

2×2 on PRIOR (excess months 6→3 ago) × RECENT (excess last 3m), stocks inside qualifying sectors:

| cell | n | mean/qtr | sd/qtr | geo |
|---|---|---|---|---|
| TURN (was behind, now ahead) | 2,072 | +1.17% | 23.89% | −1.69% |
| ESTABLISHED LEADER | 1,527 | +1.71% | 24.17% | −1.21% |
| FADING | 2,262 | +1.55% | 23.25% | −1.16% |
| LAGGARD | 2,845 | +1.59% | 23.63% | −1.20% |

**SE = 0.53%. Total spread = 0.54% = ONE SE. Flat panel, no signal.** Sectors: same, all ~1 SE.
**Caveat: this is a crude SIGN-FLIP formulation. RS-level-with-inflecting-slope, RS-crossing-its-
own-trend, and RS-drawdown-recovery are UNTESTED.**

## 7. STOCK LAYER — the decomposition (MEASURED, adjusted prices, 8,646 stock-quarters)

Forward 3m excess vs Nifty 500, stocks INSIDE qualifying sectors:

| | mean/qtr | **sd/qtr** | drag (σ²/2) | **geo/qtr** |
|---|---|---|---|---|
| SECTOR INDEX (what V24 buys) | −0.67% | **10.31%** | 0.53% | **−1.20%** |
| stock pool, equal-weight | +1.54% | 23.77% | 2.83% | −1.28% |
| **TOP DECILE (what the book buys)** | **+1.97%** | **26.63%** | **3.55%** | **−1.58%** |
| **mid DECILE 6** | **+2.38%** | **22.75%** | 2.59% | **−0.21%** |

**⭐ DECILE 6 DOMINATES DECILE 10 ON BOTH AXES** (higher mean, lower vol). By mean D10 wins;
by geometric D10 comes LAST. **"Best of the best" is strictly dominated by "good."**

By decile: D1 −0.53% · D2 +1.93% · D3 +1.38% · D4 +1.19% · D5 +1.56% · **D6 +2.38%** · D7 +2.29%
· D8 +1.88% · D9 +1.57% · D10 +1.97%. **All positive except D1, FLAT above it.**

**REFUTED hypothesis (recorded so it is not re-tried):** "beat your own sector by X% is a small-cap
filter in disguise" — FALSE. corr(ADV pctile in sector, excess-vs-own-sector) = **+0.122 POSITIVE**.
Largest 20% by ADV: mean excess **+6.77%**; smallest 20%: **−9.00%**. It selects BIG winners.

## 8. THE FULL BOOK RUNS (stock layer — SEE §9, DATA IS SUSPECT)

Latest, with 591 inferred splits patched, EQ+BE+BZ, inverse-vol, quarterly, PIT, 0.15%/side:

| config | CAGR | MaxDD | ₹1 Cr → | beta | alpha | sectors/qtr |
|---|---|---|---|---|---|---|
| Nifty 500 | **11.7%** | −56.8% | **9.38×** | — | — | — |
| Ramana's 50DMA-cross gate → stocks, inv-vol | 10.0% | −69.8% | 6.84× | 1.06 | −1.0% | 2.8 |
| same, equal-weight | 8.6% | −71.9% | 5.36× | 1.11 | −2.6% | 2.8 |
| V24's +8% gate → stocks, inv-vol | 6.1% | −66.8% | 3.29× | 0.92 | −2.7% | 2.5 |
| **NO gate → stocks, inv-vol** | **10.0%** | −71.0% | 6.93× | 1.08 | −1.1% | 16.0 |

**Ramana's gate (10.0%) ≈ NO gate (10.0%). The sector step is INERT.** All lose to the index.

Earlier sector-conditioned run (before the split patch): 7.1–8.1% vs index 11.7%. That harness
**lacked V24's cap/sleeve/tapers** — a known unfair test, never fixed.

## 9. 🔴 EVERY BUG FOUND TODAY — six retractions

1. **ETF tradeability ASSUMED** — §3-F priced all 16 sector legs as "liquid ETFs @0.15%/side."
   **~6 of 16 (Media, Realty, Consumer Durables, Infrastructure, Oil&Gas, Metal-thin) have NO
   liquid Indian index instrument.** Never verified. Every V-number inherits it.
2. **SCOPE: the whole V8→V32 ladder picks SECTORS, never STOCKS.** Engine reads only `index_rows`,
   zero stock symbols. Half the brief was never built. Caught by Ramana, not me.
3. **Hysteresis does NOT transfer sector→stock.** On sectors it is the winning lever; on stocks,
   churn falls 330%→120%/yr and performance falls FASTER (alpha −0.5% → −7.3% as the band widens).
4. **Fill quality ASSUMED.** Exit test assumed 1,407 stops all filled AT the stop price. At 2%
   gap slippage + real costs, alpha → ~0 in every window.
5. **`series='EQ'` read NSE surveillance moves as DEATHS.** BE = trade-to-trade series, 656k rows.
   Of 9,604 "deaths": **84.4% still trading in another series next month; 79.1% return to EQ within
   12 months; only 12.2% genuinely gone.** Death rate halved 0.99%→0.47%/qtr when fixed.
6. **CORPORATE ACTIONS UNADJUSTED — the deepest.** Raw close reads a 1:2 bonus as −50%, a 10:1
   split as −90%, while `index_rows` IS adjusted → every stock-vs-index comparison rigged against
   the stock. **973 of 1,489 (65%) of EQ one-day drops worse than −40% sit within 3 days of a
   corporate action.** Fix moved one book's CAGR **−9.5% → +7.1% (~16pp)**. **The repo's own
   CLAUDE.md Guardrail #5 named this in advance: "Value > quantity… eliminates corporate-action
   adjustment bugs." It was violated in every stock script.**

**Plus, uncounted:** stale-price vol (illiquid names show fake-low vol → inverse-vol overweights
junk; the control collapsed to 1.71× at beta 0.38) · dead names credited **0%** instead of a loss
(≈ survivorship bias: dead=0% gives selection effect +2.06%, full exclusion gives +2.12% —
**identical**) · ADV look-ahead (filtered on the buy-month's full average) · **validating against
my own memory** (I "checked" ITC/TATAMOTORS against a half-remembered TOTAL-return figure while
measuring PRICE-only — the mismatch was MY error, not the data's).

## 10. 🔴 THE DATA IS STILL BROKEN — the live blocker

After adjustment, **1,415 EQ drops worse than −40% remain**: 202 explained by a recorded action,
**522 land within 4% of an EXACT split ratio** (315 at −50%, 70 at −90%, 53 at −60%, 50 at −80%,
34 at −67%) → **almost certainly MISSING corporate actions**; 691 look like genuine crashes.
**We hold 1,224 SPLIT/BONUS events; we need ~1,746. The table is ~30% incomplete.**
Adjustment logic VALIDATED where data exists: RELIANCE 4.8%→15.1%, HDFCBANK 3.7%→18.8%,
TCS 3.7%→14.0%, SUNPHARMA 7.9%→19.8%, MARUTI 17.0% (no actions, unchanged).

**Dividends (MEASURED): correctly ignored.** Both our prices and Nifty 500 are PRICE-only, so they
cancel. Yield gap: book **0.54%/yr** vs universe **0.73%/yr** → we are flattered by ~**0.19%/yr**
(≈0.3% adjusting for the 62.5% parse rate). **Not material.**

## 11. ✅ THE ONE BLOCKER THAT DISSOLVED

`stock_index_membership` = 4 weeks → "we cannot know who was in Nifty Auto in 2011" → I declared a
~1,973-name classification job necessary. **WRONG — it is unnecessary.** Assigning each stock to the
sector index its **EXCESS returns** correlate with most (trailing 500d, excess-vs-excess so it
measures sector co-movement not shared market beta) reproduces **NSE's own labels at 85.1% top-1 /
93.1% top-3** (random = 6.2%, n=202 labelled symbols). **Every weak sector is an OVERLAPPING one**
(Bank 1/3, Private Bank 3/5, FinServices 11/6, Infrastructure 4/8) — the method picking an
equally-correct sibling, so true accuracy is higher. **Works for dead companies** (they have returns
to their last day) → the full 21 years are testable, PIT, with no membership table.

## 12. FALSIFIED ELSEWHERE IN THIS PROJECT (cite before re-proposing)

- **REVERSAL family falsified at EVERY level** — 07-13 (timing), 07-14b FRACTAL FENCES:
  *"every fence fails; the reversal-pair program closes with ZERO tradeable survivors."*
- **Momentum = BETA not skill (t=1.99).** Only **LOWVOL_MOM quarterly large-cap** ever cleared the
  fundable bar (1.02 @₹50cr) — a LOW-VOL tilt, not raw momentum. §7's drag finding is a candidate
  MECHANISM for why (momentum supplies edge, low-vol removes the toll) — **unverified**.
- Short/F&O leg REJECTED (0.49 vs 0.87) · monthly cadence REJECTED 3× (churn) · book-level 200DMA
  kill REJECTED (wealth collapses; works only on the residual sleeve) · book-level vol-targeting
  REJECTED (MaxDD blew to −50.8%/−53.6%) · "raise the liquidity bar" REJECTED (at ₹25cr the pond
  sinks MORE, −1.52%, AND selection collapses +1.73%→+0.20% — momentum is a small/mid-cap effect).
- **C-BLEND 1.32 = flat-cost-only, NOT fundable.** CCI alpha FALSIFIED. PEAD wrappers net-fail.
- Constraint: **primary sources only** (NSE/BSE/SEBI/XBRL). No vendors, no Screener.

## 13. ⚠ SELECTION-ON-ONE-WINDOW RISK

Everything above was selected on **ONE window (2005–2026)**. The sector ladder alone is **four
rounds deep** (V1→V8→V17→V21→V24→V32). Trail−20% is 1 of 10 tested. A prior lane already found
V24-vs-V32 **statistically indistinguishable** (0.013 gap vs a 0.148 noise floor, p=0.745) and
retired V32. **The TR-benchmark re-cut is still owed** — no total-return index exists in `index_rows`,
so every comparison above is price-index vs price-index.

---

# THE QUESTION

Given ALL of the above:

1. **Is there ANY logic here likely to beat Nifty Next 50 (13.8%/16.00×) net of real costs?**
   Or is "hold Next-50" the honest answer? Say so if so.
2. **Is the §4 interpretation right — that V24's 17.3% is the Next-50 sleeve plus a defensive
   overlay, not sector selection?** It is the load-bearing claim. Attack it.
3. **§7's decile-6-dominates-decile-10 is the only finding I still believe.** Is it real, or is it
   noise I have not tested properly? What test would falsify it?
4. **Ramana's 50DMA-cross gate ties with NO gate.** Does that kill the sector step entirely, or is
   there a formulation that would not be inert?
5. **What is the ONE experiment worth running next** — assuming the corporate-action data gets
   completed from NSE first? Be specific enough to implement.
6. **What have I got wrong above?** I have retracted six things today. Assume there is a seventh.

Answer in order. Be blunt. "Insufficient evidence" is a valid and welcome answer.
