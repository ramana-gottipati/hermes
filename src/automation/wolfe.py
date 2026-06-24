"""Wolfe-wave detector (production — rebuilt 2026-06-23 on the CORRECT convention).

Canonical Wolfe structure (confirmed with Ramana):
  BULLISH (buy at 5): pivots 1·3·5 are DESCENDING LOWS, 2·4 are highs.
    3 < 1, 5 < 3 and 5 overshoots the 1-3 support line. Reverses UP.
    Target / EPA = the 1-4 line (1 low → 4 high ⇒ up-sloping).
  BEARISH (sell at 5): the mirror — 1·3·5 are ASCENDING HIGHS, 2·4 lows.
    3 > 1, 5 > 3 and 5 overshoots the 1-3 resistance line. Reverses DOWN.
    Target / EPA = the 1-4 line (down-sloping).
  Valid wave: leg 1-2 ≈ leg 3-4 (symmetry), 1-3 trends, 5 overshoots 1-3.

Detection is on-the-fly per symbol/index. Pure-stdlib + the production CA adjuster.

Point-5 / target Fibs (Ramana's method): `fib_zones()` draws a standard Fib EXTENSION
on each thrust leg (1-2 and 3-4), anchored at the leg's LOW and projected toward the
overshoot — UP for a sell (zone ABOVE the structure, e.g. PARAS 1226) — and reports
where the two grids OVERLAP (the strong zones). 2026-06-24 fix: the extensions now
project toward the overshoot side, so a sell reads its zone above (1226), not below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

try:
    from src.automation import adjust as _adjust_mod
except Exception:  # pragma: no cover
    _adjust_mod = None

RATIOS_FULL = (1.272, 1.414, 1.618, 2.0, 2.618)


@dataclass
class Pivot:
    idx: int
    price: float
    kind: str  # 'H' | 'L'


@dataclass
class Wave:
    direction: str          # 'BULL' | 'BEAR'
    p: list                 # [p1, p2, p3, p4]  (1·3 = same extreme)
    p5: object              # Pivot (overshoot) or None (forming)
    state: str              # 'CONFIRMED' | 'FORMING'
    leg12_price: float
    leg12_bars: int
    leg34_price: float
    leg34_bars: int
    sym_price: float
    sym_time: float
    line13_slope: float     # slope of the 1-3 line (overshoot reference)
    epa_slope: float        # slope of the 1-4 line (target)
    quality: float
    tier: str
    swing_k: float


# --------------------------------------------------------------------------- #
# indicators / zigzag (convention-agnostic)                                    #
# --------------------------------------------------------------------------- #
def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def atr(high, low, close, period=14):
    n = len(close)
    out = [None] * n
    if n <= period:
        return out
    trs = [0.0]
    for i in range(1, n):
        trs.append(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
    seed = sum(trs[1:period + 1]) / period
    out[period] = seed
    prev = seed
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out


def near_atr(atr_arr, i):
    j = min(i, len(atr_arr) - 1)
    while j >= 0 and (atr_arr[j] is None or atr_arr[j] <= 0):
        j -= 1
    return atr_arr[j] if j >= 0 else None


def zigzag(high, low, atr_arr, k):
    n = len(high)
    piv = []
    if n < 3:
        return piv
    dirn = 0
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


def fractal_pivots(high, low, periods=(2, 10)):
    """Williams fractals — Ramana's Fyers **Fractals 2 & 10** mechanism, replicated on
    the daily timeframe (his pivot method; replaces the ATR-zigzag). A fractal HIGH at
    bar i = a strict, unique local max of high[] over `period` bars each side; a fractal
    LOW = a strict, unique local min of low[]. Pivots from all periods are merged and
    reduced to a strictly ALTERNATING H/L sequence (keep the more-extreme of consecutive
    same-kind) so the Wolfe 1-4 scan can slide over them. A fractal only confirms
    `period` bars later — point-in-time safe (the most-recent bars carry no fractal)."""
    n = len(high)
    cand = {}
    for p in periods:
        if p < 1:
            continue
        for i in range(p, n - p):
            wh = high[i - p:i + p + 1]
            wl = low[i - p:i + p + 1]
            if high[i] == max(wh) and wh.count(high[i]) == 1:
                cand[('H', i)] = Pivot(i, high[i], 'H')
            if low[i] == min(wl) and wl.count(low[i]) == 1:
                cand[('L', i)] = Pivot(i, low[i], 'L')
    out = []
    for pv in sorted(cand.values(), key=lambda x: x.idx):
        if out and out[-1].kind == pv.kind:               # same kind in a row → keep extreme
            if (pv.kind == 'H' and pv.price > out[-1].price) or (pv.kind == 'L' and pv.price < out[-1].price):
                out[-1] = pv
        else:
            out.append(pv)
    return out


# --------------------------------------------------------------------------- #
# Wolfe structure validation + build                                           #
# --------------------------------------------------------------------------- #
def _sc(x, denom):
    if x <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(math.log(x)) / math.log(denom))


def _tier(q):
    return "HIGH" if q >= 0.75 else "MED" if q >= 0.55 else "LOW"


def _line(p_a, p_b):
    """slope of the line through two pivots (price per bar)."""
    if p_b.idx == p_a.idx:
        return 0.0
    return (p_b.price - p_a.price) / (p_b.idx - p_a.idx)


def _classify(a, b, c, d, sym_lo, sym_hi):
    """a=1, b=2, c=3, d=4 — return 'BULL'/'BEAR' if a valid Wolfe 1-4, else None."""
    # BULLISH: 1·3 are LOWS (descending), 2·4 highs.
    if a.kind == 'L' and b.kind == 'H' and c.kind == 'L' and d.kind == 'H':
        if not (c.price < a.price):          # 3 is a lower low than 1
            return None
        if _line(a, c) >= 0:                 # 1-3 lows must descend
            return None
        direction = 'BULL'
    # BEARISH: 1·3 are HIGHS (ascending), 2·4 lows.
    elif a.kind == 'H' and b.kind == 'L' and c.kind == 'H' and d.kind == 'L':
        if not (c.price > a.price):          # 3 is a higher high than 1
            return None
        if _line(a, c) <= 0:                 # 1-3 highs must ascend
            return None
        direction = 'BEAR'
    else:
        return None
    leg12 = abs(b.price - a.price)
    leg34 = abs(d.price - c.price)
    if leg12 <= 0 or leg34 <= 0:
        return None
    if not (sym_lo <= leg34 / leg12 <= sym_hi):   # Wolfe symmetry
        return None
    # point 4 must stay inside the 1-2 channel — it cannot breach point 2
    # (bull: 4 not above 2; bear: 4 not below 2).
    if direction == 'BULL' and d.price > b.price:
        return None
    if direction == 'BEAR' and d.price < b.price:
        return None
    return direction


def _build(a, b, c, d, p5, state, direction, k):
    leg12 = abs(b.price - a.price)
    leg34 = abs(d.price - c.price)
    leg12_b = b.idx - a.idx
    leg34_b = d.idx - c.idx
    if leg12_b <= 0 or leg34_b <= 0:
        return None
    sym_p = leg34 / leg12
    sym_t = leg34_b / leg12_b
    q = 0.55 * _sc(sym_p, 2.0) + 0.25 * _sc(sym_t, 3.0) + 0.20 * (1.0 if state == 'CONFIRMED' else 0.6)
    return Wave(direction, [a, b, c, d], p5, state, leg12, leg12_b, leg34, leg34_b,
                sym_p, sym_t, _line(a, c), _line(a, d), q, _tier(q), k)


def detect_waves(high, low, close, ks=(1.0, 1.5, 2.5), atr_period=14, sym_lo=0.6, sym_hi=1.6):
    """Find Wolfe 1-4 structures (with point 5 if it has overshot). (waves, atr_arr).

    Pivots via the ATR-zigzag across a small multi-scale grid: fine (1.0/1.5) surfaces
    the recent tight wave, coarse (2.5) surfaces the bigger monthly wave — so a name can
    show two nested Wolfes of different degree (validated on PARAS: k≈1.0 → the May-Jun
    wave, k≈2.5 → the Mar-Jun wave, both ending at the Jun-19 high). `fractal_pivots`
    exists but the zigzag is what cleanly identifies the five points on daily bars."""
    atr_arr = atr(high, low, close, atr_period)
    waves = []
    for k in ks:
        piv = zigzag(high, low, atr_arr, k)
        for i in range(len(piv) - 3):
            a, b, c, d = piv[i], piv[i + 1], piv[i + 2], piv[i + 3]
            direction = _classify(a, b, c, d, sym_lo, sym_hi)
            if not direction:
                continue
            s13 = _line(a, c)

            def line13(t, _a=a, _s=s13):
                return _a.price + _s * (t - _a.idx)

            # point 5 (Ramana's rule): a candidate is NOT point 5 until price crosses
            # the EXTENDED 1-3 line — ABOVE for a bear, BELOW for a bull. Take the
            # post-point-4 extreme that has crossed the rail as point 5 (CONFIRMED — and
            # it may keep extending). It need NOT be a confirmed zigzag pivot (that's why
            # the coarse Mar-Jun wave's Jun-19 high counts as point 5 even mid-pullback).
            # If price hasn't crossed the rail yet → FORMING (zone projected from Fibs).
            p5, state = None, 'FORMING'
            ex_idx = ex_val = None
            # point 5 must arrive within the wave's own horizon (~1.5× the 1-4 span),
            # not months later through an unrelated move — else a tiny old wave would
            # wrongly claim a far-future high as its point 5.
            win_end = min(len(high) - 1, d.idx + max(10, int(1.5 * (d.idx - a.idx))))
            for t in range(d.idx + 1, win_end + 1):
                rail = line13(t)
                if direction == 'BEAR' and high[t] > rail and (ex_val is None or high[t] > ex_val):
                    ex_val, ex_idx = high[t], t
                elif direction == 'BULL' and low[t] < rail and (ex_val is None or low[t] < ex_val):
                    ex_val, ex_idx = low[t], t
            if ex_idx is not None:
                p5 = Pivot(ex_idx, ex_val, 'H' if direction == 'BEAR' else 'L')
                state = 'CONFIRMED'
            # Wolfe rule: point 4 (d) must NOT be breached before point 5 forms —
            # bull: no high above point 4; bear: no low below point 4. A breach
            # means price broke out instead of forming the wave → reject.
            end_b = p5.idx if p5 else len(high) - 1
            breached = False
            for t in range(d.idx + 1, end_b + 1):
                if direction == 'BULL' and high[t] > d.price:
                    breached = True
                    break
                if direction == 'BEAR' and low[t] < d.price:
                    breached = True
                    break
            if breached:
                continue
            w = _build(a, b, c, d, p5, state, direction, k)
            if w:
                waves.append(w)
    # dedupe: same direction & point-4 within 3 bars -> keep best quality
    waves.sort(key=lambda w: -w.quality)
    kept = []
    for w in waves:
        if any(o.direction == w.direction and abs(o.p[3].idx - w.p[3].idx) <= 3 for o in kept):
            continue
        kept.append(w)
    kept.sort(key=lambda w: w.p[3].idx)
    return kept, atr_arr


# --------------------------------------------------------------------------- #
# point 5 zone + target geometry                                               #
# --------------------------------------------------------------------------- #
def epa_at(wave, t):
    """The 1-4 (EPA target) line value at bar t."""
    return wave.p[0].price + wave.epa_slope * (t - wave.p[0].idx)


def line13_at(wave, t):
    return wave.p[0].price + wave.line13_slope * (t - wave.p[0].idx)


def point5_zone(wave, atr_val):
    """Anticipated point-5 price zone (Wolfe symmetry: leg 4-5 ≈ leg 2-3), clamped
    to the overshoot side of the 1-3 line. Returns {center, low, high} or None."""
    if not atr_val or atr_val <= 0:
        return None
    p1, p2, p3, p4 = wave.p
    drop23 = abs(p2.price - p3.price)            # the 2->3 swing
    t5 = wave.p5.idx if wave.p5 else p4.idx + (p4.idx - p2.idx)
    if wave.direction == 'BULL':
        center = p4.price - drop23               # symmetric projection of 5
        center = min(center, line13_at(wave, t5))   # at least past the 1-3 line
    else:
        center = p4.price + drop23
        center = max(center, line13_at(wave, t5))
    return {"center": center, "low": center - 0.6 * atr_val, "high": center + 0.6 * atr_val, "t5": t5}


def target_fibs(wave):
    """Fib levels of the 4->5 leg projected toward the target (Ramana's '4 and 5
    Fibs'). Returns {ratio: price} or None (needs a formed point 5)."""
    if not wave.p5:
        return None
    p4 = wave.p[3]
    p5 = wave.p5
    span = p5.price - p4.price                    # negative for BULL (5 below 4)
    # retrace/extension UP from 5 toward 4 and beyond: level = p5 - r*span
    return {r: p5.price - r * span for r in (0.5, 0.618, 1.0, 1.272, 1.618, 2.0)}


# --------------------------------------------------------------------------- #
# data access                                                                  #
# --------------------------------------------------------------------------- #
def _adjust(opens, highs, lows, closes, prevs):
    if _adjust_mod:
        try:
            f = _adjust_mod.adjustment_factors(
                [{"close": c, "prev_close": p} for c, p in zip(closes, prevs)])
            opens = [o * g if o == o else o for o, g in zip(opens, f)]
            highs = [h * g if h == h else h for h, g in zip(highs, f)]
            lows = [l * g if l == l else l for l, g in zip(lows, f)]
            closes = [c * g if c == c else c for c, g in zip(closes, f)]
        except Exception:
            pass
    return opens, highs, lows, closes


def stock_series(conn, sym):
    rows = conn.execute(
        """SELECT trade_date, open, high, low, close, prev_close FROM bhavcopy_rows
           WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL)
           ORDER BY trade_date ASC""", (sym,)).fetchall()
    if len(rows) < 40:
        return None
    dates = [r[0] for r in rows]
    opens = [_f(r[1]) for r in rows]
    highs = [_f(r[2]) for r in rows]
    lows = [_f(r[3]) for r in rows]
    closes = [_f(r[4]) for r in rows]
    prevs = [_f(r[5]) for r in rows]
    opens, highs, lows, closes = _adjust(opens, highs, lows, closes, prevs)
    return dates, opens, highs, lows, closes


def index_series(conn, idx):
    rows = conn.execute(
        """SELECT trade_date, close_value FROM index_rows
           WHERE index_name=? AND close_value > 0 ORDER BY trade_date ASC""", (idx,)).fetchall()
    if len(rows) < 40:
        return None
    dates = [r[0] for r in rows]
    closes = [_f(r[1]) for r in rows]
    return dates, list(closes), list(closes), list(closes), closes  # o=h=l=c (index = close only)


def analyze(conn, sym=None, idx=None, pad=25):
    """View-ready dict: the visible window + detected waves (lines, zone, target)."""
    if sym:
        s, label, kind = stock_series(conn, sym), sym, "stock"
    elif idx:
        s, label, kind = index_series(conn, idx), idx, "index"
    else:
        return None
    if not s:
        return None
    dates, opens, highs, lows, closes = s
    n = len(closes)
    cur = closes[-1]
    waves, atr_arr = detect_waves(highs, lows, closes)
    x0 = max(0, min((w.p[0].idx for w in waves[-3:]), default=n - 300) - pad)
    x1 = n - 1
    out = []
    for w in waves:
        if w.p[3].idx < x0:
            continue
        a = near_atr(atr_arr, w.p[3].idx) or 1.0
        zone = point5_zone(w, a)
        t5 = int(w.p5.idx if w.p5 else (zone["t5"] if zone else w.p[3].idx))
        target = epa_at(w, t5)
        entry = w.p5.price if w.p5 else (zone["center"] if zone else None)
        upside = rr = rank = rank_tier = None
        if entry is not None and zone:
            buf = 0.5 * a                                  # stop just beyond the actual overshoot
            if w.direction == "BULL":
                stop = (w.p5.price if w.p5 else zone["low"]) - buf
                reward, risk = target - entry, entry - stop
            else:
                stop = (w.p5.price if w.p5 else zone["high"]) + buf
                reward, risk = entry - target, stop - entry
            upside = round(100.0 * reward / entry, 1) if entry else None
            rr = round(reward / risk, 2) if risk and risk > 0 else None
            # --- WolfeRank (0-100): the 6 dimensions ----------------------- #
            track = w.quality                                          # structure
            target_s = min(1.0, max(0.0, (upside or 0) / 50.0))        # 5->EPA amplitude
            rr_s = min(1.0, max(0.0, (rr or 0) / 3.0))                 # risk-reward
            zone_s = _sc(w.sym_price, 2.0)                             # zone strength (symmetry proxy *)
            prox_s = max(0.0, 1.0 - abs(cur - entry) / a / 5.0)        # proximity of price to entry
            age = n - 1 - (w.p5.idx if w.p5 else w.p[3].idx)
            fresh_s = max(0.0, 1.0 - age / 40.0)                       # freshness
            rank = round(100.0 * (0.30 * track + 0.20 * target_s + 0.20 * rr_s
                                  + 0.15 * zone_s + 0.10 * prox_s + 0.05 * fresh_s), 1)
            rank_tier = "A" if rank >= 70 else "B" if rank >= 50 else "C"
        out.append({
            "direction": w.direction, "tier": w.tier, "quality": round(w.quality, 2),
            "state": w.state, "sym_price": round(w.sym_price, 2),
            "pivots": [{"idx": p.idx, "price": p.price, "kind": p.kind, "date": dates[p.idx]} for p in w.p],
            "p5": ({"idx": w.p5.idx, "price": w.p5.price, "date": dates[w.p5.idx]} if w.p5 else None),
            "line13_slope": w.line13_slope, "epa_slope": w.epa_slope,
            "zone": zone, "target": target, "upside_pct": upside, "rr": rr,
            "wolfe_rank": rank, "rank_tier": rank_tier, "target_fibs": target_fibs(w),
        })
    out.sort(key=lambda x: -(x["wolfe_rank"] or 0))   # best setup first
    return {"label": label, "kind": kind, "n": n, "x0": x0, "x1": x1,
            "dates": dates, "opens": opens, "closes": closes, "highs": highs, "lows": lows,
            "has_ohlc": kind == "stock", "waves": out}


# Standard Fib-extension ratio set (matches the Fyers tool).
_FIB_R = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.414, 1.618, 2.0, 2.618, 3.618, 4.236)


