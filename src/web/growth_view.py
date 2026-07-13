"""Growth-intent — concall forward-looking PROPOSALS as a scannable board.

Surfaces `concall_signals` (src/automation/concall_signals.py): every capex / expansion /
debt-reduction / new-product / volume statement managements made on earnings calls, ₹-amounts
NORMALIZED. A DESCRIPTIVE PROPOSAL LEDGER — what management SAID it will do, sortable by ₹-size.
⚠ Codex D6-F3: the early month-granular "growth-intent forward tilt" (debt_reduction +2.8% etc.) was
PLACEBO-KILLED on real dates (2026-07-08 — random windows of the same covered names drift MORE:
covered-universe beta, NOT a content edge; strategy-ledger.md § Studies 2026-07-08). No return edge
ships. Isolated view (own router); reuses dashboard._shell so it renders natively inside the shell + nav.

View options: per-type tabs · instant text filter · click-to-sort columns · symbol / min-₹ / since
server filters.

Route: /dash/growth  [?type=…] [?since=YYYY] [?min_cr=N] [?pullback=1] [?symbol=X]
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from urllib.parse import quote

from src.core.db import get_conn
from src.web.dashboard import _shell, _esc
from src.automation.concall_signals import ensure_schema, scan


def _q(s) -> str:
    """URL-encode a symbol for a query string (CL-VIEW-05). `_esc` only HTML-escapes;
    a symbol with `&`/`%`/space would break the href without percent-encoding."""
    return quote(str(s) if s is not None else "", safe="")

router = APIRouter()

_TABS = [("", "All growth"), ("debt_reduction", "Debt ↓"), ("volume", "Volume"),
         ("new_product", "New product"), ("capex", "Capex"), ("expansion", "Expansion")]

_CSS = """
<style>
.gw-note{color:var(--ink-2);font-size:13px;line-height:1.5;margin:2px 0 10px;max-width:1100px;}
.gw-tabs{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 10px;}
.gw-tab{padding:5px 11px;border:1px solid var(--line-2);border-radius:16px;color:var(--ink);font-size:12px;
  text-decoration:none;white-space:nowrap;}
.gw-tab:hover{border-color:#58a6ff;}
.gw-tab.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.gw-tab.warn.on{background:#b9484e;border-color:#b9484e;}
.gw-ctrl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0 12px;}
.gw-ctrl input{background:var(--bg-1);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:6px 9px;font-size:13px;}
.gw-ctrl input#gwfilter{flex:1;min-width:240px;}
.gw-ctrl button{background:var(--bg-3);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);
  padding:6px 12px;cursor:pointer;font-size:13px;}
