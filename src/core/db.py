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
"""


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """Idempotently add a column to an existing table (SQLite has no IF NOT EXISTS for columns)."""
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _init() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Base schema — tables + non-telegram indexes (safe on fresh and existing DBs).
        conn.executescript(SCHEMA_BASE)
        # 2. Migrate existing DBs that pre-date the telegram_user_id column.
        _ensure_column(conn, "conversations", "telegram_user_id", "INTEGER")
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
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
