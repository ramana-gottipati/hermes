"""X-07 — volume-at-price shelves (S200).

A daily-bar volume profile: over a trailing window, spread each day's ₹ turnover
(``value``) uniformly across that day's price range ``[adj_low, adj_high]`` and accumulate
into price bins. The result answers "at what PRICE levels has the money actually changed
hands?" — the high-turnover bins are **shelves** (the support/resistance zones a market
tends to defend), the modal bin is the **point of control (POC)**, and the narrowest band
holding ``VA_FRACTION`` of the turnover is the **value area**.

Prices are ADJUSTED (``adj_low``/``adj_high``, back-adjusted to the current basis), so a
split inside the window can never smear the profile across two price regimes; ``value`` is
already in ₹ and is basis-invariant. DESCRIPTIVE ONLY — shelves are context, not a signal.

Prior art (reused as a pattern, not code): ``src.automation.rsband._poc_value_area`` does
the POC + expand-to-value-area read on a COUNT histogram of RS-band values; this module is
the ₹-turnover-weighted price sibling and lives independently in the research tree.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, eq_symbols, load_series, main_conn

WINDOW = 66                                                    # ~3 trading months of profile
BINS = 40
VA_FRACTION = float(os.environ.get("X07_VA_FRACTION", 0.70))  # value area = 70% of turnover
SHELF_MULT = float(os.environ.get("X07_SHELF_MULT", 1.8))     # a bin is a shelf at >= 1.8x mean turnover
MAX_SHELVES = 6


# ---------- pure compute (array-level; hermetically testable) --------------------

def volume_profile(adj_low, adj_high, value, bins=BINS, price_lo=None, price_hi=None):
    """(edges, vol) — each day's ``value`` spread uniformly over ``[adj_low, adj_high]``.

    A limit-locked day (high == low) drops its whole value in the bin holding that price.
    Total turnover is conserved: ``vol.sum() == sum(valid value)`` (to float tolerance).
    """
    lo_a = np.asarray(adj_low, float)
    hi_a = np.asarray(adj_high, float)
    val = np.asarray(value, float)
    ok = np.isfinite(lo_a) & np.isfinite(hi_a) & np.isfinite(val) & (val > 0) & (hi_a >= lo_a)
    if not ok.any():
        return None, None
    lo_a, hi_a, val = lo_a[ok], hi_a[ok], val[ok]
    plo = float(np.min(lo_a)) if price_lo is None else price_lo
    phi = float(np.max(hi_a)) if price_hi is None else price_hi
    if phi <= plo:
        phi = plo + max(1e-6, abs(plo) * 1e-6)
    edges = np.linspace(plo, phi, bins + 1)
    w = (phi - plo) / bins
    vol = np.zeros(bins)
    for lo, hi, v in zip(lo_a, hi_a, val):
        if hi <= lo:                                           # limit-locked: single bin
            b = min(bins - 1, max(0, int((lo - plo) / w)))
            vol[b] += v
            continue
        b0 = min(bins - 1, max(0, int((lo - plo) / w)))
        b1 = min(bins - 1, max(0, int((hi - plo) / w)))
        span = hi - lo
        for b in range(b0, b1 + 1):
            overlap = min(hi, edges[b + 1]) - max(lo, edges[b])
            if overlap > 0:
                vol[b] += v * (overlap / span)
    return edges, vol


def poc_value_area_shelves(edges, vol, frac=VA_FRACTION, shelf_mult=SHELF_MULT,
                           max_shelves=MAX_SHELVES):
    """POC (modal turnover bin), value area (narrowest ``frac`` band expanding out from the
    POC), and the shelves (bins >= ``shelf_mult`` x mean turnover), as price levels."""
    centers = (edges[:-1] + edges[1:]) / 2.0
    total = float(vol.sum())
    if total <= 0:
        return None
    poc_bin = int(np.argmax(vol))
    # value area: expand out from the POC bin, taking the heavier neighbour first.
    lo_b = hi_b = poc_bin
    acc = vol[poc_bin]
    target = frac * total
    n = len(vol)
    while acc < target and (lo_b > 0 or hi_b < n - 1):
        left = vol[lo_b - 1] if lo_b > 0 else -1.0
        right = vol[hi_b + 1] if hi_b < n - 1 else -1.0
        if right >= left:
            hi_b += 1; acc += vol[hi_b]
        else:
            lo_b -= 1; acc += vol[lo_b]
    mean_v = total / n
    shelves = [{"price": float(centers[b]), "share": float(vol[b] / total)}
               for b in range(n) if vol[b] >= shelf_mult * mean_v]
    shelves.sort(key=lambda s: s["share"], reverse=True)
    return {
        "poc": float(centers[poc_bin]),
        "va_low": float(edges[lo_b]),
        "va_high": float(edges[hi_b + 1]),
        "va_share": float(acc / total),
        "shelves": shelves[:max_shelves],
        "n_shelves": len(shelves),
    }


# ---------- per-symbol row (as-of + liquidity; used by the scan) ------------------

def symbol_shelves(ss, window=WINDOW, asof=None, bins=BINS):
    dates = np.asarray(ss.date)
    cut = np.ones(len(dates), dtype=bool) if asof is None else (dates <= asof)
    if cut.sum() < max(20, window // 2):
        return None
    idx = np.where(cut)[0][-window:]
    edges, vol = volume_profile(ss.adj_low[idx], ss.adj_high[idx], ss.value[idx], bins)
    if edges is None:
        return None
    prof = poc_value_area_shelves(edges, vol)
    if prof is None:
        return None
    med_turn = getattr(ss, "med_turn", None)
    mt = float(med_turn[cut][-1]) if med_turn is not None and len(med_turn) else float("nan")
    last_close = float(ss.adj_close[idx][-1]) if getattr(ss, "adj_close", None) is not None else float("nan")
    # where does price sit vs its value area? (below=cheap-vs-shelf, above=extended)
    pos = ("in_value_area" if prof["va_low"] <= last_close <= prof["va_high"]
           else "above_value_area" if last_close > prof["va_high"] else "below_value_area")
    return {"symbol": ss.symbol, "asof": dates[cut][-1], "window": int(len(idx)),
            "last_close": last_close, "price_vs_va": pos, "med_turn": mt, **prof}


def scan(con, window=WINDOW, asof=None, liq_floor=LIQ_FLOOR, bins=BINS):
    out = []
    for sym in eq_symbols(con):
        ss = load_series(con, sym)
        if ss is None:
            continue
        row = symbol_shelves(ss, window, asof, bins)
        if row is None:
            continue
        if liq_floor and not (np.isfinite(row["med_turn"]) and row["med_turn"] >= liq_floor):
            continue
        out.append(row)
    out.sort(key=lambda r: r["n_shelves"], reverse=True)
    return out


# ---------- selftest (offline, no DB) --------------------------------------------

def _fake(adj_low, adj_high, value):
    n = len(adj_low)
    return SimpleNamespace(
        symbol="TEST",
        date=[f"2026-01-{d + 1:02d}" for d in range(n)],
        adj_low=np.array(adj_low, float), adj_high=np.array(adj_high, float),
        value=np.array(value, float),
        adj_close=(np.array(adj_low, float) + np.array(adj_high, float)) / 2.0,
        med_turn=np.full(n, 5e7),
    )


def selftest() -> None:
    # 1. turnover is conserved by the uniform spread.
    edges, vol = volume_profile([100., 105, 98], [110., 115, 102], [3e7, 2e7, 1e7], bins=40)
    assert abs(vol.sum() - 6e7) < 1.0, vol.sum()

    # 2. concentration -> POC at the concentrated price; value area inside the traded range.
    W = 30
    conc = _fake([99.0] * W, [101.0] * W, [1e7] * W)          # everything trades ~100
    r = symbol_shelves(conc, W)
    assert r is not None and 99.0 <= r["poc"] <= 101.0, r["poc"]
    assert r["va_low"] >= 99.0 - 1e-6 and r["va_high"] <= 101.0 + 1e-6, r
    assert 0.69 <= r["va_share"] <= 1.0001, r["va_share"]

    # 3. bimodal turnover -> at least two shelves, one near each mode.
    lo, hi, val = [], [], []
    for k in range(40):
        if k % 2 == 0:
            lo.append(99.5); hi.append(100.5); val.append(5e7)     # heavy ~100
        else:
            lo.append(119.5); hi.append(120.5); val.append(5e7)    # heavy ~120
    bimod = _fake(lo, hi, val)
    rb = symbol_shelves(bimod, 40, bins=40)
    assert rb is not None and rb["n_shelves"] >= 2, rb
    prices = sorted(s["price"] for s in rb["shelves"])
    assert prices[0] < 105 < prices[-1], prices                    # one shelf each side of the gap

    # 4. as-of is point-in-time (no peeking) + price-vs-value-area is labelled.
    ra = symbol_shelves(conc, W, asof=conc.date[-3])
    assert ra is not None and ra["asof"] == conc.date[-3]
    assert r["price_vs_va"] in ("in_value_area", "above_value_area", "below_value_area")

    # 5. WHY adjusted prices matter: the same shares traded either side of a 2:1 split, profiled
    #    on RAW prices, break into two shelves (~50 and ~100); on ADJUSTED prices they are one.
    v20 = [5e7] * 20
    e_raw, vol_raw = volume_profile([49.5] * 10 + [99.5] * 10, [50.5] * 10 + [100.5] * 10, v20)
    s_raw = poc_value_area_shelves(e_raw, vol_raw)
    e_adj, vol_adj = volume_profile([99.0] * 10 + [99.5] * 10, [101.0] * 10 + [100.5] * 10, v20)
    s_adj = poc_value_area_shelves(e_adj, vol_adj)
    assert s_raw["n_shelves"] >= 2 and s_adj["n_shelves"] < s_raw["n_shelves"], (s_raw, s_adj)

    print("VOLUME_SHELVES (X-07) selftest OK")


def run():
    con = main_conn()
    rows = scan(con)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "volume_shelves.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"volume_shelves: {len(rows)} names profiled -> {path}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run()
