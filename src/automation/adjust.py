"""Corporate-action (split / bonus) back-adjustment — single source of truth.

This module is the ONE canonical implementation of the split/bonus back-
adjustment that makes a raw bhav-copy close series continuous (the same method
Zerodha uses for its charts). It was first written inline in the dashboard
render (`src/web/dashboard.py`, D36); this module extracts that EXACT two-layer
logic so every consumer — the dashboard chart, RS (D33), and any future
zones-on-adjusted-price recompute — shares one definition.

The dashboard's inline copy can be unified to call `adjusted_closes` later
(open item B5); keep the algorithm here authoritative.

Pure: no DB, no I/O. Caller supplies the rows.

Algorithm (two layers, identical to D36):
  - NSE sets prev_close to the ADJUSTED previous close on a split/bonus
    ex-date, so `prev_close[i] / close[i-1]` deviates from 1 ONLY on real
    action dates. PRIMARY layer flags those (deviation > PC_THRESH, sane band).
  - Dividends do NOT adjust prev_close, so they don't trigger the primary layer.
  - FALLBACK layer catches actions NSE left unadjusted: a single-day close
    jump > CC_THRESH (a real 30%+ daily move is impossible under circuit
    limits, so it's always a corporate action). Only used when the primary
    layer didn't already flag the row.
  - Walk BACKWARD from newest to oldest, accumulating the cumulative factor
    `cum`; older closes are scaled by the cumulative factor in force at their
    position so the whole curve is continuous to the latest (unadjusted) close.
"""

from typing import Optional

# Thresholds — kept identical to the dashboard's D36 inline values.
PC_THRESH = 0.03   # prev_close flag: real splits/bonuses; normal days ≈ 0%
CC_THRESH = 0.30   # close-jump fallback: >30% single-day move = action NSE
                   # didn't adjust prev_close for (circuit limits make a real
                   # 30%+ daily move impossible, so it's always a corp action)


def adjustment_factors(rows: list[dict]) -> list[float]:
    """Cumulative back-adjustment factor per row, OLDEST→NEWEST.

    `rows` = list of dicts with at least `close` and `prev_close`, ordered
    oldest first. Returns a parallel list of floats: multiply a row's raw OHLC
    by its factor to get the back-adjusted value. The newest row's factor is
    always 1.0 (anchor); older rows carry the product of every action factor
    that occurred after them.
    """
    n = len(rows)
    factors = [1.0] * n
    if n < 2:
        return factors
    cum = 1.0
    for i in range(n - 1, 0, -1):
        prior_close = rows[i - 1].get("close")
        this_close = rows[i].get("close")
        pc = rows[i].get("prev_close")
        ratio: Optional[float] = None
        # Primary: prev_close-based (precise, NSE-adjusted on ex-dates).
        if pc and prior_close and prior_close > 0:
            r_pc = pc / prior_close
            if abs(r_pc - 1) > PC_THRESH and 0.02 < r_pc < 50:
                ratio = r_pc
        # Fallback: prev_close didn't flag but the close gapped hugely — an
        # unadjusted corporate action (PARAS 2025-07-04 style).
        if ratio is None and prior_close and prior_close > 0 and this_close:
            r_cc = this_close / prior_close
            if abs(r_cc - 1) > CC_THRESH and 0.02 < r_cc < 50:
                ratio = r_cc
        if ratio is not None:
            cum *= ratio
        factors[i - 1] = cum
    return factors


def adjusted_closes(rows: list[dict]) -> list[Optional[float]]:
    """Back-adjusted close per row, OLDEST→NEWEST.

    `rows` = list of dicts `{trade_date, close, prev_close}` ordered oldest
    first. Returns a parallel list of adjusted-close floats (None where the
    raw close is None). Splits/bonuses no longer fake a cliff; the latest close
    is unchanged (anchor). This is the price RS must use — a raw split would
    otherwise fake a relative-strength collapse.
    """
    factors = adjustment_factors(rows)
    out: list[Optional[float]] = []
    for r, f in zip(rows, factors):
        c = r.get("close")
        out.append(round(c * f, 6) if c is not None else None)
    return out
