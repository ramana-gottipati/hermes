"""D2-F1 regression: the rs_rank percentile universe must be survivorship-correct.

The leak: the liquid-universe gate was `s.symbol IN nse_equity_list` (a CURRENT
snapshot), so on a HISTORICAL date every since-delisted name was dropped and past
percentiles were computed over survivors only. The fix keys on the point-in-time
`security_master` spine (delisted names kept; funds excluded), with nse_equity_list
as an OR-fallback for live names not yet in the master. This pins:
  - a name delisted AFTER the ranked date is still IN that date's rank universe,
  - an ETF/fund is excluded even though it traded,
  - a live name missing from the master still ranks (OR-fallback → no regression).
"""
import sqlite3

import pytest

from src.automation import stock_rs

D = "2016-06-01"


def _db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE stock_signals (
            symbol TEXT, trade_date TEXT,
            rs_vs_broad_slope_3m REAL, rs_vs_broad_slope_6m REAL, rs_rank INTEGER
        );
        CREATE TABLE bhavcopy_rows (
            symbol TEXT, trade_date TEXT, series TEXT, segment TEXT, value REAL, close REAL
        );
        CREATE TABLE security_master (
            symbol TEXT, first_date TEXT, last_date TEXT, instrument_class TEXT
        );
        CREATE TABLE nse_equity_list (symbol TEXT);
        """
    )
    return c


def _add(c, symbol, slope3m, *, in_eqlist, sm=None, value=5e7, close=100.0):
    c.execute("INSERT INTO stock_signals VALUES (?,?,?,?,NULL)", (symbol, D, slope3m, None))
    c.execute("INSERT INTO bhavcopy_rows VALUES (?,?,?,?,?,?)", (symbol, D, "EQ", "CM", value, close))
    if sm is not None:
        first, last, klass = sm
        c.execute("INSERT INTO security_master VALUES (?,?,?,?)", (symbol, first, last, klass))
    if in_eqlist:
        c.execute("INSERT INTO nse_equity_list VALUES (?)", (symbol,))


def _run_rank(c):
    c.execute(stock_rs._rank_sql_for("AND b.trade_date = ?"), (D,))
    return {r["symbol"]: r["rs_rank"]
            for r in c.execute("SELECT symbol, rs_rank FROM stock_signals")}


def test_delisted_name_is_in_the_historical_universe_and_fund_excluded():
    c = _db()
    # survivor: in the current equity list + master, still listed today
    _add(c, "ALIVE", 5.0, in_eqlist=True, sm=("2010-01-01", "2026-07-07", "EQUITY"))
    # delisted 2018: NOT in today's equity list, but master keeps it (first<=D<=last)
    _add(c, "DELISTO", 10.0, in_eqlist=False, sm=("2010-01-01", "2018-12-31", "EQUITY"))
    # an ETF trading on D: in the master but instrument_class FUND -> must be excluded
    _add(c, "ETFXX", 8.0, in_eqlist=False, sm=("2010-01-01", "2026-07-07", "FUND"))
    # illiquid (value < ₹1cr): excluded by the liquidity gate regardless
    _add(c, "THINX", 7.0, in_eqlist=True, sm=("2010-01-01", "2026-07-07", "EQUITY"), value=5e6)

    ranks = _run_rank(c)
    # THE fix: the delisted name is present in its own historical rank universe.
    assert ranks["DELISTO"] is not None
    assert ranks["ALIVE"] is not None
    # fund + illiquid excluded
    assert ranks["ETFXX"] is None
    assert ranks["THINX"] is None
    # universe = {ALIVE mom=5, DELISTO mom=10}; PERCENT_RANK asc -> 1 and 99.
    assert ranks["ALIVE"] == 1
    assert ranks["DELISTO"] == 99


def test_or_fallback_ranks_live_name_absent_from_master():
    c = _db()
    _add(c, "ALIVE", 5.0, in_eqlist=True, sm=("2010-01-01", "2026-07-07", "EQUITY"))
    # a live name in the equity list but with NO security_master row -> OR-fallback keeps it.
    _add(c, "NOMSTR", 9.0, in_eqlist=True, sm=None)
    ranks = _run_rank(c)
    assert ranks["NOMSTR"] is not None
    assert ranks["ALIVE"] is not None
    assert ranks["NOMSTR"] == 99 and ranks["ALIVE"] == 1
