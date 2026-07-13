# Lane L3 — Charting site-wide — STATUS (2026-06-29)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the L3 charting lane closes. Registered in `docs/DOC_INDEX.md`.


> Wrap note for Lane L3. Base HEAD was `05cdeae`. L3 commits: W1 `ccbd25e`+`1a9fe2c`,
> W2 `6e3b22d`+`dc1da97`, W3 `7b49e4e`+`8b39551`, **W4 `76d465f`**. Both gates PASS. Full
> inventory = `docs/L3-chart-inventory.md` (W2 §8–§11, W3 §12–§17, **W4 §18–§22**).

## WAVE 4 (2026-06-29) — lower indicator pane + compare
All on `/dash/stock`; `stock_chart.py` + a new endpoint in `rs_overlay.py`. DESCRIPTIVE-only. `76d465f`.
- **LOWER PANE (item 1, the big one):** a SECOND lightweight-charts instance under the price chart
  (v4 has no native panes), time-synced (one-way master→follower: match barSpacing + logical range,
  RAF-coalesced — two-way froze the renderer). Volume + RSI(14, 30/70 guides) + MACD(12/26/9). Bounded
  (collapses to 0 when off; mounted OUTSIDE `.chartwrap` which clipped it; driven via min-height!important
  to beat the skin's !important height rule). Recomputes on resample. `window.__wfpc` UNTOUCHED. **In-browser:
  draws + x-axis aligned bar-for-bar with the price chart.**
- **COMPARE (item 2):** rebased multi-symbol overlay (focus vs index/peer, base 100 at window start) on a
  dedicated `cmp` scale (candles untouched); symbol-add input + chips (≤4). New `/dash/compare/series`
  endpoint (equity/index close series, reads-only). Capped ~2y (meaningful + light). Non-blocking inline
  status. Fixed a time-key bug ({t,c} vs time) that threw in setData. **In-browser: INFY+Nifty 50 draw.**
- **Coexistence (item 3) + final pass (item 5):** CPR+DVPT+MA+Volume+RSI+MACD+Wolfe+Harmonic+Compare ALL ON
  together → `__wfpc`+`__wflp` live, no overflow, **ZERO console errors**.
- **Demo-readiness (item 4):** default kept LEAN (candles+DVPT+MA, lower pane collapsed) for clean fast
  first paint; recommended DEMO toggle = + CPR + Volume (screenshot captured). Lower-pane-on-by-default
  rejected (would slow first paint).
- **Perf note:** heavy multi-overlay loads time out the *screenshot* CDP call (renderer busy) but complete
  with no errors; a native alert() in the compare path looked like a freeze (modal blocks) → replaced.

---

## WAVE 3 (2026-06-29) — professional analyst tools
All in `stock_chart.py`, all DESCRIPTIVE-only, all in-browser verified (dedicated tab):
- **Fib EXTENSION** tool (`Fx`) — projects 1.272/1.618/2/2.618 targets beyond a move (purple),
  alongside the existing Fib retracement; magnet + editable handles + persisted. (item 1)
- **Measure** now reports Δbars + Δcalendar-days on top of Δprice + Δ%. (item 2)
- **Bollinger Bands (20,2σ) + ATR bands (close±2×ATR-14)** as Indicator overlays in the rail,
  recomputed on resample, legend caveat "volatility envelope (descriptive)". Anchored-VWAP already
  existed. (item 3)
- **Drawing manager** (`≡ list`) — per-drawing colour picker + width selector + delete-one + a
  list panel + export/import drawings as JSON (caps 500, never-throws). col/w persist via the
  drawings_store JSON blob (no schema change). (item 4)
- **Mobile** — `@media(max-width:640px)` shortens the chart (`clamp(300px,52vh,460px)`) +
  `touch-action:none` for gestures; chart bounds to ~250px in a 380px container with no
  chart-level overflow. **HAND-OFF:** the residual page overflow at 380px is `NAV.ngcrumb` +
  a dashboard.py `TABLE` (frozen, L1/L2), NOT the chart (`anyMine=0`). (item 5)
- **Verification (item 6):** 8 overlays/indicators ON together (DVPT/CPR/Wolfe/Harmonic/RS/VWAP/
  Bollinger/ATR) → `__wfpc`+`__wfcandle` intact, 7 canvases, ZERO console errors. `7b49e4e`+`8b39551`.

---

## WAVE 2 (2026-06-29) — server drawing persistence + verification
- **SHIPPED — server-side drawing persistence** (`6e3b22d`): NEW `src/web/drawings_store.py`
  (`GET`/`POST /dash/drawings` over a module-owned `chart_drawings` SQLite table, self-mounted via
  `wolfe_view.include_router`) + `stock_chart.py` `makeDraw()` adopts the server copy on load
  (local→server migration if empty) and debounce-POSTs on save + `beforeunload`. localStorage stays
  the offline cache. **In-browser verified (live WIPRO):** server-seeded drawings with localStorage
  CLEARED survived a hard reload and DREW (blue trendline + purple hline@250); round-trip also via
  TestClient + live curl. Deployed atomically (backup `*.bak-L3` → scp LF → CRLF=0 → import-test →
  restart → health 200).
- **Families-where (item 2):** documented — families live in `stock_chart.SNIPPET`, available wherever
  a price candle chart renders = `/dash/stock`; other surfaces are single-purpose so families don't
  apply. No new surface in L3's modules. (inv §9)
- **Multi-TF harmonic (item 3):** VERIFIED — D/W/M all detect (D=Gartley+Crab BEAR, W=Butterfly BULL,
  M=Crab BULL); chip re-fetches W/M on interval change; in-browser ON+Weekly drew, `__wfpc` intact. (inv §10)
- **Harness gap (item 4):** made the edit (add `/dash/harmonic/overlay?sym=ACC` to OVERLAYS), proved
  the sweep PASSES with 5 overlays all 200, then **reverted** (shared + foreign-dirty file — not
  absorbed). **HAND-OFF** via spawn_task `task_d0a923cf` + this note.
- **Perf (item 5):** MEASURED — lib script cached (transferSize 0, 9 ms), NOT the bottleneck; lib
  `<script>` tag is in frozen `dashboard.py` (can't add `defer`); deferring `boot()` risks `__wfpc`.
  **Verdict: frozen-dashboard.py hand-off to L1.** (inv §11)

---

## WAVE 1 — What L3 found
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
