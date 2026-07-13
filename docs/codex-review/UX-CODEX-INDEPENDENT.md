# UX-CODEX-INDEPENDENT - Patearn Web Estate Review

## Executive Summary

1. Patearn has unusually strong analytical depth, but the journey still reads like an expert's workbench before it reads like a product.
2. The top-level IA is directionally right: Markets / Screener / Strategies / Tracker / Trust matches a professional workflow better than a flat lens dump.
3. The Markets rail is overloaded: 30 first-class lenses, most collapsed by default, with "News / Wire" and "Results reactions" buried at the end of Events & flow.
4. Beginners get scattered explanation, not a guided ramp. The glossary and reading guide exist, but only newer deep-data pages consistently use bottom-line/plain-English scaffolding.
5. Experts get dense tables and fast access once they know the names, but the best work is not sold as best work on the home page.
6. The biggest discoverability leak is not total orphaning anymore; it is "second-class surfaces" outside the lens contract: Pat, stock/index dossiers, legacy ratio/RS, replay, credibility fingerprint, Wolfe open trades, and stock news.
7. Route inventory confirms 156 live `/dash` paths versus 62 registry lens routes; many extras are APIs/actions/compat routes, but several are user-facing pages.
8. The news estate is confusing: `/dash/markets/wire` is a full market wire, while `/dash/news` is a stock-timeline page with no ticker selected and no registry lens.
9. Redundancy is now a UX tax: RS, rotation, momentum, bands, divergence, and sector momentum are correct as models but not legible as one "strength" workflow.
10. Seasonal work is valuable but split across tape, screen, divergence, and event pages without one obvious seasonal hub.
11. PAT is safe and useful for core screening queries, but it cannot reach much of the newer estate in natural language.
12. The SEBI/descriptive fence is mostly well preserved; keep making it explicit on any scanner that looks action-oriented.
13. Future-proofing should promote "route registry compliance" from convention to test: every GET HTML page must be a lens, nested child, dossier, API/action, or explicitly exempted with owner and rationale.

## Findings

### 1. P1 - The First Screen Is Expert-Dense And Has No Beginner Starting Path

EVIDENCE: Live `https://srv1704897.hstgr.cloud/dash` renders boards such as "Conviction", "Positioning", "Rotation", "Leaders", "Launchpad", "Accumulation watch", "Distribution watch", "RS Band", and "Attention". The content uses MEP, RS, DVPT, bands, and strategy jargon before offering a "what should I look at first?" path. Code evidence: home board definitions in `src/web/cockpit.py` include many expert pillars and labels at lines 394-481.

EVIDENCE: The reading/education layer exists separately in the Trust nav: `src/web/lens_registry.py:259` registers Glossary and `src/web/lens_registry.py:263` registers How to read. They are not a first-run overlay or a beginner lane on `/dash`.

PROPOSAL: Add a two-mode home treatment without reducing expert density:

- Default home keeps the expert cockpit.
- Add a persistent "Start here" strip above the boards: "1. Market mood, 2. What's changing, 3. Best evidence pages, 4. Ask Pat". Each item should link to `/dash/markets/market-internals`, `/dash/markets/attention`, `/dash/coverage`, and `/dash/pat`.
- Add one sentence per board in plain language, not more metrics. Example: "MEP asks whether delivery pressure looks like accumulation or distribution."

### 2. P1 - Markets IA Has Too Many First-Class Lenses For A Left Rail

EVIDENCE: `src/web/lens_registry.py` registers 30 Markets lenses. The generated list includes Big picture, Events & flow, Sectors, Strength & momentum, Rotation, Patterns, Participants, Wire, and Compare. The route inventory command showed the Markets nested routes from `/dash/markets/actions` through `/dash/markets/wolfe-scan`.

EVIDENCE: The live `/dash/markets/wire` rail collapses most groups by default: Big picture is open, while Strength & momentum, Rotation, Sectors, Patterns, and Events & flow are collapsed. News / Wire is the last item in the last collapsed group.

PROPOSAL: Make Markets a small set of workflow groups, not a long list:

