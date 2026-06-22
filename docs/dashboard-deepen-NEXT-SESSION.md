# Dashboard-deepen — AUTONOMOUS NEXT-SESSION RUN-BOOK

> **Created** session 30 (2026-06-22) as a planned, agent-researched run-book. **TRANSIENT** (transient-doc-lifecycle):
> fold the durable bits into `PROJECT_STATE.md` once shipped, then `git rm`. **Written so an AUTONOMOUS model
> continues one workstream at a time, no further acceptances.** Companion plan with the same content:
> `C:\Users\gotti\.claude\plans\lazy-splashing-toucan.md`.

---
## ▶ PROGRESS (session 31 — 2026-06-22, autonomous build; NOT committed — Ramana commits)
- **W1 SHIPPED + DEPLOYED.** New `/dash/index?idx=` page (`cockpit.render_index_detail`, broad/sector branch):
  two-axis verdict (on-read ABS price trend BESIDE RS trend — the "trends not identified" fix; IN-LINE defers to
  the price trend so the headline never contradicts the PRICE pill), own-price LightweightCharts (close + 50/200-DMA),
  returns/MA/52w/valuation (PE own-1y percentile), and the EQUAL-WEIGHT bottom-up roll-up (breadth=members RS-up,
  RS leaders, avg/median rs_rank, accumulation split bar, leaders/laggards, intra-index DVPT ladder). Helpers added to
  cockpit.py: `_abs_trend`, `_rel_trend`, `_index_verdict`, `sector_weather`/`_weather_badge`, `_news_card`,
  `_INDEX_PRICE_JS`, `_row_trends`, `_MKT_COLS`, `_idx_median`. `render_markets` rebuilt (regime banner + momentum-ranked
  rotation strip + ABS/RS/weather pills + clickable bundle + headlines card). Nav fixed: every index handle across
  markets/home/sectors/rs/leaders → `/dash/index` (166 links live on /dash/markets); `/dash/ratio` kept as the linked
  full-ratio sub-page. New thin route `dash_index` in dashboard.py. Verified on VPS: `/dash/index?idx=Nifty+Bank`
  → "RISING · IN-LINE" + 14-member roll-up; broad `Nifty+50`/`Nifty+500` 200; full regression sweep 200.
- **W2 SHIPPED + DEPLOYED.** `/dash/stock` migrated to `wide=True` + `_CKPT_CSS`, a 7-tile verdict count-strip
  (CMP·1d · Conviction · RS rank · DVPT trigger+⚡ · pt14 tier·NS · **CCI tier + PROVEN/UNPROVEN · settled** · 52w),
  and the 18 sections wrapped into a 6-pane tabbed sub-nav (Price default · Positioning·DVPT · Relative Strength ·
  Quality · Structure·CPR · Credibility·CCI) via the in-file `.tabbar` + a show/hide JS (all panes stay in the DOM →
  the 4-pane sync graph is byte-untouched). RS overlay is LAZY: its IIFE became `window.__bootRS`, called on first
  RS-tab open (was sizing to a 0-width hidden container). Sticky tabbar offset measured from the header. Hash deep-link
  (`#rs` etc.). Verified VPS: RELIANCE → wrap wide + 6 panes + strip "UNPROVEN · 0/1 settled"; regression 200.
  Added `cci_state()` to cockpit.py (PROVEN/UNPROVEN/STALE from settled-count + `as_of_period` recency).
