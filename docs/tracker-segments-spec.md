# Tracker — per-segment content spec (research-grounded)

**Status:** design spec (2026-06-21). Researched best-in-class trackers + mapped to what Patearn can pull. Feeds the Phase-2/3 build of the Tracker umbrella (Dashboard · Portfolios · Watchlists · Performance). Companion to the memory note `tracker-workspace-redesign`.

## Method
Surveyed leading tools — **Tickertape** (portfolio analytics: diversification score, red flags, scorecard, return attribution, concentration, sector/market-cap allocation), **Kuvera / INDmoney / Zerodha Console** (multi-asset tracking, tax harvesting, allocation), and generic standards for **performance metrics** (XIRR / CAGR / absolute / drawdown / benchmark), **alerts** (price / % / technical / corporate-event / portfolio-risk), and **dashboard KPIs** (net worth, allocation, holdings, movers). Then graded each candidate feature by what our data can actually deliver.

## What we can PULL / compute today (data inventory)
- **EOD OHLCV + delivery** per stock (NSE bhav copy) — our "CMP" = last close; "Day Δ" = close vs prev_close. **No intraday/live** (deliberate; fine for a positional/swing tracker).
- **DVPT signals** — delivery-value-per-trade, p_score/r_score, trigger rank, `is_ath_dvpt`, and **`accum_character`** (ACCUMULATION / DISTRIBUTION / CONSOLIDATION / NEUTRAL).
- **Relative Strength** — `rs_rank` (1–99), vs sector, vs broad.
- **CPR structure**, **pt14 quality** (cached), **Conviction** (composite).
- **Index data** (Nifty 50/500/sector) → benchmark return + excess.
- **Corporate actions** (`corp_actions`: split/bonus/dividend) → dividends received, pending ex-dates, split-adjustment.
- **News feed** (RSS, classified, per-ticker) → news per holding/watch.
- **Screener fundamentals** (cached) + `nse_equity_list` → sector, P/E, ROE, market-cap.
- **`stocks_in_play`** — book, qty, entry price/date, target, stop, strategy, thesis, frozen snapshot, status.

**Pull legend below:** ✅ have now · ⚙ needs a new compute/pull (small) · ✦ Patearn-only edge (no generic tracker has it).

## Our differentiator (lead with this)
Generic trackers stop at price/allocation/quality. We already compute **DVPT character, RS, CPR, Conviction, pt14** — so every holding can answer *"is my thesis still valid — is the strong hand still ACCUMULATING, or now DISTRIBUTING; is RS decaying; has conviction drifted since I bought?"* That live thesis-health is the thing Tickertape/Kuvera/INDmoney cannot show. It should be front-and-centre in Portfolios, Watchlists, and the Dashboard's "needs attention".

## Honest constraints (set expectations)
- **EOD, not live** — values refresh after the daily bhav ingest, not tick-by-tick.
- **Manual add + CSV/Excel import**, not broker auto-sync (no account aggregation).
- **Promoter-pledge / ASM / GSM red flags** (Tickertape-style) need data we don't pull yet — a possible future Screener pull; for now our red flags are price/signal-native.

---

## 1) DASHBOARD — the cockpit ("where do I stand right now")
| Item | Pull |
|---|---|
| Net-worth tiles: **Total value · Invested · Unrealized ₹P&L (+%) · Today's Δ (₹+%) · Realized ₹ (closed)** | ✅ |
| **Allocation** — by sector, by book, by market-cap (large/mid/small); **concentration** (top 3/5/10 % of value) | ⚙ sector/mcap map |
| **Today's movers** among holdings (top gainers / losers, EOD) | ✅ |
| **Needs attention** (Patearn red flags): character flipped to **DISTRIBUTION**, **RS decay**, **below / near stop**, **over-concentration** | ✦ |
| **Alerts firing** (in-app) | ⚙ alert engine |
| **News** for held + watched names | ✅ |
| **Upcoming corporate actions** (ex-div / bonus / split soon) | ✅ |
| **Top contributors / detractors** (attribution preview) | ✅ |

