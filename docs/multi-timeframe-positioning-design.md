# Multi-timeframe Positioning — design (D43) + accumulation/distribution character (D42)

> **Status:** design agreed (session 18, 2026-06-18). Not yet built.
> **Owner decision:** build the multi-timeframe **foundation (D43) first**, then the three-axis **character (D42)** rides on top of it at every timeframe. Building D42 daily-only first would mean writing the character compute three times.
> **Companion to:** Doctrine § C/§ E, decisions D28/D31 (daily DVPT trigger system), D41 (strategy surface + the on-read weekly/monthly *days-fired* toggle this supersedes).

---

## 1. Problem

The Positioning pillar today is **daily-only**. D41 added a Daily/Weekly/Monthly toggle on `/dash/stocks`, but Weekly/Monthly there just **count daily fires** over the last 5 / ~22 trading days ("3/5 days fired"). That is an *event count*, not a measurement of strength at a higher timeframe.

**Counting daily fires ≠ measuring weekly strength.** A stock can accumulate strongly on a weekly basis with **zero** daily fires (gradual buying that never clears the daily peak-day bar), and a stock can fire 3 noisy daily spikes in a week that nets to flat. The two reads answer different questions:

- **Days-fired** → "how many individual days popped?" (intensity / event count)
- **Weekly/monthly strength** → "what is the dominant character of the *resampled* weekly/monthly bar?" (trend strength)

Ramana wants **both**, and wants the higher-timeframe read done *properly* — on real weekly and monthly bars.

---

## 2. Core principle

Real weekly/monthly strength means **resampling the daily data into true weekly and monthly bars** and running the strength logic *on those bars* — not aggregating daily verdicts.

The payoff is **multi-timeframe alignment**, not a bigger number: daily, weekly and monthly are correlated, so we do **not** sum them into a mega-score. We surface **agreement** (all three accumulating = high conviction) and **divergence** (daily hot but monthly cold = a one-off blip; daily cold but monthly still accumulating = a pullback inside a longer campaign, often the entry).

---

## 3. The design panel (synthesis)

**🎯 Quant / financial analyst.** Resample to true OHLC + delivery bars. The rule people get wrong: **timeframe DVPT must be recomputed from summed components — Σ(delivery value) ÷ Σ(trades) for the period — never the average of daily DVPTs** (ratio-of-sums ≠ mean-of-ratios; averaging dilutes the big-trade days). Direction at each timeframe = **period close vs prior period close** (weekly close-over-close, monthly close-over-close), not intra-period. Baselines scale with the timeframe. Value is in alignment/divergence, not a summed score.

**🗄️ Data engineer.** Don't compute on read — rolling top-N over 52 weeks per stock per query is too heavy. Materialize nightly (Doctrine § C / D11). Resample is a pure re-aggregation of `bhavcopy_rows` we already hold — **no NSE re-fetch**. Cheap: weekly ≈ 1/5, monthly ≈ 1/22 of daily rows. Three gotchas: (1) the **current bar is partial** (week/month-to-date) — compute but flag `is_partial`; (2) use **adjusted closes** for direction so a split doesn't fake a down-week (delivery *value* is value-based and split-invariant, so summing is safe); (3) calendar grouping keyed by the period's last trading day.

**🎨 UI/UX.** The D/W/M toggle already exists on `/dash/stocks` — swap the engine behind Weekly/Monthly from days-fired to the real weekly/monthly score + character, and **keep days-fired as a secondary "intensity" column**. The real win is a compact **D·W·M strip** (three cells, like the RS heat strip) on each row — one glance shows whether strength is confirmed across timeframes or only flickering on the daily. Stock page: a timeframe switch on the DVPT/character panels + an **alignment badge**.

**🏗️ Architect.** This realizes D41 Phase 2 (the deferred `weekly_signals` table) — build it as the foundation. Write the resample + signal computation **once, timeframe-parameterized** (`timeframe ∈ {D,W,M}`) and reuse it for all three (DRY: same DVPT, R/P baselines, scores, *and* the D42 character). Separate `weekly_signals` / `monthly_signals` tables — do not add a timeframe column to the 2.35M-row daily `stock_signals`. Bonus: once a resampled-bars layer exists, weekly/monthly **RS** and pt14-over-time become nearly free later.

---

## 4. Methodology

### 4.1 Resampling rules
- **Weekly bar** — group EQ `bhavcopy_rows` by (symbol, ISO year-week), keyed on the **last trading day of the week** (`week_end_date`):
  - open = first day's open · high = max · low = min · close = last day's close · prev = prior week's close
  - volume / deliv_qty / delivery_value / no_of_trades / turnover = **sums** over the week
  - `n_days` = trading days in the bar · `is_partial` = 1 if it's the current, not-yet-closed week
- **Monthly bar** — same, grouped by (symbol, YYYY-MM), keyed on the month's last trading day.
- **Adjusted close** for direction: adjust the daily series via `adjust.adjusted_closes`, then take last-of-period as the adjusted period close. Direction = adj close vs prior period's adj close. Exclude any day with |daily return| > 0.30 (D36 anomaly guard).

### 4.2 DVPT per timeframe
`period_dvpt = Σ(delivery value in period) ÷ Σ(no_of_trades in period)`. **Component sums — never average daily DVPT.**

### 4.3 Baselines, scores, rank per timeframe (mirror D28/D31, windows scaled)
Same R-tier (flat rolling mean) + P-tier (mean of top-N) two-tier scheme, `r_score`/`p_score` (0–5), `trigger_rank` SS/S/A/B/C, near-break pointer.