def fib_zones(p1, p2, p3, p4, direction="BEAR", ratios=_FIB_R, tol_frac=0.004):
    """Standard Fib EXTENSIONS on swing 1-2 and swing 3-4, drawn the way Ramana draws
    them in Fyers: each leg anchored at its LOW and projected TOWARD THE OVERSHOOT —
    UP for a BEAR/sell (zone above the structure, e.g. PARAS 1226), DOWN for a BULL/buy.
    Returns (grid12, grid34, zones) where zones = the STRONG OVERLAPS — a 1-2 level
    coinciding with a 3-4 level — deduped and sorted strongest (tightest) first.

    2026-06-24 fix: previously projected literally from p1 by r·(p2−p1), so a sell
    (point 1 = high) projected DOWN and read the wrong-side zone (~807). Now it
    normalises each leg to (low, high) and projects toward the overshoot, reproducing
    his exact zones (legs 968.1/1066.75 & 1075.5/1133 → 2.618 ∩ 2.618 = 1226.4/1226.0)."""
    lo12, hi12 = min(p1, p2), max(p1, p2)
    lo34, hi34 = min(p3, p4), max(p3, p4)
    if direction == "BULL":               # overshoot is DOWN, below the structure
        e12 = {r: hi12 - r * (hi12 - lo12) for r in ratios}
        e34 = {r: hi34 - r * (hi34 - lo34) for r in ratios}
    else:                                  # BEAR — overshoot is UP, above the structure
        e12 = {r: lo12 + r * (hi12 - lo12) for r in ratios}
        e34 = {r: lo34 + r * (hi34 - lo34) for r in ratios}
    raw = []
    for r1, v1 in e12.items():
        for r2, v2 in e34.items():
            mid = (v1 + v2) / 2.0
            if mid and abs(v1 - v2) <= tol_frac * abs(mid):
                raw.append({"price": round(mid, 2), "r12": r1, "r34": r2,
                            "low": round(min(v1, v2), 2), "high": round(max(v1, v2), 2),
                            "tight": abs(v1 - v2)})
    raw.sort(key=lambda z: z["tight"])
    zones = []
    for z in raw:
        if any(abs(z["price"] - k["price"]) <= tol_frac * abs(z["price"]) for k in zones):
            continue
        zones.append({k: z[k] for k in ("price", "r12", "r34", "low", "high")})
    return e12, e34, zones[:4]


