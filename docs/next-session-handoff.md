# Next-session handoff — Patearn Tracker (AUTONOMOUS self-driving build)

> **TRANSIENT.** Fold the shipped results into `PROJECT_STATE.md` once the parallel "Session 25 explosive-move research" session settles, then `git rm` this file. Created 2026-06-21.

## 0. How to run this session (READ FIRST)
**You are running autonomously. Do NOT wait for Ramana. Resolve every doubt yourself.**
- For any open design decision: pick the **recommended default** in this doc. If a call is genuinely ambiguous, **spawn a small agent panel** (Agent tool — e.g. a quant + a data-engineer + a UX reviewer), let them weigh it, take the majority/recommended option, record the choice, and proceed. Never block on the user.
- Work the **OPEN ITEMS in order** (§3). Ship → verify on the VPS → commit → push → update memory, **one item at a time**. Keep every commit green (no half-deployed state).
- **Environment check before deploying:** confirm `ssh hermes` works and `D:\Hermes` is present. If you are NOT in Ramana's environment (no SSH key / no local repo — e.g. a cloud run), then do **code + commit + push only**, and explicitly flag that **deploy + verification must be run from Ramana's machine** — never claim a feature is "live" without a real VPS curl check.
- If you hit the usage/time limit mid-way: stop cleanly (last commit green), leave a one-line status in the memory note. The 2:10 AM IST routine re-fires and you continue from the next unfinished open item.

