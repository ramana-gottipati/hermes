# SURFACE PLAYBOOK — where new screens go, and how they must land

**Class: CANONICAL · BINDING.** Read this BEFORE writing any new page, board, tab, or embed under
`/dash` (or any new user-facing surface anywhere). Purpose: the estate has ~62 lenses and a history
of building pages that never got linked ("orphans") or that re-render data a sibling page already
shows. This playbook makes both structurally impossible.
Born from the 2026-07-13 joint Claude+Codex UX audit (`docs/ux-journey-audit-2026-07-13.md`).

---

## 1. The IA model (do not re-derive)

- **Altitudes × Lenses.** Top nav = 5 workspaces: **Markets** (market-wide state), **Screener**
  (cross-sectional stock tables), **Strategies** (stock-selection lenses), **Tracker** (the user's
  own books/watchlists), **Trust** (methodology, provenance, education). A lens = one way of
  evaluating, registered once in `src/web/lens_registry.py` — **the single nav source**. Nothing
  else may define nav.
- **Canonical URL** = D80 nesting: `/dash/<workspace>/<page>`. Flat routes 307-redirect
  (`src/web/nested_nav.py`). Never invent a third URL shape.
- **Mounting** = one anchored entry in `src/web/v2_surfaces.py::_ROUTER_SPECS` (durable across
  redeploys). Never `app.include_router` from your module directly.
- **Left rail** groups the workspace's lenses (`src/web/left_rail.py`; group order pinned per
  altitude). A new Markets/Strategies lens must declare which rail group it belongs to.
- **Dossiers** (`/dash/stock`, `/dash/index`, `/dash/theme`) are integration hubs, not lenses:
  per-symbol content lands as a dossier **tab/embed**, not a standalone page.

## 2. Decision tree for any new surface

Answer IN ORDER; stop at the first hit:

1. **Sister-data check (mandatory, first).** Does an existing page already show this data or a
   cut of it? Check the family tables in the UX audit §redundancy (RS family · seasonal family ·
   fundamentals/CCI family · screens · change-feeds). If yes → extend that page (new tab, toggle,
   column, drill) or cross-link from it. The Wolfe fresh⇄open **toggle** and the seasonal
   `_subnav()` trio are the approved patterns. Building a parallel page for sister data is a
   defect, not a feature.
