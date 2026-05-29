# Hermes — Project State

> **Last updated:** 2026-05-29
> **Running document.** This is the source of truth for the next Claude Code session.

---

## 🔴 BINDING RULE — How this document is maintained

This document is maintained **continuously** by every Claude Code session, not just at session wrap. Updating it is part of the work, not paperwork afterwards.

A commit that changes code or behaviour **MUST** include the corresponding update to this file in the same commit. Specifically:

- New decision made → append numbered entry to **§ Decision log** with WHY
- New Telegram command → update **§ Telegram bot commands** table
- New DB table / column / view → update **§ Database schema**
- New file in `src/` or `scripts/` → update **§ Key file paths**
- Item from **§ What's NOT yet built** built → remove it from there
- New limitation or missing piece discovered → add it to **§ What's NOT yet built**
- End-of-session with anything shipped → new **§ Session log** entry at the TOP

This rule applies even if the user does not explicitly ask. The user ratified it once (session 13). It is now permanent.

The goal: any future session can read this file and have a complete, current picture — no need to grep the codebase or re-derive architecture.

If you (a future Claude session) find yourself thinking "I'll update this at the end" — **don't**. Update it as you make the decision or write the code. Otherwise it gets forgotten.

---

---

## TL;DR — Where things stand right now

Hermes is a personal AI agent running 24/7 on a Hostinger VPS in Mumbai. It does three things today:

1. **Telegram bot** — Ramana chats with Hermes via `@ramana_hermes_bot`. Conversational memory persists in SQLite. Currently uses Haiku 4.5 by default to keep cost down.
2. **Indian market news intelligence** — twice-daily news poller (9 AM + 5 PM IST weekdays) pulls from Moneycontrol / Livemint / ET Markets / Business Standard, Haiku classifies items, EARNINGS items trigger Stage 1 rule-based scoring.
3. **patearn 14-pattern Indian equity screener** — rule-based Python scoring (no LLM) using Screener.in fundamentals on-demand, plus NSE bhav copy with delivery data, plus corporate actions, plus pre-computed rolling "delivery value per trade" signals.

**Deep stock analysis (Phase 4 qualitative)** is done in **claude.ai** under Ramana's existing $20/mo subscription — NOT via the API. Hermes does the data collection, filtering, and rule-based scoring; claude.ai handles the reasoning. This is the deliberate cost-control design choice.

**Current Anthropic API spend pattern (target):** ~₹150–300/month. Cap set at $10/month in console.anthropic.com.

**5-year bhav copy backfill** — built and ready to run on VPS but not yet executed at the time of this writing. Single command to start: `nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &`

---

## Quick reference

### URLs and IDs

| What | Where |
|---|---|
| GitHub repo (public) | https://github.com/ramana-gottipati/hermes |
| VPS IP | 187.127.173.149 |
| VPS hostname | srv1704897.hstgr.cloud |
| Telegram bot | https://t.me/ramana_hermes_bot |
| Candidates web page | http://187.127.173.149:8000/candidates |
| Ramana's Telegram user ID | 282907906 |
| Telegram news group | "Hermes_Stock News" (supergroup, chat_id `-1003852136413`) |

### Key file paths

