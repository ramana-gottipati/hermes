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

## Capital allocation — C (what management did with incremental capital)

- **ca_score (0–100).** Has management compounded *incremental* capital well, or just grown size? Blends return on incremental capital (ROIIC), ROCE level and trend, **dilution drag** (profits growing faster than per-share earnings = quiet share issuance), the share of growth funded by debt, and growth efficiency — each mapped smoothly around documented economic anchors, deliberately **no cliff thresholds**. Banks/NBFCs are scored on an ROE/ROA model instead (leverage IS a lender's business, so ROCE/ROIIC are meaningless there). Recomputed nightly, point-in-time. Inputs currently come from the frozen Screener-era fundamentals archive — migrating to BSE/NSE XBRL under the primary-source policy. *Source:* `ca_score` in `capital_allocation_scores`.
- **C tier — EXCELLENT / GOOD / AVERAGE / WEAK / POOR.** The ca_score banded by **cross-sectional quintile** within the same model (industrial vs financial) — relative standing among peers scored the same way, never a fixed cutoff. *Source:* `ca_tier`.
- **C-blend (0–100).** mean(risk-adjusted-momentum percentile, C percentile) — a DESCRIPTIVE tilt of price strength toward well-allocating managements; names without a C score take the neutral 50th percentile. In the recorded walk-forward test (strategy ledger, Experiment 2026-07-03) this blend kept the momentum portfolio's return while cutting its worst drawdown by about a third. Shown as context on the momentum scanner — **never a buy list, never a hard veto** (both harder shapes tested WORSE).

## Conviction (the cross-pillar composite)

- **Conviction (0–100).** A composite that floats the strongest cross-pillar names to the top of the screener. Today it blends two inputs into one positioning-weighted 0–100 sort key: **institutional positioning strength** (the power score) and **relative-strength rank**. (The exact blend weights are internal — see the calculations reference.)
- **★ (triple-confirm flag)** = a **strong power score** **and** a **high relative-strength rank** **and** quality not failing — the "all aligned" headline.
- **⚠ Honest caveats (important):**
  - It currently **does NOT include Quality (pt14)** — Quality was held out until the pt14 scale was confirmed (now confirmed → folding it in is open work).
  - The blend weights are a **reasonable default, not backtested.** Conviction is a **sorting heuristic**, not a validated model or a price target. Tuning/validating it (and adding Quality) is open.
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
- **Rank — R1…R4.** Narrowness of the two recent bands, with **C0 (today's coil)** the priority bar: **R1** both narrow (sharpest) · **R2** C0 narrow · **R3** C1 narrow · **R4** neither. Derived on read vs a per-timeframe width knob (exact values internal). 
- **★ Structure tier (the cross-TF conviction).** A reversal on a faster timeframe is **amplified** when slower timeframes are also coiled/aligned — **the larger TF carries more weight**. The score sums the base rank with weighted contributions from each other timeframe's coil / reversal / regime alignment plus confluence (exact weights internal). Transparent tiers: **★★★ Prime** (strong base + a higher TF coiled+aligned + regime) · **★★ Strong** (strong base + some higher-TF support) · **★ Setup** (reversal present, little higher-TF support). Always shown with its D·W·M breakdown. **Derived on read — weights are tunable, nothing re-materialized.**
- **Regime.** Sign of close vs the pivot: **above** (+) / **below** (−). The higher-TF trend context that the amplifier rewards. *Source:* `regime`.
- **Confirmed.** Price has engaged the turning band (bull-U: close > TC; bear-∩: close < BC). A `confirmed` flag, not a gate — unconfirmed "forming" setups still show. *Source:* `confirmed`.
- **Fresh (days-since).** Bars since the pattern first appeared on that timeframe — **0 = formed this period** (fresh surfaces first; a stale signal isn't a signal). *Source:* `days_since_pattern`.
- **Separation% / Depth%.** Secondary quality (displayed, not gates): **separation** = full non-overlap on the turn leg; **depth** = how far the valley/peak over-ran the lead-in (size of the move being reversed). *Source:* `separation_pct`, `depth_pct`.

**Where it shows:** a **CPR column-group** in the screener (D/W/M width% + glyph + rank + ★ tier + Comp%, group-toggle-able, plus a **"CPR-confirmed"** gate); a **CPR card** in `/dash/strategies`; the dedicated **`/dash/cpr`** (Reversals · Compression · per-TF EOD Reports); and a **CPR panel** on the stock page.

## Tracking — the action loop (D54, UI Phase 1)

- **Watchlist vs Portfolio.** Two stages of one tracked idea (`stocks_in_play.status`). **Watchlist** (`watch`) = a lightweight idea, no entry needed. **Portfolio** (`open`) = a committed position-under-a-strategy, with an entry price + a thesis. Promote watch → portfolio when you commit; **Close** moves it to `closed`.
- **Frozen snapshot.** The signal values **captured at add time** (conviction · p/r · rank · ×power · key-gap · RS · pt14 · character), stored once. *Why:* the daily `stock_signals` row is overwritten nightly, so this is the only honest record of *what you saw when you added it*. *Source:* `stocks_in_play.snapshot_json`.
- **Conv then→now.** The frozen Conviction at add vs its live value today — green if it strengthened, red if it faded. Shows a thesis ageing.
- **Mark-to-market (MTM) / P/L%.** (live close − entry) ÷ entry. Entry = the latest close on the add date (auto-captured). Live close via an indexed point-lookup.
- **Hit-rate by strategy.** Of the *closed* positions in a strategy, the % that exited above entry. Read alongside avg return. *(Populates as you close trades.)*
- **Excess vs Nifty 500.** A closed position's return minus the Nifty 500's return over the same hold window — the benchmark gap (am I beating the index?).
- **Avg hold.** Mean calendar days from add to close, over closed positions.

## RS depth — RRG (relative-strength ratio + momentum)

> Second-order RS reads on a stock/sector's RS line vs a benchmark (Nifty 500 broad, or the sector index), all normalised around 100 so every name is directly comparable. Descriptive; stored in `rs_extras`.

- **RS-Ratio (~100).** Where the RS line sits *relative to its own recent history*, smoothed and re-centred so 100 is normal. **Above 100 = outperforming the benchmark by more than usual; below 100 = lagging.** The x-axis of the RRG map. *Source:* `rs_ratio`.
- **RS-Momentum — "RS MOM" (~100).** The *rate of change* of RS-Ratio — momentum of relative strength, same 100-centred scale. **Above 100 = relative strength is accelerating; below 100 = decelerating.** The y-axis of the RRG map. *Source:* `rs_momentum`.
- **RS Quadrant — Leading / Weakening / Lagging / Improving.** The RRG cell from RS-Ratio × RS-Momentum: **Leading** (strong & still accelerating) · **Weakening** (strong but decelerating) · **Lagging** (weak & still decelerating) · **Improving** (weak but turning up). The classic clockwise rotation reads Improving → Leading → Weakening → Lagging. *Source:* `quadrant`.
- **RSI-of-RS (0–100).** A 14-period RSI run on the RS line itself (not price) — is the *relative performance* overbought or oversold? **>70 = relative outperformance stretched; <30 = relative underperformance stretched.** *Source:* `rsi_of_rs`.
- **Mansfield RS (zero-centred %).** The RS line vs its own long (~200-day) average, as a % deviation. **Above 0 = RS above its long-term trend (structurally leading); below 0 = lagging.** Unlike RSI it does not saturate in a strong trend, so a fresh cross of 0 is the robust turn. *Source:* `mansfield`.
- **RRG turn flags.** Descriptive base-and-turn markers: momentum crossing 100 up/down, an emerging base (momentum turning up while still lagging), a leader cracking, Mansfield crossing 0, an RSI-of-RS oversold turn, and RS divergences where price and RSI-of-RS disagree. Each a 1/0 flag. *Source:* `rs_extras`.

## RS Band — support & resistance on relative strength

> Where a stock/sector's RS ratio sits inside its OWN ~3-year envelope (cheap vs rich vs its own history), and whether it's breaking out of it. The cheap/rich read is only honest on a mean-reverting series (see Regime). Stored in `rsband_signals`.

- **RS band % (0–100).** Today's RS level as a recency-weighted percentile of its own trailing 3-year range. **0 = at historical RS support (cheap vs its own history); 100 = at RS resistance (rich).** Read together with the regime — "cheap" on a de-rating trend is a trap. *Source:* `rs_band_pct`.
- **Band label.** Plain-word band off the %: **At RS support** (≤15) · **Lower band** (<35) · **Mid-band** (<65) · **Upper band** (<85) · **At RS resistance** (≥85). *Source:* `rs_band_label`.
- **Support / median / resistance rails.** The recency-weighted 5th / 50th / 95th-percentile RS levels — the floor, fair-value line, and ceiling on the chart. *Source:* `rs_band_low`, `rs_band_mid`, `rs_band_high`.
- **POC — point of control.** The single most-visited RS level over the history — the fair-value magnet RS keeps returning to (a Market-Profile read). *Source:* `rs_poc`.
- **Value area (VAL–VAH).** The narrowest RS band that contained ~70% of all observations — where RS spends most of its time. Inside = ordinary; outside = unusual. *Source:* `rs_val`, `rs_vah`.
- **Break state — INSIDE / TOUCH_SUP / TOUCH_RES / BREAKOUT_UP / BREAKDOWN_DN.** Whether RS is inside its envelope, merely touching a rail, or has *confirmed* a structural break (cleared by a buffer, held ~a week, momentum agreeing). **BREAKOUT_UP = a re-rating; BREAKDOWN_DN = a de-rating.** A single wick reads only as TOUCH. *Source:* `rs_band_state`.
- **Regime — MEAN_REVERTING / TRENDING.** The honesty gate. **MEAN_REVERTING** = RS oscillates in a range → the cheap/rich read is valid. **TRENDING** = RS is on a multi-year re-rating run → a break means the trend continues, not exhaustion. From how well a straight trend fits the RS history plus its drift. *Source:* `rs_regime`.
- **Detrended band % (0–100).** The band percentile on the *trend-removed* (Mansfield) RS series — "rich vs its own history but NOT vs its trend." Separates a genuinely stretched name from one simply high because it is steadily re-rating. *Source:* `rs_band_pct_detr`.
- **Band width % / maturity.** Width = resistance-to-support spread as a % of the median (how wide the envelope is). Maturity = **full** (≥3y, scored) or **provisional** (2–3y); under 2y no verdict. *Source:* `rs_band_width_pct`, `band_maturity`.

## RS Rotation — the weather phase

> A single "weather" label shared by stocks and sectors, from the RS-vs-broad slopes at 1m/3m/6m/12m plus trend state (and, for sectors, breadth). First-match-wins; descriptive. Stored in `rs_phase`.

- **Phase — 🌤 Tailwind / 🌅 Recovery / ⛅ Rolling-over / 🌧 Headwind / ☁ Neutral.** **Tailwind** = strong and still strengthening. **Recovery** = a deep base turning up (long-horizon RS still negative but 1m turning). **Rolling-over** = a leader cracking (12m still positive but 1m rolling down). **Headwind** = weak and still weakening. **Neutral** = no clean signature. *Source:* `rs_phase`.
- **Rotation pills.** Short badges showing *why* a phase fired / what confirms it: **RS▲>price** (RS at a new 52w high while price is still off its high), **⚡accel / ⚡down** (RS term-structure stacked up 1m>3m>6m>12m / stacked down), **✅deliv** (delivery-backed turn), **RSI hot / RSI cold** (RSI-of-RS overbought / oversold), **abs✔** (absolute price trend also up). Descriptive tags. *Source:* `rs_phase`.

## Capture — how a sector behaves on up vs down days

> How much of the benchmark's moves a sector takes on, split by the benchmark's up days and down days (~3m/6m/12m). Stored in `capture_signals`. Objective: hold what falls LESS than the market.

- **Down-capture (ratio, <1 good).** On the days the benchmark fell, the fraction of that fall the sector took. **<1 = fell LESS than the market (defensive); >1 = fell harder.** *Source:* `down_capture_63` (also `_126`, `_252`).
- **Up-capture (ratio).** On benchmark up-days, the fraction of the rise the sector captured. **>1 = rallied more than the market; <1 = lagged the rally.** *Source:* `up_capture_63`.
- **Down-excess (% per down day).** The denominator-free "falls less": the average by which the sector beat the benchmark *on down days*. **Positive = falls less than the market.** More robust when moves are small. *Source:* `down_excess_63`.
- **Capture spread.** Up-capture minus down-capture. **High = "all-weather"** (captures upside while shielding downside); low/negative = worst of both. *Source:* `capture_spread_63`.

## MEP — signed accumulation / distribution (price-tape)

> The signed sibling of DVPT: where DVPT is side-blind, MEP separates buying from selling by reading the price tape (close-vs-VWAP, close-in-range, drift, up/down-volume), each standardised against the stock's OWN history. Positive = accumulation, negative = distribution. Descriptor-only (D62). Stored in `mep_signals`.

- **Pressure.** Where the close landed vs the day's own VWAP. **Positive = buyers paid up into the close; negative = sellers pressed it down.** *Source:* `pressure`.
- **CLV — close-location value (−1…+1).** Where in the day's range the stock closed. **+1 = on the high (demand); −1 = on the low (supply); 0 = mid-range.** *Source:* `clv`.
- **Drift (22-day).** The split-adjusted price return over the **last ~22 trading days (already realised — a look-BACK, not a forecast).** So "+70%" means the stock has *already* risen ~70% over the past month; it is the near-term trend sitting under the intraday reads. *Source:* `drift_22d`.
- **Up/down-volume skew (22-day, −1…+1).** Over ~a month, volume on up days minus down days as a share of total. **Positive = effort on up days (accumulation); negative = effort on down days (distribution).** *Source:* `updown_vol_22d`.
- **MEP score (signed).** The blended, within-stock-standardised composite of the four signed terms. **Positive = net accumulation vs the stock's own norm; negative = net distribution.** The raw daily score flips often — read the smoothed phase for the regime. *Source:* `mep_score`.
- **MEP daily state — STRONG_ACCUM / ACCUM / NEUTRAL / DISTRIB / STRONG_DISTRIB.** The daily score banded — the granular day-to-day view. *Source:* `mep_state`.
- **MEP phase (headline) — STRONG_ACCUM / ACCUM / NEUTRAL / DISTRIB / STRONG_DISTRIB.** The daily score smoothed over ~3 weeks with hysteresis so a regime *holds* and transitions slowly instead of whipsawing. **This smoothed phase is the headline; the daily state sits underneath.** *Source:* `mep_state_smooth`.
- **MEP phase score.** The MEP score smoothed over ~3 trading weeks (the number the Accum↔Distrib bar position encodes) — slower and steadier than today's raw score. *Source:* `mep_score_smooth`.
- **Compression (MEP) — ATR ratio.** Short-term (14-day) volatility ÷ long-term (60-day), both as a % of price. **Below 1 = coiled** (recent range tighter than the stock's own norm — a spring); **above 1 = expanding** (range opening up). Context only — shown beside the verdict, never summed into the score. *Source:* `compression`.

## F&O Open Interest — positioning (derivatives)

> Read directly off NSE stock-futures & options open interest — the "identity" channel the price tape can't see. Descriptor-only (D62). Stored in `fno_oi_signals`.

- **Positioning quadrant — LONG_BUILDUP / SHORT_BUILDUP / LONG_UNWIND / SHORT_COVER / FLAT.** Day's price change crossed with day's futures-OI change: **LONG_BUILDUP** (price up + OI up = fresh longs) · **SHORT_BUILDUP** (price down + OI up = fresh shorts) · **LONG_UNWIND** (price down + OI down) · **SHORT_COVER** (price up + OI down) · **FLAT**. *Source:* `quadrant`.
- **Futures OI change %.** Day-over-day change in total stock-futures open interest. Blanked when a corporate action / lot-size change makes the comparison meaningless (never a fabricated jump). *Source:* `fut_oi_chg_pct`.
- **PCR — put/call OI ratio.** Total put OI ÷ total call OI. **>1 = more puts open than calls** (hedging / contrarian floor); <1 = call-heavy. A sentiment read, not a verdict. *Source:* `pcr`.
- **Basis %.** Near-month future vs spot, as a %. **Positive (premium) = futures richer than cash (bullish carry); negative (discount) = bearish carry.** *Source:* `basis_pct`.
- **Max-pain.** The expiry price at which option *writers* pay out the least — often cited as a magnet into expiry. *Source:* `max_pain`.
- **Put wall / call wall.** The strike with the most put OI (**put wall = the support buyers defend**) and the most call OI (**call wall = the resistance sellers cap**). *Source:* `sup_strike`, `res_strike`.

## Oscillators — momentum (RSI / MACD)

> The standard TA momentum family from the close history (RSI-14 Wilder, MACD-12/26/9). Stored in `stock_oscillators`.

- **RSI-14 (0–100).** Wilder's 14-day Relative Strength Index. **>70 = overbought; <30 = oversold;** ~50 = neutral. *Source:* `rsi_14`.
- **MACD.** The 12-day minus 26-day EMA of price — momentum as the gap between a fast and slow trend line. Above 0 = up-momentum. *Source:* `macd`.
- **MACD signal.** The 9-day EMA of the MACD line — the smoothed reference it's compared against. *Source:* `macd_signal`.
- **MACD histogram.** MACD minus its signal line. **Positive = up-momentum building; negative = fading.** A sign flip is the classic crossover. *Source:* `macd_hist`.

## CCI — Concall Intelligence (management credibility)

> Management credibility from earnings-call transcripts, on MEASURABLE items only (D61) — no LLM opinion and no price ever enter the score (a hard firewall). Snapshot in `concall_scores`; point-in-time history in `credibility_series`.

- **Guidance accuracy (0–100).** The resolved-promise hit-rate: of management's forward promises now come due, the share they MET (partials half). **Higher = a better track record of doing what they said.** *Source:* `guidance_accuracy_score`.
- **Quantification rate (0–100).** The share of forward statements that are *falsifiable numbers* rather than vague talk. **Higher = more transparent, checkable guidance.** *Source:* `quantification_rate`.
- **Credibility composite (0–100) + tier (A+/A/B/C/D).** The blended measurable score (track record + quantification, penalised for recent disclosure deterioration; capped without a settled track record or when a forensic veto is active). Bands: **A+ ≥80 · A ≥70 · B ≥55 · C ≥40 · D <40.** *Source:* `composite_score`, `tier`.
- **Credibility level / momentum (point-in-time).** The composite recomputed *as of each past concall using only what was knowable then*, plus its change vs the prior period. **Rising = trust being earned; falling = eroding.** *Source:* `level`, `momentum`.
- **Credibility tape — EARNING_TRUST / DETERIORATION.** A flagged series event: **EARNING_TRUST** when promises are met / the level jumps; **DETERIORATION** when disclosure flags appear or the level drops. *Source:* `tape`.

## Capital allocation — ROIIC quality (Dataset C)

> Has management compounded INCREMENTAL capital well, or just grown bigger? From point-in-time fundamentals; scored on smooth curves around economic anchors, ranked within model (lenders separate from industrials). Stored in `capital_allocation_scores`.

- **ROIIC (%).** Return on *incremental* capital — extra operating profit per extra rupee of capital employed over the window. **Higher = each new rupee deployed is productive (a compounder);** low/negative = growth that doesn't pay. Read vs a ~12% cost-of-capital anchor. *Source:* `roiic`.
- **Dilution drag (pp/yr).** Profit CAGR minus per-share (EPS) CAGR. **Positive = shares were issued to fund growth** (owners saw less than headline growth); ~0 = clean, non-dilutive. *Source:* `dilution_drag`.
- **Debt-funding share (%).** The share of incremental capital that came from borrowings. **High (>~50%) = growth leaned on debt (more fragile);** low = self-funded. *Source:* `debt_funding_share`.
- **Growth efficiency (ratio).** Profit CAGR ÷ capital-employed CAGR. **>1 = earnings grew faster than the capital base (efficient);** <1 = the balance sheet outgrew profits. *Source:* `growth_efficiency`.
- **CA score / tier — EXCELLENT / GOOD / AVERAGE / WEAK / POOR.** The weighted composite (plus ROCE level & trend), mapped to a cross-sectional percentile tier *within its model*. *Source:* `ca_score`, `ca_tier`.

## Ignition — DVPT crossing intensity

> Among today's institutional-delivery all-stars (the SS/S DVPT crossers), how HARD each one crossed. Ranks browsably; nothing discarded but un-actionable illiquid names. Stored in `ignition_ranking`.

- **Intensity (×) + band.** Today's delivery-per-trade vs the average of the stock's own peak-day baselines. **"5×" = 5× the stock's own institutional peak-day norm.** Bands: **MILD** (<1.5×) · **MODERATE** (≥1.5) · **ELEVATED** (≥3) · **HIGH** (≥5) · **EXTREME** (≥10). Against the stock's own history, not the market. *Source:* `intensity`, `intensity_band`.
- **Ignition tier — ACT / WATCH / AVOID.** **ACT** = huge intensity + a full all-stars (SS) cross + clean accumulation character. **AVOID** = distribution character (kept, flagged). **WATCH** = everything else that ignited (kept, browsable). Descriptive. *Source:* `tier`.
- **Ignition status — NEW / FRESH / CONTINUING / COOLING.** **NEW** = first-ever full ignition. **FRESH** = ignited today, not ranked yesterday. **CONTINUING** = still ranked, intensity holding. **COOLING** = intensity dropped meaningfully off the prior day. *Source:* `status`.
- **Breadth (0–5).** How many of the 5 peak-day baselines today's delivery-per-trade beat. *Source:* `breadth`.

---

### Status
- ✅ **DONE (S72):** these definitions are wired as `?` **hover-help** across Screen+ / RRG / RS-band / rotation headers + the stock-dossier tabs, AND rendered as a browsable page at **`/dash/glossary`** (`src/web/glossary_view.py`) — both single-sourced from THIS doc so they can't drift. Keys 95→245.
- Open: a **"how is this computed"** drill-down for the composites (conviction, character, key price) — the calculation *schema* without the proprietary weights.
- Decide the **conviction formula** (add Quality? CPR? re-weight? backtest?) — a design-panel decision, not a silent default.
