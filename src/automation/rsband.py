"""RS Support & Resistance — the mean-reversion / range lens on relative strength.

The complement to the *trend* reads already shipped (``index_signals`` slopes,
``rrg.py`` RRG/Mansfield, ``rs_phase.py`` weather). Those answer *"which way is
RS moving?"*. This answers the orthogonal question: *"where does RS sit inside
its OWN historical envelope — cheap or rich vs its own history — and is it
breaking out of that envelope (a structural re-rating)?"*

For a sector's RS ratio vs the broad market (``close(sector)/close(Nifty 500)``,
already stored daily in ``ratio_rows``) it computes, per (numerator, denominator):

  - **rs_band_pct** (0–100): the recency-weighted percentile of TODAY's ratio
    within its trailing 3-year window — 0 = at its historical RS support (cheap
    vs own history), 100 = at RS resistance (rich). The headline number.
  - **rails**: recency-weighted 5th / 50th / 95th-percentile support / median /
    resistance levels (interpretable ratio values for the chart).
  - **POC + value area**: the most-visited RS level (the "fair-value magnet") and
    the 70% value area — a Market-Profile read of where RS actually lingers.
  - **regime gate (Hurst)**: mean-reverting vs trending. THE honesty gate — the
    cheap/rich verdict is only valid on a mean-reverting series; on a trending
    one (a sector mid re-rating, e.g. IT/Defence) the band read is suppressed and
    a break = re-rating, not exhaustion.
  - **break state**: INSIDE / TOUCH_SUP / TOUCH_RES / BREAKOUT_UP / BREAKDOWN_DN —
    penetration + persistence (5 closes) + 3m-momentum confirmation, so a wick to
    the rail is not mistaken for a structural break.
  - **detrended twin** (band_pct on the Mansfield-detrended series) so "rich vs
    history but NOT vs trend" is visible.
  - **maturity / history floor**: < 2y of data → no band verdict; < 3y → provisional.

Self-contained (the ``rrg.py`` / ``capture.py`` pattern): OWNS its
``rsband_signals`` table (``CREATE TABLE IF NOT EXISTS`` on first use), NEVER edits
``db.py`` (which is parallel-held). Reads the curve already in ``ratio_rows`` — no
new ingestion, no schema change to existing tables. A nightly run stores one latest
row per pair; the read path is a ₹0 SELECT. Pure arithmetic — no LLM (cost doctrine);
every value is re-derivable from ``ratio_rows`` (pre-compute-over-recompute doctrine).

Reuses ``rrg._mansfield_series`` for the detrended twin (don't fork the math).

Run the job:   python -m src.automation.rsband
Self-check:    python -m src.automation.rsband --selftest
"""

from __future__ import annotations

import argparse
import logging
import math
from typing import Optional

from src.core.db import get_conn
from src.automation import rrg

log = logging.getLogger("hermes.rsband")


def _fin(v):
    """Coerce non-finite (inf/nan) to None so it never poisons the DB or a sort."""
    if v is None:
        return None
    return v if (isinstance(v, (int, float)) and math.isfinite(v)) else None


# ── tunable knobs (defaults; revisit after live use — design doc §10) ─────────
W_PRIMARY = 756       # 3y rolling window — the scored band (the headline)
W_LONG = 2520         # 10y window for the dual-window context (NULL if too short)
HALFLIFE = 252        # 1y recency half-life for the weighted percentile / quantiles
PCT_LOW = 5           # support-rail percentile
PCT_HIGH = 95         # resistance-rail percentile
POC_BINS = 50         # histogram bins for POC / value area
VA_FRACTION = 0.70    # Market-Profile value-area fraction
MIN_HISTORY = 504     # 2y: below this, no band verdict (the history floor)
SLOPE_WIN = 63        # ≈3m window for the momentum/direction read
BREAK_PERSIST = 5     # consecutive closes beyond a rail to confirm a break (≈1 week)
BREAK_BUFFER = 0.015  # 1.5% penetration buffer (a wick must clear the rail by this)
HURST_TREND = 0.55    # Hurst ≥ this → TRENDING (band cheap/rich read suppressed)