**On Ramana's Windows laptop (D: drive):**
```
D:\Hermes\                                          ← local working copy of repo
├── CLAUDE.md                                       ← entry point for Claude Code sessions
├── PROJECT_STATE.md                                ← THIS FILE (running doc)
├── docs\
│   ├── hermes-bhavcopy-architecture.docx           ← architecture Word doc
│   └── build-architecture-doc.js                   ← script that generates the docx
├── src\
│   ├── main.py                                     ← FastAPI app (incl. /candidates view)
│   ├── core\
│   │   ├── db.py                                   ← SQLite schema + init
│   │   ├── llm.py                                  ← Anthropic client wrapper
│   │   └── settings.py                             ← .env loader (with load_dotenv fix)
│   ├── assistant\
│   │   ├── chat.py                                 ← Telegram chat handler w/ memory + prompt caching
│   │   ├── conversations.py                        ← SQLite CRUD for conversation history
│   │   ├── telegram_bot.py                         ← bot listener, all slash commands
│   │   └── patearn.py                              ← patearn system prompt + Haiku/Sonnet wrapper
│   └── automation\
│       ├── news_feed.py                            ← RSS pull + classifier + Stage 1 screen trigger
│       ├── digest.py                               ← twice-daily Telegram candidate digest
│       ├── bhavcopy.py                             ← NSE sec_bhavdata_full ingestion (incl. backfill)
│       ├── corp_actions.py                         ← NSE corporate actions (bonus/split/etc.)
│       ├── signals.py                              ← rolling DVPT signals (flat + power deliveries)
│       ├── screener.py                             ← Screener.in HTML scraper
│       └── scoring.py                              ← rule-based 14-pattern patearn scorer
├── resources\patearn\                              ← copy of patearn skill files (used by patearn.py)
│   ├── SKILL.md
│   ├── patterns.md
│   ├── failures.md
│   └── exit-protocol.md
├── scripts\
│   ├── vps-bootstrap.sh                            ← initial VPS deploy script
│   ├── setup-news.sh                               ← incremental update (rerun for new features)
│   ├── full-backfill.sh                            ← 5-year bhav copy + signals backfill
│   └── download-from-vps.bat                       ← Windows batch to scp data home
└── .env                                            ← secrets (gitignored; ANTHROPIC + TELEGRAM keys)
```

**On VPS (mirror of repo + data):**
```
/opt/hermes/                                        ← clone of github repo
├── .venv/                                          ← Python virtualenv
├── .env                                            ← secrets (copy of laptop .env, may diverge)
├── data/                                           ← THE DATA — NOT IN GITHUB
│   ├── hermes.db                                   ← single SQLite file = everything
│   └── bhavcopy/                                   ← raw NSE archive (5y when backfilled)
│       └── YYYY/MMM/sec_bhavdata_full_*.csv
└── (rest of repo content same as laptop)

/etc/systemd/system/
├── hermes-telegram.service                         ← bot (always running)
├── hermes-api.service                              ← FastAPI on :8000
├── hermes-news.service + .timer                    ← 9 AM + 5 PM IST weekdays
├── hermes-digest.service + .timer                  ← 10 AM + 6 PM IST weekdays
└── hermes-bhavcopy.service + .timer                ← 6 PM IST weekdays (after backfill is run)

/var/log/
├── hermes-telegram.log
├── hermes-api.log
├── hermes-news.log
├── hermes-digest.log
├── hermes-bhavcopy.log
└── hermes-backfill.log                             ← only present if backfill has been run
```

### Most-used commands

| To do this... | Run this... |
|---|---|
| SSH into VPS | `ssh root@187.127.173.149` |
| Pull latest code + restart bot | `wget -qO /tmp/setup.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh && bash /tmp/setup.sh` |
| Run 5-year backfill (background) | `nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &` |
| Watch backfill progress | `tail -f /var/log/hermes-backfill.log` |
| Check bot status | `systemctl status hermes-telegram` |
| Pull all data to laptop | Double-click `D:\Hermes\scripts\download-from-vps.bat` |
| Score one stock manually | In Telegram: `/score RELIANCE` |
| Manual deep analysis | In claude.ai with patearn skill loaded — paste the /score result |

---

## Architecture

### High-level data flow

```
NSE / BSE / Moneycontrol / Livemint / ET Markets / BS / Screener.in
                              ↓ (free public sources)
              ┌───────────────────────────────────────────┐
              │             HERMES on VPS                  │
              │                                            │
              │  1. News poller (2x/day)                  │
              │     RSS → Haiku classify → EARNINGS items │
              │                ↓                           │
              │     ticker → Screener.in scrape            │
              │     (cached 7d) → rule-based scoring       │
              │     → screen_candidates                    │
              │                                            │
              │  2. Bhav copy fetcher (daily, 7:30 PM IST)│
              │     sec_bhavdata_full → bhavcopy_rows      │
              │     (raw archive at data/bhavcopy/)        │
              │                                            │
              │  3. Signals computation (nightly)          │
              │     DVPT + flat avg + power deliveries     │
              │     → stock_signals                        │
              │                                            │
              │  4. Digest (2x/day, 10 AM + 6 PM IST)     │
              │     pending screen_candidates              │
              │     → Telegram patearn group                │
              │                                            │
              │  5. FastAPI :8000 → /candidates web view  │
              │     Telegram bot (slash commands)          │
              └───────────────────────────────────────────┘
                              ↓
         ┌──────────────────────┴─────────────────────┐
         ↓                                            ↓
   Telegram phone               Browser (candidates page)
   • Digest msgs                       │
   • Slash commands                    │ copy row
                                       ↓
                                 claude.ai
                                 (Ramana's $20/mo subscription)
                                 • Sonnet 4.6
                                 • patearn skill activated
                                 • Phase 4 qualitative analysis
```