- **W3 SHIPPED + DEPLOYED.** Stock dossier gains a `#promises settled` chip + a PROVEN/UNPROVEN/STALE badge
  (`cci_state`); the concalls board gains a **#Settled** column + a **"Proven names"** tile (≥1 promise settled vs
  actuals — currently 0, honest: nothing has resolved yet); the screener CCI group gains a **#C** column (group
  colspan 4→5, body 5 g-cci cells matching). New `cci_targets()` in `cci_pipeline.py` (portfolio/`stocks_in_play` ∪
  `watchlist` ∪ conviction shortlist ∪ RS leaders ∪ PILOT, dedup+cap; VPS returns 66) + a `--targets` CLI mode.
  Repointed `hermes-concalls.service`: a non-fatal `ExecStartPre` ingests the targets (`--targets --ingest`) before
  the unchanged `--all --extract --oldest --no-results --max-calls 18` drain; timer still Mon–Sat 07:00, armed.
  Verified VPS: screener #C + colspan5 + 5 cells; concalls #Settled + Proven tile; IDEA dossier "UNPROVEN" + settled chip.

- **W1 FOLLOW-UP (Ramana feedback) — RS-ratio chart restored on /dash/index.** Making `/dash/index` the index landing
  dropped the embedded RS-ratio chart (only a link to /dash/ratio remained); Ramana navigates in specifically to review
  it. Now `render_index_detail` fetches the `ratio_rows ⋈ ratio_signals` curve and embeds the full RS-ratio chart
  (ratio + 50/200-MA + ↑/↓50 crosses + new-52w-RS-high markers + crosshair readout) in the RS block, BESIDE the own-
  price chart. Combined `_INDEX_CHART_JS` renders both, each with its OWN scoped range bar (`#idxPriceRange` /
  `#idxRatioRange`) so they never fight over the buttons. Verified VPS: Nifty Bank/IT show both charts (3521 pts each);
  broad Nifty 50 shows price only (no self-ratio). `/dash/ratio` kept as the standalone page (also vs Nifty 50).

- **W1 FOLLOW-UP #2 (Ramana feedback) — full charting on /dash/index.** The index page's own-price chart was line-only
  with range buttons; Ramana expects the same charting depth as the stock page. `_INDEX_CHART_JS` rewritten: own-price
  chart now defaults to **candlesticks** (index_rows OHLC, fetched back to 2012) with a **Line** toggle, a
  **Daily/Weekly/Monthly/Quarterly** interval switch (client-side OHLC resample, close-of-period), 3M/6M/1Y/2Y/5Y/Max
  ranges, and 50/200-MA recomputed per interval. The RS-ratio chart (line — a ratio has no OHLC) got the same D·W·M·Q
  interval switch + ranges, with ↑/↓50 crosses + new-high markers recomputed per interval. Range buttons compute the
  date window from the full DAILY array so they're correct in every interval. Verified VPS: Nifty Bank/IT show candles
  + both charts + all toggles; broad Nifty 50 candles only (no self-ratio). **NB: the stock page was never touched —
  its 4-pane candlestick + D/W/M/Q resampler + ranges remained intact on the default Price tab the whole time (verified
  live: addCandlestickSeries + data-ptf d/w/m/q + data-r all present in the visible price pane).**

- **CLARITY PASS (5-agent read-only panel → converged fixes; Ramana "tidy up the index/stock pages").** Ran a Nav /
  Index-clarity / Stock-clarity / Consistency / Data-first panel; verified each finding against live data before acting
  (rejected the false ones: valuation-percentile + RS-percentile were correct; "stock page not wide" was wrong — it is;
  `_rel_trend v>1` is healthy — LEADING 4/IN-LINE 10/LAGGING 5 across 19 sectors, slopes −30..+42). Shipped:
  (1) **Index price chart now leads** — reordered to Price → today-snapshot → Relative-Strength(+ratio chart) →
  roll-up (price-first analyst flow). (2) **Honest labels**: `NEW HIGH`→`NEAR HIGH`, `AT LOWS`→`NEAR LOW` (the
  ±2%-of-extreme override was overclaiming). (3) **Breadcrumbs**: `← Markets · Sectors` on /dash/index, `← Screener ·
  Conviction` on /dash/stock (were dead-ends). (4) **Data-first snapshot**: real **50-DMA / 200-DMA** and **52w high /
  low LEVELS** (with the % beside), replacing the %-only + the duplicated trend pill / technicals line. (5) **Stock
  chart parity**: added a **Candles/Line type toggle** (visibility-flip; 4-pane sync untouched) + a **5Y** range —
  matching the index chart and Ramana's "let me switch chart types" ask. (6) Conviction tile shows scales (`/100`,
  `p/5`, `RS/99`); broad-index "see all constituents" drill ungated; `dash_stocks` empty-state link repointed
  /dash/ratio→/dash/index; RS-overlay boot logs errors instead of silently swallowing. Verified VPS: index order
  Price<Snapshot<RS<Rollup, levels + NEAR labels + toggle present; stock Candles/Line + 5Y + crumb; full regression 200.

