"""CCI deep actuals — grade old concall promises against the 24-yr
`fundamentals_history` archive (research.db), not just Screener's shallow
~FY2019 `concall_results`. This is the depth lever for the credibility strategy:
it lets a management's promises be settled far back in time, so the track record
(and the per-period credibility SERIES) has real history.

Returns actuals in `concall_results`' SHAPE —
    {(fy, quarter): {revenue, ebitda_margin, rev_yoy_pct, ebitda_yoy_pct, pat,
                     period_label, source}}
— so `concall_settle.settle_symbol` uses it as a DROP-IN fallback with ZERO change
to its grading logic.

Point-in-time by construction: only figures whose `report_date <= as_of` are
visible (no look-ahead). With as_of=None it returns everything reported to date
(correct for current settlement); the per-period credibility series (Phase 2)
passes as_of=<concall date> to grade exactly what was knowable then.

Mapping: `fundamentals_history` is keyed by (period_type 'A'|'Q', period_end =
CALENDAR quarter-end date). We map each quarterly period_end to the Indian-FY
(fy, quarter) the settler uses, pull Sales→revenue / 'OPM %'→ebitda_margin /
'Net Profit'→pat, and DERIVE the YoY the grader needs from the same calendar
quarter one year earlier. concall_results (fresher, Screener) wins where present;
this fills the gaps Screener can't reach.

Read-only; opens research.db directly (like fundamentals_asof.py). Degrades to an
empty dict if the archive is absent (e.g. local dev) so settlement never breaks.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Optional

log = logging.getLogger("hermes.cci_deep_actuals")

RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")

# fundamentals_history metric names -> our column (first present wins; bank fallbacks).
_REVENUE = ("Sales", "Revenue")
_MARGIN = ("OPM %", "Financing Margin %")
_PAT = ("Net Profit",)
_WANTED = _REVENUE + _MARGIN + _PAT


def _fy_quarter(period_end: str):
    """Calendar period_end 'YYYY-MM-DD' -> Indian (fy, quarter). Jan–Mar = Q4 of the
    FY ending that March; Apr–Jun/Jul–Sep/Oct–Dec = Q1/Q2/Q3 of the NEXT FY (FY named
    by its Mar-end year) — the same convention as concalls._derive_period."""
    try:
        y, m, _ = (int(x) for x in period_end.split("-"))
    except (ValueError, AttributeError):
        return None
    if m <= 3:
        return (y, 4)
    if m <= 6:
        return (y + 1, 1)
    if m <= 9:
        return (y + 1, 2)
    return (y + 1, 3)


def _pct(now, prev) -> Optional[float]:
    if now is None or prev in (None, 0):
        return None
    return round(100.0 * (now - prev) / abs(prev), 1)


def deep_actuals(symbol: str, *, as_of: Optional[str] = None,
                 db_path: str = RESEARCH_DB) -> dict:
    """{(fy, quarter): actuals-dict} from fundamentals_history, point-in-time
    filtered by `as_of` (YYYY-MM-DD; None = everything reported to date). Empty dict
    on any problem (missing archive, etc.).

    Quarterly ('Q') rows fill (fy, Q1–Q3) [Screener keeps ~13 recent quarters — the
    BREADTH win across the universe]; annual ('A') rows fill (fy, Q4) with the
    FULL-YEAR figure [the DEPTH win, 24 yrs back, and the right actual for fy/
    multiyear promises]. Annual overwrites the Q4 quarter at (fy,4); the settler
    merges concall_results FIRST, so Screener still wins for recent periods it covers."""
    if not db_path or not os.path.exists(db_path):
        return {}
    cutoff = as_of or "9999-12-31"
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        ph = ",".join("?" * len(_WANTED))
        rows = con.execute(
            "SELECT period_type, period_end, metric, value FROM fundamentals_history "
            "WHERE symbol=? AND period_type IN ('Q','A') AND value IS NOT NULL "
            f"AND report_date<=? AND metric IN ({ph})",
            (symbol.upper(), cutoff, *_WANTED)).fetchall()
        con.close()
    except sqlite3.Error as e:
        log.debug("deep_actuals %s: %s", symbol, e)
        return {}

    # period_type -> period_end -> {revenue, ebitda_margin, pat}
    by_type: dict = {"Q": {}, "A": {}}
    for r in rows:
        d = by_type[r["period_type"]].setdefault(r["period_end"], {})
        m, v = r["metric"], r["value"]
        if m in _REVENUE:
            d.setdefault("revenue", v)          # first listed name wins (Sales before Revenue)
        elif m in _MARGIN:
            d.setdefault("ebitda_margin", v)
        elif m in _PAT:
            d.setdefault("pat", v)

    def _emit(pemap: dict) -> dict:
        res: dict = {}
        for period_end, d in pemap.items():
            fq = _fy_quarter(period_end)
            if not fq:
                continue
            y, mm, dd = period_end.split("-")
            prev = pemap.get(f"{int(y) - 1:04d}-{mm}-{dd}", {})
            res[fq] = {
                "revenue": d.get("revenue"),
                "ebitda_margin": d.get("ebitda_margin"),
                "pat": d.get("pat"),
                "rev_yoy_pct": _pct(d.get("revenue"), prev.get("revenue")),
                # margin "YoY" as a pp change (sign is what the directional grader uses)
                "ebitda_yoy_pct": (round(d["ebitda_margin"] - prev["ebitda_margin"], 1)
                                   if d.get("ebitda_margin") is not None
                                   and prev.get("ebitda_margin") is not None else None),
                "period_label": period_end,      # ISO date doubles as a deep-source marker
                "source": "fundamentals_history",
            }
        return res

    out = _emit(by_type["Q"])           # quarterly → (fy, Q1–Q3) + Q4 quarter
    out.update(_emit(by_type["A"]))     # annual full-year OVERWRITES (fy, Q4)
    return out


# --- CLI (inspection) -------------------------------------------------------

def main() -> None:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Inspect deep actuals for a symbol (read-only)")
    ap.add_argument("symbol")
    ap.add_argument("--as-of", help="YYYY-MM-DD point-in-time cutoff")
    args = ap.parse_args()
    d = deep_actuals(args.symbol, as_of=args.as_of)
    print(f"{args.symbol}: {len(d)} quarterly actuals from fundamentals_history")
    for k in sorted(d)[-6:]:
        print(" ", k, json.dumps({x: d[k][x] for x in ("revenue", "ebitda_margin", "rev_yoy_pct", "period_label")}))


if __name__ == "__main__":
    main()
