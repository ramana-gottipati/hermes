# Performance hand-off → the UI/UX (D54) session

> **From:** the data/performance session (2026-06-19). **To:** the agents building the D54 UI revamp (`docs/ui-design.md`).
> **Why this doc exists:** a parallel performance pass diagnosed why the dashboard hiccups. The fixes split cleanly in two. The **render-layer** items below all live in `src/web/dashboard.py` — *your* file — so they are handed to you as todo-pointers rather than edited from under you (two sessions sharing one working tree is a known hazard, PROJECT_STATE session-19 note). The **backend/data** items are being worked separately — see `docs/perf-architecture.md`.
> **This fills in `ui-design.md` § 10 (lightness / performance budget) with concrete, code-grounded actions.** Every item is **additive and no-regression** — it matches D-UI-3 (server-render + vanilla JS, no SPA) and D-UI-4 (no regression).

## The one-line diagnosis
The app **computes and ships a full, uncompressed, uncacheable document on every click**, where fast data apps (TradingView / Screener.in / Trendlyne) **ship a cached shell once and then move only thin, precomputed data**. It's the delivery model, not the size. All of the below stays within the current stack.

## ✅ Already done for you (backend, shipped this session)
- **App-layer gzip** (`src/main.py`, `GZipMiddleware`, minimum_size=500). Every HTML/JSON response is now compressed. **Consequence for your planning:** the *uncompressed-payload* half of items 1 and 3 below is already mitigated — those items now buy you **caching + smaller DOM**, not compression. Don't double-count the win.

## Render-layer todo-pointers (all in `src/web/dashboard.py`)

| # | Item | Why | Evidence | ui-design.md phase |
|---|---|---|---|---|
| 1 | **Externalize `_BASE_CSS` + `_DT_JS` (+ the chart/picker JS) to hashed static routes** served with `Cache-Control: immutable, max-age=31536000`; stop inlining them in `_shell`. | ~17 KB of identical CSS+JS is re-inlined on **every** page; cached-once removes it from 100% of navigations after first load. No build step — serve the existing string constants from one cached route. | `_shell` inlines at `dashboard.py:361,381`; `_BASE_CSS` 46–207, `_DT_JS` 217–321 | Phase 1 (lightness) |
| 2 | **Self-host lightweight-charts; add `Cache-Control` to `/icon.svg`, `/manifest`, `/sw.js`.** | The chart lib loads from third-party **unpkg** on 5 paths (a network dependency you don't control); the icon/manifest are byte-identical yet re-sent every load. | `_LWC_CDN` `dashboard.py:2414`; asset routes `4781–4800` | Phase 1 |
| 3 | **Thin chart data: add a small JSON endpoint** (e.g. `/dash/api/stock/<sym>/series`); chart pages fetch it instead of inlining ≤1,300-point arrays into the HTML body. Optionally downsample to the visible range. | The stock page embeds ~100–150 KB of inline JSON in the document. Moving it to a cacheable/gzipped fetch shrinks the initial doc and lets the chart lazy-load. Still vanilla JS. | `json.dumps(chart_data)` `dashboard.py:2691,2807,3402` | Phase 1/2 |
| 4 | **Virtualize the screener grid only** (render the visible window, recycle on scroll). Keep the frozen panes (D-UI-12). | Up to **27 cols × 2,000 rows ≈ 54k `<td>`** are server-rendered into one document and the sticky-pane CSS forces a full layout pass. This is *the* screener hiccup. Virtualize **only this widest grid** — per § 10, "only if a real bottleneck appears." | cap `dashboard.py:1700`; row loop `1750–1819`; header `1856–1865` | Phase 1 (centrepiece) |
| 5 | **Switch `/dash/stock` to READ the precomputed `adj_close`** (the backend is landing it — see perf-architecture.md) and **delete the inline back-adjustment loop**. | Today the split/bonus re-adjustment is recomputed in Python over ≤1,300 rows on every stock-page load — the documented ~3.5 s cold route — and it's a hand-copied duplicate of `adjust.py`. Reading a column makes it instant. Closes open item **B5** on the render side. | inline loop `dashboard.py:2746–2790` (dupe of `adjust.py`) | Phase 1 (data-first retrofit) |
| 6 | **Switch the screener `ORDER BY conv` to the precomputed `conv` column + its index** (backend landing it). | The conviction score is currently a computed SQL expression → guaranteed temp-B-tree sort of the whole universe every request. An indexed column makes it a range-scan + LIMIT. | `dashboard.py:1733–1752` | Phase 1 |
| 7 | **Memoize `_latest_dates()` per trading day.** | It runs two `MAX()` scans on a 2nd connection on **14 routes**; the value can't change within a trading day. | `dashboard.py:621` | Phase 1 (cheap) |
| 8 | **Maintainability (the § 5 "extend, don't replace" goal):** dedupe the chart bootstrap (≈5 copies), the type-ahead picker (authored **twice**: `_COMPARE_PICKER_JS` / `_STOCK_CMP_PICKER_JS`), and the `chart_css` literal (×3); plan the split of the 4,719-line module into shell / components / charts / api / pages. | The slowness and the un-maintainability share one root: HTML + CSS + 8 inline JSON payloads + duplicated JS all tangled in one file. The same split that caches the shell also de-duplicates the JS. | `dashboard.py:217,1890,2424,3326,4449,4568,4663` | Phase 1→2 (refactor, zero behaviour change) |

## How items 5 & 6 coordinate with the backend
Items **5** and **6** depend on two new precomputed columns (`adj_close`, `conv`) that the data session is adding to `stock_signals` and populating during the **D47 post-backfill full recompute** (avoiding a wasteful second full-history pass). Until those columns are populated they will be `NULL` — so guard the read (`COALESCE`/fallback) and flip the switch when the recompute lands. The data session will ping when the columns are live.

## What NOT to do (shared doctrine, so we don't drift)
No SPA, no framework, no build pipeline beyond serving hashed static files, no virtualizing tables that don't need it (only the screener), no premature caching layer. Every item is reversible and additive.
