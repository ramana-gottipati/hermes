# CPR — Central Pivot Range (Patearn charting lens) — Canonical Reference

> **Class:** CANONICAL reference (permanent — do not archive).
> **Status:** LIVE (descriptive charting lens) · **Governing decision(s):** D53 (CPR "STRUCTURE" pillar / engine) · D71 (the "CPR Spine" charting overlay) · **Reconciled:** 2026-07-11 (S111).
> **Origin:** 📚 CLASSIC base (floor-trader pivot-range school) + 🏠 HOUSE multi-degree amplification (the "CPR Spine" ladder · compression-percentile · confluence). See [origins.md](origins.md).
> **Charter:** the single canonical definition + current-state reference for CPR. Deep design: [cpr-strategy-design.md](../cpr-strategy-design.md). Numbers live in code + [calculations-and-weights.md](../calculations-and-weights.md); this page never restates a formula's constants — it links.

**One-line definition:** CPR (Central Pivot Range) is a three-line band — a central **Pivot** wrapped by a **BC/TC** envelope — projected from a period's *prior* High/Low/Close and read at several degrees (Daily / Weekly / Monthly / Half-yearly); Patearn renders it as the amber **"CPR Spine"** behind price and screens on its width/shape as **descriptive structure and context**, never as a ranked or fundable return signal.

---

## 1. What it is

CPR is a floor-trader pivot construct: from a completed period's H/L/C you derive three horizontal lines — a **Pivot** (the range's centre) plus two envelope lines, **BC** (bottom-central) and **TC** (top-central) — that project onto the *next* period as a support/resistance band. Plotted across consecutive periods the band becomes a **stepped ribbon** whose two readable properties carry the signal:

- **Width** — how tight the BC↔TC band is (as a % of the Pivot). A **narrow** band = a *coiled* market (a large move pending); a **wide** band = an already-expanded / trending state.
- **Shape** — the sequence of consecutive bands stepping up, down, or turning (the U / inverted-∩ reversal).

The same logic is read at multiple **degrees** — Daily, Weekly, Monthly, and (added for the chart ladder) Half-yearly — with only the period changing. In Patearn CPR wears **two faces over one shared primitive**:

1. **The STRUCTURE pillar (D53)** — a nightly-materialized screening engine (`cpr_signals`) exposing U/∩ reversals, an *unusually-narrow* compression scanner, cross-timeframe amplification and confluence, surfaced in the screener and at `/dash/cpr`. This is the 4th Patearn pillar beside Positioning (DVPT), Relative Strength, and Quality — it answers *where price sits in its multi-degree structure, whether that structure just turned, and whether it is coiled*.
2. **The "CPR Spine" (D71)** — a charting overlay that draws that same geometry as an amber ribbon behind price on the `/dash/stock` chart, as higher-timeframe S/R context for whatever interval you are looking at.

Both faces are **descriptive**: they frame and select, they do not rank a return edge (see §4).

## 2. Our variation vs. the standard technique

The **standard** floor-trader CPR is a single-degree, intraday construct: one day's H/L/C → today's Pivot/BC/TC, used as intraday support/resistance. Patearn's variation departs on four points:

- **Multi-degree, end-of-day, not intraday.** We compute Daily, Weekly, Monthly (and Half-yearly) CPRs from each period's prior H/L/C and read them together — the "CPR Spine" is a *sequence of bands across time*, not one intraday line. Width and shape are read at every degree.
- **Width as a first-class "coil" metric.** The band width (normalised by the Pivot) is the narrowness signal: **narrower = more coiled = bigger pending move**. Both an absolute per-degree width cutoff and a *relative* own-history compression percentile ("unusually narrow **for this stock**") are exposed — the truer "unusual". (Numbers → §3 / [calculations-and-weights.md §5b](../calculations-and-weights.md).)
- **Shape as a reversal pattern.** Three consecutive same-degree CPRs where each leg is a *clean directional step* (both band lines move the same way) form a **U** (bullish bottom) or **∩ / inverted-U** (bearish top). Strength is graded by how narrow the two recent bands are (R1…R4, today's band the priority).
- **The chart-ladder convention (D71, Ramana's rule).** On the **Spine overlay**, the CPR shown is **one degree HIGHER than the chart interval** — a daily chart shows the **Weekly** CPR, weekly → **Monthly**, monthly → **Half-yearly** — because higher-degree pivots are the meaningful S/R for the horizon you trade. (Contrast: the *screener* / `/dash/cpr` reads each timeframe's own same-degree CPRs and their reversals.) The Half-yearly (`H`) degree exists specifically to serve this ladder.

The combiner across degrees: **a faster-timeframe signal is amplified when slower timeframes are also coiled/aligned, with the larger timeframe carrying more weight** — surfaced as transparent ★ Structure tiers with a visible per-degree breakdown, never an opaque mega-score. Full model + rank tables: [cpr-strategy-design.md](../cpr-strategy-design.md) §3–§5.

## 3. How it works (methodology)

**The primitive.** Each CPR is built from the **prior completed period's** High/Low/Close: a central **Pivot**, a **BC** line, and a **TC** line mirrored about the Pivot, forming the `[BC…TC]` band centred on the Pivot. The **width%** normalises the band by the Pivot. Prices are **split/bonus-adjusted** first so the band and the current close share one continuous price regime.
→ The exact arithmetic for Pivot / BC / TC / width% is **not restated here** — it lives in code (`src/automation/cpr_signals.py`, and the `chart_view.cpr_segments` transform) and is documented once in [calculations-and-weights.md §5b](../calculations-and-weights.md) and [metrics-glossary.md](../metrics-glossary.md) (CPR section).

**Width interpretation ("coil").** A band is flagged *coiled* when its width% is at/under a **per-degree cutoff** (Daily is tightest, Half-yearly loosest — a flat cutoff would make wider degrees never qualify). The relative measure (**compression percentile** vs the stock's own trailing history) is the primary "unusually narrow" sort. The per-degree cutoffs and weights are query-time knobs — geometry/widths are stored, rank/score derived **on read** — so they can be tuned without re-materialising. Values: [calculations-and-weights.md §5b](../calculations-and-weights.md); overlay cutoffs live in `chart_view.COIL_PCT`.

**Multi-timeframe stacking.** Latest D/W/M pivots that cluster within a small tolerance merge into a **confluence** S/R slab (a high-probability magnet, drawn as the "D·W·M" band). `regime` = the sign of close vs Pivot gives the higher-degree trend context that the amplifier rewards. The cross-TF **conviction/★ tier** is an *additive, breakdown-visible* score (larger degree weighted more), computed on read. All formulae and weights: [cpr-strategy-design.md](../cpr-strategy-design.md) §4 + [calculations-and-weights.md §5b](../calculations-and-weights.md).

## 4. Status, validation & honesty fence

**LIVE — and deliberately descriptive.** CPR is shipped and running (materialized nightly; drawn on the live chart; screenable), but it is a **charting / context / selection lens, not a validated alpha signal**:

- **No standalone return backtest is recorded** for CPR in the strategy ledger. There is no measured, cost-net return edge attributed to CPR reversals or compression. This page does **not** claim one; if you need a fundable edge, CPR is not it.
- **Kept OUT of the cross-pillar Conviction number** (which stays Positioning + RS only). CPR surfaces as a *parallel* ★ Structure tier column and a one-click "CPR-confirmed" screener gate — never folded into the ranked composite. Rationale (D53): the composite is itself unvalidated, CPR has no live history, and doctrine is "master each pillar alone, then club."
- **Consistent with project doctrine:** this is context/selection, not fundable alpha. Treat CPR output as *"where is structure, is it coiled, has it turned"* framing that a human (or another validated pillar) then acts on — not as a buy/sell instruction.

Any future attempt to promote CPR into a ranked/return claim must first clear a leak-free out-of-sample backtest and be recorded in the ledger; until then it stays descriptive.

## 5. Where it lives (code · routes · DB · timers)

**Engine (STRUCTURE pillar, D53):**
- `src/automation/cpr_signals.py` — the timeframe-parameterized nightly materializer. **Self-resamples** its own split-adjusted D/W/M/H H/L/C bars from `bhavcopy_rows` (replicates `_period_key`; **no dependency** on the held MTF foundation, D52). Computes the CPR primitive + clean-step U/∩ reversal + compression percentile + regime + freshness + `confirmed`. CLI: `--backfill` / `--recent` / `--symbol`, `--timeframe D|W|M|all`.
- **DB:** the **`cpr_signals`** table (defined in `src/core/db.py`, additive; `stock_signals` untouched). PK `(symbol, period_end_date, timeframe ∈ D/W/M/H)`. Stores geometry + widths + pattern/regime/flags; **rank, amplification and ★ tier are derived on read** (never stored).
- **Timer:** runs as a leg of the **nightly signals chain** (`cpr_signals.py --recent --timeframe all`, appended after `stock_rs`) — no upstream dependency, WAL means it never blocks dashboard reads. It is *not* a standalone systemd timer (unlike the harmonic scanner).

**Charting overlay (CPR Spine, D71):**
- `src/web/cpr_overlay.py` — the **`/dash/cpr/overlay`** JSON endpoint (reads `cpr_signals`, one-degree-higher ladder) **+** a self-contained SNIPPET that draws the Spine primitive on the existing candle series (`window.__wfcandle` / `window.__wfpc`) and injects the **CPR chip** into the chart's "Strategies" family. **Default OFF, opt-in.** Draws: regime-tinted BC↔TC band, dashed/solid Pivot core, brighter fill at coil, an amber D·W·M confluence slab, and U/∩ markers on the **middle candle** (with a `?` until `confirmed`).
- `src/web/chart_view.py` — the DB-free transforms the overlay reuses: `cpr_segments()` (rows → stepped segments, sets the `coil` flag off `COIL_PCT`) and `confluence()` (clustered-pivot slab). ⚠️ `render_stock_chart()` in this module is **DEPRECATED / not live** (the live `/dash/stock` chart is `src/web/stock_chart.py`'s snippet); only `cpr_segments` / `confluence` are wired.

**Screener & pages (D53 surfaces, in `src/web/dashboard.py`):**
- The **CPR column-group** in the screener (`g-cpr`): D/W/M width% + D·W·M glyph strip + R-rank + ★ Structure tier + Comp%, a group-toggle chip, and the **"CPR-confirmed"** gate.
- The **CPR card** in `/dash/strategies` (top fresh structure setups → links out).
- **`/dash/cpr`** — three tabs: **Reversals** (cross-TF amplified ★ screen), **Compression** (unusually-narrow CPRs by own-history percentile), **EOD Reports** (Daily/Weekly/Monthly "what fired", W/M carry a "live for the current period" badge).
- A per-stock **CPR panel** on `/dash/stock` (the D·W·M strip + P/BC/TC table + plain-English verdict).
- Read-only rollups also consume `cpr_signals` via `src/automation/strategy_registry.py` and `src/web/strategist_view.py`; Pat grounds on it via `src/pat/glossary.py` / `src/pat/flows.py`.

## 6. Data & provenance

CPR is derived **entirely from NSE bhav-copy OHLC** (`bhavcopy_rows`) — a primary/authentic source (Doctrine Guardrail #8, primary-sources-only). No vendor or Screener.in dependency. The engine self-resamples split/bonus-**adjusted** H/L/C period bars (per-day adjustment factors applied, then aggregated), drops anomalous bars (`|daily return| > 0.30`, D36), and honours the equity-only allowlist (D42) + thin-prior-period skips. Everything is re-derivable from the raw archive; the bhav-copy archive is never normalised away (Doctrine § C).

## 7. Terminology canon

- **CPR (Central Pivot Range)** — the three-line band (Pivot + BC/TC) from a prior period's H/L/C. *Disambiguation:* this is a **pivot-derived S/R + coil construct**, distinct from generic hand-drawn support/resistance and distinct from **RS-band** (`rs_band_pct`, a relative-strength position vs Nifty 500 — a different lens entirely).
- **Pivot (P)** — the central line / band centre. **BC / TC** — the bottom-central / top-central envelope lines that bound the band. (Arithmetic → linked, not restated.)
- **Width% / "coil"** — band width as a % of the Pivot; the narrowness metric. **Coiled** = width at/under its per-degree cutoff. **Compression percentile (Comp%)** = how narrow the current band is vs the stock's own history (the relative "unusual").
- **CPR Spine** — the amber ribbon rendering of the band sequence behind price on the stock chart (the D71 charting identity). On the overlay it shows the CPR **one degree higher** than the chart interval.
- **U / ∩ (BULL_U / BEAR_INVU)** — the three-CPR reversal shapes (bottom / top), each leg a clean directional step.
- **Regime** — sign of close vs Pivot (above/below); the higher-degree trend context.
- **Confluence** — ≥2 of the D/W/M bands overlapping at one price → an S/R slab.
- **Narrow vs Wide CPR** — narrow = coiled/energy-stored (move pending); wide = already-expanded/trending.
- **Degrees** — D (Daily) / W (Weekly) / M (Monthly) / **H (Half-yearly**, added for the chart ladder).

Client-facing definitions live in [metrics-glossary.md](../metrics-glossary.md) (CPR section); internal thresholds/weights in [calculations-and-weights.md §5b](../calculations-and-weights.md).

## 8. Decision & session history

- **D53 — CPR "STRUCTURE" pillar (2026-06-19, Session 21).** The 4th Patearn strategy shipped end-to-end, no-regression: the `cpr_signals` engine (D/W/M) + screener CPR column-group + Strategies card + `/dash/cpr` (Reversals · Compression · EOD Reports) + stock panel. All seven OPEN modelling decisions resolved to the recommended defaults via multiple-choice-with-recommendations (leg = both-lines clean step; rank priority = C0; show both + `confirmed`; width ÷ Pivot; per-TF cutoffs D 1.0 / W 2.5 / M 5.0%; TF weights D 1 · W 2 · M 3; "unusual" = own-history percentile **+** absolute knob). CPR kept **out** of the Conviction number. Local decisions **CPR-A1…A7, CPR-B1, CPR-X1/X2** ([cpr-strategy-design.md](../cpr-strategy-design.md) §14). Build log: design doc §16.
- **D71 — Charting overhaul → the "CPR Spine" (2026-06-24, Sessions 41–42).** "Build our OWN chart on lightweight-charts (inspired, not copy)"; the CPR Spine became the chart's signature identity. `cpr_overlay.py` + `chart_view.py` built, wired, and **deployed to the VPS** (verified live on real symbols). Ramana's corrections (commit `bfe6093`): CPR **follows the chart interval**, marker on the **middle candle**, **default OFF**, grouped under "Strategies". Ladder correction (commit `e5b369c`): CPR is **one degree HIGHER** than the chart → **new Half-yearly `H` degree** added to `cpr_signals` (`_period_key` H1/H2) and **backfilled 2,358 symbols / 48,229 rows**; `H` joins `--timeframe all` so the nightly keeps it current. Design/build record: [chart-redesign-design.md](../chart-redesign-design.md) §0.1/§14; memory `charting-overhaul-cpr-spine`.
- **Session 42 — one-chart engine.** `src/web/stock_chart.py` re-homed the CPR chip into the unified four-family rail; **the CPR was NOT re-implemented** — it stays owned by `cpr_overlay.py`, and the `window.__wfpc`/`__wfcandle` contract is preserved so the Spine keeps working. (Ramana is happy with the CPR itself — don't touch it.)
- **Healing / price-scale sessions (S95–S9x).** After the D95 dead-zone and price-scale fixes, `cpr_signals` was re-materialized across D/W/M/H as one of the nightly legs (anchor-CPR sanity checked); no methodology change.

## 9. Open items / frozen work

- **Telegram `/cpr` — designed but NOT shipped.** The design doc §7 lists a Telegram `/cpr` (+`/cpr narrow`) surface; no such handler exists in `src/assistant/telegram_bot.py` today. Treat it as an unbuilt design aspiration, not a live command. *(Contradiction flagged — see below.)*
- **Full 3C trend-stack screen** — only the `regime` bit (close vs Pivot) is consumed today; the full stack/slope `FULL BULL…BEAR` screen with `stack_age`/`signal_event` is deferred.
- **3D confluence as a chart visualization** — only the binary flag / merged slab is used; a richer confluence-zone view is deferred.
- **Compression coil-age "freshness"** (how long a CPR has stayed coiled) — deferred; reversal `days_since_pattern` freshness is live.
- **CPR × DVPT × RS hybridization** ([cpr-strategy-design.md](../cpr-strategy-design.md) §12) — recorded only, do **not** build without an explicit decision; the §4 score is kept additive so this stays a clean extension.
- **Folding CPR (or Quality) into the Conviction composite** — deferred pending live history + a leak-free validation; a design-panel decision, not a silent default.
- **`chart_view.render_stock_chart()`** — DEPRECATED/not live; do not re-wire without a decision (the live chart is `stock_chart.py`).

## 10. Sources of truth

- **Deep design + build log:** [cpr-strategy-design.md](../cpr-strategy-design.md) (the design of record — §3–§5 model, §13 resolved decisions, §14 local decision log, §16 build log).
- **Numbers (internal):** [calculations-and-weights.md §5b](../calculations-and-weights.md) — CPR width knobs + ★ Structure tier weights (code constants remain the single source of truth).
- **Definitions (client-facing):** [metrics-glossary.md](../metrics-glossary.md) — CPR section (Pivot/BC/TC, Width%, Comp%, U/∩, Rank, Regime, where-it-shows).
- **Charting identity:** [chart-redesign-design.md](../chart-redesign-design.md) (the "CPR Spine" signature + four-family rail) · memory `charting-overhaul-cpr-spine`.
- **Code:** `src/automation/cpr_signals.py` (engine) · `src/web/cpr_overlay.py` (Spine overlay + `/dash/cpr/overlay`) · `src/web/chart_view.py` (`cpr_segments` / `confluence` / `COIL_PCT`) · `src/core/db.py` (`cpr_signals` table) · `src/web/dashboard.py` (screener group, `/dash/cpr`, stock panel).
- **PROJECT_STATE:** [../../PROJECT_STATE.md](../../PROJECT_STATE.md) — Decision log **D53** (STRUCTURE pillar) and **D71** (charting overhaul); Session-log entries 21 and 41/42.

---

## Maintenance

- **This page is a reference, not a source.** It links; it must never restate a formula's constants. When the pivot arithmetic, per-degree cutoffs, or tier weights change, edit **code + [calculations-and-weights.md](../calculations-and-weights.md)** — then reconcile the prose here.
- **Honesty fence is load-bearing.** CPR stays **descriptive** (charting/context/selection) and **out of the Conviction number** until a leak-free out-of-sample return backtest is recorded in the ledger. Do not soften §4 without that evidence.
- **Two faces, one primitive.** Keep the D53 engine (`cpr_signals`) and the D71 Spine (`cpr_overlay.py`) in sync conceptually — the overlay reads the engine's table via `chart_view`. The Spine's **one-degree-higher ladder** is Ramana's rule; the screener reads same-degree CPRs — don't conflate them.
- **On any material CPR change,** update: this page, [cpr-strategy-design.md](../cpr-strategy-design.md), [calculations-and-weights.md](../calculations-and-weights.md), [metrics-glossary.md](../metrics-glossary.md), and the PROJECT_STATE Session log — in the same commit as the code (state-doc gate).
- **Reconciled:** 2026-07-11 (S111). Re-verify against `cpr_signals.py` + `cpr_overlay.py` + `chart_view.py` before treating any file:line detail as current.
