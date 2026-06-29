# Nav IA — DECISIONS + execution prompts (Scope × Lens pass) — 2026-06-29

> Ramana approved the full Scope × Lens nav pass (option b). This LOCKS the IA and gives the disjoint-lane
> prompts. Grounds: `docs/navigation-and-structure-review.md` (analysis) + `docs/ui-architecture-v2.md`
> §0/§3 (the prior red-team corrections this finally implements). Additive + reversible; the chrome gate
> + regression sweep guard every step.

## 1. The DECIDED IA (build to this exactly)
**Top bar (unchanged):** Markets · Screener · Strategies · Tracker · [Trust] · [Ask Pat ⌘K]

| Altitude | Sub-nav (decided) | Change from today |
|---|---|---|
| **Markets** | Overview · Sectors · **Relative Strength** · Rotation·Map · Rotation·Weather · Rotation·Band · Participants · Wire · Compare | **Leaders/"Strength" (`/dash/leaders`) MOVES here** from Strategies (RS = Markets content, §0.1). RS is now consolidated under Markets. |
| **Screener** | Screen · Screen+ · Themes · Review · Workbench | unchanged |
| **Strategies** *(stock-selection lenses ONLY)* | **Strategist** · Conviction · **Accumulation** · Structure · Credibility · Growth · Launchpad | **Hub MERGES into Strategist** (one landing). **Positioning + MEP GROUP under "Accumulation"** (two views: Delivery/DVPT + MEP signed-phase; keep both pages, one heading). **Removed:** Strength→Markets, Lab→Trust, Wolfe→overlay. |
| **Tracker** | Dashboard · Portfolios · Watchlists · Performance · Import | unchanged |
| **Trust** *(utility)* | Coverage · **Strategy validation** | **Lab (`/dash/testing`) MOVES here**, reframed as rigor evidence (honest backtests incl. "nothing beats buy-and-hold net of cost"). |

**Wolfe / Harmonic = chart overlays only** (§3-C): removed from the Strategies sub-nav; reachable as the
toggle on the stock & index chart, **with the scanner (`/dash/wolfe/scan`, `/dash/harmonic`) kept reachable
from that chart control** — do NOT orphan them (the prior "I lost Wolfe" lesson). They are not lenses.

**Two judgment calls (encoded; flag if you disagree):** (a) Positioning+MEP are *grouped* under one
"Accumulation" heading now — a full page-merge is a later strategy task, not this nav pass; (b) Wolfe
demotes to overlay but stays reachable. Everything else follows the model mechanically.

## 2. The cross-page model (the registry is the single source — stops the drift)
`src/web/lens_registry.py` (NEW) registers each lens ONCE; nav, highlights, dossier tabs, screener
columns, and cross-links all generate from it.
```python
# one record per lens
{ "key","label","scope",          # scope: market|screen|stock|trust
  "altitude",                      # markets|screener|strategies|tracker|trust
  "route","dossier_tab","screener_col","overlay" }
```
Plus: canonical link helpers that carry the lens (`stock_link(sym, lens) -> /dash/stock?sym=…#<tab>`),
lateral "see this lens elsewhere" links, `Markets → Sector → Stock` breadcrumbs, and a fix for the
dossier highlight (it currently lights Strategies›Positioning via the `stock→stocks` alias — a per-stock
page must not claim one lens).

## 3. DO-NO-HARM (every lane, every change — non-negotiable)
- `bash scripts/regression_sweep.sh` → PASS (it runs `chrome_gate.py` + the live route sweep).
- `python scripts/chrome_gate.py` → PASS, and **add every new/moved nav href to its swept set** so nav
  truth holds (no menu item may 404/500 in a clean checkout — the lesson from `/dash/testing`).
- **Additive + reversible** (backup `*.bak-navia`, one-command revert); **sacred routes**
  (`/dash/ratio`,`/dash/rrg`,`/dash/compare`) keep URLs; **no-loss** (no page dropped — moved, not deleted);
  descriptive-only. Deploy per `parallel-sessions-PLAN.md` §3 (safety-diff → scp → import-test → restart →
  verify live). Commit ONLY your owned files.

## 4. Lanes (disjoint ownership — N1 owns the nav source; run N1+N2 in parallel, N3 after N1)

