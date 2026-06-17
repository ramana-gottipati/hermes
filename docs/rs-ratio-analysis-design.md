# Hermes — Relative-Strength Ratio-Analysis Design (D39 spec)

> **Status:** DESIGN — to build. Synthesized 2026-06-17 from a 5-perspective panel
> (financial/quant analyst · equity-practitioner analyst · data analyst · UI/UX · architect).
> **Drives:** the next dashboard build after D38. Phase A is shippable from existing data
> (no schema change, no backfill); Phase B adds two precomputed columns + one backfill.

---

## 1. The problem (Ramana's brief)

The Markets/Sectors tables mix two reference frames in one row:
- **Absolute** return columns (`index_signals.ret_1d/1m/3m_pct` = "did the index go up?")
- **Relative** trend chip (`rs_vs_broad_trend_state` = "did it beat Nifty 500?")

…with no visual separation, and the relative read collapsed into **one blended word** that hides the timeframe. Five asks:
1. Multi-timeframe trend — is it an uptrend on 1m **and** 3m **and** 6m **and** 12m, or just one?
2. Disambiguate absolute vs relative (the "+20.6% 3M" for Microcap = its **own** return, not RS).
3. Ratio **charts** — see index/Nifty over time; cross up = outperforming, cross down = weakening.
4. **Smoothing** + rate-of-change so it isn't day-to-day noise.
5. **Normalization** so RS momentum is comparable across sectors with different ratio magnitudes.

## 2. Key finding — normalization is already (mostly) solved

`ratio_signals.slope_1m/3m/6m/12m_pct` (and the denormalized `index_signals.rs_vs_broad_slope_*`)
are **percentage** changes of the ratio, i.e. `(ratio_now − ratio_then)/ratio_then × 100`. Because
they're %, **they are already cross-sector comparable** — the IT-0.5 vs Bank-2.0 paradox is gone by
construction. The fix is to make this the **explicit, labeled basis** and surface it; NOT to rebuild it.

The genuinely missing normalization pieces are finer:
- **Cross-sector ranking** (percentile/z of RS momentum across all sectors on a date) — not stored.
- **Chart-overlay baseline** (rebase each ratio to 100 at window start) — a render-time transform.
- **Cross-horizon** comparability (annualize so a 1m and 12m slope are per-unit-time) — render-time.

---

## 3. Methodology decisions

**D-A — Work in % / log-returns of the ratio, never absolute deltas.**
Display = the existing `slope_*_pct`. For Phase-B scoring rigor, use the log-return `r_t = ln(R_t/R_{t-1})`
(scale-invariant, additive, symmetric). At daily magnitudes log ≈ %, so no interpretability loss.

**D-B — Smoothing: EMA-20 working line + SMA-50/200 regime.**
On the ratio chart the **50-day MA is the "read-this" smoother** (amber line); the **200-day** is the
slow regime/reference (above = structurally leading). EMA-20 is the responsive signal line for
cross logic. Keep SMA for 50/200 (standard, already computed, `ratio_ma_50/200`).

**D-C — Rate-of-change: OLS log-slope (Phase B), % slope now (Phase A).**
Phase A uses the existing `slope_*_pct`. Phase B adds an OLS log-slope over each window (uses all
points, robust to an outlier endpoint) + its R² as a trend-quality measure; compute ROC on the
**smoothed** ratio so momentum isn't jittery.

**D-D — Multi-timeframe trend: per-horizon UP/FLAT/DOWN with a dead-band.**
Per horizon (1m/3m/6m/12m) from the slope sign + a dead-band to kill whipsaw:
- `slope ≥ +3%` → strong-up ▲ (green); `0..+3%` → mild-up ▲ (dim green)
- `|slope| ≤ 1%` → FLAT ▬ (amber)   ← symmetric dead-band
- `−3%..0` → mild-down ▼ (dim red); `≤ −3%` → strong-down ▼ (red)
- `NULL` (index too young for the window) → `·` grey "no data"
These are **render-time thresholds** (tunable, no schema change). Phase B can upgrade the dead-band to
volatility-scaled (`τ_N = 0.5·σ_r·252/√N`) + 2-day hysteresis (Schmitt trigger) for fewer flip-flops.
**Daily state is deliberately suppressed** (pure noise); **weekly ≈ covered by the 1m read.**

**D-E — The alignment vector is the headline read.** Render `[1m][3m][6m][12m]` left→right as a 4-cell
heat strip. The **shape** is the signal:
- `▲▲▲▲` persistent leader · `▼▼▲▲` improving (laggard turning up = entry) · `▲▲▼▼` deteriorating leader (exit)
- green spreading **rightward** over time = strengthening; green only on the **left** = short-term pop / dead-cat trap.

