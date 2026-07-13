# Parallel-Sessions PLAN — decoupled big wins (3 + 1 lanes)

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the parallel-lanes program completes (RUN-BOOK-by-rule until then). Registered in `docs/DOC_INDEX.md`.


> **Created 2026-06-28.** Ramana: plan the big wins across ≥3 parallel sessions, decoupled so the work
> isn't interdependent; streamline the process + the screeners; give pasteable per-session prompts.
> **Companion to** `docs/ui-restore-and-migration-TRACKER.md` (the what) — this is the HOW (who owns
> what, the contract, the prompts). Registered in PROJECT_STATE § open items + memory.

## 0. Why we keep colliding (the root cause this plan fixes)
`src/web/dashboard.py` + `src/web/cockpit.py` render almost every page (markets, screener, strategies,
mep, cpr, concalls, conviction, workbench…). Every session that wanted to change a page edited the SAME
file → clobbered nav, renamed MEP, orphaned Wolfe, left two UIs. **Fix: freeze `dashboard.py`/
`cockpit.py`/`main.py`. All new work lands in NEW modules + runtime wraps** (the proven `v2_surfaces.py`
monkeypatch pattern). Sessions then own disjoint files and never touch each other's.

## 1. File-ownership matrix (BINDING — a session edits ONLY its column)
| Lane | OWNS (may edit/create) | MUST NOT TOUCH |
|---|---|---|
| **A — Chrome & Migration** | `ui_kit.py`, `v2_surfaces.py`, NEW `src/web/shell_skin.py` | dashboard.py/cockpit.py bodies, wolfe*, strategy compute, research lane |
| **B — Strategist & Screeners** | NEW `src/web/strategist_view.py`, NEW `src/web/screener_plus.py` | ui_kit.py, v2_surfaces.py, dashboard.py/cockpit.py, wolfe* |
| **C — Engines & Wolfe** | `wolfe.py`, `wolfe_view.py`, `wolfe_overlay.py`, NEW `src/automation/strategy_registry.py` | any web shell/chrome, dashboard.py/cockpit.py, research lane |
| **D — Data & Provenance** (bonus, fully independent) | `provenance.py`, `fundamentals_filing_dates.py`, `fundamentals_provenance.py`, `cci_*`, research.db lane | ALL web-layer files |
| **shared (append-only, one writer at wrap)** | `main.py` (router includes only, EOF), `PROJECT_STATE.md`, this doc + the tracker | — |

`main.py` router-include lines are append-only at EOF; if two sessions both add one, the wrap script
(`scripts/wire_v2_surfaces.py` pattern) is idempotent. Prefer self-mounting via `v2_surfaces._mount_routers`.

## 2. The integration CONTRACT (fixed now → no mid-flight renegotiation)
**2a. Pre-allocated routes + nav slots** (Lane A wires these into the nav up front; B/C build the pages):
- `/dash/strategist` — Lane B's strategist dashboard. Nav: `Strategies → "Strategist"` (first sub-nav item, before Hub).
- `/dash/screener` stays Lane-frozen (dashboard.py); Lane B adds `/dash/screen2` (the streamlined screener) → nav `Screener → "Screen+"`; promote to default once parity-verified.
- `/dash/wolfe` + `/dash/wolfe/scan` — Lane C (already in nav: "Wolfe · Chart" / "Wolfe · Scan").

**2b. Read-API contract** (Lane C provides, Lane B consumes — define the signature, build independently):
```python
# src/automation/strategy_registry.py  (Lane C owns)
def summary(conn=None) -> list[dict]:
    """One row per strategy for the strategist dashboard. Reads precomputed tables only.
    [{ "key","label","route","count","as_of","top":[{"symbol","note"}], "health":"ok|stale|empty" }]"""
```
Lane B renders whatever `summary()` returns; if C isn't ready, B ships against a stub of the same shape.

**2c. Data boundary** = table names (already stable): `stock_signals` (MEP/accum), `concall_scores`
(CCI), `cpr_signals` (CPR), `stock_rs` (RS/leaders), `wolfe_*`/scan output, `fund_panel` (research).
Reads only; hubs/dashboards NEVER recompute on-read.

