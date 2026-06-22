"""Event-driven daily backtest engine.

Pipeline:
  signals(cache, strat, window)    -> entry candidates (as-of close s, enter s+1 open)
  simulate_trade(arrays, sig, strat) -> one trade: exit mgmt + tiered costs (both sides)
                                        + a daily value path for mark-to-market
  portfolio(trades, regime, strat)  -> daily equity curve under regime gate, risk
                                       sizing, portfolio heat / slot caps

No look-ahead: every entry feature is as-of the close of day s; the trade is entered at
the OPEN of s+1; exits are decided on subsequent daily bars only. Corporate-action rows
are excluded around entry and all prices are CA-back-adjusted, so splits/bonuses neither
fake a move nor distort a fill. Costs (half-spread + fees + slippage + S3 adverse-fill
extra) are charged as additive friction on traded notional on BOTH entry and exit.
Sizing is risk-based (risk_frac of equity per trade); the equity curve compounds summed
daily MTM across concurrent positions.
"""
from __future__ import annotations

import os
import numpy as np

from .strategies import Strategy, COST_TIERS, tier_for_turnover
from .common import WARMUP_ROWS, STUDY_START

NOCOST = bool(os.environ.get("EM_NOCOST"))   # diagnostic: zero all frictions when set


def signals(cache: dict, strat: Strategy, window=None) -> list[dict]:
    """Entry candidates at the ONSET of the setup (rising edge of entry_mask), not on
    every day the condition holds — this mirrors the discovery's de-overlapped episodes
    and is how one actually trades (take the breakout, not day-15 of a run). A per-symbol
    cooldown blocks re-firing within ``strat.cooldown`` trading days.

    Liquid (tier floor), CA-clean (no split/bonus at s or s+1), >= STUDY_START.
    window = (start_date, end_date) inclusive on the ENTRY date (s+1). None = all.
    """
    out = []
    p = strat.params
    lo, hi = (window or (STUDY_START, "9999"))
    lo = max(lo, STUDY_START)
    cd = strat.cooldown
    for sym, A in cache.items():
        F = A["feats"]
        mask = strat.entry_mask(F, p) & (A["med_turn"] >= strat.liq_floor)
        mask = np.nan_to_num(mask, nan=False).astype(bool)
        # rising edge: True today, not yesterday
        edge = mask.copy()
        edge[1:] &= ~mask[:-1]
        n = len(A["date"])
        is_ca, dates, mt = A["is_ca"], A["date"], A["med_turn"]
        last = -10 ** 9
        for s in np.where(edge)[0]:
            if s - last < cd:
                continue
            e = s + 1
            if s < WARMUP_ROWS or e >= n:
                continue
            if is_ca[s] or is_ca[e]:
                continue
            ed = dates[e]
            if ed < lo or ed > hi:
                continue
            last = s
            out.append({"sym": sym, "s": int(s), "e": int(e), "entry_date": ed,
                        "mt": float(mt[s]), "atrp": float(F["atr14_pct"][s])})
    out.sort(key=lambda r: r["entry_date"])
    return out


ATR_STOP_SLIP = 0.5     # adverse slippage on a STOP fill, as a multiple of ATR%


def _cost_components(strat: Strategy, tier: str, atrp: float, cost_mult: float):
    """Realistic per-side friction split by fill type (fractions of notional):
      base = half-spread + fees       -> entry, target/scale, time exits (limit-like)
      stop_slip = ATR_STOP_SLIP*ATR%  -> ADDED only on a stop/gap fill (adverse, market)
      entry_extra = strat.extra_slip  -> S3 falling-bar adverse entry
    The old model charged 0.5*ATR on BOTH sides of EVERY trade, which for ~3.8%-ATR
    momentum names was a ~3.8% round-trip phantom cost that swamped the edge. Slippage
    that large only occurs on a market stop in a fast move, not on an open/limit fill.
    """
    if NOCOST:
        return 0.0, 0.0, 0.0
    c = COST_TIERS[tier]
    a = atrp if atrp == atrp else 0.04
    base = cost_mult * (c["spread_rt"] / 2.0 + c["fees_ps"])
    stop_slip = cost_mult * min(ATR_STOP_SLIP * a, 0.06)
    entry_extra = cost_mult * strat.extra_slip
    return base, stop_slip, entry_extra


