"""Harmonic XABCD pattern detector (D72 — the harmonic lane, sibling to wolfe.py).

Reuses the Wolfe engine's pivot machinery (ATR-zigzag + split-adjusted series) — see
`docs/chart-redesign-design.md` §13 (the capability audit: ~60-70% of the infra already
exists in wolfe.py). This module adds the harmonic XABCD ratio-template library + a
per-type validator + the forming-pattern PRZ (potential reversal zone) projection.

A harmonic pattern is five swing points X-A-B-C-D whose Fibonacci leg ratios match a
named template:
    AB = |B-A| / |A-X|     (B retraces the XA leg)
    BC = |C-B| / |B-A|     (C retraces the AB leg)
    CD = |D-C| / |C-B|     (D extends the BC leg)
    AD = |D-A| / |A-X|     (the DEFINING ratio — where D sits vs the XA leg)
Direction is read off D: a pattern whose D is a swing LOW reverses UP (bullish), a D that
is a swing HIGH reverses DOWN (bearish).

DESCRIPTIVE-ONLY. Detection is the cheap part; whether any pattern×timeframe carries a
real forward edge on our universe is decided by `harmonic_backtest.py` BEFORE anything
here is surfaced as a signal (Ramana's principle: don't dress research as product).

Scope (v1): the five well-agreed templates — Gartley · Bat · Butterfly · Crab · Deep
Crab. Cypher / Shark / Three-Drives use different leg references (XC, 0-X-A-B-C, three
symmetric drives) whose published ratios vary by source — deferred until pinned, rather
than encode a dubious template that would poison the backtest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

try:
    from src.automation.wolfe import Pivot, atr, zigzag, fractal_pivots, stock_series, rsi
except Exception:  # pragma: no cover - import-path fallback
    from automation.wolfe import Pivot, atr, zigzag, fractal_pivots, stock_series, rsi  # type: ignore


# --------------------------------------------------------------------------- #
# Ratio-template library — (lo, hi) acceptance band + `ideal` for scoring.      #
# AB/CD/AD are the discriminating legs; BC is a wide common range (low weight). #
# --------------------------------------------------------------------------- #
@dataclass
class _Tpl:
    ab: tuple
    bc: tuple
    cd: tuple
    ad: tuple
    ab_i: float
    cd_i: float
    ad_i: float


HARMONICS = {
    # name        AB band        BC band         CD band        AD band       ab_i   cd_i   ad_i
    "Gartley":   _Tpl((0.55, 0.66), (0.382, 0.886), (1.13, 1.618), (0.74, 0.83), 0.618, 1.27, 0.786),
    "Bat":       _Tpl((0.382, 0.50), (0.382, 0.886), (1.50, 2.618), (0.85, 0.92), 0.45, 2.0, 0.886),
    "Butterfly": _Tpl((0.74, 0.83), (0.382, 0.886), (1.50, 2.24), (1.20, 1.70), 0.786, 1.80, 1.27),
    "Crab":      _Tpl((0.382, 0.618), (0.382, 0.886), (2.0, 3.80), (1.55, 1.70), 0.50, 3.0, 1.618),
    "DeepCrab":  _Tpl((0.85, 0.92), (0.382, 0.886), (2.0, 3.80), (1.55, 1.70), 0.886, 3.0, 1.618),
}

_FIB_CD = {"Gartley": 1.27, "Bat": 1.618, "Butterfly": 1.618, "Crab": 2.618, "DeepCrab": 2.24}


@dataclass
class Harmonic:
    name: str
    direction: str            # 'BULL' | 'BEAR'
    state: str                # 'CONFIRMED' | 'FORMING'
    points: list              # [(label, idx, price, date)] X..D  (D absent when forming)
    ratios: dict              # {ab,bc,cd,ad}
    score: float              # 0-1 fit quality (closeness to ideal ratios)
    prz: dict = field(default_factory=dict)   # forming: {lo,hi,mid,templates:[…]}
    rsi_d: float | None = None


def _ratios(X, A, B, C, D):
    xa = abs(A.price - X.price)
    ab = abs(B.price - A.price)
    bc = abs(C.price - B.price)
    cd = abs(D.price - C.price)
    if xa <= 0 or ab <= 0 or bc <= 0:
        return None
    return {"ab": ab / xa, "bc": bc / ab, "cd": cd / bc, "ad": abs(D.price - A.price) / xa}


def _in(v, band):
    return band[0] <= v <= band[1]


def _score(r, t: _Tpl):
    """Mean closeness to the ideal AB/CD/AD (1.0 = bullseye, 0 = at a band edge)."""
    def close(v, ideal, band):
        half = max(abs(band[1] - band[0]) / 2.0, 1e-9)
        return max(0.0, 1.0 - abs(v - ideal) / half)
    return round((close(r["ab"], t.ab_i, t.ab)
                  + close(r["cd"], t.cd_i, t.cd)
                  + close(r["ad"], t.ad_i, t.ad)) / 3.0, 3)


def _structure_ok(X, A, B, C, D):
    """Alternation + the monotonic frame (B is a real XA retrace; C between; D the turn)."""
    kinds = (X.kind, A.kind, B.kind, C.kind, D.kind)
    if kinds not in (("L", "H", "L", "H", "L"), ("H", "L", "H", "L", "H")):
        return False
    bull = D.kind == "L"          # D a low ⇒ reverses up
    if bull:
        # X low < A high ; B above X (a retrace, not a break) ; C below A ; D below C
        return X.price < A.price and B.price > X.price and C.price < A.price and D.price < C.price
    return X.price > A.price and B.price < X.price and C.price > A.price and D.price > C.price


def match_xabcd(X, A, B, C, D):
    """Return the best-fitting Harmonic for five pivots, or None."""
    if not _structure_ok(X, A, B, C, D):
        return None
    r = _ratios(X, A, B, C, D)
    if not r:
        return None
    best = None
    for name, t in HARMONICS.items():
        if _in(r["ab"], t.ab) and _in(r["bc"], t.bc) and _in(r["cd"], t.cd) and _in(r["ad"], t.ad):
            sc = _score(r, t)
            if best is None or sc > best[1]:
                best = (name, sc)
    if not best:
        return None
    return best  # (name, score)


def _project_forming(X, A, B, C):
    """X-A-B-C present, D not yet — project the PRZ (the cluster where D would complete a
    valid pattern). The 'catch it forming, down the stream' ask. Returns a list of one
    Harmonic per cluster (usually one) with state='FORMING'."""
    xa = abs(A.price - X.price)
    ab = abs(B.price - A.price)
    bc = abs(C.price - B.price)
    if xa <= 0 or ab <= 0 or bc <= 0:
        return []
    if C.kind not in ("H", "L"):
        return []
    bull = C.kind == "H"          # next pivot D is a LOW ⇒ bullish reversal
    sign = -1.0 if bull else 1.0
    ab_r = ab / xa
    # only templates whose AB the leg already satisfies can still complete
    cands = []
    for name, t in HARMONICS.items():
        if not _in(ab_r, t.ab):
            continue
        d_ad = A.price + sign * t.ad_i * xa          # D from the defining XA ratio
        d_cd = C.price + sign * _FIB_CD[name] * bc   # D from the BC extension
        cands.append((name, d_ad, d_cd))
    if not cands:
        return []
    # Codex D7-F4: the PRZ is the CONFLUENCE of BOTH projections — the defining XA/AD
    # ratio AND the BC/CD extension. Building it from d_ad (c[1]) alone discarded the CD
    # leg (c[2]) and rendered a too-narrow zone that hid the real two-projection spread.
    cands.sort(key=lambda c: c[1])
    levels = [c[1] for c in cands] + [c[2] for c in cands]   # AD- and CD-projected D levels
    lo, hi = min(levels), max(levels)
    mid = (lo + hi) / 2.0
    return [Harmonic(
        name="+".join(c[0] for c in cands),
        direction="BULL" if bull else "BEAR", state="FORMING",
        points=[("X", X.idx, X.price, None), ("A", A.idx, A.price, None),
                ("B", B.idx, B.price, None), ("C", C.idx, C.price, None)],
        ratios={"ab": round(ab_r, 3)}, score=0.0,
        prz={"lo": round(lo, 2), "hi": round(hi, 2), "mid": round(mid, 2),
             "templates": [c[0] for c in cands]})]


def _pivots(highs, lows, closes, method="zigzag", k=1.5):
    if method == "fractal":
        return fractal_pivots(highs, lows)
    return zigzag(highs, lows, atr(highs, lows, closes), k)


def _period_key(date_str, tf):
    """Bucket a YYYY-MM-DD date into an ISO-week ('w') or calendar-month ('m') key."""
    s = str(date_str)
    if tf == "m":
        return s[:7]
    # ISO week (no external deps): Thursday-of-week year + week number
    import datetime as _dt
    try:
        d = _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return s
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def resample_series(dates, opens, highs, lows, closes, tf):
    """Daily OHLC arrays -> weekly ('w') or monthly ('m') OHLC arrays (date = last bar
    in the bucket, so detection on the resampled series stays point-in-time). 'd' is a
    no-op. Pure; mirrors the client D/W/M/Q resample so W/M harmonics line up on the chart."""
    if tf not in ("w", "m") or not dates:
        return dates, opens, highs, lows, closes
    rd, ro, rh, rl, rc = [], [], [], [], []
    key = None
    for i in range(len(dates)):
        k = _period_key(dates[i], tf)
        if k != key:
            key = k
            rd.append(dates[i]); ro.append(opens[i]); rh.append(highs[i]); rl.append(lows[i]); rc.append(closes[i])
        else:
            rh[-1] = max(rh[-1], highs[i]); rl[-1] = min(rl[-1], lows[i])
            rc[-1] = closes[i]; rd[-1] = dates[i]
    return rd, ro, rh, rl, rc


def detect_from_series(dates, opens, highs, lows, closes,
                       method="zigzag", k=1.5, forming=True, max_age=None):
    """All harmonic patterns in a price series. CONFIRMED = five locked pivots; FORMING =
    last four pivots + a projected PRZ. `max_age` (bars since D / since C) prunes to recent
    setups. Point-in-time by construction: a zigzag pivot only confirms after the reversal,
    so no look-ahead is introduced beyond what the pivot detector already needs."""
    n = len(closes)
    piv = _pivots(highs, lows, closes, method=method, k=k)
    out = []
    rsi_arr = rsi(closes)
    for i in range(len(piv) - 4):
        X, A, B, C, D = piv[i:i + 5]
        m = match_xabcd(X, A, B, C, D)
        if not m:
            continue
        name, sc = m
        if max_age is not None and (n - 1 - D.idx) > max_age:
            continue
        r = _ratios(X, A, B, C, D)
        out.append(Harmonic(
            name=name, direction=("BULL" if D.kind == "L" else "BEAR"), state="CONFIRMED",
            points=[("X", X.idx, round(X.price, 2), dates[X.idx]),
                    ("A", A.idx, round(A.price, 2), dates[A.idx]),
                    ("B", B.idx, round(B.price, 2), dates[B.idx]),
                    ("C", C.idx, round(C.price, 2), dates[C.idx]),
                    ("D", D.idx, round(D.price, 2), dates[D.idx])],
            ratios={k2: round(v, 3) for k2, v in r.items()}, score=sc,
            rsi_d=(round(rsi_arr[D.idx], 1) if D.idx < len(rsi_arr) and rsi_arr[D.idx] is not None else None)))
    if forming and len(piv) >= 4:
        # CL-RS-05: an in-progress X-A-B-C can sit one (or two) pivots back from the
        # very last pivot — the old code only ever projected piv[-4:], so a pattern
        # whose C is the second-to-last pivot was never caught forming. Scan the last
        # few trailing 4-pivot windows; the C pivot (window[-1]) is the recency anchor
        # for max_age, and dedup identical PRZ projections.
        _FORMING_WINDOWS = 3
        seen = set()
        for w in range(1, min(_FORMING_WINDOWS, len(piv) - 3) + 1):
            window = piv[-3 - w:len(piv) - w + 1] if w > 1 else piv[-4:]
            c_piv = window[-1]
            if max_age is not None and (n - 1 - c_piv.idx) > max_age:
                continue
            for f in _project_forming(*window):
                key = (f.name, c_piv.idx, f.prz["mid"] if f.prz else None)
                if key in seen:
                    continue
                seen.add(key)
                out.append(f)
    return out


def detect(conn, sym, tf="d", **kw):
    """Detect harmonics for a symbol on the chosen timeframe. tf='w'/'m' resamples the
    daily series to weekly/monthly bars first (the multi-TF detection hand-off), so the
    chart's W/M interval shows W/M harmonics rather than re-snapped daily ones."""
    s = stock_series(conn, sym)
    if not s:
        return []
    if tf in ("w", "m"):
        s = resample_series(*s, tf)
    return detect_from_series(*s, **kw)


