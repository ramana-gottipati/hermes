"""X-09 — base length x breakout velocity (S203).

The classic O'Neil idea, made quantitative and point-in-time: a stock advances, pauses in a
consolidation **base** below a resistance **pivot** (the base's prior high), then **breaks
out** when it closes above that pivot. Two descriptors, and their interaction:

  * base_length       trading days from the base's prior peak to the breakout (how long it
                      coiled) -- longer bases store more energy.
  * breakout_velocity realized %-above-pivot PER DAY since the breakout, up to as-of
                      (point-in-time -- never reads past the as-of date).
  * x09_score         base_length x breakout_velocity -- a long base released fast scores high;
                      a failed breakout (price back below the pivot) scores NEGATIVE.

Also reports base_depth (how deep the base corrected off the pivot) and vol_surge (breakout-day
turnover vs the base's average). Prices are ADJUSTED (basis-consistent) so a split can't fake a
breakout; turnover (value, Rs) is basis-invariant. DESCRIPTIVE ONLY -- a structural read, not a
buy/sell signal.

Complements, does not duplicate: launchpad's COILED is a boolean coiled *state* (its feature
math lives in the render layer) and ignition.py ranks *delivery* intensity; this is the
price-structure base/breakout measurement neither computes.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, eq_symbols, load_series, main_conn

BASE_MAX = 250                                                 # look back up to ~1y for the base's pivot
RECENT = int(os.environ.get("X09_RECENT", 20))                # the breakout must be within N days of as-of
MIN_BASE = int(os.environ.get("X09_MIN_BASE", 10))            # ignore breakouts off a base shorter than this


# ---------- pure compute (array-level; hermetically testable) --------------------

def find_recent_breakout(adj_close, adj_high, asof_idx, base_max=BASE_MAX,
                         recent=RECENT, min_base=MIN_BASE):
    """The most recent FRESH breakout at or before ``asof_idx``, within ``recent`` days.

    A fresh breakout at day i: ``close[i]`` closes above the prior ``base_max``-day high
    (the pivot) while ``close[i-1]`` did NOT -- the first close through resistance. Returns
    ``(breakout_idx, pivot, prior_peak_idx)`` or None. Bases shorter than ``min_base`` days
    (noise pops) are skipped.
    """
    c = np.asarray(adj_close, float)
    h = np.asarray(adj_high, float)
    lo_i = max(1, asof_idx - recent + 1)
    for i in range(asof_idx, lo_i - 1, -1):
        w0 = max(0, i - base_max)
        if i - w0 < min_base:                                 # not enough prior history for a base
            continue
        prior_high = float(np.nanmax(h[w0:i]))
        if not (c[i] > prior_high):
            continue
        pw0 = max(0, (i - 1) - base_max)
        prev_prior_high = float(np.nanmax(h[pw0:i - 1])) if (i - 1) > pw0 else float("-inf")
        if c[i - 1] > prev_prior_high:                        # yesterday was already above -> not fresh
            continue
        peak = w0 + int(np.nanargmax(h[w0:i]))
        if i - peak < min_base:                               # base too short
            continue
        return i, prior_high, peak
    return None


def base_breakout_row(ss, asof=None, base_max=BASE_MAX, recent=RECENT, min_base=MIN_BASE):
    """One base/breakout descriptor row for a SymbolSeries(-like) ``ss`` as of a date
    (``asof`` truncates to <= that date). None if no qualifying recent breakout."""
    dates = np.asarray(ss.date)
    cut = np.ones(len(dates), dtype=bool) if asof is None else (dates <= asof)
    idx = np.where(cut)[0]
    if len(idx) < min_base + 2:
        return None
    asof_idx = int(idx[-1])
    res = find_recent_breakout(ss.adj_close, ss.adj_high, asof_idx, base_max, recent, min_base)
    if res is None:
        return None
    i, pivot, peak = res
    if pivot <= 0:
        return None
    base_length = i - peak
    base_low = float(np.nanmin(ss.adj_low[peak:i]))
    base_depth = (pivot - base_low) / pivot
    base_val = float(np.nanmean(ss.value[peak:i]))
    vol_surge = (float(ss.value[i]) / base_val) if base_val > 0 else float("nan")
    days_since = asof_idx - i
    last_close = float(ss.adj_close[asof_idx])
    velocity = (last_close / pivot - 1.0) / max(1, days_since)   # realized %/day above pivot (PIT)
    med_turn = getattr(ss, "med_turn", None)
    mt = float(med_turn[cut][-1]) if med_turn is not None and len(med_turn) else float("nan")
    return {
        "symbol": ss.symbol,
        "asof": dates[asof_idx],
        "breakout_date": dates[i],
        "pivot": pivot,
        "base_length": int(base_length),
        "base_depth": float(base_depth),
        "vol_surge": vol_surge,
        "days_since_breakout": int(days_since),
        "breakout_velocity": float(velocity),
        "x09_score": float(base_length * velocity),
        "last_close": last_close,
        "still_above_pivot": bool(last_close > pivot),
        "med_turn": mt,
    }


def scan(con, asof=None, liq_floor=LIQ_FLOOR, base_max=BASE_MAX, recent=RECENT, min_base=MIN_BASE):
    """Names with a qualifying recent breakout, ranked by x09_score (long base x fast thrust)."""
    out = []
    for sym in eq_symbols(con):
        ss = load_series(con, sym)
        if ss is None:
            continue
        row = base_breakout_row(ss, asof, base_max, recent, min_base)
        if row is None:
            continue
        if liq_floor and not (np.isfinite(row["med_turn"]) and row["med_turn"] >= liq_floor):
            continue
        out.append(row)
    out.sort(key=lambda r: r["x09_score"], reverse=True)
    return out


# ---------- selftest (offline, no DB) --------------------------------------------

def _fake(adj_high, adj_low, adj_close, value=None):
    n = len(adj_close)
    return SimpleNamespace(
        symbol="TEST",
        date=[f"2026-{1 + d // 28:02d}-{1 + d % 28:02d}" for d in range(n)],
        adj_high=np.array(adj_high, float), adj_low=np.array(adj_low, float),
        adj_close=np.array(adj_close, float),
        value=np.full(n, 1e7) if value is None else np.array(value, float),
        med_turn=np.full(n, 5e7),
    )


def _base_then(after_close, after_high, after_low, after_val):
    """A 41-day scaffold: a prior peak at 100, a 40-day base under it dipping to 90, then the
    caller's post-days appended. Returns (high, low, close, value) lists."""
    hi = [100.0] + [98.0] * 40
    lo = [97.0] + [90.0 if k == 20 else 94.0 for k in range(40)]
    cl = [98.0] + [95.0] * 40
    val = [1e7] * 41
    return hi + after_high, lo + after_low, cl + after_close, val + after_val


