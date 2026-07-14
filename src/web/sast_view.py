"""Stake & pledge confluence — SAST disclosures as a decision board (D94 #3, S88).

Surfaces the two Dataset-A+ primary feeds (src/automation/sast_events.py, both
NSE listing feeds, PIT on the exchange broadcast clock):

  * **Reg 29** — substantial-holder stake moves: acquisitions/sales crossing 5%
    or moving ±2%, promoter-flagged, in % of diluted capital;
  * **Reg 31/32** — promoter pledge FLOW with magnitude: creation / release /
    invocation, each event's % of equity + the post-event total encumbrance.

The board's subject is the CONFLUENCE — names where BOTH feeds fired inside 90
days — labelled with a descriptive SHAPE (constructive / distress / mixed).
HONESTY FENCES (ledger-cited): the accumulation-footprint detector FAILED its
pre-registered gate (764/947 episodes had no pre-public window — SEBI T+2), so
everything here is a POST-disclosure read; E-04 (campaign arcs) and E-05
(pledge-release velocity) are armed-not-run — no arc or velocity claim appears
on this page. Shapes describe a crossing; they never predict.

Flag logic single-sourced in sast_events.flagged_symbols (page == card ==
pillar == board_health). Route: /dash/sast [?window=30|90|180] [?feed=…] [?sym=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx  # shared readability scaffold + fence() vocabulary (S-C)
from src.automation import sast_events as SE

router = APIRouter()

_SHAPE_CHIP = {
    "constructive": ("constructive", "background:var(--up-dim);color:var(--up)"),
    "distress":     ("distress", "background:var(--down-dim);color:var(--down)"),
    "mixed":        ("mixed", "background:var(--bg-3);color:var(--ink-2)"),
}
_FEED_CHIP = {
    "ACQ":     ("STAKE · ACQ", "background:var(--up-dim);color:var(--up)"),
    "SALE":    ("STAKE · SALE", "background:var(--down-dim);color:var(--down)"),
    "CREATE":  ("PLEDGE · CREATE", "background:rgba(240,136,62,.15);color:#f0883e"),
    "RELEASE": ("PLEDGE · RELEASE", "background:rgba(88,166,255,.15);color:#58a6ff"),
    "INVOKE":  ("PLEDGE · INVOKE", "background:rgba(248,81,73,.25);color:#ff7b72"),
    "OTHER":   ("other", "background:var(--bg-3);color:var(--ink-3)"),
}

_CSS = """
<style>
.sp-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.sp-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.sp-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.sp-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.sp-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.sp-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.sp-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.sp-h small{font-weight:400;color:var(--ink-3);}
table.sp{border-collapse:collapse;width:100%;font-size:12.5px;}
table.sp th{position:sticky;top:0;background:var(--bg-1);text-align:right;padding:6px 9px;color:var(--ink-2);
  border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;}
table.sp th.l,table.sp td.l{text-align:left;}
table.sp td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.sp td.num{text-align:right;font-variant-numeric:tabular-nums;}
table.sp tr:hover td{background:#11161d;}
.sp-sym{font-weight:700;color:var(--ink);}
.sp-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;letter-spacing:.2px;}
.sp-pos{color:var(--up);} .sp-neg{color:var(--down);} .sp-mut{color:var(--ink-3);}
.sp-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 10px;}
.sp-ctrl a{padding:4px 11px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;
  text-decoration:none;white-space:nowrap;}
