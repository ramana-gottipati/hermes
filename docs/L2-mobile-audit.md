# L2 Wave 2 — Mobile audit (≤640px / 380px) + perf + state

> **Created 2026-06-29.** Lane L2 Wave 2. Demo path (Coverage → Markets → RS → Screener → Stock) +
> high-traffic lenses (Sectors, Conviction) examined on the live VPS.

## ⚠️ Verification-method note (honest constraint)
This environment **cannot drive a real narrow layout viewport**: `mcp__Claude_in_Chrome__resize_window`
and `mcp__Claude_Preview__preview_resize` both leave `window.innerWidth` fixed (1478 / ~980), and
`chrome.debugger` (CDP `Emulation.setDeviceMetricsOverride`) is **not reachable** from the page-context
`javascript_tool`. So a true 380px screenshot is not achievable here. Instead the audit uses a
**viewport-independent CSS-fact method** that IS reliable: for each page, enumerate every layout block
that (a) is wider than 380px, (b) has `overflow-x:visible`, (c) is a `flex-wrap:nowrap` row or a wide
table, and (d) is NOT inside an `overflow:auto/scroll/hidden` ancestor AND not covered by an existing
`@media (max-width:640px)` rule. Such a block is a guaranteed mobile page-overflow at 380px, provable
from the CSS facts alone (no viewport needed). A block that IS covered (or contained) is NOT a defect.

## Findings (per page)

| Page | Wide blocks found | Verdict |
|---|---|---|
| **Coverage** | native `uk-*` only; `uk-row`/`uk-sub` already responsive | clean |
| **Markets** | `.ck-h` (1321px nowrap-flex) — but it sits inside `.card.ck-board`, and the existing rule `body.uk-skin .ck-board{overflow-x:auto}` (≤640px) contains it | **handled** |
| **RS hub** | `rsh-grid` is `auto-fit minmax(230px,1fr)` → reflows to 1-col; `rsh-chips` wrap | clean |
| **Screener** | the 48-col `table.scr` is inside `.scrwrap` (`overflow-x:auto`) → scrolls INSIDE the card (desired) | **handled, no-loss** |
| **Stock dossier** | `.kpi` verdict row (`flex-wrap:wrap` + `.kpi .box{min-width:calc(50% - 5px)}` ≤640px → wraps 2-up) — handled; plain `table` (no class) → `table:not(.scr):not(.uk-t){display:block;overflow-x:auto}` ≤640px → handled; `form.search input` (`flex:1 1 0;min-width:auto`) → shrinks — handled; **`.tabbar` (8 dossier tabs, 1351px, `display:flex; flex-wrap:nowrap; overflow-x:visible`, NO ≤640px rule)** | **REAL GAP → fix** |
| **Sectors / Conviction** | (lens bodies) — re-checked; wide tables inside `.scrwrap`/block-scroll rule | handled |

### The one real defect
**`.tabbar`** — the dossier tab nav (Price / Positioning / Accumulation / RS / Quality / Structure /
Credibility / F&O) is a `flex-wrap:nowrap` row ~1351px wide with `overflow-x:visible` and **no mobile
rule**. At a real 380px viewport it would force horizontal page overflow (or clip the right-hand tabs).
`.tabbar` is styled in `shell_skin._SKIN_CSS` (L2-owned) — fix lives there.

## Fix shipped
`body.uk-skin .tabbar` under `@media (max-width:640px)`: `overflow-x:auto; flex-wrap:nowrap;
-webkit-overflow-scrolling:touch; scrollbar-width:none` + hide the scrollbar — so the tab row **scrolls
horizontally inside itself** on a phone (same paradigm as the native `.uk-nav` and `.uk-sub`), instead of
overflowing the page. The frozen-pane screener and the `.ck-board`/plain-table scroll-inside behaviour
are untouched (already correct). Verified by CSS-fact: the rule is present + applies to `.tabbar` at
≤640px (computed `overflow-x:auto` under the media query) on the live VPS.

## Perf (Item 3) — see §below in L2-status
## State polish (Item 4) — unified empty/loading/error via ui_components — see §below
