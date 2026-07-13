# Lane L2 — Native bodies & chrome polish — STATUS

> **Lifecycle: TRANSIENT.** Retire (`git rm`) once the L2 lane closes. Registered in `docs/DOC_INDEX.md`.


> **Closed 2026-06-29.** Sole builder: autonomous L2 session. Branch `main`, started at HEAD
> `05cdeae`. All work in owned files only (`src/web/shell_skin.py` + new docs). Both gates PASS;
> every change deployed to the live VPS and verified IN-BROWSER before commit.

## Commits (all owned-files-only, explicit-path staged)
| Commit | What |
|---|---|
| `5f4cef5` | **Bleed-through neutralisation + reskin-deepen.** Re-assert native `.uk-*` geometry under `body.uk-skin .uk-*` (specificity (0,2,x) beats every bare `_BASE_CSS` element rule) → any native component on any reskinned page now renders identically to the native reference. Deepen legacy primitives (`.maj`/`.kpi .box`/`.chip`/`.scard`) to native token geometry (radius/spacing/mono-numerics). + `docs/L2-body-migration-audit.md`. |
| `eaa165c` | **RS-hub `rsh-*` retint.** The RS hub's self-contained mini-design-system still carried the OLD palette (#161b22 / #30363d / #1f6feb / 10px); mapped every `rsh-*` primitive to the ui_kit tokens via the skin. |
| `ca5674d` | Docs: shipped status + browser evidence in the audit. |

## What shipped (against the 9-item backlog)
1. **Audit** — `docs/L2-body-migration-audit.md`. Rendered the demo path IN-BROWSER vs the live VPS
   (local DB too sparse). Coverage + Screen+ = native shell; Markets/RS/Screener/Stock = legacy `_shell`
   reskinned; bodies live in frozen `dashboard.py`/`cockpit.py`. ✓
2. **Bleed-through sweep** — enumerated the live bare-element rules (`h2`/`table`/`th`/`td`/`nav`/`nav a`/
   `header`) on `/dash/markets`; confirmed absent on native `/dash/coverage`. Neutralised the whole class
   under `body.uk-skin .uk-*` (the `9def4ff` pattern, generalised). ✓
3–6. **Markets / RS / Screener / Stock bodies** — the bodies are FROZEN. Deepened the reskin so the legacy
   primitives adopt native token geometry (not just colour) → reskinned bodies read native. Screener
   frozen-pane (sticky col + header, 48 cols) and Stock dossier (8 tabs + chart controls) **preserved,
   no-loss** (browser-verified). A full body rewrite into new modules was deliberately deferred (see audit
   §5 — high blast radius for marginal gain). ✓ (via deepen)
7. **Coverage** — verified fully native; the reference, no drift. ✓
8. **Density / responsive / a11y / print** — density drives `--grid-pad` 6→3px on the reskinned screener
   grid; skip-link + `#uk-main` + `aria-current` + density toggle present; my additions add no width
   constraints. ✓
9. **End-to-end** — all 6 demo pages: `uk-top` + Trust + `ui_tokens` foundation; one consistent native
   look. `regression_sweep.sh` PASS (chrome gate 11+4; live 31 routes + 4 overlays). ✓

## Mechanism / design decision
The demo-path BODIES live in `dashboard.py`/`cockpit.py` (Lane L1-frozen). L2 may not edit them. The
realistic, owned-file path to "native look end-to-end" is to make `shell_skin._SKIN_CSS` carry (a) a
defensive `body.uk-skin .uk-*` re-assertion that immunises native components against bare-element
bleed-through, and (b) a deepen layer that lifts the legacy primitives from colour-only to native
geometry. This achieves the visual goal with ZERO edits to the frozen bodies and zero risk to the
frozen-pane grid (no layout/sticky/z-index touched). A body REWRITE is the right move only when a body
needs a structural (not cosmetic) change — then build a new `*_native.py` module for THAT body and
runtime-swap it.

## Revert
- Local backup: `src/web/shell_skin.py.bak-L2` (pre-L2 baseline).
- VPS backups: `/opt/hermes/src/web/shell_skin.py.bak-L2-<ts>` (per deploy).
- One-command: restore the bak + `systemctl restart hermes-api`.

