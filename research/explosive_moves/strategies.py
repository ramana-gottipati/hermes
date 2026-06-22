"""The 4 candidate strategies — entry predicates, tiers, exits, sizing, regime.

Each Strategy is a pure spec (data) + an ``entry_mask`` callable over the cached
feature arrays. Thresholds live in ``params`` so walk-forward / plateau-sweep / ±10%
jitter passes can perturb them without touching code. Canonical entry numbers are the
FROZEN forward-split OOS tree cuts (research.db oos_monthly, T12-19→2020-26):
  M1  ret_22d>0.07303, vol_ratio_22_66<=1.477, range_tight_22>0.0962
  M2  ret_22d<=0.07303, vol_66>0.0243, ret_1d<=-0.02186

Exit design is grounded in calibrate.py's per-trade forward paths (NOT the cohort-mean
mae): winners that touch +12% still dip pre-peak to ~-13% at p25, so the initial stop is
WIDE (~-15%); a naive hold to 66d is ~flat (+2.2%), so the edge is HARVESTED — scale out
as the +24%-median MFE develops and trail the runner; trailing activates only AFTER the
move matures (trail_after) so the first leg can breathe.

Liquidity tiers (point-in-time trailing-22d median turnover, ₹): T1 1-5cr, T2 5-25cr,
T3 25cr+ — cost % falls as tier rises.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import numpy as np

CR = 1e7

# Per-tier cost model. spread_rt = ROUND-TRIP catalog spread (₹1-5cr~1.5% / 5-25cr~0.6%
# / 25cr+~0.25%); per side = half. fees_ps = blended STT+brokerage+GST+stamp per side.
# slippage added at sim time as 0.5*ATR%(entry) (+ extra_slip for S3 adverse fills).
COST_TIERS = {
    "T1": {"floor": 1 * CR, "ceil": 5 * CR, "spread_rt": 0.015, "fees_ps": 0.0015},
    "T2": {"floor": 5 * CR, "ceil": 25 * CR, "spread_rt": 0.006, "fees_ps": 0.0012},
    "T3": {"floor": 25 * CR, "ceil": np.inf, "spread_rt": 0.0025, "fees_ps": 0.0010},
}


def tier_for_turnover(mt: float) -> str | None:
    for t, c in COST_TIERS.items():
        if c["floor"] <= mt < c["ceil"]:
            return t
    return None


@dataclass
class Strategy:
    name: str
    desc: str
    liq_floor: float
    entry_mask: Callable
    params: dict
    cooldown: int = 22
    # --- exit management ---
    init_stop_pct: float = 0.15           # initial hard stop (calibrated wide)
    use_chandelier: bool = True           # trail = peak - atr_mult*ATR(entry)
    atr_mult: float = 4.0
    atr_mult_tight: float = 3.0
    tighten_at: float = 0.40              # tighten trail after a big run
    trail_after: float = 0.12             # only start trailing once peak gain >= this
    scales: tuple = ((0.12, 0.33), (0.30, 0.33))   # (gain level, fraction sold)
    be_after_scale: bool = True           # after first scale, lift stop toward entry
    be_offset: float = -0.03              # post-scale stop = entry*(1+be_offset)
    time_exit_bars: int = 132
    time_check_at: int = 22
    time_check_min: float = 0.0           # cut at time_check_at if close gain < this
    gap_down_kill: bool = False
    # --- sizing / portfolio ---
    risk_frac: float = 0.005
    max_pos_frac: float = 0.20
    max_heat: float = 0.12
    max_positions: int = 25
    regime_mode: str = "trend"            # 'trend' | 'off' | 'inverted'
    breadth_min: float = 0.0
    extra_slip: float = 0.0


# ---- entry predicates -------------------------------------------------------
def _m1_core(F, p):
    return ((F["ret_22d"] >= p["ret22"]) &
            (F["vol_ratio_22_66"] <= p["volr"]) &
            (F["range_tight_22"] > p["rng"]))


def s1_entry(F, p):
    m = _m1_core(F, p) & (F["close_vs_sma50"] >= 0) & (F["sma50"] >= F["sma200"])
    if p.get("coiled", False):
        m = m & (F["vol_ratio"] < p.get("vratio", 1.0))
    return m


def s2_entry(F, p):
    return _m1_core(F, p) & (F["close_vs_sma50"] >= 0) & (F["sma50"] >= F["sma200"])


def s3_entry(F, p):
    return ((F["ret_1d"] <= p["shake"]) & (F["ret_22d"] <= p["ret22_max"]) &
            (F["vol_66"] > p["vol66"]) & (F["dist_high_22"] >= p["dist_high_min"]) &
            (F["close_vs_sma200"] >= 0))


def s4_entry(F, p):
    return (F["vol_ratio"] < p["vratio"]) & (F["ret_22d"] >= p["ret22"])


def build_strategies() -> dict:
    S = {}
    S["S1"] = Strategy(
        name="S1", desc="Coiled-Launchpad Core (momentum, vol-targeted, 5cr+)",
        liq_floor=5 * CR, entry_mask=s1_entry,
        params={"ret22": 0.075, "volr": 1.477, "rng": 0.0962, "coiled": False, "vratio": 1.0},
        init_stop_pct=0.18, use_chandelier=True, atr_mult=6.0, atr_mult_tight=4.0,
        tighten_at=0.60, trail_after=0.25, scales=((0.25, 0.50),),
        be_after_scale=True, be_offset=-0.05,
        time_exit_bars=132, time_check_at=22, time_check_min=0.0,
        risk_frac=0.005, max_pos_frac=0.20, max_heat=0.12, max_positions=25,
        regime_mode="trend")
    S["S2"] = Strategy(
        name="S2", desc="Heat-Capped Large-Cap Launchpad (25cr+, fixed-fractional)",
        liq_floor=25 * CR, entry_mask=s2_entry,
        params={"ret22": 0.075, "volr": 1.477, "rng": 0.0962},
        init_stop_pct=0.18, use_chandelier=True, atr_mult=6.0, atr_mult_tight=4.0,
        tighten_at=0.60, trail_after=0.25, scales=((0.25, 0.50),),
        be_after_scale=True, be_offset=-0.05,
        time_exit_bars=132, time_check_at=22, time_check_min=0.0,
        risk_frac=0.005, max_pos_frac=0.15, max_heat=0.10, max_positions=25,
        regime_mode="trend")
    S["S3"] = Strategy(
        name="S3", desc="Shakeout-in-Volatility Reversion (mean-reversion diversifier)",
        liq_floor=5 * CR, entry_mask=s3_entry,
        params={"shake": -0.022, "ret22_max": 0.07, "vol66": 0.024, "dist_high_min": -0.12},
        init_stop_pct=0.18, use_chandelier=True, atr_mult=6.0, atr_mult_tight=4.0,
        tighten_at=0.60, trail_after=0.25, scales=((0.25, 0.50),),
        be_after_scale=True, be_offset=-0.05,
        time_exit_bars=132, time_check_at=15, time_check_min=0.0, gap_down_kill=True,
        risk_frac=0.005, max_pos_frac=0.15, max_heat=0.10, max_positions=20,
        regime_mode="inverted", extra_slip=0.004)
    S["S4"] = Strategy(
        name="S4", desc="Skeptic's Cost-Stressed Coiled-Momentum (25cr+, audit)",
        liq_floor=25 * CR, entry_mask=s4_entry,
        params={"vratio": 1.0, "ret22": 0.10},
        init_stop_pct=0.18, use_chandelier=True, atr_mult=6.0, atr_mult_tight=4.0,
        tighten_at=0.60, trail_after=0.25, scales=((0.25, 0.50),),
        be_after_scale=True, be_offset=-0.05,
        time_exit_bars=132, time_check_at=22, time_check_min=0.0,
        risk_frac=0.005, max_pos_frac=0.15, max_heat=0.10, max_positions=25,
        regime_mode="trend")
    return S