- **LAUNCHPAD SHIPPED (the §3.C strategic build) — live setup screen.** New `/dash/launchpad` (cockpit.render_launchpad
  + thin route; LAUNCH registry pillar repointed there). Ports research/explosive_moves/launchpad_scan.launchpad_flags
  RENDER-TIME over today's liquid (≥₹5cr trailing-median-turnover) universe, using `src.automation.adjust` (same
  back-adjustment as the research) — MOM_CONT / COILED / PULLBACK, plain-Python (no numpy/cron/table/backfill).
  Consulted the explosive-move research agent: the raw flags are a COMMON precursor universe (342 today), NOT a
  shortlist, so the screen (a) leads with the **fresh rising edge** (setup just turned on ≤2 sessions — the backtest
  enters the edge, not the 8th day; ~84 trades/yr selected from days like these), (b) ⭐-stars any name with a **genuine
  institutional bulk/block net-buyer** that day (`_lp_net_buyers` ⋈ client_classify — the research's high-conviction
  intersection; deals feed is young so usually 0-few), (c) labels the 342 honestly as the universe. HONEST evidence
  card = the real S1 backtest (net of costs, regime-gated: CAGR +4.0% · hit 39% · PF 1.31 · both walk-forward windows
  net-positive) — NOT the inflated 63%/5.7× headline. Verified VPS: GOKEX (⭐ + MOM·CONT/COILED, fresh) tops the list;
  342 universe / 144 fresh / ⭐2 buyers; regression + MEP screener intact.
  NOTE — a parallel **MEP** work-stream is concurrently building an "accumulation·mep" screener column into cockpit.py +
  dashboard.py (its `_mv_adbar`/`_mep_pill` + `mep_signals` table, deployed, uncommitted). My launchpad is additive +
  coexists; deploys were CRLF-diff-checked to never revert MEP.

- **INDEX-RESTORE (Ramana feedback — "you removed my participants + RS").** Root cause: making `/dash/index` the
  click-target dropped his rich content. Fixed ADDITIVELY (no nav rewire, his `/dash/ratio` + `/dash/rrg` untouched):
  (1) the **full sortable participants table for EVERY index** incl. size (Midcap 150=183, Smallcap 250=283 liquid
  members) with a Character (accum/dist) column; (2) a **relative-strength section for SIZE indices** = return vs
  Nifty 500 per window + Compare link + RRG link (size indices have no ratio series; their RRG depth is keyed under
  variant names in rs_extras); (3) sectors keep the RS-ratio chart + a new RS-depth panel (rs_extras/capture) + RRG
  link. Verified live. **accumulation/distribution confirmed intact in 5 places** (index split + Character col, stock
  page, screener Character + MEP column, home Stealth). **HARD LESSON recorded: build additively, never replace his
  ecosystem** (see the operating mode in `docs/tags-and-index-NEXT-SESSION.md`).
- **➡ WHAT'S NEXT lives in `docs/tags-and-index-NEXT-SESSION.md`** — the THEME-TAGS feature (AI-assisted, you approve;
  stock page + Themes page + screener + participant lists) + the index polish open items. That doc is the new
  self-prompting run-book + kickstart.

