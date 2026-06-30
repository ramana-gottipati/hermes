# Lane G3 — Charting completion (the do-no-harm backlog + progress)

> Autonomous build lane (2026-06-29). Owns ONLY: `src/web/chart_view.py`,
> `src/web/stock_chart.py`, `src/web/static/hermes-charts.js`, `src/web/wolfe_view.py`,
> `src/web/wolfe_overlay.py`, `src/web/harmonic_view.py`, `src/automation/harmonic_*`,
> NEW chart modules. Never touches dashboard.py/cockpit.py bodies, v2_surfaces.py,
> ui_kit.py/shell_skin.py, src/pat, lens_registry.py/nav_links.py, the research lane.
>
> Builds ON what already shipped (do not redo): the bounded one-chart engine + the
> four-family rail + the drawing engine (magnet/hide-all/localStorage) + harmonic UI
> (`1eeae16`) are LIVE on `/dash/stock`. This lane FINISHES the story.
>
> DO-NO-HARM (every commit): safety-diff → backup `*.bak-g3` → scp LF → VPS import-test →
> restart hermes-api → `bash scripts/regression_sweep.sh` + `python scripts/chrome_gate.py`
> BOTH PASS → live-verify on a real symbol → commit ONLY owned files. Gate fails → revert,
> re-verify green, STOP+report. Descriptive-only.

## State at lane start (audited)

- `stock_chart.py` SNIPPET (LIVE engine): four-family rail, full drawing engine
  (trend/hline/rect/Fib/measure/text + magnet + hide-all + per-symbol localStorage),
  harmonic overlay, RS docked lane, VWAP/AVWAP, fullscreen, D/W/M/Q resample. Renko/Kagi/
  P&F are disabled "soon" stubs in the type dropdown. Harmonic chip has no read-by-side caveat.
- `hermes-charts.js` (reusable site-wide engine, the "CPR Spine"): drawing tools are
  decorative stubs (no handlers, magnet/hide-all inert); chart-type only Candles/Line.
- `harmonic_patterns.py`: series-based `detect_from_series`; daily only (no W/M resample).
- `harmonic_view.py`: scanner + overlay feed; daily only; no `tf` param.

## Backlog (ranked; each item is a self-contained do-no-harm commit)

1. **[G3-1] Renko + Kagi chart types** in `stock_chart.py` — real client-side transforms
   (Renko brick + Kagi line on the existing candle/line series), promote from "soon". P&F
   stays deferred (column-grid needs a different axis; flag honestly). LOW risk (owned, additive).
2. **[G3-2] Harmonic read-by-side caveat on the /dash/stock overlay** — the chip + a small
   legend line carry the BULL ✓ edge / BEAR ⚠ tail caveat the scanner already states, so the
   drawn pattern is never read as a naked buy/sell. `stock_chart.py` + `harmonic_view.py` feed.
3. **[G3-3] Multi-TF harmonic detection (W/M)** — `harmonic_patterns.py` gains a `tf`
   resample (daily→weekly/monthly bars) before detection; `harmonic_view.py` overlay + scanner
   gain a `tf` param. Surfaces W/M harmonics (the hand-off item). DESCRIPTIVE; daily default unchanged.
4. **[G3-4] Complete the reusable engine's drawing engine** in `hermes-charts.js` — port the
   proven `makeDraw` primitive (canvas drawings + magnet + hide-all + per-symbol localStorage)
   so the site-wide engine is no longer a decorative stub. Adds Heikin-Ashi/Area/Hollow to its
   type dropdown for parity. This is the "roll bounded engine site-wide" foundation.
5. **[G3-5] Chart "read"/legend story line** on `/dash/stock` — a compact, always-visible
   legend strip under the rail naming what each active overlay means (descriptive grammar),
   so the chart reads as a workstation not a wall of lines. `stock_chart.py`.
6. **[G3-6] Perf: incremental harmonic re-snap** — avoid `removeSeries`/re-add churn on every
   resample where the data is unchanged; reuse series, `setData` only. `stock_chart.py`.
