# Patearn — Metrics Glossary (canonical definitions)

> **Single source of truth** for every *custom* metric the dashboard shows. Standard finance terms (P/E, EBITDA, market-cap…) are deliberately NOT listed — only Patearn's own signals, which nobody can be expected to know.
> **This doc has two jobs:** (1) answer "what does this number mean / measured against what?" for Ramana today; (2) be the **content source for the planned hover-help / "?" explainers** (Session 1). **Rule: when you add a metric to a screen, define it HERE first.**
> Each entry: **What · How computed · Measured against · How to read · Source.**

---

## Positioning — DVPT (institutional delivery footprint)

- **DVPT — Delivery Value per Trade.** Σ(delivery value ₹) ÷ Σ(number of trades) for the day. The average ₹-size of a *delivered* trade — bigger = larger hands. *Source:* `delivery_value_per_trade`.
- **Power baseline — P1M / P3M / P6M / P12M.** The **average DVPT of only the top-N highest-DVPT days** in the last 1 / 3 / 6 / 12 months (the institutional *peak* days, not all days). *Source:* `power_dvpt_*`.
- **R baseline — R1M…R12M.** The flat average DVPT over the window (the "normal day"). *Source:* `avg_dvpt_*`.
- **p_score (0–5).** How many of the 5 **power** baselines today's DVPT beats. 5 = above *every* institutional peak-day bar. *Source:* `p_score`.
- **r_score (0–5).** Same vs the 5 **flat** baselines. *Source:* `r_score`.
- **Rank — SS / S / A / B / C.** A label off p_score: SS=5 · S=4 · A=3 · B=2 · C=1. *Source:* `trigger_rank`.
- **×Power (intensity).** Today's DVPT ÷ the **average of its own power baselines** (P1M/P3M/P6M/P12M). **"1.6×" = today's per-trade delivery is 1.6× the stock's own institutional peak-day average**, blended across 1–12 months. **Measured against the stock's own history, not the market.** *Computed on read.*
- **Deliv ₹Cr.** Total delivered value that day, in ₹ crore. *Source:* `delivery_value_today`.
- **Surge 1m / 3m / 1y.** Today's turnover ÷ its average turnover over 1m / 3m / 1y. "3.6×" = today's traded value is 3.6× the 1-month norm. *Source:* `turnover_surge_*`.
- **Character — ACCUMULATION / DISTRIBUTION / CONSOLIDATION / NEUTRAL.** Delivery is *side-blind* (every delivered share was both bought and sold), so this fuses 3 independent axes — **WHO** (trade-count breadth + delivery-₹ trend), **WHICH-WAY** (value-weighted up/down skew + price drift), **CONTEXT** (distance from 52w-high + persistence). DISTRIBUTION on a high rank is a *warning*, not a buy. *Source:* `accum_character`. (Doctrine §E / D43.)
- **Key price (1M…12M) + gap.** The **value-weighted average price on the power days** — where the big institutional money actually transacted — per horizon. Gap = today's close vs that key. 🎯 = inside the −1%…+5% "launch band". *Source:* `key_price_p*`, `gap_to_key_p*`.

## Relative Strength

- **RS rank (1–99).** The stock's relative-strength percentile vs the broad universe; higher = stronger. *Source:* `rs_rank`.
- **RS vs broad / sector.** Price ratio of the stock vs **Nifty 500** (broad) and vs its **sector index**, each with a trend-state + slope per 1/3/6/12m. *Source:* `rs_vs_broad_*`, `rs_vs_sector_*`.
- **RS heat strip.** 4 cells (1m/3m/6m/12m) of the RS slope — ▲ outperforming · ▬ flat · ▼ lagging.

## Quality — pt14 (the 14-pattern durability screen, rule-based, no LLM)

- **ns_base (0–100) — *this is the "pt14" number you see*.** Normalized score = `pws ÷ MAX_CWS × 100` (MAX_CWS = 582). NATCO 46, Adani 29, etc. *Source:* `ns_base`.
- **pws (raw).** The raw sum of the 14 pattern scores (~148–266). Internal; **no longer shown** (it was the confusing "266").
- **PAC (x/14).** "Patterns Actively Confirming" — how many of the 14 patterns are firing. *Source:* `pac`.
- **Tier — T1 / T2 / T3 / T4.** Quality band off ns_base + the quality-gate:
  - **T1** = ns_base ≥ 72 **and** quality-gate passes (best)
  - **T2** = ns_base ≥ 55 · **T3** = ns_base ≥ 40 · **T4** = ns_base < 40 (weakest)
  - **DISQUALIFIED** = hard-fail (e.g. red-flag pattern).
  - So **"Tier 4" = a weak score (<40/100)** on the durability screen. *Source:* `tier`.

## Conviction (the cross-pillar composite — read this, you asked)

- **Conviction (0–100).** A composite **I (Claude) introduced** to float the strongest cross-pillar names to the top of the screener. Today it blends **Positioning + Relative Strength**:
  ```
  conviction = 0.55 × (p_score ÷ 5 × 100)   ← 55%: institutional positioning strength
             + 0.45 × rs_rank               ← 45%: relative-strength rank (1–99)
  ```