**DEPLOY STATE:** all three workstreams live on the VPS (`hermes-api` active), CRLF/parallel-diff-checked, py_compile-
guarded. NOT committed — Ramana commits. Full 20-route regression sweep 200, no API errors. Files touched:
`src/web/cockpit.py`, `src/web/dashboard.py`, `src/automation/cci_pipeline.py`, `/etc/systemd/system/hermes-concalls.service`.

## 0. WHAT THIS IS (one line)
Deepen the dashboard into a real equity-analyst tool across 3 sequenced workstreams: **(W1) Markets/Index analytics +
navigation**, **(W2) the per-stock screen → cockpit + tabs**, **(W3) CCI coverage + record count** — all on the
existing full-bleed cockpit UI, deterministic, data-first.

## 1. DECISIONS LOCKED (Ramana, session 30 — do not re-litigate)
- **Sector headwind/tailwind/recovery = DERIVED FROM DATA** (RS trend + RS slope + constituent breadth), deterministic,
  zero-LLM-at-render. **PLUS a light, read-only "latest headlines" card** (market-wide) reusing the existing news store.
- **Stock page = TABBED** (verdict tile-strip + sticky sub-nav; Price default; charts lazy-load). Mockup approved.
- **Scope = all 3 workstreams, sequenced** (W1 → W2 → W3), one autonomous run.

## 2. CONFIRMED DATA FACTS (verified live on the VPS this session — build on these, don't re-derive)
- **`index_signals`** has, per index: `close_value`, `ret_1d/1w/1m/3m/6m/12m_pct`, **`pct_above_50d_avg`,
  `pct_above_200d_avg`, `pct_off_52w_high`, `pct_above_52w_low`** (the absolute-trend inputs), `rs_vs_broad_today`,
  `rs_vs_broad_slope_1m/3m/6m/12m`, `rs_vs_broad_above_50ma/200ma`, `rs_vs_broad_new_52w_high`,
  **`rs_vs_broad_trend_state`** (RS-only!), **`broad_benchmark`** (NULL ⇒ broad/size index).
- **`index_rows`** (index OHLC history): `open/high/low/close_value`, `change_pct`, `volume`, `turnover_cr`,
  **`pe`, `pb`, `dividend_yield`** — feeds the index price chart + valuation.
- **`stock_index_membership`**: 4,005 rows, **24 indices**, latest snapshot 2026-06-19, `weight_pct` EMPTY (→ EQUAL-WEIGHT
  roll-ups; label it). `_sector_symbols(conn, idx)` returns members. (e.g. Nifty Bank = 14 members.)
- **`stock_signals`** carries every roll-up input: `rs_rank` (1–99 broad), `rs_vs_broad_trend_state`,
  `rs_vs_sector_trend_state`, `accum_character` (ACCUMULATION/DISTRIBUTION/CONSOLIDATION/NEUTRAL), `p_score`,
  `trigger_rank`, `is_ath_dvpt`, `pct_from_52w_high`, `power_dvpt_*`, `delivery_value_today`, `key_price_p3m`,
  `gap_to_key_p3m`, `price_vs_hot_avg_pct`, `primary_sector`. NOTE: the only per-stock 200-DMA flag is
  **`rs_vs_broad_above_200ma`** (RS-vs-200DMA, NOT price-MA) — so member breadth is **RS-based**; label it precisely or
  add a small nightly price-200DMA flag in `signals.py` (optional).
- **`sent_news`**: columns `id, source, url, title, sent_at` only (656 rows) — **no body, no sector tag** ⇒ the news
  card is a **market-wide latest-headlines list** (title + source + date, linked), NOT per-sector. Sector weather stays
  data-derived.
- **`concall_scores`** already has `n_concalls`, `n_promises_resolved`, tier, composite, guidance_accuracy,
  quantification_rate, deterioration_score, veto, as_of_period.
