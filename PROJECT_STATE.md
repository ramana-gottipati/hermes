# Hermes — Project State

> **Last updated:** 2026-06-19 (session 19 — the two session-18 P0 `/dash/compare` chart bugs are FIXED, D49g; deep-history foundation still building on the VPS). **⚡ READ § Session log → "Session 18 — WRAP" FIRST.** **Project rebranding Hermes → Patearn** (patearn.in; "Hermes" now = the Nous agent only — D34). **The deep-history data foundation (D47 — MTO⋈legacy delivery → DVPT to ~2004) is BUILDING AUTONOMOUSLY on the VPS at wrap:** Stage-1 backfill (pid 133884, log `/var/log/hermes-deepbackfill.log`) → orchestrator `scripts/deep-foundation.sh` (pid 134151, log `/var/log/hermes-foundation.log`) → Stage-2 full recompute; a local watcher re-invokes the session when done. **The DVPT picking-strategy program is the throughline — full design in `docs/dvpt-picking-strategy-design.md` + `docs/multi-timeframe-positioning-design.md` (kept rich; binding doc-persistence rule — do NOT one-line).** Also shipped: **D48** dashboard enrichment (CMP·Δday·DVPT·**×power**·Deliv₹ on boards/screen; stock-page traded+delivery pane + RS-overlay chart w/ D/W/M/Q) + **SQLite WAL** perf (3–7s → 0.03–0.12s). **NEXT SESSION: ① verify the foundation finished + record coverage; ② build the MTF signal engine → ③ ignition+ranking → ④ backtest → ⑤ ML.** ⚠ Two Claude sessions shared one working tree today (git-add cross-absorption — caught, nothing lost) → next session be the sole one or use a worktree. — Earlier this session: **D46** bounded/prioritized batch **pt14 scoring** (`score_batch.py`) lights up the Quality pillar for surfaced names — honors D8 (over-time, not bulk); daily `hermes-pt14batch` timer; closes B6. Built right after **D45** cross-pillar **CONVICTION shortlist**: the synthesis where all 3 pillars align (RS leader + D43 accumulating + D44 entry + pt14 quality), read-only via `stock_rs.conviction_shortlist` → **`/dash/conviction`** + a ⭐ Home preview + `/conviction`. Built this session on **D43** DVPT accumulation/distribution **CHARACTER** (3-axis → `accum_character`) and **D44** value-weighted institutional **KEY PRICE** + near-key entry + ticket/surge + **`/dash/workbench`** (both additive, zero regression). D44 refines D31's flat `avg_close_p*` zones — the big institutional day now dominates the value-weighted cost line. Prior: session 17 — D33b/D33c (RS pillar COMPLETE) + **D41** strategy-surface Phase 1; **D42** equity-only scanners. Built on the session-16 D33a/D38/D39/D40 base.)
> **Running document.** This is the source of truth for the next Claude Code session.
> **⚠ Session-16 WRAP (read § Session log → "Session 16 — WRAP" first):** A very large session. P0 operational mess fully cleared (git identity → `Ramana Gottipati <gottipati.ramana@gmail.com>` repo-local; everything pushed; VPS reconciled). Shipped: **D38** macro→micro dashboard + index membership · **D39** RS ratio-analysis (multi-TF heat strip, `/dash/ratio`, `/dash/rs`) · **D40** `/dash/compare` rebase chart + chart range-switch perf fix · **D33a** stock-vs-broad RS + 1–99 rank (backfilled 2.37M rows). Plus on-page RS reconciliation table, chart hover-readouts, and a data-grid toolbar (sort/filter/Excel-CSV export) on the query tables. **HEAD = origin/main = VPS = `0adcf5d`, clean** (only the long-dormant uncommitted `patearn.py` diff remains — leave it). Telegram bot still network-blocked (waiting). **D33b + D33c shipped (session 17)** — stock-vs-sector RS + composite leaders/laggards (`/dash/leaders` board + Home preview; `/rs` `/leaders` `/laggards` commands); the third RS pillar is COMPLETE and `stock_rs` is wired into the nightly chain. **D41 Phase 1 shipped (session 17):** strategy badges on every board + a Strategies hub on Home + sector rotation curated to real sectors (factor/IPO indices no longer dead-end) + a Daily/Weekly/Monthly DVPT-trigger toggle (weekly/monthly roll up the last 5/22 trading days so a mid-week spike isn't missed). **Next:** D41 Phase 2 (materialised `weekly_signals` + add real missing sectors to membership), Phase 3 (saved-screener/query-builder + Conviction shortlist); then B5 (zones-on-adjusted-price), B6 (pt14 caching), Telegram unblock.

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

## 🧭 DOCTRINE — Read this before proposing architectural changes

These are the binding principles of the project. Every decision below has a WHY. If you (next session) want to overturn one, do it with a full reasoning rebuttal — NEVER silently. Hard rules without reasons are useless; here are the reasons.

### A. Cost-routing doctrine (Why what runs where)

Hermes uses four distinct compute paths. Each has a cost profile and use case. Defend the choice; don't drift.

| Path | Provider | Cost per call | Used for | Why this and not something else |
|---|---|---|---|---|
| **Anthropic Sonnet via API** | Anthropic | ~₹5-10 | **NOTHING**. Banned for routine use. | claude.ai under existing $20/mo subscription gives unlimited Sonnet 4.6 access. API duplicates this. Saves ~₹150-1000/month depending on volume. |
| **Anthropic Haiku via API** | Anthropic | ~₹0.20 | Telegram conversational chat only | Quality of voice / instruction-following in conversation is noticeably better than Gemini Flash. Volume is low (most messages route to data commands, not chat). Cost is bounded. |
| **Gemini Flash via API** | Google | ~₹0.008 | All classifier tasks (intent routing, news classification) | ~13× cheaper than Haiku at near-equal quality for JSON classification. Auto-fallback to Haiku if Gemini fails. Saves ~₹150/month at current volume, scales with usage. |
| **No LLM (pure Python/SQL)** | — | ₹0 | All deterministic logic: patearn scoring, DVPT signals, SQL queries | Rule-based logic for reproducibility and zero marginal cost. The framework is mostly mechanical; LLM doesn't add value to math. |
| **claude.ai (subscription)** | Anthropic | ₹0 marginal | Deep qualitative analysis (Phase 4 patearn, narrative work, bull/bear cases) | Already paid via $20/mo subscription. Sonnet 4.6 quality, larger context window, interactive follow-ups in same thread. The 30-second cost of "paste output into claude.ai" is trivial compared to API spend. |

**If next session proposes Sonnet API integration**: ask "Can this be done via claude.ai workflow instead?" 99% of the time yes. Decision D13 + D22.

**If next session proposes Anthropic Haiku for classifiers**: ask "Is there a quality regression from Gemini Flash that justifies 13× cost?" Need usage data, not speculation. Decision D20.

**If next session proposes "let's switch chat to Gemini too"**: only if chat volume grows above ~100 messages/day AND user explicitly complains about cost. Current chat volume is low enough that cost saved isn't worth quality regression risk.

### B. Build philosophy (honest review, session 14)

Session 14 retrospective: **~30-40% of features built so far were over-engineered for actual usage**. Recurring failure modes I caught:

- Default reflex to build API integrations rather than recommend subscription workflows (`/analyze` was the egregious case — burned API ₹10/call for months duplicating what claude.ai does free under subscription)
- Adding features before existing ones are battle-tested
- Multiple-iteration architectures (live news poller → twice-daily → on-demand → live again → hourly → twice-daily) — should have observed usage first, decided once
- Building an architecture Word doc when PROJECT_STATE.md was sufficient

**Going-forward rules** (next session: please respect):

1. **Before building**, ask: "Is this a real bottleneck or a hypothetical one?" If hypothetical, defer.
2. **Before choosing API**, ask: "Can this be done in claude.ai under subscription?" 
3. **Before adding a command**, ask: "Will Ramana use this >once a week?" If no, don't add it.
4. **After 2 weeks of usage data**, review what's actually being used. Sunset the rest.
5. **A Claude Code session costs ~₹200-700.** The session itself is the biggest line item. Bundle changes. Avoid long iterative architecture chats. SSH-edit on VPS for text/threshold tweaks.

### C. Data layer philosophy

- All data on VPS in single portable SQLite file (`/opt/hermes/data/hermes.db`)
- Raw NSE archive preserved un-touched (audit trail; can re-parse if logic changes)
- Pre-compute nightly into `stock_signals`; query instantly at use-time (reproducibility + speed)
- **Value-based metrics (rupees, not share quantities)** for corporate-action invariance — DELIV_QTY × CLOSE is the canonical metric, not DELIV_QTY alone
- New analysis dimensions should be COLUMNS in `stock_signals` (computed nightly), not separate tables

### D. Sector adaptation — patearn for financials (NEW from session 14)

The patearn framework was designed primarily for non-financial companies. For HFCs/NBFCs/banks, several pattern thresholds need adaptation. **Without this adaptation, financials score misleadingly low.**

| Pattern | Standard reading | Financial-sector adaptation |
|---|---|---|
| 1. ROCE Trajectory | ROCE > 18% | Use RoE/RoA. HFCs typically 12-15% RoE = good. ROCE is suppressed by leverage by design. |
| 2. Operating Leverage | EPS CAGR > 2× Rev CAGR | NII (not Revenue) growth + PAT + cost-to-income trajectory |
| 5. Balance Sheet | D/E < 1.5× | HFC D/E always 6-8× by business design. Use GNPA <1.5%, CAR > 18%, ALM gap discipline instead. |
| 6. Promoter Conviction | High family-promoter holding | For PE-funded financials (Aavas, HomeFirst), evaluate strategic-stakeholder commitment (e.g., Cholamandalam's stake in Aavas) |
| 12. Receivables | Debtor days trend | Loan-book asset-quality trend (proxy via Pattern 5) |
| 13. Working Capital | Cycle improvement | ALM gap discipline (proxy via Pattern 5) |

**Whenever Hermes scores a financial-sector stock, note in the output:** *"Score uses sector-adapted thresholds (see Doctrine D)"*. Decision D24.

### E. Two-tier DVPT trigger system — IMPLEMENTED session 15 (supersedes D26 spec)

Session 14 spec (D26) had two structural flaws Ramana caught in session 15:
1. The SS/S/A/B rank used an *ordered* check ("must be `1m+2m+3m`, not 6m" = S) that silently downgraded valid 3-of-4 hits in other window combinations. Asymmetric, hidden assumption.
2. Only four power baselines (P1M/P2M/P3M/P6M). P12M was missing entirely. And R-tier (rolling averages) was computed nightly but never surfaced — only one ratio (`ratio_today_vs_power_1m`) reached the user, so building intensity below the institutional-peak bar was invisible.

The replacement design (D28) splits the signal into two tiers:

**R-tier — rolling averages (soft bars).** "Above the normal day." Calendar-day windows (D31 revision):
- R1M = flat avg of last 30 calendar days
- R2M = last 60
- R3M = last 90
- R6M = last 180
- R12M = last 360

**P-tier — power deliveries (hard bars).** "Above the institutional peak days." Calendar-day windows + selective top-N (D31 revision):
- P1M = avg of top 4 DVPT days in last 30 calendar days
- P2M = top 7 in last 60
- P3M = top 12 in last 90
- P6M = top 20 in last 180
- P12M = top 30 in last 360

**Companion price for every baseline (D31):** for each R/P baseline, also store `avg_close_*` — the average close price on the same days that fed the baseline. Lets us read "where institutions actually transacted" at every horizon, not just "how intense was activity." `/dvpt TICKER` renders this as the "Institutional price zones" section.

**Two scores per (symbol, day):**
- `r_score` (0–5) = count of R-baselines today's DVPT beats
- `p_score` (0–5) = count of P-baselines today's DVPT beats

**Rank — pure count from p_score (no hidden window ordering):**
| Rank | Condition |
|---|---|
| SS  | p_score = 5 (above ALL P-baselines) |
| S   | p_score = 4 |
| A   | p_score = 3 |
| B   | p_score = 2 |
| C   | p_score = 1 |
| —   | p_score = 0 |

**Near-break pointer.** For every row, identify the smallest P-baseline today does NOT beat (the closest "wall above"). Store as `next_p_above` (e.g. "P3M") + `gap_to_next_p_pct` (negative = below the wall). When a stock is within −10% of a P-line AND r_score ≥ 4, that's the breakout-imminent signal — the user's "action zone."

**Orthogonal flags (unchanged from D26):**
| Trigger | Condition |
|---|---|
| ⚡ ATH-DVPT | DVPT_today > MAX(DVPT) across the stock's full DB history |
| 🟢 Discount entry | close < hot-day avg × 0.97 |
| 🟡 At-cost | close within ±3% of hot-day avg |
| 🔴 Above-cost | close > hot-day avg × 1.03 |

**`/scan` sort:** `is_ath_dvpt DESC → p_score DESC → r_score DESC → discount-flag DESC → r1m DESC`.

**`/triggers` modes:**
- `/triggers` (default) → rank A or better (`p_score ≥ 3`), capped at 50 rows
- `/triggers ss` → SS only (`p_score = 5`)
- `/triggers near` → near-break: `next_p_above IS NOT NULL` AND `gap_to_next_p_pct > -10` AND `r_score ≥ 4`

This surfaces three real failure modes that the old single-ratio scheme hid: (a) any 3-of-5 P-hit regardless of which windows, (b) the R-tier "building intensity" rows that never crossed P yet, (c) the "kissing a P-line" rows about to break.

Decision D28 (supersedes D26 + D27).

**Character dimension (D43) — the trigger system is SIDE-BLIND on its own.** The R/P scores and rank tell you a strong hand is *active* and *how intense*, but delivery data can never tell you which **side** he was on — every delivered share was simultaneously bought and sold. A high p_score is equally consistent with accumulation (strong hand buying) and distribution (strong hand selling into a retail bid). So D43 layers a `accum_character` label (ACCUMULATION / DISTRIBUTION / CONSOLIDATION / NEUTRAL) on top of the trigger, derived from three INDEPENDENT axes that are never collapsed into one number: **WHO** (trade-count breadth: concentrated vs broadening + delivery-₹ trend + delivery %), **WHICH WAY** (the only direction-revealer — adjusted-price drift + value-weighted up/down delivery skew), **CONTEXT** (distance from the 52w high + p_score persistence). The numerics are stored raw; the label is derived (re-tunable via `--relabel-character`). A high-rank trigger that reads DISTRIBUTION (heavy delivery on down-days / price rolling over near highs while the crowd broadens) is a **warning**, not a buy. See Decision D43.

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
| **Market dashboard (PWA, HTTPS)** | **https://srv1704897.hstgr.cloud/dash** — installable; charts/inertia/insights/zones |
| **Nous Hermes Agent (separate product)** | **https://srv1704897.hstgr.cloud:9443** — Nous Portal login; NOT our system (see D34) |
| Ramana's Telegram user ID | 282907906 |
| Telegram news group | "Hermes_Stock News" (supergroup, chat_id `-1003852136413`) |
| Laptop → VPS shell | `ssh hermes` (passwordless; key + ~/.ssh/config). Deploy dashboard: `scp /d/Hermes/src/web/dashboard.py hermes:/opt/hermes/src/web/dashboard.py && ssh hermes 'systemctl restart hermes-api'` |

### Key file paths

**On Ramana's Windows laptop (D: drive):**
```
D:\Hermes\                                          ← local working copy of repo
├── CLAUDE.md                                       ← entry point for Claude Code sessions
├── PROJECT_STATE.md                                ← THIS FILE (running doc)
├── docs\
│   ├── hermes-bhavcopy-architecture.docx           ← architecture Word doc
│   ├── build-architecture-doc.js                   ← script that generates the docx
│   ├── rs-ratio-analysis-design.md                 ← D39/D40 spec: RS ratio analysis + compare chart
│   ├── dvpt-picking-strategy-design.md             ← D47+: the DVPT picking-strategy PROGRAM (ignition/ranking/backtest/ML, data plan §9, universe integrity §13) — KEEP RICH
│   └── multi-timeframe-positioning-design.md       ← MTF foundation spec (weekly/monthly resampled signals + timeframe-parameterized engine)
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
│       ├── scoring.py                              ← rule-based 14-pattern patearn scorer
│       ├── indexes.py                              ← NSE index OHLC ingestion (D32)
│       ├── index_signals.py                        ← index + ratio signals, sector-vs-broad RS (D32)
│       ├── membership.py                            ← NSE constituent lists → stock_index_membership (D33b)
│       ├── adjust.py                                ← reusable split/bonus back-adjustment (extracted from D36; used by stock_rs)
│       ├── stock_rs.py                              ← stock-vs-broad + stock-vs-sector RS + 1-99 rank + leaders/laggards → stock_signals (D33a/b/c)
│       ├── equity_list.py                           ← NSE EQUITY_L.csv → nse_equity_list allowlist (equity-only scanners, D42)
│       └── score_batch.py                           ← bounded/prioritized batch pt14 scoring (B6/D46; honors D8 — surfaced names only)
├── resources\patearn\                              ← copy of patearn skill files (used by patearn.py)
│   ├── SKILL.md
│   ├── patterns.md
│   ├── failures.md
│   └── exit-protocol.md
├── scripts\
│   ├── vps-bootstrap.sh                            ← initial VPS deploy script
│   ├── setup-news.sh                               ← incremental update (rerun for new features)
│   ├── full-backfill.sh                            ← 5-year bhav copy + signals backfill
│   ├── probe_data_reachability.py                  ← one-off: how far back NSE delivery/index/deals reach (session 18)
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
├── hermes-bhavcopy.service + .timer                ← 6 PM IST weekdays (after backfill is run)
└── hermes-pt14batch.service + .timer               ← daily — bounded batch pt14 scoring of surfaced names (B6/D46)

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
| Score one stock manually | In Telegram: `/pt14 RELIANCE` |
| Delivery flow signal | In Telegram: `/dvpt PIXTRANS` |
| Manual deep analysis | In claude.ai with patearn skill loaded — paste the /pt14 result |

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
| `/menu` | Open the inline-keyboard menu — pick a strategy without remembering commands (D29) | ₹0 |
| `/pt14 TICKER` | patearn 14-pattern rule-based score from Screener data (no LLM) | ₹0 |
| `/dvpt TICKER [days]` | Delivery Value Per Trade institutional-flow signal: today vs power baselines + history + institutional price zones + **🧭 Character block (D43)** + **📍 Key-price block (D44)** — value-weighted key price per horizon + signed gap + 🎯 near-key flag + ticket size + turnover surge | ₹0 |
| `/scan [N]` | Top N stocks across the market, ranked by D28 two-tier layered triggers (ATH → p_score → r_score → discount → r1m). Shows R/P scores, near-break pointer, entry marker, **Ch character glyph (D43)** | ₹0 |
| `/triggers [ss\|near\|accum\|distrib]` | Strict view. Default: rank A+. `ss` → SS only. `near` → kissing a P-line with r_score ≥ 4. **`accum` → ACCUMULATION + p_score≥3 + concentrated · `distrib` → DISTRIBUTION (D43)** | ₹0 |
| `/rs TICKER` | Stock relative strength — vs broad (Nifty 500) + 1–99 rank + vs its sector + leader/laggard verdict (D33) | ₹0 |
| `/leaders` | Top "strong-in-strong" stocks — stock + sector + market all trending up (D33c) | ₹0 |
| `/conviction` | ⭐ Cross-pillar Conviction shortlist — RS leader + institutions accumulating now + entry read, pt14 quality starred (D45) | ₹0 |
| `/laggards` | "Weak-in-weak" stocks — stock + sector + market all trending down (D33c) | ₹0 |
| `/provider` | Show which LLM provider is active for classifier tasks | ₹0 |
| `/analyze TICKER` | **Now just prints the claude.ai workflow guide** — no API call. Use claude.ai for deep dives under subscription. | ₹0 |
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

Plain text in DM or group → **natural-language intent routing** (Haiku ~₹0.10/msg classifier):
  - "what's pixtrans?" / "look at reliance" → runs BOTH score + flow
  - "score X" / "is X a good buy" → runs /pt14
  - "delivery flow on X" / "institutional buying in X" / "DVPT on X" → runs /dvpt
  - anything else → conversational chat with memory (existing path)
Plain text in group from non-authorized users: silently ignored.

### Web dashboard routes (FastAPI `src/web/dashboard.py`, served under `/dash*`)

Read-only, no LLM, pure SQL over existing tables. PWA-installable over HTTPS (Caddy). 5-tab macro→micro nav: Home · Markets · Sectors · Stocks · Stock (Compare is a destination reached with intent, not a nav tab — see D40).

| Route | What it does | Decision |
|---|---|---|
| `/dash` | Home — regime banner, **Strategies hub (3 pillar cards w/ live counts, D41)**, KPIs, top sectors by 3m RS (real-sector curated), strong-in-strong leaders preview, top trigger stocks (now w/ Character pill), **Stealth-accumulation board (D43)** = concentrated ACCUMULATION still off the highs; every board carries a strategy thesis badge | D38/D41/D43 |
| `/dash/markets` | Major indexes & sectors (curated accent cards) pinned above the full ~150-index bundle (All/Broad/Sectoral filter); card → constituents | D38 |
| `/dash/sectors` | Sector RS-rotation leaderboard (D32 trend_state), strongest first; **curated to real economic sectors (D41)** — factor/thematic indices excluded; row → its stocks; 1m/3m/6m/12m heat strip | D32/D38/D39/D41 |
| `/dash/rs` | Cross-sector RS-momentum ranking (on-read window fn; `0.6·slope_3m + 0.4·slope_6m`); real-sector curated (D41) | D39/D41 |
| `/dash/stocks?period=d\|w\|m` | Stock hub — search + layered-DVPT screen + filter pills (SS/A+/⚡ATH/🟢Discount/🔥Near-break + **🟢Accumulation/🔴Distribution, D43** + **🎯Near-key-price, D44**) + watchlist + `?sector=` filter + **Workbench ⇄ link (D44)**. Daily table carries **Character** + **Total delivery ₹Cr** columns (D43). **D41: Daily/Weekly/Monthly toggle** — w/m roll up the last 5/22 trading days (days-fired + peak rank + latest-day character, on-read); factor-index `?sector=` shows a graceful "see ratio chart" empty-state | D38/D41/D43/D44 |
| **`/dash/workbench?limit=`** | **D44 — every signal on one wide, sortable, downloadable table** for the latest day (liquid equity universe): symbol · close · DVPT · rank · r/p · character · `key_price_p{3m,6m,12m}` + `gap_to_key` (near-key cells highlighted) · power/avg_close ref · ticket size · turnover surge · total delivery ₹. Reuses the `_DT_JS` data-grid toolbar (click-sort / filter / Export-to-CSV). Reached via the Workbench link from `/dash/stocks`; `active="stocks"` (NOT a 6th nav tab, per D40-A) | D44 |
| `/dash/leaders` | Composite "strong-in-strong" leaders + "weak-in-weak" laggards — stock RS vs sector AND vs broad AND the sector's own RS vs broad all aligned; sortable boards; previewed on Home | D33c |
| **`/dash/conviction?limit=`** | **D45 — the cross-pillar Conviction shortlist:** names where ALL 3 pillars align — RS leader (D33c) + institutions accumulating now (D43 `accum_character='ACCUMULATION'`) + the D44 entry read (🎯 near-key / discount), with pt14 quality as a ★ confirmation. Sortable/filterable/exportable `.dt` table + 🎯/★ filter pills; previewed by a ⭐ board on Home (after the Strategies hub). Read-only synthesis (no schema). `active="stocks"` | D45 |
| `/dash/stock?sym=X` | Per-stock — adjusted candle + DVPT/delivery charts, DVPT inertia vs every baseline, D31 institutional price zones, **D43 Accumulation-character panel** (label + plain-English read + up/down delivery bar + WHO row + 52w-high distance + ⚠️ distribution-while-high warning), **D44 Institutional key-price section** (value-weighted key per horizon + signed gap + 🎯 launch-band read + ticket/surge, beside the flat zones), pt14 snapshot, RS vs broad+sector, auto-READ | D33-web/D36/D43/D44 |
| `/dash/ratio?idx=&den=` | Per-index ONE-STOP view (D49): **today snapshot** (close/OHLC/Δday/volume/turnover/PE/PB/divyield + returns 1d–12m + 50/200-DMA + 52w pos) + RS ratio chart (ratio + 50/200-MA + cross/new-RS-high markers + range + vs-50/500) + RS-momentum gauge + abs×rel quadrant + auto-READ + **constituents table** (DVPT trigger **+ CMP/Δday + RS rank + 3m + vs-index excess**, all-constituents, sortable/filterable/CSV `.dt`) | D39/D49 |
| **`/dash/compare?idx=…&den=&mode=&r=`** | **Overlay up to `_COMPARE_MAX` (now 12) indices on one chart, each indexed to 100 at a fluid common anchor → read who outperformed.** Modes **Rebased** / **Ratio** (the Base 100/0% toggle is REMOVED — D49c: always base-100, matching the stock RS overlay; 12-color palette + golden-angle HSL overflow, so the cap is a soft readability limit, not technical). Chip-rail picker (chips = legend, multi-select Add, D49b) + presets. Entry points: `/dash/ratio` fbar (**seeds sector + Nifty 50 + Nifty 500 by default**, removable, D49b) + `/dash/markets` & `/dash/sectors` footers. Render-only, zero schema. | **D40/D49b/D49c** |
| `/dash/scan` | D28/D31 layered-triggers table (working orphan — kept, not in nav) | D33-web |
| `/dash/offline` · `/manifest.webmanifest` · `/sw.js` · `/icon.svg` | PWA shell — offline fallback, install manifest, network-first service worker, icon | D33-web |

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
- `stock_signals` — pre-computed nightly. Per (symbol, trade_date): delivery_value_today, total_value_today, delivery_value_per_trade. **R-tier (D31):** `avg_dvpt_1m/2m/3m/6m/12m` (flat avg DVPT over 30/60/90/180/360 **calendar** days). **P-tier (D31):** `power_dvpt_1m/2m/3m/6m/12m` (avg of top-N DVPT within window: 4/30d, 7/60d, 12/90d, 20/180d, 30/360d). **Price zones (D31):** `avg_close_r1m..r12m` (avg close over R-tier window) + `avg_close_p1m..p12m` (avg close on the same top-N DVPT days). **Scores:** `r_score`, `p_score` (0–5 each, count of baselines today's DVPT beats). **Rank:** `trigger_rank` (SS/S/A/B/C/'-' from p_score). **ATH + entry:** `is_ath_dvpt`, `hot_days_avg_price`, `price_vs_hot_avg_pct`. **Near-break:** `next_p_above` (closest P-wall above), `gap_to_next_p_pct`. **RS vs broad (D33a):** `rs_vs_broad_today` + `rs_vs_broad_slope_{1m,3m,6m,12m}` + `rs_vs_broad_above_50ma/above_200ma/new_52w_high/trend_state` (= adj_close ÷ Nifty 500, D32 vocabulary) + `rs_rank` (1–99 cross-stock percentile of blended RS momentum over the liquid universe). **RS vs sector (D33b):** `primary_sector` (the stock's narrowest NSE sectoral index) + `rs_vs_sector_today` + `rs_vs_sector_slope_{1m,3m,6m,12m}` + `rs_vs_sector_above_50ma/above_200ma/new_52w_high/trend_state` (= adj_close ÷ that sector index; NULL for stocks in no sectoral index). Populate via `python -m src.automation.stock_rs --backfill` (broad+rank+sector) or `--sector-backfill` (sector only). **Accumulation/distribution character (D43):** `deliv_value_ratio_1m_6m`, `trade_count_ratio_1m_6m`, `avg_deliv_pct_1m`, `avg_deliv_pct_6m`, `deliv_updown_ratio_3m`, `accum_price_drift_3m`, `pct_from_52w_high` (the 7 stored numerics) + derived `accum_character` (ACCUMULATION/DISTRIBUTION/CONSOLIDATION/NEUTRAL/NULL). Index `idx_signals_accum_character(trade_date, accum_character)`. Legacy trading-day cols (`avg_dvpt_5d/10d/30d/60d/90d/180d/365d`, three ratio cols) kept for /dvpt history table only. Backfill via `python -m src.automation.signals --backfill-triggers` — MANDATORY after D31 since old D28 values are wrong under new windowing; it now ALSO populates the D43 character fields. Re-derive only the label after a threshold tweak via `--relabel-character` (fast, no measure recompute). **Value-weighted key price + entry/ticket/surge (D44, additive):** `key_price_p{1m,2m,3m,6m,12m}` (Σ price·deliv-value ÷ Σ deliv-value over the top-N power days, priced at avg_price — the big institutional day dominates; `avg_close_p*` left untouched) + `gap_to_key_p{1m..12m}` (signed % of close vs key; near-key DERIVED on read via `_KEY_BAND=(-1,5)`) + `avg_trade_qty`, `avg_deliv_qty_per_trade` (ticket size = volume|deliv_qty ÷ num_trades) + `turnover_surge_{1m,3m,1y}` (today value ÷ rolling-avg value over 30/90/360 cal days). 15 columns, all additive. Populate via `python -m src.automation.signals --backfill-keyprice` (UPDATE-only, never rewrites D28/D31/D43 columns); nightly `compute_for_date` keeps them current.

- `nse_equity_list` (D42) — NSE `EQUITY_L.csv` equity universe (symbol PK, company_name, isin, listing_date, snapshot_date; ~2,374 rows). The **allowlist that keeps all scanners EQUITY-ONLY** — ETFs/MFs are not in it, and `sec_bhavdata_full` carries no ISIN so a symbol allowlist is the robust separator. Refreshed nightly by `equity_list.py`; replaced only on a successful, non-empty fetch (never wiped on failure). Scanner filters use `s.symbol IN (SELECT symbol FROM nse_equity_list)`.

**View:** `prices_eq` — filtered to EQ series + CM segment, exposes OHLC + delivery cleanly for downstream code.

---

## Decision log (the big ones)

### D49h — Stock RS-overlay chart: gutter name labels replicated + the SAME boot-anchor drift fixed (found while replicating D49g) — FIXED (session 19)

Replicated the D49g right-gutter name labels onto the D48 stock-page RS-overlay chart (`_RS_OVERLAY_JS` + its container): added the `#rsNames` 104px gutter, a `positionNames()` (value badge on the axis, line name just outside, de-collided ≥13px, "Nifty " stripped), and the bounded-rAF boot retry so labels survive the pre-layout `priceToCoordinate()` null.

While verifying hands-on I found the RS overlay had been **silently mis-anchoring all along** — contrary to the session-18 belief that it was the race-free "working reference." It rebased to a recent mid-window date (`2026-02-05`) instead of the full-series start (`2021-03-15`), so the lines didn't start at 100 on the left. SAME root cause as D49g, in two spots: (1) `reanchorToView()` read `getVisibleRange().from`, which lags a frame on first/off-screen layout (the overlay boots below the fold) → fixed by anchoring deterministically to `commonAnchor(null)` (the earliest point — valid because the overlay always `fitContent()`s the full series); (2) its `subscribeVisibleTimeRangeChange` handler then re-anchored on settle/relayout events → fixed with the same `userInteracted` gate as D49g (pan-reanchor responds only to real user input). Verified live on RELIANCE: anchor holds at `2021-03-15` across boot + scroll (no drift), values reflect growth from 100 (RELIANCE 129.8 / Oil & Gas 159.3 / Nifty 500 174.8), all three gutter labels render and de-collide. Additive — the D/W/M/Q toggle and pan-reanchor are unchanged.

### D49g — /dash/compare chart: deterministic left-edge rebase + gutter name labels (the session-18 P0) — FIXED (session 19)

Both long-standing P0 compare-chart bugs shared ONE root cause: the chart's boot logic acted before lightweight-charts had laid out its first paint. Debugged hands-on in the live browser via the Chrome MCP — the prior blind `py_compile` + route-200 loop is exactly why it stayed unresolved across D49d/e/f.

- **Left-edge rebase.** `setRange()` correctly anchored each line to the window's deterministic left edge (`allT[len-n]`, e.g. 1Y → `2025-06-11`), but a layout-settling `subscribeVisibleTimeRangeChange` fired AFTER `internalSet` was cleared and re-anchored every line to a transient mid-window date (reproduced: `2026-02-05`), so the lines no longer started at 100 at the visible left edge. **Fix:** the fluid pan-to-reanchor now responds ONLY to genuine user interaction — a `userInteracted` flag, set by `wheel/pointerdown/mousedown/touchstart` listeners on the chart host, gates `scheduleRebase()`. Settle-time (non-user) range-change events are inert; range buttons and the pin still anchor explicitly. This is deterministic — it does NOT depend on settle timing, which is why D49d's `getVisibleRange()` read and D49e's `internalSet` seed both failed. The `rightOffset:3` and short-series-`commonAnchor` theories were the wrong layer.
- **Right-gutter name labels (built D49f).** Silently empty on load because `positionNames()` ran before the price scale existed, so `series.priceToCoordinate()` returned null and every label was skipped — with nothing re-triggering it until a pan/resize. **Fix:** a bounded `requestAnimationFrame` retry at boot re-runs `positionNames()` until each visible line's label is placed.

Verified live against real VPS data: a fresh load (zero interaction) holds the correct anchor AND renders names; all four ranges anchor to their own left edge (Max→`2021-06-02`, 3M→`2026-03-16`, 6M→`2025-12-11`, 1Y→`2025-06-11`); adding a short/newer 4th series (Nifty India Defence) does not corrupt the anchor and its label still renders. Deployed via `scp` + `systemctl restart hermes-api`. Follow-up (optional): replicate the `userInteracted` gate to the D48 stock RS-overlay chart if it ever shows the same boot drift (it currently uses `fitContent()`, which sidesteps the race).

### D49 — Index page → one-stop view: today/OHLC snapshot + constituents get RS-vs-index (not just DVPT) — SHIPPED (session 18)
Why: Ramana asked, on `/dash/ratio?idx=...`, (a) to see the index's OWN today's movement (close/OHLC/day-change/valuation) — the page showed the RS picture but never queried the index's price row — and (b) for the "top constituents" to carry **relative strength vs the index** (which constituents are out/under-performing it), keeping DVPT, not replacing it. (Distinct from D48, which was the stock page + screen rows — different route, no overlap. Numbered D49 since the concurrent session took D48.)

**Shipped (render-only, no schema/backfill — all data already stored):**
- **Index one-stop snapshot** at the top of the page — from `index_rows`: today close + points/% change + OHLC + volume + turnover ₹Cr + P/E + P/B + div-yield; from `index_signals`: returns 1d/1w/1m/3m/6m/12m + %-vs-50/200-DMA + %-off-52w-high + %-above-52w-low. The "everything an analyst/data-engineer wants for this index" header, beside the existing RS chart/gauge/quadrant/READ.
- **Constituents — keep DVPT, ADD RS** — the table now carries, per constituent: CMP + Δday%, **RS rank (1–99)**, the stored **adjusted 3m return** (`accum_price_drift_3m`, D43 — split-correct), and **vs idx** = stock 3m return − the index's `ret_3m_pct` (positive = outperforming the index). Shows ALL constituents (was top-8), default-sorted by DVPT trigger, now a `.dt` table → click-sort by any column (DVPT / Δday / RS rank / vs-idx) + filter + CSV export.

Used the stored `accum_price_drift_3m` + `index_signals.ret_3m_pct` for the "vs index" excess (cheap, adjusted, no per-symbol fetch); `rs_rank` for market strength. DVPT stays primary and untouched.

### D48 — Dashboard enrichment (Positioning rows + stock-page charts) + SQLite WAL perf — SHIPPED (session 18)
Why: Ramana wanted the Home boards + screen to tell the full institutional story per row (not just rank/Δhot), the stock page to show traded-vs-delivery value + an RS-overlay chart at multiple timeframes, and flagged 3–7s click latency. **Screen-level only — no schema/pipeline change.**
Shipped (render-only + one perf pragma; commits `5e1314f`, `ff8581d`, `2bf4036`, all deployed + HTTP-200 verified):
- **Home "Top trigger stocks" + "Stealth accumulation" boards** and **`/dash/stocks`**: each row now shows **CMP · Δday · DVPT · ×power · Deliv ₹**. The **×power** = today's DVPT ÷ avg of its power baselines = *how hard it crossed* — the ranking-driving intensity, now visible (and sortable on the screen). Shared `_pos_cells` / `_intensity` / `_rupee` helpers.
- **`/dash/stock` — two new sections:** (1) a 4th synced pane — total **traded value** (bar) + **delivery value** overlaid on top (= delivered fraction of turnover; value-based RAW ₹, corp-action invariant); (2) **"Relative strength — overlay"** — stock vs narrow (`primary_sector`) index vs Nifty 500 (broad), rebased, with a **Daily/Weekly/Monthly/Quarterly** resample toggle (close-of-period, client-side, no refetch; reuses the `/dash/compare` rebase + `_COMPARE_PALETTE`). One added `index_rows` read.
- **SQLite WAL perf (`db._tune`):** `journal_mode=WAL` + `busy_timeout=5000` + `synchronous=NORMAL` + cache/mmap on every connection → readers no longer block on writes (nightly chain / backfills). Clicks **3–7s → 0.03–0.12s**. (`/dash/stock` still ~3.5s cold under the live backfill — profile post-backfill; it's the one heavy route WAL alone doesn't fully cover.)
- These are the chart-only halves of Ramana's stock-page asks; the *signal* halves (every strategy recomputed on weekly/monthly bars in identical logic) are deferred to the MTF foundation (see § NEXT BUILDS).

### D47 — Deep-history data foundation: pre-2020 delivery via MTO ⋈ legacy bhav (DVPT back to ~2005) — IN PROGRESS (session 18)
The DVPT picking-strategy program (calls from **Jan 2019** → a ranked 30–40-stock portfolio) needs delivery history far before our ~2021 floor — for the 12-month baselines AND "first-ever all-stars" detection. **Full design: `docs/dvpt-picking-strategy-design.md`** (+ `docs/multi-timeframe-positioning-design.md` for the weekly/monthly foundation); kept rich per the doc-persistence rule (design §14, user directive session 18) — read those for the complete intent.
- **Reachability probed (session 18, from the laptop):** `sec_bhavdata_full` (delivery) only **2020→present**; but the legacy **`MTO_DDMMYYYY.DAT`** delivery file ⋈ legacy **`cm*bhav.csv.zip`** (which carries close + num_trades + ISIN) reaches **≥2005**; indices ~2013; bulk/block `/api` returns 503 (needs a browser handshake). `scripts/probe_data_reachability.py` added.
- **Shipped:** `bhavcopy.py` MTO merge — `_mto_url` / `_parse_mto` / `_merge_mto` + an additive block in `ingest_date` that, for any no-delivery (pre-2020) date, fetches + archives the MTO file and fills `deliv_qty`/`deliv_per` on the legacy rows. **Additive — the 2020+ `sec_bhavdata_full` path and the schema are untouched.** Validated locally on 2015-02-13: **1507/1507 rows merged, 0 qty mismatches** (MTO traded-qty == bhav volume — a built-in join check), 20MICRONS DVPT=3139.8, ISIN captured. Pre-2020 has no `avg_price`, so the D44 key price uses close pre-2020 (consistent with our close-based DVPT).
- **Principles (binding):** **data window ≠ call window** — backfill deep (~2005) so a 2019 call has full lookback; calls from 2019. **Full-history recompute, not append** — once 2005–2020 lands, `is_ath_dvpt` + (future) first-ever-ignition must be recomputed across ALL years incl. the existing 2021–2026 rows (a recompute pass over D31/D43 signals + D44 keyprice + stock_rs across the extended range; RS only ≥2013 index floor); windowed baselines change only at the boundary.
- **Rebrand (phased, user-facing first):** **Hermes → Patearn** (patearn.in); "Hermes" now = the Nous agent only (D34). DVPT/RS/14-Pattern are strategies, not brands.
- **Next:** VPS deep backfill (bhav+MTO → ~2005) → full-history recompute → `security_master`/universe-integrity (survivorship/renames/demergers, design §13) → weekly/monthly foundation → ignition + intensity-ranking + ranking-history → absolute full-journey backtest → champion vs offline-ML challenger.

### D46 — Bounded, prioritized batch pt14 scoring (B6) — lights up the Quality pillar, HONORS D8 — SHIPPED (session 18)
Building D45 exposed that the Quality pillar is dark: the Conviction shortlist (and the stock-page pt14 card, and the hub's "scored" count) read cached `pattern_scores`/`fundamentals`, which only exist for stocks someone has manually `/pt14`'d — so both D45 conviction names showed `unscored`. B6 fixes that by keeping the SURFACED names scored.

**The D8 tension, and how this honors it (NOT overturns it):** D8 is a deliberate "Ramana's call" — *"don't pre-scrape Screener for 5,000 stocks; wait for results events; cache 7 days; natural incremental growth."* A naive "score all ~2,400 equities nightly" would violate it. So `src/automation/score_batch.py` is explicitly the opposite of bulk:
- **Prioritized** — only the surfaced universe (watchlist → recent news-driven `screen_candidates` → Conviction shortlist → RS leaders), capped at 300, NOT the full equity list.
- **Incremental** — skips any symbol already scored within the 7-day TTL; each run only does outstanding work, so coverage grows over days then just refreshes ("natural incremental growth", D8's exact words).
- **Bounded** — at most `--limit` (default 40) real Screener scrapes per run; the rest wait for the next run.
- **Throttled** — a polite `--throttle` (default 2.5s) sleep after each real scrape (anti-rate-limit / anti-block). Fresh-cached names are re-scored locally with no network.
- **No LLM** — reuses the existing rule-based `scoring.score_symbol` (Screener HTML parse + `score_fundamentals`); ₹0 marginal.

D8 stays the doctrine; D46 is its careful application to the small set the system actually surfaces. Scheduled via a daily `hermes-pt14batch` systemd timer on the VPS (runs after the signals chain). Closes open item B6. The Conviction shortlist's ★ quality-confirmed dimension (and the stock-page pt14 card) now populate for surfaced names.

### D45 — Cross-pillar CONVICTION shortlist (RS leader + accumulating + entry + quality) — SHIPPED (session 18)
The payoff that makes the three strategy pillars worth more together than apart. With RS (D33), Positioning character + key price (D43/D44) and Quality (pt14) all built, D45 is the SYNTHESIS — one decision-ready shortlist of names where every pillar aligns. (Realizes the "Conviction shortlist" half of D41's Phase-3 roadmap.)

**Alignment rule (`stock_rs.conviction_shortlist`, ONE shared read helper, DRY):** a name lands on the list only if —
- **RELATIVE STRENGTH** — it's an RS LEADER by the D33c 3-layer test (stock-vs-sector AND stock-vs-broad AND its sector's own RS-vs-broad all ∈ {UPTREND, BREAKOUT}); reuses `_LEADER_STATES` + the same join as `leaders_laggards`.
- **POSITIONING** — institutions are accumulating it now: `accum_character='ACCUMULATION'` (D43 — which already encodes p_score≥2 active).
- **QUALITY** — pt14 is surfaced as CONFIRMATION, not a gate (LEFT JOIN `pattern_scores` latest; pt14 coverage is sparse, so gating would empty the list — instead a ★ marks quality-confirmed names, ✗ flags hard-disqualified).
- **ENTRY (D44)** — each row carries the near-key / discount read so the user sees whether it's buyable now, not just "a good company going up."
Strongest leaders first (`rs_rank` DESC). Liquid equity universe only.

**Why read-only (no schema, no backfill):** it's a JOIN/filter over already-computed columns (the D33c join + D43 `accum_character` + D44 `gap_to_key_*` + `pattern_scores`), exactly like `leaders_laggards`. Computing on-read keeps it additive and zero-risk; if it ever needs to be a materialized "Conviction" column it can be later.

**Surfaced:** NEW **`/dash/conviction`** (sortable/filterable/exportable `.dt` table: symbol · RS rank · sector · character · entry · key price + gap · rank·p · pt14 quality; 🎯 near-key + ★ quality filter pills) + a **⭐ Conviction shortlist preview board on Home** (placed right after the Strategies hub — it's the headline) + the **`/conviction` Telegram command** (same shared helper). `active="stocks"` (nav stays at 5, per D40-A). Empty-state is honest ("conviction is rare").

### D44 — Value-weighted institutional KEY PRICE + multi-horizon near-key entry + ticket/surge + one-screen workbench — SHIPPED (session 18)
Borrowed the genuinely-better ideas from an external "Delivery Per Order Screener" functional spec, implemented **strictly additively** (the non-regression mandate below was the user's hard requirement).

**Why (the flaw it fixes):** the D31 institutional zone `avg_close_p*` averages the **close** on the top-N power-DVPT days with **equal weight** (`sum(closes)/len`). But the biggest institutional day should DOMINATE the cost line, and the day's **avg_price** (not close) is where shares actually changed hands. So the flat zone can sit well away from where the size really transacted.

**What shipped (4 additive components, 15 new `stock_signals` columns):**
- **① Value-weighted key price** — `key_price_p{1m,2m,3m,6m,12m}` = Σ(price·w)/Σ(w) over the SAME top-N power-DVPT days `p_stats` already selects, where `price=avg_price` (fallback close) and `w=deliv_qty·price` (delivered value). The big day dominates; verified the value-weighting pulls the key BELOW the equal-weight avg when the biggest power day was the cheapest. **`avg_close_p*` left byte-identical** (kept for the reconciliation/history view).
- **② Asymmetric multi-horizon entry** — `gap_to_key_p{label}` = signed % of today's close vs each key (− below cost, + above). **near-key is DERIVED on read** (band `_KEY_BAND=(-1.0, 5.0)` — price at/just-above the institutional cost, not far below: close ∈ [key−1%, key+5%]). Independent of, and coexists with, the DVPT near-break (`next_p_above`/`gap_to_next_p_pct`).
- **③ Ticket size** — `avg_trade_qty` = volume/num_trades, `avg_deliv_qty_per_trade` = deliv_qty/num_trades (a cleaner direct ticket-size read than the D43 trade-count ratio).
- **④ Activity surge** — `turnover_surge_{1m,3m,1y}` = today value ÷ avg(value over the prior 30/90/360-cal-day window). A liquidity/attention filter complementary to DVPT.

**Non-regression mandate (honored):** every field is a NEW `_ensure_column`; the new compute is a SEPARATE block in the per-symbol pass that reuses the already-fetched window rows but alters no existing calc; a SEPARATE `--backfill-keyprice` (UPDATE-only on the 15 columns — never re-runs `--backfill-triggers`, which would needlessly rewrite established D28/D31/D43 values). Regression gate run on the VPS before shipping: snapshot existing columns for sample symbols, run the new backfill, assert existing columns unchanged (diff=0) and only the new columns populated.

**Store-raw/derive-flag (Doctrine C):** store the gaps; derive the near-key band on read so re-tuning `_KEY_BAND` needs no backfill. No LLM; value-based; calendar-day windows reuse `signals._WINDOWS`.

**Surfaced:** `/dash/stock` gets an "Institutional key price (value-weighted)" section beside the existing flat zones (key per horizon + signed gap + 🎯 launch-band read + ticket/surge); `/dash/stocks` gets a **🎯 Near key price** filter pill (existing screen + 🟢/🟡/🔴 marker unchanged) and a **Workbench ⇄** link; NEW **`/dash/workbench`** = the spec's "everything on one screen" — a wide read-only table (symbol · close · DVPT · rank · r/p · character · key_price_p* + gap_to_key_p* near-key-highlighted · power/avg_close ref · ticket · surge · total delivery ₹) reusing the existing `_DT_JS` toolbar (click-sort/filter/Export-CSV), `active="stocks"` (nav stays at 5 per D40-A). Telegram `/dvpt` gets a "📍 Key price (value-weighted)" block. Parked for later (open items): fiscal-quarter/week-number grain, query alerts, EWMA key-price variant.

### D43 — DVPT accumulation/distribution CHARACTER (Positioning pillar, item 1) — SHIPPED (session 18)
> Numbering note: the session kickstart called this "D42"; D42 was already taken by the equity-allowlist work (below), so this deepening of the Positioning signal is **D43**.

**The core principle — delivery data is SIDE-BLIND.** Every delivered share was simultaneously bought AND sold, so DVPT / delivery value / delivery % reveal the *size and ownership-intent of who transacted* — NEVER which side initiated. "High DVPT" means a strong hand was on **one** side of the tape; it does NOT say whether he was the buyer (accumulation) or the seller unloading into demand (distribution) — those wear nearly the same delivery signature. Only **price** reveals direction, and **trade-count breadth + trend location** separate strong-hand accumulation from strong-hands-distributing-to-retail. Hence **three independent axes — never collapsed into one number**:

| Axis | Answers | Stored fields |
|---|---|---|
| **WHO** | strong hands or retail crowd? | `deliv_value_ratio_1m_6m` (delivery ₹ picking up?), `trade_count_ratio_1m_6m` (≥1.3 broadening/retail · ≤1.1 concentrated/few-hands), `avg_deliv_pct_1m`/`_6m` |
| **WHICH WAY** | buyers or sellers initiating? | `deliv_updown_ratio_3m` (Σ delivery ₹ on up-days ÷ on down-days, 90d, on ADJUSTED closes), `accum_price_drift_3m` (the only direction-revealer) |
| **CONTEXT** | campaign vs one-off, where in the trend? | `pct_from_52w_high`, plus existing `p_score` persistence |

Key tell: **concentration** (high DVPT, contained trade count, price firm) = accumulating; **broadening** (rising trade count, falling avg ticket, high total delivery, price stalling near highs) = distributing into a retail crowd. Avg-ticket trend = `deliv_value_ratio ÷ trade_count_ratio` (derived on read, no column).

**Store the raw, derive the flag (Doctrine C).** The 7 numerics are stored; the `accum_character` label (TEXT) is DERIVED via `signals.accum_character(...)` so re-tuning thresholds needs no full backfill — `python -m src.automation.signals --relabel-character` re-derives every label in seconds. Default thresholds (TUNABLE, in `signals._CHAR_THRESH`; first match wins): `active`=p_score≥2 · `broadening`=tcr≥1.3 · `concentrated`=tcr≤1.1 · `up_skew`=updown≥1.30 · `down_skew`=updown≤0.77 · `price_up`=drift>5 · `price_down`=drift<−5 · `near_high`=pct_from_52w_high>−10. Rule: **DISTRIBUTION** if active AND (price_down OR (near_high AND not price_up)) AND (broadening OR down_skew); **ACCUMULATION** if active AND (price_up OR price_flat) AND (concentrated OR up_skew); **CONSOLIDATION** if (not active) AND price_flat; else **NEUTRAL**; NULL inputs → NULL ('-').

**Doctrine compliance:** no LLM (pure Python/SQL, nightly); value-based & split-invariant (delivery ₹ = deliv_qty × close); ADJUSTED closes (reuses `adjust.adjusted_closes`) for every direction/return read so a split can't fake a down-day; days with |daily return|>0.30 excluded as corp-action anomalies (D36 CC_THRESH); calendar-day windows (30/90/180) matching `signals._WINDOWS`.

**Shipped:**
- **`signals.py`** — shared label brain (`_char_flags` / `accum_character` / `accum_character_read`), metric compute (`_ret_signs` / `_character_metrics` / `_character_arrays`), folded into BOTH the live `compute_signals_for_symbol_date` (per-symbol fetch extended to 372 cal days for the 52w high; now also pulls `prev_close`+`deliv_per`) and the `--backfill-triggers` per-symbol pass (same batch UPDATE, +8 fields). New `--relabel-character` mode. ONE shared helper so dashboard + bot derive identical labels (DRY).
- **`db.py`** — 8 new `stock_signals` columns + `idx_signals_accum_character(trade_date, accum_character)`.
- **`dashboard.py`** — `_char_pill` + `.ca-*` pills; `/dash/stocks` daily gains a **Character** column, a **Total delivery ₹Cr** column, and **🟢 Accumulation / 🔴 Distribution** filter pills (wired into the existing `sflt` client filter via `data-accum`/`data-distrib`, composing with the `.dt` grid); weekly/monthly rollup carries the latest-day character; `/dash/stock` gets an **"Accumulation character"** panel (label + plain-English read + up/down delivery bar + WHO row + 52w-high distance + a ⚠️ distribution-while-high warning); Home gains a **"Stealth accumulation"** board (ACCUMULATION + p_score≥3 + concentrated + off-highs) and a Character pill on Top-trigger-stocks; `_PILLARS["POS"]` thesis now mentions character.
- **`telegram_bot.py`** — `/dvpt` gains a **🧭 Character** block; `/scan` + `/triggers` rows gain a **Ch** marker; `/triggers` gains modes **`accum`** (ACCUMULATION + p_score≥3 + concentrated) and **`distrib`** (DISTRIBUTION); `/start` help + `BOT_COMMANDS` updated. Same shared label helper as the dashboard.

**Verification:** all 4 modules `py_compile` clean; label rule + metric/anomaly-exclusion unit-tested synthetically (markup⇒ACCUMULATION, quiet base⇒ACCUMULATION/absorption, near-high broadening⇒DISTRIBUTION, split-day excluded from up/down skew, all boundaries); dashboard routes (`/dash`, `/dash/stocks` ±weekly/monthly, `/dash/stock`) return HTTP 200 on empty DB. Real-data eyeball + full backfill done on the VPS (see § Session log).

**Future (NOT built):** NSE **bulk & block deals** feed is the only source that names buyer/seller + side (trades >0.5% of equity) — the lone ground-truth for direction. Not ingested today; flagged in § "What's NOT yet built" as the next deepening of this pillar.

### D42 — Equity-only scanners via the NSE equity allowlist (ETF exclusion) — SHIPPED (session 17)
Why: Ramana flagged ETFs/MFs polluting the equity scanners — this is equity research; scanners must be equity-only (a separate ETF section is fine, but not mixed in). The D23 name-pattern filter (`NOT LIKE '%ETF%'/'%BEES%'/'%GOLD%'…`) is **leaky** — 44 ETFs slipped through on the latest day (ALPHA, BFSI, DEFENCE, ENERGY, IT, MAFANG, HDFCNIFTY, GROWW*, LIQUID*, HDFCSML250 … whose symbols carry no ETF-ish token) — AND it **wrongly drops real equities** (GOLDIAM via `%GOLD%`, MONARCH via `MON%`). Our bhav source (`sec_bhavdata_full`) carries **no ISIN** (the `isin` column is entirely NULL), so the structural INE-vs-INF ISIN split isn't available — a symbol allowlist is the robust separator.

Shipped:
- **`nse_equity_list` table** + **`src/automation/equity_list.py`** — fetches NSE `EQUITY_L.csv` (the canonical listed-equity universe, ~2,374 symbols; ETFs/MFs are NOT in it). Refreshed nightly; the table is replaced ONLY on a successful, non-empty fetch (a failed fetch leaves the prior list intact) so the scanner filter can never silently empty.
- **All three scanner filters** — `dashboard._SCAN_FILTERS`, `stock_rs._LIQUID_FILTER`, `telegram_bot._SCAN_FILTERS_SQL` — replaced the leaky `NOT LIKE` name patterns with `AND s.symbol IN (SELECT symbol FROM nse_equity_list)`. Fixes the leak EVERYWHERE (daily + weekly screens, /scan, /triggers, the RS-rank universe, leaders/laggards) and stops the GOLDIAM/MONARCH false-drops.
- Wired `equity_list` into the nightly `10-signals.conf` chain (before `stock_rs`); recomputed `rs_rank` over the equity-only universe (`--rank-only`, 1.29M rows).
- Verified live: scanner = **0 non-equity symbols, 0 known ETF leakers**; MAFANG/HDFCNIFTY/GROWWDEFNC filtered out; GOLDIAM now allowed.

Separate ETF section (offered, not built): the data exists trivially now — EQ-series symbols NOT in `nse_equity_list` = the ETF/MF universe — so a dedicated ETF view is a small follow-up if wanted. The equity-only-research priority is done.

### D41 — Strategy-surface redesign Phase 1 (labels + Strategies hub + sector curation + weekly DVPT) — SHIPPED (session 17)
Why: Ramana's feedback — the 3 strategies (DVPT positioning / Relative Strength / patearn quality) felt BLENDED (no board said which strategy it was); he wanted to "click a strategy and it shows up"; clicking factor indices (e.g. Nifty High Beta) dead-ended with no constituents; and DVPT triggers were a TODAY-only snapshot, so a mid-week institutional spike was missed if not checked daily. Designed via a 4-perspective panel (financial analyst + data + UI/UX + architect); the full roadmap (Phases 1–3) is below.

Shipped (Phase 1 — `dashboard.py` only, render-only, NO schema/backfill):
- **Strategy badges** — a `_strategy_badge(family)` thesis header (POSITIONING / RELATIVE STRENGTH / QUALITY, colour-coded) stamped on Home sub-blocks, `/dash/sectors`, `/dash/rs`, `/dash/leaders`, `/dash/stocks` — so no board is silent about its strategy.
- **Strategies hub on Home** — 3 pillar cards (thesis + a live count: "N SS/S today", "N leaders", "N scored") → each pillar's screen. Ramana's "click a strategy → it shows up." Placed 2nd on Home (after the regime banner). NOT a 6th nav tab (nav stays at 5, per D40-A).
- **Sector curation** — a `REAL_SECTORS` whitelist (the 16 `MAJOR_SECTORS` + Nifty India Defence); `/dash/sectors`, `/dash/rs`, and Home top-sectors filter to it, so factor/strategy/thematic indices (High Beta, Alpha, Momentum, IPO…) no longer pollute rotation. Their RS read still lives on `/dash/markets`. The sector→stock drill empty-state now says "factor/thematic index, not a sector — see its ratio chart →" (no more dead clicks). Verified: High Beta gone from /dash/sectors, Nifty Bank present.
- **Weekly/Monthly DVPT triggers (v1)** — a Daily/Weekly/Monthly toggle on `/dash/stocks`. Weekly/Monthly **roll up the daily verdicts over the last 5 / ~22 trading days** (on-read GROUP BY over existing `stock_signals`, no backfill): per symbol = peak rank + **"days fired" (count of A+ days, N/window)** + avg DVPT — so a Tuesday spike is visible on Friday. Daily stays the default + unchanged.

Decisions: (a) **deferred the full strategy-REGISTRY refactor** (one Strategy object powering dashboard + bot + screeners) — the panel recommended it but it's an invasive behaviour-preserving refactor; a light `_PILLARS` descriptor delivers the labels/hub now, the registry lands with the screener phase. (b) **Weekly v1 is on-read, not materialised** — a `weekly_signals` rollup table (the doctrine-correct destination) is deferred to Phase 2; the last-5-day read-aggregate validates the UX with zero backfill. (c) sector curation is a render-side whitelist (Phase 1), not the deeper `index_signals.broad_benchmark` classifier (Phase 2).

Roadmap — **Phase 2:** materialise `weekly_signals` (W+M grain) in the nightly chain (instant queries + week-over-week + monthly history); ~~add real missing sectors (India Defence / Private Bank / Chemicals) to `membership.py`~~ ✅ **DONE (session 18)** — the 3 are now in `membership.py` + `REAL_SECTORS` and their constituents loaded (slugs `ind_niftyindiadefence_list`/`ind_nifty_privatebanklist`/`ind_niftychemicals_list`; 19/10/20 members), so their sector→stock drill works. **Phase 3:** a saved-screener / safe parameterised query-builder ("build your own queries") sharing a column whitelist with a proper strategy registry; a composite **Conviction shortlist** (RS leader → institutions buying it this week → pt14 quality). All no-LLM, read-only, doctrine-aligned.

### D33c — Composite "strong-in-strong" leaders / laggards — SHIPPED (session 17)
Why: the payoff of the whole RS pillar (Ramana's original thesis, made objective). With D32 (sector vs broad), D33a (stock vs broad + 1–99 rank) and D33b (stock vs sector) in place, D33c combines all three into one screen — a **leader** is strong at every layer, a **laggard** weak at every layer.

Definition (D37): **LEADER** = stock `rs_vs_sector_trend_state` ∈ {UPTREND,BREAKOUT} AND stock `rs_vs_broad_trend_state` ∈ {UPTREND,BREAKOUT} AND its sector's own `rs_vs_broad_trend_state` (D32 `index_signals`) ∈ {UPTREND,BREAKOUT}. **LAGGARD** = the mirror in {DOWNTREND,BREAKDOWN}. Leaders ordered by broad `rs_rank` DESC (strongest first), laggards ASC.

Shipped:
- **`stock_rs.leaders_laggards(kind, limit, trade_date=None)`** — ONE shared read helper (DRY) over `stock_signals` JOIN `bhavcopy_rows` JOIN `index_signals` (the sector's row at the latest index date) + the liquid filter. Used by BOTH the dashboard and the bot.
- **`/dash/leaders`** — Leaders + Laggards boards as sortable `dt` tables (symbol · RS rank · sector · the 3 trend pills: stock-vs-broad / stock-vs-sector / sector-vs-broad). Reached from a **"Strong-in-strong leaders" preview on Home** (top 5) and deep-links to each stock/sector. `active="stocks"` — NOT a 6th nav tab (the macro→micro nav stays at 5, like /dash/rs, /dash/ratio, /dash/compare).
- **`/rs TICKER`, `/leaders`, `/laggards`** Telegram commands (pure SQL, ₹0). `/rs` shows the stock's broad RS + 1–99 rank + sector RS + the composite verdict. (Bot is network-blocked from the VPS; the code is live and the commands register when Telegram is reachable.)
- Verified live: leaders WELCORP/POWERINDIA/THERMAX/BHEL (Energy/Metal, rank 92–97), laggards HCLTECH/TCS (IT), SBICARD/HDFCLIFE (Fin Svcs), PATANJALI/UBL (FMCG) — all three layers aligned. All routes HTTP 200.

This closes the **third strategy pillar (Relative Strength)**. No new schema — reuses the D33a/b columns + D32 `index_signals`.

### D33b — Stock-vs-sector Relative Strength — SHIPPED (session 17)
Why: second slice of the third-pillar RS spec (D37). D33a gave stock-vs-broad (Nifty 500) RS + a 1–99 rank; D33b adds stock-vs-its-own-SECTOR RS so the stock page answers BOTH "is it beating the market?" and "is it leading its own pack?" — the two inputs the D33c "strong-in-strong" leader flag needs.

Shipped:
- **Primary-sector assignment (the new rule):** each stock's PRIMARY sector = the NARROWEST NSE sectoral index it belongs to in `stock_index_membership` — the one with the FEWEST members (most specific) — with size/broad indices excluded (REUSES D32's `SIZE_BASED_INDEX_NAMES`). Ties broken alphabetically (deterministic). Self-correcting on macro-overlap: a bank in Financial Services(~20) + Bank(~12) → **Nifty Bank**; RELIANCE in Oil&Gas/Energy/Commodities → **Nifty Oil & Gas** (both verified live). A stock in NO sectoral index → `primary_sector` NULL → broad RS only. **209 stocks** got a sector (the rest of the membership universe is broad/size-only — correct, not a bug).
- **`rs_vs_sector = adjusted_close(stock) / close(primary_sector_index)`**, same D32 ratio-signal vocabulary (slopes / MA-flags / 52w-high / trend_state). Built by EXTENDING `src/automation/stock_rs.py` (not a new module): `primary_sector_map()`, `_sector_close_maps()`, `compute_symbol_sector_rs()` (REUSES `build_rs_history` + `index_signals.compute_ratio_signal` — the SAME adjusted-price path as broad, so splits don't fake a sector-RS cliff; unit-verified on a synthetic 2:1 split), `run_sector_backfill()` (~500 syms), `compute_sector_for_date()` (nightly). CLI: `--sector-backfill`, `--symbol` now prints broad+sector, `--backfill` does both.
- **10 new `stock_signals` columns** (db.py `_ensure_column`): `primary_sector` + `rs_vs_sector_today` + `rs_vs_sector_slope_{1m,3m,6m,12m}` + `rs_vs_sector_above_50ma` / `above_200ma` / `new_52w_high` / `trend_state`; index `idx_signals_primary_sector(trade_date, primary_sector)` for the D33c join. Denormalized per row (Doctrine C), like rs_vs_broad. **No sector rank** — cross-ranking a bank-vs-banks against a pharma-vs-pharmas on one 1–99 scale is apples-to-oranges; the 1–99 percentile rank stays broad-only.
- **`/dash/stock` RS card** now shows BOTH: a "vs broad Nifty 500" sub-section (trend pill + 1–99 rank gauge + heat strip) and a "vs sector <name>" sub-section (pill + heat strip), and the reconciliation table gained **sector-return + RS·sector columns** so "RS ≈ stock − benchmark" is verifiable for both reads. Graceful "no NSE sectoral index covers this stock — broad RS only" when `primary_sector` is NULL.
- Verified live on VPS: HDFCBANK→Nifty Bank, RELIANCE→Nifty Oil & Gas; sector backfill 209 symbols / 237,716 rows in ~70s; `/dash/stock?sym=HDFCBANK` HTTP 200 rendering both blocks. (Membership itself was already populated back in D38 — no re-fetch needed.)

Next: **D33c** — composite "strong-in-strong" leaders/laggards (stock rs_vs_sector ∈ {UPTREND,BREAKOUT} AND stock rs_vs_broad ∈ {UPTREND,BREAKOUT} AND the sector's own rs_vs_broad (D32) ∈ {UPTREND,BREAKOUT}) → `/dash/leaders` board + `/rs` `/leaders` `/laggards` Telegram commands.

### D40 — Multi-index comparison/rebase chart + chart range-switch perf fix — SHIPPED
Why: Ramana wanted to overlay indices on one chart **rebased to a common start** (both starting together) to compare relative strength — with a **fluid anchor** (pan left → that point becomes the new 0/100) and a **ratio↔rebased toggle**; and flagged the chart range-switch (1Y→Max/6M) as **slow**. 2nd 5-agent panel; full design in **`docs/rs-ratio-analysis-design.md` Part 2** (decisions D40-A..G).

Shipped (`dashboard.py` only — render-only, no schema/backfill):
- **`/dash/compare?idx=&idx=&den=&mode=&base=&r=`** — overlay ≤6 indices, each **rebased client-side** (base 100 or 0%); **fluid anchor** = first visible point (pan to re-anchor) or 📅 pin/⟳ reset; **Mode [Rebased %|Ratio]**; Range 3M/6M/1Y/Max; vs-50/500 (ratio mode); **chip-rail picker** (seeded from `MAJOR_BROAD`/`MAJOR_SECTORS` + substring search over all index names, sticky 6-color palette); one-click presets; live "REBASED FROM <date>" + crosshair value row. Reached via a "Compare ⇄" button on `/dash/ratio` + "⇄ Compare indices" links on `/dash/markets` + `/dash/sectors`. `active="markets"`. Validates `idx` against `SELECT DISTINCT index_name` (title-case). Full-history series inlined so client-side range/rebase need no refetch (~100KB/line; if 5-6 lines feel heavy, switch to a JSON endpoint + downsample — noted in the doc).
- **Why a new route — not a mode on `/dash/ratio`, not a 6th nav tab (D40-A):** `/dash/ratio` is single-subject (its gauge/quadrant/READ/constituents are meaningless for N overlaid lines), and the macro→micro nav is full at 5 tabs — so Compare is a *destination reached with intent* (deep-linked from the ratio/markets/sectors surfaces), not a top-level tab. The sticky 6-color palette (`#1f6feb #d29922 #3fb950 #f85149 #a371f7 #58a6ff`, indexed by slot) means removing a line never recolors the others; rebase is client-side with one common **forward-snapped** fluid anchor (first trading day ≥ left edge), dropping any line with no/zero value at the anchor rather than fudging it.
- **Chart perf fix (the slowness):** root cause = `/dash/stock`'s 3-chart `subscribeVisibleLogicalRangeChange` sync **ping-pong** (no reentrancy guard) + the `ResizeObserver` `applyOptions` re-layout. Fix: a `syncing` reentrancy flag, `setRange` applies to all charts **directly** (bypassing the sync loop), debounced ResizeObserver; same debounce on `/dash/ratio`. `/dash/compare`'s fluid rebase is rAF-coalesced + anchor-gated so panning stays smooth.
All routes verified HTTP 200 on real data (incl. ratio mode + idx validation), no regressions, no errors.

### D39 — RS ratio-analysis layer (multi-timeframe trend, ratio charts, normalization) — SHIPPED (Phase A + B-on-read)
Why: Ramana flagged that the dashboard mixes ABSOLUTE return with RELATIVE strength in one row, hides the timeframe behind a single blended "UPTREND" label, and never charts the index/Nifty ratio. Convened a 5-perspective panel (quant/financial + equity-practitioner + data + UI/UX + architect). **Full design: `docs/rs-ratio-analysis-design.md`** (decisions D-A..D-H + phased tasks).

Key findings:
- The IT-0.5-vs-Bank-2.0 **normalization worry is already solved** — `ratio_signals.slope_*_pct` / `index_signals.rs_vs_broad_slope_*` are % changes (cross-sector comparable). Just **label & surface** it; don't rebuild.
- **Phase A ships from EXISTING data — no schema change, no backfill:** (A1) relabel into RETURN vs RELATIVE-STRENGTH column groups; (A2) a 4-cell **1m/3m/6m/12m heat strip** (▲▬▼ from the slope columns) on Markets/Sectors/Home; (A3) new **`/dash/ratio?idx=&den=`** ratio-chart page (ratio line + 50-MA smoother + 200-MA reference + up/down-cross + new-RS-high markers + range/benchmark toggles + auto-READ), deep-linked from RS cells; (A4) absolute×relative quadrant SVG + RS-momentum percentile + constituent stocks.
- **Phase B (one backfill):** smoothed/normalized ROC + cross-sectional z-momentum (2nd pass in `compute_for_date`) + volatility-scaled dead-band/hysteresis + a `/dash/rs` ranking page.
- Reuses the `/dash/stock` lightweight-charts block + existing `.p-*` palette. ⚠ Title-case index names (validate `idx` against `SELECT DISTINCT index_name`). No runtime LLM.

**Built (session 16, on-read — no schema change, no backfill):**
- **RETURN vs RELATIVE-STRENGTH column groups** + a **4-cell 1m/3m/6m/12m heat strip** (`_rs_strip`, ▲▬▼) on Home/Markets/Sectors.
- **`/dash/ratio?idx=&den=`** — per-index RS ratio chart (lightweight-charts): ratio line + 50-MA smoother + 200-MA reference + up/down-cross + new-RS-high markers + 3M/6M/1Y/Max range + vs-Nifty-50/500 toggle + on-read RS-momentum percentile gauge + absolute×relative quadrant SVG + auto-READ + top constituents (by DVPT trigger). Deep-linked from RS cells. Guards size-index (no ratio_rows) + unknown-index.
- **`/dash/rs`** — cross-sector RS-momentum ranking (on-read window fn; `0.6·slope_3m + 0.4·slope_6m`).
- Cross-sector ranking is computed **on-read** (window function); the stored z-momentum column + 10-min backfill (Phase-B-stored) was **skipped as unnecessary** — only needed later if historical rank-over-time charting is wanted. All routes verified HTTP 200 on real data incl. edge cases; no regressions.

### D38 — Analyst dashboard redesign (macro→micro) + index-constituent membership
Why: the v1 dashboard (D33-web/D36) was 4 flat pages. Ramana (the equity analyst it serves) wanted a real macro→micro structure, the **major** indexes/sectors separated from the ~150-index factor/strategy/thematic bundle, and a discoverable **stocks** surface (he literally couldn't find stocks). Designed via a 3-perspective pass (data audit + equity-analyst IA & major-list + UI/UX spec), synthesized into one blueprint.

Shipped (Phase 1, pure SQL, no schema change beyond populating membership):
- **5-tab macro→micro nav**: Home → Markets → Sectors → Stocks → Stock. A ticker-search box in **every** page header (the biggest discoverability fix).
- **/dash** rebuilt: RISK-ON/NEUTRAL/RISK-OFF regime banner (breadth + Nifty-vs-200DMA) · KPIs (Nifty 1d, % indices >200-DMA, size leadership) · top-5 sectors by 3m RS + weakest-3 · top-5 trigger stocks.
- **/dash/markets** (NEW): Block A curated **Major indexes & sectors** (accent cards from `MAJOR_BROAD`+`MAJOR_SECTORS`) pinned on top; Block B the full bundle below (All/Broad/Sectoral JS filter). Tap a card → its constituent stocks.
- **/dash/sectors**: now the pure RS rotation leaderboard; each sector row drills to `/dash/stocks?sector=`.
- **/dash/stocks** (NEW): the stock hub — search + layered-DVPT screen (moved from /dash/scan) + JS filter pills (All/SS/A+/⚡ATH/🟢Discount/🔥Near-break) + live watchlist chips + `?sector=` constituent filter.
- **/dash/scan** kept as a working orphan (not in nav); **/dash/stock** unchanged.

Membership (**D33b** — was the blocker for the sector→stock drill): new `src/automation/membership.py` fetches niftyindices.com constituent CSVs (`ind_<slug>list.csv`) for 21 curated indices → `stock_index_membership` (symbol, index_name, snapshot_date; weight NULL — not in the CSV). 1,305 rows / 511 symbols. Index names verified to match `index_rows.index_name` exactly (incl. the quirk **'Nifty Healthcare Index'**; Private Bank + Chemicals have no clean feed, skipped). Wired into the nightly timer (last ExecStart in 10-signals.conf).

Phase 2 (deferred): stock-level RS (**D33/D37** — still the real third-pillar build) + the stock-page RS card, breadcrumb, section reorder, pt14 batch scoring (B6), inline sparklines, click-sort. Reused lesson from the index_signals bug: NSE names are title-case — both the membership map and the MAJOR lists hard-code exact title-case names.

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

### D33-web — Installable web dashboard (PWA)
Why: User wanted a "desktop app" for Hermes (initially confused with Nous Research's identically-named Hermes Agent — unrelated product). What he actually wanted: a richer-than-Telegram view of Hermes, installable as a desktop app. Path chosen = PWA (Progressive Web App): a browser dashboard that Chrome/Edge can "Install" → own icon + frameless window, feels native, zero extra maintenance, reuses the FastAPI server already running on :8000.

Built:
- `src/web/dashboard.py` — FastAPI APIRouter with 4 views + PWA assets. Dark theme matching the existing /candidates page, bottom-nav like a mobile app.
  - `/dash` — overview (KPIs: SS+S triggers today, ATH-DVPT count, sector breakouts; nav cards; data-freshness)
  - `/dash/sectors` — D32 sector-rotation table, color-coded by trend_state, sorted strongest first
  - `/dash/scan` — D28/D31 layered triggers table (rank, r/p score, Δhot, near-P); tap symbol → stock detail
  - `/dash/stock?sym=X` — per-stock DVPT + D31 institutional price zones (P-tier + R-tier) + 15-day history
  - PWA: `/manifest.webmanifest`, `/sw.js` (network-first service worker, offline fallback), `/icon.svg`, `/dash/offline`
- `src/web/__init__.py` — package marker
- Wired into `src/main.py` via `app.include_router(dashboard_router)`
- Read-only. No LLM. No mutation. Pure SQL over existing tables.

HTTPS prerequisite (required for the "Install" button to appear): Caddy reverse-proxy with auto Let's Encrypt cert. The Hostinger VPS hostname `srv1704897.hstgr.cloud` publicly resolves to the VPS IP (confirmed via 8.8.8.8) — so Caddy gets a cert for it with zero extra domain setup. Caddyfile: `srv1704897.hstgr.cloud { reverse_proxy localhost:8000 }`. Needs ports 80/443 open in Hostinger firewall.

Deploy:
```bash
cd /opt/hermes && git pull && systemctl restart hermes-api
# Install Caddy (one-time):
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
# Configure:
echo 'srv1704897.hstgr.cloud {
    reverse_proxy localhost:8000
}' > /etc/caddy/Caddyfile
systemctl reload caddy
```
Then on the laptop: open `https://srv1704897.hstgr.cloud/dash` in Chrome/Edge → click the Install icon in the address bar → Hermes gets a desktop icon + own window.

Access without HTTPS: dashboard works over plain `http://187.127.173.149:8000/dash` immediately (just no install button until Caddy is up).

### D37 (SPEC, NOT BUILT) — D33 stock-level Relative Strength + standardization
The third strategy pillar's stock layer. Discussed at length; this is the agreed standardized design. **Build next as a fresh focused session — do NOT cram into a long mixed session.**

**Two ratio series per stock per day (the canonical RS):**
- `rs_vs_broad = adj_close(stock) / close(NIFTY 500)` — works for ALL ~3,000 stocks.
- `rs_vs_sector = adj_close(stock) / close(primary_sector_index)` — only stocks with a known NSE sector (~500).

**Five standardization rules (binding for the build):**
1. **Adjusted prices ALWAYS** — RS = relative return; raw splits fake an RS collapse. Must use the split/bonus back-adjustment (currently only in the dashboard render — must be moved to a reusable pipeline layer; see D36/open item).
2. **Same windows as everything else** — 1m/3m/6m/12m (the DVPT/D31 horizons). One time-language.
3. **Same technical reads + trend_state vocabulary as D32** — 20/50/200 MA, 52w hi/lo, slope%, BREAKOUT/UPTREND/CONSOLIDATING/DOWNTREND/BREAKDOWN. Reuse the D32 ratio engine.
4. **Percentile RS rank (1–99)** — THE cross-stock standardization. Rank each stock's blended RS momentum (weighted 3m+6m slope of rs_vs_broad) across all liquid stocks. "RS 90 = stronger than 90% of the market." Without this RS is just a chart, not a screen.
5. **Nifty 500 = canonical broad benchmark** (Nifty 50 secondary). D32 decision kept.

**Composite "strong-in-strong" leader flag (Ramana's original thesis, made objective):**
Leader = stock `rs_vs_sector` ∈ {UPTREND,BREAKOUT} AND stock `rs_vs_broad` ∈ {UPTREND,BREAKOUT} AND its sector's `rs_vs_broad` (D32) ∈ {UPTREND,BREAKOUT}. All 3 layers aligned up = bullseye; all down = laggard.

**The membership hurdle:** stock-vs-broad needs no membership (do first). stock-vs-sector needs `stock_index_membership` (empty table in schema) populated from NSE sectoral-index constituent CSVs, assigning each stock its NARROWEST sectoral index as "primary sector." NSE indexes cover only ~500 stocks; the rest get broad-only (or a Screener sector scrape later).

**Phasing:** D33a (DONE, s16) = stock-vs-broad RS + slope + percentile rank (all stocks). D33b (DONE, s17) = stock-vs-sector RS (membership was already populated back in D38, so D33b was just the sector-RS pass + assignment). D33c (next) = composite leader/laggard + `/rs`, `/leaders`, `/laggards` + dashboard leaders board.

**D33a — DONE (session 16), D33b — DONE (session 17).** See the D33b decision-log entry near the top for the sector design. D33a: `src/automation/adjust.py` (reusable corp-action back-adjustment, extracted from D36) + 10 `rs_vs_broad_*`/`rs_rank` columns + `idx_signals_rs_rank` + `src/automation/stock_rs.py` (reuses `index_signals.compute_ratio_signal` + `adjust.adjusted_closes`; UPDATEs existing rows; SQL `PERCENT_RANK()` over the liquid universe) + the `/dash/stock` RS card; backfilled 2.37M RS rows / 1.37M ranked. D33b: `primary_sector` + 9 `rs_vs_sector_*` columns + the sector pass in `stock_rs.py` (narrowest-sector assignment, REUSING the broad adjusted-price path) + the sector block on the stock page; backfilled 209 symbols / 237,716 rows.

### D36 — Corporate-action back-adjustment for price charts (NOT for signals)
Why: The `/dash/stock` price chart plotted raw bhav-copy close, so every split/bonus made a fake cliff (PARAS showed a phantom ₹1800 spike vs Zerodha's smooth ~₹250→₹1089). Fix is in the dashboard render: two-layer detection — (a) `prev_close[i]/close[i-1]` deviation >3% (NSE adjusts prev_close on ex-dates); (b) fallback for >30% single-day close jumps prev_close left unadjusted (data anomaly; a real 30%+ move is impossible under circuit limits). Back-adjust historical OHLC by the cumulative factor. **DVPT signals are unaffected** — they're value-based (₹=qty×price), already split-invariant (Doctrine § C). **Limitation:** the institutional ZONES (avg_close_*) are computed from raw closes in signals.py; if an action falls in the zone window they're off-scale on the adjusted chart (the ⚠ "zone overlay approximate" warning). **Open item:** move the adjustment into a reusable layer and recompute zones (and D33 RS) on adjusted prices.

### D35 — Daily pipeline self-heal (signals run with bhav copy)
Why: The bhavcopy systemd timer ingested daily but `signals.py` never ran automatically — signals lagged silently for a week (caught only when `/dvpt` showed stale data). Fix: systemd drop-in `/etc/systemd/system/hermes-bhavcopy.service.d/10-signals.conf` adds `ExecStart=/opt/hermes/.venv/bin/python -m src.automation.signals` after the bhav fetch. (Also the place to wire `indexes` + `index_signals` for D32.) Idempotent — signals skip already-computed (symbol,date). **Full nightly chain as of session 17:** `signals → indexes → index_signals → membership → equity_list → stock_rs` (`equity_list` D42 refreshes the equity allowlist; `stock_rs` added in s17 — D33a/b/c RS would otherwise go stale after the manual backfill; `stock_rs` with no args = `run_today`, ~40s for the latest date: broad + sector + rank).

### D34 — Nous Hermes Agent self-hosted on the VPS (separate product)
Why: Ramana wanted "the Hermes Agent" (a general AI assistant), which turned out to be **Nous Research's open-source Hermes Agent** — unrelated to our market system, just a name collision (and a 3rd collision with nexos.ai, a model-credits upsell Hostinger bundles, which he did NOT buy). Set up via Docker (`nousresearch/hermes-agent`), NOT the paid Hostinger/nexos bundle (that one needs no purchase — the agent is free, you bring your own model). Config: container `hermes-agent`, dashboard bound `127.0.0.1:9119` (loopback), Caddy front at `:9443` (HTTPS), Nous Portal OAuth login (free tier), model `nvidia/nemotron-3-ultra:free`, free tool pool. Registered with Nous Portal via `dashboard register --redirect-uri https://srv1704897.hstgr.cloud:9443/auth/callback` + `public_url` set in config. **Isolated from market Hermes** (own container, ports 8642/9119 vs our 8000/80/443; own data /root/.hermes). Cost: ₹0 on free model. **This is NOT part of the market Hermes codebase** — it's Ramana's separate general-AI tool that happens to share the VPS.

### D32 — Index data + ratio infrastructure (third strategy pillar, phase 1)
Why: User specified the third strategy alongside quality (/pt14) and positioning (/dvpt+D31) — relative strength. Treat sector-vs-broad ratios as **continuous time series**, apply technical reads (MA / breakout / trend state), surface in Telegram. Sector ratio breakout = "sector starting to outperform" signal. Companion to ratio breakdown for weakness detection.

Architecture (4 layers):
- **`index_rows`** — daily OHLC + P/E + P/B + Div Yield per NSE index. Sourced from `ind_close_all_DDMMYYYY.csv`. ~50 indexes × 1 row/day.
- **`ratio_rows`** — generic (numerator, denominator, trade_date) → ratio. Symmetric: numerator/denominator can be index or stock. Source of truth for "the ratio chart as raw values."
- **`ratio_signals`** — pre-computed technical reads per ratio per day: 20/50/200d MA, 50d/200d/52w high/low, 1m/3m/6m/12m slope, above/below MA, cross flags, new-high flags, composite `trend_state` ∈ {BREAKOUT, UPTREND, CONSOLIDATING, DOWNTREND, BREAKDOWN}.
- **`index_signals`** — per-index per-day: 1d/1w/1m/3m/6m/12w returns, MA distances, 52w positioning, AND **denormalized RS vs default broad benchmark (Nifty 500)** — today's ratio + slopes + flags + trend_state. Lets `/index NAME` return full picture in one row read.
- **`stock_index_membership`** — constituent lists (D33 will populate). Not used in D32.

Files added:
- `src/automation/indexes.py` — fetcher mirroring `bhavcopy.py`. Archives raw CSV, parses, ingests, tracks dates.
- `src/automation/index_signals.py` — orchestrates index_signals + ratio_rows + ratio_signals for sector-vs-broad pairs (every non-size-based index × {Nifty 50, Nifty 500}).

Telegram surface — 6 new commands:
- `/index NAME` — level + technicals + RS vs Nifty 500 + trend_state
- `/sectors` / `/rotation` — sector dashboard ordered by trend_state then 3m RS slope. The "what's leading the market" view.
- `/ratio NUM DEN` — full read for one pair: ratio + MAs + slopes + breakout flags + 30-day history of the ratio chart as values
- `/breakouts` — every ratio at BREAKOUT or UPTREND, sorted by 3m slope DESC
- `/breakdowns` — every ratio at BREAKDOWN or DOWNTREND

Breakout definitions (objective, no manual chart-reading):
- `new_52w_high` = today's ratio strictly > max of prior 252 days
- `new_200d_high` = same against prior 200 days
- `new_50d_high` = same against prior 50 days
- `cross_50_today` = ratio crossed up through 50d MA today
- `cross_200_today` = ratio crossed up through 200d MA today
- Composite `trend_state` = BREAKOUT (new 52w or new 200d + above 200ma) / UPTREND (above 200ma + positive 3m slope) / CONSOLIDATING (within 5% of 50ma) / DOWNTREND (below 200ma + negative 3m slope) / BREAKDOWN (>40% below 52w high + below 200ma)

Deploy after commit:
```bash
cd /opt/hermes && git pull
sudo tee -a /etc/systemd/system/hermes-bhavcopy.service.d/10-signals.conf > /dev/null <<EOF
ExecStart=/opt/hermes/.venv/bin/python -m src.automation.indexes
ExecStart=/opt/hermes/.venv/bin/python -m src.automation.index_signals
EOF
sudo systemctl daemon-reload
systemctl restart hermes-telegram

# 5y backfill
nohup .venv/bin/python -m src.automation.indexes --backfill 1830 > /var/log/hermes-indexes-backfill.log 2>&1 &
# Then once that's done:
nohup .venv/bin/python -m src.automation.index_signals --backfill > /var/log/hermes-index-signals-backfill.log 2>&1 &
```
Index fetch ~5-10 min for 5y. Signal+ratio compute ~5-10 min after.

What's next (D33 — stock-level RS): with `stock_index_membership` populated from sectoral constituent CSVs, layer stock-vs-sector and stock-vs-broad ratios on top of D32's machinery. Add denormalized RS columns to `stock_signals`. Add `/rs TICKER`, `/leaders`, `/laggards`. Defer until D32 has been used in real workflow.

### D31 — Calendar-day windowing + institutional price zones (revises D28)
Why: Two material gaps Ramana surfaced during session 15 deploy testing:
1. **Windowing was wrong.** D28 used trading-day windows with top-N (5/10/15/40/80 of 22/44/66/132/264 trading days). Ramana specified calendar-day windows with much more selective top-N (4/7/12/20/30 of 30/60/90/180/360 calendar days). The new top-N is ~8–13% of days (vs old 23–30%), so the P-tier baselines now genuinely represent exceptional institutional days, not "above average."
2. **Companion price was missing.** DVPT alone tells you institutional intensity. Without the avg CLOSE on the baseline days, you can't tell whether to follow the institutions in (discount) or stay out (above their bid). The entire strategy needs both. D28 had only ONE such metric (hot_days_avg_price, hybrid window). D31 adds the proper paired price for every R + P baseline.

Implementation:
- **Schema:** 10 new columns on `stock_signals` via `_ensure_column`:
  - `avg_close_r1m/r2m/r3m/r6m/r12m` — flat avg close over 30/60/90/180/360 calendar days
  - `avg_close_p1m/p2m/p3m/p6m/p12m` — avg close on the same top-N-by-DVPT days that defined `power_dvpt_*`
- **Existing P-tier and R-tier DVPT baselines redefined.** Same column names (`power_dvpt_1m..12m`, `avg_dvpt_1m..12m`) but new semantics: calendar-day windows with new top-N. The trading-day `avg_dvpt_5d/10d/30d/60d/90d/180d/365d` columns stay as LEGACY for the `/dvpt` history table only.
- **Signal compute (`signals.py`)** — single source of truth `_WINDOWS = (('1m',30,4), ('2m',60,7), ('3m',90,12), ('6m',180,20), ('12m',360,30))`. Calendar-day filter via `_cutoff_date(trade_date, days)` (uses `datetime + timedelta`). Per (symbol, day), fetch all bhav rows within 360 calendar days once, then slice per window for R-tier and P-tier with companion avg close.
- **`/dvpt TICKER` output** — new "📍 Institutional price zones" section after the history table. Shows P-tier first (more actionable: where the institutions actually transacted), then R-tier. Each row: baseline label, avg close, %gap to today's close, marker (🟢 below −3%, 🟡 ±3%, 🔴 above +3%).
- **`/scan` and `/triggers`** unchanged structure (still r/p score + entry marker for one-glance read). The 10-row grid is per-stock detail only.
- **Backfill MANDATORY.** Existing D28 power/R values are wrong under the new windowing. `--backfill-triggers` recomputes ALL D28 + D31 fields per row using calendar-day slicing. Per-symbol bulk fetch + batch UPDATE. Expected ~25-30 min on VPS for 2.35M rows.

Trade-offs accepted:
- New top-N is selective enough that SS hits will be rarer. By design — meaningful when they occur.
- Calendar-day windows mean baseline counts vary slightly (~22 trading days ≈ 30 cal days, less in holiday-heavy weeks). Real institutional behaviour aligns to calendar, not exchange schedule.
- 10 rows in /dvpt could feel noisy; if usage shows R-tier is rarely read, collapse it behind a flag later.

Doctrine § E updated. D28 and D29 still apply for everything else (menu, scoring framework). D30 still applies for the regex/chat-prompt hardening.

### D30 — Robustness pass: bare-ticker fast-path + chat-prompt hardening
Why: Session 15 deploy testing surfaced two real bugs:
1. Menu flow (`/menu` → Delivery flow → typed `BANDHANBNK`) did NOT route to /dvpt as intended. Bot replied with a Bloomberg-terminal-style hallucination ("I've got your delivery & momentum data loaded. What would you like to see? — Pattern analysis / Technicals / ..."). The `menu_pending` state machine somewhere along the way (PTB user_data lost, or never set, or a silent exception) failed silently; message fell through to chat handler.
2. Chat handler was happy to invent feature categories Hermes doesn't have (Pattern analysis, Technicals, Volume profile). D21 system prompt wasn't strict enough.

Fix shipped (D30, single commit):
- **Bare-ticker fast-path in `intent.py`.** Regex `^[A-Z][A-Z0-9]{2,14}$` — if the entire message is a single uppercase NSE-shaped token, skip the LLM classifier and return `{intent: "BOTH", ticker: <text>}` directly. Catches BANDHANBNK, RELIANCE, INFY, TCS, etc. Robust against intent-classifier misses AND `menu_pending` state loss. Saves a Gemini/Haiku call too.
- **Hardened HERMES_SYSTEM_PROMPT in `chat.py`.** Explicit list of what Hermes does NOT have (technical chart analysis, support/resistance, volume profile, intraday tick data, sentiment scoring). Explicit forbiddance of Bloomberg-terminal-style fake-menu offers. Explicit instruction: when a stock is named, point at /pt14 / /dvpt — never invent capabilities.
- **Diagnostic logging in `telegram_bot.py`.** `on_message` now logs `user_id`, text prefix, current `menu_pending`, and `user_data` keys. `on_menu_callback` logs when it sets `menu_pending`. Next reproduction will tell us definitively whether menu_pending is set/lost/raced.

Trade-off accepted: regex requires leading letter, so `360ONE` doesn't fast-path. Edge case — type lowercase or with prose and the LLM classifier handles it.

### D29 — Inline-keyboard menu system
Why: Command surface had grown to 17+ slash commands. Ramana surfaced (session 15) that he couldn't remember which command did what — a real discoverability bottleneck, not hypothetical. The standard Telegram-native fix is inline keyboards (`InlineKeyboardMarkup` + `CallbackQueryHandler` in python-telegram-bot). Pure button routing — zero LLM cost. Doesn't replace slash commands; sits alongside them as a discovery layer.
- New `/menu` command opens the root keyboard
- Tree: Quality (pt14) → ticker prompt · Delivery flow (dvpt) → ticker prompt · Market scan → 15/25/50 · Layered triggers → A+/SS/Near-break · Watchlist → Show/Add/Remove · Status (provider)
- "Back" buttons edit message in place to traverse up
- State machine via `context.user_data["menu_pending"]` for actions that need a ticker — next plain-text message is consumed as the ticker, then state clears. /menu cancels pending state.
- Reuses existing helpers (`_scan_top_dvpt`, `_scan_triggers`, `_format_scan_message`, `_format_triggers_message`, `_fetch_flow_rows`, `_format_flow_message`, scoring/screener) — no logic duplication.
- `/start` help text updated to point at /menu first, plain English second, slash commands third.
- All natural-language routing untouched. Slash commands untouched.
This is a discovery layer on top of existing functionality. If usage data after a week shows a button is never tapped, sunset it. Conversely if Ramana finds himself reaching for an action that isn't in the menu, add it.

### D28 — Two-tier DVPT trigger system (supersedes D26)
Why: D26's SS/S/A/B definition was asymmetric — only "1m+2m+3m, not 6m" counted as S; other 3-of-4 combinations silently graded as A or B. Ramana caught this in session 15. Also D26 used only 4 power baselines (P1M/2M/3M/6M); P12M was missing entirely, and the R-tier rolling averages were computed nightly but never surfaced to the user. The replacement:
- 5 R-baselines (R1M..R12M, flat rolling avgs at 22/44/66/132/264 trading days) + 5 P-baselines (P1M..P12M, top-N within those windows)
- Two pure-count scores: `r_score` and `p_score` (each 0–5)
- Rank derived purely from p_score: SS=5, S=4, A=3, B=2, C=1, '-'=0. No hidden window ordering.
- Near-break pointer: `next_p_above` + `gap_to_next_p_pct` — surfaces stocks within −10% of a P-line they haven't yet broken (the breakout-imminent signal)
- `/triggers` modes: default = rank A+, `ss` = SS only, `near` = breakout-imminent
- `/scan` sort updated: ATH → p_score → r_score → discount → r1m
- 14 new columns on `stock_signals` (5 R-tier, 1 new P12M, 2 scores, rank, 2 ATH/entry, 2 hot-day, 2 near-break) via `_ensure_column` migration
- `--backfill-triggers` mode (per-symbol bulk fetch + batch UPDATE) populates all D28 columns on the 2.35M historical rows; expected ~20-30 min on VPS
Full doctrine in § E above. Decision **D28 supersedes D26 and D27**; the session-14 spec is no longer canonical.

### D27 — D26 first-pass implementation (superseded same session by D28)
Why: Session 15 first shipped D26 as specified, then Ramana flagged the asymmetric-rank flaw and asked for richer baselines. The first-pass code was discarded before commit. D27 is preserved here as a flag that the in-conversation pivot happened; no code from this iteration exists on disk.

### D26 — Layered DVPT trigger system replacing single-ratio scan ranking (superseded by D28)
Why: Single-ratio (`ratio_today_vs_power_1m`) is an under-cooked signal. Ramana's specification (session 14): rank stocks by which power-baselines today's DVPT exceeds simultaneously. SS = above ALL 4 (1m, 2m, 3m, 6m). S = above 3 of 4. A = above 2 of 4. Plus orthogonal flags: ATH-DVPT (all-time high in stock's history), Discount Entry (current price below avg price during recent hot days). Full spec in Doctrine § E above. Schema needs 4 new columns on `stock_signals`. NOT YET IMPLEMENTED — first priority for next session. Decision documented now so the spec doesn't get lost.

### D25 — Cost-routing doctrine consolidation
Why: Sessions 13-14 surfaced a real conflict between my reflex (build API integrations) and Ramana's instinct (use subscription where possible). Three routing decisions (D13, D20, D22) collectively define a coherent doctrine, documented in detail in § A of the Doctrine section above. Future sessions: defend deviations from this doctrine with explicit reasoning, not silent drift. Especially: do NOT propose Sonnet via API. The claude.ai subscription handles this.

### D24 — Sector-adapted patearn scoring for financials (HFC/NBFC/bank)
Why: Session 14 AAVAS rationale work revealed that the standard patearn framework, designed for non-financial companies, misleadingly scores HFCs low. Multiple patterns (ROCE, Op Leverage, Balance Sheet) need adaptation for the leveraged-balance-sheet business model. Adaptation table is in Doctrine § D. Whenever Hermes scores a financial-sector stock, output must note that sector-adapted thresholds were applied. Worked example: AAVAS T3 under standard scoring (NS 46.3%, QG Fail), but the QG fail is structural to HFC business model — the "real" sector-adapted tier might be T2.

### D23 — ETF filtering on /scan and /dvpt outputs
Why: Session 14 /scan output was polluted with ETF/mutual-fund instruments (EBBETF0433, IVZINGOLD, METALIETF, etc.) that have DVPT signals but where the methodology doesn't apply (ETFs trade against NAV, not on institutional positioning). Need to filter symbol patterns: `LIKE '%ETF%' OR LIKE '%IETF%' OR LIKE '%GOLD%' OR LIKE '%SILVER%' OR LIKE 'MON%'` (Mirae Asset MF). Implemented in session 14.

### D22 — /analyze repurposed as a claude.ai workflow guide (no API call)
Why: Ramana correctly identified `/analyze` as a cost leak (~₹2-10 per call on Haiku/Sonnet) duplicating what claude.ai already does for free under his existing $20/mo subscription. This is the spirit of Decision D13 ("deep dives in claude.ai, not API") which `/analyze` had quietly violated. `/analyze` now prints a structured guide telling Ramana to copy `/pt14` + `/dvpt` output into claude.ai with the patearn skill loaded. Zero LLM call, zero cost. Slash menu description updated to flag the change. The command is preserved (not removed) so muscle-memory typing doesn't produce "command not recognised."

### D21 — SCAN intent + /scan command for market-wide top-N queries
Why: Session 14 caught a real gap — natural-language queries like "where did smart money go yesterday" were falling through to the chat handler, which made up generic Bloomberg-terminal answers ("I don't have real-time data") instead of using our 5-year delivery database. Two fixes:
  (a) New SCAN intent in `intent.py` for market-wide queries (no specific ticker named). Examples cover "where did smart money go", "top accumulation today", "biggest institutional buys", "exceptional delivery flows", "high conviction names", etc.
  (b) New `/scan [N]` command that runs a top-N SQL query against `stock_signals JOIN bhavcopy_rows` for the latest trading day, ordered by `ratio_today_vs_power_1m DESC`, with a ₹1 Cr turnover liquidity filter. Default N=15, cap 30. Verdict header counts how many hit Exceptional (>1.50) and Institutional (1.00-1.50) levels.
  (c) Chat handler's HERMES_SYSTEM_PROMPT updated to tell Hermes about the available data and to NEVER claim "no real-time data" — instead, route Ramana to /pt14, /dvpt, /scan, or natural-language equivalents. Prevents future "Bloomberg-terminal-style" hallucinations.

### D20 — Multi-provider LLM routing for classifier tasks
Why: Anthropic Haiku is excellent but expensive vs Gemini Flash for pure classification (intent routing + news category tagging). Gemini 2.0 Flash is ~13× cheaper ($0.075/$0.30 per M tokens vs $1/$5) at similar quality for JSON classification. Anticipating usage growth, the user requested cost-optimal routing. Implementation:
  - `src/core/llm_router.py` exposes `call_classifier(system, user_msg, max_tokens)` that routes to Gemini Flash if `GEMINI_API_KEY` is set in .env, otherwise Anthropic Haiku.
  - On Gemini failure, falls back to Anthropic automatically — user never sees a hard failure.
  - Uses OpenAI Python SDK pointed at Gemini's OpenAI-compatible endpoint (no extra dependency since openai SDK is light).
  - Chat (Telegram conversational) and /analyze (deep patearn) stay on Anthropic unchanged — quality matters there.
  - Refactored `src/assistant/intent.py` and `src/automation/news_feed.py` to use the router.
  - New `/provider` Telegram command shows which classifier provider is active.
  - Opt-in via .env only — no code change needed to enable.
Cost impact: if user enables Gemini, annual savings ~₹2,500/year at current usage; ~₹15-20K/year if usage grows 5×.

### D19 — Renamed /score → /pt14 and /flow → /dvpt
Why: Generic names ("score", "flow") hid the underlying methodologies. New names are methodology-tagged: `/pt14` for the patearn 14-pattern framework; `/dvpt` for Delivery Value Per Trade. Easier to remember, more accurate to what's being computed, and frees up the namespace for future "different scoring" or "different flow" commands. Slash menu updated; help text in /start updated; setup-news.sh deploy footer updated. Natural-language routing in `intent.py` unchanged (still SCORE/FLOW/BOTH intent types internally — those are just labels).

### D18 — Natural-language intent routing for plain text Telegram messages
Why: Ramana asked (session 14) for slash commands to be optional. Now plain text like "what's pixtrans?" or "score reliance" is classified by a tiny Haiku call and routed to /score, /flow, or BOTH automatically. Cost per message: ~₹0.10 for classification + ₹0 for the underlying lookups (rule-based). Implementation in `src/assistant/intent.py`. CHAT intent falls through to the existing chat-with-memory path unchanged. Slash commands still work for power users who prefer them.

### D17 — /flow command surfaces DVPT signal alongside /score (patearn)
Why: Session 14 closeout revealed a gap — the DVPT/power-deliveries signal data was being computed and stored nightly, but had no user-facing Telegram interface. /score only surfaced patearn-rule-based scoring. Now /flow gives a structured read on institutional delivery intensity for any stock: today's DVPT, power baselines (1m / 3m), ratio interpretation (Exceptional / Institutional / Approaching / Normal / Quiet), and a 15-day history table. Both signals are independent and complementary — patearn screens quality, DVPT signals positioning. Cost: ₹0 (pure SQL query, no LLM).

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

### 🔜 NEXT BUILDS — the Patearn DVPT picking-strategy program (the throughline, session 18 →)
Full plan + locked decisions: **`docs/dvpt-picking-strategy-design.md`** + **`docs/multi-timeframe-positioning-design.md`** (keep rich — binding doc-persistence rule). Sequence:
0. **⏳ IN PROGRESS at wrap — deep-history data foundation (D47)** building autonomously on the VPS (Stage-1 backfill pid 133884 → orchestrator `scripts/deep-foundation.sh` pid 134151 → Stage-2 recompute; a local watcher re-invokes the session on completion). **FIRST next-session task: verify it finished — `tail /var/log/hermes-foundation.log` for "ALL DONE" + the per-year coverage report (if "ABORTING", diagnose `/var/log/hermes-deepbackfill.log`) — then record the result here + the VPS deploy.** Note: VPS dashboard code is at `2bf4036`; origin is `a612c70` (parallel D41-P2 membership commit on top — deploy that too if not already).
1. **Multi-timeframe signal engine** — weekly/monthly **materialised** signals + a timeframe-parameterized compute (`multi-timeframe-positioning-design.md`). Weekly DVPT = Σ(deliv value)÷Σ(trades) per bar (never averaged). Unblocks weekly/monthly DVPT+RS everywhere AND the stock page's deferred #2/#3 (signals on weekly bars — the chart halves already shipped in D48).
2. **Ignition + intensity-ranking + `ranking_history`** (the picker) — design §2–3. Actionable gate = **unusually huge value + clear accumulation** (huge intensity ×, huge ABSOLUTE deliv ₹, clean ACCUMULATION); **Act vs Watch tiers — lesser-intensity is kept/browsable, never discarded.** Calls from Jan 2019; data already deep (~2004) for lookback + first-ever.
3. **`security_master` / universe-integrity** (survivorship by point-in-time bhav, symbol-rename stitching via ISIN, demerger/merger flags — the Vedanta problem; design §13) — **before** the backtest.
4. **Absolute full-journey backtest** (MFE/peak · MAE-from-signal · MAE-from-entry · fate) → DERIVE target / stop / averaging. No benchmark (indices have no delivery).
5. **Champion (rules) vs challenger (offline classical ML, ₹0 at run-time).** LLMs = offline research aids you validate, never in the live loop.

Side items: **bulk/block-deals ingester** (NSE `/api/historical` needs a browser cookie handshake — the only named buyer/seller + side feed; design §9.1); **`/dash/stock` perf profile** (post-backfill — the ~3.5s route); **phased Hermes→Patearn user-facing rename** (labels first); **B5** zones-on-adjusted-price; **Telegram** still network-blocked.
⚠ **Working-tree discipline:** two Claude sessions shared `D:\Hermes` today and cross-absorbed each other's `git add`s (caught, nothing lost). Next session: be the SOLE session on this tree (or use a worktree); always `git diff --cached --name-only` before commit; never `git add -A`.

### ✅ COMPLETED in session 14 (formerly IN-FLIGHT)

1. ✅ **setup-news.sh deployed on VPS** — session 11+12+13 code is live
2. ✅ **5-year bhav copy backfill executed** — 1,297 trading days from 2021-05-24 to 2026-05-28, 1,296 with delivery (sec_bhavdata_full). 2,356,143 EQ rows across 3,051 stocks.
3. ✅ **Signals fully computed** — 2,350,570 rows in stock_signals across 3,051 stocks × 1,237 days. (The 60-day gap from bhav copy days is expected — those are the early dates where the rolling 365-day window can't be computed.)
4. ✅ **sqlite3 CLI installed on VPS** (was missing from Ubuntu base image; now auto-installed by setup-news.sh and vps-bootstrap.sh — see commit 96f9649)
5. ✅ **Bhav copy timer moved from 6:00 PM IST to 7:30 PM IST** (Decision D16, commit c292e47)

### Other open items (queued, in priority order)

**🟢 P0 — Operational reconciliation (RESOLVED in session 16, 2026-06-17):**

- ✅ **Git identity fixed.** Was `ramana-debug <cirqlelife@gmail.com>` (inherited from the global `C:/Users/gotti/.gitconfig`, a different project's identity). Now set **repo-local** to `Ramana Gottipati <gottipati.ramana@gmail.com>` (global + other repos untouched). The 4 unpushed commits re-authored via `rebase --exec "git commit --amend --reset-author --no-edit"`. Already-public D28–D32 left as-is (destructive rewrite declined). **Canonical git identity for this repo going forward = `Ramana Gottipati <gottipati.ramana@gmail.com>`, repo-local.**
- ✅ **GitHub credential fixed.** Removed the `git:https://github.com` (User: CirqleLife) entry from Windows Credential Manager (`cmdkey /delete:git:https://github.com`); GCM (helper = `manager`) re-authed as `ramana-gottipati`.
- ✅ **Dashboard work pushed.** `716f702..ec5d34c` — D33-web PWA (`6c05e31`) + D36 enriched stock view (`9c707f5`) + P0 doc note (`96ac05f`) + new `.gitignore` for Drive `.tmp.drive*` sync junk (`ec5d34c`). On GitHub under the correct identity.
- ✅ **VPS reconciled.** `/opt/hermes` was git@716f702 + scp'd untracked `src/web/*` + modified `src/main.py`. Verified all 3 byte-identical to the pushed blobs (hash check — nothing lost), then `stash -u` + fast-forward → VPS HEAD `ec5d34c`, clean. (NOTE: plain `git stash && git pull` would have FAILED — `src/web/*` were untracked on the VPS and block the pull; must use `stash -u`.) Safety snapshot in `stash@{0}` (vps-scp-snapshot-s16).
- ✅ **D32 indexes.** Timer wiring was already present — in fact duplicated (a prior session double-appended the ExecStart lines); deduped to single clean copies (`10-signals.conf` = `signals → indexes → index_signals`). The actual gap was the **5-year index backfill, never run** — now run as a chained detached job (`indexes --backfill 1830 && index_signals --backfill`). `index_rows` = 143,319 rows / 1,244 days (2021-06-02→2026-06-16); `index_signals` (ratios + trend_state) computing → `/sectors` + dashboard sector view populate on completion.

**✅ P0 — RESOLVED session 19 (D49g):**

- **`/dash/compare` chart — BOTH bugs FIXED**, verified hands-on in the live browser (Chrome MCP), exactly as the note below demanded. ONE root cause: boot ran before lightweight-charts' first layout settled. **(1) Left-edge rebase:** `setRange` set the correct deterministic anchor (1Y → `2025-06-11`) but a layout-settle `subscribeVisibleTimeRangeChange` re-anchored everything to a transient mid-window date (observed `2026-02-05`) after `internalSet` cleared → **fix:** gate the fluid pan-reanchor on genuine user input (a `userInteracted` flag set by `wheel/pointerdown/mousedown/touchstart` on the chart host); buttons/pin still anchor explicitly, settle-time events are inert. The `rightOffset:3` / `getVisibleRange`-lag / short-series-`commonAnchor` hypotheses were red herrings. **(2) Gutter names empty:** `positionNames()` ran before `priceToCoordinate()` laid out (returned null) → **fix:** bounded `requestAnimationFrame` retry until each label places. Verified: fresh load + all 4 ranges (each anchors to its own left edge) + a short 4th series (Nifty India Defence). Full write-up: § Decision log **D49g**. (The detailed symptom notes just below are now historical — kept for the record.)

**🔴 P0 — still open:**

- **`/dash/compare` chart — TWO bugs the user still reports UNRESOLVED (session 18, D49b–D49f).** I iterated on these BLIND (canvas/DOM rendering can't be curl-verified — only `py_compile` + route-200 + reading the source), and the user confirms both are still wrong. **Next session MUST debug hands-on (browser devtools / live screenshots), not by reading code.**
  1. **Rebase-to-base-100 at the visible LEFT EDGE is still off.** Symptom: "REBASED FROM `<date>`" shows a date that is NOT the visible window's left edge, so lines don't all start at 100 at the left. Data verified: the 3 indices (Nifty 50/500/Realty) span 2021-06-02→2026-06-18 (1246 rows); the 1Y left edge is **2025-06-11**, but it anchored at 2025-12-26 then 2025-09-26 across attempts. Tried (D49d) a `bootAnchor()` reading `getVisibleRange()` (failed — lags a frame), then (D49e) made `setRange` anchor to the deterministic `allT[len-n]` + seed under `internalSet` to kill a setData-auto-fit race. STILL reported broken. Hypotheses to check live: `rightOffset:3` shifting the real visible edge vs `allT[len-n]`; `commonAnchor(edge)` returning a later date if a series (India Defence, ~1087 rows, newer) lacks data exactly at `edge`; a late `subscribeVisibleTimeRangeChange` re-anchoring after boot. The RS-overlay chart's `reanchorToView()` boot pattern works — compare to it.
  2. **Line-name labels.** Want: **value badge on the Y axis + the line's NAME in a right gutter, vertically aligned to that line's value** (NOT on the chart covering lines, NOT only in the bottom legend). D49f built this (`#cmpNames` 104px gutter + `positionNames()` using `series.priceToCoordinate(v)`, de-collision ≥13px, "Nifty " prefix stripped). The latest screenshot showed the gutter labels rendering and roughly aligned (India Defence/500/50) — but the user still says "not resolved", so either the alignment is visually off, the stripped names aren't wanted, or they're conflating it with bug #1. **Get a precise restatement from the user.** If good, replicate to the D48 stock RS-overlay chart for consistency.
- **Telegram bot network block** — `api.telegram.org` unreachable from the Mumbai VPS (DPI throttling). Bot crash-loops. Decided session 16: **wait** (web dashboard is the working alternative). Revisit proxy / Hostinger ticket only if it persists.
- **SSH rate-limit discipline** (standing operational rule) — never hammer `ssh hermes` on failure (triggers a port-22 IP ban). One attempt; on timeout, wait or restart the router for a fresh IP.

**🔴 P1 — Next builds:**

A. ✅ **Two-tier DVPT trigger system** (D28) — shipped.
B. ✅ **Telegram menu system** (D29) — shipped.
B2. ✅ **Web dashboard + PWA** (D33-web) — shipped (live on VPS via scp; not yet pushed to GitHub — see P0).
B3. ✅ **Enriched stock view** — charts + corporate-action adjustment (D36) + DVPT inertia + insights + pt14 snapshot — shipped (live on VPS via scp).

B4. ✅ **D33 stock-level Relative Strength — COMPLETE (the third strategy pillar).** D33a (s16, stock-vs-broad + 1–99 rank) + D33b (s17, stock-vs-sector) + D33c (s17, composite "strong-in-strong" leaders/laggards). All backfilled & deployed: `/dash/stock` shows broad + sector RS; `/dash/leaders` + a Home preview surface the leaders/laggards; `/rs` `/leaders` `/laggards` Telegram commands added (bot still network-blocked). ✅ `stock_rs` now wired into the nightly `10-signals.conf` chain (after `membership`) so broad+sector+rank stay current — the s17 sub-item is closed.

B5. **Move corporate-action back-adjustment to a reusable pipeline layer + recompute zones on adjusted prices.** ⏳ **Half done (session 17):** the reusable layer now exists — `src/automation/adjust.py` (`adjusted_closes`/`adjustment_factors`, the verbatim D36 logic), already consumed by D33a's `stock_rs.py`. **Still open:** (a) unify the dashboard's inline D36 copy to call `adjust.adjusted_closes` (currently duplicated); (b) recompute the institutional ZONES (avg_close_*) on adjusted prices in `signals.py` — they're still computed from raw closes, so they're off-scale when an action falls in the zone window (the ⚠ warning).

B6. ✅ **pt14 fundamentals caching for the dashboard** — SHIPPED as **D46** (session 18). `src/automation/score_batch.py` keeps the SURFACED names (watchlist / news candidates / conviction / RS leaders) scored — bounded, prioritized, throttled, TTL-respecting, so it honors D8 (not a bulk scrape). Daily `hermes-pt14batch` timer. The Conviction shortlist's ★ quality + the stock-page pt14 card now populate.

B7. ✅ **Dashboard macro→micro redesign Phase 1 + index membership** — SHIPPED (D38). Markets major/bundle split, Stocks hub, Home regime overview, header search everywhere, sector→stock drill (via populated `stock_index_membership`). **Phase 2 pending:** stock-RS card on the stock page (needs D33), breadcrumb + section reorder, inline sparklines, pt14 batch scoring (B6), click-sort on the bundle.

B8. **Positioning pillar — deepening, item by item.** ✅ **Item 1 (D43): accumulation/distribution CHARACTER** — SHIPPED (session 18). ✅ **Item 2 (D44): value-weighted institutional key price + multi-horizon near-key entry + ticket/surge + one-screen workbench** — SHIPPED (session 18, additive, no regression). **Future items (NOT built):**
  - **NSE bulk & block deals direction feed** — the only public source that names buyer/seller + side (trades >0.5% of equity, reported with counterparty + BUY/SELL). The lone GROUND-TRUTH for the WHICH-WAY axis that delivery data can only infer from price; would *confirm* (not just infer) accumulation vs distribution on names where a block printed. Free daily CSV from NSE.
  - **Fiscal-quarter / week-number grain** (parked from the D44 spec) — bucket signals by NSE fiscal quarter + ISO week for quarter-over-quarter / week-over-week reads. ⚠ NOTE: `docs/multi-timeframe-positioning-design.md` exists but its "D42/D43" labels PREDATE the now-shipped D42 (equity allowlist) and D43 (character) — **renumber those references when that multi-timeframe layer is actually built** so the decision numbers don't collide.
  - **Saved-query alerts** (parked from the D44 spec) — let a saved screen/query notify when a stock newly enters it (e.g. newly 🎯 near-key, or newly ACCUMULATION). Pairs with the D41-Phase-3 saved-screener/query-builder.
  - **EWMA key-price variant** (parked from the D44 spec) — `key_price_ewma_p*` (exponentially-weighted toward recent power days) as an explore-alongside to the WMA `key_price_p*` deliverable.
  - Other candidates: promoter/FII/DII quarterly-holding deltas, F&O OI/PCR cross-check for the largest names.

C. **Portfolio / strategy tracker** (real gap surfaced in session 14):
```sql
CREATE TABLE stocks_in_play (
    id INTEGER PK,
    symbol TEXT NOT NULL,
    strategy TEXT,           -- 'patearn' / 'dvpt_institutional' / 'manual' / 'discount_entry'
    date_added TEXT,
    entry_thesis TEXT,
    entry_price REAL,
    price_target REAL,
    stop_loss REAL,
    current_status TEXT,     -- 'active' / 'hold' / 'exit'
    exit_date TEXT,
    exit_reason TEXT,
    notes TEXT
);
```
Commands: `/track TICKER [strategy] [thesis]`, `/portfolio`, `/exit TICKER reason`, `/performance` (hit-rate by strategy). Daily monitor: 8 AM IST digest with each holding's day-change + delivery + r1m.

**🟡 P2 — Worth doing but not urgent:**

C. **ETF filter refinement** — current filter is pattern-based. Could maintain a small `is_etf` flag in `bhavcopy_rows` for cleanliness. Low priority — current pattern match catches 95%.

D. **Pattern 11 (VCP) and 14 (Volume breakout) full scoring** — currently use DVPT proxy; could be richer with explicit ATR + 50-day moving average data from bhav copy. Quick win.

E. **Pattern 12 (Receivables) + 13 (Working capital)** in `scoring.py` — need Screener balance sheet time series parsing.

F. **Telegram digest enrichment** — surface ROCE / NS / ratio_today_vs_power_1m per row in digest instead of just symbol.

G. **/candidates web page edit-in-place** — add inline status update (Reviewed / Picked / Passed). Currently read-only.

**🟢 P3 — Long-term / parked:**

H. **NSE corporate-announcements poller** — authoritative earnings trigger (currently news-based). Designed but not built.

I. **Kite Connect intraday** — ~₹500/mo when Ramana wants real-time alerts.

J. **Voice messages** — Whisper STT + ElevenLabs/OpenAI TTS. ~3 hours.

K. **Sector adaptation in scoring.py** — implement Doctrine § D adaptations as code (currently noted only in documentation; scorer applies standard thresholds).

L. **MCP server on VPS** — would let claude.ai query Hermes data directly via the Anthropic connector framework. ~2-3 hours setup. Eliminates copy-paste workflow between Telegram and claude.ai.

---

## Session log (reverse chronological — newest at top)

### Session 19 — 2026-06-19 — D49g: fixed the two session-18 P0 /dash/compare chart bugs (hands-on browser debug)

Resumed after the session-18 handoff. First, confirmed (read-only) the deep-history foundation is mid-build on the VPS: **Stage-1 raw bhav copy is COMPLETE** (2004-07-23→2026-06-18, 5,411 trading days, 9.33M rows) and **Stage-2 `signals --backfill` is ~55%** (3,029 / 5,490 dates, at ~Oct 2016, ETA ~12-14h). Noted the `corp_actions` step 404'd on all four NSE URLs this run (0 split/bonus rows — flagged for when the foundation lands). Did NOT disturb the running backfill.

Then fixed the **two P0 `/dash/compare` chart bugs** D49b–f left unresolved (full write-up: **§ Decision log D49g**). Debugged hands-on in the live browser via the Chrome MCP (navigate + JS DOM probes + screenshots) — which cracked it after the prior blind `py_compile`/route-200 loop. Both shared one root cause (boot acting before the chart's first layout settled): the correct left-edge rebase was overridden by a settle-time `subscribeVisibleTimeRangeChange` (**fix:** gate fluid re-anchor on real user input via a `userInteracted` flag), and the gutter name labels were computed before `priceToCoordinate()` was ready (**fix:** bounded rAF retry). Verified across a fresh load, all four range windows (each anchors to its own left edge), and a short 4th series (Nifty India Defence). Deployed `src/web/dashboard.py` via `scp` + `systemctl restart hermes-api`; committed [`ddf7640`](https://github.com/ramana-gottipati/hermes/commit/ddf7640). Then **D49h**: replicated the right-gutter name labels onto the D48 stock RS-overlay chart — and discovered it had the SAME boot-anchor drift (mis-anchoring to ~2026 instead of the 2021 series start, despite being the supposed "working reference"); fixed both with the deterministic earliest-anchor + the same `userInteracted` gate. Verified on RELIANCE.

### Session 18 (continued) — 2026-06-18 — D49f compare chart: right-gutter name labels (value on axis | name just outside, per line)
What Ramana actually wanted all along: each line's NAME sitting just outside the chart's right edge, vertically aligned to its value badge (value stays on the Y axis). Built it on `/dash/compare`: reserved a 104px right gutter (`#compareChart{margin-right}` + an absolute `#cmpNames` layer), and a `positionNames()` JS fn that, for each line, reads its last value's pixel via `series.priceToCoordinate(v)` and drops a colored HTML label at that Y in the gutter — with a simple de-collision nudge (≥13px apart) and the "Nifty " prefix dropped for brevity. Repositioned on every rebase (rAF after applyRebase), range/layout change (subscribeVisibleTimeRangeChange), and resize. Value badges stay native on the axis; bottom crosshair-value row kept. **Compare chart only for now — pending the user's visual confirmation of alignment before replicating to the D48 stock RS-overlay chart** (can't curl-verify canvas/DOM positioning). `py_compile` clean; gutter + positionNames wired; route 200.

### Session 18 (continued) — 2026-06-18 — D49d compare/RS-overlay chart polish (line-name labels + initial-rebase fix)
Two more chart observations from Ramana: (6) on the overlay charts the right-axis last-value badge showed just the number (e.g. 97.59) — he wanted the line's NAME on it too so it's self-identifying without the legend. Set the lightweight-charts series `title:s.name` on BOTH the `/dash/compare` chart and the D48 stock RS-overlay chart, so each line's name shows at its last value (alongside the value); the bottom legend stays. (NOTE: the library shows name + value at the line end; the exact "value | name" pipe ordering he sketched isn't directly formattable without a custom per-series price formatter, which would pollute the shared axis gridline labels — so `title` is the clean approach.) (7) BUG on `/dash/compare`: on first load the lines weren't rebased to base-100 at the visible left edge until you panned. The compare boot relied on `setRange`'s rAF-gated `scheduleRebase`; the RS-overlay's boot already force-calls `reanchorToView`. Fixed by adding an explicit `bootAnchor()` after `setRange` that reads the laid-out `getVisibleRange()` (retrying on rAF until ready) and force-rebases to its left edge. Render-only; no schema. Shipped `6b48ac0` — **but BOTH parts needed correction (next entry).**

### Session 18 (continued) — 2026-06-18 — D49e fix the two D49d regressions (label overlap + rebase STILL wrong)
Ramana reported D49d didn't land: (6-fix) the `title:s.name` labels rendered as badges ON the chart, **covering the lines** — he wants names OUT of the plot, values on the Y axis only. Reverted `title` on both charts → value badges stay on the axis, names live in the bottom legend (outside the plot). (7-fix) the rebase was STILL anchored mid-window (`REBASED FROM 2025-12-26` on a 1Y view whose left edge is 2025-06-11). Root cause confirmed by data: all 3 indices span 2021-06→2026-06 (1246 rows), 1Y left edge = **2025-06-11**, but the code anchored off `getVisibleRange()` which lags a frame on first layout. **Real fix:** `setRange` now anchors to the window's KNOWN deterministic left edge `allT[len-n]` (not `getVisibleRange`) and applies directly; AND the boot seeds data under `internalSet` so `setData`'s auto-fit range-change can't schedule a stray rebase that overrides the anchor (the race that pinned it mid-window). Panning still re-anchors fluidly. Verification: `py_compile` clean; `title` gone (0), deterministic `commonAnchor(edge)` present, `bootAnchor` removed; routes 200. (Rendered rebase still needs the user's eyes — canvas.)

### Session 18 (continued) — 2026-06-18 — D49b /dash/compare UX (default benchmarks + multi-add)
Ramana's feedback on the compare page (D40): (1) entering Compare from a sector should default to the sector **+ Nifty 50 + Nifty 500** (the broad benchmarks, like the stock-page narrow-vs-broad overlay), removable; was sector-only. Fixed the `/dash/ratio` "Compare ⇄" link to seed `idx=<sector>&idx=Nifty 50&idx=Nifty 500` (route already dedups + caps at 6). (2) The "+ Add" picker added one index per click+reload; he wanted to add several at once. Reworked the picker JS to **multi-select** — suggestion chips are now toggle buttons that stage a Set, and an "**Add N**" button navigates once with all picked appended (respects the 6-cap; search-box dynamic results are toggles too). Removed the now-dead `_add_href`. (3) Rebase-to-visible-start (base 100 from the first visible day) already works as he wanted — no change. Render-only in `dash_compare`/`dash_ratio` fbar; no schema. **Shipped & deployed:** commit **`5fb6bd8`** (pushed); pulled on VPS, `hermes-api` restarted. Verified live: the ratio Compare link now emits `/dash/compare?idx=Nifty+Bank&idx=Nifty+50&idx=Nifty+500`; the picker renders toggle `<button>`s + the "Add N" confirm (zero one-add `<a href>` links remain); routes 200.

**D49c (more compare feedback):** (4) "Why max 6?" — no technical limit; the cap was a palette/readability choice. Raised `_COMPARE_MAX` **6 → 12**, extended the palette to 12 + a `_cmp_color(i)` golden-angle-HSL fallback so ANY count renders distinctly (the cap can be bumped freely). (5) "Remove the Base 100/Base 0% toggle — handle like the stock RS chart." Done: removed the toggle + its handler; the chart is now **always base-100** (`(v/anchor)·100`), the exact convention the D48 stock RS-overlay uses (each line starts at 100, 122 = +22%); renamed the mode button `Rebased % → Rebased`; updated help text. Render-only. **Shipped & deployed:** commit **`54d62ac`** (pushed); pulled on VPS, `hermes-api` restarted. Verified live: an **8-index** compare renders 200 with 8 distinct series colors (past the old 6-cap), zero Base-toggle markup remains, "Rebased" + indexed-to-100 help present.

### Session 18 (continued) — 2026-06-18 — D49 index page → one-stop view + constituent RS
Ramana, on `/dash/ratio`, asked to see the index's OWN today's movement (it only showed RS, never the index's price row) and for the constituents to carry relative-strength-vs-the-index, keeping DVPT. Shipped (render-only in `dash_ratio`, no schema): an **index snapshot header** (today close/Δ/OHLC + volume/turnover + PE/PB/div-yield from `index_rows`; returns 1d–12m + 50/200-DMA + 52w-position from `index_signals`); and **constituents now carry CMP/Δday + RS rank + adjusted 3m return (`accum_price_drift_3m`) + "vs idx" = stock 3m − index 3m return** (positive = outperforming the index), all constituents, default-sorted by DVPT, now a sortable/filterable/exportable `.dt` table. DVPT kept primary. Distinct route from the concurrent session's D48 (stock page + screen rows) — numbered D49 (D48 taken). Built after that session went on hold (no collision). **Shipped & deployed:** commit **`16ec687`** (pushed); pulled on VPS, `hermes-api` restarted. Verified live: `/dash/ratio?idx=Nifty Bank` & `Nifty India Defence` render 200 with all new sections (Today snapshot / Returns / Technicals / Turnover / RS rank / vs idx). Real-data sanity (Nifty Bank, 3m index ret +8.49%): IDFCFIRSTB vs_idx **+15.6** (3m +24.1%), FEDERALBNK +11.5, AXISBANK +4.5 outperforming; CANBK **−9.6** (3m −1.1%), BANKBARODA −7.4 underperforming — `vs_idx = stock 3m − index 3m` checks out exactly. DVPT cols intact.

### Session 18 — WRAP (2026-06-18) — Patearn rebrand direction · D47 deep-history foundation (building) · D48 dashboard enrichment · the DVPT picking-strategy program
The session that set the **forward program**. Much of it is design + an autonomous data build still running at wrap — so this entry is the handoff.

**Rebrand:** Hermes → **Patearn** (patearn.in, "pattern + earn"). "**Hermes**" now means ONLY the Nous agent (D34) — never this product. Phased: **user-facing labels first**; code/paths/services/repo/DB deferred. DVPT / RS / 14-Pattern are *strategies, not brands*.

**The picker program — DVPT-only first, vanilla (no strategy mixing).** Full design + the WHY in **`docs/dvpt-picking-strategy-design.md`** + **`docs/multi-timeframe-positioning-design.md`** — KEEP RICH (Ramana's explicit, binding instruction: never reduce the strategy intent to one-liners; design §14). Locked decisions:
- **Ignition** = first time a stock clears ALL its power-DVPT baselines (all-stars), ranked by **intensity of the cross** (today DVPT ÷ avg power baseline). Multi-horizon (D/W/M/Q).
- **Actionable gate (Ramana: "unusually huge value + clear accumulation"):** (1) huge intensity (≥~5×/10×), (2) huge ABSOLUTE delivery ₹ (a thin stock's big *ratio* on tiny rupees must NOT qualify — intensity AND absolute footprint both huge), (3) clean **ACCUMULATION** (D43). Strictness cuts ~4,000 → ~30–40. **Lesser-intensity is NEVER discarded — stored + browsable (Act vs Watch tiers).**
- **Calls from Jan 2019** (to include the COVID black-swan) but **data backfilled DEEP (~2004)** so 2019 calls have full 12-month lookback + true first-ever detection (**data window ≠ call window**).
- **Backtest** = absolute full-journey (MFE/peak = best exit, MAE-from-signal, MAE-from-entry, eventual fate) → DERIVE target / stop / averaging. **No benchmark** (indices carry no delivery → no DVPT for them). **Champion (rules) vs challenger (offline classical ML, ₹0 at run-time).** LLMs (Nous Hermes / claude.ai) = offline research aids you validate, NEVER in the live decision loop (doctrine).
- **Universe integrity (design §13):** survivorship-by-construction (point-in-time bhav incl. delisted) + `security_master` (ISIN-keyed rename stitching) + demerger/merger flags (the Vedanta problem). Build before the backtest.

**D47 — deep-history data foundation (code SHIPPED; data BUILDING at wrap).** Probed NSE reachability from the laptop: `sec_bhavdata_full` delivery only 2020→present, BUT the legacy **MTO `.DAT` ⋈ legacy `cm*bhav`** reconstructs delivery back to **≥2004** (legacy carries close + num_trades + ISIN); indices ~2013; bulk/block `/api` returns 503 (handshake deferred). Shipped the MTO merge in `bhavcopy.py` (`_mto_url`/`_parse_mto`/`_merge_mto` + an additive block in `ingest_date`; 2020+ path + schema untouched; validated 2015-02-13 = **1507/1507 merged, 0 qty mismatches**, ISIN captured). Added `scripts/probe_data_reachability.py`. **RUNNING AUTONOMOUSLY ON THE VPS AT WRAP:** `bhavcopy --backfill 8000` (pid 133884, 2004→ forward, `/var/log/hermes-deepbackfill.log`) → `scripts/deep-foundation.sh` orchestrator (pid 134151, `/var/log/hermes-foundation.log`) which waits for Stage-1, verifies earliest≈2004, then runs **Stage-2 full recompute** (corp_actions → `signals --backfill` → `--backfill-triggers` → `--backfill-keyprice` → indexes/index_signals → `stock_rs --backfill`) so EVERY derived column fills 2004→present and `is_ath_dvpt` / first-ever re-evaluate across ALL years (incl. existing 2021–2026 — Ramana's "adjust the later values too"). A local background watcher re-invokes this session when pid 134151 exits.

**D48 — dashboard enrichment + WAL perf (SHIPPED + deployed).** See decision D48. Trigger+stealth boards + `/dash/stocks` rows now carry CMP·Δday·DVPT·**×power**·Deliv₹; `/dash/stock` gained a traded+delivery pane + an RS-overlay chart (stock vs narrow vs broad, D/W/M/Q toggle); **SQLite WAL** killed the 3–7s clicks (→0.03–0.12s).

**Commits (mine):** `f745edc` (D47) · `5e1314f` (board enrich + WAL) · `ff8581d` (stealth/screen mirror) · `2bf4036` (stock-page charts — ⚠ this `git add` also bundled the parallel session's uncommitted `dashboard.py` REAL_SECTORS/empty-state edits; verified intact, nothing lost). Parallel session shipped the D41-P2 membership fix on top → **origin HEAD = `a612c70`**. VPS dashboard at `2bf4036` (deploy `a612c70` next to pick up the membership constituents).

**⚠ HAZARD — two sessions on one working tree:** my session and a parallel session both ran on `D:\Hermes` today; `git add <file>` swept the other's uncommitted edits twice (caught, re-verified, nothing lost). **Next session: be the SOLE session on this tree, or use a git worktree. Always `git diff --cached --name-only` before commit; never `git add -A`.**

**NEXT (kickstart handed to Ramana) — see § NEXT BUILDS:** ① verify the foundation finished + record coverage → ② MTF signal engine → ③ ignition+ranking+ranking_history → ④ security_master → ⑤ backtest → ⑥ champion/challenger ML. Plus bulk/block-deals, `/dash/stock` perf, the phased rename.

### Session 18 (continued) — 2026-06-18 — Fix: India Defence/Private Bank/Chemicals sector drill (D41-P2 membership gap)
Ramana noticed `/dash/stocks?sector=Nifty India Defence` showed "0 constituents" + a misleading "it's a factor/thematic index" message. Root cause (verified on VPS): the index has price/RS data (1,087 `index_rows`) and was whitelisted as a real sector in D41, but its CONSTITUENT list was never loaded — `membership.py` fetched 21 indexes and these 3 weren't among them (the deferred D41-Phase-2 "add missing sectors to membership" item). Fixed: added the 3 to `membership.py` `INDEX_CONSTITUENTS` (probed the irregular niftyindices slugs: `ind_niftyindiadefence_list`/`ind_nifty_privatebanklist`/`ind_niftychemicals_list` → 19/10/20 members) + to `REAL_SECTORS`; and corrected the empty-state to distinguish a real sector with unloaded membership ("constituents not loaded yet") from a genuine factor index (was mislabeling all 0-constituent indexes as "factor/thematic"). ⚠ **Parallel-session interleave (audit note):** the `dashboard.py` half of this fix (the `REAL_SECTORS` +3 and the empty-state if/else) was **absorbed into a concurrent session's commit `2bf4036`** ("feat(web): stock page traded+delivery pane + RS overlay") — same working tree, their `git add` swept in my uncommitted `dashboard.py` edits. Verified intact + correct + compiling, just bundled under their message; nothing lost. The `membership.py` + this doc are the separate (correctly-attributed) commit. This is the second clean-but-risky interleave today → **two sessions on one working tree must serialize** (lesson logged). Deploy: pull + membership refresh of the 3 + restart api; verify the drill populates — see deploy note.

### Session 18 (continued) — 2026-06-18 — D47 deep-history data foundation (MTO ⋈ legacy delivery → DVPT to ~2005)
Scoped the **DVPT-only auto-picking program** (ignition = first all-stars cross ranked by intensity-of-cross, multi-horizon D/W/M; absolute full-journey backtest → derive target/stop/averaging; champion vs offline-ML challenger) — full design in **`docs/dvpt-picking-strategy-design.md`** + `docs/multi-timeframe-positioning-design.md`. **Probed NSE reachability from the laptop:** delivery via `sec_bhavdata_full` only to 2020, but via **MTO `.DAT` ⋈ legacy `cm*bhav` ≥ 2005**; indices ~2013; bulk/block `/api` 503 (needs browser handshake). Added `scripts/probe_data_reachability.py`. **Shipped + validated the MTO ⋈ legacy delivery-merge** in `bhavcopy.py` (additive; 2020+ path + schema untouched) → DVPT reconstructable to ~2005 (2015-02-13: 1507/1507 merged, 0 qty mismatches, ISIN captured). Decided the **Hermes → Patearn** rebrand (phased, user-facing first; "Hermes" = the Nous agent only). Locked: data window ≠ call window; full-history recompute (ATH/first-ever re-evaluated across ALL years incl. 2021–2026 once old data lands); survivorship-by-construction + `security_master`/demerger handling (design §13); the doc-persistence rule (design §14 — never one-line the strategy intent). See decision **D47**. Next: VPS deep backfill (staged: raw bhav+MTO → ~2005, then full-history recompute).

### Session 18 (continued) — 2026-06-18 — D46 batch pt14 scoring (lights up the Quality pillar; honors D8)
Building D45 surfaced that the Quality pillar was dark — the Conviction shortlist read pt14 from `pattern_scores`, which only exists for manually-`/pt14`'d names (both conviction names showed `unscored`). Shipped `src/automation/score_batch.py`: keeps the SURFACED names (watchlist → recent news `screen_candidates` → conviction → RS leaders) scored, reusing the rule-based `scoring.score_symbol` (no LLM). Carefully built to HONOR D8 ("over time, not bulk"): prioritized (surfaced set only, cap 300 — not the ~2,400 equity list), incremental (skips names scored within the 7-day TTL), bounded (≤`--limit`/40 real Screener scrapes per run), throttled (`--throttle`/2.5s after each scrape). Fresh-cached names re-score locally with no network. Daily `hermes-pt14batch` systemd timer. Closes B6.

**Shipped & deployed:** code commit **`e8e99ab`** (pushed to `main`); FF-pulled on the VPS. Real run verified: **25 surfaced names, 25 scored, 0 failed** in ~66s (polite, no Screener blocks). The Quality pillar is now LIT — the conviction names that showed `unscored` now carry their pt14 tier: **GLAND → T4** (NS 39.4), **ZYDUSLIFE → T3** (NS 45.5), neither hard-disqualified; `pattern_scores` now covers 32 symbols. Timer installed + enabled (`OnCalendar=*-*-* 15:30:00` UTC = 9 PM IST daily; `ExecStart=/opt/hermes/.venv/bin/python -m src.automation.score_batch --limit 40`; logs to `/var/log/hermes-pt14batch.log`) — next run Thu 2026-06-18 15:30 UTC. (Units are VPS-side per project convention; the OnCalendar + ExecStart above make them reproducible.)

### Session 18 (continued) — 2026-06-18 — D45 cross-pillar Conviction shortlist (the synthesis)
With all three pillars now built — RS (D33), Positioning character + key price (D43/D44), Quality (pt14) — shipped the payoff: ONE decision-ready shortlist of names where every pillar aligns. `stock_rs.conviction_shortlist()` (one shared read helper, DRY): RS LEADER by the D33c 3-layer test AND `accum_character='ACCUMULATION'` (D43), enriched with the D44 entry read (near-key / discount) and pt14 quality as a ★ CONFIRMATION (LEFT JOIN, not a gate — pt14 coverage is sparse). Strongest leaders first; liquid universe. **Read-only** (a JOIN/filter over already-computed columns, like `leaders_laggards`) — no schema, no backfill, fast deploy.

Surfaced: NEW `/dash/conviction` (sortable/filterable/exportable `.dt` + 🎯 near-key / ★ quality filter pills) + a ⭐ Conviction preview board on Home (right after the Strategies hub — the headline) + the `/conviction` Telegram command (same helper). Realizes the Conviction-shortlist half of D41's Phase-3 roadmap.

**Shipped & deployed:** code commit **`1a94343`** (pushed to `main`); FF-pulled on the VPS, `hermes-api` restarted (active). No schema/backfill (read-only). Real-data check on 2026-06-17: the shortlist returned **2 genuinely-aligned names** — GLAND (Nifty Pharma, RS rank 83, ACCUMULATION, near-key +1.9%) and ZYDUSLIFE (Nifty Healthcare, rank 65, ACCUMULATION, near-key −1.5%): both are RS leaders in a leading sector, being accumulated, AND at a buyable entry near the institutional key price. A TIGHT list is by-design (conviction is rare; the intersection of strict RS-leader ∩ ACCUMULATION is small — 233 ACCUMULATION names that day, very few of which are also 3-layer RS leaders); the empty-state handles 0 gracefully. `/dash`, `/dash/conviction` HTTP 200. If a looser "conviction watchlist" tier is ever wanted (e.g. RS leader OR rs_rank>80), that's a future tweak — the strict list ships first.

### Session 18 (continued) — 2026-06-18 — D44 value-weighted key price + multi-horizon entry + workbench (additive)
Borrowed the genuinely-useful ideas from an external "Delivery Per Order Screener" spec and shipped them **strictly additively** (the user's hard non-regression requirement). The fix: D31's flat `avg_close_p*` zone equal-weights *close* on the top-N power days, so the BIG institutional day doesn't dominate the cost line and the day's *avg_price* (where shares actually traded) is ignored. D44 adds, without touching any existing column: ① **value-weighted `key_price_p*`** (Σ price·deliv-value ÷ Σ deliv-value over the same top-N power days, priced at avg_price); ② **`gap_to_key_p*`** + an asymmetric **near-key** band derived on read (`_KEY_BAND=(-1,+5)` — price at/just-above institutional cost); ③ **ticket size** (avg_trade_qty, avg_deliv_qty_per_trade); ④ **turnover surge** (1m/3m/1y). 15 new `stock_signals` columns.

Approach (non-regression): a SEPARATE compute block in the per-symbol pass reusing the already-fetched window rows (zero change to D28/D31/D43 paths); a SEPARATE `--backfill-keyprice` that UPDATEs ONLY the 15 columns (never re-runs `--backfill-triggers`). Surfaced: `/dash/stock` key-price section beside the flat zones; `/dash/stocks` 🎯 near-key pill + Workbench link (existing screen/markers unchanged); NEW `/dash/workbench` (wide sortable/exportable table reusing `_DT_JS`); `/dvpt` 📍 key-price block. Parked (open items B8): fiscal-quarter/week grain (+ the `docs/multi-timeframe-positioning-design.md` D42/D43 renumber note), saved-query alerts, EWMA key-price.

Verification: 4 modules `py_compile` clean; synthetic unit test PASSES the value-weighting spot-check (biggest power day cheapest ⇒ key 82.95 vs equal-weight 117.0) + asymmetric band + ticket/surge; dashboard routes (incl. `/dash/workbench`) HTTP 200.

**Shipped & deployed:** code commit **`d6195c3`** (pushed to `main`); FF-pulled on the VPS, `hermes-api` restarted (active). **Regression gate PASSED (ship-blocker)** — snapshot of 5 symbols before/after `--backfill-keyprice`: **73 existing columns byte-identical**, 15 new columns added, 6,250 rows populated. Full `--backfill-keyprice`: **3,053 symbols / 2,384,778 rows (~7 min** — lighter than D43 since no adjusted-close build). Real-data spot-check (2026-06-17, 2,427 rows; key_price_p3m on 100%, 1,161 near-key): ① value-weighting demonstrably repositions the cost line vs the equal-weight `avg_close_p12m` in BOTH directions — AQYLON key 142.1 vs avgclose 301.4 (−52.8%, its biggest power day far cheaper), MCX −29.2%, vs SILVERTUC/COCKERILL +30–60% (big day expensive); ② near-key gaps all within [−1%,+5%] (ASHOKLEY +0.7%, CCL −0.0%, FINPIPE +4.0%); ③ ticket size sane (deliv/trade ≤ trade qty always); ④ surge discriminating (0.4×–55×). **All spec verification steps satisfied.** (Known carry-over: key/avg_close zones use raw close → a split inside the window shows a pre-split key, e.g. SILVERTUC close 195 vs key 1137 — the SAME property the existing D31 zones have; addressed by open item B5 zones-on-adjusted-price, not a D44 regression.)

### Session 18 — 2026-06-18 — D43 DVPT accumulation/distribution CHARACTER (Positioning pillar, item 1)
Deepened the Positioning signal with the one thing the R/P trigger system structurally cannot tell you: delivery data is **side-blind** (every delivered share was simultaneously bought AND sold), so a high p_score is equally consistent with a strong hand *accumulating* and a strong hand *distributing into a retail bid*. Built a 3-axis read — **WHO** (trade-count breadth + delivery-₹ trend + delivery %), **WHICH WAY** (adjusted-price drift + value-weighted up/down delivery skew — price is the only direction-revealer), **CONTEXT** (52w-high distance + p_score persistence) — into 7 stored numerics + a derived `accum_character` label (ACCUMULATION/DISTRIBUTION/CONSOLIDATION/NEUTRAL). Store-the-raw/derive-the-flag (Doctrine C): thresholds are tunable and re-derivable via `--relabel-character` with no measure recompute. Scope-disciplined to this ONE pillar item; RS + Quality untouched.

Shipped (decision **D43**; kickstart called it "D42" but that number was taken by the equity-allowlist work, so it's D43):
- **`signals.py`** — shared label brain (`_char_flags`/`accum_character`/`accum_character_read`) + metric compute (`_ret_signs`/`_character_metrics`/`_character_arrays`), reusing `adjust.adjusted_closes` so splits can't fake a down-day and excluding |daily-return|>0.30 corp-action anomalies. Folded into BOTH the live `compute_signals_for_symbol_date` (fetch extended to 372 cal days for the 52w high; now pulls `prev_close`+`deliv_per`) and the `--backfill-triggers` per-symbol pass (+8 fields in the same batch UPDATE). New `--relabel-character` mode.
- **`db.py`** — 8 new `stock_signals` columns + `idx_signals_accum_character`.
- **`dashboard.py`** — `/dash/stocks` Character + Total-deliv columns + 🟢Accumulation/🔴Distribution filter pills (compose with the `.dt` grid via `data-*` + the existing `sflt` filter); weekly/monthly carry latest-day character; `/dash/stock` Accumulation-character panel (label + plain-English read + up/down bar + WHO row + 52w distance + ⚠️ distribution-while-high warning); Home Stealth-accumulation board + Character pill on Top-trigger-stocks; `_PILLARS["POS"]` thesis updated.
- **`telegram_bot.py`** — `/dvpt` 🧭 Character block; `/scan`+`/triggers` Ch glyph; `/triggers accum|distrib` modes; `/start` + `BOT_COMMANDS` updated. Same shared label helper (DRY).

Verification: all 4 modules `py_compile` clean; the label rule + metric/anomaly logic unit-tested synthetically (markup⇒ACCUMULATION, quiet base⇒ACCUMULATION/absorption, broadening-near-highs⇒DISTRIBUTION, split-day excluded from the skew, all boundaries pass); db migration adds the 8 cols + index; dashboard routes return HTTP 200.

**Shipped & deployed:** code commit **`e3d345d`** (pushed to `main`); FF-pulled on the VPS, `hermes-api` restarted (active), `hermes-telegram` left as-is (still network-blocked — bot code is on-disk, goes live when Telegram is reachable). Full `--backfill-triggers` run on the VPS: **3,053 symbols / 2,384,778 rows** (~30 min, non-destructive UPDATE — RS columns preserved). Real-data verification on 2026-06-17 (2,427 rows): character distribution is SANE across all buckets — NEUTRAL 1575 · CONSOLIDATION 481 · ACCUMULATION 233 · DISTRIBUTION 22 · null 116 (insufficient history). DISTRIBUTION names match the signature (GENCON p=5 down-skew 0.38 drift −12%; GLAXO broadening 1.23 + down-skew; PASHUPATI broadening 1.57 while price −10%; SBICARD down-skew 0.57). ACCUMULATION names = concentrated + active + turning up off a base (HIKAL/MPSLTD/LEMONTREE p=5, deep below 52w-high). `/dash/stock` with the new panel renders 200. **All spec verification steps satisfied.** Future Positioning item flagged: NSE bulk & block-deals direction feed (B8).

### Session 17 (continued) — 2026-06-17 — D42 equity-only scanners (ETF exclusion)
Ramana flagged ETFs leaking into the equity scanners. The D23 name-pattern filter was leaky (44 ETFs slipped through on the latest day — ALPHA/BFSI/DEFENCE/IT/MAFANG/HDFCNIFTY/GROWW*…) and also wrongly dropped real equities (GOLDIAM, MONARCH). Diagnosed that `sec_bhavdata_full` carries no ISIN (column entirely NULL), so the INE/INF split wasn't available — switched to a **symbol allowlist** from NSE `EQUITY_L.csv`.

Shipped (decision **D42**): new `nse_equity_list` table + `src/automation/equity_list.py` (fetch EQUITY_L.csv, ~2,374 equities; replaced only on a successful fetch, never wiped on failure); all three scanner filters (`dashboard._SCAN_FILTERS`, `stock_rs._LIQUID_FILTER`, `telegram._SCAN_FILTERS_SQL`) now use `s.symbol IN (SELECT symbol FROM nse_equity_list)` instead of the leaky `NOT LIKE` patterns; `equity_list` wired into the nightly chain before `stock_rs`; `rs_rank` recomputed over the equity-only universe (1.29M rows). Verified live: scanner has 0 non-equity symbols / 0 ETF leakers; GOLDIAM now correctly allowed. A separate ETF section (EQ-series symbols not in the allowlist) is a small follow-up if wanted. Deployed scp + restart.

### Session 17 (continued) — 2026-06-17 — D41 strategy-surface redesign Phase 1
After the RS pillar (D33b/c), Ramana asked to (1) separate & **label** the strategies, (2) be able to **build his own queries**, (3) reorganise Home + show only **real sectors** (Nifty High Beta dead-ended with no constituents), (4) get DVPT triggers on a **weekly** basis (not just today — else a mid-week spike is missed). Ran a **4-perspective design panel** (financial + data + UI/UX + architect), presented a pointer proposal (Phases 1–3), and shipped **Phase 1** (decision **D41**), deferring the registry refactor / materialised weekly table / screener to Phases 2–3.

Shipped (`dashboard.py` only — render-only, no schema/backfill):
- Strategy thesis **badges** on every board + a **Strategies hub** (3 pillar cards w/ live counts) on Home → "click a strategy, it shows up."
- **Sector curation:** rotation views (`/dash/sectors`, `/dash/rs`, Home) filtered to a `REAL_SECTORS` whitelist (+ India Defence); factor/thematic indices no longer pollute or dead-end (graceful "see ratio chart" empty-state on the drill).
- **Weekly/Monthly DVPT trigger toggle** on `/dash/stocks` — rolls up the last 5/22 trading days (days-fired + peak rank, on-read) so mid-window spikes aren't missed; Daily stays default.
- Verified live: all 7 affected routes HTTP 200; High Beta absent from /dash/sectors (Nifty Bank present); weekly view + factor empty-state render. Deployed scp + restart.

Next: D41 **Phase 2** (materialised `weekly_signals`; the missing-sectors-in-membership half is now DONE — India Defence/Private Bank/Chemicals loaded), **Phase 3** (saved-screener/query-builder — **the Conviction-shortlist half SHIPPED as D45**). Then B5, Telegram unblock. (B6 pt14 batch = D46, done.)

### Session 17 — 2026-06-17 — D33b stock-vs-sector RS + D33c leaders/laggards (third pillar COMPLETE)
Built **D33b** (stock-vs-sector RS) then **D33c** (composite "strong-in-strong" leaders/laggards) — closing the third strategy pillar (Relative Strength). Full design in the **D33b** + **D33c** decision-log entries.

Shipped (one commit — code + this doc):
- **`src/core/db.py`** — 10 new `stock_signals` columns (`primary_sector` + `rs_vs_sector_today` + `rs_vs_sector_slope_{1m,3m,6m,12m}` + `rs_vs_sector_above_50ma/above_200ma/new_52w_high/trend_state`) via `_ensure_column`; index `idx_signals_primary_sector(trade_date, primary_sector)` for the D33c join.
- **`src/automation/stock_rs.py`** — EXTENDED (not a new module) with the sector pass: `primary_sector_map()` (narrowest NSE sectoral index per stock — fewest members, size/broad excluded via D32's `SIZE_BASED_INDEX_NAMES`, alphabetical tiebreak), `_sector_close_maps()`, `compute_symbol_sector_rs()` (REUSES `build_rs_history` + `compute_ratio_signal` — same adjusted-price path as broad), `run_sector_backfill()`, `compute_sector_for_date()` (nightly, wired into `compute_for_date`). CLI: `--sector-backfill`; `--symbol` prints broad+sector; `--backfill` does both.
- **`src/web/dashboard.py`** — `/dash/stock` RS card now shows broad (vs Nifty 500, with the 1–99 rank gauge) AND sector (vs the stock's narrowest sector) — two trend pills + two heat strips + a reconciliation table extended with sector-return + RS·sector columns. Graceful broad-only fallback when the stock has no NSE sector.
- **Verification:** logic unit-tested locally on a synthetic 2:1 split (sector RS continuous across the split — adjust.py flows through; narrowest-sector + tiebreak + size-exclusion correct). Live on VPS: HDFCBANK→Nifty Bank, RELIANCE→Nifty Oil & Gas; `--sector-backfill` did **209 symbols / 237,716 rows in ~70s** (the other membership symbols are broad/size-only → NULL primary_sector → broad-only, by design); `/dash/stock?sym=HDFCBANK` HTTP 200 rendering both blocks. Deployed via scp + `systemctl restart hermes-api`.

Then **D33c** (same session — composite "strong-in-strong" leaders/laggards):
- **`src/automation/stock_rs.py`** — `leaders_laggards(kind, limit)` shared read helper: a LEADER has stock-vs-sector RS AND stock-vs-broad RS AND its sector's own RS-vs-broad (D32 `index_signals`) ALL in {UPTREND,BREAKOUT}; a LAGGARD all in {DOWNTREND,BREAKDOWN}. Liquid universe; leaders by rs_rank DESC, laggards ASC. Used by BOTH the dashboard and the bot (DRY).
- **`src/web/dashboard.py`** — new **`/dash/leaders`** route (Leaders + Laggards as sortable `dt` boards: symbol · RS rank · sector · the 3 trend pills) + a **"Strong-in-strong leaders" preview** on Home (top 5 → the board).
- **`src/assistant/telegram_bot.py`** — **`/rs TICKER`** (broad RS + 1–99 rank + sector RS + leader/laggard verdict), **`/leaders`**, **`/laggards`** (top 30), in BOT_COMMANDS + the handler table. Bot still network-blocked from the Mumbai VPS — code is live; commands register when Telegram is reachable.
- **Nightly currency fix:** `stock_rs` was NOT in the `10-signals.conf` systemd chain (broad+sector+rank would have gone stale after today). Added it as the last `ExecStart` (after signals/indexes/index_signals/membership); validated `run_today` = 2427 broad + 204 sector RS + 1404 ranked for 2026-06-17 in ~40s. (D35 chain note updated.)
- **Verified live:** leaders WELCORP/POWERINDIA/THERMAX/BHEL (Energy/Metal, rank 92–97); laggards HCLTECH/TCS (IT), SBICARD/HDFCLIFE (Fin Svcs), PATANJALI/UBL (FMCG). `/dash/leaders` + `/dash` + `/dash/stock` all HTTP 200; telegram_bot imports clean with the 3 new handlers.

**Third strategy pillar (Relative Strength) COMPLETE:** D32 (sector vs broad) + D33a (stock vs broad + rank) + D33b (stock vs sector) + D33c (composite). Data layer + dashboard live; Telegram pending network.

Commits: **`f0ba915`** (D33b) + the D33c commit (this). Next: B5 (unify dashboard's inline adjustment to call adjust.py + zones-on-adjusted-price), B6 (pt14 caching for the dashboard), Telegram network unblock.

### Session 16 — WRAP (2026-06-17, very large session) — P0 reconciliation + D38/D39/D40/D33a + UX
The longest session yet. Cleared the entire session-15 P0 operational backlog AND shipped the third strategy pillar (relative strength) end-to-end — data layer + dashboard. Detailed per-phase entries are below; this is the index.

**Arc — 16 commits, `716f702 → 0adcf5d`, ALL authored `Ramana Gottipati <gottipati.ramana@gmail.com>`:**
- `6c05e31` D33-web PWA + `9c707f5` D36 enriched stock view — the session-15 work, re-authored to the correct identity and finally pushed.
- `96ac05f` / `ec5d34c` / `31b64f3` — P0 git-identity reconciliation + `.gitignore` (Drive junk) + doc.
- `03c2f0a` — **D32 fix**: `index_signals` NSE title-case match (the "0 ratio pairs" bug — sector RS / `/sectors` was empty until this; index backfill had been run but produced no ratios).
- `7d4500f` — **D38** macro→micro dashboard (5-tab nav, header search everywhere, Home regime overview, `/dash/markets` major-vs-bundle split, `/dash/sectors` drill, `/dash/stocks` hub) + `stock_index_membership` backfill (new `membership.py`; 21 indices, 1,305 rows, 511 symbols).
- `96964c3` / `2837a63` — **D39** RS ratio analysis (1m/3m/6m/12m heat strip, RETURN-vs-RS column groups, `/dash/ratio` per-index ratio chart, `/dash/rs` cross-sector ranking).
- `4f684f4` / `f836aee` / `806fea6` — **D40** `/dash/compare` multi-index rebase chart (fluid anchor, ratio↔rebased toggle) + the chart **range-switch perf fix** (3-chart sync ping-pong reentrancy guard).
- `eb7f38e` — **D33a** stock-vs-broad RS + 1–99 percentile rank: new `adjust.py` (reusable corp-action adjustment) + `stock_rs.py`; 10 new `stock_signals` columns; backfilled **2.37M RS rows / 1.37M ranked**. Verified: PARAS continuous across its split; RS = exact relative return (HFCL/MTARTECH rank 99, RELIANCE/TCS bottom).
- `d9c642f` on-page RS reconciliation table · `7b6af7e` chart hover crosshair readouts · `0adcf5d` data-grid toolbar (sort / filter / **Export-to-Excel(CSV)** / row-count / sticky header) on the 4 query tables.

**Final state:** HEAD = origin/main = VPS `/opt/hermes` = **`0adcf5d`**, all working trees clean (except the long-dormant uncommitted `patearn.py` diff — D7/D22 conflict, leave alone). Two 5-perspective agent design panels were run (D39, D40), documented in `docs/rs-ratio-analysis-design.md`.

**Next:** **D33b** (stock-vs-sector RS via the populated `stock_index_membership`) → **D33c** (composite "strong-in-strong" leaders/laggards + `/rs` `/leaders` `/laggards` + a dashboard leaders board). Telegram bot still network-blocked from the Mumbai VPS (waiting).

### Session 16 (continued) — 2026-06-17 — D33a stock-level Relative Strength (stock-vs-broad RS + rank)
Built the **D33a** slice of the third-pillar RS spec (D37): stock-vs-broad (Nifty 500) relative strength as a real data layer — new reusable adjustment module + schema columns + a compute pipeline + the dashboard RS card. **Deployed + verified before backfill:** `--symbol PARAS` confirmed the split-adjustment holds in the RS series — rs_vs_broad is **continuous across PARAS's 2025-07-04 split** (0.0365→0.0364→0.0346, no cliff); RELIANCE reads sane (DOWNTREND, lagging the market). Then the full `--backfill` was run over 3,053 symbols (~3.7M rows + the cross-stock percentile pass). py_compile clean; split-adjustment + rank SQL also unit-verified in-memory.

Shipped:
- **`src/automation/adjust.py`** (NEW, pure/no-DB) — the single source of truth for the split/bonus back-adjustment, extracted verbatim from the dashboard's D36 inline copy (`PC_THRESH=0.03` prev_close-deviation primary layer; `CC_THRESH=0.30` close-jump fallback; backward-cumulative factor). `adjusted_closes(rows)` + `adjustment_factors(rows)`. (Closes the *reusable-layer* half of open item B5; the dashboard's inline copy can be unified to call this next, and zones-on-adjusted-price is still pending.)
- **`src/core/db.py`** — 10 new `stock_signals` columns via the idempotent `_ensure_column` pattern: `rs_vs_broad_today`, `rs_vs_broad_slope_{1m,3m,6m,12m}`, `rs_vs_broad_above_50ma`, `rs_vs_broad_above_200ma`, `rs_vs_broad_new_52w_high`, `rs_vs_broad_trend_state`, `rs_rank` (1–99). New index `idx_signals_rs_rank ON stock_signals(trade_date, rs_rank)`.
- **`src/automation/stock_rs.py`** (NEW) — the pipeline. `BROAD="Nifty 500"` (title-case). Per symbol: full EQ bhav history → `adjusted_closes` → `rs_history=[{adj_close/n500_close}]` on dates in BOTH series → REUSES `index_signals.compute_ratio_signal` for the slopes/MA-flags/52w-high/trend_state → **UPDATEs** the existing stock_signals row (never INSERTs). Then a SQL `PERCENT_RANK()` percentile pass over the liquid universe (same filter as signals/dashboard) on a blended `0.6·slope_3m + 0.4·slope_6m` → `rs_rank` 1–99 (only rows with slope_3m NOT NULL). CLI: `--symbol X` (full series + prints latest 5 days for spot-check), `--date YYYY-MM-DD`, `--backfill`, `--rank-only`.
- **`src/web/dashboard.py`** — replaced the `/dash/stock` "Relative strength" placeholder with a real section: a `trend_state` pill, an **RS rank gauge** ("RS 73 / 99 — stronger than 73% of the market", reuses `.bar`), and the **4-cell heat strip** (reuses `_rs_strip` on the 4 rs_vs_broad slopes). Muted "RS not yet computed — run stock_rs backfill" note while the columns are NULL. `s.*` in the stock query already exposes the new columns — no query change. **Plus a per-window reconciliation table** (the stock's own return | Nifty 500's return | the resulting RS, for 1m/3m/6m/12m) so RS ≈ stock − Nifty-500 is verifiable directly on the page — stock return from the adjusted `series`, Nifty 500 return from its `index_signals.ret_*` (same 30/90/180/365-day windows); compute-on-read, no new storage. The **stock chart** (`/dash/stock`) and **ratio chart** (`/dash/ratio`) also gained a **hover crosshair value readout** above the chart (stock: date + O/H/L/C + DVPT + delivery%, fed by all 3 synced panes via `subscribeCrosshairMove`; ratio: date + ratio + 50/200-MA) — always-on, shows the latest day when the cursor is off-chart. (The `/dash/compare` chart already had one.) The four **query-result tables** (`/dash/stocks` screen, `/dash/rs`, `/dash/sectors`, `/dash/markets` bundle) gained a reusable **data-grid toolbar** (`_DT_JS`, opt-in via `class="dt"`): click-to-sort columns (numeric-aware, asc/desc), a text filter, **Export to Excel (CSV)** of the currently-visible rows, a live row count, and a sticky header. Pure client-side (no deps); composes with the existing filter pills via a `.dt-hide{display:none!important}` class so pill + text filters AND together and export skips hidden rows.

Still pending: B5's zones-recompute-on-adjusted-price + unifying the dashboard's inline D36 adjustment to call `adjust.py`. **Next D33 phases:** **D33b** (stock-vs-sector RS via the now-populated `stock_index_membership`) and **D33c** (composite "strong-in-strong" leaders/laggards + `/rs` `/leaders` `/laggards` Telegram commands + a dashboard RS-rank leaders/ranking view).

Next: D33b (membership + stock-vs-sector RS), then D33c (composite leader/laggard + `/rs` `/leaders` `/laggards`).

### Session 16 (continued) — 2026-06-17 — Multi-index comparison/rebase chart + chart perf fix (D40)
Ramana asked for a normalized multi-index comparison (overlay indices rebased to a common start, fluid anchor on pan, ratio↔rebased toggle) and flagged chart range-switching as slow. 2nd 5-agent panel (financial + data + UI/UX + architect); design in `docs/rs-ratio-analysis-design.md` Part 2 (**D40**); built by a focused build agent.

Shipped (`dashboard.py` only — render-only):
- **`/dash/compare`** — overlay ≤6 indices, client-side rebase (base 100/0%), fluid anchor (pan → re-anchor) + 📅 pin, Mode Rebased%↔Ratio, range buttons, vs-50/500, chip picker + search + presets, live "REBASED FROM <date>" label + crosshair value row. Entry: "Compare ⇄" on `/dash/ratio` + "⇄ Compare indices" on Markets/Sectors.
- **Chart perf fix** — root cause found: `/dash/stock`'s 3-chart range-sync ping-pong (no reentrancy guard) + ResizeObserver re-layout. Fixed with a `syncing` guard + direct `setRange` to all charts + debounced ResizeObserver; `/dash/compare` fluid rebase is rAF-coalesced + anchor-gated.
- All routes verified HTTP 200 on real data (ratio mode, idx validation, empty state), no regressions, no errors. Live via scp + restart; committed + pushed + VPS reconciled. **Commits:** `806fea6` (D40 code + initial PROJECT_STATE.md D40 entries), `4f684f4` (design doc, Part 2); the routes-table + route-placement rationale + hash citation = this follow-up doc-sync.

Next: **D33 stock-level RS** (the third-pillar build) remains the big open item.

### Session 16 (continued) — 2026-06-17 — RS ratio analysis: multi-timeframe trend + ratio charts (D39)
Ramana pushed for deeper RS insight — the dashboard mixed absolute return with relative strength, hid the timeframe behind one "UPTREND" label, and had no ratio charts. Convened a **5-perspective panel** (quant + equity-practitioner + data + UI/UX + architect), documented the design in `docs/rs-ratio-analysis-design.md` (**D39**), then built Phase A + Phase-B-on-read.

Shipped (`dashboard.py` only — no schema change, no backfill):
- **RETURN vs RELATIVE-STRENGTH column groups** + the **4-cell 1m/3m/6m/12m heat strip** (`_rs_strip`) on Home/Markets/Sectors — disambiguates absolute-vs-relative and shows the trend per timeframe at a glance.
- **`/dash/ratio?idx=&den=`** ratio chart (ratio line + 50/200-MA + up/down-cross + new-RS-high markers + range + vs-50/500 toggle + RS-momentum percentile gauge + abs×rel quadrant + auto-READ + constituents).
- **`/dash/rs`** cross-sector RS-momentum ranking (on-read).
- Key finding: the IT-0.5-vs-Bank-2.0 normalization worry was **already solved** (slope_*_pct are % changes); just surfaced + labeled it. Cross-sector ranking done on-read — skipped the stored-column backfill as unnecessary.
- Implemented by a focused build agent against the design doc; all routes verified HTTP 200 on real data (incl. size-index + unknown-index guards), no regressions, no errors. Live via scp + restart; committed + pushed + VPS reconciled.

Next: **D33 stock-level RS** (the third-pillar build) remains the big open item.

### Session 16 (continued) — 2026-06-17 — Analyst dashboard redesign (macro→micro) + index membership
After the P0 reconciliation, Ramana flagged the dashboard wasn't analyst-grade: ~150 indices dumped together (no major-vs-bundle split) and stocks undiscoverable. Ran a **3-agent design pass** (data analyst + equity analyst + UI/UX), synthesized a macro→micro blueprint, and built **Phase 1 + the index-membership backfill** (Decision **D38**).

Shipped:
- `src/automation/membership.py` (NEW) — NSE constituent fetch → `stock_index_membership` populated (21 indices, 1,305 rows, 511 symbols). Verified slugs + exact index-name matches against `index_rows`.
- `src/web/dashboard.py` — 5-tab nav (Home/Markets/Sectors/Stocks/Stock), header search on every page, Home regime overview, **/dash/markets** (Major-vs-bundle split — the headline ask), **/dash/sectors** drill links, **/dash/stocks** hub (screen + filter pills + watchlist + sector filter).
- All routes verified HTTP 200, no errors; **sector→stock drill works** (Nifty Bank → HDFCBANK/ICICIBANK). Market currently reads RISK-OFF on the new banner.
- Deployed via scp + `systemctl restart hermes-api`; git committed + pushed + VPS reconciled.

Next: **D33 stock-level Relative Strength** (the real third-pillar build, spec D37) — fresh focused session.

### Session 16 — 2026-06-17 — P0 operational reconciliation (git identity, push, VPS sync, D32 index backfill)

No new product features — this was the "clean up the session-15 operational mess" session. The entire 🔴 P0 backlog is cleared.

**Git identity (the CirqleLife footprint):**
- Root cause: the global `C:/Users/gotti/.gitconfig` was `ramana-debug <cirqlelife@gmail.com>` (a *different* project's identity), stamping every Hermes commit. The remote was already correct (`ramana-gottipati/hermes` — nothing ever went to CirqleLife).
- Set **repo-local** `user.name="Ramana Gottipati"`, `user.email="gottipati.ramana@gmail.com"` (Ramana supplied the email; global + other repos untouched).
- Re-authored the 4 unpushed commits with `git rebase origin/main --exec "git commit --amend --reset-author --no-edit"`. The dormant `src/assistant/patearn.py` diff (stage1_screen + use_sonnet — D7/D22 conflict) was stashed around the rebase and restored **untouched / still uncommitted** — left alone per prior sessions.
- Removed the blocking `git:https://github.com` (User: CirqleLife) entry from Windows Credential Manager (`cmdkey /delete`); the push then re-authed through GCM (helper=`manager`) as `ramana-gottipati` (completed an interactive "Connect to GitHub" dialog).
- Did **NOT** rewrite the already-public D28–D32 history (destructive force-push declined).

**Pushed:** `716f702..ec5d34c main -> main`. New SHAs (all `Ramana Gottipati <gottipati.ramana@gmail.com>`): `6c05e31` (D33-web PWA), `9c707f5` (D36 enriched stock view), `96ac05f` (P0 doc note), `ec5d34c` (`.gitignore` Drive `.tmp.drive*` junk).

**VPS reconciled:** verified the scp'd `src/web/*` + `src/main.py` byte-identical to the pushed blobs (hash check), then `stash -u` + fast-forward → `/opt/hermes` HEAD now `ec5d34c`, working tree clean. Safety snapshot kept in `stash@{0}` (vps-scp-snapshot-s16). Caught that the kickstart's `git stash && git pull` plan would have failed (untracked `src/web/*` block the pull) — used `stash -u`.

**D32 index data (the real reason `/sectors` was empty):** the systemd timer wiring was already there (and duplicated — deduped `10-signals.conf` to a single clean `signals → indexes → index_signals`). The missing piece was the **5-year index backfill**, never run. Launched chained: `indexes --backfill 1830 && index_signals --backfill`. `index_rows` populated to **143,319 rows / 1,244 days / 2021-06-02→2026-06-16**; `index_signals` per-index level signals computed for all 1,244 days. **BUT a bug surfaced on verification:** the first `index_signals --backfill` produced **0 ratio pairs** (ratio_rows/ratio_signals stayed empty) — `index_signals.py` hard-coded UPPER-case benchmark names (`NIFTY 500`) while NSE's `ind_close_all` CSV stores TITLE case (`Nifty 500`), so every sector-vs-broad denominator lookup missed and `is_size_based` never matched. **Fixed (session 16):** `BROAD_BENCHMARKS`/`DEFAULT_BROAD` → title case + size-exclusion made case-insensitive (`name.upper() in SIZE_BASED_INDEX_NAMES`); re-ran `index_signals --backfill` → ratios populate → `/sectors` works. **⚠ Lesson for D33 RS (D37):** NSE index/stock names are title-case in this data — any name matching must normalize case.

**Telegram bot:** still network-blocked from the Mumbai VPS (unchanged; not our bug). Defaulted to **wait** — web dashboard remains the working surface.

**Next:** D33 stock-level Relative Strength (spec D37) — a fresh focused session. Hard dependency unchanged: move the corp-action back-adjustment into a reusable layer + recompute zones on adjusted prices (open item B5).

### Session 15 (continued, very long) — 2026-06 — Web dashboard, charts, corporate-action adjustment, Nous Agent on VPS, RS design

This is the same session 15, which ran extremely long and shipped far beyond the D28–D32 trigger work. **Read this whole block — it captures the current operational state, several non-code infra changes, and unresolved items.**

**🔴 CRITICAL OPERATIONAL STATE (read first):**

1. **GitHub push is BLOCKED.** Windows Credential Manager on the laptop has a cached `CirqleLife` GitHub credential that overrides `ramana-gottipati`. `git push` fails with 403 "Permission to ramana-gottipati/hermes.git denied to CirqleLife." **Fix:** Win → Credential Manager → Windows Credentials → remove the `git:https://github.com` (CirqleLife) entry → re-auth as ramana-gottipati. Until fixed, nothing reaches GitHub.

2. **GitHub origin/main is at `716f702` (D32).** Local main has `d8bfa6a` (D33-web, the PWA dashboard) committed but **not pushed**. On top of that, **all the dashboard enrichments below are uncommitted local edits to `src/web/dashboard.py`** (charts, corp-action adjustment, DVPT inertia, insights, pt14 snapshot, RS placeholder).

3. **VPS `/opt/hermes` is a DIVERGED state:** git repo at `716f702`, PLUS files copied directly via `scp` that are NOT in git: `src/web/__init__.py`, `src/web/dashboard.py` (the full enriched version), and `src/main.py` (dashboard router wired in). **A `git pull` on the VPS will conflict.** Reconciliation plan: fix the credential (#1), commit the dashboard work locally, push, then on VPS `git stash && git pull && git stash drop` (the stashed scp'd files are identical to the committed ones).

4. **Deployment method this session was `scp` + `systemctl restart hermes-api`** (not git), because of #1. Single-command: `scp /d/Hermes/src/web/dashboard.py hermes:/opt/hermes/src/web/dashboard.py && ssh hermes 'systemctl restart hermes-api'`.

5. **VPS SSH (port 22) intermittently rate-limit-bans the laptop IP** after rapid retries (brute-force protection). Symptom: `ssh hermes` → "Connection timed out" while port 443 (dashboards) stays up. **Confirmed it's VPS-side IP ban, NOT the laptop network** (`ssh git@github.com` works fine). Fix: stop all SSH attempts (each can reset the ban timer), wait ~30-45 min, OR restart the home router for a fresh dynamic IP (worked this session). **Do NOT hammer SSH on failure.**

6. **Telegram bot is NETWORK-BLOCKED from the VPS.** `api.telegram.org` is unreachable from the Mumbai datacenter (both IPv4 and IPv6 time out at a consistent ~4s — DPI throttling of Telegram, common in India), while general internet works. The bot crash-loops on `telegram.error.TimedOut` during `get_me()`. It was intermittent (worked some hours, failed others). **Not our bug.** Options: wait (auto-recovers when Telegram reachable), proxy the bot's Telegram traffic, or Hostinger ticket. **The web dashboard is the working alternative** and needs no Telegram.

**What shipped this session block:**

- **D33-web — installable PWA dashboard** (commit `d8bfa6a`, NOT pushed; live on VPS via scp). `src/web/dashboard.py` + `src/web/__init__.py`, wired into `src/main.py`. Views: `/dash` (overview), `/dash/sectors` (D32 rotation), `/dash/scan` (D28/D31 triggers), `/dash/stock?sym=X` (per-stock). PWA: `/manifest.webmanifest`, `/sw.js` (cache `hermes-v2`), `/icon.svg`, `/dash/offline`. Dark theme, mobile bottom-nav. Read-only, no LLM.

- **HTTPS via Caddy** — installed Caddy v2.11.4 on VPS. `/etc/caddy/Caddyfile`: `srv1704897.hstgr.cloud { reverse_proxy localhost:8000 }` (market dashboard) + `srv1704897.hstgr.cloud:9443 { reverse_proxy 127.0.0.1:9119 }` (Nous agent). Auto Let's Encrypt cert for the Hostinger hostname `srv1704897.hstgr.cloud` (which publicly resolves to the VPS IP — confirmed via 8.8.8.8). Caddy + hermes-api enabled on boot. **Market dashboard: `https://srv1704897.hstgr.cloud/dash`** — installable as PWA.

- **Enriched stock view (`/dash/stock`)** — major rebuild, all live on VPS via scp:
  - **Interactive charts** (lightweight-charts v4.1.3 from CDN): candlestick price + DVPT histogram (institutional-intensity days in amber) + delivery% line, time-synced, range buttons 3M/6M/1Y/2Y/Max (default Max = full history). Query loads up to 1300 trading days (5y).
  - **Corporate-action back-adjustment** (splits/bonuses) — TWO-layer detection: (a) primary = `prev_close[i]/close[i-1]` deviation >3% (NSE adjusts prev_close on ex-dates); (b) **fallback** = any single-day close jump >30% that prev_close did NOT flag (a real 30%+ daily move is impossible under circuit limits, so it's always an unadjusted action — e.g. PARAS 2025-07-04 dropped 45% with prev_close left unadjusted). Back-adjusts historical OHLC by the cumulative factor → continuous chart matching Zerodha. Verified: PARAS earliest adjusted close ₹252 (was the phantom-₹1800-spike problem; now matches Zerodha's ~₹250).
  - **📌 READ insights banner** — auto-derived (no LLM): inertia level, ATH flag, rank, entry zone, near-break. Pure Python.
  - **DVPT inertia table** — today's DVPT vs EVERY baseline: R-tier avg (avg_dvpt_1m..12m) AND P-tier power (power_dvpt_1m..12m), with the × multiple per baseline (🔥≥3× ⚡≥1.5× 🟢≥1×). This is Ramana's explicit "gauge inertia" ask (avg 500k vs today 1M = 2×; vs 3-4M = 6-8×).
  - **Quality — patearn (pt14)** — cached fundamentals snapshot (PE/ROCE/RoE/growth/OPM/D-E/promoter/pledge) + tier from `pattern_scores` if cached; else prompts to run `/pt14`.
  - **Relative strength** — honest placeholder (D33 not built).

- **Nous Hermes Agent installed on the VPS** (Docker) — a SEPARATE product (Nous Research, open-source, MIT), NOT our market Hermes. See Decision D34. Running as container `hermes-agent`, dashboard at `https://srv1704897.hstgr.cloud:9443` behind Caddy with Nous-Portal OAuth login, free model `nvidia/nemotron-3-ultra:free`, free Nous tool pool. Free tier ($0). Config in `/root/.hermes/`.

- **Daily pipeline self-heals now** — systemd drop-in `/etc/systemd/system/hermes-bhavcopy.service.d/10-signals.conf` adds extra `ExecStart` lines so the 7:30 PM IST bhavcopy timer ALSO runs `signals.py` (and is the place to add `indexes` + `index_signals` when D32 is wired). Previously signals never ran automatically — bhav copy ingested but signals lagged silently for a week (May 28–Jun 5 had to be caught up manually this session). **D35.**

- **Laptop SSH set up** — passwordless `ssh hermes` (ed25519 key + `~/.ssh/config` Host alias → 187.127.173.149). VS Code Remote-SSH available too.

**The big three-name "Hermes" confusion (resolved, recorded so it never recurs):**
- **Market Hermes** = OUR custom stock system. `/opt/hermes/`, systemd services `hermes-telegram` + `hermes-api`, Telegram + the `/dash` web dashboard. Free. Built by us over 15 sessions.
- **Nous Research Hermes Agent** = open-source general AI agent (Docker `nousresearch/hermes-agent`). What Ramana set up at `:9443`. Free to self-host.
- **nexos.ai** = a separate model-credits provider Hostinger bundles (the ₹559 "Hermes Agent" upsell). NOT a Hermes product; just optional fuel. Ramana did NOT buy it (invoice H_43941916 was VPS-only, ₹31,123.68). Don't confuse it with our system or with Nous.

### Session 15 — 2026-05-29 — Two-tier DVPT trigger system (P1.A → D28)
**Goal:** ship the D26 spec. Mid-session pivot to D28 after Ramana caught structural flaws in the original spec.

**The pivot:**
- First pass shipped D26 literally (sequential SS/S/A/B checks, 4 P-baselines). Ramana flagged: the asymmetric rank silently downgrades 3-of-4 hits in non-canonical window combinations. Also pointed out P12M was missing and R-tier was invisible to user.
- Reverted the D26 work, redesigned as two-tier model (R-tier + P-tier, 5 baselines each, pure-count scoring, near-break pointer). New decision D28 supersedes D26+D27.

**Shipped (single commit, D28):**
- `src/core/db.py`: 14 new columns on `stock_signals` via idempotent `_ensure_column`. New indexes on (trade_date, p_score), (trade_date, trigger_rank), (trade_date, is_ath_dvpt).
- `src/automation/signals.py`:
  - 5 R-baselines (`avg_dvpt_1m/2m/3m/6m/12m`), 1 new P-baseline (`power_dvpt_12m`) computed nightly via existing `flat_avg` / `power_avg` helpers
  - `_count_beaten`, `_rank_from_p_score` (SS/S/A/B/C/-), `_next_p_above` (finds closest P-wall above today's DVPT + gap %), `_hot_days_avg_close` (walks prior days for last 10 r1m>1 closes)
  - ATH-DVPT via full-history `stock_signals` lookup (true-ATH, not 1y-bounded)
  - `run_backfill_triggers` + `--backfill-triggers` CLI mode (per-symbol bulk fetch + batch UPDATE, expected ~20-30 min for 2.35M rows on VPS)
- `src/assistant/telegram_bot.py`:
  - `/scan` rewritten: SQL sort `is_ath_dvpt DESC → p_score DESC → r_score DESC → discount-flag → r1m DESC`. Output shows rank label (⚡ on ATH), `r/p` score, Δhot%, entry marker emoji (🟢/🟡/🔴), Near-P pointer with gap.
  - New `/triggers` command + 3 modes: default (rank A+ = p_score ≥ 3, cap 50), `ss` (SS only), `near` (next_p_above NOT NULL AND gap > -10% AND r_score ≥ 4 — breakout-imminent)
  - Registered in `BOT_COMMANDS` and `CommandHandler` table
- `src/assistant/intent.py`: extended SCAN vocabulary for ATH / "rank SS" / discount-entry / near-break / "kissing P3M" phrasing
- `PROJECT_STATE.md`: D28 (+ D27 pivot note + D26 superseded) added to decision log. Doctrine § E completely rewritten with the two-tier model. Schema description + commands table + open-items list all updated.

**Deploy steps for VPS (must run before /scan or /triggers will return meaningful rows):**
```bash
cd /opt/hermes && git pull
systemctl restart hermes-telegram
nohup .venv/bin/python -m src.automation.signals --backfill-triggers \
    > /var/log/hermes-trigger-backfill.log 2>&1 &
tail -f /var/log/hermes-trigger-backfill.log
```
After backfill: all 2.35M historical signal rows get D28 columns populated. Nightly compute populates them for new days automatically.

**Flagged but not touched:** uncommitted local diff on `src/assistant/patearn.py` adds `stage1_screen()` + `use_sonnet` param. Contradicts current doctrine (D7 / D22). Left alone — likely dormant work; needs explicit user decision before commit.

**Also shipped (commit 2, D29) — inline-keyboard menu system:**
- `/menu` opens root keyboard. Tree: Quality (pt14) / Delivery flow (dvpt) / Market scan (15/25/50) / Layered triggers (A+/SS/Near-break) / Watchlist (Show/Add/Remove) / Status.
- Ticker-prompt actions use `context.user_data["menu_pending"]` — next plain-text message gets consumed as the ticker, then state clears. /menu cancels pending.
- Reuses all existing helpers (no logic duplication); slash commands and NL routing untouched.
- Zero LLM cost — pure button routing via `CallbackQueryHandler`.
- `/start` help text rewritten to point at /menu first.
- Ramana asked for this mid-session because the command surface (17+ slash commands) had become unmemorizable. After ~1 week of usage, sunset buttons that don't get tapped (Doctrine § B.4).

**Not yet shipped (P1):**
- C. **Portfolio / strategy tracker** — unchanged from session 14, still open.

### Session 14 (continued) — 2026-05-29 — Cost-routing doctrine + applied analytics + AAVAS case study + KT consolidation
**Major direction shift**: Ramana pushed back hard on multiple architectural choices. Real friction surfaced, real corrections made. This second half of session 14 is itself a substantial KT artifact.

**Themes:**
- **Cost-routing doctrine consolidated** (§ A above) — Sonnet API banned for routine use; Gemini Flash for classifiers; Anthropic Haiku for chat only; claude.ai for deep dives
- **Honest retrospective**: ~30-40% of features built so far were over-engineered (§ B above)
- **HFC sector adaptation for patearn** (§ D above + D24)
- **Layered DVPT trigger system specified** (§ E above + D26) — NOT yet implemented, must ship next session
- **Applied analytics for the first time** — instead of building more features, SSH'd into VPS and produced a ranked watchlist from real data

**Shipped:**
- /analyze repurposed as claude.ai workflow guide (D22, commit 432974b) — no more API burn on a redundant feature
- Gemini Flash classifier opt-in (D20, commit 6749141) + /provider command + auto-fallback to Haiku
- SCAN intent + /scan command + chat system-prompt updated to describe available data (D21, commit c7d60b6)
- Natural-language intent routing (D18, commit 101635e) — type plain English instead of slash commands; classifier vocabulary tuned for DVPT terminology
- /score → /pt14, /flow → /dvpt rename (D19, commit e8f29fe)

**Applied (no code, real value):**
- Real watchlist from production data: AAVAS, ZYDUSLIFE, SYNGENE, DRREDDY, HEIDELBERG, HYUNDAI ranked Tier A/B with sector themes (pharma cluster, housing finance tailwind, CV cycle)
- AAVAS full patearn scoring walked through pattern-by-pattern (NS 46.3% base, 38-68% sensitivity band, T3 strict / T2 sector-adapted, QG fails by 6.5 pts but structurally for HFC sector)
- Documented case study lives in the Decision log + Doctrine section as the canonical reference for HFC sector-adapted scoring

**Pending (P1 for next session):**
- Layered DVPT trigger system (specified in detail in Doctrine § E)
- Portfolio / strategy tracker (`stocks_in_play` table + /track + /portfolio + /exit + /performance)

**Commits in this session segment:**
- `101635e` natural-language intent routing
- `1e99bb6` intent vocabulary tune for DVPT
- `e8f29fe` /score → /pt14, /flow → /dvpt rename
- `6749141` multi-provider LLM router (Gemini opt-in)
- `c7d60b6` SCAN intent + /scan command
- `432974b` /analyze workflow guide (no API call)
- (this commit) doctrine consolidation + new decisions D23-D26

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
