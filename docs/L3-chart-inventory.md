# L3 — Site-wide Chart Inventory & Triage

> **Lane L3 — Charting site-wide.** Created 2026-06-29 (HEAD `05cdeae`). This is the
> backlog-item-1 deliverable: every live chart surface, the JS each uses, whether it is
> **bounded** (fits its container, no overflow, retina-crisp), and the L3 action for each.
> Companion: `docs/chart-redesign-design.md` (§14 resume), `docs/harmonic-pattern-design.md`,
> memory `charting-overhaul-cpr-spine.md`.
> **Wave-2 addendum: §8–§11 below** (drawing persistence · families-where · multi-TF harmonic · perf).

---

## WAVE 3 (2026-06-29) — professional analyst tools (§12–§16)

All in `stock_chart.py` (the `/dash/stock` workstation), all **DESCRIPTIVE-only**.

### §12. Fib extension + Fib retracement (Wave-3 item 1)
- **Fib retracement** (existing, `fib`, amber): 0/0.236/0.382/0.5/0.618/0.786/1 between two pivots.
- **Fib EXTENSION** (NEW, `fibext`, purple, the `Fx` tool): 0/0.618/1/1.272/1.618/2/2.618 — projects
  *targets beyond* a measured move; levels past 1.0 dashed. Both: magnet-snap to pivots, editable
  handles, persisted via `drawings_store` (the JSON blob holds the new type — no schema change).

### §13. Measure + annotate (Wave-3 item 2)
- **Measure** (`measure`): now shows **Δprice + Δ% + Δbars + Δcalendar-days** between the two clicks
  (was price+% only). `barsBetween()` counts resampled bars; `calDays()` = calendar gap.
- **Text annotation** (`text`, existing): click to drop a note; styleable + persisted.

### §14. Indicators — Bollinger + ATR bands (Wave-3 item 3)
- **Bollinger Bands** (`bb`, 20, 2σ): upper/mid/lower around a 20-period SMA. Purple.
- **ATR bands** (`atr`, close ± 2×ATR-14): volatility envelope around the close. Green.
- **Anchored-VWAP** (`avwap`): already existed (anchor at a clicked bar) — noted, not rebuilt.
- All toggle from the **Indicators** family in the four-family rail; recomputed on resample; the
  legend carries the "volatility envelope (descriptive)" caveat. **No buy/sell language.**

### §15. Drawing manager (Wave-3 item 4)
The `≡ list` button opens a floating panel:
- One row per drawing: **colour picker** (`<input type=color>`) + **width selector** (1/1.4/2/3px) +
  **delete-one** (×) + click-name-to-select-on-chart.
- **Export** (download all drawings as `drawings_<sym>.json`) + **Import** (load from a JSON file,
  replaces current, capped 500, never-throws). Per-drawing `col`/`w` persist via the existing
  `drawings_store` JSON blob (schema-flexible — no migration).

### §16. Mobile chart QA (Wave-3 item 5)
- **Chart bounds at 380px:** forced into a 380px container the chart host shrinks to ~250px with
  **no chart-level overflow** (the `max-width:1280px` + width ResizeObserver). Verified in-browser.
- **`@media(max-width:640px)`** shortens the chart to `clamp(300px,52vh,460px)` so it isn't
  awkwardly portrait on a phone; host `touch-action:none` lets lightweight-charts own pinch/drag.
- The four-family rail wraps (`flex-direction:column` + per-row `flex-wrap`).
- **HAND-OFF (not L3):** the residual *page-level* horizontal overflow at 380px is from
  **`NAV.ngcrumb`** (breadcrumb chrome) + a **dashboard.py layout `TABLE`** wrapping the chart —
  both frozen, outside L3. None of the overflow is from the chart host or rail (`anyMine=0`).
  → L1/L2 mobile hand-off (L2 is already doing dossier-mobile work, `b239f90`).

### §17. Wave-3 verification (item 6)
In-browser (dedicated tab, live ACC + WIPRO): every new tool/indicator present; Bollinger+ATR draw;
the manager shows per-drawing colour/width/delete + export/import on server-loaded drawings; **8
overlays/indicators toggled together** (DVPT/CPR/Wolfe/Harmonic/RS/VWAP/Bollinger/ATR) →
`window.__wfpc`+`__wfcandle` intact, 7 canvases, **ZERO console errors**. Screenshots captured.
Commits `7b49e4e` (tools+indicators+manager) + `8b39551` (mobile).

