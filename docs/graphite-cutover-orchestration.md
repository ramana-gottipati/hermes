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
| W1 | Graphite stock page (cutover blocker; port of `/dash/preview/stock` M4 hub) | 🔄 dev DONE, review pending | 1 dev + 1 review + 1 verify | `lane/w1-stock-page`: `/dash/home/stock?sym=` + 3 new home modules + 17-test gate; suite 869/0/1 |
| W2 | M-Markets estate (34 markets surfaces, 4 family lanes) | queued | 4 dev + 1 review + 1 verify | — |
| W3 | M7 Strategies (18) + Tracker (6) | queued | 2 dev + 1 review/verify | — |
| W4 | M8 Screener (5 surfaces) | queued | 1–2 dev + 1 review | — |
| W5 | M6 Journey/help layer (trust 11) | queued | 1 dev + 1 review | — |
| W6 | Cutover mechanics (nav promotion · retire old preview · isolation-contract rewrite · parity 100% accounted) | queued | 1 dev | — |
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

- **2026-07-27 · W1 dev (Opus), branch `lane/w1-stock-page` (base `f1ee223`):** the Graphite stock
  page `/dash/home/stock?sym=` shipped — `src/web/home/{stock_reads,stock_chart_g,stock_page}.py`
  + one route on the existing home router + one anchored `INTERNAL_DEV` entry +
  `tests/test_home_stock_page.py` (17). **Zero edits to `components.py` / `reads.py` /
  `v2_surfaces.py`** — the hot multi-lane files are untouched, so integration is a clean add.
  Suite **869 passed / 0 failed / 1 skipped** (baseline 852 + 17); Graphite+governance cluster 108
  green; `doc_hygiene_gate` 5/5.
  - **Three real bugs the adversarial pass caught (all fixed + pinned):** F&O columns were invented
    (`oi`/`oi_change`/`pcr_oi` vs canonical `fut_oi`/`fut_oi_chg`/`pcr`) — would have been silent em
    dashes on the box; **`wolfe_signals` keys on `sym`, not `symbol`** — the query inherited from
    `hub_sections_v3.load_core` raises and is swallowed, so the Wolfe badge can never fire (**the M4
    hub still has this bug** — worth a fix wherever the preview survives); and `str.capitalize()`
    mangled stored grades ("tier B" -> "tier b"). New read-contract test builds the schema the way
    production does (`db._init_ddl` + the capital_allocation/wolfe/rs_phase module DDLs).
  - **Payload:** a 6,000-session `?chart=max` island was 854KB of the 1MB archetype budget; rows now
    serialise as compact arrays (519KB, -39%, full history kept), which also bought back the classic
    traded-vs-delivered-value pane.
  - **Chart verdict (from the diff, not vibes):** fork base `20b28161` = `stock_chart.py` @ `392ec2c`;
    the single newer legacy commit is `f830a0e` (6 hunks; click-to-place + fullscreen-overlay trim +
    in-chart brand badge). The fork was **not** regenerated — `stock_chart_v3` is BANNED by name in
    `test_home_isolation`, and the classic engine binds legacy DOM + the banned `dashboard`, so the
    Graphite page can import neither. A Graphite-native chart carries identity/zones/panes/fullscreen/
    branded-PNG; the analyst workstation (drawings · fib · overlays · compare · indicator panes) is
    explicitly NOT carried and stays on classic `/dash/stock`.
  - **Parity, not over-claimed:** classic `/dash/stock` is not a registry lens (no row); no lens is
    fully ported. Eight lenses gained DEFERRED-with-note entries recording per-symbol-tab coverage.
    PORTED stays 2.
  - **For W6:** this route is an intentional `nav_integrity_gate` orphan until the flip; the parent
    nav link, repointing `components.sym_link` to `/dash/home/stock`, and retiring
    `/dash/preview/stock` all belong to the cutover.

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
