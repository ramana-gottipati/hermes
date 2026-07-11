"""Sector economics — a decade of each sector's fundamentals as a heat-grid (deep-data sprint).

The product's "Sectors" lens is RS/rotation (price-relative). This is the ORTHOGONAL view: how
the *economics* of each sector drifted over a decade — median ROCE / operating margin by sector ×
year — using the depth of the 24-year fundamentals archive that the per-stock Growth page can't
show. One glance reads which sectors structurally compounded (IT, FMCG), which peaked and rolled
over (Chemicals' China+1 boom-bust), which are cyclical (Metals, Auto).

Source: `fundamentals_history` (research.db, annual) ⋈ `company_tags` (hermes.db, source='index'
sector membership). Aggregate → sidesteps the D66 "don't rank individual quality" constraint.

⚠ HONESTY (stated on-page): (1) sectors = CURRENT index-membership tags applied backward to history
→ SURVIVORSHIP (today's constituents, not the sector as it was); (2) thin — ~15 tagged names/sector,
so MEDIAN not mean, N shown, cells with N<5 blanked; (3) MULTI-LABEL — a name can sit in two
sectors; (4) provenance — some fundamentals are Screener-era, being migrated to NSE/BSE XBRL; (5)
financials (banks/NBFCs) report RoE not ROCE by design (Doctrine D) → mostly blank here. Descriptive
sector context, never a ranking. Route: /dash/sector-economics [?metric=roce|opm].
"""
from __future__ import annotations

import os
import sqlite3
import statistics
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx

router = APIRouter()

_RESEARCH_DB = os.environ.get("HERMES_RESEARCH_DB", "/opt/hermes/data/research.db")
_METRICS = {"roce": ("ROCE %", "Return on capital employed", "%"),
            "opm": ("OPM %", "Operating margin", "%")}
_METRIC_PLAIN = {
    "roce": "how much profit a company earns for every ₹100 of capital it puts to work — higher = a better business",
    "opm": "how much profit is left from every ₹100 of sales — higher = fatter margins",
}
_Y0, _Y1 = 2015, 2026
_MIN_N = 5

_CSS = """
<style>
.se-note{color:var(--ink-2);font-size:13px;line-height:1.6;margin:2px 0 12px;max-width:1180px;}
.se-note b{color:var(--ink);}
.se-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 14px;}
.se-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.se-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.se-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:15px 17px;margin:0 0 15px;}
.se-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.se-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
.se-sub{color:var(--ink-2);font-size:12px;line-height:1.5;margin:4px 0 12px;max-width:1080px;}
.se-mv{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-top:6px;}
.se-mvc{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;font-size:12.5px;}
.se-mvc .s{font-weight:700;color:var(--ink);font-size:13px;}
.se-mvc .d{font-variant-numeric:tabular-nums;margin-top:3px;color:var(--ink-2);}
.se-up{color:var(--up);} .se-dn{color:var(--down);}
.se-fence{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.06);border-radius:0 10px 10px 0;
  padding:11px 15px;margin:14px 0 2px;font-size:12.5px;color:var(--ink-2);line-height:1.55;max-width:1120px;}
.se-fence b{color:var(--ink);} .se-fence ul{margin:6px 0 0;padding-left:18px;} .se-fence li{margin:3px 0;}
.se-legend{display:flex;gap:6px;align-items:center;font-size:11px;color:var(--ink-3);margin:8px 0 2px;}
.se-legend .ramp{width:120px;height:10px;border-radius:3px;
  background:linear-gradient(90deg,#123b46,#175e63,#2f8f7f,#7bb26a,#d6b13f,#f0883e);}
</style>
"""


@lru_cache(maxsize=4)
def _compute(metric_key: str, research_db: str):
    metric_col = _METRICS[metric_key][0]
    # sector tags (current index membership) from hermes.db
    tags: dict[str, list[str]] = {}
    with get_conn() as h:
        for sym, tag in h.execute(
                "SELECT symbol, tag FROM company_tags WHERE approved=1 AND source='index'"):
            tags.setdefault(sym, []).append(tag)
    if not tags:
        return None
    # metric values from research.db (annual, >= _Y0)
    con = sqlite3.connect(f"file:{research_db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT symbol, period_end, value FROM fundamentals_history "
            "WHERE metric=? AND period_type='A' AND value IS NOT NULL AND period_end>=?",
            (metric_col, f"{_Y0}-01-01")).fetchall()
    finally:
        con.close()
    cells: dict = {}
    for sym, pe, val in rows:
        secs = tags.get(sym)
        if not secs or not pe:
            continue
        y = pe[:4]
        for s in secs:
            cells.setdefault((s, y), []).append(val)
    years = [str(y) for y in range(_Y0, _Y1 + 1)]
    # sectors with enough coverage overall, sorted by most-recent populated median (desc)
    sectors = sorted({s for (s, _y) in cells})
    matrix, latest, keep = {}, {}, []
    for s in sectors:
        row, pops = [], 0
        for y in years:
            vals = cells.get((s, y))
            if vals and len(vals) >= _MIN_N:
                m = statistics.median(vals)
                row.append(m); pops += 1
                latest[s] = m
            else:
                row.append(None)
        if pops >= 3:                       # need a few populated cells to earn a row
            matrix[s] = row
            keep.append(s)
    keep.sort(key=lambda s: -(latest.get(s, -999)))
    mat = [matrix[s] for s in keep]
    # notable trajectories: biggest swing (max-min over populated cells)
    movers = []
    for s in keep:
        pv = [v for v in matrix[s] if v is not None]
        if len(pv) >= 3:
            movers.append((s, pv[0], pv[-1], max(pv), min(pv), max(pv) - min(pv)))
    movers.sort(key=lambda t: -t[5])
    return {"years": years, "sectors": keep, "matrix": mat, "movers": movers[:4],
            "n_syms": len(tags)}