- **ROOT CAUSE of "trends not properly identified":** `rs_vs_broad_trend_state` is computed over the RS ratio
  (index ÷ Nifty 500) ONLY, never the index's own price → a sector rising but lagging Nifty 500 shows "DOWNTREND."
  Fix = derive an ABSOLUTE trend on-read and show BOTH.

## 3. THE COCKPIT PATTERN (how to build — see `docs/ui-cockpit-NEXT-SESSION.md`)
New `render_*` in `src/web/cockpit.py`; `dashboard.py` handler = thin wrapper that early-returns
`HTMLResponse(_shell(title, cockpit.render_x(...), active, date, wide=True))`, old body left dead. Reuse `_CKPT_CSS`,
`_ck_tile`/`_ck_strip`, `_board`, `_rs_strip`, `p-{STATE}` pills, `_mv_ladder`, `_sector_symbols`, `_real_sectors_in`,
`MAJOR_BROAD/MAJOR_SECTORS/LEADERSHIP_SET`, `_q/_pct/_num/_esc`, LightweightCharts (`_LWC_CDN`).

---

## 4. WORKSTREAM 1 — Markets / Index analytics + navigation  (PRIORITY 1)

**1a. Nav fix (the dead-click).** Route every index handle → new `/dash/index?idx=<name>`:
- markets **bundle table rows** (no `<a>` today, `cockpit.py` render_markets `brows`) → wrap symbol cell in `<a href="/dash/index?idx=…">`.
- `maj_card` href `/dash/ratio?idx=` → `/dash/index?idx=`; home sector-rotation rows; the `/dash/ratio?idx=` links in render_sectors/render_rs/render_leaders. Keep `/dash/ratio` as the linked "full ratio chart" sub-page.

**1b. New `/dash/index?idx=` page** — `cockpit.render_index_detail(idx, idx_date, sig_date)`, `wide=True`, one
`is_broad=(broad_benchmark IS NULL)` branch for broad + sector:
- **Verdict banner (the fix):** ABS axis `abs_score=(pct_above_200d_avg>0)+(pct_above_50d_avg>0)+(ret_3m_pct>0)` →
  3 UPTREND/2 UP-BIASED/1 MIXED/0 DOWNTREND; overrides `pct_off_52w_high>=-2`→NEW HIGH, `pct_above_52w_low<=2`→AT LOWS.
  REL axis = `rs_vs_broad_trend_state` + `rs_up=#{slope_1m/3m/6m/12m > +1}` → LEADING (RS up & rs_up>=3) / LAGGING
  (RS down & rs_up<=1) / IN-LINE. Render a `.banner` (`b-on/neu/off`) with the raw numbers beside the verdict;
  **show BOTH trends as pills.** Composite label = the abs×rel matrix: broad index → just the ABS label;
  sector → UPTREND×LEADING = **MARKET LEADER**, UPTREND×LAGGING = **RISING BUT LAGGING**, DOWNTREND×LEADING =
  **DEFENSIVE / RELATIVE WINNER**, DOWNTREND×LAGGING = **AVOID**, else **NEUTRAL**.
- **Top-down:** index **price chart** (LightweightCharts over `index_rows` OHLC); returns table (1d…12m); MA/52w chips;
  valuation `pe/pb/dividend_yield` + own-1y percentile (`below = COUNT(pe_hist<pe_today) over last 252 index_rows`);
  sectors also get `_rs_strip` + the abs×rel quadrant + RS-momentum percentile + "Open full ratio chart →".
  REUSE: `dash_ratio` already builds the index KPI/stats block (close/Open/High/Low/volume/turnover_cr + the returns
  row + MA/52w block) and the abs×rel quadrant SVG + the RS-momentum percentile gauge + the "top constituents by DVPT"
  list — lift those builders into `render_index_detail` rather than rewriting; the new page is the cockpit-framed
  superset of today's `/dash/ratio`.