## 3. Operating protocol (the streamlining, every lane obeys)
1. **Boot:** read PROJECT_STATE + this doc + the tracker + your lane's memory; `git status --short` +
   `git log --oneline -15`; confirm your owned files' state. **If an owned file is dirty from another
   lane, STOP and flag — don't edit over it.**
2. **Build in YOUR modules only.** New routes self-mount; nav entries are Lane A's job (use the
   pre-allocated slots in §2a — don't invent nav).
3. **Deploy discipline (every change):** safety-diff VPS vs repo baseline → backup `*.bak-<lane>` →
   scp (LF) → import-test / module selftest on the VPS venv → `systemctl restart hermes-api` →
   health 200 + curl-verify the surface → keep the one-command revert. `ssh hermes` works here.
4. **Verify, don't claim.** Pull the live page, grep for the change. Screenshot-worthy = done.
5. **Track as you go:** update YOUR section of the tracker + write your own memory entry. Append a
   PROJECT_STATE Session-log entry at wrap (don't `git add PROJECT_STATE.md` if another lane's edits
   are uncommitted — note it rides the reconciliation).
6. **Commit only your owned files** (explicit paths; verify the staged set is exactly yours — the
   `safe-git-add-new` discipline). Never `git add -A`.

## 4. Sequencing / merge order
- **A, C, D start immediately** (zero overlap). **B** can start immediately against the `summary()` stub,
  then swap to C's real registry when it lands.
- Lane A lands the nav slots for `/dash/strategist` + `/dash/screen2` on day one (cheap), so B's pages
  are reachable the moment they deploy.
- No lane blocks another. Worst case a lane ships against a stub and re-points later.

---

## 5. PASTEABLE SESSION PROMPTS
Each is self-contained + autonomous. Paste one per fresh session.

### ── SESSION A — Chrome & Migration ──
```
You are the sole builder of Lane A — "Chrome & Migration" — for Patearn (D:\Hermes). Read FIRST:
PROJECT_STATE.md, docs/parallel-sessions-PLAN.md (your ownership + contract), docs/ui-restore-and-
migration-TRACKER.md (Track A), docs/ui-architecture-v2.md, and memory: integrate-not-orphan,
build-additive-never-replace, autonomous-blanket-access-multisession, vps-deploy-reality.

MISSION: make the WHOLE site use the new ui_kit look (the /dash/coverage "Trust" page is the reference),
so Markets/Screener/Strategies/Tracker/stock stop showing the old dashboard._shell chrome + old logo.

OWN ONLY: src/web/ui_kit.py, src/web/v2_surfaces.py, NEW src/web/shell_skin.py. DO NOT TOUCH
dashboard.py/cockpit.py bodies, wolfe*, strategy compute, or the research lane.

APPROACH (decoupled — no dashboard.py edits): build src/web/shell_skin.py that RUNTIME-RESKINS legacy
_shell pages into the ui_kit shell (same monkeypatch/runtime-wrap pattern v2_surfaces already uses on
dashboard._nav; intercept/replace the _shell wrapper or post-process the HTML so the cyan-dot logo +
"Search or ask Pat ⌘K" + card system apply everywhere). Migrate page-by-page: /dash/markets FIRST
(highest-visibility win), then screener, strategies, tracker, stock, then the Markets lenses. Keep every
body/data intact (no-loss); sacred routes keep URLs. ALSO: pre-wire the nav slots from the plan §2a
(Strategies→"Strategist"→/dash/strategist; Screener→"Screen+"→/dash/screen2) NOW so Lanes B's pages are
reachable. ALSO fold the v2 nav/IA into a durable repo form so a redeploy can't wipe it.

DEPLOY each change per plan §3 (safety-diff → backup *.bak-chrome → scp LF → VPS selftest/import →
restart → health 200 → curl-verify the reskinned page → revert path). Verify live, don't claim. Track in
Track A; write a memory entry; append a PROJECT_STATE Session-log entry at wrap. Commit ONLY your owned
files. Autonomous — convene a red-team on your own approach before shipping; report only when Lane A is
done or a hard blocker stops you.
```

