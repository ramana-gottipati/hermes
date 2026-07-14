# Relative Strength (RS) Suite — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** DESCRIPTIVE (deployed lens suite) · **Governing decision(s):** D39 (RS ratio-analysis layer) · D40 (multi-index compare/rebase) · D64 (RRG + RS-depth + capture + constituent drill) · D67 (size-index RS parity) · with D41 (real-sector curation), D68 (rotation-vocabulary unification) and the session-25 weather-rotation build · **Reconciled:** 2026-07-11 (S111).
> **Origin:** 📚 CLASSIC families (RRG — de Kempenaer · Mansfield/Weinstein RS · sector rotation) + 🏠 HOUSE measurement (rs_band · capture · size-index parity). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for the RS suite. Deep design: [rs-rotation-design.md](../rs-rotation-design.md), [rs-band-support-resistance-design.md](../rs-band-support-resistance-design.md), [rs-ratio-analysis-design.md](../rs-ratio-analysis-design.md), [rrg-rotation-NEXT-SESSION.md](../rrg-rotation-NEXT-SESSION.md), [rs-momentum-divergence-roadmap.md](../rs-momentum-divergence-roadmap.md). Numbers live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page never restates a formula's constants — it links.

**One-line definition:** in Patearn, **relative strength (RS)** is how much a name's (stock or sector) price return *beats or lags the broad index's return over a horizon* — operationally the ratio `close(name) ÷ close(Nifty 500)` and how that ratio behaves through time — **not** the Wilder RSI momentum oscillator of a single price (that is `RSI-of-RS`, one derived member below).

---

## 1. What it is

RS is a **suite of analytical lenses**, not one indicator, that all read the same underlying object — a name's strength *relative to* the market (default benchmark **Nifty 500**; Nifty 50 kept as the cap-tilt/breadth lens). Each lens answers a different question about that relationship:

- **Level** — how cheap/rich is this name vs its *own* RS history? (RS-band)
- **Direction & momentum** — which way is RS rotating and how fast? (RRG, RS-Momentum, RSI-of-RS, Mansfield)
- **Phase** — where in the lifecycle (Recovery → Tailwind → Rolling-over → Headwind) does it sit, and did it *just* turn? (RS Rotation "weather")
- **Resilience** — does it fall *less* than the index on down days? (down/up-capture)
- **Structure** — is the whole thing consistent across the market-cap ladder? (size-index parity)

The suite deliberately spans **level ⟂ trend ⟂ phase ⟂ resilience** because they are orthogonal: band-position is the *fuel gauge*, the RRG is the *speedometer*, capture is the *shock absorber*, the weather is the *stage of the journey*. You read them together; none is sold as a standalone trade (see §4).