- **Bottom-up roll-up** (`_sector_symbols` ⋈ latest `stock_signals` ⋈ `bhavcopy_rows`, `_SCAN_FILTERS`, EQUAL-WEIGHT,
  show N): breadth `% in (UPTREND,BREAKOUT)`; `# RS leaders (rs_rank>=80)`; avg rs_rank (SQL) + median (Python);
  accumulation split (`accum_character`); `# near 52w-high (pct_from_52w_high>=-5)`; `# ATH-DVPT`; net accum skew.
- **Leaders & laggards within the index** (top/bottom 8 by rs_rank) + **intra-index DVPT** (top by
  `is_ath_dvpt,p_score,delivery_value_today` with `_mv_ladder`, trigger pill, entry tag from `price_vs_hot_avg_pct`).

**1c. `sector_weather()`** — deterministic, first-match-wins, each rule justified:
TAILWIND (RS up · s3>+1 · s1>0 · breadth≥55 · accum skew≥0) · RECOVERY (s6/s12<0 but s1>+1 · s3>s6 · breadth>40) ·
HEADWIND (RS down · s3<-1 · weak breadth/distribution) · ROLLING-OVER (RS up but s1<0 · s12>0) · NEUTRAL. Ship
slope-only first. Badge on /dash/index, the markets bundle, /dash/sectors (reasons[] on hover).

**1d. News card** — read-only "latest market brief": newest ~8 `sent_news` rows (title→url, source, `sent_at`),
on the Markets landing, labelled "headlines · context, not a signal." NO LLM at render. (Market-wide; sent_news has no
sector tag.)

**1e. Markets landing upgrades** (`render_markets`): regime header (Nifty 50 ABS trend + `% indices >200-DMA` +
`% REAL_SECTORS in RS uptrend` + size rotation via `LEADERSHIP_SET` 3m); sector rotation strip ranked by
`0.6·s3+0.4·s6` with weather badges; bundle table gains an ABS-trend pill beside the RS-trend pill + weather badge +
clickable rows.

**Build order:** nav fix + `/dash/index` shell → Verdict + ABS pill → roll-up + leaders/laggards → `sector_weather` →
markets regime/rotation → valuation pctl + intra-index DVPT → news card.

## 5. WORKSTREAM 2 — Stock page: cockpit + tabs  (PRIORITY 2)
Migrate `dash_stock` (`dashboard.py`), ONE server render, reusing every section builder verbatim:
- `wide=True` + `_CKPT_CSS` + **verdict count-strip** (7 `_ck_tile`s: CMP·1d · Conviction(`_conv_of`) · RS rank ·
  DVPT trigger+×pow(⚡ATH) · pt14 tier·NS · **CCI tier + `{n_concalls} calls·{n_promises_resolved} settled`** · 52w).
  Degrade to "—" when unscored.
- **Tabbed sub-nav** (approved mock): 6 panes — **Price** (4 synced LWC panes, eager default) · **Positioning·DVPT**
  (insights, inertia, character, zones, key-price) · **Relative Strength** (RS overlay + RS summary) · **Quality**
  (pt14 + fundamentals) · **Structure·CPR** · **Credibility·CCI**. Use the in-file `.tabbar` CSS + a `cflt`-style
  `display` show/hide (keeps all panes in the DOM → LWC sync graph untouched). Search + Track stay outside tabs.
- **Perf:** lazy-init the **RS-overlay chart** on first RS-tab open; **reveal hook** (`fitContent()`+`applyOptions({})`
  on first show) for hidden-tab sizing. Do NOT touch the 4-pane `syncing` guard or the D/W/M/Q resampler. Hash deep-link.

**Build order:** verdict strip + wide + CSS → wrap 18 sections into 6 panes + sticky tabbar + show/hide → reveal hook →
lazy RS chart → `#tab` deep-link.

