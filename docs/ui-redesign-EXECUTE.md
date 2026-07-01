# Autonomous execution brief — patearn UI/UX redesign

> **Self-prompt. Operating autonomously (no user inputs; use subagents for research/decisions/parallel work).** Authorized 2026-06-23.
> **Companion spec:** `docs/ui-redesign-2026-06.md` (the audit, IA, no-loss census, phasing, decision log).

> **⚠ For the SCHEMA redesign, the canonical resume guide is now `docs/ui-architecture-v2.md` §14** (the stress-tested v3 architecture + full takeover guide). This file's Phase-0/1 progress below remains valid history.

## PROGRESS (live — 2026-06-23)
- ✅ **Phase 1 sub-nav** — BUILT + verified (28/28). dashboard.py only.
- ✅ **Phase 0 Batch A** — BUILT + verified (Import de-orphan · Remove→origin redirect · `?closed=1` banner [fixed a shadowing bug] · watch Target/Stop · scan `.dt`). dashboard.py only.
- ✅ **Batch A+ (tracker action-loop)** — closed-trade **reopen** + **notes** column surfaced. dashboard.py only; verified.
- ⏸ **HARD STOP on all web-layer edits.** The parallel (Wolfe Wave) session now owns the **entire web layer** — `cockpit.py`, `dashboard.py`, `rrg_view.py` dirty + new `wolfe_view.py`/`wolfe_overlay.py`. It **adopted my sub-nav** (added `"wolfe"` to my `_WS` + `_SUBNAV`, a wolfe_overlay import, a stock-page Wolfe button) → our work is **comingled in the same regions of dashboard.py**. Combined tree is healthy (25/25) and my 4 increments are intact. But editing now = two sessions in the same uncommitted file = cross-absorption/clobber risk. **Do not solo-edit the web layer until the parallel session commits / the tree frees.** My clean +87/−19 baseline patch is at `C:/Users/gotti/.claude/projects/D--Hermes/ui-redesign-phase01-dashboard.patch` (note: now stale vs the comingled tree — reference only).
- **Resume plan:** once the parallel session commits dashboard.py (my work likely lands inside their commit since they built on it), re-pull the shovel-ready anchors below, re-verify they still match (their edits may have shifted the target functions), then execute B1/B1b/C1 + the stock News tab.

### Shovel-ready anchors (execute when cockpit.py is clean / tree is calm)
- **B1 — Index RS card** (`cockpit.render_index_detail`): index var = `idx`; `q=D._q` available; splice a one-line `<a class="row" style="display:inline" href="/dash/ratio?idx={q(idx)}">RS vs benchmark →</a>` card into the final `return (... + rs_block + band_block + rollup ...)`. NOTE: size/broad index branches currently DON'T render the ratio link (only the sector branch does) — that's the gap to close.
- **B1b — "Open in Screener" lens links** (`render_mep`/`render_conviction`/`render_leaders`/`render_concalls`): after each `head`/`head_html`, insert the existing idiom `'<div class="sub" style="margin:10px 0 0"><a class="row" style="display:inline" href="/dash/screener?scope=all">Open in screener →</a></div>'`. `q` NOT aliased in mep/conviction/concalls — add `D._q` if needed.
- **B2 — Workbench's 3 cols → screener** (dashboard.py screener): HIGH RISK (virtualizer + `<colgroup>` widths + group toggles). Defer; workbench keeps its URL so nothing is lost meanwhile.
- **B3 — Themes as a screener scope** (dashboard.py screener): medium risk; add to the scope selector + scope handling.
- **C1 — Glossary `?` hook**: `docs/metrics-glossary.md` EXISTS and is rich (DVPT/×Power/Character/Key-price/RS all defined). Add a `tip=` kwarg to `_ck_tile` (cockpit.py) + a CSS popover; baked at render. Wiring needs cockpit.py → blocked now.
- **C2 — tap-fallback for RRG/rotation/rsband tooltips**: BLOCKED (parallel-owned view modules).

## Role
equity-research + UI/UX + architect agent, building the additive UI redesign to completion of the safe/high-value scope.

## Invariants (NEVER violate)
1. **Purely additive.** No route rerouted. Sacred pages (`/dash/ratio`, `/dash/rrg`, `/dash/compare`) keep URLs. The 4 borderline removals (stock Character de-dup · filter-UI unify · dual-CSV · column-drop) are implemented as **KEEP-BOTH** only — never remove.
2. **Edit only files I own AND that are currently clean:** `src/web/dashboard.py` (thin), `src/web/cockpit.py`, and NEW modules. **NEVER touch parallel-owned/dirty files:** `src/main.py`, `src/automation/rsband.py`, `src/automation/scoring.py`, `src/automation/ignition*.py`, `src/web/rsband_view.py`, or any new file the parallel session adds. Re-check `git status` before each batch.
3. **Verify after every batch** with the TestClient harness — 28/28 routes 200 + targeted HTML assertions. Never regress.
4. **CRLF-safe** (string-match Edits preserve endings).
5. **No autonomous git commits** (shared tree + active parallel session → clobber/cross-absorption risk). Record every change in the build-log so nothing is informationally lost.
6. **Defer the ~700-line dead-code deletion** (large diff = highest collision risk with the parallel session).

## Harness
`python` (hermes-agent venv on PATH) imports `src.web.dashboard`; local `data/hermes.db`; mount `dashboard.router` (+ rrg/rotation/rsband routers) on a throwaway FastAPI app; assert 200 + HTML markers. Baseline = 28/28.

## Work queue (priority order; each item = edit → verify → document)
**A — Phase-0 fixes (dashboard.py; additive bug-fixes + de-orphan):**
- A1. De-orphan **Import** → add to `_track_subnav`.
- A2. **Action-loop:** Remove returns to origin list (watch→`/dash/watchlists`); "position closed" confirmation banner on `/dash/performance` (`?closed=1`); surface **Target/Stop** on watchlist rows.
- A3. **Scan** → give its table `class="dt"` (sort/filter/export) — ends the regression.
- A4. **Frozen-pane** → wrap wide Portfolios/Watchlists/Performance tables in `.scrwrap` so headers freeze.

**B — Phase-2 additive surfacing:**
- B1. **Index page** (`cockpit.render_index_detail`): add an "RS" section linking `/dash/ratio` (reduce index/ratio duplication additively; ratio stays).
- B2. **Workbench's 3 unique columns** (AvgClose-3m, trade-qty, deliv/trade) → add to the screener positioning group (additive; workbench stays). Higher risk (screener virtualizer) → subagent + verify.
- B3. **Themes as a screener scope** (add to the scope selector).

**C — Phase-3 polish (owned files only):**
- C1. **Glossary "?" hover-help** popover (from `docs/metrics-glossary.md` if present) → new module + thin wiring.
- C2. **BLOCKED:** tap-fallback for RRG/rotation/rsband hover tooltips (parallel-owned view modules). Document as blocked.

## Documentation
After each batch, append a dated line to `docs/ui-redesign-2026-06.md` § 10 build log.

## Stop condition
When A+B+C-doable are done & green, write a final build-log summary + report. If a batch is risky/blocked, document and move on.
