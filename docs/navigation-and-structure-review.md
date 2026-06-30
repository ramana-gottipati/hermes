# Patearn — Navigation & Page-Structure Review (2026-06-29)

> **Status: REVIEW DRAFT — nothing decided, nothing built.** This documents the *actual* page
> structure (grounded in the DB schema + the live route handlers, not the menu) and a proposed
> cross-page navigation model. It exists to be challenged (Codex review = `codex-bridge/req-02`) and
> then decided by Ramana. It does NOT authorize any change.
>
> Companion docs: `docs/ui-architecture-v2.md` (the IA design + §0 red-team corrections),
> `docs/ui-restore-and-migration-TRACKER.md`, `docs/parallel-sessions-PLAN.md`.

## 1. The core finding — there are TWO structures, and only one is coherent
- **The DATA + the STOCK DOSSIER are a logical, principled "lens" architecture.** ✅
- **The MENU is a flat 1-D list of what is really a 2-D (Scope × Lens) reality.** ✗ — this is why the
  nav keeps feeling "off," and it's where the divergences live.

## 2. The real model — every lens, its data, and the surfaces it renders at (the multi-page model)
Each analytical idea is a **lens** backed by one table at a consistent grain (mostly *per-symbol-per-day*),
and each lens manifests at 4–5 surfaces. That multiplicity — not the menu — is the structure.

| Lens | Data table (grain) | Market-wide list | Screener column | Dossier tab (`/dash/stock`) | Chart overlay |
|---|---|---|---|---|---|
| Positioning / DVPT | `stock_signals` (sym×day) | `/dash/stocks`, `/dash/workbench` | ✓ | `pos` | DVPT subchart |
| MEP (signed accum) | `mep_signals` (sym×day) | `/dash/mep` | ✓ | `mep` | MEP tint |
| Relative Strength | `ratio_rows`/`rs_extras`/`stock_signals.rs_*` | `/dash/leaders`,`/dash/rs`,`/dash/sectors`,`/dash/rrg`,`/dash/rotation`,`/dash/rsband` | ✓ | `rs` | RS line |
| Structure (CPR) | `cpr_signals` (sym×period×TF) | `/dash/cpr` | ✓ | `cpr` | CPR Spine |
| Credibility (CCI) | `concall_scores`/`credibility_series` | `/dash/concalls` | ✓ | `cci` | — |
| Quality (pt14) | `pattern_scores`/`fundamentals` | (screener only) | ✓ | `qual` | — |
| F&O / OI | `fno_oi_signals`/`participant_oi` | `/dash/participants` | — | `fno` | — |
| Themes | `company_tags` | `/dash/themes`,`/dash/theme` | ✓ | header chips | — |
| Wolfe / Harmonic | `wolfe_signals`/`harmonic_signals` (snapshot) | `/dash/wolfe/scan` | — | Price-tab toggle | Wolfe/Harmonic |
| Conviction (synthesis) | blends the above | `/dash/conviction` | — | header verdict tile | — |

**The two axes this implies:** **SCOPE** (whole market → filtered universe → one stock → your positions)
× **LENS** (the ~9 questions above). The **stock dossier** handles the lens axis cleanly (7 tabs, one per
lens, 4 chart overlays, all converging on one name). The **Screener** is "all lenses at once, filtered."
Those two surfaces are well-designed. The **top menu** is where the 2-D collapses to 1-D and breaks.

## 3. Page archetypes (≈46 GET + 6 POST routes, 20 handler modules)
- **List/board** (ranked table over one table): leaders, scan, stocks, screener, screen2, workbench, mep, cpr, concalls, conviction, growth, rs, rsband…
- **Detail/dossier** (multi-section, per entity): `/dash/stock` (7 tabs — the convergence hub), `/dash/index`, `/dash/wolfe`, `/dash/theme`, `/dash/performance`.
- **Chart-only**: rrg, rotation, rsband, ratio.
- **Hub/landing**: `/dash`, strategies, themes, markets.
- **Overlay fragment endpoints** (JSON for the stock chart): `/dash/{cpr,mep,rs,wolfe}/overlay`.
- **Action/POST**: tags, track, track/edit, track/alerts.

## 4. Navigation MECHANICS as wired today (verified in code)
- **Entity deep-links via query params** — every list row is `<a href="/dash/stock?sym=X">` /
  `/dash/index?idx=Y` / `/dash/theme?tag=Z` (+ `?den=`,`?cmp=`,`?sector=`,`?scope=`,`?vs=`).
  (e.g. `cockpit.py:669,705,723`.)
- **Dossier tabs ARE deep-linkable** — the stock page honors `?tab=<lens>` (`dashboard.py:3475,3491`)
  AND `location.hash` on load (`dashboard.py:7061`: `show(panes[h]||'price')`). So
  `/dash/stock?sym=INFY#cci` already lands on the Credibility tab. The mechanism exists; it's barely used.
