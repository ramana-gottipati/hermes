# Graphite Cutover — orchestration ledger

**Lifecycle: TRANSIENT** — the running program ledger of the mega-orchestration session
(2026-07-27, Fable-5 parent + Opus-5 child sessions). Retire when the cutover completes: fold
outcomes into `PROJECT_STATE.md` §Session log + `docs/redesign-coordination.md`, then `git rm`
this file and `docs/graphite-home-carryforward.md` together. Register in `docs/DOC_INDEX.md`
at first commit.

## 0. Program charter (owner go, 2026-07-27)

Owner (Ramana) directive: complete the new design — migrate the whole classic estate into the
Graphite identity, orchestrated from one parent session with autonomous Opus child sessions
reporting back until the loop closes. This message is treated as the owner GO for M6/M7/M8 +
M-Markets + cutover, executed in the Graphite identity (already owner-directed through the
§5 A–E queue). Pixel sign-off stays with the owner via a `?v=N` link per deployed wave.

Binding rules for every lane: classic site byte-frozen · additive + isolated (`.g-*`, no
legacy/preview imports) · fixed-size internally-scrolling boxes · demo/sample honesty ·
descriptive-only fences + evidence links · Free never crippled · primary sources only ·
worktree isolation, atomic add→commit, stage only own hunks · verify pushes by content ·
deploys serialized by the parent per the §6 recipe (writer-safe, never ~14:01 UTC) · argue
back + record verdicts on genuine forks.

## 1. Wave board

| Wave | Scope | Status | Sessions | Proof / commits |
|---|---|---|---|---|
| W0 | Recon + briefing pack + env probes | ✅ DONE | 1 recon (Opus) | BRIEFING.md + WORKLIST.md in session scratchpad; findings §2 |
| W0.5 | Reconcile diverged main↔origin (68 local / 33 origin, base `09052db`) | ✅ DONE | 1 reconcile (Opus) | merge `35c8a47` pushed + content-verified; suite **852/0/1**; doc gates PASS; shared checkout ff'd |
| W1 | Graphite stock page (cutover blocker) | review ✅ → CONVERGENCE 🔄 | dev + review + converge | dev `f0f1926` → review APPROVE-W-FIXES `76c8586` (11 bugs fixed+pinned, chart browser-verified, 880/0/1). 🔴 COLLISION: a sibling session shipped its OWN stock page on main (`815c941`, `stock_view.py`) and the owner cut the landing over on top of it (D148). `lane/w1-converge` decides which engine serves `/dash/home/stock` + folds the loser's strengths |
| W2 | M-Markets estate (32 remaining, 3 lanes) | A ✅ · B ✅ · C 🔄 | 3 dev + wave review/verify | A `lane/w2-internals` @ `586c04e` (885/0/1; 11 PORTED; 4 pages) · B `lane/w2-rs-rotation` @ `2bb2cb3` (869/0/1; 8 PORTED + 3 honest-DEFERRED w/ owed-notes; 3 pages) · C resumed post-restart (13 files WIP at base) |
| W3 | M7 Strategies (18) + Tracker (6) | tracker ✅ · strategies 🔄 | 2 dev + wave review/verify | tracker `lane/w3-tracker` @ `e104b39` (872/0/1; 5 PORTED + 1 merge-DROP — first fully-accounted workspace; XIRR fidelity-gated, TWR headline) · strategies resumed post-restart (6 files WIP) |
| W4 | M8 Screener (5 surfaces) | 🔄 RUNNING ∥ | 1 dev + wave review | `lane/w4-screener` — screen2 REBUILD (URL-state · server CSV · <500KB budget) + themes; screener/tags-review/workbench verdicts |
| W5 | M6 Journey/help layer (trust 11) | 🔄 RUNNING ∥ | 1 dev + wave review | `lane/w5-journey` — trust pages + `journey.py` (nudge/help/teaching-empty per M6 spec v1.1) + Pat-dock reconciliation (no third Pat) |
| W6 | Cutover mechanics — SCOPE SHRANK: the landing flip shipped EXTERNALLY (D148, owner call, LIVE: `/dash` → 302 `/dash/home` via new `src/web/home/cutover.py` middleware; classic byte-identical at `/dash/classic`; lens-registration mechanism (a) explicitly REJECTED — would drift classic nav). Remaining: old-preview retirement (owner OK'd) · isolation-contract rewrite (#3/#5) · Graphite in-app nav wiring (`shell.DESTS`) · `components.sym_link` retarget · parity 100% + docstring fix | queued | 1 dev | — |
| W7 | Full-estate walk on box + docs fold + ledger close | queued | walk fleet + parent | — |

## 2. W0 findings (2026-07-27)

- Parity (computed, not prose): **74 surfaces · 261 metrics · 16 strategies**; PORTED 2
  (markets→M5 Today, wire→M3 dock) · DEFERRED 72 · UNSCOPED 0. By workspace: markets 34 ·
  strategies 18 · trust 11 · tracker 6 · screener 5. Module docstring drift (says 73/257/17)
  — fix in W6.
- Suite baseline: `python -m pytest -q` = **1 failed / 851 passed / 1 skipped** with plain
  `python` (hermes-agent venv). 🔴 The in-repo `.venv` is a stale py3.13 env, no numpy —
  NEVER use it. The single red (`test_rule_lab` byte-verbatim) is already fixed on origin.
- 🔴 main↔origin DIVERGED 68/33 (merge-base `09052db`; `49c1223`⇄`670a7df` same change
  cherry-picked twice). The 68 local = the entire unpushed Graphite lane. → W0.5.
- `codex` CLI present (0.133.0). Gemini reviewer still down.
- Local `data/hermes.db` is a 15 MB fixture — structure verifiable locally (TestClient 200s),
  data only verifiable on the box. Standing correction #9 holds.
- Hot/co-edited files for parallel lanes: `v2_surfaces.py` · `lens_registry.py` ·
  `test_dash_route_registry.py` (anchored-insert only, never full-file) · `src/web/home/
  components.py` (2123 lines) + `reads.py` (partition by function block or serialize).
- `stock_chart_v3.py` fork base stale again (BASE_MD5 `20b28161` vs 5 newer legacy chart
  commits on origin) → W1 carries the re-pin/regenerate verdict.
- rrg/rotation already partially ported (`/dash/home/rotation` reuses canonical
  `rrg._rs_ratio_momentum`) — add explicit SURFACE_PARITY entries, don't re-scope into W2.
- W6 named sub-task: `test_home_isolation` assertions #3/#5 (classic carries no Graphite
  marker; default chrome never links `/dash/home`) become false BY DESIGN at cutover — the
  replacement contract must be specified BEFORE the flip.
