"""test_home_read_contract.py — the DATA-coupling contract gate (bidirectional-isolation follow-up).

The Graphite Home is insulated from the rest of the codebase in every layer EXCEPT one, and that
one is deliberate: its read-only data layer (`src/web/home/reads.py` + four shared, non-preview
helpers). This gate turns that soft coupling into a HARD contract — if another lane renames a column
or changes a shared helper's signature / return shape that the home reads, THIS test goes red (a
loud, early warning) instead of the home silently losing a zone's data. Asserted against the
CANONICAL schema definitions + real signatures, never a private copy.

It can only ever catch OLD -> NEW breakage: the home writes nothing, so it can never move the old
data (NEW -> OLD is structurally impossible, proven by test_home_isolation).
"""
from __future__ import annotations

import inspect
import sqlite3


def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _mem(*scripts) -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    for s in scripts:
        c.executescript(s)
    return c


# ── table columns the home reads (against the canonical schema strings) ──────────
def test_index_signals_columns():
    from src.core.db import SCHEMA_BASE
    have = _cols(_mem(SCHEMA_BASE), "index_signals")
    for col in ("index_name", "trade_date", "close_value", "ret_1d_pct", "pct_above_200d_avg"):
        assert col in have, ("index_signals dropped a column the home reads", col)


def test_sent_news_columns():
    from src.core.db import SCHEMA_BASE
    have = _cols(_mem(SCHEMA_BASE), "sent_news")
    for col in ("source", "url", "title", "sent_at"):
        assert col in have, ("sent_news dropped a column the home reads", col)


def test_stock_signals_power_dvpt_column():
    from src.core.db import SCHEMA_BASE
    have = _cols(_mem(SCHEMA_BASE), "stock_signals")
    for col in ("symbol", "trade_date", "power_dvpt_3m"):
        assert col in have, ("stock_signals dropped a column the home reads", col)


def test_corporate_actions_columns():
    from src.core.db import SCHEMA_BASE
    have = _cols(_mem(SCHEMA_BASE), "corporate_actions")
    for col in ("symbol", "action_type", "ex_date", "ratio_from", "ratio_to", "details"):
        assert col in have, ("corporate_actions dropped a column the home reads", col)


def test_market_internals_daily_columns():
    from src.automation.market_internals import _SCHEMA
    have = _cols(_mem(_SCHEMA), "market_internals_daily")
    for col in ("d", "adv", "dec", "pct_adv"):
        assert col in have, ("market_internals_daily dropped a column the home reads", col)


def test_fii_dii_flows_columns_and_category_contract():
    from src.automation import deals
    have = _cols(_mem(deals._DDL), "fii_dii_flows")
    for col in ("trade_date", "category", "net_value"):
        assert col in have, ("fii_dii_flows dropped a column the home reads", col)
    # the CATEGORY-STRING contract the home filters on ('FII/FPI' | 'DII'): if the ingest relabels
    # FII, the home's WHERE clause silently misses it. Pin the literal in the ingest source.
    assert "FII/FPI" in inspect.getsource(deals), \
        "the 'FII/FPI' category label changed — the home's FII filter would miss it"


def test_board_meetings_columns():
    from src.automation.results_calendar import SCHEMA
    have = _cols(_mem(SCHEMA), "board_meetings")
    for col in ("symbol", "company", "meeting_date", "purpose", "is_results"):
        assert col in have, ("board_meetings dropped a column the home reads", col)


def test_signal_alert_state_columns():
    from src.automation import signal_alerts
    c = sqlite3.connect(":memory:")
    signal_alerts.ensure_schema(c)
    have = _cols(c, "signal_alert_state")
    for col in ("symbol", "lens", "from_state", "to_state", "severity", "valence", "as_of"):
        assert col in have, ("signal_alert_state dropped a column the home reads", col)


# ── the scroll-stack additions: pulse deck · featured card · ticker feeds ─────────
def test_market_internals_pulse_deck_columns():
    from src.automation.market_internals import _SCHEMA
    have = _cols(_mem(_SCHEMA), "market_internals_daily")
    for col in ("avg_dp", "mep_net", "disp"):
        assert col in have, ("market_internals_daily dropped a pulse-deck column the home reads", col)


