# RS Momentum & Divergence — Roadmap & Plan

> **Status:** LIVING master plan. Created 2026-07-02 (Session 69). Owner: Ramana.
> **Mandate:** build the RSI-of-RS + divergence + staged-recovery ecosystem, **surgically and
> additively** — every addition is a NEW isolated module or an ADDITIVE nullable column; nothing
> existing is edited destructively, re-scoped, or removed. Every addition must be a *better
> indication*, not decoration. Client-grade, presentable to the world's best institutions.
> **Hero visual:** `docs/visuals/momentum-roadmap-swimlane.svg`.

---

## 1. The objective (one line)

**Relative strength = does the stock's/sector's %Δ beat the Nifty's %Δ over a horizon** (beating in a
down market = falls less = still strong). We want to see the *momentum of that RS* — its RSI — and
catch the **turn early via divergence**, then confirm it up a **staged ladder** (week → 3 months).
Posture is **DESCRIPTIVE** (outperform-Nifty read + early-warning), never a tradable alpha claim
(the momentum edge dies net of cost — see `docs/strategy-ledger.md`).

## 2. The concept ecosystem (the visuals, in order)

These accumulate into one shared vocabulary (reproducible in-session; keys saved to `docs/visuals/`):
1. **Horizon sweep** — beat/lag vs Nifty across 24m→1w; the *phase is the shape of the sweep*.
2. **Recovery ladder** — a turn climbs week→2w→1m→3m→6m; each horizon that confirms upgrades the tier;
   long horizons are *base-depth context, not a gate*.
3. **RSI-of-RS placement** — the RSI oscillator docks under the RS line; a divergence reads vertically.
4. **Roadmap swimlane** — this plan across 3 lenses × 4 phases.

## 3. Feature catalog (all additive; placement fixed)

| # | Feature | Where it lives | Better indication because… |
|---|---|---|---|
| 1 | RSI-of-RS oscillator pane (30/50/70 bands) under the RS line | stock dossier RS tab · `/dash/ratio` · `/dash/rsband` | momentum read directly beneath the level |
| 2 | RSI column: level + ▲/▼ + divergence flag | Screen+ · `/dash/sectors` · `/dash/leaders` · `/dash/rotation` | scan momentum/turns across the universe |
| 3 | Divergence markers auto-drawn on RS + RSI panes | dossier RS tab | the visual proof of the early turn |
| 4 | Divergence board (bullish/bearish, by horizon) | NEW card under Markets / RS-hub + strategist badge | one "watch closely" surface for every diverging name |
| 5 | Divergence as Stage-0 of the recovery ladder | rotation / ladder | earliest rung — precedes the week-green |
| 6 | RRG points colored by RSI-of-RS speed | `/dash/rrg` · `mini_rrg` | position + how fast it's moving |
| 7 | Cycle-clock dot glow = RSI speed | rotation cycle-clock | velocity around the loop |
| 8 | RSI-of-RS horizon heat strip (1w/2w/1m/3m) | dossier RS tab + sector page | momentum building short→long |
| 9 | RSI-of-RS breadth (% constituents rising) | sector / index dossier | early breadth thrust |
| 10 | "Momentum & Divergence" lens (RRG + RSI + board + ladder) | NEW lens under Markets (`lens_registry`) | the cockpit for the whole theme |
| 11 | Early-signal watchlist (Stage 0–1 across universe) | Home preview + rotation section | the daily "what's turning" feed |
| 12 | Sector → constituent RSI drill | extend `/dash/rrg?idx=` (exists) | which stocks drive a sector's turn |

## 4. Phased delivery (the swimlane)

- **Phase 1 — Momentum visible (no VPS).** Render from the *existing* single `rsi_of_rs`.
  Ships: RSI pane + divergence markers (dossier) · divergence board · RSI column. **Building now** in
  `src/web/momentum_pane.py` (isolated).
- **Phase 2 — Multi-horizon (needs backfill).** Add `rs_*_1w/2w` + `rsi_of_rs_1w/2w` via additive
  columns + recompute/backfill (§6). Ships: horizon heat strip · staged ladder live · RSI breadth.
- **Phase 3 — Rotation fused.** RRG colored by RSI speed · cycle-clock · sector→constituent drill ·
  the Momentum & Divergence lens (cockpit).
- **Phase 4 — Early-signal engine.** Universe divergence scan · early-signal watchlist · Home preview
  · alerts · client-grade PDF export.

## 5. The three lenses

- **Financial-analysis lens.** RS answers "are we beating Nifty, over which horizons"; RSI-of-RS adds
  *speed*; divergence is the *earliest* actionable tell (momentum turns before price). The ladder turns
  a binary label into graded conviction (Watch → Confirmed), so an analyst acts on evidence, not a flip.
- **Data & compute lens.** All pre-computed nightly into signal columns (reproducible, ₹0, no LLM).
  New dimensions are COLUMNS via `db._ensure_column` (never edits to `db.py`); raw archive untouched;
  value-based/self-scaling (percentile of the name's own RS-vol — no static thresholds).
- **UI/UX lens.** Oscillator docks under the line (institutional convention: ~30% pane height,
  30/50/70 banding, restrained 2-hue palette, divergence drawn as a thin connecting line). Everything
  additive: sacred routes (`/dash/ratio`, `/dash/rrg`, `/dash/compare`) keep their URLs and behavior.

## 6. Backfill spec (Phase 2 — the one VPS step)

- **Additive columns** (via a module-owned `_ensure_column` guard, mirroring `rs_phase._ROTATION_COLUMNS`):
  `stock_signals` / `index_signals`: `rs_vs_broad_1w, rs_vs_broad_2w, rsi_of_rs_1w, rsi_of_rs_2w`
  (+ sector variants for stocks). Nullable; existing columns untouched.
- **Compute:** short-horizon RS = stock %Δ − Nifty500 %Δ over 5 / 10 trading days; short-period
  RSI-of-RS (period ~5 / ~10) on the RS line. Extend the existing nightly RS chain (module confirmed by
  the injection-point recon).
- **Backfill:** recompute history so the ladder/heat-strip have a track record. Script: `scripts/` (to
  be added once the compute module is confirmed). **Runs on the VPS** — outward; owner-run/authorized.
- **Windows/thresholds** pinned empirically by `scratchpad/rotation_timeframe_study.py`.

## 7. Surgical / non-disruption doctrine (binding for this workstream)

1. New work = **NEW isolated modules** (the `credibility_fingerprint.py` / `rsband_view.py` pattern),
   mounted durably via `v2_surfaces._ROUTER_SPECS` — no `main.py` / `dashboard.py` edits.
2. New data = **additive nullable columns** via `db._ensure_column`; never edit `db.py`; never drop.
3. Overlays follow the existing `window.__wf*` SNIPPET convention (CPR/MEP/harmonic) — append, don't
   rewrite `stock_chart.py`.
4. Every change **import-tested** + run through the project regression gate before it's considered done.
5. **Nothing existing is removed or re-scoped.** Sacred routes are sacred. Revert path documented.

Cross-refs: methodology memory `rotation-phase-methodology`, `docs/rs-rotation-design.md`,
`docs/premium-visuals-brainstorm.md`, ledger `docs/strategy-ledger.md`.
