"""MEP — signed accumulation/distribution character (descriptor-only).

A SIBLING of signals.py (DVPT), deliberately built from the OHLC + VWAP + volume
tape and NOT from delivery-per-trade. Where DVPT is side-blind (a magnitude), MEP
is SIGNED — it separates buying from selling — which is its only real edge over
DVPT and the reason it can drive a distribution-warning surface DVPT cannot.

DESCRIPTOR-ONLY (locked 2026-06-22). A walk-forward + Deflated-Sharpe test showed
these price-tape features carry NO incremental risk-adjusted alpha (DSR 0.45→0.36
when added to the 85-feature panel), so MEP never ranks/sizes/sorts-by-default —
it characterises. See docs/mep-strategy-design.md (§1, §8) and D62.

The score = the within-stock z-average of four SIGNED directional terms, so + =
accumulation, − = distribution. Each term is standardised against the STOCK'S OWN
trailing distribution (a thin name's lumpy day can't masquerade as a signal):

  pressure        = (close − VWAP) / VWAP            intraday: did buyers pay up?
  clv             = ((close−low) − (high−close))/(high−low)   where in range it closed
  drift_22d       = adjusted-close return over ~22 trading rows      trend direction
  updown_vol_22d  = (up-day vol − down-day vol) / total vol, 22 rows effort direction

Two CONTEXT terms are stored (shown, not summed — they modulate confidence, not
direction): compression (σ short/long — the coiled spring) and amihud_22d
(illiquidity / effort-vs-result). Raw terms are stored beside the verdict so the
UI can show the values, not just the label (data-first).

THE PHASE (the headline). The daily score is essentially TODAY'S tape — three of
its four terms are intraday or near-intraday — so it flips state ~3 days in 4: a
pressure oscillator, not a regime. So we ALSO store a smoothed, persistent PHASE:

  mep_score_smooth = rolling mean of the daily score over ~15 trading rows
  mep_state_smooth = that smoothed score banded with HYSTERESIS (asymmetric
                     enter/exit deadbands) so a regime HOLDS and transitions
                     slowly: accumulation → consolidation → distribution.

The smoothed PHASE is the headline on every surface; the daily score sits
underneath as the granular pressure read. Both are descriptor-only (D62).

Stored nightly into mep_signals (its OWN table — the 2.35M-row stock_signals hot
table is left untouched, mirroring the MTF tables' separation).

Usage:
    python -m src.automation.mep_signals                 # today's row for every stock traded today
    python -m src.automation.mep_signals --backfill      # full-history per-symbol walk (heavy)
    python -m src.automation.mep_signals --resmooth      # recompute ONLY the smoothed phase from stored daily scores (light)
    python -m src.automation.mep_signals --date 2026-06-20
    python -m src.automation.mep_signals --symbol RELIANCE
"""

import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from src.automation.adjust import adjusted_closes
from src.core.db import get_conn

log = logging.getLogger("hermes.mep")

# --- tunables (raw terms are stored, so re-tuning these + re-deriving the label
#     via --relabel never needs the underlying measures recomputed) -------------
_FETCH_DAYS = 400          # incremental per-symbol window (≥ _Z_WIN trading rows for today)
_Z_WIN = 200               # trailing trading rows for within-stock standardisation
_Z_MIN = 40                # need at least this many prior points to form a z-score
_Z_CLAMP = 4.0             # clamp z to ±this so one outlier day can't dominate
_DRIFT_LB = 22             # trading rows for the trend term
_UPDOWN_LB = 22            # trading rows for the up/down volume-skew term
_ATR_SHORT, _ATR_LONG = 14, 60   # compression = short ATR% / long ATR%
_AMIHUD_LB = 22            # trailing rows for Amihud illiquidity
_CC_THRESH = 0.30          # >30% single-day move = unadjusted corp action → not a real up/down day

# Signed-score → DAILY state bands (the granular pressure read; tunable).
_STATE = {
    "strong_accum":  1.00,
    "accum":         0.35,
    "distrib":      -0.35,
    "strong_distrib": -1.00,
}

