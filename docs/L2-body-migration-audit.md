# L2 — Native body migration audit + bleed-through inventory

> **Lane L2 — Native bodies & chrome polish.** Created 2026-06-29. Live-render audit of the
> demo path (Coverage → Markets → RS → Screener → Stock) done IN-BROWSER against the live VPS
> (`https://srv1704897.hstgr.cloud/dash/...`), not from served markup — the local checkout DB is
> too sparse to render the real bodies (markets/screener/stock fall back to empty states locally).
> Method: navigate each page in Chrome, enumerate stylesheet rules, probe computed styles by
> injecting a native `uk-card`/`uk-t` component into each body.

## 1. Shell classification (which render path each demo page uses)

| Page | Route | Shell | Body language | Verdict |
|---|---|---|---|---|
| **Coverage / Trust** | `/dash/coverage` | **native** `ui_kit.shell` | `uk-card` / `uk-pill` / `uk-eyebrow` / `uk-badge` / `uk-stat` | **REFERENCE — fully native.** No `_BASE_CSS`, zero bare-element rules. |
| **Markets** | `/dash/markets` | legacy `_shell` (reskinned, `body.uk-skin`) | `maj` / `card` / custom `hstrip`/`hs-*` heat-strip / `pill`/`pos`/`neg` | legacy body, CSS-retinted only |
| **RS hub** | `/dash/rs-hub` | legacy `_shell` (reskinned) | self-contained `rsh-*` classes (not `_BASE_CSS`, not `uk-*`) | own mini design-system |
| **Screener** | `/dash/screener` | legacy `_shell` (reskinned) | frozen-pane `table.scr` / `scrwrap` + `g-*` column groups | legacy frozen-pane grid, retinted |
| **Screen+** | `/dash/screen2` | **native** `ui_kit.shell` | `uk-pill` + custom `cg-*` confluence columns (Lane B) | already native-built |
| **Stock dossier** | `/dash/stock` | legacy `_shell` (reskinned) | `card` / `kpi`/`box` / `tabbar` / `chip` / `fbtn` (classic `_shell`) | legacy body, retinted |

**Bodies live in FROZEN files** (`dashboard.py`, `cockpit.py` — Lane L1-owned). L2 may not edit them.
The two already-native bodies (Coverage, Screen+) prove the target look. The four legacy bodies are
reskinned (color-correct via `shell_skin._SKIN_CSS`) but still legacy-structured.

## 2. Bare-element CSS bleed-through inventory (the `9def4ff` bug class)

`dashboard._BASE_CSS` (injected on every `_shell` page → present on all four reskinned demo pages)
contains bare-element rules. These outrank nothing of higher specificity, but they FILL IN any
property a native `.uk-*` component does not self-assert, and win outright where the native rule
uses a bare or lower-specificity selector. Verified by enumerating live stylesheet rules on
`/dash/markets` (`body.uk-skin`) and confirming ABSENT on native `/dash/coverage`:

| Bare rule (in `_BASE_CSS`) | Computed leak onto a native probe component | Native rule that should win | Status |
|---|---|---|---|
| `nav {position:fixed;bottom:0;…}` | lifts `.uk-nav` out of flow, overlays logo+search | `.uk-top .uk-nav{position:static}` | **FIXED `9def4ff`** |
| `nav a {flex:1;text-align:center}` | stretches topbar tabs edge-to-edge | `.uk-top .uk-nav a{flex:0 0 auto}` | **FIXED `9def4ff`** |
| `h2 {font-size:16px;margin:18px 0 10px}` | native card `<h2>` renders 16px vs 21px on the reference | (none — `.uk-*` has no h2 rule) | **OPEN → L2 fixes** |
| `table {width:100%;border-collapse:collapse;font-size:13px}` | forces width/collapse/size onto `.uk-t` | `table.uk-t` (0,1,1) mostly wins | partial — re-assert defensively |
| `th {text-align:left;color;padding:8px 6px;font-weight:600}` | `.uk-t th` (0,1,1) beats bare `th` (0,0,1) | `.uk-t th` wins | OK by specificity; re-assert for safety |
| `td {padding:9px 6px;border-bottom}` | `.uk-t td` (0,1,1) wins | `.uk-t td` wins | OK by specificity |
| `header {position:sticky;…}` | topbar is divs, not `<header>` → no leak in practice | n/a | OK |
| `input,button {font-family:inherit}` | benign (matches native) | n/a | OK |

### Decision
Rather than chase rules one at a time, **L2 adds a defensive re-assertion block** in
`shell_skin._SKIN_CSS`, scoped `body.uk-skin .uk-*`, that re-states the native component geometry
(card padding/radius, `uk-h1`/`h2` scale, `uk-t` table metrics, `uk-stat`, `uk-pill`, `uk-seg`,
`uk-badge`). This immunises ANY native component dropped onto ANY reskinned page against present and
future bare-element bleed-through — the same neutralise-at-the-skin pattern as `9def4ff`, generalised.
This is the realistic, owned-file path to a consistent native look without editing the frozen bodies.

## 3. Migration approach (within owned files)

- **Item 2 (this doc's §2):** ship the `body.uk-skin .uk-*` re-assertion block. ✓ highest value.
- **Items 3–6 (Markets/RS/Screener/Stock bodies):** the bodies are frozen. The achievable, no-loss
  win is to deepen the reskin so the legacy primitives (`maj`, `card`, `kpi`/`box`, `tabbar`,
  `rsh-*`, `scr`/`g-*`) adopt true native ui_kit token geometry (radius/spacing/elevation/type), not
  just color — closing the structural gap to the native reference. A full body rewrite into new
  modules would duplicate large data-fetch paths inside frozen files (high blast radius) and is
  deferred; the reskin-deepen achieves the visual "native look end-to-end" goal at low risk.
- **Item 7 (Coverage):** verified fully native — the reference; no drift to bring back.
- **Item 8:** density / responsive / a11y / print already site-wide via `ui_tokens` + `density_js`
  (Lane A2); L2 confirms each migrated/deepened surface still holds them.

## 4. Evidence
- Live rule enumeration on `/dash/markets`: bare `h2`/`table`/`th`/`td`/`nav`/`nav a`/`header` all present.
- Same enumeration on `/dash/coverage`: all absent (clean native reference).
- Computed-style probe (injected `uk-card`+`uk-t`): on markets `h2`→16px, on coverage `h2`→21px — the
  measurable bleed-through this lane closes.
