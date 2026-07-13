# QA Issue Register — patearn live site

> **Lifecycle: PERMANENT.** keep-forever round-1 QA findings record; not retired. Registered in `docs/DOC_INDEX.md`.


**Method:** In-browser sweep of the live VPS app (localhost:8000 via SSH tunnel), driven with Claude-in-Chrome as a skeptical user. Every surface in `src/web/lens_registry.py` plus `/dash/stock?sym=RELIANCE` and `/dash/pat`. For each: computed-style probe (greens-in-use by exact RGB, table/row counts, overflow at the real CSS viewport, `NaN`/`None`/error-text scan), console read, and a screenshot. Findings are graded by what was **confirmed in the DOM/computed styles**, not by eyeballing a screenshot.

**Date:** 2026-06-29 · **Reviewer:** QA-SWEEP agent · **Build under test:** HEAD `29cd9a3`

**Viewport note (important for reading this register):** the page renders at **1182 CSS px** (devicePixelRatio 1.25). The screenshot canvas only captures ~940 CSS px of width, so the right ~20% of every page is cropped *in the screenshots*. I re-verified with `getBoundingClientRect` that at the true 1182px viewport **no page overflows and no table/card is actually clipped** (`document.scrollWidth === innerWidth` on every page checked; wide screeners scroll correctly inside their own container). Apparent "right-edge clipping" in screenshots is a capture artifact, **not** a product bug, and is deliberately **excluded** from this register. Behaviour below 1182px (e.g. 1280px physical at 1.5× DPR ≈ 853 CSS px) was **not** testable through the fixed screenshot viewport and is marked needs-confirm where relevant.

**Console:** the only exceptions seen are `"A listener indicated an asynchronous response… message channel closed"` — these originate from the **Claude-in-Chrome extension itself**, not the app. **Zero app-level JS errors** were observed across the whole sweep. No 500s, no `NaN`, no stray `None`/`undefined` in rendered text on any surface.

---

## Top 10 to fix first

| # | Sev | Surface(s) | One-liner |
|---|-----|-----------|-----------|
| 1 | P1 | All cockpit-rendered pages | RS-state pills render truncated to 5 chars — "UPTRE", "BREAK", "CONSO", "DOWNT" — from a `{st[:5]}` slice in `dashboard.py`. Reads as broken on flagship tables (Leaders, Sectors). |
| 2 | P1 | Site-wide theme | Five different greens in use; institutional `--up #3fd486` competes with three GitHub greens (`#3fb950`, `#7ee787`, `#2ea043`). All five coexist on `/dash/screener`. |
| 3 | P1 | `/dash/wire`, `/dash/compare` | Sub-nav highlights "Overview" instead of the page's own lens ("News / Wire" / "Compare"). Active-lens resolution falls back to the first Markets item. |
| 4 | P1 | `/dash/screen2` (Screen+) | Screener sub-nav is wrong on this page only: it shows **"Strategist"** (a Strategies lens) and **omits "Review"**. Diverges from the registry-driven sub-nav every other Screener page renders. |
| 5 | P2 | `/dash/stock` Price tab | Eight stacked "… ELSEWHERE" cross-link rails sit between the tab bar and the chart, pushing the candle chart ~2 screens down. The chart is the point of the Price tab. |
| 6 | P2 | `/dash/rrg`, `/dash/rotation`, `/dash/rsband`, `/dash/testing` | `<title>` missing the "· patearn" suffix every other page has ("RS rotation", "Strategy validation", …). Tab-title inconsistency. |
| 7 | P2 | `/dash/stocks` | Same surface is named three ways: nav lens "Positioning", `<title>` "Stocks", page `<h2>` "Stock screen". Pick one. |
| 8 | P2 | `/dash/stock?sym=RELIANCE` | Stray bare dash in the headline: "RELIANCE **-** · Reliance Industries Limited" (an empty field rendering as " - "). |
| 9 | P2 | `/dash/wire` | With an empty watchlist the page is just an empty-state — there is **no** market-wide news fallback, so a fresh user sees a dead page under a top-level Markets lens. |
| 10 | P2 | Screener IA | Two near-duplicate screeners — "Screen (classic)" (61 cols, green-fragmented, white symbol links) and "Screen+" (46 cols, green-correct, blue symbol links). Overlapping purpose + divergent styling is confusing; decide which is canonical. |

---

## Full register