| Timeframe | Baseline windows | P-tier top-N (selective, ~D31 philosophy) |
|---|---|---|
| **Daily** (existing) | 30/60/90/180/360 cal days | 4/7/12/20/30 |
| **Weekly** | 4/8/13/26/52 weeks | 1/1/2/4/6 |
| **Monthly** | 3/6/12/18/24 months | 1/1/2/3/4 |

(Top-N values are **defaults — tunable**; raw baselines stored, score derived, so re-tuning needs no re-aggregation of bars.)

### 4.4 Character per timeframe (the D42 three-axis model, on the bars)
The corrected D42 model (side-blind delivery ⇒ WHO / WHICH-WAY / CONTEXT) is computed on the resampled bars, with windows scaled per timeframe:
- **WHO** — delivery-value trend (recent vs longer block), trade-count trend (broadening = retail / concentrated = strong hands), delivery %.
- **WHICH WAY** — value-weighted up/down delivery ratio over the recent block (period direction) + period price drift.
- **CONTEXT** — 52-week-high distance, persistence (consecutive accumulation periods).
- Same derived label via **one shared helper**: ACCUMULATION / DISTRIBUTION / CONSOLIDATION / NEUTRAL.

### 4.5 Multi-timeframe alignment (the payoff, computed on read)
Join the latest D / W / M signal per symbol:
- **Aligned-strength count (0–3)** = number of timeframes where `trigger_rank ≥ A` (or `character = ACCUMULATION`). Use for sorting/ranking.
- **Confirmed** = all three agree (all accumulating / all rank ≥ A).
- **Divergence tells** — daily hot + monthly cold = blip/fade-risk; daily cold + monthly accumulating = pullback-in-uptrend (entry).
- Surfaced as a 3-cell **D·W·M strip** on the screen + an alignment badge on the stock page. **Not summed into one score.**

---

## 5. Schema (mirrors `stock_signals`; nightly-materialized)

- **`bars_weekly`** (symbol, week_end_date, iso_year, iso_week, open, high, low, close, prev_close, adj_close, volume, deliv_qty, delivery_value, no_of_trades, turnover, n_days, is_partial) — PK (symbol, week_end_date), index (week_end_date).
- **`bars_monthly`** (symbol, month_end_date, ym, … same fields …, n_days, is_partial) — PK (symbol, month_end_date), index (month_end_date).
- **`weekly_signals`** — per (symbol, week_end_date): `dvpt`, R/P baselines named by window (`avg_dvpt_w4..w52`, `power_dvpt_w4..w52`) + companion `avg_close_*`, `r_score`, `p_score`, `trigger_rank`, near-break (`next_p_above`,`gap_to_next_p_pct`), `is_ath_dvpt`, `hot_days_avg_price`, `price_vs_hot_avg_pct`, the D42 character columns, `is_partial`. PK (symbol, week_end_date).
- **`monthly_signals`** — same shape, windows `*_m3..m24`. PK (symbol, month_end_date).

All re-derivable from `bhavcopy_rows`; raw archive untouched (Doctrine § C).

---

## 6. Decisions (numbered, with WHY)

- **D43-A — Resample to true calendar bars** (week-ending / month-end), not rolling daily-windows. *Why:* matches how analysts read weekly/monthly charts; denoises daily noise.
- **D43-B — DVPT from Σ-components per timeframe**, never the mean of daily DVPTs. *Why:* ratio-of-sums ≠ mean-of-ratios; averaging dilutes the institutional days.
- **D43-C — Materialize nightly** (bars + signals tables); don't compute on read. *Why:* Doctrine C / D11; rolling top-N over 52w is too heavy on read; enables cross-sectional screening.
- **D43-D — One timeframe-parameterized engine** for D/W/M (DRY); D42 character rides on it. *Why:* avoid writing the compute three times; guarantees consistency.
- **D43-E — Keep daily "days-fired"** as a complementary intensity column. *Why:* it answers a different question (event count vs bar strength); Ramana wants both.
- **D43-F — Surface alignment, not a summed MTF score.** *Why:* the three timeframes are correlated; the signal is confirmation/divergence.
- **D43-G — Baselines & top-N scale per timeframe** (defaults tunable; raw stored, score derived). *Why:* preserves D31 selectivity across timeframes without re-aggregation on re-tune.
- **D43-H — Adjusted closes for direction; delivery value (value-based) for magnitude.** *Why:* split-safety (D36/D10).
- **D43-I — Flag the partial current bar** (`is_partial`). *Why:* week/month-to-date must not be read as a closed signal.
- **D43-J — Separate `weekly_signals`/`monthly_signals` tables**, not a timeframe column on daily `stock_signals`. *Why:* don't bloat/lock the 2.35M-row hot daily table; W/M are small.

---

## 7. Phasing

- **D43 (foundation, build first):** `bars_weekly`/`bars_monthly` + `weekly_signals`/`monthly_signals` (DVPT, R/P baselines, scores, rank, near-break, ATH) via a timeframe-parameterized engine + nightly wiring + backfill; swap the `/dash/stocks` W/M toggle to the materialized signals (keep days-fired as a secondary column); add the D·W·M alignment strip + stock-page timeframe switch; Telegram parity.
- **D42 (character, on top):** the three-axis accumulation/distribution character, computed through the **same** engine so it lands in `stock_signals` **and** `weekly_signals` **and** `monthly_signals`; character pills per timeframe + D·W·M character alignment; the Home "Stealth accumulation" board prefers **weekly-confirmed** accumulation.

---

## 8. Future (record in PROJECT_STATE open items; do NOT build now)
- Weekly/monthly **Relative Strength** and **pt14-over-time** become cheap once the resampled-bars layer exists.
- NSE **bulk & block deals** feed — the only source that names buyer/seller + side (the one ground-truth for direction); not ingested today.
