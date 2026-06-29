# L3 — Site-wide Chart Inventory & Triage

> **Lane L3 — Charting site-wide.** Created 2026-06-29 (HEAD `05cdeae`). This is the
> backlog-item-1 deliverable: every live chart surface, the JS each uses, whether it is
> **bounded** (fits its container, no overflow, retina-crisp), and the L3 action for each.
> Companion: `docs/chart-redesign-design.md` (§14 resume), `docs/harmonic-pattern-design.md`,
> memory `charting-overhaul-cpr-spine.md`.

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
| 7 | Drawing engine + magnet + persistence | **DONE** (§6); SQLite persistence = future tier |
| 8 | Harmonic + Wolfe overlays still draw on bounded engine; `__wfpc` intact | **verify in-browser** (next) |
| 9 | Final in-browser pass — screenshot every surface | **next** |

The headline: **the L3 mission was largely already shipped in S41/42/48/49.** L3's net-new value
this session is the *audit + triage + decision record* (this doc), the `hermes-charts.js`
retirement, the harness gap-fix (add `/dash/harmonic/overlay` to the overlay sweep), and a fresh
**in-browser verification** that every overlay still draws on the bounded `__wfpc` after the RRG
landing in `05cdeae`.