## Deploy reality (confirmed this session)
- VPS `shell_skin.py` matched committed HEAD exactly at start (clean safety-diff).
- Local repo files are pure LF → `scp` directly, no CR-strip. SHA-verified each deploy; CRLF=0 on VPS.
- VPS Python 3.10.12 — selftest + py_compile pass there.
- Parallel lanes are live (Lane L4's `1ef085a` landed mid-session); explicit-path staging kept L2 commits
  clean (no cross-absorption).

---

## WAVE 2 — Mobile + perf + state polish (2026-06-29, re-baselined at `b47b98b`)

### Commits (owned-files-only)
| Commit | What |
|---|---|
| `b239f90` | **Mobile fix.** Audit (`docs/L2-mobile-audit.md`) via a viewport-independent CSS-fact method (env can't drive a real 380px layout viewport — see below). Only real unhandled overflow on the demo path = the dossier `.tabbar` (8-tab nav, nowrap, no mobile rule). Fixed: ≤640px → `overflow-x:auto` so it scrolls inside itself like `.uk-nav`/`.uk-sub`. Everything else already handled by Lane A2. |
| `75442fd` | **State polish + ⌘K verified.** Native state system (`uk-empty`/`uk-error`/`uk-note`/`uk-skel`/`uk-spin`) was NOT injected on legacy pages → injected `ui_components.components_css()` site-wide (class-scoped, idempotent) + upgraded legacy `.empty` to the centered `uk-empty` look (○ glyph, bold ticker). ⌘K verified: Cmd+K opens overlay, collapses gracefully ≤640px. |

### Backlog coverage (Wave 2)
1. **Mobile audit** — `docs/L2-mobile-audit.md`; demo path + Sectors/Conviction; CSS-fact method. ✓
2. **Fix overflow** — one real gap (`.tabbar`) fixed; all others contained/covered. Zero page-overflow
   provable from CSS facts; screener stays scroll-inside (no-loss). ✓
3. **Perf** — measured; shell injection already on the fast path (inline `<head>`, ~20 ms parse vs
   508 ms TTFB + 1.7 MB frozen body). No safe win in owned files; recorded honestly. ✓ (no change shipped)
4. **State polish** — unified empty/loading/error via `ui_components` site-wide; legacy `.empty` polished. ✓
5. **⌘K / Ask-Pat** — verified working + mobile-graceful; no fix needed. ✓
6. **Final pass** — desktop screenshots captured (consistent look + the polished empty state). Real-380px
   screenshots NOT achievable in-env (constraint below). ✓ (within env limits)

### ⚠️ Environment constraint (real-viewport verification)
This environment **cannot drive a true narrow layout viewport**: `resize_window` (Chrome) and
`preview_resize` (Preview) both leave `window.innerWidth` fixed; `chrome.debugger`/CDP
(`Emulation.setDeviceMetricsOverride`) is unreachable from the page-context `javascript_tool`. So a
genuine 380px screenshot isn't possible here. Mobile correctness was instead established
**viewport-independently from the CSS facts** (a block overflows at 380px IFF it's >380px wide AND
`overflow-x:visible` AND a nowrap-flex/table AND not contained by a scroll ancestor AND not covered by a
≤640px rule). The `.tabbar` fix was verified the same way (computes `overflow-x:auto` under the ≤640px
media query on the live VPS). This is a genuine verification-method limitation, surfaced honestly per the
non-negotiables rather than claimed-as-done.

### Process note (cross-absorption caught + fixed)
A first attempt at the state-polish commit (`6c0c4fb`, since replaced) wrongly swept in L4's staged
`screener_plus.py` — the `git add` only staged `shell_skin.py`, but L4 had `screener_plus.py` staged
concurrently and the plain `git commit` consumed it. Caught immediately, `git reset --soft HEAD~1`, then
`git commit src/web/shell_skin.py …` (explicit pathspec) → re-committed as `75442fd` touching ONLY
`shell_skin.py`; L4's `screener_plus.py` was preserved in the index and L4 committed it cleanly in
`361c95e`. **Lesson reinforced:** `git diff --cached` showing a foreign path is a HARD STOP — unstage it
or commit with an explicit pathspec; never `git commit` a mixed index.

---

## WAVE 3 — Pitch-demo polish + Trust front-door + WCAG-AA (2026-06-29, re-baselined `b926f7a`)

### Commits (owned-files-only)
| Commit | What |
|---|---|
| `e7ee6d5` | **WCAG-AA contrast.** Lifted `--ink-3` #5c6f84 → #7e90a8 (the sole systemic AA failure — 3.44:1, carries muted text site-wide) across ui_tokens/ui_kit/shell_skin + cmdk footer; + skin block mapping frozen-body hardcoded greys (#6e7681/#5f7488) to the AA-safe ink. Coverage AA fails 10→1. |
| `4f4e7b6` | **a11y ⌘K.** The Cmd-K summon was a `<div>` (not focusable/announced) → now a `<button>` with aria-label + aria-keyshortcuts + focus-visible ring. Verified keyboardFocusable + opensOnActivate. |
| `5c7be8f` | **Consistency.** Markets `.ck-tile` (index-bundle tiles) carried the OLD palette → mapped to ui_kit tokens. Zero remaining old-palette bg on Markets. |
| `232cb05` | **Print.** Deepened to a leave-behind: @page A4+margins, full light-flip (color-adjust:exact), hide interactive-only controls, cards/tables intact across breaks, value contract preserved, footer disclaimer. |

### Backlog coverage (Wave 3)
1. **Pitch-demo visual QA** — `docs/L2-pitch-qa.md`; 6 beats walked in a dedicated tab. Coverage = clean reference (descriptive, no leaderboard); dossier descriptive (UNPROVEN not a grade); the `.ck-tile` palette break fixed. ✓
2. **Trust front-door depth** — Coverage confirmed institutional (uniform cards, evidence eyebrows, Strategy-validation + provenance trails, no ranking). The missing "Replay the Tape" trail needs a route + a coverage_view edit (not L2-owned) → flagged task_568e63a8. ✓ (within scope)
3. **WCAG-AA** — systemic `--ink-3` fix + ⌘K keyboard/aria fix + frozen-grey class overrides. Coverage 10→1, Stock 3→2 (2 remaining are inline styles in L3's stock_chart.py → task_c0cc1023). ✓
4. **Design-system completeness + print** — `/dash/_ui` current (all families incl. states); print deepened to a leave-behind. ✓
5. **Consistency sweep** — old-palette `.ck-tile` fixed; native-component bleed-through re-confirmed clean (uk-card h2 21px, uk-t cols right-aligned). ✓
6. **Final pass** — Coverage + Stock screenshots show one consistent institutional look; gates green. ✓ (643px window cap — see W2 viewport constraint)

### Out-of-scope flagged (not L2-owned files)
- **D-PITCH-2 Rotation blue/amber colour clash** — lives in `rotation_view.py` (not an L2-owned file, not a `*_native.py`); not edited, belongs to that view's owner.
- **Replay-the-Tape route + Coverage trail** (`coverage_view.py` + routing) → spawn_task task_568e63a8.
- **Chart-control inline-style contrast** (`stock_chart.py`, L3) → spawn_task task_c0cc1023.

### Discipline held
Every commit explicit-pathspec staged; `git diff --cached --name-only` checked == exactly my files before each commit (the W2 cross-absorption lesson). All deploys atomic (concurrent L3/L4), VPS==HEAD safety-diff each time, py3.10 import-test, health 200, browser-verified. No PROJECT_STATE.md edit.

---

## WAVE 4 — Full-site consistency + a11y sweep (2026-06-29, re-baselined `cdbfa5e`)

### Commits (owned-files-only — shell_skin.py)
| Commit | What |
|---|---|
| `14341ab` | `.cprstrip .c` (CPR pivot cells) #161b22 → --bg-2. + fixed an invisible CSS bug: `*/` inside a `rsh-*/ck-tile` comment closed the comment early → the rule silently didn't parse (gate green, only the in-browser check caught it). |
| `0e7be9d` | Growth `gw-*` mini-system → tokens; + generic bare `input`/`select`/`textarea`/`button` retint. |
| `91cc054` | `.nv-empty` (News/Wire empty box) → --ink-3/--line/--r. |

### Sweep result (all ~31 surfaces, live computed-style scan)
The static `grep` css= counts are NOISE (frozen `_BASE_CSS` definitions + my comments). The live RENDER
is the truth. **Every surface is now class-based-clean** — the W1-W4 `body.uk-skin` maps cover every
legacy page. Three new class-based holdouts found + fixed (CPR `.cprstrip .c`, Growth `gw-*`, Wire
`.nv-empty`) + the generic form-control retint. Residual sub-AA / off-shade is exclusively INLINE styles
in frozen bodies (chart labels, heat-strip micro-glyphs, tag chips) — not class-reachable.

### Backlog coverage (Wave 4)
1. **Inventory all ~31 surfaces** — `docs/L2-fullsite-sweep.md`, live-scanned each. ✓
2. **Fix systematically** — CPR/Growth/Wire mini-systems + bare form controls, all via the one
   `body.uk-skin` lever. ✓
3. **WCAG-AA everywhere** — the W3 `--ink-3` lift + by-class grey map cover every surface; W4 added
   gw-mut/gw-count/.nv-empty (#6e7681) to the map. Residual = inline-only (frozen). ✓
4. **State coverage** — native state system site-wide; legacy `.empty` + `.nv-empty` read intentional. ✓
5. **Non-owned flags** — chart-control inline contrast (stock_chart.py → task_c0cc1023), rotation colour
   clash (rotation_view.py, reported), replay trail (coverage_view.py → task_568e63a8). ✓
6. **Final pass** — screenshot matrix (Coverage/Stock/Markets/CPR) one consistent look; gates green. ✓

### The bug worth remembering
A CSS **comment containing `*/`** (e.g. `rsh-*/ck-tile`) silently closes the comment early and breaks the
NEXT rule — it passes `py_compile` AND the chrome gate (the page still 200s, the chrome markers still
present), and is invisible in the served markup. Only the in-browser computed-style check caught it
(`myRuleParsed:false`). Never put `*/` inside a CSS comment; verify a new skin rule actually PARSES + wins
in-browser, not just that it's in the served HTML.
