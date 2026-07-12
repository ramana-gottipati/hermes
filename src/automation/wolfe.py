"""Wolfe-wave detector (production — rebuilt 2026-06-23 on the CORRECT convention).

Canonical Wolfe structure (confirmed with Ramana):
  BULLISH (buy at 5): pivots 1·3·5 are DESCENDING LOWS, 2·4 are highs.
    3 < 1, 5 < 3 and 5 overshoots the 1-3 support line. Reverses UP.
    Target / EPA = the 1-4 line (1 low → 4 high ⇒ up-sloping).
  BEARISH (sell at 5): the mirror — 1·3·5 are ASCENDING HIGHS, 2·4 lows.
    3 > 1, 5 > 3 and 5 overshoots the 1-3 resistance line. Reverses DOWN.
    Target / EPA = the 1-4 line (down-sloping).
  Valid wave: leg 1-2 >= leg 3-4 (price), point 4 between 2 & 3, 1-3 trends, 5 overshoots 1-3.

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
    score: object = None    # §B quality dict {p1,B,C,F,G,H,I,D,total} (ported 2026-06-25)
    source: str = ""        # pivot source that found it: "zz@1.5" | "frac@10"


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


def rsi(closes, period=14):
    """Wilder RSI (pure-stdlib) aligned to closes; None until seeded. Feeds §B comp I."""
    n = len(closes)
    out = [None] * n
    if n <= period:
        return out
    g = l = 0.0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        g += ch if ch > 0 else 0.0
        l += -ch if ch < 0 else 0.0
    ag, al = g / period, l / period
    out[period] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    for i in range(period + 1, n):
        ch = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + (ch if ch > 0 else 0.0)) / period
        al = (al * (period - 1) + (-ch if ch < 0 else 0.0)) / period
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    return out


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
    # convergence rule (Ramana, 2026-07-11 — SUPERSEDES the price-only leg-ratio cap):
    # extend the two wedge rails 1-3 and 2-4; they must INTERSECT at a bar AFTER point 4
    # (a genuine converging wedge). Whether they meet is a slope question (price ÷ time),
    # not a price one — the old |leg34| <= |leg12| cap ignored time and wrongly killed
    # converging wedges whose thrust leg 3-4 out-priced leg 1-2 (when leg 1-2 spanned more
    # time, its late point 2 steepens the 2-4 rail into convergence). Direction-blind: solve
    # the crossing bar, require it forward of point 4; parallel rails (no crossing) fail.
    # sym_lo/sym_hi stay in the signature but no longer gate. Measured 2026-07-11: on
    # Nifty-500 this admits ~4,551 true converging wedges the cap killed and drops ~3,146
    # that passed on symmetry but whose rails never converge (net +1,405).
    s13, s24 = _line(a, c), _line(b, d)
    if abs(s13 - s24) < 1e-12:                              # parallel — rails never meet
        return None
    t_cross = ((b.price - a.price) + s13 * a.idx - s24 * b.idx) / (s13 - s24)
    if t_cross <= d.idx:                                    # must cross forward of point 4
        return None
    # Ramana's point-placement rules:
    #   point 2 vs 1 — BULL: 2 above 1;  BEAR: 2 below 1.
    #   point 4 between 2 and 3 — BULL: 3 < 4 < 2 (lower high);  BEAR: 2 < 4 < 3 (higher low).
    if direction == 'BULL' and not (b.price > a.price and c.price < d.price < b.price):
        return None
    if direction == 'BEAR' and not (b.price < a.price and b.price < d.price < c.price):
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


# --------------------------------------------------------------------------- #
# §B — fractal pivot quality + the points-sum quality score                    #
#   Ported verbatim from research/wolfe_waves/fractal_proto.py (validated      #
#   2026-06-25). The §A geometry is UNCHANGED; this is the additive ranking.    #
#   See docs/wolfe-rules.md §B for each component.                              #
# --------------------------------------------------------------------------- #
DETECT_DEGREES = (2, 5, 10, 20, 30)    # fractal scales for DETECTION (coarse → long waves)


def frac_degree(highs, lows, i, kind, degrees=(10, 5, 2)):
    """Largest N (CAPPED AT 10 for quality) for which bar i is a strict unique fractal."""
    n = len(highs)
    for N in degrees:
        if i - N < 0 or i + N >= n:
            continue
        if kind == 'H':
            w = highs[i - N:i + N + 1]
            if highs[i] == max(w) and w.count(highs[i]) == 1:
                return N
        else:
            w = lows[i - N:i + N + 1]
            if lows[i] == min(w) and w.count(lows[i]) == 1:
                return N
    return 0


def _lvl(deg):
    """Fractal degree → quality level: candle 0 · 2-fr 1 · 5-fr 2 · 10-fr 3 (caps at 10)."""
    return {0: 0, 2: 1, 5: 2, 10: 3}.get(deg, 3)


def find_p5(highs, lows, a, c, d, direction, n):
    """§A4 point 5: the deepest overshoot past point 3 that crosses the extended 1-3 line,
    taken until the EPA (1-4) line is touched (then it locks). Returns a Pivot or None
    (forming). The base inline scan, factored out so detection + the score agree."""
    s13, s14 = _line(a, c), _line(a, d)
    cap = min(n - 1, d.idx + max(10, int(4.0 * (d.idx - a.idx))))
    ex_idx = ex_val = None
    for t in range(d.idx + 1, cap + 1):
        epa_t = a.price + s14 * (t - a.idx)
        if (direction == 'BULL' and highs[t] >= epa_t) or (direction == 'BEAR' and lows[t] <= epa_t):
            break
        rail = a.price + s13 * (t - a.idx)
        if direction == 'BEAR' and highs[t] > rail and highs[t] > c.price and (ex_val is None or highs[t] > ex_val):
            ex_val, ex_idx = highs[t], t
        elif direction == 'BULL' and lows[t] < rail and lows[t] < c.price and (ex_val is None or lows[t] < ex_val):
            ex_val, ex_idx = lows[t], t
    return Pivot(ex_idx, ex_val, 'H' if direction == 'BEAR' else 'L') if ex_idx is not None else None


def breached(highs, lows, d, p5, direction, n):
    """Point 4 must NOT be breached before 5 forms (bull: no high>4; bear: no low<4)."""
    end_b = p5.idx if p5 else n - 1
    for t in range(d.idx + 1, end_b + 1):
        if direction == 'BULL' and highs[t] > d.price:
            return True
        if direction == 'BEAR' and lows[t] < d.price:
            return True
    return False


def score(p_list, p5, direction, highs, lows, closes, rsi_arr):
    """§B quality = plain points-sum (A×2)+B+C+F+G+H+I+D (≈3–24); point 1 separate, ×2.
    Ported from the validated sandbox; two expert panels resolved C/D/I/G/dedupe."""
    a, b, c, d = p_list
    bull = direction == 'BULL'
    n = len(highs)
    p1_lvl = _lvl(frac_degree(highs, lows, a.idx, a.kind))     # point-1 fractal level 0-3 (kept for the scan filter)
    A = 4 if p1_lvl >= 1 else 1     # Ramana 2026-07-11: candle point-1 = 1 pt · ANY fractal (>=2-fr) = 4 pts (flat, no grade, no ×2)
    B = max(1.0, (_lvl(frac_degree(highs, lows, b.idx, b.kind))                         # 1-3 (floored)
                  + _lvl(frac_degree(highs, lows, c.idx, c.kind))
                  + _lvl(frac_degree(highs, lows, d.idx, d.kind))) / 3.0)
    _e12, _e34, zones = fib_zones(a.price, b.price, c.price, d.price,
                                  direction=direction, tol_frac=0.02)
    C = F = G = D = 0
    entry = p5.price if p5 else d.price                    # default; refined to the zone below
    if zones:
        z = min(zones, key=lambda zz: abs(entry - zz["price"]))
        lo, hi = min(z["low"], z["high"]), max(z["low"], z["high"])
        gap = (hi - lo) / z["price"] * 100.0 if z["price"] else 99
        F = 4 if gap <= 0.3 else 3 if gap <= 0.6 else 2 if gap <= 1.2 else 1 if gap <= 2.0 else 0   # 0-4 (Ramana +wt; F<=2 still = gap>0.6% for the scan)
        # G (Ramana 2026-07-11, CORRECTED — "anywhere" was wrong): judge the confluence zone
        # NEAREST THE CURRENT PRICE (LTP). It starts at point 5 and tracks the LTP as price
        # travels up toward point 3 (bull) / down toward point 3 (bear); the zones all sit
        # between point 5 and point 3, so once price clears point 3 nothing is near and G=0.
        # Score by the ratios of that nearest zone IF the LTP is near it (its band ±2%), else 0:
        #   not near any zone = 0 · a shallow confluence = 1 · zone involves 2.618 = 2 ·
        #   involves 4.618 = 3 · involves BOTH 2.618 and 4.618 (one from each leg) = 4.
        cur = closes[-1]
        gz = min(zones, key=lambda zz: abs(cur - zz["price"]))
        g_lo, g_hi = min(gz["low"], gz["high"]), max(gz["low"], gz["high"])
        if g_lo * 0.98 <= cur <= g_hi * 1.02:              # LTP near this zone's band (±2%)
            _rr = {gz["r12"], gz["r34"]}
            G = (4 if (2.618 in _rr and 4.618 in _rr) else 3 if 4.618 in _rr
                 else 2 if 2.618 in _rr else 1)
        # else: G stays 0 (init) — price not near any confluence zone
        if p5:
            if lo <= p5.price <= hi:                       # clean land INSIDE the zone band
                dist = abs(p5.price - z["price"]) / p5.price * 100.0
                C = 4 if dist <= 0.1 else 3 if dist <= 0.5 else 2 if dist <= 1.0 else 1 if dist <= 1.5 else 0   # 0-4 (Ramana +wt)
                entry = z["price"]
            else:                                          # point 5 PIERCED the zone (a SPRING)
                # SPRING-AND-RECLAIM (Ramana, canon §A9): point 5 breaks the zone by ANY depth,
                # then price CLOSES BACK into/through it = a valid, often STRONG point-5 reversal
                # (the break was a stop-hunt; the broken zone flips support→resistance, and
                # reclaiming it up confirms the turn). "Any depth that reclaims counts." If it has
                # NOT reclaimed yet but price is NEAR the zone and working back toward it, partial
                # credit — the fresh point 5 is still live and has a chance. Else 0. PIT: bars > p5.
                reclaimed = any((closes[t] >= lo) if bull else (closes[t] <= hi)
                                for t in range(p5.idx + 1, n))
                if reclaimed:
                    C = 3                                  # sprang below then reclaimed the zone = strong
                    entry = lo if bull else hi
                else:
                    cur = closes[-1]                        # the fresh, still-living point 5: where is price NOW?
                    near = (cur >= lo * 0.98) if bull else (cur <= hi * 1.02)   # within ~2% of the band, turning back
                    C = 1 if near else 0
                    if near:
                        entry = lo if bull else hi
    if p5:                                                 # D = tradeable upside from ENTRY (not the spike)
        s14 = _line(a, d)
        tgt = a.price + s14 * (p5.idx - a.idx)
        up = abs(tgt - entry) / entry * 100.0 if entry else 0.0
        D = 0 if up < 10 else 1 if up < 20 else 2 if up < 35 else 3                    # 0-3
    # H = the EPA (1-4) line as SUPPORT/RESISTANCE — "touched, NOT cut" (Ramana 2026-07-11):
    # a CUT (the line passes THROUGH a candle: low <= line <= high — price moved through it) is
    # NOT a touch. A TOUCH = the candle sits ENTIRELY ON ONE SIDE of the line AND its facing
    # extreme (a low reaching DOWN to the line, or a high reaching UP to it) comes WITHIN 0.3%
    # then reverses (the line held as S/R). Counted STRICTLY BETWEEN point 1 and point 4 (the
    # endpoints define the line). Buckets: 0->0 · 1-2->1 · 3-4->2 · >4->3.
    s14 = _line(a, d)
    _EPA_TOUCH_TOL = 0.003                                  # 0.3% buffer (Ramana-chosen 2026-07-11)
    touches = 0
    for t in range(a.idx + 1, d.idx):
        ln = a.price + s14 * (t - a.idx)
        if ln <= 0 or lows[t] <= ln <= highs[t]:           # invalid, OR a CUT (line inside the candle)
            continue
        gap = (lows[t] - ln) if lows[t] > ln else (ln - highs[t])   # facing extreme -> line
        if gap / ln <= _EPA_TOUCH_TOL:
            touches += 1
    H = 0 if touches == 0 else 1 if touches <= 2 else 2 if touches <= 4 else 3
    # I = RSI(14) divergence at point 5 (Ramana 2026-07-11 fix). Compare point 5's low against
    # the PRIOR PIVOT LOW = point 3 (bull) / point 3 high (bear) — the textbook regular divergence:
    # BULL price prints a LOWER low at 5 but RSI a HIGHER low; BEAR the mirror. p5 is a lower low
    # than p3 by construction (find_p5 requires it), so we only test the RSI side. The OLD code
    # compared p5 to the RSI DURING the fall pt4->p5 (the WRONG reference) and MISSED real
    # divergences — e.g. TCS pt3(May-14) RSI 27.4 -> pt5(Jul-01) RSI 29.4 across a lower price low.
    I = 0
    r5 = rsi_arr[p5.idx] if p5 else None
    r3 = rsi_arr[c.idx]
    if r5 is not None and r3 is not None and ((bull and r5 > r3) or ((not bull) and r5 < r3)):
        I = 2
    total = A + B + C + F + G + H + I + D                   # A is now the 1/4 points directly (no ×2)
    return {"p1": p1_lvl, "A": A, "B": round(B, 2), "C": C, "F": F, "G": G, "H": H, "I": I, "D": D,
            "total": round(total, 2)}


def _reconcile_point4(waves):
    """Point-4 reconciliation (Ramana, 2026-07-11): among waves that share the SAME
    1-2-3 skeleton, point 4 is the EXTREME high (BULL) / low (BEAR) of the rally into
    point 5 — his rule "select the maximum high before the next decline; exclude any
    subsequent lower highs." The multi-scale pivot union can surface several point-4
    candidates for one wave (a later, LOWER high that is a cleaner / higher-degree fractal
    among them), and the §B score then rewards the tidier fractal over the true apex — so a
    lower, later high wins the display (TARSONS Feb-2022: Feb-21@674.5 deg-5 beat the true
    Feb-10@698.8 deg-2). This collapses each 1-2-3 group to its extreme point 4. It only
    ever chooses among candidates that ALREADY cleared §A geometry and the D108 2/3/4
    fractal gate — it never invents a point and never drops a lone structure — so it is
    orthogonal to the §B weightage (incl. the D111 rebalance): a raw-price selection, not a
    score change. Tie (equal point-4 price) → higher §B total, then earliest bar (stable)."""
    out = []
    for w in waves:
        twin_i = None
        for i, o in enumerate(out):
            if (o.direction == w.direction
                    and abs(o.p[0].idx - w.p[0].idx) <= 3
                    and abs(o.p[1].idx - w.p[1].idx) <= 3
                    and abs(o.p[2].idx - w.p[2].idx) <= 3):
                twin_i = i
                break
        if twin_i is None:
            out.append(w)
            continue
        o = out[twin_i]
        bull = w.direction == 'BULL'
        if w.p[3].price == o.p[3].price:              # exact tie → deterministic fallback
            wins = ((w.score or {}).get("total", 0.0), -w.p[3].idx) > \
                   ((o.score or {}).get("total", 0.0), -o.p[3].idx)
        else:
            wins = (w.p[3].price > o.p[3].price) if bull else (w.p[3].price < o.p[3].price)
        if wins:
            out[twin_i] = w
    return out


def detect_waves(high, low, close, ks=(1.0, 1.5, 2.5), atr_period=14, sym_lo=0.2, sym_hi=1.0,
                 degrees=DETECT_DEGREES):
    """Find Wolfe 1-4 structures (with point 5 if it has overshot). (waves, atr_arr).

    UNION pivot sourcing (2026-06-25, Ramana: additive — never lose a wave the base
    already drew): the ATR-zigzag grid (the base mechanism: fine 1.0/1.5 = the recent
    tight wave, coarse 2.5 = the monthly wave) ∪ multi-degree Williams fractals (degrees
    2/5/10/20/30 — coarse scales surface the long-range waves the zigzag misses, e.g.
    RELIANCE Nov-2022). Every candidate is validated by the LOCKED §A `_classify` and
    ranked by the §B `score` (which rewards fractal-clean pivots), so a zigzag wave whose
    pivots aren't fractals simply ranks BELOW the fractal ones; the dedup keeps the
    higher-quality copy.

    sym_lo defaults to 0.2 (the §A3 'small floor'; his rule has no hard floor — a 0.45
    contracting 2nd leg like RELIANCE Nov-2022 is valid). Geometry is unchanged from base."""
    atr_arr = atr(high, low, close, atr_period)
    rsi_arr = rsi(close)
    n = len(close)
    seqs = [("zz@%g" % k, zigzag(high, low, atr_arr, k)) for k in ks]
    seqs += [("frac@%d" % N, fractal_pivots(high, low, periods=(N,))) for N in degrees]
    raw = []
    for src, piv in seqs:
        for i in range(len(piv) - 3):
            a, b, c, d = piv[i], piv[i + 1], piv[i + 2], piv[i + 3]
            direction = _classify(a, b, c, d, sym_lo, sym_hi)
            if not direction:
                continue
            # D108 — MANDATORY 2/3/4 FRACTAL GATE (Ramana, verbatim rule: points 2, 3
            # and 4 "must, minimum 2 fractals; without a fractal do not consider them").
            # This was always the §B1 rule but had only lived as the soft B score
            # component, so candle/zigzag-pivot waves were accepted and merely scored
            # lower — measured 32% (735/2,239 over 10 names) of surfaced waves violated
            # it once D96 freshness stopped hiding them. Point 1: NO gate (a fractal
            # there is the valued §B-A bonus, not mandatory). Point 5: NO gate (§B1 —
            # entry timeliness; find_p5's 1-3 line-cross rule untouched). A pre-filter
            # only: §A geometry and §B component math stay locked.
            if (frac_degree(high, low, b.idx, b.kind) < 2
                    or frac_degree(high, low, c.idx, c.kind) < 2
                    or frac_degree(high, low, d.idx, d.kind) < 2):
                continue
            p5 = find_p5(high, low, a, c, d, direction, n)
            if breached(high, low, d, p5, direction, n):
                continue
            state = 'CONFIRMED' if p5 else 'FORMING'
            w = _build(a, b, c, d, p5, state, direction, 0.0)
            if not w:
                continue
            w.source = src
            w.score = score(w.p, p5, direction, high, low, close, rsi_arr)
            raw.append(w)
    # union dedupe: same direction & BOTH endpoints within 3 bars → keep the higher §B
    # quality (so the zigzag and fractal copies of one wave collapse to the best-scored).
    raw.sort(key=lambda w: -(w.score["total"] if w.score else 0.0))
    kept = []
    for w in raw:
        if any(o.direction == w.direction
               and abs(o.p[0].idx - w.p[0].idx) <= 3
               and abs(o.p[3].idx - w.p[3].idx) <= 3 for o in kept):
            continue
        kept.append(w)
    # point-4 reconciliation (2026-07-11): among waves sharing the same 1-2-3, keep the
    # EXTREME point 4 (Ramana's "maximum high before the next decline"), not the tidiest
    # fractal. Fixes the later-lower-high mislabel; fixed at the source so every surface
    # (overlay_for / winner_scan / /dash/wolfe) inherits it. Orthogonal to the §B weightage.
    kept = _reconcile_point4(kept)
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


def epa_touched(wave, highs, lows, n):
    """CLOSED test (Ramana): a wave is CLOSED once, AFTER point 5, price REACHES
    and TOUCHES the 1-4 (EPA) target line. BULL: a high ≥ the EPA line; BEAR: a
    low ≤ it. A confirmed wave whose EPA is NOT yet touched stays OPEN."""
    if not wave.p5:
        return False
    bull = wave.direction == 'BULL'
    for t in range(wave.p5.idx + 1, n):
        lv = epa_at(wave, t)
        if (bull and highs[t] >= lv) or ((not bull) and lows[t] <= lv):
            return True
    return False


def close_quality(wave, highs, lows, n):
    """HOW NEATLY a CLOSED wave reached the EPA (Ramana: "even if closed, I want to
    see how neatly it was closed"). From point 5 to the FIRST EPA touch: bars taken
    (speed) + the largest give-back during that run (choppiness). A fast run with a
    small pullback = a clean close; a slow, choppy run = a messy one."""
    if not wave.p5:
        return None
    bull = wave.direction == 'BULL'
    tt = None
    for t in range(wave.p5.idx + 1, n):
        lv = epa_at(wave, t)
        if (bull and highs[t] >= lv) or ((not bull) and lows[t] <= lv):
            tt = t
            break
    if tt is None:
        return None
    maxdd = 0.0
    if bull:
        run = highs[wave.p5.idx]
        for t in range(wave.p5.idx, tt + 1):
            run = max(run, highs[t])
            if run > 0:
                maxdd = max(maxdd, (run - lows[t]) / run * 100.0)
    else:
        run = lows[wave.p5.idx]
        for t in range(wave.p5.idx, tt + 1):
            run = min(run, lows[t])
            if run > 0:
                maxdd = max(maxdd, (highs[t] - run) / run * 100.0)
    tier = 'clean' if maxdd <= 3.0 else 'ok' if maxdd <= 7.0 else 'choppy'
    return {"bars_to_epa": tt - wave.p5.idx, "pullback_pct": round(maxdd, 2),
            "tier": tier, "touch_idx": tt}


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
            # CL-SCO-10: only the `o == o` (NaN) case was guarded, so a real stored
            # 0.0 (a corrupt/empty OHLC cell) survived `0 * g = 0` and entered zigzag
            # as a genuine zero LOW — instantly the all-time low, fabricating a swing.
            # A price of 0 (or negative) is invalid: map non-finite/≤0 to NaN so the
            # convention-agnostic detectors (which skip NaN naturally) ignore the bar.
            def _adj(v, g):
                if not (v == v) or v <= 0:        # NaN or non-positive ⇒ invalid bar
                    return float("nan")
                return v * g
            opens = [_adj(o, g) for o, g in zip(opens, f)]
            highs = [_adj(h, g) for h, g in zip(highs, f)]
            lows = [_adj(l, g) for l, g in zip(lows, f)]
            closes = [_adj(c, g) for c, g in zip(closes, f)]
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


def analyze(conn, sym=None, idx=None, pad=25, all_waves=False):
    """View-ready dict: the visible window + detected waves (lines, zone, target).
    all_waves=True keeps EVERY detected wave (no recent-window prune) — used by the
    overlay's ◄/► timeline walk through historical completed Wolfe waves."""
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
    x0 = 0 if all_waves else max(0, min((w.p[0].idx for w in waves[-3:]), default=n - 300) - pad)
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
        # LIFECYCLE (Ramana's 3 sections): prediction = no point 5 · open = point 5
        # printed, EPA target NOT yet touched (the actionable now) · closed = EPA
        # touched (reference; carries how-neatly-it-closed).
        if not w.p5:
            lifecycle, cq = "prediction", None
        elif epa_touched(w, highs, lows, n):
            lifecycle, cq = "closed", close_quality(w, highs, lows, n)
        else:
            lifecycle, cq = "open", None
        out.append({
            "direction": w.direction, "tier": w.tier, "quality": round(w.quality, 2),
            "quality_total": (w.score["total"] if w.score else 0), "score": w.score,
            "source": w.source, "lifecycle": lifecycle, "close_quality": cq,
            "state": w.state, "sym_price": round(w.sym_price, 2),
            "pivots": [{"idx": p.idx, "price": p.price, "kind": p.kind, "date": dates[p.idx]} for p in w.p],
            "p5": ({"idx": w.p5.idx, "price": w.p5.price, "date": dates[w.p5.idx]} if w.p5 else None),
            "line13_slope": w.line13_slope, "epa_slope": w.epa_slope,
            "zone": zone, "target": target, "upside_pct": upside, "rr": rr,
            "wolfe_rank": rank, "rank_tier": rank_tier, "target_fibs": target_fibs(w),
        })
    # rank by the §B quality points-sum (the locked quality metric); WolfeRank/upside/RR
    # stay in the payload as secondary CONTEXT (data-first), no longer the sort key.
    out.sort(key=lambda x: (-(x["quality_total"] or 0), -(x["wolfe_rank"] or 0)))
    return {"label": label, "kind": kind, "n": n, "x0": x0, "x1": x1,
            "dates": dates, "opens": opens, "closes": closes, "highs": highs, "lows": lows,
            "has_ohlc": kind == "stock", "waves": out}


# Fib EXTENSION ratios only ( >1.0 ) — these project BEYOND each thrust leg toward the
# overshoot, so an extension∩extension coincidence is a genuine forward target. The
# 0.236–1.0 levels are RETRACEMENTS (inside the leg) and must NOT enter the overlap test
# — they were producing false "zones" sitting within the structure (e.g. 0.786∩0.618).
_FIB_R = (1.272, 1.414, 1.618, 2.0, 2.618, 3.618, 4.236, 4.618)   # 2.0 RESTORED (Ramana 2026-07-11):
# it is a standard charting Fib EXTENSION (the drawing tool's FIBX already carried it), and the set
# already keeps 1.414 (√2) which is equally non-φ — so excluding 2.0 was arbitrary and hid real
# confluences (e.g. TCS 2.0∩1.414 ≈ 2090). 1.414 KEPT (his call — keep both).

# The maximum §B quality points a wave can score — A(6)+B(3)+C(3)+F(3)+G(2)+H(2)+I(2)+D(3).
# The overlay badge shows points/_QUALITY_MAX. Bump this WITH any §B weightage change
# (Ramana's pending rebalance → 25/26) so the "out of total" stays truthful.
_QUALITY_MAX = 27   # A(4)+B(3)+C(4)+F(4)+G(4)+H(3)+I(2)+D(3) — G widened to 0-4 (2026-07-11)


def fib_zones(p1, p2, p3, p4, direction="BEAR", ratios=_FIB_R, tol_frac=0.02):
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
    return e12, e34, zones[:6]


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
    # A FORMING wave runs to the right edge (so the 1-3 rail shows where price must cross
    # to confirm 5). A COMPLETED wave is framed to itself, but its rail/EPA project well
    # PAST point 5 (line_r) into the empty right so the EPA target stays visible on the
    # right of the screen (Ramana); the pan (pan_r) leaves that projection space in view.
    span = max(5, last5 - p1["idx"])
    pf = max(0, p1["idx"] - int(0.15 * span))
    pan_r = (n - 1) if not p5 else min(n - 1, last5 + int(0.70 * span))
    line_r = (n - 1) if not p5 else min(n - 1, last5 + int(1.10 * span))
    line13 = [{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
              {"time": dates[line_r], "value": round(p1["price"] + w["line13_slope"] * (line_r - p1["idx"]), 2)}]
    # EPA (1-4 target line) — ONLY once point 5 is confirmed (no projection before then).
    # It runs all the way to the chart's RIGHT EDGE (the latest bar) so the target stays
    # visible however far right Ramana scrolls — not localised to the wave like the rail.
    epa = ([{"time": dates[p1["idx"]], "value": round(p1["price"], 2)},
            {"time": dates[n - 1], "value": round(p1["price"] + w["epa_slope"] * (n - 1 - p1["idx"]), 2)}]
           if p5 else None)
    markers = [{"time": pt["date"], "position": "aboveBar" if pt["kind"] == "H" else "belowBar",
                "color": color, "shape": marker_shape, "text": str(j)} for j, pt in enumerate(p, 1)]
    if p5:
        markers.append({"time": p5["date"], "position": "aboveBar" if not bull else "belowBar",
                        "color": color, "shape": marker_shape, "text": "5"})
    # predicted 5 (forming only): the tightest Fib overlap that sits on the CORRECT side of
    # point 3 — below 3 for a bull, above 3 for a bear (it cannot be a point 5 otherwise).
    p5pred = None
    if not p5 and zones:
        side = [z for z in zones if (z["price"] < P3 if bull else z["price"] > P3)]
        if side:
            z = side[0]
            p5pred = {"value": z["price"], "low": z["low"], "high": z["high"],
                      "label": f'5 ≈ {z["price"]} (1-2 ×{z["r12"]} ∩ 3-4 ×{z["r34"]})'}
    sc = w.get("score") or {}
    qbits = (f' · [A={sc.get("A",0)} B={sc.get("B",0)} C={sc.get("C",0)} F={sc.get("F",0)} '
             f'G={sc.get("G",0)} H={sc.get("H",0)} I={sc.get("I",0)} D={sc.get("D",0)}]') if sc else ''
    # lifecycle badge (Ramana's 3 sections): OPEN = point 5 in, EPA target pending;
    # CLOSED = EPA reached (+ how neatly). Leads the §B chips so he reads state first.
    lc = w.get("lifecycle")
    cq = w.get("close_quality") or {}
    lc_txt = ''
    if lc == 'open':
        lc_txt = ' · OPEN (EPA target pending)'
    elif lc == 'closed':
        lc_txt = (f' · CLOSED ({cq.get("tier","")}: reached EPA in {cq.get("bars_to_epa","?")} bars, '
                  f'pullback {cq.get("pullback_pct","?")}%)')
    # lead with the WAVE Ramana reads (dir · status · point-4 date · ₹ zone), THEN the Q
    # quality badge + the §B chips (panel/Ramana-proxy: "I read the wave, not letter-soup").
    summary = (f'{w["direction"]} Wolfe · {w["state"]} · pt4 {w["pivots"][3]["date"]}'
               + lc_txt
               + (f' · zone {zones[0]["price"]}' if zones else '')
               + (f' · 5≈{p5pred["value"]}' if p5pred else '')
               + f' · Q{w.get("quality_total",0)}'
               + (f' (rank {w["wolfe_rank"]}{w["rank_tier"]})' if w.get("wolfe_rank") is not None else '')
               + qbits)
    return {"color": color, "dir": w["direction"], "state": w["state"], "dashed": dashed,
            "lifecycle": lc, "close_quality": w.get("close_quality"),
            "points": w.get("quality_total", 0), "points_max": _QUALITY_MAX,
            "rank_tier": w.get("rank_tier"), "wolfe_rank": w.get("wolfe_rank"),
            "struct": struct, "line13": line13, "epa": epa, "markers": markers, "summary": summary,
            "p5pred": p5pred, "p4_time": p[3]["date"], "p4_value": round(p[3]["price"], 2),
            "last_time": dates[line_r], "fib12": fib12, "fib34": fib34, "zones": zones,
            "pan_from": dates[pf], "pan_to": dates[pan_r]}


_OVERLAY_MAX = 40   # cap the ◄/► candle-overlay walk to the top-N waves by §B quality
_FRESH_KEEP_BARS = 250   # freshness guarantee: a confirmed wave whose point 5 printed within
                         # the last ~1 trading year ALWAYS enters the walk, whatever its §B Q.
                         # (2026-07-10, Ramana's TCS miss: the top-40-by-quality cut was taken
                         # across the FULL 22y history — 261 confirmed waves, #40 cutoff Q17.33 —
                         # so the live Jun-2026 wedge at Q15.0 was silently invisible. The walk
                         # exists to read CURRENT structure first; quality curates only history.)


def overlay_for(conn, sym=None, idx=None):
    """Shape the detected waves for the stock-page candle overlay, split into the two
    sections Ramana navigates (ONE wave drawn at a time):
      • prediction — the single most-recent FORMING wave at the current right edge
        (point 5 not yet confirmed; predicted-5 zone, NO EPA).
      • completed  — every CONFIRMED wave (point 5 printed), NEWEST-FIRST, for the ◄/►
        timeline walk; each carries its own structure, Fib zones and EPA.
    Returns {prediction, completed, label, kind} or None."""
    d = analyze(conn, sym=sym, idx=idx, all_waves=True)
    if not d or not d["waves"]:
        return None
    ws, dates, n = d["waves"], d["dates"], d["n"]

    def last_idx(w):
        return w["p5"]["idx"] if w["p5"] else w["pivots"][3]["idx"]

    def dedupe(lst):
        out = []
        for w in lst:
            if any(w["direction"] == q["direction"]
                   and abs(w["pivots"][3]["idx"] - q["pivots"][3]["idx"]) <= 2 for q in out):
                continue
            out.append(w)
        return out

    # completed = confirmed waves. The ◄/► walk is ONE-at-a-time, so cap it to the top
    # _OVERLAY_MAX by §B quality (the union can surface 200+; the FULL list lives on
    # /dash/wolfe, click-to-draw). 40 keeps mid-quality historical waves (RELIANCE
    # Nov-2022 ranks ~30) that a tighter cap would hide. Then show NEWEST-FIRST.
    conf = [w for w in ws if w["state"] == "CONFIRMED" and w["p5"]]
    conf.sort(key=lambda w: -(w.get("quality_total") or 0))
    top = conf[:_OVERLAY_MAX]
    top_ids = {id(w) for w in top}
    fresh = [w for w in conf if id(w) not in top_ids
             and (n - 1 - last_idx(w)) <= _FRESH_KEEP_BARS]
    confirmed = dedupe(sorted(top + fresh, key=lambda w: -last_idx(w)))
    completed = [_wave_payload(w, dates, n) for w in confirmed]
    # prediction = the single most-recent FORMING wave, only if fresh (a prediction is
    # about current price, not a closed-out historical structure).
    prediction = None
    for w in sorted([w for w in ws if not w["p5"]], key=lambda w: -last_idx(w)):
        if n - 1 - last_idx(w) <= 90:
            prediction = _wave_payload(w, dates, n)
            break
    if prediction is None and not completed:
        return None
    # compact recent bars (date, high, low) so the manual "✎ draw your own" mode can snap
    # each click to the nearer real swing extreme — the analyst sets the pivots, we compute
    # the zones. Cap to the last 800 bars (plenty of history, keeps the payload light).
    highs, lows = d["highs"], d["lows"]
    b0 = max(0, n - 800)
    bars = [{"t": dates[i], "h": round(highs[i], 2), "l": round(lows[i], 2)}
            for i in range(b0, n)]
    return {"prediction": prediction, "completed": completed,
            "label": d["label"], "kind": d["kind"], "bars": bars}
# * zone_s uses symmetry as a confluence-tightness proxy until Ramana's exact
#   legs-1-2/3-4 Fib overlay is wired (open item).


# --------------------------------------------------------------------------- #
# Wolfe SCANNER — the OOS-validated reachable-EPA winner-profile (2026-06-25)   #
#   Phase-1 backtest + walk-forward: the RAW lens has no edge, but selecting    #
#   on reachable EPA (D<=1) + strong point-1 (p1>=2) + not-narrowest zone       #
#   (F<=2) is a robust two-sided BETA-NEUTRAL edge (median +2.4% net; bears     #
#   +1.1% median, positive across all 3 eras). This is the OPPOSITE of ranking  #
#   by the §B total — descriptive scanner feed, surfaced at /dash/wolfe/scan.   #
# --------------------------------------------------------------------------- #
def is_winner_profile(score):
    """The validated edge filter: reachable EPA + strong point-1 + not-narrowest zone."""
    return bool(score) and score.get("D", 9) <= 1 and score.get("p1", 0) >= 2 and score.get("F", 9) <= 2


def t1_confluence(p, direction, tol=0.02):
    """T1 partial target = leg-1-2's 0.618 ∩ leg-3-4's 0.618 (None if they don't converge)."""
    bull = direction == "BULL"
    a, b, c, d = p[0].price, p[1].price, p[2].price, p[3].price
    if bull:
        l12, l34 = max(a, b) - 0.618 * abs(b - a), max(c, d) - 0.618 * abs(d - c)
    else:
        l12, l34 = min(a, b) + 0.618 * abs(b - a), min(c, d) + 0.618 * abs(d - c)
    mid = (l12 + l34) / 2.0
    return mid if mid and abs(l12 - l34) / abs(mid) <= tol else None


def scan_universe(conn, universe="nifty500"):
    """Resolve a scan universe to its symbol list. 'nifty500' = the latest membership
    snapshot · 'inclusive' = top-liquid incl. delisted · else a comma list of symbols."""
    if universe == "nifty500":
        return [r[0] for r in conn.execute(
            """SELECT symbol FROM stock_index_membership WHERE index_name='Nifty 500'
               AND snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name='Nifty 500')
               ORDER BY symbol""").fetchall()]
    if universe == "inclusive":
        return [r[0] for r in conn.execute(
            """SELECT symbol FROM bhavcopy_rows WHERE series='EQ' AND (segment='CM' OR segment IS NULL) AND value>0
               GROUP BY symbol HAVING COUNT(*)>=500 ORDER BY AVG(value) DESC LIMIT 300""").fetchall()]
    return [s.strip().upper() for s in str(universe).split(",") if s.strip()]


def winner_scan(conn, universe="nifty500", fresh=15, asof=None):
    """FRESH winner-profile Wolfe setups across a universe — the scanner feed. Each item:
    sym/dir/cmp/zone/sl/t1/epa/up%/age/in_zone/dates, actionable-first then freshest. PIT
    via `asof` (bars <= as-of; the fractal/point-5 design is naturally point-in-time)."""
    import bisect
    out = []
    for sym in scan_universe(conn, universe):
        s = stock_series(conn, sym)
        if not s:
            continue
        dates, _o, highs, lows, closes = s
        if asof:
            k = bisect.bisect_right(dates, asof)
            if k < 60:
                continue
            dates, highs, lows, closes = dates[:k], highs[:k], lows[:k], closes[:k]
        n = len(closes)
        cmp_ = closes[-1]
        waves, _ = detect_waves(highs, lows, closes)
        for w in waves:
            if w.state != "CONFIRMED" or not w.p5 or not is_winner_profile(w.score):
                continue
            age = n - 1 - w.p5.idx
            if age > fresh:
                continue
            _e12, _e34, zones = fib_zones(w.p[0].price, w.p[1].price, w.p[2].price, w.p[3].price, direction=w.direction)
            if not zones:
                continue
            bull = w.direction == "BULL"
            z = sorted(zones, key=lambda zz: (-zz["price"] if bull else zz["price"]))[0]
            sl = z["low"] * 0.997 if bull else z["high"] * 1.003
            t1 = t1_confluence(w.p, w.direction)
            epa = w.p[0].price + w.epa_slope * (n - 1 - w.p[0].idx)
            up = abs(epa - z["price"]) / z["price"] * 100.0 if z["price"] else 0.0
            out.append({
                "sym": sym, "dir": w.direction, "cmp": round(cmp_, 1),
                "zlo": round(z["low"], 1), "zhi": round(z["high"], 1), "zprice": round(z["price"], 1),
                "sl": round(sl, 1), "t1": (round(t1, 1) if t1 else None), "epa": round(epa, 1),
                "up": round(up, 1), "age": age, "Q": w.score["total"],
                "in_zone": bool(z["low"] * 0.995 <= cmp_ <= z["high"] * 1.005),
                "p5date": dates[w.p5.idx], "p4date": dates[w.p[3].idx]})
    out.sort(key=lambda r: (not r["in_zone"], r["age"]))
    return out


# --------------------------------------------------------------------------- #
# PERSISTED scan — nightly-materialise winner_scan() so /dash/wolfe/scan is     #
# instant (the live scan is ~30s over the universe) and strategy_registry can   #
# give Wolfe a real count/as_of/top. wolfe.py OWNS this table (CREATE IF NOT    #
# EXISTS here — db.py is NOT touched, per the lens's isolation design).         #
# Descriptive feed — persisting the scan changes nothing about the no-buy/sell  #
# stance; it just caches what the live scanner already shows.                   #
# --------------------------------------------------------------------------- #
_SCAN_COLS = ("sym", "dir", "cmp", "zlo", "zhi", "zprice", "sl", "t1", "epa",
              "up", "age", "Q", "in_zone", "p5date", "p4date")


def _ensure_scan_table(conn):
    # Autoincrement id (NOT a natural composite key) so the persisted snapshot is a
    # faithful 1:1 of winner_scan's output — clean-snapshot semantics come from the
    # DELETE-by-universe in persist_scan, so a composite PK would only silently collapse
    # distinct same-day setups and make the cached count drift below the live count.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wolfe_signals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            universe     TEXT NOT NULL,
            sym          TEXT NOT NULL,
            dir          TEXT NOT NULL,
            cmp          REAL,
            zlo          REAL,
            zhi          REAL,
            zprice       REAL,
            sl           REAL,
            t1           REAL,
            epa          REAL,
            up           REAL,
            age          INTEGER,
            q            INTEGER,
            in_zone      INTEGER,
            p5date       TEXT,
            p4date       TEXT,
            fresh        INTEGER,
            scan_date    TEXT,
            computed_at  TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wolfe_universe "
                 "ON wolfe_signals(universe, in_zone DESC, age ASC)")


def _scan_as_of(conn):
    """The data date the scan reflects (latest signals snapshot; bhav fallback)."""
    for sql in ("SELECT MAX(trade_date) FROM stock_signals",
                "SELECT MAX(date) FROM bhavcopy_rows"):
        try:
            r = conn.execute(sql).fetchone()
            if r and r[0]:
                return str(r[0])[:10]
        except Exception:
            continue
    return None


def persist_scan(conn, universe="nifty500", fresh=15, computed_at=None):
    """Materialise winner_scan(universe) into wolfe_signals as a clean snapshot
    (replace the prior rows for this universe). Returns (n_rows, scan_date).
    `computed_at` is passed in (callers stamp the wall-clock; this module avoids
    Date.now-style nondeterminism)."""
    _ensure_scan_table(conn)
    rows = winner_scan(conn, universe=universe, fresh=fresh)
    scan_date = _scan_as_of(conn)
    conn.execute("DELETE FROM wolfe_signals WHERE universe=?", (universe,))
    conn.executemany(
        "INSERT INTO wolfe_signals "
        "(universe,sym,dir,cmp,zlo,zhi,zprice,sl,t1,epa,up,age,q,in_zone,"
        " p5date,p4date,fresh,scan_date,computed_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(universe, r["sym"], r["dir"], r["cmp"], r["zlo"], r["zhi"], r["zprice"],
          r["sl"], r["t1"], r["epa"], r["up"], r["age"], r["Q"],
          1 if r["in_zone"] else 0, r["p5date"], r["p4date"], fresh,
          scan_date, computed_at) for r in rows])
    # CL-SCO-12: do NOT commit here. `conn` is always passed in by the caller (the
    # CLI uses `with get_conn()`, which commits on success / rolls back on error), so
    # an internal `try: conn.commit() except: pass` (a) committed a foreign connection
    # mid-transaction and (b) swallowed disk-full / database-locked errors, leaving the
    # DELETE-then-INSERT half-applied and silent. Let the owner commit and let errors
    # propagate so the replace stays atomic.
    return len(rows), scan_date


