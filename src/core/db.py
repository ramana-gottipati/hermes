"""SQLite-backed persistence layer for Hermes.

Day-1 scope: small, synchronous, single-process. Plenty for personal-agent
volumes. Swap to Postgres + asyncpg when there's a real reason (multi-process,
high write concurrency, or shared state across boxes).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "hermes.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA_BASE = """
CREATE TABLE IF NOT EXISTS conversations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    title            TEXT,
    telegram_user_id INTEGER
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role            TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS sent_news (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    source  TEXT    NOT NULL,
    url     TEXT    NOT NULL UNIQUE,
    title   TEXT    NOT NULL,
    sent_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sent_news_url ON sent_news(url);

CREATE TABLE IF NOT EXISTS news_destinations (
    chat_id    INTEGER PRIMARY KEY,
    chat_title TEXT,
    chat_type  TEXT,
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    added_by   INTEGER
);

CREATE TABLE IF NOT EXISTS patearn_destinations (
    chat_id    INTEGER PRIMARY KEY,
    chat_title TEXT,
    chat_type  TEXT,
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    added_by   INTEGER
);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol     TEXT PRIMARY KEY,
    note       TEXT,
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    added_by   INTEGER
);

CREATE TABLE IF NOT EXISTS earnings_triggers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    news_url     TEXT NOT NULL,
    news_title   TEXT,
    triggered_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(symbol, news_url)
);