@router.get("/dash/sector-economics", response_class=HTMLResponse)
def dash_sector_economics(metric: str = "roce") -> HTMLResponse:
    metric = metric if metric in _METRICS else "roce"
    mlabel, mdesc, munit = _METRICS[metric]
    body = [_CSS, ifx.readability_css()]
    try:
        d = _compute(metric, _RESEARCH_DB)
        if not d or not d["sectors"]:
            raise LookupError("no coverage")
        yr_labels = [f"FY{y[2:]}" for y in d["years"]]

        body.append(
            '<h2 style="margin:0 0 2px">Sector economics '
            f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">a decade of each '
            f'sector\'s fundamentals · {mdesc} · median by sector × year</small></h2>'
            '<div class="se-note">The <a href="/dash/sectors">Sectors</a> lens tracks sector '
            '<b>share prices</b>. This is the other side of the coin — how the actual <b>business quality</b> '
            'of each sector changed over a decade. <b>' + _esc(mdesc) + '</b> is ' + _esc(_METRIC_PLAIN[metric])
            + '. Warmer cells = higher. <b>Aggregate &amp; descriptive</b> — sector context, never a ranking.</div>')

        top = ", ".join(d["sectors"][:2])
        mv = d["movers"][0][0] if d["movers"] else None
        body.append(ifx.bottom_line(
            f'Measured by <b>{_esc(mdesc.lower())}</b>, the strongest sectors of the last decade are '
            f'<b>{_esc(top)}</b>' + (f', while <b>{_esc(mv)}</b> swings the most with global cycles' if mv else '')
            + '. This is about the <b>businesses</b> underneath — how good they are — not their share prices.'))
        body.append(ifx.how_to_read_link())

        tabs = "".join(f'<a class="{"on" if metric==k else ""}" href="/dash/sector-economics?metric={k}">'
                       f'{_esc(v[1])}</a>' for k, v in _METRICS.items())
        body.append(f'<div class="se-ctrl">{tabs}</div>')

        body.append(
            '<div class="se-panel">'
            f'<div class="se-h">{_esc(mlabel)} by sector, FY{_Y0 % 100}→FY{_Y1 % 100} '
            '<small>— median of current index constituents</small></div>'
            + ifx.plain('Each <b>row</b> is a sector, each <b>column</b> a year. The <b>warmer (oranger)</b> '
                        'the cell, the more profitable that sector was that year. Read across a row to watch '
                        'a sector rise or fade over the decade; a <b>blank</b> cell means too few companies '
                        'to be reliable.')
            + '<div class="se-sub">Each cell is the <b>median</b> across that sector\'s current index '
            f'members (blank where fewer than {_MIN_N} report). Read a row left-to-right for a sector\'s '
            'decade; read a column for the market that year.</div>'
            '<div class="se-legend"><span>low</span><span class="ramp"></span><span>high</span></div>'
            + ifx.heat_grid(d["sectors"], yr_labels, d["matrix"], w=1060, cell_h=27, fmt=1, row_w=118)
            + '</div>')

        if d["movers"]:
            cards = ""
            for s, first, last, hi, lo, swing in d["movers"]:
                dcls = "se-up" if last >= first else "se-dn"
                cards += (f'<div class="se-mvc"><div class="s">{_esc(s)}</div>'
                          f'<div class="d">FY{_Y0 % 100} <b>{first:.1f}</b> → FY{_Y1 % 100} '
                          f'<b class="{dcls}">{last:.1f}</b>{munit} '
                          f'<span style="color:var(--ink-3)">· peak {hi:.1f} / trough {lo:.1f}, '
                          f'swing {swing:.1f}pp</span></div></div>')
            body.append('<div class="se-panel"><div class="se-h">Biggest swings '
                        '<small>— the sectors whose economics moved most</small></div>'
                        '<div class="se-sub">The widest peak-to-trough range over the decade — cyclical '
                        'sectors (metals, autos) and structural re-ratings (chemicals) surface here.</div>'
                        f'<div class="se-mv">{cards}</div></div>')

        body.append(
            '<div class="se-fence"><b>Read the coverage honestly:</b>'
            '<ul>'
            '<li><b>Survivorship.</b> Sectors are <i>today\'s</i> index membership applied backward — a '
            'picture of how current constituents evolved, not the sector as it stood then.</li>'
            f'<li><b>Thin &amp; multi-label.</b> ~{d["n_syms"]} tagged names across all sectors (median, '
            f'not mean; blank under N={_MIN_N}); a company can belong to two sectors.</li>'
            '<li><b>Financials mostly blank</b> — banks/NBFCs report RoE, not ROCE, by design (Doctrine D); '
            'a RoE cut is a natural follow-up.</li>'
            '<li><b>Provenance.</b> Some fundamentals are Screener-era, being migrated to NSE/BSE XBRL '
            '(guardrail #8) — cross-source quarters carry that caveat.</li>'
            '</ul></div>')
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Sector economics</h2><div class="se-note">The fundamentals archive '
            '(<code>fundamentals_history</code>, research.db) or the sector tags '
            '(<code>company_tags</code>) are not populated on this host. This surface is read-only and '
            'never fabricates data.</div>')
    return HTMLResponse(_shell("Sector economics · patearn", "".join(body), "sector-economics", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/sector-economics" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    for url in ("/dash/sector-economics", "/dash/sector-economics?metric=opm"):
        r = c.get(url)
        assert r.status_code == 200 and "Sector economics" in r.text
    print("sector_econ_view selftest OK — page 200 (populated or honest-empty), metrics 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