# --- the PHASE: smoothing + hysteresis (turns the daily oscillator into a regime) ---
# WINDOW = 15 trading rows (~3 trading weeks). The user's spec said "~10-day mean";
# the binding acceptance metric was single-digit state changes per 70 rows. A VPS
# grid-search (scripts/_mep_probe.py, design §9) showed win10–14 leave choppy
# range-bound large-caps (SBIN/WIPRO) at 10–13 flips/70; win15 is the SMALLEST
# window that puts EVERY reference stock single-digit (avg 5.7, max 8, sustained
# 4.8/70). 15 is well within "~multi-week regime", so we take it.
_SMOOTH_WIN = 15           # trailing AVAILABLE daily scores averaged into the phase
_SMOOTH_MIN = 5            # need at least this many before a phase is emitted
# Hysteresis ladder over the SMOOTHED score. The 5 phases, low→high, sit between 4
# boundaries; each boundary b has a pair LO[b] < HI[b]: you cross UP into the higher
# phase only at score ≥ HI[b], and drop DOWN only at score < LO[b]. The LO→HI gap is
# the deadband that kills the daily whipsaw. Bands are calibrated against the real
# smoothed-score spread (VPS: p50≈+0.07, p95≈+0.86, std≈0.43) so STRONG is the
# selective ~10% tail and NEUTRAL/consolidation is the plurality, while transitions
# stay single-digit (design §9). Boundaries are strictly increasing & disjoint.
_SMOOTH_STATES = ["STRONG_DISTRIB", "DISTRIB", "NEUTRAL", "ACCUM", "STRONG_ACCUM"]
_SMOOTH_HI = [-0.40, -0.10, 0.28, 0.62]   # enter the higher phase at score ≥ HI[b]
_SMOOTH_LO = [-0.62, -0.28, 0.10, 0.40]   # drop to the lower phase at score < LO[b]


def _cutoff_date(trade_date: str, days: int) -> str:
    dt = datetime.strptime(trade_date, "%Y-%m-%d")
    return (dt - timedelta(days=days)).strftime("%Y-%m-%d")


def _ret_signs(adj: list) -> list:
    """+1 up / -1 down / 0 flat|first|corp-action, from ADJUSTED closes (oldest→newest)."""
    n = len(adj)
    signs = [0] * n
    for j in range(1, n):
        a0, a1 = adj[j - 1], adj[j]
        if a0 and a1 and a0 > 0:
            r = a1 / a0 - 1.0
            if abs(r) > _CC_THRESH:
                signs[j] = 0
            elif r > 0:
                signs[j] = 1
            elif r < 0:
                signs[j] = -1
    return signs


def _zscore(series: list, i: int) -> Optional[float]:
    """z of series[i] vs the stock's OWN strictly-prior trailing window. None when
    too few points or zero variance. Clamped to ±_Z_CLAMP."""
    cur = series[i]
    if cur is None:
        return None
    lo = max(0, i - _Z_WIN)
    vals = [series[j] for j in range(lo, i) if series[j] is not None]
    if len(vals) < _Z_MIN:
        return None
    m = sum(vals) / len(vals)
    var = sum((v - m) ** 2 for v in vals) / len(vals)
    sd = var ** 0.5
    if sd <= 0:
        return None
    z = (cur - m) / sd
    return max(-_Z_CLAMP, min(_Z_CLAMP, z))


