"""Wolfe-wave detector (production — rebuilt 2026-06-23 on the CORRECT convention).

Convention (panel-decided 2026-06-24; see docs/wolfe-NEXT-SESSION.md §7). Both setups
label point 1 on a LOW, so pivots run L,H,L,H; the two thrust legs 1→2 and 3→4 point
TOWARD point 5 (their standard-Fib-extension confluence is the point-5 zone):
  BEAR (sell at 5) — ASCENDING wedge: lows 1,3 rise AND highs 2,4 rise. Point 5 is the
    upper overshoot of the 2-4 rail = the Fib-confluence zone (validated on PARAS:
    legs 968.1→1066.75 & 1075.5→1133 → strong zone ≈ 1226). Then reverses DOWN.
  BULL (buy at 5) — DESCENDING wedge (Ramana's confirmed buy convention, UNCHANGED):
    descending lows, point 4 inside the 1-2 channel; point 5 = the lower overshoot of
    the 1-3 rail, reverses UP. (Fib-method reconciliation deferred — open #B1.)
  H,L,H,L decompositions are rejected (legs point away from 5 → wrong-side zone).
  Valid wave: leg 1-2 ≈ leg 3-4 (symmetry, tol 0.5–2.0), both rails monotone.

Detection is on-the-fly per symbol/index. Pure-stdlib + the production CA adjuster.
The point-5 zone is the strongest Fib overlap on the overshoot side; `fib_zones()`
returns the standard extensions level(r)=a+r·(b−a) on swings 1→2 & 3→4 and their
strong overlap zones (validated to the decimal vs Ramana's Fyers).
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
    line13_slope: float     # slope of the 1-3 line (lower rail through lows 1,3)
    line24_slope: float     # slope of the 2-4 line (upper rail; BEAR point-5 overshoots this)
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
    """a=1, b=2, c=3, d=4 — return 'BULL'/'BEAR' for a valid Wolfe 1-4, else None.

    Both setups label point 1 on a LOW (the foot Ramana draws), so pivots run L,H,L,H.
    Direction is set by the channel's slope, anchored on his method: the two thrust
    legs 1→2 and 3→4 point TOWARD point 5 (their standard-Fib-extension confluence is
    the point-5 zone), so —
      • ASCENDING wedge (lows AND highs rise) → BEAR / sell: point 5 is the upper
        overshoot of the 2-4 rail (the Fib-confluence zone, e.g. PARAS ≈ 1226), then
        price reverses DOWN.  ← validated 2026-06-24 against his Fyers PARAS drawing.
      • DESCENDING wedge (Ramana's confirmed buy convention, kept unchanged) → BULL.
    H,L,H,L decompositions place the confluence on the WRONG side of point 5 (legs
    point away from 5) — they produced the bogus downward zone and are rejected.
    See docs/wolfe-NEXT-SESSION.md §7 for the panel decision + rationale.
    """
    if not (a.kind == 'L' and b.kind == 'H' and c.kind == 'L' and d.kind == 'H'):
        return None
    # BULL — UNCHANGED: descending lows, point 4 inside the 1-2 channel (≤ 2). Deferred
    # for Fib-method reconciliation (open #B1); do not retune without a real buy drawing.
    if c.price < a.price and _line(a, c) < 0 and d.price <= b.price:
        direction = 'BULL'
    # BEAR — ascending wedge: lower rail (1-3) and upper rail (2-4) both rise; 3>1, 4>2.
    elif (c.price > a.price and d.price > b.price
          and _line(a, c) > 0 and _line(b, d) > 0):
        direction = 'BEAR'
    else:
        return None
    leg12 = abs(b.price - a.price)
    leg34 = abs(d.price - c.price)
    if leg12 <= 0 or leg34 <= 0:
        return None
    if not (sym_lo <= leg34 / leg12 <= sym_hi):   # Wolfe symmetry (legs 1-2 ≈ 3-4)
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
                sym_p, sym_t, _line(a, c), _line(b, d), _line(a, d), q, _tier(q), k)


def detect_waves(high, low, close, ks=(1.0, 1.5), atr_period=14, sym_lo=0.5, sym_hi=2.0):
    """Find Wolfe 1-4 structures (with point 5 if it has overshot). (waves, atr_arr)."""
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
            s24 = _line(b, d)

            def line13(t, _a=a, _s=s13):
                return _a.price + _s * (t - _a.idx)

            def line24(t, _b=b, _s=s24):
                return _b.price + _s * (t - _b.idx)

            # point 5 = the terminal overshoot pivot.
            #  BULL (descending): the next LOW (piv[i+4]) below point 3, overshooting
            #        the 1-3 lower rail downward — reverses up.
            #  BEAR (ascending): the next HIGH (piv[i+5], after the pullback low piv[i+4])
            #        above point 4, overshooting the 2-4 upper rail upward — reverses down.
            p5, state = None, 'FORMING'
            if direction == 'BULL' and i + 4 < len(piv):
                e = piv[i + 4]
                if e.kind == 'L' and e.price < c.price and e.price < line13(e.idx):
                    p5, state = e, 'CONFIRMED'
            elif direction == 'BEAR' and i + 5 < len(piv):
                e = piv[i + 5]
                if e.kind == 'H' and e.price > d.price and e.price > line24(e.idx):
                    p5, state = e, 'CONFIRMED'
            # Wolfe rule: the structure must NOT break out the wrong way before point 5.
            #  BULL: no HIGH above point 4 (price must turn down to 5, not break up).
            #  BEAR: no LOW below point 3 (the wedge's lower rail must hold into the
            #        terminal up-overshoot; a break below = it broke down, not a Wolfe).
            end_b = p5.idx if p5 else len(high) - 1
            breached = False
            for t in range(d.idx + 1, end_b + 1):
                if direction == 'BULL' and high[t] > d.price:
                    breached = True
                    break
                if direction == 'BEAR' and low[t] < c.price:
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


def line24_at(wave, t):
    return wave.p[1].price + wave.line24_slope * (t - wave.p[1].idx)


def point5_zone(wave, atr_val):
    """Fallback symmetry projection of the point-5 zone (leg 4-5 ≈ leg 2-3), clamped
    past the overshoot rail. analyze() prefers the Fib-confluence zone; this is used
    only when no strong Fib overlap exists on the overshoot side. Returns
    {center, low, high, t5} or None.

    BULL (descending): 5 below, clamped past the 1-3 lower rail.
    BEAR (ascending):  5 above, clamped past the 2-4 upper rail."""
    if not atr_val or atr_val <= 0:
        return None
    p1, p2, p3, p4 = wave.p
    drop23 = abs(p2.price - p3.price)            # the 2->3 swing
    t5 = wave.p5.idx if wave.p5 else p4.idx + (p4.idx - p2.idx)
    if wave.direction == 'BULL':
        center = p4.price - drop23               # symmetric projection of 5 (below)
        center = min(center, line13_at(wave, t5))   # at least past the 1-3 rail
    else:
        center = p4.price + drop23               # symmetric projection of 5 (above)
        center = max(center, line24_at(wave, t5))   # at least past the 2-4 rail
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


def analyze(conn, sym=None, idx=None, ks=(1.0, 1.5), pad=25):
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
    waves, atr_arr = detect_waves(highs, lows, closes, ks=ks)
    x0 = max(0, min((w.p[0].idx for w in waves[-3:]), default=n - 300) - pad)
    x1 = n - 1
    out = []
    for w in waves:
        if w.p[3].idx < x0:
            continue
        a = near_atr(atr_arr, w.p[3].idx) or 1.0
        # point-5 zone = the strongest Fib-extension overlap on the OVERSHOOT side
        # (BEAR: above point 4 / BULL: below point 4) — Ramana's actual method, so this
        # surface agrees with the candle overlay. Fall back to the symmetry projection
        # when no strong overlap sits on that side.
        P1, P2, P3, P4 = (pt.price for pt in w.p)
        _, _, fzones = fib_zones(P1, P2, P3, P4)
        side = [z for z in fzones
                if (z["price"] > P4 if w.direction == "BEAR" else z["price"] < P4)]
        sym_zone = point5_zone(w, a)
        if side:
            f5 = side[0]
            t5 = int(w.p5.idx if w.p5 else (sym_zone["t5"] if sym_zone else w.p[3].idx))
            zone = {"center": f5["price"], "low": f5["low"], "high": f5["high"], "t5": t5,
                    "fib": True, "r12": f5["r12"], "r34": f5["r34"]}
        else:
            zone = sym_zone
        t5 = int(w.p5.idx if w.p5 else (zone["t5"] if zone else w.p[3].idx))
        target = epa_at(w, t5)
        entry = w.p5.price if w.p5 else (zone["center"] if zone else None)
        upside = rr = rank = rank_tier = None
        if entry is not None and zone:
            buf = 0.5 * a                                  # stop just beyond the overshoot
            if w.direction == "BULL":
                stop = (w.p5.price if w.p5 else zone["low"]) - buf
                reward, risk = target - entry, entry - stop
            else:
                stop = (w.p5.price if w.p5 else zone["high"]) + buf
                reward, risk = entry - target, stop - entry
            # EPA (1-4 line) can project the wrong side for a young ascending wedge;
            # only surface upside/R:R when the target is genuinely beyond entry.
            upside = round(100.0 * reward / entry, 1) if (entry and reward > 0) else None
            rr = round(reward / risk, 2) if (risk and risk > 0 and reward > 0) else None
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


def fib_zones(p1, p2, p3, p4, ratios=_FIB_R, tol_frac=0.004):
    """Standard Fib EXTENSIONS on swing 1-2 and swing 3-4: level(r) = a + r·(b−a),
    anchored 0 at the swing start and 1.0 at its end (Ramana's / the Fyers tool).
    Returns (grid12, grid34, zones) where zones are the STRONG OVERLAPS — a 1-2 level
    coinciding with a 3-4 level — deduped and sorted strongest (tightest) first."""
    e12 = {r: p1 + r * (p2 - p1) for r in ratios}
    e34 = {r: p3 + r * (p4 - p3) for r in ratios}
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


def _wave_payload(w, dates, n):
    """Shape ONE analyzed wave (an entry of analyze()['waves']) for the candle overlay:
    line-series points keyed by date + pivot markers + Fib grids + overlap zones. The
    strongest overlap on the OVERSHOOT side leads `zones` (BEAR above point 4 / BULL
    below), and is the predicted point 5 when 5 hasn't printed yet (Ramana's method)."""
    p, p5, p1 = w["pivots"], w["p5"], w["pivots"][0]
    bull = w["direction"] == "BULL"
    color = "#3fb950" if bull else "#f85149"
    P1, P2, P3, P4 = p[0]["price"], p[1]["price"], p[2]["price"], p[3]["price"]
    e12, e34, zones = fib_zones(P1, P2, P3, P4)
    fib12 = [{"r": r, "value": round(v, 2)} for r, v in e12.items()]
    fib34 = [{"r": r, "value": round(v, 2)} for r, v in e34.items()]
    struct = [{"time": pt["date"], "value": round(pt["price"], 2)} for pt in p]
    if p5:
        struct.append({"time": p5["date"], "value": round(p5["price"], 2)})
    last5 = p5["idx"] if p5 else p[3]["idx"]
    f13 = min(n - 1, last5 + 5)
    line13 = [{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
              {"time": dates[f13], "value": round(p1["price"] + w["line13_slope"] * (f13 - p1["idx"]), 2)}]
    epa = [{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
           {"time": dates[n - 1], "value": round(p1["price"] + w["epa_slope"] * (n - 1 - p1["idx"]), 2)}]
    markers = [{"time": pt["date"], "position": "aboveBar" if pt["kind"] == "H" else "belowBar",
                "color": color, "shape": "circle", "text": str(j)} for j, pt in enumerate(p, 1)]
    if p5:
        markers.append({"time": p5["date"], "position": "aboveBar" if not bull else "belowBar",
                        "color": color, "shape": "circle", "text": "5"})
    overshoot = [z for z in zones if (z["price"] > P4 if not bull else z["price"] < P4)]
    zones = overshoot + [z for z in zones if z not in overshoot]
    p5pred = None
    if not p5 and overshoot:
        z = overshoot[0]
        p5pred = {"value": z["price"], "low": z["low"], "high": z["high"],
                  "label": f'5 ≈ {z["price"]} (1-2 ×{z["r12"]} ∩ 3-4 ×{z["r34"]})'}
    summary = (f'WolfeRank {w["wolfe_rank"]} · {w["rank_tier"]} · {w["direction"]} · {w["state"]}'
               + (f' · R:R {w["rr"]}' if w["rr"] else '')
               + (f' · up {w["upside_pct"]}%' if w["upside_pct"] is not None else '')
               + (f' · 5≈{p5pred["value"]}' if p5pred else ''))
    return {"color": color, "dir": w["direction"], "state": w["state"], "wolfe_rank": w["wolfe_rank"],
            "struct": struct, "line13": line13, "epa": epa, "markers": markers, "summary": summary,
            "p5pred": p5pred, "p4_time": p[3]["date"], "p4_value": round(p[3]["price"], 2),
            "last_time": dates[n - 1], "fib12": fib12, "fib34": fib34, "zones": zones}


def overlay_for(conn, sym=None, idx=None):
    """ALL detected waves shaped for the stock-page candle overlay, best-first by
    WolfeRank (the snippet cycles them with ‹ ›). Returns
    {waves, default, nearest, label, kind} or None. `default` = top-ranked;
    `nearest` = the wave whose point-5 zone is closest to the last close."""
    d = analyze(conn, sym=sym, idx=idx)
    if not d or not d["waves"]:
        return None
    dates, n, ws = d["dates"], d["n"], d["waves"]
    waves = [_wave_payload(w, dates, n) for w in ws]   # analyze already sorts best-first
    cur = d["closes"][-1] if d.get("closes") else None
    nearest, best = 0, None
    for i, wp in enumerate(waves):
        z = wp["p5pred"]["value"] if wp["p5pred"] else (wp["zones"][0]["price"] if wp["zones"] else None)
        if z is None:
            continue
        dist = abs(cur - z) if cur is not None else 0
        if best is None or dist < best:
            best, nearest = dist, i
    return {"waves": waves, "default": 0, "nearest": nearest,
            "label": d["label"], "kind": d["kind"]}
