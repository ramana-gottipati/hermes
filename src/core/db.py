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
