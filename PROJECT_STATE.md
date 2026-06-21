# Hermes — Project State

> **Last updated:** 2026-06-20 — **🆕 Session 24 — Portfolios/Watchlists now carry an inline "+ Add a stock" quick-capture (POST `/dash/track`, server-validated via `_is_listed`), closing the "tracker/watchlists/portfolios — can't add anything in there" gap. The feature was always working; capture just lived only on the stock page (D54 design), so the view-only section pages felt broken. Deployed to VPS + verified end-to-end (valid add freezes entry; invalid ticker → red banner, no row; no regression).** Earlier — **🆕 Session 21 shipped the CPR "Structure" pillar (D53)** — the 4th strategy (multi-TF CPR U/∩ reversal + compression), queryable + triggerable EOD: `cpr_signals` materialized D/W/M + screener CPR group + Strategies card + `/dash/cpr` + stock panel; conviction kept separate (★ Structure tier + "CPR-confirmed" gate). Verified no-regression (19/19 routes 200); **deploy to VPS via scp + run the backfill** (see § Session log → Session 21). Design/build log: `docs/cpr-strategy-design.md`. — *(earlier: session 19 — the two session-18 P0 `/dash/compare` chart bugs are FIXED, D49g; deep-history foundation still building on the VPS). **⚡ READ § Session log → "Session 18 — WRAP" FIRST.** **Project rebranding Hermes → Patearn** (patearn.in; "Hermes" now = the Nous agent only — D34). **The deep-history data foundation (D47 — MTO⋈legacy delivery → DVPT to ~2004) is BUILDING AUTONOMOUSLY on the VPS at wrap:** Stage-1 backfill (pid 133884, log `/var/log/hermes-deepbackfill.log`) → orchestrator `scripts/deep-foundation.sh` (pid 134151, log `/var/log/hermes-foundation.log`) → Stage-2 full recompute; a local watcher re-invokes the session when done. **The DVPT picking-strategy program is the throughline — full design in `docs/dvpt-picking-strategy-design.md` + `docs/multi-timeframe-positioning-design.md` (kept rich; binding doc-persistence rule — do NOT one-line).** Also shipped: **D48** dashboard enrichment (CMP·Δday·DVPT·**×power**·Deliv₹ on boards/screen; stock-page traded+delivery pane + RS-overlay chart w/ D/W/M/Q) + **SQLite WAL** perf (3–7s → 0.03–0.12s). **NEXT SESSION: ① verify the foundation finished + record coverage; ② build the MTF signal engine → ③ ignition+ranking → ④ backtest → ⑤ ML.** ⚠ Two Claude sessions shared one working tree today (git-add cross-absorption — caught, nothing lost) → next session be the sole one or use a worktree. — Earlier this session: **D46** bounded/prioritized batch **pt14 scoring** (`score_batch.py`) lights up the Quality pillar for surfaced names — honors D8 (over-time, not bulk); daily `hermes-pt14batch` timer; closes B6. Built right after **D45** cross-pillar **CONVICTION shortlist**: the synthesis where all 3 pillars align (RS leader + D43 accumulating + D44 entry + pt14 quality), read-only via `stock_rs.conviction_shortlist` → **`/dash/conviction`** + a ⭐ Home preview + `/conviction`. Built this session on **D43** DVPT accumulation/distribution **CHARACTER** (3-axis → `accum_character`) and **D44** value-weighted institutional **KEY PRICE** + near-key entry + ticket/surge + **`/dash/workbench`** (both additive, zero regression). D44 refines D31's flat `avg_close_p*` zones — the big institutional day now dominates the value-weighted cost line. Prior: session 17 — D33b/D33c (RS pillar COMPLETE) + **D41** strategy-surface Phase 1; **D42** equity-only scanners. Built on the session-16 D33a/D38/D39/D40 base.)
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
│   ├── multi-timeframe-positioning-design.md       ← MTF foundation spec (weekly/monthly resampled signals + timeframe-parameterized engine)
│   ├── cpr-strategy-design.md                       ← Strategy 4 (STRUCTURE pillar): multi-TF CPR — U/∩ reversal + unusually-narrow compression scanner + cross-TF amplification (larger TF weighted more) + confluence/regime; trend-stack sibling — design in progress (D53)
│   └── ui-design.md                                 ← UI/UX doctrine + revamp + system-growth roadmap (data-first · wide frozen-pane screener · light · no-regression); D54 — design in progress (session 20)
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
│   ├── automation\
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
│       ├── score_batch.py                           ← bounded/prioritized batch pt14 scoring (B6/D46; honors D8 — surfaced names only)
│       ├── mtf_signals.py                            ← HELD MTF engine (D52; weekly/monthly bars+signals) — authored, not run (memory: mtf-foundation-held-uncommitted)
│       └── cpr_signals.py                            ← CPR "Structure" pillar engine (D53): self-resampled D/W/M CPR geometry + U/∩ reversal + compression → cpr_signals
│   └── pat\                                          ← "Pat" NL guided-search tab (D55) — Gemini-only, web not Telegram
│       ├── __init__.py
│       ├── glossary.py                               ← Pat's data dictionary (grounding asset; 39 terms / 7 families)
│       ├── flows.py                                  ← read-only SQL templates compiled from chips (accumulation + RS + fundamentals)
│       ├── engine.py                                 ← Gemini free-text router: English → {flow, params} (never SQL, never-Claude, cached)
│       └── web.py                                    ← /dash/pat render: persona + 6 avatars + explain + 3 data flows + free-text
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
├── research\explosive_moves\                       ← Explosive-move research program (D56, session 25)
│   ├── common.py events.py features.py             ← read-only DB+adjust; 3 detectors; precursor matrix
│   ├── mine.py validate.py sensitivity.py run_all.py ← univariate+CART mining; OOS; robustness; orchestrator
│   └── out\*.csv                                    ← results (univariate/rules/oos/sensitivity/importance)
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