- 12 DROP-candidates (screener-classic · stealth · cpr · launchpad-track ·
  insider/ratings/sast/shp→one hub · factor-league→library · model-books · evidence-pack ·
  inbox · tags-review · workbench · early-signals) — each needs a written rationale or the
  parity gate fails. Lanes propose; parent ratifies; disclosed in wave reports (reversible —
  classic stays reachable).

## 3. Lane log (append per lane completion)

- **2026-07-27 · W0 recon (Opus):** parity 74/261/16 derived by execution; suite baseline
  851/1/1 (plain `python`; repo `.venv` stale — never use); divergence 68/33 found; codex CLI
  0.133.0 present; briefing pack + work-list written to session scratchpad.
- **2026-07-27 · W0.5 reconcile (Opus):** merge `35c8a47` (parents `a4828e4` + `ea276c2`),
  pushed + content-verified (`rev-list --count` 0, diff empty). Only 2 conflict files:
  PROJECT_STATE.md (2 hunks, UNION, nothing dropped) + `src/web/stock_chart.py` (local taken —
  proven strict superset: origin's fullscreen work already re-landed via `f830a0e`; only
  click-to-place differed). Cherry-pick twin `49c1223`⇄`670a7df` deduped clean. Suite
  **852 passed / 0 failed / 1 skipped**; `doc_hygiene_gate` 5/5 + doc/pat/strategy tests 21
  green. Parent then ff'd the shared checkout after md5-proving the 8 sibling untracked
  `research/explosive_moves/*.py` byte-identical to origin (backup in session scratchpad
  `sibling-backup-w05/`), deleted them, `merge --ff-only` → `D:\patearn` at `35c8a47`.

