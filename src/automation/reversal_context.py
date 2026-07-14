"""Reversal context — DESCRIPTIVE band-state / stretch / floor columns (no signal).

The two survivors of the reversal-pair research arc (docs/strategy-ledger.md
§§ Study 2026-07-13 STREAM BAND · 2026-07-14 FRACTAL FLOOR · 2026-07-14b FENCES),
shipped ONLY as context columns. The falsification is part of the product copy:

  * STREAM BAND (EMA13 of highs / EMA13 of lows banks, EMA5 of HLC/3 trigger):
    the BUY-cross was an ANTI-signal (22d excess med -1.25%, both placebos better)
    — so the band STATE is surfaced with the reclaim cross labelled a CAUTION
    ("early reclaims have historically underperformed"), never an entry.
  * STRETCH percentile: signed % gap between the trigger and the violated bank,
    ranked against the stock's OWN trailing 756-bar history (per-stock, percent,
    never absolute — the no-static-threshold doctrine). Descriptive extension read.
  * FRACTAL FLOOR: the latest CONFIRMED degree-10 (fallback degree-5) down-fractal
    low = a well-defined support/invalidation level. The breakout trigger was inert
    and the trading book died at true cost (fences 07-14b) — what remains useful is
    the RISK GEOMETRY: how far above a confirmed floor the price sits, how old the
    floor is, and whether it is still unbroken.

Contract: owns the isolated table `reversal_context` (one latest row per symbol,
bounded snapshot — space rule; no db.py edit, same pattern as signal_alerts.py).
Pure stdlib (prod venv has no numpy). PIT-honest: a degree-N fractal is only used
once N bars have printed after it. Readers (Screen+ group "rev") are read-only.

CLI:
  python -m src.automation.reversal_context --compute [--limit N]
  python -m src.automation.reversal_context --selftest
"""
from __future__ import annotations

import bisect
import sys
from datetime import datetime, timezone

try:
    from src.core.db import get_conn
    from src.automation import adjust as _adjust
except Exception:  # pragma: no cover - import-path fallback
    from core.db import get_conn  # type: ignore
    from automation import adjust as _adjust  # type: ignore

EMA_FAST, EMA_SLOW = 5, 13
STRETCH_WIN, STRETCH_MIN = 756, 250
FLOOR_LOOKBACK = 400
DEGREES = (10, 5)
ROWS_NEEDED = 1100

SCHEMA = """
CREATE TABLE IF NOT EXISTS reversal_context (
    symbol         TEXT PRIMARY KEY,
    trade_date     TEXT,
    band_state     TEXT,     -- ABOVE / INSIDE / BELOW / RECLAIM / SLIP
    below_run      INTEGER,  -- consecutive bars trigger<=lower bank before today
    stretch_pct    REAL,     -- signed % gap trigger vs violated bank (0 inside)
    stretch_pctile REAL,     -- rank of today's stretch vs own trailing 756 bars
    floor_deg      INTEGER,  -- 10 or 5 (degree of the confirmed down-fractal)
    floor_price    REAL,     -- the fractal low, in current (adjusted=latest raw) terms
    floor_date     TEXT,
    floor_age      INTEGER,  -- bars since the fractal bar
    floor_gap_pct  REAL,     -- close vs floor, %
    floor_alive    INTEGER,  -- 1 = no close below the floor since it formed
    computed_at    TEXT,
    ceil_deg       INTEGER,  -- bearish mirror (S132c): degree of the confirmed up-fractal
    ceil_price     REAL,     -- the fractal high, current terms
    ceil_date      TEXT,
    ceil_age       INTEGER,
    ceil_gap_pct   REAL,     -- close vs ceiling, % (negative below it)
    ceil_alive     INTEGER   -- 1 = no close above the ceiling since it formed
);
CREATE INDEX IF NOT EXISTS idx_revctx_state ON reversal_context(band_state);
"""

# idempotent column migration for tables created before S132c (bear mirror).
_MIGRATE = ["ceil_deg INTEGER", "ceil_price REAL", "ceil_date TEXT",
            "ceil_age INTEGER", "ceil_gap_pct REAL", "ceil_alive INTEGER"]


