"""Point-in-time forward-outcome backtest for the Wolfe setup.

For each detected, point-4-locked wave: locate the point-5 confluence band, then
walk FORWARD only (no look-ahead) — enter in the reversal direction when price
first reaches the band, exit on an R-multiple target or stop, and score the
outcome in ATR units. Aggregates win-rate / expectancy by quality tier and
compares to an unconditional forward-return baseline.

This is the Phase-0 gate: does the setup reverse better than chance? Pure stdlib.

Usage (from repo root):
    .venv/Scripts/python.exe research/wolfe_waves/backtest.py --describe --symbols all
    HERMES_MAIN_DB=/opt/hermes/data/hermes.db python3 research/wolfe_waves/backtest.py --symbols all
"""
import argparse
import os
import sys
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common   # noqa: E402
import detect   # noqa: E402
import point5   # noqa: E402


def simulate(series, atr_arr, wave, band, R=2.0, S=1.0, max_wait=40, max_hold=66):
    """Forward sim from the wave's lock bar. Returns dict with outcome in R units."""
    high, low, close, n = series.high, series.low, series.close, series.n
    f = wave.lock_idx
    entry = None
    for t in range(f + 1, min(f + 1 + max_wait, n)):
        if wave.direction == 'BULL' and low[t] <= band["high"]:
            entry = t
            break
        if wave.direction == 'BEAR' and high[t] >= band["low"]:
            entry = t
            break
    if entry is None:
        return {"entered": False}
    a = common.near_atr(atr_arr, entry)
    if not a or a <= 0:
        return {"entered": False}
    last = min(entry + max_hold, n) - 1
    if wave.direction == 'BULL':
        ep = band["high"]
        tgt, stp = ep + R * a, band["low"] - S * a
        outcome = None
        for t in range(entry, last + 1):
            if low[t] <= stp:
                outcome = -S
                break
            if high[t] >= tgt:
                outcome = R
                break
        if outcome is None:
            outcome = (close[last] - ep) / a
    else:
        ep = band["low"]
        tgt, stp = ep - R * a, band["high"] + S * a
        outcome = None
        for t in range(entry, last + 1):
            if high[t] >= stp:
                outcome = -S
                break
            if low[t] <= tgt:
                outcome = R
                break
        if outcome is None:
            outcome = (ep - close[last]) / a
    return {"entered": True, "R": outcome, "win": outcome > 0,
            "tier": wave.tier, "direction": wave.direction, "narrow": band.get("narrow")}


def baseline_fwd(series, atr_arr, H=66):
    """Unconditional mean forward move in ATR units (long bias) — a sanity ref."""
    close, n = series.close, series.n
    vals = []
    for t in range(n - H):
        a = atr_arr[t]
        if a and a > 0:
            vals.append((close[t + H] - close[t]) / a)
    return (mean(vals), len(vals)) if vals else (None, 0)


def run(symbols, ks, describe=False, ratios=point5.RATIOS_FULL, min_turnover=0.0):
    con = common.main_conn()
    if symbols == ["all"]:
        symbols = common.eq_symbols(con)
    results, base_vals = [], []
    n_waves = 0
    per_symbol = []
    for sym in symbols:
        s = common.load_series(con, sym)
        if not s:
            continue
        waves, atr_arr = detect.find_waves(s, ks=ks)
        n_waves += len(waves)
        b, bn = baseline_fwd(s, atr_arr)
        if b is not None:
            base_vals.append(b)
        sym_entries = 0
        for w in waves:
            band = point5.high_prob_band(w, common.near_atr(atr_arr, w.lock_idx), ratios)
            if not band:
                continue
            r = simulate(s, atr_arr, w, band)
            if describe:
                _print_wave(s, w, band)
            if r.get("entered"):
                results.append(r)
                sym_entries += 1
        per_symbol.append((sym, s.n, len(waves), sym_entries))
    con.close()
    _report(per_symbol, results, base_vals, n_waves)


def _print_wave(s, w, band):
    p = lambda pv: f"{s.date[pv.idx]}@{pv.price:.1f}"
    print(f"  {w.symbol:12s} {w.direction} {w.tier:4s} q={w.quality:.2f} "
          f"symP={w.sym_price:.2f} symT={w.sym_time:.2f} | "
          f"1:{p(w.p1)} 2:{p(w.p2)} 3:{p(w.p3)} 4:{p(w.p4)} | "
          f"band {band['low']:.1f}-{band['high']:.1f} "
          f"({band['tightness_atr']:.2f}atr{' NARROW' if band['narrow'] else ''}) "
          f"tgt={w.target_price:.1f}")


def _report(per_symbol, results, base_vals, n_waves):
    print("\n" + "=" * 64)
    print(f"symbols scanned: {len(per_symbol)} | waves detected: {n_waves} | "
          f"entries: {len(results)}")
    if per_symbol and n_waves == 0:
        print("(no valid 1-4 waves on this sample — expected on the tiny local DB; "
              "run on the VPS archive for a real sample)")
    if results:
        wins = sum(1 for r in results if r["win"])
        rs = [r["R"] for r in results]
        print(f"\nALL setups   n={len(results):4d}  win%={100*wins/len(results):5.1f}  "
              f"meanR={mean(rs):+.2f}  sumR={sum(rs):+.1f}")
        for tier in ("HIGH", "MED", "LOW"):
            t = [r for r in results if r["tier"] == tier]
            if t:
                w = sum(1 for r in t if r["win"])
                print(f"  {tier:4s}       n={len(t):4d}  win%={100*w/len(t):5.1f}  "
                      f"meanR={mean([r['R'] for r in t]):+.2f}")
        narrow = [r for r in results if r.get("narrow")]
        if narrow:
            w = sum(1 for r in narrow if r["win"])
            print(f"  NARROW-band  n={len(narrow):4d}  win%={100*w/len(narrow):5.1f}  "
                  f"meanR={mean([r['R'] for r in narrow]):+.2f}")
    if base_vals:
        print(f"\nbaseline (unconditional {66}-bar fwd move, ATR units): "
              f"mean={mean(base_vals):+.2f} across {len(base_vals)} symbols")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="all",
                    help="'all' or comma-separated list")
    ap.add_argument("--k", default="1.5",
                    help="swing scale(s), comma-separated ATR multiples")
    ap.add_argument("--describe", action="store_true",
                    help="print each detected wave")
    args = ap.parse_args()
    syms = ["all"] if args.symbols == "all" else [s.strip().upper() for s in args.symbols.split(",")]
    ks = tuple(float(x) for x in args.k.split(","))
    print(f"DB: {common.MAIN_DB}")
    run(syms, ks, describe=args.describe)


if __name__ == "__main__":
    main()