1. Today: Attention, Wire, Results reactions, Corp actions.
2. Market State: Market internals, Rotation, Sectors, Sector economics.
3. Strength: RS hub, Leaders/Laggards, Momentum, Capture map, Divergence.
4. Patterns: Wolfe, Harmonic.
5. Seasonality: Seasonal tape, This-month, Index divergence.

Keep the underlying lens routes, but make the rail group labels task-oriented. "Events & flow" is too vague for news/results/actions.

### 3. P1 - Route Inventory Still Has User-Facing Pages Outside The Lens Contract

EVIDENCE: Runtime import of `src.main.app` found 156 live `/dash` paths and 62 registry lens routes. User-facing routes not represented as lenses/nested lenses include `/dash/pat`, `/dash/stock`, `/dash/index`, `/dash/ratio`, `/dash/rs`, `/dash/news`, `/dash/replay`, `/dash/credibility`, `/dash/wolfe/trades`, `/dash/theme`, and tracker compat pages (`/dash/watchlists`, `/dash/portfolios`, etc.).

EVIDENCE: Code route lines:

- `src/web/news_view.py:200` registers `/dash/news`; `src/web/news_view.py:208` registers `/dash/wire`.
- `src/web/wolfe_trades_view.py:441` registers `/dash/wolfe/trades`.
- `src/web/credibility_fingerprint.py:255` registers `/dash/credibility`.
- `src/web/dashboard.py:1178` registers `/dash/pat`.
- `src/web/dashboard.py:1220` registers `/dash/rs`; `src/web/dashboard.py:7119` registers `/dash/ratio`.
- `src/web/dashboard.py:5821` registers `/dash/stock`; `src/web/dashboard.py:7037` registers `/dash/index`.

PROPOSAL: Create a `RouteKind` contract checked in tests:

- `lens`: must be in `lens_registry.LENSES`.
- `nested_child`: must declare parent lens and appear in that lens's local tab/toggle.
- `dossier`: stock/index/theme pages, discoverable from search and row links.
- `api_or_action`: post endpoints, overlays, JSON, CSV, ack/save.
- `compat_redirect`: old URL redirecting to canonical nested path.
- `internal_dev`: `_ui`, offline.

Fail CI when a GET HTML route is none of these.

### 4. P1 - News/Wire Is Conceptually Split And Buried

EVIDENCE: `src/web/lens_registry.py:176` registers only `Lens("wire", "News / Wire", ... "/dash/wire")`. `src/web/v2_surfaces.py:55` mounts the news module sample route as `/dash/wire`.

EVIDENCE: Live `https://srv1704897.hstgr.cloud/dash/markets/wire` is a full market feed with headlines. Live `https://srv1704897.hstgr.cloud/dash/news` returns HTTP 200 but displays "Pick a stock to see its news timeline." That second page is not in the lens registry.

PROPOSAL: Split names and jobs clearly:

- Rename nav item to "Market Wire" and move it into a "Today" group near Attention.
- Rename `/dash/news` UI to "Stock news timeline" and expose it only inside `/dash/stock?sym=...`, not as a blank standalone page.
- If `/dash/news` remains public, make `/dash/news` show a search box plus examples, and add it as a nested child under Wire or Stock dossier, not as an unowned route.

### 5. P1 - The Best "Wow" Analyses Are Not Presented As The Product's Proof

EVIDENCE: Differentiating pages exist as first-class lenses:

- Attention bus: `src/web/lens_registry.py:70`.
- Market internals 22-year surface: `src/web/lens_registry.py:76`.
- Seasonal tape: `src/web/lens_registry.py:89`.
- All-weather capture map: `src/web/lens_registry.py:133`.
- Results reactions: `src/web/lens_registry.py:138`.
- Wolfe scanner: `src/web/lens_registry.py:172`.
- Evidence pack: `src/web/lens_registry.py:269`.
- Replay any date: `src/web/lens_registry.py:273`.

EVIDENCE: Live home emphasizes many boards equally. Attention appears, but market internals, seasonal tape, PIT replay, evidence pack, all-weather capture, and replay-any-date are not presented as a flagship tour.

PROPOSAL: Add a "Why this is different" band on `/dash` with 5 cards:

1. Point-in-time replay: `/dash/replay-any-date`.
2. Signal bus / attention: `/dash/markets/attention`.
3. 22-year market internals: `/dash/markets/market-internals`.
4. Calendar seasonality with null controls: `/dash/markets/seasonal-tape`.
5. Management credibility / promise ledger: `/dash/strategies/concalls` plus `/dash/credibility`.

This is not marketing fluff; it is procurement/demo orientation for expert visitors.

### 6. P1 - Education Scaffolding Is Uneven Across Old And New Pages

EVIDENCE: The reusable education helpers live in `src/web/infographics.py:496` (`how_to_read_link`), `src/web/infographics.py:502` (`bottom_line`), and `src/web/infographics.py:507` (`plain`).

EVIDENCE: Adoption is concentrated in newer pages: launchpad track, market internals, move anatomy, participants, reading guide, seasonal, seasonal screen, sector economics, and seasonal events. `rg` found helper calls in these files but not in major older pages like `dashboard.py` stock/rs/ratio/stocks, `rrg_view.py`, `rotation_view.py`, `rsband_view.py`, `screener_plus.py`, and `news_view.py`.

PROPOSAL: Define an "explainability minimum" for every public lens:

- One `bottom_line(...)` near the top.
- One "In plain English" line per non-obvious chart/table group.
- One link to `/dash/reading-guide` or `/dash/glossary`.
- Header tooltip glossary for all custom metric columns.

Roll it out first to `/dash/stocks`, `/dash/leaders`, `/dash/rrg`, `/dash/rsband`, `/dash/screen2`, `/dash/wire`, and `/dash/wolfe/scan`.

### 7. P1 - PAT Covers Core Screening, But Not The Complete Estate

EVIDENCE: Pat is closed-vocabulary by design. `src/pat/flows.py:1` says flows are pure read-only SQL templates compiled from chip parameters. `src/pat/engine.py:234` augments routed flows with `rs`, `fundamentals`, `accumulation`, and `movers`. `src/pat/web.py:2215` labels supported flows such as accumulation, RS, fundamentals, movers, index, distribution, pt14, redflags, stock, oscillators, credibility, confluence, strategy, compare, why, and trend.

EVIDENCE: Dispatch code in `src/pat/web.py:2349-2374` handles accumulation, RS, fundamentals, movers, and credibility. `src/pat/web.py:2660` handles a generic strategy board. There are no direct flows for wire/news, market internals, seasonal tape/screen/divergence, replay/replay-any-date, evidence pack, coverage, capture map, participants, buyback calculator, or Wolfe open trades.

PROPOSAL: Add Pat "navigation answer" flows for the estate, not necessarily full data answers:

- "show me today's news" -> `/dash/markets/wire`.
- "what changed today" -> `/dash/markets/attention`.
- "market breadth" -> `/dash/markets/market-internals`.
- "seasonality for X" -> `/dash/markets/seasonal-tape?...`.
- "replay INFY on 2024-06-04" -> `/dash/replay-any-date?...`.
- "open Wolfe trades" -> `/dash/wolfe/trades`.

Pat should say "I can open that page" when it cannot compute the answer directly.

### 8. P1 - Redundant Strength/Rotation/Momentum Pages Need A Unified Journey

EVIDENCE: The registry places related pages under several groups:

- Relative strength: `rs-hub` and `leaders` at `src/web/lens_registry.py:123-126`.
- Momentum: `momentum-scan` at `src/web/lens_registry.py:129`, `divergence` at line 149, `early-signals` at line 155.
- Rotation: `rrg`, `rotation`, `rsband`, `cycle-clock` at lines 140-146.
- Sector momentum: `sector-momentum` at line 157.

PROPOSAL: Keep separate analytical pages for experts, but create one "Strength workflow" landing:

1. Is the market/sector improving? Rotation Weather/Clock.
2. Which sectors lead? Sectors and RRG.
3. Which names lead inside strong sectors? Leaders.
4. Is it overextended or early? RS band, momentum, divergence.
5. Candidate table. Link to Screen+ filtered to the same context.

The page can be a guide/hub; it does not need new calculations.