7. **[G3-7] DVPT + RS first-class multi-TF** — confirm DVPT/RS ride the D/W/M/Q resample
   correctly (RS lane re-fetch is daily; document/guard). `stock_chart.py`.
8. **[G3-8] Kill remaining preserveAspectRatio="none" stretch in owned surfaces** — audit
   owned files for the stretch anti-pattern; bound any sparkline/mini-chart they emit.

## Progress log

### 2026-06-29 — batch 1: G3-1/2/3/5/6 SHIPPED (one commit)
- **G3-1 Renko + Kagi** chart types LIVE (`stock_chart.py`): price-driven transforms keyed
  on the bar dates (EOD-faithful, ATR-median brick = self-scaling box). Dropdown promotes
  Renko/Kagi out of "soon"; P&F stays honestly disabled (needs a column-grid axis).
- **G3-2 Harmonic read-by-side caveat** on `/dash/stock`: the Harmonic chip carries the
  BULL=edge / BEAR=tail tooltip; the new legend strip restates it inline.
- **G3-3 Multi-TF harmonic detection (W/M)** (`harmonic_patterns.py` + `harmonic_view.py`):
  `resample_series` daily→weekly/monthly; `detect(tf=…)`; overlay `?tf=` param; the chart
  re-fetches W/M harmonics when the interval crosses into W/M. Live-verified: RELIANCE 0
  daily but 1 weekly + 1 monthly; INFY weekly-only — genuinely different per TF.
- **G3-5 Chart "read"/legend strip**: a compact, always-current legend under the rail names
  every ACTIVE overlay in plain grammar — the chart reads as a workstation, not a wall of lines.
- **G3-6 Perf**: harmonic re-snap only re-draws (no re-fetch) when the TF is unchanged;
  re-fetches only when the interval actually crosses into/out of W/M.
- **Gates:** chrome gate PASS · regression sweep PASS (31 routes + 4 overlays 200). **Live
  (browser, IP:8000, ACC + RELIANCE/INFY/TCS):** all 7 chart types switch, harmonic toggles,
  W→M→D re-fetch, legend updates — `window.__wfpc` intact, chart bounded 1280×760, ZERO
  console errors. Backups: `*.bak-g3` on VPS.

### 2026-06-29 — batch 2: multi-TF harmonic SCANNER (commit) 
- **Scanner timeframe selector** (`harmonic_view.py` + `harmonic_signals.py`): the
  `/dash/harmonic` page gains a Daily/Weekly/Monthly pill. Daily reads the nightly
  snapshot (instant); W/M are a live multi-TF scan (`HS.scan(tf=…)` — backward-compatible,
  `tf="d"` default unchanged, so the nightly persist + Wolfe scanner are untouched). The
  multi-TF DETECTION hand-off is now discoverable, not chart-only.
- **Gates:** chrome gate PASS · regression sweep PASS. **Live (browser):** weekly 147
  setups, monthly 140 setups, pills active, by-side tags render, zero app console errors
  (the 4 message-channel exceptions seen were the benign Chrome-extension artifact from a
  prior tab, not our code). Backup: `harmonic_signals.py.bak-g3` on VPS.

### G3-8 audit — CLEAN (no commit needed)
- No `preserveAspectRatio="none"` stretch in ANY owned file. `wolfe_view.py`'s SVG uses
  `viewBox="0 0 1000 460" width="100%"` with default proportional scaling — already bounded.

### G3-4 reusable engine — DEFERRED (intentional, not gold-plated)
- `hermes-charts.js` (`HermesCharts.createStockChart`) + `chart_view.render_stock_chart` are
  **not consumed by any live page** and `/static/hermes-charts.js` returns **404** (the
  static mount was never wired). The live `/dash/stock` uses the `stock_chart.py` SNIPPET
  instead. Completing the unused engine's drawing stub would polish dead code; the real
  site-wide rollout target (RRG/RS/ratio in `cockpit.py`/`rrg_view.py`) is OFF-LIMITS
  (non-owned). Left as-is. If the reusable engine is ever revived, port `makeDraw` from
  `stock_chart.py` and wire the `/static` mount first.