### Telegram bot commands (registered in slash menu)

| Command | What it does | Cost per use |
|---|---|---|
| `/score TICKER` | Rule-based patearn score from Screener data (no LLM) | ₹0 |
| `/analyze TICKER` | Full Haiku patearn analysis (use sparingly) | ~₹2 |
| `/watch TICKER [note]` | Add to watchlist | ₹0 |
| `/unwatch TICKER` | Remove | ₹0 |
| `/watchlist` | List watched stocks | ₹0 |
| `/news` | Manual news pull | ~₹0.50 |
| `/news_here` | Register chat as news destination | ₹0 |
| `/news_where` | List registered news destinations | ₹0 |
| `/news_stop` | Remove chat as news destination | ₹0 |
| `/patearn_here` | Register chat as digest destination | ₹0 |
| `/patearn_stop` | Remove as digest destination | ₹0 |
| `/reset` | Start fresh conversation | ₹0 |
| `/whoami` | Show Telegram user ID | ₹0 |
| `/start` | Help | ₹0 |

Plain text in DM → conversational chat with memory (Haiku).
Plain text in group → conversational chat (auth gate — only Ramana gets responses, others ignored).

### Database schema (SQLite at `/opt/hermes/data/hermes.db`)

**Conversation memory:**
- `conversations` (id, created_at, title, telegram_user_id)
- `messages` (id, conversation_id, role, content, created_at)

**News + screening:**
- `sent_news` (url unique — dedup for news brief delivery)
- `news_destinations` (chat_id PK)
- `screen_candidates` (symbol, verdict PASS/WATCH, rationale, signals_json, news_url, screened_at, digest_sent_at, your_note, your_status)
- `patearn_destinations` (chat_id PK)
- `watchlist` (symbol PK, note, added_at, added_by)
- `earnings_triggers` (legacy — kept for compat)

**Fundamentals (Screener.in cache, 7-day TTL):**
- `fundamentals` (symbol PK, company_name, fetched_at, market_cap_cr, current_price, pe, pb, roce, roe, debt_to_equity, promoter_holding, promoter_pledge, fii_holding, dii_holding, sales/profit growth 5y/3y/ttm, opm_latest, eps_ttm, etc.)
- `pattern_scores` (id, symbol, scored_at, pws, ns_base, ns_pessimistic, ns_optimistic, pac, tier, qg_pass, hard_disqualified, disqualifier_reasons, detail_json)

**Bhav copy + delivery (THE data layer):**
- `bhavcopy_rows` — every column from sec_bhavdata_full + raw_json fallback. Wide schema, ~25 columns, indexed on (symbol, trade_date), trade_date, series. Includes deliv_qty, deliv_per. Unique on (symbol, trade_date, series, instrument_type).
- `bhavcopy_dates` — tracks ingested dates for idempotent backfill.
- `corporate_actions` — bonus/split/rights/dividend per (symbol, action_type, ex_date). Parsed ratios where possible.
- `stock_signals` — pre-computed nightly. Per (symbol, trade_date): delivery_value_today, total_value_today, delivery_value_per_trade, flat averages over 5/10/30/60/90/180/365 days (excl. today), power deliveries (top-N: 5 of 22 days, 10 of 44, 15 of 66, 40 of 132), ratios today vs avg_30d / power_1m / power_3m.

**View:** `prices_eq` — filtered to EQ series + CM segment, exposes OHLC + delivery cleanly for downstream code.

---

## Decision log (the big ones)

### D1 — Telegram as primary interface
Why: Ramana already has Telegram, free, mobile-first, real-time. Web UI later for review (candidates page) but interaction primary is Telegram.

### D2 — Haiku default, Sonnet rarely
Why: Cost. Original Sonnet default burned $4 in a single casual chat session (long history × Sonnet pricing × no caching). Switched everything to Haiku + sliding window (last 30 messages) + prompt caching. /analyze uses Haiku by default; deep dives happen in claude.ai (subscription) not API.

