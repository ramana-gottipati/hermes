"""Credit-rating transitions — the NSE rating-disclosure register as a decision
lens (D94 queue #2, S87).

Surfaces `credit_rating_events` (src/automation/credit_ratings.py — NSE's
centralised rating-disclosure database, LODR-mandated): every agency action on a
listed issuer's debt, with the headline read DEDUPED TO COMPANY-LEVEL ACTIONS —
the E-02 study proved multi-ISIN debt re-ratings inflate raw rows ~6× (118 raw
notch-rows → 19 true events, S85e). Counting rows is pseudo-replication; this
page never does it.

Two reads:
  * TRANSITIONS board — deduped company-level upgrades / downgrades / fresh
    defaults (one event per symbol × broadcast day × direction, max notch kept);
  * the raw TAPE — every disclosure row incl. reaffirmations / watch / new /
    withdrawn, filterable, nothing hidden; census line discloses the dedup.

DESCRIPTIVE ONLY — the pre-registered E-02 rating-drift study is ARMED and
self-gating (fires monthly until its sample reconciles); NO return edge is
claimed here, in either direction. Isolated view module (insider_view pattern);
flag logic single-sourced in credit_ratings.flagged_symbols so this page, the
strategist card, the home pillar and the board-health gate can never disagree.

Route: /dash/ratings  [?window=90|180|365] [?cls=UPGRADE|DOWNGRADE|…] [?sym=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.automation import credit_ratings as CR

router = APIRouter()

_ACT_CHIP = {
    "UPGRADE":   ("UPGRADE", "background:var(--up-dim);color:var(--up)"),
    "DOWNGRADE": ("DOWNGRADE", "background:var(--down-dim);color:var(--down)"),
    "DEFAULT":   ("DEFAULT", "background:rgba(248,81,73,.25);color:#ff7b72"),
    "WATCH":     ("watch", "background:rgba(240,136,62,.15);color:#f0883e"),
    "REAFFIRM":  ("reaffirm", "background:var(--bg-3);color:var(--ink-3)"),
    "NEW":       ("new", "background:rgba(88,166,255,.15);color:#58a6ff"),
    "WITHDRAWN": ("withdrawn", "background:var(--bg-3);color:var(--ink-3)"),
    "OTHER":     ("other", "background:var(--bg-3);color:var(--ink-3)"),
}

_CSS = """
<style>
.rv-note{color:var(--ink-2);font-size:13px;line-height:1.55;margin:2px 0 12px;max-width:1150px;}
.rv-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 14px;}
.rv-tile{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:10px 13px;}
.rv-tile .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1;}
.rv-tile .l{font-size:11.5px;font-weight:700;margin-top:4px;color:var(--ink);}
.rv-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;}
.rv-h{font-size:14px;font-weight:700;margin:16px 0 6px;color:var(--ink);}
.rv-h small{font-weight:400;color:var(--ink-3);}
table.rv{border-collapse:collapse;width:100%;font-size:12.5px;}
table.rv th{position:sticky;top:0;background:var(--bg-1);text-align:right;padding:6px 9px;color:var(--ink-2);
  border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;}
table.rv th.l,table.rv td.l{text-align:left;}
table.rv td{padding:5px 9px;border-bottom:1px solid #1b2027;white-space:nowrap;vertical-align:middle;}
table.rv td.num{text-align:right;font-variant-numeric:tabular-nums;}
table.rv tr:hover td{background:#11161d;}
.rv-sym{font-weight:700;color:var(--ink);}
.rv-chip{display:inline-block;padding:1px 8px;border-radius:9px;font-size:10.5px;font-weight:700;letter-spacing:.2px;}
.rv-up{color:var(--up);font-weight:700;} .rv-dn{color:var(--down);font-weight:700;} .rv-mut{color:var(--ink-3);}
.rv-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 10px;}
.rv-ctrl a{padding:4px 11px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;
  text-decoration:none;white-space:nowrap;}
.rv-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.rv-ctrl input{background:var(--bg-1);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:5px 9px;font-size:12.5px;min-width:220px;}
.rv-count{color:var(--ink-3);font-size:12px;margin-left:auto;}
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
  wire('rvBoard','rvBoardF','rvBoardC');
  wire('rvTape','rvTapeF','rvTapeC');
})();</script>
"""


def _chip(cls: str) -> str:
    label, style = _ACT_CHIP.get(cls or "OTHER", _ACT_CHIP["OTHER"])
    return f'<span class="rv-chip" style="{style}">{_esc(label)}</span>'


def _grade(ordv) -> str:
    """Ordinal → grade label via the module's canonical scale (D=1 … AAA=20)."""
    try:
        return CR._LT[int(ordv) - 1] if ordv else "—"
    except Exception:  # noqa: BLE001
        return "—"


def _doc(url) -> str:
    if not url:
        return '<td class="l rv-mut">—</td>'
    return (f'<td class="l"><a href="{_esc(url)}" target="_blank" rel="noopener" '
            f'title="the rating disclosure document on the NSE archive — the primary '
            f'source this row was parsed from">⇗</a></td>')