**D-F — Absolute × Relative quadrant (read them together, always).**

| | RS rising (beats Nifty) | RS falling (lags Nifty) |
|---|---|---|
| **Price ▲** | **① LEADER** — buy / hold / add | **② LAZY LAGGARD** — up but trailing; avoid/trim (own the index instead) |
| **Price ▼** | **③ DEFENSIVE** — falls less; watch for the turn | **④ DOG** — avoid / underweight |

Key transitions: **③→①** (defensive price turns up = best fresh buy) and **①→②** (leader's RS rolls while
price still rising = first distribution warning). Quadrant ② is the dangerous "false comfort" (P&L green,
alpha negative). Surface ② as a **caution**, not a green arrow.

**D-G — vs Nifty 50 vs vs Nifty 500 divergence = cap-tilt + breadth.**
Both RS rising = clean broad leadership (full conviction). vs-50 ▲ / vs-500 ▼ = **narrow** large-cap-led
(buy the sector's large-caps; rally maturing). vs-50 ▼ / vs-500 ▲ = **broadening** down-cap (buy the
mid/small names; often an earlier phase). One "breadth divergence" chip = `sign(vs500 slope) − sign(vs50 slope)`.

**D-H — Composite RS-momentum score (Phase B), 0–100, cross-sector rankable.**
Robust-z (median/MAD) each horizon across the sector universe per day → weighted blend
`0.15·z1m + 0.35·z3m + 0.30·z6m + 0.20·z12m` → ×trend-agreement ×quality(R²) → map to 0–100 (50 = median
sector). Sorting sectors by this *is* the rotation leaderboard. Phase A interim: percentile of
`rs_vs_broad_slope_3m` computed on-read.

---

## 4. Ratio chart page — `/dash/ratio?idx=<name>&den=Nifty 500` (Phase A)

Read-only detail page (reached by deep-link from Markets/Sectors RS cells; **not** a new nav tab — 5 slots full).
Clones the `/dash/stock` lightweight-charts v4 block.

**Series** (from `ratio_rows` + `ratio_signals`, oldest→newest):
- **Ratio line** (blue) — `ratio_rows.ratio` for `(idx, den)`. Up = outperforming.
- **50-day MA** (amber, the "read this" smoother) — recompute client-side over the ratio array so every range fills.
- **200-day reference** (grey dashed) — above = structurally leading.
- **Markers:** ▲ up-cross of 50-MA (green, "starting to outperform"), ▼ down-cross (red, derive client-side),
  ● new 52-week RS high (`new_52w_high`).
- **Range buttons** 3M/6M/1Y/Max (reuse `.rangebar`); **vs-50 / vs-500 toggle** (reload `&den=`, both pairs stored);
  optional **rebase-100** toggle (`ratio/ratio[firstVisible]×100`).

**Auto "📌 READ" block** (Python strings, no LLM — same pattern as the stock page): 2–4 bullets from
`cross_50_today`, `above_200_ma`, `new_52w_high`, the four slope signs. E.g. *"RS broke above its 50-day line
4 sessions ago — starting to outperform the broad market; above the 200-day reference = structurally leading;
1m/3m/6m rising, 12m flat = a maturing rotation."*

**Granular sections (stack on the same page):** multi-TF heat strip + trend pill · ratio chart · RS-momentum
percentile gauge · **absolute×relative quadrant** (inline SVG, X=`ret_3m_pct`, Y=`rs_vs_broad_slope_3m`,
sector as a dot) · cross-flag pill row · top constituent stocks (via `stock_index_membership` → `stock_signals`,
labeled "by DVPT trigger" until stock-level RS / D33 lands).

---

## 5. Data mapping (have / gap / placement)

**Already stored — do NOT recompute:** full ratio curve (`ratio_rows.ratio`, +`num_close`/`den_close` for the
absolute overlay); `ratio_ma_20/50/200`; 50d/200d/52w high-low bands; `slope_1m/3m/6m/12m_pct` (the normalized
multi-TF trend); `above_50/200_ma`; `cross_50/200_today` (up-cross only); `new_50d/200d/52w_high`; `trend_state`;
and all of it denormalized vs Nifty 500 onto `index_signals.rs_vs_broad_*` + the absolute `ret_*_pct`.

**Gaps → placement:**

