"""STEP-1 SANDBOX — fractal-sourced Wolfe detection + the §B quality score.

Sources pivots from Williams fractals (Ramana's Fyers mechanism) instead of the
ATR-zigzag, so the waves base MISSES surface (his RELIANCE Nov-2022 wave + the
long-range screenshot waves), and ranks them by the locked §B points-sum. Every §A
geometry rule is reused unchanged (validators only).

READ-ONLY. Prod src/automation/wolfe.py ("base") is NOT mutated; we borrow its
validated helpers (_classify, _line, fib_zones, atr, Pivot, loaders).

DETECTION degrees = 2/5/10/20/30 (coarse needed to surface long waves).
QUALITY point-level caps at 10 (per Ramana: "no 20/30" — a d20/d30 pivot scores the
max level 3, same as a 10-fractal).

Run on the VPS (real bhav data):
    cd /opt/hermes && python3 research/wolfe_waves/fractal_proto.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))  # repo / app root

from src.automation import wolfe                          # noqa: E402
from src.automation.wolfe import Pivot, _classify, _line  # noqa: E402

DETECT_DEGREES = (2, 5, 10, 20, 30)   # find pivots at all scales (long waves need coarse)
SYM_LO, SYM_HI = 0.2, 1.0             # §A distance rule (floor dropped 0.5→0.2 per Ramana)


# --------------------------------------------------------------------------- #
# fractals                                                                     #
# --------------------------------------------------------------------------- #
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


def lvl(deg):
    """Fractal degree → quality level: candle 0 · 2-fr 1 · 5-fr 2 · 10-fr 3."""
    return {0: 0, 2: 1, 5: 2, 10: 3}.get(deg, 3)


def rsi(closes, period=14):
    """Wilder RSI."""
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


# --------------------------------------------------------------------------- #
# point 5 + breach (LOCKED §A4 behaviour)                                      #
# --------------------------------------------------------------------------- #
def find_p5(highs, lows, a, c, d, direction, n):
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
    end_b = p5.idx if p5 else n - 1
    for t in range(d.idx + 1, end_b + 1):
        if direction == 'BULL' and highs[t] > d.price:
            return True
        if direction == 'BEAR' and lows[t] < d.price:
            return True
    return False


# --------------------------------------------------------------------------- #
# §B quality score (plain points sum; point 1 separate + x2)                  #
# --------------------------------------------------------------------------- #
def score(w, highs, lows, closes, rsi_arr):
    a, b, c, d = w["p"]
    p5, direction = w["p5"], w["dir"]
    bull = direction == 'BULL'
    n = len(highs)
    A = lvl(frac_degree(highs, lows, a.idx, a.kind))                                   # 0-3
    B = max(1.0, (lvl(frac_degree(highs, lows, b.idx, b.kind))                         # 1-3 (floored)
                  + lvl(frac_degree(highs, lows, c.idx, c.kind))
                  + lvl(frac_degree(highs, lows, d.idx, d.kind))) / 3.0)
    _e12, _e34, zones = wolfe.fib_zones(a.price, b.price, c.price, d.price,
                                        direction=direction, tol_frac=0.02)
    C = F = D = 0
    G = 1
    entry = p5.price if p5 else d.price                    # default; refined to the zone below
    if zones:
        z = min(zones, key=lambda zz: abs(entry - zz["price"]))
        lo, hi = min(z["low"], z["high"]), max(z["low"], z["high"])
        gap = (hi - lo) / z["price"] * 100.0 if z["price"] else 99
        F = 3 if gap <= 0.6 else 2 if gap <= 1.2 else 1 if gap <= 2.0 else 0           # 1-3
        G = 2 if (z["r12"] == 4.618 or z["r34"] == 4.618) else 1                       # 1-2 (Ramana-locked)
        if p5:
            if lo <= p5.price <= hi:                       # clean land INSIDE the zone band
                dist = abs(p5.price - z["price"]) / p5.price * 100.0
                C = 3 if dist <= 0.1 else 2 if dist <= 0.5 else 1 if dist <= 1.5 else 0
                entry = z["price"]
            else:                                          # pierced beyond the band
                depth = (lo - p5.price) if bull else (p5.price - hi)
                depth_pct = depth / z["price"] * 100.0 if z["price"] else 99
                # returned into the band after the overshoot? PIT: bars <= end only;
                # zone fixed by the structure (no future zone-shopping).
                ret = any((closes[t] >= lo) if bull else (closes[t] <= hi)
                          for t in range(p5.idx + 1, n))
                if 0 < depth_pct <= 1.5 and ret:           # pierce-and-RETURN: a notch below clean
                    C = 2
                    entry = lo if bull else hi
                else:                                      # deep break, or not (yet) returned
                    C = 0
    if p5:                                                 # D = tradeable upside from ENTRY (not the spike)
        s14 = _line(a, d)
        tgt = a.price + s14 * (p5.idx - a.idx)
        up = abs(tgt - entry) / entry * 100.0 if entry else 0.0
        D = 0 if up < 10 else 1 if up < 20 else 2 if up < 35 else 3                    # 0-3
    s14 = _line(a, d)                                       # H = wedge-rail (1-4 line) adherence, legs 1-2 & 2-3
    touches = 0
    for t in range(a.idx + 1, c.idx):
        ln = a.price + s14 * (t - a.idx)
        if ln > 0 and (abs(highs[t] - ln) / ln <= 0.001 or abs(lows[t] - ln) / ln <= 0.001):
            touches += 1
    H = 0 if touches == 0 else 1 if touches < 3 else 2                                 # 0-2
    I = 0                                                   # RSI divergence: SHIFTED point 5 vs the INITIAL
    if p5 and rsi_arr[p5.idx] is not None:                  # point-5 TROUGH it undercut (panel-resolved)
        s13 = _line(a, c)
        init = init_ext = None                              # DEEPEST prior overshoot >=5 bars before p5
        for t in range(d.idx + 1, max(d.idx + 2, p5.idx - 4)):
            rail = a.price + s13 * (t - a.idx)
            if bull and lows[t] < c.price and lows[t] < rail and (init_ext is None or lows[t] < init_ext):
                init_ext, init = lows[t], t
            elif (not bull) and highs[t] > c.price and highs[t] > rail and (init_ext is None or highs[t] > init_ext):
                init_ext, init = highs[t], t
        if init is not None and rsi_arr[init] is not None:
            depth = (lows[init] - p5.price) / lows[init] if bull else (p5.price - highs[init]) / highs[init]
            if depth >= 0.01:                               # min depth ~1% (kill marginal/adjacent false +2)
                if bull and rsi_arr[p5.idx] > rsi_arr[init]:
                    I = 2
                elif (not bull) and rsi_arr[p5.idx] < rsi_arr[init]:
                    I = 2
        # (point-3 fallback dropped — fired on the RSI base-rate; skeptic + Ramana-proxy)
    total = A * 2 + B + C + F + G + H + I + D
    return {"p1": A, "B": round(B, 2), "C": C, "F": F, "G": G, "H": H, "I": I, "D": D,
            "total": round(total, 2)}


# --------------------------------------------------------------------------- #
# detection                                                                    #
# --------------------------------------------------------------------------- #
def detect(highs, lows, closes, asof_idx=None):
    if asof_idx is not None:
        highs, lows, closes = highs[:asof_idx + 1], lows[:asof_idx + 1], closes[:asof_idx + 1]
    n = len(closes)
    rsi_arr = rsi(closes)
    best = {}
    for N in DETECT_DEGREES:
        piv = wolfe.fractal_pivots(highs, lows, periods=(N,))
        for i in range(len(piv) - 3):
            a, b, c, d = piv[i], piv[i + 1], piv[i + 2], piv[i + 3]
            direction = _classify(a, b, c, d, SYM_LO, SYM_HI)
            if not direction:
                continue
            p5 = find_p5(highs, lows, a, c, d, direction, n)
            if breached(highs, lows, d, p5, direction, n):
                continue
            w = {"degree": N, "dir": direction, "p": [a, b, c, d], "p5": p5, "span": d.idx - a.idx}
            w["score"] = score(w, highs, lows, closes, rsi_arr)
            key = (direction, a.idx, d.idx)               # same endpoints → keep the HIGHER-quality one
            if key not in best or w["score"]["total"] > best[key]["score"]["total"]:
                best[key] = w
    out = sorted(best.values(), key=lambda w: -w["score"]["total"])
    return out


# --------------------------------------------------------------------------- #
# validation                                                                   #
# --------------------------------------------------------------------------- #
def _show(w, dates):
    p = w["p"]
    pts = " ".join("%d:%s@%.0f" % (j + 1, dates[q.idx][2:], q.price) for j, q in enumerate(p))
    p5 = (" 5:%s@%.0f" % (dates[w["p5"].idx][2:], w["p5"].price)) if w["p5"] else " 5:forming"
    s = w["score"]
    sb = "p1=%d B=%.1f C=%d F=%d G=%d H=%d I=%d D=%d" % (s["p1"], s["B"], s["C"], s["F"], s["G"], s["H"], s["I"], s["D"])
    return "Q%5.1f [%s d%d sp%d] %s%s  {%s}" % (s["total"], w["dir"], w["degree"], w["span"], pts, p5, sb)


def main():
    from src.core.db import get_conn
    with get_conn() as conn:
        for sym in ("RELIANCE", "PARAS"):
            s = wolfe.stock_series(conn, sym)
            if not s:
                print(sym, "-> no data"); continue
            dates, opens, highs, lows, closes = s
            waves = detect(highs, lows, closes)
            print("\n================= %s (n=%d) — TOP 8 by quality =================" % (sym, len(dates)))
            for w in waves[:8]:
                print("  " + _show(w, dates))
            if sym == "RELIANCE":
                hit = [w for w in waves if "2022-11-2" in dates[w["p"][0].idx] and "2023-01-1" in dates[w["p"][3].idx]]
                rank = (waves.index(hit[0]) + 1) if hit else None
                print("\n  -- your Nov-2022 wave (rank %s of %d) --" % (rank, len(waves)))
                for w in hit:
                    print("  " + _show(w, dates))
                longs = [w for w in waves if w["span"] > 90 and w["p"][3].idx > len(dates) - 400]
                print("\n  -- recent long-range (>90 bar) waves --")
                for w in sorted(longs, key=lambda w: -w["p"][3].idx)[:4]:
                    print("  " + _show(w, dates))


if __name__ == "__main__":
    main()