Read-only **except the D54 action-loop POSTs** (`/dash/track*` — the dashboard's only mutation); no LLM, pure SQL over existing tables. PWA-installable over HTTPS (Caddy). Top workspace nav (D54): Markets · Screener · Strategies · Portfolios · Tracker · **Pat (D55)** (sub-pages map via `_WS`; Compare under Markets; Watchlists under Portfolios).

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
| **`/dash/cpr?tab=&tf=&direction=&tier=`** | **D53 — the CPR (Structure) pillar surface.** Three tabs: **Reversals** (cross-TF amplified ★ U/∩ screen, filter TF/direction/min-tier, `.dt` sort/filter/CSV), **Compression** (unusually-narrow CPRs ranked by own-history percentile, per-TF), **EOD Reports** (Daily/Weekly/Monthly "what fired" — fresh reversals + coiled names; W/M carry a "live for the current period" badge). Linked from the Strategies CPR card. `active="strategies"` | **D53** |
| **`/dash/portfolios`** | **D54 (UI Phase 1) — committed positions under a strategy.** Holdings table: entry → live CMP → **P/L%**, target, **Conv then→now** drift (frozen snapshot vs live), thesis hover, **Close** action. In-page sub-nav Portfolios·Watchlists (Tracker is its own top tab, S24). MTM via indexed close point-lookup; `.dt` sort/filter/CSV. **Inline `+ Add a stock` quick-capture on the page (S24).** | **D54** |
| **`/dash/watchlists`** | **D54 — the lightweight idea tier** (`status='watch'`): symbol + strategy + note + LIVE signal chips + **Promote**-to-portfolio / Remove. **Inline `+ Add a stock` quick-capture (S24).** | **D54** |
| **`/dash/tracker`** | **D54 — how tracked ideas performed:** open MTM, **hit-rate by strategy** (closed) bars, **avg excess vs Nifty 500**, avg hold — pure SQL/point-lookups; honest empty-states until trades close. **Standalone top-level menu tab — not a Portfolios sub-page; carries no sub-nav (S24).** | **D54** |
| **POST `/dash/track` · `/track/close` · `/track/promote` · `/track/remove` · GET `/dash/track/quote`** | **D54 — capture + lifecycle (the dashboard's only writes).** `/track` freezes the as-of-day snapshot SERVER-side; **Portfolio entries auto-fill the close and accept an optional entry date + price validated to that day's OHLC `[low,high]`** (S24); `/track/quote` is the read-only OHLC helper behind the auto-fill + range hint; the rest manage `status` | **D54** |
| **`/dash/pat?flow=&explain=&q=&sector=&strength=&entry=&align=&val=&qual=&grow=&bs=&own=`** | **D55 — "Pat", the natural-language guided-search tab.** Persona + 6 selectable Indianised avatars (localStorage). **Explain-a-metric** + **three live data flows** — Accumulation-setups, RS-leaders, and **Fundamentals** (6 chip groups + 4 one-tap presets; financials judged on ROE via index-membership) — each compiling to a read-only parameterized SELECT, rendered data-first on the house **`table.dt`** grid (click-sort / filter / CSV-export). Free-text via the **Gemini engine** (`engine.py`): typed English → {flow, params}, validated against the chip vocab, cached; degrades to `find()`. **Gemini-Flash-only, never Claude.** `src/pat/web.py` + `flows.py` + `engine.py` | **D55** |
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

- `cpr_signals` (D53, CPR "Structure" pillar) — nightly-materialized multi-timeframe CPR per (symbol, period_end_date, **timeframe ∈ D/W/M**), PK on those three. GEOMETRY + widths STORED (objective): `p, bc, tc, width_pct` (the C0 CPR from the prior period's split-adjusted H/L/C; width ÷ pivot) · `c1_width_pct, c2_width_pct` (prior two bands, for the rank) · `compression_pctile` (own-history percentile, ≈252 D / 52 W / 24 M; high = unusually coiled) · `pattern` (BULL_U/BEAR_INVU/NONE) · `leg_in_clean, leg_turn_clean` · `separation_pct, depth_pct` · `regime` (sign close−P) · `days_since_pattern` (0=fresh; NULL=none) · `confirmed` (price engaged) · `close, adj_used, is_partial` (W/M current period), `n_bars_used`. The R1–R4 narrowness RANK, the cross-TF AMPLIFICATION, the ★ CONVICTION TIER + confluence are **DERIVED ON READ** (tunable knob/weights — `dashboard._CPR_MAXW`=D1.0/W2.5/M5.0, `_CPR_WEIGHT`=D1/W2/M3 — nothing re-materialized; mirrors D43-G). Indexes: `idx_cpr_tf_date`, `idx_cpr_sym_tf`, `idx_cpr_tf_date_pattern`. **Self-resampled** from `bhavcopy_rows` (split-adjusted) by `cpr_signals.py` — NOT dependent on the held MTF `bars_weekly/bars_monthly` (CPR-A5). `stock_signals` UNTOUCHED. Populate: `python -m src.automation.cpr_signals --backfill --timeframe all`; nightly `--recent --timeframe all`.

- `stocks_in_play` (D54, UI Phase 1 — the action loop) — one row per tracked idea. `status` ∈ `watch`|`open`|`closed` (watch = the lightweight watchlist tier, open = a committed position-under-a-strategy, closed = exited). Cols: `symbol, strategy, status, date_added, entry_price, price_target, stop_loss, entry_thesis, snapshot_json` (**FROZEN** as-of-add signal values — conviction/p/r/rank/×power/key-gap/RS/pt14/character — the daily `stock_signals` row overwrites nightly so it can't be reconstructed later; the one place denormalization is correct), `exit_date, exit_price, exit_reason, notes`. Indexes `idx_sip_status(status,strategy)`, `idx_sip_symbol(symbol)`. Written ONLY via the `/dash/track*` POSTs; mark-to-market + hit-rate are pure-SQL/point-lookups on read. The legacy `watchlist` (symbol PK) is kept untouched (the `scope=watch` screener source).

**View:** `prices_eq` — filtered to EQ series + CM segment, exposes OHLC + delivery cleanly for downstream code.

---

## Decision log (the big ones)

### D59 — Concall guidance ledger: re-extraction wipes the WHOLE (symbol, source_period) set, settled rows included (2026-06-21)
`concall_extract._persist` deleted only `status='OPEN'` guidance before reinserting every statement as `OPEN`. Once the Phase-2 settlement pass exists (flips OPEN→MET/MISSED/PARTIAL), a `--force` re-extract (e.g. after a prompt/model bump) would leave the settled row behind AND insert a fresh `OPEN` duplicate of the same promise → that statement is counted twice in `concall_guidance` → `guidance_accuracy_score` / `n_promises_resolved` in `concall_scores.py` corrupt. **Decision:** extraction OWNS a period's raw promise set; settlement is a deterministic, re-runnable derivation from later `concall_results`, so re-extraction deletes ALL rows for the `(symbol, source_period)` — settled included — matching the delete-set-then-reinsert idempotency the sibling concall tables already use; settlement is simply re-run afterwards (before `concall_scores --rerank`). No `UNIQUE(symbol, source_period, claim_text)` constraint: `claim_text` is an LLM paraphrase that drifts across prompt bumps (a content-hash key wouldn't catch the `--force` duplicate either), so the contract — not a row constraint — enforces single-copy. Bug was **latent** (settlement pass not built yet; every row `OPEN` today, local DB has 0 guidance rows) → fixed pre-emptively. Settlement contract written into `docs/concall-intelligence-design.md` §5. Fix in `src/automation/concall_extract.py` (untracked/uncommitted with the rest of CCI Phase-0; commit gated on Ramana per design §11).

### D58 — SQLite `_tune`: `busy_timeout` MUST precede `journal_mode=WAL` (2026-06-21)
Pragma ORDER is load-bearing. A fresh connection starts at `busy_timeout=0`; flipping to WAL needs a brief exclusive lock, so `journal_mode`-first fails instantly with "database is locked" under any concurrency — this crashed the nightly `stock_rs` step on 2026-06-19 and left `hermes-bhavcopy.service` failed (the data was fine; it died at step 7 of 8). `busy_timeout` (raised 5s→30s) is now set first so the WAL flip waits out brief contention. **Do not reorder.** Committed `adaa443`; see `vps-deploy-reality` memory for the deploy/regression-watch note.

### D57 — Stock charts load FULL history; every chart names its scrip (2026-06-21)
The per-stock charts silently truncated to the most recent ~1300 trading rows (~5y), making "Max" start at ~2021 despite a 2004→ archive. Decision: charts show ALL available history ("Max" = max); the row cap is removed and the client-side range buttons still default the visible window. Reinforces the data-first principle ([[data-first-light-ui]]) — never display less data than exists. Companion: every chart self-identifies (ticker on every pane; ticker + company name on the price chart) — no unlabelled chart. Committed `7ece6df`.

### D56 — Explosive-move reverse-engineering: bottom-up strategy discovery + the validated "Launchpad" (2026-06-20)
Ramana asked for a from-scratch, data-driven discovery program (no given strategy): find genuine explosive movers, fingerprint the *pre-move* data state, mine recurring patterns, measure hit/success ratios. Built as an offline research layer (`research/explosive_moves/`, isolated `.venv-research`; production DB read-only). Full log + pattern library: **`docs/explosive-move-research.md`** (keep rich — binding doc-persistence rule).

**Method (rigor — see doc):** 3 rolling event studies — +10% day / +10% week / **Ramana's monthly = rolling +10% HELD over ~22td** (today ≥ +10% vs a month ago; *corrected from the initial wrong ≥20%-thrust-retain-50% bar — a genuine +10% that keeps all 10% must count*). Any-date rolling, never calendar-bucketed. Survivorship-safe (raw archive incl. delisted — 20–24% delisted/renamed); point-in-time ₹1cr liquidity; strictly as-of-base features; 1-in-10 reweighted quiet-day baseline; **OOS walk-forward both directions** + by-year + by-liquidity. ~149k events. **Raw price/volume/delivery is the PRIMARY discovery battery; DVPT/house = comparison ONLY** (Ramana: "don't lean on my strategy — show what the data finds"). **Rigor catch:** the v2 monthly onset-flip de-overlap created a base-day↔outcome coupling artifact (fake "ret_1d>0 ⇒ ~100% sustained") → caught + fixed with spacing-based de-overlap.

**Findings (hold OOS both directions + every year 2012–26):**
- **Moves are preceded by momentum + volatility + trend** (already rising, extended vs 20/50/200-DMA, off the 52w low, volatile; Cliff's δ up to +0.80) — NOT by a delivery surge.
- **★ Counter-DVPT (the headline answer to Ramana):** reading data ALONE, a *rising delivery footprint is NOT* what precedes moves — the winning rules prefer `deliv_qty_trend ≤ ~1.5` (no surge) + lower delivery%. DVPT's own RS-rank/accum-drift rank competitively-not-superior, are the house construct, and are sparse pre-2021. **The AI's independent read disagrees with the DVPT premise and holds OOS.** It *refines*, doesn't replace, the DVPT throughline (D47).
- **★ "Launchpad" (monthly +10% held, base 11%):** momentum-continuation (`ret_22d>7% AND vol not expanding AND ranging`, OOS TEST lift 7.1 / hit 80%) OR pullback-in-vol (`ret_22d≤7% AND vol_66>2.4% AND ret_1d≤−2.2%`, OOS 4.7). Combined **hit 63.5%, lift 5.7×**, +24%/66td, 80% win, **43% become ≥50% winners** (vs 3.7% base). Stronger in liquid names (>₹25cr: 86%; momentum-only **97%**). Holds every year.
- **Sustain = strength/control:** a +10% month HOLDS when launched from a calm/tight, non-falling, near-52w-high, closing-strong base (OOS **85%** vs 53.5% base) = Ramana's "genuine buying = the close holds."
- **NOT yet:** costs/slippage/sizing/entry-exit (precursor study, not a P&L backtest) → next builds.

### D55 — "Pat": a natural-language guided-search tab in the web tool (Gemini-only, glossary-grounded) — Phase 1 SHIPPED (2026-06-20)
Ramana asked for "an AI chatbot on my data, in plain English, in this tool" — named **Pat** (it's about *patterns*). Built as a tab in the web dashboard (**`/dash/pat`**), **NOT Telegram** (network-blocked), and **Gemini-Flash-only, never Claude** (his call; the cost-doctrine classifier path, ~13× cheaper than Haiku).

**WHY this shape:**
- **It generalizes the interface.** Instead of hand-building a command/panel per question, Pat answers ad-hoc questions over the existing data — the one feature that scales instead of adding to the pile.
- **"Train on our data" = GROUND, not fine-tune.** The asset is a hand-written **glossary** (`src/pat/glossary.py`) describing every metric/column/value in plain words; Pat reads it at question-time, live numbers always come fresh from the DB. Cheaper, always-current, and it powers both "explain a metric" and free-text understanding.
- **₹0 on the common path.** The guided **chips ARE the query parameters** → the tap-through path compiles to template SQL in pure Python (no LLM, can't hallucinate a column). Gemini Flash is used ONLY at the edges: free-text→params, and phrasing a glossary entry conversationally.

**Architecture:** chips→params→template SQL (deterministic) · glossary grounding · 6 selectable **Indianised avatars** (Seth/Rao/Singh/Chai/Lakshmi/Nandi — persona + engagement, persisted in localStorage).

**Phase 1 shipped (DB-free, verified):** `/dash/pat` tab + avatar picker + the **Explain-a-metric** flow (search + tap, family-grouped, related-link chaining). `src/pat/{__init__,glossary,web}.py` + 4 wirings in `dashboard.py` (import · `Pat` nav tab · `_WS` · route). Verified: `py_compile` clean; the real FastAPI route returns **200** through `_shell`; `explain=p_score` renders the detail. Glossary = **39 terms / 7 families**.

**Phase 1b/1c shipped:** two live **data flows** over `stock_signals` — **accumulation** (`build_accumulation_query()`: ACCUMULATION + active strong hand, strength/entry/sector chips) and **RS-leaders** (`build_rs_query()`: high `rs_rank`, strength/sector chips + a strong-in-strong gate = above 200-DMA on BOTH the vs-broad and vs-sector RS lines). Both compile to read-only parameterized SELECTs, rendered data-first (raw values beside rank/character pills, CMP via `prices_eq`). Synthetic-DB verified (filters compose, no universe/character leak; real route 200 with rows).

**Open (see § What's NOT yet built):** the micro-viz design pass (Phase 6 — reuse the `_mv_*` cells in Pat tables, after the reconcile lands them in git); **deploy must carry `src/pat/`** + reconcile the VPS-only `dashboard.py` work (screener lag-fix + `_mv_*`). Memory: [[patearn-brand-and-dvpt-direction]].

### D54 — UI revamp (session 22, design-first): Phase 1 = the strategy → watchlist → portfolio ACTION LOOP — SHIPPED (2026-06-19)

The dedicated UI/UX redesign session (planned "Session 1" in `docs/ui-design.md §14`). Flow as briefed: boot → spawn a **5-agent design panel** (UI/UX · IA · analyst · data · design-researcher, parallel) → present the pivotal calls as **multiple-choice-with-recommendations**; Ramana chose **action-loop first · two-tier+frozen-snapshot · per-stock-news+static-strip (no marquee) · attach-don't-grow-nav** → **section-by-section visualize stencils** establishing the **"instrument"** aesthetic (inline static SVG/CSS micro-viz, monospaced numerals, evidence-beside-verdict; approved "perfect") → built Phase 1, no-regression. Full design + decisions: `docs/ui-design.md §14–16`. *(Ran in parallel with the D53 CPR session on the same tree; waited for its commit `2edb6b5` before editing the shared `dashboard.py`/`db.py` to avoid cross-absorption.)*
**Phase 1 shipped (additive, zero regression):** the `stocks_in_play` table; the capture flow (**+ Track** on the stock page → inline server-rendered form → POST `/dash/track`, which **freezes the as-of-day snapshot server-side**, entry = latest close, never trusting the client); real **`/dash/portfolios`** (entry→CMP→P/L · Conv then→now · thesis · Close) + new **`/dash/watchlists`** (watch tier + Promote) + real **`/dash/tracker`** (open MTM · hit-rate by strategy · excess vs Nifty 500 · avg hold). Verified: the full loop via TestClient (capture→view→close; snapshot confirmed frozen) + **all 22 routes 200 (no regression)**.
**Phases 2–3 (designed in the stencils, not yet built):** the "instrument" screener micro-viz that surfaces the under-utilized 88-col `stock_signals` data; metric **hover-help `?` popovers** (content baked from `metrics-glossary.md`); comparison enrichment (auto-rebase + transposed metric table); per-stock **news** + a static typed strip; **onboarding** strip + glossary page; the **inline-row Track** affordance on the screener/strategy grids. UI decisions logged in `docs/ui-design.md §13`.

**Follow-up — session 24 (2026-06-20): inline "+ Add a stock" on Portfolios & Watchlists (closes a discoverability gap).** Ramana reported "tracker/watchlists/portfolios … not able to add anything in there at all." Diagnosis: the loop was 100% functional on the VPS (routes deployed, `python-multipart` present, `stocks_in_play` exists, POST `/dash/track` returns 303 + inserts) — but per the original D54 design, **capture lived ONLY on the stock page**; the Portfolios/Watchlists/Tracker pages were view-only, so they read as "can't add." Fix (chosen from a 4-option menu = "inline add box on pages"): a compact **`_add_box(default_status)`** form rendered on both `/dash/portfolios` (default Portfolio) and `/dash/watchlists` (default Watchlist), empty AND populated states — typed ticker + list + strategy + optional thesis → POSTs the SAME `/dash/track` endpoint (entry + frozen snapshot still captured server-side; no new write path). Added **`_is_listed(conn, sym)`** validation (NSE equity list ∪ has-signals, permissive on any lookup error so a missing table never blocks a legit add) → typo tickers get a red `b-off` error banner via `?err=` instead of a junk row. Additive, reuses existing CSS (`.cap`/`.field`/`.row2`/`.banner`); the stock-page `+ Track` form is unchanged. Verified end-to-end on VPS: empty pages render the box; valid add (RELIANCE) → entry frozen ₹1309.5; invalid (ZZNOTREAL) rejected, 0 rows; error banner renders; all key routes 200; QA rows cleaned. Deployed `scp dashboard.py` + `systemctl restart hermes-api`. **(S24 cont.)** Added a Manual→free-text `strategy_custom` field to the add boxes (the custom basis is stored as the strategy, so hit-rate-by-strategy can group by the user's own names) and sharpened each tab's copy to communicate the funnel — **Watchlist** (watching) → **Portfolio** (committed) → **Tracker** (scoreboard). Per Ramana's explicit call, the **Tracker stays a derived scoreboard, NOT a third list** (no add box; it auto-fills from Portfolio + closed trades).

### D53 — CPR "STRUCTURE" pillar (the 4th strategy): multi-TF CPR reversal + compression, queryable + triggerable EOD — SHIPPED (CPR build session, 2026-06-19)

The 4th Patearn pillar beside Positioning (DVPT), Relative Strength, Quality. Answers what they don't: **where is price in its multi-degree structure, has it just turned, is it coiled?** One primitive (the 3-line CPR from the prior period's H/L/C) read at **Daily / Weekly / Monthly** — each TF its own CPRs, its own triggers, its own EOD report. Full design + build log: `docs/cpr-strategy-design.md` (§16); metric defs: `docs/metrics-glossary.md`.

Built after a **3-agent build panel** (quant · data engineer · strategy/product) → the OPEN decisions to the user as multiple-choice-with-recommendations → all confirmed the recommended defaults. **WHY each sub-decision:**
- **CPR-A4** geometry + widths materialized; **rank/amplification/★ tier derived ON READ** — the narrowness knob + TF weights stay tunable with zero re-materialization (mirrors D43-G).
- **CPR-A5** ONE timeframe-parameterized engine; **self-resamples** its own split-adjusted H/L/C bars (replicates `_period_key`) so CPR is **NOT blocked on / coupled to** the held MTF foundation (D52). A CPR needs only prior-period H/L/C — far lighter than the MTF delivery bar.
- **CPR-A6** split/bonus-adjusted OHLC + |return|>0.30 anomaly drop (D36) + equity-only allowlist (D42) + thin-prior-period skip — band & close share one continuous regime.
- **OPEN-1..7 resolved (all = recommended defaults):** both-lines clean step · rank priority C0 · show-both + `confirmed` flag · width ÷ pivot · per-TF D1.0/W2.5/M5.0% · TF weights D1·W2·M3 · both absolute + percentile (percentile primary for compression).
- **Conviction integration (user's call + panel consensus):** CPR is kept **OUT of the cross-pillar Conviction NUMBER** (stays positioning+RS). It surfaces as a parallel **★ Structure tier** column + a one-click **"CPR-confirmed"** screener gate. WHY: the composite is already unvalidated, CPR has no live history, doctrine = "master each pillar alone, then club." Re-weight/amplifier folding deferred.

**Shipped:** `cpr_signals` table (`db.py`, additive) · `src/automation/cpr_signals.py` (materializer, `--backfill`/`--recent`/`--symbol`, `--timeframe D|W|M|all`) · screener CPR column-group + "CPR-confirmed" gate · live Strategies CPR card (replaces "coming soon") · `/dash/cpr` (Reversals · Compression · per-TF EOD Reports) · per-stock CPR panel. Verified: CPR-math self-test + synthetic end-to-end backfill (800 D/160 W/40 M) + full 19-route 200 sweep (no regression). `stock_signals` untouched.

### D51 — Stock-page RS overlay made configurable (default Nifty 500 + Nifty 50 + sector; + Add any stock/index) — SHIPPED (session 19)

Ramana, viewing a stock's RS overlay, asked for the D50 compare style ON the stock page itself: "add similar features to the stocks as well" (and keep the Compare page — he loved it). So the stock-page RS overlay is now configurable, mirroring D50.

- **Default benchmarks are now Nifty 500 + Nifty 50** (+ the stock's sector if any) — was Nifty 500 + sector only. This third line is the visible "difference" he wasn't seeing on the stock page.
- **`/dash/stock` gains a repeatable `?cmp=` param** — index names OR tickers, server-detected (index if in `index_rows`, else a validated NSE ticker; the page's own `?sym=` is pinned as line 1). Overlay = the stock + the cmp items; bare page = the defaults. Overlay indices come from `index_rows` (date-bounded to the stock's window); overlay stocks from `_stock_levels` (the D50 helper), filtered to the window. Cap = `_COMPARE_MAX - 1` benchmarks.
- **Removable chips** (each cmp item, ✕ → rebuilds `?cmp=`) + a **+ Add type-ahead picker** (`_STOCK_CMP_PICKER_JS`) over the full equity universe + indices, same rules as D50 (ticker prefix from 2 chars, company-name substring from 4, capped 30, debounced 110ms). The picker carries the CURRENT overlay forward (`__CUR__`) so **Add APPENDS to the visible benchmarks instead of replacing them** — a bug caught + fixed during testing (without it, adding from the default view dropped 500+50).
- Reuses the D49h overlay chart untouched (D/W/M/Q toggle, deterministic earliest anchor, gutter labels, `userInteracted` gate — it already plots N series). Added the `.cmp-*` chip CSS to the stock page's `chart_css` (those styles previously lived only on the compare page).

Verified: default ACE overlay = ACE + Nifty 500 + Nifty 50 (browser: chips + gutter labels `ACE | 500 | 50`, anchor 2021-03-15, vals ACE 517.5 / 500 174.8 / 50 155.2); picker RELIANCE → Reliance Industries + name matches (browser); `?cmp=Nifty 500&cmp=Nifty 50&cmp=RELIANCE` → 4 lines and `?cmp=TATASTEEL&cmp=Nifty Bank` → stock+index mix (server). The Compare page (D50) is unchanged. ⚠ The browser connection (Chrome MCP) was intermittently dropping during this build, so the final interactive Add click-through wasn't screen-confirmed — but the append URL it builds, the default render, and the picker search all were.

### D50 — /dash/compare extended to STOCKS (+ smart type-ahead picker over the full equity universe) — SHIPPED (session 19)

The compare overlay was indices-only; it now overlays any mix of **stocks and indices**. Requested by Ramana: "compare a specific stock with any other stock… by default Nifty 500 and Nifty 50, but configurable."

- **Route.** `/dash/compare` gains a repeatable `?sym=` param alongside `?idx=`. Stock lines = split/bonus-adjusted closes from `bhavcopy_rows` via `adjust.adjusted_closes` (new `_stock_levels()` helper — ONE batched query, reuses the canonical D36 adjuster so a split never fakes an RS cliff). Symbols validated against `nse_equity_list`. Selection is a combined ordered `(kind, name)` list (indices first, then stocks); colour = position; a new `_cmp_href()` builds every chip/remove/denominator URL preserving both kinds. **Bare `/dash/compare` now defaults to Nifty 500 + Nifty 50** (was an empty state).
- **Picker (rewritten).** Searches the WHOLE universe — every index + the full NSE equity list (symbol + company_name), shipped once as inline JSON (~2k items) and filtered client-side (no per-keystroke server round-trip). Rules tuned for performance + to never blank: **< 2 chars → nothing; ticker PREFIX from 2 chars (LT → LT, LTF, LTFOODS, LTM, LTTS); symbol/company-name SUBSTRING from 4 chars (RELIANC → RELIANCE + RCOM/RHFL by name); indices substring-match; capped at 30, sorted exact→prefix→substring, input debounced 110ms.** Staged multi-select → one navigation emitting `?idx=`/`?sym=` per kind. Chips carry a small `stk` tag.
- **Stock page.** The RS-overlay heading gets an "↗ open in Compare ⇄" link → `/dash/compare?sym=<SYM>&idx=Nifty+500&idx=Nifty+50`, so any stock jumps straight into the overlay, ready to add narrow/sector indices.
- Stocks are **rebase-mode only** (no precomputed RS ratio) — in Ratio mode a stock drops out with the existing note; stock-RS-vs-index already lives on the stock page (D33/D49h).

Verified live: bare → 500+50; `sym=ACE&idx=Nifty 500&idx=Nifty 50` renders ACE+500+50 rebased (gutter labels 500/50/ACE, ACE 74.4 over 1Y default); picker LT/RELIANC/TATA return the right names + company labels, 1 char → 0 (no blank); staged TATASTEEL → Add → 2 stocks + 2 indices overlaid. Deployed (scp + restart hermes-api).

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

### 🔧 Session-27 follow-ups (deploy hygiene + verification)
- ✅ **CLOSED — `hermes-bhavcopy.service` failed-state** (D58): pragma-order lock bug fixed + deployed + the failing `stock_rs` step re-run clean; failed flag cleared. Production confirmation = the Mon 2026-06-22 14:00 UTC run goes green on its own (verify next session).
- **CCI `db.py` carry-check** — the D58 fix is in git (`adaa443`) and on the VPS, but the Concall-Intelligence session holds `db.py` with 200+ uncommitted lines; before its `db.py` deploys, confirm `busy_timeout`-before-`journal_mode` survives or the bug regresses. (`vps-deploy-reality` memory.)
- **VPS ↔ git reconciliation** — `/opt/hermes` git tree is dirty with HEAD behind `origin/main`; deploys happen by direct file-sync, so the documented `git pull` (`setup-news.sh`) path would fail. Reconcile to a clean pull-based deploy. (`vps-deploy-reality` memory.)
- **PWA cache** — the dashboard service worker can serve a stale cached page after a deploy; users need a hard-refresh until the SW cache version is bumped (edits `dashboard.py`, deferred while the CCI/web session holds it).
- **CCI Phase-2 guidance-settlement pass (D59)** — the deterministic OPEN→MET/MISSED/PARTIAL pass is still not built; when built it MUST be idempotent and re-run after any `--force` re-extract *before* `concall_scores --rerank`. Optional later: a `UNIQUE(symbol, source_period, claim_text)` backstop (needs a `concall_guidance` rebuild).

### 🚀 EXPLOSIVE-MOVE "Launchpad" — discovered + validated, NOT yet productized (D56, session 25)
The research is done (`research/explosive_moves/`, `docs/explosive-move-research.md`); the edge holds OOS + every year. Open follow-ons, in priority order:
1. **Live "Launchpad" daily screener** (highest value) — the M1∪M2 setup (volatile/wide-range + shakeout-or-thrust) with the S1 sustain filter (low-ATR / near-52w-high / non-penny), as a daily scan + a Strategies card on the dashboard. All inputs already exist nightly in `stock_signals`/bhavcopy. Fold the rule into Decision log + retire the research doc to a pointer.
2. **Tradeable backtest with costs** — add slippage/transaction-cost/position-sizing + entry-stop-target derived from the per-event MFE/MAE distributions already computed. (Current study is precursor-discovery, NOT a P&L backtest.)
3. **RS-era deep-dive (2021+)** where `rs_rank` is dense — likely sharpens M1/W1; consider adding RS rank to the live Launchpad gate.
4. **Sensitivity re-runs** via env params (`EM_LIQ_FLOOR`/`EM_THRUST`/`EM_HOLD`) — confirm thresholds; `weekly_signals`/`monthly_signals` (D52 MTF) would add multi-TF precursors if populated.
This is the **bottom-up sibling of the DVPT picking-strategy throughline (D47 below)** — it refines, not replaces it (it found that delivery/DVPT is a *confirmation* lens, not the *prediction* engine).

### 🤖 PAT — the natural-language guided-search assistant (D55, Phase 1 shipped session 23)
Tab is LIVE (`/dash/pat`) with the persona + 6 avatars + the DB-free **Explain-a-metric** flow. Remaining:
1. ✅ **All three data flows SHIPPED** — accumulation + RS-leaders (`build_accumulation_query`/`build_rs_query` over `stock_signals`) + **fundamentals** (`build_fundamentals_query` over `fundamentals`: 6 chip groups, NULL-honest gates, financials judged on ROE via index-membership, 4 one-tap presets). Tap path stays ₹0 (no LLM).
2. ✅ **Gemini free-text engine SHIPPED** (`src/pat/engine.py`) — typed English → {flow, params} via Gemini Flash, validated against the chip vocab (never SQL; never-Claude — an Anthropic fallback is discarded; cached by normalized query). A global ask-bar on Home routes into it; an "I read that as →" note shows the interpretation; degrades to the `find()` keyword match when the engine declines. (Conversational phrasing of glossary entries = a future nicety.)
3. ✅ **`pt14` glossary entry tightened** from `scoring.py` — `ns_base` (0–100), `pws`, `ns_pessimistic/optimistic` band, `pac`, `qg_pass`, and the T1–T4/DISQUALIFIED tiering now precisely defined.
4. **Deploy wiring** — the one-line `scp dashboard.py` deploy must now ALSO carry `src/pat/` (dashboard.py imports `src.pat.web`); fold `src/pat/` into `setup-news.sh`/the deploy step or `hermes-api` fails to boot.

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

### 🎨 UI REVAMP + system-growth roadmap (D54 — session 20, design-first) — see `docs/ui-design.md`
Ramana's UI direction, **binding doctrine for ALL screens** (present + future): **data-first** — show the raw values *beside* every verdict/pill, never bury the data; a **wide screener** holding **50–100+ columns** with horizontal scroll, **frozen top header AND frozen left column** (symbol stays put scrolling right); **light** — server-render + vanilla JS, no SPA/heavy framework (we handle lots of data); **no regression** — preserve chat, Telegram, charts, every page (improve only); keep the **refined** dark look. **IA:** one shared wide data grid; a *strategy = a lens over it* (saved query + verdict columns) with "Open in Screener" everywhere; Home **workspace tiles** (Markets · Screener · Strategies · Portfolios · Tracker), revisiting D40-A's 5-nav cap. **Growth (record now, build later):** **Portfolios** per-strategy + combination; **Tracker** — day/week/month performance + benchmark vs Nifty/broad/narrow + gap analysis ("where are we missing out"); **delivery beyond Telegram** (PWA primary, Telegram = alerts only — it's currently India-blocked); **BSE filings scraper** (results/returns → web-scrape on announcement, fills the NSE calendar gap). **Phase 1** = a new frozen-pane `/dash/screener` + data-first retrofit of DVPT/RS/CPR/Quality (additive, zero-risk). Full spec + 4 open questions in `docs/ui-design.md`. Memory: [[data-first-light-ui]].

**Phase 1 — BUILT + DEPLOYED (session 20; LIVE on VPS; local working-tree change NOT yet git-committed):** new **additive** route **`/dash/screener`** in `src/web/dashboard.py` — the data-first wide grid: 21 columns grouped Identity · Price · Positioning(DVPT) · Relative-Strength · Quality, with a **frozen Symbol column + sticky 2-row (group+column) header**, reusing `table.dt`/`_DT_JS` (click-sort · filter · CSV-export). **Verdict pills sit beside the raw values** (D-UI-1). Linked from `/dash/stocks`. Also: **header wordmark rebranded `HERMES → patearn`** (lowercase, green `e` `#3fb950` — D-UI-9, applies site-wide). CPR column group joins at D53. Verified by seeding synthetic rows → route returns 200 with correct groups/frozen-classes/pills/RS-strip, and a clean 200 empty-state. **Deploy:** `scp /d/Hermes/src/web/dashboard.py hermes:/opt/hermes/src/web/dashboard.py && ssh hermes 'systemctl restart hermes-api'` — **done s20** (VPS `/dash/screener`·`/dash`·`/dash/stocks` all 200; rollback backup `src/web/dashboard.py.bak.20260619-112929`). **Next (Ramana s20):** full **column flexibility** — show/hide any column, drag-reorder, choose-any (+ vertical header-pin via max-height) — the Phase-2 column manager (vanilla JS, persisted in localStorage). **Full-width (D-UI-10) shipped + deployed s20** — `_shell(wide=True)` → `.wrap.wide` (whole viewport) + `table.scr{width:100%}`; reading pages stay 760px (legibility). Live-verified `class="wrap wide"` in the VPS response.

**Richness pass — SHIPPED + DEPLOYED (session 20; consulted 3 design agents: UI/UX · analyst · data → synthesized):** (a) **Header band now truly frozen** — the grid is a single `max-height:calc(100vh-230px)` scroll viewport (both axes), the `_DT_JS` toolbar lifted OUTSIDE it (inserts before `.scrwrap`), 2-row sticky header (group `top:0` / col `top:26px`) + sticky Symbol col + frozen-column shadow on h-scroll. (b) **Comfortable gutter** `padding:clamp(12px,4vw,56px)`, `max-width:1900px`. (c) **Principled universe** replaces the arbitrary top-250: default = **Nifty 500 constituents** (504 in DB → 498 liquid), **scope selector** (broad indices · sectors via `REAL_SECTORS` `<select>` · watchlist · all-capped-600), shows members-vs-shown counts. (d) **Tri-pillar Conviction sort** `0.55·(p_score/5·100)+0.45·rs_rank` + **★ triple-confirm** (p≥4 & rs≥80 & quality-not-failing) + value-traded ₹Cr + 52w% + reordered grouped cols (Identity·Conviction·Positioning·RS·Quality·Context) + **heat-tinted cells** (h-pos/neg, `!important`) + tabular-nums + group dividers (`gsep`) + zebra + frozen-col shadow. (e) **Screener is now a permanent bottom-nav item** (replaced standalone `/dash/stock` "Stock" — still reachable via header search + row-tap). Live-verified: default 498 rows · all 600 · Nifty Bank 14 · 4 ★ · 215 heat cells. Backup `dashboard.py.bak.20260619-122356`. **Still open:** the **column-manager** (hide / drag-reorder / choose-any — Ramana's "completely flexible columns"); pws-scale-aware Conviction (confirm pws range before adding the Quality weight — currently positioning+RS only); optional Home hero card; per-index membership snapshot-date display.

**Navigation REFRAME + workspaces — SHIPPED + DEPLOYED (session 20):** the bottom 5-item nav is replaced by a **top workspace menu** (`.wsnav` in the header, on EVERY page): **Markets · Screener · Strategies · Portfolios · Tracker** (sub-pages map to a workspace via the `_WS` dict; brand wordmark links Home). New **`/dash/strategies`** workspace — today's best names per strategy (Conviction · Positioning/DVPT · Relative-Strength · Quality, 8 each = 32 live chips; a CPR card marked "in design D53"), each card linking to that strategy's full screen. New honest stubs **`/dash/portfolios`** + **`/dash/tracker`** (roadmap §6/§7) so the menu is complete. The screener gained a **view-bar**: column-group **toggle chips** (Conviction/Positioning/RS/Quality/Context — hide/show whole groups, persisted `localStorage['patearn_scr_hidden']`) + **Saved views** (named scope+hidden-groups, `patearn_scr_saved`), beside the existing filter/sort/CSV + the scope selector. All 11 routes verified 200 (incl. scan/leaders/conviction/sectors/stock — no regression). Backup `dashboard.py.bak.20260619-134728`. **Perf fix (s20, Ramana flagged toggle lag):** column-group hide was O(rows×cols) per click (~3000 inline `display:none` writes on the 498-row grid → janky). Rewrote to **class-based**: every cell carries its group class (`g-conv`/`g-pos`/`g-rs`/`g-qual`/`g-ctx`), toggling adds ONE class to the table (`hide-pos`, …) and CSS `table.scr.hide-pos .g-pos{display:none}` hides the group in a single reflow. ~2996 cells tagged live; backup `dashboard.py.bak.20260619-135728`. **Still open:** individual-column hide + drag-reorder (group-level shipped); if 500-row scroll itself feels heavy, next lever = `content-visibility:auto` on rows or a lower default row cap; real Portfolios/Tracker builds; CPR strategy (D53).

**Perf + clarity fixes — SHIPPED + DEPLOYED (session 20; Ramana flagged):** (1) **`/dash/stock` 3.3s → ~0.2s** — root cause found by in-process cProfile: the "latest" query `stock_signals ⋈ bhavcopy_rows … WHERE b.series='EQ' ORDER BY s.trade_date DESC LIMIT 1` mis-planned to drive off `idx_bhav_series` (scanning EVERY EQ bhav row, millions) → **3140ms**. Rewrote as **two indexed point-lookups** (latest `stock_signals` row by PK, then that day's EQ `close`/`deliv_per`) = **0.2ms**. Live: NATCO 0.23s · RELIANCE 0.30s · others ~0.04s. **Closes the long-open "/dash/stock ~3.5s" side-item.** (2) **The confusing "266"** on the Quality card was raw `pws` (sum of pattern scores, ~148–266); now shows the **normalized `ns_base` (0–100)** in the screener `pt14` column AND the Strategies cards, and every Strategies card states **"number shown = …"** (conviction 0–100 · DVPT rank SS▶C · RS rank 1–99 · pt14 0–100). (3) **Compare-picker universe** (~4000 equities) now **cached per data-date** (`_CMP_PICKER`) instead of re-queried+re-serialized on every stock page. Backups `…140752`/`…141143`. **Note:** other `stock_signals ⋈ bhavcopy_rows ORDER BY … LIMIT 1` spots (if any) risk the same mis-plan — driving off the symbol PK or splitting into point-lookups avoids it. (4) **Header de-crowded** (Ramana: "layout/crowding") — split into **two rows**: brand + ticker-search on top, the **workspace tabs on their own full-width row** with a clean green underline active-indicator (replaces the cramped single row). Live; all pages 0.004–0.15s. Backup `…141914`.

**Phase 1 (the ACTION LOOP) — SHIPPED (session 22, 2026-06-19; NOT yet committed/deployed at write time):** the strategy → watchlist → portfolio loop. `stocks_in_play` table; **+ Track** capture on the stock page (`?track=1` → inline form → POST `/dash/track`, server-frozen as-of-day snapshot, entry = latest close); real `/dash/portfolios` (entry→CMP→P/L · Conv then→now drift · thesis · Close) + new `/dash/watchlists` (watch tier + Promote) + real `/dash/tracker` (open MTM · hit-rate by strategy · excess vs Nifty 500 · avg hold). All additive; verified full loop via TestClient + all 22 routes 200. Design = "the instrument" aesthetic (`docs/ui-design.md §15–16`). **Still open (Phase 2–3, designed in stencils):** instrument-screener micro-viz that surfaces the under-utilized 88-col `stock_signals` data; metric `?` hover-help (content from `metrics-glossary.md`); comparison enrichment (auto-rebase + transposed table); per-stock news + static typed strip; onboarding; inline-row Track affordance. **Deploy when Ramana asks:** scp `db.py`+`dashboard.py` → VPS, restart `hermes-api` (creates the table).

### 🎯 NEXT = TWO dedicated, agent-driven sessions (planned s20; kickoff prompts authored)
Ramana wants to stop spot-fixing and run two focused sessions, each opening with **multiple-choice-with-recommendations** (mine + spawned agents') and staying interactive; **no-regression** throughout.
- ⏳ **Session 1 — UI/UX redesign — Phase 1 (action loop) SHIPPED (s22, D54); Phases 2–3 open** — full plan in **`docs/ui-design.md §14`**. A design panel (UI/UX · IA · analyst · data · design-researcher) proposed the best UI for this dense, high-perf platform; section-by-section stencils before building. New scope: **metric hover-help** (sourced from the new **`docs/metrics-glossary.md`** — canonical defs of DVPT/×power/surge/conviction/tier/pt14; answers "what is this number / measured against what"), **strategy→watchlist→portfolio action flow with thesis**, **news** (ticker + per-stock + affordable scrape), **stock & index comparisons**, **onboarding**, **under-utilized-data audit**, **comparable-platform style research**, performance-first.
- ✅ **Session 2 — CPR build — DONE (D53, 2026-06-19).** Multi-TF CPR strategy shipped queryable + triggerable EOD: `cpr_signals` materialized D/W/M + screener CPR group + Strategies card + `/dash/cpr` (Reversals · Compression · per-TF reports) + stock panel. Conviction integration = kept separate (★ Structure tier + "CPR-confirmed" gate), per the panel + user call. Build log: `docs/cpr-strategy-design.md §16`.
- **New artifact:** `docs/metrics-glossary.md` — the canonical metric dictionary + hover-help content source. **Conviction is a Claude-introduced heuristic** (`0.55·(p_score/5·100) + 0.45·rs_rank`), positioning+RS only, **NOT yet validated/backtested** — documented honestly in the glossary; tuning + folding in Quality/CPR is open.

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

C. ✅ **Portfolio / strategy tracker — BUILT (D54 Phase 1, session 22)** as the web action-loop: `stocks_in_play` + `/dash/portfolios`·`watchlists`·`tracker` + `/dash/track*` POSTs (capture freezes the as-of-day snapshot; MTM + hit-rate-by-strategy + excess-vs-Nifty on read). The original session-14 spec + Telegram commands below are kept as historical reference (the `/track` `/portfolio` `/exit` `/performance` bot commands remain optional — Telegram is network-blocked):
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

### Session 27 — 2026-06-21 — Stock charts un-truncated (full history + scrip name) · nightly DB-lock crash fixed — SHIPPED + deployed + verified

**Context:** Ramana (charts): "We have data from 2004, but you're providing this nonsense only from around April 2021… none of the charts are refreshed… at the top of the chart it doesn't show the name of the script." Then, on a flagged failed systemd unit: "investigate."

**Chart fix — `src/web/dashboard.py` (commit `7ece6df`):**
- Root cause: the `/dash/stock` candle + RS-overlay query capped at `ORDER BY b.trade_date DESC LIMIT 1300` (~5.1 trading yrs) → "Max" anchored at ~2021 even though the bhav archive runs to 2004 (ADANIPORTS 2012→, Nifty 50/500/Infrastructure 2012→). The RS overlay inherited the window (it reuses `series`, bounded by `series[0]..series[-1]`); `/dash/compare` and `/dash/ratio` were never capped (uncapped `_stock_levels`/`ratio_rows`; `r=252` only sets the default zoom). **Removed the LIMIT** — "Max" now means max; query stays fast (covered by `idx_bhav_sym_date`; deepest name RELIANCE ~5.4k rows).
- Added the scrip name to all four price-family chart labels — `{sym}` on each, plus the full `company_name` (from `nse_equity_list`) on the price chart — so each chart self-identifies without scrolling to the page header.
- Verified: a synthetic 1500-row symbol renders all 1500 pts (old cap was 1300); live ADANIPORTS = 3559 pts, 2012-01-17→2026-06-19, name in the label. Deploy: `scp dashboard.py` (LF) + `systemctl restart hermes-api` — the VPS git tree is dirty/HEAD-behind so the documented `git pull` deploy would fail (see `vps-deploy-reality` memory).

**Nightly DB-lock fix — `src/core/db.py` `_tune` (commit `adaa443`):**
- `hermes-bhavcopy.service` had been `failed` since 2026-06-19. Diagnosis: the **data was fine** (bhav/signals/indexes/index_signals/membership/equity_list/RS/CPR all reached 06-19); the chain crashed at step 7 of 8 (`stock_rs`) with `sqlite3.OperationalError: database is locked` at `PRAGMA journal_mode = WAL`. **Root cause:** `_tune` ran `journal_mode=WAL` BEFORE setting `busy_timeout`; a fresh connection defaults to `busy_timeout=0`, and the WAL flip needs a brief exclusive lock, so under concurrency (heavy manual VPS dev that day) it failed instantly instead of waiting. **Fix:** set `busy_timeout=30000` FIRST, then `journal_mode=WAL` (D58).
- Applied surgically on the VPS (backup `db.py.bak.lockfix-20260621-173141`), cleared the failed flag (`systemctl reset-failed`), restarted `hermes-api` + `hermes-telegram` so all services pick it up, and landed in git isolated from the in-flight CCI `db.py` WIP via plumbing (`git hash-object` + `update-index --cacheinfo`). **Verified post-fix by re-running the failed `stock_rs` step** under the patched db.py — clean through all 2415 per-symbol connections ("computed 2415 RS rows, 1364 ranked for 2026-06-19"). The Mon 2026-06-22 14:00 UTC scheduled run is the production confirmation.

**Commits:** `7ece6df` (charts), `adaa443` (db lock) — both pushed to `origin/main`. (This PROJECT_STATE.md entry carries the parallel CCI/web session's coherent doc WIP — Session 26, D56 v3 corrections, commands-table update — since it shares the file.)

### Session 26 — 2026-06-20 — Nous Hermes agent operationalized as the offline learner/teacher; DVPT actionable-gate REFINED (design doc)

Mostly Nous-Hermes-agent work (D34 — the separate Nous Research agent on the VPS, NOT this repo; full detail in the `nous-hermes-bridge` auto-memory + the agent's on-VPS `AGENTS.md`). **One repo change (uncommitted):** the gate refinement in `docs/dvpt-picking-strategy-design.md` §3.

**Gate REFINED (supersedes the session-18 criterion 2):** intensity **≥5×** = ACT floor (≈1/day → a natural 30–40 portfolio; ≥10× = a "monster" sub-tier, not the floor; below 5× but p5 + clean ACCUM = WATCH); **the absolute ₹-floor is REMOVED** — Ramana ruling: an absolute floor deletes the thin-float small/mid-caps where the best gems hide → significance is now judged **relative to each stock's OWN trailing-avg delivery value** (~2× its own norm), never a market-wide ₹ bar; clean ACCUMULATION unchanged; **pure DVPT, no RS gate** (vanilla). Build item surfaced: add `deliv_value_self_surge = delivery_value_today ÷ own trailing-avg delivery_value` (today only `turnover_surge_*` = a total-turnover proxy exists). → this unblocks the DVPT backtest (§5), the next major piece.

**Nous-Hermes side (VPS, see `nous-hermes-bridge` memory):** model fixed → `gemini-2.5-flash` (Ramana's Google key, billing enabled); persona + a profile of Ramana + an assistant charter + an absolute never-delete rule; a read-only `hermes.db` query tool (verified, used autonomously); a daily self-study loop (outbound channel + verify-gate, on a timer); and PAT's factual foundations (DVPT / character / RS / 14-Pattern / CPR — code-true + data-verified) plus the gate locked into its always-loaded `AGENTS.md`. Naming locked: **Hermes** = the Nous agent only; **Pattern** = the operational Patearn agent; **PAT** = the in-dashboard assistant.

### Session 25 — 2026-06-20 — Explosive-move reverse-engineering research program — v3 COMPLETE, corrected per Ramana (offline, not deployed)
**Context:** Ramana: "I am not going to give you strategy… I want you to find strategy… ground-breaking. Identify stocks that moved 10% in a month and sustained, 10% in a week, 10% in a day; track back; identify the data patterns; compile them; understand the hit ratio and success ratio." A from-scratch, bottom-up discovery program. (Decision **D56**.)
**Built — new offline research layer `research/explosive_moves/` (isolated `/opt/hermes/.venv-research`; production `hermes.db` READ-ONLY; outputs → `/opt/hermes/data/research.db` + `out/*.csv`):**
- `common.py` (read-only DB, reused `adjust.py` standalone, per-symbol numpy series + point-in-time trailing-median turnover, Cliff's δ), `events.py` (3 detectors + forward outcomes), `features.py` (precursor matrix: raw descriptors + house `stock_signals` + CPR, as-of-t-1, 1-in-10 reweighted baseline), `mine.py` (univariate lift/precision/coverage + depth-3 CART rules + RF importance), `validate.py` (walk-forward OOS both directions + success ratio), `sensitivity.py` (liquidity + by-year robustness), `run_all.py` (orchestrator).
- **Corpus (v3):** 2012→2026, **~149k events** (13,720 daily / 52,791 weekly / 69,746 monthly +10%-intramonth, **37,343 sustained = 53.5%**) vs ~29.9k reweighted baseline. Survivorship-safe (20–24% delisted/renamed).
- **⚠ CORRECTED per Ramana (v2/v3):** (1) monthly = **rolling +10% HELD** over ~22td, NOT the initial ≥20%-thrust-retain-50% (a genuine +10% that keeps all 10% must count); (2) **rolling, any-date** (not calendar); (3) **raw data is the PRIMARY discovery battery, DVPT = comparison ONLY** ("don't lean on my strategy"); (4) expanded the raw delivery/volume battery; (5) **caught + fixed a base-day↔outcome coupling artifact** in the v2 monthly onset-flip (→ spacing-based de-overlap).
**Result (raw-only, validated OOS both directions + every year 2012–26):** **★ Counter-DVPT headline** — reading data alone, a *delivery surge is NOT what precedes moves* (winning rules want `deliv_qty_trend ≤ ~1.5`, lower delivery%); momentum+volatility+trend lead (δ up to +0.80); DVPT RS/accum-drift are competitive-not-superior + the house's own. The **"Launchpad"** (momentum-continuation `ret_22d>7% AND vol-not-expanding AND ranging` OOS lift 7.1/hit 80%; OR pullback-in-vol `ret_22d≤7% AND vol_66>2.4% AND ret_1d≤−2.2%` OOS 4.7) → combined **hit 63.5%, lift 5.7×**, +24%/66td, 80% win, 43% become ≥50% winners (vs 3.7% base); stronger in liquid names (>₹25cr 86%, momentum-only 97%). Sustain = strength/control (calm/tight, non-falling, near-52w-high base → OOS 85% vs 53.5%) = "genuine buying." Refines, doesn't replace, the DVPT throughline (D47).
**Deliverable:** `docs/explosive-move-research.md` (methodology + ranked precursor catalog + the Pattern Library cards M1/M2/W1/D1/S1 + caveats + reproduce steps). **NOT committed/deployed** (offline research; awaiting Ramana's call to turn the Launchpad into a live screener). No production code touched. **Commit:** _(pending — ask before committing)_.

### Session 24 — 2026-06-20 — Portfolios/Watchlists inline "+ Add a stock" + Tracker promoted to a standalone top tab + custom-strategy field + clarified tab semantics + entry auto-fill/OHLC-validated backdating — SHIPPED + deployed
**Context:** Ramana: "Section of tracker, watchlists, portfolios are not built yet properly, not able to add anything in there at all?"
**Diagnosis (VPS, read-only):** the D54 action-loop was fully working — `/dash/track*` routes deployed (dashboard.py @ 2026-06-19 20:20), `python-multipart 0.0.32` installed, `stocks_in_play` table present, a live POST returned 303 and inserted + rendered + cleaned up. The real issue was **discoverability**: D54 put capture ONLY on the stock page, leaving Portfolios/Watchlists/Tracker view-only — so they felt unusable.
**Shipped (additive, zero regression):**
- `src/web/dashboard.py` — new **`_add_box(default_status)`** inline quick-capture form on `/dash/portfolios` (default Portfolio) and `/dash/watchlists` (default Watchlist), in both empty and populated states; POSTs the existing `/dash/track` (server-side entry/snapshot freeze unchanged).
- new **`_is_listed(conn, sym)`** server validation (NSE equity list ∪ has-signals; permissive on lookup error) — invalid tickers redirect with `?err=` → red `b-off` banner, no junk row. `dash_track` restructured to validate first; `dash_portfolios`/`dash_watchlists` gained an `err` query param + the box; intro/empty copy updated.
- **Tracker promoted to a clean standalone tab** (Ramana: "we need the tracker tab beside the portfolio tab in the menu"). It was ALREADY a top-level tab in `_nav`, but the in-page `_track_subnav` (Portfolios·Watchlists·**Tracker**) made it read as nested under Portfolios. Removed Tracker from `_track_subnav` (now just Portfolios·Watchlists — the two list tiers) and dropped the sub-nav entirely from `dash_tracker`, so Tracker is reached only from its top menu tab. Verified live: Portfolios/Watchlists sub-nav = 2 items; Tracker page renders 0 `.fbtn` (no sub-nav) with the top **Tracker** tab `on`; top nav unchanged (Markets·Screener·Strategies·Portfolios·Tracker·Pat); routes 200.
- **Custom strategy / basis free-text** — selecting "Manual" in any add box (`_add_box` on Portfolios/Watchlists + the stock-page `_capture_form`) reveals a `strategy_custom` text input (≤60 chars) via the shared `_CS_JS` toggle (fires on `select[data-cs]`); `dash_track` stores the typed basis as the strategy when Manual + non-empty, else the preset/"Manual". So Tracker's hit-rate-by-strategy can group by the user's own strategy names. Verified: Manual+"52w breakout test"→stored verbatim; Manual+blank→"Manual"; preset+custom→preset (custom ignored).
- **Tab semantics clarified in-app** (Ramana: "what is the difference between tracker and watchlist?"): each `.sub` intro now states its role + cross-links the others — **Watchlist** = ideas you're watching (pre-commit input) · **Portfolio** = positions you've committed to (live P/L) · **Tracker** = the auto-computed scoreboard over Portfolio+closed (hit-rate by strategy, excess vs Nifty). **Decision (Ramana's call): Tracker STAYS a derived scoreboard, not a third list** — no add box; you add via Watchlist/Portfolio and Tracker scores them.
- **Portfolio entry: auto-fill + optional backdate + impossible-price guard** (Ramana). Portfolio adds now auto-fill the entry price (visible) and accept an **optional entry date + price**; the price is **validated server-side to that trading day's `[low, high]`** (a custom date snaps to the last trading day on/before it) so a price that never traded can't be saved. New `_ohlc_on(conn,sym,date)` resolves the OHLC; `dash_track` stores `date_added` = the entry date and freezes the snapshot **as-of that date** (`_capture_snapshot(as_of=)`). New read-only **`GET /dash/track/quote`** powers the live auto-fill + a "valid ₹low–₹high" hint (`_ENTRY_JS`, on every `form.cap`). **Per-segment by design:** only Portfolio gets entry fields; **Watchlist** has none (pre-commit idea; snapshot still records the as-of price); **Tracker** is derived (the corrected entry flows into its P/L, hit-rate, excess). Portfolio table headers → "Entry date" / "Entry ₹". Verified on VPS: quote→`{close 1252.2, low 1241.85, high 1257.0}`; auto→latest close ₹1309.5 @ latest date; backdated 2025-01-15→₹1252.2 stored at that date; **₹999999 rejected** ("traded ₹1241.85–₹1257 on 2025-01-15 … never traded that day"); watch→entry NULL; all routes 200; QA rows cleaned.
**Verified end-to-end on VPS** (compile-gated, restart): empty pages show the box; `POST symbol=reliance status=open` → `303 → /dash/portfolios?added=RELIANCE`, entry frozen ₹1309.5; `POST symbol=ZZNOTREAL` → `303 → ?err=… not a recognized NSE equity`, 0 rows; populated page shows RELIANCE + box; error banner renders; routes `/dash`,`/dash/portfolios`,`/dash/watchlists`,`/dash/tracker`,`/dash/stock`,`/dash/screener`,`/dash/cpr`,`/dash/pat` all 200. QA rows deleted (table back to 0). Deploy: `scp dashboard.py` + `systemctl restart hermes-api`. **Commit:** _(see git log)_.

### Session 23 — 2026-06-20 — "Pat" Phase 1: the natural-language guided-search tab — SHIPPED (local), verified
**Context:** Ramana asked for an AI chatbot over his data, in plain English, *in this tool* — and to run it on **Gemini Flash only, no Claude**. Named **Pat** (patterns). Built as a web-dashboard tab, not Telegram.
**Shipped (additive, zero regression, DB-free):**
- **`src/pat/glossary.py`** — Pat's data dictionary / grounding asset: **39 terms across 7 families** (basics · positioning/DVPT · character · RS · structure/CPR · quality · concepts), each with plain + detail + real `table.column` source + aliases + related cross-links; tiny dependency-free `get`/`find`/`family` helpers. The honest reframe: "train on our data" = **ground** on a glossary, not fine-tune.
- **`src/pat/web.py`** — the `/dash/pat` body: persona hero + **6 selectable Indianised avatars** (Seth/Rao/Singh/Chai/Lakshmi/Nandi, self-contained SVG, persisted in localStorage) + the live **Explain-a-metric** flow (search + family-grouped chips + related-link chaining), themed to the dark shell. The 3 data flows are announced (need SQL templates).
- **`src/web/dashboard.py`** — 4 wirings: `from src.pat.web import render_pat`, the **Pat** nav tab, `_WS["pat"]`, and `@router.get("/dash/pat")` (now opens `with get_conn() as conn` + passes the chip params).
- **`src/pat/flows.py`** (added later same session) — the **data flows**: `build_accumulation_query()` (ACCUMULATION + active strong hand) and `build_rs_query()` (high `rs_rank` + strong-in-strong both-above-200DMA gate) compile the strength/entry/sector/align chips to read-only, parameterized SELECTs over `stock_signals`; rendered data-first (raw values beside rank/character pills, CMP via `prices_eq`).
**Verified:** `py_compile` clean; every glossary cross-link + family resolves; `find()` ranks sensibly; the accumulation query is SELECT-only + fully parameterized; on a synthetic DB the filters narrow correctly (default 3 → IT 2 → SS 1 → discount 1), character/universe filters don't leak, and the **real** FastAPI route returns **200 with rows** through `_shell` (TestClient, `get_conn` patched) — nav shows Pat, `explain=p_score` renders the detail.
- **UI direction (user call): Pat stays conversational** — the "Pat says…" bubbles + the 6 avatars are kept; the two result tables were promoted to the house **`table.dt`** grid → click-sort / filter / CSV-export / sticky sortable headers via the shared `_DT_JS` (one-class change, `_PAT_CSS` adds tabular-nums). A fuller "control-panel" reskin (frozen-pane grid, `.fbtn` chips, slim persona, `.scards` home with live counts, "Open in Screener →") was proposed by an **architect + product-designer review this session** and **deferred per the user**.
**⚠ Deploy — via `git pull`, NOT `scp dashboard.py`:** dashboard.py now imports `src.pat.web`, so the legacy single-file scp would crash `hermes-api` on import (restart-loop → the WHOLE dashboard down). Correct path: push origin/main → verify the VPS tree is clean (`ssh hermes 'cd /opt/hermes && git status --short'`) → `git pull && systemctl restart hermes-api` → smoke-test all routes 200; rollback = restore the latest `dashboard.py.bak.*`. (Full landing plan came from this session's architect review.)
- **`src/pat/flows.py` (Phase 1d, analyst-consulted): the fundamentals flow** — `build_fundamentals_query()` over the `fundamentals` table. 6 chip groups (valuation/quality/growth/balance-sheet/ownership/sector) with India-calibrated thresholds reused from `scoring.py`; **NULL-honesty rule** (core gates strict, BS/OWN NULL-tolerant so sparse rows aren't silently dropped); **financials handling** — detected via `stock_index_membership` (Bank/Financ/NBFC/Insur), judged on **ROE not ROCE**, D/E + promoter gates dropped; 4 one-tap presets (Quality compounders / Deep value / Clean-sheet growth / Quality financials). Synthetic-DB verified.
- **`src/pat/engine.py` (Gemini free-text engine):** typed English → `{flow, params}` via `llm_router.call_classifier` (Gemini Flash). System prompt is built from the chip dicts + glossary terms (single source of truth). Output validated against the chip vocab (off-menu/bad values dropped); **never-Claude** (provider≠gemini → discarded → `find()` fallback); cached by normalized query; never invoked on the tap path (₹0). Wired via `_free_text` + a Home ask-bar + an "I read that as →" interpretation note. Verified with a **mocked** classifier (no real API spend).
- **Pre-deploy adversarial review + reconciliation (this session, agent-consulted):** an architect, a product-designer, and a code-reviewer agent reviewed Pat. **Review verdict: 0 P0s** — SQLi structurally unreachable (chips→params; column/operator only from constant dicts; every value bound via `?`), never-Claude holds, the route can't 500. Applied the 3 P1 fixes: avatar JS-map now via `json.dumps` (+ `</`→`<\/` guard) and `_esc` escapes `"` (attribute-safe); a **6s Gemini timeout** (`llm_router`, `max_retries=0`) so the free-text path can't park a worker thread; and a double-escape fix on the "I read that as →" note. **Reconciliation VERIFIED:** the VPS-only `dashboard.py` work (screener lag-fix + `_mv_*` micro-viz) was already synced into the local file and rode into the Pat commits — a CRLF-normalized diff vs the live VPS shows the committed union = VPS work + Pat wiring, differing only by ONE reworded CSS comment. So git already holds the VPS work; deploying the union loses nothing.
- **DEPLOYED — Pat is LIVE on the VPS (2026-06-20).** scp'd the union `dashboard.py` + `src/pat/` + timeout'd `llm_router` + `settings`; restarted `hermes-api`; **all 9 routes 200, no regression**, Pat in nav, explain renders, the screener lag-fix + `_mv_*` preserved (reconciliation held). **Perf gate passed:** accumulation/RS/fundamentals queries hit indexes (`idx_signals_p_score` / `idx_signals_rs_rank` / `fundamentals` PK — no full scan of the 2.35M-row table); routes **4–6 ms**. **Gemini fix:** the free-text engine 429'd because **`gemini-2.0-flash` free tier is quota-0**; switched `settings.gemini_classifier_model` → **`gemini-2.5-flash-lite`** (has quota + captures chip params better — *also un-breaks the news classifier*, which had been silently 429-falling-back to Haiku) and bumped the engine's `max_tokens` 160→512 (2.5-tier thinking budget). Live free-text verified routing.
**NEXT:** the micro-viz design pass (Phase 6 — reuse `_mv_*` in Pat tables) is the only remaining nice-to-have. **Pat is functionally complete + deployed.** Backups on VPS: `dashboard.py.bak.pat-*`.

### Session 22 — 2026-06-19/20 — D54 UI revamp: Phase 1 ACTION LOOP + stock-page live-trial fixes — SHIPPED, deployed, no-regression
The dedicated UI/UX redesign session (planned "Session 1", `docs/ui-design.md §14`). Boot → **5-agent design panel** (UI/UX · IA · analyst · data · design-researcher, parallel) → pivotal calls as **multiple-choice-with-recommendations**; Ramana picked **action-loop first · two-tier+frozen-snapshot · per-stock-news+static-strip · attach-don't-grow-nav** → **visualize stencils** establishing the **"instrument"** aesthetic (inline static SVG/CSS micro-viz, evidence-beside-verdict — nav frame · action capture · portfolio/tracker · the dense instrument screener · hover-help popover · stock decision masthead · comparison · per-stock news; approved "perfect") → built Phase 1.
**⚠ Concurrency:** ran in parallel with the D53 CPR session on the SAME working tree. Per the standing rule, did NOT touch shared files until the CPR work was committed — armed a background git-watcher, waited for commit `2edb6b5`, re-verified the tree quiesced, then built. No cross-absorption.
**Shipped (D54 Phase 1, additive, zero regression):**
- **`stocks_in_play` table** (`src/core/db.py`) — status watch|open|closed; `snapshot_json` freezes the as-of-add signals.
- **Capture** — `+ Track` on `/dash/stock` (`?track=1`) → inline form → **POST `/dash/track`** (+ `/track/close|promote|remove`), the dashboard's first mutations; the snapshot + entry price are frozen SERVER-side (entry = latest close), never trusted from the client.
- **Views** — real **`/dash/portfolios`** (entry→CMP→P/L · Conv then→now · thesis · Close), new **`/dash/watchlists`** (watch tier + Promote), real **`/dash/tracker`** (open MTM · hit-rate by strategy · excess vs Nifty 500 · avg hold). In-page Portfolios·Watchlists·Tracker sub-nav; `_WS` maps watchlists→portfolios. `python-multipart 0.0.27` present.
**Verified:** full loop via FastAPI TestClient (empty-states → capture ALPHA open + BETACO watch → views render → snapshot frozen [conv 96 / rank SS / rs 92, entry ₹519.99 auto] → close → tracker) + **all 22 routes 200 (no regression)**. Test rows cleaned up.
**Committed + DEPLOYED:** commit `c339098` (the 2 code files + 3 docs ONLY — `patearn.py`/`mtf_signals.py` deliberately excluded via explicit `git add`; not pushed). scp'd `db.py`+`dashboard.py` → VPS + restart `hermes-api` (the `CREATE TABLE IF NOT EXISTS` runs on boot). ⚠ **The restart crash-looped:** the `Form(...)` capture routes need **`python-multipart`**, which was absent from the VPS venv (FastAPI raises it at startup) → installed it (`0.0.32`) + **added `python-multipart==0.0.32` to `requirements.txt`** (this follow-up commit) so a rebuild won't regress. After that: service `active`, **all routes 200 on the box** (incl. `/dash/portfolios`·`watchlists`·`tracker` + the `?track=1` capture form). *(`main` is ahead of origin — CPR + perf + D54; not pushed.)*
**Phases 2–3 open (designed in the stencils):** instrument-screener micro-viz (surface the under-utilized 88-col data), metric `?` hover-help, comparison enrichment, per-stock news + static strip, onboarding, inline-row Track. See `docs/ui-design.md §15–16`.
**Live-trial fixes (s22, deployed via scp + verified on the box):** the **stock RS-overlay** now (1) seeds the stock's **sector index by default** even when `primary_sector` is NULL — new `_narrow_sector(conn,sym)` membership fallback (narrowest REAL_SECTORS index; RELIANCE → Nifty Oil & Gas); (2) shows **same-sector peer tickers as tap-to-stage chips** under the picker search (`#soPeers`, reuses the existing staging, ≤12 shown, filtered to the equity set; type-ahead covers any other name). Diagnosed the **empty RS panel** on the stock page: NOT a regression — the deep-history recompute is in flight (`index_signals --backfill` running, pid 160498) and the per-stock `rs_vs_broad`/`rs_rank`/`primary_sector` on the latest day are repopulated by `stock_rs --backfill` *after* it; self-heals — left the running job untouched (running stock_rs now would collide + use incomplete inputs). Tried **log-scaling the traded/delivery-value chart** for spike-readability but **REVERTED** — log on a *histogram* flattens every bar (they fill from the bottom of a ~10-decade log range, so all look ~full) and destroys the bright/muted delivery overlay (Ramana: "horrible"). Back to linear. The genuine spike case (NETWORK18 ~790× outlier crushing normal days on a linear axis) needs a **robust y-cap** (clip rare outliers, overlay intact) or a **two-line** treatment — NOT log on bars. **Shipped option A:** the value chart's axis is capped at ~the 98th percentile of traded value (`autoscaleInfoProvider` on both the traded + delivery histograms); spike days clip at the top and get an amber ▲ marker; the exact value is still on hover; the bright/muted overlay is intact; RELIANCE-style uniform stocks don't clip (cap ≈ max). Also **added 1Y/2Y/3Y/5Y/Max length buttons to the RS overlay** (`#rsRangeBar`, years-based + left-edge rebase, default Max) — it previously had only the D/W/M/Q interval toggle; verified against `b63d13f` that the price-chart range bar was never removed (the overlay just never had length control). The candle-chart **D/W/M/Q interval toggle (relay #3) — SHIPPED** (Ramana picked Option A): `#ivBar`/`setIv` resample ALL 4 stacked panes together so they stay time-synced — candle OHLC (first/max/min/last), DVPT pane = the period's PEAK day (NOT an average — true period DVPT is the MTF engine's job, D43-B), delivery % = period mean, traded/delivery value = period sum with the y-cap recomputed per interval; zone price-lines are horizontal so they're untouched. Client-side resample (isoWeek/month/quarter keys), no MTF dependency.
**WRAP (s22).** Everything above is shipped + deployed + verified on the VPS (every route 200; both stock-page charts now have interval **and** length parity; value chart readable). **Commits — `main`, NOT pushed (11 ahead of origin):** `c339098` Phase-1 loop · `8c57794` python-multipart pin · `005efde` sector default + peers · `16c6084`→`1648d8b` value-chart log-scale then revert · `4d618a5` RS-overlay length buttons · `926e2b5` value y-cap (option A) · `f1306b3` candle interval toggle (option A) · `9406712` peer cap 12. Working tree clean except the dormant `patearn.py` diff + held `mtf_signals.py` (untouched). **⚠ NEXT-SESSION FIRST CHECKS:** (1) the backend RS recompute (`index_signals` → `stock_rs --backfill`) was IN FLIGHT — verify it finished and `rs_vs_broad`/`rs_rank`/`primary_sector` repopulated universe-wide (stock-page RS panel + screener RS columns were sparse pending it; the overlay's `_narrow_sector` fallback masks it for the sector line only); (2) `git push`? (Ramana's call — 11 unpushed.) **Phase 2 = the instrument screener; Phase 3 = hover-help · comparison · news · onboarding · inline-row Track. Full autonomous run-book: `docs/next-session-kickstart.md`.**

### Perf work-stream — 2026-06-19 (parallel session) — dashboard delivery-model performance pass
Diagnosis: the app ships a full, uncompressed, uncacheable document per click (vs the fast-app model of a cached shell + thin precomputed data). **Shipped + committed (not pushed):** app-layer gzip (`GZipMiddleware`, `src/main.py`) + `scripts/db-maintenance.sh` (commits `6d9e5ee`, `197e54a`, `b63d13f`). **Render-layer todos handed to this D54 UI session** (Steps 1–5, dependency-gated) live in the transient `docs/ui-perf-handoff.md` → **folded into `ui-design.md §10`**; backend backlog + the `adj_close`/`conv` precompute in `docs/perf-architecture.md`. **The ONLY cross-session gate:** UI items 5/6 (read `adj_close`; screener `ORDER BY` precomputed `conv`) must wait for the perf stream's "columns live" signal (D47 recompute) — guard with `COALESCE` until then. Retire `ui-perf-handoff.md` (`git rm`) once Steps 1–5 are shipped/folded.

### Session 21 — 2026-06-19 — D53 CPR "Structure" pillar (the 4th strategy) — BUILT, verified, no-regression
The dedicated CPR build session (planned as "Session 2" in `docs/cpr-strategy-design.md §15`). Flow exactly as briefed: boot → spawn a **3-agent build panel** (quant · data engineer · strategy/product, run in parallel) → present the OPEN decisions (§11/§13 + conviction integration) to Ramana as **multiple-choice-with-recommendations** → he chose all four recommended defaults (`go`) → built end-to-end, no-regression.
**Shipped (D53):**
- **`cpr_signals` table** (`src/core/db.py`, additive; PK symbol·period_end_date·timeframe). Geometry+widths stored; rank/amplification/★ tier derived on read. `stock_signals` untouched.
- **`src/automation/cpr_signals.py`** — timeframe-parameterized engine that **self-resamples** split-adjusted D/W/M H/L/C bars from `bhavcopy_rows` (replicates `_period_key`; **no dependency on the held MTF D52**), computes the CPR primitive + clean-step U/∩ reversal + compression percentile + regime + freshness + confirmed. `--backfill`/`--recent`/`--symbol`, `--timeframe D|W|M|all`. Guards: split-adjust, |ret|>0.30 drop, equity-only, thin-bar skip.
- **Dashboard (`src/web/dashboard.py`, all additive):** screener **CPR column-group** (D/W/M width% + glyph + R-rank + ★ tier + Comp%, toggle chip) + **"🔷 CPR-confirmed" gate**; live **Strategies CPR card** (replaced "coming soon"); **`/dash/cpr`** (Reversals · Compression · per-TF EOD Reports tabs, with W/M "live for the current period" staleness badges); per-stock **CPR panel** (D·W·M strip + P/BC/TC table + verdict).
- **Conviction integration:** CPR kept **OUT of the composite number** (stays 0.55·pos+0.45·RS) — surfaced as a parallel ★ Structure tier + the gate, per panel consensus + Ramana's call. Glossary caveat updated.
**Verified:** CPR-math self-test (BULL_U/BEAR_INVU/clean-step/engulfing-exclusion/width÷pivot) + synthetic end-to-end backfill (800 D / 160 W / 40 M rows) + **full 19-route TestClient sweep all 200 (no regression)**. Docs current: `cpr-strategy-design.md` (§13 resolved, §16 build log), `metrics-glossary.md` (CPR section), this file.
**Deploy — ✅ COMPLETE + VERIFIED LIVE (2026-06-19 19:52 UTC).** scp'd `db.py`+`cpr_signals.py`+`dashboard.py`; wired `--recent` nightly after `stock_rs`; ran `--backfill --timeframe all` via a detached orchestrator (`scripts/cpr-deploy.sh`) that **waited out the in-progress deep-foundation chain** (index_signals→stock_rs→CNX-redeepen, ~3.5h) to avoid single-writer SQLite contention, then backfilled + self-checked + restarted the API. **Backfill ran in ~6 min** at ~12 symbols/sec (refuted the "tens of hours" record-count fear — CPR is a per-symbol single pass, not the index job's pairwise model). **Coverage:** Daily 5,414,738 rows · Weekly 1,156,243 · Monthly 272,548 — **all 2,358 equities × full history 2004-07-23→2026-06-19**. Latest-period fresh reversals: D 720 · W 656 · M 374. All routes 200 & fast (`/dash/cpr` ~0.07s, screener ~0.10s incl. the CPR join, stock page ~0.05s). *(Note: a stock page loaded mid-backfill briefly showed W/M "no data" — daily computes first; resolves on reload once W/M land. Not a bug.)* **Committed + pushed: `2edb6b5` → origin/main** (D52 MTF engine + `patearn.py` deliberately left out).

### Session 19 — 2026-06-19 — D49g: fixed the two session-18 P0 /dash/compare chart bugs (hands-on browser debug)

Resumed after the session-18 handoff. First, confirmed (read-only) the deep-history foundation is mid-build on the VPS: **Stage-1 raw bhav copy is COMPLETE** (2004-07-23→2026-06-18, 5,411 trading days, 9.33M rows) and **Stage-2 `signals --backfill` is ~55%** (3,029 / 5,490 dates, at ~Oct 2016, ETA ~12-14h). Noted the `corp_actions` step 404'd on all four NSE URLs this run (0 split/bonus rows — flagged for when the foundation lands). Did NOT disturb the running backfill.

Then fixed the **two P0 `/dash/compare` chart bugs** D49b–f left unresolved (full write-up: **§ Decision log D49g**). Debugged hands-on in the live browser via the Chrome MCP (navigate + JS DOM probes + screenshots) — which cracked it after the prior blind `py_compile`/route-200 loop. Both shared one root cause (boot acting before the chart's first layout settled): the correct left-edge rebase was overridden by a settle-time `subscribeVisibleTimeRangeChange` (**fix:** gate fluid re-anchor on real user input via a `userInteracted` flag), and the gutter name labels were computed before `priceToCoordinate()` was ready (**fix:** bounded rAF retry). Verified across a fresh load, all four range windows (each anchors to its own left edge), and a short 4th series (Nifty India Defence). Deployed `src/web/dashboard.py` via `scp` + `systemctl restart hermes-api`; committed [`ddf7640`](https://github.com/ramana-gottipati/hermes/commit/ddf7640). Then **D49h**: replicated the right-gutter name labels onto the D48 stock RS-overlay chart — and discovered it had the SAME boot-anchor drift (mis-anchoring to ~2026 instead of the 2021 series start, despite being the supposed "working reference"); fixed both with the deterministic earliest-anchor + the same `userInteracted` gate. Verified on RELIANCE. Finally **D50**: extended `/dash/compare` to overlay STOCKS as well as indices (new `?sym=` param + `_stock_levels` via adjust.py), defaulted the bare page to Nifty 500 + Nifty 50, and rebuilt the picker to type-ahead over the full equity universe (ticker prefix from 2 chars, company-name substring from 4, capped/debounced) + a stock-page "open in Compare ⇄" link. Verified live: ACE + TATASTEEL overlaid with 500/50; LT → LT/LTF/LTFOODS. Then **D51** (on Ramana's "add similar features to the stocks as well"): made the STOCK-page RS overlay itself configurable too — default benchmarks now Nifty 500 + Nifty 50 (+ sector), removable chips + the same + Add picker via a new `?cmp=` param, with the picker carrying the current overlay forward so Add appends (not replaces). Compare page kept intact. **Verified the D47 deep recompute FINISHED + clean** (5,406 dates, no errors; only 5 special-session days skipped — Muhurat/NSE-special-Saturdays; DVPT/scores/zones/key-price-D44/character-D43 all 95-100% non-null across 2011→2026, RS columns preserved not nulled). The one remaining gap — the **RS block** — is bounded by `index_rows` starting only 2021-06-02. On Ramana's "every field, oldest→newest, no exceptions", kicked off **`scripts/full-field-backfill.sh`** (detached, log `/var/log/hermes-fullfield.log`): deepen NSE index history (~2010) → recompute index signals/ratios → `stock_rs --backfill` so RS fills as deep as NSE's `ind_close_all` archive reaches. `stock_rs` is pure UPDATE of only the RS columns (safe — verified). **FINISHED ~13:06 UTC 2026-06-19**: RS deepened 2021→**2015-11-10**; `index_rows` fetched back to **2012-02-21** (NSE's `ind_close_all` archive floor); stock_rs wrote 4.42M RS rows + 2.05M ranked. The 2015-11 RS floor = the **NSE 2015 index rebrand** (S&P CNX 500 / CNX 500 → Nifty 500; CNX Nifty → Nifty 50; CNX Bank → Nifty Bank; …) — the levels exist to 2012-02 but the pre-2015 rows are under OLD names RS can't match. So launched **`scripts/normalize-cnx-rename.sh`** (detached, log `/var/log/hermes-cnxnorm.log`): normalize old→current index names in `index_rows` (merge only into an existing Nifty name; disjoint dates, no conflict) → re-run `index_signals --backfill` + `stock_rs --backfill` to push RS to 2012-02. **RUNNING** — next session: confirm RS floor reached 2012.

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