| Sev | Surface | Issue | Evidence | Suspected owning file |
|-----|---------|-------|----------|----------------------|
| **P1** | Leaders, Sectors, + any "all-three-RS" table | RS-state pills are sliced to 5 characters, so "UPTREND"→"UPTRE", "BREAKOUT"→"BREAK", "CONSOLIDATING"→"CONSO", "DOWNTREND"→"DOWNT". Confirmed it is a **content** truncation, not CSS: `pill.innerText === "UPTRE"` with `overflow:visible` and `scrollWidth === clientWidth` (text fits the box). On Leaders the first data row's pill cells read literally `["BREAK","BREAK","UPTRE"]`. | screenshot ss_030850al0 (Leaders), ss_3872nn9is (Sectors "UPTRE"/"CONSO"). DOM: `firstRowCells:[…,"BREAK","BREAK","UPTRE"]` | `src/web/dashboard.py` — `{st[:5]}` at lines **1212, 1505, 1525, 1600, 1669, 1716, 1717, 1718** |
| **P1** | Site-wide (theme) | Palette fragmentation: institutional value-green is `--up:#3fd486` (`ui_tokens.py:44`), but legacy GitHub greens are used widely instead — `#3fb950`, `#7ee787` (status pills), `#2ea043`. The probe counts **all five** greens on `/dash/screener` (`3fb950×240, 7ee787×517, 1f6f3a×226, 2ea043×31, 3fd486×193`). Newer view-modules are correct (`rotation`, `screen2`, `growth`, `coverage`, `strategist` use only `#3fd486`); the cockpit/dashboard-rendered pages are the offenders. These are different hues (teal-green vs yellow-green), visibly inconsistent side by side. | DOM greens-by-RGB per page (recorded for all 35). Worst: ss_6018z0nxq (Screener). `dashboard.py:106 .p-UPTREND{color:#7ee787}` | `src/web/cockpit.py` (`#3fb950` accents/tiles ~30 occurrences incl. `_ck_tile` calls 1307-2455, `366` RS accent); `src/web/dashboard.py:105-107` (pill colors `#7ee787`); participants/mep use `#2ea043` |
| **P1** | `/dash/wire`, `/dash/compare` | Sub-nav active-highlight is wrong: on both pages the lens with class `on` is **"Overview"**, not the page's own lens. Confirmed via DOM: on `/dash/wire` only "Overview" has class `on` + the active background `rgb(24,34,47)`; "News / Wire" has none. Same on `/dash/compare` (active = "Overview"). The page's `active` value isn't resolving to the `wire`/`compare` lens key, so the highlighter falls through to the first Markets item. | DOM: `activeMatches:[{txt:"Overview",cls:"on",bg:"rgb(24,34,47)"}]` (wire); `activeSubnav:["Overview"]` (compare). ss_8640byrjn, ss_8458alepm | wire route: `src/web/news_view.py` (router passes wrong/empty `active`); compare route; highlight logic `src/web/v2_surfaces.py:261,318` |
| **P1** | `/dash/screen2` (Screen+) | The Screener sub-nav rendered on this page is non-registry: items + hrefs are `Screen→/dash/screener, Screen+→/dash/screen2, Themes/Baskets→/dash/themes, **Strategist→/dash/strategist**, Workbench→/dash/workbench`. "Strategist" belongs to the Strategies altitude; **"Review" (`/dash/tags-review`) is missing**. Every other Screener page (screener, themes, tags-review, workbench) renders the correct set (…·Review·Workbench), so this page builds its own strip. | DOM (screen2): subnav hrefs list incl. `Strategist -> /dash/strategist`, no Review. Contrast `/dash/themes` subnav = "…Themes/Baskets·Review·Workbench". ss_7444084l7 | `src/web/screener_plus.py` |
| **P2** | `/dash/stock` (dossier) Price tab | Eight "… ELSEWHERE" cross-link rails (RELATIVE STRENGTH / PARTICIPANTS / CONVICTION / POSITIONING / MEP / STRUCTURE / CREDIBILITY / GROWTH ELSEWHERE) stack vertically between the dossier tab bar and the chart controls. A user who clicks the default **Price** tab scrolls through ~8 link rows + the control rows before any candles appear. The chart itself renders correctly (candles + MA50/MA200 + zone overlay, OHLC header). | ss_3708n39vc (header), ss_1469qn2in (rails+controls), ss_3635uc35q (chart renders fine, no error) | `src/web/stock_chart.py` (and the dossier assembler that injects the elsewhere rails) |
| **P2** | `/dash/rrg`, `/dash/rotation`, `/dash/rsband`, `/dash/testing` | `<title>` lacks the "· patearn" suffix used everywhere else. Observed titles: "Relative rotation — sectors", "RS rotation", "RS support & resistance", "Strategy validation". | DOM `document.title` per page | `src/web/rrg_view.py`, `src/web/rotation_view.py`, `src/web/rsband_view.py`, `src/web/testing_view.py` (and `rs_section.py`) |
| **P2** | `/dash/stocks` | One surface, three names: nav lens label "Positioning", `<title>` "Stocks", page `<h2>` "Stock screen". Inconsistent labelling for the same page hurts orientation. | DOM: `title:"Stocks · patearn"`, `h2:"Stock screen"`; registry label "Positioning" | `src/web/dashboard.py` (the `/dash/stocks` `_shell` title + the page `<h2>`) |
| **P2** | `/dash/stock?sym=RELIANCE` | Headline renders a stray bare dash: "RELIANCE **-** · Reliance Industries Limited" (h1 and sub-line). Looks like an empty field (exchange/ticker?) being joined with " - " separators. | DOM `h1:"RELIANCE - · Reliance Industries Limited"`. ss_3708n39vc | `src/web/dashboard.py` or `src/web/stock_chart.py` (dossier header template) |
| **P2** | `/dash/wire` | Wire is entirely watchlist-gated; with an empty watchlist it shows only "Your watchlist is empty…" — there is no market-wide / global news fallback, so a top-level Markets lens reads as a dead page for any user who hasn't built a watchlist. (Possibly by design, but weak for an institutional demo.) | ss_8640byrjn; body text = single empty-state line (313 chars) | `src/web/news_view.py` (`render_market_wire` / empty path) |
| **P2** | Screener altitude (IA) | Two overlapping screeners with divergent styling: "Screen (classic)" (`/dash/screener`, 61 cols, uses all 5 greens, **white/bold** symbol links) vs "Screen+" (`/dash/screen2`, 46 cols, only `#3fd486`, **blue** symbol links, has Pat hooks + saved screens). Overlapping purpose + inconsistent symbol-link colour and green palette between the two is confusing. Decide canonical, or visually unify. | ss_6018z0nxq (classic), ss_7444084l7 (plus). DOM col counts 61 vs 46; greens differ | `src/web/dashboard.py` (classic) vs `src/web/screener_plus.py` (plus) |
| **P2** | `/dash/pat` | `<title>` uses an em-dash separator "Pat — patearn" where the rest of the site uses "· patearn". Minor brand-consistency nit. | DOM `title:"Pat — patearn"` | `src/web/dashboard.py` (`_shell("Pat — patearn", …)` ~line 1469) |
| **P2** | `/dash/watchlists` | Empty-state has a lone "." (period) on its own line at the bottom and a circle glyph that reads like a loading spinner — could be mistaken for "still loading". Cosmetic. | ss_2408b5lbo | `src/web/dashboard.py` (watchlists empty-state) |
| needs-confirm | All pages, < 1182px CSS width | Could not test viewports narrower than 1182 CSS px through the fixed screenshot canvas. At 1182px everything fits with zero overflow; whether the multi-card stat rows / wide forms wrap gracefully at ~1280px-physical-at-1.5×-DPR (~853 CSS px) is unverified. The portfolio/watchlist "+ Add a stock" forms and 7-8-tile stat rows are the likeliest to need a wrap rule there. | JS: `document.scrollWidth === innerWidth (1182)` on every page; below that untested | `src/web/ui_tokens.py` / responsive grid rules |