**Canonical definition (binding):** **RS = beat Nifty %Δ per horizon**; the rotation **"phase" = the SHAPE of the RS sweep across horizons** (1w → 24m). A "Recovery" classification is a **staged ladder** (week → 2w → 1m → 3m → 6m; long horizons grade base-depth, they don't gate) and is **descriptive only**.

---

## 2. Our variation vs. the standard technique

The suite adopts industry-standard primitives (JdK RRG, Mansfield RS, %-relative strength à la IBD RS-rating) but our **variations** are deliberate:

- **RS = %Δ-beat-per-horizon, and phase = the sweep's shape.** We do not collapse RS to one blended "UPTREND" word (the D39 complaint). We render the full `[1w][…][24m]` horizon sweep as a heat strip; the *shape* (`▲▲▲▲` persistent leader · `▼▼▲▲` improving = entry · `▲▲▼▼` deteriorating leader = exit) is the read, not any single cell.
- **RS-band as support/resistance vs Nifty 500.** The novel lens (vs the standard trend-only RRG): a rolling, **recency-weighted percentile** `rs_band_pct` (0–100) of a name's RS ratio inside its *own* historical distribution — 0 = at RS support (cheapest vs its history), 100 = at RS resistance. Everything in log space, dual-window (3y/10y shown side-by-side so their disagreement is itself signal), with a **detrended twin** and a **regime gate** (band verdict fires only for mean-reverting series; suppressed for trending/re-rating names — the IT/Defence killer). This is *level*, which the RRG and weather are structurally silent on.
- **The 2×2 weather-rotation** (project-native naming). We reuse the shipped `_WEATHER` vocabulary (🌤 Tailwind · 🌅 Recovery · ⛅ Rolling-over · 🌧 Headwind · ☁ Neutral) as **one phase label per name** applied to *both* stocks and sectors, with the 200-MA boundary making the quadrants disjoint and phase-*transitions* (fresh crossings) as the actionable event.
- **Size-index RS parity (D67).** Cap-segment size indexes (Smallcap 250 et al.) get the *full* RS apparatus — not the degenerate broad aggregates. `Smallcap 250 ÷ Nifty 500` is the canonical small-cap-leadership line and is treated exactly like a sector.
- **JdK normalisation (~100)** for RS-Ratio (x) and RS-Momentum (y) so every name is comparable on one quadrant chart (kills the IT-1.19 vs Bank-2.0 magnitude problem), with **constituent drill-down** (sector dot → its member-stock RRG) as the recursion.
- **Nifty 500 standardised as the primary yardstick**; Nifty 50 retained as the narrow-vs-broad breadth/cap-tilt divergence read.

---

## 3. How it works (methodology)

One tight paragraph per sub-lens. **All arithmetic, no LLM, ₹0 reads.** Formula constants live in code and [calculations-and-weights.md](../calculations-and-weights.md) — linked, never restated here.

- **RS ratio + multi-timeframe trend (D39).** The base layer. `ratio = close(name) ÷ close(Nifty 500)`, with 20/50/200-day MAs on the ratio, 50d/200d/52w bands, per-horizon slopes (1m/3m/6m/12m, extended to 18m/24m for base-depth), breakout flags and a composite `trend_state`. The multi-TF **heat strip** (`▲▬▼` per horizon, dead-banded) is the headline scan. Engine: [`index_signals.py`](../../src/automation/index_signals.py) (denormalises the Nifty-500 read onto `index_signals.rs_vs_broad_*`); the % slopes are already cross-sector comparable, so normalisation is *labelled and surfaced*, not rebuilt.
- **Multi-index compare / rebase (D40).** Overlay ≤6 indices on one chart, each **rebased client-side** to a common start (base 100 or 0%) with a *fluid anchor* (pan left → that point becomes the new 0) and a Rebased ⇄ Ratio toggle — read who outperformed from a shared origin. Render-only (no schema).
- **RRG — Relative Rotation Graph (D64).** JdK **RS-Ratio** (EMA-smoothed RS ratio, trailing-z normalised to ~100) on x, **RS-Momentum** (same normalisation on the RS-ratio's rate-of-change) on y → four quadrants vs 100: **Leading** (≥,≥) · **Weakening** (≥,<) · **Lagging** (<,<) · **Improving** (<,≥). Comet tails show the journey; dot size/hover encode params. Engine: [`rrg.py`](../../src/automation/rrg.py) (owns `rs_extras`). Constituent drill (`?idx=`) recomputes member-stock RRG on-read; the inline single-name glance is [`mini_rrg.py`](../../src/web/mini_rrg.py); the lifecycle "cycle-clock" is [`cycle_clock.py`](../../src/web/cycle_clock.py).
- **RS-band — support/resistance vs Nifty 500.** Rolling recency-weighted percentile `rs_band_pct` (0–100) in log space, dual-window 3y/10y, Mansfield-detrended twin, KDE point-of-control + value area, an all-time anchored reference for **break detection** (a persisted state machine: INSIDE / TOUCH / BREAK_ARMED / BREAKOUT / BREAKDOWN / FAILED_BREAK), a **regime gate** (Hurst/ADF — verdict fires only when mean-reverting) and a **history floor** (thin/young indexes get no verdict). Engine: [`rsband.py`](../../src/automation/rsband.py); view [`rsband_view.py`](../../src/web/rsband_view.py).
- **RS Rotation "weather" (2×2 phase, session-25 build).** One `rs_phase` label per name from its RS-vs-broad slopes + trend_state, applied to **both** stocks (`stock_signals.rs_phase`) and sectors (`index_signals.rs_phase`) via the *same* classifier (`rs_weather`, ported verbatim from the sector-weather badge — not forked). Disjoint quadrants via the 200-MA boundary; the **phase-transition** (today's phase ≠ prior row's) is the "✨ just turned" event. Engine: [`rs_phase.py`](../../src/automation/rs_phase.py); view [`rotation_view.py`](../../src/web/rotation_view.py). Distinct from the RRG (continuous scatter) — complementary phase *buckets*.
- **Mansfield RS.** `(RS ÷ SMA200(RS) − 1)·100`, zero-centred — the robust turn signal that does *not* saturate in strong trends (unlike RSI); zero-cross = a relative turn. Stored in `rs_extras.mansfield` ([`rrg.py`](../../src/automation/rrg.py)); shown in the RS-depth table.
- **RS-capture — "accumulate what falls less than the Nifty" (D64).** **down_capture** = compounded name return ÷ compounded benchmark return over the days the benchmark *fell* (`<1` = falls less → accumulate; `<0` = rose while the market fell = strongest; `>1` = falls harder → avoid); **up_capture** symmetric on up-days; **down_excess** = the denominator-free "falls less" primary. Regime-gate the "accumulate" framing to weak tapes; the *change* in down-capture is the alpha. Engine: [`capture.py`](../../src/automation/capture.py) (owns `capture_signals`).
- **RSI-of-RS + divergence.** Wilder RSI(14) run on the **RS ratio line itself** (not the price) — is the *relative* performance overbought/oversold and turning? Used for washouts/divergence at extremes, never as a standalone trend (it saturates). Stored `rs_extras.rsi_of_rs` + `stock_signals.rsi_of_rs`; the multi-horizon RSI + **divergence** ecosystem (compute-on-read from the RS line — no full-history series persisted, per the space doctrine) lives in [`momentum_pane.py`](../../src/web/momentum_pane.py). Roadmap: [rs-momentum-divergence-roadmap.md](../rs-momentum-divergence-roadmap.md).
- **Per-stock RS + rs_rank.** [`stock_rs.py`](../../src/automation/stock_rs.py) stores each stock's `rs_vs_broad_*` (vs Nifty 500) and `rs_vs_sector_*` (vs its own sector index) plus a blended **`rs_rank`** (0–100). The blend weights (stock-vs-broad / stock-vs-sector = 0.6 / 0.4) live in [calculations-and-weights.md](../calculations-and-weights.md) — `rs_rank` is also the RS half of the Conviction score.
- **Size-index RS parity (D67).** The engine gate was narrowed from "all size indexes" to only the aggregate `BROAD_MARKET_PROXIES` (Nifty 100/200/500/Total Market, where a ratio vs Nifty 500 is near-circular). The 11 admitted cap segments now carry `broad_benchmark='Nifty 500'`, so RRG / Mansfield / RSI-of-RS / capture / band all light up automatically off `ratio_rows` — **zero edits** to the downstream modules.
- **RS hub (umbrella).** [`rs_section.py`](../../src/web/rs_section.py) (`/dash/rs-hub`) is a *router*, not a re-implementation — it links Momentum (`/dash/rrg`), Level (`/dash/rsband`) and Phase (`/dash/rotation`) into one entry surface.

---

## 4. Status, validation & honesty fence

**BINDING — the RS suite is DESCRIPTIVE.** It is a Tier-3 analytical lens (see the [strategy ledger](../strategy-ledger.md) Tier-3 row: *"RS suite (RRG, RSI-of-RS, Mansfield, capture, RS-band) · relative strength vs index · deployed (descriptive)"*): **built + deployed, but NOT return-tested as standalone alpha.** It reads relative strength vs the index; it does **not** trade as a book.

- **No RS lens is fundable alpha.** It is *context / selection*, consistent with project doctrine: **price strength is a gross selection lens, not net alpha.** Momentum is the only factor that survives the walk-forward, and even that is **beta, not skill** (t≈1.99), and the momentum edge dies net of cost (see the ledger's Tier-1/failure sections). RS informs *which* names are interesting; it never earns a return claim on its own.
- **The recovery ladder is descriptive only.** The week→6m staged confirmation grades conviction (Watch → Confirmed); it is an early-warning read, never a tradable signal.
- **RS-band verdicts are gated, not naive.** The "cheap/rich" verdict fires **only** for mean-reverting series (Hurst/ADF regime gate) and only above a **minimum-history floor**; on trending/re-rating names it is *suppressed* ("band invalid; breakouts = re-rating, not exhaustion"). A band break only *upgrades to a watch* — direction of action comes from the fused signals (level × direction × confirmation), never from the break alone. Point-in-time (no look-ahead) by construction.
- **Capture framing is regime-gated.** "Accumulate what falls less" is surfaced only when the market is weak; in a bull tape it is not a green arrow.
- **Related-but-separate — CCI-RRG.** [`cci_rrg.py`](../../src/automation/cci_rrg.py) reuses the RRG *grammar* on the credibility time-series (not price RS). CCI is **FALSIFIED as a factor** (no validated long/short/risk edge; high-credibility names underperform) → it is descriptive/veto-only and is **not** part of the price-RS suite. Do not conflate.

---

## 5. Where it lives (code · routes · DB · timers)

| Sub-lens | Compute module | Read surface / route | DB table(s) |
|---|---|---|---|
| RS ratio + multi-TF trend strip (D39) | `src/automation/index_signals.py` | `/dash/ratio?idx=&den=` · `/dash/rs` (cross-sector rank) · strips on `/dash/sectors`, `/dash/markets`, Home | `ratio_rows`, `ratio_signals`, `index_signals.rs_vs_broad_*` |
| Multi-index compare / rebase (D40) | `src/web/dashboard.py` (render-only) | `/dash/compare?idx=&idx=&den=&mode=` | `index_rows`, `ratio_rows` |
| RRG map + constituent/stock drill (D64) | `src/automation/rrg.py` | `/dash/rrg` (+ `?idx=` constituents, `?sym=` stock, `?den=`/`?vs=` toggles) · inline `mini_rrg.py` · `/dash/cycle-clock` | `rs_extras` |
| Mansfield RS | `src/automation/rrg.py` | RS-depth table on `/dash/rrg` | `rs_extras.mansfield` |
| RSI-of-RS + divergence | `src/automation/rrg.py` (+ on-read) | `/dash/momentum` (`momentum_pane.py`) · RRG hover/table · stock dossier RS tab | `rs_extras.rsi_of_rs`, `stock_signals.rsi_of_rs` |
| RS-capture (down/up) | `src/automation/capture.py` | down-capture column on `/dash/rrg` · regime-gated "resilient fallers" board | `capture_signals` |
| RS-band support/resistance | `src/automation/rsband.py` | `/dash/rsband` (+ `?idx=`, `?sym=`, `?den=`, `?view=lanes\|rrg`) · thermometer column · Channel embeds | `rsband_signals` (+ denormalised trio on `index_signals`) |
| RS Rotation "weather" (2×2 phase) | `src/automation/rs_phase.py` | `/dash/rotation?phase=` (`rotation_view.py`) · Home strip · stock badge | `stock_signals.rs_phase`, `index_signals.rs_phase` |
| Per-stock RS + rs_rank | `src/automation/stock_rs.py` | `/dash/rs/overlay` (`rs_overlay.py`), stock dossier · Screen+/leaders columns | `stock_signals.rs_vs_broad_*`, `rs_vs_sector_*`, `rs_rank` |
| Size-index RS parity (D67) | `src/automation/index_signals.py` (`BROAD_MARKET_PROXIES` gate) | full RS section on `/dash/index?idx=<size index>` | `ratio_rows` (+ all downstream) |
| RS hub (umbrella router) | `src/web/rs_section.py` | `/dash/rs-hub` | (reads only) |
| CCI-RRG grammar (related, falsified) | `src/automation/cci_rrg.py` | descriptive credibility map | `credibility_rrg` |

**Nav placement (doctrine):** none of these is a 6th top-level tab. RRG/band/rotation are **views inside Markets**, reached with intent and unified under the RS hub + [D80 nested nav](../../src/web/lens_registry.py); isolated modules mounted one-line so they never edit the contended `cockpit.py`/`dashboard.py`.

**Timers:** all pre-computed nightly. The core signal chain (`hermes-bhavcopy`) builds `ratio_rows`/`stock_signals`; the `rrg` → `capture` passes run after it via the `/etc/systemd/system/hermes-bhavcopy.service.d/20-rsdepth.conf` drop-in; `rs_phase` and `rsband` ride the same nightly pass. RSI-of-RS multi-horizon + divergence are **compute-on-read** (nothing persisted — space doctrine).

---

## 6. Data & provenance

- **Primary source only.** All RS lenses derive from **NSE bhav copy** (daily EOD OHLCV, archived) and the **NSE index series** (`index_rows`), split/bonus-safe via the `adjust.adjusted_closes` corporate-action chain. The ratio, slopes, RRG, Mansfield, capture, band and phase are *all* pure arithmetic over these primary series — no vendor, no Screener dependency, doctrine-clean.
- **Value-based RS** (adjusted price ratios), never share-count — eliminates corporate-action adjustment bugs.
- **Constituents** come from `stock_index_membership` (latest snapshot) joined to `adjust.adjusted_closes` for the drill-downs.
- **Space discipline:** derivable series (RSI-of-RS, %Δ) are computed on read, not persisted; the production DB is ~16 GB and every stored byte is a cost. Stored columns are bounded (one row/entity/date) and additive (owned at runtime via `db._ensure_column`, never a `db.py` edit).

---

## 7. Terminology canon

- **Relative strength (RS)** — a name's price %Δ vs the benchmark's %Δ over a horizon; the ratio `close(name)/close(Nifty 500)`. Beating in a *down* market (falling less) still counts as strong.
- **Phase = sweep-shape** — the rotation phase is the *shape* of the RS beat/lag sweep across horizons (1w→24m), not a single-horizon label.
- **RRG quadrants** (JdK, vs 100): **Leading** (strong & strengthening) · **Weakening** (strong, losing momentum) · **Lagging** (weak & weakening) · **Improving** (weak, base turning up = the entry corner).
- **Weather phases** (the phase-bucket analogue): 🌤 Tailwind (≈ Leading) · 🌅 Recovery (≈ Improving) · ⛅ Rolling-over (≈ Weakening) · 🌧 Headwind (≈ Lagging) · ☁ Neutral. Unified vocabulary (D68) so the mini-quad, RS-depth panel and full RRG all speak one language.
- **RS-band 0–100** (`rs_band_pct`) — position-in-band percentile: 0 = at RS support (cheap vs own history), 100 = at RS resistance (rich), 50 = rolling median. Level, not direction.
- **Mansfield RS** — `(RS/SMA200(RS)−1)·100`, zero-centred; zero-cross = relative turn; does not saturate.
- **RSI-of-RS** — Wilder RSI on the RS *ratio line* (not price); overbought/oversold + divergence at extremes only.
- **Capture** — down/up-capture: ratio of compounded returns on benchmark-down / -up days; `<1` down-capture = falls less.
- **rs_rank** — blended 0–100 stock RS score (broad 0.6 / sector 0.4); the RS half of Conviction.
- **⚠ RS-momentum ≠ the momentum FACTOR engine.** "RS-Momentum" here is the *y-axis of the RRG* (the derivative of the relative-strength ratio) — a descriptive rotation read. The tradable **momentum factor** (MOM12/RISKADJ/LOWVOL_MOM, cross-sectional return ranking) is a different, return-tested object; see [momentum-riskadj.md](momentum-riskadj.md) (and [momentum-engine-formalization.md](../momentum-engine-formalization.md)). RS is **not** that engine.

---

## 8. Decision & session history

- **D39** — RS ratio-analysis layer: multi-timeframe trend, ratio charts (`/dash/ratio`), normalisation labelled-not-rebuilt, cross-sector rank (`/dash/rs`). Shipped Phase A + B-on-read (session 16).
- **D40** — Multi-index comparison / rebase chart (`/dash/compare`) + the chart range-switch perf fix. Shipped.
- **D41** — Sector surfaces curated to real economic sectors (factor/thematic indexes excluded from the RS leaderboard/RRG/band).
- **D64** — RRG rotation map + RS-depth (RSI-of-RS / Mansfield) + down-capture + constituent drill-down (`/dash/rrg`, session ~2026-06-22); isolated `rrg.py`/`capture.py`/`rrg_view.py` + systemd drop-in.
- **Session 25** — the four-phase RS **weather** rotation (`/dash/rotation`, `rs_phase.py`) built as the phase-bucket complement to the RRG.
- **D67** — Size-index RS parity: cap-segment size indexes (Smallcap 250 + 10 others) get the full RS apparatus; engine gate narrowed to `BROAD_MARKET_PROXIES` (session 38).
- **D68** — Rotation-vocabulary unification (`mini_rrg.py`): one Improving→Leading→Weakening→Lagging language across every RRG surface.
- **RS-band** (`rsband.py`/`rsband_view.py`, `/dash/rsband`) — the level lens; design gated then built, with the beeswarm/lanes hero, Channel, thermometer column, scrubber + Play, constituent drill and stock Channel.
- **S69+** — RSI-of-RS + divergence + staged-recovery ecosystem (`momentum_pane.py`, `/dash/momentum`); backfill **superseded by compute-on-read** (space doctrine).
- **S75** — glossary keys 95→245 + popovers wired on `/dash/rrg` and `/dash/rotation`.

For exact commit hashes and the blow-by-blow, see `PROJECT_STATE.md` § Session log (Sessions 16, 19, 25, 33, 35, 37, 38, 64+) and § Decision log (D39/D40/D41/D64/D67/D68).

---

## 9. Open items / frozen work

- **Sectors-page RRG map embed** — the one-line `render_sectors_map` embed at the top of `/dash/sectors` was left PENDING (gated on the contended `cockpit.py` being committed + disk==running). The RRG hub, band lanes and rotation surfaces are live; the *in-page* map-on-sectors weave is the residual discoverability item.
- **Reconcile the 3 quadrant lenses** (abs×rel on `/dash/ratio` · RRG · capture) into ONE "Relative strength" panel with a lens toggle — design agreed, build outstanding.
- **RS-depth weave into `/dash/sectors` rows** (RS-Momentum / quadrant / down-capture columns) + the regime-gated "accumulate the resilient fallers" board.
- **Pre-compute per-stock RRG** for ₹0 drills (currently on-read, cap 50 members) + a D/W/M/Q timeframe selector for tails.
- **Size-index parity backfill (D67)** — the 11 cap segments **require a one-time `python -m src.automation.index_signals --backfill` on the VPS** to populate `ratio_rows` history before RRG/capture/band fully light up; nightly fills thereafter. *Deployment-state of this backfill is not verifiable from the repo — confirm on the VPS before assuming full history.*
- **RS-based position sizing — the throughline.** Rank → *weight* an actual portfolio (band-position as a sizing modulator on rs_rank: tilt-on-entry soft, gate-on-exit strict). Longer-horizon; its own design pass; this is where the RS work is meant to land (per the DVPT→ranked-portfolio direction).

---

## 10. Sources of truth

**Design docs (deep, keep rich — do not one-line):**
- [rs-rotation-design.md](../rs-rotation-design.md) — the four-phase weather rotation (stocks + sectors), the seven RS-leverage reads.
- [rs-ratio-analysis-design.md](../rs-ratio-analysis-design.md) — D39 ratio-analysis spec (Part 1), D40 compare/rebase (Part 2), D64 RRG + capture + drill (Part 3).
- [rs-band-support-resistance-design.md](../rs-band-support-resistance-design.md) — the RS support/resistance level lens (regime gate, break state machine, fusion matrix).
- [rrg-rotation-NEXT-SESSION.md](../rrg-rotation-NEXT-SESSION.md) — RRG wrap, placement/IA, deploy run-book.
- [rs-momentum-divergence-roadmap.md](../rs-momentum-divergence-roadmap.md) — RSI-of-RS + divergence + staged-recovery roadmap.

**Canonical numbers & glossary:**
- [calculations-and-weights.md](../calculations-and-weights.md) — the ONLY place RS constants live (rs_rank blend, Conviction). Never restated here.
- [metrics-glossary.md](../metrics-glossary.md) — RS-Ratio / RS-Momentum / Mansfield / RSI-of-RS / rs_band definitions + site popovers.
- [strategy-ledger.md](../strategy-ledger.md) — the Tier-3 "RS suite" row (deployed, descriptive); the momentum factor / cost-net evidence in Tier-1.

**Sibling strategy reference:**
- [momentum-riskadj.md](momentum-riskadj.md) — the return-tested momentum *factor* engine (distinct from RS-Momentum). RS is not that.

**Memory anchors:** [[rs-rotation-design]] · [[rs-band-support-resistance-design]] · [[rotation-phase-methodology]] · [[d67-size-index-rs-parity]] · [[rs-deepen-rrg-capture-held]] · [[build-additive-never-replace]] (isolation doctrine).

**PROJECT_STATE.md sections:** § Telegram/route table (`/dash/ratio`, `/dash/rs`, `/dash/rrg`, `/dash/rsband`, `/dash/rotation`, `/dash/compare`) · § Database schema (`rs_extras`, `capture_signals`, `rsband_signals`, `ratio_rows`/`ratio_signals`) · § Decision log (D39/D40/D41/D64/D67/D68) · § Session log (16/19/25/33/35/37/38/64+).

---

## Maintenance

- **This page is a canonical *reference*, not a design doc.** When a sub-lens changes: update its deep design doc + the code, change the constants in [calculations-and-weights.md](../calculations-and-weights.md), and only then adjust the *pointers/status* here. Never copy a formula's constants into this file.
- **Honesty fence is load-bearing.** If any RS lens is ever return-tested, record the result in the [strategy ledger](../strategy-ledger.md) FIRST; do not upgrade the DESCRIPTIVE badge here until the ledger row moves. A falsified result is BLOCKING and must be cited before re-attempting.
- **Additive-only doctrine.** New RS work = new isolated module + additive nullable column + one-line mount; sacred routes (`/dash/ratio`, `/dash/rrg`, `/dash/rsband`, `/dash/rotation`, `/dash/compare`) are never rerouted.
- **Keep the sub-lens table (§5) in sync** with the route/module reality when anything is added, renamed, or unified under the RS hub.