| Gap | Placement |
|---|---|
| Per-timeframe UP/FLAT/DOWN label | **compute-on-read** (sign+deadband over existing slopes) |
| Daily/weekly horizons | **on-read** (derive from `ratio_rows`); skip daily-state |
| EMA / smoothed ratio, rebase-100, annualized ROC | **on-read** (transform the fetched series) |
| Bearish (down) cross flag | **on-read now** (sign-change of ratio−MA in JS); optional cheap stored col in Phase B |
| Cross-sector RS-momentum percentile / z | **on-read (Phase A)** via window fn `PERCENT_RANK() OVER (...)`; **store (Phase B)** as a 2nd-pass column for history |
| Smoothed/normalized ROC column | **store (Phase B)** — needs the full curve, reused across pages |

**Pair-series query (Phase A chart):**
```sql
SELECT r.trade_date, r.ratio, r.num_close, r.den_close,
       s.ratio_ma_50, s.ratio_ma_200, s.cross_50_today, s.new_52w_high
FROM ratio_rows r
LEFT JOIN ratio_signals s
  ON s.numerator=r.numerator AND s.denominator=r.denominator AND s.trade_date=r.trade_date
WHERE r.numerator=:idx AND r.denominator=:den   -- TITLE case, e.g. 'Nifty IT' / 'Nifty 500'
ORDER BY r.trade_date ASC;
```

---

## 6. Phased build plan

**Phase A — ship now (only `dashboard.py`; zero schema change, zero backfill):**
- **A1** Two labeled column-groups — **RETURN** (abs) vs **RELATIVE STRENGTH vs Nifty 500** — on `/dash/sectors`
  and the Markets bundle; relabel the major cards' rows "Abs" / "RS".
- **A2** 4-cell **multi-TF heat strip** (`.hstrip`, from `rs_vs_broad_slope_1m/3m/6m/12m`) on Markets cards,
  Sectors table, Home top-sectors. + a derived agreement label (broadening / rotating / deteriorating).
- **A3** New `/dash/ratio?idx=&den=` route — ratio line + 50-MA smoother + 200-MA reference + cross/new-high
  markers + range buttons + vs-50/500 toggle + auto-READ block. Deep-link from Markets/Sectors RS cells.
- **A4** On the ratio page: RS-momentum percentile (on-read), absolute×relative quadrant SVG, cross-flag pills,
  top-constituents table. Guard empty `ratio_rows` (size indexes have none) with `.empty`.

**Phase B — new precomputed metrics + ONE backfill:**
- **B1** Add `roc_smoothed_1m/3m` + `rs_momentum_z` to `ratio_signals` (+ denormalize the Nifty-500 z onto
  `index_signals`). `rs_momentum_z` = **2nd pass** in `compute_for_date` after all sectors for the date are
  written (cross-row z-score). Volatility-scaled dead-band + hysteresis on the trend labels.
- **B2** One `index_signals --backfill` (~10 min / 1,244 days) — batch all new columns together.
- **B3** `/dash/rs` cross-sector ranking page (sort by `rs_momentum_z`); RRG-style quadrant tail (optional).

## 7. Risks / rules
- **Title-case names** (the bug that just bit us): pass benchmark names from `DEFAULT_BROAD`/`BROAD_BENCHMARKS`
  verbatim; **validate `idx` against `SELECT DISTINCT index_name`** rather than trusting the querystring.