def _migrate(conn) -> None:
    for col in _MIGRATE:
        try:
            conn.execute(f"ALTER TABLE reversal_context ADD COLUMN {col}")
        except Exception:  # noqa: BLE001 - duplicate column = already migrated
            pass


# ── pure helpers (unit-tested; no DB) ────────────────────────────────────────
def ema(vals, n):
    """First-valid-seed recursive EMA; None until n updates; None inputs carry state."""
    out = [None] * len(vals)
    a = 2.0 / (n + 1)
    e, k = None, 0
    for i, v in enumerate(vals):
        if v is not None:
            e = v if e is None else a * v + (1 - a) * e
            k += 1
        if k >= n:
            out[i] = e
    return out


def stretch_series(T, U, L):
    """Signed % gap trigger vs the violated bank; 0.0 inside; None while warming."""
    out = [None] * len(T)
    for i in range(len(T)):
        t, u, lo = T[i], U[i], L[i]
        if t is None or u is None or lo is None or u <= 0 or lo <= 0:
            continue
        if t > u:
            out[i] = (t - u) / u * 100.0
        elif t < lo:
            out[i] = (t - lo) / lo * 100.0
        else:
            out[i] = 0.0
    return out


def band_state(T, U, L):
    """(state, below_run) for the LAST bar. RECLAIM/SLIP = today's cross events."""
    m = len(T) - 1
    if m < 1 or T[m] is None or U[m] is None or L[m] is None:
        return None, 0
    run = 0
    j = m - 1
    while j >= 0 and T[j] is not None and L[j] is not None and T[j] <= L[j]:
        run += 1
        j -= 1
    prev_ok = T[m - 1] is not None and U[m - 1] is not None and L[m - 1] is not None
    if prev_ok and T[m - 1] <= L[m - 1] and T[m] > L[m]:
        return "RECLAIM", run
    if prev_ok and T[m - 1] >= U[m - 1] and T[m] < U[m]:
        return "SLIP", run
    if T[m] > U[m]:
        return "ABOVE", run
    if T[m] < L[m]:
        return "BELOW", run
    return "INSIDE", run


def stretch_pctile(series, m):
    """Percentile (0-100) of series[m] within series[m-756..m-1]; None if <250 vals."""
    s = series[m]
    if s is None:
        return None
    window = [v for v in series[max(0, m - STRETCH_WIN):m] if v is not None]
    if len(window) < STRETCH_MIN:
        return None
    window.sort()
    lo = bisect.bisect_left(window, s)
    hi = bisect.bisect_right(window, s)
    return round(100.0 * (lo + 0.5 * (hi - lo)) / len(window), 1)


def _latest_extreme(xs, closes, N, kind, lookback=FLOOR_LOOKBACK):
    """Latest CONFIRMED degree-N fractal within `lookback` bars of the end.

    kind='low'  -> floor  on lows  (strict min; alive = no close BELOW since)
    kind='high' -> ceiling on highs (strict max; alive = no close ABOVE since)
    Returns (f_idx, value, alive) or None. Confirmed = N bars printed after f (PIT)."""
    lower = kind == "low"
    m = len(xs) - 1
    for f in range(m - N, max(N - 1, m - lookback) - 1, -1):
        v = xs[f]
        if v is None:
            continue
        neigh = xs[f - N:f] + xs[f + 1:f + N + 1]
        if len(neigh) < 2 * N or any(x is None for x in neigh):
            continue
        if all((v < x) if lower else (v > x) for x in neigh):
            alive = 1
            for c in closes[f + 1:]:
                if c is not None and ((c < v) if lower else (c > v)):
                    alive = 0
                    break
            return f, v, alive
    return None


def latest_floor(lows, closes, N, lookback=FLOOR_LOOKBACK):
    return _latest_extreme(lows, closes, N, "low", lookback)


def latest_ceiling(highs, closes, N, lookback=FLOOR_LOOKBACK):
    return _latest_extreme(highs, closes, N, "high", lookback)