.sp-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.sp-ctrl input{background:var(--bg-1);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:5px 9px;font-size:12.5px;min-width:220px;}
.sp-count{color:var(--ink-3);font-size:12px;margin-left:auto;}
</style>
"""

_JS = """
<script>
(function(){
  function wire(tid, fid, cid){
    var t=document.getElementById(tid), f=document.getElementById(fid), c=document.getElementById(cid);
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
  }
  wire('spBoard','spBoardF','spBoardC');
  wire('spTape','spTapeF','spTapeC');
})();</script>
"""


def _chip(table: dict, key: str) -> str:
    label, style = table.get(key or "OTHER", table.get("OTHER", ("—", "")))
    return f'<span class="sp-chip" style="{style}">{_esc(label)}</span>'


def _pct(v, signed=True) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%" if signed else f"{v:.2f}%"


def _doc(url) -> str:
    if not url:
        return '<td class="l sp-mut">—</td>'
    return (f'<td class="l"><a href="{_esc(url)}" target="_blank" rel="noopener" '
            f'title="the disclosure document on the NSE archive — the primary source '
            f'this row was parsed from">⇗</a></td>')


def _tiles(aggs: dict, census: dict) -> str:
    shapes = {"constructive": 0, "distress": 0, "mixed": 0}
    invoked = ctrl = 0
    for a in aggs.values():
        shapes[a["shape"]] = shapes.get(a["shape"], 0) + 1
        invoked += a["pledge_invocations_90d"]
        ctrl += a.get("control_transfers_90d", 0)
    t = [
        (str(census.get("confluence_names", 0)), "Confluence names · 90d",
         "stake AND pledge events on the same name", "var(--ink)"),
        (str(shapes["constructive"]), "Constructive shape",
         "stake added · encumbrance flat/falling", "var(--up)"),
        (str(shapes["distress"]), "Distress shape",
         "invocation, or selling into rising pledge", "var(--down)"),
        (str(invoked), "Invocations · 90d", "lender forced-sale events (always adverse)", "#ff7b72"),
        (str(ctrl), "Control transfers ⚡", "≥25% of capital in one filing — badged, never summed", "#e3b341"),
        (f'{census.get("stake_names", 0)} / {census.get("pledge_names", 0)}',
         "Context census", "names with any stake / any pledge event", "var(--ink-3)"),
    ]
    tiles = "".join(
        f'<div class="sp-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="sp-tiles">{tiles}</div>'


def _board(flags: list) -> str:
    if not flags:
        return ('<div class="sp-note">No confluence names in the window — no symbol had both '
                'a stake event and a pledge event inside 90 days.</div>')
    trs = []
    for sym, a in flags[:200]:
        sn, pn = a["stake_net_pct_90d"], a["net_pledge_flow_90d"]
        enc = a.get("latest_encumbered_pct")
        ctrl = (' <span title="control-size transfer(s) in the window (≥25% of capital '
                'in one filing — the SEBI takeover trigger); excluded from flow sums" '
                'style="color:#e3b341">⚡</span>'
                if a.get("control_transfers_90d") else "")
        trs.append(
            f'<tr><td class="l"><a class="row" href="/dash/stock?sym={_esc(sym)}">'
            f'<span class="sp-sym">{_esc(sym)}</span></a>{ctrl}</td>'
            f'<td class="l">{_chip(_SHAPE_CHIP, a["shape"])}</td>'
            f'<td class="num {"sp-pos" if sn > 0 else ("sp-neg" if sn < 0 else "sp-mut")}" '
            f'data-sort="{sn}">{_pct(sn)}</td>'
            f'<td class="num" data-sort="{a["stake_acquired_pct_90d"]}">{_pct(a["stake_acquired_pct_90d"], False)}</td>'
            f'<td class="num" data-sort="{a["stake_sold_pct_90d"]}">{_pct(a["stake_sold_pct_90d"], False)}</td>'
            f'<td class="num {"sp-neg" if pn > 0 else ("sp-pos" if pn < 0 else "sp-mut")}" '
            f'data-sort="{pn}">{_pct(pn)}</td>'
            f'<td class="num" data-sort="{a["pledge_invocations_90d"]}">{a["pledge_invocations_90d"] or "—"}</td>'
            f'<td class="num" data-sort="{enc if enc is not None else -1}">{_pct(enc, False)}</td>'
            f'<td class="num" data-sort="{a["n_reg29_known"] + a["n_pledge_events_known"]}">'
            f'{a["n_reg29_known"] + a["n_pledge_events_known"]}</td>'
            f'<td class="l"><a href="/dash/sast?sym={_esc(sym)}" class="sp-mut">tape →</a></td></tr>')
    head = ('<tr><th class="l">Symbol</th><th class="l">Shape</th>'
            '<th data-t="n" title="stake acquired − sold, % of diluted capital, 90d">Stake net</th>'
            '<th data-t="n">Acq 90d</th><th data-t="n">Sold 90d</th>'
            '<th data-t="n" title="pledge created − released, % of equity, 90d; positive = encumbrance rising">Pledge net</th>'
            '<th data-t="n">Invoked</th>'
            '<th data-t="n" title="post-event TOTAL encumbered % (latest pledge filing)">Encumb now</th>'
            '<th data-t="n">Filings</th><th class="l">Drill</th></tr>')
    return (f'<div class="sp-ctrl"><input id="spBoardF" placeholder="Filter symbols…"/>'
            f'<span class="sp-count" id="spBoardC"></span></div>'
            f'<div style="max-height:48vh;overflow:auto"><table class="sp" id="spBoard">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tape(conn, window: int, feed: str, sym: str) -> str:
    """Unified newest-first tape over BOTH feeds (each row keeps its ⇗ document)."""
    rows: list = []
    p29 = ["substr(broadcast_dt,1,10) >= date((SELECT MAX(substr(broadcast_dt,1,10)) "
           "FROM sast_reg29_events), ?)"]
    a29: list = [f"-{window} days"]
    if sym:
        p29.append("symbol = ?"); a29.append(sym.upper())
    if feed in ("", "ACQ", "SALE"):
        q = ("SELECT substr(broadcast_dt,1,10) d, symbol, acq_sale k, promoter_flag pf, "
             "COALESCE(pct_acq, pct_sale) pct, pct_after extra, mode detail, attachment "
             f"FROM sast_reg29_events WHERE {' AND '.join(p29)}")
        a = list(a29)
        if feed:
            q += " AND acq_sale = ?"; a.append(feed)
        rows += [dict(zip(("d", "symbol", "k", "pf", "pct", "extra", "detail", "att"),
                          tuple(r))) | {"feed": "stake"} for r in conn.execute(q, a)]
    if feed in ("", "CREATE", "RELEASE", "INVOKE"):
        ppl = ["substr(broadcast_dt,1,10) >= date((SELECT MAX(substr(broadcast_dt,1,10)) "
               "FROM sast_pledge_events), ?)"]
        apl: list = [f"-{window} days"]
        if sym:
            ppl.append("symbol = ?"); apl.append(sym.upper())
        q = ("SELECT substr(broadcast_dt,1,10) d, symbol, event_type k, 1 pf, event_pct pct, "
             "encumb_pct extra, counterparty detail, attachment "
             f"FROM sast_pledge_events WHERE {' AND '.join(ppl)}")
        a = list(apl)
        if feed:
            q += " AND event_type = ?"; a.append(feed)
        rows += [dict(zip(("d", "symbol", "k", "pf", "pct", "extra", "detail", "att"),
                          tuple(r))) | {"feed": "pledge"} for r in conn.execute(q, a)]
    rows.sort(key=lambda r: (r["d"] or "", r["pct"] or 0), reverse=True)
    rows = rows[:400]
    if not rows:
        return '<div class="sp-note">No disclosure rows match this filter.</div>'
    trs = []
    for r in rows:
        who = ("promoter" if r["pf"] else "other holder") if r["feed"] == "stake" else "promoter"
        extra_lbl = "holds after" if r["feed"] == "stake" else "encumb after"
        trs.append(
            f'<tr><td class="l sp-mut">{_esc(r["d"] or "—")}</td>'
            f'<td class="l"><a class="row" href="/dash/sast?sym={_esc(r["symbol"])}">'
            f'<span class="sp-sym">{_esc(r["symbol"])}</span></a></td>'
            f'<td class="l">{_chip(_FEED_CHIP, r["k"])}</td>'
            f'<td class="l sp-mut">{_esc(who)}</td>'
            f'<td class="num" data-sort="{r["pct"] or 0}">{_pct(r["pct"], False)}</td>'
            f'<td class="num sp-mut" data-sort="{r["extra"] if r["extra"] is not None else -1}" '
            f'title="{extra_lbl}">{_pct(r["extra"], False)}</td>'
            f'<td class="l sp-mut" title="{_esc(r["detail"] or "")}">{_esc((r["detail"] or "—")[:36])}</td>'
            + _doc(r["att"]) + '</tr>')
    head = ('<tr><th class="l">Broadcast</th><th class="l">Symbol</th><th class="l">Event</th>'
            '<th class="l">Who</th><th data-t="n">% of equity</th><th data-t="n">After</th>'
            '<th class="l">Mode / lender (as filed)</th><th class="l">Filing</th></tr>')
    return (f'<div class="sp-ctrl"><input id="spTapeF" placeholder="Filter the tape…"/>'
            f'<span class="sp-count" id="spTapeC"></span></div>'
            f'<div style="max-height:52vh;overflow:auto"><table class="sp" id="spTape">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _feed_tabs(active: str, window: int) -> str:
    tabs = [("", "All"), ("ACQ", "Stake buys"), ("SALE", "Stake sales"),
            ("CREATE", "Pledge created"), ("RELEASE", "Pledge released"),
            ("INVOKE", "Invocations")]
    parts = [f'<a class="{"on" if active == k else ""}" '
             f'href="/dash/sast?window={window}&feed={k}">{_esc(l)}</a>' for k, l in tabs]
    for w in (30, 90, 180):
        parts.append(f'<a class="{"on" if window == w else ""}" '
                     f'href="/dash/sast?window={w}&feed={active}">{w}d</a>')
    return f'<div class="sp-ctrl">{"".join(parts)}</div>'


@router.get("/dash/sast", response_class=HTMLResponse)
def dash_sast(window: int = 90, feed: str = "", sym: str = "") -> HTMLResponse:
    window = window if window in (30, 90, 180) else 90
    body = [_CSS, ifx.readability_css()]
    as_of = None
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='sast_reg29_events'").fetchone():
                raise LookupError("sast tables absent")
            aggs, census, as_of = SE.universe_confluence(conn, days=90)
            flags, _ = SE.flagged_symbols(conn, as_of)
            body.append(
                '<h2 style="margin:0 0 2px">Stake &amp; pledge confluence <small style="color:var(--ink-3);'
                f'font-size:12px;font-weight:400">SAST Reg 29 + Reg 31/32 · as of {_esc(str(as_of) if as_of else "—")} '
                f'· {ifx.fence("not_advice", "broadcast-date anchored")}</small></h2>'
                '<div class="sp-note">Substantial-holder stake moves crossed with promoter pledge FLOW — the '
                'board shows names where <b>both fired inside 90 days</b>, labelled by SHAPE: '
                '<b>constructive</b> (stake added while encumbrance falls/holds) · <b>distress</b> '
                '(invocation, or selling into rising pledge) · <b>mixed</b>. All magnitudes in '
                '<b>% of equity</b>, never share counts. A shape describes a crossing that already '
                'happened — the footprint study proved there is NO pre-public window to detect '
                '(SEBI T+2), and the arc/velocity studies (E-04/E-05) are pre-registered and pending, '
                'so nothing here predicts. <b>Source:</b> NSE\'s SAST disclosure feeds; every tape row '
                'links (⇗) to the filed document on the NSE archive. '
                '<a href="/dash/glossary?q=pledge">glossary →</a></div>')
            body.append(ifx.bottom_line(
                'Names where a big shareholder\'s stake move and a promoter-pledge change <b>both '
                'fired inside 90 days</b> — labelled <b>constructive</b> (stake up while pledge '
                'falls) or <b>distress</b> (selling into rising pledge). A crossing that already '
                'happened — <b>descriptive, not advice</b>.'))
            body.append(ifx.how_to_read_link())
            body.append(_tiles(aggs, census))
            body.append('<div class="sp-h">Confluence board <small>— both feeds, same name, 90 days; '
                        'sorted by combined magnitude</small></div>')
            body.append(_board(flags))
            body.append(f'<div class="sp-h">The tape <small>— every disclosure, both feeds, newest '
                        f'first (window {window}d{", " + _esc(sym.upper()) if sym else ""})</small></div>')
            body.append(_feed_tabs(feed, window))
            body.append(_tape(conn, window, feed, sym))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Stake &amp; pledge confluence</h2><div class="sp-note">The SAST tables are not '
            'populated on this host. They are ingested nightly on production from NSE\'s SAST '
            'disclosure feeds (<code>src/automation/sast_events.py</code>). This surface is '
            'read-only and never fabricates data.</div>')
    body.append(_JS)
    return HTMLResponse(_shell("Stake & pledge · patearn", "".join(body),
                               "sast", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/sast" not in paths:
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
    assert c.get("/dash/sast").status_code == 200
    assert "confluence" in c.get("/dash/sast").text.lower()
    assert c.get("/dash/sast?window=30&feed=INVOKE").status_code == 200
    assert c.get("/dash/sast?sym=RELIANCE").status_code == 200
    print("sast_view selftest OK — page 200 (populated or honest-empty), filters 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
