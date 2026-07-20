"""X-04 — overnight vs intraday return decomposition + an overnight-pump flag (S199).

Every daily move splits cleanly, in LOG space, into two additive pieces:

    on_log[i]    = ln(open[i]  / prev_close[i])     # the gap held OVERNIGHT (close->open)
    intra_log[i] = ln(close[i] / open[i])           # what happened INTRADAY (open->close)
    tot_log[i]   = ln(close[i] / prev_close[i]) = on_log[i] + intra_log[i]   # EXACT identity

Over a trailing window this answers a real question: *when* did a name's move happen —
in the auction gap before the session (news / manipulation / global cues) or during
continuous trading (organic demand)? The estate already uses the overnight leg as one
`footprint.f_overnight` feature; this module makes the full split first-class and adds a
descriptive **overnight-pump flag**: a meaningful up-move whose gains are overwhelmingly
overnight (>= ON_DOMINANCE of the total) — the classic "gap it up at the open, distribute
into the session" footprint. DESCRIPTIVE ONLY — no buy/sell verdict.

Correctness: NSE's ``prev_close`` is corporate-action-adjusted on ex-days (SymbolSeries
docstring: "split-clean but genuine big moves preserved"), so ``open/prev_close`` carries
no fake split gap; we ADDITIONALLY mask rows the adjuster flagged (``is_ca``) and any
non-positive prices. Pure-compute; the trailing-window scan reuses ``common.load_series``.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import numpy as np

from .common import LIQ_FLOOR, OUT_DIR, eq_symbols, load_series, main_conn

WINDOW = 22                                                     # ~1 trading month
PUMP_UP_MIN = float(os.environ.get("X04_PUMP_UP_MIN", 0.10))   # >= +10.5% (log) over the window
PUMP_ON_DOMINANCE = float(os.environ.get("X04_PUMP_ON_DOM", 0.90))  # >= 90% of the move is overnight


# ---------- pure compute (array-level; hermetically testable) --------------------

def day_logs(open_, close, prev_close, is_ca=None):
    """Per-day (on_log, intra_log) with tot_log = on_log + intra_log by construction.

    Rows with non-positive open/close/prev_close, or flagged ``is_ca`` (corporate action),
    are set to NaN so a split ex-day can never masquerade as an overnight gap.
    """
    open_ = np.asarray(open_, dtype=float)
    close = np.asarray(close, dtype=float)
    prev_close = np.asarray(prev_close, dtype=float)
    ok = (open_ > 0) & (close > 0) & (prev_close > 0)
    if is_ca is not None:
        ok &= ~np.asarray(is_ca, dtype=bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        on_log = np.where(ok, np.log(open_ / prev_close), np.nan)
        intra_log = np.where(ok, np.log(close / open_), np.nan)
    return on_log, intra_log


def window_summary(on_log, intra_log, window=WINDOW):
    """Cumulative log split over the trailing ``window`` rows (NaN rows drop out)."""
    on_w = np.asarray(on_log, dtype=float)[-window:]
    intra_w = np.asarray(intra_log, dtype=float)[-window:]
    cum_on = float(np.nansum(on_w))
    cum_intra = float(np.nansum(intra_w))
    cum_total = cum_on + cum_intra
    n_valid = int(np.count_nonzero(~np.isnan(on_w)))
    on_share = (cum_on / cum_total) if cum_total != 0 else float("nan")
    return {
        "cum_on_log": cum_on,
        "cum_intra_log": cum_intra,
        "cum_total_log": cum_total,
        "cum_total_pct": float(np.expm1(cum_total)),   # readable % move over the window
        "on_share": on_share,                          # fraction of the move that was overnight
        "n_valid": n_valid,
    }


def is_overnight_pump(summary, up_min=PUMP_UP_MIN, on_dom=PUMP_ON_DOMINANCE):
    """Descriptive footprint: a meaningful UP move (>= up_min log) that is overnight-dominated
    (>= on_dom of the total came from gaps). NOT a signal — a red-flag descriptor."""
    tot = summary["cum_total_log"]
    if not np.isfinite(tot) or tot < up_min:
        return False
    share = summary["on_share"]
    return bool(np.isfinite(share) and share >= on_dom)


# ---------- per-symbol row (handles as-of + liquidity; used by the scan) ----------

def symbol_row(ss, window=WINDOW, asof=None, up_min=PUMP_UP_MIN, on_dom=PUMP_ON_DOMINANCE):
    """One decomposition row for a SymbolSeries(-like) ``ss``. ``asof`` truncates to <= that
    date (point-in-time). Returns None if too little valid history in the window."""
    dates = np.asarray(ss.date)
    cut = np.ones(len(dates), dtype=bool) if asof is None else (dates <= asof)
    if cut.sum() < window:
        return None
    is_ca = getattr(ss, "is_ca", None)
    on_log, intra_log = day_logs(ss.open[cut], ss.close[cut], ss.prev_close[cut],
                                 None if is_ca is None else np.asarray(is_ca)[cut])
    summ = window_summary(on_log, intra_log, window)
    if summ["n_valid"] < max(5, window // 2):          # too many masked rows to trust the split
        return None
    med_turn = getattr(ss, "med_turn", None)
    mt = float(med_turn[cut][-1]) if med_turn is not None and len(med_turn) else float("nan")
    return {
        "symbol": ss.symbol,
        "asof": dates[cut][-1],
        "window": window,
        **summ,
        "med_turn": mt,
        "overnight_pump": is_overnight_pump(summ, up_min, on_dom),
    }


def scan(con, window=WINDOW, asof=None, liq_floor=LIQ_FLOOR, only_flagged=False,
         up_min=PUMP_UP_MIN, on_dom=PUMP_ON_DOMINANCE):
    """Run the decomposition across the EQ universe (box: needs a populated bhavcopy).

    ``liq_floor`` keeps only names whose trailing median turnover clears the floor;
    ``only_flagged`` restricts to overnight-pump rows. Sorted flagged-first, then on_share."""
    out = []
    for sym in eq_symbols(con):
        ss = load_series(con, sym)
        if ss is None:
            continue
        row = symbol_row(ss, window, asof, up_min, on_dom)
        if row is None:
            continue
        if liq_floor and not (np.isfinite(row["med_turn"]) and row["med_turn"] >= liq_floor):
            continue
        if only_flagged and not row["overnight_pump"]:
            continue
        out.append(row)
    out.sort(key=lambda r: (r["overnight_pump"], r["on_share"] if np.isfinite(r["on_share"]) else -9),
             reverse=True)
    return out


# ---------- selftest (offline, no DB) --------------------------------------------

def _fake(open_, close, prev_close, n_days=None, is_ca=None):
    """A minimal SymbolSeries stand-in for the hermetic tests."""
    n = len(open_)
    return SimpleNamespace(
        symbol="TEST",
        date=[f"2026-01-{d + 1:02d}" for d in range(n)],
        open=np.array(open_, float), close=np.array(close, float),
        prev_close=np.array(prev_close, float),
        is_ca=(np.zeros(n, bool) if is_ca is None else np.array(is_ca, bool)),
        med_turn=np.full(n, 5e7),
    )


def selftest() -> None:
    # 1. the additive identity holds exactly (log space), row by row.
    o = [100., 101, 99, 102];  c = [101., 100, 103, 101];  p = [99., 100, 101, 99]
    on, intra = day_logs(o, c, p)
    tot = np.log(np.array(c) / np.array(p))
    assert np.allclose(on + intra, tot), (on + intra, tot)

    # 2. corporate-action + bad rows are masked to NaN (no fake gap).
    on2, intra2 = day_logs([100., 50], [101., 51], [100., 100], is_ca=[False, True])
    assert np.isfinite(on2[0]) and np.isnan(on2[1]) and np.isnan(intra2[1])
    on3, _ = day_logs([100.], [101.], [0.0])          # prev_close <= 0 -> NaN
    assert np.isnan(on3[0])

    # 3. an intraday-driven riser is NOT flagged (gains are intraday, on_share ~ 0).
    W = 22
    op = [100.0] * W                                   # open == prior close (no gap)
    pc = [100.0 * (1.01 ** k) for k in range(W)]       # prev_close drifts with the rally
    cl = [100.0 * (1.01 ** (k + 1)) for k in range(W)]  # +1% intraday each day
    intr = _fake(op, cl, pc)
    r_intr = symbol_row(intr, W)
    assert r_intr is not None and r_intr["cum_total_log"] > 0.10
    assert r_intr["on_share"] < 0.1 and r_intr["overnight_pump"] is False, r_intr

    # 4. an overnight-pump (gap up +2%, fade -1% intraday) IS flagged.
    op4, cl4, pc4 = [], [], []
    base = 100.0
    for _k in range(W + 4):                             # a few extra days so the as-of cut still fills a window
        prev = base
        opn = prev * 1.02                              # +2% overnight gap
        clo = opn * 0.99                               # -1% intraday give-back
        op4.append(opn); cl4.append(clo); pc4.append(prev)
        base = clo
    pump = _fake(op4, cl4, pc4)
    r_pump = symbol_row(pump, W)
    assert r_pump is not None and r_pump["cum_total_log"] >= 0.10
    assert r_pump["on_share"] >= 0.90 and r_pump["overnight_pump"] is True, r_pump

    # 5. a flat name (tiny moves) is NOT flagged (below the up-move floor).
    flat = _fake([100.0] * W, [100.05] * W, [100.0] * W)
    r_flat = symbol_row(flat, W)
    assert r_flat is not None and r_flat["overnight_pump"] is False, r_flat

    # 6. as-of truncation is point-in-time (no peeking past the cut).
    r_asof = symbol_row(pump, W, asof=pump.date[-2])
    assert r_asof is not None and r_asof["asof"] == pump.date[-2]

    print("OVERNIGHT_SPLIT (X-04) selftest OK")


def run():
    con = main_conn()
    rows = scan(con, only_flagged=False)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "overnight_split.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flagged = sum(1 for r in rows if r["overnight_pump"])
    print(f"overnight_split: {len(rows)} names, {flagged} overnight-pump flagged -> {path}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run()