## 2) PORTFOLIOS — manage holdings (per named book)
**Per-book header:** Invested · Value · ₹P&L (+%) · **XIRR** · Day Δ · count.
| Per-holding column | Pull |
|---|---|
| Symbol · **Sector** · Book · Strategy | ✅ / ⚙ sector |
| Entry date · Entry ₹ · **Qty** · **Invested ₹** | ✅ |
| CMP · **Day Δ** · P/L % · **₹ P&L** | ✅ |
| **Target (dist %)** · **Stop (dist %)** · Days held | ✅ |
| **Thesis health** — character now · RS rank · **Conviction then→now** drift | ✦ |
| **Dividends received** (since entry, qty × ex-div) | ✅ |
| News · Edit · Close | ✅ |
| Per-book **allocation / concentration** view | ⚙ |

## 3) WATCHLISTS — candidates (per named list)
| Per-item column | Pull |
|---|---|
| Symbol · **Sector** · List · Basis/strategy | ✅ / ⚙ |
| Added date · **Days watched** · Price-then · CMP · **% change since** | ✅ |
| **Live signals** — DVPT rank + character · RS rank · CPR · Conviction · pt14 | ✦ |
| **Alert** (set / active) | ⚙ alert engine |
| News · Promote · Edit · Remove | ✅ |
| **"Ready to act"** — watch items now firing a strong setup (fresh ACCUM + near key price, RS breakout) | ✦ |

**Alert types to support (EOD-evaluated):** price crosses level · % move since add · near 52w high/low · **DVPT trigger fires** · **RS rank > N** · **character flips to ACCUM** · near target/stop. (In-app first; Telegram push when unblocked.)

## 4) PERFORMANCE — the scoreboard ("over time")
| Item | Pull |
|---|---|
| **Total return (₹ + %)** · **XIRR** (cash-flow weighted — the right metric given entry dates+amounts) · **CAGR** · realized vs unrealized | ✅ / ⚙ XIRR |
| **vs Nifty 500 excess** | ✅ |
| **Max drawdown** (portfolio value curve) | ⚙ value series |
| **Win-rate · avg hold** | ✅ |
| **Hit-rate by strategy + by book** | ✅ |
| **Return attribution** — top contributors / detractors by holding · sector · book · strategy | ✅ |
| **Equity curve vs benchmark** (portfolio value over time) | ⚙ value series |
| **Closed-trades log** (realized P&L per closed position) | ✅ |

---

## Suggested build order
1. **Smart CSV/Excel importer** (already queued) — get holdings in.
2. **Enrich Portfolios** — sector + ₹ columns + target/stop distance + days held + **thesis-health** (the differentiator) + dividends.
3. **Performance** — XIRR + return attribution + closed-trades log + drawdown/equity-curve.
4. **Dashboard** — allocation + concentration + movers + red-flags + news + corporate actions.
5. **Watchlists alerts engine** (EOD eval; in-app) + "ready to act".
6. Later: promoter-pledge/ASM/GSM pull; weighted-avg lot grouping; Telegram push.

## Sources
- Tickertape — [diversification/red-flags/forecast](https://www.tickertape.in/blog/diversification-score-redflags-and-portfolio-forecast-our-new-updates-make-portfolio-analysis-quick-and-easy/), [return attribution](https://www.tickertape.in/blog/a-simple-way-of-looking-at-return-attribution-in-your-portfolio/)
- [Best portfolio trackers in India (Pocketful)](https://www.pocketful.in/blog/best-free-stock-portfolio-trackers-in-india/)
- XIRR vs CAGR vs absolute — [Axis MF](https://www.axismf.com/mutual-fund-knowledge-centre/articles/how-to-assess-mutual-fund-returns), [Quantum AMC](https://www.quantumamc.com/article/understanding-xirr-a-key-metric-for-mutual-fund-performance)
- Alerts/watchlist standards — [Guardfolio](https://www.guardfolio.ai/best-stock-alert-app), [Stock Alarm](https://pro.stockalarm.io/blog/best-stock-alert-apps-2026)
- Dashboard KPIs — [Tempo](https://www.tempo.io/blog/essential-portfolio-management-metrics)
