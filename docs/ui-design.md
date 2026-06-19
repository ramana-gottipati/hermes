# Patearn — UI / UX design & doctrine

> **Status:** design in progress (session 20, 2026-06-19). Captures Ramana's UI direction + the system-growth roadmap. **Design-first: present, then build on sign-off.** No code rewrite has happened yet.
> **Hard guardrail:** **NO REGRESSION.** Every existing page, the Telegram bot, the chat, the charts — all preserved. The revamp *improves*; it never deletes working behaviour. (Ramana, explicit: "Chat should not kill whatever work we've done… it should only be improved.")
> **Canonical decision number at build:** **D54** (UI revamp). D52 = held MTF engine · D53 = CPR strategy.
> **Companion:** Doctrine § C (data layer), D38 (the macro→micro dashboard this builds on), D40-A (the 5-item nav cap — this revamp deliberately revisits it, see § 3).

---

## 1. Why this revamp (the intent)

Ramana is a financial analyst. The dashboard today leans on **verdicts** — pills, badges, ranks, character labels. Those are useful, but a verdict is a *lens*, not the evidence. Ramana wants the **evidence visible**: the raw values behind every verdict, so he can form his *own* perspective instead of only consuming what the system concluded. "We get nothing by burying the data." This is **not CPR-specific** — it applies to every strategy surface (DVPT, RS, CPR, Quality) and to anything built from here on.

At the same time the system is **growing** — more strategies, portfolios per strategy, combination portfolios, a performance tracker, benchmark/gap analysis. The UI must be an information architecture that scales to that, while staying **light** (we're playing with a lot of data) and keeping the **refined, classy** look it already has.

---

## 2. UI DOCTRINE (binding — applies to ALL screens, present and future)

- **D-UI-1 — Data-first. Never bury the data.** Every strategy/screen shows the **raw numeric columns alongside** the verdict/pill. The verdict is an added column, never a replacement for the values. If a screen currently shows only a badge, it gets the underlying numbers too. *(Ramana: "I don't want to just consider whatever is shown by the system… I need the data handy.")*
- **D-UI-2 — The wide screener is first-class.** A screener must comfortably hold **50–100+ columns** with **horizontal scroll**, a **frozen top header** *and* a **frozen left column** (the symbol/"participant" name stays put as you scroll right). Easy to navigate, easy to read values. This is the centrepiece, not an afterthought.
- **D-UI-3 — Lightness is a hard constraint.** Server-rendered HTML + vanilla JS (the current stack). **No SPA / no heavy framework.** It must *feel* light with lots of data. Performance budget in § 9.
- **D-UI-4 — No regression.** Preserve every existing page, the Telegram bot, the chat, the charts. Improve in place. A revamp that breaks today's working surface is a failure, not a revamp.
- **D-UI-5 — Refined & classy.** Keep the dark analyst theme (it already reads as refined). Elevate polish — spacing, alignment, typographic rhythm, restrained colour — don't redecorate.
- **D-UI-9 — Wordmark.** The brand is **`patearn`** — all lowercase, geometric sans (Sora shown; swappable). The **`e`** is differentiated by a **colour accent only** (same typeface/weight/baseline) — the *pattern→earn* hinge — and **doubles as the app icon** (lone `e` on a dark rounded square). Accent: **earn-green `#3fb950`** recommended (alts: signal-blue `#58a6ff`, warm-gold `#e3b341`); final pick pending. Never caps or title-case. Detail in memory `patearn-brand-and-dvpt-direction`.
- **D-UI-10 — Data workspaces are full-bleed.** The screener and other data/grid views use the **whole viewport width** (`.wrap.wide` → `max-width:100%`), and the grid **fills the width** (stretches when columns fit, scrolls only on true overflow). The 760px reading column is kept ONLY for prose/card pages (markets · sectors · stock detail) where line-length legibility matters. *Why:* a 21–100-column screener boxed into 760px wastes the screen and forces needless scrolling — a data app must own the page. (Shipped s20.)
- **D-UI-11 — Screener universe is PRINCIPLED & scoped, never a magic N.** Default = a real index (**Nifty 500** constituents); a **scope selector** switches broad index / sector / watchlist / all (all capped at 600 by conviction), with members-vs-shown counts shown. Ranked by a tri-pillar **Conviction** (positioning + relative strength) with a **★** triple-confirm flag. *Why:* an arbitrary top-250 has no basis; an analyst screens a *defined* universe and compares within an index. (Shipped s20.)
- **D-UI-12 — Frozen-pane grid = ONE scroll viewport (both axes), toolbar outside it.** An overflow container traps vertical `sticky`, so the grid lives in a `max-height` scroll box that owns both axes (sticky 2-row header + sticky first column + frozen-column shadow on h-scroll), and the filter/export toolbar is lifted *outside* the box so it stays put. Richness stays pure-CSS/server-side: heat-tinted cells, group dividers, tabular numerals, zebra — no libraries. (Shipped s20.)
- **D-UI-13 — Top workspace menu is the primary navigation.** **Markets · Screener · Strategies · Portfolios · Tracker** in the header on every page (sub-pages map onto a workspace via `_WS`; brand links Home). The **Strategies** workspace surfaces today's best names per strategy (preview chips → full screen); the **Screener** carries column-group toggles + saved views beside the scope selector; **Portfolios/Tracker** are honest stubs until built. *Why:* this is a multi-workspace analyst tool, not one screen — the menu must be visible everywhere and scale. (Shipped s20; replaced the 5-item bottom nav. Realizes §3's workspace-tiles intent.)