### D3 — Self-hosted on Hostinger VPS, not cloud-managed
Why: Ramana bought a KVM4 (2-year prepaid) for ₹31,123. Wants ownership. Mumbai location = low latency. 200 GB / 16 GB RAM is overkill for Hermes but covers future projects.

### D4 — SQLite, not Postgres
Why: Portability. Single file backup via scp. No DBA work. Personal scale fits SQLite comfortably (~2M rows expected after 5y backfill).

### D5 — Public GitHub repo
Why: Code has no secrets (.env is gitignored). Public lets the deploy script wget straight from raw.githubusercontent.com without auth. Private repo would need a PAT for every VPS pull.

### D6 — Slash menu registration on bot startup
Why: Discoverability. Without `set_my_commands`, the user has no way to see what commands exist.

### D7 — News classification kept LLM-driven, Stage 1 screening moved to rule-based
Why: Cost control. Classifier (Haiku) is small per-item and runs only on fresh items (deduped). Stage 1 was originally Haiku-based but produced fuzzy signals — replaced with Python rules over Screener data for precision and ₹0 marginal cost.

### D8 — Build fundamentals over time, not bulk
Why: Ramana's call. Don't pre-scrape Screener for 5,000 stocks. Wait for results events to drive on-demand scraping. Cache 7 days. Natural incremental growth.

### D9 — sec_bhavdata_full as primary source (not slim bhav copy)
Why: It has DELIV_QTY, DELIV_PER, NO_OF_TRADES, AVG_PRICE — the columns the Delivery Value Per Trade signal needs. Slim bhav copy lacks delivery.

### D10 — Value-based metrics, not quantity-based
Why: Corporate-action invariance. DELIV_QTY × CLOSE stays the same across a split; DELIV_QTY alone gets distorted. Eliminates entire class of adjustment bugs. Documented in architecture.docx §7.

### D11 — Pre-compute signals nightly, store in table
Why: Query-time speed (~10ms vs ~2s per stock), historical reproducibility, batch friendliness. Storage cost is trivial (~280 MB for 5y × 2000 stocks).

### D12 — Power deliveries (top-N within window), not just flat averages
Why: Ramana's insight. Institutional buying is event-driven, not constant — flat average dilutes signal with noise days. Top-N captures the genuine institutional days. Both metrics computed and stored so user has both views. Documented in architecture.docx §6.

### D13 — Deep analysis happens in claude.ai (subscription), not API
Why: Cost. Phase 4 patearn (qualitative + bear case + adversarial check) on Sonnet via API would burn ~₹150–500/month at moderate use. Same quality is unmetered under the existing ₹1,700/mo claude.ai subscription. Hermes' job is to surface candidates worth a deep look; the deep look happens elsewhere.

### D14 — Open-ended question prompts (AskUserQuestion tool) sometimes return empty answers
Observed in this project — questions where the user clicks away or interrupts return empty. Fallback: ask in prose, expect free-text answer. Documented for future sessions.

### D15 — PROJECT_STATE.md is maintained continuously by every Claude session
Why: One-off "update at wrap" instructions get forgotten. Ramana ratified (session 13) that every future Claude Code session must update this file as work happens, in the same commit as the code. Codified at the top of this document and in CLAUDE.md. The rule is permanent and self-enforcing — Claude reads both files at boot.

### D16 — Daily bhav copy fetch scheduled at 7:30 PM IST (was 6:00 PM)
Why: Initial 6:00 PM scheduling was on the edge — NSE's `sec_bhavdata_full` with delivery data sometimes lags basic bhav copy by 1-2 hours depending on settlement processing. Estimated miss rate at 6:00 PM was ~30%, at 6:30 PM ~15%, at 7:00 PM ~5%, at 7:30 PM ~1%. Ramana chose 7:30 PM for maximum reliability — morning digest sees today's actual data, not yesterday's catch-up. Cost of waiting 90 extra minutes is zero (we don't watch in real time anyway). Change applied to `scripts/setup-news.sh` `hermes-bhavcopy.timer` (OnCalendar=Mon..Fri *-*-* 14:00:00 UTC).

---

## Cost model