### ── SESSION N1 — IA restructure + lens registry (the core) ──
```
You are Lane N1 — "Nav IA restructure" — for Patearn (D:\Hermes). Read FIRST: docs/nav-ia-DECISIONS-and-
prompts.md (THE SPEC — build §1 exactly), docs/navigation-and-structure-review.md, docs/ui-architecture-
v2.md §0/§3, PROJECT_STATE.md, memory: integrate-not-orphan, build-additive-never-replace, lane-a2-native-
ui-design-system, autonomous-blanket-access-multisession. MISSION: implement the DECIDED Scope × Lens IA
in the nav, driven by a single registry. OWN ONLY: src/web/v2_surfaces.py, NEW src/web/lens_registry.py.
DO NOT TOUCH dashboard.py/cockpit.py bodies, coverage_view.py (Lane N2), testing_view.py (N2), the chart/
wolfe modules. DO: (1) build lens_registry.py (§2 shape) as the single source; (2) rewrite v2_surfaces
`_IA_ALT`/`_IA_SUB`/`_SUB_ALIAS`/`_ALT_OF` to the §1 map — move Leaders→Markets, merge Hub→Strategist,
group Positioning+MEP under "Accumulation", REMOVE Wolfe·Scan/Wolfe·Chart from Strategies (they become
overlays — but DO NOT 404 them; leave the routes live and reachable from the chart), and add the Trust
sub-nav (Coverage · Strategy validation→/dash/testing) — N2 builds that page, you wire the nav slot per
the registry; (3) fix the dossier/index highlight so /dash/stock no longer claims Strategies›Positioning.
Per change: deploy → `bash scripts/regression_sweep.sh` PASS + `python scripts/chrome_gate.py` PASS (ADD
the moved hrefs: /dash/leaders under Markets, /dash/testing under Trust, to the gate's swept set) → commit
owned files. NAV TRUTH: every sub-nav href must resolve 200 in a clean checkout. Run the autonomous loop;
report at complete or a hard blocker.
```

### ── SESSION N2 — Lab → Trust "Strategy validation" ──
```
You are Lane N2 — "Strategy validation under Trust" — for Patearn (D:\Hermes). Read FIRST: docs/nav-ia-
DECISIONS-and-prompts.md (§1: Lab moves under Trust, reframed as rigor evidence), PROJECT_STATE.md, memory:
phase0-provenance-coverage, build-additive-never-replace, integrate-not-orphan. MISSION: reframe the
strategy testing lab (`/dash/testing`) as the Trust-altitude "Strategy validation" surface — the honest
backtest evidence (incl. "nothing beats buy-and-hold net of cost") presented as an audit-grade rigor
asset, not a strategy lens. OWN ONLY: src/web/coverage_view.py (additive — add a "Strategy validation"
tab/section that surfaces the validation story + links to /dash/testing), src/web/testing_view.py
(reframe its heading/intro to the Trust framing; KEEP the graceful-degrade fallback from ee7b4ad intact).
DO NOT TOUCH v2_surfaces.py (Lane N1 wires the nav slot), dashboard.py/cockpit.py, the chart/wolfe modules.
Coordinate via the registry contract: N1 adds the Trust→"Strategy validation"→/dash/testing nav entry; you
own the page content. Per change: deploy → `bash scripts/regression_sweep.sh` PASS + `python scripts/
chrome_gate.py` PASS → verify /dash/testing renders under the Trust framing (and still degrades when
research.db absent) → commit owned files. Descriptive-only; no over-claim. Run the loop; report at complete.
```

### ── SESSION N3 — Cross-page links + breadcrumbs (after N1 lands) ──
```
You are Lane N3 — "Cross-page navigation glue" — for Patearn (D:\Hermes). PREREQ: Lane N1's lens_registry.py
is committed (consume it; do not edit it). Read FIRST: docs/nav-ia-DECISIONS-and-prompts.md (§2), docs/
navigation-and-structure-review.md (§4–§5 mechanics), PROJECT_STATE.md, memory: integrate-not-orphan,
autonomous-blanket-access-multisession. MISSION: make the Scope × Lens structure NAVIGABLE — implement the
cross-page glue WITHOUT editing the contended dashboard.py/cockpit.py bodies. OWN ONLY: NEW src/web/nav_
links.py (canonical link helpers `stock_link(sym, lens)`/`index_link`/`theme_link` that carry the lens as
`#<dossier_tab>` from the registry; a `Markets → Sector → Stock` breadcrumb component; lateral "see this
lens elsewhere" link rows) + a thin append-only runtime hook (the shell_skin/v2_surfaces injection pattern:
post-process responses to add breadcrumbs + lens-carrying links + the lateral rail). DO NOT edit
dashboard.py/cockpit.py bodies, v2_surfaces.py, lens_registry.py, the chart modules. Per change: deploy →
`bash scripts/regression_sweep.sh` PASS + `python scripts/chrome_gate.py` PASS → verify a real drill path
live (Markets row → index → stock#tab lands on the right tab; breadcrumb present; lateral links work) →
commit owned files. No-loss; sacred routes intact. Run the loop; report at complete or a hard blocker.
```

## 5. Sequencing
- **N1 + N2 start now** (disjoint files; N1 owns nav, N2 owns the Trust page; they meet only at the
  registry-defined nav slot). **N3 starts when N1's `lens_registry.py` is committed.**
- After all three: one `chrome_gate` + `regression_sweep` PASS on a clean checkout = the nav pass is done
  and demo-safe. Reconcile PROJECT_STATE + memory at wrap.