---

## 14. SESSION 1 — UI/UX redesign (kickstart plan)

> **A dedicated, agent-driven, interactive session.** Goal: design (then build) the **best UI for THIS environment** — a high-performance, data-dense, multi-strategy Indian-equity decision platform. Ramana does **not** want to dictate the design; the **agent panel proposes**, the session presents **multiple-choice decisions each with a recommended option + the why**, and converges **interactively** (UI is taste — keep asking). Then **section-by-section stencils** before building. **No-regression** — enrich the working dashboard, never discard good work.

### Scope (gathered session 20)
1. **Self-explaining metrics — hover-help / "?" explainers** on every custom term (DVPT · ×power · surge · conviction · tier · pt14…), content sourced from **`docs/metrics-glossary.md`**. A first-timer (and Ramana later) must hover/click and get *what is this · how computed · measured against what*, plus a "how was this scored" drill-down for composites.
2. **Action flow: strategy → watchlist → portfolio**, capturing a **reason/thesis** — move a stock from any strategy/screener row into a watchlist or a **portfolio under a strategy** ("my portfolio under this strategy, for this reason"). Real tracking (ties to the long-open `stocks_in_play`).
3. **News** — a slow-scrolling **today's-news ticker** in a side corner (placeholder "coming soon" OK first); a **per-stock news** view; affordable scraping (5-min cadence aspirational — cost/feasibility is a panel call).
4. **Comparison** — compare **stocks** and **indices** side-by-side / parallel; enrich the existing `/dash/compare` + RS-overlay, don't duplicate.
5. **Onboarding / first-run** — how a new user grasps the strategies + vocabulary.
6. **Under-utilized-data audit** — surface where our strong data is hidden (88-col `stock_signals` + indices + deliveries hold far more than we show).
7. **No redundancy / no clutter** per tab; data-together-when-wanted + easy querying.
8. **Style research** — survey comparable platforms (TradingView · Koyfin · Trendlyne · Tijori · Sensibull · Screener.in) for dense-fast-dark patterns; adopt what fits, cite what's borrowed.
9. **Performance is first-class** (we just killed a 3.3s route + a per-cell toggle — keep that discipline: server-render + vanilla JS, no SPA).

### Design panel (spawn in parallel; each returns a concise, *recommended* proposal w/ rationale)
**UI/UX designer** · **Information architect** · **Financial analyst (the user)** · **Data engineer** · **Design researcher (comparable-platform survey)**.