.gw-ctrl button:hover{border-color:#58a6ff;}
.gw-count{color:var(--ink-3);font-size:12px;margin-left:auto;}
table.gw{border-collapse:collapse;width:100%;font-size:13px;}
table.gw th{position:sticky;top:0;background:var(--bg-1);text-align:left;padding:7px 10px;color:var(--ink-2);
  border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;}
table.gw th.gw-sort{cursor:pointer;user-select:none;}
table.gw th.gw-sort:hover{color:var(--ink);}
table.gw th .ar{color:var(--ink-3);font-size:10px;margin-left:3px;}
table.gw th.num{text-align:right;}
table.gw td{padding:6px 10px;border-bottom:1px solid #1b2027;vertical-align:top;}
table.gw td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
table.gw tr:hover td{background:#11161d;}
.gw-sym{font-weight:700;color:var(--ink);} .gw-cr{color:var(--series-4);font-weight:600;}
.gw-pos{color:var(--up);} .gw-neg{color:var(--down);} .gw-mut{color:var(--ink-3);}
.gw-type{color:#58a6ff;font-size:11px;text-transform:uppercase;letter-spacing:.3px;}
.gw-claim{color:var(--ink);max-width:620px;}
</style>
"""

_JS = """
<script>
(function(){
  var f=document.getElementById('gwfilter'), t=document.getElementById('gwt'), cnt=document.getElementById('gwcount');
  function recount(){ if(!cnt)return; var rs=t.tBodies[0].rows,n=0; for(var i=0;i<rs.length;i++){if(rs[i].style.display!=='none')n++;} cnt.textContent=n+' rows'; }
  if(f&&t){ f.addEventListener('input',function(){
    var q=f.value.toLowerCase(), rs=t.tBodies[0].rows;
    for(var i=0;i<rs.length;i++){ rs[i].style.display = rs[i].textContent.toLowerCase().indexOf(q)>=0 ? '' : 'none'; }
    recount();
  }); }
  if(t&&t.tHead){ var ths=t.tHead.rows[0].cells;
    for(var c=0;c<ths.length;c++){ (function(th){
      if(!th.classList.contains('gw-sort')) return;
      var dir=1;
      th.addEventListener('click',function(){
        var col=+th.getAttribute('data-c'), typ=th.getAttribute('data-t');
        var tb=t.tBodies[0], rows=Array.prototype.slice.call(tb.rows); dir=-dir;
        rows.sort(function(a,b){
          var ca=a.cells[col], cb=b.cells[col];
          if(typ==='n'){ var na=parseFloat(ca.getAttribute('data-sort'))||-1, nb=parseFloat(cb.getAttribute('data-sort'))||-1; return (na-nb)*dir; }
          var va=(ca.getAttribute('data-sort')||ca.textContent||'').trim().toLowerCase();
          var vb=(cb.getAttribute('data-sort')||cb.textContent||'').trim().toLowerCase();
          return va<vb?-dir : va>vb?dir : 0;
        });
        rows.forEach(function(r){ tb.appendChild(r); });
      });
    })(ths[c]); }
  }
})();
</script>
"""


def _tabs(active_type: str, pullback: bool) -> str:
    parts = []
    for key, label in _TABS:
        on = (not pullback) and ((active_type or "") == key)
        parts.append(f'<a class="gw-tab{" on" if on else ""}" href="/dash/growth?type={key}">{label}</a>')
    parts.append(f'<a class="gw-tab warn{" on" if pullback else ""}" href="/dash/growth?pullback=1">'
                 f'⚠ Pullbacks (no-capex)</a>')
    return f'<div class="gw-tabs">{"".join(parts)}</div>'


def _controls(stype, since, min_cr, symbol, pullback, n_shown) -> str:
    hidden = ""
    if stype:
        hidden += f'<input type="hidden" name="type" value="{_esc(stype)}">'
    if pullback:
        hidden += '<input type="hidden" name="pullback" value="1">'
    return (
        '<form class="gw-ctrl" method="get">'
        '<input id="gwfilter" placeholder="filter loaded rows…  (symbol · type · text)" autocomplete="off">'
        f'<input name="symbol" placeholder="symbol" value="{_esc(symbol or "")}" style="max-width:130px">'
        f'<input name="min_cr" type="number" placeholder="min ₹cr" value="{min_cr or ""}" style="max-width:110px">'
        f'<input name="since" type="number" placeholder="since yr" value="{since or ""}" style="max-width:100px">'
        + hidden +
        '<button type="submit">Apply</button>'
        f'<span class="gw-count" id="gwcount">{n_shown} rows</span>'
        '</form>')


def _table(rows) -> str:
    if not rows:
        return '<div class="gw-note">No statements match this filter.</div>'
    hdr = ('<th class="gw-sort" data-c="0" data-t="s">Symbol<span class="ar">↕</span></th>'
           '<th class="gw-sort" data-c="1" data-t="n">Period<span class="ar">↕</span></th>'
           '<th class="gw-sort" data-c="2" data-t="s">Type<span class="ar">↕</span></th>'
           '<th class="gw-sort num" data-c="3" data-t="n">₹ cr<span class="ar">↕</span></th>'
           '<th>What management said</th>')
    out = [f'<table class="gw" id="gwt"><thead><tr>{hdr}</tr></thead><tbody>']
    for r in rows:
        av = r["amount_cr"]
        amt = f'<span class="gw-cr">{av:,.0f}</span>' if av is not None else '<span class="gw-mut">—</span>'
        sym = _esc(r["symbol"])
        sym_q = _q(r["symbol"])   # CL-VIEW-05: URL-encode for the href (sym is HTML-escaped for text)
        per_sort = (r["year"] or 0) * 100 + (r["month"] or 0)
        claim_cls = "gw-neg" if r["polarity"] == -1 else "gw-claim"
        out.append(
            f'<tr><td><a class="gw-sym" href="/dash/stock?sym={sym_q}" style="text-decoration:none">{sym}</a></td>'
            f'<td class="gw-mut" data-sort="{per_sort}">{_esc(r["period_label"] or "")}</td>'
            f'<td class="gw-type">{_esc(r["statement_type"] or "")}</td>'
            f'<td class="num" data-sort="{av if av is not None else -1}">{amt}</td>'
            f'<td class="{claim_cls}">{_esc((r["claim_text"] or "")[:240])}</td></tr>')
    out.append('</tbody></table>')
    return "".join(out)


@router.get("/dash/growth", response_class=HTMLResponse)
def growth(type: str = "", since: int = 0, min_cr: float = 0, pullback: int = 0,
           symbol: str = "") -> HTMLResponse:
    stype = type or None
    is_pull = bool(pullback)
    with get_conn() as conn:
        ensure_schema(conn)
        n_total = conn.execute("SELECT COUNT(*) FROM concall_signals").fetchone()[0]
        rows = scan(conn, stype=stype, symbol=(symbol or None), min_cr=(min_cr or None),
                    since_year=(since or None),
                    growth=(stype is None and not is_pull and not symbol),
                    polarity=(-1 if is_pull else None), limit=600)

    head = ('<h2>Growth-intent <span class="sub" style="margin:0">concall forward-looking proposals</span></h2>'
            '<div class="gw-note">What managements say they will <b>do</b> — capex, capacity, new products, '
            'deleveraging — from earnings calls, ₹-amounts normalized. A <b>descriptive proposal ledger</b>: the '
            'early per-type "forward tilt" was <b>placebo-killed</b> on real dates (covered-universe drift, not a '
            'content edge — strategy-ledger § 2026-07-08); order reflects commitment size, not expected return. '
            'Click a column to sort · type to filter · tap a symbol for its dossier. '
            '<span class="gw-mut">Descriptive research signal — not investment advice.</span></div>')
    if not n_total:
        body = head + '<div class="gw-note">The signal table is empty — run <code>concall_signals --rebuild</code>.</div>'
    else:
        body = (_CSS + head + _tabs(stype, is_pull)
                + _controls(stype, since, (int(min_cr) if min_cr else 0), symbol, is_pull, len(rows))
                + _table(rows) + _JS)
    return HTMLResponse(_shell("Growth-intent · patearn", body, "growth", wide=True))