def latest_scan(conn, universe="nifty500"):
    """Read the persisted scan snapshot for a universe (instant). Returns
    {rows:[…same shape as winner_scan…], scan_date, computed_at, fresh} or None
    when the table is absent/empty (caller falls back to a live winner_scan)."""
    try:
        cur = conn.execute(
            "SELECT sym,dir,cmp,zlo,zhi,zprice,sl,t1,epa,up,age,q,in_zone,"
            "p5date,p4date,fresh,scan_date,computed_at "
            "FROM wolfe_signals WHERE universe=? "
            "ORDER BY in_zone DESC, age ASC", (universe,))
        recs = cur.fetchall()
    except Exception:
        return None
    if not recs:
        return None
    rows = [{"sym": r[0], "dir": r[1], "cmp": r[2], "zlo": r[3], "zhi": r[4],
             "zprice": r[5], "sl": r[6], "t1": r[7], "epa": r[8], "up": r[9],
             "age": r[10], "Q": r[11], "in_zone": bool(r[12]),
             "p5date": r[13], "p4date": r[14]} for r in recs]
    return {"rows": rows, "scan_date": recs[0][16], "computed_at": recs[0][17],
            "fresh": recs[0][15]}


def _cli():
    """Nightly entry: `python -m src.automation.wolfe --persist-scan`."""
    import argparse
    import datetime as _dt
    try:
        from src.core.db import get_conn
    except Exception:
        from core.db import get_conn  # type: ignore
    ap = argparse.ArgumentParser(description="Wolfe scanner — persist the winner-profile scan")
    ap.add_argument("--persist-scan", action="store_true", help="materialise winner_scan into wolfe_signals")
    ap.add_argument("--universe", default="nifty500", help="nifty500 | inclusive | sym,sym,…")
    ap.add_argument("--fresh", type=int, default=15, help="max age (bars) of a setup")
    args = ap.parse_args()
    if args.persist_scan:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_conn() as conn:
            n, scan_date = persist_scan(conn, universe=args.universe, fresh=args.fresh, computed_at=stamp)
        print(f"persisted {n} winner-profile setups for {args.universe} (as-of {scan_date}, computed {stamp})")
    else:
        ap.print_help()


if __name__ == "__main__":
    _cli()