def _state_from_score(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= _STATE["strong_accum"]:
        return "STRONG_ACCUM"
    if score >= _STATE["accum"]:
        return "ACCUM"
    if score <= _STATE["strong_distrib"]:
        return "STRONG_DISTRIB"
    if score <= _STATE["distrib"]:
        return "DISTRIB"
    return "NEUTRAL"


def mep_state_read(state: Optional[str], score: Optional[float]) -> str:
    """Plain-English nuance for the DAILY pressure read (DRY — one wording everywhere)."""
    if not state or score is None:
        return ""
    return {
        "STRONG_ACCUM":   "strong accumulation — price closing up its own range on conviction",
        "ACCUM":          "accumulation — net buying pressure vs the stock's own norm",
        "NEUTRAL":        "neutral — no clear accumulation or distribution signature",
        "DISTRIB":        "distribution — net selling pressure vs the stock's own norm",
        "STRONG_DISTRIB": "strong distribution — price pressed down its range, supply winning",
    }.get(state, "")


def mep_phase_read(state: Optional[str], score: Optional[float]) -> str:
    """Plain-English nuance for the SMOOTHED PHASE (the headline regime)."""
    if not state or score is None:
        return ""
    return {
        "STRONG_ACCUM":   "sustained accumulation — net buying has held for weeks",
        "ACCUM":          "accumulation phase — buyers in control over the recent run",
        "NEUTRAL":        "consolidation — no sustained accumulation or distribution",
        "DISTRIB":        "distribution phase — sellers in control over the recent run",
        "STRONG_DISTRIB": "sustained distribution — net selling has held for weeks",
    }.get(state, "")


def _smooth_state(score: Optional[float], prev: Optional[str]) -> Optional[str]:
    """Hysteretic 5-phase band from the SMOOTHED score. Sticky ratchet: from the
    previous phase, move UP a band only when score ≥ HI of that boundary, move DOWN
    only when score < LO of that boundary — so a regime holds through the deadband
    (no daily whipsaw). `prev` seeds the ratchet (NEUTRAL when unknown). Monotone
    thresholds ⇒ converges, can't oscillate."""
    if score is None:
        return None
    try:
        i = _SMOOTH_STATES.index(prev)
    except ValueError:
        i = 2  # NEUTRAL
    while i < 4 and score >= _SMOOTH_HI[i]:
        i += 1
    while i > 0 and score < _SMOOTH_LO[i - 1]:
        i -= 1
    return _SMOOTH_STATES[i]


def _smooth_chain(scores: list) -> tuple:
    """Full daily-score series oldest→newest (None gaps allowed) →
    (smooth_scores, smooth_states), aligned to the same indices. The smoothed score
    is a rolling mean over the trailing _SMOOTH_WIN AVAILABLE (non-None) daily
    scores; the phase is the hysteresis ratchet walked in order (path-dependent, so
    it MUST start from the beginning). O(n) via a sliding window — identical to the
    incremental trailing-window read, so backfill and nightly agree exactly."""
    from collections import deque
    n = len(scores)
    smooth_scores = [None] * n
    smooth_states = [None] * n
    win: deque = deque()
    wsum = 0.0
    avail = 0
    prev_state = None
    for i in range(n):
        s = scores[i]
        if s is None:
            continue
        win.append(s)
        wsum += s
        avail += 1
        if len(win) > _SMOOTH_WIN:
            wsum -= win.popleft()
        if avail >= _SMOOTH_MIN:
            ss = wsum / len(win)
            st = _smooth_state(ss, prev_state)
            smooth_scores[i] = ss
            smooth_states[i] = st
            if st is not None:
                prev_state = st
    return smooth_scores, smooth_states


def _action_events(conn, symbol: str) -> dict:
    """Corporate-action ratio tape for the tape-primary adjustment layer (D95).
    {} when the tape is absent/unreadable — inference-only, the legacy behavior."""
    try:
        from src.automation.corp_actions import price_ratios
        return price_ratios(conn, symbol)
    except Exception:  # noqa: BLE001 — the tape must never fail a compute
        return {}


def _term_arrays(asc_rows: list, events: dict = None) -> dict:
    """Per-day SIGNED + context term arrays from bhav rows OLDEST→NEWEST.
    Needs close/prev_close/avg_price/high/low/value/volume. ``events`` = the
    corporate-action ratio tape (D95 tape-primary adjustment)."""
    n = len(asc_rows)
    close = [r["close"] for r in asc_rows]
    high  = [r["high"] for r in asc_rows]
    low   = [r["low"] for r in asc_rows]
    vwap  = [r["avg_price"] for r in asc_rows]
    vol   = [r["volume"] for r in asc_rows]
    val   = [r["value"] for r in asc_rows]
    adj   = adjusted_closes([{"trade_date": r["trade_date"], "close": r["close"],
                              "prev_close": r["prev_close"]}
                             for r in asc_rows], events)
    signs = _ret_signs(adj)

    pressure = [None] * n
    clv      = [None] * n
    drift    = [None] * n
    updown   = [None] * n
    compr    = [None] * n
    amihud   = [None] * n

    for i in range(n):
        # pressure: close vs the day's own VWAP
        if vwap[i] is not None and vwap[i] > 0 and close[i] is not None:
            pressure[i] = (close[i] - vwap[i]) / vwap[i]
        # close-location value (intraday — raw OHLC, split-irrelevant within a day)
        if high[i] is not None and low[i] is not None and close[i] is not None:
            rng = high[i] - low[i]
            clv[i] = ((close[i] - low[i]) - (high[i] - close[i])) / rng if rng > 0 else 0.0
        # trend: adjusted return over _DRIFT_LB rows
        j = i - _DRIFT_LB
        if j >= 0 and adj[j] and adj[j] > 0 and adj[i] is not None:
            drift[i] = adj[i] / adj[j] - 1.0
        # up/down volume skew over the trailing _UPDOWN_LB rows (incl. today)
        up = dn = tot = 0.0
        for k in range(max(0, i - _UPDOWN_LB + 1), i + 1):
            v = vol[k]
            if v is None:
                continue
            tot += v
            if signs[k] > 0:
                up += v
            elif signs[k] < 0:
                dn += v
        updown[i] = ((up - dn) / tot) if tot > 0 else None
        # compression: short ATR% / long ATR%  (lower ⇒ coiled)
        atr_s = _atr_pct(high, low, close, i, _ATR_SHORT)
        atr_l = _atr_pct(high, low, close, i, _ATR_LONG)
        compr[i] = (atr_s / atr_l) if (atr_s is not None and atr_l and atr_l > 0) else None
        # amihud illiquidity: mean(|ret| / turnover) over trailing _AMIHUD_LB rows
        amihud[i] = _amihud(adj, val, i, _AMIHUD_LB)

    return {
        "pressure": pressure, "clv": clv, "drift": drift,
        "updown": updown, "compr": compr, "amihud": amihud,
        "dates": [r["trade_date"] for r in asc_rows],
    }


def _atr_pct(high, low, close, i, win) -> Optional[float]:
    lo = max(0, i - win + 1)
    vals = []
    for k in range(lo, i + 1):
        if high[k] is not None and low[k] is not None and close[k] and close[k] > 0:
            vals.append((high[k] - low[k]) / close[k])
    return (sum(vals) / len(vals)) if vals else None


def _amihud(adj, val, i, win) -> Optional[float]:
    lo = max(1, i - win + 1)
    vals = []
    for k in range(lo, i + 1):
        if adj[k - 1] and adj[k - 1] > 0 and adj[k] is not None and val[k] and val[k] > 0:
            r = abs(adj[k] / adj[k - 1] - 1.0)
            vals.append(r / val[k])
    return (sum(vals) / len(vals)) if vals else None


def _row_from_arrays(symbol: str, arr: dict, i: int) -> dict:
    """Build one mep_signals row for index i (signed z-composite + raw terms)."""
    zp = _zscore(arr["pressure"], i)
    zc = _zscore(arr["clv"], i)
    zd = _zscore(arr["drift"], i)
    zu = _zscore(arr["updown"], i)
    zs = [z for z in (zp, zc, zd, zu) if z is not None]
    score = (sum(zs) / len(zs)) if len(zs) >= 2 else None
    return {
        "symbol": symbol,
        "trade_date": arr["dates"][i],
        # raw signed terms (data-first: shown beside the verdict)
        "pressure": arr["pressure"][i],
        "clv": arr["clv"][i],
        "drift_22d": arr["drift"][i],
        "updown_vol_22d": arr["updown"][i],
        # context terms (stored, not summed)
        "compression": arr["compr"][i],
        "amihud_22d": arr["amihud"][i],
        # within-stock z-scores
        "z_pressure": zp, "z_clv": zc, "z_drift": zd, "z_updown": zu,
        # signed composite + banded DAILY state (the granular pressure read)
        "mep_score": score,
        "mep_state": _state_from_score(score),
        # smoothed PHASE (the headline) — filled by the _smooth_* pass, not here,
        # because it needs the stock's score SERIES, not one day. Default None so
        # the row dict always carries every _MEP_COLS key.
        "mep_score_smooth": None,
        "mep_state_smooth": None,
        "data_points_used": len([1 for j in range(i) if arr["pressure"][j] is not None]),
    }


def compute_mep_for_symbol_date(symbol: str, trade_date: str) -> Optional[dict]:
    """One (symbol, trade_date) row. Fetches a _FETCH_DAYS window (enough trailing
    rows to z-score today), computes the term arrays, returns today's row."""
    cutoff = _cutoff_date(trade_date, _FETCH_DAYS)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, open, high, low, close, prev_close, avg_price,
                   value, volume, num_trades
            FROM bhavcopy_rows
            WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
              AND trade_date <= ? AND trade_date >= ?
            ORDER BY trade_date ASC
            """,
            (symbol, trade_date, cutoff),
        ).fetchall()
        events = _action_events(conn, symbol)
    if not rows or rows[-1]["trade_date"] != trade_date:
        return None
    arr = _term_arrays(rows, events)
    return _row_from_arrays(symbol, arr, len(rows) - 1)


_MEP_COLS = [
    "symbol", "trade_date",
    "pressure", "clv", "drift_22d", "updown_vol_22d",
    "compression", "amihud_22d",
    "z_pressure", "z_clv", "z_drift", "z_updown",
    "mep_score", "mep_state",
    "mep_score_smooth", "mep_state_smooth",
    "data_points_used",
]


_ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS mep_signals (
    symbol TEXT NOT NULL, trade_date TEXT NOT NULL,
    pressure REAL, clv REAL, drift_22d REAL, updown_vol_22d REAL,
    compression REAL, amihud_22d REAL,
    z_pressure REAL, z_clv REAL, z_drift REAL, z_updown REAL,
    mep_score REAL, mep_state TEXT,
    mep_score_smooth REAL, mep_state_smooth TEXT,
    data_points_used INTEGER,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_mep_date  ON mep_signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_mep_state ON mep_signals(trade_date, mep_state);
CREATE INDEX IF NOT EXISTS idx_mep_score ON mep_signals(trade_date, mep_score DESC);
-- idx_mep_phase (on the smoothed column) is created in ensure_table() AFTER the
-- ADD COLUMN migration, so it can't live here (this runs before the column exists
-- on a pre-existing table).
"""


def ensure_table() -> None:
    """Defensive create + additive migration — the canonical def lives in db.py
    SCHEMA_BASE, but this lets the module stand up (and forward-migrate) its own
    table on a host whose deployed db.py predates it, so we can ship ONLY this new
    file (parallel-tree safety). ADD COLUMN is idempotent via the pragma guard."""
    with get_conn() as conn:
        conn.executescript(_ENSURE_SQL)
        have = {r["name"] for r in conn.execute("PRAGMA table_info(mep_signals)").fetchall()}
        if "mep_score_smooth" not in have:
            conn.execute("ALTER TABLE mep_signals ADD COLUMN mep_score_smooth REAL")
        if "mep_state_smooth" not in have:
            conn.execute("ALTER TABLE mep_signals ADD COLUMN mep_state_smooth TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mep_phase "
                     "ON mep_signals(trade_date, mep_score_smooth DESC)")


def store_mep(signal: dict) -> None:
    placeholders = ",".join("?" * len(_MEP_COLS))
    sql = (f"INSERT OR REPLACE INTO mep_signals ({','.join(_MEP_COLS)}) "
           f"VALUES ({placeholders})")
    with get_conn() as conn:
        conn.execute(sql, [signal.get(c) for c in _MEP_COLS])


def mep_exists(symbol: str, trade_date: str) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM mep_signals WHERE symbol = ? AND trade_date = ?",
            (symbol, trade_date),
        ).fetchone() is not None


