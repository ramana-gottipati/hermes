"""Backtest base — symbol cache, vectorized entry features, market regime.

The discovery/validation modules (events/features/mine/validate) operate on the
de-overlapped EVENT set + a 1/10 baseline sample stored in research.db. A tradeable
backtest instead needs a POINT-IN-TIME scan of EVERY liquid (symbol, day) with the
entry features computed strictly as-of the close of day ``s`` (enter ``s+1`` open),
plus corporate-action-clean forward bars to manage the exit. This module provides:

  build_symbol_cache() : load every EQ symbol once (CA-adjusted OHLC + delivery +
                         turnover + the entry-feature arrays) and pickle to disk on
                         the VPS, so repeated backtest/sweep runs are cheap.
  load_symbol_cache()  : reload it.
  market_regime()      : Nifty-50 > 200DMA (+ optional breadth) daily ON/OFF series.

ALL feature formulas here are byte-for-byte the same as features.raw_features so the
mined rules apply unchanged. Windows are "ending at and inclusive of s" of length w
(x[s-w+1 : s+1]); with the WARMUP_ROWS=260 entry floor every window is always full,
so partial-window edge cases never affect a real entry and we keep NaN before warmup.
"""
from __future__ import annotations

import os
import pickle
import time
from typing import Optional

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .common import (
    LIQ_FLOOR, WARMUP_ROWS, STUDY_START,
    SymbolSeries, eq_symbols, load_series, main_conn,
)

CACHE_PATH = os.environ.get("EM_CACHE", "/opt/hermes/data/em_cache.pkl")
MIN_ROWS = 280   # need >=1y warmup + a little forward room to be a usable symbol