# ── compute ──────────────────────────────────────────────────────────────────
def _symbol_rows(conn, symbol):
    return conn.execute(
        "SELECT trade_date, high, low, close, prev_close FROM ("
        "  SELECT trade_date, high, low, close, prev_close FROM bhavcopy_rows"
        "  WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL)"
        "  ORDER BY trade_date DESC LIMIT ?) ORDER BY trade_date ASC",
        (symbol, ROWS_NEEDED)).fetchall()


def compute_symbol(rows, events=None):
    """rows -> dict of column values (or None when not computable)."""
    if len(rows) < 320:
        return None
    dict_rows = [{"trade_date": r["trade_date"], "close": r["close"],
                  "prev_close": r["prev_close"]} for r in rows]
    try:
        factors = _adjust.adjustment_factors(dict_rows, events)
    except Exception:  # noqa: BLE001 - adjustment must never kill the sweep
        factors = [1.0] * len(rows)

    def _adj(field):
        out = []
        for r, f in zip(rows, factors):
            v = r[field]
            out.append(float(v) * f if v is not None and f else None)
        return out

    ah, al, ac = _adj("high"), _adj("low"), _adj("close")
    tp = [None if (h is None or lo is None or c is None) else (h + lo + c) / 3.0
          for h, lo, c in zip(ah, al, ac)]
    U, L, T = ema(ah, EMA_SLOW), ema(al, EMA_SLOW), ema(tp, EMA_FAST)
    state, run = band_state(T, U, L)
    if state is None:
        return None
    st = stretch_series(T, U, L)
    m = len(rows) - 1
    out = {"trade_date": rows[m]["trade_date"], "band_state": state, "below_run": run,
           "stretch_pct": round(st[m], 2) if st[m] is not None else None,
           "stretch_pctile": stretch_pctile(st, m),
           "floor_deg": None, "floor_price": None, "floor_date": None,
           "floor_age": None, "floor_gap_pct": None, "floor_alive": None,
           "ceil_deg": None, "ceil_price": None, "ceil_date": None,
           "ceil_age": None, "ceil_gap_pct": None, "ceil_alive": None}
    for N in DEGREES:
        hit = latest_floor(al, ac, N)
        if hit:
            f, v, alive = hit
            out.update({"floor_deg": N, "floor_price": round(v, 2),
                        "floor_date": rows[f]["trade_date"], "floor_age": m - f,
                        "floor_gap_pct": round((ac[m] / v - 1.0) * 100.0, 2)
                        if ac[m] else None,
                        "floor_alive": alive})
            break
    for N in DEGREES:                                   # bearish mirror (S132c)
        hit = latest_ceiling(ah, ac, N)
        if hit:
            f, v, alive = hit
            out.update({"ceil_deg": N, "ceil_price": round(v, 2),
                        "ceil_date": rows[f]["trade_date"], "ceil_age": m - f,
                        "ceil_gap_pct": round((ac[m] / v - 1.0) * 100.0, 2)
                        if ac[m] else None,
                        "ceil_alive": alive})
            break
    return out


