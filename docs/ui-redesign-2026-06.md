# Patearn — UI/UX redesign & templates (2026-06)

> **Status:** DESIGN — proposed, build-gated. No code changed yet. Authored 2026-06-23 by the UI/UX + architect + equity-research review pass.
> **Parent doctrine:** `docs/ui-design.md` (D54 + D-UI-1…17). This document does NOT overturn it — it extends it with a full screen-by-screen audit, a re-homing map, and a build plan.
> **Cardinal rule (non-negotiable):** NO value is deleted or suppressed. Every unique metric on every screen is explicitly re-homed before its old container is retired. See § 4 (re-homing map) — that table IS the no-loss guarantee.
> **No regression:** every existing route keeps working; the redesign regroups, de-orphans, and surfaces. Routes are NOT rerouted.
> **🔴 Sacred-pages reconciliation (memory `build-additive-never-replace`, session-31 lesson):** `/dash/ratio`, `/dash/rrg`, `/dash/compare` — and by extension EVERY user-facing route — keep their existing URLs. The "umbrellas" and "tabs" below are realized **additively** as a shared sub-nav strip that *links between* the existing pages; nothing is 307'd away from its URL. The only deletions are unreachable dead CODE (post-`return` bodies) and dead CSS — never a page.

---

## 1. Method

A full inventory was taken of all **35 screens** (every column, metric, micro-viz, link, empty-state). The system is well-built: data-first is honoured, the "instrument" micro-viz vocabulary (DVPT ladder · accum/distrib bar · key-price band · character triglyph · RS heat-strip · CPR D·W·M strip) is consistent and is the product's signature, the frozen-pane virtualized screener is excellent, and empty-states are honest. The problems are **structural (findability + order)**, not cosmetic.

The redesign is organized around the analyst decision arc:
**read the weather → query the universe → apply a lens → decide on a name → commit & track → (or just ask).**
Top nav stays 6 tabs (no muscle-memory break); each workspace gains a **consistent sub-nav** (Tracker already proves the pattern), plus consolidation that loses nothing.

**Three pivotal decisions taken (recommended options):**
1. Consolidation scope = **Medium** — consolidate only where nothing is lost.
2. Themes = **keep its own tab**, additionally exposed as a Screener scope.
3. Rotation lenses = **unified** under one route (Map · Weather · Band).

---

## 2. Audit findings (5 buckets)

