"""Holdings QoQ — the shareholding-pattern quarter-over-quarter deltas board
(D94 queue #4, S90).

Surfaces `shareholding_history` (research.db): promoter / FII / DII / public /
pledge levels per quarter, rendered as the DELTAS that matter — who added, who
trimmed, quarter over quarter, in percentage points of equity.

PROVENANCE (guardrail #8, disclosed here and on-page): the historical archive is
the FROZEN Screener-era collection — read-only, never re-fetched, being replaced
quarter-by-quarter by `shareholding_xbrl.py` (NSE SHP XBRL filings, the primary
source; a continuity gate requires XBRL↔archive agreement within 1pp at overlap).
Pairs whose two quarters come from different sources are marked ⓧ. As the
June-2026 filing flood lands (~Jul-21), the latest-quarter column turns primary
organically — the census tile shows that takeover happening.

Pairing honesty: quarters are calendar buckets; deltas only pair a symbol's two
LATEST buckets, and only ADJACENT quarters can flag (a gapped pair is shown,
labelled, never counted as a QoQ shift). Flag = |Δ| ≥ 1.0 pp on Promoters, FIIs
or DIIs. Descriptive — holder-mix facts, not signals; no return edge is claimed.

Flag logic single-sourced in shareholding_xbrl.flagged_symbols (page == card ==
pillar == board_health). Route: /dash/shp [?sym=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web.dashboard import _shell, _esc
from src.automation import shareholding_xbrl as SX

router = APIRouter()

_CSS = """
<style>
.hq-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.hq-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.hq-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.hq-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.hq-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.hq-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.hq-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.hq-h small{font-weight:400;color:var(--ink-3);}
table.hq{border-collapse:collapse;width:100%;font-size:12.5px;}
table.hq th{position:sticky;top:0;background:var(--bg-1);text-align:right;padding:6px 9px;color:var(--ink-2);
  border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;}