### 9. P2 - Seasonal Surfaces Are Valuable But Fragmented

EVIDENCE: Seasonal lenses are registered separately: `seasonal-tape` at `src/web/lens_registry.py:89`, `seasonal-screen` at line 93, `seasonal-divergence` at line 97. `src/web/seasonal_events_view.py` also uses education scaffolding but was not in the live lens inventory output as a first-class lens.

PROPOSAL: Create one Seasonal hub with tabs:

- Tape: entity detail.
- This month: lookup screen.
- Divergence: pairwise index comparison.
- Events: event-linked seasonality if retained.

In the left rail, show one "Seasonality" group rather than three Big picture entries plus hidden event pages.

### 10. P1 - Credibility Has Two Destinations With Different Mental Models

EVIDENCE: The primary strategy nav labels Credibility at `src/web/lens_registry.py:215` and routes to `/dash/concalls`. A separate router is mounted at `/dash/credibility` in `src/web/v2_surfaces.py:117`, and live `/dash/credibility` shows a "Credibility fingerprint" picker with settled promise counts. This route is not a lens.

PROPOSAL: Make "Credibility" a small local sub-journey:

- `/dash/strategies/concalls`: board / ranking / deterioration tape.
- `/dash/strategies/credibility-fingerprint` or `/dash/strategies/concalls/fingerprint`: per-company promise timeline.
- Add the fingerprint as an in-page tab/toggle from the Credibility lens, not a separate hidden URL.

### 11. P2 - Tracker URL Compatibility Keeps Old Paths Alive But Muddy

EVIDENCE: Runtime routes include both nested tracker paths (`/dash/tracker/watchlists`, `/dash/tracker/portfolios`, etc.) and flat compat routes (`/dash/watchlists`, `/dash/portfolios`, `/dash/performance`, `/dash/import`, `/dash/dashboard`). The registry uses nested tracker routes in `src/web/lens_registry.py:244-252`.

PROPOSAL: Keep flat compat redirects for bookmarks, but ensure all in-app links and command-bar targets point to nested tracker paths. The command palette snippet in live HTML still maps `watchlists` to `/dash/watchlists` and `portfolios` to `/dash/portfolios`; update those to `/dash/tracker/watchlists` and `/dash/tracker/portfolios`.

### 12. P1 - Command Palette Search Is Helpful But Hard-Coded And Incomplete

EVIDENCE: `src/web/v2_surfaces.py:386` injects `cmdk_overlay()`. Live HTML contains a hard-coded `PAGES={...}` map with only selected pages: markets, screener, strategies, tracker, coverage, trust, news/wire, rs, growth, wolfe, rotation, sectors, conviction, accumulation, mep, stocks, credibility, screen, ratio, watchlists, portfolios, launchpad, participants, glossary. It omits many registered lenses: market internals, seasonal pages, attention, results reactions, capture map, sector economics, buyback calc, replay-any-date, evidence pack, spec sheets, ratings, SAST, holdings, etc.

PROPOSAL: Generate command-palette destinations from `lens_registry.LENSES` plus declared aliases. Do not hand-maintain `PAGES`. Add route-kind metadata for dossiers and nested children.

### 13. P1 - Trust Is Strong, But Demo/Procurement Proof Is Not The Default Journey

EVIDENCE: Trust surfaces are first-class: Glossary (`src/web/lens_registry.py:259`), Reading guide (`:263`), Evidence pack (`:269`), Replay any date (`:273`), Coverage and Testing. The live top nav has a Trust chip, but a first-time institutional reviewer landing on `/dash` sees mostly live screens before they see data boundaries, provenance, and zero-look-ahead proof.

PROPOSAL: Add an "Institutional proof" path:

- `/dash/evidence-pack` as the canonical demo route.
- Add a home-page "Audit trail" card linking Coverage, Spec sheets, Replay any date, Strategy validation, and Glossary.
- On every high-wow scanner, add a small footer: "Evidence: spec sheet | coverage | replay".

### 14. P2 - Some Labels Optimize For Internal History, Not User Mental Models

