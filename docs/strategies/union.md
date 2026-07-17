# The Union (RS turn ∪ RS trend, stock-level) — Canonical Reference

> ## 🟡 STATUS — READ BEFORE ANY NUMBER ON THIS PAGE
>
> **This is a PRE-REGISTERED LEAD, not a deployed strategy, and NOT investment advice.** Every number below
> is **IN-SAMPLE** — the Union was selected after seeing 2005–2026 across ~30 configurations, so its 17.5%
> CAGR is a research lead inflated by selection, not evidence. It is **SEALED for forward testing**
> ([`docs/prereg/union-prereg.md`](../prereg/union-prereg.md), SHA-256
> `a9a14058f2140e22639b9504ab6d4af9c60fc76144de0f9f5e47f21b1b98d21c`) and may not be deployed until it clears
> its frozen forward criteria. **No live surface** — there is deliberately no `/dash` page, because a page
> would imply tradeability the evidence does not yet support.
>
> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** **RESEARCH — PRE-REGISTERED LEAD.** The one construct from the 2026-07-15/16 RS arc that beat
> Nifty Next 50 in-sample on return, drawdown AND beta together — built entirely on Ramana's theses (the RS
> turn + RS persistence + cash-out sizing) over the trailing-stop / index-sleeve machinery. Awaiting forward
> evidence; every sizing "fix" tested (throttle · inverse-vol) was rejected. **Governing record:**
> [strategy-ledger.md](../strategy-ledger.md) §§ 2026-07-16U → 2026-07-16X.
> **Origin:** 🧑 RAMANA (both signal theses — "catch the oversold RS turn before it runs" and "confirm
> persistent relative strength", plus the cash-out/set-aside sizing instinct) + 🏠 HOUSE (the union
> construction, the PIT harness, the falsification + pre-registration). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference. Result numbers live ONLY in
> [strategy-ledger.md](../strategy-ledger.md); code lives in `research/explosive_moves/cash_blend.py` (the
> union) · `cash_6b.py` (6b book) · `dim6.py`/`dim6g.py` (the reversal battery that isolated 6b). This page
> states the RULESET (definitional) and links the rest.

**One-line definition:** a long-only, stock-level book that holds every liquid Indian stock which is EITHER recovering from an oversold relative-strength dip (the *turn*) OR showing confirmed, persistent relative strength (the *trend*) — top 60 equal-weighted, idle capital parked in a Nifty Next 50 sleeve while the market is healthy, each name closed on a −20% trailing stop, rebalanced quarterly.

---

## 1. What it is — and what it is NOT

It is the answer to a question Ramana pressed all through the 2026-07 RS arc: *"we are taking the best of the
best of the best stocks and still struggling — why?"* The arc's central finding (ledger 15P) was that chasing
the **single strongest** names buys peak volatility and loses to the variance toll. The Union is the
opposite instinct made mechanical: hold **strong-but-not-extreme** names, caught either as they *turn up* or
once their strength is *confirmed*, and let a stop and a sleeve carry the risk.

It is **NOT** the sector ladder ([sector-rotation.md](sector-rotation.md), which selects sector INDICES, not
stocks). It is **NOT** deployed, and it is **NOT** a recommendation. It is a sealed lead awaiting its own
forward test.

## 2. Our variation vs. the standard technique

Textbook momentum buys the top-ranked names and rebalances. The Union departs on three of Ramana's axes:
(a) **two entry modes, not one** — a mean-reversion *turn* signal (rare in momentum books) is unioned with a
trend signal, because the arc proved they fire on different stocks at different times (11% overlap; the
intersection is only 9% invested); (b) **the middle of the strength band, not the peak** — the persistence
gate and the oversold-turn both deliberately avoid the extreme top decile that 15P showed is dominated by
"merely good"; (c) **idle capital is never dead** — the un-invested fraction works the index sleeve (the V17
lesson) instead of sitting in cash or being force-concentrated into a handful of names.

## 3. How it works — THE COMPLETE RULESET (definitional)

**A. Universe (checked each rebalance).** NSE bhavcopy series **EQ + BE + BZ**, prices **corporate-action
adjusted** (`adjust.py`), with the runtime **split-ratio quarantine** (`quarantine.py`, ~156 symbols whose
recorded split ratios do not reconcile — excluded, nothing written to the DB). A stock is eligible only if its
**prior-month** average daily traded value ≥ **₹5 crore** (liquidity, no look-ahead). Dead names realise
**−50%** on delisting; a name that simply doesn't print on a date is carried, not punished. Zero survivorship
bias — every stock is present on exactly the dates it was tradeable.

**B. Sector assignment (PIT).** Each stock is mapped to one of the 16 NSE sector indices by which sector its
**trailing-500-day excess returns** correlate with most. No membership table is used (reproduces NSE's own
labels at ~85%). This is what lets both signals reference a stock's *own* sector.

