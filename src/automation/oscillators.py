"""Momentum oscillators (RSI / MACD) computed from the bhav-copy OHLC archive.

The catalog's highest-ROI 🔴 GAP item (Part 4.1 / Part 12 Tier-1): the most-asked
TA family, and it needs NO new ingestion — it is derived from the ~5,400-session
close history Pat already stores in ``prices_eq``.

Self-contained (the feedback.py pattern): this module OWNS its ``stock_oscillators``
table (``CREATE TABLE IF NOT EXISTS`` on first use) and never edits ``db.py``. It is
a PRE-COMPUTE job (honors the "pre-compute over recompute" doctrine): a nightly run
stores one latest row per symbol — RSI(14, Wilder), MACD(12,26,9) and the previous
day's histogram (so "MACD crossover today" is a flag, not a recomputation) — and the
read path is a deterministic ₹0 SELECT over that table.

  - ``compute_and_store()``  — the nightly job (idempotent upsert).
  - ``build_oscillators_query(screen)`` — the flow builder (pure; constant clause).

Run the job:  python -m src.automation.oscillators
"""

from __future__ import annotations

from src.core.db import get_conn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_oscillators (
    symbol         TEXT PRIMARY KEY,
    trade_date     TEXT,
    rsi_14         REAL,
    macd           REAL,
    macd_signal    REAL,
    macd_hist      REAL,
    macd_hist_prev REAL,
    computed_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_osc_rsi  ON stock_oscillators(rsi_14);
CREATE INDEX IF NOT EXISTS idx_osc_hist ON stock_oscillators(macd_hist);
"""

# How many trailing sessions to pull per symbol. MACD(26)+signal(9) needs ~35 to
# stabilize; 90 gives the EMAs plenty of seasoning for accurate latest values.
_LOOKBACK = 90
# Minimum closes required to emit a row (skip freshly-listed names).
_MIN_CLOSES = 35


# ── the math (pure functions over a close series, oldest → newest) ────────────
def _rsi(closes, period: int = 14):
    """Wilder's RSI (the standard). Returns the latest value in [0,100], or None."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(d if d > 0 else 0.0)
        losses.append(-d if d < 0 else 0.0)
    avg_gain = sum(gains[:period]) / period          # seed = SMA of first `period`
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):              # Wilder smoothing
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _ema(values, period: int):
    """EMA seeded by the SMA of the first `period` values. Returns {index: ema}."""
    if len(values) < period:
        return {}
    k = 2.0 / (period + 1)
    out = {}
    ema = sum(values[:period]) / period
    out[period - 1] = ema
    for i in range(period, len(values)):
        ema = (values[i] - ema) * k + ema
        out[i] = ema
    return out


