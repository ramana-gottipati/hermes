"""reversal_context — pure-function tests (descriptive columns; no signal claims).

The module ships the SURVIVORS of the falsified reversal-pair arc (ledger
2026-07-13/14/14b) as context columns only. These tests pin the math + the
PIT discipline: EMA warmup, band-state transitions, per-stock stretch
percentile causality, and the fractal-floor confirmation lag.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation.reversal_context import (band_state, compute_symbol, ema,
                                             latest_floor, stretch_pctile,
                                             stretch_series)


def _v_shape():
    closes = [100.0 - 1.5 * i for i in range(30)] + [55.5 + 2.0 * i for i in range(25)]
    highs = [c + 2.0 for c in closes]
    lows = [c - 2.0 for c in closes]
    return closes, highs, lows


def test_ema_warmup_and_value():
    e = ema([10.0] * 20, 5)
    assert e[3] is None and abs(e[4] - 10.0) < 1e-9
    # NaN-free recursive check vs brute force
    xs = [float(i % 7 + 1) for i in range(40)]
    e2 = ema(xs, 5)
    a, bf = 2.0 / 6, xs[0]
    for v in xs[1:]:
        bf = a * v + (1 - a) * bf
    assert abs(e2[-1] - bf) < 1e-9


def test_band_state_reclaim_then_above():
    closes, highs, lows = _v_shape()
    tp = [(h + lo + c) / 3.0 for h, lo, c in zip(highs, lows, closes)]
    U, L, T = ema(highs, 13), ema(lows, 13), ema(tp, 5)
    states = [band_state(T[:m + 1], U[:m + 1], L[:m + 1])[0] for m in range(30, len(T))]
    assert "RECLAIM" in states
    assert states[-1] == "ABOVE"
    # the reclaim carries the below-run context
    m = 30 + states.index("RECLAIM")
    _s, run = band_state(T[:m + 1], U[:m + 1], L[:m + 1])
    assert run >= 3


def test_stretch_negative_below_band_and_pctile_causal():
    closes, highs, lows = _v_shape()
    tp = [(h + lo + c) / 3.0 for h, lo, c in zip(highs, lows, closes)]
    U, L, T = ema(highs, 13), ema(lows, 13), ema(tp, 5)
    st = stretch_series(T, U, L)
    assert min(v for v in st if v is not None) < 0
    series = [float(i % 50) for i in range(400)]
    assert stretch_pctile(series, 100) is None          # <250 prior values
    p = stretch_pctile(series, 399)
    assert p is not None and 0.0 <= p <= 100.0


def test_floor_confirmation_lag_and_invalidation():
    closes, highs, lows = _v_shape()
    hit = latest_floor(lows, closes, 10)
    assert hit is not None
    f, v, alive = hit
    assert f == 30 and alive == 1
    # not confirmed until 10 bars print after the trough: truncate to f+9 -> no D10 floor
    assert latest_floor(lows[:f + 10], closes[:f + 10], 10) is None or \
        latest_floor(lows[:f + 10], closes[:f + 10], 10)[0] != f
    # a close below the floor flips alive
    closes2 = list(closes)
    closes2[-1] = v - 1.0
    assert latest_floor(lows, closes2, 10)[2] == 0


def test_compute_symbol_round_trip():
    closes, highs, lows = _v_shape()
    # pad history so the 320-row floor is met (flat pre-history)
    pre = 400
    rows = []
    for i in range(pre):
        # flat 100 with one triangle peak at i=365 (a confirmable up-fractal —
        # ties never qualify, so the flat stretch alone carries no ceiling)
        c = 100.0 + max(0, 15 - abs(365 - i))
        rows.append({"trade_date": f"2023-{(i//28)%12+1:02d}-{i%28+1:02d}",
                     "high": c + 2, "low": c - 2, "close": c, "prev_close": c})
    for i, c in enumerate(closes):
        rows.append({"trade_date": f"2025-{(i//28)%12+1:02d}-{i%28+1:02d}",
                     "high": c + 2, "low": c - 2, "close": c, "prev_close": c})
    out = compute_symbol(rows, events=None)
    assert out is not None
    assert out["band_state"] in ("ABOVE", "INSIDE", "BELOW", "RECLAIM", "SLIP")
    assert out["floor_deg"] in (10, 5)
    assert out["floor_alive"] in (0, 1)
    assert out["floor_gap_pct"] is not None
    assert out["ceil_deg"] in (10, 5)
    assert out["ceil_alive"] in (0, 1)
    assert out["ceil_gap_pct"] is not None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
