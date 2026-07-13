# Pat — seasonal ranking demo (ask in plain English, get the report)

> **What this is.** A live demo of Pat's **seasonal ranking** flow: ask for the historically
> strongest (or weakest) stocks for **this month / next month / this week / next week**, and Pat
> returns a ranked report over the same per-entity calendar base-rates the This-month screen
> ranks. Built in Session 127 (`src/pat/seasonal_flow.py` + `engine.py` + `web.py`, commit
> `55dbfdf`); live at **`/dash/pat`**.
>
> **The one rule that governs all of it (SEBI-safe):** this is **descriptive calendar history,
> never a forecast, ranking-to-trade, or recommendation.** Expectancy is ≈ 0 net of STT + impact.
> Every answer carries that fence; so does this doc.
>
> ⏱ **Outputs below are a dated snapshot (2026-07-13/14).** The names change with the calendar
> (this/next month & ISO week are computed live) and as the nightly seasonal snapshot updates —
> re-run the query to see the current read.

---

## What you can ask

Type any of these at `/dash/pat` (or the Cmd-K bar). Recognition is deterministic and ₹0 — it
fires only on a `<this|next> <month|week>` period + a ranking/seasonal intent:

- **Bullish:** *top stocks this month* · *top-ranked stocks for next month* · *strongest stocks
  this week* · *seasonal winners next month* · *best stocks next week*
- **Bearish (the reverse):** *historically bearish stocks this month* · *seasonal losers next
  week* · *weakest stocks this week* · *worst stocks next month*

It deliberately **yields** when the ask isn't seasonal: *"biggest movers this week"* → the movers
flow; *"will nifty go up next month"* → the prediction guardrail (Pat doesn't forecast).

---

## How to read the report

Every row is one stock's historical base-rate **for that one calendar cell** (a month, or an ISO
week), after stripping the market move. Columns:

| Column | Meaning |
|---|---|
| **Hit-rate k/n (P%)** | years the cell was **up** out of the years of history (e.g. 18/19 = up 18 of 19 Julys) |
| **95% CI** | Wilson confidence interval on that hit-rate — **if it straddles 50%, the lean is noise** |
| **Mean residual** | the average size of the move, in σ (market-stripped) |
| **Years** | depth of history (a **≥15-year floor** applies) |

**Ranking = confidence-adjusted**, mirroring the This-month screen's default: **bullish** sorts by
the Wilson **lower** bound (so many steady years beat a lucky 3/3); **bearish** by the Wilson
**upper** bound (most-reliably-down first). Ties break on the **mean residual** (bigger move wins).

---

## Live examples

### 1. "top stocks this month" — bullish, July

| # | Symbol | Hit-rate | 95% CI | Mean resid | Yrs |
|---|---|---|---|---|---|
| 1 | TORNTPHARM | 19/19 (100%) | 83–100% | +0.21σ | 19 |
| 2 | MRF | 18/19 (95%) | 75–99% | +0.27σ | 19 |
| 3 | BATAINDIA | 18/19 (95%) | 75–99% | +0.17σ | 19 |
| 4 | GRANULES | 17/18 (94%) | 74–99% | +0.35σ | 18 |
| 5 | SONATSOFTW | 17/18 (94%) | 74–99% | +0.22σ | 18 |

*Reading:* TORNTPHARM's 19 straight positive Julys give the highest lower bound (83%), so it leads.
MRF ranks above BATAINDIA on the tie-break — both 18/19, but MRF's average July is bigger (+0.27σ
vs +0.17σ).

### 2. "top stocks next month" — bullish, August

| # | Symbol | Hit-rate | 95% CI | Mean resid | Yrs |
|---|---|---|---|---|---|
| 1 | HAVELLS | 18/18 (100%) | 82–100% | +0.25σ | 18 |
| 2 | KOTHARIPRO | 17/17 (100%) | 82–100% | +0.28σ | 17 |
| 3 | XPROINDIA | 16/17 (94%) | 73–99% | +0.23σ | 17 |
| 4 | JAICORPLTD | 16/17 (94%) | 73–99% | +0.22σ | 17 |
| 5 | BPL | 15/16 (94%) | 72–99% | +0.24σ | 16 |

*Reading:* HAVELLS (18/18) edges KOTHARIPRO (17/17) even though KOTHARIPRO moves more — 18 perfect
Augusts give a slightly higher lower bound (82.4% vs 81.6%) than 17. More evidence wins.

### 3. "historically bearish stocks this week" — bearish, ISO week 29

| # | Symbol | Up k/n | 95% CI | Mean resid | Yrs |
|---|---|---|---|---|---|
| 1 | PARSVNATH | 2/15 (13%) | 4–38% | −0.26σ | 15 |
| 2 | MANGCHEFER | 3/15 (20%) | 7–45% | −0.34σ | 15 |
| 3 | LICHSGFIN | 4/18 (22%) | 9–45% | −0.24σ | 18 |
| 4 | ELGIEQUIP | 4/18 (22%) | 9–45% | −0.18σ | 18 |
| 5 | NIPPOBATRY | 4/18 (22%) | 9–45% | −0.15σ | 18 |

*Reading:* the `k/n` column is still **years up**, so a *low* number = reliably down. PARSVNATH was
up only 2 of its last 15 week-29s (~87% down), and its CI (4–38%) sits entirely below 50% — a real
lean, not noise. Weekly base-rates rest on fewer observations than monthly, so treat them as noisier.

### Also served (same session, symbols only)

- **"historically bearish stocks this month"** (July) → KOTAKBANK · UNIONBANK · SUTLEJTEX · ABB · NTPC
- **"strongest stocks this week"** (ISO W29) → FORTIS · FOSECOIND · NSIL · LYKALABS · COLPAL

---

## Where each answer links

- **Month** asks deep-link to the full sortable **This-month screen**
  (`/dash/markets/seasonal-screen`) — all columns, the history-floor filter, bullish/bearish views.
- **Week** asks deep-link to the **Seasonal tape** (`/dash/markets/seasonal-tape`) — the per-stock
  weekly detail.
- Every symbol row links to that stock's **Seasonal tab** (`/dash/stock?sym=…#seasonal`).

---

## The fence (shown with every answer)

> Historical calendar base-rates over ≥15 years, net-of-cost expectancy ≈ 0 — **descriptive
> context, never a signal, ranking, or trade.** When the 95% CI straddles 50%, the lean is noise.

Companion docs: [pat-question-catalog.md](pat-question-catalog.md) ·
[strategies/README.md](strategies/README.md) · the seasonal engine is `src/automation/seasonal_tape.py`.