**C. The two signals — a stock qualifies if EITHER fires (the UNION):**
- **Signal A — TREND (RSI + persistence):** price **RSI(14)** is above its own **50-day simple moving
  average** (SMA beat EMA in testing), AND the stock beat its own sector index on **≥ 70% of the trailing
  quarter's trading days**.
- **Signal B — TURN ("6b"):** the **RSI(14) of the RS line** (stock ÷ its own sector) was **below 30** within
  the trailing ~60 days and has **crossed back ≥ 30**. No persistence gate — 6b fires early, before
  persistence can exist.
- The two are **mutually exclusive by construction** (a stock just turning up hasn't had a persistent
  quarter). Combined by **OR only** — the intersection (AND) collapses to ~9% invested and underperforms; do
  not use it.

**D. Ranking & sizing.** Keep the first **60** qualifiers **in the engine's qualifier order** (symbol-load
order — effectively an arbitrary, stable sample of the qualifying set), **equal-weight** (1/60 each).
*Correction (2026-07-16, ledger 16Z): this page previously said "rank by RSI strength" — the engine never
ranked, and when ranking was actually tested, BOTH RSI-descending and RSI-ascending truncation LOST to the
arbitrary order (15P physics: the top of the strength band buys the variance toll). The engine's behaviour,
which produced every recorded number and runs the forward test, is definitional.* *Inverse-volatility sizing
was tested (ledger 16X) and REJECTED as a wash — do not substitute it.*

**E. The residual sleeve (the V17 mechanic).** The un-invested fraction (fewer than 60 names qualify, or stops
have fired) is held in **Nifty Next 50 while Nifty 500 ≥ its 200-day SMA**, else in **cash**. The stock book
is never touched by this switch. *(Why sleeve-only: applied to the whole book, the same 200DMA kill destroys
wealth — the standing V8→V17 lesson.)*

**F. Exit & cadence.** A **−20% trailing stop** from each position's peak close, filled with **1% slippage**.
**Quarterly** rebalance. Costs **0.15% per side**.

**G. What was tested and must NOT be added** (each rejected with numbers, ledger cited):
- **Consistency gate on 6b** — halves the return (6b + persistence are mutually exclusive). 16V.
- **Market-stretch throttle** on the invested fraction — worsened every metric. 16W.
- **Inverse-volatility stock sizing** — a wash, net slightly worse. 16X.
- **BE-surveillance veto · fundamentals veto** — one falsified, one inert. 16T.
- **Sector-neutral name caps** — starve the book; its sector concentration is load-bearing. 16Z.
- **RSI-ranked truncation (either direction)** — loses to the engine order (see D). 16Z.
- **6b threshold variants (25 / 35 / 25→30) · 6b∪6f · weekly-RS 6b · daily-AND-weekly confirmation** —
  every one worse than the sealed rules. 16Z.
- **Quality/valuation tilt at selection** (Screener-table, G#8-disclosed) — dead; the 16T "fundamentals
  add nothing here" doctrine now covers tilts as well as vetoes. 16Z.
- **ML re-ranking of the qualifiers** — the pre-registered primary model failed its frozen bar (16AA);
  any new attempt requires a fresh pre-registration, never an in-sample score.

## 4. Status & candidate ladder

> 📋 **The complete family record** — every configuration in full (rulesets + all recorded numbers),
> the sealed validation (C1/C2/C3 significance · interim OOS · deflation · PBO), and the deflated
> forward expectations — lives in the **[Union Ladder compendium](union-ladder.md)**.

- **The UNION** — the sealed lead. In-sample 2006–2026: the best full-period result of the RS arc. *(Numbers
  live in the ledger, §16V, never restated here.)*
- **UNION-β14 — the pre-registered SIBLING lead (2026-07-16, ledger 16Y):** the union plus exactly one rule —
  a qualifier whose trailing-250d beta vs Nifty 500 exceeds 1.4 is excluded at selection. In-sample it beats
  the union on return, drawdown, beta AND alpha together and flips the 2012–17 window positive, surviving
  four pre-declared kill checks (threshold plateau, beta-window, dead-cash decomposition, missing-data).
  **Same epistemic class as the union — an in-sample-selected lead** — so it is sealed beside it
  ([`union-beta14-prereg.md`](../prereg/union-beta14-prereg.md), SHA-256 `08b46199…`) with a frozen sibling-
  adjudication rule; the forward window judges both.
- **UNION-C40RA — the THIRD pre-registered sibling (2026-07-16 S168, ledger 16AB):** β14 plus exactly two
  rules — rank the capped qualifiers by RISKADJ (6-month return ÷ 3-month volatility, the estate's
  best-of-32 factor) and hold the top 40. In-sample it is the family's best (all three windows
  alpha-positive) and it survives the 2%-slip and next-day-execution honesty passes; the worst honest case
  still clears every sibling. Third-generation in-sample selection — sealed
  ([`union-c40ra-prereg.md`](../prereg/union-c40ra-prereg.md), SHA-256 `0715a0d9…`) with the multiplicity
  risk disclosed inside and a frozen three-way adjudication. **The family stops at three registrations.**