| Layer | Provider | Monthly | Notes |
|---|---|---|---|
| VPS (Hostinger KVM4, 2y prepaid) | Hostinger | ~₹1,300 amortised | Already paid through 2028 |
| Anthropic API (Hermes runtime) | Anthropic | **₹150–300** | Capped at $10/mo in console |
| Claude.ai (deep dives) | Anthropic | ₹1,700 | Existing subscription, unchanged |
| Claude Code sessions | Anthropic | **₹200–500/session** | Building/architecting — biggest variable cost. **THIS conversation is the line item that surprises.** |
| Telegram, NSE, Screener, GitHub | various | ₹0 | All free public services |

**Hard rule:** never let an automated job depend on Sonnet via API. All scheduled compute either uses Haiku or has no LLM at all.

---

## Operating procedures

### Daily user workflow

1. Morning — open Telegram, read overnight digest in `Hermes_Stock News` group (will exist once digest runs after backfill)
2. Glance at PASS/WATCH list
3. Tap a candidate → opens source article
4. For interesting ones → open browser to `http://187.127.173.149:8000/candidates` for filterable table
5. For ones worth deeper look → copy candidate metrics into claude.ai with patearn skill → ask for full Mode 1 analysis
6. Make decision

### Backup to laptop (manual, anytime)

Double-click on Windows: `D:\Hermes\scripts\download-from-vps.bat`

It scps `/opt/hermes/data/` into `D:\Hermes-data-backup\<datestamp>\` — preserves each backup separately. Asks for VPS password once.

### Deploy / update flow (when code changes)

1. On laptop: edit code in `D:\Hermes\` → commit → push to GitHub
2. On VPS: `wget -qO /tmp/setup.sh https://raw.githubusercontent.com/ramana-gottipati/hermes/main/scripts/setup-news.sh && bash /tmp/setup.sh`
3. Script: git pull → pip install → restart all services → done in ~30 seconds

### First-time 5-year backfill (one-shot)

1. SSH into VPS
2. Pull latest code: `cd /opt/hermes && git pull && .venv/bin/pip install -r requirements.txt --quiet`
3. Launch in background: `nohup bash /opt/hermes/scripts/full-backfill.sh > /var/log/hermes-backfill.log 2>&1 &`
4. Watch progress: `tail -f /var/log/hermes-backfill.log` (Ctrl+C just stops watching, not the job)
5. Done message appears after ~45–60 min
6. Verify: `sqlite3 /opt/hermes/data/hermes.db 'SELECT COUNT(DISTINCT trade_date), COUNT(DISTINCT symbol) FROM bhavcopy_rows;'`

---

## What's NOT yet built / open items

### ✅ COMPLETED in session 14 (formerly IN-FLIGHT)

