# Patearn — UI Architecture v2 (the complete schema redesign)

> **Status:** DESIGN — architect synthesis, build-gated. Authored 2026-06-23 by a panel (financial-analyst proxy · preservation-census auditor · design-researcher w/ web sources) + architect synthesis.
> **This is the canonical IA/schema doc.** Supersedes the IA portions of `docs/ui-design.md` + `docs/ui-redesign-2026-06.md` (those remain valid for the doctrine + the additive Phase-0/1 already shipped).
> **Cardinal rule:** NOTHING is deleted or rendered dead. Every metric/variant/percentage/comparison is explicitly re-homed (see §8 no-loss census). This session is DESIGN ONLY — no code removed, no orphan deleted yet.
> **Mandate (Ramana, 2026-06-23):** unload the overloaded dashboard; give Relative Strength a proper first-class home (the unified Lanes/Clock/RRG section is the seed); zero redundancy, zero orphans; real navigation + index→component→constituent drill-down; fix buried news; fix too-wide charts + add fullscreen; responsive by experience not enumeration; a rules system that auto-places future components; light, no lag, every component tied to coherent logic.

---

## 0. STRESS-TEST CORRECTIONS (adversarial red-team, 2026-06-23 — these SUPERSEDE any conflicting text below)

A four-angle red-team (taxonomy · analyst-workflow · performance · no-loss/migration) found real flaws in the v2 draft. Binding corrections:

- **0.1 — RS belongs under MARKETS (macro altitude), NOT Strategies. [reverses §3-B / §4.]** v2 (all-RS-under-Strategies) *regresses* the headline journey: it pushes `leaders` from 2 clicks → 3, deeper into the menu the friction log calls the wrong cupboard, and pulls sector-rotation out of the macro workspace. ~85% of RS already lives under Markets; the only real misfiling is `leaders`. **Correct model — RS distributes by altitude:** macro RS (**Leaders · Sectors · Rotation[Momentum/Level/Phase]**) = a first-class section **under Markets** (move `leaders` here); single-name RS = the dossier RS tab (already built); RS-as-screen (rs_rank/slopes) = a Screener column-group (already there). **Strategies keeps stock-selection lenses only** (DVPT/MEP/CPR/Quality/CCI/Conviction/Launchpad). The v2 claim "RS is the only lens with a sector dimension" is FALSE (MEP/DVPT/Quality have sector aggregates) — RS isn't special; its macro face is just Markets content. The user's unified Lanes/Clock/RRG section = the **Rotation** sub-section under Markets.
- **0.2 — Taxonomy must be MECE; add three kinds. [extends §3.]** Altitude/Lens/Overlay is not exhaustive. Add **Syntheses** (Conviction = blend of Positioning+RS; opts OUT of a dossier tab — renders as a ranking + verdict pill); **Attribute families** (Key-price · Character · Context — first-class Screener column-groups, not lenses); **Content** (News/Timeline). **Launchpad = an event-screen** (a scan/list), not a standing lens — gets a Strategies entry + home tile but no always-on dossier tab/column.
- **0.3 — `/dash/ratio` is SACRED — KEEP it, do NOT redirect. [reverses §5 / §8.]** The `build-additive-never-replace` doctrine marks `/dash/ratio` sacred; code intends it to stay as the full RS-ratio sub-page (also vs Nifty 50). The Index page LINKS to it; it is not retired.
- **0.4 — The §9 registries are TO-BE-BUILT, not existing. [corrects §9.]** Only `STRATEGY_REGISTRY` exists; nav/sub-nav/dossier-tabs/screener-groups are hand-maintained in 4 places. "Register once → self-place" is the TARGET (net-new scaffolding), not current behaviour — no present-tense "enforces."
- **0.5 — No-loss census widened. [extends §8.]** v2's census was RS-scoped and omitted live surfaces. Explicit homes added: **/dash/participants** (FII/DII/Pro/Client OI overlay → Markets; currently an orphan — give it a Markets entry); **/dash/workbench** (wide raw-signal grid → Strategies; home for the ~30 long-tail `stock_signals` columns); **/candidates** (legacy Stage-1 screen → kept as-is or re-homed to Pat, not dropped); **/dash/scan** (keep as a deep-link unless `/dash/stocks` provably reproduces its layered sort + Near-P); **Tracker import/export** family; the **non-RS `stock_signals` long tail** (turnover-surge, deliv-updown, drift, trade-count, gap-to-key… → Screener groups + Workbench, frozen).
- **0.6 — Several v2 "fixes" are already shipped. [corrects §2 / §11.]** The **dossier sticky tab bar EXISTS** and the 3 RS `<h2>` blocks are ALREADY one RS tab — so P5 only ADDS a News/Timeline tab; do NOT rebuild. The friction-log line about a 1,100-line scroll is stale.
- **0.7 — Performance guardrails (hard). [binds §4 / §5.]** Every hub/landing/column reads PRECOMPUTED tables (`leaders_laggards`, `_sector_rows`, `rrg.latest_all`, `rsband.latest_all` / `band_home_inner`, `phase_movers`) — NEVER the on-read recompute (`current_all`/`band_lane`/`_lane_data`/per-member adjusted-close RS), reserved for user-clicked deep-dives. Index RS-component drill = a **toggle on the already-inline constituent table** (vs-sector / vs-broad), NOT 3 eager-rendered doors. De-dupe the home `conviction_shortlist`/`leaders_laggards` (run once) and make count tiles `COUNT(*)`.
- **0.8 — Migration safety (hard). [binds §11.]** The parallel Wolfe session owns `dashboard.py` and is editing `_WS`/`_SUBNAV` (it added `"wolfe"`). Do NOT co-edit those dicts. Build the RS-section consolidation + registries in a **NEW module with a thin hook**; defer `_WS`/`_SUBNAV` edits until the file frees; reconcile the Wolfe nav entry WITH the parallel owner (Wolfe is overlay-only per §3-C, but do not unilaterally remove their shipped nav entry — coordinate).

---

## 1. Design constraints (what every decision must satisfy)
1. **Unload the dashboard** — it must not be the only route to RS, nor a wall-of-everything.
2. **RS = a first-class top-level workspace** (the seed: the unified Lanes/Clock/RRG section).
3. **Zero redundancy / zero orphans** — every screen has one logical home; duplicates merge; orphans re-home.
4. **Preserve every RS measure** (§8) — nothing dies or goes dead.
5. **News not buried** — scoped + co-located (per-stock Timeline + a rail), not a bottom card.
6. **Charts** bounded (height + width cap) + fullscreen toggle + multi-pane + tap-tooltips.
7. **Real drill-down** — index → its 3 RS components → constituents, breadcrumbs throughout, insights live *at* the index.
8. **Preserve all comparison/add controls + params** (overlay, rebase, ranges, denominators, presets).
9. **Responsive by progressive disclosure** — summary on narrow, full grid on wide; never just enumerate.
10. **Rules system** — registries so new components self-place (no manual bolting).
11. **Light, no lag, logical** — server-render + vanilla JS; every component tied to coherent logic.