def _smooth_date(conn, trade_date: str, symbol: Optional[str] = None) -> int:
    """Fill mep_score_smooth / mep_state_smooth for trade_date from the ALREADY
    STORED daily-score series (no bhav fetch). For each symbol with a daily score on
    trade_date: smoothed score = mean of its trailing _SMOOTH_WIN available daily
    scores; phase = the hysteresis ratchet seeded from the most recent prior phase.
    This matches _smooth_chain exactly (the stored series has no NULL mep_score
    rows), so the nightly incremental and a full --resmooth agree to the digit."""
    if symbol:
        syms = [symbol]
    else:
        syms = [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM mep_signals WHERE trade_date=? AND mep_score IS NOT NULL",
            (trade_date,)).fetchall()]
    updates = []
    for sym in syms:
        recent = conn.execute(
            "SELECT mep_score FROM mep_signals "
            "WHERE symbol=? AND trade_date<=? AND mep_score IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT ?",
            (sym, trade_date, _SMOOTH_WIN)).fetchall()
        scores = [r["mep_score"] for r in recent]   # newest→…; order-independent for a mean
        ss = (sum(scores) / len(scores)) if len(scores) >= _SMOOTH_MIN else None
        prev = conn.execute(
            "SELECT mep_state_smooth p FROM mep_signals "
            "WHERE symbol=? AND trade_date<? AND mep_state_smooth IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1", (sym, trade_date)).fetchone()
        st = _smooth_state(ss, prev["p"] if prev else None)
        updates.append((ss, st, sym, trade_date))
    if updates:
        conn.executemany(
            "UPDATE mep_signals SET mep_score_smooth=?, mep_state_smooth=? "
            "WHERE symbol=? AND trade_date=?", updates)
    return len(updates)