- **★ (triple-confirm flag)** = `p_score ≥ 4` **and** `rs_rank ≥ 80` **and** quality not failing — the "all aligned" headline.
- **⚠ Honest caveats (important):**
  - It currently **does NOT include Quality (pt14)** — I held it out until the pt14 scale was confirmed (now confirmed → folding it in is open work).
  - The weights (0.55/0.45) are a **reasonable default, not backtested.** Conviction is a **sorting heuristic**, not a validated model or a price target. Tuning/validating it (and adding Quality) is open.
  - **CPR (Structure) is deliberately NOT folded into this number (D53, 2026-06-19).** The build panel + the user agreed: keep the composite as positioning+RS, and surface CPR as its own parallel **★ Structure tier** + a one-click **"CPR-confirmed"** screener gate instead. Rationale: the composite is already unvalidated, CPR has no live history yet, and the doctrine is "master each pillar alone, then club." Folding CPR (and/or Quality) in — as an amplifier or a re-weight — is a future decision once CPR has been observed.

## Price / context

- **CMP · Δ%D · Deliv%** — current price · day change % · delivery %.
- **52w%** — % below the 52-week high (`pct_from_52w_high`); near 0 = near highs.
- **Δhot%** — close vs the hot-day average price (`price_vs_hot_avg_pct`); negative = discount to where the action happened.

## CPR — Structure (the 4th pillar, D53)

The Central Pivot Range: a 3-line range projected from a period's **prior** High/Low/Close, read at three degrees — Daily / Weekly / Monthly. Materialized nightly in `cpr_signals`; full design in `docs/cpr-strategy-design.md`.

- **CPR / Pivot · BC · TC.** From the prior period's H/L/C: **Pivot** = (H+L+C)/3 · **BC** = (H+L)/2 · **TC** = 2·Pivot−BC. The band is [min(BC,TC) … max(BC,TC)], centred on the pivot. Built from **split/bonus-adjusted** prices. *Source:* `cpr_signals.p/bc/tc`.
- **Width% (the coil metric).** (TC−BC) ÷ Pivot × 100. **Smaller = narrower = more coiled** (a bigger move pending). Shown per timeframe (D%/W%/M% in the screener). *Source:* `width_pct`.
- **Compression percentile (Comp%).** How narrow today's CPR is **vs this stock's own history** — the fraction of the trailing N CPR widths (≈252 D / 52 W / 24 M) that are *wider* than now. **High = unusually coiled FOR THIS STOCK** (the truer "unusual" than a flat %). *Source:* `compression_pctile`.
- **Pattern — U / ∩.** A **reversal**: three consecutive CPRs where each leg is a clean directional step (both band lines move the same way). **BULL_U** = down-step then up-step (a bottom); **BEAR_INVU** (∩) = up-step then down-step (a top). *Source:* `pattern`.
- **Rank — R1…R4.** Narrowness of the two recent bands, with **C0 (today's coil)** the priority bar: **R1** both narrow (sharpest) · **R2** C0 narrow · **R3** C1 narrow · **R4** neither. Derived on read vs the per-TF knob (D 1.0 / W 2.5 / M 5.0%). 
- **★ Structure tier (the cross-TF conviction).** A reversal on a faster timeframe is **amplified** when slower timeframes are also coiled/aligned — **the larger TF carries more weight** (D 1 · W 2 · M 3). Score = base rank (R1=4…R4=1) + Σ over other TFs `w_TF · (narrow? + reversal-aligned? + regime-aligned?)` + confluence. Transparent tiers: **★★★ Prime** (strong base + a higher TF coiled+aligned + regime) · **★★ Strong** (strong base + some higher-TF support) · **★ Setup** (reversal present, little higher-TF support). Always shown with its D·W·M breakdown. **Derived on read — weights are tunable, nothing re-materialized.**
- **Regime.** Sign of close vs the pivot: **above** (+) / **below** (−). The higher-TF trend context that the amplifier rewards. *Source:* `regime`.
- **Confirmed.** Price has engaged the turning band (bull-U: close > TC; bear-∩: close < BC). A `confirmed` flag, not a gate — unconfirmed "forming" setups still show. *Source:* `confirmed`.
- **Fresh (days-since).** Bars since the pattern first appeared on that timeframe — **0 = formed this period** (fresh surfaces first; a stale signal isn't a signal). *Source:* `days_since_pattern`.
- **Separation% / Depth%.** Secondary quality (displayed, not gates): **separation** = full non-overlap on the turn leg; **depth** = how far the valley/peak over-ran the lead-in (size of the move being reversed). *Source:* `separation_pct`, `depth_pct`.

**Where it shows:** a **CPR column-group** in the screener (D/W/M width% + glyph + rank + ★ tier + Comp%, group-toggle-able, plus a **"CPR-confirmed"** gate); a **CPR card** in `/dash/strategies`; the dedicated **`/dash/cpr`** (Reversals · Compression · per-TF EOD Reports); and a **CPR panel** on the stock page.

---

### Open (Session 1 will action)
- Wire these definitions into **hover-help / "?" explainers** on every metric label and column header (this doc = the content source).
- A **"how is this computed"** drill-down for the composites (conviction, character, key price).
- Decide the **conviction formula** (add Quality? CPR? re-weight? backtest?) — a design-panel decision, not a silent default.