## 1. Boot (read these, in order)
1. `D:\Hermes\CLAUDE.md` — binding rules (cost discipline, update PROJECT_STATE, guardrails).
2. `D:\Hermes\PROJECT_STATE.md` — running doc. **NOTE: none of this session's Tracker work is recorded there yet** (see §3 "PROJECT_STATE reconciliation").
3. `D:\Hermes\docs\tracker-segments-spec.md` — the research-grounded per-segment spec (WHAT goes in each segment + pull-status). This is the design source of truth for the open items.
4. Memory notes: `tracker-workspace-redesign` (plan + shipped log), `data-first-light-ui` (UI doctrine), `pat-built-deployed-live` (parallel-session caution — don't absorb its files).
5. `git log --oneline -25`.

## 2. Current state (shipped + LIVE this session, all on VPS at https://srv1704897.hstgr.cloud/dash)
Top nav tab **Tracker** → sub-nav **Dashboard · Portfolios · Watchlists · Performance**.
Commits (newest first): `6bf3191` importer · `09910a4` segments-spec · `f80a0e7` edit · `5efb545` qty+₹P&L · `7ffde05` watchlist-change · `682296b` umbrella+books · `7960cec` custom-strategy · `01d2b14` entry-validation · `66be6df` autocomplete · `40362b5` tracker-tab · `5c55831` add-box.
- **`stocks_in_play`** columns: `id, symbol, strategy, book('Main'), status(watch|open|closed), date_added(=entry date), entry_price, qty, price_target, stop_loss, entry_thesis, snapshot_json(frozen as-of-add signals), exit_date, exit_price, exit_reason, notes`.
- **Routes:** `/dash/dashboard` (cockpit: books/positions/MTM/invested/₹P&L + per-book rollup) · `/dash/portfolios` & `/dash/watchlists` (named-book `?book=` chips, add box w/ ticker autocomplete + Book datalist + entry date/price/qty + Manual→custom-strategy, **Edit** link) · `/dash/performance` (scoreboard; `/dash/tracker`→307) · `/dash/import` + `/dash/import/preview` + `/dash/import/commit` (smart CSV/Excel importer) · `/dash/track` `/track/close` `/track/promote` `/track/remove` `/track/edit` `/track/update` `/track/quote`.
- **Reusable helpers in `src/web/dashboard.py`:** `_capture_snapshot(conn,sym,as_of=)`, `_ohlc_on(conn,sym,date)`, `_equities_ac_json()`, `_rpl(v)`, `_rupee`, `_num`, `_pct`, `_rawnum`, `_book_chips`, `_track_subnav`, `_is_listed`, `_add_box`, `_edit_form`, `_imp_*`/`_parse_upload`/`_detect_mapping`. `openpyxl` installed on the VPS venv.
- **Data we can pull:** EOD OHLCV+delivery (bhavcopy_rows; CMP = last close, NOT live), `stock_signals` (DVPT p/r_score, trigger_rank, `accum_character`, rs_rank, key-price gaps), `index_rows`/`index_signals` (Nifty 50/500/sector → benchmark), `corp_actions` (split/bonus/dividend), news_feed tables, Screener fundamentals (cached), `nse_equity_list` (symbol+company_name).

## 3. OPEN ITEMS — do in order; ship+verify+commit each
### Step 2 — Enrich Portfolios (THE DIFFERENTIATOR — highest value)
- **Sector (+ market-cap) per holding:** build a sector map (prefer Screener `fundamentals`/sector; else index-membership/`stock_rs` sector; else "—"). Add a Sector column. Cache it like `_equities_ac_json`.
- **Target/Stop distance %** columns: (target−CMP)/CMP and (CMP−stop)/CMP, coloured.
- **Days held** = today − date_added.
- **Thesis-health** (lead feature): per holding show **DVPT character now** (`stock_signals.accum_character`), **RS rank**, **Conviction then→now** (frozen `snapshot_json.conv` vs live). Warning colour for DISTRIBUTION / RS-decay / conviction-drop. This is the "is my thesis still valid" view no generic tracker has.
- **Dividends received** since entry: `corp_actions` dividends with ex-date in [date_added, today] × qty.
- Per-book allocation/concentration mini-view (top holdings %).
### Step 3 — Performance
- **XIRR** (cash-flow weighted): outflow qty×entry on date_added; inflow qty×exit on exit_date (closed); open positions = synthetic inflow qty×CMP dated today. Implement Newton/bisection (no scipy). Plus CAGR, absolute, realized vs unrealized.
- **Return attribution:** top contributors / detractors by holding · sector · book · strategy (₹ and % of total P&L).
- **Max drawdown + equity curve:** daily portfolio-value series (Σ qty×close per day) vs Nifty 500, rebased.
- **Closed-trades log** (realized P&L per closed position). **Hit-rate by book** (extend the by-strategy bars).
### Step 4 — Dashboard
- Allocation by **sector / book / market-cap** + **top 3/5/10 concentration**.
- **Today's movers** among holdings (EOD gainers/losers).
- **Needs-attention / red flags:** character→DISTRIBUTION · RS decay · below/near stop · over-concentration.
- **News** for held + watched (map news_feed tickers).
- **Upcoming corporate actions** (ex-dates soon).
- Top contributors/detractors preview (links to Performance).
### Step 5 — Watchlist alerts engine (in-app first; Telegram push deferred — bot is network-blocked)
- Alert rules per watch item: price crosses level · % move since add · near 52w high/low · DVPT trigger fires · RS rank > N · character flips to ACCUM · near target/stop. Store as a new table or a JSON column; evaluate on page-load + a nightly systemd timer; surface "firing now" on Dashboard + Watchlists.
- "Ready to act" surfacing: watch items now hitting a strong setup.
### PROJECT_STATE.md reconciliation (do when untangled)
- `git status` + `git diff PROJECT_STATE.md`. If there are NO foreign uncommitted "explosive-move/Session 25/Launchpad" hunks, it's safe: write a proper Session entry documenting ALL §2 commits + the new routes/columns/decisions (umbrella, named books, qty/₹P&L, entry-validation, edit, importer, segments-spec), update the §"Telegram bot commands"/§"Database schema"/§"Key file paths"/route tables, and commit. If still tangled, leave it, re-note in memory. **NEVER absorb the parallel session's content into your commit.**
### Deferred (only if everything above is done): promoter-pledge/ASM/GSM red flags (needs a Screener pull); weighted-avg grouping for multiple lots of the same script; Telegram push when the bot network unblocks.

## 4. Working method (repeat for every piece)
1. Plan briefly; spawn an agent panel for genuinely open calls, pick the recommended default, proceed.
2. Implement in `src/web/dashboard.py` (+ `src/core/db.py` with an `_ensure_column` migration if a new column; `_init()` runs on import so a restart migrates).
3. Deploy: `scp /d/Hermes/src/web/dashboard.py hermes:/opt/hermes/src/web/dashboard.py` (+ db.py if changed) → `ssh hermes '/opt/hermes/.venv/bin/python -m py_compile /opt/hermes/src/web/dashboard.py && systemctl restart hermes-api'`.
4. **Verify on the VPS:** curl the changed routes + a functional test; create test rows under a scoped marker (`book='QATEST'` or `entry_thesis='QA_*'`) and **delete only those** — NEVER touch Ramana's real rows. Confirm no-regression: every `/dash/*` route returns 200.
5. Commit **only your changed files**: `git add -- <paths>` then a foreign-content check `git diff --cached | grep -iE 'session 25|explosive|launchpad'` must be EMPTY. **NEVER `git add -A`. NEVER stage `PROJECT_STATE.md` while the parallel session is active.** End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Push.
6. Update memory note `tracker-workspace-redesign` with the commit hash + what shipped.

## 5. Guardrails
- **Cost discipline** (CLAUDE.md): bundle changes; no Sonnet in scheduled jobs; rule-based > LLM.
- **EOD data** — CMP = last close; never imply live ticks.
- **Data-first, light UI** — raw values beside verdicts; wide tables fine; never regress.
- **Surgical git** — the working tree is shared with a parallel session (Pat / explosive-move research editing `src/pat/*`, `src/main.py`, `src/assistant/patearn.py`, `PROJECT_STATE.md`, untracked `research/`). Touch ONLY Tracker files.
- The dashboard is the ONLY mutation surface; keep behaviour consistent.

## 6. Definition of done
Steps 2–5 shipped + VPS-verified + committed + pushed; memory updated; PROJECT_STATE.md reconciled if untangled. When all open items are complete, say so plainly in the memory note and note that the 2:10 AM IST auto-restart routine can be deleted.
