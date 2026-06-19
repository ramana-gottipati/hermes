# CPR Strategy (Patearn Strategy 4 — STRUCTURE pillar) — design + build

> **Status:** ✅ **BUILT + verified end-to-end (CPR build session, 2026-06-19) — D53.** All seven OPEN modelling points (§ 13) RESOLVED via multiple-choice-with-recommendations; the build matched every panel + user call. Materialized engine + screener column-group + Strategies card + dedicated `/dash/cpr` (Reversals · Compression · per-TF EOD Reports) + per-stock CPR panel — all live behind a no-regression route sweep (19/19 routes 200). Deploy: scp the same safe way as session 20.
> **Canonical decision number at build:** **D53** (D52 is reserved for the held MTF engine — see memory `mtf-foundation-held-uncommitted`).
>
> **Resolved OPEN decisions (all = the recommended defaults; § 13):** OPEN-1 both-lines clean step · OPEN-2 rank priority C0 · OPEN-3 show both + `confirmed` flag · OPEN-4 width ÷ pivot · OPEN-5 per-TF D 1.0 / W 2.5 / M 5.0% · OPEN-6 TF weights D 1 · W 2 · M 3 · OPEN-7 both absolute + percentile (percentile-primary for 3B compression).
> **Conviction integration (user's call + panel consensus):** CPR is kept OUT of the cross-pillar Conviction NUMBER (it stays positioning+RS, unchanged). CPR surfaces as its own parallel **★ Structure tier** column + a one-click **"CPR-confirmed"** screener gate. Re-weighting / amplifier folding is deferred until CPR has live history ("master each pillar alone, then club"). See `metrics-glossary.md`.
> **Implementation:** `src/automation/cpr_signals.py` (materializer) · `cpr_signals` table in `src/core/db.py` · `/dash/cpr` + screener CPR group + Strategies card + stock panel in `src/web/dashboard.py`. CPR **self-resamples** its own lightweight adjusted H/L/C bars (replicates `_period_key`) — carries **no dependency** on the held MTF foundation (CPR-A5).
> **Pillar:** the 4th Patearn strategy, beside Positioning (DVPT — D28/D31/D43/D44), Relative Strength (RS — D32/D33), Quality (pt14). The first three answer *who's buying*, *what's leading*, *what's good*. CPR answers what none of them do: **where is price in its multi-degree structure, has the structure just turned, and is it coiled for a move?**
> **Doctrine:** obeys § C (materialize nightly, raw archive untouched, value/price-based, split-safe), the binding doc rule, and the *preserve-strategy-intent* directive — kept rich; do not one-line.
> **Build order:** master the **Reversal (3A)** + **Compression (3B)** scanners standalone first (they share one primitive and one nightly pass). Trend-stack/regime (3C) and confluence (3D) layer on. Hybridization with DVPT/RS is last (§ 12). "Individually master each, then club them."
>
> **Session-20 additions over v1:** Model 3B (unusually-narrow single-CPR scanner), § 4 cross-timeframe amplification (larger TF carries more weight), confluence (3D) + regime (3C) promoted to first-class components feeding the amplifier, relative "unusual" narrowness (§ 5.2).

---

## 1. Intent (one paragraph)

CPR (Central Pivot Range) is a 3-line range — Pivot, BC, TC — projected from a period's prior H/L/C onto the current period. Plotted *across* consecutive periods it becomes a **sequence of bands** whose **shape** and **width** carry signal, read identically at three degrees — **Daily, Weekly, Monthly** — only the period changes. The CPR pillar is a small family of models over that one primitive: **(A) Reversal** — three consecutive CPRs forming a **U** (bullish bottom) or **inverted-U / ∩** (bearish top), strongest when the recent bands are **narrow** (a coiled, sharp turn); **(B) Compression** — *unusually narrow* single CPRs (coiled springs, big move pending) scanned across D/W/M; **(C) Trend-stack/regime** — price's position relative to the three CPRs; **(D) Confluence** — D/W/M pivots clustering into high-probability S/R zones. The multiplier that ties them together: **a signal on a faster timeframe is amplified when slower timeframes are also coiled/aligned, with the larger timeframe carrying more weight** (§ 4). Narrowness is a **user-tunable knob** so result counts can be widened/tightened. Output: universe-wide EOD screens (ranked) + a per-stock multi-TF read.

---

## 2. CPR primitives (shared by every component)

From the **prior completed period's** High/Low/Close:

```
Pivot (P) = (H + L + C) / 3
BC        = (H + L) / 2
TC        = 2P − BC                 (= P + (P − BC))
band      = [ min(BC,TC) … max(BC,TC) ]   ; centre = P
width%    = (TC − BC) / P × 100             ; the narrowness metric
```

The three degrees, identical logic:

| Degree | Built from | Refreshes |
|---|---|---|
| **Daily CPR** | yesterday's H/L/C | every trading day |
| **Weekly CPR** | last week's H/L/C | once a week (static Mon–Fri) |
| **Monthly CPR** | last month's H/L/C | once a month (static) |

**Split-safety (Doctrine D36/D10):** prior-period H/L/C and the current close must be in one consistent price regime — build the band from **back-adjusted** OHLC (`adjust.py`). Drop bars with |daily return| > 0.30 (D36 anomaly guard).

---

## 3. The components

### 3A. Reversal — U / inverted-U (the 3-CPR pattern) — PRIMARY

**The three CPRs** (most recent first), consecutive on the chosen timeframe:

| Label | Which | Daily example |
|---|---|---|
| **C0** | most recent — the signal bar | today's CPR (from yesterday) |
| **C1** | previous — the valley / peak | yesterday's CPR |
| **C2** | previous-to-previous — confirms the lead-in leg | day-before's CPR |

**Atomic rule — each leg is a clean *directional step*** (both band lines move the same way):

- **Up-step** (X→Y higher): `Y.TC > X.TC AND Y.BC > X.BC`
- **Down-step** (X→Y lower): `Y.TC < X.TC AND Y.BC < X.BC`

This one rule builds the pattern **and** excludes exactly the cases to reject — *engulfing/outside* (TC up while BC down — the "middle swallows the oldest" example) and *inside* (TC down while BC up). Those aren't clean steps, so they never qualify. Partial overlap is fine **if both lines move together**; full separation is a bonus (§ 3A.3), not a gate.

**Bullish U (reversal up)** — valley at C1:
```
   C2 ▭                     ▭ C0      ← oldest & today HIGH
                ▭ C1                  ← middle LOW (valley)
   t-2          t-1         t(today)
   require:  C2→C1 = down-step   AND   C1→C0 = up-step
```

**Bearish ∩ (reversal down)** — peak at C1:
```
                ▭ C1                  ← middle HIGH (peak)
   C2 ▭                     ▭ C0      ← oldest & today LOW
   require:  C2→C1 = up-step     AND   C1→C0 = down-step
```

C2 only confirms the lead-in leg was a genuine directional move, so the turn at C1 is a true reversal, not noise.

**3A.2 Strength — narrowness of the two recent bands (C0, C1):** a band is `narrow` if `width% ≤ max_width_pct` (the knob, § 5).

| Rank | C0 (today) | C1 (valley/peak) | Reading |
|---|---|---|---|
| **R1** | narrow | narrow | both recent bands coiled — sharpest |
| **R2** | narrow | wide | the immediate/turn bar coiled (priority) |
| **R3** | wide | narrow | the valley/peak coiled, turn bar loosened |
| **R4** | wide | wide | pattern present but slack |

Priority bar = **C0** (the coiled spring about to release), so R2 > R3. Tiebreak: smaller combined width first.

**3A.3 Secondary quality (displayed; optional rank inputs, not gates):** **separation** (full non-overlap on the turn leg, `C0.BC ≥ C1.TC`), **depth** (how far C1 over-ran C2 = size of the move being reversed), **freshness** (`days_since_pattern`, 0 = formed this bar — fresh surfaces first; the state-vs-event rule).

### 3B. Compression — *unusually narrow* single CPRs (coiled springs)

Independent of any pattern. **"Which stocks have an unusually narrow CPR right now?"** — a narrow CPR forecasts an outsized move on that horizon. Scanned across **all three degrees**, **larger TF carrying more weight** (a narrow *monthly* CPR ≈ a big *month* pending — far more significant than a narrow day).

- Compute the latest CPR `width%` on D, W, M per stock.
- **Narrow** by the absolute knob (§ 5.1) **and/or** *unusual* by the relative percentile (§ 5.2 — recommended: narrow **relative to the stock's own history**, not a flat market %).
- **Rank** by a **TF-weighted compression score** (§ 4 weights): `score = wM·compM + wW·compW + wD·compD`, where `comp_TF ∈ [0,1]` = how deeply below the cutoff / how high the own-history percentile. Sort desc.
- Surface the **D·W·M narrowness strip** (three cells) so you see at a glance which degrees are coiled. Filterable ("monthly-narrow only", etc.).

This is the standalone "regular unusually-narrow CPR" section requested — usable on its own *and* as the amplifier for 3A (§ 4).

### 3C. Trend-stack & regime — price vs D/W/M CPR (later; also a 4-input)

Is price stacked above/below Daily·Weekly·Monthly CPR, and are the CPRs sloping together? `stack_score`/`slope_score` (−3…+3) → FULL BULL / TRANSITION / NEUTRAL / BEAR, **timing-aware** (every stack carries `stack_age` + `signal_event`: SETUP→FRESH→RE-ENTRY→IN-TREND→BREAKDOWN). Its key job for the reversal: **regime context** — `regime_TF = sign(close − P_TF)` (or vs the whole band). A bullish U **in a bullish higher-TF regime** (price above the monthly CPR) is a pullback-resume = higher win-rate; a U fighting the monthly trend is counter-trend = flag/penalty.

### 3D. Confluence — D/W/M pivot/band clustering = S/R zones (a 4-input)

When the Daily, Weekly and/or Monthly CPR lines **cluster** at one price, that zone is a high-probability support/resistance magnet. Operational: **confluence present** when ≥2 of the D/W/M bands overlap at the current price (or the three pivots sit within a small % of each other). A reversal that forms **at a confluence** (e.g., a daily U turning right on the monthly pivot) is far stronger than one in open space.

---

## 4. Cross-timeframe synthesis & amplification (the combiner)

**Principle (Ramana, session 20):** a signal on a faster timeframe is **amplified** when slower timeframes are also coiled/aligned — *and the larger timeframe carries more weight.* A daily R1 reversal alone is strong; with a narrow **weekly** it's stronger; with a narrow **monthly (~5%)** stronger still.

**Timeframe weights** `wD < wW < wM` — default **D 1 · W 2 · M 3** (tunable).

**Per-TF structure score** `s_TF` (0–3) = `narrow?` + `reversal-aligned?` + `regime-aligned?` (each 0/1; `narrow?` may be graded by depth/percentile).

**CPR Conviction Score** (the sort key for the amplified reversal screen):
```
conviction = base_rank(anchor reversal)            # R1=4 … R4=1, on its own TF
           + Σ over the OTHER timeframes  w_TF · s_TF     # higher TF dominates
           + confluence_bonus                       # 3D
```
The **amplification ladder** (bullish, anchor = daily reversal):

| Situation | Conviction |
|---|---|
| Daily R1 U, nothing higher | base |
| + weekly narrow | +wW |
| + monthly narrow (~5%) | +wM (largest jump) |
| + price above monthly CPR (regime) | +regime |
| + turn sits on a weekly/monthly pivot (confluence) | +confluence |

Anchors can be **daily or weekly** (monthly reversal is itself the strongest base, with no higher TF to add). "Same holds for the weekly" — a weekly reversal amplified by a narrow monthly.

**Doctrine balance (D43-F — surface alignment, not an opaque mega-score):** the score is the *sort key*, but every row **always shows its breakdown** — the D·W·M narrowness/pattern/regime strip and the named bonuses — and **all weights are visible and tunable**. We present it as **transparent conviction tiers** backed by the additive score:

- **★★★ Prime** — anchor R1/R2 **and** ≥1 higher TF coiled (monthly weighted most) **and** regime-aligned.
- **★★ Strong** — anchor R1/R2 with some higher-TF support (narrow or aligned).
- **★ Setup** — reversal present, little/no higher-TF support.

---

## 5. The narrowness knob & "unusual"

### 5.1 Absolute threshold — `max_width_pct` (query-time)
Not baked into storage — geometry/widths are materialized (objective); "narrow" + rank are applied **on read** with the knob (mirrors D43-G "raw stored, score derived").
- **Defaults (per-TF, tunable):** Daily **1.0%** · Weekly **2.5%** · Monthly **5.0%**. *Per-TF because a flat 1% would make W/M (wider by nature) essentially never qualify — killing the multi-TF point.*
- **Direction:** **lower = stricter = fewer/sharper**, higher = looser/more. *(The brief said "raise to 2.5% for fewer" — flagging it's the reverse: raising admits more.)*

### 5.2 Relative "unusual" — own-history compression percentile (recommended for 3B)
"Unusually narrow" is best measured **against the stock's own typical width**, not a flat market %. `compression_pctile_TF` = fraction of the trailing N CPR widths (≈ 252 D / 52 W / 24 M) **wider** than the current one; high = unusually coiled *for this stock*. A name that's normally 2% wide is dramatically coiled at 0.8%; one normally 0.3% wide is not. Offer **both**: absolute knob (simple default) + percentile (the truer "unusual"), filterable.

---

## 6. Freshness & confirmation
- **Freshness** — `days_since_pattern` (3A) / how long a CPR has been coiled (3B). Fresh formations surface first; stale ones demoted with a visible age. (State-vs-event.)
- **Confirmation (optional view)** — the pattern is a *setup*; flag `confirmed=1` when price has actually engaged (bullish U: today's close `> C0.TC`). Default: show both, flag confirmed.

---

## 7. Surfaces

- **Reversal screen** — `/dash/cpr` + Telegram `/cpr`. Params: `tf`, `max_width_pct`, `dir` (U/∩/both), `min_rank`. Rows: pattern glyph, rank R1–R4, **conviction tier ★** + breakdown, C0/C1 width%, the **D·W·M strip**, separation, depth, days-since, confirmed, CMP. Sort: fresh → conviction → combined-width. Badge: **STRUCTURE**.
- **Compression screen** — `/dash/cpr/narrow` (or a section on the same page) + Telegram `/cpr narrow`. Ranked by TF-weighted compression; D·W·M strip; absolute/percentile filters; "monthly-narrow only" toggle.
- **Stock-page** — a CPR panel + `/cpr TICKER`: the three CPRs' P/BC/TC, the close's position in each, the leg steps, narrowness, regime, confluence, the verdict — a D·W·M strip like the RS heat strip.
- **Conviction (D45) later** — folds in as a confirming filter.

---

## 8. Schema — `cpr_signals` (nightly-materialized; geometry+widths stored, rank/score on read)

Per (symbol, period_end_date, timeframe ∈ `D`/`W`/`M`):

| Column | Meaning |
|---|---|
| symbol, date, timeframe | key |
| p, bc, tc, width_pct | the C0 CPR |
| c1_width_pct, c2_width_pct | prior two bands' widths (rank-on-read) |
| compression_pctile | current width's percentile vs trailing N (3B/§5.2) |
| pattern (`BULL_U`/`BEAR_INVU`/`NONE`) | qualified geometry |
| leg_in_clean, leg_turn_clean | the two step bools |
| separation_pct, depth_pct | secondary quality (3A.3) |
| regime | sign(close − P) — for amplification (3C) |
| days_since_pattern, confirmed | freshness + engagement (§ 6) |
| close, adj_used | CMP + split-adjust audit |

Cross-TF **amplification, confluence and conviction are computed on read** (they join the latest D/W/M rows per symbol) — kept out of storage so weights stay tunable without re-materializing. All re-derivable from `bhavcopy_rows` (+ `bars_weekly`/`bars_monthly` when present); raw archive untouched (Doctrine § C).

---

## 9. Generalization to Weekly / Monthly
One **timeframe-parameterized** engine (`tf ∈ {D,W,M}`), exactly like the MTF foundation (D43-D). Weekly/Monthly CPR needs only prior-period **H/L/C** — a trivial resample, far lighter than the full `weekly_signals` machinery — so **CPR is not blocked** on the heavy D43 build. Reuses `bars_weekly`/`bars_monthly` H/L/C if present, else aggregates its own.

## 10. Guards (necessary, not over-engineering)
Adjusted OHLC (split/bonus) · |return|>0.30 anomaly drop (D36) · equity-only allowlist (`nse_equity_list`, D42) + turnover floor (no penny-stock narrow-% noise) · whipsaw debounce (a fresh pattern that flickers across adjacent bars must hold before flagging fresh).

## 11. Practical improvements (curated — no over-engineering)
1. **Per-TF width thresholds** (§ 5.1) — without this the multi-TF promise breaks.
2. **Relative "unusual" percentile** (§ 5.2) — a far better "unusually narrow" than a flat %.
3. **Freshness** (§ 6) — separates today's turn/coil from stale ones.
4. **Confirmation flag** (§ 6) — geometry vs price engaging.
5. **Liquidity floor** (§ 10).
> Deliberately NOT adding yet: ML, multi-factor opaque scoring, intraday band-interaction — out of scope until A+B are battle-tested.

## 12. Future — hybridization (record only; do NOT build now)
**CPR × DVPT × RS.** Master each pillar alone, then club. When a CPR reversal/compression co-occurs with DVPT accumulation / RS leadership, **relax** the (normally strict) DVPT bar and lift the blended score — the structure adds independent confidence. A cross-strategy scoring layer + **exception rules** ("be slightly liberal on DVPT when a strong CPR reversal is present") → a portfolio of all-pillar setups. Keep the § 4 score additive so this blend is a clean extension.

## 13. OPEN decisions — ✅ ALL RESOLVED (CPR build session, 2026-06-19; each = the recommended default, confirmed by the user after the build panel)
- **OPEN-1 — Leg qualification:** ✅ **both-lines clean step** (`Y.TC,Y.BC both move same way`) — one rule builds the U/∩ and excludes engulfing/inside. Implemented in `cpr_signals._clean_step`.
- **OPEN-2 — Rank priority bar:** ✅ **C0** (today's coil) — R1 both-narrow · R2 C0-narrow · R3 C1-narrow · R4 neither. `dashboard._cpr_rank`.
- **OPEN-3 — Confirmation:** ✅ **show both + `confirmed` flag** (bull-U close>TC / bear-∩ close<BC) — keeps the anticipatory "forming" view; a `confirmed` filter is available.
- **OPEN-4 — Width normaliser:** ✅ **÷ pivot** — the band is intrinsic to the prior period; ÷ close would drift with how far price has run.
- **OPEN-5 — Per-TF thresholds:** ✅ **D 1.0 / W 2.5 / M 5.0%** — `dashboard._CPR_MAXW` (query-time knob; tune after observing the live run).
- **OPEN-6 — TF weights:** ✅ **D 1 / W 2 / M 3** — `dashboard._CPR_WEIGHT` (larger TF dominates the amplified conviction).
- **OPEN-7 — "Unusual" definition:** ✅ **both** — own-history `compression_pctile` (stored; the truer "unusual", primary sort for 3B) **+** the absolute knob (reversal-rank narrowness). Both shown beside each other (data-first).

## 14. Local decision log (canonical D53 assigned at build → PROJECT_STATE)
- **CPR-A1** — CPR is the 4th pillar (STRUCTURE); a family of models over one primitive. *Why:* answers "where / has it turned / is it coiled," which Positioning/RS/Quality don't.
- **CPR-A2** — Clean directional step (both lines same way) is the atomic qualifier. *Why:* one rule that builds the U/∩ and excludes the engulfing/overlap cases.
- **CPR-A3** — Reversal strength = narrowness of C0 & C1, 4-tier rank, C0 priority. *Why:* coiled recent bands = sharp turns; matches the brief.
- **CPR-B1** — Standalone compression scanner (unusually-narrow single CPRs), multi-TF, larger TF weighted more. *Why:* a narrow CPR forecasts an outsized move; the monthly coil dominates.
- **CPR-X1** — Cross-TF amplification: faster-TF signal × slower-TF coil/alignment, `wD<wW<wM`. *Why:* a daily turn inside a coiled monthly is a far higher-conviction event.
- **CPR-X2** — Confluence (3D) + regime (3C) are first-class amplifier inputs. *Why:* a reversal at a multi-TF S/R zone, with the higher-TF trend, is the textbook setup.
- **CPR-A4** — `max_width_pct` is a query-time knob; geometry/widths materialized, rank/score derived on read. *Why:* flexibility without re-materializing (D43-G).
- **CPR-A5** — Timeframe-parameterized engine; per-TF thresholds; CPR not blocked on D43 heavy build. *Why:* DRY + the multi-TF promise needs scaled cutoffs + CPR needs only prior H/L/C.
- **CPR-A6** — Split-adjusted OHLC + anomaly + liquidity guards. *Why:* Doctrine D36/D10/D42.
- **CPR-A7** — Freshness (`days_since_pattern`/coil age); fresh surfaces first. *Why:* state-vs-event — a stale signal isn't a signal.

---

## 15. SESSION 2 — CPR build (kickstart plan)

> **A dedicated, agent-driven, interactive build session.** Goal: turn this design into a **queryable, triggerable, end-of-day** strategy that joins the others (screener columns · Strategies card · conviction). The design above is largely locked — **confirm the OPEN decisions (§11/§13) via multiple-choice-with-recommendations**, then build. **No-regression.**

### Build framework
- **Triggers per timeframe.** Because we compute **Daily, Weekly AND Monthly** CPRs, each produces its **own triggers** and **own report** — daily triggers (fast), weekly triggers, monthly triggers. A signal "fires" when a qualified **U/∩ reversal (§3A)** or **compression (§3B)** appears on that timeframe (with freshness, §6).
- **Queryable.** CPR columns in the screener (D/W/M width · pattern · rank · conviction · regime — §5/§8), scope-filterable like every pillar.
- **EOD reports.** A daily / weekly / monthly "what fired" report (triggers + amplified-conviction names — §4), surfaced in Strategies, later pushable.
- **Materialized** `cpr_signals` (§8) nightly, reusing `bars_weekly`/`bars_monthly`; not blocked on the heavy D43 build (§9).
- **Integration.** A real CPR card in `/dash/strategies` (replaces "coming soon"); a CPR column-group in the screener; **fold into the conviction composite** (an explicit panel decision — see `metrics-glossary.md` conviction caveat).

### Build panel (spawn)
**Quant / technical analyst** (trigger definitions, per-TF narrowness thresholds, amplification, report contents) · **Data engineer** (`cpr_signals` schema + timeframe-parameterized resample/compute + nightly wiring + perf) · **Strategy/product** (surfacing + reports + conviction integration).

### Session flow (binding)
Spawn panel → **AskUserQuestion multiple-choice with recommendations** on the OPEN decisions (§11/§13 + trigger/report shape) → confirm → build materialization + D/W/M triggers + per-TF reports + surfaces — **no-regression**, updating this doc + `metrics-glossary.md` + `PROJECT_STATE.md`.

---

## 16. BUILD LOG — what shipped (CPR build session, 2026-06-19, D53)

A 3-agent panel (quant · data engineer · strategy/product) returned converging recommendations; the OPEN decisions went to the user as multiple-choice and all four returned the recommended defaults. Then built end-to-end, no-regression.

**Data layer — `cpr_signals` table** (`src/core/db.py`, additive; `stock_signals` untouched). PK `(symbol, period_end_date, timeframe∈D/W/M)`. STORED (objective): `p, bc, tc, width_pct, c1_width_pct, c2_width_pct, compression_pctile, pattern, leg_in_clean, leg_turn_clean, separation_pct, depth_pct, regime, days_since_pattern, confirmed, close, adj_used, is_partial, n_bars_used`. DERIVED ON READ (tunable, never stored): the R1–R4 narrowness rank, the cross-TF amplification, the ★ conviction tier, confluence. Indexes: `idx_cpr_tf_date` (universe screen per TF), `idx_cpr_sym_tf` (stock page + cross-TF join), `idx_cpr_tf_date_pattern` (EOD reports).

**Engine — `src/automation/cpr_signals.py`** (mirrors the held `mtf_signals.py` shape: resample → compute → store; `--backfill` / `--recent` / `--symbol`, `--timeframe D|W|M|all`). Self-resamples lightweight **split-adjusted** H/L/C period bars from `bhavcopy_rows` (per-day `adjustment_factors` applied to H/L/C, then aggregated; **NOT** dependent on the held `bars_weekly/bars_monthly` — `_period_key` is replicated, CPR-A5). Guards: |adjusted daily return|>0.30 anomaly drop (D36), equity-only allowlist (D42, when populated), thin-prior-period skip (W<2 / M<3 days → NULL geometry). CPR primitive from the PRIOR period's adj H/L/C; clean-step legs → `BULL_U`/`BEAR_INVU`; `compression_pctile` = fraction of trailing N (252 D / 52 W / 24 M) widths wider than now; `regime` = sign(adj_close − P); `days_since_pattern` (0 = fresh); `confirmed`; daily bars never `is_partial` (EOD-complete), W/M current period flagged. Verified: math self-test (BULL_U/BEAR_INVU/clean-step/engulfing-exclusion/width÷pivot) + an end-to-end synthetic backfill (800 D / 160 W / 40 M rows).

**Surfaces — `src/web/dashboard.py`** (all additive; 19/19 routes 200 post-build):
- **Screener CPR column-group** (`g-cpr`, between RS and Quality): `D% · W% · M% · D·W·M glyph strip · Rnk · ★ Str tier · Comp%` — raw widths beside the verdict (D-UI-1); group-toggle chip + the **"🔷 CPR-confirmed"** gate (one table-class, composes with the other toggles + text filter). The cross-pillar Conviction NUMBER is **untouched**.
- **Strategies CPR card** — replaces the "coming soon" stub; previews today's top fresh structure setups (★ tier + glyph + anchor TF) → links to `/dash/cpr`.
- **`/dash/cpr`** — three tabs: **Reversals** (cross-TF amplified ★ screen, filterable by TF / direction / min-tier, `.dt` sort/filter/CSV), **Compression** (unusually-narrow CPRs ranked by own-history percentile, per-TF), **EOD Reports** (Daily/Weekly/Monthly "what fired" — fresh reversals + coiled names; W/M carry a "live for the current period (fixed)" badge so they never look stale mid-period).
- **Per-stock CPR panel** (`/dash/stock`) — the D·W·M strip + the three CPRs' P/BC/TC, close-vs-band, width%, rank, regime, freshness, and a plain-English verdict line.

**On-read amplification (the §4 combiner), `dashboard._cpr_conviction`:** per-TF structure score `s_TF = narrow? + reversal-aligned? + regime-aligned?` (0–3); anchor = the largest-TF reversal present (or pinned for a TF-filtered screen); `score = base_rank_pts(anchor R1=4…R4=1) + Σ_{other TF} w_TF·s_TF + confluence(0/1)`; transparent **★★★ Prime / ★★ Strong / ★ Setup** tier from the design's boolean rules (strong base + higher-TF support/strength + regime), always shown with its per-TF breakdown.

**Nightly (wired at deploy):** `cpr_signals.py --recent --timeframe all` appended after `stock_rs` in the signals chain (no upstream dependency; WAL means it never blocks dashboard reads).

**Deferred (recorded, not built — § 11/§ 12):** the CPR×DVPT×RS exception-rule hybrid; folding CPR/Quality into the Conviction number (await live history); the full 3C trend-stack screen (only the `regime` bit is used now); 3D confluence-zone chart visualization (only the binary flag is used); compression coil-age "freshness".