def compute_all(conn=None, limit=None) -> int:
    if conn is None:
        with get_conn() as c:   # src.core.db.get_conn is a @contextmanager
            return compute_all(c, limit)
    conn.executescript(SCHEMA)
    _migrate(conn)          # pre-S132c tables gain the ceiling columns idempotently
    try:
        from src.automation.corp_actions import price_ratios
    except Exception:  # noqa: BLE001
        price_ratios = None
    syms = [r[0] for r in conn.execute(
        "SELECT symbol FROM nse_equity_list ORDER BY symbol")]
    if limit:
        syms = syms[:int(limit)]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    n = 0
    for sym in syms:
        try:
            rows = _symbol_rows(conn, sym)
            events = None
            if price_ratios is not None:
                try:
                    events = price_ratios(conn, sym)
                except Exception:  # noqa: BLE001
                    events = None
            out = compute_symbol(rows, events)
            if out is None:
                continue
            # explicit column list: fresh-create vs ALTER-migrated tables order
            # the ceiling columns differently, so positional VALUES would skew.
            conn.execute(
                "INSERT OR REPLACE INTO reversal_context "
                "(symbol, trade_date, band_state, below_run, stretch_pct, "
                " stretch_pctile, floor_deg, floor_price, floor_date, floor_age, "
                " floor_gap_pct, floor_alive, computed_at, ceil_deg, ceil_price, "
                " ceil_date, ceil_age, ceil_gap_pct, ceil_alive) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sym, out["trade_date"], out["band_state"], out["below_run"],
                 out["stretch_pct"], out["stretch_pctile"], out["floor_deg"],
                 out["floor_price"], out["floor_date"], out["floor_age"],
                 out["floor_gap_pct"], out["floor_alive"], now,
                 out["ceil_deg"], out["ceil_price"], out["ceil_date"],
                 out["ceil_age"], out["ceil_gap_pct"], out["ceil_alive"]))
            n += 1
            if n % 500 == 0:
                conn.commit()
        except Exception as e:  # noqa: BLE001 - one bad symbol never kills the sweep
            print(f"  skip {sym}: {e}")
    conn.commit()
    return n


# ── selftest (offline, no DB) ────────────────────────────────────────────────
def selftest():
    # EMA seed + warmup
    e = ema([10.0] * 20, 5)
    assert e[3] is None and abs(e[4] - 10.0) < 1e-9

    # a V-shape: decline -> trough -> recovery crossing the lower bank
    closes = [100.0 - 1.5 * i for i in range(30)] + [55.5 + 2.0 * i for i in range(25)]
    highs = [c + 2.0 for c in closes]
    lows = [c - 2.0 for c in closes]
    tp = [(h + lo + c) / 3.0 for h, lo, c in zip(highs, lows, closes)]
    U, L, T = ema(highs, 13), ema(lows, 13), ema(tp, 5)
    st = stretch_series(T, U, L)
    assert min(v for v in st if v is not None) < 0          # stretched below in the fall
    # somewhere in the recovery the trigger reclaims the lower bank
    states = []
    for m in range(30, len(T)):
        s, _r = band_state(T[:m + 1], U[:m + 1], L[:m + 1])
        states.append(s)
    assert "RECLAIM" in states and states[-1] in ("ABOVE", "INSIDE")

    # floor: trough at index 30 (close 55.5) is a degree-10 down-fractal, confirmed + alive
    hit = latest_floor(lows, closes, 10)
    assert hit is not None
    f, v, alive = hit
    assert f == 30 and alive == 1 and abs(v - (closes[30] - 2.0)) < 1e-9
    # break the floor -> alive flips
    closes2 = list(closes)
    closes2[-1] = v - 1.0
    _f2, _v2, alive2 = latest_floor(lows, closes2, 10)
    assert alive2 == 0

    # ceiling mirror: the peak of an inverted V is a confirmed up-fractal;
    # a close above it flips ceil_alive
    peak_closes = [100.0 + 1.5 * i for i in range(30)] + [143.0 - 2.0 * i for i in range(25)]
    peak_highs = [c + 2.0 for c in peak_closes]
    hitc = latest_ceiling(peak_highs, peak_closes, 10)
    assert hitc is not None
    fc, vc, alivec = hitc
    assert fc == 29 and alivec == 1 and abs(vc - (peak_closes[29] + 2.0)) < 1e-9
    pc2 = list(peak_closes)
    pc2[-1] = vc + 1.0
    assert latest_ceiling(peak_highs, pc2, 10)[2] == 0

    # pctile causality: needs 250 prior values, ranks against the past only
    series = [float(i % 50) for i in range(400)]
    p = stretch_pctile(series, 399)
    assert p is not None and 0.0 <= p <= 100.0
    assert stretch_pctile(series, 100) is None               # window too short

    print("REVERSAL_CONTEXT selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--compute" in sys.argv:
        lim = None
        if "--limit" in sys.argv:
            lim = int(sys.argv[sys.argv.index("--limit") + 1])
        n = compute_all(limit=lim)
        print(f"reversal_context: {n} symbols computed")
    else:
        print(__doc__)
