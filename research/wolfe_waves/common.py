"""Read-only data access + indicators for the Wolfe-wave research sandbox.

Pure stdlib (no numpy). Reuses the production CA adjuster when present, else falls
back to raw prices. All windows are counted in TRADING DAYS (rows per symbol).
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[2]


def _first_existing(*paths) -> str:
    for p in paths:
        if p and Path(p).exists():
            return str(p)
    return str(paths[-1])


MAIN_DB = os.environ.get("HERMES_MAIN_DB") or _first_existing(
    _REPO / "data" / "hermes.db", "/opt/hermes/data/hermes.db")
ADJUST_PATH = os.environ.get("HERMES_ADJUST_PATH") or _first_existing(
    _REPO / "src" / "automation" / "adjust.py", "/opt/hermes/src/automation/adjust.py")

# EQ cash segment only (segment may be NULL in older rows).
_SERIES_FILTER = "series='EQ' AND (segment='CM' OR segment IS NULL)"


def main_conn() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def eq_symbols(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        f"SELECT DISTINCT symbol FROM bhavcopy_rows WHERE {_SERIES_FILTER} ORDER BY symbol")]


_adj = None


def _load_adjust():
    global _adj
    if _adj is None:
        try:
            spec = importlib.util.spec_from_file_location("wolfe_adjust", ADJUST_PATH)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            _adj = mod
        except Exception:
            _adj = False
    return _adj


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


@dataclass
class Series:
    symbol: str
    date: list
    high: list
    low: list
    close: list
    value: list  # ₹ turnover (liquidity)

    @property
    def n(self) -> int:
        return len(self.close)


def load_series(con: sqlite3.Connection, symbol: str) -> Optional[Series]:
    rows = con.execute(
        f"""SELECT trade_date, high, low, close, prev_close, value
            FROM bhavcopy_rows
            WHERE symbol=? AND {_SERIES_FILTER}
            ORDER BY trade_date ASC""", (symbol,)).fetchall()
    if len(rows) < 40:
        return None
    date = [r["trade_date"] for r in rows]
    high = [_f(r["high"]) for r in rows]
    low = [_f(r["low"]) for r in rows]
    close = [_f(r["close"]) for r in rows]
    value = [_f(r["value"]) for r in rows]
    adj = _load_adjust()
    if adj:
        try:
            f = adj.adjustment_factors(
                [{"close": r["close"], "prev_close": r["prev_close"]} for r in rows])
            high = [h * g if h == h else h for h, g in zip(high, f)]
            low = [l * g if l == l else l for l, g in zip(low, f)]
            close = [c * g if c == c else c for c, g in zip(close, f)]
        except Exception:
            pass  # fall back to raw
    return Series(symbol, date, high, low, close, value)


def atr(high: list, low: list, close: list, period: int = 14) -> list:
    """Wilder's ATR. Returns a list aligned to bars; None for the warm-up."""
    n = len(close)
    out = [None] * n
    if n <= period:
        return out
    trs = [0.0]
    for i in range(1, n):
        trs.append(max(high[i] - low[i],
                       abs(high[i] - close[i - 1]),
                       abs(low[i] - close[i - 1])))
    seed = sum(trs[1:period + 1]) / period
    out[period] = seed
    prev = seed
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out


def near_atr(atr_arr: list, i: int):
    """Nearest non-None ATR at/just-before i (handles warm-up rows)."""
    j = min(i, len(atr_arr) - 1)
    while j >= 0 and (atr_arr[j] is None or atr_arr[j] <= 0):
        j -= 1
    return atr_arr[j] if j >= 0 else None