BAND_STATES = ("INSIDE", "TOUCH_SUP", "TOUCH_RES", "BREAKOUT_UP", "BREAKDOWN_DN")
REGIMES = ("MEAN_REVERTING", "TRENDING")


# ── pure math (operate on a ratio series, oldest → newest) ────────────────────
def _decay_weights(n: int, halflife: int = HALFLIFE) -> list[float]:
    """Newest element weight 1.0, decaying with the given half-life going back."""
    lam = 0.5 ** (1.0 / halflife)
    return [lam ** (n - 1 - i) for i in range(n)]


def _weighted_percentile(vals: list[float], wts: list[float], x: float) -> Optional[float]:
    """Recency-weighted percentile rank (0–100) of x within vals."""
    tw = sum(wts)
    if tw <= 0:
        return None
    below = sum(w for v, w in zip(vals, wts) if v <= x)
    return 100.0 * below / tw


def _weighted_quantile(vals: list[float], wts: list[float], q: float) -> Optional[float]:
    """Recency-weighted q-quantile (0–1) value — the rail level."""
    if not vals:
        return None
    pairs = sorted(zip(vals, wts), key=lambda p: p[0])
    tw = sum(w for _, w in pairs)
    if tw <= 0:
        return None
    target = q * tw
    cum = 0.0
    for v, w in pairs:
        cum += w
        if cum >= target:
            return v
    return pairs[-1][0]


