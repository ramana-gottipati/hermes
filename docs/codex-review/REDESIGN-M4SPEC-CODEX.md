# Codex review — M4 stock-hub SPEC, pre-build (2026-07-20)

> Channel record per docs/redesign-coordination.md §1.3. Dispositions: coordination §2 (2026-07-20 rows).
> Verdict on spec v1.0; v1.1 is the accepted-fixes revision, re-review follows.

VERDICT: OBJECT

1. BLOCKING: The chart “wrapper” plan is not feasible as written.  
`docs/redesign-m4-stock-hub-spec.md:68-81` says M4 will wrap `stock_chart.py` unchanged while adding `?cmp=` initialization, URL write-back, type-3 picker behavior, and dense-rail reshaping. But `src/web/stock_chart.py:38-40` is a closed IIFE string; compare state is local (`cmpReg`, `cmpPeers`) at `src/web/stock_chart.py:295-298`; add/remove do not write URL state at `src/web/stock_chart.py:694-718`; only `window.__cmpAdd` / `window.__cmpRemove` are exposed at `src/web/stock_chart.py:755-756`; and the drawing controls are built internally at `src/web/stock_chart.py:1063-1088`. A pure wrapper cannot reliably replace the rail, intercept removals, or make URL state authoritative. Fix the spec to require either an additive v3 fork/copy of the snippet or a small explicit exported API in `stock_chart.py`; the current “unchanged snippet + wrapper” claim is false.

2. BLOCKING: The M4 spec does not implement the ratified navigation contract, including the user-toggleable rail collapse.  
The ratified contract requires a global 6-destination bar plus per-destination left rail in fixed order (`docs/redesign-plan-2026-07-17.md:517-520`) and explicitly allows persistent user-invoked collapse while starting visible (`docs/redesign-plan-2026-07-17.md:521-525`). The M4 anatomy only names Focus + Context rail using `shell_v3` (`docs/redesign-m4-stock-hub-spec.md:23-26`), and current `shell_v3` renders only topbar + Focus/Context grid (`src/web/shell_v3.py:74-82`) with no destination rail or collapse control. Add this to the M4 build requirements or explicitly route it to a same-commit shell/nav module requirement.

3. BLOCKING: The §O stock-chart gap list is not fully carried into the M4 landing checklist.  
The ratified stock-chart row requires: compare set to URL+carryover, type-3 picker, gloss chips, data CSV, and drawings rail type-1 (`docs/redesign-plan-2026-07-17.md:920`). The M4 spec covers dense rail and `?cmp=` URL state (`docs/redesign-m4-stock-hub-spec.md:71-81`) and has generic “metric labels are term chips” (`docs/redesign-m4-stock-hub-spec.md:86-89`), but it omits chart data CSV and the session carryover half of “URL+carryover.” Its CSV promise is limited to tabular tables (`docs/redesign-m4-stock-hub-spec.md:95-96`). Add explicit chart data CSV, carryover semantics, and stock-chart education trio/gloss-chip acceptance tests.

4. BLOCKING: The “thin wrappers over existing panel functions” claim is over-broad.  
The four named reuse targets in the prompt are importable/callable: `_mep_stock_panel(sym)` (`src/web/dashboard.py:2316-2323`), `credibility_fingerprint.card_html(sym, conn=...)` (`src/web/credibility_fingerprint.py:211-217`), `seasonal_full_panel(scope, entity, ...)` (`src/web/seasonal_view.py:1003-1012`), and `momentum_pane.card_html(sym, conn=..., bench=...)` (`src/web/momentum_pane.py:291-341`). But the spec also claims pt14/CPR are thin wrappers (`docs/redesign-m4-stock-hub-spec.md:116`); pt14 is inline inside `dash_stock`, not a reusable panel function (`src/web/dashboard.py:6352-6393`), and CPR requires precomputed `by_tf` input (`src/web/dashboard.py:2204-2208`). Amend the spec to name the required extraction or caller-owned data assembly.

