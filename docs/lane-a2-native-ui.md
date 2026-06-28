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

## Backlog (self-driven; one-line status per item)
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
- **Items 1–3 + density mechanism DONE + LIVE** (2026-06-29): NEW `ui_tokens.py` (tokens + base + a11y +
  density scale, palette preserved exactly), NEW `ui_components.py` (btn/field/tabs/tooltip/skeleton/
  spinner/empty/error/note/kbd/progress/tag/switch + render helpers), NEW `ui_showcase.py` → `/dash/_ui`
  (living style guide, self-mounted via `_ROUTER_SPECS`). Density switch verified (comfortable↔compact
  rescales row-pad/fs/spacing via computed styles). `/dash/_ui` added to the harness. Sweep = PASS.
- (starting) baseline `regression_sweep.sh` = PASS (30 routes + 4 overlays). Backlog written.