CREATE TABLE IF NOT EXISTS screen_candidates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    verdict         TEXT NOT NULL CHECK (verdict IN ('PASS', 'WATCH')),
    rationale       TEXT,
    signals_json    TEXT,
    news_url        TEXT NOT NULL,
    news_title      TEXT,
    news_source     TEXT,
    screened_at     TEXT NOT NULL DEFAULT (datetime('now')),
    digest_sent_at  TEXT,
    your_note       TEXT,
    your_status     TEXT NOT NULL DEFAULT 'new',
    UNIQUE(symbol, news_url)
);
CREATE INDEX IF NOT EXISTS idx_candidates_screened ON screen_candidates(screened_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_digest   ON screen_candidates(digest_sent_at);
CREATE INDEX IF NOT EXISTS idx_candidates_status   ON screen_candidates(your_status);

-- Wide bhav copy storage — every column NSE publishes + raw_json for absolute
-- completeness. Primary source is sec_bhavdata_full (has DELIV_QTY / DELIV_PER).
-- For dates where sec_bhavdata_full isn't available, we fall back to UDIFF or
-- legacy bhavcopy (no delivery data — deliv_qty/deliv_per will be NULL).
CREATE TABLE IF NOT EXISTS bhavcopy_rows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    series          TEXT,
    instrument_type TEXT,
    segment         TEXT,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    last_price      REAL,
    prev_close      REAL,
    avg_price       REAL,
    settlement_price REAL,
    volume          INTEGER,
    value           REAL,
    num_trades      INTEGER,
    deliv_qty       INTEGER,
    deliv_per       REAL,
    open_interest   INTEGER,
    change_in_oi    INTEGER,
    isin            TEXT,
    expiry_date     TEXT,
    strike_price    REAL,
    option_type     TEXT,
    format_version  TEXT,
    raw_json        TEXT,
    UNIQUE(symbol, trade_date, series, instrument_type)
);
CREATE INDEX IF NOT EXISTS idx_bhav_sym_date ON bhavcopy_rows(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_bhav_date     ON bhavcopy_rows(trade_date);
CREATE INDEX IF NOT EXISTS idx_bhav_series   ON bhavcopy_rows(series);

-- Backfill progress tracking — which dates we've successfully ingested
CREATE TABLE IF NOT EXISTS bhavcopy_dates (
    trade_date    TEXT PRIMARY KEY,
    format_version TEXT,
    row_count     INTEGER,
    has_delivery  INTEGER DEFAULT 0,
    ingested_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Corporate actions: splits, bonuses, dividends, rights, mergers. Sourced
-- from NSE corporate-actions CSV feeds. Required for safe cross-period
-- volume comparisons (value-based metrics are naturally action-neutral).
CREATE TABLE IF NOT EXISTS corporate_actions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    action_type  TEXT NOT NULL,
    ex_date      TEXT,
    record_date  TEXT,
    ratio_from   REAL,
    ratio_to     REAL,
    details      TEXT,
    source       TEXT,
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(symbol, action_type, ex_date, details)
);
CREATE INDEX IF NOT EXISTS idx_corp_sym_ex ON corporate_actions(symbol, ex_date);

-- D32 Index data — daily OHLC + P/E + P/B + Div Yield per NSE index.
-- ~50 indexes × 1 row/day. Sourced from ind_close_all_DDMMYYYY.csv.
CREATE TABLE IF NOT EXISTS index_rows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_name      TEXT    NOT NULL,
    trade_date      TEXT    NOT NULL,
    open_value      REAL,
    high_value      REAL,
    low_value       REAL,
    close_value     REAL,
    points_change   REAL,
    change_pct      REAL,
    volume          INTEGER,
    turnover_cr     REAL,
    pe              REAL,
    pb              REAL,
    dividend_yield  REAL,
    ingested_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(index_name, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_index_rows_name_date ON index_rows(index_name, trade_date);
CREATE INDEX IF NOT EXISTS idx_index_rows_date      ON index_rows(trade_date);

CREATE TABLE IF NOT EXISTS index_dates (
    trade_date    TEXT PRIMARY KEY,
    row_count     INTEGER,
    ingested_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- D32 Pre-computed nightly per-index signals — returns, MA, 52w positioning,
-- and the denormalized RS vs broad benchmark (Nifty 500 default).
CREATE TABLE IF NOT EXISTS index_signals (
    index_name           TEXT NOT NULL,
    trade_date           TEXT NOT NULL,
    close_value          REAL,
    -- Returns over windows
    ret_1d_pct           REAL,
    ret_1w_pct           REAL,
    ret_1m_pct           REAL,
    ret_3m_pct           REAL,
    ret_6m_pct           REAL,
    ret_12m_pct          REAL,
    -- Moving averages on level
    pct_above_50d_avg    REAL,
    pct_above_200d_avg   REAL,
    -- 52w positioning
    pct_off_52w_high     REAL,
    pct_above_52w_low    REAL,
    -- Denormalized RS vs broad benchmark (default = NIFTY 500)
    broad_benchmark      TEXT,
    rs_vs_broad_today    REAL,
    rs_vs_broad_slope_1m  REAL,
    rs_vs_broad_slope_3m  REAL,
    rs_vs_broad_slope_6m  REAL,
    rs_vs_broad_slope_12m REAL,
    rs_vs_broad_above_50ma   INTEGER,
    rs_vs_broad_above_200ma  INTEGER,
    rs_vs_broad_new_52w_high INTEGER,
    rs_vs_broad_trend_state  TEXT,
    computed_at          TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (index_name, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_index_signals_date_trend
    ON index_signals(trade_date, rs_vs_broad_trend_state);

-- D32 Generic ratio time series. Symmetric: numerator/denominator can be
-- any (index, index) or (stock, index) pair. Source of truth for ratio charts.
CREATE TABLE IF NOT EXISTS ratio_rows (
    numerator    TEXT NOT NULL,
    denominator  TEXT NOT NULL,
    trade_date   TEXT NOT NULL,
    num_close    REAL,
    den_close    REAL,
    ratio        REAL,
    computed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (numerator, denominator, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_ratio_num_date ON ratio_rows(numerator, trade_date);
CREATE INDEX IF NOT EXISTS idx_ratio_den_date ON ratio_rows(denominator, trade_date);

-- D32 Pre-computed ratio signals — MA, slope, breakout flags, trend state.
CREATE TABLE IF NOT EXISTS ratio_signals (
    numerator       TEXT NOT NULL,
    denominator     TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    ratio           REAL,
    ratio_ma_20     REAL,
    ratio_ma_50     REAL,
    ratio_ma_200    REAL,
    ratio_high_50d  REAL,
    ratio_low_50d   REAL,
    ratio_high_200d REAL,
    ratio_high_52w  REAL,
    ratio_low_52w   REAL,
    slope_1m_pct    REAL,
    slope_3m_pct    REAL,
    slope_6m_pct    REAL,
    slope_12m_pct   REAL,
    above_50_ma      INTEGER,
    above_200_ma     INTEGER,
    cross_50_today   INTEGER,
    cross_200_today  INTEGER,
    new_50d_high     INTEGER,
    new_200d_high    INTEGER,
    new_52w_high     INTEGER,
    pct_below_52w_high REAL,
    trend_state     TEXT,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (numerator, denominator, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_ratio_signals_trend
    ON ratio_signals(trade_date, trend_state);

-- D32 Stock-index membership (constituent lists). One row per (symbol, index).
-- Refreshed weekly. snapshot_date tracks when the constituent was current.
CREATE TABLE IF NOT EXISTS stock_index_membership (
    symbol         TEXT NOT NULL,
    index_name     TEXT NOT NULL,
    snapshot_date  TEXT NOT NULL,
    weight_pct     REAL,
    PRIMARY KEY (symbol, index_name, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_membership_symbol ON stock_index_membership(symbol);
CREATE INDEX IF NOT EXISTS idx_membership_index  ON stock_index_membership(index_name);

-- Pre-computed nightly rolling signals per (symbol, date). Captures both the
-- regular baseline (flat averages) and the power-delivery signal (top-N within
-- a window). All values are RUPEES, naturally split/bonus invariant.
CREATE TABLE IF NOT EXISTS stock_signals (
    symbol          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    -- Today's primary values
    delivery_value_today      REAL,
    total_value_today         REAL,
    delivery_value_per_trade  REAL,
    -- Flat baselines (regular averages, excluding today)
    avg_dvpt_5d     REAL,
    avg_dvpt_10d    REAL,
    avg_dvpt_30d    REAL,
    avg_dvpt_60d    REAL,
    avg_dvpt_90d    REAL,
    avg_dvpt_180d   REAL,
    avg_dvpt_365d   REAL,
    -- Power deliveries: average of top-N within a window, excluding today
    power_dvpt_1m   REAL,
    power_dvpt_2m   REAL,
    power_dvpt_3m   REAL,
    power_dvpt_6m   REAL,
    -- Today's reading vs the baselines
    ratio_today_vs_avg_30d    REAL,
    ratio_today_vs_power_1m   REAL,
    ratio_today_vs_power_3m   REAL,
    -- Data sufficiency flag — not all windows may have enough history
    data_points_used INTEGER,
    computed_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_signals_date ON stock_signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_power1m ON stock_signals(trade_date, ratio_today_vs_power_1m DESC);

-- Screener.in scraped fundamentals (cached, refreshed periodically)
CREATE TABLE IF NOT EXISTS fundamentals (
    symbol             TEXT PRIMARY KEY,
    company_name       TEXT,
    fetched_at         TEXT NOT NULL DEFAULT (datetime('now')),
    market_cap_cr      REAL,
    current_price      REAL,
    pe                 REAL,
    pb                 REAL,
    book_value         REAL,
    dividend_yield     REAL,
    roce               REAL,
    roe                REAL,
    roce_3y_avg        REAL,
    roe_3y_avg         REAL,
    debt_to_equity     REAL,
    promoter_holding   REAL,
    promoter_pledge    REAL,
    fii_holding        REAL,
    dii_holding        REAL,
    sales_growth_5y    REAL,
    profit_growth_5y   REAL,
    sales_growth_3y    REAL,
    profit_growth_3y   REAL,
    sales_growth_ttm   REAL,
    profit_growth_ttm  REAL,
    opm_latest         REAL,
    eps_ttm            REAL,
    debt_cr            REAL,
    cash_cr            REAL,
    interest_coverage  REAL,
    raw_html_snippet   TEXT
);
CREATE INDEX IF NOT EXISTS idx_fundamentals_fetched ON fundamentals(fetched_at);

-- Rule-based patearn pattern scores (one row per scoring run per stock)
CREATE TABLE IF NOT EXISTS pattern_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    scored_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pws             REAL,
    ns_base         REAL,
    ns_pessimistic  REAL,
    ns_optimistic   REAL,
    pac             INTEGER,
    tier            TEXT,
    qg_pass         INTEGER,
    hard_disqualified INTEGER,
    disqualifier_reasons TEXT,
    detail_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_pattern_scores_symbol ON pattern_scores(symbol, scored_at DESC);

-- D42 NSE equity universe (from EQUITY_L.csv) — the allowlist that keeps the
-- scanners EQUITY-ONLY. ETFs / mutual-fund units are NOT in EQUITY_L, and our
-- bhav source (sec_bhavdata_full) carries no ISIN, so a symbol allowlist is the
-- robust equity-vs-ETF separator. Refreshed nightly by src.automation.equity_list;
-- the table is replaced only on a SUCCESSFUL fetch (never wiped on failure), so
-- the scanner filter `symbol IN (SELECT symbol FROM nse_equity_list)` can rely on it.
CREATE TABLE IF NOT EXISTS nse_equity_list (
    symbol        TEXT PRIMARY KEY,
    company_name  TEXT,
    isin          TEXT,
    listing_date  TEXT,
    snapshot_date TEXT
);

-- ===========================================================================
-- Multi-timeframe (MTF) foundation — D52 (was labelled D43 in
-- docs/multi-timeframe-positioning-design.md, predating the now-shipped D43).
-- True weekly/monthly resampled bars + signals, materialized nightly. The daily
-- stock_signals table is UNTOUCHED; these are separate, smaller tables (weekly
-- ~1/5, monthly ~1/22 of daily rows) so the 2.35M-row daily hot table is not
-- bloated/locked (decision D43-J in the design doc). All re-derivable from the
-- raw bhavcopy_rows archive (Doctrine C). Period DVPT = Sum(delivery value) /
-- Sum(num_trades) over the bar — NEVER the average of daily DVPTs (D43-B).
-- ===========================================================================

-- Weekly resampled OHLC + delivery bars (one row per symbol per ISO week).
CREATE TABLE IF NOT EXISTS bars_weekly (
    symbol          TEXT NOT NULL,
    week_end_date   TEXT NOT NULL,     -- last trading day of the ISO week (key)
    iso_year        INTEGER,
    iso_week        INTEGER,
    open            REAL,              -- first day's open
    high            REAL,              -- max over the week
    low             REAL,              -- min over the week
    close           REAL,              -- last day's close (raw)
    prev_close      REAL,              -- prior week's close (raw)
    adj_close       REAL,              -- last day's split/bonus-adjusted close
    volume          INTEGER,           -- sum
    deliv_qty       INTEGER,           -- sum
    delivery_value  REAL,              -- sum of (deliv_qty * close) per day
    num_trades      INTEGER,           -- sum
    turnover        REAL,              -- sum of daily traded value
    n_days          INTEGER,           -- trading days in the bar
    is_partial      INTEGER DEFAULT 0, -- 1 = current, not-yet-closed week
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, week_end_date)
);
CREATE INDEX IF NOT EXISTS idx_bars_weekly_date ON bars_weekly(week_end_date);

-- Monthly resampled OHLC + delivery bars (one row per symbol per calendar month).
CREATE TABLE IF NOT EXISTS bars_monthly (
    symbol          TEXT NOT NULL,
    month_end_date  TEXT NOT NULL,     -- last trading day of the month (key)
    ym              TEXT,              -- 'YYYY-MM'
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    prev_close      REAL,
    adj_close       REAL,
    volume          INTEGER,
    deliv_qty       INTEGER,
    delivery_value  REAL,
    num_trades      INTEGER,
    turnover        REAL,
    n_days          INTEGER,
    is_partial      INTEGER DEFAULT 0,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, month_end_date)
);
CREATE INDEX IF NOT EXISTS idx_bars_monthly_date ON bars_monthly(month_end_date);

-- Weekly signals — the D28/D31 two-tier scheme computed on weekly bars. Windows
-- scaled per the design doc table: 4/8/13/26/52 weeks, P-tier top-N 1/1/2/4/6.
CREATE TABLE IF NOT EXISTS weekly_signals (
    symbol          TEXT NOT NULL,
    week_end_date   TEXT NOT NULL,
    dvpt            REAL,              -- period DVPT = sum(deliv value)/sum(trades)
    delivery_value_period REAL,        -- absolute delivery footprint (rupees)
    total_value_period    REAL,        -- absolute traded turnover (rupees)
    num_trades_period     INTEGER,
    -- R-tier flat means over the last N weekly bars
    avg_dvpt_w4 REAL, avg_dvpt_w8 REAL, avg_dvpt_w13 REAL, avg_dvpt_w26 REAL, avg_dvpt_w52 REAL,
    -- P-tier mean of top-N within the window
    power_dvpt_w4 REAL, power_dvpt_w8 REAL, power_dvpt_w13 REAL, power_dvpt_w26 REAL, power_dvpt_w52 REAL,
    -- Institutional price zones (avg close on the R / P baseline bars)
    avg_close_rw4 REAL, avg_close_rw8 REAL, avg_close_rw13 REAL, avg_close_rw26 REAL, avg_close_rw52 REAL,
    avg_close_pw4 REAL, avg_close_pw8 REAL, avg_close_pw13 REAL, avg_close_pw26 REAL, avg_close_pw52 REAL,
    r_score         INTEGER,
    p_score         INTEGER,
    trigger_rank    TEXT,
    next_p_above    TEXT,
    gap_to_next_p_pct REAL,
    is_ath_dvpt     INTEGER,
    hot_bars_avg_price REAL,
    price_vs_hot_avg_pct REAL,
    n_bars_used     INTEGER,
    is_partial      INTEGER DEFAULT 0,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, week_end_date)
);
CREATE INDEX IF NOT EXISTS idx_weekly_signals_date ON weekly_signals(week_end_date);

-- Monthly signals — same scheme on monthly bars. Windows 3/6/12/18/24 months,
-- P-tier top-N 1/1/2/3/4.
CREATE TABLE IF NOT EXISTS monthly_signals (
    symbol          TEXT NOT NULL,
    month_end_date  TEXT NOT NULL,
    dvpt            REAL,
    delivery_value_period REAL,
    total_value_period    REAL,
    num_trades_period     INTEGER,
    avg_dvpt_m3 REAL, avg_dvpt_m6 REAL, avg_dvpt_m12 REAL, avg_dvpt_m18 REAL, avg_dvpt_m24 REAL,
    power_dvpt_m3 REAL, power_dvpt_m6 REAL, power_dvpt_m12 REAL, power_dvpt_m18 REAL, power_dvpt_m24 REAL,
    avg_close_rm3 REAL, avg_close_rm6 REAL, avg_close_rm12 REAL, avg_close_rm18 REAL, avg_close_rm24 REAL,
    avg_close_pm3 REAL, avg_close_pm6 REAL, avg_close_pm12 REAL, avg_close_pm18 REAL, avg_close_pm24 REAL,
    r_score         INTEGER,
    p_score         INTEGER,
    trigger_rank    TEXT,
    next_p_above    TEXT,
    gap_to_next_p_pct REAL,
    is_ath_dvpt     INTEGER,
    hot_bars_avg_price REAL,
    price_vs_hot_avg_pct REAL,
    n_bars_used     INTEGER,
    is_partial      INTEGER DEFAULT 0,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, month_end_date)
);
CREATE INDEX IF NOT EXISTS idx_monthly_signals_date ON monthly_signals(month_end_date);

-- ===========================================================================
-- CPR (Central Pivot Range) "STRUCTURE" pillar — D53. The 4th Patearn strategy,
-- beside Positioning (DVPT), Relative Strength, Quality (pt14). A small family
-- of models over ONE primitive: the 3-line CPR (Pivot / BC / TC) projected from
-- a period's prior H/L/C, read identically at three degrees — Daily / Weekly /
-- Monthly. Materialized nightly per (symbol, period_end_date, timeframe).
--
--   GEOMETRY + widths are STORED (objective). The narrowness RANK (R1–R4 vs the
--   query-time max_width_pct knob), the cross-TF AMPLIFICATION and the ★ CONVICTION
--   TIER are DERIVED ON READ — so the knob/weights stay tunable without
--   re-materializing (mirrors D43-G; decision CPR-A4).
--
--   Self-resampled from the raw bhavcopy_rows archive on SPLIT-ADJUSTED OHLC —
--   NOT blocked on the held MTF bars_weekly/bars_monthly (decision CPR-A5; design
--   §9). stock_signals is UNTOUCHED — purely additive, zero regression.
--   Design + decision log: docs/cpr-strategy-design.md.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS cpr_signals (
    symbol             TEXT NOT NULL,
    period_end_date    TEXT NOT NULL,    -- last trading day of the period (= trade_date for D)
    timeframe          TEXT NOT NULL,    -- 'D' / 'W' / 'M'
    -- C0 CPR — built from the PRIOR completed period's adjusted H/L/C (§2)
    p                  REAL,             -- pivot = (H + L + C) / 3
    bc                 REAL,             -- (H + L) / 2
    tc                 REAL,             -- 2P − BC
    width_pct          REAL,             -- (TC − BC) / P × 100  (÷ pivot — OPEN-4)
    -- Prior two bands' widths — feed the R1–R4 narrowness rank derived on read
    c1_width_pct       REAL,             -- C1 = the valley/peak bar
    c2_width_pct       REAL,             -- C2 = the lead-in bar
    -- 3B compression — own-history percentile of the current width (§5.2).
    -- High = unusually coiled FOR THIS STOCK (fraction of trailing N widths wider
    -- than now; N ≈ 252 D / 52 W / 24 M). The truer "unusual" than a flat %.
    compression_pctile REAL,
    -- 3A reversal pattern (clean directional both-lines step — OPEN-1)
    pattern            TEXT,             -- 'BULL_U' / 'BEAR_INVU' / 'NONE'
    leg_in_clean       INTEGER,          -- 1 = C2→C1 was a clean directional step
    leg_turn_clean     INTEGER,          -- 1 = C1→C0 was a clean directional step
    -- 3A.3 secondary quality — displayed; optional rank inputs, not gates
    separation_pct     REAL,             -- (C0.BC − C1.TC) / C1.TC × 100  (>0 = full non-overlap on turn leg)
    depth_pct          REAL,             -- |C1.P − C2.P| / C2.P × 100  (size of the move being reversed)
    -- 3C regime — sign(adj_close − P); the higher-TF trend context for amplification
    regime             INTEGER,          -- +1 above pivot / −1 below / 0 at
    -- §6 freshness + engagement
    days_since_pattern INTEGER,          -- 0 = formed on this bar (fresh); NULL = no pattern
    confirmed          INTEGER,          -- 1 = bull-U & close > C0.TC, or bear-∩ & close < C0.BC
    -- audit / display / sufficiency
    close              REAL,             -- raw close on period_end_date (for display)
    adj_used           INTEGER DEFAULT 1,-- 1 = band built from split/bonus-adjusted OHLC (always 1)
    is_partial         INTEGER DEFAULT 0,-- 1 = current, not-yet-closed W/M period (week/month-to-date)
    n_bars_used        INTEGER,          -- prior period bars available (history depth)
    computed_at        TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, period_end_date, timeframe)
);
-- Latest-day universe screen per TF (the screener + compression scan).
CREATE INDEX IF NOT EXISTS idx_cpr_tf_date         ON cpr_signals(timeframe, period_end_date);
-- Per-symbol latest D/W/M (the stock page + cross-TF amplification join).
CREATE INDEX IF NOT EXISTS idx_cpr_sym_tf          ON cpr_signals(symbol, timeframe, period_end_date DESC);
-- "What fired on date X for TF T" (the per-TF EOD reports).
CREATE INDEX IF NOT EXISTS idx_cpr_tf_date_pattern ON cpr_signals(timeframe, period_end_date, pattern);

-- ===========================================================================
-- D54 (UI Phase 1) — the strategy → watchlist → portfolio ACTION LOOP. One row
-- per tracked idea. status 'watch' = the lightweight watchlist tier (no entry
-- needed); 'open' = a committed position-under-a-strategy (captures entry +
-- target/stop + a frozen as-of-day snapshot); 'closed' = exited. snapshot_json
-- FREEZES the signal values at add time (conviction, p/r, rank, ×power, key-gap,
-- RS, pt14, character) so the tracker can honestly show "what it looked like
-- when added" vs live — the daily stock_signals row is overwritten/appended
-- nightly and cannot be reconstructed later (the one place denormalization is
-- correct: it's an audit record, not a cache). Mark-to-market + hit-rate are
-- pure-SQL / indexed point-lookups on read. The legacy `watchlist` table
-- (symbol PK) is kept untouched (the scope=watch screener source); this is the
-- richer, lifecycle-aware tracker behind /dash/portfolios·watchlists·tracker.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS stocks_in_play (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    strategy      TEXT NOT NULL DEFAULT 'Manual',
    book          TEXT NOT NULL DEFAULT 'Main',   -- named portfolio/watchlist book
    status        TEXT NOT NULL DEFAULT 'open',   -- 'watch' | 'open' | 'closed'
    date_added    TEXT NOT NULL DEFAULT (datetime('now')),
    entry_price   REAL,
    qty           REAL,                              -- shares held (for ₹ P&L); NULL = untracked
    price_target  REAL,
    stop_loss     REAL,
    entry_thesis  TEXT,
    snapshot_json TEXT,                            -- frozen as-of-add signal values
    exit_date     TEXT,
    exit_price    REAL,
    exit_reason   TEXT,
    notes         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sip_status ON stocks_in_play(status, strategy);
CREATE INDEX IF NOT EXISTS idx_sip_symbol ON stocks_in_play(symbol);
"""


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """Idempotently add a column to an existing table (SQLite has no IF NOT EXISTS for columns)."""
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _tune(conn: sqlite3.Connection) -> None:
    """Concurrency + cache pragmas. WAL lets reads (the dashboard) proceed
    WITHOUT blocking on writes (the nightly chain / backfills) — the fix for the
    slow clicks + 'database is locked'. busy_timeout waits out brief contention
    instead of erroring; the rest warm the cache. journal_mode=WAL is persistent
    (set once, stays); the others are per-connection so are set on each open."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -65536")     # ~64 MB page cache
    conn.execute("PRAGMA mmap_size = 268435456")   # 256 MB memory-map
    conn.execute("PRAGMA foreign_keys = ON")


def _init() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _tune(conn)
    try:
        # 1. Base schema — tables + non-telegram indexes (safe on fresh and existing DBs).
        conn.executescript(SCHEMA_BASE)
        # 2. Migrate existing DBs that pre-date the telegram_user_id column.
        _ensure_column(conn, "conversations", "telegram_user_id", "INTEGER")
        # 2b. Named portfolio/watchlist books (Tracker umbrella — D54 follow-up).
        _ensure_column(conn, "stocks_in_play", "book", "TEXT NOT NULL DEFAULT 'Main'")
        # 2c. Share quantity (absolute ₹ P&L / invested / current value).
        _ensure_column(conn, "stocks_in_play", "qty", "REAL")
        # 3. Index on the new column (now guaranteed to exist).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_tg_user ON conversations(telegram_user_id, id DESC)"
        )
        # 4. Migration: previous schema had a slim daily_prices table. We replaced
        #    it with the wider bhavcopy_rows. Drop the old table if it exists and
        #    is empty (data wasn't shipped in production yet).
        conn.execute("DROP TABLE IF EXISTS daily_prices")

        # 4b. Two-tier signal columns on stock_signals (Decision D28).
        # R-tier rolling averages aligned with P-tier windows (22/44/66/132/264 trading days).
        _ensure_column(conn, "stock_signals", "avg_dvpt_1m",          "REAL")
        _ensure_column(conn, "stock_signals", "avg_dvpt_2m",          "REAL")
        _ensure_column(conn, "stock_signals", "avg_dvpt_3m",          "REAL")
        _ensure_column(conn, "stock_signals", "avg_dvpt_6m",          "REAL")
        _ensure_column(conn, "stock_signals", "avg_dvpt_12m",         "REAL")
        # P-tier — 12-month power baseline (top-80 of last 264 trading days)
        _ensure_column(conn, "stock_signals", "power_dvpt_12m",       "REAL")
        # Score columns — count of R/P baselines today's DVPT beats (0-5 each)
        _ensure_column(conn, "stock_signals", "r_score",              "INTEGER")
        _ensure_column(conn, "stock_signals", "p_score",              "INTEGER")
        # Rank derived from p_score (SS=5, S=4, A=3, B=2, C=1, '-'=0)
        _ensure_column(conn, "stock_signals", "trigger_rank",         "TEXT")
        # ATH flag — today's DVPT is highest in the stock's entire history
        _ensure_column(conn, "stock_signals", "is_ath_dvpt",          "INTEGER")
        # Hot-day average close + price gap vs that average
        _ensure_column(conn, "stock_signals", "hot_days_avg_price",   "REAL")
        _ensure_column(conn, "stock_signals", "price_vs_hot_avg_pct", "REAL")
        # Near-break pointer — lowest P-baseline today did NOT beat + how far below
        _ensure_column(conn, "stock_signals", "next_p_above",         "TEXT")
        _ensure_column(conn, "stock_signals", "gap_to_next_p_pct",    "REAL")

        # 4d. Institutional price-zone columns (D31). For every R-tier and
        # P-tier baseline, store the avg close on the days that contributed
        # to that baseline. R-tier: avg close over the full window. P-tier:
        # avg close on the same top-N-by-DVPT days that defined power_dvpt_*.
        # Lets us read "where was the institutional bid" at every horizon.
        _ensure_column(conn, "stock_signals", "avg_close_r1m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_r2m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_r3m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_r6m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_r12m",       "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_p1m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_p2m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_p3m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_p6m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_close_p12m",       "REAL")

        # 4e. D33a — stock-level Relative Strength vs the broad market
        # (rs_vs_broad = adjusted_close(stock) / close(Nifty 500)). Mirrors the
        # D32 ratio-signal vocabulary (slopes/MA flags/52w-high/trend_state) but
        # denormalized onto the per-stock signal row. rs_rank is the cross-stock
        # percentile (1-99) of blended RS momentum across the liquid universe.
        _ensure_column(conn, "stock_signals", "rs_vs_broad_today",        "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_slope_1m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_slope_3m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_slope_6m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_slope_12m",    "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_above_50ma",   "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_above_200ma",  "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_new_52w_high", "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_broad_trend_state",  "TEXT")
        _ensure_column(conn, "stock_signals", "rs_rank",                  "INTEGER")

        # 4f. D33b — stock-level Relative Strength vs the stock's PRIMARY SECTOR
        # (rs_vs_sector = adjusted_close(stock) / close(primary_sector_index)).
        # primary_sector = the NARROWEST (smallest-membership) NSE sectoral index
        # the stock belongs to, with size/broad indices excluded, assigned from
        # stock_index_membership. Same D32 ratio-signal vocabulary as rs_vs_broad,
        # denormalized per row so the dashboard + the D33c "strong-in-strong"
        # leader join read it directly. NULL for stocks in no NSE sectoral index.
        _ensure_column(conn, "stock_signals", "primary_sector",            "TEXT")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_today",        "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_slope_1m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_slope_3m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_slope_6m",     "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_slope_12m",    "REAL")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_above_50ma",   "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_above_200ma",  "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_new_52w_high", "INTEGER")
        _ensure_column(conn, "stock_signals", "rs_vs_sector_trend_state",  "TEXT")

        # 4g. D43 — accumulation/distribution CHARACTER of the DVPT activity.
        # Delivery data is side-blind, so we store three INDEPENDENT axes of raw
        # measures and DERIVE the `accum_character` label (re-tunable via
        # signals.run_relabel_character without a full backfill):
        #   WHO       — deliv_value_ratio_1m_6m (delivery ₹ picking up?),
        #               trade_count_ratio_1m_6m (broadening retail vs concentrated),
        #               avg_deliv_pct_1m / _6m (conviction holding?)
        #   WHICH WAY — deliv_updown_ratio_3m (value-weighted up/down skew, on
        #               ADJUSTED closes), accum_price_drift_3m (the direction read)
        #   CONTEXT   — pct_from_52w_high (near highs vs in a base)
        _ensure_column(conn, "stock_signals", "deliv_value_ratio_1m_6m", "REAL")
        _ensure_column(conn, "stock_signals", "trade_count_ratio_1m_6m", "REAL")
        _ensure_column(conn, "stock_signals", "avg_deliv_pct_1m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_deliv_pct_6m",        "REAL")
        _ensure_column(conn, "stock_signals", "deliv_updown_ratio_3m",   "REAL")
        _ensure_column(conn, "stock_signals", "accum_price_drift_3m",    "REAL")
        _ensure_column(conn, "stock_signals", "pct_from_52w_high",       "REAL")
        _ensure_column(conn, "stock_signals", "accum_character",         "TEXT")

        # 4h. D44 — value-weighted institutional KEY PRICE + multi-horizon entry
        # gap + ticket-size + activity-surge. ALL ADDITIVE: these refine the D31
        # flat `avg_close_p*` zones (which equal-weight close on the top-N power
        # days) WITHOUT modifying them — the big institutional day dominates the
        # value-weighted cost line, computed on the day's avg_price.
        #   key_price_p*    = Σ(price·deliv_value) / Σ(deliv_value) over the SAME
        #                     top-N power-DVPT days; gap_to_key_p* = signed % of
        #                     today's close vs that key (− below cost, + above).
        #   near_key is DERIVED on read (band _KEY_BAND) — no column.
        #   avg_trade_qty / avg_deliv_qty_per_trade = today's ticket size.
        #   turnover_surge_{1m,3m,1y} = today value ÷ its own rolling avg.
        _ensure_column(conn, "stock_signals", "key_price_p1m",          "REAL")
        _ensure_column(conn, "stock_signals", "key_price_p2m",          "REAL")
        _ensure_column(conn, "stock_signals", "key_price_p3m",          "REAL")
        _ensure_column(conn, "stock_signals", "key_price_p6m",          "REAL")
        _ensure_column(conn, "stock_signals", "key_price_p12m",         "REAL")
        _ensure_column(conn, "stock_signals", "gap_to_key_p1m",         "REAL")
        _ensure_column(conn, "stock_signals", "gap_to_key_p2m",         "REAL")
        _ensure_column(conn, "stock_signals", "gap_to_key_p3m",         "REAL")
        _ensure_column(conn, "stock_signals", "gap_to_key_p6m",         "REAL")
        _ensure_column(conn, "stock_signals", "gap_to_key_p12m",        "REAL")
        _ensure_column(conn, "stock_signals", "avg_trade_qty",          "REAL")
        _ensure_column(conn, "stock_signals", "avg_deliv_qty_per_trade","REAL")
        _ensure_column(conn, "stock_signals", "turnover_surge_1m",      "REAL")
        _ensure_column(conn, "stock_signals", "turnover_surge_3m",      "REAL")
        _ensure_column(conn, "stock_signals", "turnover_surge_1y",      "REAL")

        # 4c. Indexes on the new columns (post-ALTER, guaranteed to exist).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_p_score "
            "ON stock_signals(trade_date, p_score DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_trigger_rank "
            "ON stock_signals(trade_date, trigger_rank)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_ath "
            "ON stock_signals(trade_date, is_ath_dvpt)"
        )
        # D33a — RS rank lookup per date (the cross-stock percentile screen).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_rs_rank "
            "ON stock_signals(trade_date, rs_rank)"
        )
        # D33b — primary-sector lookup per date (the D33c leaders/laggards join
        # of each stock onto its sector's index_signals trend_state).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_primary_sector "
            "ON stock_signals(trade_date, primary_sector)"
        )
        # D43 — accumulation/distribution character screen per date (the Home
        # "stealth accumulation" board + /dash/stocks character filter pills).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_accum_character "
            "ON stock_signals(trade_date, accum_character)"
        )

        # 5. Helper view for clean equity-cash-market queries. Includes delivery.
        # Drop and recreate to pick up any new columns.
        conn.execute("DROP VIEW IF EXISTS prices_eq")
        conn.execute("""
            CREATE VIEW prices_eq AS
            SELECT symbol, trade_date, open, high, low, close, prev_close,
                   avg_price, volume, value, num_trades, deliv_qty, deliv_per,
                   isin
            FROM bhavcopy_rows
            WHERE series='EQ' AND (segment='CM' OR segment IS NULL)
        """)
        conn.commit()
    finally:
        conn.close()


_init()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a row-factory-enabled connection with auto-commit on success."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _tune(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