### Session flow (binding)
1. Spawn the panel → recommendations with rationale.
2. Present pivotal choices as **AskUserQuestion multiple-choice — each with a RECOMMENDED option (yours) + the agents' opinions surfaced** — so Ramana picks. Stay interactive.
3. On alignment, deliver **section-by-section stencils** (visualize widgets) → iterate to "this looks really good."
4. Only then build — **enriching existing pages, never discarding** — updating `metrics-glossary.md`, this doc, and `PROJECT_STATE.md` as you go.

---

## 3. Information architecture (the structure that scales)

**The reconciliation of "data vs strategy, kept separate" with "data always handy":** one shared wide data grid is the substrate; **a strategy is a *lens* over that grid** (a saved query + its verdict columns), not a different, data-stripped view. From any strategy you can **"Open in Screener"** to see the full column set for exactly those picks. So the sections feel separate, but the data is never more than one click away — and never buried.

**The flow Ramana described:** **Query → Results (raw grid) → Picks (system selections).** A query produces a result set (the wide grid); the system's strategy picks are a highlighted/filtered subset of it; tiles/buttons jump between them.

**Workspaces (navigation tiles on Home + a persistent compact switcher):**

| Tile | What it is | Status |
|---|---|---|
| **Markets** | macro: regime, indices, sectors | exists (D38) |
| **Screener / Data** | the wide grid — all stocks × all columns, query-driven, saved queries | **NEW central workspace** |
| **Strategies** | DVPT · RS · CPR · Quality · Conviction — each a lens (saved query + verdict cols) over the grid; "Open in Screener" everywhere | refactor of existing strategy pages (data-first retrofit) |
| **Portfolios** | per-strategy portfolios + combination portfolios | **NEW (growth, § 6)** |
| **Tracker** | D/W/M performance, vs benchmark, gap analysis | **NEW (growth, § 7)** |
| **Stock** | per-symbol deep page | exists |

**Nav decision:** D40-A capped the bottom nav at 5 for phone ergonomics. This revamp **revisits that** — workspaces are launched from a Home **tile grid** + a compact top/side switcher, so we can grow past 5 destinations without crowding the phone bottom bar. (Logged as D-UI-6 at build.)

---

## 4. The Screener (centrepiece) — detailed spec

The single most important deliverable. Built by **extending the existing `table.dt` grid + `_DT_JS` toolbar** (already does click-sort, text-filter, CSV-export, sticky header) — we *add* to it, we don't replace it.

- **Frozen panes** — `position: sticky` on `thead th` (have it) **+ a sticky left column** (`td:first-child`, `th:first-child`) with a higher z-index at the corner. Pure CSS — zero JS weight. This is the headline fix.
- **Column groups** — columns organized into labelled groups so 50–100 cols stay navigable:
  `Identity` (symbol, name, sector, index membership) · `Price/Action` (CMP, Δday, Δweek, 52w-pos) · `Positioning/DVPT` (r/p scores, rank, character, key price, gap, ×power, deliv₹) · `Relative Strength` (vs-broad, vs-sector, 1–99 rank, D/W/M heat) · `CPR` (D/W/M width%, pattern, rank, conviction, regime) · `Quality` (pt14 pillars/score) · `Delivery` (deliv%, turnover, ticket).
- **Group toggles / column chooser** — show/hide whole groups or individual columns (vanilla JS, state in URL/localStorage). Default view = a curated ~15-column set; expand to the full set on demand.
- **Sort / multi-filter / export** — extend `_DT_JS`: numeric range filters per column, multi-column sort, the existing Excel-CSV export (keep — Ramana exports). 
- **Saved queries** — name + restore a column-set + filter-set (the "keep putting that type of a query" ask). Stored server-side (SQLite) or URL-encoded.
- **Density & lightness** — compact rows, right-aligned numerics with tabular figures, subtle zebra, colour only to encode (green/red deltas), not to decorate. Values always rendered as numbers; pills sit *beside* them, never instead.

---

## 5. Strategy screens — data-first retrofit (D-UI-1 in practice)

Each existing strategy surface keeps its verdict **and gains the numbers behind it**, plus an "Open in Screener" jump:

- **DVPT** — show r_score/p_score, each baseline value + companion price, gap-to-next-P, deliv₹, ×power, ticket — not just the rank pill.
- **RS** — show the actual ratios + percentile + 1–99 rank + D/W/M values, not just leader/laggard.
- **CPR (D52)** — show C0/C1/C2 width%, leg steps, separation, depth, regime, the D·W·M strip + conviction breakdown — not just the ★ tier.
- **Quality (pt14)** — show the per-pattern pillar values, not just the composite.

---

## 6. Portfolios (✅ Phase 1 BUILT — session 22, D54)

- A **portfolio under each strategy** (the names that strategy currently holds/picks), and **combination portfolios** (e.g., CPR-reversal ∩ DVPT-accumulation ∩ RS-leader).
- Each portfolio = a tracked set of (symbol, entry date, entry context, thesis) with live mark-to-market. Reuses the long-open `stocks_in_play`/tracker idea (PROJECT_STATE open item C).

## 7. Tracker & benchmark/gap analysis (✅ Phase 1 BUILT — session 22, D54)

- **Performance tracker** by **day / week / month closure** — how is each portfolio (and the system overall) performing per period? "What exactly is missing?"
- **Benchmark comparison** — vs Nifty / a broad index / a narrow index — "where are we really missing out?" Gap analysis = where the system under- or over-performs the benchmark, by period and by strategy.
- This is the difference between "a tracker/dashboard" and Ramana's **complete tracking system**.

## 8. Delivery mechanism evolution (growth — record)

- **Telegram** is currently blocked in India (regulatory) and is, longer-term, **only an alert channel** — fine for pings, not for the growing analytical surface.
- Direction: the **web app (PWA) becomes the primary interface** (we already serve `/dash` as an installable PWA over HTTPS). Grow that into the full workbench; keep Telegram for alerts. Possibly a dedicated phone-friendly view.

## 9. BSE filings scraping (growth — background data, record)

- When a company **files results/returns to BSE**, scrape the filing after a notification (BSE announcements feed). The NSE/results-calendar coverage is incomplete; BSE filings fill the gap. Feeds the news/earnings → screening chain. Independent of the UI work.

---

## 10. Lightness / performance budget (how we honour D-UI-3 with 50–100 cols)

- **Server-render** the grid HTML (current approach). No client-side framework.
- **Frozen panes via CSS `sticky`** — no JS scroll-sync.
- **Default to a curated column set**; full set on demand — the DOM stays small until asked.
- If a result set is very large, **paginate / cap server-side** (and *log* the cap per Doctrine — no silent truncation).
- Consider lightweight **row virtualization** only if a real bottleneck appears — not pre-emptively (avoid over-engineering).
- Keep CSS in the single `_BASE_CSS` block; vanilla JS in `_DT_JS`. Ship nothing heavy.

**Perf hand-off (data/perf session, 2026-06-19) — folds into this section.** A parallel pass diagnosed the hiccup as the *delivery model* (a full, uncompressed, uncacheable doc per click), not size. Source of truth (transient): `docs/ui-perf-handoff.md`; full reasoning + backend backlog: `docs/perf-architecture.md`. **Already shipped (backend):** app-layer gzip (`GZipMiddleware`, `src/main.py`) — so the render-layer items below buy *caching + smaller DOM*, not compression. **Execution sequence (dependency-gated — do in order):**
1. *(zero-risk, no deps — rides Phase 1)* externalize `_BASE_CSS`+`_DT_JS` (+ chart/picker JS) to hashed static routes with `Cache-Control: immutable`; self-host lightweight-charts + add `Cache-Control` to `/icon.svg`·`/manifest`·`/sw.js`; **memoize `_latest_dates()`** per trading day.
2. **Virtualize the screener grid AS PART OF the frozen-pane/column-group build** (Phase 2) — never after (shipping the ~54k-cell grid then virtualizing = a visible regression window). Keep the frozen panes (D-UI-12).
3. Dedupe the chart bootstrap (×5), the type-ahead picker (authored ×2), `chart_css` (×3); then the module split — *before* Phase 2 stacks saved-queries/tiles on the 4.7k-line file.
4. Thin chart-data JSON endpoint (`/dash/api/stock/<sym>/series`) + lazy fetch — replaces the ~100–150 KB inline JSON on `/dash/stock`.
5. **BLOCKED — the only cross-session gate:** read precomputed `adj_close` (kills the ~3.5 s `/dash/stock`, closes B5) + switch the screener `ORDER BY conv` to a precomputed `conv` column. WAIT for the perf work-stream's "columns live" signal (D47 recompute); until then guard with `COALESCE` and do NOT delete the inline back-adjustment.

