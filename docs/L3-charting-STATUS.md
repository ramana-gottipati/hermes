# Lane L3 — Charting site-wide — STATUS (2026-06-29)

> Wrap note for Lane L3. Base HEAD was `05cdeae`; L3 commit = **`ccbd25e`**. Both gates PASS.
> Full inventory + triage = `docs/L3-chart-inventory.md`.

## What L3 found
The L3 mission (bounded engine site-wide · four-family controls · drawing engine ·
revive-or-retire `hermes-charts.js`) was **largely already shipped** across Sessions
41/42/48/49 (`stock_chart.SNIPPET`, the four-family rail, the drawing engine + magnet +
localStorage persistence, the harmonic + Wolfe + CPR + MEP + RS overlays on `window.__wfpc`).
L3's net-new value this session was the **audit + triage + decision record + fresh
in-browser re-verification** after the animated RRG landed in `05cdeae`.

## What L3 shipped (commit `ccbd25e`, owned files only)
1. **`docs/L3-chart-inventory.md`** — every live chart surface, the JS each uses, bounded-or-not,
   and the per-surface L3 action. (Backlog 1.)
2. **`hermes-charts.js` triage → RETIRE** — confirmed dead (`/static` never mounted;
   `stock_chart.SNIPPET` superseded it). Added DEPRECATED banners to `hermes-charts.js`,
   `_chart_demo.html`, and `chart_view.render_stock_chart()` so no future session mistakes
   them for live code. `chart_view.cpr_segments()`/`confluence()` stay LIVE (used by
   `cpr_overlay.py`). Comment/docstring-only — zero behavior change, no VPS deploy needed
   (these strings aren't served). (Backlog 2.)

## What L3 verified (no code change needed — already correct)
- **Bounded primitive (backlog 3):** `stock_chart.SNIPPET` is the single bounded engine —
  `height:clamp(420px,62vh,760px)` + `max-width:1280px` + width+height ResizeObserver +
  fullscreen. **In-browser (live ACC):** host 1280×760, **no page x-overflow**, 5416 bars,
  7 canvases, `__wfpc`/`__wfcandle` live objects.
- **RRG (backlog 4):** `/dash/rrg` (L1's `rrg_view.py`, landed `05cdeae`) is **self-bounded** —
  fixed-aspect viewBox 760×480 + `max-width` + default `preserveAspectRatio`. **In-browser:**
  760×480, ratio 1.583, no distortion, no x-overflow. **No L3 action** — read-only, do not wrap.
- **RS / ratio (backlog 5):** RS has no primary chart (tables + sparklines; the RS line lens
  is the docked lane on the bounded stock chart). `/dash/ratio` is width-responsive but not the
  full primitive — it's in **frozen `dashboard.py`** → **L1 hand-off** (swap `height:300`→clamp,
  RO re-apply `{width,height}`), not an L3 build.
- **Four-family controls (backlog 6):** live on `/dash/stock`; **decision recorded** — the rail
  is the stock-workstation contract; single-purpose surfaces (RRG/ratio/RS) keep their
  domain-appropriate controls (replicating the rail would be clutter, not consistency).
- **Drawing engine (backlog 7):** live — trend/hline/rect/Fib/measure/text + 🧲 magnet +
  hide-all + clear + select/edit, persisted per-symbol in `localStorage`. SQLite persistence =
  documented future tier (not built — marginal value vs cost for a single-user product; the
  localStorage contract already survives reloads).
- **Overlays on the bounded engine (backlog 8):** **in-browser (live ACC), all draw, zero
  console errors** — CPR Spine ribbon + U/∩ markers, DVPT institutional zone-lines (P6M/P3M/P1M)
  + DVPT histogram, MA 20/50/200, Wolfe forming-wave polyline (pts 1–5) + Fib targets
  (1.618/2.618), Harmonic pivot markers. **`window.__wfpc` contract intact after `05cdeae`.**
- **Final in-browser pass (backlog 9):** screenshots of `/dash/stock` (full chart + rail) and
  `/dash/rrg` captured; both bounded, controls + overlays working.

## Hand-offs (not L3-owned)
- **L1:** make `/dash/ratio`'s `_RATIO_CHART_JS` use the bounded primitive (clamp height +
  RO re-apply width/height/retina) — it's in frozen `dashboard.py`.
- **L1/L2:** the remaining `preserveAspectRatio="none"` sparkline/curve SVGs (dashboard.py
  2804/2828/4156, cockpit.py 531, ui_kit.py 384) — cosmetic at sparkline size; bound the
  `_curve_svg` equity curve if Ramana wants it crisp.
- **Harness:** add `/dash/harmonic/overlay?sym=ACC` to `scripts/regression_sweep.sh` OVERLAYS
  (it's a live overlay endpoint but unguarded). Flagged as a spawn_task — that file is shared
  and currently dirty from another lane, so L3 did not touch it.

## Future tiers (documented, not built)
- Drawing persistence → SQLite (cross-device); drawing tiers T2/T3 (channels/pitchfork/Gann);
  Point & Figure render (flagged "soon" in the chart-type dropdown); true split RS pane (v5);
  log-scale toggle. None are committed requirements; all in `docs/chart-redesign-design.md` §14.

## Gates
- Chrome gate: **PASS** (11 legacy + 4 native, all markers).
- Live 200-sweep: **PASS** (31 routes + 4 overlays all 200, hermes-api active).