- **2026-07-27 · W1 dev (Opus):** `/dash/home/stock?sym=` BUILT — `stock_reads.py` +
  `stock_chart_g.py` (Graphite-native chart; `stock_chart_v3` fork NOT re-pinned: banned by name in
  the isolation gate + binds legacy DOM, so a re-pin would polish an unreachable module) +
  `stock_page.py` + 17 tests. Suite **869/0/1**; isolation 8/8; page 132 KB, 0.04-0.07s;
  `?chart=max` gate-asserted <700 KB. X-04/07/09 setups block shipped (bounded SELECT, not
  `latest()` — that calls `ensure_table()`, a WRITE, on a read-only page). Dropped-with-reason:
  drawings/overlay engines (banned imports; linked to classic) · seasonality section (legacy render
  module) · track-capture (home already owns the write path). Branch `lane/w1-stock-page`
  @ `f0f1926`, push content-verified. Candid handoff to review: production-schema read-contract
  risk (2 self-caught invented-column bugs), chart JS runtime-untested, zero real-data exposure.
- **W1 dev cross-lane finding:** the M4 hub (`hub_sections_v3.load_core`) queries `wolfe_signals`
  by `symbol` but the table keys on `sym` — its Wolfe badge has NEVER fired. Not fixed (module
  retires at W6); recorded so the retirement isn't mistaken for losing a working feature.

- **2026-07-27 · W1 review (Opus): APPROVE-WITH-FIXES-APPLIED, `76c8586`.** 11 bugs found+fixed,
  each test-pinned RED→GREEN: wolfe `ORDER BY id` on an id-less legacy table (badge silently dead,
  observed on the real fixture) · 2 unguarded `stock_signals` joins · BE-series blank chart ·
  `json.dumps` bare-NaN killing the whole chart in a browser (`allow_nan=False` + finite guards) ·
  `OverflowError` escape · `M&M` HTML-escaped-not-URL-quoted · `compression_pctile` fraction
  rendered raw · nan-prints · absent-flag "no" → "—" · conviction tile over-claim (docstring said
  "labelled a heuristic", the HTML had no such word). Schema audit 15 tables clean otherwise.
  Chart RUNTIME-verified in a real browser (uvicorn + LWC: crosshair units, 6 ranges, fullscreen,
  screenshot, zero console errors). Codex pass: 9 findings, 8 adopted, 1 refuted. Suite 880/0/1.
- **2026-07-27 · EXTERNAL (sibling session + owner): D148 LANDING CUTOVER LIVE.** `815c941` (its
  own Graphite stock page `stock_view.py`) → `4315ad7`/`3d13d97`: `/dash` → 302 `/dash/home` via
  new `src/web/home/cutover.py` pure-ASGI middleware; `/dash/classic` internally rewrites to the
  byte-identical classic home. Owner explicitly REJECTED lens-registry registration (mechanism a)
  — it would drift the generated classic nav. Only the old-preview retirement remains from D148's
  scope. CONSEQUENCE: two rival stock pages → `lane/w1-converge` decides on evidence (feature/bug
  matrix + box md5s) and folds the loser; parent pushed the sibling's unpushed D148 pair to origin.
- **2026-07-27 · PROCESS RESTART:** the parent CLI exited with 6 lanes in flight. Recovered:
  W2-B and W3-B had finished+pushed (reports re-sent, worktrees verified clean, nothing outside
  their heads); W2-C (13 files WIP) · W3-A (6) · W4 (1) · W5 (1) resumed from transcripts.
  Parent's stalled W1 merge aborted cleanly (superseded by the convergence lane).
- **2026-07-27 · W2-A (Opus):** 11 keys → 4 pages (`/dash/home/internals` · `flows` · `events` ·
  `attention`), all 11 PORTED, no drops; fences travel (PEAD 0.10-vs-0.85 precedes its table;
  F&O Phase-0; surveillance "context, never a gate"). Suite 885/0/1 (+33). `586c04e`.
- **2026-07-27 · W2-B (Opus):** 11 keys → 3 pages (`rotation?view=` 4-in-1 · `strength` ·
  `sectors?tab=`); engines reused, renderers never (gate-asserted, 16 modules); `band_verdict`
  instructional keys never reach the DOM; fundamentals get NO sample data (indistinguishable-
  from-real rule). 8 PORTED + 3 DEFERRED w/ owed-notes. Suite 869/0/1 (+17). `2bb2cb3`.