table.hq th.l,table.hq td.l{text-align:left;}
table.hq td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.hq td.num{text-align:right;font-variant-numeric:tabular-nums;}
table.hq tr:hover td{background:#11161d;}
.hq-sym{font-weight:700;color:var(--ink);}
.hq-pos{color:var(--up);} .hq-neg{color:var(--down);} .hq-mut{color:var(--ink-3);}
.hq-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 10px;}
.hq-ctrl input{background:var(--bg-1);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:5px 9px;font-size:12.5px;min-width:220px;}
.hq-count{color:var(--ink-3);font-size:12px;margin-left:auto;}
</style>
"""

_JS = """
<script>
(function(){
  var t=document.getElementById('hqBoard'), f=document.getElementById('hqBoardF'), c=document.getElementById('hqBoardC');
  if(!t) return;
  function recount(){ if(!c)return; var rs=t.tBodies[0].rows,n=0;
    for(var i=0;i<rs.length;i++){ if(rs[i].style.display!=='none') n++; } c.textContent=n+' rows'; }
  if(f){ f.addEventListener('input',function(){
    var q=f.value.toLowerCase(), rs=t.tBodies[0].rows;
    for(var i=0;i<rs.length;i++){ rs[i].style.display = rs[i].textContent.toLowerCase().indexOf(q)>=0?'':'none'; }
    recount(); }); }
  if(t.tHead){ var ths=t.tHead.rows[0].cells;
    for(var k=0;k<ths.length;k++){ (function(th){
      var dir=1;
      th.addEventListener('click',function(){
        var col=th.cellIndex, typ=th.getAttribute('data-t')||'s';
        var tb=t.tBodies[0], rows=Array.prototype.slice.call(tb.rows); dir=-dir;
        rows.sort(function(a,b){
          var ca=a.cells[col], cb=b.cells[col];
          if(typ==='n'){ return ((parseFloat(ca.getAttribute('data-sort'))||-1e18)
                                -(parseFloat(cb.getAttribute('data-sort'))||-1e18))*dir; }
          var va=(ca.getAttribute('data-sort')||ca.textContent||'').trim().toLowerCase();
          var vb=(cb.getAttribute('data-sort')||cb.textContent||'').trim().toLowerCase();
          return va<vb?-dir : va>vb?dir : 0;
        });
        rows.forEach(function(r){ tb.appendChild(r); });
      });
    })(ths[k]); } }
  recount();
})();</script>
"""


def _d(v, cls=True) -> str:
    """Render a delta in pp with sign + colour; '—' when unpaired."""
    if v is None:
        return '<span class="hq-mut">—</span>'
    c = ("hq-pos" if v > 0 else "hq-neg" if v < 0 else "hq-mut") if cls else ""
    return f'<span class="{c}">{v:+.2f}</span>'


def _sortv(v):
    return v if v is not None else -1e18


def _tiles(rows: dict, flags: list, census: dict) -> str:
    def _cnt(metric, sign):
        n = 0
        for _s, r in flags:
            d = r["metrics"].get(metric, (None, None, None))[2]
            if d is not None and (d >= SX.MATERIAL_PP if sign > 0 else d <= -SX.MATERIAL_PP):
                n += 1
        return n
    xb, ar = census.get("xbrl_cells", 0), census.get("archive_cells", 0)
    t = [
        (str(len(flags)), "Material shifts", f"|Δ| ≥ {SX.MATERIAL_PP:.0f}pp on promoter/FII/DII, adjacent quarters", "var(--ink)"),
        (str(_cnt("Promoters", +1)), "Promoters added ≥1pp", "skin in the game rising", "var(--up)"),
        (str(_cnt("Promoters", -1)), "Promoters trimmed ≥1pp", "descriptive — reasons vary", "var(--down)"),
        (str(_cnt("FIIs", +1)), "FII adds ≥1pp", "foreign institutions building", "#79c0ff"),
        (str(sum(1 for r in rows.values() if r.get("structural"))), "Structural ⚡",
         "≥25pp on a class — ownership event, not drift", "#e3b341"),
        (f'{census.get("in_latest_quarter", 0)}', f'In {census.get("latest_quarter", "—")}',
         f'{census.get("symbols_paired", 0)} symbols paired overall', "var(--ink-3)"),
        (f'{xb}', "Primary-source cells", f'{ar} frozen-archive cells · ⓧ = mixed pair · takeover in progress',
         "#7ee787"),
    ]
    tiles = "".join(
        f'<div class="hq-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="hq-tiles">{tiles}</div>'


def _board(rows: dict) -> str:
    # material movers first (the flag order), then the rest of the paired universe
    def _maxshift(r):
        return max((abs(d[2]) for m, d in r["metrics"].items()
                    if m in ("Promoters", "FIIs", "DIIs") and d[2] is not None), default=0.0)
    ordered = sorted(rows.items(), key=lambda kv: -_maxshift(kv[1]))
    trs = []
    for sym, r in ordered[:400]:
        met = r["metrics"]

        def g(m, i):
            t = met.get(m)
            return t[i] if t else None
        marks = ""
        if r.get("structural"):
            marks += (' <span style="color:#e3b341" title="structural ownership event — a holder '
                      'class moved ≥25pp in one quarter (new promoter via acquisition, restructure); '
                      'shown, never counted as holder-mix drift">⚡</span>')
        if r["mixed"]:
            marks += (' <span class="hq-mut" title="mixed provenance: one quarter from the frozen '
                      'archive, one from NSE XBRL (continuity-gated to ≤1pp at overlap)">ⓧ</span>')
        if not r["adjacent"]:
            marks += (' <span style="color:#e3b341" title="non-adjacent quarters — a reporting gap; '
                      'shown, never flagged as a QoQ shift">◌</span>')
        dP, dF, dD, dPub, dPl = (g("Promoters", 2), g("FIIs", 2), g("DIIs", 2),
                                 g("Public", 2), g("Promoter Pledge", 2))
        trs.append(
            f'<tr><td class="l"><a class="row" href="/dash/stock?sym={_esc(sym)}">'
            f'<span class="hq-sym">{_esc(sym)}</span></a>{marks}</td>'
            f'<td class="l hq-mut">{_esc(r["q1"])} → {_esc(r["q0"])}</td>'
            f'<td class="num" data-sort="{_sortv(dP)}">{_d(dP)}</td>'
            f'<td class="num" data-sort="{_sortv(g("Promoters", 0))}">'
            f'{g("Promoters", 0) if g("Promoters", 0) is not None else "—"}</td>'
            f'<td class="num" data-sort="{_sortv(dF)}">{_d(dF)}</td>'
            f'<td class="num" data-sort="{_sortv(dD)}">{_d(dD)}</td>'
            f'<td class="num" data-sort="{_sortv(dPub)}">{_d(dPub)}</td>'
            f'<td class="num" data-sort="{_sortv(dPl)}">{_d(dPl)}</td>'
            f'<td class="num" data-sort="{_sortv(g("Promoter Pledge", 0))}">'
            f'{g("Promoter Pledge", 0) if g("Promoter Pledge", 0) is not None else "—"}</td></tr>')
    head = ('<tr><th class="l">Symbol</th><th class="l">Quarters</th>'
            '<th data-t="n" title="promoter holding, percentage points QoQ">Δ Prom</th>'
            '<th data-t="n" title="promoter holding now, % of equity">Prom now</th>'
            '<th data-t="n">Δ FII</th><th data-t="n">Δ DII</th><th data-t="n">Δ Public</th>'
            '<th data-t="n" title="promoter pledge, pp QoQ (sparse pre-flood)">Δ Pledge</th>'
            '<th data-t="n" title="promoter pledge now, % (where filed)">Pledge now</th></tr>')
    return (f'<div class="hq-ctrl"><input id="hqBoardF" placeholder="Filter symbols…"/>'
            f'<span class="hq-count" id="hqBoardC"></span></div>'
            f'<div style="max-height:62vh;overflow:auto"><table class="hq" id="hqBoard">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _series(sym: str) -> str:
    """Per-symbol quarter series (?sym=X) — every stored quarter, per metric,
    provenance-marked. Opens research.db read-only via the module's path."""
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{SX.RESEARCH_DB}?mode=ro", uri=True)
    except Exception:  # noqa: BLE001
        return '<div class="hq-note">research.db is not present on this host.</div>'
    try:
        rows = con.execute(
            "SELECT period_end, metric, value, source FROM shareholding_history "
            "WHERE symbol=? AND metric IN ('Promoters','FIIs','DIIs','Public','Promoter Pledge') "
            "ORDER BY period_end DESC LIMIT 120", (sym.upper(),)).fetchall()
    finally:
        con.close()
    if not rows:
        return f'<div class="hq-note">No shareholding history stored for {_esc(sym.upper())}.</div>'
    trs = "".join(
        f'<tr><td class="l hq-mut">{_esc(str(p)[:10])}</td><td class="l">{_esc(m)}</td>'
        f'<td class="num">{v:.2f}</td>'
        f'<td class="l hq-mut">{"NSE-XBRL" if s else "archive (frozen)"}</td></tr>'
        for p, m, v, s in rows)
    return (f'<div class="hq-h">{_esc(sym.upper())} — stored quarters '
            f'<small>(newest first · provenance per row)</small></div>'
            f'<div style="max-height:40vh;overflow:auto"><table class="hq">'
            f'<thead><tr><th class="l">Period end</th><th class="l">Metric</th>'
            f'<th>% of equity</th><th class="l">Source</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div>')


