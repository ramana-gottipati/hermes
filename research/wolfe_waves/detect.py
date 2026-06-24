"""Wolfe-wave 1-4 detection (the part Hermes owns).

ATR-normalized zigzag -> alternating pivots -> candidate (1,2,3,4) validated
against Ramana's convention (bullish: 1 high, 2 low, 3 lower-high, 4 lower-low;
legs 1-2 & 3-4 the two down-thrusts) -> symmetry / channel scoring -> EPA target.

Every pivot returned by the zigzag is CONFIRMED by a subsequent >= k*ATR reversal,
so point 4 is always locked by construction; a still-forming point 5 is the job of
point5.py against live price. Pure stdlib.
"""
import math
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


@dataclass
class Pivot:
    idx: int
    price: float
    kind: str  # 'H' | 'L'


@dataclass
class Wave:
    symbol: str
    direction: str  # 'BULL' | 'BEAR'
    p1: Pivot
    p2: Pivot
    p3: Pivot
    p4: Pivot
    leg12_price: float
    leg12_bars: int
    leg34_price: float
    leg34_bars: int
    sym_price: float
    sym_time: float
    channel_ratio: float
    retrace: float
    quality: float
    tier: str
    swing_k: float
    target_price: float
    eta_idx: int
    lock_idx: int  # = p4.idx (confirmed)


def zigzag(high, low, atr_arr, k):
    """ATR-normalized zigzag -> list[Pivot], strictly alternating H/L."""
    n = len(high)
    piv: list[Pivot] = []
    if n < 3:
        return piv
    dirn = 0                      # 0 undetermined, +1 seeking high, -1 seeking low
    hi_i, hi_p = 0, high[0]
    lo_i, lo_p = 0, low[0]
    for i in range(1, n):
        a = atr_arr[i]
        if high[i] > hi_p:
            hi_p, hi_i = high[i], i
        if low[i] < lo_p:
            lo_p, lo_i = low[i], i
        if a is None or a <= 0:
            continue
        th = k * a
        if dirn >= 0 and hi_i < i and (hi_p - low[i]) >= th:
            piv.append(Pivot(hi_i, hi_p, 'H'))
            dirn = -1
            lo_i, lo_p = i, low[i]
            continue
        if dirn <= 0 and lo_i < i and (high[i] - lo_p) >= th:
            piv.append(Pivot(lo_i, lo_p, 'L'))
            dirn = 1
            hi_i, hi_p = i, high[i]
            continue
    return piv


def _sc(x, denom):
    """1.0 at x==1, decaying with |ln x|; 0 at x==denom or 1/denom."""
    if x <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(math.log(x)) / math.log(denom))


def _retrace_score(r):
    if 0.382 <= r <= 0.886:
        return 1.0
    d = min(abs(r - 0.382), abs(r - 0.886))
    return max(0.0, 1.0 - d / 0.382)


def _tier(q):
    return "HIGH" if q >= 0.75 else "MED" if q >= 0.55 else "LOW"


def _classify(a, b, c, d, sym_lo, sym_hi):
    """Return 'BULL'/'BEAR' if the 4 pivots pass the hard gates, else None."""
    if a.kind == 'H' and b.kind == 'L' and c.kind == 'H' and d.kind == 'L':
        if not (c.price < a.price and d.price < b.price):
            return None
        direction = 'BULL'
    elif a.kind == 'L' and b.kind == 'H' and c.kind == 'L' and d.kind == 'H':
        if not (c.price > a.price and d.price > b.price):
            return None
        direction = 'BEAR'
    else:
        return None
    leg12 = abs(b.price - a.price)
    leg34 = abs(d.price - c.price)
    if leg12 <= 0 or leg34 <= 0:
        return None
    if not (sym_lo <= leg34 / leg12 <= sym_hi):           # symmetry gate
        return None
    s13 = (c.price - a.price) / (c.idx - a.idx)
    s24 = (d.price - b.price) / (d.idx - b.idx)
    if s13 == 0 or s24 == 0 or (s24 / s13) <= 0:          # channel: same sign
        return None
    return direction


def _build(symbol, a, b, c, d, direction, k):
    leg12 = abs(b.price - a.price)
    leg34 = abs(d.price - c.price)
    leg12_b = b.idx - a.idx
    leg34_b = d.idx - c.idx
    if leg12_b <= 0 or leg34_b <= 0:
        return None
    sym_p = leg34 / leg12
    sym_t = leg34_b / leg12_b
    s13 = (c.price - a.price) / (c.idx - a.idx)
    s24 = (d.price - b.price) / (d.idx - b.idx)
    chan = s24 / s13
    retr = abs(c.price - b.price) / leg12
    q = (0.40 * _sc(sym_p, 2.0) + 0.20 * _sc(sym_t, 3.0)
         + 0.25 * _sc(chan, 3.0) + 0.15 * _retrace_score(retr))
    eslope = (d.price - a.price) / (d.idx - a.idx)        # EPA = line 1->4
    eta = d.idx + max(leg34_b, leg12_b)
    tgt = a.price + eslope * (eta - a.idx)
    return Wave(symbol, direction, a, b, c, d, leg12, leg12_b, leg34, leg34_b,
                sym_p, sym_t, chan, retr, q, _tier(q), k, tgt, eta, d.idx)


def find_waves(series, ks=(1.5,), atr_period=14, sym_lo=0.6, sym_hi=1.6,
               min_quality=0.0):
    """Detect all valid 1-4 waves across the given swing scale(s); dedupe.

    Returns (waves_sorted_by_lock_idx, atr_arr).
    """
    high, low, close = series.high, series.low, series.close
    atr_arr = common.atr(high, low, close, atr_period)
    waves = []
    for k in ks:
        piv = zigzag(high, low, atr_arr, k)
        for i in range(len(piv) - 3):
            a, b, c, d = piv[i], piv[i + 1], piv[i + 2], piv[i + 3]
            direction = _classify(a, b, c, d, sym_lo, sym_hi)
            if not direction:
                continue
            w = _build(series.symbol, a, b, c, d, direction, k)
            if w and w.quality >= min_quality:
                waves.append(w)
    # dedupe overlapping candidates across scales: same direction & point-4 within
    # 3 bars -> keep the higher quality.
    waves.sort(key=lambda w: -w.quality)
    kept = []
    for w in waves:
        if any(o.direction == w.direction and abs(o.lock_idx - w.lock_idx) <= 3
               for o in kept):
            continue
        kept.append(w)
    kept.sort(key=lambda w: w.lock_idx)
    return kept, atr_arr
