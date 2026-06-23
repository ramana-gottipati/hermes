"""Combined test — do patearn FUNDAMENTALS add to TECHNICAL strength?

Joins fund_panel (point-in-time patearn score) ⨝ ml_panel (RS / accumulation / delivery) on
(symbol, date) and asks the patearn thesis directly: among technically-strong names, does
fundamental quality (non-disqualified, above-median NS) improve forward 12m return and cut
blow-ups? Outcome = fund_panel's SURVIVORSHIP-AWARE fwd_252.

Tables stay SEPARATE (different source + cadence). This only adds a `combined_panel` VIEW — a
saved join, no copied data — and analyses it. Re-scoring fundamentals or rebuilding ml_panel
leaves the other untouched; the view always reflects both.

Run: cd /opt/hermes/research && PYTHONPATH=/opt/hermes python -m explosive_moves.combo_test
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.environ.get("HERMES_ROOT", "/opt/hermes"), os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

from explosive_moves.common import research_conn

ML_COLS = ["p_score", "r_score", "rs_rank", "accum_price_drift_3m", "deliv_value_ratio_1m_6m",
           "avg_deliv_pct_1m", "pct_from_52w_high", "mom6", "mom12", "turnover_surge_3m", "is_ath_dvpt"]


def _ensure_view(rc):
    rc.execute("DROP VIEW IF EXISTS combined_panel")
    rc.execute("CREATE VIEW combined_panel AS SELECT f.*, %s FROM fund_panel f "
               "JOIN ml_panel m USING(symbol, date)" % ",".join("m." + c for c in ML_COLS))
    rc.commit()


def _stats(fr):
    a = fr[~np.isnan(fr)]
    if len(a) == 0:
        return None
    return {"n": len(a), "med": float(np.median(a)) * 100, "hit": float((a > 0).mean()) * 100,
            "blow": float((a < -0.5).mean()) * 100, "mean": float(np.mean(a)) * 100}


def _row(label, st):
    if not st:
        return f"{label:30}{'(empty)':>8}"
    return f"{label:30}{st['n']:>7}{st['med']:>9.1f}%{st['hit']:>7.0f}%{st['blow']:>8.0f}%{st['mean']:>9.1f}%"


HDR = f"{'cell':30}{'n':>7}{'med12m':>10}{'hit%':>7}{'blow%':>8}{'mean':>10}"


def _2x2(name, tech_strong, fund_good, fwd):
    print(f"\n=== {name} × fundamental quality (fwd 12m) ===")
    print(HDR)
    for tl, tm in (("Tech STRONG", tech_strong), ("Tech weak", ~tech_strong)):
        for fl, fm in (("fund GOOD", fund_good), ("fund bad", ~fund_good)):
            print(_row(f"{tl} + {fl}", _stats(fwd[tm & fm])))


def main():
    rc = research_conn()
    _ensure_view(rc)
    rows = rc.execute(
        "SELECT ns_base, hard_disq, fwd_252, rs_rank, accum_price_drift_3m, p_score "
        "FROM combined_panel WHERE fwd_252 IS NOT NULL").fetchall()
    rc.close()

    def col(i):
        return np.array([r[i] if r[i] is not None else np.nan for r in rows], dtype=float)

    ns, disq, fwd, rs, accum, pscore = (col(0), col(1), col(2), col(3), col(4), col(5))
    print(f"combined_panel rows with fwd_252: {len(rows)}")

    ns_med = np.nanmedian(ns)
    fund_good = (disq == 0) & (ns >= ns_med)            # non-disqualified AND above-median NS

    tech_rs = rs >= np.nanquantile(rs, 2 / 3)           # top-tercile relative strength
    tech_ac = accum >= np.nanquantile(accum, 2 / 3)     # top-tercile 3m accumulation drift

    _2x2("RS leaders (top-tercile rs_rank)", tech_rs, fund_good, fwd)
    _2x2("Accumulation (top-tercile 3m drift)", tech_ac, fund_good, fwd)

    print("\n=== among RS LEADERS: does the patearn disqualifier still protect? ===")
    print(HDR)
    print(_row("RS-strong + DISQUALIFIED", _stats(fwd[tech_rs & (disq == 1)])))
    print(_row("RS-strong + non-disqualified", _stats(fwd[tech_rs & (disq == 0)])))

    best = _stats(fwd[tech_rs & fund_good])
    worst = _stats(fwd[(~tech_rs) & (~fund_good)])
    if best and worst:
        print(f"\nlong-short median 12m: (RS-strong & fund-good) − (RS-weak & fund-bad) "
              f"= {best['med'] - worst['med']:+.1f} pts   [n {best['n']} vs {worst['n']}]")
    rs_only = _stats(fwd[tech_rs])
    rs_and_good = _stats(fwd[tech_rs & fund_good])
    if rs_only and rs_and_good:
        print(f"fundamental overlay on RS leaders: median {rs_only['med']:+.1f}% → {rs_and_good['med']:+.1f}%, "
              f"blow {rs_only['blow']:.0f}% → {rs_and_good['blow']:.0f}%  (does adding fund-quality help?)")


if __name__ == "__main__":
    main()
