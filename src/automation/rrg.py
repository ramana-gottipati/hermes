"""Relative-strength depth layer — RRG (RS-Ratio + RS-Momentum), RSI-of-RS,
Mansfield RS, and the rotation quadrant + turn flags.

This is the compute half of the "deepen relative strength" work (design panel,
session 20). It is the *complement* to the existing RS stack (``index_signals``
/ ``ratio_signals``): it adds the second-order reads Ramana asked for —

  - **JdK RS-Ratio** (x-axis): the relative line, EMA-smoothed and normalised so
    every sector oscillates around 100 → cross-sector comparable (the IT-1.19 vs
    Bank-2.0 magnitude problem disappears by construction).
  - **JdK RS-Momentum** (y-axis): the rate-of-change of RS-Ratio, normalised the
    same way — i.e. the *momentum of relative strength* ("RS of RS").
  - **RSI-of-RS**: Wilder's RSI run on the *ratio line itself* (not the index
    price) — "is the relative performance overbought/oversold, and turning?".
  - **Mansfield RS**: RS ÷ its own long MA, zero-centred — the robust turn
    signal that does NOT saturate the way RSI does in a strong trend.
  - **Quadrant + turn flags**: Leading / Weakening / Lagging / Improving, plus
    the base-and-turn flags (momentum crossing the 100 centerline, oversold
    turns, RS divergences).

Self-contained (the ``oscillators.py`` pattern): this module OWNS its
``rs_extras`` table (``CREATE TABLE IF NOT EXISTS`` on first use) and NEVER edits
``db.py``. It reads the full ratio curve already stored in ``ratio_rows`` — no
new ingestion, no schema change to existing tables. A nightly run stores one
latest row per (numerator, denominator); the read path is a ₹0 SELECT. The map
*tails* are computed on-read by ``tail()`` (cheap for the ~19 sectors shown).

All metrics are arithmetic — no LLM (cost doctrine). Every value is
re-derivable from ``ratio_rows`` (pre-compute-over-recompute doctrine).

Run the job:   python -m src.automation.rrg
Self-check:    python -m src.automation.rrg --selftest
"""

from __future__ import annotations

import argparse
import logging
import math
from typing import Optional

from src.core.db import get_conn

log = logging.getLogger("hermes.rrg")


def _fin(v):
    """Coerce non-finite (inf/nan) to None so it never poisons the DB or a sort."""
    if v is None:
        return None
    return v if (isinstance(v, (int, float)) and math.isfinite(v)) else None

# ── tunable knobs (defaults; revisit after live use) ──────────────────────────
SMOOTH_SPAN = 10      # EMA span for the JdK RS line (responsiveness vs noise)
NORM_WIN = 60         # rolling window to normalise RS-Ratio around 100 (~1 quarter)
MOM_SMOOTH = 10       # EMA span for the momentum line
MOM_NORM_WIN = 60     # rolling window to normalise RS-Momentum around 100
NORM_SCALE = 10.0     # JdK convention: 100 ± 10·z
RSI_PERIOD = 14       # Wilder RSI on the ratio line
MANSFIELD_WIN = 200   # long MA for Mansfield RS (daily; ≈ Weinstein's 200)
DIV_WIN = 20          # lookback half-window for the divergence heuristic

QUADRANTS = ("Leading", "Weakening", "Lagging", "Improving")


# ── pure math (operate on a ratio series, oldest → newest) ────────────────────
def _ema(vals: list[float], span: int) -> list[Optional[float]]:
    """EMA seeded by the SMA of the first `span` values. Leading entries None."""
    out: list[Optional[float]] = [None] * len(vals)
    if len(vals) < span:
        return out
    k = 2.0 / (span + 1)
    e = sum(vals[:span]) / span
    out[span - 1] = e
    for i in range(span, len(vals)):
        e = (vals[i] - e) * k + e
        out[i] = e
    return out