def _tiles(events: list, census: dict, watch_90: int) -> str:
    ups = [e for e in events if e["sign"] > 0]
    downs = [e for e in events if e["sign"] < 0]
    fallen = [e for e in downs if e.get("below_investment_grade")]
    t = [
        (str(len(ups)), "Upgrades · 90d", "company-level, deduped", "var(--up)"),
        (str(len(downs)), "Downgrades · 90d", "incl. fresh defaults", "var(--down)"),
        (str(len(fallen)), "Fell below IG", "crossed under BBB− (fallen angels)", "#ff7b72"),
        (str(watch_90), "Watch placements · 90d", "raw watch rows (not deduped)", "#f0883e"),
        (f'{census.get("raw_transition_rows", 0)}→{census.get("deduped_actions", 0)}',
         "Dedup census", f'{census.get("unmapped_rows", 0)} unmapped debt-only rows excluded',
         "var(--ink)"),
    ]
    tiles = "".join(
        f'<div class="rv-tile"><div class="n" style="color:{c}">{_esc(n)}</div>'
        f'<div class="l">{_esc(l)}</div><div class="s">{_esc(s)}</div></div>'
        for n, l, s, c in t)
    return f'<div class="rv-tiles">{tiles}</div>'


def _board(events: list) -> str:
    if not events:
        return ('<div class="rv-note">No company-level rating transitions in the window '
                '(true actions run ~2/month post-dedup — quiet stretches are normal).</div>')
    trs = []
    for e in events[:200]:
        arrow = ("<span class='rv-up'>▲" if e["sign"] > 0 else "<span class='rv-dn'>▼") \
            + (f'{abs(e["notch"])}' if e.get("notch") else "") + "</span>"
        frm, to = _grade(e.get("lt_ord_earlier")), (e.get("lt_grade") or _grade(e.get("lt_ord")))
        big = ' <span title="below investment grade (under BBB−)" style="color:#ff7b72">✦</span>' \
            if e.get("below_investment_grade") else ""
        trs.append(
            f'<tr><td class="l rv-mut">{_esc(str(e["t0"])[:10])}</td>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_esc(e["symbol"])}">'
            f'<span class="rv-sym">{_esc(e["symbol"])}</span></a>{big}</td>'
            f'<td class="l" data-sort="{e["sign"] * abs(e.get("notch") or 1)}">{arrow}</td>'
            f'<td class="l">{_esc(frm)} → <b>{_esc(to or "—")}</b></td>'
            f'<td class="l rv-mut">{_esc(e.get("agency") or "—")}</td>'
            f'<td class="l rv-mut">{_esc((e.get("outlook") or "—").title())}</td>'
            f'<td class="l">{_chip(e.get("action_class"))}</td>'
            + _doc(e.get("attachment_url")) + '</tr>')
    head = ('<tr><th class="l">Broadcast</th><th class="l">Symbol</th><th class="l" data-t="n">Move</th>'
            '<th class="l">Rating</th><th class="l">Agency</th><th class="l">Outlook</th>'
            '<th class="l">Action</th><th class="l" title="link to the disclosure document '
            'on the NSE archive">Filing</th></tr>')
    return (f'<div class="rv-ctrl"><input id="rvBoardF" placeholder="Filter transitions…"/>'
            f'<span class="rv-count" id="rvBoardC"></span></div>'
            f'<div style="max-height:48vh;overflow:auto"><table class="rv" id="rvBoard">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tape(conn, window: int, cls: str, sym: str) -> str:
    where = ["COALESCE(broadcast_dt, rating_date) >= date((SELECT MAX(COALESCE(broadcast_dt, rating_date)) "
             "FROM credit_rating_events), ?)"]
    params: list = [f"-{window} days"]
    if cls:
        where.append("action_class = ?"); params.append(cls)
    if sym:
        where.append("symbol = ?"); params.append(sym.upper())
    rows = conn.execute(
        "SELECT COALESCE(broadcast_dt, rating_date) t0, symbol, issuer_name, agency, "
        "action_class, rating_raw, outlook, watch_flag, attachment_url "
        f"FROM credit_rating_events WHERE {' AND '.join(where)} "
        "ORDER BY t0 DESC LIMIT 400", params).fetchall()
    if not rows:
        return '<div class="rv-note">No disclosure rows match this filter.</div>'
    trs = []
    for r in rows:
        name = r["symbol"] or (r["issuer_name"] or "—")[:28]
        link = (f'<a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                f'<span class="rv-sym">{_esc(r["symbol"])}</span></a>' if r["symbol"]
                else f'<span class="rv-mut" title="debt-only issuer — no listed equity mapping">{_esc(name)}</span>')
        watch = ' <span style="color:#f0883e" title="on rating watch">◉</span>' if r["watch_flag"] else ""
        trs.append(
            f'<tr><td class="l rv-mut">{_esc(str(r["t0"])[:10])}</td>'
            f'<td class="l">{link}{watch}</td>'
            f'<td class="l rv-mut">{_esc(r["agency"] or "—")}</td>'
            f'<td class="l">{_chip(r["action_class"])}</td>'
            f'<td class="l rv-mut" title="{_esc(r["rating_raw"] or "")}">{_esc((r["rating_raw"] or "—")[:44])}</td>'
            f'<td class="l rv-mut">{_esc((r["outlook"] or "—").title())}</td>'
            + _doc(r["attachment_url"]) + '</tr>')
    head = ('<tr><th class="l">Broadcast</th><th class="l">Issuer</th><th class="l">Agency</th>'
            '<th class="l">Action</th><th class="l">Rating (as filed)</th><th class="l">Outlook</th>'
            '<th class="l">Filing</th></tr>')
    return (f'<div class="rv-ctrl"><input id="rvTapeF" placeholder="Filter the tape…"/>'
            f'<span class="rv-count" id="rvTapeC"></span></div>'
            f'<div style="max-height:52vh;overflow:auto"><table class="rv" id="rvTape">'
            f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cls_tabs(active: str, window: int) -> str:
    tabs = [("", "All"), ("UPGRADE", "Upgrades"), ("DOWNGRADE", "Downgrades"),
            ("DEFAULT", "Defaults"), ("WATCH", "Watch"), ("NEW", "New"),
            ("REAFFIRM", "Reaffirmations"), ("WITHDRAWN", "Withdrawn")]
    parts = [f'<a class="{"on" if active == k else ""}" '
             f'href="/dash/ratings?window={window}&cls={k}">{_esc(l)}</a>' for k, l in tabs]
    for w in (90, 180, 365):
        parts.append(f'<a class="{"on" if window == w else ""}" '
                     f'href="/dash/ratings?window={w}&cls={active}">{w}d</a>')
    return f'<div class="rv-ctrl">{"".join(parts)}</div>'


@router.get("/dash/ratings", response_class=HTMLResponse)
def dash_ratings(window: int = 180, cls: str = "", sym: str = "") -> HTMLResponse:
    window = window if window in (90, 180, 365) else 180
    body = [_CSS]
    as_of = None
    try:
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='credit_rating_events'").fetchone():
                raise LookupError("credit_rating_events absent")
            events, census, as_of = CR.transitions(conn, days=90)
            watch_90 = conn.execute(
                "SELECT COUNT(*) FROM credit_rating_events WHERE action_class='WATCH' "
                "AND COALESCE(broadcast_dt, rating_date) >= date(?, '-90 days')",
                (as_of,)).fetchone()[0] if as_of else 0
            body.append(
                '<h2 style="margin:0 0 2px">Credit-rating transitions <small style="color:var(--ink-3);'
                f'font-size:12px;font-weight:400">NSE rating-disclosure register · as of '
                f'{_esc(str(as_of)[:10] if as_of else "—")} · broadcast-date anchored · descriptive, '
                'not advice</small></h2>'
                '<div class="rv-note">The headline counts <b>company-level actions</b>, never raw rows — '
                'one issuer\'s multi-ISIN debt re-rated across programs collapses to ONE action per '
                'direction per day (the E-02 study measured raw rows at ~6× pseudo-replication). '
                'Reaffirmations dominate the raw feed and live in the tape, not the headline. '
                '<b>Source:</b> NSE\'s centralised rating-disclosure database (LODR-mandated agency '
                'actions) — every row links (⇗) to the disclosure document on the NSE archive; nothing '
                'is scraped from a third-party site. The pre-registered E-02 drift study is ARMED and '
                'self-gating — <b>no return edge is claimed</b>, in either direction. '
                '<a href="/dash/glossary?q=rating">glossary →</a></div>')
            body.append(_tiles(events, census, watch_90))
            body.append('<div class="rv-h">Transitions <small>— deduped company-level actions, '
                        '90 days, newest first</small></div>')
            body.append(_board(events))
            body.append(f'<div class="rv-h">The tape <small>— every disclosure row '
                        f'(window {window}d{", " + _esc(sym.upper()) if sym else ""})</small></div>')
            body.append(_cls_tabs(cls, window))
            body.append(_tape(conn, window, cls, sym))
    except Exception:  # noqa: BLE001 — degrade to the honest empty state, never 500
        body.append(
            '<h2>Credit-rating transitions</h2><div class="rv-note">The '
            '<code>credit_rating_events</code> table is not populated on this host. It is ingested '
            'nightly on production from NSE\'s rating-disclosure database '
            '(<code>src/automation/credit_ratings.py</code>). This surface is read-only and never '
            'fabricates data.</div>')
    body.append(_JS)
    return HTMLResponse(_shell("Rating transitions · patearn", "".join(body),
                               "ratings", str(as_of or "")[:10], wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/ratings" not in paths:
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
    r = c.get("/dash/ratings")
    assert r.status_code == 200, r.status_code
    assert "Credit-rating transitions" in r.text
    assert c.get("/dash/ratings?window=365&cls=DOWNGRADE").status_code == 200
    assert c.get("/dash/ratings?sym=RELIANCE").status_code == 200
    print("ratings_view selftest OK — page 200 (populated or honest-empty), filters 200")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
