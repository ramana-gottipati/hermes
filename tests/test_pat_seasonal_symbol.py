"""test_pat_seasonal_symbol.py — contracts for the per-symbol seasonal base-rate flow (S150).

Guards the symbol-anchored recognizer (does NOT steal the market-wide seasonal ranking or
movers), the seasonal_cells read, and engine.route wiring. Pat eval battery left UNCHANGED.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.pat import seasonal_flow as SF        # noqa: E402
from src.pat import engine as ENGINE           # noqa: E402


def test_recognizes_per_symbol_base_rate_asks():
    assert SF.parse_seasonal_symbol("is TCS usually up in July")["params"] == {"symbol": "TCS", "month": 7}
    assert SF.parse_seasonal_symbol("does INFY tend to rise in March")["params"]["month"] == 3
    assert SF.parse_seasonal_symbol("TCS seasonality this month")["params"]["month"] == 0
    assert SF.parse_seasonal_symbol("is WIPRO usually down next month")["params"]["month"] == -1


def test_yields_to_market_wide_and_intraday():
    assert SF.parse_seasonal_symbol("top stocks this month") is None      # no symbol → ranking
    assert SF.parse_seasonal_symbol("is TCS up today") is None            # no month/seasonal cue
    assert SF.parse_seasonal_symbol("TCS news") is None
    assert SF.parse_seasonal_symbol("") is None


def test_engine_route_splits_symbol_vs_market_seasonal():
    assert ENGINE.route("is TCS usually up in July")["flow"] == "seasonal_stock"
    # market-wide ranking still wins its own ask
    assert ENGINE.route("top stocks this month")["flow"] == "seasonal"
    assert ENGINE.route("historically bearish stocks next week")["flow"] == "seasonal"


def test_stock_month_read():
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE seasonal_cells(scope TEXT, entity TEXT, axis TEXT, cell INT, "
              "script_z REAL, n_years INT, hit_rate REAL)")
    c.execute("INSERT INTO seasonal_cells VALUES('stock','TCS','month',7,0.30,18,0.72)")
    cell = SF.stock_month(c, "TCS", 7)
    assert cell and cell["hit_rate"] == 0.72 and cell["n_years"] == 18
    assert cell["month_label"] == "Jul" and cell["k"] == 13
    assert SF.stock_month(c, "TCS", 0, today=date(2026, 7, 1))["month"] == 7   # "this month"
    assert SF.stock_month(c, "NOSUCH", 7) is None and SF.stock_month(None, "TCS", 7) is None
    c.close()