def _wave_payload(w, dates, n, marker_shape="circle", dashed=False):
    """Shape ONE analyzed wave for the candle overlay: 1-2-3-4-(5) structure + numbered
    markers, the 1-3 line (the point-5 confirmation rail), the EPA, the two Fib grids and
    the strong overlap zones (projected toward the overshoot)."""
    p, p5, p1 = w["pivots"], w["p5"], w["pivots"][0]
    bull = w["direction"] == "BULL"
    color = "#3fb950" if bull else "#f85149"
    P1, P2, P3, P4 = p[0]["price"], p[1]["price"], p[2]["price"], p[3]["price"]
    e12, e34, zones = fib_zones(P1, P2, P3, P4, direction=w["direction"])
    fib12 = [{"r": r, "value": round(v, 2)} for r, v in e12.items()]
    fib34 = [{"r": r, "value": round(v, 2)} for r, v in e34.items()]
    struct = [{"time": pt["date"], "value": round(pt["price"], 2)} for pt in p]
    if p5:
        struct.append({"time": p5["date"], "value": round(p5["price"], 2)})
    last5 = p5["idx"] if p5 else p[3]["idx"]
    # 1-3 line extended well past the latest bar — point 5 confirms only once it
    # crosses this rail (above for BEAR / below for BULL).
    f13 = n - 1
    line13 = [{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
              {"time": dates[f13], "value": round(p1["price"] + w["line13_slope"] * (f13 - p1["idx"]), 2)}]
    epa = [{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
           {"time": dates[n - 1], "value": round(p1["price"] + w["epa_slope"] * (n - 1 - p1["idx"]), 2)}]
    markers = [{"time": pt["date"], "position": "aboveBar" if pt["kind"] == "H" else "belowBar",
                "color": color, "shape": marker_shape, "text": str(j)} for j, pt in enumerate(p, 1)]
    if p5:
        markers.append({"time": p5["date"], "position": "aboveBar" if not bull else "belowBar",
                        "color": color, "shape": marker_shape, "text": "5"})
    p5pred = None
    if not p5 and zones:
        z = zones[0]
        p5pred = {"value": z["price"], "low": z["low"], "high": z["high"],
                  "label": f'5 ≈ {z["price"]} (1-2 ×{z["r12"]} ∩ 3-4 ×{z["r34"]})'}
    summary = (f'{w["direction"]} · {w["state"]} · rank {w["wolfe_rank"]}{w["rank_tier"]}'
               + (f' · zone {zones[0]["price"]}' if zones else '')
               + (f' · 5≈{p5pred["value"]}' if p5pred else ''))
    return {"color": color, "dir": w["direction"], "state": w["state"], "dashed": dashed,
            "struct": struct, "line13": line13, "epa": epa, "markers": markers, "summary": summary,
            "p5pred": p5pred, "p4_time": p[3]["date"], "p4_value": round(p[3]["price"], 2),
            "last_time": dates[n - 1], "fib12": fib12, "fib34": fib34, "zones": zones}


def overlay_for(conn, sym=None, idx=None, want=2):
    """Up to `want` (default 2) of the most-recent, clearest Wolfe waves, shaped for the
    stock-page candle overlay. Selection = most-recent by last pivot, ties broken by
    WolfeRank; structurally distinct (point 4 ≥3 bars apart). Returns {waves, label,
    kind} or None. (A name can carry two nested Wolfes of different degree — e.g. PARAS:
    the May-Jun wave and the Mar-Jun wave, both ending at the Jun-19 high.)"""
    d = analyze(conn, sym=sym, idx=idx)
    if not d or not d["waves"]:
        return None
    ws, dates, n = d["waves"], d["dates"], d["n"]

    def last_idx(w):
        return w["p5"]["idx"] if w["p5"] else w["pivots"][3]["idx"]

    fresh = [w for w in ws if n - 1 - last_idx(w) <= 90]
    if not fresh:
        return None
    fresh.sort(key=lambda w: (-last_idx(w), -(w["wolfe_rank"] or 0)))   # most-recent, then clearest
    picked = []
    for w in fresh:
        if any(abs(w["pivots"][3]["idx"] - q["pivots"][3]["idx"]) <= 2 for q in picked):
            continue
        picked.append(w)
        if len(picked) >= want:
            break
    waves = [_wave_payload(w, dates, n, marker_shape=("circle" if i == 0 else "square"), dashed=(i > 0))
             for i, w in enumerate(picked)]
    return {"waves": waves, "label": d["label"], "kind": d["kind"]}
# * zone_s uses symmetry as a confluence-tightness proxy until Ramana's exact
#   legs-1-2/3-4 Fib overlay is wired (open item).