---

## WAVE 2 (2026-06-29) — addendum

### §8. Drawing persistence → server (Wave-2 item 1, SHIPPED)
The on-chart drawing engine now persists **server-side**, so drawings follow the user across
device + browser (not just a reload in the same one).
- **`src/web/drawings_store.py`** (NEW, owned) — `GET`/`POST /dash/drawings?sym=X` over a
  module-owned `chart_drawings` table (`CREATE IF NOT EXISTS` in the module; `db.py` untouched,
  same pattern as `harmonic_signals`). Whole-set replace, count+size caps (500 items / 256 KB),
  empty-list deletes the row, never 500s the chart. Router self-mounts via
  `wolfe_view.include_router` (no `main.py` edit, redeploy-durable).
- **`stock_chart.py` `makeDraw()`** — on load, adopts the server copy if non-empty (server wins
  over the local cache; first-time local→server migration if the server is empty); `save()`
  debounce-POSTs (600 ms coalesce) + flushes on `beforeunload`. `localStorage` stays as the
  instant/offline cache.
- **In-browser verified (live, WIPRO):** seeded 2 drawings on the SERVER with `localStorage`
  cleared (= a different session), hard-reloaded → the engine fetched them, rehydrated
  `localStorage`, and DREW them (blue trendline + purple hline@250 visible on candles). Round-trip
  also proven via TestClient + live curl. Commit `6e3b22d`.

### §9. Chart families — where they are / aren't (Wave-2 item 2)
The chart-type family controls (Candles / Hollow / Heikin-Ashi / Line / Area / Renko / Kagi;
P&F flagged "soon") live in **`stock_chart.SNIPPET`**, which renders on **`/dash/stock` only**.

| Surface | Renders a price candle chart? | Families available? | Why |
|---|---|---|---|
| `/dash/stock` | **YES** (the workstation) | **ALL** (Candles/Hollow/Heikin/Line/Area/Renko/Kagi; P&F soon) | the canonical chart |
| `/dash/rrg` | No — RRG scatter (SVG) | n/a | not a time-series price chart |
| `/dash/ratio` | a single ratio LINE (frozen `dashboard.py`) | no | a ratio line, not OHLC; families don't apply |
| `/dash/rs` | tables + sparklines | n/a | no primary price chart |
| `/dash/wolfe`, `/dash/harmonic` | scanner tables → click into `/dash/stock` | inherit (on the stock chart) | the overlay draws on the stock chart's families |

**Decision:** chart-type families belong to the **stock workstation** — it is the only surface in
L3's modules that renders OHLC bars, so "families site-wide" = *available wherever a price candle
chart renders, which is `/dash/stock`*. The other surfaces are single-purpose (scatter / ratio
line / tables); adding a Renko/Kagi selector to a ratio line or an RRG scatter would be a control
that does nothing. No new surface to roll families onto within L3's ownership. (`/dash/ratio`'s
line chart is in frozen `dashboard.py` — even a Line/Area toggle there is an L1 change, not L3.)

### §10. Multi-TF harmonic (Wave-2 item 3, VERIFIED — no regression)
Harmonic detection runs **Daily / Weekly / Monthly** consistently — confirmed live:
- `/dash/harmonic/overlay?sym=ACC&tf=d` → Gartley+Crab BEAR FORMING (4 pts, +PRZ)
- `…&tf=w` → Butterfly BULL CONFIRMED (5 pts)
- `…&tf=m` → Crab BULL FORMING (4 pts, +PRZ)
The `stock_chart.SNIPPET` re-fetches W/M when the price interval crosses into them (`harmTf`
guard) and re-snaps point dates onto the resampled bars. **In-browser verified (ACC):** Harmonic
chip ON + interval = Weekly → chip drew on the weekly resample, `window.__wfpc` intact, no chart
console errors. DESCRIPTIVE-only (read-by-side caveat in the legend). No TF regression found.

### §11. Perf — chart-JS first-paint (Wave-2 item 5, MEASURED → frozen-file hand-off)
**Measured (live, ACC, Performance API):** the lightweight-charts lib script is **cached
(transferSize 0), 9 ms duration**, loads at startTime 446 ms; domInteractive 562 ms,
DOMContentLoaded 813 ms. The lib `<script>` is `async:false, defer:false`.
- The lib is **NOT the bottleneck** (9 ms cached). The real cost is chart *construction*
  (5416 bars → `setData` on 7 series) in `boot()`.