---

## 11. Phasing

1. **Phase 1 (build first, low-risk, high-value):** the **frozen left column** + **column groups/chooser** on `table.dt`, and the **Screener/Data workspace** that exposes the full column set. Pure additive CSS/JS — zero regression. Retrofit DVPT/RS/CPR/Quality screens to data-first.
2. **Phase 2:** Home **workspace tiles** + nav reorganization (D-UI-6); saved queries.
3. **Phase 3:** Portfolios (per-strategy + combination) on the `stocks_in_play` foundation.
4. **Phase 4:** Tracker + benchmark/gap analysis.
5. **Parallel/background:** BSE filings scraper; delivery-mechanism evolution.

---

## 12. Open questions for Ramana
- **OPEN-UI-1 — Default screener columns.** Which ~15 columns are the "always-on" default before expanding to the full set? (I'll propose a set from the most-used.)
- **OPEN-UI-2 — Nav model.** Home tile-launcher + compact top switcher (recommended), or keep the bottom bar and add an overflow menu?
- **OPEN-UI-3 — Saved queries scope.** Per-device (localStorage) or account-wide (SQLite, syncs across phone/desktop)?
- **OPEN-UI-4 — Phase-1 first cut.** Build the frozen-pane wide Screener as a brand-new `/dash/screener` page first (safest, zero risk to existing pages), then retrofit the strategy pages — agreed?

---

## 13. Decision log (UI) — canonical D54 at build → PROJECT_STATE
- **D-UI-1 … D-UI-5** — the doctrine in § 2 (data-first · wide frozen screener · lightness · no-regression · refined look).
- **D-UI-6 — Workspace tiles + nav reorg**, revisiting D40-A's 5-cap. *Why:* the system now has more destinations than a 5-item phone bar holds; tiles scale, and Ramana asked for tiles/buttons to navigate.
- **D-UI-7 — Strategy = a lens over one shared grid** (saved query + verdict columns), with "Open in Screener" everywhere. *Why:* reconciles "separate data & strategy sections" with "data always handy"; the data is never buried or duplicated.
- **D-UI-8 — Extend `table.dt`/`_DT_JS`, never replace.** *Why:* no-regression + lightness; the existing grid already does sort/filter/export/sticky-header.
- **D-UI-14 — The action loop = ONE `stocks_in_play` table keyed by `status`** (watch → open → closed), NOT separate watchlist/portfolio tables; capture **freezes an as-of-day snapshot**. *Why:* watchlist and portfolio are the same object at two lifecycle stages under a strategy; the snapshot is the only honest way to show "what it looked like when added" (the daily signals overwrite nightly). Panel: data-eng + analyst + IA converged.
- **D-UI-15 — News = per-stock factual FIRST + a STATIC typed strip, not an auto-scrolling marquee.** *Why:* three panelists flagged marquees as unreadable; the analyst wants filings/results/corp-actions over a headline crawler. ₹0 via the existing RSS feeds; 15-min cadence. (Build = Phase 3.)
- **D-UI-16 — Visual language = "the instrument."** Rows are *readouts*: inline static SVG/CSS micro-viz (DVPT-vs-power ladder, key-price band, 3-axis character glyph, RS sparkline) turn the buried 88-col data into scannable shapes; the verdict sits ON its evidence; monospaced tabular numerals; ink discipline (2 encoding accents, colour = information only). Lighter than a chart library (static, server-rendered). *Why:* a re-skin buries the data; the instrument surfaces it — D-UI-1 made literal. Approved by Ramana.
- **D-UI-17 — Nav: attach, don't grow the bar.** Keep ~5 top tabs; new destinations attach to an owner (Watchlists/Portfolios under Portfolios via an in-page sub-nav; Compare under Markets) or a global utility strip (news + `?` glossary + search, Phase 3). *Why:* the phone bar can't grow indefinitely; every datum gets one canonical home.

---

## 15. Session-1 outcomes — the design decisions (session 22, 2026-06-19)

A 5-agent panel (UI/UX · IA · analyst-as-user · data-eng · design-researcher) ran in parallel; proposals converged on most points, and the genuine splits went to Ramana as multiple-choice-with-recommendations. **His calls:**
1. **Build order → action-loop first.** The tracking loop (row → watchlist → portfolio + thesis → MTM + hit-rate) is the only item that changes what he *learns* over time; the rest is polish on a working workbench. Then: under-utilized data → hover-help → comparison → per-stock news → onboarding.
2. **Action flow → two-tier + frozen snapshot.** One `stocks_in_play` row; ★ Watchlist (lightweight) → promote to Portfolio-under-a-strategy capturing strategy (auto), a required thesis, entry date+price (auto), optional target/stop, and a **frozen snapshot** of that day's key numbers. (→ D-UI-14.)
3. **News → per-stock factual first + static typed strip** (no marquee). (→ D-UI-15.)
4. **Nav → attach, don't grow the bar.** (→ D-UI-17.)

**Adopted without a vote (panel consensus):** surface the computed-but-hidden data first (≈30 of 88 `stock_signals` cols never reach the UI — gap-to-key + 🎯, the 3 character sub-axes, surge 3m/1y, near-break, RS slopes; `hot_days_avg_price` + the RS `above_50/200ma`/`new_52w` flags are near-dead → surface or delete); hover-help = a CSS `?` popover, content baked from `metrics-glossary.md` at render (zero fetch), on group-headers + pills, with a "how it's scored" drill-down for composites; saved views → SQLite (cross-device); comparison → enrich `/dash/compare` (auto-rebase + transposed table), don't duplicate; onboarding = a dismissible one-line strip + the glossary page, no coachmark tour; polish = tabular numerals everywhere, tone heat-tints down, lighter pills. Researcher citations: Screener.in (`?` header tooltips), Koyfin (column chooser + summary-row footer + watchlist↔portfolio split), Trendlyne (thesis "My Notes"), Tijori (typed "Ideas" news streams over a firehose), TradingView (Compare auto price→%), Sensibull (density toggle).

**Stencils approved ("perfect"):** nav frame + global utility strip + static news strip · action-capture form · portfolio + tracker · **the dense "instrument" screener** (inline micro-viz) · the **hover-help popover** with the Conviction breakdown · the **stock decision masthead** · comparison · per-stock news. Aesthetic locked = **"the instrument"** (→ D-UI-16).

## 16. Phase-1 build log (session 22)

Built additively, zero regression (all 22 routes 200; full loop verified via TestClient):
- **`stocks_in_play`** table (`src/core/db.py`) — status watch|open|closed + `snapshot_json`.
- **Capture** — `+ Track` on `/dash/stock` (`?track=1`) → `_capture_form` → **POST `/dash/track`** (+ `/track/close|promote|remove`). The snapshot + entry (= latest close) are frozen **server-side** in `_capture_snapshot` (never trusted from the client). `_xpower`/`_conv_of` mirror the screener's ×power / Conviction.
- **`/dash/portfolios`** — open positions, entry→CMP→P/L (MTM via indexed close point-lookup), Conv **then→now** drift (frozen vs live), thesis hover, Close.
- **`/dash/watchlists`** — watch tier, live signal chips, Promote / Remove.
- **`/dash/tracker`** — open MTM · hit-rate by strategy (SQL) · avg excess vs Nifty 500 (`index_rows`) · avg hold; honest empty-states.
- In-page Portfolios·Watchlists·Tracker sub-nav (`_track_subnav`); `_WS` maps `watchlists→portfolios`; `_TRACK_CSS` self-contained (no `_BASE_CSS` edit).

**Next (Phase 2–3):** the instrument-screener micro-viz (surface the under-utilized data); `?` hover-help; comparison enrichment; per-stock news + static strip; onboarding; inline-row Track on the grids.
