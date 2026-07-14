"""Insider activity — SEBI PIT disclosures as a decision lens (D94 queue #1, S86).

Surfaces `insider_events` (src/automation/insider_events.py — 10K+ primary-source
NSE filings): every promoter / director / KMP transaction, CLASSIFIED so the
signal isn't buried in plumbing — open-market conviction buys vs caution sells vs
pledge distress vs ESOP/gift/inter-se noise. Two reads on one page:

  * the per-symbol BOARD — who principals are net-buying with their own money
    (the module's PIT `aggregate()`: supersede-collapsed, disclosure-date
    anchored, value-based per Ramana's rupees-not-shares principle);
  * the raw event TAPE — every filing, filterable, nothing hidden.

DESCRIPTIVE ONLY — a "skin in the game" read, not a buy list; no return edge is
claimed. Isolated view module (growth_view pattern): own router, reuses
dashboard._shell, mounted durably via v2_surfaces._ROUTER_SPECS; the flag logic
lives in insider_events.flagged_symbols so this page, the strategist card, the
home pillar and the board-health gate can never disagree.

Route: /dash/insider  [?window=30|90|180] [?cls=conviction|caution|…] [?sym=X] [?min_cr=N]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx  # shared readability scaffold + fence() vocabulary (S-C)
from src.automation import insider_events as IE

router = APIRouter()

_SIG_CHIP = {
    "conviction":    ("CONVICTION", "background:var(--up-dim);color:var(--up)"),
    "caution":       ("CAUTION", "background:var(--down-dim);color:var(--down)"),
    "buy_other":     ("buy", "background:var(--up-dim);color:var(--up);opacity:.65"),
    "sell_other":    ("sell", "background:var(--down-dim);color:var(--down);opacity:.65"),
    "pledge_risk":   ("PLEDGE RISK", "background:rgba(240,136,62,.15);color:#f0883e"),
    "pledge_relief": ("pledge release", "background:rgba(88,166,255,.15);color:#58a6ff"),
    "plumbing":      ("plumbing", "background:var(--bg-3);color:var(--ink-3)"),
    "ignore":        ("—", "background:var(--bg-3);color:var(--ink-3)"),
}

_CSS = """
<style>
.iv-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.iv-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.iv-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.iv-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.iv-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.iv-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.iv-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.iv-h small{font-weight:400;color:var(--ink-3);}
table.iv{border-collapse:collapse;width:100%;font-size:12.5px;}
table.iv th{position:sticky;top:0;background:var(--bg-1);text-align:right;padding:6px 9px;color:var(--ink-2);
  border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;}
table.iv th.l,table.iv td.l{text-align:left;}
table.iv td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.iv td.num{text-align:right;font-variant-numeric:tabular-nums;}
table.iv tr:hover td{background:#11161d;}
.iv-sym{font-weight:700;color:var(--ink);}
.iv-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;letter-spacing:.2px;}
.iv-pos{color:var(--up);} .iv-neg{color:var(--down);} .iv-mut{color:var(--ink-3);}
.iv-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 10px;}
.iv-ctrl a{padding:4px 11px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;
  text-decoration:none;white-space:nowrap;}
