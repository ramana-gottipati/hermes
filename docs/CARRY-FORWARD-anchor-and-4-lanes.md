# CARRY-FORWARD ANCHOR — nav/chrome arc takeover + the next 4 parallel lanes

> **Created 2026-06-29.** This is the **anchor** for the next phase: it (a) documents everything the
> nav/chrome arc changed, (b) gives the takeover + takeaway, (c) classifies every open item by UI-vs-not,
> and (d) defines **four disjoint parallel lanes** so the next phase runs as 4 sessions, not one.
> Companion specs: `docs/nav-ia-DECISIONS-and-prompts.md` (the decided IA), `docs/navigation-and-structure-
> review.md` (the analysis), `docs/parallel-sessions-PLAN.md` (the ownership/contract doctrine).

---

## 1. TAKEOVER SUMMARY — where the system is right now
- **HEAD = `9def4ff`** on `main`. **Both gates PASS** (`chrome_gate.py` 11 legacy + 4 native; live 200-sweep 0 non-200). Live VPS `hermes-api` active.
- **The site now renders ONE unified chrome.** Every page (legacy + native) shows the **native single-row topbar**: cyan-dot `patearn` logo · `Markets · Screener · Strategies · Tracker · Trust` · `Search or ask Pat ⌘K` · ☰ + a contextual sub-nav. Verified IN-BROWSER on a fresh load (not just HTML).
- **Two shells still exist under the hood, but are visually unified:**
  - **NATIVE (ui_kit.shell):** `/dash/coverage`, `/dash/screen2`, `/dash/strategist`, `/dash/_ui`.
  - **LEGACY (dashboard._shell + cockpit, runtime-reskinned by `shell_skin`):** everything else (markets, screener, strategies, tracker, stock, mep, cpr, concalls, leaders, conviction, sectors, rrg, rotation, rsband, participants, wire, compare, themes, workbench, launchpad, testing, growth, wolfe, harmonic, …). `shell_skin.reskin()` now swaps the legacy 2-row header for the native topbar + retints the body.
- **Nav is registry-driven:** `src/web/lens_registry.py` is the SINGLE source — the nav, highlights, dossier tabs, screener columns, and cross-links all generate from it (no more 4-places drift).
- **Trust = the institutional lead wedge**, discoverable everywhere; **Lab → Trust "Strategy validation"** (rigor evidence). MEP findable as "Accumulation (MEP)"; Wolfe = overlay + scanner, reachable.

## 2. CHANGE LOG — the nav/chrome arc (newest first)
| Commit | What |
|---|---|
| `9def4ff` | **nav-overlap fix** — neutralised two legacy base rules (`nav{position:fixed;…}` mobile bottom-bar + `nav a{flex:1}`) that hijacked the unified topbar's `<nav>` (logo+search vanished, tabs stretched). Found via in-browser computed-style inspection. |
| `8d3e661` | **M1 chrome unification** — legacy pages now emit the native `uk-top` topbar (via `shell_skin`), replacing the 2-row `v2bar` header; gate flipped to lock it. |
| `7ad7255` | Trust lifted into the top row on legacy pages (superseded by M1 but the discoverability intent stands). |
| `e940fc9` | Trust = prominent `✓` chip + a "Strategy validation → Trust" trail in Strategies. |
| `ee7b4ad` | `/dash/testing` degrades gracefully when `research.db` absent + gated. |
| `85cc5a7` | **N3** cross-page glue — `nav_links.py`: lens-carrying `#tab` deep-links + breadcrumbs + lateral lens rails. |
| `d15a60d` / `6128d1b` | **N1** registry-driven Scope×Lens IA — Leaders→Markets, Hub→Strategist, Accumulation group, Wolfe overlay-only, Trust sub-nav. |
| `17526d0` | **N2** `/dash/testing` reframed as Trust "Strategy validation". |
| `e033b11` / `029e34f` | nav truth (no 404s in a clean checkout) + the durable `v2_surfaces.wire` repo hook (repo self-sufficient). |

(Earlier in the broader arc: A2 native UI foundation, F2/F3 Pat planner+analyst, G2/G3 charting+harmonic, H/H2 provenance — all on `main`.)

## 3. TAKEAWAY — the lessons this arc paid for (carry these into every lane)
1. **Look at the RENDER, not the HTML.** Three user-caught bugs (MEP/Wolfe hidden, Trust missing, logo+search overlapped) were invisible in the served markup — only the live computed styles / a screenshot revealed them. **Verify chrome in-browser (computed styles + screenshot) before claiming done.** The browser is wired (Claude-in-Chrome).
2. **Every move/rename needs a visible trail at the old location** — or it reads as "hidden" (MEP→Accumulation, Wolfe→overlay, Lab→Trust all bit us). Leave a signpost.
3. **Legacy bare-element CSS (`nav`, `nav a`, `header`) bleeds onto new components on reskinned pages.** When building new chrome on a legacy page, neutralise the legacy base rules (scope overrides under `body.uk-skin .uk-*`). Expect more of this during the body migration.
4. **The harness is law:** `bash scripts/regression_sweep.sh` (= `chrome_gate.py` clean-checkout + live 200-sweep) must PASS before any commit; revert-don't-force-fix on red.
5. **One registry, one source:** new nav/lens/column work goes through `lens_registry.py`, never hand-maintained in parallel.
6. **Freeze `dashboard.py`/`cockpit.py`** for everyone except the ONE designated owner (Lane 1) — this is the root of every collision and every "blocked" feature.