5. ADVISORY: The payload plan is coherent, but underspecified.  
`?section=` server-side expansion can plausibly keep the initial page under 1 MB (`docs/redesign-m4-stock-hub-spec.md:101-109`; ratified payload discipline at `docs/redesign-plan-2026-07-17.md:315-317`). To make it testable, define whether the budget is raw HTML bytes or compressed transfer bytes, and require expanded-section URLs to preserve `sym`, `cmp`, dock channel state, and anchor behavior.
tokens used
VERDICT: OBJECT

1. BLOCKING: The chart “wrapper” plan is not feasible as written.  
`docs/redesign-m4-stock-hub-spec.md:68-81` says M4 will wrap `stock_chart.py` unchanged while adding `?cmp=` initialization, URL write-back, type-3 picker behavior, and dense-rail reshaping. But `src/web/stock_chart.py:38-40` is a closed IIFE string; compare state is local (`cmpReg`, `cmpPeers`) at `src/web/stock_chart.py:295-298`; add/remove do not write URL state at `src/web/stock_chart.py:694-718`; only `window.__cmpAdd` / `window.__cmpRemove` are exposed at `src/web/stock_chart.py:755-756`; and the drawing controls are built internally at `src/web/stock_chart.py:1063-1088`. A pure wrapper cannot reliably replace the rail, intercept removals, or make URL state authoritative. Fix the spec to require either an additive v3 fork/copy of the snippet or a small explicit exported API in `stock_chart.py`; the current “unchanged snippet + wrapper” claim is false.

2. BLOCKING: The M4 spec does not implement the ratified navigation contract, including the user-toggleable rail collapse.  
The ratified contract requires a global 6-destination bar plus per-destination left rail in fixed order (`docs/redesign-plan-2026-07-17.md:517-520`) and explicitly allows persistent user-invoked collapse while starting visible (`docs/redesign-plan-2026-07-17.md:521-525`). The M4 anatomy only names Focus + Context rail using `shell_v3` (`docs/redesign-m4-stock-hub-spec.md:23-26`), and current `shell_v3` renders only topbar + Focus/Context grid (`src/web/shell_v3.py:74-82`) with no destination rail or collapse control. Add this to the M4 build requirements or explicitly route it to a same-commit shell/nav module requirement.

3. BLOCKING: The §O stock-chart gap list is not fully carried into the M4 landing checklist.  
The ratified stock-chart row requires: compare set to URL+carryover, type-3 picker, gloss chips, data CSV, and drawings rail type-1 (`docs/redesign-plan-2026-07-17.md:920`). The M4 spec covers dense rail and `?cmp=` URL state (`docs/redesign-m4-stock-hub-spec.md:71-81`) and has generic “metric labels are term chips” (`docs/redesign-m4-stock-hub-spec.md:86-89`), but it omits chart data CSV and the session carryover half of “URL+carryover.” Its CSV promise is limited to tabular tables (`docs/redesign-m4-stock-hub-spec.md:95-96`). Add explicit chart data CSV, carryover semantics, and stock-chart education trio/gloss-chip acceptance tests.

4. BLOCKING: The “thin wrappers over existing panel functions” claim is over-broad.  
The four named reuse targets in the prompt are importable/callable: `_mep_stock_panel(sym)` (`src/web/dashboard.py:2316-2323`), `credibility_fingerprint.card_html(sym, conn=...)` (`src/web/credibility_fingerprint.py:211-217`), `seasonal_full_panel(scope, entity, ...)` (`src/web/seasonal_view.py:1003-1012`), and `momentum_pane.card_html(sym, conn=..., bench=...)` (`src/web/momentum_pane.py:291-341`). But the spec also claims pt14/CPR are thin wrappers (`docs/redesign-m4-stock-hub-spec.md:116`); pt14 is inline inside `dash_stock`, not a reusable panel function (`src/web/dashboard.py:6352-6393`), and CPR requires precomputed `by_tf` input (`src/web/dashboard.py:2204-2208`). Amend the spec to name the required extraction or caller-owned data assembly.

5. ADVISORY: The payload plan is coherent, but underspecified.  