## 6. WORKSTREAM 3 — CCI coverage + record count  (PRIORITY 3)
- **Record count:** stock verdict tile cta + dossier (`n_concalls`/`n_promises_resolved`); concalls board **#Settled**
  col + **"Proven names"** tile; screener CCI group **#C** col (group colspan 4→5 in both header rows).
- **PROVEN/UNPROVEN + stale** — deterministic `cci_state()` from counts + `as_of_period` (stale if newest period older
  than ~2 quarters). Degrades gracefully while data is thin.
- **Coverage policy:** the drain (`concall_extract.pending_rows`) is oldest-first over whatever's in `concalls`, so the
  ingest list steers it. Add `cci_targets()` = (portfolio ∪ watchlist ∪ conviction shortlist ∪ pillar-surfaced ∪
  PILOT/golden floor), dedup+cap; repoint `hermes-concalls.timer` to `cci_pipeline --ingest <targets>` then the
  unchanged `--extract --oldest --max-calls 18`. Accelerator: paid Gemini / claude.ai-bulk (only way past 20/day).

**Build order:** `cci_state()` → stock tile + dossier → board #Settled + Proven tile → screener #C col → `cci_targets()`
+ repoint cron.

## 7. CONSTRAINTS (binding)
Cockpit pattern only (thin wrappers, `wide=True`, old bodies dead). **Zero LLM at render. Data-first (raw number beside
every verdict). Never regress. Honest labels** (roll-ups EQUAL-WEIGHT; breadth RS-vs-200DMA unless a price-200DMA flag
is added — never mislabel; `rs_rank` is broad-universe). Don't edit `src/assistant/patearn.py`. **Commit only when
Ramana asks.** Deploy: `py_compile` (watch Py3.10 f-string backslash) → CRLF/parallel-diff-check vs VPS → `scp
cockpit.py dashboard.py` → py_compile-guard + `systemctl restart hermes-api` → curl + grep + regression sweep.

## 8. VERIFICATION
`/dash/index?idx=Nifty+Bank` (sector) AND `?idx=Nifty+50` (broad) → 200 with verdict + roll-up; markets bundle rows
have `href`; `/dash/stock?sym=RELIANCE` → 200, `wrap wide` + `tabbar`, tabs switch, only Price eager; CCI #Settled +
PROVEN render. Regression 200: `/dash`, `/dash/markets`, `/dash/strategies`, `/dash/concalls`, `/dash/screener`, the 4
strategy detail pages. Post the public URLs.

## 9. OUT OF SCOPE (state, don't silently build)
Price-200DMA nightly flag (optional) · weighted roll-ups (needs weight_pct) · screener registry refactor (cockpit
§3.B) · Launchpad productization (§3.C) · CCI falsification-gate verdicts (data-gated, separate).

---

## 10. THE KICKSTART PROMPT (paste this to start the next session)