def _sma(vals: list[float], win: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(vals)
    if len(vals) < win:
        return out
    s = sum(vals[:win])
    out[win - 1] = s / win
    for i in range(win, len(vals)):
        s += vals[i] - vals[i - win]
        out[i] = s / win
    return out


def _normalise_100(series: list[Optional[float]], win: int,
                   scale: float = NORM_SCALE) -> list[Optional[float]]:
    """Map a series to oscillate around 100 via a trailing z-score: 100 + scale·z."""
    out: list[Optional[float]] = [None] * len(series)
    for i in range(len(series)):
        if series[i] is None:
            continue
        window = [series[j] for j in range(max(0, i - win + 1), i + 1)
                  if series[j] is not None]
        if len(window) < win:
            continue
        m = sum(window) / len(window)
        var = sum((x - m) ** 2 for x in window) / len(window)
        sd = var ** 0.5
        out[i] = 100.0 + scale * ((series[i] - m) / sd) if sd > 1e-12 else 100.0
    return out


def _rsi_series(vals: list[float], period: int = RSI_PERIOD) -> list[Optional[float]]:
    """Wilder's RSI over the whole series (run this on the RATIO line). [0,100]."""
    out: list[Optional[float]] = [None] * len(vals)
    if len(vals) < period + 1:
        return out
    gains, losses = [], []
    for i in range(1, len(vals)):
        d = vals[i] - vals[i - 1]
        gains.append(d if d > 0 else 0.0)
        losses.append(-d if d < 0 else 0.0)

    def _rsi(ag: float, al: float) -> float:
        if al == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + ag / al)

    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out[period] = _rsi(ag, al)                       # gains[i] ↔ vals[i+1]
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi(ag, al)
    return out


def _mansfield_series(vals: list[float], win: int = MANSFIELD_WIN) -> list[Optional[float]]:
    """Mansfield RS: (RS / SMA(RS, win) − 1) × 100. Zero-centred oscillator."""
    sma = _sma(vals, win)
    return [((vals[i] / sma[i] - 1.0) * 100.0)
            if (sma[i] is not None and sma[i] != 0) else None
            for i in range(len(vals))]


def _rs_ratio_momentum(ratio: list[float]) -> tuple[list[Optional[float]], list[Optional[float]]]:
    """JdK RS-Ratio and RS-Momentum series (both normalised ~100)."""
    jdk_rs = _ema(ratio, SMOOTH_SPAN)
    rs_ratio = _normalise_100(jdk_rs, NORM_WIN)

    # Momentum = normalised EMA of the rate-of-change of the smoothed RS line.
    start = next((i for i, v in enumerate(jdk_rs) if v is not None), None)
    rs_momentum: list[Optional[float]] = [None] * len(ratio)
    if start is not None and len(jdk_rs) - start >= 2:
        valid = [v for v in jdk_rs[start:] if v is not None]
        roc = [0.0] + [(valid[i] / valid[i - 1] - 1.0) * 100.0 if valid[i - 1] else 0.0
                       for i in range(1, len(valid))]
        mom_ema = _ema(roc, MOM_SMOOTH)
        mom_full: list[Optional[float]] = [None] * len(ratio)
        for i, v in enumerate(mom_ema):
            mom_full[start + i] = v
        rs_momentum = _normalise_100(mom_full, MOM_NORM_WIN)
    return rs_ratio, rs_momentum


def quadrant(rs_ratio: Optional[float], rs_momentum: Optional[float]) -> Optional[str]:
    if rs_ratio is None or rs_momentum is None:
        return None
    if rs_ratio >= 100:
        return "Leading" if rs_momentum >= 100 else "Weakening"
    return "Improving" if rs_momentum >= 100 else "Lagging"


def _divergence(ratio: list[float], rsi: list[Optional[float]], win: int = DIV_WIN) -> tuple[int, int]:
    """Heuristic RS divergence over the last two `win`-blocks.
    bull = ratio prints a lower low but RSI-of-RS a higher low (under-perf fading).
    bear = ratio prints a higher high but RSI-of-RS a lower high (out-perf fading)."""
    if len(ratio) < 2 * win:
        return 0, 0
    r_recent, r_prior = ratio[-win:], ratio[-2 * win:-win]
    rs_recent = [x for x in rsi[-win:] if x is not None]
    rs_prior = [x for x in rsi[-2 * win:-win] if x is not None]
    if not rs_recent or not rs_prior:
        return 0, 0
    bull = 1 if (min(r_recent) < min(r_prior) and min(rs_recent) > min(rs_prior)) else 0
    bear = 1 if (max(r_recent) > max(r_prior) and max(rs_recent) < max(rs_prior)) else 0
    return bull, bear