---

## 2. Analyst friction log (preserved verbatim — the "why" of this redesign)

*(From the buy-side analyst proxy walking the real decision workflow. Kept intact per Ramana's instruction.)*

- **(a) RS only reachable from an overloaded home — worse than stated.** The RS ecosystem has **no first-class home**; its pieces are scattered across `/dash/leaders` (Strategies), `/dash/rrg`, `/dash/rotation`, `/dash/rsband` (Markets▸Rotation), `/dash/rs`, `/dash/sectors`, and three sections of the stock dossier. `/dash/leaders` — the single most decision-relevant RS screen (the three-layer alignment table) — is filed under **Strategies▸"Strength"**, where I'd never look for a market-wide leaders list. `_WS` splits the RS family across two top-level workspaces.
- **(b) News buried, and worse.** On `/dash/markets` the headlines card renders dead-last after the full index bundle — I never scroll there. The **stock dossier has no News at all**; when evaluating a name, company news is exactly what I want and it isn't there. `sent_news` is market-wide only (no per-symbol tag).
- **(c) Charts too wide, stretch the page, no fullscreen.** `.wrap.wide` is `max-width:1900px`; on a wide monitor the price/index charts stretch edge-to-edge, candles hard to read. RRG SVG caps at 760px but the lane SVG is `width:100%` and balloons. No fullscreen anywhere. The RRG/lane/markets-rotation SVGs are hover-only → on touch their unique numbers (RS-ratio, Mansfield, band%, POC) are unreachable.
- **(d) Can't click an index and drill into its 3 RS components → constituents.** The pieces exist but are split across two pages (`/dash/rrg?idx=` momentum, `/dash/rsband?idx=` level) with two different `?vs=` toggles and opposite defaults. There is no single "click index → see its 3 RS components → click one → ranked constituents" path. `/dash/index` doesn't offer the constituent RRG inline (links out).
- **(e) Redundant screens.** `/dash/ratio` and `/dash/index` both render own-price chart + RS-ratio + returns + valuation + constituents (index_detail's own comment calls itself "the superset of the old /dash/ratio") — both live, both linked. `/dash/sectors` vs `/dash/rs` both rank sectors by RS with the same strip — should be one sortable table. Stock dossier has **three** consecutive "Relative strength" `<h2>` blocks.
- **(f) Having to remember which screen holds which metric — the core tax.** RS-momentum percentile→only `/dash/rs`; RRG quadrant+Mansfield+RSI-of-RS+capture→only `/dash/rrg`; band%/POC/regime/R²/verdict→only `/dash/rsband`; weather→sectors/rotation/markets but not `/dash/rs`; 3-layer aligned→only `/dash/leaders`. Five vocabularies, no glossary surface.
- **(g) Two sub-nav paradigms** (Tracker's `_track_subnav` vs the newer `_subnav`, which renders nothing on home/screener).
- **(h) Cryptic Rotation labels** "Map · Weather · Band" hide the function (which is RRG-momentum, phase, level).
- **(i) Inconsistent benchmark toggles** — `/dash/rrg ?vs=sector|broad` vs `/dash/rsband ?vs=broad|sector`, opposite defaults.
- **(j) Rotation advertised in three places** (home board, markets tile cluster, markets sub-nav) yet still has no canonical home.
- **(k) Stock dossier has no in-page navigation** — a ~1,100-line single scroll; no sticky tab bar.

**Bottom line (analyst):** *the data and analytics are best-in-class; the problem is purely structural findability.*

---

## 3. The governing principle — ALTITUDES vs LENSES (corrected 2026-06-23)

> **Revision (Ramana's challenge, 2026-06-23):** v1 of this doc made Relative Strength a top-level tab. That was **incoherent** — RS is one *lens* among many (DVPT, MEP, CPR, Quality, CCI, Wolfe…); elevating only RS implies it outranks the others with no rule to justify it. Corrected below.

**The app contains two kinds of things, and the top menu is ONE of them:**

**A. Altitudes — WHERE you look (these are the navigational destinations / top menu):**
| Altitude | Home |
|---|---|
| The whole market | **Markets** (regime, breadth, + a sector-rotation preview that links into the RS lens) |
| The whole universe, filtered | **Screener** (every lens = a column-group) + Themes-as-scope |
| The lens launcher (market-wide ranked deep-dive per lens) | **Strategies** |
| Your positions | **Tracker** |
| Ask | **Pat** |
| One sector/index | **Index page** (destination, not a tab) |
| One stock | **Stock dossier** (destination, not a tab) |

**Net top-nav: `Markets · Screener · Strategies · Tracker · Pat`** (5; Themes→Screener scope). Phone: Priority+ overflow.

**B. Lenses — HOW you evaluate (cross-cutting; NEVER a top-level tab):** Relative Strength, Positioning (DVPT), Accumulation (MEP), Structure (CPR), Quality (pt14), Credibility (CCI), Conviction, Launchpad, Ignition…

**THE RULE — every lens manifests at the same consistent touchpoints:**
| A lens appears as… | …at this altitude |
|---|---|
| a **tab** | Stock dossier |
| a **column-group** | Screener |
| a **deep-dive section** (its canonical market-wide home) | **Strategies** |
| a **section / preview** — *only if it has a sector/market dimension* | Index page / Markets |

So **RS is one lens, handled exactly like the others** — unified into one rich **Strategies ▸ Relative Strength** section (its 5 sub-lenses, §4), and *also* surfaced as the dossier RS tab, a screener column-group, the Index-page RS section, and a sector-rotation preview on Markets. **Unified and findable, but not elevated.** The one nuance: RS is the *only* lens with a genuine sector/market dimension (sector rotation) — handled by **cross-linking** Markets→RS, not by giving RS a tab the others lack.

**The rules system (registry) enforces this:** register a lens once → it auto-gets a dossier tab + a screener column-group + a Strategies deep-dive section (+ an Index/Markets preview if it declares a sector dimension). A new lens (Ignition, Wolfe, anything future) self-places — the registry IS the "parking place," so nothing is ever bolted onto the dashboard again. (See §9.)

**C. Overlays — things you toggle ON A CHART (never nav, never a screener column, never a Strategies section):** Wolfe waves, institutional-zone price-lines, CPR pivot lines, moving averages, key-price bands. An overlay is a checkbox/menu on the **stock chart** and the **index chart** only; it draws on the existing price/RS chart and has zero footprint elsewhere.
- **Wolfe wave is an Overlay (Ramana, 2026-06-23):** it is NOT settled, so it gets **no screener column, no Strategies lens, no dossier tab, no nav entry** — it is purely a **"Wolfe wave" toggle on the stock and index charts** (its existing `wolfe_overlay` snippet + the `#wfChk` checkbox is exactly right; keep it there and nowhere else). If Wolfe later proves out, it can be *promoted* to a lens via the registry — but not before.
- **The rule for overlays:** registered in an `OVERLAY_REGISTRY` (§9) that only ever injects a toggle into the chart toolbar. This is the clean home for "experimental / chart-only / not-yet-a-strategy" signals — so unsettled ideas have a place without polluting the nav, screener, or strategy set.

Home (`/dash`) becomes a *light* saved-overview, not a dumping ground.

---

## 4. Strategies ▸ Relative Strength — the RS lens's canonical home (the core deliverable)

> Reached via **Strategies ▸ Relative Strength** (NOT a top-level tab — see §3). This is the unified market-wide RS deep-dive; the stock-level RS lives on the dossier RS tab and the sector-level RS on the Index page (§5), all cross-linked to here.

**One section, five lenses, ordered by how RS decomposes — rank → momentum → level → phase.** Each is a sub-nav tab within the RS section; the set is **registry-driven** (`RS_LENS_REGISTRY`) so a new RS lens self-adds. Every lens carries ONE unified benchmark toggle (**vs Nifty 500 / vs Nifty 50**, default 500) — killing the inconsistent `?vs=`/`?den=` defaults. The Strategies hub gives every *other* lens (DVPT, MEP, CPR, Quality, CCI, Conviction, Launchpad, Wolfe) the same kind of unified section — RS is not special, just the richest.

| Lens (tab) | Question it answers | Seeded from | Holds (must keep) |
|---|---|---|---|
| **Leaders** *(default)* | Who is strong-in-strong / weak-in-weak? | `/dash/leaders` (promoted out of Strategies) | the 3-layer alignment table (stock-vs-broad · stock-vs-sector · sector-vs-broad), rs_rank, "Open in Screener" |
| **Sectors** | How do sectors rank on RS right now? | merge `/dash/sectors` + `/dash/rs` into ONE sortable table | returns 1m/3m, RS heat strip 1m–24m, weather badge, RS-momentum composite + **percentile bar**, trend-state |
| **Momentum** | Direction of travel (rotating where)? | `/dash/rrg` | RRG scatter (RS-Ratio × RS-Momentum), quadrants, **tails 3/6/12/24m** + Play, quadrant-sorted table (RSI-of-RS, Mansfield, up/down-capture, down-excess), flag pills |
| **Level** | Cheap or rich vs its own RS range? | `/dash/rsband` (the unified **Lanes/Clock/Channel** view-switcher) | rs_band_pct 0–100, POC magnet, regime (mean-rev/trending), trend-R², band-state, the **to-support%/to-resistance%** entry gauge, verdict (Accumulate…Fade) |
| **Phase** | Lifecycle state + fresh turns? | `/dash/rotation` | 4-phase weather grid (Tailwind/Recovery/Rolling-over/Headwind), **just-turned movers**, leverage marks (RS▲>price, ⚡accel, ✅deliv, abs✔, RSI hot/cold) |

**Notes on the seed:** the parallel session's unified section ([Lanes][Clock][RRG] in `rsband_view`) maps in cleanly — **Lanes + Clock + Channel are the three *views* of the Level lens** (same band data rendered 3 ways → a view-switcher inside "Level"), and **RRG becomes the Momentum lens**. This separates by *concept* (the coherent logic Ramana asked for: each lens = one question) rather than by viz. Nothing is lost; the work is re-slotted.

**RS section landing:** a compact **RS overview** — the regime-relative read + the top of each lens (top leaders, hottest sector, sharpest rotators, names at RS support, fresh phase-turns) — each a preview that opens its full lens. This is the "experience the strategy" entry the responsive brief wants.

**Single-name RS** (`/dash/rrg?sym=`, `/dash/rsband?sym=`) is reached from the **Stock dossier RS tab** (fixes the dead-end) AND from any constituent row.

---

## 5. Index / Sector drill-down (Ramana's explicit ask)

**`/dash/index?idx=X` is the canonical index page** — `/dash/ratio` **STAYS** (sacred, §0.3) as the full RS-ratio sub-page the index links to; it is NOT retired. Pattern = researcher's *aggregate strip → constituent table with a vs-sector/vs-broad TOGGLE (§0.7, not 3 eager doors) → frozen-pane constituents*, breadcrumbs throughout (`Markets → Sector → Stock`).

The page, top to bottom:
1. **Aggregate strip** — constituent count, breadth, median RS rank / MEP / phase, performance bands, the index composite verdict (MARKET LEADER / DEFENSIVE WINNER / AVOID…).
2. **Own-price chart** (bounded + fullscreen, §6) + **RS-ratio chart vs benchmark** (50/200-MA, cross markers, new-high dots) — the single canonical copy.
3. **The 3 RS-component doors** (the "graph of the three relative-strength components" → drill each):
   - **① Sector vs broad** — this index's own RS (ratio chart + its RRG quadrant + capture). Click → the Momentum lens focused on this index.
   - **② Stocks vs this sector** — click → constituents **ranked by RS-vs-sector** (RRG/band scoped here).
   - **③ Stocks vs broad** — click → constituents **ranked by RS-vs-broad**.
   - One unified `vs` model; each door → a ranked, frozen-pane constituent table; each row → the stock dossier.
4. **Constituent roll-up table** (frozen-pane, column-priority responsive) — every member, sortable, linking down.

So: **click index → its charts/graphs → pick an RS component → ranked constituents → name.** Insights live at the index; drill-down is direct.

---

## 6. Chart system (fix: too-wide / no-fullscreen / page-stretch)

Per the research (TradingView/Lightweight-Charts/StockCharts ACP):
- **Bound every chart**: a host `div` with **explicit height** `clamp(360px, 60vh, 640px)`, `width:100%`, `overflow:hidden`, **and a readable `max-width` (~1100–1200px)** even inside `.wrap.wide` so a single chart never spans 1900px. Size the canvas from the *container* (`clientWidth/clientHeight` via the existing `ResizeObserver`), never from the data — this kills the page-stretch outright (the classic LWC overflow bug is sizing from data, not container).
- **Fullscreen/expand**: a top-right ⤢ button on every chart and the RRG/band SVGs → CSS `position:fixed; inset:0; z-index:50` overlay + a `Shift+F`-style hotkey. Pure client-side, no route change.
- **Multi-pane**: price + volume + one oscillator (RSI/DVPT) stacked, **one synchronized x-axis**, draggable dividers, ~30px min pane height, default **≤3 panes** (price `flex:3`, sub-panes `flex:1` ≈ 80–120px).
- **Tap-to-pin tooltips** on the hover-only SVGs (RRG, lanes, markets rotation) so their numbers survive on touch.
- Preserve all overlay/compare controls (§8 H) — they just live inside the bounded host.

---

## 7. News system (fix: buried, unused)

Research lesson: *news is used when scoped + de-noised + co-located; ignored as a standalone firehose.*
- **Per-stock "Timeline" tab** on the dossier — newest-first **typed** events: Results (with your QoQ/YoY deltas) · Board Meeting · Reg-30/LODR · Insider/PIT · Trading-window · Corporate Action · Credit Rating · Concall-Guidance — each row → source PDF, each results row led by a **pre-computed one-line summary** (no LLM, per cost doctrine).
- **Typed announcement stream** keyed to Indian filing reality, scoped by watchlist, with **subtractive mute** for routine notices.
- **Market Wire rail** on Markets (and a thin strip on the cockpit) — move the market-wide card **above** the index bundle; add a static **"Moving now"** strip of watchlist movers as click-through chips (not a marquee).
- **Data gap to close:** `sent_news` needs per-symbol/per-sector tagging for scoping (a backend task — note, don't block the IA).

---

## 8. The no-loss census — every RS metric → its new home

*(The preservation guarantee. Source: the RS-ecosystem census. Every item keeps a first-class home.)*

| Metric / feature | New home |
|---|---|
| RS-Ratio, RS-Momentum, quadrant, **tails 3/6/12/24m**, Play | RS ▸ **Momentum** (+ index door ①, + stock RS tab) |
| RSI-of-RS, Mansfield RS, up/down-capture (63d+252d), down-excess Δ% | RS ▸ Momentum table (+ index RS-depth, + stock RS tab) |
| rs_band_pct (0–100), POC magnet, regime, trend-R², band-state, **to-support%/to-resistance%**, verdict (Accumulate…Fade) | RS ▸ **Level** (Lanes/Clock/Channel view-switcher) (+ index door, + stock RS tab) |
| rs_rank (1–99) | RS ▸ Leaders + Sectors; Screener "RS#"; stock verdict strip; conviction |
| RS-momentum composite + **percentile bar** | RS ▸ **Sectors** (merged table) + index gauge |
| 3 RS layers (broad/sector/sector-vs-broad) trend-states | RS ▸ **Leaders** (the joint table) + index doors ②③ + stock RS tab |
| RS heat strip 1m/3m/6m/12m/**18m/24m** | RS ▸ Sectors; Screener "Heat"; stock RS tab; index page |
| trend-states BREAKOUT…BREAKDOWN | everywhere RS is shown (pills) |
| weather (Tailwind/Recovery/Rolling-over/Headwind) + **just-turned movers** + leverage marks | RS ▸ **Phase** (+ Sectors weather badge + Markets cards) |
| RRG flag pills (base-turn, rolling-over, RSI-turn, bull/bear div, MRS±) | RS ▸ Momentum |
| Composite verdicts (abs-trend, rel-trend, index verdict) | Markets cards + **Index page** aggregate strip |
| RS-ratio chart (50/200-MA, cross markers, new-high dots) | **Index page** (single canonical copy; `/dash/ratio` retires into it) |
| Stock-page RS overlay: add tickers/indices, rebase base100, range 1Y–Max, interval D/W/M/Q, sector-peer quick-pick, "open in Compare" | **Stock dossier ▸ RS tab** (unchanged controls, bounded chart) |
| `/dash/compare`: Rebased/Ratio mode, denominator 50/500, range, pin-anchor, presets, multi-add | **Markets ▸ Compare** (unchanged) |
| Benchmark toggles (vs Nifty 500 / vs Nifty 50) | Unified across ALL RS lenses (one model, default 500) |

**Merges/retires (no deletion — redirects + folds):** `/dash/sectors` + `/dash/rs` → RS▸Sectors (one sortable table); `/dash/ratio` → Index page (redirect); `/dash/leaders` → RS▸Leaders; `/dash/rrg`,`/dash/rotation`,`/dash/rsband` → RS▸Momentum/Phase/Level (their routes can stay as deep-links). `/dash/scan` → Strategies▸Positioning (redirect). Stock dossier's 3 RS `<h2>` blocks → one RS tab.

---

## 9. The rules system (future-proof — components self-place)

**TO-BE-BUILT (§0.4 — only `STRATEGY_REGISTRY` exists today; nav/sub-nav/dossier-tabs/screener-groups are hand-maintained in 4 places).** Target: generalize `STRATEGY_REGISTRY` into **per-workspace registries**, each entry = `{key, label, accent, href, lens/builder, count_fn, thesis, columns?}`:
- `STRATEGY_REGISTRY` — a new *settled* stock-selection lens (e.g. Ignition) → auto tile on home + board + Strategies deep-dive section + screener column group + dossier tab.
- `RS_LENS_REGISTRY` — a new RS sub-lens → auto RS sub-nav tab + overview preview.
- `MARKET_VIEW_REGISTRY` — a new macro view → auto Markets entry.
- `SCREENER_COLUMN_GROUPS` (exists) — a new metric family → auto column group + toggle.
- `DOSSIER_TAB_REGISTRY` — a new per-stock analysis → auto dossier tab.
- **`OVERLAY_REGISTRY` — a new chart overlay (e.g. Wolfe) → injects ONLY a toggle into the stock/index chart toolbar. No nav, no screener, no strategy.** This is where unsettled/experimental/chart-only signals live until (if ever) they earn promotion to a `STRATEGY_REGISTRY` lens.

A new component is registered once; nav, home tiles, screener columns, and dossier tabs update automatically. **No more bolting onto the dashboard** — the registry IS the "better parking place."

---

## 10. Responsive strategy (experience, not enumeration)
- **Priority+ top-nav** — show what fits, overflow the rest behind a visible **"More"** (not a hamburger).
- **Column-priority tables** — tag each screener/constituent column with a priority; narrow keeps Symbol + headline verdicts (RS-band%, MEP/phase, %chg), the rest behind horizontal scroll (frozen-pane) on desktop, **collapse-to-card** (tap to expand) on mobile.
- **Two disclosure levels max** (NN/g): workspace → page; deeper → tabs within page. Mobile = verdict + 2–3 headline numbers; desktop = the full grid.

---

## 11. Build phasing (for when code resumes — currently DESIGN-ONLY + web layer is parallel-owned)
- **P0 — the RS section shell (under Strategies):** add `RS_LENS_REGISTRY` + the RS deep-dive section reached via Strategies ▸ Relative Strength, with sub-nav (Leaders/Sectors/Momentum/Level/Phase), each pointing at the EXISTING route initially (pure re-grouping; zero logic change). Consolidate `/dash/leaders` + `/dash/rrg` + `/dash/rotation` + `/dash/rsband` under it. Unify the benchmark toggle. (No new top-level tab — §3.)
- **P1 — merges:** Sectors+RS → one table; `/dash/ratio` → Index redirect; relabel Rotation lenses honestly.
- **P2 — index drill-down:** the 3-component doors + breadcrumbs + constituent tables on `/dash/index`.
- **P3 — chart system:** bounded hosts + width cap + fullscreen + tap-tooltips + multi-pane.
- **P4 — news:** stock Timeline tab + Market Wire rail + (backend) sent_news tagging.
- **P5 — dossier tabs + responsive:** sticky dossier tab bar + News tab + Priority+ nav + column-priority tables.
- **Cross-cutting:** the glossary `?` hook; the rules registries.
- **Coordinate with the parallel (Wolfe) session** — the entire web layer is theirs right now; this is design until it frees.

---

## 12. Sources (design research)
StockCharts RRG (help + ChartSchool), Optuma RRG, TradingView "RRG India", Mansfield RS — RS/RRG section structure & drill-by-tail. TradingView widget sizing + maximize/`Shift+F`, Lightweight-Charts autoSize + panes, StockCharts ACP panels — chart bounding/fullscreen/multi-pane. Koyfin Watchlist News, Tijori Timeline, Trendlyne typed announcements, Bloomberg Launchpad/News-Trends — scoped news. TradingView heatmap drill, Trendlyne industry page, Koyfin exposures — index→constituent drill. Koyfin left-nav + "My Koyfin", Bloomberg command line, NN/g progressive disclosure — IA. Brad Frost Priority+, LogRocket/DataTables column-priority — responsive. (Full URL list captured in the research agent output for this session.)

---

## 13. P0 build status (2026-06-23) — the RS hub module is BUILT + verified

**Shipped as an isolated new module (zero contended-file edits, per §0.8):** `src/web/rs_section.py` — the Markets-altitude **Relative Strength hub** at `GET /dash/rs-hub` (`active="markets"`).
- **Registry-driven** (`_LENSES`, the §9 scaffolding scoped to RS): 5 lenses — Leaders · Sectors · Momentum · Level · Phase — each a card linking to its EXISTING route (`/dash/leaders`, `/dash/sectors`, `/dash/rrg`, `/dash/rsband`, `/dash/rotation`). A future RS lens = one row → auto card.
- **Perf guardrail honored (§0.7):** previews read ONLY precomputed tables (`leaders_laggards`, `rrg.latest_all`, `rsband.latest_all`, `phase_movers`) — verified **36ms** (vs Nifty 500) / **11ms** (vs Nifty 50); zero on-read recompute. Each preview is wrapped defensively → a shifting upstream signature degrades to "open →", never crashes the hub.
- **Self-contained chrome:** only imports the stable `_shell`/`_esc`/`_q`; own scoped `rsh-` CSS; no coupling to cockpit internals. Unified benchmark toggle (vs Nifty 500 / vs Nifty 50) baked in.
- **Verified standalone:** mounted on a throwaway app → `/dash/rs-hub` 200, all 5 cards + links + toggle present; `dashboard.py` confirmed untouched (48 routes).

**The ONLY remaining P0 step — the deferred thin hook (apply when the parallel session frees `main.py`):**
```python
# src/main.py — append next to the other include_router lines
from src.web.rs_section import router as rs_section_router
app.include_router(rs_section_router)
```
Until that one line lands, the module is inert and harmless.

**Also BUILT + verified (isolated new module):** `src/web/glossary.py` — the cross-cutting **`?` hover-help** (design item C1). Parses `docs/metrics-glossary.md` into a term index (**95 lookup keys** — by name, short-name, and source column) and exposes `gloss(term, label=None)` (a pure-CSS `:hover`/`:focus` popover, content baked at render — zero fetch, zero JS) + `css()`. **Zero `src` imports** (no circular-import risk; any view can call it). Defensive: an unknown term degrades to the plain label; HTML-escaped. Verified: DVPT/rs_rank/RS rank/p_score/×Power/Conviction/Width%/ns_base/Character/Tier/Key price/Surge 1m all resolve; fallback + escaping pass. **Wiring it onto group-headers/pills is a later contended-file edit (deferred)** — until then, inert.

**P1 (deferred, coordinate with the Wolfe session — small `dashboard.py` edits, held until the file frees):** add an "RS" entry to `_SUBNAV["markets"]` pointing at `/dash/rs-hub`; move `leaders` out of `_SUBNAV["strategies"]`; unify the `?vs=`/`?den=` default (rrg vs rsband currently flip — §2(i)); reconcile/remove the Wolfe Strategies-nav entry (Wolfe = overlay-only, §3-C).

---

## 14. SESSION TAKEOVER — state · remaining work · exact edits · resume (2026-06-24)

> **Read this section to continue the work.** Design is complete (v3, stress-tested, §0); P0 is started as isolated modules; everything below is **wiring-gated on the parallel Wolfe session**, not on more design. Nothing is lost — it's all here.

### 14.1 Tree state at hand-off
- **Mine, safe (untracked `??`):** `docs/ui-architecture-v2.md` (THIS doc — canonical), `docs/ui-redesign-2026-06.md` (additive Phase-0/1 plan + build log), `docs/ui-redesign-EXECUTE.md` (older run-book), `src/web/rs_section.py` (built+verified), `src/web/glossary.py` (built+verified), `src/automation/news_tagging.py` (built+verified 2026-06-24 — the P4 backend dep; see §14.8).
- **Mine, COMINGLED (in a parallel-owned file):** my Phase-0/1 edits live inside `src/web/dashboard.py` (which is ` M`, also holding the Wolfe session's changes — combined diff ~+126/−50; my portion = the sub-nav + Batch A + reopen + notes, fully logged in `ui-redesign-2026-06.md` §10). Stale protective patch: `C:/Users/gotti/.claude/projects/D--Hermes/ui-redesign-phase01-dashboard.patch`. **If my work is ever lost, reconstruct from the §10 build log — every edit is recorded.**
- **PARALLEL-OWNED — DO NOT EDIT while dirty:** `src/web/dashboard.py`, `src/web/cockpit.py`, `src/web/rrg_view.py`, `src/main.py`, `src/automation/rsband.py`, `src/automation/index_signals.py`, `PROJECT_STATE.md`, plus the Wolfe session's new files (`wolfe_view.py`, `wolfe_overlay.py`, `wolfe.py`, `mini_rrg.py`, …).

### 14.2 Done this session
- **Design:** full 35-screen audit → v3 architecture → adversarial stress-test → §0 corrections.
- **P0 modules (isolated, built + verified, INERT until wired):** `rs_section.py` (`/dash/rs-hub`, 36ms, registry-driven), `glossary.py` (`?` help, 95 keys).
- **Phase-0/1 (earlier, comingled in dashboard.py, was 28/28 green):** consistent sub-nav + `/dash/rsband` de-orphaned; Import de-orphan; Remove→origin; `?closed=1` banner; watch Target/Stop; scan `.dt`; closed-trade reopen; `notes` column.

### 14.3 Remaining work — ordered, with EXACT edits (match by string; line numbers drift)
**WIRING HOOKS (apply first when the files free):**
- **H1 — mount the RS hub.** In `src/main.py`, beside the other view-module includes (after `app.include_router(wolfe_router)`):
  ```python
  from src.web.rs_section import router as rs_section_router
  app.include_router(rs_section_router)
  ```
  Verify: `GET /dash/rs-hub` → 200.
- **H2 — wire the glossary `?`.** `from src.web import glossary as G`; inject `G.css()` ONCE per page (cleanest: append to `_BASE_CSS` or `_shell`); wrap metric labels, e.g. screener header `<th>RS#</th>` → `<th>{G.gloss("rs_rank","RS#")}</th>`. First high-value spots: screener group/column headers, the stock verdict-strip tiles, the MEP/CPR/CCI pills. Unknown terms degrade to the plain label — safe to wrap liberally.

**P1 — RS-under-Markets nav (`dashboard.py`, coordinate w/ Wolfe session):**
- In `_SUBNAV["markets"]` add `({"rs-hub"}, "/dash/rs-hub", "Relative strength")` (after "Sectors").
- In `_SUBNAV["strategies"]` REMOVE the `({"leaders", "laggards"}, "/dash/leaders", "Strength")` row (leaders moves to the Markets RS hub; the `/dash/leaders` route stays — the hub links it).
- Unify the benchmark default: `rrg_view.py` defaults `vs="sector"`, `rsband_view.py` defaults `vs="broad"` — pick one (recommend `broad`/Nifty 500) so the same toggle behaves identically.
- ~~Reconcile the Wolfe nav~~ **DECIDED (Ramana, 2026-06-24): KEEP the Wolfe view + nav as the parallel session shipped it.** The parallel session built `/dash/wolfe` as a *full view* (`wolfe_view.py`: "1-4 EPA target + WolfeRank") with a `"wolfe"` entry in `_WS` (dashboard.py:388) + `_SUBNAV["strategies"]` ("Wolfe", dashboard.py:436). The v2 spec §3-C says Wolfe should be overlay-only — but Ramana chose to keep the shipped view for now (also aligns with [[build-additive-never-replace]]); demoting to overlay is deferred/optional. **→ P1 must NOT remove the Wolfe nav entries.** Revisit only if Ramana later asks.

**P2 — lossless merges:** Sectors+RS → one sortable table (`render_sectors`+`render_rs`, cockpit); index drill = a vs-sector/vs-broad TOGGLE on the already-inline constituent table (NOT 3 eager doors, §0.7). `/dash/ratio` STAYS (sacred).
**P3 — charts (§6):** bound every chart host (`height:clamp(360px,60vh,640px); max-width~1100px; overflow:hidden`), add a `⤢` fullscreen toggle (CSS `position:fixed;inset:0` + `Shift+F`; never re-instantiate the chart — CSS toggle only, §perf), tap-to-pin tooltips on the RRG/lane/markets SVGs.
**P4 — news (§7):** per-stock **Timeline tab** (typed events) + a Markets **Wire** rail; **backend dep = tag `sent_news` per-symbol/sector** (it's market-wide only today) — a data-layer task that can proceed independently. ✅ **BACKEND DEP BUILT (2026-06-24): `src/automation/news_tagging.py`** — rule-based gazetteer matcher (no LLM, cost-doctrine) over `nse_equity_list`; owns its `news_symbol_tags` table; `backfill()` + `news_for_symbol()`/`wire_for_symbols()` read-APIs ready for the Timeline/Wire UI. Verified against 676 real headlines (precision-first; see §14.8). Remaining for P4 = the UI tabs (gate-closed) + the prod backfill run (deploy-gated) + the optional forward-path hook in `news_feed.py` (documented in the module footer).
**P5 — dossier + responsive:** ADD a News tab to the EXISTING dossier tab bar (do NOT rebuild it — §0.6); Priority+ nav overflow; column-priority tables (frozen-pane desktop / collapse-to-card mobile, keep row-height constant so the screener virtualizer's spacer math holds — §perf).
**No-loss census widening (§0.5) — assign homes:** `/dash/participants` (orphan → a Markets entry); `/dash/workbench` (→ Strategies; home for the ~30 non-RS `stock_signals` long-tail columns); `/candidates` (keep as-is or re-home to Pat); `/dash/scan` (keep deep-link unless `/dash/stocks` provably reproduces its layered sort + Near-P); Tracker import/export family.
- **`/dash/testing` (strategy-research session's backtest Lab + strategy registry; `testing_view.py`, isolated, already mounted live)** → **Strategies ▸ "Lab"** (sub-nav, NOT a top tab — research/validation is Strategies content; sits beside Workbench). Mechanics decided 2026-06-26: `_WS["testing"]="strategies"` + `({"testing"},"/dash/testing","Lab")` in `_SUBNAV["strategies"]`; keep `active="testing"`. No route clash. On-theme with the trust-first mandate (honest "nothing beats buy-hold net of cost" verdict = no-fake-alpha). The 2 nav lines wait on `dashboard.py` freeing (parallel-owned).

### 14.4 Verification harness (every change must keep this green)
```python
# run with the hermes-agent venv python (has the app deps); local data/hermes.db
from fastapi import FastAPI; from fastapi.testclient import TestClient
import importlib, src.web.dashboard as d
app=FastAPI(); app.include_router(d.router)
for m in ("src.web.rrg_view","src.web.rotation_view","src.web.rsband_view","src.web.rs_section"):
    try: app.include_router(importlib.import_module(m).router)
    except Exception as e: print("skip",m,e)
c=TestClient(app)
# 28-route smoke baseline + any new asserts; inject-test-row→assert→DELETE for data-dependent pages.
```

### 14.5 Pending doc updates (when the tree frees)
- **`PROJECT_STATE.md` session-log entry is DEFERRED** (the file is parallel-owned now — co-editing would clobber the Wolfe session). Add this when free: *"Session — UI Architecture v2: full 35-screen audit + stress-tested v3 schema (RS = Markets-altitude content, not a tab/strategy; altitudes·lenses·overlays·syntheses·attribute-families·content taxonomy); P0 started — `rs_section.py` (RS hub) + `glossary.py` (`?` help) built+verified isolated, wiring deferred; spec `docs/ui-architecture-v2.md`."*
- After H1/H2/P1 land → tick them in §13.

### 14.6 RESUME — first action when the web layer frees
1. Confirm `git status` shows `dashboard.py`/`cockpit.py`/`main.py` clean (Wolfe session committed).
2. Apply **H1** (1 line, `main.py`) → verify `/dash/rs-hub` 200 in the live app.
3. Apply **P1** nav edits → run the §14.4 harness (must stay green) → then H2 (glossary) on a couple of high-value headers → verify.
4. Land the deferred `PROJECT_STATE.md` entry (§14.5) in the SAME commit; branch first (don't commit straight to `main`).
5. Proceed P2 → P5 per §11, verifying after each.

### 14.7 Kickstart self-prompt (paste to start the takeover session)

> You are taking over the **patearn UI Architecture v2** redesign (dense Indian-equity analyst dashboard; FastAPI server-rendered HTML; dark "instrument" theme). Design is **complete + adversarially stress-tested**, **P0 is started**, and the remaining work is **wiring-gated on a parallel session — not on more design.** Resume safely and finish the build when the tree frees: autonomously, verified, losing nothing.
>
> **BOOT FIRST (before touching anything):** (1) read `docs/ui-architecture-v2.md` in full — §0 (binding corrections), §13 (build status), §14 (this guide); (2) read memory `ui-redesign-templates`, `build-additive-never-replace`, `data-first-light-ui`, `autonomous-blanket-access-multisession`, `work-plan-two-lanes`; (3) run `git status --short` + `git log --oneline -15` and establish who owns the web layer now.
>
> **CARDINAL GUARDRAILS (never violate):** nothing lost or rendered dead, additive only; sacred routes (`/dash/ratio`,`/dash/rrg`,`/dash/compare`) keep URLs; build new work in **new modules + a thin hook**, **never co-edit a parallel-owned/dirty file** (re-check `git status` before every edit); **verify every change** with the §14.4 harness (28-route baseline green; inject→assert→cleanup for data pages); hubs/landings/columns read **precomputed tables only**, never on-read recompute; RS = **Markets-altitude content** (not a tab/strategy), **Wolfe = a chart overlay only**.
>
> **STATE/GATE:** the web layer (`dashboard.py`,`cockpit.py`,`rrg_view.py`,`main.py`,`PROJECT_STATE.md`) is owned by the parallel **Wolfe** session → wiring-gated. Built + verified, isolated, inert-until-wired: `src/web/rs_section.py` (RS hub `/dash/rs-hub`) + `src/web/glossary.py` (`?` help). Phase-0/1 is comingled in `dashboard.py` (logged in `docs/ui-redesign-2026-06.md` §10; reconstructable).
>
> **FIRST ACTIONS:** if `dashboard.py`/`cockpit.py`/`main.py` are **CLEAN** → execute §14.6 (H1 main.py include → verify `/dash/rs-hub` 200; P1 nav edits, **coordinate the Wolfe nav entry, don't clobber**; H2 glossary on a few headers; harness green after each; land the deferred PROJECT_STATE entry §14.5 in the same commit; **branch first**). If still **DIRTY** → don't touch them; continue isolated work or stand by, re-checking.
>
> **HOW TO RUN:** autonomous + agent-driven (don't pester the user; convene panels/red-teams for decisions and to **stress-test your own conclusions before committing** — be ruthlessly self-critical); grounded (verify real data/code; query the VPS via `ssh hermes` for live-data questions; never speculate); decisive but safe (forward motion, sensible defaults; HALT only at a tripwire); honest + documented (keep §13/§14 + memory current; no new docs — fold in).
>
> **STOP-AND-ASK tripwires (else proceed):** (1) a needed edit is in a parallel-owned file that hasn't freed; (2) a change would reroute a sacred route or risk no-loss; (3) an irreversible/outward-facing action (commit to `main`, push, deploy, delete).
>
> **REMAINING:** §14.3 — hooks → P1 → P2 (sectors+rs merge; index-drill toggle) → P3 (charts bounded+fullscreen+tap-tooltip) → P4 (news timeline + `sent_news` per-symbol tagging) → P5 (dossier News tab + responsive) → census homes (participants/workbench/candidates/scan). **Known data-integrity item:** stock chart truncates on ticker renames (GMRINFRA→GMRAIRPORT) — wire `src/automation/security_master.py` symbol-continuity into the chart's bhavcopy fetch.
>
> **Goal:** finish exactly per `ui-architecture-v2.md` — RS unified at the Markets altitude, charts bounded+fullscreen, news surfaced, drill-downs working, rules registries built — losing not one metric, regressing not one route, never colliding with the parallel session.

---

## 14.8 Session 2026-06-24 — re-verify · recon · P4 backend built (gate still closed)

Took over per §14.7; the web layer was **still parallel-owned/dirty** (`dashboard.py`, `cockpit.py`, `main.py`, `rrg_view.py`, `rsband.py`, `index_signals.py`, `PROJECT_STATE.md` all ` M`) → **gate CLOSED**, so the wiring branch (H1/P1) did not run. Did safe isolated work + read-only recon instead. **Touched zero contended files.**

**Re-verified the P0 modules are intact + green** (§14.4 harness, local hermes-agent venv): `glossary.py` 95 keys, all 11 documented terms resolve, escaping/fallback/css pass; `dashboard`+`rrg_view`+`rotation_view`+`rsband_view`+`rs_section` all mount; `/dash/rs-hub` 200 with all 5 cards + bench toggle + links (and `?den=Nifty 50` 200). 44 genuine 200s; the 12 non-200 are expected POST-only (405) / param-required (422) routes hit with a bare GET.

**Recon (read-only) — verified against current drifted code, so P1 is mechanical when the gate frees:**
- **H1 slot** = `src/main.py:49`, right after `app.include_router(wolfe_router)`.
- **`_SUBNAV["markets"]`** = dashboard.py:417 (add RS-hub after "Sectors" @419); **`_SUBNAV["strategies"]`** leaders row = dashboard.py:431.
- **`vs=` defaults confirmed flipped**: `rrg_view.py:735` defaults `"sector"`; `rsband_view.py` defaults `"broad"` → unify to `broad`/Nifty 500.
- **`/dash/participants` is no longer an orphan** — it's now a mounted module (`participants_view.py`, main.py:17/46). The §0.5 census item shrinks to "give it a Markets *nav* entry," not "de-orphan a route."
- **Wolfe**: shipped as a *full view* + nav entries → **DECIDED: keep** (see the P1 bullet above; P1 must not remove it).

**Built + verified (isolated, inert-until-consumed): `src/automation/news_tagging.py`** — the P4 backend dep (per-symbol tagging of `sent_news`, which is market-wide-only). Rule-based gazetteer (NO LLM, per the cost doctrine) over `nse_equity_list`; precision-first (generic tokens like Power/Oil/Bank never match alone; acronym tickers match only as standalone ALL-CAPS tokens; span-containment suppression drops nested over-tags). Owns its `news_symbol_tags` table (no db.py edit). APIs: `backfill()`, `news_for_symbol()`, `wire_for_symbols()`, `stats()`, `tag_url()` (forward path).
  - **Verified against 676 REAL headlines + the 2,372-symbol registry (pulled read-only from VPS):** 37% tagged (251/676) — honest precision-first (most untagged are genuinely macro: Sensex/FII/gold/Fed, or brand≠legal gaps Nykaa/RIL/Jio by design). **Audited every match: ZERO generic-word false positives; every acronym match a real ticker.** Top symbols = TCS/VEDL/INFY/WIPRO/COALINDIA… (all real large-caps). DB plumbing proven via inject→assert→cleanup on the local DB (schema, idempotent backfill, read-APIs), local DB left as found.
  - **Known recall gap (documented):** brand≠legal names need an alias map (future); the forward-path hook (persist news_feed.py's already-computed classifier `tickers`) recovers many — left unwired (additive edit to a non-contended file), documented in the module footer.
  - **Shipped 2026-06-24** (see "COMPLETED + LIVE" below): deployed + prod backfill run (359 tags) + forward hook live + committed `f19ca29`. **Remaining for P4 = the UI only** (dossier Timeline tab + Markets Wire rail — gate-closed; read-APIs ready).

**COMPLETED + LIVE (Ramana: "dont hold. complete." 2026-06-24):** the news backend lane is shipped to prod:
- **Deployed** `news_tagging.py` (new) + `news_feed.py` (hook) to the VPS via LF-normalized stream (per [[vps-deploy-reality]]); CRLF-aware diff-check first confirmed VPS `news_feed.py` == my base (overwrite reverted nothing); both verified byte-identical post-copy.
- **Backfill run on prod:** 696 headlines scanned → **254 tagged, 359 tags** (name 302 / symbol 57); top symbols VEDL/TCS/INFY/WIPRO/COALINDIA — matches local verification.
- **Forward hook verified live on VPS** (real env, feedparser present): `news_feed` imports clean, persists classifier tickers (method=classifier, conf .95). Live on the `hermes-news.timer` scheduled path automatically (fresh process per run) AND on the on-demand `/news` path after a clean **hermes-telegram restart** (came back `active`, no import errors).
- **Committed to main** (local): `f19ca29` (v1) then `60bfb86` (review fixes); explicit paths only, index clean each time → no cross-absorption; all contended files still ` M` = parallel work untouched. **NOT pushed** (outward step left for explicit go; already live on prod via scp).
- **Adversarial re-review (2026-06-24, two independent reviewers + my pass) → 2 real bugs found & fixed (`60bfb86`, redeployed + bot restarted + re-verified live):**
  1. *Coverage gap* — the forward hook persisted ONLY classifier tickers; the rule-based matcher ran only in the one-time backfill (no scheduled caller), so new headlines the classifier files as OTHER (tickers=[]) but which name a listed company were missed going forward. Fix: `news_feed._persist_news_tags` now runs `match_title` on every sent headline AND the classifier tickers.
  2. *Orphan tags* — the hook ran before `mark_sent` / independent of send success → failed sends wrote tags for URLs never in `sent_news` (and `stats()` overcounted). Fix: tagging now runs AFTER `mark_sent` on both return paths.
  Plus: `ensure_schema` once + direct inserts in the hook; dropped dead/risky `_LEGAL_SUFFIX` entries. **Matcher precision findings (IDEA/JUSTDIAL/TRENT-class) reviewed and DECLINED** — zero FPs across 696 real headlines; a corroboration guard would regress real recall (e.g. "IRCTC: …"). Recall gaps (M&M/L&T short-forms, "Company"/"Corporation" suffix) noted as future, precision-safe.

**Still deferred (gated, not "held"):** the news **UI** (dossier News/Timeline tab + Markets Wire rail) needs edits to the parallel-owned `dashboard.py`/`cockpit.py` → blocked until the tree frees; the read-APIs (`news_for_symbol`/`wire_for_symbols`) are ready for it. Also gated: H1/H2/P1 wiring; the `PROJECT_STATE.md` entry (§14.5 — should also mention `news_tagging.py` shipped + `f19ca29`).

### 14.9 Session 2026-06-24 (cont.) — news VIEW layer built (UI session, gate still closed)

Ramana opened a **UI session** (rule: additive only, never delete/tamper functionality). Gate re-checked: **still closed** — the parallel session is now mid **chart overhaul** (`.bak-stockchart` files, recent `fix(charts)` + "one-chart stock engine" commits), so charts + dossier + nav are all off-limits. News remains my clear lane.

**Built + verified + committed `7f5041c` (isolated, inert-until-wired): `src/web/news_view.py`** — the P4 §7 view layer consuming the `news_tagging` read-APIs:
- Reusable fragments `render_stock_timeline(sym, conn)` (per-stock News/Timeline) + `render_market_wire(conn[, symbols])` (watchlist-scoped Wire) — so the dossier grows a News tab and Markets a Wire rail with a **one-line embed** when the tree frees. Plus standalone routes `/dash/news?sym=` + `/dash/wire` (wire = a single `include_router` in main.py, deferred). Data-first (date · source · headline link + honest rule/ai provenance marker); dark instrument theme (`nv-` scoped CSS); imports only the stable `_shell/_esc/_q` (import-safe).
- **Additive only**: adds new routes, touches no existing route, deletes nothing, changes no functionality. Verified: mounts clean, routes 200 (empty + populated), renders injected sample data (stock timeline + wire with symbol chips), **46-route baseline green (44 prior + 2 new, no regression)**. A `get_conn` context-manager misuse in the Wire path was caught by the test and fixed before commit.
- Shown to Ramana as an inline rendered mockup (real component HTML + sample data).
- **Remaining to wire (gated):** `main.py` include for the two routes; embed `render_stock_timeline` as a dossier News tab + `render_market_wire` as a Markets rail (both in parallel-owned files).

**Wiring queue when the web layer frees (all blocked on the same gate):** H1 (rs-hub include) → P1 (RS nav + leaders move + vs unify, keep Wolfe) → H2 (glossary) → news_view include + dossier/Markets embeds. Three isolated modules now ready: `rs_section.py`, `glossary.py`, `news_view.py`.