def simulate_trade(A: dict, sig: dict, strat: Strategy, cost_mult: float = 1.0) -> dict | None:
    """Simulate one trade. Returns a record incl. a normalized daily value path."""
    o, h, l, c = A["adj_open"], A["adj_high"], A["adj_low"], A["adj_close"]
    n = len(c)
    e = sig["e"]
    tier = tier_for_turnover(sig["mt"])
    if tier is None or e >= n:
        return None
    entry_px = float(o[e])
    if not (entry_px > 0):
        return None
    base_fr, stop_slip, entry_extra = _cost_components(strat, tier, sig["atrp"], cost_mult)
    shares = 1.0 / entry_px                               # 1.0 capital at gross open
    atrp = sig["atrp"] if sig["atrp"] == sig["atrp"] else 0.04
    atr_price = atrp * entry_px

    if strat.use_chandelier:
        init_stop = max(entry_px * (1 - strat.init_stop_pct), entry_px - strat.atr_mult * atr_price)
    else:
        init_stop = entry_px * (1 - strat.init_stop_pct)
    R0 = (entry_px - init_stop) / entry_px
    if R0 <= 0:
        return None

    stop = init_stop
    peak = entry_px
    units = 1.0
    cash = -(base_fr + entry_extra)                       # entry-side friction on full notional
    path = []
    exit_idx = e
    reason = "open"
    scales_done = 0
    scales = strat.scales
    hzn = min(e + strat.time_exit_bars, n - 1)

    def sell(frac, price, is_stop=False):
        nonlocal units, cash
        frac = min(frac, units)
        f = base_fr + (stop_slip if is_stop else 0.0)
        notional = frac * shares * price
        cash += notional - f * notional
        units -= frac

    for t in range(e, hzn + 1):
        ot, ht, lt, ct = float(o[t]), float(h[t]), float(l[t]), float(c[t])
        # gap-down through stop -> fill at open (adverse)
        if ot <= stop:
            sell(units, ot, is_stop=True); exit_idx = t; reason = "stop_gap"; path.append(cash); break
        # profit scale-outs (take every level the bar's high reaches, in order)
        while scales_done < len(scales) and units > 1e-9:
            lvl, frac = scales[scales_done]
            tp = entry_px * (1 + lvl)
            if ot >= tp:
                sell(frac, ot)
            elif ht >= tp:
                sell(frac, tp)
            else:
                break
            scales_done += 1
            if scales_done == 1 and strat.be_after_scale:
                stop = max(stop, entry_px * (1 + strat.be_offset))
        # intrabar stop on the remainder (adverse market fill)
        if units > 1e-9 and lt <= stop:
            sell(units, stop, is_stop=True); exit_idx = t; reason = "stop"; path.append(cash); break
        if units <= 1e-9:                                 # fully scaled out
            exit_idx = t; reason = "scaled_out"; path.append(cash); break
        bars = t - e
        if bars == strat.time_check_at and ct < entry_px * (1 + strat.time_check_min):
            sell(units, ct); exit_idx = t; reason = "time_cut"; path.append(cash); break
        if t == hzn:
            sell(units, ct); exit_idx = t; reason = "time_exit"; path.append(cash); break
        # mark to market (open units at close)
        path.append(cash + units * shares * ct)
        # trail for next bar (peak through today) — only once the move has matured
        peak = max(peak, ht)
        gain = peak / entry_px - 1.0
        if strat.use_chandelier and gain >= strat.trail_after:
            mult = strat.atr_mult_tight if gain >= strat.tighten_at else strat.atr_mult
            stop = max(stop, peak - mult * atr_price)

    net_ret = cash - 1.0
    mfe = float(np.nanmax(h[e:exit_idx + 1]) / entry_px - 1.0)
    mae = float(np.nanmin(l[e:exit_idx + 1]) / entry_px - 1.0)
    return {
        "sym": sig["sym"], "entry_date": A["date"][e], "exit_date": A["date"][exit_idx],
        "e": e, "exit_idx": exit_idx, "tier": tier, "bars": int(exit_idx - e),
        "R0": float(R0), "net_ret": float(net_ret), "r_multiple": float(net_ret / R0),
        "mfe": mfe, "mae": mae, "reason": reason,
        "path": np.array(path, dtype=float),
        "_dates": list(A["date"][e:exit_idx + 1]),
    }


