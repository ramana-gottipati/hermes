"""/dash/rs/overlay — a stock-vs-benchmark Relative Strength ratio line for the
stock page's docked RS lane (the "RS as a sub-pane" ask).

Isolated module (router only; no dashboard.py import) — same pattern as
``cpr_overlay`` / ``mep_overlay``. The stock-chart engine (``stock_chart.py``)
fetches this on first toggle of the RS chip and draws the series as a docked,
cyan ratio lane on its own overlay price scale.

RS ratio = rebased outperformance vs the benchmark, base 100 at the window start:

    rs[i] = (stock[i] / stock[0]) / (bench[i] / bench[0]) * 100

Rising = the stock is outpacing the benchmark; flat = moving with it. Uses raw
``bhavcopy_rows`` / ``index_rows`` closes (a relative lens; the primary candles on
the chart are the split-adjusted ones). Benchmark defaults to Nifty 500 (the broad
market), overridable via ?bench=.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.core.db import get_conn

router = APIRouter()


@router.get("/dash/rs/overlay")
def rs_overlay(sym: str = Query("", max_length=24), bench: str = Query("Nifty 500", max_length=64)):
    """JSON: {benchmark, series:[{t,v}]} — rebased RS line (base 100), or null."""
    sym = sym.strip().upper()
    bench = bench.strip()
    if not sym or not bench:
        return JSONResponse(None)
    with get_conn() as conn:
        srows = conn.execute(
            "SELECT trade_date, close FROM bhavcopy_rows "
            "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
            "AND close IS NOT NULL ORDER BY trade_date",
            (sym,),
        ).fetchall()
        if len(srows) < 2:
            return JSONResponse(None)
        d_lo, d_hi = srows[0][0], srows[-1][0]
        brows = conn.execute(
            "SELECT trade_date, close_value FROM index_rows "
            "WHERE index_name=? AND trade_date>=? AND trade_date<=? "
            "AND close_value IS NOT NULL ORDER BY trade_date",
            (bench, d_lo, d_hi),
        ).fetchall()
    if len(brows) < 2:
        return JSONResponse(None)

    bench_by = {r[0]: r[1] for r in brows}
    # align on shared trading dates, then rebase both legs to their first shared point
    pairs = [(r[0], r[1], bench_by[r[0]]) for r in srows if r[0] in bench_by and bench_by[r[0]]]
    if len(pairs) < 2:
        return JSONResponse(None)
    s0, b0 = pairs[0][1], pairs[0][2]
    if not s0 or not b0:
        return JSONResponse(None)
    series = [
        {"t": d, "v": round((sc / s0) / (bc / b0) * 100.0, 2)}
        for d, sc, bc in pairs
        if sc and bc
    ]
    if len(series) < 2:
        return JSONResponse(None)
    return JSONResponse({"benchmark": bench, "series": series})


@router.get("/dash/compare/series")
def compare_series(sym: str = Query("", max_length=64)):
    """JSON: {sym, kind, series:[{t,c}]} — a name's RAW close series (an equity from
    ``bhavcopy_rows`` or an index from ``index_rows``), ascending. The stock chart's
    Compare mode rebases each leg to 100 at the visible window start client-side, so
    this stays a neutral data feed. Tries equity first, then index. Returns null on miss.
    DESCRIPTIVE — just a price series, no signal."""
    name = sym.strip()
    if not name:
        return JSONResponse(None)
    up = name.upper()
    with get_conn() as conn:
        erows = conn.execute(
            "SELECT trade_date, close FROM bhavcopy_rows "
            "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
            "AND close IS NOT NULL ORDER BY trade_date",
            (up,),
        ).fetchall()
        if len(erows) >= 2:
            return JSONResponse({"sym": up, "kind": "equity",
                                 "series": [{"t": r[0], "c": r[1]} for r in erows]})
        irows = conn.execute(
            "SELECT trade_date, close_value FROM index_rows "
            "WHERE index_name=? AND close_value IS NOT NULL ORDER BY trade_date",
            (name,),
        ).fetchall()
    if len(irows) >= 2:
        return JSONResponse({"sym": name, "kind": "index",
                             "series": [{"t": r[0], "c": r[1]} for r in irows]})
    return JSONResponse(None)