- **Batch Phase-B columns into one backfill** (don't pay 10 min per column). Add nothing to schema in Phase A.
- **Idempotency:** all writes `INSERT OR REPLACE`; the z-score 2nd pass must run after the per-pair loop.
- **MA warm-up:** `ratio_ma_200` is NULL until 200 points — tolerate leading nulls; young indexes show grey `·`.
- **No runtime LLM** (cost doctrine): every metric is arithmetic; insights are deterministic Python strings.

## 8. Tunable knobs (defaults to revisit after use)
Dead-band ±1% / strong-cut ±3% (D-D) · score weights 0.15/0.35/0.30/0.20 (D-H) · hysteresis 2 closes ·
smoother = SMA-50 · k=0.5 for the volatility-scaled dead-band.

---

# PART 2 — Multi-index comparison + rebase chart (D40) + chart performance fix

> Added 2026-06-17 from a 2nd panel (financial + data + UI/UX + architect). Render-only; **zero schema, zero backfill, no new deps.**

## The feature
Overlay N indices (≤6) on one chart, each **rebased to a common start** so they begin together → read who outperformed. **Fluid anchor:** the rebase point = the first visible day; pan left so Feb is the left edge → Feb becomes the new 0/100 and all lines recompute. Toggle **Rebased ↔ Ratio**. Works on absolute index levels (any index) and on RS ratios.

## Decisions
- **D40-A — New route `/dash/compare`** (NOT a mode on /dash/ratio — that page is single-subject: gauge/quadrant/READ/constituents are meaningless for N lines; NOT a 6th nav tab — nav is full at 5, and Compare is a *destination reached with intent*). Entry points: a "Compare ⇄" button in /dash/ratio's fbar, a "⇄ Compare indices" `.row .sub` link on /dash/markets + /dash/sectors. `active="markets"`. URL-addressable & shareable: `?idx=A&idx=B&den=&mode=&base=&anchor=&r=` (FastAPI maps repeated `?idx=` → list).
- **D40-B — Data (render-only):** `index_rows.close_value` (absolute level of ANY index — this is why a new route: N peer series, not the single-numerator `ratio_rows`). `ratio_rows.ratio` for ratio mode. **Validate every `idx` against `SELECT DISTINCT index_name`** (title-case gotcha — strip + drop unknowns, never case-munge). Send RAW values, rebase client-side. `{t,v}` only, rounded (close 2dp / ratio 4dp). Default window 1Y; cap 6 lines. Existing composite indexes cover the queries.
- **D40-C — Rebase math (client-side):** base-100 `v[t]/v[t₀]×100` (default) or base-0% `(v[t]/v[t₀]−1)×100` — same geometry, relabeled axis. Log-axis toggle, auto-suggest when window >~1y or max/min spread >~1.4×. **One common forward-snapped anchor for all lines** (snap to first trading day ≥ left edge); drop (don't fudge) a line with no data at the anchor; guard `v[t₀]>0`.
- **D40-D — Modes:** **Rebased %** (N peers, no denominator) | **Ratio** (each line ÷ chosen denominator, then rebased). **NEVER co-plot price-rebased and ratio on one axis.** Ratio overlays must share ONE denominator (vs Nifty 50 or 500); self-reference (a line == denominator) drops out with a note.
- **D40-E — Picker:** chip rail of active lines (color swatch ● + name + ✕) + `[+ Add]` → `.search` + suggestion chips seeded from `MAJOR_BROAD`/`MAJOR_SECTORS` (filter by substring over ALL index names so any index is addable). Sticky deterministic 6-color palette (`#1f6feb #d29922 #3fb950 #f85149 #a371f7 #58a6ff`) — removing a line never recolors the others. URL is the source of truth (`history.replaceState` on add/remove). The chips ARE the legend.
- **D40-F — Controls (top→bottom, chart is the hero):** Mode [Rebased %|Ratio] · Base [100|0%] (rebased only) · Anchor (fluid default; 📅 pin to a date; ⟳ reset to fluid) · Range [3M/6M/1Y/Max] (a range click also re-anchors fluid to that left edge) · Denom [vs 50|vs 500] (ratio only). Always-visible "**REBASED FROM <date>**" indicator (live in fluid; 🔒 when pinned). Crosshair value row under the chart shows each line's value (color-coded).
- **D40-G — Presets (one-click):** default **"Sector vs market (50 & 500)"** (price-rebased) · "Sector race" (N sectors) · "Sector vs benchmark — RS" (ratio) · "RS head-to-head (same denom)" · "My basket".

## Chart PERFORMANCE fix (the range-switch slowness)
- **Root cause (in code):** `/dash/stock` syncs 3 charts via `subscribeVisibleLogicalRangeChange` with **NO reentrancy guard** → a range-button click ping-pongs range updates pc↔vc↔dc until float-convergence (worst on →Max, where `fitContent()` vs `setVisibleLogicalRange` never exactly reconcile), each hop a full pane redraw. Amplified by the `ResizeObserver` calling `applyOptions({})` on all 3 charts. (NOT MA/data recompute — those are set once.)
- **Fix:** (A) a `syncing` reentrancy flag guarding the sync subscription; (B) `setRange` applies the range to all charts **directly** under the flag (bypassing the sync round-trip), `fitContent()` per-chart for Max; (C) debounce the ResizeObserver (~100ms) + gate with `syncing`. /dash/ratio: debounce its ResizeObserver. ~10 lines, touches the /dash/stock IIFE + /dash/ratio ResizeObserver.
- **/dash/compare fluid-rebase smoothness:** recompute on `subscribeVisibleTimeRangeChange`, **rAF-coalesced + anchor-gated** (skip if the left-edge trading day hasn't changed → panning within a day is free), reentrancy-guarded so `setData` doesn't recurse.
