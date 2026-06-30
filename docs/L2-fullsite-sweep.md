# L2 Wave 4 — Full-site consistency + a11y sweep (beyond the demo path)

> **Lane L2 Wave 4.** Created 2026-06-29. Extended the demo-path rigor (W1-W3) to all ~31 nav
> surfaces. Verified IN-BROWSER on the live VPS in a dedicated tab (the shared tab gets hijacked by
> L3/L4 nav). The authoritative method is the **live computed-style scan** — a static `grep` of the
> served HTML's `<style>` counts the frozen `_BASE_CSS` class definitions (~15 `#161b22`, ~28
> `#30363d` on *every* legacy page) plus my own code comments, which is NOISE; the truth is what
> actually RENDERS, which the computed-style scan measures (class-based, excluding inline styles).

## Method
For each surface: enumerate every rendered element's computed bg/border/color; flag (a) **class-based**
old-palette (`#161b22`/`#30363d`/`#1f6feb`/`#2ea043`, excluding inline `style=`), (b) **class-based**
WCAG-AA contrast fails (proper alpha compositing), (c) native-component bleed-through (inject `uk-card`
`h2` → must be 21px), (d) empty-state polish. Inline-styled hits are recorded separately — they live in
frozen bodies and are NOT reachable by a class rule (flagged to the owning lane, never `!important`-hacked).

## Surface inventory + result (all ~31)

| Surface | Result |
|---|---|
| coverage, screen2, strategist, _ui | **native** (ui_kit.shell) — clean reference |
| markets, sectors, rs-hub, ratio, compare, rrg, rotation, rsband, leaders, conviction, strategies, mep, concalls, wolfe, wolfe/scan, harmonic, themes, launchpad, testing, participants, workbench, pat, dashboard, stock | **clean** — class-based surfaces already covered by the W1-W3 maps (no rendered old-palette, no class-based AA fail) |
| **cpr** | FIXED — `.cprstrip .c` pivot cells were #161b22 → `--bg-2` |
| **growth** | FIXED — the whole `gw-*` mini-system was OLD-palette → mapped to tokens |
| (site-wide) | FIXED — bare `input`/`select`/`button` (`_BASE_CSS` #0d1117/#30363d/#21262d) → tokens |
| **wire** | FIXED — `.nv-empty` empty-state box (#6e7681 grey + #30363d dashed border) → `--ink-3`/`--line` |

**After the W4 fixes: every surface is class-based-clean** — zero rendered class-based old-palette, zero
class-based AA fails (the systemic `--ink-3` lift + by-class frozen-grey map from W3 cover the rest).

## Fixes shipped (commits)
| Commit | Fix |
|---|---|
| `14341ab` | `.cprstrip .c` → `--bg-2`. **Also fixed a real invisible bug:** the rule's comment contained `rsh-*/ck-tile` whose `*/` CLOSED the CSS comment early → the rule silently failed to parse (passed py_compile + the chrome gate; only the in-browser computed-style check caught it). Reworded to avoid `*/`. |
| `0e7be9d` | Growth `gw-*` mini-system → tokens (greys→ink, blue→accent, green/red→up/down, line→--line); + generic bare `input`/`select`/`textarea`/`button` retint (excludes the already-styled `.fbtn`/`.uk-cmdk`/density-toggle). |
| `91cc054` | `.nv-empty` (News/Wire empty box) → `--ink-3`/`--line`/`--r`. |

## WCAG-AA (Item 3)
The W3 `--ink-3` lift (#5c6f84 → #7e90a8) + the by-class frozen-grey map already cover every surface. W4
added `gw-mut`/`gw-count` (#6e7681 4.2:1) and `.nv-empty` (#6e7681 4.0:1) to that map. **Residual sub-AA
is exclusively INLINE styles in frozen bodies** — chart-control labels (`stock_chart.py`), heat-strip
micro-glyphs (the green/red value-contract on tinted cells, an accepted dense-grid exception), and tag
chips — none reachable by a class rule.

## State coverage (Item 4)
The native state system (`uk-empty`/`uk-error`/`uk-note`/`uk-skel`/`uk-spin`) is injected site-wide (W2);
the legacy `.empty` renders the polished centered look (verified on `/dash/stock?sym=ZZZBAD`: ○ glyph,
flex-column, centered). `.nv-empty` now also reads intentional. Every empty/error state reads deliberate.

## Non-owned hand-offs (precise, file:line + fix)
| Item | File | Fix | Flagged |
|---|---|---|---|
| 2 chart-control labels at 4.04:1 | `stock_chart.py` (inline `style="color:#6e7681"`) | change inline colour #6e7681 → #7e90a8 | spawn_task `task_c0cc1023` |
| Rotation blue=bull/amber=bear clash (D-PITCH-2) | `rotation_view.py:42+` (`#79c0ff`/amber quadrant colours) | unify to one colour contract | report (not L2-owned) |
| Replay-the-Tape route + Coverage trail | `coverage_view.py` + routing | add `/dash/replay` + a descriptive trail | spawn_task `task_568e63a8` |
| Heat-strip micro-glyph contrast (`pill p-SS`, `.c.up` greens at ~4.0) | `cockpit.py`/`dashboard.py` (inline/heat-strip) | accepted dense-grid exception (value also in adjacent cols) | documented, no change |
| Inline tag chips (#21262d/#30363d) on markets/sectors | frozen bodies (inline `style=`) | subtle shade nuance; inline → not class-reachable | documented |

## Owned files touched
`src/web/shell_skin.py` only (the `body.uk-skin` retint is the one lever that immunises many pages).
`ui_tokens.py`/`ui_kit.py` unchanged this wave (the W3 `--ink-3` token already does the AA heavy lifting).