# --- Modes -----------------------------------------------------------------

def compute_for_date(trade_date: str, force: bool = False) -> int:
    """Compute today's MEP row for every symbol that traded on trade_date.

    CL-RS-10: by default an existing (symbol, trade_date) row is skipped so a
    re-run is cheap. But that meant a row written by a PARTIAL/earlier run was
    never refreshed once more bhav data landed. Pass force=True (CLI --force) to
    recompute and overwrite existing rows for the date."""
    ensure_table()
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE trade_date = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol""",
            (trade_date,),
        ).fetchall()]
    if not symbols:
        log.info("no symbols for %s — nothing to compute", trade_date)
        return 0
    log.info("computing MEP for %d symbols on %s", len(symbols), trade_date)
    n = 0
    for i, sym in enumerate(symbols, 1):
        if not force and mep_exists(sym, trade_date):
            continue
        sig = compute_mep_for_symbol_date(sym, trade_date)
        if sig and sig.get("mep_score") is not None:
            store_mep(sig)
            n += 1
        if i % 200 == 0:
            log.info("  progress: %d / %d", i, len(symbols))
    # second pass: fill the smoothed PHASE for today from the stored daily series
    with get_conn() as conn:
        n_ph = _smooth_date(conn, trade_date)
    log.info("date %s done: %d MEP rows stored, %d phases smoothed", trade_date, n, n_ph)
    return n


def run_today(force: bool = False) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(trade_date) AS d FROM bhavcopy_rows").fetchone()
    if not row or not row["d"]:
        return False, "no bhav data found"
    n = compute_for_date(row["d"], force=force)
    return True, f"computed {n} MEP rows for {row['d']}"


def _backfill_mep_for_symbol(conn, symbol: str) -> int:
    """Load a symbol's FULL history once, compute every date's row (within-stock
    z uses strictly-prior windows → no look-ahead), and INSERT OR REPLACE all."""
    rows = conn.execute(
        """SELECT trade_date, open, high, low, close, prev_close, avg_price,
                  value, volume, num_trades
           FROM bhavcopy_rows
           WHERE symbol = ? AND series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
           ORDER BY trade_date ASC""",
        (symbol,),
    ).fetchall()
    if not rows:
        return 0
    arr = _term_arrays(rows, _action_events(conn, symbol))
    daily = [_row_from_arrays(symbol, arr, i) for i in range(len(rows))]
    # smoothed PHASE over the full daily-score series (None warmup gaps preserved
    # so indices stay aligned with `daily`)
    smooth_scores, smooth_states = _smooth_chain([d["mep_score"] for d in daily])
    out = []
    for i, sig in enumerate(daily):
        if sig.get("mep_score") is None:
            continue
        sig["mep_score_smooth"] = smooth_scores[i]
        sig["mep_state_smooth"] = smooth_states[i]
        out.append([sig.get(c) for c in _MEP_COLS])
    if out:
        placeholders = ",".join("?" * len(_MEP_COLS))
        conn.executemany(
            f"INSERT OR REPLACE INTO mep_signals ({','.join(_MEP_COLS)}) "
            f"VALUES ({placeholders})", out)
    return len(out)


def run_backfill() -> tuple[int, int]:
    """Full-history per-symbol walk — the heavy initial/recompute pass."""
    ensure_table()
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            """SELECT DISTINCT symbol FROM bhavcopy_rows
               WHERE series = 'EQ' AND (segment = 'CM' OR segment IS NULL)
               ORDER BY symbol"""
        ).fetchall()]
    log.info("MEP backfill: %d symbols to walk", len(symbols))
    total = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            try:
                total += _backfill_mep_for_symbol(conn, sym)
            except Exception as e:
                log.warning("MEP backfill failed for %s: %s", sym, e)
        if k % 100 == 0:
            log.info("  progress: %d / %d symbols, %d rows", k, len(symbols), total)
        time.sleep(0.01)
    log.info("MEP backfill complete: %d symbols, %d rows", len(symbols), total)
    return len(symbols), total


def run_resmooth() -> tuple[int, int]:
    """Recompute ONLY the smoothed PHASE columns from the already-stored daily
    mep_score series — no bhav fetch, no term recompute. The light post-deploy
    backfill for the two new columns (and the place to re-run after re-tuning the
    bands). Idempotent."""
    ensure_table()
    with get_conn() as conn:
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM mep_signals ORDER BY symbol").fetchall()]
    log.info("MEP resmooth: %d symbols to re-phase", len(symbols))
    total = 0
    for k, sym in enumerate(symbols, 1):
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT trade_date, mep_score FROM mep_signals "
                "WHERE symbol=? ORDER BY trade_date ASC", (sym,)).fetchall()
            if not rows:
                continue
            ss, sst = _smooth_chain([r["mep_score"] for r in rows])
            upd = [(ss[i], sst[i], sym, rows[i]["trade_date"]) for i in range(len(rows))]
            conn.executemany(
                "UPDATE mep_signals SET mep_score_smooth=?, mep_state_smooth=? "
                "WHERE symbol=? AND trade_date=?", upd)
            total += len(upd)
        if k % 200 == 0:
            log.info("  resmooth progress: %d / %d symbols, %d rows", k, len(symbols), total)
    log.info("MEP resmooth complete: %d symbols, %d rows", len(symbols), total)
    return len(symbols), total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true",
                   help="Full-history per-symbol walk (heavy initial/recompute pass).")
    p.add_argument("--resmooth", action="store_true",
                   help="Recompute ONLY the smoothed phase from stored daily scores (light).")
    p.add_argument("--date", type=str, help="YYYY-MM-DD — compute one date for all symbols")
    p.add_argument("--symbol", type=str, help="compute one symbol's latest MEP row")
    p.add_argument("--force", action="store_true",
                   help="recompute & overwrite existing rows for the date (CL-RS-10) "
                        "instead of skipping symbols that already have a row")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.symbol:
        ensure_table()
        with get_conn() as conn:
            row = conn.execute(
                "SELECT MAX(trade_date) AS d FROM bhavcopy_rows WHERE symbol = ?",
                (args.symbol.upper(),),
            ).fetchone()
        if not row or not row["d"]:
            log.warning("no bhav data for %s", args.symbol)
            return
        sig = compute_mep_for_symbol_date(args.symbol.upper(), row["d"])
        if sig:
            store_mep(sig)
            with get_conn() as conn:
                _smooth_date(conn, row["d"], symbol=args.symbol.upper())
                m = conn.execute(
                    "SELECT mep_score_smooth ss, mep_state_smooth st FROM mep_signals "
                    "WHERE symbol=? AND trade_date=?", (args.symbol.upper(), row["d"])).fetchone()
            log.info("MEP %s @ %s: daily score=%s state=%s | phase score=%s state=%s",
                     args.symbol.upper(), row["d"], sig.get("mep_score"), sig.get("mep_state"),
                     m["ss"] if m else None, m["st"] if m else None)
    elif args.backfill:
        n_syms, n_rows = run_backfill()
        log.info("MEP backfill complete: %d symbols, %d rows", n_syms, n_rows)
    elif args.resmooth:
        n_syms, n_rows = run_resmooth()
        log.info("MEP resmooth complete: %d symbols, %d rows", n_syms, n_rows)
    elif args.date:
        compute_for_date(args.date, force=args.force)
    else:
        ok, msg = run_today(force=args.force)
        log.info(msg)


if __name__ == "__main__":
    main()