- The lib `<script src=…>` tag for `/dash/stock` is emitted in **frozen `dashboard.py`** (~line
  7162/8275) — L3 cannot add `defer`/`async` to it.
- Deferring `boot()` (e.g. `requestIdleCallback`) would risk the `window.__wfpc` contract that the
  CPR/MA/MEP/RS/Wolfe/Harmonic overlays bind to synchronously after DOMContentLoaded.
- **Verdict:** the meaningful lever (defer the lib tag) is a **frozen-`dashboard.py` hand-off to
  L1**; deferring boot in-SNIPPET isn't worth the contract risk for a 9 ms cached lib. Documented,
  not forced. (If L1 ever adds `defer` to the lib tag, the SNIPPET already guards
  `if(!window.LightweightCharts)` so it degrades gracefully.)

---

## 0. The two chart engines that exist today

| Engine | File | Used by | Bounded? | Owner |
|---|---|---|---|---|
| **`stock_chart.SNIPPET`** — the "one chart" rebuild (lightweight-charts v4) | `src/web/stock_chart.py` (L3-owned) | `/dash/stock` | **YES** — `height:clamp(420px,62vh,760px)` + `max-width:1280px` + a **width+height ResizeObserver** that calls `pc.applyOptions({width,height})`, + fullscreen. Retina-crisp via lightweight-charts' own bitmap canvas. | **L3** |
| **`hermes-charts.js` + `chart_view.render_stock_chart()`** — the original reusable "CPR Spine" engine | `src/web/static/hermes-charts.js`, `src/web/chart_view.py` (L3-owned) | **NOTHING** — never wired; `/static` is not even mounted (see §3). `cpr_overlay.py` imports `chart_view` only for the pure `cpr_segments()`/`confluence()` transforms, **not** the renderer. | n/a (dead engine) | **L3** |

**Key fact:** the live stock chart does NOT use `hermes-charts.js`. The `stock_chart.SNIPPET`
superseded it (Session 42, commit `ad49c30`). `hermes-charts.js` is **dead code** — see §3 triage.

---

## 1. Every live chart surface (inventoried 2026-06-29, live VPS verified)

| Route | What it draws | Rendering tech | File (owner) | Bounded? |
|---|---|---|---|---|
| **`/dash/stock`** | Price candles + DVPT/Delivery/Traded sub-panes + four-family rail + all strategy overlays (CPR/MA/MEP/RS/Wolfe/Harmonic) + drawing engine | lightweight-charts v4 via `stock_chart.SNIPPET`; overlays draw on `window.__wfpc`/`__wfcandle` | `stock_chart.py` (**L3**) + overlays | **YES** (clamp+RO, fullscreen) |
| **`/dash/ratio`** | Index/sector ratio line vs Nifty + MA50/MA200 + cross markers + range bar | lightweight-charts v4 via `_RATIO_CHART_JS` | `dashboard.py` ~7159 (**L1 frozen**) | **Partial** — fixed `height:300`; ResizeObserver only `applyOptions({})` (width-follow via lib, no explicit width/height/retina re-apply). Width-responsive but not the bounded primitive. |
| **`/dash/rrg`** | Relative-Rotation-Graph scatter (4 quadrants, tails, animation/timeframe-native) | **inline SVG**, `viewBox="0 0 760 480" width="100%" style="max-width:760px"` (NO `preserveAspectRatio="none"`) | `rrg_view.py` ~130/611 (**L1 frozen** — landed in `05cdeae`) | **YES — self-bounded.** Proportional scale (fixed-aspect viewBox + max-width); does not stretch. No L3 action needed (see §4). |
| **`/dash/rs`** | RS tables + per-row RS sparklines (12m→1m slope trajectory) | inline SVG sparkline `_rs_spark` | `dashboard.py` ~1037 (**L1 frozen**) | sparkline (small fixed viewBox) — fine at size |
| **`/dash/cpr`** | CPR signals table (no large chart; the CPR draws as an *overlay* on `/dash/stock`) | table + `cpr_overlay.SNIPPET` on the stock chart | `dashboard.py` ~3414 + `cpr_overlay.py` | n/a (table) / overlay bounded with stock |
| **`/dash/wolfe`** | Wolfe scan rows → link into `/dash/stock`; overlay draws on the stock chart | `wolfe_view.py` page + `wolfe_overlay.SNIPPET` on `window.__wfpc` | `wolfe_view.py`, `wolfe_overlay.py` (**L3**) | overlay bounded with stock |
| **`/dash/harmonic`** | Harmonic XABCD scanner table → rows into `/dash/stock`; overlay draws X-A-B-C-D+PRZ | `harmonic_view.py` page + harmonic draw inside `stock_chart.SNIPPET` (`/dash/harmonic/overlay` feed) | `harmonic_view.py` (**L3**), draw in `stock_chart.py` | overlay bounded with stock |
| **Sparklines** (markets/leaders/conviction tables, OI, participants) | tiny trend lines in table cells | inline SVG, several with `preserveAspectRatio="none"` | `dashboard.py` ~2804/2828/4156, `cockpit.py` ~531, `participants_view.py` ~64 (**L1 frozen** except participants_view) | small cells — stretch is cosmetic at sparkline size, not a "broad sides" regression |
| **`/dash/_ui`** (showcase) | demo chart placeholder | static SVG polyline `preserveAspectRatio="none"` in a `chart_host` | `ui_kit.py` ~384 (**L2 frozen**) | demo only |