---

## Surfaces swept — clean (no issues beyond the global theme greens)

These rendered correctly, data-rich, on-theme, no errors, controls functional:

- **Markets:** markets (overview), rrg (animated 4-quadrant RRG, Play control), rotation (4-phase weather cards), rsband (lanes/clock/RRG), participants (FII/DII/Pro/Client), compare (rebased Nifty 500 vs 50 line chart — default populated)
- **Screener:** screener (61-col frozen-pane flagship, horizontal scroll works), themes (29 themes / 375 tagged), tags-review (proposal + manual-tag tables, ✓/✗ controls), workbench (every-signal one sortable table, CSV export)
- **Strategies:** strategist ("Workbench" board, confluence alerts, credibility RRG tiles), conviction (3-pillar shortlist), mep (signed accum/distrib, 300 rows), cpr (reversals/compression, ★-tier, D-W-M band tiles), concalls (credibility worst-first, settlement-graded), growth (concall forward-looking ₹-amounts), launchpad (validated explosive-move setups, RISK-OFF regime banner)
- **Tracker:** dashboard, portfolios (add-stock form + positions), performance (XIRR scoreboard) — all functional with clean "—" empty-cell handling
- **Trust:** coverage (the polished trust front-door — Replay-the-Tape, settlement funnel, sub-tabs), testing (honest strategy-validation ledger, "none beats buy-and-hold net of cost")
- **Deep dossier** `/dash/stock?sym=RELIANCE`: hero cards, theme pills, 9 dossier tabs, candle chart with overlays — all render; only the buried-chart UX (#5) and stray-dash (#8) noted
- **Pat** `/dash/pat`: NL search functional — clicking "biggest movers today" resolved to "Today's movers" + a 60-row table (verified live, not a dead control)

## Counts
- **P0 (broken):** 0
- **P1 (wrong / confusing):** 4
- **P2 (polish):** 8 (+1 needs-confirm)
- **Unreachable surfaces:** 0 — all ~35 nav surfaces + dossier + Pat loaded (HTTP 200, correct chrome)