2. **Is it per-symbol?** → dossier tab/embed on `/dash/stock` (+ optional standalone deep page
   only if the embed genuinely can't hold it — then the standalone must be linked FROM the embed).
3. **Is it a new way to evaluate (market- or stock-cross-section)?** → a new **Lens** in
   `lens_registry.py` with workspace + rail group + plain-English label (see §4 naming).
4. **Is it a child view of an existing lens?** → mount under the parent's route
   (`/dash/<parent>/<child>`), reachable from a visible control on the parent (tab/toggle/link).
   Undeclared children are orphans.
5. **Is it a tool/calculator, an API, an overlay, or an action endpoint?** → overlay/JSON/action
   routes are exempt from nav but must be reached from a chart/page control; document the caller.
6. **None of the above** → it probably shouldn't exist as a page. Ask what job it does.

## 3. The landing checklist (every new page, same session — none optional)

| # | Requirement | How |
|---|---|---|
| 1 | Registry entry | `lens_registry.py` Lens (or declared child of one) — this feeds nav, breadcrumbs, lateral rails, and the command palette |
| 2 | Durable mount | anchored insert in `v2_surfaces._ROUTER_SPECS` |
| 3 | Education minimum | `infographics.bottom_line()` near the top · `plain()` under each non-obvious chart/table · `how_to_read_link()` · `gloss()` (or `?q=` glossary link) on every custom metric column. Prose scaffold AND glossary wiring — not one or the other |
| 4 | Honesty fence | the shared fence primitive (once built — until then copy the exact wording from `insider_view.py`'s "descriptive, not advice" idiom); NEVER action verbs (buy/sell/add/avoid/ride/fade) |
| 5 | Glossary keys | new metrics get entries in `src/web/glossary.py` (and surface in Pat's explain corpus) |
| 6 | Pat registration | at minimum a **nav-answer** (Pat can name + link the page for a matching question); data flow if the page is a table/screen |
| 7 | Strategy doc | if it's a strategy surface: its `docs/strategies/` page updates in the SAME commit (existing rule, `tests/test_strategy_docs_coverage.py`) — and remember `/opt/hermes/docs/strategies/` re-scp |
| 8 | Export | tables ship server-side `format=csv` (the `wolfe_trades_view.py` pattern), not client-side DOM blobs |
| 9 | Symbol links | every symbol cell links `/dash/stock?sym=` (param is `sym`, never `symbol`) |
| 10 | Home exposure decision | explicitly decide: home tile/board, flagship band, or deliberately not — record why in the commit message |
| 11 | Writes are POST | never a state-mutating GET (`ack`/`track`/`clear` are legacy debt, not precedent) |
| 12 | State doc | PROJECT_STATE §Key-paths/§Decision-log in the same commit (existing gate) |

## 4. Naming rules (nav labels)

- Plain English first, acronym second: "Accum / Distrib" not "MEP"; "Rotation map" not "RRG".
- No metaphor-only labels: a first-time user cannot decode Weather/Clock/Band/All-weather from the
  nav — pair every metaphor with a plain subtitle.
- No internal language on public surfaces: session numbers (S111), decision IDs (D124), "Ramana",
  "CANONICAL — do not archive", agent/lane vocabulary. Those live in docs/ and PROJECT_STATE, never
  in rendered HTML.
- One regime vocabulary site-wide (the Market-mood strip's words are canonical). Do not invent a
  new state word (RISK-OFF / UP-BIASED / Cautious all saying the same thing was a defect).

## 5. The no-orphan gate

`tests/test_dash_route_registry.py` (build tracked in the UX audit's session S-H) enumerates every
GET-HTML `/dash` route from `src.main.app` and fails unless the route is one of: registered lens ·
declared nested child · dossier · api/action/overlay · compat redirect · explicitly exempted with
owner+rationale. Until that test lands, THIS checklist is the gate — reviewer = whoever wraps the
session. Known pre-existing orphans and their dispositions are inventoried in the UX audit; do not
add to that list.

## 6. Where families live today (sister-data index)

- **RS / rotation / momentum**: rs-hub (launcher) · rrg · rotation · rsband · cycle-clock ·
  divergence · early-signals · sector-momentum · capture-map · momentum-scan · leaders. Anything
  RS-shaped extends one of these (consolidation program: audit §S-B).
- **Seasonality**: seasonal-tape · seasonal-screen · seasonal-divergence (+ dossier/seasonal embed,
  event-cadence embed). Extend via the shared `_subnav()`.
- **Fundamentals / management**: growth · concalls(CCI) · credibility fingerprint · sector-economics
  · pt14 scoring (screener). 
- **Change-feeds**: the signal-event bus (`signal_events` → attention queue + alert rail + /v1) is
  THE "what changed" substrate — never build a fourth change-feed; add a lens to the bus.
- **News**: `news_feed.py` → wire lens + dossier News tab + `news_symbol_tags`. Extend these; do
  not create parallel news pages.
- **Ownership/filings**: insider · ratings · sast · shp (one cohort, shared idioms).
- **Market state**: market-internals · move-anatomy · participants · band-locks · surveillance ·
  results-reactions · actions.
- **Education**: web glossary (`src/web/glossary.py`) · reading-guide · strategy-ref · Pat explain
  (single corpus target — audit §S-C/S-E).

## 7. Deploy reminders for surfaces (unchanged doctrine)

Forked-nav files (`lens_registry.py`, `v2_surfaces.py`, `dashboard.py`) deploy by **anchored
insert / pull-patch-push, never full-file scp**. Walk the journey live after deploy
(walk-the-journey skill) — unit-green ≠ journey-green.