def compute_one(ratio: list[float]) -> Optional[dict]:
    """All latest RRG/RSI-of-RS/Mansfield metrics + turn flags for one ratio
    series, or None if too short to define RS-Ratio."""
    if len(ratio) < NORM_WIN + SMOOTH_SPAN:
        return None
    rs_ratio_s, rs_mom_s = _rs_ratio_momentum(ratio)
    if rs_ratio_s[-1] is None or rs_mom_s[-1] is None:
        return None
    rsi_s = _rsi_series(ratio)
    mans_s = _mansfield_series(ratio)

    rr, rm = rs_ratio_s[-1], rs_mom_s[-1]
    rr_p = rs_ratio_s[-2] if len(rs_ratio_s) > 1 else None
    rm_p = rs_mom_s[-2] if len(rs_mom_s) > 1 else None
    rsi, rsi_p = rsi_s[-1], (rsi_s[-2] if len(rsi_s) > 1 else None)
    mans, mans_p = mans_s[-1], (mans_s[-2] if len(mans_s) > 1 else None)

    mom_cross_up = 1 if (rm_p is not None and rm_p <= 100 < rm) else 0
    mom_cross_down = 1 if (rm_p is not None and rm_p >= 100 > rm) else 0
    bull, bear = _divergence(ratio, rsi_s)

    return {
        "rs_ratio": _fin(rr),
        "rs_momentum": _fin(rm),
        "quadrant": quadrant(rr, rm),
        "rsi_of_rs": _fin(rsi),
        "mansfield": _fin(mans),
        # base-and-turn flags
        "improving_entry": 1 if (mom_cross_up and rr < 100) else 0,
        "weakening_warning": 1 if (mom_cross_down and rr > 100) else 0,
        "mom_cross_up": mom_cross_up,
        "mom_cross_down": mom_cross_down,
        "mansfield_cross_up": 1 if (mans is not None and mans_p is not None
                                    and mans_p <= 0 < mans) else 0,
        "mansfield_cross_down": 1 if (mans is not None and mans_p is not None
                                      and mans_p >= 0 > mans) else 0,
        "rsi_oversold_turn": 1 if (rsi is not None and rsi_p is not None
                                   and rsi_p < 30 and rsi > rsi_p) else 0,
        "rsi_overbought": 1 if (rsi is not None and rsi > 70) else 0,
        "rs_div_bull": bull,
        "rs_div_bear": bear,
    }