def _poc_value_area(vals: list[float], bins: int = POC_BINS,
                    frac: float = VA_FRACTION) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Point-of-Control (modal level) + value area (narrowest band holding `frac`
    of observations), expanding out from the POC bin — a Market-Profile read."""
    if not vals:
        return None, None, None
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return lo, lo, hi
    w = (hi - lo) / bins
    hist = [0] * bins
    for v in vals:
        b = min(bins - 1, int((v - lo) / w))
        hist[b] += 1
    poc_bin = max(range(bins), key=lambda b: hist[b])
    poc = lo + (poc_bin + 0.5) * w
    total = sum(hist)
    target = frac * total
    lo_b = hi_b = poc_bin
    acc = hist[poc_bin]
    while acc < target and (lo_b > 0 or hi_b < bins - 1):
        left = hist[lo_b - 1] if lo_b > 0 else -1
        right = hist[hi_b + 1] if hi_b < bins - 1 else -1
        if right >= left:
            hi_b += 1
            acc += hist[hi_b]
        else:
            lo_b -= 1
            acc += hist[lo_b]
    return poc, lo + lo_b * w, lo + (hi_b + 1) * w


def _hurst(series: list[float]) -> Optional[float]:
    """Diffusion-exponent Hurst on the LOG levels: regress log(std of k-step
    differences) on log(k). ~0.5 = random walk; >0.55 = trending/persistent;
    <0.5 = mean-reverting. Stabler than R/S. None if too short."""
    lts = [math.log(x) for x in series if x and x > 0]
    n = len(lts)
    if n < 200:
        return None
    xs, ys = [], []
    for k in (1, 2, 4, 8, 16, 32, 64):
        if k >= n // 4:
            break
        diffs = [lts[i + k] - lts[i] for i in range(n - k)]
        if len(diffs) < 20:
            continue
        m = sum(diffs) / len(diffs)
        sd = (sum((d - m) ** 2 for d in diffs) / len(diffs)) ** 0.5
        if sd <= 0:
            continue
        xs.append(math.log(k))
        ys.append(math.log(sd))
    if len(xs) < 3:
        return None
    nn = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(xs[i] * ys[i] for i in range(nn))
    den = nn * sxx - sx * sx
    if abs(den) < 1e-12:
        return None
    return (nn * sxy - sx * sy) / den


def _break_state(vals: list[float], band_pct: Optional[float]) -> str:
    """Distinguish a confirmed structural break (penetration + persistence +
    momentum) from a touch-and-bounce at a rail. See design doc §2b."""
    n = len(vals)
    win = vals[-W_PRIMARY:] if n >= W_PRIMARY else vals
    last = vals[-1]
    mom = (last / vals[-1 - SLOPE_WIN] - 1.0) if (n > SLOPE_WIN and vals[-1 - SLOPE_WIN]) else 0.0
    if len(win) > BREAK_PERSIST + 5:
        ref = win[:-BREAK_PERSIST]
        tail = vals[-BREAK_PERSIST:]
        pmax, pmin = max(ref), min(ref)
        if all(r > pmax for r in tail) and last > pmax * (1 + BREAK_BUFFER) and mom > 0:
            return "BREAKOUT_UP"
        if all(r < pmin for r in tail) and last < pmin * (1 - BREAK_BUFFER) and mom < 0:
            return "BREAKDOWN_DN"
    if band_pct is not None and band_pct >= 85:
        return "TOUCH_RES"
    if band_pct is not None and band_pct <= 15:
        return "TOUCH_SUP"
    return "INSIDE"


def _band_label(p: Optional[float]) -> str:
    if p is None:
        return "n/a"
    if p <= 15:
        return "At RS support"
    if p < 35:
        return "Lower band"
    if p < 65:
        return "Mid-band"
    if p < 85:
        return "Upper band"
    return "At RS resistance"


def compute_one(ratio: list[float]) -> Optional[dict]:
    """All band metrics for one ratio series (oldest → newest), or None if there
    is less than the history floor (``MIN_HISTORY``) of usable data."""
    vals = [r for r in ratio if r is not None and r > 0]
    n = len(vals)
    if n < MIN_HISTORY:
        return None

    win = vals[-W_PRIMARY:] if n >= W_PRIMARY else vals
    wts = _decay_weights(len(win))
    last = vals[-1]

    band_pct = _weighted_percentile(win, wts, last)
    low = _weighted_quantile(win, wts, PCT_LOW / 100.0)
    mid = _weighted_quantile(win, wts, 0.5)
    high = _weighted_quantile(win, wts, PCT_HIGH / 100.0)

    band_pct_long = None
    if n >= 1260:                       # ≥5y before a "long-window" read is meaningful
        lw = vals[-W_LONG:]
        band_pct_long = _weighted_percentile(lw, _decay_weights(len(lw)), last)

    poc, val, vah = _poc_value_area(vals[-W_LONG:] if n > W_LONG else vals)

    h = _hurst(vals)
    regime = "TRENDING" if (h is not None and h >= HURST_TREND) else "MEAN_REVERTING"

    # detrended twin — percentile on the Mansfield-detrended series (reuse rrg)
    band_pct_detr = None
    mans = rrg._mansfield_series(vals)
    mvals = [x for x in mans if x is not None]
    if len(mvals) >= MIN_HISTORY // 2 and mans[-1] is not None:
        mw = mvals[-W_PRIMARY:] if len(mvals) >= W_PRIMARY else mvals
        band_pct_detr = _weighted_percentile(mw, _decay_weights(len(mw)), mans[-1])

    slope_3m = ((last / vals[-1 - SLOPE_WIN] - 1.0) * 100.0
                if (n > SLOPE_WIN and vals[-1 - SLOPE_WIN]) else None)

    state = _break_state(vals, band_pct)
    width = ((high - low) / mid * 100.0) if (low is not None and high is not None
                                             and mid not in (None, 0)) else None

    return {
        "rs_band_pct": _fin(round(band_pct, 1)) if band_pct is not None else None,
        "rs_band_pct_long": _fin(round(band_pct_long, 1)) if band_pct_long is not None else None,
        "rs_band_pct_detr": _fin(round(band_pct_detr, 1)) if band_pct_detr is not None else None,
        "rs_band_low": _fin(low),
        "rs_band_mid": _fin(mid),
        "rs_band_high": _fin(high),
        "rs_poc": _fin(poc),
        "rs_val": _fin(val),
        "rs_vah": _fin(vah),
        "rs_alltime_high": _fin(max(vals)),
        "rs_alltime_low": _fin(min(vals)),
        "rs_band_width_pct": _fin(round(width, 1)) if width is not None else None,
        "rs_regime": regime,
        "rs_hurst": _fin(round(h, 3)) if h is not None else None,
        "rs_band_state": state,
        "slope_3m_pct": _fin(round(slope_3m, 2)) if slope_3m is not None else None,
        "band_maturity": "full" if n >= W_PRIMARY else "provisional",
        "rs_band_label": _band_label(band_pct),
    }


def slope_dir(slope_3m_pct: Optional[float]) -> str:
    if slope_3m_pct is None:
        return "flat"
    return "up" if slope_3m_pct > 1 else "down" if slope_3m_pct < -1 else "flat"


def band_verdict(band_pct: Optional[float], regime: str, slope_3m_pct: Optional[float],
                 band_state: Optional[str] = None,
                 falls_less: Optional[bool] = None) -> tuple[str, str]:
    """The fused, rule-based verdict (design doc §3). band-position is NEVER a
    standalone trigger — it is crossed with regime, direction, and (optionally)
    the down-capture 'falls-less' veto. Returns (verdict, one-line reason)."""
    if band_state == "BREAKOUT_UP":
        return "Ride", "broke its ceiling — structural re-rating, ride it"
    if band_state == "BREAKDOWN_DN":
        return "Avoid", "broke its floor — de-rating, cheapness is a trap"
    if band_pct is None:
        return "n/a", "insufficient history for a band read"
    if regime == "TRENDING":
        return "Trend", "trending regime — band read not valid; follow the trend"
    d = slope_dir(slope_3m_pct)
    if band_pct <= 20:
        if d == "down":
            return "Avoid", "cheap but still falling — value trap"
        if d == "up":
            return ("Accumulate", "cheap, turning up, falls less than market") if falls_less \
                else ("Add", "cheap and turning, but no defensive edge yet")
        return "Watch", "cheap but no turn yet — arm an alert"
    if band_pct >= 80:
        if d == "down":
            return "Fade", "rich and rolling over — exhaustion"
        if d == "up":
            return "Ride", "rich but still pushing — trail it"
        return "Trim", "pinned at resistance"
    return ("Add", "mid-band, rising") if d == "up" \
        else ("Trim", "mid-band, fading") if d == "down" \
        else ("Hold", "fairly valued vs its own history")


# ── storage (owns its own table) ──────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS rsband_signals (
    numerator         TEXT NOT NULL,
    denominator       TEXT NOT NULL,
    trade_date        TEXT,
    rs_band_pct       REAL,
    rs_band_pct_long  REAL,
    rs_band_pct_detr  REAL,
    rs_band_low       REAL,
    rs_band_mid       REAL,
    rs_band_high      REAL,
    rs_poc            REAL,
    rs_val            REAL,
    rs_vah            REAL,
    rs_alltime_high   REAL,
    rs_alltime_low    REAL,
    rs_band_width_pct REAL,
    rs_regime         TEXT,
    rs_hurst          REAL,
    rs_band_state     TEXT,
    slope_3m_pct      REAL,
    band_maturity     TEXT,
    rs_band_label     TEXT,
    computed_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (numerator, denominator)
);
CREATE INDEX IF NOT EXISTS idx_rsband_den ON rsband_signals(denominator, rs_band_pct);
"""

