# Parallel-Sessions ROUND 3 — large autonomous missions (2026-06-28)

> Companion to `docs/parallel-sessions-PLAN.md`. Round 1+2 are done; this is the next wave — **large,
> self-driving missions** (no small wins), each session **auto-prompts itself** through a backlog, with a
> mechanical do-no-harm guard so none of Ramana's existing processes/charts/work are hampered.

## Round-2 audit — what each session shipped (verified live: 30 routes + 4 overlays all 200)
| Lane (session) | Commit(s) | Shipped | Recorded |
|---|---|---|---|
| E — Consolidation (A-session) | `f8fdfa9` | Lane-B routers durably mounted via `v2_surfaces._ROUTER_SPECS` (no more uncommitted-main.py dep) + `wire_v2_surfaces.py` re-applier + Round-1 docs | PROJECT_STATE S46 |
| F — Pat planner (B-session) | `3970345`, `5b58ad1` | Pat = general analytics planner (621 lines): multi-condition confluence, ANY strategy askable, compare; provenance-stamped, descriptive-only | PROJECT_STATE S47 |
| G — Charting/harmonic | `bd77588` | D72 harmonic lane (707 lines): XABCD detector + reliability backtest + nightly scanner + design docs | PROJECT_STATE S48 |
| H — Data hardening (D-session) | `cdd3751` | knowable_at leak cut ~10× (11.8% → ~1.2% effective) + forward-capture scheduler enabled + `data-licensing-decision.md` | memory provenance-knowable-plan |

**Nothing hampered** — `scripts/regression_sweep.sh` = PASS across all sessions. The decoupling held.

## THE DO-NO-HARM HARNESS (mandatory — every lane, every change)
`bash scripts/regression_sweep.sh` sweeps the live VPS: 30 nav routes + 4 chart overlays + health.
**It MUST print PASS before any commit.** A FAIL = a regression in Ramana's existing work → STOP; fix or
revert (`*.bak-<lane>`) before anything else. Add any new route/overlay you create to the script.

## THE AUTONOMOUS SELF-PROMPT LOOP (every Round-3 lane runs this — no small wins, no waiting on Ramana)
1. **Plan a backlog** of >=8 SUBSTANTIAL items for your mission; write it to your lane doc.
2. **Execute one item fully** (build -> deploy per PLAN.md section 3 -> verify live).
3. **Run `scripts/regression_sweep.sh` -> must PASS.** If FAIL: revert, fix, re-verify.
4. **Commit only your owned files**; one-line progress note in your lane doc.
5. **Immediately self-prompt to the next backlog item — do NOT return to Ramana between items.**
6. **Stop + report ONLY when:** the whole backlog is done, OR a hard blocker (spend cap, missing
   credential, an unrecoverable regression, a destructive/irreversible step). Re-run the do-no-harm
   checklist every cycle. Additive-only; never edit another lane's files; descriptive-only (no buy/sell).

---

## Round-3 prompts (large; each self-drives the loop above)

### SESSION A -> Lane A2: Native UI + responsive design-system
You are Lane A2 — "Native UI & Responsive" — for Patearn (D:\Hermes). Read FIRST: PROJECT_STATE.md,
docs/parallel-sessions-PLAN.md + docs/parallel-sessions-ROUND3.md (the harness + the autonomous loop),
docs/ui-architecture-v2.md, docs/ui-restore-and-migration-TRACKER.md, memory: lane-a-chrome-migration-
shipped, data-first-light-ui, integrate-not-orphan, autonomous-blanket-access-multisession. CONTEXT:
Track A reskinned the site via a CSS overlay on legacy dashboard._shell — good, but a retint, not native.
LARGE MISSION: take the UI to genuinely institutional-grade. Backlog (>=8, refine then self-drive the
loop): (1) migrate each page to render through NATIVE ui_kit components, per-page, behind the existing
skin as a safe fallback; (2) full RESPONSIVE/mobile layout (collapsing nav, fluid grids) — usable on a
phone; (3) complete the ui_kit design system (type scale, spacing tokens, every component + a /dash/_ui
showcase); (4) accessibility (focus/contrast/keyboard) + perf (lazy charts, cached CSS); (5) a polished
empty/loading/error-state system; (6) print/export styling beyond Coverage; (7) density toggle
(comfortable/compact); (8) retire the two-shell duality once native parity is verified. OWN ONLY:
src/web/ui_kit.py, src/web/v2_surfaces.py, src/web/shell_skin.py, NEW src/web/ui_*.py helpers, NEW static
assets. DO NOT TOUCH dashboard.py/cockpit.py bodies, wolfe*/chart modules, src/pat, research lane. Per
change: deploy -> `bash scripts/regression_sweep.sh` MUST PASS -> commit owned files -> next. No-loss
(every datum preserved). Run the autonomous loop; report only at mission-complete or a hard blocker.

