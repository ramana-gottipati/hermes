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
-- completeness. Replaces the earlier slim daily_prices table. Both legacy
-- (pre-July-2024) and UDIFF (current) NSE formats map into the same row shape.
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
    settlement_price REAL,
    volume          INTEGER,
    value           REAL,
    num_trades      INTEGER,
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
    ingested_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

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
        # 5. Helper view for clean equity-cash-market queries.
        conn.execute("""
            CREATE VIEW IF NOT EXISTS prices_eq AS
            SELECT symbol, trade_date, open, high, low, close, prev_close,
                   volume, value, num_trades, isin
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