> You are continuing the Patearn project (personal Indian-equity quant dashboard; repo `D:\Hermes` on Windows,
> deployed to a Mumbai VPS reachable as `ssh hermes` → `/opt/hermes`, served at `https://srv1704897.hstgr.cloud/dash`).
> Work AUTONOMOUSLY to completion: single acceptance, self-drive workstream-by-workstream, deploy as you go, keep
> records current, don't stop to ask between steps. Be concise; don't dump full context.
>
> BOOT (read in order, then continue): 1) `docs/dashboard-deepen-NEXT-SESSION.md` (THE run-book — locked decisions,
> confirmed data facts, the 3 workstreams with exact formulas/columns + build orders). 2) `docs/ui-cockpit-NEXT-SESSION.md`
> (cockpit pattern + §4 deploy recipe). 3) `PROJECT_STATE.md` Decision log + latest Session entries. 4)
> `git log --oneline -10`. Then skim `src/web/cockpit.py` (`STRATEGY_REGISTRY`, `_CKPT_CSS`, `_ck_tile/_ck_strip`,
> `_board`, the `render_*`) + `src/web/dashboard.py` (`dash_stock`, `dash_ratio`, `_sector_symbols`, `_rs_strip`,
> `_mv_*`, `_real_sectors_in`, `.tabbar` CSS).
>
> BUILD — three workstreams IN ORDER (every formula/column/file is in the run-book §4–6):
> **W1 Markets/Index + navigation** — fix the dead-click (markets bundle rows + cards → a new full-bleed
> `/dash/index?idx=` page, `cockpit.render_index_detail`, branches broad vs sector). Give it a rigorous **two-axis trend
> verdict** (derive the ABSOLUTE price trend on-read from `pct_above_50d/200d_avg`+`ret_3m_pct`+52w and show it BESIDE
> the existing RS trend — this fixes "trends not properly identified"), an index **price chart** (LightweightCharts over
> `index_rows`), returns/MA/52w/valuation, and the **bottom-up constituent roll-up** (`_sector_symbols` ⋈ `stock_signals`,
> EQUAL-WEIGHT, show N: breadth, # RS leaders, avg/median rs_rank, accumulation split, leaders/laggards within the index,
> intra-index DVPT). Add a deterministic **`sector_weather()`** badge (tailwind/headwind/recovery/rolling-over) to the
> index page, the markets bundle, and `/dash/sectors`. Upgrade the markets landing (regime header + rotation strip +
> both-trend pills). Add a **read-only latest-headlines card** from `sent_news` (title/source/date, market-wide,
> "context not a signal", NO LLM).
> **W2 Stock page → cockpit + tabs** — migrate `/dash/stock` to `wide=True` + `_CKPT_CSS` with a 7-tile verdict
> count-strip, and wrap its 18 sections into a tabbed sub-nav (Price · Positioning · Relative Strength · Quality ·
> Structure · Credibility; Price default) using the in-file `.tabbar` CSS + a `cflt`-style show/hide. Lazy-init the
> RS-overlay chart on first RS-tab open + a `fitContent` reveal hook; do NOT touch the 4-pane chart sync. (Tabbed
> layout already approved via mockup.)
> **W3 CCI coverage + record count** — surface `n_concalls`/`n_promises_resolved` on the stock verdict tile + dossier,
> a #Settled column + "Proven names" tile on the concalls board, and a #C col in the screener CCI group. Add a
> deterministic PROVEN/UNPROVEN + stale state (`cci_state()`). Add `cci_targets()` (portfolio ∪ watchlist ∪ conviction
> ∪ pillar-surfaced ∪ pilot/golden) and repoint `hermes-concalls.timer` to ingest those before the 18/day oldest-first
> drain.
>
> CONSTRAINTS: cockpit pattern only (new `render_*` in `cockpit.py` + thin `dashboard.py` wrappers, `_shell(...,
> wide=True)`, old bodies dead). **Zero LLM at render; data-first; never regress; honest labels** (roll-ups EQUAL-WEIGHT
> — `weight_pct` empty; breadth is RS-vs-200DMA unless you add a price-200DMA nightly flag — never mislabel). Deploy via
> `py_compile` → CRLF/parallel-diff-check vs VPS → `scp cockpit.py dashboard.py` → py_compile-guard + `systemctl restart
> hermes-api` → curl 200 + grep markers + regression sweep (`/dash`, `/dash/markets`, `/dash/strategies`,
> `/dash/concalls`, `/dash/screener`, `/dash/stock`, the 4 strategy detail pages). Do NOT edit
> `src/assistant/patearn.py`. **Commit to git ONLY when Ramana asks.** Update `PROJECT_STATE.md` + this run-book as you
> ship. Pause only for a genuine visual-taste fork (show a `show_widget` mockup first) or a deploy eyeball (post the URL).
>
> Start with W1 (nav fix + `/dash/index` shell), deploy, post the URL, then continue.