## 4. OPEN ITEMS — classified by UI vs not, and by lane
| Item | UI? | Lane | Blocked-by / note |
|---|---|---|---|
| **364-line `dashboard.py` WIP refactor** (uncommitted, unowned; folds chart-snippet imports + tracker sub-nav; net −96 lines; does NOT fix the blockers) | UI | **L1** | the central landmine — triage (land or shelve) FIRST |
| `cockpit.py`, `rrg_view.py` also dirty (parallel WIP) | UI | **L1** | reconcile with the dashboard.py decision |
| **Leaders page highlights Strategies›Positioning** (handler passes `active="stocks"`) | UI | **L1** | 1-line fix, but needs the dirty dashboard.py resolved first |
| **Pat true multi-turn thread** — `render_pat` in `dashboard.py` has no `Request`/cookie plumbing | UI (enables Pat) | **L1** (plumb) → **L4** (use) | F3-3 blocked here |
| **Native page-BODY migration** — headers unified; bodies still legacy-reskinned. Migrate the top demo path (Coverage→Markets→RS→Screener→Stock) to native `ui_kit` bodies | UI | **L2** | do via new native view modules; don't edit dashboard bodies |
| **Remaining legacy-rule bleed-through** (more `nav`/`header`/bare-element rules may leak onto other pages like the nav one did) | UI | **L2** | sweep + neutralise, verify in-browser |
| **Site-wide bounded charts** — roll the bounded engine onto RRG/RS/ratio/sparklines; the dead `hermes-charts.js` (/static 404) revive-or-retire; four-family controls; drawing engine | UI | **L3** | the RRG/RS/ratio live in frozen `cockpit.py`/`rrg_view.py` → coordinate with L1 |
| **Pat deepening** — multi-turn (post-L1), saved boards polish, richer intents, ranked top-N | UI | **L4** | multi-turn gated on L1 |
| **Survivorship deterioration re-test** (delisted-name concalls), **knowable_at** leak→0 + scheduler, **CCI Phase 3** backtest, data-licensing migration | **NOT UI** (backend research) | **L4** | research.db / provenance lane, zero web files |
| **PROJECT_STATE.md reconciliation** (the whole arc — deferred to avoid clobbering the shared file mid-parallel) | NOT UI (docs) | any lane at wrap / a wrap pass | 424KB shared file — append carefully |
| **Untracked durable files** to commit (`nav-ia-DECISIONS-and-prompts.md`, `navigation-and-structure-review.md`, new modules like `mini_rrg.py`, `cci_*.py`, `enrich.py`, `code_review.py`) + **junk** (`8}]` accidental file) | NOT UI (housekeeping) | **L1** or a cleanup pass | triage; commit real, `git rm` junk after sign-off |

## 5. THE FOUR LANES (disjoint ownership; UI-classified; per-page)
**Binding:** only **L1** may edit `dashboard.py`/`cockpit.py`/`rrg_view.py`. L2/L3/L4 build in NEW modules + runtime wraps and coordinate with L1 only at contracts. Every lane: harness PASS + **in-browser verify** before commit; backup `*.bak-<lane>`; commit only owned files.

| Lane | UI? | OWNS | MISSION |
|---|---|---|---|
| **L1 — Dashboard core & unblocks** | UI (structural) | `dashboard.py`, `cockpit.py`, `rrg_view.py` (SOLE owner) | Triage + land/shelve the 364-line WIP; fix the leaders highlight; plumb `Request`/`tid` into `render_pat` (unblock L4 Pat threading); commit/clean the untracked-real + junk files. THE unblocker — run first. |
| **L2 — Native bodies & chrome polish** | UI | `ui_kit.py`, `shell_skin.py`, `v2_surfaces.py`, NEW `src/web/*_native.py` | Migrate the top demo-path page BODIES (Coverage→Markets→RS→Screener→Stock) to native `ui_kit`; sweep + neutralise remaining legacy-rule bleed-through; verify each in-browser. |
| **L3 — Charting site-wide** | UI | `chart_view.py`, `stock_chart.py`, `hermes-charts.js`, `wolfe*`, `harmonic_*`, NEW chart modules | Bounded responsive chart engine site-wide (RRG/RS/ratio onto it); four-family controls; drawing engine + magnet + persistence; revive-or-retire the dead `hermes-charts.js`. |
| **L4 — Pat copilot + research wedge** | UI (Pat) + backend (research) | `src/pat/*`, `strategist_view.py`, `screener_plus.py`, `provenance.py`, `cci_*`, research.db lane | Pat multi-turn (post-L1) + saved boards + richer intents; the survivorship re-test, knowable_at→0, CCI Phase 3 backtest, data-licensing. Descriptive-only, provenance-stamped. |

**Sequencing:** L1 first (unblocks leaders + Pat threading + frees the frozen files). L2, L3, L4 start in parallel immediately (disjoint files); L4's Pat-multi-turn and L3's RRG/RS-on-the-engine wait on L1's contract points but the rest of each lane proceeds. Pasteable per-lane prompts: build them from this table + `docs/parallel-sessions-PLAN.md` §3 (operating protocol) + the takeaway §3.

## 6. CARRY-FORWARD RISKS (must not be lost)
- The **dashboard.py/cockpit.py/rrg_view.py dirty WIP** is real, uncommitted, unowned — L1 must decide its fate before any of those files can be safely touched. Do NOT `git add` them blindly (cross-absorption).
- **`scripts/regression_sweep.sh`** shows as modified — confirm its current form still runs `chrome_gate` + the live sweep before relying on it.
- **A junk file literally named `8}]`** exists (a botched-command artifact) — verify empty, then `git rm`/delete.
- Untracked durable docs (the nav specs) should be committed so the next sessions inherit the decisions.

## 7. CODEX = continuous reviewer
Codex reviews this arc + the 4-lane plan (`codex-bridge/req-05-*`) and is asked to **continuously review each lane's commits + improvements** as they land. Claude (lead) filters Codex's findings → PROPOSALS-NN → Ramana approves → implement.