.iv-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.iv-ctrl input{background:var(--bg-1);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:5px 9px;font-size:12.5px;min-width:220px;}
.iv-count{color:var(--ink-3);font-size:12px;margin-left:auto;}
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
  wire('ivBoard','ivBoardF','ivBoardC');
  wire('ivTape','ivTapeF','ivTapeC');
})();
</script>
"""


def _cr(v) -> str:
    """value_rs → '₹x.x cr' (dash when absent)."""
    if not v:
        return "—"
    return f"₹{v / 1e7:,.1f}cr"


def _chip(sig: str) -> str:
    label, style = _SIG_CHIP.get(sig or "ignore", _SIG_CHIP["ignore"])
    return f'<span class="iv-chip" style="{style}">{_esc(label)}</span>'


def _tiles(aggs: dict, flagged: list, as_of: str) -> str:
    buy30 = sum(a["open_market_buy_value_30d"] for a in aggs.values())
    sell90 = sum(a["open_market_sell_value_90d"] for a in aggs.values())
    pledge_names = sum(1 for a in aggs.values() if a["pledge_adverse_events_90d"] > 0)
    cluster = sum(1 for a in aggs.values() if a["promoter_cluster_buy_30d"] >= 2)
    t = [
        (str(len(flagged)), "Fresh conviction", "principals net-buying, bought in last 30d", "var(--up)"),
        (_cr(buy30), "Principal buys · 30d", "open-market only (plumbing excluded)", "var(--up)"),
        (_cr(sell90), "Principal sells · 90d", "open-market caution tape", "var(--down)"),
        (str(cluster), "Cluster buys · 30d", "≥2 distinct principal buyers", "#d2a8ff"),
        (str(pledge_names), "Pledge-risk names · 90d", "pledge created / invoked", "#f0883e"),
    ]
    tiles = "".join(
        f'<div class="iv-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="iv-tiles">{tiles}</div>'


def _board(aggs: dict) -> str:
    rows = [(s, a) for s, a in aggs.items()
            if a["open_market_buy_value_90d"] or a["open_market_sell_value_90d"]
            or a["pledge_adverse_events_90d"]]
    rows.sort(key=lambda x: -x[1]["open_market_buy_value_30d"])
    if not rows:
        return '<div class="iv-note">No principal open-market activity in the window.</div>'
    trs = []
    for s, a in rows[:300]:
        net = a["net_promoter_cashflow_90d"]
        ncls = "iv-pos" if net > 0 else ("iv-neg" if net < 0 else "iv-mut")
        trs.append(
            f'<tr><td class="l"><a class="row" href="/dash/stock?sym={_esc(s)}">'
            f'<span class="iv-sym">{_esc(s)}</span></a></td>'
            f'<td class="l">{_chip(a["insider_signal_class"])}</td>'
            f'<td class="num" data-sort="{a["open_market_buy_value_30d"]}">{_cr(a["open_market_buy_value_30d"])}</td>'
            f'<td class="num" data-sort="{a["open_market_buy_value_90d"]}">{_cr(a["open_market_buy_value_90d"])}</td>'
            f'<td class="num" data-sort="{a["open_market_sell_value_90d"]}">{_cr(a["open_market_sell_value_90d"])}</td>'
            f'<td class="num {ncls}" data-sort="{net}">{_cr(abs(net)) if net else "—"}{"" if not net else (" in" if net > 0 else " out")}</td>'
            f'<td class="num" data-sort="{a["promoter_cluster_buy_30d"]}">{a["promoter_cluster_buy_30d"] or "—"}</td>'
            f'<td class="num" data-sort="{a["pledge_adverse_events_90d"]}">{a["pledge_adverse_events_90d"] or "—"}</td>'
            f'<td class="num" data-sort="{a["n_events_known"]}">{a["n_events_known"]}</td></tr>')
    head = ('<tr><th class="l">Symbol</th><th class="l">Verdict</th>'
            '<th data-t="n">Buys 30d</th><th data-t="n">Buys 90d</th><th data-t="n">Sells 90d</th>'
            '<th data-t="n">Net 90d</th><th data-t="n">Cluster</th><th data-t="n">Pledge ev.</th>'
            '<th data-t="n">Filings</th></tr>')
    return (f'<div class="iv-ctrl"><input id="ivBoardF" placeholder="Filter symbols…"/>'
            f'<span class="iv-count" id="ivBoardC"></span></div>'
            f'<div style="max-height:52vh;overflow:auto"><table class="iv" id="ivBoard">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tape(conn, window: int, cls: str, sym: str, min_cr: float) -> str:
    where, params = ["disclosure_dt >= date((SELECT MAX(disclosure_dt) FROM insider_events), ?)"], [f"-{window} days"]
    if cls:
        where.append("signal_class = ?"); params.append(cls)
    if sym:
        where.append("symbol = ?"); params.append(sym.upper())
    if min_cr > 0:
        where.append("COALESCE(value_rs,0) >= ?"); params.append(min_cr * 1e7)
    rows = conn.execute(
        "SELECT disclosure_dt, transaction_dt, symbol, category, txn_class, signal_class, "
        "shares, value_rs, mode, amendment_flag, source_url FROM insider_events "
        f"WHERE {' AND '.join(where)} ORDER BY disclosure_dt DESC, value_rs DESC LIMIT 400",
        params).fetchall()
    if not rows:
        return '<div class="iv-note">No filings match this filter.</div>'
    trs = []
    for r in rows:
        amend = ' <span class="iv-mut" title="revised filing — supersedes the original (AUD-08)">✎</span>' if r["amendment_flag"] else ""
        trs.append(
            f'<tr><td class="l iv-mut">{_esc(str(r["disclosure_dt"])[:10])}</td>'
            f'<td class="l"><a class="row" href="/dash/insider?sym={_esc(r["symbol"])}">'
            f'<span class="iv-sym">{_esc(r["symbol"])}</span></a>{amend}</td>'
            f'<td class="l iv-mut">{_esc((r["category"] or "—")[:26])}</td>'
            f'<td class="l">{_chip(r["signal_class"])}</td>'
            f'<td class="l iv-mut">{_esc((r["txn_class"] or "").replace("_", " ").lower())}</td>'
            f'<td class="num" data-sort="{r["shares"] or 0}">{f"{int(r[6]):,}" if r["shares"] else "—"}</td>'
            f'<td class="num" data-sort="{r["value_rs"] or 0}">{_cr(r["value_rs"])}</td>'
            f'<td class="l iv-mut" title="{_esc(r["mode"] or "")}">{_esc((r["mode"] or "—")[:34])}</td>'
            + (f'<td class="l"><a href="{_esc(r["source_url"])}" target="_blank" rel="noopener" '
               f'title="the XBRL disclosure document on the NSE archive — the primary source '
               f'this row was parsed from">⇗</a></td>' if r["source_url"]
               else '<td class="l iv-mut">—</td>') + '</tr>')
    head = ('<tr><th class="l">Disclosed</th><th class="l">Symbol</th><th class="l">Who</th>'
            '<th class="l">Signal</th><th class="l">Type</th><th data-t="n">Shares</th>'
            '<th data-t="n">Value</th><th class="l">Mode (as filed)</th>'
            '<th class="l" title="link to the filed XBRL document on nsearchives.nseindia.com">Filing</th></tr>')
    return (f'<div class="iv-ctrl"><input id="ivTapeF" placeholder="Filter the tape…"/>'
            f'<span class="iv-count" id="ivTapeC"></span></div>'
            f'<div style="max-height:56vh;overflow:auto"><table class="iv" id="ivTape">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cls_tabs(active: str, window: int) -> str:
    tabs = [("", "All"), ("conviction", "Conviction buys"), ("caution", "Caution sells"),
            ("pledge_risk", "Pledge risk"), ("pledge_relief", "Pledge release"),
            ("buy_other", "Other buys"), ("sell_other", "Other sells"), ("plumbing", "Plumbing")]
    parts = [f'<a class="{"on" if active == k else ""}" '
             f'href="/dash/insider?window={window}&cls={k}">{_esc(l)}</a>' for k, l in tabs]
    for w in (30, 90, 180):
        parts.append(f'<a class="{"on" if window == w else ""}" '
                     f'href="/dash/insider?window={w}&cls={active}">{w}d</a>')
    return f'<div class="iv-ctrl">{"".join(parts)}</div>'


@router.get("/dash/insider", response_class=HTMLResponse)
def dash_insider(window: int = 90, cls: str = "", sym: str = "",
                 min_cr: float = 0.0) -> HTMLResponse:
    window = window if window in (30, 90, 180) else 90
    body_parts = [_CSS, ifx.readability_css()]
    as_of = None
    try:
        with get_conn() as conn:
            has = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                               "AND name='insider_events'").fetchone()
            if not has:
                raise LookupError("insider_events absent")
            aggs, as_of = IE.universe_aggregate(conn, days=185)
            flagged, _ = IE.flagged_symbols(conn, as_of)
            body_parts.append(
                '<h2 style="margin:0 0 2px">Insider activity <small style="color:var(--ink-3);'
                f'font-size:12px;font-weight:400">SEBI PIT disclosures · as of {_esc(str(as_of)[:10] if as_of else "—")} '
                f'· {ifx.fence("not_advice", "disclosure-date anchored (what was knowable when)")}</small></h2>'
                '<div class="iv-note">Principals = promoters / directors / KMP acting with their own money. '
                'The headline reads only <b>open-market</b> buys and sells — ESOPs, gifts, inter-se transfers and '
                'other plumbing are classified out (visible in the tape below). Revised filings supersede their '
                'originals, so nothing is double-counted. All flows in <b>rupees, not share counts</b>. '
                '<b>Source:</b> NSE\'s corporate-filings register + each disclosure\'s own XBRL '
                'instance document — every tape row links (⇗) to the filed document on the NSE '
                'archive; nothing here is scraped from a third-party site. '
                '<a href="/dash/glossary?q=insider">glossary →</a></div>')
            body_parts.append(ifx.bottom_line(
                'Where insiders — promoters, directors, KMP — put <b>their own money</b>: net '
                'open-market buying vs selling (in rupees) over 30/90 days. Clustered buying is a '
                'conviction tell, clustered selling a caution — <b>context, not a trade</b>.'))
            body_parts.append(ifx.how_to_read_link())
            body_parts.append(_tiles(aggs, flagged, as_of or ""))
            body_parts.append('<div class="iv-h">By symbol <small>— PIT roll-up, 30/90-day windows, '
                              'supersede-collapsed; sorted by fresh buying</small></div>')
            body_parts.append(_board(aggs))
            body_parts.append(f'<div class="iv-h">The tape <small>— every filing, newest first '
                              f'(window {window}d{", " + _esc(sym.upper()) if sym else ""})</small></div>')
            body_parts.append(_cls_tabs(cls, window))
            body_parts.append(_tape(conn, window, cls, sym, min_cr))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body_parts.append(
            '<h2>Insider activity</h2><div class="iv-note">The <code>insider_events</code> table is not '
            'populated on this host. It is ingested nightly on production from NSE PIT disclosures '
            '(<code>src/automation/insider_events.py</code>). This surface is read-only and never '
            'fabricates data.</div>')
    body_parts.append(_JS)
    return HTMLResponse(_shell("Insider activity · patearn", "".join(body_parts),
                               "insider", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/insider" not in paths:
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
    r = c.get("/dash/insider")
    assert r.status_code == 200, r.status_code
    assert "Insider activity" in r.text
    # filters + tabs must never 500, with or without data
    assert c.get("/dash/insider?window=30&cls=conviction").status_code == 200
    assert c.get("/dash/insider?sym=RELIANCE&min_cr=5").status_code == 200
    print("insider_view selftest OK — page 200 (populated or honest-empty), filters 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