- **Chrome + highlight** — `v2_surfaces.wire()` rebinds `dashboard._nav` at runtime; the active
  altitude/sub-nav is resolved by `_altitude_of(active)` via the hand-kept `_ALT_OF` / `_SUB_ALIAS` maps.
- **Overlay cross-binding** — overlays share a JS contract (`window.__wfpc`/`__wfcandle`) so
  CPR/MEP/RS/Wolfe draw on one chart without colliding.
- **Breadcrumbs/back** — only ad-hoc: a one-off `←` link on index pages (`cockpit.py:1447,2443`);
  otherwise the browser back button. No structured trail.

## 5. The proposed cross-page navigation model (to make Scope × Lens navigable)
The plumbing is good; what's missing is consistency + the lateral glue. Six patterns:
1. **One canonical link helper per entity** — `stock_link(sym, lens=None)` → `/dash/stock?sym=…#<lens>`,
   `index_link`, `theme_link`. Replaces the dozens of hand-written hrefs (which drift).
2. **The lens travels with the click** — screener MEP cell → `…#mep`; a Leaders row → `…#rs`; a CCI tile
   → `…#cci`. Land on the lens clicked, not generic price. (The `?tab=`/`#hash` plumbing already supports it.)
3. **Lateral "see this lens elsewhere" links** — on each dossier lens tab AND each market-wide list, a
   rail: *▸ market-wide list · ▸ open in Screener (filtered to this lens) · ▸ on the chart.* Turns a
   lens's 5 surfaces from islands into a loop.
4. **Structured breadcrumbs** for the real drill chain: `Markets → Sector/Index → Stock` (and `Theme → Stock`).
5. **A single nav/lens REGISTRY as the source of truth** — register each lens once:
   `{key, label, route, dossier_tab, screener_col, overlay, altitude, scope}`. The menu entry, the
   highlight map (`_ALT_OF`), the dossier tab, the screener column, and every cross-link then GENERATE
   from that one record (this is `ui-architecture-v2.md` §9, "register once → self-place").
6. **Fix the highlight quirks** — `/dash/stock` currently highlights **Strategies › Positioning**
   (alias `stock → stocks` in `_SUB_ALIAS`), which is wrong for a per-stock everything-page; deep pages
   (stock/index/theme/pat) need deliberate altitude mapping.

## 6. Confirmed structural divergences (data-grounded, not taste)
| # | Divergence | Evidence |
|---|---|---|
| 1 | **RS split across two altitudes** | `leaders`/`rs`/`sectors`/`rrg`/`rotation`/`rsband` all read the same RS tables, yet `leaders` sits under **Strategies ("Strength")** while the rest are under **Markets**. `ui-architecture-v2.md` §0.1 explicitly says move `leaders` to Markets. |
| 2 | **Two overlapping "accumulation" lenses** | `Positioning` (`/dash/stocks`, `stock_signals` delivery) and `Accumulation·MEP` (`/dash/mep`, `mep_signals`) are both institutional-flow — two Strategies items + two dossier tabs (`pos`+`mep`) for one concept. |
| 3 | **Wolfe/Harmonic as nav lenses** | They are *snapshot scan* tables + chart overlays; IA §3-C says overlay-only, no nav entry. The menu has Wolfe twice (`Scan` + `Chart`). |
| 4 | **Strategist + Hub** | Two strategy landing pages over the same per-pillar data. |
| 5 | **Dossier highlights the wrong altitude** | `/dash/stock` lights up Strategies›Positioning (alias quirk). |

## 7. Root cause + the fix
The links and highlight maps are **hand-maintained in ~4 separate places** (nav, sub-nav, dossier tabs,
screener columns; IA §0.4 confirms). Nothing forces them to agree → RS got misfiled, Wolfe doubled, the
dossier highlights the wrong altitude. **Patterns #1 + #5 (canonical link helper + registry) make
cross-page navigation *generated*, not hand-wired — so it can't drift.** That is simultaneously the
structural fix and the anti-regression mechanism.

## 8. Open questions for Ramana (decisions, not yet made)
1. **Adopt the Scope × Lens model for the menu** (push the dossier's logic up to the nav)?
2. **RS:** unify all of RS (incl. Leaders) under Markets per §0.1, leaving Strategies = stock-selection lenses only?
3. **Positioning vs MEP:** keep as two lenses, or merge into one "Accumulation" lens with sub-views?
4. **Wolfe/Harmonic:** demote to overlay-only (no nav), or keep a Scan list entry?
5. **Strategist vs Hub:** merge into one Strategies landing?
6. **Build the lens registry** as the single source for nav + links + dossier tabs + screener columns?

> Until Ramana decides, this is descriptive analysis only. No nav/route/page changes are authorized.