### ── SESSION B — Strategist Dashboard & Screener Streamlining ──
```
You are the sole builder of Lane B — "Strategist & Screeners" — for Patearn (D:\Hermes). Read FIRST:
PROJECT_STATE.md, docs/parallel-sessions-PLAN.md (ownership + the §2b read-API contract), docs/ui-
restore-and-migration-TRACKER.md (Track C), and memory: data-first-light-ui, build-additive-never-
replace, autonomous-blanket-access-multisession, mep-strategy-built-deployed, tracker-workspace-redesign.

MISSION: (1) build the STRATEGIST DASHBOARD at /dash/strategist — every strategy's current read at a
glance (count, freshness, top names, health), each card linking to its deep page; (2) STREAMLINE
SCREENING — one wide, configurable, frozen-pane screener at /dash/screen2 with saved screens + strategy
column-groups + the confluence columns (MEP × CCI × RS × CPR × Wolfe) so screening is unified, not
scattered.

OWN ONLY: NEW src/web/strategist_view.py, NEW src/web/screener_plus.py (self-mount their routers). DO NOT
TOUCH ui_kit.py, v2_surfaces.py, dashboard.py/cockpit.py, wolfe*. The nav entries for your routes are
Lane A's job (plan §2a) — don't edit nav.

CONTRACT: consume src/automation/strategy_registry.summary() (Lane C, signature in plan §2b). If it
isn't on the VPS yet, ship against a local stub of the SAME shape and swap when it lands. Read PRECOMPUTED
tables only (stock_signals, concall_scores, cpr_signals, stock_rs…) — never recompute on-read. Style to
the ui_kit look so you merge cleanly with Lane A.

DEPLOY per plan §3 (backup *.bak-strat → scp LF → VPS import/selftest → restart → health 200 → curl
/dash/strategist + /dash/screen2, grep the strategy rows/columns). Verify live. Track in Track C; memory
entry; PROJECT_STATE entry at wrap. Commit ONLY your owned files. Autonomous; red-team your own design
(is it genuinely "at a glance"? is the screener actually faster than today?); report only when done.
```

### ── SESSION C — Strategy Engines & Wolfe ──
```
You are the sole builder of Lane C — "Engines & Wolfe" — for Patearn (D:\Hermes). Read FIRST:
PROJECT_STATE.md, docs/parallel-sessions-PLAN.md (ownership + §2b contract), docs/ui-restore-and-
migration-TRACKER.md (Track B), docs/wolfe-NEXT-SESSION.md (§0 resume), and memory: wolfe-wave-strategy,
wolfe-backtest-methodology, autonomous-blanket-access-multisession.

MISSION: (1) RESTORE the Wolfe manual "draw-your-own" pivot mode — recover it from commit b7ad360,
reconcile it with the current /dash/wolfe drawing lens (Track B2/B3), so Ramana can hand-draw his pivots
again and the machine computes the Fib zones; decide + document the canonical Wolfe home. (2) Build NEW
src/automation/strategy_registry.py exposing summary() per plan §2b — a uniform per-strategy read (count,
as_of, top names, health) over the EXISTING compute tables — the single source Lane B's dashboard reads.

OWN ONLY: wolfe.py, wolfe_view.py, wolfe_overlay.py, NEW src/automation/strategy_registry.py. Touch the
strategy engines (mep_signals/cpr_signals/concall_*/stock_rs) READ-ONLY (registry reads their tables;
don't edit them). DO NOT TOUCH any web shell/chrome, dashboard.py/cockpit.py, the research lane.

DEPLOY per plan §3 (backup *.bak-wolfe → scp LF → VPS selftest/import → restart → health 200 → curl
/dash/wolfe + verify the draw-mode controls render + that strategy_registry.summary() returns rows on the
VPS). Wolfe stays DESCRIPTIVE-ONLY (the §C falsification stands) — no buy/sell claims. Verify live; track
in Track B; memory; PROJECT_STATE entry at wrap. Commit ONLY your owned files. Autonomous; re-ground the
Wolfe method against Ramana's open questions in wolfe-NEXT-SESSION.md §0 before changing detector logic.
```