def selftest() -> None:
    # 1. clean base + breakout: prior peak day 0 (=100), 40-day base to day 40, breakout day 41.
    hi, lo, cl, val = _base_then(
        after_close=[105., 104, 103, 104, 105], after_high=[106., 105, 104, 105, 106],
        after_low=[101., 101, 100, 101, 102], after_val=[3e7, 1e7, 1e7, 1e7, 1e7])
    ss = _fake(hi, lo, cl, val)
    r = base_breakout_row(ss)
    assert r is not None, "expected a breakout"
    assert r["base_length"] == 41 and r["breakout_date"] == ss.date[41], r
    assert abs(r["base_depth"] - 0.10) < 1e-6, r["base_depth"]         # (100-90)/100
    assert r["vol_surge"] > 2.5 and r["still_above_pivot"] and r["breakout_velocity"] > 0, r
    assert r["x09_score"] > 0, r

    # 2. no breakout: price never crosses the pivot -> None.
    hi2 = [100.0] + [98.0] * 45
    ss2 = _fake(hi2, [90.0] * 46, [95.0] * 46)
    assert base_breakout_row(ss2) is None

    # 3. a too-short base (< MIN_BASE) is not counted, with no fallback breakout: day 20 is a
    #    spike-and-fail (new intraday HIGH 105 but CLOSE 96 stays under the 98 resistance, so it
    #    is NOT itself a breakout), then day 24 breaks out off that 4-day base -> rejected -> None.
    hi3 = [98.0] * 20 + [105.0] + [100.0, 100.0, 100.0] + [107.0]
    lo3 = [96.0] * 20 + [95.0] + [95.0, 95.0, 95.0] + [104.0]
    cl3 = [97.0] * 20 + [96.0] + [97.0, 97.0, 97.0] + [106.0]
    assert base_breakout_row(_fake(hi3, lo3, cl3)) is None

    # 4. a FAILED breakout (fell back below the pivot) scores NEGATIVE velocity, not-above.
    hi4, lo4, cl4, val4 = _base_then(
        after_close=[105., 101, 98, 96, 95], after_high=[106., 102, 99, 97, 96],
        after_low=[101., 97, 94, 93, 92], after_val=[3e7, 1e7, 1e7, 1e7, 1e7])
    r4 = base_breakout_row(_fake(hi4, lo4, cl4, val4))
    assert r4 is not None and r4["breakout_velocity"] < 0 and not r4["still_above_pivot"], r4
    assert r4["x09_score"] < 0, r4

    # 5. point-in-time: as-of the breakout day sees days_since 0 and a fresh, above-pivot read.
    ra = base_breakout_row(ss, asof=ss.date[41])
    assert ra is not None and ra["days_since_breakout"] == 0 and ra["still_above_pivot"], ra

    print("BASE_BREAKOUT (X-09) selftest OK")


def run():
    con = main_conn()
    rows = scan(con)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "base_breakout.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"base_breakout: {len(rows)} recent breakouts -> {path}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run()
