# Chart redesign — design + plan (the "CPR Spine" charting overhaul)

> **Status:** DRAFTING — 2026-06-24. Diagnosis, signature motif, and the four-family control
> taxonomy are locked; **all screenshots received** (chart types · indicators · drawings/Fib/Gann ·
> patterns/Elliott). **Library RESOLVED → build our own (§12).** ✅ **Phase 0 + CPR Spine BUILT + verified
> (commit `7dee885`)** — `src/web/static/hermes-charts.js` + `src/web/chart_view.py`; wire-in into
> `/dash/stock` pending (dashboard.py parallel-held). See **§14 build log**. Canonical home; **intents §0.1**;
> cross-session pointer = PROJECT_STATE S41/D71/D72 + memory `[[charting-overhaul-cpr-spine]]`. TRANSIENT companion run-books may spin off but
> this doc is the durable design.
> **Session origin:** "Improve Charting" — a charts-only session. Four research panels
> (analyst · layperson/UX · charting engineer w/ web research · design language) converged.
> **PIVOT (2026-06-24, after Ramana's FYERS screenshots):** the target feature set = FYERS' menus,
> which are **TradingView Advanced Charts**. This forces a library decision (lightweight-charts can
> never reach it) with a real licensing caveat — see **§12**. Everything below (Spine, grammar,
> phasing) still holds; §12 decides the *engine* it's built on.
> **RESOLVED 2026-06-24 — Ramana: "we won't copy what TradingView gives, we only get inspired."**
> → Build our OWN charting on **lightweight-charts** (Apache-2.0, free for any use — licensing gate
> dissolved), inspired by FYERS' feature set but with our own design language + a *curated* toolset.
> The drawing/pattern engine becomes our largest, prioritized workstream — see expanded **§6**.

---

## 0. Intent (one paragraph)

The stock price chart (`/dash/stock`) — and charts site-wide — are weak: stretched, fragmented,
the proprietary strategies are never drawn on the price, and CPR (already materialized) is shown
only as a text strip. Rebuild into **ONE responsive price chart** with a clean control taxonomy
(chart-type ▾ · proprietary strategies · standard indicators · drawing tools), draw the strategies
as toggleable overlays with **CPR as the signature "Spine,"** and ship a **single reusable chart
engine + fixed visual grammar** rolled across the whole site so every chart — down to a 92px
sparkline — speaks the same language.

---

## 0.1 Ramana's intents & asks (verbatim-faithful — the brief; do NOT lose these)

Captured across the charting session (2026-06-24). Keep faithful; everything below serves these.

1. **Charting is poor — fix it.** Stretched, lacks features, can't display content. ("I don't want to keep explaining.")
2. **Strategies → indicators on the SAME chart.** DVPT/etc. are separate lines today; make each a toggleable overlay on ONE chart with per-item **show/hide**.
3. **CPR must be DRAWN** (we already compute it) — "actually work on it," a real visual, not a text strip.
4. **Exclusive, non-generic identity** with strong unique patterns, applied to the WHOLE website. "What's special about it?" → the **CPR Spine** (§2).
5. **Plan first, ranked by priority;** gather analyst + layperson input; multiple researchers. (Delivered §8 + two mockups.)
6. **Chart TYPES are NOT indicators** — own section, as a **dropdown** (space-efficient): Candles, Hollow, Volume candles, Bars, HLC, Line, Line-w-markers, Step, Area, HLC area, Baseline, Columns, High-low, **Heikin Ashi, Renko, Line break, Kagi, Point & Figure**.
7. **Proprietary strategies = their own section; standard indicators = a separate section.** (The four-family control bar, §3.)
8. **Drawings** — full set inspired by FYERS: lines, channels, pitchforks, **Fibonacci** suite, Gann, **patterns** (XABCD/Cypher/Head-&-Shoulders/ABCD/Triangle/Three-Drives), **Elliott** waves, cycles, projections, volume-based, **measurers**. (Curated tiers, §6.)
9. **Magnet** — a drawing's anchors **snap to the nearest OHLC**, but stay **freely overridable**.
10. **Hide-all-drawings = one button:** tap to hide all, tap again to restore.
11. **"We won't copy what TradingView gives — we only get inspired."** → build our OWN (resolves the engine to lightweight-charts; §12).
12. **Auto-detect patterns when selected** — especially **Harmonic Patterns** ("very important"), detect where they are **forming** (down the stream) for stronger/more-reliable signals; be able to **screen/scan**; **predict** setups. Elliott = maybe, exploratory. (Capability audit §13.)
13. **Data reality:** daily EOD OHLC only, **no intraday** — fine for an investor; may buy an intraday set later for research. (Confirmed sufficient, §13.)
14. **Record intents + maintain the MD files** so a session ending never loses the work. (This §0.1 + PROJECT_STATE S41/D71/D72 + memory `[[charting-overhaul-cpr-spine]]`.)

---

## 1. Diagnosis — why it's poor today

- **Focal chart:** `src/web/dashboard.py` ~7060–7325. Library: **lightweight-charts v4.1.3** (CDN
  constant `_LWC_CDN`, line 5925). Server-rendered: Python f-string of HTML+JS with `DATA={...}`.
- **Four separate chart instances**, fixed short heights, manually time-synced via
  `subscribeVisibleLogicalRangeChange` + a reentrancy guard: price (300px), DVPT histogram (150px),
  delivery-% (120px), traded/delivery value (130px). The short-wide stack **is** the "stretched" feel.
- **Strategies are stranded in 7 tabs**, never on the candles. DVPT = an isolated pane. **CPR is a
  text table** (`_cpr_stock_panel` ~2529) even though P/BC/TC are horizontal price levels already
  stored in `cpr_signals` (`src/core/db.py`, materialized by `src/automation/cpr_signals.py`).
- **Other charts** (RRG, RS overlay `_RS_OVERLAY_JS` ~5935, ratio `_RATIO_CHART_JS` ~7331,
  sparklines) are copy-pasted JS f-strings; sparklines/heat-strips use `preserveAspectRatio="none"`
  (literal shape distortion).
- The only strategy already wired as a true on-chart toggle is **Wolfe** (`wolfe_overlay.py`,
  `window.__wfpc`, fetch-on-toggle, autoscale opt-out via `NS`). That is the pattern to generalize.

---

## 2. Signature motif — the **CPR Spine** (the "what's special")

Every Patearn price chart floats over one ownable, luminous element: the Central Pivot Range
rendered not as three dotted broker lines but as a **breathing amber ribbon** behind the candles.

- **Geometry:** Pivot = a solid 1px core at `#d29922`; the BC↔TC band = translucent amber fill
  (`rgba(210,153,34,0.12)`), stepped flat across each period → the "sequence of bands."
- **Regime tint:** price above pivot → faint green wash; below → faint red wash.
- **Coiled spring:** when the band compresses (width below the per-TF knob D 1.0 / W 2.5 / M 5.0%,
  or high own-history `compression_pctile`), the segment brightens to a saturated amber stroke
  (`#d29922`, lineWidth 2) with an optional 2.4s opacity breath — compression *felt*, not labelled.
- **Confluence slab:** when ≥2 of D/W/M pivots cluster (~within 0.75%), they fuse into one brighter
  zone (`rgba(227,179,65,0.16–0.28)`) with a left "D·W·M" tab — the S/R magnet.
- **U / ∩ reversal:** a marker drops on the turning candle (bull-U green ▲ "U·R1" below, bear-∩ red
  ▼ above); solid when `confirmed`, hollow/dashed when forming.
- **Scales by reduction:** the big chart shows the full ribbon; a 92px sparkline collapses it to a
  2px amber hairline at the pivot. Learn "amber ribbon = structure" once, read it everywhere.

Paired with a **fixed colour + glyph per strategy** and a **legend rail whose toggle chips light up
in each strategy's own hue**, the site becomes one learnable visual language.

### Strategy colour & glyph grammar (fixed, site-wide)

| Strategy | Hue | Treatment | States |
|---|---|---|---|
| **CPR** | amber `#d29922` (slab `#e3b341`) | spine ribbon + dashed pivot | coiled = bright/pulse · confluence = slab · U=green edge / ∩=red edge |
| **DVPT / MEP** | violet `#bc8cff` (distrib pink `#db61a2`) | candle under-glow + markers | accumulate violet · distribute pink · neutral `#30506b` |
| **RS** | cyan `#39c5cf` | docked pane / 0–100 band lane | support floor `#1f6feb` → resistance ceiling `#f85149` |
| **Wolfe** | blue `#58a6ff` | dashed target ray | forming dashed · confirmed solid + target dot |
| **Conviction** | white→amber `#e6edf3`→`#d29922` | radial dial glyph | hue scales by score |

---

## 3. Control architecture — FOUR distinct families (Ramana, 2026-06-24)

Chart **type** ≠ indicator ≠ proprietary strategy ≠ drawing. Four separate control groups:

1. **Chart type — a DROPDOWN** (space-efficient; NOT an indicator). See feasibility §4.
   Candles · Hollow candles · Line · Bar (OHLC) · Heikin Ashi · Renko · Point & Figure.
2. **Strategies (proprietary) — its own toggle section:** CPR (spine) · DVPT · MEP · RS · Wolfe ·
   Conviction. Each chip in its fixed hue (§2); active = filled in that hue.
3. **Indicators (standard) — a separate section:** MA/EMA · VWAP / Anchored-VWAP · Bollinger ·
   Volume · RSI · MACD · ATR … Compact "+ add" menu so the bar stays clean.
4. **Drawings — a tool palette:** trendline · ray · horizontal line · Fib retracement ·
   rectangle/zone · parallel channel · text note · measure. Scope from screenshots (§6).

---

## 4. Chart types — feasibility (lightweight-charts is a TIME-axis engine)

| Type | Tier | How |
|---|---|---|
| Candles, Line, Bar (OHLC), Area/Baseline | **Native — now** | built-in series types |
| **Heikin Ashi** | **Computed — easy** | transform OHLC client-side → feed a candlestick series |
| **Hollow candles** | **Computed — easy** | candlestick styling: transparent up-bodies + coloured borders |
| **Renko** | **Hard — no time axis** | price-bucketed; breaks the time scale → custom-series primitive (v5) or separate render path |
| **Point & Figure** | **Hard — no time axis** | column-of-X/O, price-bucketed; same constraint as Renko |

→ Renko & P&F are a **later dedicated workstream**, not Phase 0/1. Everything else is in scope early.

---

## 5. Strategies as overlays — where each lives

| Strategy | Placement | Why |
|---|---|---|
| **CPR spine** | price-pane overlay (ribbon + markers + confluence lines) | they are price levels |
| **DVPT / MEP** | markers + under-glow ON candles (+ optional histogram pane) | the *event* belongs on price |
| **RS** | docked sub-pane (ratio + MA) or 0–100 band lane | own units/axis |
| **Wolfe** | price-pane overlay (already `__wfpc`) | geometric, on-price |
| **Conviction** | header badge / crosshair readout, not a series | composite score |

**Default-on (clean first paint):** Candles · 50/200 MA · Weekly CPR ribbon + Monthly pivots +
confluence · DVPT institutional markers · one docked volume/flow pane. Everything else opt-in.

---

## 6. Drawings workstream — our OWN, inspired & curated (the largest part)

**Doctrine (Ramana 2026-06-24): "inspired, not copy."** We build our own drawing engine on
lightweight-charts (v5 primitives: render + click/drag hit-testing + per-symbol persistence), **curate
hard** (not all 110 TradingView tools), and give it our identity. This is the single biggest workstream;
phase it by real frequency of use.

### Two explicit cross-cutting features Ramana specified
- **Magnet mode (toggle).** When ON, a drawing's anchor points **snap to the nearest OHLC value of the
  nearest bar** (any of open/high/low/close — whichever is closest to the cursor), **but remain freely
  draggable/overridable** after snapping. Implementation: on pointer-move during draw/edit, find nearest
  bar by x → nearest of its 4 OHLC y-values → snap anchor; a modifier or post-drag releases the snap.
  (TradingView-style weak/strong magnet; we ship one sensible snap.)
- **Hide-all-drawings (single toggle button).** One button flips the visibility of **all** drawings at
  once (retained, not deleted); press again to restore. Implementation: a `visible` flag on the drawings
  layer / each drawing primitive.

### Curated tiers (inspired by FYERS' full menu — screenshots 2026-06-24)

| Tier | Tools | Note |
|---|---|---|
| **T1 — core, build first** | Trend line · Horizontal line/ray · Vertical line · Rectangle/zone · Fib retracement · **Measurers** (Price range, Date range, Date+Price range) · **Long/Short position** · Text note | The high-frequency 90% · + Magnet + Hide-all + toolbar + persistence |
| **T2 — common** | Ray / Extended line · Parallel channel · Trend-based Fib extension · Anchored VWAP (also an indicator) · Horizontal ray · Info line | |
| **T3 — specialist, later/optional** | Harmonic **patterns** (XABCD, Cypher, ABCD, Three Drives, Head & Shoulders) · **Elliott** wave tools (Impulse 12345, Correction ABC, Triangle ABCDE, WXY, WXYXZ) · **Pitchforks** (Schiff/Modified/Inside) · **Gann** (Box/Square/Fan) · **Cycles** (Cyclic lines, Time cycles, Sine) · **Projection/Forecast/Ghost feed/Bars pattern** · Fixed-range Volume Profile | Specialist, lower frequency — curate to what Ramana uses |

### Overlap with our proprietary auto-patterns (our differentiation)
"Auto detection of patterns if I select" = our **server-computed** patterns surfaced as on-select
overlays (already materialized): **CPR U/∩** (`cpr_signals.pattern`), **Wolfe** (a 5-point harmonic — our
inspired answer to the XABCD/Three-Drives family), **DVPT/MEP** spikes. These are auto-drawn (no manual
point-placing) — the thing FYERS can't do — while T1–T3 above are manual user drawings.

### Effort & phasing
Drawing engine + magnet + hide-all + persistence + T1 ≈ the bulk of Phase 3. T2/T3 are incremental adds
behind the same engine. Build the engine once (primitive base class: anchors, hit-test, drag, snap,
visibility, serialize) so each new tool is a thin subclass.

---

## 7. Engine + grammar (site-wide)

- **Single static `hermes-charts.js`** served once (FastAPI `StaticFiles`) + a small per-page JSON
  contract, replacing the inlined/copy-pasted f-strings (`_RS_OVERLAY_JS`, `_RATIO_CHART_JS`, the
  stock-page block). One config, palette, behaviour for every chart.
- **Upgrade lightweight-charts v4.1.3 → v5.x** — v5 adds native **panes** (`chart.addPane()`) and a
  **primitives/custom-series** API (`IPrimitivePaneView`/`IPrimitivePaneRenderer`) that are exactly
  what CPR bands, confluence boxes, drawings, Renko/P&F need. Migration is mostly mechanical
  (`addXSeries(o)` → `addSeries(XSeries,o)`, `setMarkers` → `createSeriesMarkers`); the UMD/standalone
  CDN `<script>` pattern survives, so build CPR **once** on v5 primitives, not twice.
- Kill `preserveAspectRatio="none"` everywhere; real viewBoxes.

---

## 8. Ranked priorities (merged from the four panels)

Effort: S ≤½d · M 1–2d · L 3d+. CPR data already exists, so the CPR rows are *draw*, not *compute*.

| # | Idea | Fixes | Impact | Effort | Default |
|---|---|---|---|---|---|
| 1 | One chart + overlay registry (collapse 4 panes / 7 tabs) | stretch + stranded strategies | H | M | — |
| 2 | Tall responsive non-stretched sizing (autoSize) | the "stretched" look | H | S | — |
| 3 | CPR Spine ribbon (D/W/M, regime-tinted) | CPR finally drawn; signature | H | M | W on |
| 4 | CPR U/∩ reversal markers | reversal at a glance | H | S | on |
| 5 | CPR confluence slab | S/R magnet | H | S | on |
| 6 | CPR coiled-spring highlight | pending-move signal on chart | H | S | when present |
| 7 | Strategy colour+glyph grammar | "same colour = 3 things" | H | S | — |
| 8 | Self-colouring legend rail + plain labels/tooltips | jargon + show/hide UX | H | M | — |
| 9 | Plain-English "Read:" line (MEP+CPR+RS) | instant "what's going on" | H | S | on |
| 10 | DVPT/MEP footprint on candles | positioning where it happened | H | M | DVPT on |
| 11 | MA/EMA + VWAP / anchored-VWAP | table-stakes (none today) | H | S | 50/200 on |
| 12 | Smart default-on set | avoids spaghetti | H | S | — |
| 13 | Reusable `hermes-charts.js` engine + JSON contract | site-wide consistency | H | M | — |
| 14 | Upgrade v4 → v5 (panes + primitives) | build CPR/drawings once | H | M | — |
| 15 | Chart-type dropdown (native + Heikin Ashi + hollow) | Ramana's taxonomy | M | M | Candles |
| 16 | Indicators section (+add menu) | Ramana's taxonomy | M | M | — |
| 17 | RS docked pane / 0–100 band lane | RS next to price | M | M | off |
| 18 | Rich crosshair readout (plain, active-only) | hover = teaching moment | M | S | on |
| 19 | Simple ⇄ Detailed switch (data-first tables behind it) | novice + power user | M | M | — |
| 20 | Log-scale toggle | multi-year readability | M | S | off |
| 21 | Fix `preserveAspectRatio="none"` site-wide | distortion everywhere | M | S | — |
| 22 | Drawings palette (trendline/Fib/rect/text/measure) | Ramana's request | H | L | — |
| 23 | Renko / Point & Figure | Ramana's type list | M | L | off |
| 24 | Site-wide rollout (RRG/RS/ratio/sparklines onto engine) | whole-site coherence | M | L | — |

---

## 9. Phasing (each ships independently, no-regression, update PROJECT_STATE on ship)

- **Phase 0 — Foundation & un-stretch** (#1,2,13,14,7): one responsive chart on a shared v5 engine +
  colour tokens + control-bar shell. *The stretch is gone after this.* ~2–3d.
- **Phase 1 — CPR made visual** (#3–6,9): Spine, reversals, confluence, coil, Read line. ~2d.
- **Phase 2 — Controls & overlays** (#8,10,11,12,15,16,17,18,19): four-family control bar populated;
  DVPT/MEP footprint; MAs/VWAP; RS lane; chart-type dropdown; indicators section. ~3–4d.
- **Phase 3 — Drawings, exotic types, rollout** (#20,21,22,23,24): drawing tools; Renko/P&F;
  site-wide engine adoption. ~4–6d (drawings dominate).

---

## 10. Open items

- ✅ **GATE RESOLVED — Path B (build our own on lightweight-charts).** Ramana: "we won't copy what
  TradingView gives, we only get inspired" → our own curated engine; licensing non-issue (Apache-2.0).
  (Revisit only if Patearn later wants wholesale TradingView adoption — currently ruled out.)
- ✅ All FYERS screenshots received (chart types · indicator library · drawings/Fib/Gann · patterns ·
  Elliott · cycles · projections · volume-based · measurers) — folded into §3/§6.
- Sequencing = **Foundation-first** (Phase 0 → 1) unless CPR-first is preferred. Awaiting Ramana's "start".
- Curate T2/T3 drawings (§6) to the tools Ramana actually uses — confirm later.
- Drawing persistence storage = a SQLite table per user×symbol (Phase 3).

## 12. PIVOT — FYERS parity means TradingView Advanced Charts (decision pending)

Ramana's screenshots (chart-type list, searchable indicator library, drawings incl. pitchforks/Gann/
full Fib suite, pattern auto-detect) are the **TradingView Advanced Charts** library — the same engine
FYERS/Zerodha/Upstox use. **lightweight-charts cannot reach this** (no drawing tools, no indicator
library, no pitchforks/Gann/Fib, no magnet, no persistence — by design). Verified via web research.

**Licensing catch (the gate):** Advanced Charts is *free* but the free grant is for **companies, public
web apps** — *not* personal/internal/hobby use; requires an application → private GitHub repo + a visible
TradingView attribution logo. Hermes is a private personal tool today; Patearn going public/company would
satisfy it. The Apache-2.0 **lightweight-charts** is the only one cleared for personal/private use.

**Chart-type catch:** Renko / Kagi / Point & Figure are *Trading Platform*–exclusive (heavier library),
not base Advanced Charts. Heikin Ashi / Hollow / Line Break / Area / Baseline are in the standard set.

**Our 5 proprietary overlays on Advanced Charts:** JS **custom studies** (`custom_indicators_getter`;
band/histogram/line plots, multi-pane) + `createShape`/`createMultipointShape` for markers/lines, and/or
server **UDF `/marks` + `/timescale_marks`** for pattern auto-detection from `cpr_signals`/Wolfe/DVPT.
Datafeed = **UDF** REST adapter over our SQLite OHLC (`/config`,`/symbols`,`/search`,`/history`,`/time`,
`/marks`,`/timescale_marks`). Drawing persistence = a small save/load REST adapter → SQLite.

### The decision (Ramana's call — product posture drives it)

| Path | What you get | Licensing | Effort | Best if |
|---|---|---|---|---|
| **A — Adopt TradingView Advanced Charts** | True FYERS parity: all chart types, drawings, Fib, Gann, pitchforks, indicator library, magnet, persistence + our 5 studies on top | Free **only** under company/public-app framing + attribution logo; app → repo. Renko/Kagi/PnF need Trading Platform build | UDF adapter S–M · 5 studies M each · persistence M · library integ S | Patearn becomes a public/company product and you want everything in one place |
| **B — Stay lightweight-charts (proprietary-focused)** | The CPR Spine + DVPT/MEP/RS/Wolfe done beautifully + a curated hand-built subset of indicators/drawings; **no** Gann/pitchfork/full-Fib/Renko parity | Clean Apache-2.0, fine for personal/private use | The Phase 0–3 plan in §9–10 (no TradingView dep) | Hermes stays a private personal tool; you keep FYERS for heavy drawing |

**Note worth saying once:** FYERS already gives you the full drawing/Gann/Fib arsenal for free. Hermes'
unique value is the *proprietary data lens* (DVPT/MEP/CPR/RS) that FYERS lacks — that works on **either**
library. Path B nails that edge cheaply; Path A is for when you want FYERS-in-one-place under a public
Patearn. Recommendation deferred to the posture answer.

Integration plan if Path A (verified, ranked): license/repo (S, **license risk**) → UDF adapter (M) →
widget mount (S) → drawing persistence adapter (M) → CPR spine study (M) → DVPT+MEP studies (M) →
RS study (S–M) → Wolfe shapes (M) → pattern-on-select via `/marks` (S) → [opt] Trading Platform for
Renko/Kagi/PnF (M).

## 13. Auto-pattern detection (harmonics / Elliott) — capability assessment (2026-06-24)

Ramana asked: can we auto-detect harmonic patterns + Elliott waves, screen the universe, and backtest
reliability — on daily-only data? Code-grounded audit verdict: **~60–70% already exists and is reusable;
a focused build, not a redesign.** (This is really a NEW STRATEGY LANE — sibling to `wolfe-wave-design.md`
/ `cpr-strategy-design.md`; spin a dedicated design doc when greenlit. On the chart it is the
"auto-detect patterns when I select" overlay — auto-drawn, vs the manual T1–T3 drawing tools in §6.)

**HAVE & reusable**
- **Swing/pivot/zigzag engine** — ATR-normalized zigzag + Fibonacci-confluence in the Wolfe detector
  (`src/automation/wolfe.py` ~94–191; `fib_zones` ~435–456; research twin `research/wolfe_waves/`).
  Swing-extraction + Fib-zone primitives are copy-paste ready. Partial-wave (forming) detection already
  exists (Wolfe 1–4 locked, point-5 zone projected) → the same mechanism yields a harmonic's projected
  **D "potential reversal zone"** (the "catch it forming, down the stream" ask).
- **Universe-wide nightly scanner** — proven by DVPT/CPR/ignition (`signals.py`, `cpr_signals.py`,
  `ignition.py`): per-symbol compute → signal table → screener column-group + `/dash` page + systemd
  timer. A `harmonic_signals` scanner slots in identically.
- **Backtest harness** — `ignition_backtest.py` (no-look-ahead next-open entry, MFE/MAE, forward returns
  1/3/6/12/24m, survivor-inclusive, point-in-time) + the Wolfe research backtest → extend to
  `harmonic_outcomes` to PROVE reliability per pattern-type × timeframe.
- **Data** — `bhavcopy_rows` (~2,000 equities, 5y+ daily, split-adjusted) + `bars_weekly`/`bars_monthly`
  resampled nightly. Daily is the CORRECT granularity for positional harmonics on D/W/M; **no intraday
  needed** (would only matter for intraday scalping). No intraday data (acknowledged; may buy later).

**GAP to build**
- **Harmonic XABCD ratio-template library** (Gartley/Bat/Butterfly/Crab/Cypher/Shark/Three-Drives) +
  per-type validator on the existing zigzag — generalize Wolfe's Wolfe-specific `_classify()`. ~400–500 ln.
- **`harmonic_signals.py` nightly scanner** (D/W/M) + table + screener/`/dash` surface + timer. ~400 ln.
- **`harmonic_outcomes` backtest** extension. ~200 ln. **Multi-TF zigzag** (Wolfe is D-only today).

**Honest split & recommendation**
- **Harmonics = YES, strong.** Precise Fib ratios → rule-based, automatable, backtestable. Lead here.
- **Elliott = weak, DEFER.** No code; auto-counting is subjective/ambiguous and fragile out-of-sample;
  "predict before it happens" reliably via Elliott is dubious. Heuristic labeler only later, exploratory —
  do NOT gate harmonic work on it.
- **The reliability edge (our moat):** detection is the cheap part. Value = (1) backtest which patterns/
  ratios/TFs actually have forward edge on OUR universe, and (2) **fuse** the harmonic D-zone with our
  proprietary **DVPT accumulation + RS strength + CPR confluence** — a harmonic completing where
  institutions are accumulating is the "stronger, more reliable" signal nobody else can compute.

## 14. Build log

**Phase 0 + Phase 1 (CPR Spine) — BUILT & verified, 2026-06-24 (commit `7dee885`).** Isolated new files
(no `dashboard.py` edit — parallel-held):
- `src/web/static/hermes-charts.js` — the reusable engine on lightweight-charts v4.1: ONE responsive
  chart (`ResizeObserver` width-follow — kills the stretch), the four-family control bar (chart-type
  dropdown · proprietary strategy chips · indicator chips · drawing tools + magnet/hide-all stubs), an
  overlay registry (per-item show/hide, self-colouring chips), a docked DVPT sub-pane (overlay price
  scale — collapses the old 4-chart stack), MAs, zones, crosshair readout, and the **CPR Spine** drawn
  as an `ISeriesPrimitive` canvas layer: stepped translucent amber band (BC↔TC) + dashed pivot, regime
  tint, brighter solid "coil" when compressed, full-width confluence slab, and U/∩ reversal markers.
- `src/web/chart_view.py` — DB-free: `cpr_segments()` (`cpr_signals` rows → segments), `confluence()`,
  `render_stock_chart()` (JSON contract + engine boot HTML). Unit-smoke-tested (no DB).
- `src/web/static/_chart_demo.html` — standalone harness with synthetic uptrend→pullback→coil→breakout
  data; **rendering verified via headless preview** (one un-stretched chart, the CPR Spine reads as the
  signature, no console errors).

**Decision (build-time):** built on **lightweight-charts v4.1** (primitives available; the app's known-good
pin) rather than upgrading to v5 first — lower risk for a verified result; v5's native panes are a later
optimization, not a blocker. The CPR band primitive is contained, so a v5 swap stays localised.

**Live wire-in SHIPPED via snippet-injection (commit `bb8ae77`) — verified on real data.** Rather than
swap the whole chart (dashboard.py contended), the CPR Spine attaches to the EXISTING `/dash/stock` chart
via `src/web/cpr_overlay.py` (mirrors `wolfe_overlay.py`): a `/dash/cpr/overlay` JSON endpoint
(`cpr_signals`→segments, reusing `chart_view`) + a self-contained SNIPPET that draws the Spine primitive
on `window.__wfpc` and injects a chip + D/W/M toggle (default ON). Hooks = 2 additive lines in `main.py` +
3 in `dashboard.py` (import · snippet · `window.__wfcandle`; **hardened** — the Spine binds to the real candle series for exact price mapping with no time-axis pollution, and skips off-axis segments so it stays clean across the chart's interval/range controls — verified cycling D/W/M with zero console errors), **left uncommitted** (Wolfe protocol — those files carry a parallel UI session's
edits). **Verified by running the app locally on `data/hermes.db` (sym=ALPHA): endpoint HTTP 200,
199 D / 39 W / 9 M segments, 37 coiled, BULL_U/BEAR_INVU detected, controls injected, zero console
errors.** ✅ **DEPLOYED to the VPS (2026-06-24)** — isolated files scp'd LF-clean (`git show … | ssh`), the 5 hooks added IN-PLACE by anchor (never overwriting the contended files), backups `*.bak-cpr`, `hermes-api` restarted behind an auto-rollback guard → **health 200, verified on real symbol ACC** (overlay returns real segments to 2004; stock page 200 + snippet wired). Re-apply the 5 hooks if a parallel session overwrites the VPS dashboard.py/main.py.

**Phase 2 started — MA 20/50/200 overlay BUILT + DEPLOYED (2026-06-24, commit `2423ce8`).**
`src/web/indicators_overlay.py` (NEW, isolated, SNIPPET-only — no router/endpoint): EMA 20/50/200 drawn
as a canvas **primitive** on the existing candle series (reading `window.__wfdata`, the page data), so it
never pollutes the shared time axis and degrades cleanly on resample/zoom — same trick as the CPR Spine.
Toggle chips (50/200 default ON), coexists with the CPR Spine. 3 additive `dashboard.py` hooks (import ·
`{_MA_SNIPPET}` · `window.__wfdata=DATA`) added in-place on the VPS (backup `*.bak-ma`), `hermes-api`
health 200, **verified wired on the ACC page**. Fills the table-stakes gap (the live chart had no MAs).
Next Phase-2 candidates: MEP/RS on-chart overlays, VWAP/anchored-VWAP, the chart-type dropdown; then the
full one-chart engine swap (the "un-stretch") when dashboard.py is free.

**MEP accumulation/distribution tint BUILT + DEPLOYED (2026-06-24, commit `6a78341`).**
`src/web/mep_overlay.py`: `/dash/mep/overlay` serves contiguous **smoothed-phase** bands
(`mep_signals.mep_state_smooth`); the SNIPPET tints the price-chart background green (accumulation) /
red (distribution) as a primitive on `window.__wfcandle`. Default OFF (opt-in lens), fetch-on-first-toggle,
chip joins the existing chip row. 4 in-place hooks (2 `main.py` router, 2 `dashboard.py`), backups
`*.bak-mep`. Verified: health 200, endpoint 200, snippet wired on ACC.
**Deploy hardening (lesson):** the first MEP restart tripped a *false* "unhealthy" (the 3s health wait was
shorter than the ~5–7s restart) → the guard auto-rolled-back harmlessly. Re-deployed with a **pre-restart
`import src.main` check + a health-retry loop (≤20s)** — now the standard overlay-deploy guard.
**Known polish:** the MEP chip joined the MA/indicators row (load-order); unifying all overlays into one
shared chip rail is the next cleanup as overlays multiply.

**Ramana's CPR corrections BUILT + DEPLOYED (2026-06-24, commit `bfe6093`).** He confirmed the CPR is
correct + he's happy with it; corrections to behaviour: (1) **CPR degree follows the chart's interval** —
daily chart → daily CPR, weekly → weekly, monthly → monthly (the snippet hooks the existing `[data-ptf]`
buttons; quarterly hides); **no** independent CPR timeframe toggle. (2) **U/∩ marker on the MIDDLE candle**
(C1, the valley/peak): the pattern is flagged in `cpr_signals` on **C0** (the signal bar), and the flagged
segment's `t0` IS C1's date, so the marker uses `s.t0` (verified vs data — BEAR_INVU marker at 2024-01-15,
not signal-bar 2024-01-16; **100% of weekly segments align to the weekly candle axis**). (3) **CPR default
OFF** — it's a proprietary strategy you call up (opt-in, fetch-on-first-toggle). (4) CPR + MEP grouped in a
labelled **"Strategies"** chip group (MA stays "Indicators"; **MA still default-on** — a standard indicator,
flagged for confirmation). The **full** four-family grouping + Wolfe/DVPT integration is Ramana's planned
**UI-architecture-overhaul session** (deliberately deferred — not now). The full `render_stock_chart()` engine swap (one
chart replacing the 4-pane stack) remains the eventual Phase-0 rebuild when dashboard.py is free.

**Remaining for Phase 0/1:** wire `render_stock_chart()` into `/dash/stock` + mount `/static` (one call
each) when `dashboard.py`/`main.py` are free; add the server query pulling `cpr_signals` rows per symbol;
add the interval (D/W/M/Q) resampler + log-scale toggle. Then Phase 2 (full control bar populated) and
Phase 3 (drawing engine: magnet + hide-all + persistence).

## 11. Key file paths

- Focal chart: `src/web/dashboard.py` ~7060–7325 (sync 7204–7230 · resample 7246–7280 · readout
  7299–7320 · `_LWC_CDN` 5925 · `_RS_OVERLAY_JS` 5935 · `_RATIO_CHART_JS` 7331 · `_cpr_stock_panel` 2529).
- Overlay pattern to generalize: `src/web/wolfe_overlay.py`.
- CPR data: `cpr_signals` in `src/core/db.py`; engine `src/automation/cpr_signals.py`; design `docs/cpr-strategy-design.md`.
- RS-band data: `src/web/rsband_view.py` + `src/automation/rsband.py`.
- Other chart consumers to migrate: `src/web/cockpit.py`, `rrg_view.py`, `mini_rrg.py`.