# ---- rolling helpers (window ends at & includes index s; NaN before full) ----
def _roll_mean(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    c = np.concatenate(([0.0], np.cumsum(np.nan_to_num(x, nan=0.0))))
    cnt = np.concatenate(([0.0], np.cumsum(~np.isnan(x))))
    s = c[w:] - c[:-w]
    k = cnt[w:] - cnt[:-w]
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(k > 0, s / k, np.nan)
    out[w - 1:] = m
    return out


def _roll_max(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(x, w)               # rows i=0..n-w, row k = x[k:k+w]
    out[w - 1:] = np.nanmax(sw, axis=1)
    return out


def _roll_min(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(x, w)
    out[w - 1:] = np.nanmin(sw, axis=1)
    return out


def _roll_std(g: np.ndarray, w: int) -> np.ndarray:
    """Population std (ddof=0, == np.nanstd) of g over the trailing w values."""
    n = len(g)
    out = np.full(n, np.nan)
    if n < w:
        return out
    sw = sliding_window_view(g, w)
    out[w - 1:] = np.nanstd(sw, axis=1)
    return out


def _ret_k(ac: np.ndarray, k: int) -> np.ndarray:
    n = len(ac)
    out = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[k:] = np.where(ac[:-k] > 0, ac[k:] / ac[:-k] - 1.0, np.nan)
    return out


def _consec_up(ac: np.ndarray) -> np.ndarray:
    """Number of consecutive up-closes ending at s (ac[i] > ac[i-1])."""
    n = len(ac)
    up = np.zeros(n, dtype=float)
    run = 0
    for i in range(1, n):
        if ac[i] > ac[i - 1]:
            run += 1
        else:
            run = 0
        up[i] = run
    return up


def compute_entry_features(ss: SymbolSeries) -> dict:
    """All entry-rule features as parallel arrays (index = day s, as-of close s)."""
    ac, ah, al = ss.adj_close, ss.adj_high, ss.adj_low
    v, dq = ss.volume, ss.deliv_qty
    n = ss.n
    g = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        g[1:] = np.log(np.clip(ac[1:], 1e-9, None)) - np.log(np.clip(ac[:-1], 1e-9, None))
    f = {}
    f["ret_1d"] = _ret_k(ac, 1)
    f["ret_5d"] = _ret_k(ac, 5)
    f["ret_10d"] = _ret_k(ac, 10)
    f["ret_22d"] = _ret_k(ac, 22)
    f["ret_66d"] = _ret_k(ac, 66)
    f["vol_22"] = _roll_std(g, 22)
    f["vol_66"] = _roll_std(g, 66)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["vol_ratio"] = np.where(f["vol_66"] > 0, f["vol_22"] / f["vol_66"], np.nan)
    # volume ratio 22/66 (turnover not expanding) — M1's middle term
    vm22, vm66 = _roll_mean(v, 22), _roll_mean(v, 66)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["vol_ratio_22_66"] = np.where(vm66 > 0, vm22 / vm66, np.nan)
    # delivery-qty trend (M1-reverse term).
    # ⚠ Codex D5-F6 (Track C, verified — split-sensitivity, deferred fix): this trends RAW delivered
    # SHARE COUNT (dm22/dm66 of dq), so a split inside the 66d window inflates the ratio. The clean
    # fix is a delivered-VALUE trend = dq * ss.close (RAW close → split-invariant; NOT adj_close,
    # which would re-introduce the D1-F1 raw-qty×adjusted-price trap). Deferred because this feature
    # feeds the LIVE nightly momentum_scan → the change wants a momentum_scan re-verify + deploy.
    # Verified minor: ~0.09 Sharpe to QUAL_MOM, ~0 to DELIV_MOM (TRACK-C-RESULTS.md §D5-F6).
    dm22, dm66 = _roll_mean(dq, 22), _roll_mean(dq, 66)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["deliv_qty_trend"] = np.where(dm66 > 0, dm22 / dm66, np.nan)
    # base tightness on closes
    rmax, rmin, rmean = _roll_max(ac, 22), _roll_min(ac, 22), _roll_mean(ac, 22)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["range_tight_22"] = np.where(rmean > 0, (rmax - rmin) / rmean, np.nan)
    # trend posture
    sma20, sma50, sma200 = _roll_mean(ac, 20), _roll_mean(ac, 50), _roll_mean(ac, 200)
    f["sma50"], f["sma200"] = sma50, sma200
    with np.errstate(invalid="ignore", divide="ignore"):
        f["close_vs_sma20"] = np.where(sma20 > 0, ac / sma20 - 1.0, np.nan)
        f["close_vs_sma50"] = np.where(sma50 > 0, ac / sma50 - 1.0, np.nan)
        f["close_vs_sma200"] = np.where(sma200 > 0, ac / sma200 - 1.0, np.nan)
    # distance from 22d / 252d high (<=0)
    hi22 = _roll_max(ac, 22)
    hi252, lo252 = _roll_max(ac, 252), _roll_min(ac, 252)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["dist_high_22"] = np.where(hi22 > 0, ac / hi22 - 1.0, np.nan)
        f["range_pos_252"] = np.where((hi252 - lo252) > 0, (ac - lo252) / (hi252 - lo252), np.nan)
    # ATR% (14) — fractional true-range proxy on (high-low)/close
    tr = (ah - al) / np.clip(ac, 1e-9, None)
    f["atr14_pct"] = _roll_mean(tr, 14)
    # close strength (5) — (c-l)/(h-l) averaged
    hl = ah - al
    with np.errstate(invalid="ignore", divide="ignore"):
        cs = np.where(hl > 0, (ac - al) / hl, np.nan)
    f["close_strength_5"] = _roll_mean(cs, 5)
    f["consec_up"] = _consec_up(ac)
    # gap (raw open vs prior raw close)
    gap = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        gap[1:] = np.where(ss.close[:-1] > 0, ss.open[1:] / ss.close[:-1] - 1.0, np.nan)
    f["gap_1d"] = gap
    return f


def build_symbol_cache(path: str = CACHE_PATH, limit: Optional[int] = None) -> dict:
    """Load every usable EQ symbol, attach entry features, pickle to disk."""
    t0 = time.time()
    mc = main_conn()
    syms = eq_symbols(mc)
    if limit:
        syms = syms[:limit]
    cache: dict = {}
    kept = 0
    for k, sym in enumerate(syms):
        ss = load_series(mc, sym)
        if ss is None or ss.n < MIN_ROWS:
            continue
        feats = compute_entry_features(ss)
        adj_open = ss.open * ss.factors
        cache[sym] = {
            "date": np.array(ss.date),
            "adj_open": adj_open.astype(np.float32),
            "adj_close": ss.adj_close.astype(np.float32),
            "adj_high": ss.adj_high.astype(np.float32),
            "adj_low": ss.adj_low.astype(np.float32),
            "is_ca": ss.is_ca,
            "med_turn": ss.med_turn.astype(np.float64),
            "ret_raw": ss.ret_raw.astype(np.float32),
            "feats": {kk: vv.astype(np.float32) for kk, vv in feats.items()},
        }
        kept += 1
        if (k + 1) % 500 == 0:
            print(f"  {k+1}/{len(syms)} scanned, {kept} kept ({time.time()-t0:.0f}s)", flush=True)
    mc.close()
    with open(path, "wb") as fh:
        pickle.dump(cache, fh, protocol=5)
    sz = os.path.getsize(path) / 1e6
    print(f"CACHE built: {kept} symbols, {sz:.0f} MB, {time.time()-t0:.0f}s -> {path}")
    return cache


def load_symbol_cache(path: str = CACHE_PATH) -> dict:
    with open(path, "rb") as fh:
        return pickle.load(fh)


# ---- market regime ----------------------------------------------------------
def market_regime(index_name: str = "Nifty 50", sma: int = 200):
    """Return (dates list, regime_on dict date->bool) from index_rows.

    regime_on = index close > its own ``sma``-day moving average (a long-only trend
    filter). Dates before the SMA warms up are False (no position).

    No look-ahead (CL-RES-03): the gate for trade-entry day ``d`` must be decidable
    from data knowable BEFORE ``d`` — entries trade at the next session's OPEN, so the
    decision uses information through the PRIOR close. We therefore compare the index
    close at ``d`` against the SMA computed up to ``d-1`` (``ma[i-1]``), not the SMA
    that already folds in ``close[i]`` itself. Using ``ma[i]`` (same-day, self-inclusive)
    was a 1-bar look-ahead in the regime filter.
    """
    mc = main_conn()
    rows = mc.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name=? ORDER BY trade_date ASC",
        (index_name,)).fetchall()
    mc.close()
    dates = [r[0] for r in rows]
    close = np.array([float(r[1]) if r[1] is not None else np.nan for r in rows])
    ma = _roll_mean(close, sma)
    on = {}
    for i, d in enumerate(dates):
        # ma[i-1] = the SMA as-of the prior close (lagged one bar; no same-day leak).
        # Warm-up needs sma bars BEFORE today's close, i.e. i-1 >= sma-1  ->  i >= sma.
        ma_prior = ma[i - 1] if i >= 1 else np.nan
        on[d] = bool(close[i] > ma_prior) if (i >= sma and not np.isnan(ma_prior)) else False
    return dates, on, {d: float(close[i]) for i, d in enumerate(dates)}


if __name__ == "__main__":
    import sys
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    build_symbol_cache(limit=lim)