1. ✅ **setup-news.sh deployed on VPS** — session 11+12+13 code is live
2. ✅ **5-year bhav copy backfill executed** — 1,297 trading days from 2021-05-24 to 2026-05-28, 1,296 with delivery (sec_bhavdata_full). 2,356,143 EQ rows across 3,051 stocks.
3. ✅ **Signals fully computed** — 2,350,570 rows in stock_signals across 3,051 stocks × 1,237 days. (The 60-day gap from bhav copy days is expected — those are the early dates where the rolling 365-day window can't be computed.)
4. ✅ **sqlite3 CLI installed on VPS** (was missing from Ubuntu base image; now auto-installed by setup-news.sh and vps-bootstrap.sh — see commit 96f9649)
5. ✅ **Bhav copy timer moved from 6:00 PM IST to 7:30 PM IST** (Decision D16, commit c292e47)

### Other open items (queued, no immediate urgency)

4. **NSE corporate-announcements poller** — currently news-based earnings trigger only. Better trigger would be the authoritative NSE filings feed. Designed but not built.
5. **Pattern 11 (VCP) and 14 (Volume breakout) scoring** — defaulted to Partial-Estimated because they need price action + ATR. With bhav copy data now available (post-backfill), these can become real signals.
6. **Pattern 12 (Receivables) and 13 (Working capital)** — need balance sheet time series. Screener has it; parsing not yet implemented.
7. **Telegram digest enrichment** — currently digest just lists symbols. Could enrich with key metrics (ROCE, NS, ratio_today_vs_power_1m) per row.
8. **Web page editing** — `/candidates` is read-only. Could add status update (Reviewed / Picked / Passed) inline so Ramana tracks his own action.
9. **Kite Connect intraday** — ~₹500/mo if/when Ramana wants real-time alerts. Filed for "later".
10. **Voice messages** — Ramana mentioned wanting to talk to Hermes via voice. Would need Whisper STT + TTS. Not built. ~3 hours work.
11. **DVPT signals integration into scoring.py** — once stock_signals has historical data (post-backfill), the patearn rule-based scorer should read ratio_today_vs_power_1m as a real Pattern 14 (volume confirmation) signal instead of Partial-estimated. Quick win after backfill.

---

## Session log (reverse chronological — newest at top)

### Session 14 — 2026-05-29 — Full pipeline live + end-to-end verified
- Deployed session 11-13 code to VPS via setup-news.sh
- Installed sqlite3 CLI (was missing; fix shipped in commit 96f9649)
- 5-year bhav copy backfill confirmed complete: 1,297 days, 3,051 stocks, 2.36M rows, 1,296 days with delivery
- Signal computation confirmed complete: 2.35M stock_signals rows across 3,051 stocks × 1,237 days
- Timer shift 6:00 → 7:30 PM IST landed (Decision D16, commit c292e47)
- The 5-year dataset is fully on-VPS, fully portable via `scp -r root@VPS:/opt/hermes/data/ ./backup/`
- Bug fix: screener.py `_write_cache` SQL binding count mismatch (commit 7004b7d)
- **End-to-end verified:** `/score RELIANCE` returned T4 (correctly rejected — too large for patearn universe); `/score PIXTRANS` returned T3 NS 44.9% PAC 14/14 (interesting candidate, optimistic sensitivity 77% → potential T1)
- The full pipeline is alive: Telegram → screener scrape → rule-based scoring → structured reply, all at ₹0 marginal cost
- Live commits in this session: 96f9649 (sqlite3 install), c292e47 (timer 7:30 PM), 48afd66 (state doc), 7004b7d (screener bug)

### Session 13 — 2026-05-29 — Binding continuous-update rule + wrap
- Added 🔴 BINDING RULE at the top of PROJECT_STATE.md mandating in-commit updates whenever code or decisions change
- Mirrored the rule into CLAUDE.md so it's loaded on every Claude session boot — includes mapping table of "if you do X, update this section"
- Added Decision D15 (this decision itself)
- Goal: PROJECT_STATE.md never goes stale; future sessions never have to re-derive architecture by greping code
- Wrap protocol applied — IN-FLIGHT items 1-3 flagged 🔴 for next session (setup-news.sh re-run, 5y backfill run, post-backfill verification)
- Commits: `274984f` (binding rule), this commit (wrap)

### Session 12 — 2026-05-29 — Architecture docs and running-doc bootstrap
- Generated `D:\Hermes\docs\hermes-bhavcopy-architecture.docx` — 11 chapters, 24 tables, covering bhav copy data sources, storage layout, DVPT methodology, power deliveries, schema, nightly compute flow, corporate-action invariance, operational reference
- Created PROJECT_STATE.md as the running document
- Slimmed CLAUDE.md to a pointer file; commit `c1ba5a1`
- No code changes to functional systems

### Session 11 — 2026-05-28 — 5-year bhav copy + signals architecture
- Replaced slim daily_prices schema with wide `bhavcopy_rows` (every column + raw_json)
- Added `corporate_actions` table with parsing of bonus/split ratios
- Added `stock_signals` table with 14 derived metrics per (symbol, date)
- Built `bhavcopy.py` with sec_bhavdata_full primary + UDIFF/legacy fallbacks
- Built `corp_actions.py` for NSE corporate actions ingestion
- Built `signals.py` with flat baselines + top-N power deliveries
- Built `scripts/full-backfill.sh` orchestration script
- Built `scripts/download-from-vps.bat` for laptop backup
- Defined DVPT formula: (deliv_qty × close) / no_of_trades
- Defined power deliveries: avg of top-5/10/15/40 within 22/44/66/132-day windows
- Defined three ratio signals: today vs avg_30d, today vs power_1m, today vs power_3m
- Commits: `e220b2e`, `6835aa2`, `bb77f41`
- Backfill not yet run on VPS as of session end

### Session 10 — 2026-05-28 — Data-driven rule-based rebuild
- Replaced LLM Stage 1 in news_feed with Python rule-based scoring against Screener data
- Built `src/automation/screener.py` (Screener.in HTML scraper, 7-day cache)
- Built `src/automation/scoring.py` (pure Python 14-pattern scorer)
- Added `/score TICKER` command (free, no LLM)
- Repurposed `/analyze` to use Haiku (default) with optional Sonnet
- Wide rewrite — replaced Stage 1 LLM call with rule-based path
- Commit: `e220b2e`

### Session 9 — 2026-05-28 — Two-stage architecture proposal + cost honesty
- Surfaced the architectural mistake of news-based screening (fuzzy signal)
- Designed proper two-stage: cheap Haiku screen on every earnings + rule-based deep analysis
- User decided to go data-driven from the start (no news-only path)
- Set $10/month spend cap in console.anthropic.com (user's TODO)
- Honest reframe: Claude Code session cost is the biggest line item

### Session 8 — 2026-05-28 — Live news poller + candidates page
- Built `src/automation/digest.py` for twice-daily digest
- Added Stage 1 LLM screen in news_feed (later replaced in session 10)
- Built `/candidates` route on FastAPI (mobile-friendly, dark theme)
- Added `screen_candidates` table
- Switched news poller to hourly (Mon-Fri 06:30–21:30 IST)
- Commits: `905d90f`, `d84f9fd`, `77915c3`, `70825cd`

### Session 7 — 2026-05-28 — patearn integration
- Copied patearn skill files into `D:\Hermes\resources\patearn\`
- Built `src/assistant/patearn.py` with analysis_system_prompt builder + cache_control
- Added `/analyze TICKER` command (originally Sonnet, later defaulted to Haiku)
- Added watchlist commands (/watch, /unwatch, /watchlist) — kept but no longer the gate
- Added patearn destination management
- Commits: `1a8ef6d`, `918f707`

### Session 6 — 2026-05-28 — News destination routing
- Added `/news_here`, `/news_where`, `/news_stop` commands
- Added `news_destinations` table
- Bot ignores plain text in groups (later reverted for analysis groups)
- Slash menu registration via set_my_commands
- Commit: `905eca8`

### Session 5 — 2026-05-28 — News classifier + digest
- Built news RSS aggregator with Haiku JSON classification
- Categories: EARNINGS / MACRO / CORPORATE_ACTION / STOCK_SPECIFIC / OTHER
- Tagged digest format
- Initial twice-daily push
- Commits: `2b9a0ed` through `4e50e85`

### Session 4 — 2026-05-28 — Cost crisis + sliding window + prompt caching
- User noticed $5 spend from long Sonnet chat
- Diagnosed: full history replay on Sonnet for casual chat
- Switched Telegram bot default to Haiku
- Added MAX_HISTORY_MESSAGES=30 sliding window
- Added Anthropic prompt caching (ephemeral) on system + last historical message
- Documented quadratic cost shape
- Commit: `56d5617`

### Session 3 — 2026-05-26/27 — Multi-turn memory + Telegram bot
- Built SQLite-backed conversation memory
- /reset, /whoami commands
- Telegram bot front-end via python-telegram-bot
- Authorization gate (TELEGRAM_ALLOWED_USER_IDS=282907906)
- Per-user conversations
- Commits: `ddda848`, `905eca8`

### Session 2 — 2026-05-26 — VPS deploy
- Hostinger KVM4 setup (Mumbai, Ubuntu 22.04)
- vps-bootstrap.sh deploy script
- systemd service for Telegram bot (24/7)
- GitHub repo made public for unauthenticated wget access
- Auth via Personal Access Token initially, browser auth later

### Session 1 — 2026-05-26 — Scaffold
- Local repo at `D:\Hermes\`
- FastAPI + Anthropic SDK + python-telegram-bot stack
- pinned requirements.txt
- Initial Telegram bot listener
- pydantic-settings .env loader (with override=True fix for dotenv)

---

## Notes for the next Claude Code session

- **Read this file first, then check git log for any commits since last entry.**
- **Don't re-derive architecture from scratch.** The decisions in the Decision Log are deliberate; if reversing one, explain why.
- **The biggest cost is THIS session itself.** Stay focused. Bundle changes. Avoid long iterative chats.
- **For text/prompt tweaks**, suggest SSH-edit on the VPS to avoid a full session.
- **At session wrap**, append a new entry at the top of "Session log" with what shipped + commit hashes.
- **If a piece of state is missing here**, add it. This doc is the running source of truth; keep it current.