### ── SESSION D (bonus, fully independent) — Data Integrity & Provenance ──
```
You are the sole builder of Lane D — "Data & Provenance" — for Patearn (D:\Hermes). Read FIRST:
PROJECT_STATE.md, docs/parallel-sessions-PLAN.md, docs/provenance-coverage-NEXT-SESSION.md, and memory:
phase0-provenance-coverage, provenance-knowable-plan, cci-credibility-timeseries.

MISSION: (1) the SURVIVORSHIP-COMPLETE deterioration-veto re-test on security_master's 1,722 delisted
names (does CCI deterioration flag real blow-ups OOS?) — route to quant + red-team; if it survives the
avoid-overlay earns a real claim, else keep it descriptive. (2) knowable_at BSE CALIBRATION — run
fundamentals_filing_dates.py (BSE since-2006) + the forward hook on the VPS so provenance.lag_audit() is
non-empty and ~75–85% of the archive de-models from "modeled" to real.

OWN ONLY: provenance.py, fundamentals_filing_dates.py, fundamentals_provenance.py, cci_*.py, the
research.db lane. DO NOT TOUCH any web-layer file (this lane shares ZERO files with A/B/C → fully parallel).

Run on the VPS (real data; local hermes.db is a 4-symbol stub). Verify with selftests + lag_audit
non-empty + the re-test's CIs. Track in PROJECT_STATE + memory; commit only your owned files. Autonomous;
report only when done or blocked (e.g. delisted-name concalls not captured → state the data gap honestly).
```

---

# ROUND 2 — status of Round-1 lanes + the next wave (added 2026-06-28)

## Round-1 outcome (verified live + in git)
| Lane | Commit | State | Live-verified | Gap |
|---|---|---|---|---|
| A — Chrome & Migration | ee4a213 | DONE | whole site reskinned (shell_skin.py); all routes 200 | — |
| B — Strategist & Screeners | 00d0e36 | DONE | /dash/strategist (real registry rows) + /dash/screen2 (confluence/CSV/saved) 200 | main.py mount UNCOMMITTED (VPS-only) |
| C — Engines & Wolfe | cef712c | committed, session STILL RUNNING (2nd pass on wolfe.py/wolfe_view.py) | draw-mode restored; strategy_registry.summary() live | let it finish; commit its 2nd pass |
| D — Data & Provenance | 54f4b0d | DONE | BSE calibration live, lag_audit() non-empty, 73.6% de-model | veto re-test DATA-BLOCKED (parked); +50/+90 leaks 8.7% |

Cross-cutting gaps (none of the lanes closed): (1) main.py router-mounts uncommitted -> durable fix =
register strategist_view/screener_plus in v2_surfaces._ROUTER_SPECS so wire() mounts them (no main.py
edit). (2) PROJECT_STATE has NO Session-log entries for A-D (memory only). (3) /dash/screen2 not promoted
to default. (4) the untracked round docs.

## Round-2 lanes (next wave) — freeze dashboard.py/cockpit.py; E first, F/G/H fully parallel
| Lane | OWNS (only) | MUST NOT TOUCH |
|---|---|---|
| E — Consolidation/Durability/QA | v2_surfaces._ROUTER_SPECS, scripts/wire_v2_surfaces.py, PROJECT_STATE Session-log, round docs, the Screen+->default nav swap | wolfe* (Lane C running), dashboard.py/cockpit.py bodies |
| F — Pat copilot (deepened) | src/pat/* | web shells, chart modules, research lane |
| G — Charting overhaul | chart_view.py, stock_chart.py, hermes-charts.js, NEW harmonic_* | wolfe_overlay.py (Lane C), dashboard.py/cockpit.py, src/pat |
| H — Data/provenance hardening | provenance.py, fundamentals_filing_dates.py, the forward-hook scheduler, NEW data-licensing doc | ALL web files |

See the chat message for the four pasteable SESSION E/F/G/H prompts (kept there for copy-paste).