### The chart-overlay endpoints (all 200 live, in the regression sweep)
`/dash/cpr/overlay` · `/dash/mep/overlay` · `/dash/rs/overlay` · `/dash/wolfe/overlay` · `/dash/harmonic/overlay`
— all bind to `window.__wfpc`/`__wfcandle` on the bounded stock chart. **Contract `window.__wfpc` is the law** (every overlay depends on it).

---

## 2. The `preserveAspectRatio="none"` stretch — where it actually lives

The historical "narrow top, broad sides" stretch came from SVGs with `preserveAspectRatio="none"`,
which lets a fixed viewBox distort to any box. Current occurrences:

| File | Line | Context | Owner | Verdict |
|---|---|---|---|---|
| `dashboard.py` | 2804, 2828, 4156 | OI sparkline, mini-spark, `_curve_svg` equity curve | **L1 frozen** | sparkline/curve cells — small; cosmetic. **Hand-off to L1** if Ramana wants the equity curve bounded. |
| `cockpit.py` | 531 | 92×16 table sparkline | **L1 frozen** | sparkline size — fine. |
| `participants_view.py` | 64 | signed-series sparkline | not L3-owned (Lane unclear) | sparkline — fine. |
| `ui_kit.py` | 384 | `/dash/_ui` demo polyline | **L2 frozen** | demo only. |

**Conclusion:** the *real* chart (the stock price chart) is already de-stretched (the
`stock_chart.SNIPPET` clamp + width+height RO killed it in S42). The remaining
`preserveAspectRatio="none"` are all **sparkline-scale** cells in **frozen** files — not a
"broad sides" regression on a primary chart, and **not L3-owned**. Documented as L1/L2 hand-offs;
L3 does not touch frozen files.

---

## 3. `hermes-charts.js` triage — RETIRE (documented dead, kept inert)

- **Confirmed dead:** `chart_view.render_stock_chart()` (the only caller of `hermes-charts.js`)
  is referenced **nowhere** in the wired app. `/static` is **not mounted** in `main.py`
  (`grep StaticFiles src/main.py` → empty), so `GET /static/hermes-charts.js` would **404**.
  The live stock chart uses `stock_chart.SNIPPET` instead.
- **Decision: RETIRE, don't revive.** The bounded engine site already exists and is *better*
  than `hermes-charts.js` (it has the four-family rail, drawings, fullscreen, the live overlay
  contract). Reviving `hermes-charts.js` as "the one engine" would mean re-implementing all of
  that and re-wiring `/dash/stock` — high risk, zero user gain, and it would fight the frozen
  `dashboard.py` wiring. **The single bounded primitive IS `stock_chart.SNIPPET`** (§0).
- **Why keep the file (not `git rm`):** `chart_view.py`'s `cpr_segments()`/`confluence()`
  transforms are still imported by the live `cpr_overlay.py`. The renderer half
  (`render_stock_chart`) + `hermes-charts.js` + `_chart_demo.html` are inert but harmless, and
  removing `hermes-charts.js` risks nothing functional yet loses the reference implementation of
  the "CPR Spine" design. **Action taken:** a deprecation banner added to the top of
  `hermes-charts.js`, `_chart_demo.html`, and `chart_view.render_stock_chart()`'s docstring so no
  future session mistakes it for live code. No dead `/static` ref exists to remove (it was never
  mounted). If Ramana later wants the tree cleaned, `git rm` of `hermes-charts.js` +
  `_chart_demo.html` + `render_stock_chart()` is a safe one-commit follow-up.

