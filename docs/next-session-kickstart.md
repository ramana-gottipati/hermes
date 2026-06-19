# Next-session kickstart — Patearn UI Phase 2 + Phase 3 (autonomous run-book)

> **What this is.** A self-contained, self-prompting run-book for the next Claude Code session. The design is already decided and approved (see "Locked design"); this is a **BUILD**, not a design exploration — so run it **autonomously**, pausing only at the checkpoints below. Written at the wrap of Session 22 (2026-06-20).
>
> **To start the session, paste:** *"Read `docs/next-session-kickstart.md` and run it autonomously — Phase 2 first. Follow the checkpoints; otherwise self-direct."* (or just: *"continue the Patearn UI revamp — `docs/next-session-kickstart.md`"*).

---

## 0. Operating mode (how to run this)

- **Autonomous / self-prompting.** Work through Phase 2 end-to-end, then Phase 3, without waiting for per-step instructions. Decide, build, verify, deploy, report. Keep going until a checkpoint or the phase is done.
- **Pause ONLY for:**
  1. **Visual-taste forks** on the instrument screener — present as **AskUserQuestion multiple-choice WITH a recommended option** (the log-scale incident proved visuals need a human eye; don't guess on taste).
  2. **A deploy "eyeball" checkpoint** — after each visible piece lands on the VPS, post the URL and ask Ramana to look (charts/visuals can't be verified by curl). Iterate on what he flags.
  3. **`git push`** and any **destructive/outward** action — confirm first.
- **Everything else: just do it.** Build, `py_compile`, TestClient sweep, scp-deploy, commit (with docs), report.
- **Cost discipline (CLAUDE.md):** bundle changes; avoid long blind chart iteration (the D49 saga). `py_compile` catches f-string brace errors; a VPS 200 confirms the page renders; Ramana's eyeball confirms the visual. Use that ladder.

---

## 1. Boot procedure (read these, in order)

1. `CLAUDE.md` — the binding rules (esp. the PROJECT_STATE update rule + cost/guardrails).
2. `PROJECT_STATE.md` — **§ Session log → "Session 22" (the WRAP)** first, then § "🎨 UI REVAMP" (the Phase-1 + live-trial build logs), § Database schema (`stocks_in_play`, `stock_signals` 88 cols), § Web dashboard routes.
3. `docs/ui-design.md` — **§2 doctrine (D-UI-1…17)**, **§14 the kickstart scope**, **§15 the design decisions**, **§16 the Phase-1 build log**, **§10 the perf hand-off fold (Steps 1–5)**.
4. `docs/metrics-glossary.md` — every custom metric's definition (this is the **content source for the Phase-3 hover-help**).
5. `docs/ui-perf-handoff.md` — the perf Steps 1–5 with code line-pointers (TRANSIENT — `git rm` it once Steps 1–5 are shipped/folded).
6. `docs/perf-architecture.md` — backend backlog + the `adj_close`/`conv` precompute gate.
7. Skim `git log --oneline -15` and the live file `src/web/dashboard.py` (~4.8k lines, single file).

---

## 2. ⚠ CONCURRENCY & GIT DISCIPLINE (read before editing — this bit us in s22)

Multiple Claude sessions have shared this one working tree (D53 CPR + the perf/data work-stream + this UI work). **Assume a parallel session may be live.**

- **Before editing shared files** (`src/web/dashboard.py`, `src/core/db.py`, the docs): run `git status --short` + check `dashboard.py`/`db.py` mtimes. If they're changing under you or there's uncommitted cross-session work, **wait for it to commit** (a background `git`-watcher loop works: poll `git status --short <file>` until clean) before editing. Re-verify quiesced, then build.
- **NEVER `git add -A`.** Stage your files **explicitly** by path; run `git diff --cached --name-only` and confirm it's EXACTLY your files before every commit.
- **Always-excluded (do NOT commit):** `src/assistant/patearn.py` (long-dormant diff) and `src/automation/mtf_signals.py` (held D52 MTF foundation). They must stay out of every commit.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer. Repo-local git identity is `Ramana Gottipati <gottipati.ramana@gmail.com>` (already set).

---

## 3. Current state (what's live)

- **D54 Phase 1 (action loop) — SHIPPED + DEPLOYED.** `stocks_in_play` table; `+ Track` capture on `/dash/stock?track=1` → POST `/dash/track` (+ `/track/close|promote|remove`, server-frozen snapshot, entry=latest close); real `/dash/portfolios`, `/dash/watchlists`, `/dash/tracker`. `python-multipart==0.0.32` is pinned in `requirements.txt` + installed on the VPS (its absence crash-looped the first deploy — Form() routes need it).
- **Stock-page live-trial fixes — SHIPPED + DEPLOYED:** RS overlay seeds the sector by default (`_narrow_sector` membership fallback) + same-sector peer quick-pick chips (≤12); value chart has a robust **y-cap + ▲ markers** (linear, not log); RS overlay has **1Y/2Y/3Y/5Y/Max** length buttons; price chart has a **D/W/M/Q interval toggle** (resamples all 4 synced panes). Both charts now have interval **and** length parity.
- **`main` is ~11 commits ahead of `origin`, NOT pushed** (CPR + perf + all of D54). Deploys were via `scp` (file copy), not git pull.
- **Routes (all 200):** `/dash`, `/dash/markets`, `/dash/sectors`, `/dash/rs`, `/dash/leaders`, `/dash/scan`, `/dash/stocks`, `/dash/workbench`, `/dash/screener`, `/dash/strategies`, `/dash/conviction`, `/dash/cpr`, `/dash/portfolios`, `/dash/watchlists`, `/dash/tracker`, `/dash/stock`, `/dash/ratio`, `/dash/compare`, POST `/dash/track*`, PWA shell.

### FIRST CHECKS (do these before Phase 2)
1. **Verify the backend RS recompute finished.** During s22 a deep-history recompute was running (`index_signals --backfill`, then `stock_rs --backfill`). On the VPS check coverage:
   `ssh hermes 'cd /opt/hermes && .venv/bin/python -' <<'PY'` → query `SELECT count(*),count(rs_vs_broad_today),count(rs_rank),count(primary_sector) FROM stock_signals WHERE trade_date=(SELECT max(trade_date) FROM stock_signals)`. If rank/sector are still ~0, the recompute is unfinished — check `ps aux | grep -E 'stock_rs|index_signals'`; **don't run it yourself** (collides; it's the data work-stream's job). The screener must **COALESCE/degrade gracefully** on NULL RS regardless.
2. **Ask Ramana whether to `git push`** the ~11 unpushed commits (his call).
3. **Check for a "columns live" signal** from the perf work-stream (the `adj_close`/`conv` precompute gate — see §6).

---

## 4. Locked design — "the instrument" (approved "perfect" by Ramana in s22)

The aesthetic is decided; build to it. Stencils were approved via the visualize tool (nav frame, action capture, portfolio/tracker, **the dense instrument screener**, hover-help popover, stock decision masthead, comparison, per-stock news).

**Principles (D-UI-16):**
1. **Rows are readouts, not lists** — inline static SVG/CSS micro-viz turn ~30 buried columns into scannable shapes.
2. **The verdict sits on its evidence** — the rank pill rides the end of the DVPT ladder; the ACCUM/DIST label sits under its 3 axes; never a badge without its numbers.
3. **Ink discipline** — near-black canvas, hairline rules, **monospaced tabular numerals** (`'SF Mono',ui-monospace,Consolas,monospace`), TWO encoding accents (green up/strong `#3fb950`, red down/weak `#f85149`), everything else greyscale. Colour = information, never decoration.
4. **It's a precision instrument, not a web app.** Every micro-viz is **static inline SVG or CSS** (server-rendered, computed once in Python) — lighter than a chart library, no per-cell JS.

**Palette:** bg `#0e1116`, card `#161b22`, border `#30363d`/`#21262d`, text `#e6edf3`, muted `#8b949e`/`#6e7681`, green `#3fb950`/`#2ea043`/`#7ee787`, blue `#1f6feb`/`#58a6ff`, red `#f85149`/`#ffa198`, amber/gold `#bb8009`/`#d29922`/`#ffd99a`, purple `#d2a8ff`.

**The four signature micro-instruments (from the approved screener stencil):**
- **DVPT-vs-power ladder** — a horizontal track with 5 notches (P1M/P2M/P3M/P6M/P12M); green fill to "today"; a triangle marker; the rank pill (SS/S/A/B/C) rides the end. Surfaces ~10 hidden columns (`power_dvpt_*`, `p_score`) in ~130px.
- **Key-price band gauge** — a mini axis with the −1…+5% launch band shaded; a marker at `gap_to_key_p3m` (🎯 in-band / extended / discount). Surfaces `key_price_p*` + `gap_to_key_p*`.
- **Character triglyph** — 3 stacked micro-bars (WHO / WHICH-WAY / CONTEXT) that compose the ACCUM/DIST label. Surfaces the 3 character sub-axes.
- **RS sparkline + 4-cell heat strip** — a rising/flat/falling spark + the existing `_rs_strip` (1m/3m/6m/12m). Surfaces the RS slopes.

---

## 5. PHASE 2 — the instrument screener (PRIMARY GOAL)

Turn the existing `/dash/screener` (and the strategy boards) from digit grids into the **instrument** — surfacing the under-utilized 88-column `stock_signals` data as inline micro-viz, **data-first beside the verdicts** (D-UI-1).

**Under-utilized columns to surface (from the data-engineer audit — most are computed nightly but never shown):**
- `gap_to_key_p{3m,6m,12m}` + the 🎯 launch-band (the actual entry signal) → the key-price band gauge.
- the 3 character sub-axes: `trade_count_ratio_1m_6m`, `deliv_updown_ratio_3m`, `accum_price_drift_3m` (+ `avg_deliv_pct_1m/6m`) → the character triglyph.
- `turnover_surge_3m` + `turnover_surge_1y` (today only `1m` is shown) → beside surge.
- `power_dvpt_{1m..12m}` + `p_score` → the DVPT ladder.
- `rs_vs_broad_slope_{1m,3m,6m,12m}` → the RS spark/heat strip; `rs_vs_sector_today`.
- **Computed-but-DEAD (surface or delete, log the decision):** `hot_days_avg_price`, the RS `*_above_50ma/_above_200ma/_new_52w_high` flags.

**CRITICAL — perf integration (perf hand-off Step 2):** **virtualize the grid AS PART OF this build, never after.** A 27-col × up-to-2000-row grid is ~54k `<td>` + sticky-pane layout = the screener hiccup. Render the visible window + recycle on scroll, keeping the frozen panes (D-UI-12). Do NOT ship the 54k-cell instrument grid first and virtualize later (a visible regression window). Also fold perf **Step 1** (cache `_BASE_CSS`/`_DT_JS`/chart JS to hashed static routes w/ `Cache-Control:immutable`; self-host lightweight-charts; memoize `_latest_dates()`) and **Step 3** (dedupe the chart bootstrap ×5, the type-ahead picker ×2, `chart_css` ×3; then the module split) **before/with** Phase 2 so new columns don't multiply duplication.

**Build order suggestion:** Step-1 perf quick-wins (zero-risk) → the micro-viz as reusable Python helpers (return static SVG/CSS strings) → wire into `/dash/screener` rows behind the existing column-group toggles → virtualize → retrofit the strategy boards (`/dash/stocks`, `/dash/scan`, `/dash/workbench`, `/dash/leaders`, `/dash/conviction`) to the same language → "Open in Screener" everywhere (D-UI-7).

**Checkpoint:** deploy the instrument screener, post the URL, get Ramana's eyeball before retrofitting all boards.

---

## 6. PHASE 3 — the rest (after Phase 2)

1. **Metric hover-help `?` popovers** — a CSS `?`/ⓘ affordance on group headers + pills, content **baked from `docs/metrics-glossary.md` into a Python dict at import** (zero runtime fetch), with a "how it's scored" drill-down for composites (conviction/character/key-price) — the formula + this row's live inputs (the approved popover stencil). Plus a `/dash/glossary` page the popovers deep-link into.
2. **Comparison enrichment** — extend `/dash/compare` (don't duplicate): auto-rebase to % when ≥2 names; a **transposed metric grid** under the chart (metrics as rows, names as columns); one mixed stock+index picker.
3. **News** — per-stock factual block on `/dash/stock` first (results/filings/corp-actions), then a **static typed pill strip** (Results/Upgrade/Promoter — NOT an auto-scroll marquee, D-UI-15); ₹0 via the existing RSS feeds (`news_feed.py` + `feedparser`); a `news_items` table; 15-min cadence; symbol-tagging via `nse_equity_list`. Placeholder-first is fine.
4. **Onboarding** — a dismissible one-line "what am I looking at" strip per workspace (localStorage flag) + the glossary page. No coachmark tour.
5. **Inline-row Track** — the `+ Track` affordance directly on screener/strategy rows (Phase-1 capture currently lives on the stock page; this is the deferred row-level version).

---

## 7. The perf hand-off — the ONLY cross-session gate (Step 5)

`docs/ui-perf-handoff.md` Steps 1–4 are yours to schedule (1 + 3 fold into Phase 2; 4 = a thin `/dash/api/stock/<sym>/series` JSON endpoint + lazy fetch). **Step 5 is BLOCKED on the backend:** reading precomputed `adj_close` (kills the ~3.5s `/dash/stock`, closes B5) and switching the screener `ORDER BY conv` to a precomputed `conv` column **must wait for the perf work-stream's "columns live" signal** (the D47 recompute populates them). Until then **guard with `COALESCE` and do NOT delete the inline back-adjustment**. Retire `ui-perf-handoff.md` (`git rm`) once Steps 1–5 are shipped/folded.

---

## 8. Constraints (binding)

Server-rendered HTML + vanilla JS. **NO SPA, no framework, no build step** (beyond serving hashed static files). Dark theme. **Performance-first.** **NO REGRESSION** — every existing route stays 200; the chat, Telegram, charts keep working. Micro-viz = static inline SVG/CSS (server-rendered), never a per-cell JS toggle or O(rows×cols) client work.

---

## 9. Verify → deploy → commit loop (the exact workflow)

1. Edit locally (Edit tool; string-match, not line numbers — the file shifts under parallel sessions).
2. `python -m py_compile src/web/dashboard.py src/core/db.py` (catches f-string brace errors).
3. **TestClient sweep** — `from src.web import dashboard; app.include_router(dashboard.router)` → assert ALL routes return 200 (no regression). Local DB has synthetic rows (ALPHA/BETACO/DELTA/GAMMA) — enough for 200 + schema checks; real data is on the VPS.
4. **Deploy:** `scp src/web/dashboard.py hermes:/opt/hermes/src/web/dashboard.py` (+ `src/core/db.py` if schema changed) `&& ssh hermes 'systemctl restart hermes-api'`. **SSH rate-limit discipline:** ONE attempt; on timeout, wait/don't hammer (port-22 ban risk).
5. **Verify on the box:** `ssh hermes` → `systemctl is-active hermes-api` (allow ~5s to start) + `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/dash/...` for the changed routes. A 200 on a real stock (RELIANCE) confirms the f-string + JS load.
6. **Eyeball checkpoint** (visuals only) — post the public URL `https://srv1704897.hstgr.cloud/dash/...` and ask Ramana to look.
7. **Commit** — explicit `git add <files>`; `git diff --cached --name-only` (must be exactly yours); update `PROJECT_STATE.md` + `ui-design.md` + `metrics-glossary.md` **in the same commit**; co-author trailer. **No `git push` unless asked.**

**Deploy refs:** VPS `ssh hermes` → `/opt/hermes`; SQLite `/opt/hermes/data/hermes.db` (WAL — reads OK during backfills); public `https://srv1704897.hstgr.cloud/dash` (Caddy → uvicorn :8000); service `hermes-api`.

---

## 10. Doc-update discipline (binding — CLAUDE.md)

Every commit that changes code/behaviour updates `PROJECT_STATE.md` in the **same** commit (routes table, schema, Decision log under **D54**, § What's-NOT-built, and a Session-log entry at wrap). Add new UI decisions to `docs/ui-design.md §13` (next free number after **D-UI-17**) + a build-log section. Define every new surfaced metric in `docs/metrics-glossary.md` BEFORE/as you show it (it's also the hover-help source). Keep the "instrument" design intent rich — never one-line it (memory: `preserve-strategy-intent`, `data-first-light-ui`).

---

## 11. Quick reference

- **Screener:** `/dash/screener` route ~L1700; rows built ~L1750–1820; `table.scr` CSS in `_BASE_CSS`; column-group toggles in `_SCREENER_JS`; helpers `_latest_dates`, `_sector_symbols`, `_narrow_sector`, `_cmp_picker`, `_rs_strip`, `_char_pill`, `_intensity`, `_xpower`, `_conv_of`.
- **Stock chart JS:** the big f-string at ~L3830 (`{{`/`}}` doubled); RS overlay JS `_RS_OVERLAY_JS` (plain template, single braces, `__SERIES__`/`__CDN__` replaced); picker `_STOCK_CMP_PICKER_JS`.
- **`stock_signals` (88 cols)** — see PROJECT_STATE § Database schema for the full inventory (DVPT, R/P baselines + companion prices, scores, rank, ATH, near-break, RS vs broad+sector + slopes + rank, character 7 numerics + label, key-price + gap, ticket, surge).
- **Action loop:** `stocks_in_play` (status watch|open|closed, snapshot_json); helpers `_capture_snapshot`, `_capture_form`, `_track_subnav`, `_snap_chips`, `_then_now`, `_id_form`, `_benchmark_return`.
- **Conviction** = `0.55·(p_score/5·100) + 0.45·rs_rank` (positioning+RS only; NOT backtested; Quality/CPR not folded — an open decision per the glossary).
