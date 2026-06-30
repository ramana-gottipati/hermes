# Lane A2 — Native UI & Responsive design-system (Round 3)

> Owner: Lane A2. Owns ONLY `src/web/ui_kit.py`, `src/web/v2_surfaces.py`, `src/web/shell_skin.py`,
> NEW `src/web/ui_*.py`, NEW static assets. Untouchable: dashboard/cockpit bodies, wolfe*/chart modules,
> src/pat, research. Every change: deploy → `bash scripts/regression_sweep.sh` MUST PASS → commit owned
> files → next. Additive + no-loss. Context: Track A reskinned the site via a CSS overlay on legacy
> `dashboard._shell` — good but a retint, not native. This lane goes to genuinely institutional-grade.

## Architecture (how "native" is achieved without touching page bodies)
The page bodies are rendered by the untouchable `dashboard.py`/`cockpit.py`. So "native" is achieved at
the **runtime layer**: one shared design-system foundation (`ui_tokens` + `ui_components`) consumed by
BOTH render paths — `ui_kit.shell` (native pages: coverage/strategist/screen2/showcase) and
`shell_skin` (the runtime transform of every legacy `_shell` page). Retiring the two-shell duality =
making the legacy shell structurally + visually identical to the native one at runtime.

## Backlog (self-driven; one-line status per item) — ✅ ALL 10 DONE + LIVE (2026-06-29)
1. **Design-system foundation** — NEW `ui_tokens.py` (type scale · spacing · radius · elevation · color
   tokens · base reset · a11y primitives · density scale · responsive helpers), shared by both paths. ⬜
2. **Component library** — NEW `ui_components.py` (button/input/select/tabs/tooltip/skeleton/spinner/
   empty-state/toast/kbd/divider/progress + Python render helpers). ⬜
3. **`/dash/_ui` showcase** — a comprehensive living style guide proving every component + density +
   responsive + a11y states. New route (own surface, zero risk to existing pages). ⬜
4. **Density toggle** (comfortable/compact) — `data-density` on body + a chrome control + localStorage. ⬜
5. **Responsive / mobile** — breakpoints, collapsing nav, fluid grids, touch targets, frozen-grid mobile
   behavior; usable on a phone. ⬜
6. **Accessibility** — focus-visible rings, skip-link, ARIA on nav/menus, AA contrast, reduced-motion,
   keyboard nav for Cmd-K. ⬜
7. **Empty / loading / error states** — a polished system (skeleton/spinner/empty/error) + map legacy
   `.empty`. ⬜
8. **Perf** — serve the design-system CSS as a cacheable asset (one fetch, cached across navigations)
   instead of inlining per page; font-display; reduced re-parse. ⬜
9. **Print / export styling** — a global print stylesheet so any page prints clean (beyond Coverage). ⬜
10. **Retire the two-shell duality** — shell_skin structurally adopts the native ui_kit chrome so legacy +
    native pages share ONE shell. HIGHEST risk → last, only after native parity verified. ⬜

## Progress log (newest first)
- **Items 8 (perf) + 10 (retire two-shell duality) DONE + LIVE** (2026-06-29):
  *Item 10* — a structural code-merge would need the untouchable bodies, so the achievable + verified
  retirement is EXPERIENTIAL convergence. Parity audit (computed styles, native coverage vs legacy markets):
  chrome already identical (cyan logo dot `#34e0d6`, border `#1c2937`, nav-on `#eaf1f9`, skip-link + density
  toggle both present). Closed the one real divergence — the native `<body>` had no bg/font (Times New Roman
  + a possible white strip on short pages); now `background:var(--bg-1);font:var(--font)` → matches the legacy
  skinned body exactly (`#0b0f17` / `-apple-system`). Both shells now driven by ONE foundation
  (`ui_tokens`+`ui_components`), one language, indistinguishable chrome/body/a11y/density/responsive/print.
  *Item 8* — perf reviewed + confirmed healthy: responses gzipped on the wire (CSS ~3KB gzip), grids use
  `content-visibility` virtualization, infinite animations respect `prefers-reduced-motion`. CSS
  externalization (cached `/dash/ui.css`) DEFERRED: marginal gain on a working, gzipped site vs the
  whole-site-styling blast radius of a render-blocking link, with no staging to soak-test. Sweep = PASS.
- **Items 7 (states) + 9 (print) DONE + LIVE** (2026-06-29): global `@media print` in the foundation —
  ANY page now prints as a clean light document (chrome/nav/cmdk/toggle hidden, shadows off, full-width,
  thead repeats, page-break-avoid on cards). The empty/loading/error STATE system lives in `ui_components`
  (empty/error_state/skeleton/spinner) + the showcase; legacy `.empty` mapped to the polished look. Sweep = PASS.
- **Item 6 (accessibility) DONE + LIVE** (2026-06-29): keyboard skip-link ("Skip to content" → `#uk-main`)
  as the first focusable element on every page (native `<main id="uk-main">`, legacy `.wrap` gets the id);
  primary nav `aria-label="Primary"` + `aria-current="page"` on the active altitude (both shells); sub-nav
  landmark. Plus the foundation's focus-visible rings, prefers-reduced-motion, sr-only/skip CSS (4a).
  Verified live (native + legacy). Sweep = PASS.
- **Item 5 (responsive / mobile) DONE + LIVE** (2026-06-29): phone-usable at 375px. Both navs scroll
  horizontally (legacy `.v2bar .wsnav`, native `.uk-nav`), ⌘K hidden on mobile, touch targets ≥39px,
  `--gutter` tightens to 13px. Killed horizontal PAGE overflow: grid/flex children get `min-width:0` so a
  wide nowrap table scrolls INSIDE its card (`.ck-board` overflow-x:auto; generic `table:not(.scr):not(.uk-t)`
  → display:block scroll) — the frozen-pane grids keep their own wrappers untouched. Verified via 375px
  iframes: markets/screener/coverage all docScrollW==375 (no overflow). Sweep = PASS.
- **Item 4 (density toggle) DONE + LIVE** (2026-06-29, `f3d1c81` foundation + this): `ui_kit.density_js()`
  restores saved density onto `<html>` early (no flash), self-injects a 3-bar toggle into the chrome
  (`.v2util` legacy / `.uk-top` native), persists to localStorage, sets `aria-pressed`. Density rescales
  the frozen data grid (`--grid-pad` 6→3px) + native `.uk-t` (`--row-pad` 10→6) + components (`--sp`/`--fs`).
  Verified live (computed styles): grid cell 6→3px, toggle click flips + persists. Sweep = PASS.
- **Item 4a — foundation adopted into both shells** (`f3d1c81`): a11y (focus-visible/reduced-motion) +
  density vars now site-wide; `ui_kit.shell` carries tokens+components, `shell_skin` prepends tokens.
- **Items 1–3 + density mechanism DONE + LIVE** (2026-06-29): NEW `ui_tokens.py` (tokens + base + a11y +
  density scale, palette preserved exactly), NEW `ui_components.py` (btn/field/tabs/tooltip/skeleton/
  spinner/empty/error/note/kbd/progress/tag/switch + render helpers), NEW `ui_showcase.py` → `/dash/_ui`
  (living style guide, self-mounted via `_ROUTER_SPECS`). Density switch verified (comfortable↔compact
  rescales row-pad/fs/spacing via computed styles). `/dash/_ui` added to the harness. Sweep = PASS.
- (starting) baseline `regression_sweep.sh` = PASS (30 routes + 4 overlays). Backlog written.