---

## 4. RRG / RS / ratio — bounded-engine rollout status

- **RRG (`/dash/rrg`)** — a major animated/timeframe-native RRG landed in `rrg_view.py` (`05cdeae`,
  **L1**). It renders its own SVG with a **fixed-aspect viewBox + `max-width:760px`** (no
  `preserveAspectRatio="none"`) → **already self-bounded** (scales proportionally, never stretches).
  **L3 action: NONE.** Do not duplicate or wrap it — it is L1-owned and correct. Documented, move on.
- **Ratio (`/dash/ratio`)** — `_RATIO_CHART_JS` in **frozen `dashboard.py`**. Width-responsive but
  not the full bounded primitive (fixed `height:300`, RO only `applyOptions({})`). **Cannot be
  edited by L3** (L1 owns dashboard.py). **Hand-off to L1:** swap `height:300` → `clamp(...)` and
  make the RO re-apply `{width,height}` (mirror `stock_chart`). Low risk, but it is L1's file.
- **RS (`/dash/rs`)** — tables + sparklines only; no large primary chart to roll the engine onto.
  The RS *line* lens already lives as the docked RS lane **on the bounded stock chart**
  (`/dash/rs/overlay`). **L3 action: NONE.**

**Net:** every *primary* chart surface is bounded — the stock chart (L3, the primitive) and the
RRG (L1, self-bounded). The only non-bounded primary chart is `/dash/ratio`, which is in a frozen
file → L1 hand-off, not an L3 build.

---

## 5. Four-family controls — status

The four-family rail (Chart-type ▾ · Strategies · Indicators · Drawings) is **shipped and live on
`/dash/stock`** (the canonical chart workstation), built into `stock_chart.SNIPPET`:
- **Chart type:** Candles / Hollow / Heikin-Ashi / Line / Area / Renko / Kagi (P&F flagged "soon").
- **Strategies:** DVPT · Wolfe · RS · Harmonic (CPR/MEP chips inject from sibling overlays).
- **Indicators:** MA (sibling overlay) · VWAP · Anchored-VWAP · Delivery% · Traded ₹.
- **Drawings:** trend/hline/rect/Fib/measure/text + 🧲 magnet + hide-all + clear (localStorage-persisted).
- Interval (D/W/M/Q) + Range + fullscreen re-homed into the rail.

Other surfaces (RRG/ratio/rs) are **single-purpose views**, not multi-family workstations — they
have their own purpose-built controls (timeframe/range/denominator). The four-family taxonomy
belongs to the stock workstation; replicating it onto a ratio line or an RRG scatter would be
control-clutter, not consistency. **Decision: four-family rail stays the stock-chart contract;
the other surfaces keep their domain-appropriate controls.** (Documented so it is a *decision*,
not an omission.)

---

## 6. Drawing engine — status

Shipped and live in `stock_chart.makeDraw()` on `/dash/stock`:
- Tools: trendline · horizontal line · rectangle · Fib retracement · measure · text.
- **Magnet** — snaps each anchor to the nearest OHLC of the nearest bar (still draggable/overridable).
- **Hide-all** toggle + **clear** + select/edit (drag anchors, Del to remove).
- **Persistence:** per-symbol in `localStorage` (`hdraw:<sym>`). SQLite persistence is the
  documented next tier (would need a small owned endpoint; in-memory/localStorage is the current
  contract and survives reloads per-browser).

---

## 7. L3 backlog → status map

