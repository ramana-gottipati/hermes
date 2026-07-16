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

**One-line definition:** a long-only, stock-level book that holds every liquid Indian stock which is EITHER
recovering from an oversold relative-strength dip (the *turn*) OR showing confirmed, persistent relative
strength (the *trend*) — top 60 equal-weighted, idle capital parked in a Nifty Next 50 sleeve while the market
is healthy, each name closed on a −20% trailing stop, rebalanced quarterly.

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

**D. Ranking & sizing.** Rank the qualifying names by RSI strength, keep the **top 60**, **equal-weight**
(1/60 each). *Inverse-volatility sizing was tested (ledger 16X) and REJECTED as a wash — do not substitute
it.*

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

## 4. Status & candidate ladder

- **The UNION** — the sealed lead. In-sample 2006–2026: the best full-period result of the RS arc. *(Numbers
  live in the ledger, §16V, never restated here.)*
- **Signal A alone** and **Signal B alone** — each beats the Next-50 bar in-sample but by less; the union
  beats both. Recorded reference points, not separate strategies.
- **Rejected candidates** (do not re-run): throttle (16W), inverse-vol (16X), the AND-intersection (16V).

## 5. Known weakness (disclosed, not hidden)

Walk-forward, the Union is strongly positive in 2006–2011 and 2018–2026 but **negative in 2012–2017** — a
mid-cycle bull where a lower-beta book lags a raging cap-weighted index. **Two structurally-correct fixes
(exposure throttle, inverse-vol) both failed to close it**, which establishes the weakness is *selection*
(which stocks are picked in that regime), not sizing. That is a harder, still-open research question — and one
that must NOT be pursued by re-optimising on the same window.

## 6. Data & provenance

NSE bhavcopy (primary source; corporate-action table VERIFIED complete vs NSE, ledger 15S) + NSE index closes
(`index_rows`, adjusted). PIT throughout. **Price-index benchmark** (Nifty Next 50 price, not total-return) —
disclosed wherever numbers are shown; the TRI re-cut is owed and moves both sides. The `fundamentals_history`
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

- **The forward test is the ONLY thing that matters next.** When a new quarter closes, run the Union against
  the sealed criteria in [`../prereg/union-prereg.md`](../prereg/union-prereg.md) — **do not touch the spec.**
  PASS requires, over ≥8 forward quarters: CAGR > Next-50 net of cost · alpha > 0 (not just beta) · MaxDD not
  worse · no single quarter > 60% of the excess. Miss → DESCRIPTIVE-ONLY, never deployed.
- **TR-benchmark re-cut** (owed across the whole RS estate).
- **The 2012–17 selection question** — the one genuine open research direction, and the hardest. Not to be
  attacked by re-optimising on the in-sample window.

## 10. Sources of truth

Ruleset + terminology: **this page**. Every result number: [strategy-ledger.md](../strategy-ledger.md)
§§ 2026-07-16U → 2026-07-16X. Frozen spec + forward criteria + seal:
[`../prereg/union-prereg.md`](../prereg/union-prereg.md). Code: `research/explosive_moves/cash_blend.py`,
`cash_6b.py`, `dim6.py`, `dim6g.py`, `cash_throttle.py`, `cash_ivol.py`.