# --------------------------------------------------------------------------- #
# selftest — `python -m src.automation.harmonic_patterns`                       #
# --------------------------------------------------------------------------- #
def _selftest():
    # a textbook BULLISH Gartley (D a low, reverses up)
    X = Pivot(0, 100.0, "L"); A = Pivot(10, 200.0, "H")          # XA = 100
    B = Pivot(20, 200 - 0.618 * 100, "L")                        # AB = 0.618
    C = Pivot(30, B.price + 0.60 * (A.price - B.price), "H")     # BC = 0.60 of AB
    D = Pivot(40, 200 - 0.786 * 100, "L")                        # AD = 0.786
    m = match_xabcd(X, A, B, C, D)
    assert m and m[0] == "Gartley", f"expected Gartley, got {m}"
    print(f"OK  bullish Gartley matched (score {m[1]})")

    # a BEARISH Crab (D a high, deep 1.618 extension) — ratios kept mutually consistent
    # (AB=0.50, BC=0.886 ⇒ CD≈3.5, inside the Crab CD band; AD=1.618).
    X2 = Pivot(0, 200.0, "H"); A2 = Pivot(10, 100.0, "L")        # XA = 100
    B2 = Pivot(20, 100 + 0.50 * 100, "H")                        # AB = 0.50
    C2 = Pivot(30, B2.price - 0.886 * (B2.price - A2.price), "L")  # BC = 0.886
    D2 = Pivot(40, 100 + 1.618 * 100, "H")                       # AD = 1.618
    m2 = match_xabcd(X2, A2, B2, C2, D2)
    assert m2 and m2[0] == "Crab", f"expected Crab, got {m2}"
    print(f"OK  bearish Crab matched (score {m2[1]})")

    # random non-harmonic geometry must NOT match
    R = [Pivot(0, 100, "L"), Pivot(5, 130, "H"), Pivot(9, 80, "L"), Pivot(14, 250, "H"), Pivot(20, 60, "L")]
    assert match_xabcd(*R) is None, "false-positive on noise"
    print("OK  noise rejected")

    # forming projection: X-A-B-C of the Gartley → a PRZ around the 0.786 D (121.4)
    fs = _project_forming(X, A, B, C)
    assert fs and fs[0].state == "FORMING" and fs[0].prz["lo"] <= 130, f"bad PRZ {fs}"
    print(f"OK  forming PRZ projected: {fs[0].prz}")
    print("ALL PASS")


if __name__ == "__main__":
    _selftest()
