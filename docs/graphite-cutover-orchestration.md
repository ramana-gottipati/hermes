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
| W1 | Graphite stock page (cutover blocker; port of `/dash/preview/stock` M4 hub) | 🔄 RUNNING | 1 dev + 1 review + 1 verify | — |
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

### Banked findings (not cutover work, tracked so they aren't lost)
- ~~`tests/test_home_featured.py::test_conviction_now_caches_by_date` silently passes/fails on
  AMBIENT DB presence~~ → **CLOSED 2026-07-27 (`64e85da`), test-only + additive.** The test now seeds its own
  `stock_signals` date into a `tmp_path` DB and monkeypatches `src.core.db.DB_PATH` (the real
  `get_conn()` resolves that global per call), plus `reads._CONV_CACHE` → `{}` so module state
  leaks in neither direction. Mechanism correction for the record: `DB_PATH` is **not**
  CWD-relative — `src/core/db.py:18` resolves it module-relative
  (`Path(__file__).resolve().parents[2]/"data"/"hermes.db"`), i.e. per **repo/worktree root**, and
  `_init()` at import auto-creates it schema-only. So `MAX(trade_date)` was NULL, `conviction_now`
  skipped the cache BY DESIGN, and the second call recomputed. Proof: passes with the ambient DB
  moved aside entirely (true fresh-clone), and a falsification probe confirms the assertions still
  bite (empty `stock_signals` → `calls=2`, empty cache). Coverage was *strengthened*, not weakened —
  it now also pins that the key IS `MAX(trade_date)` and that a nightly date roll evicts the stale
  entry. Suite: **852 passed / 1 skipped**.
- `scripts/nav_integrity_gate.py` (NOT in the pytest suite) fails with 5 pre-existing orphans:
  `/dash/home` · `/dash/home/_kit` · `/dash/home/rotation` · `/dash/sideways-parity` ·
  `/dash/wolfe/learnings` — intentionally unlinked until cutover. **W6 must** either add
  `INTENTIONAL_NON_NAV` entries or real nav links at the flip.

## 4. Owner hand-offs

_(a `?v=N` link per deployed wave lands here)_
