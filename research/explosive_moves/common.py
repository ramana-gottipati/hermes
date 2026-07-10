"""Shared infrastructure for the explosive-move research program.

- Opens the production hermes.db READ-ONLY (never mutate it).
- Writes all intermediate tables to a separate research.db.
- Reuses the production corporate-action adjuster (src/automation/adjust.py)
  by loading it standalone (it is pure stdlib, no package imports).

All "windows" are counted in TRADING DAYS (rows per symbol), not calendar days,
which is the correct notion for returns and naturally handles holidays. Calendar
gaps are checked separately to reject suspension artifacts.
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np

# ---- Paths (VPS defaults; override via env for local dev) -------------------
MAIN_DB = os.environ.get("HERMES_MAIN_DB", "/opt/hermes/data/hermes.db")
RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")
ADJUST_PATH = os.environ.get("HERMES_ADJUST_PATH", "/opt/hermes/src/automation/adjust.py")
OUT_DIR = Path(os.environ.get("HERMES_RESEARCH_OUT", str(Path(__file__).resolve().parent / "out")))

# ---- Study parameters (the locked decisions; parameterized for sensitivity) -
LIQ_FLOOR = float(os.environ.get("EM_LIQ_FLOOR", 1e7))      # ₹1 cr median turnover
LIQ_WINDOW = 22                                              # trailing trading days for median turnover
DAILY_MOVE = 0.10                                            # +10% in a day
WEEKLY_MOVE = 0.10                                           # +10% over 5 trading days
WEEKLY_WIN = 5
MONTHLY_WIN = 22                                             # ~1 month of trading days (~30 calendar days)
MONTHLY_MOVE = float(os.environ.get("EM_MONTHLY_MOVE", 0.10))  # +10% HELD over the rolling month
#   Ramana's definition (session 25 correction): a genuine +10% move that is SUSTAINED — i.e. today's
#   close is >= +10% above the close ~1 month ago. NO 20%-thrust / retain-half requirement. A clean
#   +10% that keeps all 10% counts; a pop-and-fade fails (it is no longer +10% at month-end).
MONTHLY_THRUST = float(os.environ.get("EM_THRUST", 0.20))   # (legacy/sensitivity only — "big move" tier)
MONTHLY_HOLD = float(os.environ.get("EM_HOLD", 0.50))       # (legacy/sensitivity only)
SUSTAIN_WIN = 22
# Forward-outcome horizons (trading days) — power the success ratio.
FWD_HORIZONS = [5, 10, 22, 66, 132, 252]
STUDY_START = "2012-01-01"   # precursors (stock_signals) reliable from ~2012
WARMUP_ROWS = 260            # require ~1y of prior history before an event

# Max calendar-day gap allowed for a move window (reject suspension artifacts).
MAX_GAP_DAILY = 6
MAX_GAP_WEEKLY = 14
MAX_GAP_MONTHLY = 45

_adjust_mod = None


def load_adjust():
    """Load the production adjuster module standalone (pure, no package chain)."""
    global _adjust_mod
    if _adjust_mod is None:
        spec = importlib.util.spec_from_file_location("hermes_adjust", ADJUST_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        _adjust_mod = mod
    return _adjust_mod


def main_conn() -> sqlite3.Connection:
    """Read-only connection to the production DB."""
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA mmap_size=1073741824")
    con.execute("PRAGMA cache_size=-200000")
    con.execute("PRAGMA temp_store=MEMORY")
    return con


def research_conn() -> sqlite3.Connection:
    """Read-write connection to the research DB (intermediate results)."""
    con = sqlite3.connect(RESEARCH_DB, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA mmap_size=1073741824")
    con.execute("PRAGMA cache_size=-200000")
    con.execute("PRAGMA temp_store=MEMORY")
    return con


# Columns we pull per symbol from bhavcopy_rows (EQ cash segment).
_SERIES_FILTER = "series='EQ' AND (segment='CM' OR segment IS NULL)"
_SYM_COLS = ("trade_date", "open", "high", "low", "close", "prev_close",
             "volume", "value", "deliv_qty", "deliv_per", "num_trades", "avg_price")


def eq_symbols(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        f"SELECT DISTINCT symbol FROM bhavcopy_rows WHERE {_SERIES_FILTER} ORDER BY symbol"
    ).fetchall()
    return [r[0] for r in rows]


class SymbolSeries:
    """A single symbol's daily EQ history as parallel numpy arrays (oldest→newest).

    Provides corporate-action-adjusted price arrays (back-adjusted, latest=raw)
    plus a per-row ``is_ca`` flag (True where the adjuster detected a split/bonus),
    and the raw daily return ``ret_raw`` = close/prev_close - 1 (NSE-adjusted
    prev_close → split-clean but genuine big moves preserved).
    """

    def __init__(self, symbol: str, rows: list[sqlite3.Row], events: dict = None):
        """``events`` = the corporate-action ratio tape (D95 tape-primary adjustment);
        None → legacy inference-only factors."""
        self.symbol = symbol
        self.n = len(rows)
        self.date = [r["trade_date"] for r in rows]
        self.open = np.array([_f(r["open"]) for r in rows], dtype=float)
        self.high = np.array([_f(r["high"]) for r in rows], dtype=float)
        self.low = np.array([_f(r["low"]) for r in rows], dtype=float)
        self.close = np.array([_f(r["close"]) for r in rows], dtype=float)
        self.prev_close = np.array([_f(r["prev_close"]) for r in rows], dtype=float)
        self.volume = np.array([_f(r["volume"]) for r in rows], dtype=float)
        self.value = np.array([_f(r["value"]) for r in rows], dtype=float)
        self.deliv_qty = np.array([_f(r["deliv_qty"]) for r in rows], dtype=float)
        self.deliv_per = np.array([_f(r["deliv_per"]) for r in rows], dtype=float)
        self.num_trades = np.array([_f(r["num_trades"]) for r in rows], dtype=float)
        self.avg_price = np.array([_f(r["avg_price"]) for r in rows], dtype=float)  # NSE VWAP (2020+)

        adj = load_adjust()
        dict_rows = [{"trade_date": r["trade_date"], "close": r["close"],
                      "prev_close": r["prev_close"]} for r in rows]
        self.factors = np.array(adj.adjustment_factors(dict_rows, events), dtype=float)
        self.adj_close = self.close * self.factors
        self.adj_high = self.high * self.factors
        self.adj_low = self.low * self.factors
        # is_ca[i]: the adjuster applied an action factor at row i (ratio != 1).
        self.is_ca = np.zeros(self.n, dtype=bool)
        for i in range(1, self.n):
            if self.factors[i] != 0 and abs(self.factors[i - 1] / self.factors[i] - 1) > 1e-9:
                self.is_ca[i] = True
        # Raw daily return (split-clean via NSE-adjusted prev_close).
        with np.errstate(divide="ignore", invalid="ignore"):
            self.ret_raw = np.where(self.prev_close > 0, self.close / self.prev_close - 1.0, np.nan)
        # All-time-high-so-far flag (cheap O(n); used for new-high counts).
        _safe = np.where(np.isnan(self.adj_close), -np.inf, self.adj_close)
        self.cummax_adj = np.maximum.accumulate(_safe)
        self.is_ath = self.adj_close >= self.cummax_adj
        # Trailing median turnover (₹) over LIQ_WINDOW prior days (excludes today).
        self.med_turn = _trailing_median(self.value, LIQ_WINDOW)

    def gap_days(self, i: int, j: int) -> int:
        """Calendar days between rows i and j (j>i)."""
        from datetime import date
        a = date.fromisoformat(self.date[i]); b = date.fromisoformat(self.date[j])
        return (b - a).days


def _f(x) -> float:
    return float(x) if x is not None else np.nan


def load_series(con: sqlite3.Connection, symbol: str) -> Optional[SymbolSeries]:
    rows = con.execute(
        f"""SELECT {','.join(_SYM_COLS)} FROM bhavcopy_rows
            WHERE symbol=? AND {_SERIES_FILTER}
            ORDER BY trade_date ASC""", (symbol,)).fetchall()
    if len(rows) < 30:
        return None
    try:                                                  # D95 tape-primary adjustment
        from src.automation.corp_actions import price_ratios
        events = price_ratios(con, symbol)
    except Exception:  # noqa: BLE001
        events = None
    return SymbolSeries(symbol, rows, events)


def _trailing_median(x: np.ndarray, win: int) -> np.ndarray:
    """Median of the prior `win` values (excluding current index). NaN if short.

    Vectorized via sliding windows: out[i] = median(x[i-win:i]) for i>=win.
    """
    n = len(x)
    out = np.full(n, np.nan)
    if n <= win:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    win_view = sliding_window_view(x, win)          # shape (n-win+1, win); row k = x[k:k+win]
    used = win_view[0:n - win]                        # rows k=0..n-win-1 -> windows ending before i=win..n-1
    valid = np.sum(~np.isnan(used), axis=1)
    with np.errstate(invalid="ignore"):
        med = np.nanmedian(np.where(np.isnan(used), np.nan, used), axis=1)
    med[valid < max(5, win // 2)] = np.nan
    out[win:n] = med
    return out


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta effect size in [-1,1] via a sort-based O(n log n) estimate.

    delta = P(a>b) - P(a<b). Positive => `a` tends to exceed `b`.
    """
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    b_sorted = np.sort(b)
    # for each a, count b < a and b <= a
    less = np.searchsorted(b_sorted, a, side="left")
    leq = np.searchsorted(b_sorted, a, side="right")
    greater = len(b) - leq            # count b > a
    gt_sum = int(np.sum(less))         # total (a > b) pairs
    lt_sum = int(np.sum(greater))      # total (a < b) pairs
    return (gt_sum - lt_sum) / (len(a) * len(b))