@router.get("/dash/shp", response_class=HTMLResponse)
def dash_shp(sym: str = "") -> HTMLResponse:
    body = [_CSS]
    as_of = None
    try:
        rows, census, as_of = SX.universe_deltas()
        if not rows:
            raise LookupError("no paired shareholding history on this host")
        flags, _ = SX.flagged_symbols()
        body.append(
            '<h2 style="margin:0 0 2px">Holdings · quarter-over-quarter <small style="color:var(--ink-3);'
            f'font-size:12px;font-weight:400">shareholding pattern deltas · latest period '
            f'{_esc(str(as_of)[:10] if as_of else "—")} · descriptive, not advice</small></h2>'
            '<div class="hq-note">Who added and who trimmed, quarter over quarter — promoter / FII / DII / '
            'public / pledge, in <b>percentage points of equity</b>. Deltas pair a symbol\'s two latest '
            'quarters; only ADJACENT quarters can flag (◌ = reporting gap, shown but never counted). '
            '<b>Provenance:</b> history = the frozen archive collection (read-only, never re-fetched); '
            'NEW quarters arrive from <b>NSE SHP XBRL filings</b> (the primary source) and take over the '
            'board organically — ⓧ marks a pair that mixes the two (continuity-gated to ≤1pp agreement '
            'at overlap). Quarterly cadence: the June-2026 filing flood lands through ~Jul-21. '
            '<a href="/dash/glossary?q=holdings">glossary →</a></div>')
        body.append(_tiles(rows, flags, census))
        if sym:
            body.append(_series(sym))
        body.append('<div class="hq-h">The board <small>— biggest movers first; click a column to '
                    're-sort; symbol → dossier</small></div>')
        body.append(_board(rows))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Holdings · quarter-over-quarter</h2><div class="hq-note">'
            '<code>shareholding_history</code> (research.db) is not present on this host. It lives on '
            'production, fed by <code>src/automation/shareholding_xbrl.py</code> (NSE SHP XBRL, nightly). '
            'This surface is read-only and never fabricates data.</div>')
    body.append(_JS)
    return HTMLResponse(_shell("Holdings QoQ · patearn", "".join(body),
                               "shp", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/shp" not in paths:
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
    assert c.get("/dash/shp").status_code == 200
    assert "quarter-over-quarter" in c.get("/dash/shp").text
    assert c.get("/dash/shp?sym=RELIANCE").status_code == 200
    print("shp_view selftest OK — page 200 (populated or honest-empty), drill 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