# ── storage (owns its own table) ──────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS rs_extras (
    numerator            TEXT NOT NULL,
    denominator          TEXT NOT NULL,
    trade_date           TEXT,
    rs_ratio             REAL,
    rs_momentum          REAL,
    quadrant             TEXT,
    rsi_of_rs            REAL,
    mansfield            REAL,
    improving_entry      INTEGER,
    weakening_warning    INTEGER,
    mom_cross_up         INTEGER,
    mom_cross_down       INTEGER,
    mansfield_cross_up   INTEGER,
    mansfield_cross_down INTEGER,
    rsi_oversold_turn    INTEGER,
    rsi_overbought       INTEGER,
    rs_div_bull          INTEGER,
    rs_div_bear          INTEGER,
    computed_at          TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (numerator, denominator)
);
CREATE INDEX IF NOT EXISTS idx_rs_extras_den ON rs_extras(denominator, rs_momentum);
"""

_COLS = [
    "numerator", "denominator", "trade_date", "rs_ratio", "rs_momentum",
    "quadrant", "rsi_of_rs", "mansfield", "improving_entry", "weakening_warning",
    "mom_cross_up", "mom_cross_down", "mansfield_cross_up", "mansfield_cross_down",
    "rsi_oversold_turn", "rsi_overbought", "rs_div_bull", "rs_div_bear",
]


def compute_and_store(conn=None) -> int:
    """Compute the RS-extras row for every (numerator, denominator) pair already
    in ratio_rows and upsert one latest row each. Returns pairs stored. Manages
    its own connection if none is given (the oscillators.py pattern)."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        pairs = conn.execute(
            "SELECT DISTINCT numerator, denominator FROM ratio_rows"
        ).fetchall()
        placeholders = ",".join("?" * len(_COLS))
        sql = f"INSERT OR REPLACE INTO rs_extras ({','.join(_COLS)}) VALUES ({placeholders})"
        n = 0
        for p in pairs:
            num, den = p["numerator"], p["denominator"]
            rows = conn.execute(
                "SELECT trade_date, ratio FROM ratio_rows "
                "WHERE numerator=? AND denominator=? AND ratio IS NOT NULL "
                "ORDER BY trade_date ASC", (num, den),
            ).fetchall()
            ratio = [r["ratio"] for r in rows]
            res = compute_one(ratio)
            if not res:
                continue
            res["numerator"], res["denominator"] = num, den
            res["trade_date"] = rows[-1]["trade_date"]
            conn.execute(sql, [res.get(c) for c in _COLS])
            n += 1
        if own:
            conn.commit()
        return n
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── read helpers (for the UI layer to call; no edits to this module needed) ───
def tail(numerator: str, denominator: str, n: int = 12, conn=None) -> list[dict]:
    """The last `n` (rs_ratio, rs_momentum, quadrant) points for one pair — the
    RRG *tail*. Computed on-read from ratio_rows (cheap for the few sectors shown)."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        rows = conn.execute(
            "SELECT trade_date, ratio FROM ratio_rows "
            "WHERE numerator=? AND denominator=? AND ratio IS NOT NULL "
            "ORDER BY trade_date ASC", (numerator, denominator),
        ).fetchall()
        ratio = [r["ratio"] for r in rows]
        if len(ratio) < NORM_WIN + SMOOTH_SPAN:
            return []
        rr, rm = _rs_ratio_momentum(ratio)
        out = []
        for i in range(len(ratio)):
            if rr[i] is None or rm[i] is None:
                continue
            out.append({"trade_date": rows[i]["trade_date"], "rs_ratio": rr[i],
                        "rs_momentum": rm[i], "quadrant": quadrant(rr[i], rm[i])})
        return out[-n:]
    finally:
        if own:
            cm.__exit__(None, None, None)


def latest_all(denominator: str, conn=None) -> list[dict]:
    """Every sector's latest stored RS-extras vs one benchmark (the map's current
    dots / a leaderboard). Empty if the nightly job hasn't run yet."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        rows = conn.execute(
            "SELECT * FROM rs_extras WHERE denominator=? ORDER BY rs_momentum DESC",
            (denominator,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            cm.__exit__(None, None, None)


def current_all(denominator: str, conn=None, only=None) -> list[dict]:
    """On-read fallback: compute each sector's CURRENT RS-extras vs one benchmark
    straight from ratio_rows (when rs_extras isn't populated). `only` (an iterable
    of sector names) curates the universe so the page stays fast. Momentum-sorted."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        nums = [r["numerator"] for r in conn.execute(
            "SELECT DISTINCT numerator FROM ratio_rows WHERE denominator=?",
            (denominator,)).fetchall()]
        if only:
            keep = set(only)
            nums = [n for n in nums if n in keep]
        out = []
        for num in nums:
            if num == denominator:        # never a self-pair (parity with compute_and_store)
                continue
            rows = conn.execute(
                "SELECT trade_date, ratio FROM ratio_rows "
                "WHERE numerator=? AND denominator=? AND ratio IS NOT NULL "
                "ORDER BY trade_date ASC", (num, denominator)).fetchall()
            res = compute_one([r["ratio"] for r in rows])
            if not res:
                continue
            res["numerator"], res["denominator"] = num, denominator
            res["trade_date"] = rows[-1]["trade_date"]
            out.append(res)
        out.sort(key=lambda d: d["rs_momentum"] if d["rs_momentum"] is not None else -1e9,
                 reverse=True)
        return out
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── self-check (synthetic series — no DB needed) ──────────────────────────────
def _selftest() -> None:
    import math
    # 1) Bounds + shape on a clean outperformance-then-fade series.
    up = [100.0 * (1.0 + 0.0015 * i) for i in range(200)]          # steady out-perf
    down = [up[-1] * (1.0 - 0.0015 * i) for i in range(1, 160)]     # then under-perf
    base = [down[-1] * (1.0 + 0.0009 * i) for i in range(1, 40)]    # then a base-turn
    series = up + down + base
    res = compute_one(series)
    assert res is not None, "compute_one returned None on a long series"
    assert 0 <= res["rsi_of_rs"] <= 100, f"RSI out of bounds: {res['rsi_of_rs']}"
    assert res["quadrant"] in QUADRANTS, f"bad quadrant {res['quadrant']}"
    assert all(math.isfinite(res[k]) for k in ("rs_ratio", "rs_momentum")), "non-finite"

    # 2) A crafted oversold-then-up tail must flag the RSI oversold turn.
    falling = [100.0 * (1.0 - 0.004 * i) for i in range(120)]
    turn = [falling[-1] * (1.0 + 0.006 * i) for i in range(1, 6)]
    res2 = compute_one(falling + turn)
    assert res2 is not None
    assert res2["rsi_oversold_turn"] == 1, "expected RSI oversold turn flag"

    # 3) A base-turn (deep under-perf, momentum crossing up while ratio<100)
    #    should fire improving_entry at least sometimes across a sweep of tails.
    fired = 0
    deep = [100.0 * (1.0 - 0.003 * i) for i in range(180)]
    for k in range(1, 30):
        rec = deep + [deep[-1] * (1.0 + 0.004 * j) for j in range(1, k)]
        r = compute_one(rec)
        if r and r["improving_entry"]:
            fired += 1
    assert fired > 0, "improving_entry never fired across the base-turn sweep"

    # 4) Quadrant logic spot-checks.
    assert quadrant(101, 101) == "Leading"
    assert quadrant(101, 99) == "Weakening"
    assert quadrant(99, 99) == "Lagging"
    assert quadrant(99, 101) == "Improving"
    print("rrg selftest: OK")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.selftest:
        _selftest()
        return
    stored = compute_and_store()
    log.info("rs_extras: stored %d pairs", stored)
    print(f"rs_extras: stored {stored} pairs")


if __name__ == "__main__":
    main()