def _macd(closes, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD(12,26,9). Returns (macd, signal, hist, hist_prev) latest, or None."""
    if len(closes) < slow + signal:
        return None
    ef, es = _ema(closes, fast), _ema(closes, slow)
    idx = sorted(i for i in es if i in ef)           # macd defined where both EMAs are
    macd_series = [ef[i] - es[i] for i in idx]
    if len(macd_series) < signal + 1:
        return None
    sig = _ema(macd_series, signal)
    last = len(macd_series) - 1
    if last not in sig or (last - 1) not in sig:
        return None
    h_last = macd_series[last] - sig[last]
    h_prev = macd_series[last - 1] - sig[last - 1]
    return macd_series[last], sig[last], h_last, h_prev


# ── the nightly compute job ───────────────────────────────────────────────────
def _recent_closes(conn, lookback: int = _LOOKBACK):
    """{symbol: [close, …]} (oldest→newest) over the last `lookback` sessions,
    equity-only, positive closes."""
    floor = conn.execute(
        "SELECT MIN(d) FROM (SELECT DISTINCT trade_date d FROM bhavcopy_rows "
        "ORDER BY d DESC LIMIT ?)", (lookback,)
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT symbol, trade_date, close FROM prices_eq "
        "WHERE symbol IN (SELECT symbol FROM nse_equity_list) "
        "AND trade_date >= ? AND close > 0 "
        "ORDER BY symbol, trade_date", (floor,)
    ).fetchall()
    series: dict = {}
    for r in rows:
        series.setdefault(r["symbol"], []).append(r["close"])
    return series


def compute_and_store(conn=None) -> int:
    """Compute RSI/MACD for every eligible symbol and upsert one latest row each.
    Returns the number of symbols stored. Manages its own connection if none given."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        latest = conn.execute("SELECT MAX(trade_date) AS d FROM bhavcopy_rows").fetchone()["d"]
        series = _recent_closes(conn)
        n = 0
        for sym, closes in series.items():
            if len(closes) < _MIN_CLOSES:
                continue
            rsi = _rsi(closes)
            macd = _macd(closes)
            if rsi is None and macd is None:
                continue
            m, sg, h, hp = (macd if macd else (None, None, None, None))
            conn.execute(
                "INSERT INTO stock_oscillators "
                "(symbol, trade_date, rsi_14, macd, macd_signal, macd_hist, macd_hist_prev, computed_at) "
                "VALUES (?,?,?,?,?,?,?, datetime('now')) "
                "ON CONFLICT(symbol) DO UPDATE SET trade_date=excluded.trade_date, "
                "rsi_14=excluded.rsi_14, macd=excluded.macd, macd_signal=excluded.macd_signal, "
                "macd_hist=excluded.macd_hist, macd_hist_prev=excluded.macd_hist_prev, "
                "computed_at=excluded.computed_at",
                (sym, latest, rsi, m, sg, h, hp),
            )
            n += 1
        if own:
            conn.commit()
        return n
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── the read path — a deterministic ₹0 screen over stock_oscillators ──────────
# screen key -> (label, WHERE clause, ORDER BY). The clause/sort come ONLY from
# this constant (never user input); no value is formatted in from the query.
OSC_SCREEN: dict[str, tuple[str, str, str]] = {
    "rsi_oversold":   ("RSI < 30 (oversold)",    "o.rsi_14 IS NOT NULL AND o.rsi_14 < 30", "o.rsi_14 ASC"),
    "rsi_overbought": ("RSI > 70 (overbought)",   "o.rsi_14 IS NOT NULL AND o.rsi_14 > 70", "o.rsi_14 DESC"),
    "macd_bull":      ("MACD bullish crossover",  "o.macd_hist > 0 AND o.macd_hist_prev <= 0", "o.macd_hist DESC"),
    "macd_bear":      ("MACD bearish crossover",  "o.macd_hist < 0 AND o.macd_hist_prev >= 0", "o.macd_hist ASC"),
    "macd_positive":  ("MACD above signal line",  "o.macd_hist > 0", "o.macd_hist DESC"),
}
OSC_LIMIT = 60


def build_oscillators_query(screen: str = "") -> tuple[str, list]:
    """Compile the oscillator screen to a read-only SELECT over stock_oscillators,
    enriched with CMP + RS-rank + sector for context. The WHERE/ORDER come only from
    the OSC_SCREEN constant; no user value reaches the SQL."""
    _lbl, where, order = OSC_SCREEN.get(screen, OSC_SCREEN["rsi_oversold"])
    sql = (
        "SELECT o.symbol, pe.close AS cmp, o.rsi_14, o.macd, o.macd_signal, o.macd_hist, "
        "s.rs_rank, s.primary_sector "
        "FROM stock_oscillators o "
        "LEFT JOIN prices_eq pe ON pe.symbol = o.symbol AND pe.trade_date = o.trade_date "
        "LEFT JOIN stock_signals s ON s.symbol = o.symbol "
        "  AND s.trade_date = (SELECT MAX(trade_date) FROM stock_signals) "
        "WHERE " + where + " "
        "ORDER BY " + order + ", o.symbol "
        "LIMIT " + str(OSC_LIMIT)
    )
    return sql, []


if __name__ == "__main__":
    stored = compute_and_store()
    print(f"stock_oscillators: stored {stored} symbols")
