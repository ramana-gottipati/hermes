"""
chart_view.py — server side of the Patearn chart engine (Phase 0/1).

Pairs with ``src/web/static/hermes-charts.js`` (the reusable client engine, the
"CPR Spine"). This module is a THIN, DB-free renderer: it turns already-built
Python data into the JSON contract + the HTML block that boots the engine, plus
a pure transform from ``cpr_signals`` rows into the engine's CPR segments.

Kept deliberately isolated (new module, no imports from ``dashboard.py``) so it
does not collide with the parallel-held web layer. Wire-in is one call — see
WIRE-IN below — to be applied to ``dashboard.py`` once that file is free.

WIRE-IN (in the /dash/stock handler, replacing the inline 4-chart JS block):

    from src.web import chart_view

    # `series` is the list the page already builds for `data_json`
    #   [{time,open,high,low,close,dvpt,r1m,deliv,tval,dval}, ...] ascending
    cpr = {tf: chart_view.cpr_segments(cpr_rows[tf], tf) for tf in ("D", "W", "M")}
    contract = {
        "symbol": sym, "name": company_name, "rank": rank, "read": read_line,
        "series": series, "zones": zones, "cpr": cpr,
        "confluence": chart_view.confluence(cpr),
    }
    body = chart_view.render_stock_chart(contract)   # drop into the template

And once, at app setup (main.py / dashboard router):

    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

`cpr_rows[tf]` = rows from `cpr_signals` for the symbol & timeframe, ascending by
`period_end_date`, each a dict/Row with: period_end_date, p, bc, tc, width_pct,
pattern, regime, confirmed.
"""

from __future__ import annotations

import json
from html import escape

# CDN for the charting lib (same pin the app already uses) + our engine asset.
_LWC_CDN = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"

# Per-timeframe "coil" (compression) width-% cutoffs — mirrors the CPR design
# (Daily 1.0 / Weekly 2.5 / Monthly 5.0). A band at/under its cutoff is coiled.
COIL_PCT = {"D": 1.0, "W": 2.5, "M": 5.0, "H": 8.0}


def cpr_segments(rows, tf: str) -> list[dict]:
    """`cpr_signals` rows (ascending by period_end_date) -> engine CPR segments.

    Each segment spans (prev_period_end, this_period_end] on the daily axis and
    carries that period's P/BC/TC (already computed from the prior period), so the
    sequence renders as the stepped ribbon. Pure; no DB, no look-ahead.
    """
    coil_pct = COIL_PCT.get(tf, 2.5)
    segs: list[dict] = []
    prev_end = None
    for r in rows:
        g = (lambda k: r[k] if not hasattr(r, "get") else r.get(k))  # Row or dict
        end = g("period_end_date")
        p, bc, tc = g("p"), g("bc"), g("tc")
        if end is None or p is None or bc is None or tc is None:
            prev_end = end if end is not None else prev_end
            continue
        lo, hi = (bc, tc) if bc <= tc else (tc, bc)
        width = g("width_pct")
        if width is None and p:
            width = (hi - lo) / p * 100.0
        if prev_end is not None:
            segs.append({
                "t0": str(prev_end), "t1": str(end),
                "p": round(float(p), 2), "bc": round(float(lo), 2), "tc": round(float(hi), 2),
                "width": round(float(width), 2) if width is not None else None,
                "coil": bool(width is not None and width <= coil_pct),
                "regime": int(g("regime") or 0) if g("regime") is not None else (1 if g("regime") else 0),
                "pattern": g("pattern") or None,
                "confirmed": bool(g("confirmed")),
            })
        prev_end = end
    return segs


def confluence(cpr: dict, tol_pct: float = 1.0) -> list[dict]:
    """Merge the latest D/W/M pivots that cluster within `tol_pct` into one S/R slab."""
    latest = []
    for tf in ("D", "W", "M"):
        segs = cpr.get(tf) or []
        if segs:
            latest.append(segs[-1])
    out: list[dict] = []
    for i, a in enumerate(latest):
        near = [b for b in latest if abs(b["p"] - a["p"]) / max(a["p"], 1e-9) * 100.0 <= tol_pct]
        if len(near) >= 2:
            lo = min(b["bc"] for b in near)
            hi = max(b["tc"] for b in near)
            slab = {"lo": round(lo, 2), "hi": round(hi, 2), "degrees": len(near)}
            if not any(abs(s["lo"] - slab["lo"]) < 1e-6 and abs(s["hi"] - slab["hi"]) < 1e-6 for s in out):
                out.append(slab)
    return out


def render_stock_chart(contract: dict, *, static_base: str = "/static", height: int = 460,
                       cpr_tf: str = "W") -> str:
    """Return the HTML block that mounts the engine for one stock.

    Streams the lib + engine, an inert JSON island, then a tiny boot call — no
    inline f-string JS logic (that all lives in the reusable engine).
    """
    data = json.dumps(contract, separators=(",", ":"), default=str)
    opts = json.dumps({"height": height, "cprTf": cpr_tf})
    cid = "hChart_" + escape(str(contract.get("symbol", "x")))
    return (
        f'<div id="{cid}" class="hermes-chart"></div>\n'
        f'<script src="{_LWC_CDN}"></script>\n'
        f'<script src="{static_base}/hermes-charts.js"></script>\n'
        f'<script type="application/json" id="{cid}_data">{data}</script>\n'
        f'<script>(function(){{'
        f'var c=JSON.parse(document.getElementById("{cid}_data").textContent);'
        f'window.HermesCharts&&HermesCharts.createStockChart(document.getElementById("{cid}"),c,{opts});'
        f'}})();</script>'
    )