- **A2-COMPOSITE — a DEFERRED LEAD, not a registration (2026-07-16 S171, ledger 16AE):** the C40RA
  machinery with an ERA-RELATIVE liquidity floor (monthly ADV percentile calibrated to today's ₹5cr
  equivalent, clamped at ₹1cr) and the bear-state idle earning the documented risk-free rate. In-sample it
  is the first union-family book to clear Ramana's 25% bar, surviving 2%/3%-slip and next-day-execution
  stress — but it CHANGES THE BOOK'S CHARACTER (small/mid-cap tilt in the early windows; median pick-ADV
  roughly a third of C40RA's; personal-scale execution only). The sibling family is closed at three, so
  this is recorded and HELD: registration awaits the 2026-10-03 forward verdict or Ramana's explicit
  reopening (both queued decisions in the ledger entry).
- **COMPOSITE-30 — THE CONFIRMED LEAD, the FOURTH sealed sibling (Ramana 2026-07-16; ledger 16AF/16AH):**
  the A2-composite plus concentration at top-30 (re-proven viable on the widened universe) and
  let-winners-run weight drift (retained names keep market-drifted weight, hard cap 5%). In-sample the
  family's best on return; the deeper drawdown was explicitly on the table when Ramana confirmed it. The
  family was REOPENED by owner decision and this spec is SEALED
  ([`union-composite30-prereg.md`](../prereg/union-composite30-prereg.md), SHA-256 `07ef2ef9…`) with a
  four-way family adjudication. Fifth-generation in-sample selection, stated in the registration.
  **Validated (S176, ledger 16AL):** the sealed ladder-validation protocol passed its frozen D139 gate
  (the C40→COMPOSITE-30 increment is statistically real, p=0.014), survival 1.01 on the 2019+ interim
  hold-out, dead-name stress clean — with the era-floor rung flagged as the highest window-fit risk and
  the honest forward expectation deflated to ≈21.6% ([union-ladder.md](union-ladder.md) §9).
- **A2-COMPOSITE — the lower-drawdown alternative, recorded IN FULL** ([union-ladder.md](union-ladder.md)
  §5), unregistered, registration-ready on Ramana's word.
- **Signal A alone** and **Signal B alone** — each beats the Next-50 bar in-sample but by less; the union
  beats both. Recorded reference points, not separate strategies.
- **Rejected candidates** (do not re-run): throttle (16W), inverse-vol (16X), the AND-intersection (16V),
  the twelve-candidate battery of 16Z (sector caps · RSI ranks · beta-rank-asc · 6b variants · 6b∪6f ·
  weekly/MTF · quality tilt), the pre-registered ML rankers **BOTH generations** (16AA Ridge-primary ·
  16AG GBM-primary over the era-floor pool — the hand rule beat the machine both times; beta was the #1
  learned feature all three runs), and the S168 kills (16AC): trail widths other than 20 · sleeve-index
  swaps · cap-floor refill · vs-bench consistency · **monthly cadence (4th confirmation of the cadence
  law)** · the cross-family LOWVOL_MOM blend (return-corr 0.83 — dilution). Concentration below top-30 and
  vol-based sizing stay dead (16AF narrowed the 16X sizing wall to vol-based only).

## 5. Known weakness (disclosed, not hidden)

Walk-forward, the Union is strongly positive in 2006–2011 and 2018–2026 but **negative in 2012–2017** — a
mid-cycle bull in which the book ran hot (high beta, near-fully invested) and still lagged. **Two
structurally-correct sizing fixes (exposure throttle 16W, inverse-vol 16X) both failed to close it**, which
established the weakness is *selection* (which stocks are picked in that regime), not sizing.

**2026-07-16 update (ledger 16Y): the selection fix was found in-sample.** A per-name trailing-beta cap at
selection closes the window — and the effect survives a dead-cash decomposition, so it is the stock choice,
not sleeve time. Because the fix was itself selected from a candidate battery on the same history, it earns
only sibling pre-registration (see §4), not a claim. The forward window decides. The in-sample give-back is
disclosed in the ledger: 2006–11 return is somewhat lower under the cap (fewer low-beta qualifiers existed
then), at materially lower beta.

## 6. Data & provenance