def test_stock_signals_pulse_and_featured_columns():
    """The RS / 52w-high / sector columns are migration-added (`_ensure_column`), not in SCHEMA_BASE.
    Pin them at the db.py schema source so a rename by the signals lane trips this gate early (same
    source-inspection discipline this file uses for the 'FII/FPI' category literal). The reads are
    also defensive — a missing column degrades a tile to its demo fallback rather than crashing."""
    import src.core.db as db
    src = inspect.getsource(db)
    for col in ("rs_vs_broad_new_52w_high", "pct_from_52w_high", "primary_sector", "rs_rank",
                "rs_vs_broad_trend_state", "rs_vs_broad_today"):
        assert ('"stock_signals", "' + col + '"') in src or (col + " ") in src, \
            ("a stock_signals column the home reads is gone from db.py's schema/migrations", col)


def test_bhavcopy_rows_day_change_columns():
    from src.core.db import SCHEMA_BASE
    have = _cols(_mem(SCHEMA_BASE), "bhavcopy_rows")
    for col in ("symbol", "trade_date", "series", "close", "prev_close", "deliv_per"):
        assert col in have, ("bhavcopy_rows dropped a column the home's day-change/movers read uses", col)


def test_watchlist_and_holdings_columns():
    from src.core.db import SCHEMA_BASE
    m = _mem(SCHEMA_BASE)
    for col in ("symbol", "added_at"):
        assert col in _cols(m, "watchlist"), ("watchlist dropped a column the home reads", col)
    for col in ("symbol", "qty", "entry_price", "status", "book"):
        assert col in _cols(m, "stocks_in_play"), ("stocks_in_play dropped a column the home's portfolio read uses", col)


# ── shared, non-preview read helpers: signatures + return shapes ─────────────────
def test_corp_actions_upcoming_returns_rows_asof_tuple():
    from src.core.db import SCHEMA_BASE
    from src.automation.corp_actions import upcoming
    p = inspect.signature(upcoming).parameters
    assert "conn" in p and "days" in p, "corp_actions.upcoming(conn, days) signature changed"
    res = upcoming(_mem(SCHEMA_BASE), days=21)
    assert isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], list), \
        "corp_actions.upcoming must return (rows, as_of) — reads.upcoming_ca depends on unpacking it"


def test_results_calendar_upcoming_results_signature():
    from src.automation.results_calendar import upcoming_results
    assert "days" in inspect.signature(upcoming_results).parameters


def test_whatchanged_flow_changes_signature():
    from src.pat.whatchanged_flow import changes
    p = inspect.signature(changes).parameters
    assert "conn" in p and "within_days" in p and "limit" in p


def test_market_mood_signature_and_shape():
    from src.web.market_mood import market_mood
    p = inspect.signature(market_mood).parameters
    assert "breadth" in p and "nifty_above_200dma" in p, "market_mood signature changed"
    assert market_mood(70, True).get("word"), "market_mood must return a dict carrying a 'word'"
    assert market_mood(None, None).get("word") == "No data"


# ── the reads execute end-to-end against the REAL schemas (empty shape, no crash) ─
def test_home_reads_execute_against_the_real_schemas():
    from src.core.db import SCHEMA_BASE
    from src.automation.market_internals import _SCHEMA as MI_SCHEMA
    from src.automation import deals, signal_alerts
    from src.automation.results_calendar import SCHEMA as BM_SCHEMA
    from src.web.home import reads
    c = _mem(SCHEMA_BASE, MI_SCHEMA, deals._DDL, BM_SCHEMA)
    signal_alerts.ensure_schema(c)
    assert reads.index_pulse(c) == []
    assert reads.mood_inputs(c) == (None, None)
    assert reads.breadth_latest(c) is None
    assert reads.fii_dii_recent(c) == []
    assert reads.recent_news(c) == []
    assert reads.severity_counts(c)["total"] == 0
    assert reads.index_series(c) == []
    assert reads.delivery_leaders(c) == []
    assert reads.upcoming_ca(c, days=21) == []
    # the scroll-stack reads also degrade to empty (never raise) against the real schemas
    assert reads.internals_series(c) == []
    assert reads.new_highs(c) == {}
    assert reads.sector_heat(c) == []
    assert reads.watchlist_rows(c) == []
    assert reads.portfolio(c) == {}
    assert reads.movers(c) == {}