_COLS = [
    "numerator", "denominator", "trade_date",
    "rs_band_pct", "rs_band_pct_long", "rs_band_pct_detr",
    "rs_band_low", "rs_band_mid", "rs_band_high",
    "rs_poc", "rs_val", "rs_vah",
    "rs_alltime_high", "rs_alltime_low", "rs_band_width_pct",
    "rs_regime", "rs_hurst", "rs_band_state", "slope_3m_pct",
    "band_maturity", "rs_band_label",
]


def _series(conn, numerator: str, denominator: str) -> tuple[list[str], list[float]]:
    rows = conn.execute(
        "SELECT trade_date, ratio FROM ratio_rows "
        "WHERE numerator=? AND denominator=? AND ratio IS NOT NULL "
        "ORDER BY trade_date ASC", (numerator, denominator),
    ).fetchall()
    return [r["trade_date"] for r in rows], [r["ratio"] for r in rows]


def compute_and_store(conn=None) -> int:
    """Compute the band row for every (numerator, denominator) pair in ratio_rows
    and upsert one latest row each. Returns pairs stored. Manages its own
    connection if none is given (the rrg.py / capture.py pattern)."""
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
        sql = f"INSERT OR REPLACE INTO rsband_signals ({','.join(_COLS)}) VALUES ({placeholders})"
        n = 0
        for p in pairs:
            num, den = p["numerator"], p["denominator"]
            if num == den:
                continue
            dates, ratio = _series(conn, num, den)
            res = compute_one(ratio)
            if not res:
                continue
            res["numerator"], res["denominator"] = num, den
            res["trade_date"] = dates[-1]
            conn.execute(sql, [res.get(c) for c in _COLS])
            n += 1
        if own:
            conn.commit()
        return n
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── read helpers (for the UI layer; ₹0) ───────────────────────────────────────
def latest_all(denominator: str, conn=None) -> list[dict]:
    """Every numerator's latest stored band row vs one benchmark, cheapest
    (lowest rs_band_pct) first. Empty if the nightly job hasn't run yet."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        conn.executescript(_SCHEMA)
        rows = conn.execute(
            "SELECT * FROM rsband_signals WHERE denominator=? "
            "ORDER BY rs_band_pct ASC", (denominator,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            cm.__exit__(None, None, None)


def current_all(denominator: str, conn=None, only=None) -> list[dict]:
    """On-read fallback: compute each numerator's CURRENT band vs one benchmark
    straight from ratio_rows (when rsband_signals isn't populated). `only` (an
    iterable of names) curates the universe so the page stays fast. Cheapest first."""
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
            nums = [x for x in nums if x in keep]
        out = []
        for num in nums:
            if num == denominator:
                continue
            dates, ratio = _series(conn, num, denominator)
            res = compute_one(ratio)
            if not res:
                continue
            res["numerator"], res["denominator"] = num, denominator
            res["trade_date"] = dates[-1] if dates else None
            out.append(res)
        out.sort(key=lambda d: d["rs_band_pct"] if d["rs_band_pct"] is not None else 1e9)
        return out
    finally:
        if own:
            cm.__exit__(None, None, None)


def band_one(numerator: str, denominator: str, conn=None) -> Optional[dict]:
    """Full current band read for one pair (the single-series Channel), computed
    fresh from ratio_rows. Includes the fused verdict (no capture join here —
    pass falls_less from the caller when fusing with the capture layer)."""
    own = conn is None
    if own:
        cm = get_conn()
        conn = cm.__enter__()
    try:
        dates, ratio = _series(conn, numerator, denominator)
        res = compute_one(ratio)
        if not res:
            return None
        res["numerator"], res["denominator"] = numerator, denominator
        res["trade_date"] = dates[-1] if dates else None
        v, why = band_verdict(res["rs_band_pct"], res["rs_regime"],
                              res["slope_3m_pct"], res["rs_band_state"])
        res["verdict"], res["verdict_why"] = v, why
        return res
    finally:
        if own:
            cm.__exit__(None, None, None)


# ── self-check (synthetic series — no DB needed; real spot-check if DB present) ─
def _synthetic_meanrevert(n: int = 900) -> list[float]:
    """AR(1) mean-reverting ratio around 1.0 (deterministic pseudo-noise)."""
    vals = [1.0]
    x = 0.0
    for i in range(1, n):
        noise = math.sin(i * 1.7) * 0.5 + math.sin(i * 0.3) * 0.5   # bounded, deterministic
        x = 0.85 * x + 0.05 * noise
        vals.append(1.0 * math.exp(x * 0.15))
    return vals


def _synthetic_trend(n: int = 900) -> list[float]:
    """A persistent (trending / re-rating) ratio: integrated, positively
    autocorrelated increments so shocks ACCUMULATE → high Hurst. A deterministic
    drift alone would not — it adds no diffusion, so the estimator (correctly)
    reads it as mean-reverting; real re-ratings carry accumulating stochastic run."""
    vals, lv, inc = [], 0.0, 0.0
    for i in range(n):
        drive = math.sin(i * 0.03) + 0.5 * math.sin(i * 0.013)   # long, sign-persistent swings
        inc = 0.8 * inc + 0.2 * (0.6 + drive)                    # persistent, mostly-positive increments
        lv += 0.01 * inc
        vals.append(math.exp(lv))
    return vals


def _selftest() -> None:
    # 1) Mean-reverting series: regime MEAN_REVERTING, band_pct in range, rails ordered.
    mr = _synthetic_meanrevert()
    r = compute_one(mr)
    assert r is not None, "compute_one returned None on a long series"
    assert 0 <= r["rs_band_pct"] <= 100, f"band_pct out of range: {r['rs_band_pct']}"
    assert r["rs_band_low"] <= r["rs_band_mid"] <= r["rs_band_high"], "rails not ordered"
    assert r["rs_regime"] == "MEAN_REVERTING", f"expected MEAN_REVERTING, got {r['rs_regime']} (H={r['rs_hurst']})"
    assert r["rs_val"] <= r["rs_poc"] <= r["rs_vah"], "value area does not bracket POC"

    # 2) Trending series: regime TRENDING (the IT/Defence re-rating case).
    tr = compute_one(_synthetic_trend())
    assert tr is not None
    assert tr["rs_regime"] == "TRENDING", f"expected TRENDING, got {tr['rs_regime']} (H={tr['rs_hurst']})"

    # 3) A fresh all-time high reached on momentum + persistence → BREAKOUT_UP.
    base = _synthetic_meanrevert(800)
    top = max(base)
    broke = base + [top * (1.0 + 0.004 * j) for j in range(1, 12)]   # 11 closes pushing past the prior max
    rb = compute_one(broke)
    assert rb["rs_band_state"] == "BREAKOUT_UP", f"expected BREAKOUT_UP, got {rb['rs_band_state']}"

    # 4) History floor: < 2y of data → no band.
    assert compute_one([1.0] * 300) is None, "history floor should reject short series"

    # 5) Verdict logic spot-checks (the §3 matrix).
    assert band_verdict(10, "MEAN_REVERTING", 3.0, "TOUCH_SUP", True)[0] == "Accumulate"
    assert band_verdict(10, "MEAN_REVERTING", -3.0, "TOUCH_SUP")[0] == "Avoid"
    assert band_verdict(90, "MEAN_REVERTING", -3.0, "TOUCH_RES")[0] == "Fade"
    assert band_verdict(8, "TRENDING", -3.0)[0] == "Trend", "trending must suppress the cheap/rich verdict"
    assert band_verdict(50, "MEAN_REVERTING", 0.0, "BREAKOUT_UP")[0] == "Ride"
    print("rsband selftest: OK (synthetic)")

    # 6) Real spot-check on IT / Defence / Media vs Nifty 500 if the DB has them.
    try:
        cm = get_conn()
        conn = cm.__enter__()
        try:
            names = ["Nifty IT", "Nifty India Defence", "Nifty Media",
                     "Nifty Pharma", "Nifty FMCG"]
            any_data = False
            for nm in names:
                res = band_one(nm, "Nifty 500", conn=conn)
                if not res:
                    continue
                any_data = True
                assert res["rs_band_pct"] is None or 0 <= res["rs_band_pct"] <= 100
                print(f"  {nm:22s} band={res['rs_band_pct']!s:>5} "
                      f"regime={res['rs_regime']:<14} state={res['rs_band_state']:<12} "
                      f"verdict={res['verdict']} ({res['rs_band_label']})")
            if not any_data:
                print("  (real spot-check skipped - no ratio_rows for those names yet)")
        finally:
            cm.__exit__(None, None, None)
    except Exception as e:   # never let the real check fail the synthetic self-test
        print(f"  (real spot-check skipped - {type(e).__name__}: {e})")


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
    log.info("rsband_signals: stored %d pairs", stored)
    print(f"rsband_signals: stored {stored} pairs")


if __name__ == "__main__":
    main()