NSE bhavcopy (primary source; corporate-action table VERIFIED complete vs NSE, ledger 15S) + NSE index closes
(`index_rows`, adjusted). PIT throughout. **Price-index benchmark** (Nifty Next 50 price, not total-return) —
disclosed wherever numbers are shown; **the TRI re-cut is DONE (S174, ledger 16AJ): the honest hurdle is Nifty Next 50 TRI 14.6%/yr and every family member's alpha survives it** — TRI columns are reported beside every future judgment ([union-ladder.md](union-ladder.md) §8); the sealed criteria stay PR-vs-PR as frozen. The `fundamentals_history`
veto experiment (16T) touched the Screener-sourced table read-only (Guardrail #8 disclosure) and is not part
of the live ruleset.

## 7. Terminology canon

- **The Union** — hold a stock if the TURN signal OR the TREND signal fires. The binding name for this
  construct.
- **Signal A / TREND** — RSI(14) > its 50-day SMA, plus ≥70% same-quarter persistence vs the stock's own
  sector.
- **Signal B / TURN / "6b"** — RSI(14) of the RS line recovering from < 30 back above 30. ("6b" is its ID from
  the Dimension-6 reversal battery, ledger 16U, where it was the only one of eight indicators to survive.)
- **The sleeve** — idle capital in Nifty Next 50 above the 200DMA, else cash (the V17 mechanic).
- Distinguish **RSI of price** (Signal A's trigger) from **RSI of the RS line** (Signal B's trigger) — two
  different constructs.
- Do NOT confuse the Union (STOCK-level) with the sector ladder ([sector-rotation.md](sector-rotation.md),
  INDEX-level) or the descriptive RS suite ([relative-strength.md](relative-strength.md)).

## 8. Decision & session history

- **2026-07-15/16 (the RS arc)** — Ramana drove a full stock-level investigation after the sector ladder was
  found to select sectors not stocks. The arc produced 8 data/method retractions, killed ~9 ideas with
  numbers, and left exactly one survivor: the Union. Codex external review (ledger 15R) confirmed the honest
  framing. The two component signals trace directly to Ramana's own theses (catch the turn; confirm
  persistence).

## 9. Open items

- **The forward test is the ONLY thing that matters next — and it now adjudicates a THREE-SIBLING FAMILY.**
  When a new quarter closes, run the Union ([`union-prereg.md`](../prereg/union-prereg.md)), union-β14
  ([`union-beta14-prereg.md`](../prereg/union-beta14-prereg.md)) and union-C40RA
  ([`union-c40ra-prereg.md`](../prereg/union-c40ra-prereg.md)) — **touch no spec.** Each is judged on its
  own frozen criteria; among passers, highest forward alpha graduates (the FOUR-way rule is frozen in the
  COMPOSITE-30 registration, which also records Ramana's explicit reopening of the family). The scheduled
  2026-10-03 task runs the union's engine; the same session runs ALL SIX ladder rows
  ([union-ladder.md](union-ladder.md) §8): the four sealed siblings judged on their own criteria, the two
  recorded composites for the record.
- ~~TR-benchmark re-cut~~ **✅ DONE S174 (ledger 16AI/16AJ)** — data + tool committed; the residue is
  the prod `index_rows` ingestion (feed-lane protocol), research needs are met from files.
- ~~The 2012–17 selection question~~ — **answered in-sample 2026-07-16 (ledger 16Y, the beta cap) and moved
  into the sibling registration above.** The remaining open questions are the forward evidence itself and the
  TR re-cut; the non-ML candidate space around this signal family is otherwise SPENT (16Z catalogues the
  kills). ML re-attempts require a fresh pre-registration (16AA).

## 10. Sources of truth

Ruleset + terminology: **this page**. **Every family configuration IN FULL (specs + all numbers,
incl. the unregistered composites): [union-ladder.md](union-ladder.md).** Every result number:
[strategy-ledger.md](../strategy-ledger.md)
§§ 2026-07-16U → 2026-07-16X (the union arc), §§ 2026-07-16Y/Z/AA (the S165 battery, the β14 sibling, the
ML verdict) and §§ 2026-07-16AB/AC/AD (the S168 battery, the C40RA sibling, the kills, the total-return
measurement). Frozen specs + seals: [`../prereg/union-prereg.md`](../prereg/union-prereg.md) ·
[`../prereg/union-beta14-prereg.md`](../prereg/union-beta14-prereg.md) ·
[`../prereg/union-c40ra-prereg.md`](../prereg/union-c40ra-prereg.md) ·
[`../prereg/union-ml-prereg.md`](../prereg/union-ml-prereg.md). Code: `research/explosive_moves/cash_blend.py`,
`cash_6b.py`, `dim6.py`, `dim6g.py`, `cash_throttle.py`, `cash_ivol.py`, `union_lab.py`, `union_lab2.py`,
`union_ml.py`, `union_lab3.py`, `union_lab3b.py`, `blend_u25.py`.