| # | Item | Status |
|---|---|---|
| 1 | Inventory every chart surface + the JS each uses | **DONE** (this doc) |
| 2 | Triage `hermes-charts.js` (revive or retire) | **DONE — RETIRE** (§3); deprecation banners added |
| 3 | Single bounded responsive primitive | **DONE — exists** (`stock_chart.SNIPPET`, §0) |
| 4 | Bounded engine onto RRG | **N/A — RRG self-bounded** (§4); coordinate read-only, no edit |
| 5 | Bounded engine onto RS + ratio | RS = N/A (no primary chart); ratio = **L1 hand-off** (frozen file, §4) |
| 6 | Four-family controls consistent across surfaces | **DONE — decision documented** (§5): rail = stock-chart contract |
| 7 | Drawing engine + magnet + persistence | **DONE** (§6) + **SQLite server persistence SHIPPED in Wave 2** (§8, `6e3b22d`) |
| 8 | Harmonic + Wolfe overlays still draw on bounded engine; `__wfpc` intact | **DONE — verified** (§8): `__wfpc`+`__wfcandle` present; wolfe/harmonic/cpr/mep overlay feeds all 200 + drawable; MA50/200 drawing on the bounded chart |
| 9 | Final in-browser pass — screenshot every surface | **DONE** (§8): fresh-checkout build re-verified `#priceChart{max-width:1280px}` 1058×620 in 1182 vp, no x-overflow, 7 canvases, zero app console errors, full four-family rail |

The headline: **the L3 mission was largely already shipped in S41/42/48/49.** L3's net-new value
this session is the *audit + triage + decision record* (this doc), the `hermes-charts.js`
retirement, the harness gap-fix (add `/dash/harmonic/overlay` to the overlay sweep), and a fresh
**in-browser verification** that every overlay still draws on the bounded `__wfpc` after the RRG
landing in `05cdeae`.

---

## 8. Fresh-checkout in-browser verification (2026-06-29, HEAD `ccbd25e`)

The `ccbd25e` commit message recorded a live-VPS (ACC) verification but left backlog items 8 & 9
marked "next". This pass **independently re-verifies the bounded contract on a fresh server built
from the current checkout** (uvicorn on `:8011`, Chrome MCP, symbol `GAMMA` — the only non-empty
symbol in the local synthetic fixture; ACC/real names live only on the VPS). Both gates ran green
first (chrome 11+4 · 31 routes + 4 overlays all 200, `HOST=local`).

**Computed-style + DOM evidence (`/dash/stock?sym=GAMMA`):**
- **Single bounded primitive:** outer wrapper `#priceChart` has **`max-width: 1280px`**; renders
  **1058×620** inside an **1182px** viewport. `document.scrollWidth (1170) ≤ innerWidth (1182)` →
  **no horizontal page overflow.** Chart right edge within viewport.
- **Retina / multi-pane:** `window.LightweightCharts` loaded; **7 `<canvas>`** (price + DVPT +
  delivery + traded sub-panes), biggest 1058×592 — lightweight-charts' own bitmap canvas = crisp.
- **Overlay contract intact:** `window.__wfpc` and `window.__wfcandle` both present (objects = the
  chart/series API refs the overlays bind to). Overlay feeds, fetched same-origin from the page:
  `/dash/wolfe/overlay` 200 (9.3KB, drawable) · `/dash/harmonic/overlay` 200 (drawable, empty
  pattern set on synthetic data) · `/dash/cpr/overlay` 200 (35KB) · `/dash/mep/overlay` 200.
  (`/dash/rs/overlay` returns an empty `[]` for GAMMA — the synthetic fixture has no Nifty-500
  universe for RS; 200 and wired, draws on the VPS per the prior pass.)
- **Overlays draw on the bounded engine (visual):** MA50/MA200 smooth lines + the DVPT baseline
  render *on* the bounded candle chart (screenshot) — proof an overlay binds `__wfpc` and draws.
- **Four-family rail complete (visual):** CHART TYPE ▾ Candles · STRATEGIES (DVPT/Wolfe/RS/
  Harmonic/CPR/MEP) · INDICATORS (MA20/50/200/VWAP/Anchored-VWAP/Delivery%/Traded₹) · DRAWINGS
  (trend/hline/rect/Fib/measure/text + 🧲 magnet + hide-all + clear) · INTERVAL · RANGE + fullscreen.
- **Console:** zero app/chart errors on the GAMMA page (the only errors captured were benign
  Chrome-extension "message channel closed" noise from a *different* tab).

**Net (Wave 1):** the bounded single-engine contract holds on a clean build of `ccbd25e`. No L3
engine build was warranted — the mission was shipped in S41/42/48/49; Wave 1 is the verification
close-out. **Wave 2 then BUILT the one real net-new feature: SQLite server-side drawing
persistence** (§8, `6e3b22d`) — drawings now follow the user across device+browser, not just a
same-browser reload. Ratio-chart bounding, the lib-`<script>` `defer` perf lever (§11), and the
sparkline `preserveAspectRatio="none"` cells remain **L1/L2 hand-offs** (frozen files, §2/§4/§11).