- **2026-07-27 · W3-B (Opus):** 6 keys → 5 routes + merge (tracker = FIRST fully-accounted
  workspace: 5 PORTED + model-books DROPPED-as-merge). XIRR is fidelity-GATED (`cashflow_fidelity`
  on live rows; position-ledger books print the reasons, not a number; clean single-lot book
  released +23.4%); headline = chained TWR (arriving positions never count as gains). Suite
  872/0/1 (+20). `e104b39`. Handoff: `shell.DESTS` line conflicts with D148 (take main's);
  `components.sym_link` retarget = one line at integration.

- **2026-07-27 · W2-C (Opus):** 10 keys → 5 routes (`/dash/home/seasonal` 4-view · `patterns`
  wolfe+harmonic · `anatomy` · `own-history` · `compare` NEW route, classic untouched).
  `early-signals` DROPPED on a TRACED mechanism (owns no data/compute: turn-ups = phase_movers
  already on rotation; bullish half = divergence_board._scan = /dash/divergence; residue = a
  display preset). 1 PORTED (seasonal-calendar, every block) + 8 DEFERRED with per-block
  SHIPPED/OUTSTANDING notes — deliberately strict: "reads well while missing load-bearing blocks
  is not ported". Wolfe ported via plain SQL, zero collision with the hot lane. Frozen
  `seasonal_tape.__doc__` untouched. Suite 871/0/1 (+19). `882c668`, content-verified.
  🔴 CROSS-LANE CORRECTION (for the W2 wave review): stock-grain `rs_phase` flips are NOT on the
  signal-alerts bus (its `rs` lens is INDEX-grain over rsband_signals) — the home's What-changed
  does NOT carry them; the rotation port must. Also: 3 SHARED call sites still deep-link classic
  stock (`components.sym_link`:41 · `_hm_tile`:1142 · pat_dock chip JS:210) — retarget queued as
  an isolated integration commit.
- **2026-07-27 · INTEGRATION-1 dispatched:** serial merge of the four finished lanes
  (w2-internals → w2-rs-rotation → w2-seasonal-patterns → w3-tracker) onto origin/main
  (`4f09fdc`) on branch `lane/integrate-1`; suite after every merge; sym-link retarget as a
  separate labeled commit; parent fast-forwards main after content verification. The
  W1-convergence branch merges main LAST (deepest conflict, decided on its own evidence).

- **2026-07-27 · W3-A (Opus):** 18 keys → 11 routes under `/dash/home/strategies` — ALL FIVE
  ratified consolidations built (library=factor-league+classics w/ 🧑/🏠/📚 filters ·
  positioning=stocks+stealth · credibility=concalls+fingerprint · ownership=insider+ratings+
  sast+shp · launchpad+evidence-tab). PORTED 16 · DROPPED 1 (`cpr`, rationale VERIFIED against
  source) · DEFERRED 1 (`shp` quarter-matrix built but research-store unverifiable off-box).
  Every fence carried (D138 above-headline · ret/vol labels — the label gate caught 2 of its own
  lines · CCI coverage-first · MEP D62 · launchpad no-edge · Screener.in provenance). Shared
  files insert-only +181/−0; components/reads untouched. Suite 852/0/1 held + workspace selftest
  17/17. `e361ccf`, content-verified.
  🔴 BRIEF CORRECTION (a briefed fact was false — recorded): `/dash/growth` does NOT run on the
  `screener.py` fundamentals path (reads `concall_signals` only). The real primary-source
  exposure = the concall corpus (~98.6% Screener.in-discovered links) behind growth+credibility
  and `research.db.fundamentals_history` behind pt14-quality on conviction — disclosed on all
  three, correctly attributed.
  🔴 WAVE-REVIEW DIRECTIVE (from its swallowed-error hazard): read layers that return `[]` on
  SQL error render PLAUSIBLE EMPTY pages that pass 200-smoke tests — every lane's review must
  hand-check fixture-absent tables against engine DDL (this pattern caught a dead
  `launchpad_signals.trade_date` key). W6 additionally owes: nav orphans now 5→16 (allowlist or
  link) · `shell.DESTS["Strategies"]` repoint · Pat registration + glossary keys at cutover.

- **2026-07-27 · W1-CONVERGENCE (Opus): VERDICT — Lineage B serves `/dash/home/stock`.**
  `lane/w1-converge` @ `1816d9f` (true merge, parents `3d13d97`+`76c8586`), suite **899/0/1**
  (main's own baseline 866; zero regressions; all 28 W1 tests green). Evidence: B was
  adversarially reviewed + browser-walked (A never reviewed — and two of B's fixed bug classes
  were CONFIRMED PRESENT in A by observation: the `M&M` &-escaping bug is LIVE-REACHABLE today
  (box has ARE&M · GET&D · AXIS-IT&T…) and `_fmt(nan)`→'nan'); B is the only lineage replacing
  what `/dash/preview/stock` uniquely served (setups·structure·credibility·quality·F&O·rail —
  THE cutover blocker); 28 gates vs 10. FOLDED from A: the 5-metric 3-year CA-adjusted
  Own-history panel + its adjustment gate · the Ownership & disclosures block (SEBI
  PIT/SAST/Reg-29 — A's only no-counterpart block) · watchlist write + classic hatch (URL-quoted
  in the fold, fixing M&M). `stock_view.py` retired (history preserved at `815c941`; a gate
  blocks its return). Box read-only check: Lineage A live (all 9 home/*.py md5==origin), full
  F&O schema + 4,614 x_setups rows present → Setups/F&O render real data on deploy. Registry
  auto-merge produced a SILENT duplicate dict key (last-wins) — deduped + pinned by a
  source-line-counting gate. Deploy notes banked in the lane report (hasattr: stock_page.compose
  /head_assets/picker · stock_reads.clean_symbol; unpkg CDN dependency w/ honest offline
  degrade; page changes visibly for the owner: 4 blocks → 10 sections + rail + real chart).

- **2026-07-27 · W4 (Opus):** screen2 REBUILT at `/dash/home/screen` + themes at
  `/dash/home/themes`. The 3 recorded debts fixed BY CONSTRUCTION: payload 2.3MB → 103KB default
  / 261KB worst (a cell budget scales rows to column width, disclosed in the pager — and the
  lane caught that a fixture-passing live check was NOT sufficient evidence, so the gate PROJECTS
  full pages at every size×column-set); server CSV honoring active filter/sort/columns
  (test-pinned); URL-state round-trip proven over 11 combinations. 72-column pool / 14 families /
  6 named views per §J; saved screens are now URLs. Verdicts: screen2+themes PORTED · screener
  DROPPED (dup, classic stays for bookmarks) · tags-review NA (owner write-desk) · workbench
  DROPPED–ABSORBED after a REAL examination — it DID own a distinct claim (the key-price family),
  which now ships as the "Key-price read" view; the evidence travelled. PARENT RATIFIES: the
  fundamentals family (~15 §J cols) deliberately NOT built — sourced from the `screener.py`
  vendor path under Guardrail #8 remediation ("do not extend"); the guardrail outranks the §J
  listing. M8 stays PLANNED until the box walk. Suite 876/0/1 (+24). `25a6c6f`, content-verified.

- **2026-07-27 · INTEGRATION-1 (Opus) → main `5115eee`:** four lanes merged serially, suite
  866 → 899 → 916 → 935 → **955/0/1** (+89, zero regressions); AST-checked merged dicts
  (SURFACE_PARITY 40/40 unique · INTERNAL_DEV 26/26 · _ROUTER_SPECS 63, zero dup routes).
  Parity official: **PORTED 27 · DEFERRED 45 · DROPPED 2 (rationaled) · 0 UNSCOPED**; metrics
  265. All 25 smoke routes 200 incl. /dash 302→home and /dash/classic. Justified doctrine
  deviation (ratified): W3-B's DESTS Tracker retarget KEPT — main never touched that line, no
  conflict existed, dropping it would have silently lost a shipped change. Sym-link retarget
  commit `5115eee`: 2 of 3 briefed sites were ALREADY done on main (kickstart-pick-verify);
  the real remainder was pat_dock chip JS + tracker movers chips. Parent ff'd main + pushed
  (content-verified 0/0). SMELL for W6: `nav_integrity_gate.py` and `INTERNAL_DEV` have drifted
  into two disagreeing allowlists (script exit 1 with 6 orphans ALREADY on pristine main; 17
  post-integration) — one cleanup owed before nav wiring. Pre-existing: `_ROUTER_SPECS` carries
  `seasonal_screen_view` at two paths (not a merge artifact).

- **2026-07-27 · W5 (Opus):** 11 trust keys → 8 pages + 1 fragment (`proof` · `validation`
  (+`?pack=1` absorbing evidence-pack — VERIFIED an assembly; its 2 self-originating claims kept)
  · `prereg` · `rule-lab` · `replay` · `glossary` · `strategy-ref` · `guide` · `pat/ask`).
  The M6 layer ships as `journey.py`: one-shot nudge · persistent help · `teaching_empty()` whose
  contract is ENFORCED by the component (bare "no data" raises) · 4 persona exits — adoption via
  `extra_head=journey.assets()`, zero shared-file edits. Pat reconciled, NO third Pat: the dock
  gained closed-vocab model-free `resolve()` (AST-proven no model/network import — ₹0); threads/
  boards/feedback honestly not carried. 10 PORTED + 1 NA (inbox = owner write-desk). Suite
  883/0/1 (+31). `5bf5414`, content-verified. PARENT RATIFIES its unilateral verdict: ZERO Pro
  gating across the Proof estate (ratified §J — evidence is never gated), gate-enforced.
  🔴 Banked: classic `strategies_view._public` sanitizer LEAKS on live `/dash/strategy-ref`
  today (`S164BB`/`S155-e`/`S1234` escape the regex) — W5's port widens it + adds a line-drop
  backstop; classic byte-frozen so recorded, not patched. 🔴 `BLOCKING_ROWS` still carry the
  pre-D142 ratio name byte-verbatim under a machine gate (page prints the correction beside the
  quote) — ledger+mirror must move together. Review verdicts owed: `spec_sheets._SHEETS`
  imported as content (data-not-renderer — defensible, wants a ruling) · glossary `_ENTRIES`
  private-accessor use.

- **2026-07-27 · INTEGRATION-2 (Opus) → main `994ad06`:** four branches merged (converge →
  strategies → screener → journey), suite 955 → 988 → 1012 → 1043 → retargets `e17e518` (1045)
  → main-remerge + D148-b gate repoint `994ad06` = **1049/0/1**. Parity FINAL-BUILD state:
  **PORTED 55 · DEFERRED 12 · DROPPED 5 · NA 2 · 0 UNSCOPED** (74 surfaces · 265 metrics).
  6 parity-key collisions resolved by the ratified board-wins-dossier-clause precedent; a
  one-Pat gate false-positive (substring 'pat' matched patterns_pages) tightened to a
  package-wide content scan, falsified before landing. D148-b repoint RATIFIED: escape-hatch
  constants → stock_page.py/`g-sclassic`, CLASSIC_EXITS enumerated w/ citations + a
  dead-exception detector; deviation ratified — cpr deep-link RETARGETED to the stock page
  rather than excepted (SECTIONS carries cpr; stronger than licensing). Main's 3 external
  commits identified: `49f1f7e` ambient-DB test fix (the banked chip — CLOSED) · `aea042d`
  D148-b gates (tests only) · `c8cc22d` sectors drill empty-state fix (sibling W2-B follow-up).
  Retargets: model-books browse door → strategies/books (follow door stays classic — it's a
  WRITE, the books page is read-only); DESTS Markets/Strategies repointed, machine-pinned
  (previously ZERO assertions read those hrefs). Parent ff'd + pushed main (0/0).
- **2026-07-27 · DEPLOY dispatched** (main `994ad06` → box): home package + sideways_parity +
  anchored v2_surfaces tuples + glossary; stock_view.py retired on box; import/hasattr sweep
  under the prod venv before restart; writer-safe restart; full real-data walk incl. the
  &-ticker probe (`ARE&M`); rollback = `.bak-w6` set. Owner links hand-off on completion.

### Banked findings (not cutover work, tracked so they aren't lost)
- `tests/test_home_featured.py::test_conviction_now_caches_by_date` silently passes/fails on
  AMBIENT DB presence (`data/hermes.db` is CWD-relative; empty schema-only DB → cache skipped
  by design → test red in any fresh clone/worktree). Latent CI landmine — spun off as a
  separate task chip.
- `scripts/nav_integrity_gate.py` (NOT in the pytest suite) fails with 5 pre-existing orphans:
  `/dash/home` · `/dash/home/_kit` · `/dash/home/rotation` · `/dash/sideways-parity` ·
  `/dash/wolfe/learnings` — intentionally unlinked until cutover. **W6 must** either add
  `INTENTIONAL_NON_NAV` entries or real nav links at the flip.

## 4. Owner hand-offs

_(a `?v=N` link per deployed wave lands here)_
