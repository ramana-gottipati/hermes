"""REGIME OVERLAY — a constructive mechanism (not a description): de-risk the low-vol book in risk-off
market regimes and MEASURE whether it lifts net CAGR / cuts drawdown. Descriptive lever test (2026-07-23).

Regime = the market's own weather, from the Nifty-500 index (primary data on hand), PIT: the signal is
read at the END of the PRIOR month and applied to the current month (no look-ahead). Two regime defs:
  TREND-off : index close < its 200-day SMA
  VOL-off   : index trailing-63d realised vol in the top tercile of history-to-date
In a risk-off month the book is scaled to `scale` invested, the rest in cash (6%/yr). Reports base vs
overlay: return/vol, CAGR, MaxDD (full + both halves), and the risk-off/on month split (does the regime
actually separate good months from bad?). This is the first orthogonal-data lever; if it works it becomes
a pre-registered variant, if not it's an honest negative.

Run: PYTHONPATH=/opt/hermes:/opt/hermes/research /opt/hermes/.venv-research/bin/python \\
       -m explosive_moves.regime_overlay --run
"""
from __future__ import annotations

import json
import sys

import numpy as np

from .common import OUT_DIR, research_conn
from .metrics import index_series

CASH_M = 1.06 ** (1 / 12) - 1


def _prior(m):
    y, mm = int(m[:4]), int(m[5:7]) - 1
    if mm == 0:
        y, mm = y - 1, 12
    return f"{y:04d}-{mm:02d}"


def _st(r, months, lo=None, hi=None):
    idx = [i for i, m in enumerate(months) if (lo is None or m >= lo) and (hi is None or m < hi)]
    x = np.asarray(r, float)[idx]
    eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq); dd = float((eq / pk - 1).min())
    return (round(float(x.mean() / x.std() * 12 ** .5), 2),
            round((float(eq[-1]) ** (12 / len(x)) - 1) * 100, 1), round(dd * 100, 1))


def _analyze(book, trend_off, vol_off):
    bmonths = sorted(book)
    base = np.array([book[m] for m in bmonths])

    def ov(reg, scale):
        return np.array([book[m] if not reg.get(_prior(m), False)
                         else scale * book[m] + (1 - scale) * CASH_M for m in bmonths])
    off = [book[m] for m in bmonths if trend_off.get(_prior(m), False)]
    on = [book[m] for m in bmonths if not trend_off.get(_prior(m), False)]
    r = {
        "base": {"full": _st(base, bmonths), "h1": _st(base, bmonths, None, "2019"), "h2": _st(base, bmonths, "2019", None)},
        "separation": {"trend_off_n": len(off), "trend_off_avg%": round(float(np.mean(off)) * 100, 2) if off else None,
                       "trend_on_n": len(on), "trend_on_avg%": round(float(np.mean(on)) * 100, 2) if on else None},
        "TREND_overlay": {"scale0.3_full": _st(ov(trend_off, 0.3), bmonths),
                          "scale0.3_h2": _st(ov(trend_off, 0.3), bmonths, "2019", None),
                          "scale0.0_full": _st(ov(trend_off, 0.0), bmonths)},
    }
    if vol_off:
        r["VOL_overlay"] = {"scale0.3_full": _st(ov(vol_off, 0.3), bmonths), "scale0.0_full": _st(ov(vol_off, 0.0), bmonths)}
    return r


def run():
    rc = research_conn()
    lowvol = {m: net for m, g, net, n in rc.execute("SELECT month,gross,net,n FROM lowvolq_book")}
    mom = {m: r for m, r in rc.execute("SELECT month,mret FROM mbr_book WHERE key='CELL_B_TREND_STRONG' AND gross_net='net'")}
    rc.close()
    d, c = index_series("Nifty 500")
    c = np.asarray(c, float)
    sma = np.full(len(c), np.nan)
    for i in range(199, len(c)):
        sma[i] = c[i - 199:i + 1].mean()
    ret = np.zeros(len(c)); ret[1:] = c[1:] / c[:-1] - 1
    vol = np.full(len(c), np.nan)
    for i in range(63, len(c)):
        vol[i] = ret[i - 62:i + 1].std() * np.sqrt(252)
    me = {}
    for i, dt in enumerate(d):
        me[dt[:7]] = i                              # last index row each month
    # regime at each month-end (PIT signal source)
    trend_off = {}; vol_off = {}
    seen_vol = []
    for m in sorted(me):
        i = me[m]
        if not np.isnan(vol[i]):
            seen_vol.append(vol[i])
        if not np.isnan(sma[i]):
            trend_off[m] = bool(c[i] < sma[i])
        if not np.isnan(vol[i]) and len(seen_vol) > 12:
            vol_off[m] = bool(vol[i] > np.percentile(seen_vol, 66.7))   # top tercile, history-to-date

    out = {
        "months_lowvol": len(lowvol), "months_mom": len(mom),
        "read": "a de-risk overlay HELPS a book that gets HURT in risk-off (separation: off<on); it HURTS a book that is ALREADY a risk-off hedge (off>on). WORKS = cuts MaxDD while holding CAGR.",
        "low_vol_v2 [defensive — overlay expected NOT to help]": _analyze(lowvol, trend_off, vol_off),
        "momentum_CELL_B_TREND_STRONG [high-beta — overlay expected to CUT the -63% DD]": _analyze(mom, trend_off, vol_off),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "regime_overlay.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run() if "--run" in sys.argv or True else None