### SESSION B -> Lane F2: Pat conversational analyst + analytics workbench
You are Lane F2 — "Pat analyst & workbench" — for Patearn (D:\Hermes). Read FIRST: PROJECT_STATE.md,
docs/parallel-sessions-PLAN.md + ROUND3.md, docs/pat-design-and-improvements.md, memory:
pat-built-deployed-live, product-strategy-b2b, strategist-and-screener-plus-lane-b, mep-strategy-built-
deployed. CONTEXT: Pat is now a general analytics PLANNER (3970345). LARGE MISSION: make Pat the flagship
"insight by querying" analyst + turn the strategist into a real workbench. Backlog (>=8): (1) MULTI-TURN
conversation (follow-ups/refine — "now only small-caps", "vs last quarter"); (2) SAVE any NL query as a
named screen/board (server-side, reloadable); (3) Pat EXPLAINS ("why is X credible?") drilling into
provenance + the underlying rows; (4) proactive ALERTS — Pat watches the watchlist + strategy_registry,
flags NEW confluence (descriptive, opt-in); (5) the strategist dashboard -> a configurable WORKBENCH
(arrange cards, per-strategy deep panels, compare baskets, CSV); (6) richer intents (ranked rankings,
sector slices, time-series asks); (7) an eval-set + accuracy harness; (8) tighten OOD/SEBI guardrails +
hallucination tests. OWN ONLY: src/pat/* + src/web/strategist_view.py + src/web/screener_plus.py. DO NOT
TOUCH ui_kit/v2_surfaces/shell_skin, dashboard.py/cockpit.py, chart modules, wolfe*, research lane.
Descriptive-only; every answer provenance-stamped. Per change: deploy -> `bash scripts/regression_sweep.sh`
MUST PASS -> verify on the REAL VPS Gemini stack (existing answers unchanged) -> commit owned files ->
next. Run the loop; report at complete or hard blocker.

### SESSION C -> Lane G2: Charting overhaul completion + harmonic in the UI
You are Lane G2 — "Charting completion" — for Patearn (D:\Hermes). Read FIRST: PROJECT_STATE.md,
docs/parallel-sessions-PLAN.md + ROUND3.md, docs/chart-redesign-design.md, docs/harmonic-pattern-design.md,
memory: charting-overhaul-cpr-spine, wolfe-wave-strategy, data-first-light-ui. CONTEXT: the harmonic D72
engine is built+backtested (bd77588) but NOT surfaced in the UI; the four-family chart control bar is
partial. LARGE MISSION: finish the charting story. Backlog (>=8): (1) SURFACE harmonic — a /dash/harmonic
scanner page + a harmonic overlay toggle on /dash/stock (descriptive, with the backtest-reliability caveat
— bull-only edge); (2) complete the four-family control bar (chart-type incl Heikin-Ashi/Renko/P&F ·
strategies · indicators · drawings); (3) the DRAWING engine (trendline/ray/rect/Fib/text + magnet snap +
hide-all + per-symbol persistence); (4) roll the bounded responsive chart engine SITE-WIDE (RRG/RS/ratio/
sparklines onto it; kill preserveAspectRatio stretch); (5) multi-timeframe (W/M) on the overlays; (6) DVPT
+ RS lanes as first-class toggles beside CPR/MEP/MA/Wolfe; (7) a chart "read" legend/story line; (8) perf
(incremental data, no relayout jank). OWN ONLY: src/web/chart_view.py, stock_chart.py, src/web/static/
hermes-charts.js, wolfe_view.py, wolfe_overlay.py, harmonic_*; NEW chart modules. KEEP the window.__wfpc /
overlay contract intact so CPR/MEP/MA/RS keep working — do NOT break existing overlays. DO NOT TOUCH
dashboard.py/cockpit.py, ui_kit/v2_surfaces, src/pat, research lane. Descriptive-only. Per change: deploy
-> `bash scripts/regression_sweep.sh` MUST PASS -> verify LIVE on a real symbol (overlays toggle, zero
console errors, chart bounded) -> commit owned files -> next. Run the loop; report at complete or hard
blocker.

### SESSION D -> Lane H2: Audit-grade research wedge + data integrity
You are Lane H2 — "Research wedge & data integrity" — for Patearn (D:\Hermes). Read FIRST: PROJECT_STATE.md,
docs/parallel-sessions-PLAN.md + ROUND3.md, docs/lane-d-knowable-at-and-veto-2026-06-28.md,
docs/data-licensing-decision.md, docs/provenance-coverage-NEXT-SESSION.md, memory: provenance-knowable-plan,
cci-credibility-timeseries, phase0-provenance-coverage, product-strategy-b2b. CONTEXT: knowable_at leak is
now ~1.2% + forward capture enabled (cdd3751); the survivorship deterioration-veto is DATA-BLOCKED (need
delisted-name concalls); CCI Phase 3 (RRG/divergence/backtest) was paused. LARGE MISSION: turn provenance
+ credibility into a fully-backtested, audit-grade wedge. Backlog (>=8): (1) close the knowable_at loop —
wire fundamentals_asof to read effective_as_of (coordinate; it is parallel-owned — do it via a new reader
or a safe additive hook); (2) execute the data-licensing migration plan (vendor-TOS feed at pre-pitch);
(3) ACQUIRE delisted-name concalls to UNBLOCK the survivorship deterioration re-test, then run it (quant +
red-team — earns a real claim or stays descriptive); (4) finish CCI Phase 3 — credibility RRG +
price-divergence + a survivorship-aware backtest; (5) a continuous DATA-QUALITY monitor feeding the
Coverage ledger (freshness/leak/coverage alarms); (6) extend the provenance lineage registry to every
dataset; (7) the credibility time-series as a research-grade PIT series (level+momentum). OWN ONLY:
provenance.py, fundamentals_filing_dates.py, fundamentals_provenance.py, cci_*.py, coverage_view.py,
research.db lane, NEW research modules + docs. DO NOT TOUCH any web shell/chart/pat module (coverage_view
is data-display only — additive). Run on the VPS (real data); descriptive-only (the section-C
falsification stands — no return claims without a passed backtest). Per change: deploy ->
`bash scripts/regression_sweep.sh` MUST PASS -> commit owned files -> next. Run the loop; report at
complete or a hard blocker (e.g. concall data unobtainable — state it honestly, don't fabricate).