def all_trades(cache, strat, window=None, cost_mult=1.0) -> list[dict]:
    trades = []
    for sg in signals(cache, strat, window):
        tr = simulate_trade(cache[sg["sym"]], sg, strat, cost_mult)
        if tr is not None:
            trades.append(tr)
    return trades


def portfolio(trades, regime_on, strat: Strategy, start_equity=1.0) -> dict:
    """Daily equity curve with regime gate, risk sizing, heat & slot caps.

    weight w_i = min(max_pos_frac, risk_frac / R0_i). daily portfolio return =
    sum_i w_i * (value_i[t]/value_i[t-1] - 1) over open trades. Trades accepted greedily
    in entry-date order subject to open-heat (sum w_i*R0_i <= max_heat), slot
    (<= max_positions) caps and the regime gate.
    """
    if not trades:
        return {"dates": [], "equity": np.array([1.0]), "port_ret": np.array([]),
                "taken": [], "n_taken": 0, "skipped_regime": 0, "skipped_heat": 0,
                "skipped_dup": 0, "n_signals": 0}
    open_book = []   # (exit_date, R0, w, sym)
    taken = []
    skipped_regime = skipped_heat = skipped_dup = 0
    for tr in sorted(trades, key=lambda r: r["entry_date"]):
        ed = tr["entry_date"]
        on = regime_on.get(ed, False)
        take = on if strat.regime_mode == "trend" else (
            True if strat.regime_mode == "off" else (not on))
        if not take:
            skipped_regime += 1
            continue
        open_book = [b for b in open_book if b[0] > ed]      # drop positions closed by today
        if any(b[3] == tr["sym"] for b in open_book):        # no same-symbol overlap
            skipped_dup += 1
            continue
        cur_heat = sum(b[2] * b[1] for b in open_book)
        w = min(strat.max_pos_frac, strat.risk_frac / tr["R0"])
        if len(open_book) >= strat.max_positions or cur_heat + w * tr["R0"] > strat.max_heat:
            skipped_heat += 1
            continue
        open_book.append((tr["exit_date"], tr["R0"], w, tr["sym"]))
        taken.append((tr, w))
    # equity calendar from the TAKEN book only
    alldates = sorted({d for tr, _ in taken for d in tr["_dates"]})
    dpos = {d: i for i, d in enumerate(alldates)}
    ndays = len(alldates)
    port_ret = np.zeros(ndays)
    for tr, w in taken:
        path = tr["path"]
        prev = 1.0
        for k, d in enumerate(tr["_dates"]):
            if k >= len(path):
                break
            r = path[k] / prev - 1.0
            port_ret[dpos[d]] += w * r
            prev = path[k]
    equity = start_equity * np.cumprod(1.0 + port_ret) if ndays else np.array([start_equity])
    return {"dates": alldates, "equity": equity, "port_ret": port_ret,
            "taken": taken, "n_taken": len(taken), "n_signals": len(trades),
            "skipped_regime": skipped_regime, "skipped_heat": skipped_heat,
            "skipped_dup": skipped_dup}