1. **Orphans & dead ends** (value that exists but can't be reached)
   - `/dash/rsband` — richest *unique* lens (RS support↔resistance level, POC magnet, regime gate, R²). **No inbound link anywhere.**
   - `/candidates` — legacy Stage-1 list; outside the whole nav/`_shell`; Telegram-only inbound; symbols not even clickable.
   - `/dash/scan` — fully superseded by `/dash/stocks`; no inbound link; regresses (plain table, no sort/filter/export).
   - `/dash/import` — powerful, reachable only via one tiny add-box link.
2. **Redundancy without hierarchy** — `/dash/screener` is a superset of `stocks`/`workbench`/`mep`/`cpr`/`conviction`/`concalls`. The "who's leading/rotating" question is split across 5 routes (Sectors · RS · RRG · Rotation · Leaders). `/dash/ratio` duplicates `/dash/index` (own-price chart, valuation, returns, constituents).
3. **Consistency debt** — ~700 lines of **dead legacy code** after `return` in 8 routes (home, markets, sectors, rs, leaders, conviction, concalls, strategies); dead fixed-bottom `nav` CSS; three screens stack two filter UIs (`#sbar`/`#mepbar`/`#cvbar` + `.dt` toolbar); `mep`/`launchpad`/`concalls` missing from the `_WS` nav map; 5 classification vocabularies with no glossary surface.
4. **Mobile data-loss** — the 3 SVG vizes (RRG, RS-band lanes, markets rotation) are **hover-only**, so their unique numbers are unreachable on touch. Wide tables (Tracker 19-col, stock dossier) lose their header on scroll — they don't use the `.scrwrap` frozen-pane wrapper the screener already proves.
5. **Action-loop friction** — Remove always redirects to Portfolios (even from Watchlists); no "position closed" confirmation (`?closed=1` ignored); no reopen/undo for a closed trade; watch rows hide Target/Stop though alerts fire on them; `notes` column never surfaced (dead); dual CSV export with two different schemas.

---

## 3. Redesigned IA (per workspace + sub-nav)

| Tab | Sub-nav | Notes |
|---|---|---|
| **Markets** | Overview · Sectors · **Rotation** · Compare | Rotation = a shared sub-nav strip across the *existing* `/dash/rrg` · `/dash/rotation` · `/dash/rsband` (labels **Map · Weather · Band**), each route unchanged at its URL. Index page gains an "RS" section linking to `/dash/ratio` (ratio stays — sacred). |
| **Screener** | Grid · Themes scope · Saved views | Centerpiece kept. Workbench's 3 activity columns are *added* to the Positioning group (workbench route also stays). Saved-views promoted to the sub-nav. |
| **Strategies** | Hub · Conviction · Launchpad · Positioning · Accumulation · Strength · Structure · Quality · Credibility | Each pillar gains "Open in Screener (this lens)". Scan + Workbench stay at their URLs, de-emphasized in nav; Scan gains the missing sort/filter/export. |
| **Tracker** | Dashboard · Portfolios · Watchlists · Performance · **Import** | Import promoted into the sub-nav (de-orphaned). Action-loop bugs fixed. |
| **Pat** | Ask · Flows · Glossary | Glossary (`explain`) also wired as a global `?` hover-help hook across all screens. |
| **Themes** | Browse · Theme · Review | Kept as a tab; additionally exposed as a Screener scope. |
| **Stock** (destination, no tab) | Price · Positioning · MEP · RS · Quality · CPR · CCI · F&O · **News** | Character panel de-duplicated (was in both Positioning + MEP). New News tab = home for the retired `/candidates` rationale. |

---

## 4. The re-homing map (THE no-loss guarantee) — full screen census

Disposition legend: **KEEP** · **ENRICH** (gains data/polish) · **CONSOLIDATE** (folds into a tab/host) · **DE-ORPHAN** (now reachable) · **RETIRE** (redirected; value preserved elsewhere).

| # | Route | Disposition | Where its unique value goes |
|---|---|---|---|
| 1 | `/dash/markets` | KEEP | regime cockpit unchanged |
| 2 | `/dash/sectors` | ENRICH | + RS Mom composite & percentile as sortable columns (from `/dash/rs`) |
| 3 | `/dash/rs` | SURFACE | Mom + percentile *added* to Sectors as columns; `/dash/rs` route KEPT + cross-linked (no reroute) |
| 4 | `/dash/ratio` | SURFACE (sacred) | Index page gains an "RS" section linking to ratio; `/dash/ratio` KEPT at its URL — sacred per `build-additive-never-replace` |
| 5 | `/dash/compare` | ENRICH | + chip click-through to stock/index detail |
| 6 | `/dash/index` | KEEP | canonical index page; gains the RS tab from ratio |
| 7 | `/dash/rrg` | SURFACE (sacred) | gains the shared Rotation sub-nav strip (label **Map**); route KEPT at URL — sacred; + tap fallback |
| 8 | `/dash/rotation` | SURFACE | same Rotation strip (label **Weather**); route KEPT; 4-phase grid + movers + leverage marks unchanged |
| 9 | `/dash/rsband` | DE-ORPHAN | same Rotation strip (label **Band**) gives it inbound links at last; route KEPT; band%/POC/regime/R²/verdict; + tap fallback |
| 10 | `/dash/themes` | KEEP | + exposed as a Screener scope |
| 11 | `/dash/theme` | KEEP | participants table unchanged |
| 12 | `/dash/tags-review` | KEEP | governance (write surface) unchanged |
| 13 | `/dash/screener` | KEEP+ENRICH | + Workbench's AvgClose-3m / trade-qty / deliv-per-trade columns; saved-views surfaced; themes scope |
| 14 | `/dash/strategies` | KEEP | 8-pillar registry hub |
| 15 | `/dash/scan` | KEEP+ENRICH | route KEPT (no reroute); de-emphasized in nav; gains the missing sort/filter/export to end its regression |
| 16 | `/dash/stocks` | ENRICH | "Positioning"; absorbs scan; weekly/monthly "days fired" rollup kept; + `_WS` entry |
| 17 | `/dash/mep` | KEEP | + add `mep` to `_WS`; pressure/CLV/drift/up-dn-vol/compression terms unchanged |
| 18 | `/dash/conviction` | KEEP | cross-pillar synthesis + Entry read |
| 19 | `/dash/cpr` | KEEP | full CPR geometry (C0/C1/sep/depth/freshness/coil pctile) unchanged |
| 20 | `/dash/workbench` | KEEP | 3 unique cols *added* to screener positioning group; `/dash/workbench` route KEPT at its URL (no reroute) |
| 21 | `/dash/launchpad` | KEEP | + add `launchpad` to `_WS`; D56 flag set + evidence card unchanged |
| 22 | `/dash/concalls` | KEEP | + add `concalls` to `_WS`; full CCI ledger + AI axes unchanged |
| 23 | `/dash/stock` | KEEP+ENRICH | de-dup character panel; + News tab; tighten Positioning tab; tap fallback on zone readouts |
| 24 | `/dash/dashboard` | KEEP | tracker cockpit (9 KPI + attention + movers + books) |
| 25 | `/dash/portfolios` | ENRICH | + frozen-pane on the 19-col table |
| 26 | `/dash/watchlists` | ENRICH | + Target/Stop columns (fields exist, alerts fire on them); Remove returns to origin list |
| 27 | `/dash/performance` | ENRICH | + "position closed" confirmation; + edit/reopen a closed trade |
| 28 | `/dash/tracker` | KEEP | 307→ performance (back-compat) |
| 29 | `/dash/import` | DE-ORPHAN | promoted into Tracker sub-nav; preview/commit/template unchanged |
| 30 | `/dash/track/*` | KEEP | action loop; fix redirect targets + add undo on hard-delete |
| 31 | `/dash/pat` | KEEP | + glossary wired as global `?` hook |
| 32 | `/candidates` | KEEP+MODERNIZE | Telegram digest links to it — KEPT; give it the shared `_shell` + clickable symbols; its rationale + source also surface on Stock ▸ News. (Retire only later, by explicit call.) |

**Near-dead data flagged for surface-or-drop (decide explicitly, don't entrench):** `stocks_in_play.notes` (never read/written); `hot_days_avg_price`; the RS `above_50/200ma` / `new_52w` flags; the ~30 of 88 `stock_signals` columns that never reach any UI (gap-to-key + 🎯, the 3 character sub-axes, surge 3m/1y, near-break, RS slopes — several already surfaced; audit the remainder).

---

## 5. Cross-cutting fixes (no fork — clearly correct)

- **Delete ~700 lines of dead legacy code** after `return` in 8 routes; delete the dead fixed-bottom `nav` CSS.
- **Complete `_WS`** — add `mep`, `launchpad`, `concalls` (currently rely on hard-coded `active=` strings; the dict is the documented source of truth).
- **One filter paradigm** — reconcile the bespoke pill bars (`#sbar`/`#mepbar`/`#cvbar`) with the generic `.dt` text-filter so a screen has one filtering model.
- **Touch fallback** for the 3 hover-only SVG vizes (RRG, RS-band lanes, markets rotation) — tap-to-pin the tooltip. Fixes real mobile data-loss.
- **Frozen panes** on the wide Tracker + stock-dossier tables (wrap in `.scrwrap`; the `_DT_JS` already supports it via `table.closest('.scrwrap')`).
- **Glossary `?` hook** — a CSS popover on group-headers + pills, content baked from `docs/metrics-glossary.md` at render (zero fetch), reusing Pat's `explain` content. Surfaces the 5 vocabularies (trend-state · Character · MEP phase · weather · RS-band verdict) everywhere.
- **Dual CSV export** — keep the server export (importer-friendly schema); drop or relabel the auto-injected `.dt` toolbar export on tracker tables to avoid two different CSVs.

---

## 6. Build phasing

- **Phase 0 — hygiene (zero visual risk):** delete dead code + dead CSS; complete `_WS`; de-orphan rsband + import via links/sub-nav; add scan's missing sort/filter/export; fix action-loop redirects + add the closed-trade confirmation. Pure correctness; no route rerouted, no layout change.
- **Phase 1 — the chrome:** the consistent per-workspace sub-nav strip on all 6 workspaces, incl. the shared Rotation strip linking rrg/rotation/rsband (additive; mirrors Tracker's `_track_subnav`).
- **Phase 2 — additive surfacing:** Index "RS" section linking ratio; workbench cols added to the screener positioning group; themes as a screener scope; candidates' rationale surfaced on Stock ▸ News (candidates page kept + modernized).
- **Phase 3 — data-first / mobile polish:** tap fallback on SVG vizes; frozen panes on wide tables; filter-UI unification; glossary `?` hook; de-dup the stock Character panel.
- **Phase 4 — tracker enrichments:** watch Target/Stop columns; performance edit/reopen closed trades; surface-or-drop the near-dead columns.

Each phase is independently shippable and reversible. Phase 0 + 1 are pure no-regression and could ship first to bank the IA win.

---

## 7. Rendered templates (stencils shown in the design session 2026-06-23)

1. **Redesigned IA sitemap** — the 6 workspaces, each sub-nav, every screen placed, colour-coded by disposition.
2. **Screener + new chrome** — the consistent sub-nav strip, scope + column-group toggles, frozen Symbol column + 2-row header, Workbench columns folded into Positioning.
3. **Markets ▸ Rotation, unified** — RRG quadrant + RS-depth table (capture/Mansfield/RSI-of-RS preserved); Weather + Band as sibling tabs; Band de-orphaned.
4. **Stock dossier** — 8-tile verdict masthead + sticky tab bar with new News tab; de-duplicated Character; tap-able institutional zone lines.

Aesthetic preserved per D-UI-5/16: dark "instrument" theme, tabular numerals, heat-tints, inline micro-viz; the redesign elevates structure, it does not redecorate.

---

## 8. Decision log (UI redesign — fold into PROJECT_STATE § Decision log at build, canonical D-UI-18…)

- **D-UI-18 — Consistent per-workspace sub-nav.** Every workspace gets a sub-nav strip (Tracker's pattern generalized). *Why:* it's the single biggest findability fix — orphaned/inline-only screens get a predictable home; screen order becomes explicit.
- **D-UI-19 — Rotation = one shared sub-nav strip over three EXISTING routes (Map=rrg · Weather=rotation · Band=rsband).** *Why:* the three answer one question (cycle position) three ways and were fragmented/orphaned; a shared strip differentiates them and de-orphans RS-band **without rerouting** any of them.
- **D-UI-20 — Index page SURFACES Ratio additively (RS section/link); `/dash/ratio` stays at its URL.** *Why:* ratio is a sacred page — the duplication is reduced by cross-linking, not by moving ratio.
- **D-UI-21 — Screener is the superset; pillar pages are lenses that link into it ("Open in Screener").** Scan + Workbench KEEP their URLs (de-emphasized in nav, columns/affordances added). Realizes D-UI-7 *additively*. *Why:* reduces redundancy without removing or rerouting any page.
- **D-UI-22 — `/candidates` is kept + modernized (shared shell, deep-links); its news rationale also surfaces on Stock ▸ News.** *Why:* the Telegram digest links to it; surface its value in the app rather than removing a live, externally-linked page.
- **D-UI-23 — No-loss is verified by the § 4 census, not assumed.** Every disposition names where the value lives before anything changes.
- **D-UI-24 — Sacred-pages rule is binding (supersedes any "consolidate by reroute").** `/dash/ratio`, `/dash/rrg`, `/dash/compare` (and all user-facing routes) keep their URLs; the redesign only *adds* nav/links/columns and *deletes* unreachable dead code. Reconciles this redesign with `build-additive-never-replace` (session-31). *If a future pass wants to actually reroute one, it needs Ramana's explicit sign-off — never silently.*

---

## 10. Build log

**2026-06-23 — Phase 1 (consistent sub-nav) BUILT + verified locally; uncommitted.** Pure-additive, in `src/web/dashboard.py` only (parallel session active on the tree → minimal footprint; no parallel-owned file touched).
- Added `_SUBNAV` map + `_subnav(active)` helper; injected into `_shell` as a third header row (`.hrow3`/`.subnav` CSS). Every workspace now shows its sibling screens; Markets carries a **Rotation** group (Map · Weather · Band) that **de-orphans `/dash/rsband`** — confirmed the parallel-owned `rsband_view.py` page renders the new strip for free (it already calls `dashboard._shell`).
- Completed `_WS` (`rs`→markets; `mep`/`launchpad`/`concalls`→strategies) and made 8 routes pass a specific `active` key so the sub-item highlights correctly (rs, leaders, workbench, mep, conviction, concalls, launchpad, ratio).
- **Verified:** 28/28 routes 200 (incl. rrg/rotation/rsband mounted); all 8 strategy highlights correct; home shows no strip; tracker shows no double strip (keeps its own `_track_subnav`). Test harness = local `data/hermes.db` + TestClient.
- **Held (deferred):** the ~700-line dead-code deletion — provably unreachable, but a large diff is risky to reconcile while a parallel session is committing to `dashboard.py`. Do it when the tree is calm or coordinate. Tracker sub-nav "Import" item + action-loop fixes (Remove redirect, closed-trade confirmation) queued next.
- **On commit:** branch first (on `main`), update `PROJECT_STATE.md` (binding rule) with a D-UI-18 entry + Session log line.

**2026-06-23 — Phase 0 Batch A BUILT + verified (28/28 green + data-injected checks); uncommitted; dashboard.py only.**
- **Import de-orphaned** → added to `_track_subnav` (5th segment; highlights on the import page).
- **Action-loop fixes:** Remove now returns to the origin list (watch→`/dash/watchlists`, else portfolios); `/dash/performance?closed=1` shows a "position closed" confirmation banner — **caught + fixed a real bug I introduced**: the `closed` query param shadowed the existing `closed` closed-trades local, so it never fired; aliased the param (`just_closed`, `alias="closed"`). **Target/Stop columns** surfaced on watchlist rows (`_num` null-safe → muted dash).
- **Scan** table made sortable/filterable/exportable (`class="dt"`) — ends its data-first regression.
- **A4 frozen-pane DEFERRED:** `.scrwrap` sticky CSS is keyed to `table.scr`, not `table.dt`; `.dt` headers are already `position:sticky` — low value / regression-risk. Documented, skipped.

**2026-06-23 — Batch A+ (tracker action-loop completion) BUILT + verified; dashboard.py only.**
- **Closed-trade reopen** — new `POST /dash/track/reopen` (closed→open, clears exit_date/price/reason) + a "Reopen" action in the closed-trades log. Fixes the "fat-fingered close is unrecoverable" gap. Verified: status flips, exit fields cleared, redirect to portfolios, test row cleaned up.
- **`notes` column surfaced** — added a Notes textarea to the edit form + persistence in `dash_track_update`. Closes a genuine "value built but never surfaced" gap (the `stocks_in_play.notes` column existed but no UI ever read/wrote it). Verified round-trip: save → DB → read back in the edit form.
- Tracker action-loop now comprehensively fixed: Remove→origin · closed banner · reopen · watch Target/Stop · notes. 25/25 routes green throughout. Patch refreshed (+103/−23).

**2026-06-23 — PAUSED further build (parallel-contention blocker).** `src/web/cockpit.py` went parallel-owned (dirty) mid-session — the other session moved into the web layer. Batch B/C (Index RS card · Open-in-Screener lens links · glossary `?` hook) all require cockpit.py edits → blocked. Screener-touching items (B2 workbench-cols, B3 themes-scope) deferred as high-risk during active parallel web work. **No data lost meanwhile** — every route keeps its URL. The dashboard.py diff (+87/−19, Phase 1 + Batch A) is protected as a patch at `C:/Users/gotti/.claude/projects/D--Hermes/ui-redesign-phase01-dashboard.patch`; shovel-ready anchors for B1/B1b/C1 are in `docs/ui-redesign-EXECUTE.md`. Resume the blocked items when cockpit.py is clean.

## 9. Open questions for Ramana

- **OPEN-RD-1** — Strategies sub-nav has 9 items; acceptable, or group as "Synthesis (Conviction · Launchpad) + Pillars (6)"?
- **OPEN-RD-2** — Quality pillar has no dedicated page (links to screener). Build a real `/dash/quality` pt14 page, or keep it as a screener lens?
- **OPEN-RD-3** — `notes` column and the other near-dead fields (§ 4): surface or drop? (one explicit call each).
- **OPEN-RD-4** — Ship Phase 0+1 (hygiene + sub-nav) first to bank the no-regression IA win, before the Phase 2 consolidations?