EVIDENCE: Labels like "MEP", "DVPT", "PIT", "pt14", "CCI", "RRG", "Divergence", "Risk-adj momentum", "Band locks", "Launchpad", and "Stealth" appear in nav or page titles. Glossary definitions exist, but labels themselves carry a learning curve.

PROPOSAL: Keep expert abbreviations where table density matters, but pair nav labels with plain descriptors:

- "MEP" -> "Accum/Distrib pressure".
- "DVPT" -> "Delivery intensity".
- "CCI" -> "Management credibility".
- "PIT replay" -> "Replay any date".
- "RRG" -> "Rotation map".

Do not remove abbreviations from advanced pages; put them second, not first, in beginner-facing chrome.

### 15. P2 - SEBI-Safe Fence Is Present But Should Be More Visible On Action-Looking Pages

EVIDENCE: The repo repeatedly states descriptive-only in registry comments and page prose, especially seasonal and evidence pages. However, live pages such as Wolfe open trades show terms like "open trades", "entry zone", "stop", "remaining ROI", and scanner rows, which can look prescriptive to a new user.

PROPOSAL: On action-looking pages (`/dash/wolfe/scan`, `/dash/wolfe/trades`, `/dash/launchpad`, `/dash/stocks`, `/dash/conviction`), add a compact persistent disclosure: "Descriptive scanner. No recommendation. Validate independently." Use the same visual language as data-quality banners.

### 16. P2 - Expert Density Is Good, But Expert Shortcuts Need More Consistency

EVIDENCE: Many dense pages include table filtering/export and row links. The stock and index dossiers are powerful (`src/web/dashboard.py:5821`, `src/web/dashboard.py:7037`), but the global route inventory shows expert destinations split between lens pages, dossier pages, overlays, and query-param children.

PROPOSAL: For experts, add consistent keyboard/URL affordances:

- `/dash/go?q=...` or command palette generated from registry.
- Every table row: stock dossier, lens-specific anchor, export.
- Every major lens: "open in Screen+" link preserving sector/cap/metric context.

### 17. P1 - Future-Proofing Needs A Test, Not More Convention

EVIDENCE: The code already recognizes the problem. `src/web/lens_registry.py` header says old nav was hand-maintained in multiple places and drifted. `src/web/v2_surfaces.py:42` defines durable router specs; `src/web/v2_surfaces.py:539-544` self-tests that router specs are mounted. `src/web/nested_nav.py` creates canonical nested URLs. But no evidence shows a test that rejects new unclassified GET HTML routes.

PROPOSAL: Add a `tests/test_dash_route_registry.py` gate:

1. Import `src.main.app`.
2. Enumerate every `GET` route beginning `/dash`.
3. Exempt regexes: overlays, JSON/CSV/action endpoints, POST-only, service worker/offline/internal `_ui`, compatibility redirects.
4. Require every remaining page to be in `lens_registry`, a declared nested child of a lens, or a declared dossier (`stock`, `index`, `theme`, `pat`).
5. Print a diff with suggested registry entry template.

This would have caught `/dash/news`, `/dash/credibility`, `/dash/wolfe/trades`, and future equivalents at PR time.

## Prioritized Top 10

1. Add the route-registry compliance test and explicit route-kind exemptions.
2. Rework Markets nav into task groups: Today, Market State, Strength, Patterns, Seasonality.
3. Promote a home-page flagship proof band: replay, attention bus, market internals, seasonal tape, credibility, evidence pack.
4. Resolve News/Wire split: market wire in Today; stock news timeline only inside stock dossier or as owned child.
5. Generate command palette destinations from `lens_registry` aliases instead of hard-coded page map.
6. Expand Pat navigation coverage for wire, attention, market internals, seasonal, replay, evidence pack, Wolfe trades.
7. Apply `bottom_line` / `plain` / glossary links to older high-traffic pages: stocks, leaders, RRG, RS band, Screen+, Wire.
8. Merge credibility fingerprint into the Credibility journey as a child/tab of Concalls.
9. Create a Strength workflow hub tying RS, rotation, bands, momentum, divergence, and sectors into one path.
10. Add visible descriptive-only disclosures to action-looking scanner pages, especially Wolfe trades and Conviction.
