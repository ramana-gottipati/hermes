"""Point-5 confluence engine — a mechanical proxy of Ramana's Fib method.

Extends the two thrust legs 1-2 and 3-4 with Fibonacci ratios; clusters levels
where a ratio from leg 1-2 lands within tolerance of a ratio from leg 3-4 ->
matched-ratio bands. Tightness is measured in ATR (the chosen "narrow" unit).
This exists in research only (Phase 0) so the backtest can locate a point-5 zone;
production P2 will own the live version. Pure stdlib.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RATIOS_FULL = (1.272, 1.414, 1.618, 2.0, 2.618)
RATIOS_CORE = (1.272, 1.618, 2.0)
RATIOS_DEEP = (1.618, 2.0, 2.618)


def fib_levels(a_price, b_price, ratios):
    """Extension levels projected beyond leg A->B in its own direction."""
    return {r: b_price + (r - 1.0) * (b_price - a_price) for r in ratios}


def matched_bands(wave, atr, ratios=RATIOS_FULL, cluster_tol_atr=0.75):
    """Bands where >=1 leg-1-2 level and >=1 leg-3-4 level cluster within tol."""
    if not atr or atr <= 0:
        return []
    l12 = fib_levels(wave.p1.price, wave.p2.price, ratios)
    l34 = fib_levels(wave.p3.price, wave.p4.price, ratios)
    pts = [(p, '12', r) for r, p in l12.items()] + [(p, '34', r) for r, p in l34.items()]
    pts.sort()
    tol = cluster_tol_atr * atr
    bands = []
    used = [False] * len(pts)
    for i in range(len(pts)):
        if used[i]:
            continue
        grp = [pts[i]]
        used[i] = True
        for j in range(i + 1, len(pts)):
            if used[j]:
                continue
            if pts[j][0] - grp[-1][0] <= tol:
                grp.append(pts[j])
                used[j] = True
            else:
                break
        legs = {g[1] for g in grp}
        if '12' in legs and '34' in legs:
            lo = min(g[0] for g in grp)
            hi = max(g[0] for g in grp)
            bands.append({
                "low": lo, "high": hi,
                "tightness_atr": (hi - lo) / atr,
                "ratios": sorted({(g[1], g[2]) for g in grp}, key=lambda x: (x[0], x[1])),
            })
    return bands


def high_prob_band(wave, atr, ratios=RATIOS_FULL, cluster_tol_atr=0.75, narrow_atr=0.5):
    """The narrowest matched band beyond point 4 in the thrust direction."""
    bands = matched_bands(wave, atr, ratios, cluster_tol_atr)
    if not bands:
        return None
    if wave.direction == 'BULL':
        cand = [b for b in bands if b["high"] <= wave.p4.price]
    else:
        cand = [b for b in bands if b["low"] >= wave.p4.price]
    cand = cand or bands
    cand.sort(key=lambda b: b["tightness_atr"])
    best = dict(cand[0])
    best["narrow"] = best["tightness_atr"] <= narrow_atr
    return best
