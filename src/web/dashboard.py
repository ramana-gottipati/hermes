"""Hermes web dashboard + installable PWA (D33-web).

A mobile/desktop browser dashboard over the same SQLite data the Telegram bot
uses. Served by the existing FastAPI app on :8000. Designed to be installed as
a Progressive Web App (PWA) — Chrome/Edge show an "Install" button when served
over HTTPS, giving it its own icon and frameless window.

Views:
  /dash            — overview (status + nav)
  /dash/markets    — D32 major indexes + full bundle (ABS vs RS column groups)
  /dash/sectors    — D32 sector-rotation dashboard (RS heat strips)
  /dash/rs         — D39 cross-sector RS-momentum ranking (on-read)
  /dash/ratio      — D39 ratio chart (?idx=Nifty IT&den=Nifty 500)
  /dash/scan       — D28/D31 layered triggers
  /dash/stock      — per-stock DVPT + institutional price zones (?sym=BANDHANBNK)
  /dash/screener   — D54 data-first wide frozen-pane grid (all strategies, one table)

PWA assets:
  /manifest.webmanifest
  /sw.js
  /icon.svg
  /dash/offline

All read-only. No LLM. No mutation. Pure SQL over the existing tables.
"""

import json
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from src.automation import adjust
from src.automation.signals import accum_character_read, is_near_key
from src.core.db import get_conn

router = APIRouter()


# --- Shared shell ----------------------------------------------------------

_THEME = "#0e1116"
_ACCENT = "#1f6feb"

_BASE_CSS = """
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin:0; padding:0; }
body { font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;
       background:#0e1116; color:#e6edf3; padding:0 0 28px; min-height:100vh; }
header { position:sticky; top:0; z-index:10; background:#0e1116ee;
         backdrop-filter:blur(8px); border-bottom:1px solid #21262d; }
.hrow1{display:flex;align-items:center;gap:10px;padding:9px 14px 6px;}
.hrow2{padding:0 8px;}
header .logo { font-size:18px; font-weight:800; letter-spacing:.5px; }
header .dot { width:8px; height:8px; border-radius:50%; background:#2ea043; }
header .date { color:#8b949e; font-size:12px; }
header .brand{display:flex;align-items:center;gap:8px;text-decoration:none;color:inherit;flex:none;}
.wsnav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;}
.wsnav::-webkit-scrollbar{display:none;}
.wsnav a{padding:8px 13px;color:#8b949e;text-decoration:none;font-size:13px;font-weight:600;white-space:nowrap;border-bottom:2px solid transparent;}
.wsnav a.on{color:#e6edf3;border-bottom-color:#3fb950;}
.wsnav a:hover{color:#e6edf3;}
.wrap { padding:16px; max-width:760px; margin:0 auto; }
h2 { font-size:16px; margin:18px 0 10px; color:#e6edf3; }
.sub { color:#8b949e; font-size:12px; margin:-6px 0 12px; }
.card { background:#161b22; border:1px solid #30363d; border-radius:10px;
        padding:14px; margin-bottom:10px; }
.kpi { display:flex; gap:10px; flex-wrap:wrap; }
.kpi .box { flex:1; min-width:120px; background:#161b22; border:1px solid #30363d;
            border-radius:10px; padding:14px; }
.kpi .num { font-size:24px; font-weight:800; }
.kpi .lbl { color:#8b949e; font-size:12px; margin-top:2px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; color:#8b949e; font-weight:600; padding:8px 6px;
     border-bottom:1px solid #30363d; font-size:11px; text-transform:uppercase;
     letter-spacing:.4px; }
td { padding:9px 6px; border-bottom:1px solid #21262d; }
tr:last-child td { border-bottom:none; }
.sym { font-weight:700; }
.pos { color:#3fb950; } .neg { color:#f85149; } .mut { color:#8b949e; }
.pill { display:inline-block; font-size:10px; font-weight:700; padding:2px 7px;
        border-radius:9px; letter-spacing:.4px; }
.p-SS{background:#1f6f3a;color:#7ee787;} .p-S{background:#225c33;color:#7ee787;}
.p-A{background:#2b4f6f;color:#79c0ff;} .p-B{background:#3a3f4b;color:#c9d1d9;}
.p-C{background:#30363d;color:#8b949e;} .p-BREAKOUT{background:#1f6f3a;color:#7ee787;}
.p-UPTREND{background:#225c33;color:#7ee787;} .p-CONSOLIDATING{background:#5a4a1f;color:#ffd99a;}
.p-DOWNTREND{background:#6f2b2b;color:#ffa198;} .p-BREAKDOWN{background:#8f1f1f;color:#ffa198;}
/* D43 accumulation/distribution character pills */
.ca-acc{background:#16341f;color:#7ee787;} .ca-dist{background:#3a1a1a;color:#ffa198;}
.ca-cons{background:#3a3417;color:#ffd99a;} .ca-neu{background:#30363d;color:#8b949e;}
nav { position:fixed; bottom:0; left:0; right:0; background:#0e1116;
      border-top:1px solid #21262d; display:flex; }
nav a { flex:1; text-align:center; padding:10px 4px; color:#8b949e;
        text-decoration:none; font-size:11px; }
nav a.active { color:#58a6ff; }
nav a .ic { font-size:20px; display:block; }
input,button { font-family:inherit; }
.search { display:flex; gap:8px; margin-bottom:14px; }
.search input { flex:1; background:#0d1117; border:1px solid #30363d; color:#e6edf3;
                padding:11px 12px; border-radius:8px; font-size:15px; }
.search button { background:#1f6feb; border:none; color:#fff; padding:0 18px;
                 border-radius:8px; font-weight:700; font-size:14px; }
.zone { display:flex; justify-content:space-between; padding:7px 0;
        border-bottom:1px solid #21262d; font-size:14px; }
.zone .lbl { color:#8b949e; width:54px; }
.zone .val { font-variant-numeric:tabular-nums; }
.empty { color:#8b949e; text-align:center; padding:48px 16px; }
a.row { color:inherit; text-decoration:none; display:block; }
.hsearch { margin-left:auto; flex:none; }
.hsearch input { background:#0d1117; border:1px solid #30363d; color:#e6edf3;
                 padding:6px 10px; border-radius:7px; font-size:13px; width:110px; }
.banner { border-radius:10px; padding:12px 14px; margin-bottom:12px; font-weight:700;
          display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.banner small { font-weight:400; opacity:.9; }
.b-on{background:#16341f;color:#7ee787;border:1px solid #1f6f3a;}
.b-off{background:#3a1a1a;color:#ffa198;border:1px solid #8f1f1f;}
.b-neu{background:#3a3417;color:#ffd99a;border:1px solid #5a4a1f;}
.majgrid { display:grid; grid-template-columns:1fr; gap:8px; }
@media(min-width:560px){ .majgrid{ grid-template-columns:1fr 1fr; } }
.maj { background:#161b22; border:1px solid #30363d; border-left:3px solid #1f6feb;
       border-radius:8px; padding:10px 12px; display:block; color:inherit; text-decoration:none; }
.maj .nm { font-weight:700; font-size:14px; }
.maj .rr { display:flex; gap:14px; margin-top:5px; font-size:12px; color:#8b949e;
           font-variant-numeric:tabular-nums; flex-wrap:wrap; }
.fbar { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
.fbtn { background:#161b22; border:1px solid #30363d; color:#8b949e; padding:5px 11px;
        border-radius:14px; font-size:12px; cursor:pointer; }
.fbtn.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chips { display:flex; gap:6px; flex-wrap:wrap; }
.chip { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:7px 10px;
        font-size:13px; color:inherit; text-decoration:none; }
.ghdr { font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:#8b949e;
        margin:16px 0 8px; font-weight:700; }
.hstrip{display:inline-flex;gap:2px;vertical-align:middle;}
.hstrip .c{width:20px;height:24px;border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px;line-height:1;font-weight:700;}
.hstrip .c small{font-size:7px;opacity:.7;margin-top:1px;font-weight:600;}
.hs-su{background:#1f6f3a;color:#7ee787;} .hs-mu{background:#225c33;color:#7ee787;}
.hs-fl{background:#5a4a1f;color:#ffd99a;} .hs-md{background:#6f2b2b;color:#ffa198;}
.hs-sd{background:#8f1f1f;color:#ffa198;} .hs-nd{background:#21262d;color:#484f58;}
.bar{height:7px;background:#21262d;border-radius:4px;overflow:hidden;} .bar>span{display:block;height:100%;background:#1f6feb;}
.grp{color:#58a6ff;} th.rsgrp{border-left:1px solid #30363d;} td.rsgrp{border-left:1px solid #30363d;}
.dttool{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.dtf{flex:1;min-width:120px;background:#0d1117;border:1px solid #30363d;color:#e6edf3;padding:6px 10px;border-radius:7px;font-size:13px}
.dtx{background:#238636;border:none;color:#fff;padding:6px 12px;border-radius:7px;font-weight:700;font-size:12px;cursor:pointer}
.dtcount{color:#8b949e;font-size:12px}
table.dt thead th{cursor:pointer;user-select:none;position:sticky;top:0;background:#0e1116;z-index:1}
table.dt thead th.sorta::after{content:" ▲"} table.dt thead th.sortd::after{content:" ▼"}
tr.dt-hide{display:none!important}
/* D33d — strategy thesis badge (stamped on every board) + strategy hub cards */
.sbadge{display:flex;align-items:flex-start;gap:9px;border-radius:9px;padding:9px 12px;margin-bottom:12px;border:1px solid #30363d;font-size:12px;}
.sbadge .tag{font-size:10px;font-weight:800;letter-spacing:.5px;white-space:nowrap;padding:2px 8px;border-radius:8px;}
.sbadge .th{color:#c9d1d9;opacity:.92;line-height:1.35;}
.sb-POS{background:#0d1f33;border-color:#1f4d7a;} .sb-POS .tag{background:#1f6feb;color:#fff;}
.sb-RS{background:#0f2417;border-color:#1f6f3a;} .sb-RS .tag{background:#2ea043;color:#fff;}
.sb-QUAL{background:#241f0d;border-color:#5a4a1f;} .sb-QUAL .tag{background:#bb8009;color:#fff;}
.scards{display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:6px;}
@media(min-width:560px){.scards{grid-template-columns:1fr 1fr 1fr;}}
.scard{display:block;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;color:inherit;text-decoration:none;border-top:3px solid #30363d;}
.scard.sc-POS{border-top-color:#1f6feb;} .scard.sc-RS{border-top-color:#2ea043;} .scard.sc-QUAL{border-top-color:#bb8009;}
.scard.sc-CPR{border-top-color:#8957e5;}
.scard .nm{font-weight:800;font-size:14px;} .scard .th{color:#8b949e;font-size:11px;margin:4px 0 8px;line-height:1.3;}
.scard .ct{font-size:13px;font-weight:700;color:#e6edf3;} .scard .ct small{color:#8b949e;font-weight:400;}
/* CPR (Structure pillar, D53) — pattern glyphs, ★ conviction tier, D·W·M strip */
.cpg{font-weight:800;font-size:12px;} .cp-bull{color:#3fb950;} .cp-bear{color:#f85149;} .cp-none{color:#6e7681;}
.cp-tier{color:#e3b341;font-weight:800;letter-spacing:1px;white-space:nowrap;}
.cprstrip{display:inline-flex;gap:3px;vertical-align:middle;}
.cprstrip .c{min-width:30px;padding:2px 4px;border-radius:4px;background:#161b22;border:1px solid #21262d;display:flex;flex-direction:column;align-items:center;line-height:1.15;}
.cprstrip .c .w{font-size:11px;font-weight:700;font-variant-numeric:tabular-nums;}
.cprstrip .c small{font-size:7px;opacity:.6;font-weight:600;}
.cprstrip .c.nw{background:#10241a;border-color:#1f6f3a;} .cprstrip .c.nw .w{color:#7ee787;}
.cprstrip .c.up{box-shadow:inset 0 -2px 0 #2ea043;} .cprstrip .c.dn{box-shadow:inset 0 -2px 0 #f85149;}
.cprpanel{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:6px;}
.cprpanel table{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;}
.cprpanel th,.cprpanel td{text-align:right;padding:5px 8px;border-bottom:1px solid #21262d;white-space:nowrap;}
.cprpanel th:first-child,.cprpanel td:first-child{text-align:left;}
.cprverdict{margin-top:9px;font-size:13px;color:#c9d1d9;line-height:1.4;}
.tabbar{display:flex;gap:6px;margin:4px 0 12px;border-bottom:1px solid #30363d;}
.tabbar a{padding:7px 14px;font-size:13px;font-weight:700;color:#8b949e;text-decoration:none;border-bottom:2px solid transparent;}
.tabbar a.on{color:#e6edf3;border-bottom-color:#8957e5;}
/* D54 — full-bleed data workspace with a COMFORTABLE gutter (D-UI-10) */
.wrap.wide{max-width:1900px;margin:0 auto;padding:14px clamp(12px,4vw,56px);}
/* D54 — frozen-pane data grid: ONE scroll viewport owns BOTH axes so the header
   band AND the Symbol column stay fixed while scrolling down AND across. */
.scrwrap{overflow:auto;max-height:calc(100vh - 230px);border:1px solid #30363d;border-radius:10px;background:#0d1117;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
table.scr{width:100%;min-width:max-content;border-collapse:separate;border-spacing:0;font-size:12px;}
table.scr th,table.scr td{white-space:nowrap;border-bottom:1px solid #1c2128;padding:6px 10px;text-align:right;}
table.scr th.l,table.scr td.l{text-align:left;}
table.scr td.num,table.scr th.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum";}
table.scr td.bold{font-weight:700;}
table.scr td.gsep,table.scr th.gsep{border-left:1px solid #262c36;}
table.scr thead tr.sgrp th{position:sticky;top:0;z-index:3;height:26px;background:#0d1117;color:#6e7681;font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;text-align:left;border-bottom:1px solid #30363d;border-left:1px solid #262c36;padding:0 10px;}
table.scr thead tr.scol th{position:sticky;top:26px;z-index:3;background:#0e1116;color:#8b949e;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #30363d;cursor:pointer;padding:6px 10px;}
table.scr .fz{position:sticky;left:0;z-index:2;background:#0d1117;border-right:1px solid #30363d;text-align:left;}
table.scr thead tr.sgrp th.fz,table.scr thead tr.scol th.fz{z-index:6;}
table.scr tbody .fz{font-weight:700;}
table.scr tbody tr:nth-child(even) td{background:rgba(255,255,255,.014);}
table.scr tbody tr:nth-child(even) td.fz{background:#0f151b;}
table.scr tbody tr:hover td{background:#1c2230!important;}
.scrwrap.scrolled table.scr .fz{box-shadow:8px 0 12px -6px rgba(0,0,0,.55);}
.h-pos3{background:rgba(63,185,80,.22)!important;} .h-pos2{background:rgba(63,185,80,.13)!important;} .h-pos1{background:rgba(63,185,80,.06)!important;}
.h-neg1{background:rgba(248,81,73,.07)!important;} .h-neg2{background:rgba(248,81,73,.14)!important;} .h-neg3{background:rgba(248,81,73,.22)!important;}
/* column-group hide = ONE class on the table (single reflow, no per-cell JS) */
table.scr.hide-conv .g-conv,table.scr.hide-pos .g-pos,table.scr.hide-rs .g-rs,table.scr.hide-cpr .g-cpr,table.scr.hide-qual .g-qual,table.scr.hide-ctx .g-ctx{display:none;}
/* CPR-confirmed gate: show only rows carrying a CPR reversal tier (one class) */
table.scr.cpr-only tbody tr:not(.has-cpr){display:none;}
"""


# Reusable data-grid enhancer (plain template — NOT an f-string; single braces).
# On DOMContentLoaded, enhances every <table class="dt"> with a toolbar
# (text filter + CSV export + visible-row count), click-to-sort headers
# (numeric-aware, asc/desc toggle), and a live row count that respects both
# the text filter (dt-hide class) and any sibling pill bar (inline display).
# Filtering uses the dt-hide class only (never inline display) so it COMPOSES
# with the existing pill filters (.fbar buttons) via the !important class.
_DT_JS = """
<script>
document.addEventListener('DOMContentLoaded', function(){
  function num(s){
    var n = parseFloat(String(s).replace(/[%,+₹\\s]/g,''));
    return n;
  }
  function csvCell(v){
    v = (v==null?'':String(v));
    if (v.indexOf('"')>=0 || v.indexOf(',')>=0 || v.indexOf('\\n')>=0 || v.indexOf('\\r')>=0){
      return '"' + v.replace(/"/g,'""') + '"';
    }
    return v;
  }
  document.querySelectorAll('table.dt').forEach(function(table){
    var tbody = table.tBodies[0];
    if (!tbody) return;
    var ths = Array.prototype.slice.call(table.tHead ? table.tHead.querySelectorAll('tr:last-child th') : []);

    // --- toolbar (inserted immediately before the table) ---
    var tool = document.createElement('div');
    tool.className = 'dttool';
    var f = document.createElement('input');
    f.className = 'dtf'; f.type = 'text'; f.placeholder = 'filter rows…';
    var x = document.createElement('button');
    x.className = 'dtx'; x.type = 'button'; x.textContent = '⬇ Export';
    var cnt = document.createElement('span');
    cnt.className = 'dtcount';
    tool.appendChild(f); tool.appendChild(x); tool.appendChild(cnt);
    // Keep the toolbar OUTSIDE a frozen-pane scroll viewport so it stays visible
    // while the grid scrolls under the fixed header (D54). Plain tables: unchanged.
    var _host = table.closest('.scrwrap') || table;
    _host.parentNode.insertBefore(tool, _host);

    function rows(){ return Array.prototype.slice.call(tbody.rows); }
    function visibleRows(){
      return rows().filter(function(r){ return r.offsetParent !== null; });
    }
    function recount(){
      cnt.textContent = visibleRows().length + ' rows';
    }

    // --- filter (toggles dt-hide only; never touches inline display) ---
    f.addEventListener('input', function(){
      var q = f.value.toLowerCase();
      rows().forEach(function(r){
        var hit = r.innerText.toLowerCase().indexOf(q) >= 0;
        r.classList.toggle('dt-hide', !hit);
      });
      recount();
    });

    // --- sort (numeric-aware, asc/desc toggle on repeat click) ---
    ths.forEach(function(th, ci){
      th.addEventListener('click', function(){
        var asc = !th.classList.contains('sorta');
        ths.forEach(function(o){ o.classList.remove('sorta','sortd'); });
        th.classList.add(asc ? 'sorta' : 'sortd');
        var rs = rows();
        rs.sort(function(a, b){
          var av = a.cells[ci] ? a.cells[ci].innerText : '';
          var bv = b.cells[ci] ? b.cells[ci].innerText : '';
          var an = num(av), bn = num(bv), c;
          if (isFinite(an) && isFinite(bn)) c = an - bn;
          else c = String(av).localeCompare(String(bv));
          return asc ? c : -c;
        });
        rs.forEach(function(r){ tbody.appendChild(r); });
        recount();
      });
    });

    // --- export (header + currently-visible rows only) ---
    x.addEventListener('click', function(){
      var lines = [];
      lines.push(ths.map(function(th){ return csvCell(th.innerText.trim()); }).join(','));
      visibleRows().forEach(function(r){
        var cells = Array.prototype.slice.call(r.cells);
        lines.push(cells.map(function(td){ return csvCell(td.innerText.trim()); }).join(','));
      });
      var csv = lines.join('\\r\\n');
      var blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = (document.title || 'export').replace(/[^a-zA-Z0-9]+/g,'-') +
                   '-' + new Date().toISOString().slice(0,10) + '.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
    });

    // --- recount when sibling pills change (they set inline display) ---
    var fbar = table.parentNode ? table.parentNode.parentNode : null;
    var pills = null;
    if (table.parentNode) pills = table.parentNode.querySelectorAll('.fbar button');
    if ((!pills || !pills.length) && fbar) pills = fbar.querySelectorAll('.fbar button');
    if (pills && pills.length){
      pills.forEach(function(b){ b.addEventListener('click', function(){ setTimeout(recount, 0); }); });
    }

    recount();
  });
});
</script>
"""


# Top workspace tabs = the primary navigation (D54 reframe). Every sub-page maps
# onto one of the five workspaces so the right tab highlights.
_WS = {
    "markets": "markets", "sectors": "markets", "ratio": "markets", "compare": "markets",
    "screener": "screener",
    "strategies": "strategies", "scan": "strategies", "stocks": "strategies",
    "leaders": "strategies", "laggards": "strategies", "conviction": "strategies",
    "workbench": "strategies", "stock": "strategies", "cpr": "strategies",
    "portfolios": "portfolios", "watchlists": "portfolios", "track": "portfolios",
    "tracker": "tracker",
}


def _nav(active: str) -> str:
    cur = _WS.get(active, active)
    items = [("markets", "/dash/markets", "Markets"),
             ("screener", "/dash/screener", "Screener"),
             ("strategies", "/dash/strategies", "Strategies"),
             ("portfolios", "/dash/portfolios", "Portfolios"),
             ("tracker", "/dash/tracker", "Tracker")]
    out = ['<div class="wsnav">']
    for key, href, label in items:
        out.append(f'<a class="{"on" if key == cur else ""}" href="{href}">{label}</a>')
    out.append('</div>')
    return "".join(out)


def _shell(title: str, body: str, active: str, latest_date: str = "", wide: bool = False) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="{_THEME}"/>
<link rel="manifest" href="/manifest.webmanifest"/>
<link rel="icon" href="/icon.svg" type="image/svg+xml"/>
<link rel="apple-touch-icon" href="/icon.svg"/>
<title>{title}</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<header>
  <div class="hrow1">
    <a href="/dash" class="brand"><span class="dot"></span><span class="logo">pat<span style="color:#3fb950">e</span>arn</span></a>
    <form class="hsearch" action="/dash/stock" method="get" autocomplete="off">
      <input name="sym" placeholder="search ticker…" autocapitalize="characters"/>
    </form>
  </div>
  <div class="hrow2">{_nav(active)}</div>
</header>
<div class="wrap{' wide' if wide else ''}">
{body}
</div>
<script>
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('/sw.js').catch(function(){{}});
}}
</script>
{_DT_JS}
</body>
</html>"""


def _esc(s) -> str:
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _q(s) -> str:
    return quote_plus(str(s) if s is not None else "")


def _pct(v, decimals=1) -> str:
    if v is None:
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    return f'<span class="{cls}">{v:+.{decimals}f}%</span>'


def _num(v, decimals=2) -> str:
    if v is None:
        return '<span class="mut">—</span>'
    return f"{v:,.{decimals}f}"


def _rs_strip(s1, s3, s6, s12) -> str:
    """4-cell multi-timeframe RS heat strip from the slope_% of the ratio.

    Per cell: None→grey ·; ≥+3 strong-up ▲; >+1 mild-up ▲; |x|≤1 flat ▬;
    <-1 mild-down ▼; ≤-3 strong-down ▼. Render [1m][3m][6m][12m] left→right.
    """
    cells = []
    for v, lbl in ((s1, "1m"), (s3, "3m"), (s6, "6m"), (s12, "12m")):
        if v is None:
            cls, glyph = "hs-nd", "·"
        elif v >= 3:
            cls, glyph = "hs-su", "▲"
        elif v > 1:
            cls, glyph = "hs-mu", "▲"
        elif v < -3:
            cls, glyph = "hs-sd", "▼"
        elif v < -1:
            cls, glyph = "hs-md", "▼"
        else:  # -1 <= v <= 1 → flat dead-band
            cls, glyph = "hs-fl", "▬"
        cells.append(f'<span class="c {cls}">{glyph}<small>{lbl}</small></span>')
    return f'<span class="hstrip">{"".join(cells)}</span>'


# --- CPR (Structure pillar, D53) on-read helpers ---------------------------
# Geometry + widths are materialized in cpr_signals; the narrowness RANK, the
# cross-TF AMPLIFICATION and the ★ CONVICTION TIER are derived HERE on read so
# the knob/weights stay tunable without re-materializing (decision CPR-A4).
# Defaults are the design's locked values (OPEN-5/6) — change here to re-tune.
_CPR_MAXW = {"D": 1.0, "W": 2.5, "M": 5.0}     # per-TF narrowness knob (OPEN-5)
_CPR_WEIGHT = {"D": 1, "W": 2, "M": 3}          # TF weights (OPEN-6) — larger TF dominates
_CPR_TF_ORDER = ("D", "W", "M")
_CPR_RANK_PTS = {"R1": 4, "R2": 3, "R3": 2, "R4": 1}
# Max attainable conviction per anchor (base 4 + Σ weight·3 over other TFs + conf 1).
_CPR_MAXSCORE = {"D": 20.0, "W": 17.0, "M": 14.0}


def _cpr_is_narrow(width, tf) -> bool:
    return width is not None and width <= _CPR_MAXW[tf]


def _cpr_rank(c0_w, c1_w, tf) -> str:
    """R1–R4 narrowness rank — C0 (today's coil) is the priority bar (OPEN-2):
    R1 both narrow · R2 C0 narrow · R3 C1 narrow · R4 neither."""
    n0, n1 = _cpr_is_narrow(c0_w, tf), _cpr_is_narrow(c1_w, tf)
    if n0 and n1:
        return "R1"
    if n0:
        return "R2"
    if n1:
        return "R3"
    return "R4"


def _cpr_glyph(pattern) -> tuple:
    """(glyph, css-class) for a pattern: U / ∩ / —."""
    if pattern == "BULL_U":
        return ("U", "cp-bull")
    if pattern == "BEAR_INVU":
        return ("∩", "cp-bear")
    return ("—", "cp-none")


def _cpr_s_tf(row, direction) -> int:
    """Per-TF structure score s_TF (0–3) = narrow? + reversal-aligned? +
    regime-aligned?  `direction` = +1 bullish anchor / −1 bearish."""
    if not row:
        return 0
    s = 0
    if _cpr_is_narrow(row.get("width_pct"), row["timeframe"]):
        s += 1
    pat = row.get("pattern")
    if (direction > 0 and pat == "BULL_U") or (direction < 0 and pat == "BEAR_INVU"):
        s += 1
    reg = row.get("regime")
    if reg is not None and ((direction > 0 and reg > 0) or (direction < 0 and reg < 0)):
        s += 1
    return s


def _cpr_conviction(by_tf, force_anchor=None):
    """Cross-TF amplified conviction for a symbol given its latest {D,W,M} cpr
    rows (§4). A signal on a faster TF is amplified when slower TFs are also
    coiled/aligned, the LARGER TF carrying more weight. Returns a dict
    {anchor, direction, score, tier, rank, confluence, breakdown} or None when no
    reversal is present on any TF. The score is the sort key; the ★ tier + the
    per-TF breakdown are the transparent label (never an opaque mega-score).
    `force_anchor` pins the anchor to a given TF (its own-TF reversal screen)."""
    anchors = [tf for tf in _CPR_TF_ORDER
               if by_tf.get(tf) and by_tf[tf].get("pattern") in ("BULL_U", "BEAR_INVU")]
    if force_anchor:
        if force_anchor not in anchors:
            return None
        anchor = force_anchor
    elif not anchors:
        return None
    else:
        anchor = anchors[-1]                   # largest-TF reversal is the strongest base
    arow = by_tf[anchor]
    direction = 1 if arow["pattern"] == "BULL_U" else -1
    rank = _cpr_rank(arow.get("width_pct"), arow.get("c1_width_pct"), anchor)
    score = float(_CPR_RANK_PTS[rank])
    breakdown = {}
    for tf in _CPR_TF_ORDER:
        if tf == anchor:
            continue
        s = _cpr_s_tf(by_tf.get(tf), direction)
        breakdown[tf] = s
        score += _CPR_WEIGHT[tf] * s
    # confluence — ≥2 of the present pivots within 0.5% of each other (§3D).
    pivs = [by_tf[tf]["p"] for tf in _CPR_TF_ORDER if by_tf.get(tf) and by_tf[tf].get("p")]
    conf = 0
    for i in range(len(pivs)):
        for j in range(i + 1, len(pivs)):
            if pivs[i] and pivs[j] and abs(pivs[i] / pivs[j] - 1) <= 0.005:
                conf = 1
    score += conf
    # Transparent tier (§4) — the design's locked boolean rules, not a raw cutoff.
    higher = [tf for tf in _CPR_TF_ORDER if _CPR_WEIGHT[tf] > _CPR_WEIGHT[anchor]]
    strong_base = rank in ("R1", "R2")
    higher_support = any(_cpr_s_tf(by_tf.get(tf), direction) >= 1 for tf in higher)
    higher_strong = any(_cpr_s_tf(by_tf.get(tf), direction) >= 2 for tf in higher)
    regime_aligned = any(
        by_tf.get(tf) and by_tf[tf].get("regime") is not None
        and ((direction > 0 and by_tf[tf]["regime"] > 0) or (direction < 0 and by_tf[tf]["regime"] < 0))
        for tf in (higher + [anchor]))
    if not higher:                              # monthly anchor — its own strongest base
        tier = "★★★" if (rank == "R1" and regime_aligned) else ("★★" if strong_base else "★")
    elif strong_base and higher_strong and regime_aligned:
        tier = "★★★"
    elif strong_base and higher_support:
        tier = "★★"
    else:
        tier = "★"
    return {"anchor": anchor, "direction": direction, "score": round(score, 1),
            "tier": tier, "rank": rank, "confluence": conf, "breakdown": breakdown}


def _cpr_latest_by_tf(conn, symbols):
    """{sym: {'D':row,'W':row,'M':row}} — each TF's latest cpr_signals row for the
    given symbols. Per-TF latest period_end_date is ONE indexed MAX lookup, then a
    keyed IN fetch — no per-symbol correlated scan. Empty {} if the table is empty."""
    out = {}
    syms = list(symbols)
    if not syms:
        return out
    ph = ",".join("?" for _ in syms)
    for tf in _CPR_TF_ORDER:
        mx = conn.execute(
            "SELECT MAX(period_end_date) d FROM cpr_signals WHERE timeframe=?", (tf,)).fetchone()
        if not mx or not mx["d"]:
            continue
        for r in conn.execute(
                f"SELECT * FROM cpr_signals WHERE timeframe=? AND period_end_date=? "
                f"AND symbol IN ({ph})", [tf, mx["d"]] + syms).fetchall():
            d = dict(r)
            out.setdefault(d["symbol"], {})[tf] = d
    return out


def _cpr_screener_cells(by_tf) -> tuple:
    """The 7 screener CPR-group <td>s for one symbol + whether it carries a
    reversal (the 'has-cpr' tag for the CPR-confirmed gate). Data-first: the raw
    D/W/M width% sit beside the glyph strip + rank + ★ tier (D-UI-1)."""
    conv = _cpr_conviction(by_tf)

    def wcell(tf):
        row = by_tf.get(tf)
        w = row.get("width_pct") if row else None
        if w is None:
            return '<td class="num g-cpr mut">—</td>'
        tint = " h-pos2" if _cpr_is_narrow(w, tf) else ""
        return f'<td class="num g-cpr{tint}">{w:.2f}</td>'

    # D·W·M glyph strip
    cells = []
    for tf in _CPR_TF_ORDER:
        row = by_tf.get(tf)
        g, cls = _cpr_glyph(row.get("pattern") if row else None)
        cells.append(f'<span class="cpg {cls}">{g}</span>')
    strip = '<td class="g-cpr l"><span class="cprstrip" style="gap:5px;padding:0 2px">' + \
            "".join(cells) + '</span></td>'

    if conv:
        rnk = f'<td class="g-cpr"><b>{conv["rank"]}</b><small class="mut"> {conv["anchor"]}</small></td>'
        tier = f'<td class="g-cpr l"><span class="cp-tier">{conv["tier"]}</span> ' \
               f'<small class="mut">{conv["score"]:.0f}</small></td>'
    else:
        rnk = '<td class="g-cpr mut">—</td>'
        tier = '<td class="g-cpr mut">—</td>'

    # max own-history compression percentile across D/W/M (how unusually coiled)
    pcts = [by_tf[tf].get("compression_pctile") for tf in _CPR_TF_ORDER
            if by_tf.get(tf) and by_tf[tf].get("compression_pctile") is not None]
    if pcts:
        mp = max(pcts)
        tint = " h-pos2" if mp >= 0.8 else (" h-pos1" if mp >= 0.6 else "")
        comp = f'<td class="num g-cpr{tint}">{mp*100:.0f}</td>'
    else:
        comp = '<td class="num g-cpr mut">—</td>'

    tds = wcell("D") + wcell("W") + wcell("M") + strip + rnk + tier + comp
    return tds, (conv is not None)


# --- Data helpers ----------------------------------------------------------

_SCAN_FILTERS = """
  AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
  AND b.value > 10000000 AND b.close > 20
  AND s.symbol IN (SELECT symbol FROM nse_equity_list)
"""


def _latest_dates() -> tuple:
    with get_conn() as conn:
        sig = conn.execute("SELECT MAX(trade_date) d FROM stock_signals").fetchone()
        idx = conn.execute("SELECT MAX(trade_date) d FROM index_signals").fetchone()
    return (sig["d"] if sig else None), (idx["d"] if idx else None)


# Curated "major" indexes for the Markets headline block. Names match
# index_rows.index_name exactly. Size indices have no RS (broad_benchmark NULL).
MAJOR_BROAD = ["Nifty 50", "Nifty Next 50", "Nifty Midcap 150",
               "Nifty Smallcap 250", "Nifty 500"]
MAJOR_SECTORS = ["Nifty Bank", "Nifty Financial Services", "Nifty IT", "Nifty Auto",
                 "Nifty Pharma", "Nifty FMCG", "Nifty Metal", "Nifty Energy",
                 "Nifty Realty", "Nifty Media", "Nifty Infrastructure",
                 "Nifty Commodities", "Nifty Healthcare Index",
                 "Nifty Consumer Durables", "Nifty Oil & Gas", "Nifty PSU Bank"]
MAJOR_ALL = MAJOR_BROAD + MAJOR_SECTORS

# Size segments for the Home leadership read (raw 3m return comparison).
LEADERSHIP_SET = ["Nifty 50", "Nifty Midcap 150", "Nifty Smallcap 250"]

# D33d — REAL economic sectors for the rotation / leaderboard views. Factor /
# strategy / thematic indices (High Beta, Alpha, Momentum, IPO, ...) are NOT
# sectors: they have no clean constituent list (so they dead-end on drill-down)
# and pollute rotation. The sector surfaces filter to this whitelist. Same set
# as MAJOR_SECTORS plus legitimate themes whose constituents are now loaded in
# membership (India Defence / Private Bank / Chemicals — D41 Phase 2 closure).
REAL_SECTORS = MAJOR_SECTORS + [
    "Nifty India Defence", "Nifty Private Bank", "Nifty Chemicals",
]

def _real_sectors_in() -> str:
    """A safe SQL IN-list of the curated sectors (constant names → inlineable)."""
    return ",".join("'" + s.replace("'", "''") + "'" for s in REAL_SECTORS)

# D33d — the 3 strategy pillars as labelled, first-class descriptors (a light
# definition for the badge + Home hub; the full query-registry refactor is
# deferred to the screener phase). family -> (tag, one-line thesis, css class).
_PILLARS = {
    "POS":  ("POSITIONING", "Where institutional money is positioning now — DVPT vs its own peak-day baselines, the entry price vs their cost, and whether strong hands are accumulating, distributing, or just consolidating.", "POS"),
    "RS":   ("RELATIVE STRENGTH", "Who's beating the market and leading their own sector.", "RS"),
    "QUAL": ("QUALITY", "Is the business worth owning — the patearn 14-pattern durability score.", "QUAL"),
}

# D43 — accumulation/distribution character pill. Shares the label vocabulary
# produced by signals.accum_character (delivery is side-blind, so the label
# fuses WHO/WHICH-WAY/CONTEXT — never one number). DISTRIBUTION carries a ⚠️.
_CHAR_PILL = {
    "ACCUMULATION":  ("🟢 ACCUM",   "ca-acc"),
    "DISTRIBUTION":  ("🔴 DISTR ⚠️", "ca-dist"),
    "CONSOLIDATION": ("🟡 CONSOL",  "ca-cons"),
    "NEUTRAL":       ("⚪ NEUTRAL", "ca-neu"),
}


def _char_pill(label: str, dash_if_none: bool = True) -> str:
    """Render the accumulation/distribution character as a pill (D43)."""
    spec = _CHAR_PILL.get(label or "")
    if not spec:
        return '<span class="pill ca-neu">—</span>' if dash_if_none else ""
    txt, cls = spec
    return f'<span class="pill {cls}">{txt}</span>'


def _strategy_badge(family: str) -> str:
    """A labelled strategy-thesis header so no board is silent about which
    strategy drives it (D33d)."""
    tag, thesis, cls = _PILLARS[family]
    return (f'<div class="sbadge sb-{cls}"><span class="tag">● {tag}</span>'
            f'<span class="th">{_esc(thesis)}</span></div>')


def _sector_symbols(conn, sector: str) -> list:
    """Member symbols of an index, from the latest membership snapshot."""
    rows = conn.execute(
        """SELECT symbol FROM stock_index_membership
           WHERE index_name=? AND snapshot_date=(
               SELECT MAX(snapshot_date) FROM stock_index_membership
               WHERE index_name=?)
           ORDER BY symbol""",
        (sector, sector),
    ).fetchall()
    return [r["symbol"] for r in rows]


def _narrow_sector(conn, sym: str):
    """The stock's NARROWEST real sectoral index (smallest membership), from
    stock_index_membership ∩ REAL_SECTORS. A render-time fallback for the stock
    RS overlay when stock_signals.primary_sector isn't populated yet (e.g. mid
    RS-recompute) — mirrors the D33b primary_sector assignment."""
    cands = [r["index_name"] for r in conn.execute(
        """SELECT DISTINCT index_name FROM stock_index_membership
           WHERE symbol=? AND snapshot_date=(
               SELECT MAX(snapshot_date) FROM stock_index_membership WHERE symbol=?)""",
        (sym, sym)).fetchall() if r["index_name"] in REAL_SECTORS]
    if not cands:
        return None
    return min(cands, key=lambda ix: len(_sector_symbols(conn, ix)) or 99999)


# --- Routes ----------------------------------------------------------------

def _rupee(v) -> str:
    """Compact ₹ formatter: Cr / L / plain."""
    if v is None:
        return "—"
    if v >= 1e7:
        return f"₹{v/1e7:.1f}Cr"
    if v >= 1e5:
        return f"₹{v/1e5:.2f}L"
    return f"₹{v:,.0f}"


def _intensity(r):
    """Today's DVPT vs the avg of its major power baselines = how hard it crossed
    (the ranking-driving intensity). None if data missing."""
    dvpt = r.get("dvpt")
    powers = [r.get(k) for k in ("p1", "p3", "p6", "p12") if r.get(k)]
    return (dvpt / (sum(powers) / len(powers))) if (powers and dvpt) else None


def _pos_cells(r) -> str:
    """The three shared Positioning cells — CMP·Δday, DVPT·×power, Deliv ₹ —
    used by the Home trigger + stealth boards. Expects r with cmp/pc/dvpt/dval +
    power baselines p1/p3/p6/p12. The ×power = today's DVPT vs the avg of its
    major power baselines = how hard it crossed (the ranking-driving intensity)."""
    cmp_, pc, dvpt = r.get("cmp"), r.get("pc"), r.get("dvpt")
    cmp_str = f"₹{cmp_:,.0f}" if cmp_ is not None else "—"
    day = _pct((cmp_ / pc - 1) * 100) if (cmp_ is not None and pc) else ""
    powers = [r.get(k) for k in ("p1", "p3", "p6", "p12") if r.get(k)]
    inten = (dvpt / (sum(powers) / len(powers))) if (powers and dvpt) else None
    intx = f' · <b>{inten:.1f}×</b>' if inten else ""
    return (f'<td>{cmp_str} {day}</td>'
            f'<td>{_rupee(dvpt)}{intx}</td>'
            f'<td>{_rupee(r.get("dval"))}</td>')


@router.get("/dash", response_class=HTMLResponse)
def dash_home() -> HTMLResponse:
    sig_date, idx_date = _latest_dates()
    nifty, breadth, lead = {}, None, None
    top_sectors, weak_sectors, top_stocks, stealth_stocks = [], [], [], []
    pos_count = qual_count = rs_count = 0   # D33d strategy-hub live counts
    with get_conn() as conn:
        if idx_date:
            r = conn.execute(
                """SELECT ret_1d_pct r1d, ret_1m_pct r1m, pct_above_200d_avg a200
                   FROM index_signals WHERE index_name='Nifty 50' AND trade_date=?""",
                (idx_date,),
            ).fetchone()
            nifty = dict(r) if r else {}
            b = conn.execute(
                """SELECT AVG(CASE WHEN pct_above_200d_avg > 0 THEN 1.0 ELSE 0 END)*100 p
                   FROM index_signals
                   WHERE trade_date=? AND pct_above_200d_avg IS NOT NULL""",
                (idx_date,),
            ).fetchone()
            breadth = b["p"] if b and b["p"] is not None else None
            lr = conn.execute(
                f"""SELECT index_name FROM index_signals
                    WHERE trade_date=? AND index_name IN ({','.join('?' for _ in LEADERSHIP_SET)})
                    ORDER BY COALESCE(ret_3m_pct,-999) DESC LIMIT 1""",
                (idx_date, *LEADERSHIP_SET),
            ).fetchone()
            lead = lr["index_name"] if lr else None
            top_sectors = [dict(x) for x in conn.execute(
                f"""SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12
                   FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL
                     AND index_name IN ({_real_sectors_in()})
                   ORDER BY COALESCE(rs_vs_broad_slope_3m,-999) DESC LIMIT 5""",
                (idx_date,),
            ).fetchall()]
            weak_sectors = [dict(x) for x in conn.execute(
                f"""SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12
                   FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL
                     AND index_name IN ({_real_sectors_in()})
                   ORDER BY COALESCE(rs_vs_broad_slope_3m,999) ASC LIMIT 3""",
                (idx_date,),
            ).fetchall()]
        if sig_date:
            top_stocks = [dict(x) for x in conn.execute(
                f"""SELECT s.symbol, s.trigger_rank rank, s.is_ath_dvpt ath,
                           s.price_vs_hot_avg_pct pvh, s.accum_character ch,
                           b.close cmp, b.prev_close pc,
                           s.delivery_value_per_trade dvpt, s.delivery_value_today dval,
                           s.power_dvpt_1m p1, s.power_dvpt_3m p3,
                           s.power_dvpt_6m p6, s.power_dvpt_12m p12
                    FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                    {_SCAN_FILTERS}
                    ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC,
                             COALESCE(s.r_score,-1) DESC LIMIT 5""",
                (sig_date,),
            ).fetchall()]
            # D43 — "stealth accumulation": strong-hand accumulation (ACCUMULATION
            # + p_score>=3 + concentrated breadth) while still OFF the highs (not
            # yet marked up) — i.e. quietly building before the crowd notices.
            stealth_stocks = [dict(x) for x in conn.execute(
                f"""SELECT s.symbol, s.p_score psc, s.pct_from_52w_high pfh,
                           s.accum_character ch,
                           b.close cmp, b.prev_close pc,
                           s.delivery_value_per_trade dvpt, s.delivery_value_today dval,
                           s.power_dvpt_1m p1, s.power_dvpt_3m p3,
                           s.power_dvpt_6m p6, s.power_dvpt_12m p12
                    FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.accum_character='ACCUMULATION'
                      AND s.p_score>=3
                      AND COALESCE(s.trade_count_ratio_1m_6m,99) <= 1.1
                      AND s.pct_from_52w_high <= -10
                    {_SCAN_FILTERS}
                    ORDER BY s.p_score DESC, s.pct_from_52w_high ASC LIMIT 5""",
                (sig_date,),
            ).fetchall()]
            pos_count = conn.execute(
                f"""SELECT COUNT(*) c FROM stock_signals s
                    JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.trigger_rank IN ('SS','S')
                    {_SCAN_FILTERS}""",
                (sig_date,),
            ).fetchone()["c"]
            try:
                qual_count = conn.execute(
                    "SELECT COUNT(DISTINCT symbol) c FROM pattern_scores").fetchone()["c"]
            except Exception:
                qual_count = 0

    above200 = nifty.get("a200")
    nifty_up = above200 is not None and above200 > 0
    if breadth is None:
        bcls, blabel = "b-neu", "NO DATA"
    elif breadth >= 60 and nifty_up:
        bcls, blabel = "b-on", "RISK-ON"
    elif breadth < 40 or not nifty_up:
        bcls, blabel = "b-off", "RISK-OFF"
    else:
        bcls, blabel = "b-neu", "NEUTRAL"
    lead_txt = {"Nifty 50": "Large-caps leading",
                "Nifty Midcap 150": "Mid-caps leading",
                "Nifty Smallcap 250": "Small-caps leading"}.get(lead, lead or "—")
    breadth_txt = f"{breadth:.0f}%" if breadth is not None else "—"

    search = ('<form class="search" action="/dash/stock" method="get" autocomplete="off">'
              '<input name="sym" placeholder="Enter NSE ticker — e.g. RELIANCE" '
              'autocapitalize="characters"/><button type="submit">Go</button></form>')
    banner = (f'<div class="banner {bcls}">{blabel}'
              f'<small>· {breadth_txt} of indices &gt; 200-DMA · {_esc(lead_txt)}</small></div>')
    kpis = (f'<div class="kpi">'
            f'<div class="box"><div class="num">{_pct(nifty.get("r1d"))}</div>'
            f'<div class="lbl">Nifty 50 today</div></div>'
            f'<div class="box"><div class="num">{breadth_txt}</div>'
            f'<div class="lbl">indices &gt; 200-DMA</div></div>'
            f'<div class="box"><div class="num" style="font-size:14px;padding-top:7px;">'
            f'{_esc(lead_txt)}</div><div class="lbl">leadership 3m</div></div></div>')

    def sect_rows(rows):
        out = []
        for r in rows:
            st = r["st"] or "—"
            strip = _rs_strip(r["s1"], r["s3"], r["s6"], r["s12"])
            out.append(f'<tr><td><a class="row" href="/dash/ratio?idx={_q(r["nm"])}">'
                       f'<span class="sym">{_esc(r["nm"])}</span></a></td>'
                       f'<td>{strip}</td>'
                       f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                       f'<td>{_pct(r["s3"])}</td></tr>')
        return "".join(out)

    sectors_block = ""
    if top_sectors:
        sectors_block = (
            _strategy_badge("RS") +
            '<h2>Top sectors <span class="sub" style="margin:0">by 3m RS</span></h2>'
            '<div class="card" style="padding:6px 10px;"><table>'
            '<thead><tr><th>Sector</th><th>1m/3m/6m/12m</th><th>Trend</th><th>RS 3m</th></tr></thead>'
            f'<tbody>{sect_rows(top_sectors)}</tbody></table></div>'
            '<div class="ghdr">Weakest</div>'
            '<div class="card" style="padding:6px 10px;"><table>'
            f'<tbody>{sect_rows(weak_sectors)}</tbody></table></div>'
            '<a class="row sub" href="/dash/sectors">See full rotation →</a>')

    srows = []
    for r in top_stocks:
        rank = r["rank"] or "-"
        ath = "⚡" if r["ath"] else ""
        pvh = r["pvh"]
        entry = ("🟢" if pvh < -3 else ("🔴" if pvh > 3 else "🟡")) if pvh is not None else ""
        srows.append(f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                     f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
                     f'{_pos_cells(r)}'
                     f'<td>{_pct(pvh)} {entry}</td>'
                     f'<td><span class="pill p-{rank}">{rank}</span></td>'
                     f'<td>{_char_pill(r.get("ch"))}</td></tr>')
    stocks_block = ""
    if srows:
        stocks_block = (
            _strategy_badge("POS") +
            '<h2>Top trigger stocks</h2>'
            '<div class="card" style="padding:6px 10px;"><table>'
            '<thead><tr><th>Symbol</th><th>CMP · Δday</th><th>DVPT · ×power</th>'
            '<th>Deliv ₹</th><th>Δhot</th><th>Rank</th><th>Character</th></tr></thead>'
            f'<tbody>{"".join(srows)}</tbody></table></div>'
            '<a class="row sub" href="/dash/stocks">See all triggers →</a>')

    # D43 — Stealth accumulation board (concentrated ACCUMULATION still off the
    # highs). The smart-money-buying-before-markup setup.
    stealth_block = ""
    if stealth_stocks:
        stl = ""
        for r in stealth_stocks:
            psc = r["psc"] or 0
            stl += (f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                    f'<span class="sym">{_esc(r["symbol"])}</span></a></td>'
                    f'{_pos_cells(r)}'
                    f'<td><span class="pill p-{("SS" if psc>=5 else "S" if psc==4 else "A")}">'
                    f'{psc}/5</span></td>'
                    f'<td>{_pct(r["pfh"])}</td>'
                    f'<td>{_char_pill(r.get("ch"))}</td></tr>')
        stealth_block = (
            _strategy_badge("POS") +
            '<h2>Stealth accumulation <span class="sub" style="margin:0">'
            'concentrated buying, still off the highs</span></h2>'
            '<div class="card" style="padding:6px 10px;"><table>'
            '<thead><tr><th>Symbol</th><th>CMP · Δday</th><th>DVPT · ×power</th>'
            '<th>Deliv ₹</th><th>p-score</th><th>vs 52w-hi</th><th>Character</th></tr></thead>'
            f'<tbody>{stl}</tbody></table></div>'
            '<a class="row sub" href="/dash/stocks">See the full screen →</a>')

    # D33c — "strong-in-strong" leaders preview (stock + its sector both leading
    # the market). Bridges the macro sector read to the micro stock picks.
    leaders_block = ""
    if sig_date:
        from src.automation.stock_rs import leaders_laggards
        lead_rows = leaders_laggards("leaders", limit=300)
        rs_count = len(lead_rows)
        if lead_rows:
            lr = ""
            for r in lead_rows[:5]:
                rk = r["rs_rank"]
                lr += (f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                       f'<span class="sym">{_esc(r["symbol"])}</span></a></td>'
                       f'<td class="mut">{_esc(r["primary_sector"] or "—")}</td>'
                       f'<td>{rk if rk is not None else "—"}</td></tr>')
            leaders_block = (
                _strategy_badge("RS") +
                '<h2>Strong-in-strong leaders <span class="sub" style="margin:0">'
                'stock + sector both leading</span></h2>'
                '<div class="card" style="padding:6px 10px;"><table>'
                '<thead><tr><th>Symbol</th><th>Sector</th><th>RS rank</th></tr></thead>'
                f'<tbody>{lr}</tbody></table></div>'
                '<a class="row sub" href="/dash/leaders">See leaders &amp; laggards →</a>')

    # D45 — Conviction shortlist preview (ALL three pillars aligned). The payoff
    # board: an RS leader that institutions are accumulating now, with the entry.
    conviction_block = ""
    if sig_date:
        from src.automation.stock_rs import conviction_shortlist
        conv_rows = conviction_shortlist(limit=50)
        if conv_rows:
            cr = ""
            for r in conv_rows[:5]:
                nk = (is_near_key(r.get("gap_to_key_p3m")) or is_near_key(r.get("gap_to_key_p6m"))
                      or is_near_key(r.get("gap_to_key_p12m")))
                qual = "★" if (r.get("pt14_tier") and not r.get("pt14_dq")) else ""
                cr += (f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                       f'<span class="sym">{qual}{_esc(r["symbol"])}</span></a></td>'
                       f'<td class="mut">{_esc(r.get("primary_sector") or "—")}</td>'
                       f'<td>{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</td>'
                       f'<td>{"🎯" if nk else ""}</td></tr>')
            conviction_block = (
                '<div class="sbadge" style="background:#1a1430;border-color:#5a3fb8">'
                '<span class="tag" style="background:#8957e5;color:#fff">● CONVICTION</span>'
                '<span class="th">All three pillars aligned — an RS leader that institutions are '
                'accumulating now (D43), with the D44 entry read. The decision-ready shortlist.</span></div>'
                '<h2>⭐ Conviction shortlist <span class="sub" style="margin:0">'
                'leader + accumulating + entry</span></h2>'
                '<div class="card" style="padding:6px 10px;"><table>'
                '<thead><tr><th>Symbol</th><th>Sector</th><th>RS rank</th><th>Entry</th></tr></thead>'
                f'<tbody>{cr}</tbody></table></div>'
                '<a class="row sub" href="/dash/conviction">See the full shortlist →</a>')

    def _scard(cls, nm, thesis, count, href):
        return (f'<a class="scard sc-{cls}" href="{href}">'
                f'<div class="nm">{nm}</div><div class="th">{_esc(thesis)}</div>'
                f'<div class="ct">{count}</div></a>')
    strat_hub = (
        '<h2>Strategies <span class="sub" style="margin:0">pick your lens</span></h2>'
        '<div class="scards">'
        + _scard("POS", "Positioning", "Smart-money DVPT accumulation & entry zone.",
                 f'{pos_count} <small>SS/S today</small>', "/dash/stocks")
        + _scard("RS", "Relative Strength", "Beating the market & leading its sector.",
                 f'{rs_count} <small>leaders</small>', "/dash/leaders")
        + _scard("QUAL", "Quality (pt14)", "14-pattern fundamental durability.",
                 f'{qual_count} <small>scored</small>', "/dash/stock")
        + '</div>')

    body = (f'{search}{banner}{strat_hub}{conviction_block}{kpis}{sectors_block}{leaders_block}'
            f'{stocks_block}{stealth_block}'
            '<h2>Data freshness</h2>'
            f'<div class="card">Stock signals: <b>{sig_date or "—"}</b><br>'
            f'Index signals: <b>{idx_date or "—"}</b></div>'
            '<div class="sub">Read-only mirror of the Telegram bot data. '
            'Updated nightly 7:30 PM IST.</div>')
    return HTMLResponse(_shell("patearn — Indian-equity strategy dashboard", body, "dash", sig_date or ""))


@router.get("/dash/conviction", response_class=HTMLResponse)
def dash_conviction(limit: int = Query(60, ge=10, le=200)) -> HTMLResponse:
    """D45 — the cross-pillar Conviction shortlist: RS leader (D33c) + institutions
    accumulating now (D43 ACCUMULATION) + the D44 entry read, with pt14 quality as
    confirmation. Read-only synthesis over existing data; sortable/exportable `.dt`."""
    from src.automation.stock_rs import conviction_shortlist
    sig_date, _ = _latest_dates()
    rows = conviction_shortlist(limit=limit)

    trs = []
    for r in rows:
        rk = r.get("rs_rank")
        g3 = r.get("gap_to_key_p3m")
        nearkey = (is_near_key(g3) or is_near_key(r.get("gap_to_key_p6m"))
                   or is_near_key(r.get("gap_to_key_p12m")))
        pvh = r.get("pvh")
        bits = []
        if nearkey:
            bits.append("🎯 near key")
        if pvh is not None and pvh < -3:
            bits.append("🟢 discount")
        elif pvh is not None and pvh > 3:
            bits.append("🔴 extended")
        entry = " ".join(bits) if bits else "🟡 at-cost"
        tier, dq = r.get("pt14_tier"), r.get("pt14_dq")
        if tier and not dq:
            qual = f'<span class="pill p-SS">★ {_esc(tier)}</span>'
        elif tier and dq:
            qual = f'<span class="pill p-DOWNTREND">{_esc(tier)} ✗</span>'
        else:
            qual = '<span class="mut">unscored</span>'
        g3s = f'{g3:+.1f}%' if g3 is not None else '—'
        kp3 = r.get("key_price_p3m")
        trs.append(
            f'<tr data-nearkey="{1 if nearkey else 0}" data-qual="{1 if (tier and not dq) else 0}">'
            f'<td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="sym">{_esc(r["symbol"])}</span></a></td>'
            f'<td>{rk if rk is not None else "—"}</td>'
            f'<td class="mut">{_esc(r.get("primary_sector") or "—")}</td>'
            f'<td>{_char_pill(r.get("accum_character"))}</td>'
            f'<td>{entry}</td>'
            f'<td>{("₹"+_num(kp3,1)) if kp3 else "—"} <span class="mut">({g3s})</span></td>'
            f'<td><span class="pill p-{r.get("trigger_rank") or "C"}">{r.get("trigger_rank") or "-"}</span> '
            f'{r.get("p_score") or 0}/5</td>'
            f'<td>{qual}</td></tr>')

    badge = ('<div class="sbadge" style="background:#1a1430;border-color:#5a3fb8">'
             '<span class="tag" style="background:#8957e5;color:#fff">● CONVICTION</span>'
             '<span class="th">The synthesis of all three pillars — a name only lands here if it is '
             'an <b>RS leader</b> (beating the market AND leading its sector AND its sector beating the '
             'market), institutions are <b>accumulating</b> it now (D43), shown with the <b>entry</b> read '
             '(D44 near-key / discount). pt14 <b>quality</b> confirms where scored. Strongest leaders first.</span></div>')
    if trs:
        pills = ('<div id="cvbar" class="fbar">'
                 "<button class=\"fbtn on\" onclick=\"cflt('all',this)\">All</button>"
                 "<button class=\"fbtn\" onclick=\"cflt('nearkey',this)\">🎯 Near key</button>"
                 "<button class=\"fbtn\" onclick=\"cflt('qual',this)\">★ Quality-confirmed</button></div>")
        table = (pills + '<div class="card" style="padding:6px 10px;"><table id="cvtbl" class="dt">'
                 '<thead><tr><th>Symbol</th><th>RS rank</th><th>Sector</th><th>Character</th>'
                 '<th>Entry</th><th>Key 3m</th><th>Rank·p</th><th>Quality</th></tr></thead>'
                 f'<tbody>{"".join(trs)}</tbody></table></div>')
        js = ("<script>function cflt(f,el){"
              "document.querySelectorAll('#cvtbl tr[data-nearkey]').forEach(function(r){"
              "r.style.display=(f==='all'||r.dataset[f]==='1')?'':'none';});"
              "document.querySelectorAll('#cvbar .fbtn').forEach(function(b){"
              "b.classList.remove('on');});el.classList.add('on');}</script>")
    else:
        table = ('<div class="empty">No names clear all three pillars today — that\'s normal; '
                 'conviction is rare. Try <a class="row" style="display:inline" href="/dash/leaders">'
                 'leaders</a> or the <a class="row" style="display:inline" href="/dash/stocks">screen</a>.</div>')
        js = ""
    body = (badge + '<h2>⭐ Conviction shortlist</h2>'
            '<div class="sub">All three strategy pillars aligned. Click a header to sort · type to filter · ⬇ Export. '
            '🎯 = buyable near the institutional key price · ★ = pt14 quality-confirmed.</div>'
            + table + js)
    return HTMLResponse(_shell("Conviction · patearn", body, "stocks", sig_date or ""))


@router.get("/dash/markets", response_class=HTMLResponse)
def dash_markets() -> HTMLResponse:
    _, idx_date = _latest_dates()
    allrows = {}
    if idx_date:
        with get_conn() as conn:
            for r in conn.execute(
                """SELECT g.index_name nm, g.ret_1d_pct r1d, g.ret_1m_pct r1m,
                          g.ret_3m_pct r3m, g.pct_above_200d_avg a200,
                          g.rs_vs_broad_trend_state st, g.broad_benchmark bb,
                          g.rs_vs_broad_slope_1m s1, g.rs_vs_broad_slope_3m s3,
                          g.rs_vs_broad_slope_6m s6, g.rs_vs_broad_slope_12m s12,
                          x.close_value close
                   FROM index_signals g
                   LEFT JOIN index_rows x USING (index_name, trade_date)
                   WHERE g.trade_date=?""",
                (idx_date,),
            ).fetchall():
                allrows[r["nm"]] = dict(r)
    if not allrows:
        return HTMLResponse(_shell("Markets · patearn",
                                   '<div class="empty">No index data yet.</div>',
                                   "markets", idx_date or ""))

    def maj_card(v):
        st = v["st"]
        chip = f' <span class="pill p-{st}">{st[:5]}</span>' if st else ''
        strip = _rs_strip(v["s1"], v["s3"], v["s6"], v["s12"])
        return (f'<a class="maj" href="/dash/ratio?idx={_q(v["nm"])}">'
                f'<div class="nm">{_esc(v["nm"])}{chip}</div>'
                f'<div class="rr"><span class="mut">ABS</span>'
                f'<span>{_num(v["close"],0)}</span>'
                f'<span>1d {_pct(v["r1d"])}</span>'
                f'<span>1m {_pct(v["r1m"])}</span>'
                f'<span>3m {_pct(v["r3m"])}</span></div>'
                f'<div class="rr"><span class="grp">RS</span>{strip}'
                f'<span class="mut" style="font-size:11px">vs Nifty 500</span></div></a>')

    broad_html = "".join(maj_card(allrows[n]) for n in MAJOR_BROAD if n in allrows)
    sect_html = "".join(maj_card(allrows[n]) for n in MAJOR_SECTORS if n in allrows)

    bundle = sorted(allrows.values(), key=lambda v: (v["r3m"] is None, -(v["r3m"] or 0)))
    brows = []
    for v in bundle:
        grp = "broad" if v["bb"] is None else "sector"
        st = v["st"] or ""
        chip = (f'<span class="pill p-{st}">{st[:5]}</span>' if st
                else '<span class="mut">—</span>')
        brows.append(
            f'<tr data-grp="{grp}"><td class="sym">{_esc(v["nm"])}</td>'
            f'<td>{_pct(v["r1d"])}</td><td>{_pct(v["r1m"])}</td>'
            f'<td>{_pct(v["r3m"])}</td><td class="rsgrp">{chip}</td></tr>')

    js = ("<script>function mflt(g,el){"
          "document.querySelectorAll('#mbundle tr[data-grp]').forEach(function(r){"
          "r.style.display=(g==='all'||r.dataset.grp===g)?'':'none';});"
          "document.querySelectorAll('#mbar .fbtn').forEach(function(b){"
          "b.classList.remove('on');});el.classList.add('on');}</script>")

    body = (
        '<h2>Major indexes &amp; sectors</h2>'
        '<div class="sub">Broad market + core sectors. Tap any → its stocks. '
        '<a class="row" style="display:inline" '
        'href="/dash/compare?idx=Nifty+50&idx=Nifty+500">⇄ Compare indices</a></div>'
        '<div class="ghdr">Broad / size</div>'
        f'<div class="majgrid">{broad_html}</div>'
        '<div class="ghdr">Core sectors</div>'
        f'<div class="majgrid">{sect_html}</div>'
        '<h2>Full index bundle</h2>'
        '<div class="sub">Everything else — strategy, thematic, factor.</div>'
        '<div id="mbar" class="fbar">'
        "<button class=\"fbtn on\" onclick=\"mflt('all',this)\">All</button>"
        "<button class=\"fbtn\" onclick=\"mflt('broad',this)\">Broad/Size</button>"
        "<button class=\"fbtn\" onclick=\"mflt('sector',this)\">Sectoral</button></div>"
        '<div class="card" style="padding:6px 10px;"><table id="mbundle" class="dt">'
        '<thead>'
        '<tr><th></th><th colspan="3">RETURN</th><th class="rsgrp grp">RS</th></tr>'
        '<tr><th>Index</th><th>1d</th><th>1m</th><th>3m</th><th class="rsgrp">Trend</th></tr></thead>'
        f'<tbody>{"".join(brows)}</tbody></table></div>' + js)
    return HTMLResponse(_shell("Markets · patearn", body, "markets", idx_date or ""))


@router.get("/dash/sectors", response_class=HTMLResponse)
def dash_sectors() -> HTMLResponse:
    _, idx_date = _latest_dates()
    rows = []
    if idx_date:
        with get_conn() as conn:
            order = ("CASE rs_vs_broad_trend_state WHEN 'BREAKOUT' THEN 0 "
                     "WHEN 'UPTREND' THEN 1 WHEN 'CONSOLIDATING' THEN 2 "
                     "WHEN 'DOWNTREND' THEN 3 WHEN 'BREAKDOWN' THEN 4 ELSE 5 END")
            rows = [dict(r) for r in conn.execute(
                f"""SELECT index_name, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12,
                          ret_1m_pct r1, ret_3m_pct r3
                   FROM index_signals
                   WHERE trade_date=? AND broad_benchmark IS NOT NULL
                     AND index_name IN ({_real_sectors_in()})
                   ORDER BY {order} ASC, COALESCE(rs_vs_broad_slope_3m,-999) DESC""",
                (idx_date,),
            ).fetchall()]
    if not rows:
        body = '<div class="empty">No index signals yet. Run the index backfill on the VPS.</div>'
    else:
        trs = []
        for r in rows:
            st = r["st"] or "—"
            nm = r["index_name"]
            strip = _rs_strip(r["s1"], r["s3"], r["s6"], r["s12"])
            trs.append(
                f'<tr><td><a class="row" href="/dash/stocks?sector={_q(nm)}">'
                f'<span class="sym">{_esc(nm)}</span></a></td>'
                f'<td>{_pct(r["r1"])}</td><td>{_pct(r["r3"])}</td>'
                f'<td class="rsgrp"><a class="row" style="display:inline" '
                f'href="/dash/ratio?idx={_q(nm)}">{strip}</a></td>'
                f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                f'<td>{_pct(r["s3"])}</td></tr>'
            )
        body = f"""
{_strategy_badge("RS")}
<h2>Sector rotation</h2>
<div class="sub">Real economic sectors only (factor/thematic indices live under Markets). Sorted strongest RS trend first. Tap a name → its stocks; tap the strip → the ratio chart. <a class="row" style="display:inline" href="/dash/rs">Full RS ranking →</a> · <a class="row" style="display:inline" href="/dash/compare?idx=Nifty+50&idx=Nifty+500">⇄ Compare indices</a></div>
<div class="card" style="padding:6px 10px;">
<table class="dt">
<thead>
<tr><th colspan="3">RETURN</th><th colspan="3" class="rsgrp grp">RELATIVE STRENGTH vs Nifty 500</th></tr>
<tr><th>Sector</th><th>1m</th><th>3m</th><th class="rsgrp">1m / 3m / 6m / 12m</th><th>Trend</th><th>RS 3m</th></tr>
</thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("Sectors · patearn", body, "sectors", idx_date or ""))


@router.get("/dash/rs", response_class=HTMLResponse)
def dash_rs() -> HTMLResponse:
    """Cross-sector RS-momentum ranking (on-read; 0.6·slope_3m + 0.4·slope_6m)."""
    _, idx_date = _latest_dates()
    rows = []
    if idx_date:
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                f"""SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12,
                          (0.6*COALESCE(rs_vs_broad_slope_3m,0)
                           +0.4*COALESCE(rs_vs_broad_slope_6m,0)) mom
                   FROM index_signals
                   WHERE trade_date=? AND broad_benchmark IS NOT NULL
                     AND index_name IN ({_real_sectors_in()})
                   ORDER BY mom DESC""",
                (idx_date,),
            ).fetchall()]
    if not rows:
        body = '<div class="empty">No index signals yet. Run the index backfill on the VPS.</div>'
        return HTMLResponse(_shell("RS ranking · patearn", body, "sectors", idx_date or ""))

    moms = sorted(r["mom"] for r in rows)
    n_mom = len(moms)

    def _pctl(m):
        if not n_mom:
            return 50
        below = sum(1 for x in moms if x < m)
        return max(1, min(99, round(below / n_mom * 99)))

    trs = []
    for i, r in enumerate(rows, 1):
        st = r["st"] or "—"
        nm = r["nm"]
        strip = _rs_strip(r["s1"], r["s3"], r["s6"], r["s12"])
        p = _pctl(r["mom"])
        trs.append(
            f'<tr><td class="mut">{i}</td>'
            f'<td><a class="row" href="/dash/ratio?idx={_q(nm)}">'
            f'<span class="sym">{_esc(nm)}</span></a></td>'
            f'<td>{strip}</td>'
            f'<td>{_pct(r["mom"])}</td>'
            f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
            f'<td style="min-width:70px"><div class="bar"><span style="width:{p}%"></span></div></td></tr>')
    body = f"""
{_strategy_badge("RS")}
<h2>RS-momentum ranking</h2>
<div class="sub">All sectors by RS momentum (0.6·3m + 0.4·6m slope vs Nifty 500), strongest first. Tap a sector → its ratio chart. <a class="row" style="display:inline" href="/dash/sectors">← Sector rotation</a></div>
<div class="card" style="padding:6px 10px;">
<table class="dt">
<thead><tr><th>#</th><th>Sector</th><th>1m/3m/6m/12m</th><th>Mom</th><th>Trend</th><th>Pctl</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("RS ranking · patearn", body, "sectors", idx_date or ""))


@router.get("/dash/leaders", response_class=HTMLResponse)
def dash_leaders() -> HTMLResponse:
    """D33c composite screen — 'strong-in-strong' leaders + 'weak-in-weak'
    laggards: a stock whose RS vs its sector AND vs the broad market AND its
    sector's own RS vs broad are ALL aligned (up = leader, down = laggard)."""
    from src.automation.stock_rs import leaders_laggards
    sig_date, _ = _latest_dates()
    leaders = leaders_laggards("leaders", limit=60)
    laggards = leaders_laggards("laggards", limit=40)

    def _tbl(rows, up):
        if not rows:
            return ('<div class="card"><div class="sub" style="margin:0">None right now — '
                    f'no stock has all three RS layers aligned {"up" if up else "down"}.'
                    '</div></div>')
        trs = ""
        for r in rows:
            rk = r["rs_rank"]
            bs = r["broad_state"] or "—"
            ss = r["sector_state"] or "—"
            xs = r["sector_broad_state"] or "—"
            trs += (
                f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                f'<span class="sym">{_esc(r["symbol"])}</span></a></td>'
                f'<td>{rk if rk is not None else ""}</td>'
                f'<td><a class="row" href="/dash/ratio?idx={_q(r["primary_sector"])}">'
                f'{_esc(r["primary_sector"])}</a></td>'
                f'<td><span class="pill p-{bs}">{_esc(bs[:5])}</span></td>'
                f'<td><span class="pill p-{ss}">{_esc(ss[:5])}</span></td>'
                f'<td><span class="pill p-{xs}">{_esc(xs[:5])}</span></td></tr>')
        return ('<div class="card" style="padding:6px 10px;"><table class="dt">'
                '<thead><tr><th>Symbol</th><th>RS rank</th><th>Sector</th>'
                '<th>stock vs broad</th><th>stock vs sector</th>'
                '<th>sector vs broad</th></tr></thead>'
                f'<tbody>{trs}</tbody></table></div>')

    body = f"""
{_strategy_badge("RS")}
<h2>Leaders <span class="sub" style="margin:0">strong-in-strong</span></h2>
<div class="sub">Stock leads its sector <b>and</b> the market, and the sector leads the market too — all three RS reads in UPTREND/BREAKOUT. Strongest (RS rank) first. Tap a symbol → its page; tap a sector → its ratio chart.</div>
{_tbl(leaders, True)}
<h2 style="margin-top:18px">Laggards <span class="sub" style="margin:0">weak-in-weak</span></h2>
<div class="sub">All three RS reads in DOWNTREND/BREAKDOWN — weakest first.</div>
{_tbl(laggards, False)}
"""
    return HTMLResponse(_shell("Leaders · patearn", body, "stocks", sig_date or ""))


@router.get("/dash/scan", response_class=HTMLResponse)
def dash_scan(limit: int = Query(25, ge=5, le=60)) -> HTMLResponse:
    sig_date, _ = _latest_dates()
    rows = []
    if sig_date:
        with get_conn() as conn:
            rank_order = ("CASE s.trigger_rank WHEN 'SS' THEN 0 WHEN 'S' THEN 1 "
                          "WHEN 'A' THEN 2 WHEN 'B' THEN 3 WHEN 'C' THEN 4 ELSE 5 END")
            rows = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, s.trigger_rank rank, s.r_score, s.p_score,
                          s.is_ath_dvpt ath, s.price_vs_hot_avg_pct pvh,
                          s.next_p_above nextp, s.gap_to_next_p_pct gap, b.close
                   FROM stock_signals s
                   JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                   {_SCAN_FILTERS}
                   ORDER BY COALESCE(s.is_ath_dvpt,0) DESC,
                            COALESCE(s.p_score,-1) DESC, COALESCE(s.r_score,-1) DESC,
                            {rank_order} ASC,
                            COALESCE(s.ratio_today_vs_power_1m,0) DESC
                   LIMIT ?""",
                (sig_date, limit),
            ).fetchall()]
    if not rows:
        body = '<div class="empty">No signals for the latest day yet.</div>'
    else:
        trs = []
        for r in rows:
            rank = r["rank"] or "-"
            ath = "⚡" if r["ath"] else ""
            pvh = r["pvh"]
            entry = ""
            if pvh is not None:
                entry = "🟢" if pvh < -3 else ("🔴" if pvh > 3 else "🟡")
            near = ""
            if r["nextp"] and r["gap"] is not None:
                near = f'{r["nextp"]} {r["gap"]:+.0f}%'
            trs.append(
                f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
                f'<td><span class="pill p-{rank}">{rank}</span></td>'
                f'<td class="mut">{r["r_score"] or 0}/{r["p_score"] or 0}</td>'
                f'<td>{_num(r["close"],1)}</td>'
                f'<td>{_pct(pvh)} {entry}</td>'
                f'<td class="mut">{near}</td></tr>'
            )
        body = f"""
<h2>Layered DVPT scan</h2>
<div class="sub">Sort: ATH → p_score → r_score → rank. Tap a symbol for full detail.</div>
<div class="card" style="padding:6px 10px;">
<table>
<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>Close</th><th>Δhot</th><th>Near-P</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("Scan · patearn", body, "scan", sig_date or ""))


@router.get("/dash/stocks", response_class=HTMLResponse)
def dash_stocks(sector: str = Query(""), limit: int = Query(40, ge=10, le=120),
                period: str = Query("d")) -> HTMLResponse:
    sig_date, _ = _latest_dates()
    sector = sector.strip()
    period = period if period in ("d", "w", "m") else "d"
    n_days = 5 if period == "w" else 22   # trading-day window for weekly/monthly
    rows, watch, sector_syms = [], [], []
    char_map = {}   # D43 — symbol -> latest-day accum_character (weekly/monthly)
    with get_conn() as conn:
        if period == "d":
            # ---- DAILY: today's layered DVPT triggers (existing behaviour) ----
            if sector:
                sector_syms = _sector_symbols(conn, sector)
            if sig_date and not (sector and not sector_syms):
                params = [sig_date]
                sector_clause = ""
                if sector and sector_syms:
                    ph = ",".join("?" for _ in sector_syms)
                    sector_clause = f" AND s.symbol IN ({ph})"
                    params += sector_syms
                params.append(limit)
                rank_order = ("CASE s.trigger_rank WHEN 'SS' THEN 0 WHEN 'S' THEN 1 "
                              "WHEN 'A' THEN 2 WHEN 'B' THEN 3 WHEN 'C' THEN 4 ELSE 5 END")
                rows = [dict(r) for r in conn.execute(
                    f"""SELECT s.symbol, s.trigger_rank rank, s.r_score, s.p_score,
                              s.is_ath_dvpt ath, s.price_vs_hot_avg_pct pvh,
                              s.next_p_above nextp, s.gap_to_next_p_pct gap, b.close,
                              s.accum_character ch, s.delivery_value_today dvt,
                              s.trade_count_ratio_1m_6m tcr,
                              s.delivery_value_per_trade dvpt,
                              s.power_dvpt_1m p1, s.power_dvpt_3m p3,
                              s.power_dvpt_6m p6, s.power_dvpt_12m p12,
                              s.gap_to_key_p1m gk1, s.gap_to_key_p3m gk3,
                              s.gap_to_key_p6m gk6, s.gap_to_key_p12m gk12
                       FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                       WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                       {_SCAN_FILTERS}{sector_clause}
                       ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC,
                                COALESCE(s.r_score,-1) DESC, {rank_order} ASC,
                                COALESCE(s.ratio_today_vs_power_1m,0) DESC
                       LIMIT ?""",
                    params,
                ).fetchall()]
        else:
            # ---- WEEKLY / MONTHLY (D33d v1): roll up the daily verdicts over the
            # last N trading days so a mid-window spike isn't missed if you don't
            # check daily. On-read aggregate over existing stock_signals — no
            # backfill. "hits" = days that fired an A+ trigger (p_score>=3). ----
            wdates = [r["d"] for r in conn.execute(
                "SELECT DISTINCT trade_date d FROM stock_signals ORDER BY d DESC LIMIT ?",
                (n_days,)).fetchall()]
            if wdates:
                window_start = wdates[-1]
                rows = [dict(r) for r in conn.execute(
                    f"""SELECT s.symbol,
                              COUNT(CASE WHEN s.p_score>=3 THEN 1 END) hits,
                              MAX(s.p_score) peak_p,
                              MAX(s.is_ath_dvpt) ath,
                              AVG(s.delivery_value_per_trade) wmean
                       FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                       WHERE s.trade_date>=? AND s.delivery_value_per_trade IS NOT NULL
                       {_SCAN_FILTERS}
                       GROUP BY s.symbol
                       HAVING hits>=1
                       ORDER BY peak_p DESC, hits DESC, wmean DESC
                       LIMIT ?""",
                    (window_start, limit)).fetchall()]
                # D43 — character on each symbol's latest stored day (= sig_date
                # for this liquid universe). Attached to the rollup rows below.
                if rows and sig_date:
                    syms = [r["symbol"] for r in rows]
                    ph = ",".join("?" for _ in syms)
                    char_map = {x["symbol"]: x["accum_character"] for x in conn.execute(
                        f"""SELECT symbol, accum_character FROM stock_signals
                            WHERE trade_date=? AND symbol IN ({ph})""",
                        (sig_date, *syms)).fetchall()}
        watch = [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]

    search = ('<form class="search" action="/dash/stock" method="get" autocomplete="off">'
              '<input name="sym" placeholder="Enter NSE ticker — e.g. RELIANCE" '
              'autocapitalize="characters"/><button type="submit">Go</button></form>')

    # Daily / Weekly / Monthly toggle (weekly & monthly are market-wide).
    def _ptab(p, lbl):
        on = " on" if period == p else ""
        return f'<a class="fbtn{on}" href="/dash/stocks?period={p}">{lbl}</a>'
    ptoggle = ('<div class="fbar" style="margin-bottom:8px">'
               + _ptab("d", "Daily") + _ptab("w", "Weekly") + _ptab("m", "Monthly")
               + '</div>')

    badge = _strategy_badge("POS")
    if period != "d":
        win = "this week (last 5 trading days)" if period == "w" else "this month (last ~22 trading days)"
        head = (f'<h2>{"Weekly" if period == "w" else "Monthly"} triggers</h2>'
                f'<div class="sub">Stocks that fired an <b>A+ DVPT trigger</b> on <b>any</b> day '
                f'{win} — so a mid-window institutional spike isn\'t missed if you don\'t check '
                f'daily. Ranked by peak intensity, then how many days it fired. '
                f'<a class="row" style="display:inline" href="/dash/stocks?period=d">← back to daily</a></div>')
    elif sector:
        head = (f'<h2>Stocks in {_esc(sector)}</h2>'
                f'<div class="sub">{len(sector_syms)} constituents · by trigger strength · '
                f'<a class="row" style="display:inline" href="/dash/stocks">clear ↺</a></div>')
        if not sector_syms:
            if sector in REAL_SECTORS:
                # A genuine sector whose constituents just aren't loaded yet —
                # NOT a factor index. (Don't mislabel; the membership fetch for
                # it is pending or failed.)
                head += (f'<div class="card sub">Constituents for this sector aren\'t loaded yet '
                         f'(membership refresh pending). '
                         f'<a class="row" style="display:inline" href="/dash/ratio?idx={_q(sector)}">'
                         f'See its ratio chart →</a></div>')
            else:
                head += (f'<div class="card sub">No constituents tracked for this index — it\'s a '
                         f'factor/thematic index, not a sector. '
                         f'<a class="row" style="display:inline" href="/dash/ratio?idx={_q(sector)}">'
                         f'See its ratio chart →</a></div>')
    else:
        head = ('<h2>Stock screen</h2>'
                '<div class="sub">Layered DVPT triggers (today). Filter, then tap a symbol.</div>')

    js = ""
    if period == "d":
        trs = []
        for r in rows:
            rank = r["rank"] or "-"
            ath = "⚡" if r["ath"] else ""
            pvh = r["pvh"]
            entry = ("🟢" if pvh < -3 else ("🔴" if pvh > 3 else "🟡")) if pvh is not None else ""
            near, near_flag = "", "0"
            if r["nextp"] and r["gap"] is not None:
                near = f'{r["nextp"]} {r["gap"]:+.0f}%'
                if r["gap"] > -10 and (r["r_score"] or 0) >= 4:
                    near_flag = "1"
            ch = r.get("ch")
            dvt = r.get("dvt")
            dvt_cr = f'{dvt/1e7:,.1f}' if dvt else "—"   # ₹ → Cr
            # D44 near-key (any horizon gap within the asymmetric launch band)
            near_key = any(is_near_key(r.get(g)) for g in ("gk1", "gk3", "gk6", "gk12"))
            flags = (f'data-ss="{1 if rank == "SS" else 0}" '
                     f'data-aplus="{1 if (r["p_score"] or 0) >= 3 else 0}" '
                     f'data-ath="{1 if r["ath"] else 0}" '
                     f'data-disc="{1 if (pvh is not None and pvh < -3) else 0}" '
                     f'data-near="{near_flag}" '
                     f'data-accum="{1 if ch == "ACCUMULATION" else 0}" '
                     f'data-distrib="{1 if ch == "DISTRIBUTION" else 0}" '
                     f'data-nearkey="{1 if near_key else 0}"')
            ix = _intensity(r)
            trs.append(
                f'<tr {flags}><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
                f'<td><span class="pill p-{rank}">{rank}</span></td>'
                f'<td class="mut">{r["r_score"] or 0}/{r["p_score"] or 0}</td>'
                f'<td><b>{(f"{ix:.1f}×" if ix else "—")}</b></td>'
                f'<td>{_num(r["close"], 1)}</td>'
                f'<td>{_pct(pvh)} {entry}</td>'
                f'<td>{_char_pill(ch)}</td>'
                f'<td class="mut">{dvt_cr}</td>'
                f'<td class="mut">{near}</td></tr>')
        if trs:
            pills = ('<div id="sbar" class="fbar">'
                     "<button class=\"fbtn on\" onclick=\"sflt('all',this)\">All</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('ss',this)\">SS</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('aplus',this)\">A+</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('ath',this)\">⚡ ATH</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('disc',this)\">🟢 Discount</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('near',this)\">🔥 Near-break</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('accum',this)\">🟢 Accumulation</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('distrib',this)\">🔴 Distribution</button>"
                     "<button class=\"fbtn\" onclick=\"sflt('nearkey',this)\">🎯 Near key price</button></div>")
            table = (pills + '<div class="card" style="padding:6px 10px;"><table id="stbl" class="dt">'
                     '<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>×pow</th><th>Close</th>'
                     '<th>Δhot</th><th>Character</th><th>Deliv ₹Cr</th><th>Near-P</th></tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table></div>')
            js = ("<script>function sflt(f,el){"
                  "document.querySelectorAll('#stbl tr[data-ss]').forEach(function(r){"
                  "r.style.display=(f==='all'||r.dataset[f]==='1')?'':'none';});"
                  "document.querySelectorAll('#sbar .fbtn').forEach(function(b){"
                  "b.classList.remove('on');});el.classList.add('on');}</script>")
        else:
            table = '<div class="empty">No stocks match.</div>'
    else:
        _RK = {5: "SS", 4: "S", 3: "A", 2: "B", 1: "C"}
        trs = []
        for r in rows:
            rk = _RK.get(r["peak_p"] or 0, "-")
            ath = "⚡" if r["ath"] else ""
            wm = r["wmean"]
            trs.append(
                f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
                f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
                f'<td><span class="pill p-{rk}">{rk}</span></td>'
                f'<td>{r["hits"]}/{n_days}</td>'
                f'<td class="mut">{_num(wm, 0) if wm is not None else "—"}</td>'
                f'<td>{_char_pill(char_map.get(r["symbol"]))}</td></tr>')
        if trs:
            table = ('<div class="card" style="padding:6px 10px;"><table class="dt">'
                     '<thead><tr><th>Symbol</th><th>Peak rank</th>'
                     '<th>Days fired</th><th>Avg DVPT ₹</th><th>Character</th></tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table></div>')
        else:
            table = '<div class="empty">No A+ triggers in this window yet.</div>'

    watch_block = ""
    if watch and period == "d":
        chips = "".join(f'<a class="chip" href="/dash/stock?sym={_esc(s)}">{_esc(s)}</a>'
                        for s in watch)
        watch_block = f'<h2>Watchlist</h2><div class="chips">{chips}</div>'

    wb_link = ('<a class="row sub" href="/dash/screener" style="margin:0 0 4px">'
               '🧮 Screener ⇄ <span class="mut">all strategies, one wide data-first grid (scroll →)</span></a>'
               '<a class="row sub" href="/dash/workbench" style="margin:0 0 8px">'
               'Workbench ⇄ <span class="mut">every DVPT signal in one sortable table</span></a>')
    body = search + ptoggle + badge + wb_link + head + table + watch_block + js
    return HTMLResponse(_shell("Stocks · patearn", body, "stocks", sig_date or ""))


@router.get("/dash/workbench", response_class=HTMLResponse)
def dash_workbench(limit: int = Query(200, ge=20, le=1000)) -> HTMLResponse:
    """D44 — every DVPT / key-price / character / activity signal for the latest
    day in ONE wide, sortable, downloadable table. Render-only; reuses the
    existing `_DT_JS` data-grid toolbar (click-sort, filter, Export-to-CSV)."""
    sig_date, _ = _latest_dates()
    rows = []
    if sig_date:
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, b.close, s.delivery_value_per_trade dvpt,
                          s.trigger_rank rank, s.r_score, s.p_score, s.accum_character ch,
                          s.key_price_p3m kp3, s.gap_to_key_p3m gk3,
                          s.key_price_p6m kp6, s.gap_to_key_p6m gk6,
                          s.key_price_p12m kp12, s.gap_to_key_p12m gk12,
                          s.power_dvpt_3m pw3, s.avg_close_p3m ac3,
                          s.avg_trade_qty atq, s.avg_deliv_qty_per_trade adq,
                          s.turnover_surge_1m su1, s.turnover_surge_3m su3,
                          s.turnover_surge_1y su1y,
                          s.delivery_value_today dvt, s.pct_from_52w_high hh
                   FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                   {_SCAN_FILTERS}
                   ORDER BY COALESCE(s.p_score,-1) DESC,
                            COALESCE(s.delivery_value_today,0) DESC
                   LIMIT ?""",
                (sig_date, limit)).fetchall()]

    def kpf(v):
        return f'₹{v:,.1f}' if v is not None else '—'

    def gapcell(g):
        if g is None:
            return '<td class="mut">—</td>'
        sty = ' style="background:#16341f;color:#7ee787;font-weight:700"' if is_near_key(g) else ''
        return f'<td{sty}>{g:+.1f}%</td>'

    def nf(v, d=0):
        return _num(v, d) if v is not None else '—'

    trs = []
    for r in rows:
        rank = r["rank"] or "-"
        dvt = r["dvt"]
        dvt_cr = f'{dvt/1e7:,.1f}' if dvt else '—'
        trs.append(
            f'<tr><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="sym">{_esc(r["symbol"])}</span></a></td>'
            f'<td>{nf(r["close"],1)}</td>'
            f'<td>{nf(r["dvpt"],0)}</td>'
            f'<td><span class="pill p-{rank}">{rank}</span></td>'
            f'<td class="mut">{r["r_score"] or 0}/{r["p_score"] or 0}</td>'
            f'<td>{_char_pill(r["ch"])}</td>'
            f'<td>{kpf(r["kp3"])}</td>{gapcell(r["gk3"])}'
            f'<td>{kpf(r["kp6"])}</td>{gapcell(r["gk6"])}'
            f'<td>{kpf(r["kp12"])}</td>{gapcell(r["gk12"])}'
            f'<td>{nf(r["pw3"],0)}</td>'
            f'<td>{kpf(r["ac3"])}</td>'
            f'<td>{nf(r["atq"],0)}</td>'
            f'<td>{nf(r["adq"],0)}</td>'
            f'<td>{nf(r["su1"],2)}</td><td>{nf(r["su3"],2)}</td><td>{nf(r["su1y"],2)}</td>'
            f'<td>{dvt_cr}</td>'
            f'<td>{_pct(r["hh"])}</td></tr>')

    head = ('<thead><tr><th>Symbol</th><th>Close</th><th>DVPT</th><th>Rank</th><th>r/p</th>'
            '<th>Character</th><th>Key 3m</th><th>Gap 3m</th><th>Key 6m</th><th>Gap 6m</th>'
            '<th>Key 12m</th><th>Gap 12m</th><th>Pow 3m</th><th>AvgClose 3m</th>'
            '<th>Trade qty</th><th>Deliv/tr</th><th>Surge 1m</th><th>Surge 3m</th><th>Surge 1y</th>'
            '<th>Deliv ₹Cr</th><th>52w-hi</th></tr></thead>')
    if trs:
        table = ('<div class="card" style="padding:6px 10px;overflow-x:auto">'
                 '<table class="dt" style="min-width:1180px">'
                 + head + f'<tbody>{"".join(trs)}</tbody></table></div>')
    else:
        table = '<div class="empty">No data yet.</div>'

    body = (_strategy_badge("POS") +
            '<h2>Workbench <span class="sub" style="margin:0">every signal, one table</span></h2>'
            '<div class="sub">Latest day · liquid equity universe. Click a header to sort · type to filter · '
            '<b>⬇ Export</b> to CSV/Excel. 🟢 gap cell = in the launch band (−1%…+5% of the value-weighted '
            'key price). <a class="row" style="display:inline" href="/dash/stocks">← back to screen</a></div>'
            + table)
    return HTMLResponse(_shell("Workbench · patearn", body, "stocks", sig_date or ""))


@router.get("/dash/screener", response_class=HTMLResponse)
def dash_screener(scope: str = Query("Nifty 500"),
                  limit: int = Query(600, ge=50, le=2000)) -> HTMLResponse:
    """D54 — the data-first wide screener (frozen-pane grid). A PRINCIPLED,
    scope-selectable universe (default = Nifty 500 constituents; switch to any
    broad index / sector / watchlist / all) — never an arbitrary top-N. Every
    built strategy's raw values sit BESIDE its verdict (D-UI-1), grouped
    Identity · Conviction · Positioning(DVPT) · Relative-Strength · Quality ·
    Context, ranked by a tri-pillar Conviction score (positioning + RS) with a
    ★ triple-confirm flag (strong positioning + RS, quality not failing). Frozen
    header band + frozen Symbol column (scroll both ways) in a full-bleed grid.
    Reuses table.dt (_DT_JS sort/filter/CSV). CPR group joins at D53."""
    sig_date, _ = _latest_dates()
    scope = (scope or "Nifty 500").strip()
    is_all = scope.lower() == "all"
    is_watch = scope.lower() in ("watch", "watchlist")
    rows, pt, n_members, cpr_by_tf = [], {}, None, {}
    if sig_date:
        with get_conn() as conn:
            if is_all:
                scope_syms = None
            elif is_watch:
                scope_syms = [r["symbol"] for r in conn.execute(
                    "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]
            else:
                scope_syms = _sector_symbols(conn, scope)
            n_members = len(scope_syms) if scope_syms is not None else None

            scope_clause, params = "", [sig_date]
            if scope_syms is not None:
                use = scope_syms or ["\x00"]   # empty scope -> empty result, not a SQL error
                scope_clause = " AND s.symbol IN (" + ",".join("?" for _ in use) + ")"
                params += use
            params.append(limit)

            conv = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
            rows = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, s.primary_sector sector, b.close,
                          s.pct_from_52w_high hh, s.trigger_rank rank,
                          s.r_score, s.p_score, s.is_ath_dvpt ath,
                          s.delivery_value_per_trade dvpt, s.power_dvpt_1m p1,
                          s.power_dvpt_3m p3, s.power_dvpt_6m p6, s.power_dvpt_12m p12,
                          s.delivery_value_today dvt, b.deliv_per,
                          s.accum_character ch, s.price_vs_hot_avg_pct pvh,
                          s.turnover_surge_1m su1, s.rs_rank,
                          s.rs_vs_broad_trend_state rsbt, s.rs_vs_broad_slope_1m b1,
                          s.rs_vs_broad_slope_3m b3, s.rs_vs_broad_slope_6m b6,
                          s.rs_vs_broad_slope_12m b12, s.rs_vs_sector_trend_state rsst,
                          {conv} conv
                   FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                   {_SCAN_FILTERS}{scope_clause}
                   ORDER BY conv DESC, COALESCE(s.p_score,-1) DESC,
                            COALESCE(s.delivery_value_today,0) DESC
                   LIMIT ?""", params).fetchall()]
            if rows:
                syms = [r["symbol"] for r in rows]
                ph = ",".join("?" for _ in syms)
                pt = {x["symbol"]: x for x in conn.execute(
                    f"""SELECT symbol, ns_base, tier, qg_pass, MAX(scored_at)
                        FROM pattern_scores WHERE symbol IN ({ph}) GROUP BY symbol""",
                    syms).fetchall()}
                cpr_by_tf = _cpr_latest_by_tf(conn, syms)   # CPR Structure group (D53)

    def trend_pill(st):
        return f'<span class="pill p-{_esc(st)}">{_esc(st)}</span>' if st else '<span class="mut">—</span>'

    def h_conv(v):
        if v is None:
            return ""
        return " h-pos3" if v >= 78 else " h-pos2" if v >= 62 else " h-pos1" if v >= 48 else ""

    def h_52(v):
        if v is None:
            return ""
        if v >= -2:  return " h-pos3"
        if v >= -5:  return " h-pos2"
        if v >= -10: return " h-pos1"
        if v <= -50: return " h-neg2"
        if v <= -25: return " h-neg1"
        return ""

    trs = []
    for r in rows:
        rank = r["rank"] or "-"
        ath = "⚡" if r["ath"] else ""
        ix = _intensity(r)
        dvt = r["dvt"]
        dvt_cr = f'{dvt/1e7:,.1f}' if dvt else "—"
        dlv = f'{r["deliv_per"]:.1f}%' if r["deliv_per"] is not None else "—"
        pp = pt.get(r["symbol"])
        qsc = f'{pp["ns_base"]:.0f}' if (pp and pp["ns_base"] is not None) else "—"
        tier = _esc(pp["tier"]) if (pp and pp["tier"]) else "—"
        qg_ok = (pp is None) or (pp["qg_pass"] == 1)
        cv = r["conv"]
        star = "★ " if ((r["p_score"] or 0) >= 4 and (r["rs_rank"] or 0) >= 80 and qg_ok) else ""
        cpr_tds, has_cpr = _cpr_screener_cells(cpr_by_tf.get(r["symbol"], {}))
        trs.append(
            f'<tr class="{"has-cpr" if has_cpr else ""}">'
            f'<td class="fz l"><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
            f'<td class="l mut">{_esc(r["sector"]) or "—"}</td>'
            f'<td class="num">{_num(r["close"], 1)}</td>'
            f'<td class="num bold gsep g-conv{h_conv(cv)}">{star}{f"{cv:.0f}" if cv is not None else "—"}</td>'
            f'<td class="g-conv"><span class="pill p-{rank}">{rank}</span></td>'
            f'<td class="l g-conv">{_char_pill(r["ch"])}</td>'
            f'<td class="num gsep mut g-pos">{r["p_score"] if r["p_score"] is not None else "—"}</td>'
            f'<td class="num mut g-pos">{r["r_score"] if r["r_score"] is not None else "—"}</td>'
            f'<td class="num g-pos"><b>{(f"{ix:.1f}×" if ix else "—")}</b></td>'
            f'<td class="num g-pos">{_num(r["su1"], 2) if r["su1"] is not None else "—"}</td>'
            f'<td class="num g-pos">{dlv}</td>'
            f'<td class="num g-pos">{dvt_cr}</td>'
            f'<td class="num gsep g-rs">{r["rs_rank"] if r["rs_rank"] is not None else "—"}</td>'
            f'<td class="l g-rs">{trend_pill(r["rsbt"])}</td>'
            f'<td class="l g-rs">{_rs_strip(r["b1"], r["b3"], r["b6"], r["b12"])}</td>'
            f'<td class="l g-rs">{trend_pill(r["rsst"])}</td>'
            + cpr_tds +
            f'<td class="num gsep g-qual">{qsc}</td>'
            f'<td class="l mut g-qual">{tier}</td>'
            f'<td class="num gsep g-ctx{h_52(r["hh"])}">{_pct(r["hh"])}</td>'
            f'<td class="num g-ctx">{_pct(r["pvh"])}</td>'
            '</tr>')

    # --- scope selector (server-state via ?scope=) ---
    BROAD = ["Nifty 50", "Nifty Next 50", "Nifty Midcap 150", "Nifty Smallcap 250", "Nifty 500"]
    def _schip(name, label=None):
        on = " on" if scope.lower() == name.lower() else ""
        return f'<a class="fbtn{on}" href="/dash/screener?scope={_q(name)}">{_esc(label or name)}</a>'
    chips = "".join(_schip(n) for n in BROAD) + _schip("all", "All") + _schip("watch", "★ Watch")
    sec_opts = "".join(
        f'<option value="{_esc(s)}"{" selected" if scope.lower()==s.lower() else ""}>{_esc(s)}</option>'
        for s in REAL_SECTORS)
    sec_sel = ('<select class="dtf" style="flex:none;max-width:210px" '
               "onchange=\"if(this.value)location='/dash/screener?scope='+encodeURIComponent(this.value)\">"
               f'<option value="">Sector ▾</option>{sec_opts}</select>')
    scope_bar = f'<div class="fbar" style="align-items:center;margin-bottom:8px">{chips}{sec_sel}</div>'

    shown = len(rows)
    if is_all:
        lbl = f'All liquid equity · top <b>{shown}</b> by conviction (cap {limit})'
    elif is_watch:
        lbl = f'Watchlist · <b>{shown}</b> stocks'
    else:
        mem = f'{n_members} members · ' if n_members else ''
        lbl = f'<b>{_esc(scope)}</b> · {mem}<b>{shown}</b> shown (liquid)'

    if trs:
        thead = (
            '<thead>'
            '<tr class="sgrp">'
            '<th class="fz l">stock</th>'
            '<th class="l" colspan="2">identity</th>'
            '<th class="l gsep g-conv" colspan="3">conviction</th>'
            '<th class="l gsep g-pos" colspan="6">positioning · dvpt</th>'
            '<th class="l gsep g-rs" colspan="4">relative strength</th>'
            '<th class="l gsep g-cpr" colspan="7">structure · cpr</th>'
            '<th class="l gsep g-qual" colspan="2">quality</th>'
            '<th class="l gsep g-ctx" colspan="2">context</th></tr>'
            '<tr class="scol">'
            '<th class="fz l">Symbol</th><th class="l">Sector</th><th class="num">CMP</th>'
            '<th class="num gsep g-conv">Conv</th><th class="g-conv">Rank</th><th class="l g-conv">Char</th>'
            '<th class="num gsep g-pos">p</th><th class="num g-pos">r</th><th class="num g-pos">×Pow</th>'
            '<th class="num g-pos">Surge</th><th class="num g-pos">Deliv%</th><th class="num g-pos">Val₹Cr</th>'
            '<th class="num gsep g-rs">RS#</th><th class="l g-rs">Broad</th><th class="l g-rs">RS heat</th><th class="l g-rs">Sector</th>'
            '<th class="num gsep g-cpr">D%</th><th class="num g-cpr">W%</th><th class="num g-cpr">M%</th>'
            '<th class="l g-cpr">D·W·M</th><th class="g-cpr">Rnk</th><th class="l g-cpr">Str</th><th class="num g-cpr">Comp%</th>'
            '<th class="num gsep g-qual">pt14</th><th class="l g-qual">Tier</th>'
            '<th class="num gsep g-ctx">52w%</th><th class="num g-ctx">Δhot%</th></tr></thead>')
        grid = (f'<div class="scrwrap"><table class="dt scr">{thead}'
                f'<tbody>{"".join(trs)}</tbody></table></div>'
                '<script>(function(){var w=document.querySelector(".scrwrap");'
                'if(w)w.addEventListener("scroll",function(){'
                'w.classList.toggle("scrolled",w.scrollLeft>0);},{passive:true});})();</script>')
    else:
        grid = ('<div class="empty">No constituents loaded for this index yet — try '
                '<a class="row" style="display:inline" href="/dash/screener?scope=all">All</a>.</div>'
                if (not is_all and not is_watch and not n_members)
                else '<div class="empty">No stocks match this scope for the latest day.</div>')

    intro = (
        f'<h2>Screener <span class="sub" style="margin:0">{lbl}</span></h2>'
        '<div class="sub">Pick a universe, then sort / filter / export. Ranked by a tri-pillar '
        '<b>Conviction</b> (positioning + relative strength); <b>★</b> = strong on both with quality not failing. '
        'Header band &amp; Symbol column stay frozen — scroll down and across.</div>')
    view_bar = '<div class="fbar" id="vbar" style="align-items:center;margin-bottom:8px"></div>'
    body = intro + scope_bar + view_bar + grid + _SCREENER_JS
    return HTMLResponse(_shell("Screener · patearn", body, "screener", sig_date or "", wide=True))


# Screener view-controls: column-group toggle chips + saved views (localStorage).
# Toggles whole groups by walking the sgrp colspans -> column indexes (so the
# colspan'd group header hides cleanly with its columns). Plain template.
_SCREENER_JS = """
<script>
(function(){
  var tbl=document.querySelector('table.scr'); if(!tbl) return;
  var vbar=document.getElementById('vbar'); if(!vbar) return;
  var TOG=[['conv','Conviction'],['pos','Positioning'],['rs','RS'],['cpr','CPR'],['qual','Quality'],['ctx','Context']];
  var KEY='patearn_scr_hidden', SKEY='patearn_scr_saved';
  function getH(){try{return JSON.parse(localStorage.getItem(KEY))||{};}catch(e){return {};}}
  function getSaved(){try{return JSON.parse(localStorage.getItem(SKEY))||[];}catch(e){return [];}}
  var h=getH();
  // CPR-confirmed gate (the conviction-integration "filter" — the cross-pillar
  // Conviction NUMBER is left untouched; this just shows only structure-confirmed
  // names). ONE class on the table, composes with the group toggles + text filter.
  var gate=document.createElement('button'); gate.type='button'; gate.className='fbtn'; gate.textContent='🔷 CPR-confirmed';
  gate.title='Show only names carrying a CPR reversal (a ★ Structure tier on some timeframe)';
  gate.onclick=function(){ var on=tbl.classList.toggle('cpr-only'); gate.className='fbtn'+(on?' on':''); };
  vbar.appendChild(gate);
  var lbl=document.createElement('span'); lbl.className='mut'; lbl.style.fontSize='11px'; lbl.style.marginLeft='8px'; lbl.textContent='columns:'; vbar.appendChild(lbl);
  TOG.forEach(function(t){
    var g=t[0];
    tbl.classList.toggle('hide-'+g, !!h[g]);            // restore saved state = ONE class
    var b=document.createElement('button'); b.type='button';
    b.className='fbtn'+(h[g]?'':' on'); b.textContent=t[1];
    b.onclick=function(){
      var s=getH(); s[g]=!s[g]; localStorage.setItem(KEY,JSON.stringify(s));
      tbl.classList.toggle('hide-'+g, !!s[g]);          // toggle = ONE class, single reflow
      b.className='fbtn'+(s[g]?'':' on');
    };
    vbar.appendChild(b);
  });
  var save=document.createElement('button'); save.type='button'; save.className='fbtn'; save.style.marginLeft='auto'; save.textContent='+ Save view';
  var sel=document.createElement('select'); sel.className='dtf'; sel.style.cssText='flex:none;max-width:150px';
  function fillSel(){ sel.innerHTML='<option value="">Saved views</option>'+getSaved().map(function(v,i){return '<option value="'+i+'">'+String(v.name).replace(/[<>&]/g,'')+'</option>';}).join(''); }
  fillSel();
  save.onclick=function(){ var nm=prompt('Name this view:'); if(!nm) return; var sc=new URLSearchParams(location.search).get('scope')||'Nifty 500'; var a=getSaved(); a.push({name:String(nm).slice(0,40),scope:sc,hidden:getH()}); localStorage.setItem(SKEY,JSON.stringify(a)); fillSel(); };
  sel.onchange=function(){ var v=getSaved()[this.value]; if(!v) return; localStorage.setItem(KEY,JSON.stringify(v.hidden||{})); location='/dash/screener?scope='+encodeURIComponent(v.scope||'Nifty 500'); };
  vbar.appendChild(save); vbar.appendChild(sel);
})();
</script>
"""


# --- CPR surface helpers (shared by the Strategies card + /dash/cpr, D53) --
_CPR_LIQ = " AND symbol IN (SELECT symbol FROM nse_equity_list) AND close > 20 "
_CPR_TIER_RANK = {"★★★": 3, "★★": 2, "★": 1}
_CPR_TF_LABEL = {"D": "Daily", "W": "Weekly", "M": "Monthly"}


def _cpr_latest_period(conn, tf):
    r = conn.execute(
        "SELECT MAX(period_end_date) d FROM cpr_signals WHERE timeframe=?", (tf,)).fetchone()
    return r["d"] if r and r["d"] else None


def _cpr_reversal_syms(conn, tf=None, fresh_only=False, direction=None) -> set:
    """Symbols carrying a reversal on the latest period (optionally one TF / one
    direction / fresh-this-period only)."""
    tfs = [tf] if tf in _CPR_TF_ORDER else list(_CPR_TF_ORDER)
    pats = (("BULL_U",) if direction == "U" else
            ("BEAR_INVU",) if direction == "INVU" else ("BULL_U", "BEAR_INVU"))
    syms = set()
    for t in tfs:
        d = _cpr_latest_period(conn, t)
        if not d:
            continue
        pph = ",".join("?" for _ in pats)
        q = (f"SELECT symbol FROM cpr_signals WHERE timeframe=? AND period_end_date=? "
             f"AND pattern IN ({pph})" + _CPR_LIQ)
        if fresh_only:
            q += " AND days_since_pattern=0"
        for r in conn.execute(q, [t, d, *pats]).fetchall():
            syms.add(r["symbol"])
    return syms


def _cpr_setups(conn, tf=None, fresh_only=False, direction=None, min_tier=None, limit=200):
    """Reversal setups for the latest period — cross-TF conviction per symbol,
    sorted fresh → tier → score. `tf` pins the anchor to that TF (its own-TF
    reversal screen); blank = anchor on each symbol's largest-TF reversal."""
    syms = _cpr_reversal_syms(conn, tf=tf, fresh_only=fresh_only, direction=direction)
    by = _cpr_latest_by_tf(conn, syms)
    out = []
    for s, tfm in by.items():
        conv = _cpr_conviction(tfm, force_anchor=tf if tf in _CPR_TF_ORDER else None)
        if not conv:
            continue
        if min_tier and _CPR_TIER_RANK.get(conv["tier"], 0) < _CPR_TIER_RANK.get(min_tier, 0):
            continue
        arow = tfm[conv["anchor"]]
        if fresh_only and arow.get("days_since_pattern") != 0:
            continue
        out.append({"symbol": s, "conv": conv, "anchor": arow, "by_tf": tfm,
                    "fresh": arow.get("days_since_pattern") == 0})
    out.sort(key=lambda x: (1 if x["fresh"] else 0,
                            _CPR_TIER_RANK.get(x["conv"]["tier"], 0),
                            x["conv"]["score"]), reverse=True)
    return out[:limit]


def _cpr_compressions(conn, tf=None, limit=200):
    """Unusually-narrow single CPRs (3B) on the latest period — ranked by the
    own-history compression percentile (the truer 'unusual'), then absolute width."""
    tfs = [tf] if tf in _CPR_TF_ORDER else list(_CPR_TF_ORDER)
    out = []
    for t in tfs:
        d = _cpr_latest_period(conn, t)
        if not d:
            continue
        for r in conn.execute(
                f"SELECT * FROM cpr_signals WHERE timeframe=? AND period_end_date=? "
                f"AND width_pct IS NOT NULL {_CPR_LIQ} "
                f"ORDER BY COALESCE(compression_pctile,-1) DESC, width_pct ASC LIMIT ?",
                (t, d, limit)).fetchall():
            row = dict(r)
            row["narrow_abs"] = _cpr_is_narrow(row.get("width_pct"), t)
            out.append(row)
    out.sort(key=lambda x: (x.get("compression_pctile")
                            if x.get("compression_pctile") is not None else -1.0), reverse=True)
    return out[:limit]


def _cpr_dwm_strip(by_tf) -> str:
    """The D·W·M structure strip (mirrors the RS heat strip): per-TF width% +
    pattern glyph, tinted green when narrow, underlined by regime."""
    cells = []
    for tf in _CPR_TF_ORDER:
        row = by_tf.get(tf)
        w = row.get("width_pct") if row else None
        g, gcls = _cpr_glyph(row.get("pattern") if row else None)
        cls = "c"
        if _cpr_is_narrow(w, tf):
            cls += " nw"
        reg = row.get("regime") if row else None
        if reg == 1:
            cls += " up"
        elif reg == -1:
            cls += " dn"
        wtxt = f"{w:.2f}" if w is not None else "—"
        cells.append(f'<span class="{cls}"><span class="w {gcls}">{g} {wtxt}</span>'
                     f'<small>{tf}</small></span>')
    return f'<span class="cprstrip">{"".join(cells)}</span>'


def _cpr_card(setups) -> str:
    """The live Strategies CPR card — top fresh structure setups today (replaces
    the D53 'coming soon' stub). Links to the full /dash/cpr screens."""
    if setups:
        chips = '<div class="chips" style="margin-top:8px">' + "".join(
            f'<a class="chip" href="/dash/stock?sym={_esc(x["symbol"])}">{_esc(x["symbol"])} '
            f'<span class="{_cpr_glyph(x["anchor"]["pattern"])[1]}">{_cpr_glyph(x["anchor"]["pattern"])[0]}</span>'
            f' <span class="cp-tier">{x["conv"]["tier"]}</span>'
            f'<span class="mut"> {x["conv"]["anchor"]}</span></a>'
            for x in setups) + '</div>'
    else:
        chips = ('<div class="mut" style="font-size:12px;padding:6px 0">No CPR reversal '
                 'setups today (or run the CPR backfill on the VPS).</div>')
    return ('<div class="scard sc-CPR">'
            '<div class="nm">CPR · Structure</div>'
            '<div class="th">Multi-timeframe CPR — has the structure just turned (U / ∩), '
            'and is it coiled? Amplified when higher timeframes agree.</div>'
            '<div class="mut" style="font-size:11px;margin-top:6px">number shown = ★ structure-conviction tier '
            '(★★★ Prime ▸ ★ Setup) + anchor TF</div>'
            f'{chips}'
            '<a class="row" style="display:inline-block;margin-top:10px;color:#58a6ff;font-weight:700;font-size:12px" '
            'href="/dash/cpr">See reversals · compression · reports →</a></div>')


_CPR_TIER_WORD = {"★★★": "Prime", "★★": "Strong", "★": "Setup"}


def _cpr_stock_panel(by_tf) -> str:
    """Per-stock CPR panel: the D·W·M strip + the three CPRs (P/BC/TC, close-vs-band,
    width%, pattern, rank, regime, freshness) + a plain-English verdict. '' when the
    stock has no CPR rows yet (panel simply omitted — graceful, like the others)."""
    if not by_tf:
        return ""
    rows = []
    for tf in _CPR_TF_ORDER:
        r = by_tf.get(tf)
        if not r:
            rows.append(f'<tr><td>{_CPR_TF_LABEL[tf]}</td>'
                        + '<td class="mut" colspan="8">no data</td></tr>')
            continue
        p, bc, tc, w = r.get("p"), r.get("bc"), r.get("tc"), r.get("width_pct")
        cl = r.get("close")
        if cl is None or bc is None or tc is None:
            pos = '<span class="mut">—</span>'
        elif cl > tc:
            pos = '<span class="pos">above</span>'
        elif cl < bc:
            pos = '<span class="neg">below</span>'
        else:
            pos = "inside"
        g, gcls = _cpr_glyph(r.get("pattern"))
        rnk = _cpr_rank(w, r.get("c1_width_pct"), tf) if r.get("pattern") in ("BULL_U", "BEAR_INVU") else "—"
        reg = r.get("regime")
        regs = ('<span class="pos">↑ above</span>' if reg == 1 else
                '<span class="neg">↓ below</span>' if reg == -1 else '<span class="mut">—</span>')
        days = r.get("days_since_pattern")
        fresh = "fresh" if days == 0 else (f"{days}p" if days is not None else "—")
        nw = ' style="color:#7ee787;font-weight:700"' if _cpr_is_narrow(w, tf) else ""
        rows.append(
            f'<tr><td><b>{_CPR_TF_LABEL[tf]}</b>{" ⏳" if r.get("is_partial") else ""}</td>'
            f'<td>{_num(p, 1)}</td><td>{_num(bc, 1)}</td><td>{_num(tc, 1)}</td>'
            f'<td{nw}>{(f"{w:.2f}%") if w is not None else "—"}</td>'
            f'<td class="l">{pos}</td>'
            f'<td class="l"><span class="cpg {gcls}">{g}</span></td>'
            f'<td>{rnk}</td><td class="l">{regs}</td><td class="l">{fresh}</td></tr>')

    conv = _cpr_conviction(by_tf)
    if conv:
        a = by_tf[conv["anchor"]]
        pat = "bullish U (bottom)" if a["pattern"] == "BULL_U" else "bearish ∩ (top)"
        sup = [f"{_CPR_TF_LABEL[t].lower()} coiled/aligned" for t in _CPR_TF_ORDER
               if t != conv["anchor"] and conv["breakdown"].get(t, 0) >= 2]
        sup_txt = (" — amplified by " + ", ".join(sup)) if sup else " — no higher-timeframe support yet"
        conf_txt = " Price has confirmed (engaged the band)." if a.get("confirmed") else " Not yet confirmed (a setup)."
        confl = " D/W/M pivots in confluence." if conv["confluence"] else ""
        verdict = (f'<div class="cprverdict"><span class="cp-tier">{conv["tier"]}</span> '
                   f'<b>{_CPR_TIER_WORD.get(conv["tier"], "")}</b> — {_CPR_TF_LABEL[conv["anchor"]]} '
                   f'{pat}, rank {conv["rank"]} (score {conv["score"]:.0f}){sup_txt}.{confl}{conf_txt}</div>')
    else:
        ds = by_tf.get("D") or by_tf.get("W") or by_tf.get("M")
        coil = [f"{_CPR_TF_LABEL[t].lower()} {by_tf[t]['width_pct']:.2f}%" for t in _CPR_TF_ORDER
                if by_tf.get(t) and by_tf[t].get("width_pct") is not None and _cpr_is_narrow(by_tf[t]["width_pct"], t)]
        coil_txt = ("Coiled: " + ", ".join(coil) + " — a move may be pending.") if coil else \
            "No active reversal and no unusual compression right now."
        verdict = f'<div class="cprverdict"><b>No reversal.</b> {coil_txt}</div>'

    return ('<div class="cprpanel"><h3 style="margin:0 0 8px">CPR · Structure '
            '<span class="mut" style="font-size:12px;font-weight:400">multi-timeframe pivot range</span></h3>'
            f'<div style="margin-bottom:8px">{_cpr_dwm_strip(by_tf)}</div>'
            '<table><thead><tr><th>TF</th><th>Pivot</th><th>BC</th><th>TC</th><th>Width%</th>'
            '<th class="l">Close</th><th class="l">U/∩</th><th>Rnk</th><th class="l">vs Pivot</th>'
            '<th class="l">Fresh</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>{verdict}'
            '<div class="mut" style="font-size:11px;margin-top:6px">CPR from the prior period\'s '
            'split-adjusted H/L/C · width ÷ pivot · narrow = coiled · ⏳ = current (open) period.</div></div>')


@router.get("/dash/strategies", response_class=HTMLResponse)
def dash_strategies() -> HTMLResponse:
    """Workspace: pick a strategy, see TODAY's best stocks from each pillar.
    Each card previews the top names + links to that strategy's full screen."""
    sig_date, _ = _latest_dates()
    conv, pos, rs, qual, cpr_top = [], [], [], [], []
    if sig_date:
        with get_conn() as conn:
            cpr_top = _cpr_setups(conn, limit=8)   # CPR Structure card (D53)
            cx = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
            conv = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, {cx} v FROM stock_signals s
                    JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL {_SCAN_FILTERS}
                    ORDER BY v DESC LIMIT 8""", (sig_date,)).fetchall()]
            pos = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, s.trigger_rank v FROM stock_signals s
                    JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL {_SCAN_FILTERS}
                    ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC,
                             COALESCE(s.delivery_value_today,0) DESC LIMIT 8""", (sig_date,)).fetchall()]
            rs = [dict(r) for r in conn.execute(
                f"""SELECT s.symbol, s.rs_rank v FROM stock_signals s
                    JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.rs_rank IS NOT NULL {_SCAN_FILTERS}
                    ORDER BY s.rs_rank DESC LIMIT 8""", (sig_date,)).fetchall()]
            qual = [dict(r) for r in conn.execute(
                """SELECT p.symbol, p.ns_base v FROM pattern_scores p
                   JOIN (SELECT symbol, MAX(scored_at) m FROM pattern_scores GROUP BY symbol) x
                     ON x.symbol=p.symbol AND x.m=p.scored_at
                   WHERE p.ns_base IS NOT NULL ORDER BY p.ns_base DESC LIMIT 8""").fetchall()]

    def picks(rows, fmt):
        if not rows:
            return '<div class="mut" style="font-size:12px;padding:6px 0">No names today.</div>'
        return '<div class="chips" style="margin-top:8px">' + "".join(
            f'<a class="chip" href="/dash/stock?sym={_esc(r["symbol"])}">{_esc(r["symbol"])} '
            f'<span class="mut">{fmt(r["v"])}</span></a>' for r in rows) + '</div>'

    def card(cls, title, thesis, metric, body_picks, href, cta, top=""):
        ts = f' style="border-top-color:{top}"' if top else ''
        return (f'<div class="scard sc-{cls}"{ts}>'
                f'<div class="nm">{title}</div><div class="th">{thesis}</div>'
                f'<div class="mut" style="font-size:11px;margin-top:6px">number shown = {metric}</div>{body_picks}'
                f'<a class="row" style="display:inline-block;margin-top:10px;color:#58a6ff;font-weight:700;font-size:12px" '
                f'href="{href}">{cta} →</a></div>')

    cards = [
        card("POS", "Conviction", "All pillars aligned — institutions positioning + leading the market.",
             "conviction score (0–100)", picks(conv, lambda v: f"{v:.0f}"), "/dash/conviction", "See conviction shortlist", "#8957e5"),
        card("POS", "Positioning · DVPT", "Where institutional delivery money is moving today.",
             "DVPT trigger rank (SS▶C)", picks(pos, lambda v: _esc(v or "-")), "/dash/scan", "See all triggers"),
        card("RS", "Relative Strength", "Stocks beating the market and leading their sector.",
             "relative-strength rank (1–99)", picks(rs, lambda v: f"#{v}"), "/dash/leaders", "See leaders"),
        card("QUAL", "Quality · pt14", "The 14-pattern durability score — businesses worth owning.",
             "pt14 quality score (0–100)", picks(qual, lambda v: f"{v:.0f}"), "/dash/screener", "Open screener"),
        _cpr_card(cpr_top),
    ]
    head = ('<h2>Strategies <span class="sub" style="margin:0">today\'s best, by strategy</span></h2>'
            '<div class="sub">Pick a strategy to see the names it surfaces right now — or open the '
            '<a class="row" style="display:inline" href="/dash/screener">screener</a> to slice all of them together.</div>')
    body = head + '<div class="scards">' + "".join(cards) + '</div>'
    return HTMLResponse(_shell("Strategies · patearn", body, "strategies", sig_date or ""))


def _cpr_sep_cell(v):
    if v is None:
        return '<span class="mut">—</span>'
    return f'<span class="pos">+{v:.2f}</span>' if v >= 0 else f'<span class="mut">{v:.2f}</span>'


def _cpr_reversal_table(setups) -> str:
    """Data-first reversal table — raw widths beside the rank/tier verdict."""
    if not setups:
        return '<div class="empty">No reversals match this filter for the latest period.</div>'
    trs = []
    for x in setups:
        a, conv = x["anchor"], x["conv"]
        sym = _esc(x["symbol"])
        g, gcls = _cpr_glyph(a["pattern"])
        pat_lbl = "Bull U" if a["pattern"] == "BULL_U" else "Bear ∩"
        anchor_lbl = _CPR_TF_LABEL.get(conv["anchor"], conv["anchor"])
        c0w = f'{a["width_pct"]:.2f}' if a.get("width_pct") is not None else "—"
        c1v = a.get("c1_width_pct")
        c1w = f"{c1v:.2f}" if c1v is not None else "—"
        dv = a.get("depth_pct")
        depth = f"{dv:.1f}" if dv is not None else "—"
        strip = _cpr_dwm_strip(x["by_tf"])
        sep = _cpr_sep_cell(a.get("separation_pct"))
        days = a.get("days_since_pattern")
        if days == 0:
            fresh = '<span class="pos">● fresh</span>'
        elif days is not None:
            fresh = f'<span class="mut">{days}p ago</span>'
        else:
            fresh = '<span class="mut">—</span>'
        conf = "✓" if a.get("confirmed") else '<span class="mut">·</span>'
        cmp_ = _num(a.get("close"), 1)
        trs.append(
            "<tr>"
            f'<td class="l"><a class="row" href="/dash/stock?sym={sym}"><b>{sym}</b></a></td>'
            f"<td>{anchor_lbl}</td>"
            f'<td class="l"><span class="cpg {gcls}">{g}</span> {pat_lbl}</td>'
            f'<td><b>{conv["rank"]}</b></td>'
            f'<td class="l"><span class="cp-tier">{conv["tier"]}</span></td>'
            f'<td class="num">{conv["score"]:.0f}</td>'
            f'<td class="num">{c0w}</td>'
            f'<td class="num">{c1w}</td>'
            f'<td class="l">{strip}</td>'
            f'<td class="num">{sep}</td>'
            f'<td class="num">{depth}</td>'
            f'<td class="l">{fresh}</td>'
            f"<td>{conf}</td>"
            f'<td class="num">{cmp_}</td>'
            "</tr>")
    thead = ('<thead><tr>'
             '<th class="l">Symbol</th><th>Anchor</th><th class="l">Pattern</th><th>Rnk</th>'
             '<th class="l">★ Tier</th><th class="num">Score</th><th class="num">C0 w%</th>'
             '<th class="num">C1 w%</th><th class="l">D·W·M</th><th class="num">Sep%</th>'
             '<th class="num">Depth%</th><th class="l">Fresh</th><th>Conf</th><th class="num">CMP</th>'
             '</tr></thead>')
    return f'<table class="dt">{thead}<tbody>{"".join(trs)}</tbody></table>'


def _cpr_compression_table(rows) -> str:
    if not rows:
        return '<div class="empty">No compression data for the latest period.</div>'
    trs = []
    for r in rows:
        tf = r["timeframe"]
        pc = r.get("compression_pctile")
        pcs = f'{pc*100:.0f}' if pc is not None else "—"
        g, gcls = _cpr_glyph(r.get("pattern"))
        reg = r.get("regime")
        regs = ('<span class="pos">above</span>' if reg == 1 else
                '<span class="neg">below</span>' if reg == -1 else '<span class="mut">—</span>')
        absn = '<span class="pos">● narrow</span>' if r.get("narrow_abs") else '<span class="mut">·</span>'
        trs.append(
            '<tr>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}"><b>{_esc(r["symbol"])}</b></a></td>'
            f'<td>{_CPR_TF_LABEL.get(tf, tf)}</td>'
            f'<td class="num"><b>{r["width_pct"]:.2f}</b></td>'
            f'<td class="num">{pcs}</td>'
            f'<td class="l">{absn}</td>'
            f'<td class="l"><span class="cpg {gcls}">{g}</span></td>'
            f'<td class="l">{regs}</td>'
            f'<td class="num">{_num(r.get("close"), 1)}</td>'
            '</tr>')
    thead = ('<thead><tr><th class="l">Symbol</th><th>TF</th><th class="num">Width%</th>'
             '<th class="num">Coil pctile</th><th class="l">Abs-narrow</th><th class="l">Pattern</th>'
             '<th class="l">vs Pivot</th><th class="num">CMP</th></tr></thead>')
    return f'<table class="dt">{thead}<tbody>{"".join(trs)}</tbody></table>'


@router.get("/dash/cpr", response_class=HTMLResponse)
def dash_cpr(tab: str = Query("reversals"), tf: str = Query(""),
             direction: str = Query(""), tier: str = Query("")) -> HTMLResponse:
    """CPR (Structure pillar, D53) — the multi-timeframe U/∩ reversal screen, the
    unusually-narrow compression scanner, and the per-TF (Daily/Weekly/Monthly)
    EOD 'what fired' reports. Each timeframe has its OWN CPRs → its own triggers
    and its own report. Reversal conviction is the cross-TF amplified ★ tier (a
    transparent, tunable sort key, NOT folded into the cross-pillar Conviction —
    see metrics-glossary.md). Sort / filter / export via the shared toolbar."""
    tab = tab if tab in ("reversals", "compression", "reports") else "reversals"
    tf = tf if tf in _CPR_TF_ORDER else ""
    direction = direction if direction in ("U", "INVU") else ""
    tier = tier if tier in ("★", "★★", "★★★") else ""

    have_cpr = False
    with get_conn() as conn:
        have_cpr = bool(conn.execute("SELECT 1 FROM cpr_signals LIMIT 1").fetchone())
        latest = {t: _cpr_latest_period(conn, t) for t in _CPR_TF_ORDER}
        if tab == "reversals":
            content = _cpr_reversal_table(_cpr_setups(
                conn, tf=tf or None, direction=direction or None, min_tier=tier or None, limit=400))
        elif tab == "compression":
            content = _cpr_compression_table(_cpr_compressions(conn, tf=tf or None, limit=400))
        else:  # reports — per-TF "what fired" for the latest period of each TF
            secs = []
            for t in _CPR_TF_ORDER:
                d = latest.get(t)
                fresh = _cpr_setups(conn, tf=t, fresh_only=True, limit=50) if d else []
                comps = [r for r in _cpr_compressions(conn, tf=t, limit=12)
                         if (r.get("compression_pctile") or 0) >= 0.8 or r.get("narrow_abs")][:12]
                badge = "" if t == "D" else (
                    f' <span class="mut" style="font-weight:400">· live for the current '
                    f'{"week" if t=="W" else "month"} (fixed for the period)</span>')
                rev_html = _cpr_reversal_table(fresh) if fresh else \
                    '<div class="mut" style="font-size:12px;padding:4px 0">No fresh reversals this period.</div>'
                comp_rows = "".join(
                    f'<a class="chip" href="/dash/stock?sym={_esc(r["symbol"])}">{_esc(r["symbol"])} '
                    f'<span class="mut">{r["width_pct"]:.2f}%'
                    f'{(" · " + format(r["compression_pctile"]*100, ".0f") + "ᵖ") if r.get("compression_pctile") is not None else ""}</span></a>'
                    for r in comps)
                comp_html = (f'<div class="chips" style="margin-top:6px">{comp_rows}</div>' if comps
                             else '<div class="mut" style="font-size:12px;padding:4px 0">No unusually-narrow CPRs.</div>')
                secs.append(
                    f'<div class="card" style="margin-bottom:14px">'
                    f'<h3 style="margin:0 0 2px">{_CPR_TF_LABEL[t]} CPR'
                    f'{(" — " + d) if d else ""}{badge}</h3>'
                    f'<div class="sub" style="margin:2px 0 8px">{len(fresh)} fresh reversal'
                    f'{"" if len(fresh)==1 else "s"} · {len(comps)} unusually-narrow</div>'
                    f'<div class="chartlbl">What turned (fresh U / ∩)</div>{rev_html}'
                    f'<div class="chartlbl" style="margin-top:10px">Coiled (unusually-narrow CPRs)</div>{comp_html}'
                    f'</div>')
            content = "".join(secs)

    if not have_cpr:
        body = ('<h2>CPR · Structure</h2>'
                '<div class="empty">No CPR signals yet — run the CPR backfill on the VPS:<br>'
                '<code>python -m src.automation.cpr_signals --backfill --timeframe all</code></div>')
        return HTMLResponse(_shell("CPR · patearn", body, "cpr"))

    # tab bar
    def _tab(key, label):
        qs = f"?tab={key}" + (f"&tf={tf}" if tf else "")
        return f'<a class="{"on" if tab==key else ""}" href="/dash/cpr{qs}">{label}</a>'
    tabbar = (f'<div class="tabbar">{_tab("reversals","Reversals")}'
              f'{_tab("compression","Compression")}{_tab("reports","EOD Reports")}</div>')

    # TF + (reversals only) direction/tier filter bar
    def _fchip(param, val, label, cur):
        keep = []
        if param != "tf" and tf:
            keep.append(f"tf={tf}")
        if param != "direction" and direction:
            keep.append(f"direction={direction}")
        if param != "tier" and tier:
            keep.append(f"tier={_q(tier)}")
        if val:
            keep.append(f"{param}={_q(val)}")
        qs = f"?tab={tab}" + ("&" + "&".join(keep) if keep else "")
        return f'<a class="fbtn{" on" if cur==val else ""}" href="/dash/cpr{qs}">{label}</a>'

    fbars = ""
    if tab in ("reversals", "compression"):
        tfchips = (_fchip("tf", "", "All TF", tf) + _fchip("tf", "D", "Daily", tf)
                   + _fchip("tf", "W", "Weekly", tf) + _fchip("tf", "M", "Monthly", tf))
        fbars = f'<div class="fbar">{tfchips}</div>'
    if tab == "reversals":
        dchips = (_fchip("direction", "", "Both", direction) + _fchip("direction", "U", "Bull U", direction)
                  + _fchip("direction", "INVU", "Bear ∩", direction))
        tchips = (_fchip("tier", "", "Any ★", tier) + _fchip("tier", "★", "★+", tier)
                  + _fchip("tier", "★★", "★★+", tier) + _fchip("tier", "★★★", "★★★", tier))
        fbars += f'<div class="fbar">{dchips}</div><div class="fbar">{tchips}</div>'

    intro = {
        "reversals": "Three consecutive CPRs forming a U (bullish bottom) or ∩ (bearish top). "
                     "Each leg is a clean directional step; strength = how narrow the recent bands are "
                     "(R1 sharpest). The <b>★ tier</b> amplifies a turn when higher timeframes are also coiled/aligned.",
        "compression": "Unusually-narrow single CPRs — coiled springs, an outsized move pending. Ranked by the "
                       "<b>own-history percentile</b> (how coiled vs this stock's own typical width), larger TF more significant.",
        "reports": "What fired this Daily / Weekly / Monthly period. Weekly &amp; Monthly CPRs are fixed for the "
                   "period, so those lists hold all period — not just today.",
    }[tab]
    head = (f'<h2>CPR · Structure <span class="sub" style="margin:0">where price is, has it turned, is it coiled</span></h2>'
            f'<div class="sub">{intro}</div>')
    body = head + tabbar + fbars + content
    return HTMLResponse(_shell("CPR · patearn", body, "cpr",
                               latest.get("D") or latest.get("W") or ""))


# === D54 (UI Phase 1) — strategy → watchlist → portfolio ACTION LOOP ========
# A tracked idea = one stocks_in_play row. status 'watch' (lightweight idea) →
# 'open' (a position-under-a-strategy: captures entry + target/stop + a FROZEN
# as-of-day snapshot) → 'closed'. The snapshot is frozen at add time (the daily
# signals overwrite nightly); mark-to-market + hit-rate are pure-SQL / indexed
# point-lookups on read. Capture is the dashboard's ONLY mutation (POST); every
# other route stays read-only. Glossary defs feed the snapshot chips.

_TRACK_STRATEGIES = ["DVPT accumulation", "RS leader", "Conviction",
                     "CPR reversal", "Quality", "Manual"]

_TRACK_CSS = """<style>
.snap{display:inline-block;background:#0d1117;border:1px solid #30363d;border-radius:7px;padding:2px 7px;margin:2px 4px 2px 0;font-size:11px;color:#c9d1d9;font-variant-numeric:tabular-nums}
.snap i{color:#6e7681;font-style:normal;margin-right:3px}
.tbtn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:5px 11px;border-radius:7px;font-size:12px;cursor:pointer;font-family:inherit}
.tbtn-go{background:#238636;border-color:#238636;color:#fff;font-weight:700}
.thq{color:#58a6ff;cursor:help;font-size:17px;line-height:1}
.trk-bar{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:12px}
.trk-lbl{width:170px;flex:none;color:#c9d1d9}
.trk-val{width:48px;flex:none;text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.cap{background:#161b22;border:1px solid #1f4d7a;border-radius:10px;padding:14px;margin:12px 0}
.cap label{display:block;color:#8b949e;font-size:11px;margin-bottom:4px}
.cap .field{background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:7px;padding:8px 10px;font-size:13px;width:100%;font-family:inherit}
.cap .row2{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.cap textarea.field{min-height:48px;resize:vertical}
</style>"""


def _xpower(L):
    """×power = today's DVPT / the mean of its own power baselines (glossary)."""
    ps = [L.get("power_dvpt_1m"), L.get("power_dvpt_3m"),
          L.get("power_dvpt_6m"), L.get("power_dvpt_12m")]
    ps = [x for x in ps if x]
    dvpt = L.get("delivery_value_per_trade")
    return (dvpt / (sum(ps) / len(ps))) if (dvpt and ps) else None


def _conv_of(p_score, rs_rank):
    """The screener's tri-pillar Conviction (positioning + RS), 0-100."""
    return 0.55 * (p_score or 0) / 5.0 * 100.0 + 0.45 * (rs_rank or 0)


def _capture_snapshot(conn, sym):
    """Latest signal row -> (entry_price = latest close, frozen snapshot dict,
    trade_date). Used both to FREEZE values at add time and to read them LIVE."""
    L = conn.execute("SELECT * FROM stock_signals WHERE symbol=? "
                     "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    if not L:
        return None, {}, None
    L = dict(L)
    td = L["trade_date"]
    bq = conn.execute("SELECT close FROM bhavcopy_rows WHERE symbol=? AND "
                      "trade_date=? AND series='EQ' LIMIT 1", (sym, td)).fetchone()
    close = bq["close"] if bq else None
    try:
        ps = conn.execute("SELECT ns_base, tier FROM pattern_scores WHERE symbol=? "
                          "ORDER BY scored_at DESC LIMIT 1", (sym,)).fetchone()
    except Exception:
        ps = None
    ix = _xpower(L)
    kg = L.get("gap_to_key_p3m")
    snap = {
        "date": td, "close": close,
        "conv": round(_conv_of(L.get("p_score"), L.get("rs_rank"))),
        "p": L.get("p_score"), "r": L.get("r_score"),
        "rank": L.get("trigger_rank"), "rs": L.get("rs_rank"),
        "xpow": round(ix, 2) if ix else None,
        "keygap": round(kg, 1) if kg is not None else None,
        "pt14": round(ps["ns_base"]) if (ps and ps["ns_base"] is not None) else None,
        "tier": ps["tier"] if ps else None,
        "char": L.get("accum_character"),
    }
    return close, snap, td


def _snap_chips(snap):
    """Compact frozen-snapshot chip row from a snapshot dict."""
    if not snap:
        return '<span class="mut">—</span>'
    bits = []

    def add(lbl, val):
        if val is not None and val != "":
            bits.append(f'<span class="snap"><i>{lbl}</i>{val}</span>')
    add("conv", snap.get("conv"))
    if snap.get("p") is not None:
        add("p/r", f'{snap.get("p")}/{snap.get("r")}')
    add("rank", snap.get("rank"))
    if snap.get("xpow") is not None:
        add("×pow", snap.get("xpow"))
    add("RS", snap.get("rs"))
    if snap.get("keygap") is not None:
        add("key-gap", f'{snap.get("keygap"):+g}%')
    add("pt14", snap.get("pt14"))
    add("char", snap.get("char"))
    return "".join(bits) or '<span class="mut">—</span>'


def _then_now(a, b):
    """Render a frozen-then -> live-now value with directional colour."""
    if a is None and b is None:
        return '<span class="mut">—</span>'
    if a is None:
        return f'{b}'
    if b is None:
        return f'<span class="mut">{a}</span>'
    cls = "pos" if b > a else ("neg" if b < a else "mut")
    return f'<span class="mut">{a}</span> → <span class="{cls}">{b}</span>'


def _id_form(action, rid, label, cls="tbtn", confirm=""):
    """A tiny single-button POST form carrying a stocks_in_play id."""
    oc = f' onsubmit="return confirm(&#39;{confirm}&#39;)"' if confirm else ""
    return (f'<form method="post" action="{action}" style="display:inline"{oc}>'
            f'<input type="hidden" name="id" value="{rid}"/>'
            f'<button class="{cls}" type="submit">{label}</button></form> ')


def _benchmark_return(conn, index_name, d0, d1):
    """% return of a broad index between two dates (as-of close on/before each)."""
    if not (d0 and d1):
        return None
    a = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND "
                     "trade_date<=? ORDER BY trade_date DESC LIMIT 1", (index_name, d0[:10])).fetchone()
    b = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND "
                     "trade_date<=? ORDER BY trade_date DESC LIMIT 1", (index_name, d1[:10])).fetchone()
    if a and b and a["close_value"]:
        return (b["close_value"] - a["close_value"]) / a["close_value"] * 100.0
    return None


def _days_between(d0, d1):
    try:
        return (datetime.fromisoformat(d1[:10]) - datetime.fromisoformat(d0[:10])).days
    except Exception:
        return None


def _track_subnav(active):
    items = [("portfolios", "/dash/portfolios", "Portfolios"),
             ("watchlists", "/dash/watchlists", "Watchlists"),
             ("tracker", "/dash/tracker", "Tracker")]
    out = ['<div class="fbar" style="margin-bottom:12px">']
    for k, h, lbl in items:
        out.append(f'<a class="fbtn{" on" if k == active else ""}" href="{h}">{lbl}</a>')
    out.append("</div>")
    return "".join(out)


def _capture_form(sym, snap):
    """The inline Track capture form (server-rendered; POSTs to /dash/track).
    Entry price + date + the frozen snapshot are captured SERVER-SIDE on submit
    (never trusted from the client) — this only previews what will be saved."""
    opts = "".join(f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in _TRACK_STRATEGIES)
    asof = snap.get("date") or ""
    px = _num(snap.get("close"), 2) if snap.get("close") is not None else "—"
    return (
        '<form class="cap" id="track" method="post" action="/dash/track">'
        f'<input type="hidden" name="symbol" value="{_esc(sym)}"/>'
        f'<div style="font-weight:600;margin-bottom:10px">Track {_esc(sym)} '
        f'<span class="mut" style="font-weight:400;font-size:12px">· entry ₹{px} (auto, as of {_esc(asof)})</span></div>'
        '<div class="row2">'
        '<div style="flex:1;min-width:150px"><label>List</label>'
        '<select name="status" class="field"><option value="open">Portfolio · a position</option>'
        '<option value="watch">Watchlist · an idea</option></select></div>'
        f'<div style="flex:1;min-width:150px"><label>Strategy</label>'
        f'<select name="strategy" class="field">{opts}</select></div></div>'
        '<div style="margin-bottom:10px"><label>Thesis — why now?</label>'
        '<textarea name="thesis" class="field" placeholder="e.g. p_score 5, fresh ACCUM off a base, '
        'close inside the key-price launch band"></textarea></div>'
        '<div class="row2">'
        '<div style="flex:1"><label>Target (optional)</label><input name="target" class="field" placeholder="₹"/></div>'
        '<div style="flex:1"><label>Stop (optional)</label><input name="stop" class="field" placeholder="₹"/></div></div>'
        '<div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;margin-bottom:12px">'
        '<div class="mut" style="font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">'
        f'Frozen snapshot · saved as of {_esc(asof)}</div>{_snap_chips(snap)}</div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Save</button>'
        f'<a class="tbtn" href="/dash/stock?sym={_q(sym)}" style="text-decoration:none;margin-left:8px">Cancel</a>'
        '</form>')


@router.post("/dash/track")
def dash_track(symbol: str = Form(...), strategy: str = Form("Manual"),
               status: str = Form("open"), thesis: str = Form(""),
               target: str = Form(""), stop: str = Form("")) -> RedirectResponse:
    sym = (symbol or "").upper().strip()
    status = status if status in ("watch", "open") else "open"

    def _f(x):
        try:
            return float(str(x).replace(",", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            return None
    if sym:
        with get_conn() as conn:
            entry_price, snap, _ = _capture_snapshot(conn, sym)
            conn.execute(
                "INSERT INTO stocks_in_play(symbol,strategy,status,entry_price,"
                "price_target,stop_loss,entry_thesis,snapshot_json) VALUES(?,?,?,?,?,?,?,?)",
                (sym, (strategy or "Manual").strip() or "Manual", status,
                 entry_price if status == "open" else None,
                 _f(target), _f(stop), (thesis or "").strip() or None,
                 json.dumps(snap) if snap else None))
    dest = "/dash/watchlists" if status == "watch" else "/dash/portfolios"
    return RedirectResponse(f"{dest}?added={_q(sym)}", status_code=303)


@router.post("/dash/track/close")
def dash_track_close(id: int = Form(...), reason: str = Form("")) -> RedirectResponse:
    with get_conn() as conn:
        row = conn.execute("SELECT symbol FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        ep = _capture_snapshot(conn, row["symbol"])[0] if row else None
        conn.execute("UPDATE stocks_in_play SET status='closed', exit_date=datetime('now'), "
                     "exit_price=?, exit_reason=? WHERE id=?",
                     (ep, (reason or "").strip() or None, id))
    return RedirectResponse("/dash/tracker?closed=1", status_code=303)


@router.post("/dash/track/promote")
def dash_track_promote(id: int = Form(...)) -> RedirectResponse:
    with get_conn() as conn:
        row = conn.execute("SELECT symbol, entry_price FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        sym = row["symbol"] if row else ""
        if row:
            ep = row["entry_price"] or _capture_snapshot(conn, sym)[0]
            conn.execute("UPDATE stocks_in_play SET status='open', entry_price=? WHERE id=?", (ep, id))
    return RedirectResponse(f"/dash/portfolios?added={_q(sym)}", status_code=303)


@router.post("/dash/track/remove")
def dash_track_remove(id: int = Form(...)) -> RedirectResponse:
    with get_conn() as conn:
        conn.execute("DELETE FROM stocks_in_play WHERE id=?", (id,))
    return RedirectResponse("/dash/portfolios", status_code=303)


@router.get("/dash/portfolios", response_class=HTMLResponse)
def dash_portfolios(added: str = Query("")) -> HTMLResponse:
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='open' "
            "ORDER BY strategy, date_added DESC").fetchall()]
        live = {}
        for sym in {r["symbol"] for r in rows}:
            ep, snap, _ = _capture_snapshot(conn, sym)
            live[sym] = (ep, snap)
    intro = ('<h2>Portfolios</h2><div class="sub">Positions you committed under a strategy — '
             'entry, live mark-to-market, and the frozen as-of-add snapshot vs now. '
             'Add from any stock page → <b>Track</b>.</div>')
    flash = (f'<div class="banner b-on">Added <b>{_esc(added)}</b> to your portfolio.</div>'
             if added else "")
    if not rows:
        empty = ('<div class="empty">No open positions yet. Open any stock and hit '
                 '<b>+ Track</b> → <b>Portfolio</b> to start the loop.</div>')
        body = _TRACK_CSS + _track_subnav("portfolios") + intro + flash + empty
        return HTMLResponse(_shell("Portfolios · patearn", body, "portfolios"))
    trs = []
    for r in rows:
        sym = r["symbol"]
        cmp_, nowsnap = live.get(sym, (None, {}))
        ep = r["entry_price"]
        pl = ((cmp_ - ep) / ep * 100.0) if (cmp_ and ep) else None
        try:
            thn = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
        except Exception:
            thn = {}
        drift = _then_now(thn.get("conv"), nowsnap.get("conv"))
        thesis = r["entry_thesis"] or ""
        th_cell = (f'<span class="thq" title="{_esc(thesis)}">&#8220;</span>'
                   if thesis else '<span class="mut">—</span>')
        tgt = _num(r["price_target"], 1) if r["price_target"] is not None else '<span class="mut">—</span>'
        trs.append(
            '<tr>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_q(sym)}"><span class="sym">{_esc(sym)}</span></a></td>'
            f'<td class="l mut">{_esc(r["strategy"])}</td>'
            f'<td class="mut">{_esc((r["date_added"] or "")[:10])}</td>'
            f'<td class="num">{_num(ep, 1)}</td>'
            f'<td class="num">{_num(cmp_, 1)}</td>'
            f'<td class="num">{_pct(pl)}</td>'
            f'<td class="num">{tgt}</td>'
            f'<td class="l">{drift}</td>'
            f'<td class="l">{th_cell}</td>'
            f'<td class="l">{_id_form("/dash/track/close", r["id"], "Close", confirm="Close this position?")}</td>'
            '</tr>')
    head = ('<table class="dt"><thead><tr>'
            '<th>Symbol</th><th>Strategy</th><th>Added</th><th>Entry</th><th>CMP</th>'
            '<th>P/L</th><th>Target</th><th>Conv then→now</th><th>Thesis</th><th></th>'
            '</tr></thead><tbody>')
    body = (_TRACK_CSS + _track_subnav("portfolios") + intro + flash
            + head + "".join(trs) + "</tbody></table>")
    return HTMLResponse(_shell("Portfolios · patearn", body, "portfolios"))


@router.get("/dash/watchlists", response_class=HTMLResponse)
def dash_watchlists(added: str = Query("")) -> HTMLResponse:
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='watch' ORDER BY date_added DESC").fetchall()]
        live = {}
        for sym in {r["symbol"] for r in rows}:
            live[sym] = _capture_snapshot(conn, sym)[1]
    intro = ('<h2>Watchlists</h2><div class="sub">Lightweight ideas you are tracking — '
             'no entry needed. Promote to a portfolio when you commit.</div>')
    flash = (f'<div class="banner b-on">Added <b>{_esc(added)}</b> to your watchlist.</div>'
             if added else "")
    if not rows:
        empty = ('<div class="empty">No watchlist items yet. On any stock page hit '
                 '<b>+ Track</b> → <b>Watchlist</b>.</div>')
        body = _TRACK_CSS + _track_subnav("watchlists") + intro + flash + empty
        return HTMLResponse(_shell("Watchlists · patearn", body, "watchlists"))
    trs = []
    for r in rows:
        sym = r["symbol"]
        trs.append(
            '<tr>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_q(sym)}"><span class="sym">{_esc(sym)}</span></a></td>'
            f'<td class="l mut">{_esc(r["strategy"])}</td>'
            f'<td class="mut">{_esc((r["date_added"] or "")[:10])}</td>'
            f'<td class="l">{_snap_chips(live.get(sym, {}))}</td>'
            f'<td class="l mut">{_esc(r["entry_thesis"] or "—")}</td>'
            f'<td class="l">{_id_form("/dash/track/promote", r["id"], "Promote", cls="tbtn tbtn-go")}'
            f'{_id_form("/dash/track/remove", r["id"], "Remove", confirm="Remove from watchlist?")}</td>'
            '</tr>')
    head = ('<table class="dt"><thead><tr><th>Symbol</th><th>Strategy</th><th>Added</th>'
            '<th>Live signals</th><th>Note</th><th></th></tr></thead><tbody>')
    body = (_TRACK_CSS + _track_subnav("watchlists") + intro + flash
            + head + "".join(trs) + "</tbody></table>")
    return HTMLResponse(_shell("Watchlists · patearn", body, "watchlists"))


@router.get("/dash/tracker", response_class=HTMLResponse)
def dash_tracker() -> HTMLResponse:
    with get_conn() as conn:
        openrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='open'").fetchall()]
        closed = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='closed' "
            "AND entry_price>0 AND exit_price IS NOT NULL").fetchall()]
        opl = []
        for r in openrows:
            cmp_ = _capture_snapshot(conn, r["symbol"])[0]
            if r["entry_price"] and cmp_:
                opl.append((cmp_ - r["entry_price"]) / r["entry_price"] * 100.0)
        bystrat = [dict(r) for r in conn.execute(
            "SELECT strategy, COUNT(*) n, "
            "AVG(CASE WHEN exit_price>entry_price THEN 1.0 ELSE 0 END)*100 hit, "
            "AVG((exit_price-entry_price)/entry_price*100) avg_ret "
            "FROM stocks_in_play WHERE status='closed' AND entry_price>0 "
            "AND exit_price IS NOT NULL GROUP BY strategy ORDER BY n DESC").fetchall()]
        excess = []
        for r in closed:
            br = _benchmark_return(conn, "Nifty 500", r["date_added"], r["exit_date"])
            if br is not None:
                pr = (r["exit_price"] - r["entry_price"]) / r["entry_price"] * 100.0
                excess.append(pr - br)
        holds = [d for d in (_days_between(r["date_added"], r["exit_date"]) for r in closed)
                 if d is not None]
    open_mtm = (sum(opl) / len(opl)) if opl else None
    overall_hit = (sum(1 for r in closed if r["exit_price"] > r["entry_price"]) / len(closed) * 100.0) if closed else None
    avg_excess = (sum(excess) / len(excess)) if excess else None
    avg_hold = (sum(holds) / len(holds)) if holds else None

    def card(lbl, val):
        return f'<div class="box"><div class="num">{val}</div><div class="lbl">{lbl}</div></div>'
    cards = ('<div class="kpi">'
             + card("open positions", len(openrows))
             + card("open MTM", _pct(open_mtm))
             + card("closed", len(closed))
             + card("hit-rate", (f"{overall_hit:.0f}%" if overall_hit is not None else '<span class="mut">—</span>'))
             + card("avg excess vs Nifty 500", _pct(avg_excess))
             + card("avg hold", (f"{avg_hold:.0f}d" if avg_hold is not None else '<span class="mut">—</span>'))
             + '</div>')
    if bystrat:
        bars = ['<div class="ghdr">Hit-rate by strategy</div>']
        for s in bystrat:
            hit = s["hit"] or 0
            bars.append(
                '<div class="trk-bar">'
                f'<span class="trk-lbl">{_esc(s["strategy"])} <i class="mut">n={s["n"]}</i></span>'
                f'<span class="bar" style="flex:1;height:16px"><span style="width:{hit:.0f}%;background:#2ea043"></span></span>'
                f'<span class="trk-val">{hit:.0f}%</span>'
                f'<span class="mut" style="width:74px;text-align:right;font-size:11px">{_pct(s["avg_ret"])}</span>'
                '</div>')
        bars_html = "".join(bars)
    else:
        bars_html = ('<div class="sub" style="margin-top:14px">No closed positions yet — hit-rate '
                     'by strategy and the benchmark gap appear once you close trades.</div>')
    intro = ('<h2>Tracker</h2><div class="sub">How your tracked ideas actually performed — '
             'open mark-to-market, hit-rate by strategy, and excess vs the Nifty 500.</div>')
    body = _TRACK_CSS + _track_subnav("tracker") + intro + cards + bars_html
    return HTMLResponse(_shell("Tracker · patearn", body, "tracker"))


_LWC_CDN = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"


# Relative-strength OVERLAY JS (plain template — __SERIES__ replaced with the
# server JSON: [{name,color,level:[{t:'YYYY-MM-DD',v}]}], stock first then
# narrow sector then broad). Reuses the /dash/compare rebase idiom (common
# forward-snapped anchor, base 100), and adds a D/W/M/Q resampler: weekly/
# monthly/quarterly bar = the LAST trading day's close within each ISO-week /
# calendar-month / calendar-quarter (close-of-period). Resampling is client-
# side from the full daily series passed once, so the toggle needs no refetch.
_RS_OVERLAY_JS = """
<script src="__CDN__"></script>
<script>
const RS_SERIES = __SERIES__;
(function(){
  const host = document.getElementById('rsOverlayChart');
  if (!host) return;
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:#8b949e;padding:20px">Chart library failed to load (offline?).</div>'; return; }
  if (!RS_SERIES.length) return;
  const common = {
    layout: { background:{color:'#161b22'}, textColor:'#8b949e', fontSize:11 },
    grid: { vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'} },
    timeScale: { borderColor:'#30363d', rightOffset:3 },
    rightPriceScale: { borderColor:'#30363d' },
    crosshair: { mode: 0 },
    handleScroll:true, handleScale:true,
  };
  const chart = LightweightCharts.createChart(host, Object.assign({height:300}, common));
  let tf = 'd';   // 'd' | 'w' | 'm' | 'q'

  // --- period keys (close-of-period resampling) ---------------------------
  // ISO week: Thursday-of-week determines the ISO year; key 'YYYY-Www'.
  function isoWeekKey(s){
    const d=new Date(s+'T00:00:00Z');
    const day=(d.getUTCDay()+6)%7;              // Mon=0..Sun=6
    d.setUTCDate(d.getUTCDate()-day+3);          // nearest Thursday
    const isoYear=d.getUTCFullYear();
    const jan4=new Date(Date.UTC(isoYear,0,4));
    const jd=(jan4.getUTCDay()+6)%7;
    jan4.setUTCDate(jan4.getUTCDate()-jd+3);
    const wk=1+Math.round((d-jan4)/(7*86400000));
    return isoYear+'-W'+('0'+wk).slice(-2);
  }
  function periodKey(s){
    if(tf==='w') return isoWeekKey(s);
    if(tf==='m') return s.slice(0,7);            // YYYY-MM
    if(tf==='q'){ const y=s.slice(0,4), mo=parseInt(s.slice(5,7),10);
      return y+'-Q'+(Math.floor((mo-1)/3)+1); }
    return s;                                      // daily: the date itself
  }
  // Resample one [{t,v}] (ascending) → last point per period (close-of-period).
  function resample(level){
    if(tf==='d') return level.slice();
    const out=[]; let curKey=null, last=null;
    for(const p of level){
      const k=periodKey(p.t);
      if(k!==curKey){ if(last) out.push(last); curKey=k; }
      last=p;                                       // keep overwriting → last wins
    }
    if(last) out.push(last);
    return out;                                     // keeps each period's real last trade date
  }

  // --- rebase (base 100) on a common forward-snapped anchor ---------------
  const lines = RS_SERIES.map(s=>({
    def:s,
    ls:chart.addLineSeries({color:s.color,lineWidth:2,priceLineVisible:false,lastValueVisible:true,crosshairMarkerVisible:true}),
    cur:[],
  }));
  function snapIdx(raw, target){
    if(!raw.length) return -1;
    if(target==null) return 0;
    let lo=0,hi=raw.length-1,ans=-1;
    while(lo<=hi){ const mid=(lo+hi)>>1;
      if(raw[mid].t>=target){ ans=mid; hi=mid-1; } else { lo=mid+1; } }
    return ans;
  }
  function commonAnchor(from){
    let best=null;
    for(const l of lines){ const i=snapIdx(l.cur, from);
      if(i>=0){ const t=l.cur[i].t; if(best===null||t<best) best=t; } }
    return best;
  }
  let anchorDate=null;
  function applyRebase(anchor){
    anchorDate=anchor;
    for(const l of lines){
      const raw=l.cur; let av=null;
      if(anchor!=null){ const ai=snapIdx(raw,anchor); if(ai>=0) av=raw[ai].v; }
      else if(raw.length){ av=raw[0].v; }
      if(av==null||av===0){ l.ls.setData([]); continue; }
      const out=new Array(raw.length);
      for(let k=0;k<raw.length;k++){ const p=raw[k]; out[k]={time:p.t,value:(p.v/av)*100}; }
      l.ls.setData(out);
    }
    relabel(anchor);
    requestAnimationFrame(positionNames);
  }
  function rebuild(keepAnchor){
    for(const l of lines) l.cur=resample(l.def.level);
    const a = keepAnchor ? (anchorDate!=null?commonAnchor(anchorDate):null) : null;
    internalSet=true; applyRebase(a); internalSet=false;
  }
  // Re-rebase every line to ONE common anchor = the full-series start (base 100).
  // The RS overlay always fitContent()s all data, so the common start IS the
  // earliest data point — anchor to it deterministically via commonAnchor(null).
  // getVisibleRange() lags a frame on first/off-screen layout and returned a
  // recent partial range, which mis-anchored the rebase mid-window so the lines
  // didn't start at 100 on the left — the same lag /dash/compare's boot avoids.
  function reanchorToView(){
    lastAnchor=commonAnchor(null);
    internalSet=true; applyRebase(lastAnchor); internalSet=false;
  }

  // --- fluid anchor on pan (rAF-coalesced, anchor-gated) ------------------
  function timeToStr(t){
    if(t==null) return null;
    if(typeof t==='string') return t;
    if(typeof t==='object'&&t.year){ const m=('0'+t.month).slice(-2),d=('0'+t.day).slice(-2);
      return t.year+'-'+m+'-'+d; }
    return String(t);
  }
  let raf=null, internalSet=false, lastAnchor=null, userInteracted=false;
  // Fluid pan-reanchor must respond ONLY to real user panning, never to the
  // settle/relayout range-change events that fire after boot — those would
  // re-anchor the deterministic full-series start to a recent mid-window date
  // (the same drift /dash/compare hit). Mark genuine user input on the host.
  ['wheel','pointerdown','mousedown','touchstart'].forEach(ev=>
    host.addEventListener(ev,()=>{ userInteracted=true; },{passive:true,capture:true}));
  chart.timeScale().subscribeVisibleTimeRangeChange(r=>{
    if(!r||internalSet) return;
    const from=timeToStr(r.from);
    requestAnimationFrame(positionNames);   // labels follow price autoscale on pan
    if(!userInteracted) return;             // boot/settle re-anchors stay inert
    if(raf) return;
    raf=requestAnimationFrame(()=>{ raf=null;
      const a=commonAnchor(from);
      if(a===lastAnchor) return;
      lastAnchor=a; internalSet=true; applyRebase(a); internalSet=false; });
  });

  function relabel(anchor){
    const el=document.getElementById('rsAnchorLbl');
    if(!el) return;
    const tfn={d:'daily',w:'weekly',m:'monthly',q:'quarterly'}[tf];
    el.innerHTML = (anchor?('REBASED FROM <b>'+anchor+'</b>'):'REBASED FROM <b>start</b>')+' · '+tfn;
  }

  // Right-gutter name labels, each aligned to its line's last-value pixel
  // (mirrors /dash/compare). Nearby labels nudged apart; "Nifty " stripped.
  function positionNames(){
    const cont=document.getElementById('rsNames'); if(!cont) return;
    const items=[];
    for(const l of lines){ const dat=l.ls.data(); if(!dat||!dat.length) continue;
      const v=dat[dat.length-1].value; if(v==null) continue;
      const y=l.ls.priceToCoordinate(v); if(y==null) continue;
      items.push({name:l.def.name.replace(/^Nifty /,''),color:l.def.color,y:y}); }
    items.sort((a,b)=>a.y-b.y);
    for(let i=1;i<items.length;i++){ if(items[i].y-items[i-1].y<13) items[i].y=items[i-1].y+13; }
    cont.innerHTML=items.map(it=>'<span style="position:absolute;right:3px;top:'+it.y.toFixed(1)
      +'px;transform:translateY(-50%);white-space:nowrap;font-size:11px;font-weight:700;color:'
      +it.color+';text-shadow:0 0 3px #0e1116,0 0 2px #0e1116">'+_e(it.name)+'</span>').join('');
  }

  // --- crosshair value row ------------------------------------------------
  const valRow=document.getElementById('rsVals');
  function _e(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function fmtVal(v){ return v==null?'—':v.toFixed(1); }
  function renderVals(map){
    if(!valRow) return;
    const parts=[];
    for(const l of lines){
      let v=null;
      if(map){ const d=map.get(l.ls); if(d&&d.value!=null) v=d.value; }
      else { const dat=l.ls.data(); if(dat&&dat.length) v=dat[dat.length-1].value; }
      parts.push('<span class="cmp-val" style="color:'+l.def.color+'">●'+_e(l.def.name)+' '+fmtVal(v)+'</span>');
    }
    valRow.innerHTML=parts.join('');
  }
  chart.subscribeCrosshairMove(p=>{
    if(!p||!p.time||!p.seriesData){ renderVals(null); return; }
    renderVals(p.seriesData);
  });

  // --- timeframe toggle ---------------------------------------------------
  document.querySelectorAll('[data-rstf]').forEach(b=>{
    b.onclick=()=>{
      tf=b.dataset.rstf;
      document.querySelectorAll('[data-rstf]').forEach(x=>x.classList.toggle('on', x===b));
      lastAnchor=null;
      rebuild(false);
      applyCurRange();
      renderVals(null);
    };
  });

  // --- length / range buttons (1Y/2Y/3Y/5Y/Max) — left-edge rebase, like the
  // price chart. Years (not bar-counts) so it works across D/W/M/Q. Max = full
  // series (default; preserves the prior behaviour). A window re-anchors the
  // rebase to its left edge so every line starts at 100 there.
  let lastDate=null, curRange=0;
  for(const s of RS_SERIES) for(const p of s.level) if(lastDate===null||p.t>lastDate) lastDate=p.t;
  function yearsAgo(d,n){ return (parseInt(d.slice(0,4),10)-n)+d.slice(4); }
  function setRsRange(yrs){
    curRange=yrs;
    if(!yrs){ internalSet=true; chart.timeScale().fitContent(); internalSet=false; reanchorToView(); }
    else { const to=lastDate, from=yearsAgo(lastDate,yrs);
      internalSet=true; chart.timeScale().setVisibleRange({from:from,to:to});
      const a=commonAnchor(from); lastAnchor=a; applyRebase(a); internalSet=false; }
    renderVals(null);
  }
  function applyCurRange(){ setRsRange(curRange); }
  document.querySelectorAll('[data-rsr]').forEach(b=>{
    b.onclick=()=>{ document.querySelectorAll('[data-rsr]').forEach(x=>x.classList.toggle('on', x===b));
      setRsRange(parseInt(b.dataset.rsr,10)); requestAnimationFrame(positionNames); };
  });

  // --- boot ---------------------------------------------------------------
  rebuild(false);
  applyCurRange();
  renderVals(null);
  // Gutter labels need the price scale laid out (priceToCoordinate null pre-paint),
  // which lags the first frame — retry until every visible line's label is placed.
  (function ensureNames(tries){
    positionNames();
    const cont=document.getElementById('rsNames');
    const want=lines.filter(l=>{ const d=l.ls.data(); return d&&d.length; }).length;
    if (cont && cont.children.length<want && tries>0)
      requestAnimationFrame(()=>ensureNames(tries-1));
  })(20);
  let rzT=null;
  new ResizeObserver(()=>{ if(internalSet) return; if(rzT) clearTimeout(rzT); rzT=setTimeout(()=>{ chart.applyOptions({}); positionNames(); },100); }).observe(host);
})();
</script>
"""


# Compare-picker universe (all indices + all equities) for the stock page's
# "+ Add" type-ahead. Identical on every stock page; changes only on the nightly
# equity/index refresh — so build the list + its JSON ONCE per data date and
# reuse, instead of a ~4000-row query + json.dumps on EVERY stock-page load.
_CMP_PICKER = {"date": None, "valid_set": None, "equity_set": None, "items_json": None}


def _cmp_picker(conn, date_key):
    if _CMP_PICKER["date"] != date_key or _CMP_PICKER["items_json"] is None:
        valid_set = {row["index_name"] for row in conn.execute(
            "SELECT DISTINCT index_name FROM index_rows").fetchall()}
        equities = [(row["symbol"], row["company_name"] or "") for row in conn.execute(
            "SELECT symbol, company_name FROM nse_equity_list ORDER BY symbol").fetchall()]
        items_json = json.dumps(
            [{"v": n, "t": "idx"} for n in sorted(valid_set)]
            + [{"v": s, "t": "stk", "n": nm} for s, nm in equities])
        _CMP_PICKER.update(date=date_key, valid_set=valid_set,
                           equity_set={s for s, _ in equities}, items_json=items_json)
    return _CMP_PICKER


@router.get("/dash/stock", response_class=HTMLResponse)
def dash_stock(sym: str = Query("", max_length=20),
               track: int = Query(0),
               cmp: list[str] = Query(default=[])) -> HTMLResponse:
    sym = sym.upper().strip()
    search = f"""
<form class="search" action="/dash/stock" method="get">
  <input name="sym" placeholder="Enter NSE ticker — e.g. BANDHANBNK" value="{_esc(sym)}" autocapitalize="characters" autocomplete="off"/>
  <button type="submit">Go</button>
</form>
"""
    if not sym:
        body = search + '<div class="empty">Enter a ticker for the full chart — price, DVPT spikes, delivery, and institutional zones.</div>'
        return HTMLResponse(_shell("Stock · patearn", body, "stock"))

    with get_conn() as conn:
        # Latest signal row + that day's EQ close/deliv as TWO indexed point
        # lookups. The single joined `ORDER BY s.trade_date DESC LIMIT 1` with
        # `b.series='EQ'` mis-planned to a scan of EVERY EQ bhav row (via
        # idx_bhav_series) → ~3.1s per stock page; this is ~0.2ms.
        latest = conn.execute(
            "SELECT * FROM stock_signals WHERE symbol=? ORDER BY trade_date DESC LIMIT 1",
            (sym,)).fetchone()
        if latest:
            latest = dict(latest)
            _bq = conn.execute(
                "SELECT close, deliv_per FROM bhavcopy_rows "
                "WHERE symbol=? AND trade_date=? AND series='EQ' LIMIT 1",
                (sym, latest["trade_date"])).fetchone()
            latest["close"] = _bq["close"] if _bq else None
            latest["deliv_per"] = _bq["deliv_per"] if _bq else None
        # Up to 5 years of daily candles + DVPT + delivery for the charts (oldest first)
        rows = conn.execute(
            """SELECT b.trade_date, b.open, b.high, b.low, b.close, b.prev_close,
                      b.deliv_per, b.value, b.deliv_qty,
                      s.delivery_value_per_trade dvpt, s.ratio_today_vs_power_1m r1m
               FROM bhavcopy_rows b
               LEFT JOIN stock_signals s USING (symbol, trade_date)
               WHERE b.symbol=? AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
               ORDER BY b.trade_date DESC LIMIT 1300""",
            (sym,),
        ).fetchall()
        # Cached fundamentals + latest pt14 pattern score (best-effort).
        try:
            fund = conn.execute("SELECT * FROM fundamentals WHERE symbol=?", (sym,)).fetchone()
        except Exception:
            fund = None
        try:
            pscore = conn.execute(
                "SELECT * FROM pattern_scores WHERE symbol=? ORDER BY scored_at DESC LIMIT 1",
                (sym,)).fetchone()
        except Exception:
            pscore = None
        try:
            cpr_by_tf = _cpr_latest_by_tf(conn, [sym]).get(sym, {})   # CPR Structure panel (D53)
        except Exception:
            cpr_by_tf = {}

    if not latest or not rows:
        body = search + f'<div class="empty">No data for <b>{_esc(sym)}</b>. Check the ticker.</div>'
        return HTMLResponse(_shell("Stock · patearn", body, "stock"))

    L = dict(latest)
    rank = L.get("trigger_rank") or "-"
    ath = "⚡ ATH-DVPT" if L.get("is_ath_dvpt") else ""
    today_close = L.get("close")

    # Build the chart series (oldest first), keeping prev_close for adjustment.
    series = []
    for r in reversed([dict(x) for x in rows]):
        c = r["close"]
        if c is None:
            continue
        o = r["open"] if r["open"] is not None else c
        hi = r["high"] if r["high"] is not None else c
        lo = r["low"] if r["low"] is not None else c
        # Traded value (turnover ₹) and delivery value (deliv_qty × raw close ₹)
        # are RUPEE figures — naturally split/bonus invariant, so they use the
        # RAW close/qty here, NOT the back-adjusted prices computed below (which
        # only rescale the candle/zone *price* levels). deliv ≤ turnover always.
        tval = r["value"] if r["value"] is not None else None
        dq = r["deliv_qty"]
        dval = (dq * c) if (dq is not None and c is not None) else None
        series.append({
            "time": r["trade_date"],
            "open": o, "high": hi, "low": lo, "close": c,
            "prev_close": r["prev_close"],
            "dvpt": int(r["dvpt"]) if r["dvpt"] is not None else 0,
            "deliv": round(r["deliv_per"], 1) if r["deliv_per"] is not None else None,
            "r1m": round(r["r1m"], 2) if r["r1m"] is not None else None,
            "tval": round(tval, 2) if tval is not None else None,
            "dval": round(dval, 2) if dval is not None else None,
        })

    # --- Corporate-action back-adjustment (splits / bonuses) ---------------
    # NSE sets prev_close to the ADJUSTED previous close on a split/bonus
    # ex-date, so prev_close[i] / close[i-1] deviates from 1 ONLY on real
    # action dates. Walk backward, accumulate the factor, scale older OHLC
    # down so the chart is continuous (same method Zerodha uses). Dividends
    # do NOT adjust prev_close, so they don't trigger this.
    n = len(series)
    factors = [1.0] * n
    cum = 1.0
    PC_THRESH = 0.03   # prev_close flag: real splits/bonuses; normal days = 0%
    CC_THRESH = 0.30   # close-jump fallback: >30% single-day move = action NSE
                       # didn't adjust prev_close for (circuit limits make a real
                       # 30%+ daily move impossible, so it's always a corp action)
    for i in range(n - 1, 0, -1):
        prior_close = series[i - 1]["close"]
        this_close = series[i]["close"]
        pc = series[i].get("prev_close")
        ratio = None
        # Primary: prev_close-based (precise, NSE-adjusted).
        if pc and prior_close and prior_close > 0:
            r_pc = pc / prior_close
            if abs(r_pc - 1) > PC_THRESH and 0.02 < r_pc < 50:
                ratio = r_pc
        # Fallback: prev_close didn't flag but the close gapped hugely — an
        # unadjusted corporate action (PARAS 2025-07-04 style).
        if ratio is None and prior_close and prior_close > 0 and this_close:
            r_cc = this_close / prior_close
            if abs(r_cc - 1) > CC_THRESH and 0.02 < r_cc < 50:
                ratio = r_cc
        if ratio is not None:
            cum *= ratio
        factors[i - 1] = cum
    for i in range(n):
        f = factors[i]
        s = series[i]
        s["open"]  = round(s["open"]  * f, 2)
        s["high"]  = round(s["high"]  * f, 2)
        s["low"]   = round(s["low"]   * f, 2)
        s["close"] = round(s["close"] * f, 2)
        s.pop("prev_close", None)

    # The institutional zones are computed from recent raw closes; if any
    # corporate action occurred within the zone window we flag it so the
    # overlay isn't silently misaligned.
    zone_action_recent = any(f != 1.0 for f in factors[-264:]) if n else False

    # Institutional zone levels for horizontal lines on the price chart.
    zone_line_defs = [
        ("P1M",  "avg_close_p1m",  "#f0b429"),
        ("P3M",  "avg_close_p3m",  "#de911d"),
        ("P6M",  "avg_close_p6m",  "#cb6e17"),
        ("P12M", "avg_close_p12m", "#b44d12"),
        ("R12M", "avg_close_r12m", "#1f6feb"),
    ]
    zone_lines = []
    for label, col, color in zone_line_defs:
        v = L.get(col)
        if v:
            zone_lines.append({"label": label, "price": round(v, 2), "color": color})

    chart_data = {"series": series, "zones": zone_lines}
    data_json = json.dumps(chart_data)

    # --- Institutional price-zone table (kept as a precise reference) ---
    zone_defs = [
        ("P1M", "avg_close_p1m"), ("P2M", "avg_close_p2m"), ("P3M", "avg_close_p3m"),
        ("P6M", "avg_close_p6m"), ("P12M", "avg_close_p12m"),
        ("R1M", "avg_close_r1m"), ("R2M", "avg_close_r2m"), ("R3M", "avg_close_r3m"),
        ("R6M", "avg_close_r6m"), ("R12M", "avg_close_r12m"),
    ]
    def zone_row(label, col):
        zp = L.get(col)
        if zp is None or not today_close:
            return f'<div class="zone"><span class="lbl">{label}</span><span class="val mut">—</span></div>'
        gap = (today_close - zp) / zp * 100
        mk = "🟢" if gap < -3 else ("🔴" if gap > 3 else "🟡")
        return (f'<div class="zone"><span class="lbl">{label}</span>'
                f'<span class="val">₹{zp:,.1f}</span>'
                f'<span class="val">{_pct(gap)} {mk}</span></div>')

    has_zones = any(L.get(c) for _, c in zone_defs)
    zones_html = ""
    if has_zones:
        p_rows = "".join(zone_row(l, c) for l, c in zone_defs[:5])
        r_rows = "".join(zone_row(l, c) for l, c in zone_defs[5:])
        zones_html = f"""
<h2>Institutional price zones</h2>
<div class="sub">Today's close vs avg close on baseline days. 🟢 discount · 🟡 at-cost · 🔴 above.</div>
<div class="card">
<div class="sub" style="margin:0 0 6px;">P-tier — where institutions transacted</div>
{p_rows}
<div class="sub" style="margin:10px 0 6px;">R-tier — flat baseline zone</div>
{r_rows}
</div>
"""

    # --- D44 value-weighted institutional KEY PRICE (additive, beside zones) --
    kp_defs = [("1M", "key_price_p1m", "gap_to_key_p1m"),
               ("2M", "key_price_p2m", "gap_to_key_p2m"),
               ("3M", "key_price_p3m", "gap_to_key_p3m"),
               ("6M", "key_price_p6m", "gap_to_key_p6m"),
               ("12M", "key_price_p12m", "gap_to_key_p12m")]
    has_kp = any(L.get(c) for _, c, _ in kp_defs)
    keyprice_html = ""
    if has_kp:
        kp_rows = ""
        near = []
        for lbl, kc, gc in kp_defs:
            kp = L.get(kc)
            g = L.get(gc)
            if kp is None:
                kp_rows += (f'<div class="zone"><span class="lbl">{lbl}</span>'
                            f'<span class="val mut">—</span><span class="val mut">—</span></div>')
                continue
            nk = is_near_key(g)
            if nk:
                near.append(lbl)
            mk = "🎯" if nk else ("🟢" if (g is not None and g < -1)
                                  else ("🔴" if (g is not None and g > 5) else "🟡"))
            kp_rows += (f'<div class="zone"><span class="lbl">{lbl}</span>'
                        f'<span class="val">₹{kp:,.1f}</span>'
                        f'<span class="val">{_pct(g)} {mk}</span></div>')
        g3 = L.get("gap_to_key_p3m")
        if near:
            read = (f'🎯 <b>In the launch band</b> on {", ".join(near)} — close ₹{_num(today_close,1)} '
                    f'is within −1%…+5% of the value-weighted institutional cost.')
        elif g3 is not None and g3 < -1:
            read = (f'Close is <b>{g3:+.1f}%</b> below the 3m key price — under institutional cost '
                    f'(discount, not yet in the launch band).')
        elif g3 is not None and g3 > 5:
            read = f'Close is <b>{g3:+.1f}%</b> above the 3m key price — extended beyond the launch band.'
        else:
            read = 'No horizon in the launch band right now.'
        tq, td = L.get("avg_trade_qty"), L.get("avg_deliv_qty_per_trade")
        s1, s3, s1y = L.get("turnover_surge_1m"), L.get("turnover_surge_3m"), L.get("turnover_surge_1y")
        meta = (f'<div class="sub" style="margin:8px 0 0">Ticket: '
                f'<b>{_num(tq,0) if tq is not None else "—"}</b> sh/trade · deliv '
                f'<b>{_num(td,0) if td is not None else "—"}</b> sh/trade · turnover surge 1m/3m/1y: '
                f'{_num(s1,2) if s1 is not None else "—"}× / {_num(s3,2) if s3 is not None else "—"}× / '
                f'{_num(s1y,2) if s1y is not None else "—"}×</div>')
        keyprice_html = f"""
<h2>Institutional key price <span class="mut" style="font-size:13px">value-weighted</span></h2>
<div class="sub">Weighted by delivered value on the top-N power days (the big institutional day dominates the cost line), priced at the day's avg price. Gap = today's close vs that key. 🎯 launch band (−1%…+5%).</div>
<div class="card">{kp_rows}</div>
<div class="sub" style="margin:6px 0 0">{read}</div>
{meta}
"""

    # --- DVPT inertia: today vs every avg (R) + power (P) baseline --------
    today_dvpt = L.get("delivery_value_per_trade")
    inertia_windows = [
        ("1M",  "avg_dvpt_1m",  "power_dvpt_1m"),
        ("2M",  "avg_dvpt_2m",  "power_dvpt_2m"),
        ("3M",  "avg_dvpt_3m",  "power_dvpt_3m"),
        ("6M",  "avg_dvpt_6m",  "power_dvpt_6m"),
        ("12M", "avg_dvpt_12m", "power_dvpt_12m"),
    ]

    def _mult_cell(mult):
        if mult is None:
            return '<span class="mut">—</span>'
        ic = "🔥" if mult >= 3 else ("⚡" if mult >= 1.5 else ("🟢" if mult >= 1 else ("🟡" if mult >= 0.5 else "🔵")))
        col = "#f0883e" if mult >= 1.5 else ("#3fb950" if mult >= 1 else "#8b949e")
        return f'<span style="color:{col};font-weight:700">{mult:.1f}× {ic}</span>'

    inertia_rows = []
    for label, acol, pcol in inertia_windows:
        av = L.get(acol)
        pv = L.get(pcol)
        am = (today_dvpt / av) if (today_dvpt and av and av > 0) else None
        pm = (today_dvpt / pv) if (today_dvpt and pv and pv > 0) else None
        inertia_rows.append(
            f'<tr><td class="mut">{label}</td>'
            f'<td>{("₹"+format(int(av),",")) if av else "—"}</td>'
            f'<td>{_mult_cell(am)}</td>'
            f'<td>{("₹"+format(int(pv),",")) if pv else "—"}</td>'
            f'<td>{_mult_cell(pm)}</td></tr>'
        )
    inertia_html = f"""
<h2>DVPT inertia — today vs baselines</h2>
<div class="sub">Today's DVPT <b>₹{int(today_dvpt or 0):,}</b>. "× today" = how many times today exceeds each baseline — the inertia gauge. 🔥 ≥3× · ⚡ ≥1.5× · 🟢 ≥1× · 🟡 &lt;1×</div>
<div class="card" style="padding:6px 10px;">
<table>
<thead><tr><th>Win</th><th>Avg DVPT (R)</th><th>×&nbsp;today</th><th>Power DVPT (P)</th><th>×&nbsp;today</th></tr></thead>
<tbody>{''.join(inertia_rows)}</tbody>
</table>
</div>
"""

    # --- D43 Accumulation/distribution character --------------------------
    # Delivery is side-blind, so this fuses three independent axes — WHO
    # (breadth), WHICH-WAY (adjusted-price direction), CONTEXT (52w location) —
    # into a label + plain-English read (both from the shared signals helper).
    char_label = L.get("accum_character")
    char_read = accum_character_read(
        char_label, L.get("p_score"), L.get("trade_count_ratio_1m_6m"),
        L.get("deliv_updown_ratio_3m"), L.get("accum_price_drift_3m"),
        L.get("pct_from_52w_high"), L.get("deliv_value_ratio_1m_6m"),
    )
    character_html = ""
    if char_label:
        updown = L.get("deliv_updown_ratio_3m")
        up_frac = (updown / (1.0 + updown)) if updown is not None else None
        if up_frac is not None:
            up_pct = max(2.0, min(98.0, up_frac * 100.0))
            skew_txt = ("up-skewed" if updown >= 1.3 else
                        "down-skewed" if updown <= 0.77 else "balanced")
            bar = (f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;'
                   f'margin:2px 0 4px;background:#21262d">'
                   f'<span style="width:{up_pct:.0f}%;background:#2ea043"></span>'
                   f'<span style="width:{100 - up_pct:.0f}%;background:#f85149"></span></div>'
                   f'<div class="sub" style="margin:0">Delivery ₹ on up-days (green) vs down-days '
                   f'(red), 3m — ratio <b>{updown:.2f}</b> ({skew_txt}).</div>')
        else:
            bar = '<div class="sub" style="margin:2px 0 0">Up/down delivery split: <span class="mut">—</span></div>'
        tcr = L.get("trade_count_ratio_1m_6m")
        breadth = ("broadening (retail crowd)" if (tcr is not None and tcr >= 1.3)
                   else "concentrated (few hands)" if (tcr is not None and tcr <= 1.1)
                   else "steady" if tcr is not None else "—")
        dvr = L.get("deliv_value_ratio_1m_6m")
        ticket = (dvr / tcr) if (dvr is not None and tcr and tcr > 0) else None
        ticket_txt = ("rising" if (ticket is not None and ticket >= 1.1)
                      else "falling" if (ticket is not None and ticket <= 0.9)
                      else "flat" if ticket is not None else "—")
        dvt_today = L.get("delivery_value_today")
        dvt_cr = f'₹{dvt_today / 1e7:,.1f} Cr' if dvt_today else "—"
        dp1, dp6 = L.get("avg_deliv_pct_1m"), L.get("avg_deliv_pct_6m")
        who = (
            '<table><tbody>'
            f'<tr><td class="mut">Total delivery ₹ (today)</td><td>{dvt_cr}</td>'
            f'<td class="mut">Trade-count trend</td><td>{breadth}</td></tr>'
            f'<tr><td class="mut">Delivery % 1m / 6m</td>'
            f'<td>{_num(dp1, 1) if dp1 is not None else "—"} / {_num(dp6, 1) if dp6 is not None else "—"}</td>'
            f'<td class="mut">Avg ticket trend</td><td>{ticket_txt}</td></tr>'
            f'<tr><td class="mut">vs 52-week high</td><td>{_pct(L.get("pct_from_52w_high"))}</td>'
            f'<td class="mut">3m price drift</td><td>{_pct(L.get("accum_price_drift_3m"))}</td></tr>'
            '</tbody></table>')
        warn = ""
        if char_label == "DISTRIBUTION" and rank in ("SS", "S", "A"):
            warn = ('<div class="card" style="border-color:#8f1f1f;background:#2a1414;margin-top:8px">'
                    '<div class="sub" style="margin:0;color:#ffa198">⚠️ Heavy delivery, but on '
                    'down-days / price rolling over near highs while the crowd broadens — this reads '
                    'as <b>distribution, not accumulation</b>, despite the high trigger rank.</div></div>')
        character_html = f"""
<h2>Accumulation character {_char_pill(char_label)}</h2>
<div class="sub">Delivery is side-blind — this fuses <b>WHO</b> (breadth) · <b>WHICH-WAY</b> (price) · <b>CONTEXT</b> (trend location). {_esc(char_read)}</div>
<div class="card" style="padding:10px 12px;">
{bar}
<div style="margin-top:8px">{who}</div>
</div>
{warn}
"""

    # --- Auto-derived insights (no LLM) -----------------------------------
    insights = []
    r1m = L.get("ratio_today_vs_power_1m")
    psc = L.get("p_score") or 0
    rsc = L.get("r_score") or 0
    if r1m is not None:
        if r1m >= 3:
            insights.append(f"🔥 <b>Explosive institutional inertia</b> — today's DVPT is <b>{r1m:.1f}×</b> the 1-month power baseline.")
        elif r1m >= 1.5:
            insights.append(f"⚡ <b>Exceptional inertia</b> — {r1m:.1f}× the 1-month peak baseline.")
        elif r1m >= 1:
            insights.append(f"🟢 Above the institutional baseline ({r1m:.1f}×).")
        elif r1m >= 0.5:
            insights.append(f"🟡 Below recent peak intensity ({r1m:.1f}×) — accumulation cooling.")
        else:
            insights.append(f"🔵 Quiet — {r1m:.1f}× the peak baseline.")
    if L.get("is_ath_dvpt"):
        insights.append("⚡ <b>ATH-DVPT</b> — highest per-trade delivery value in the stock's entire history.")
    if rank in ("SS", "S", "A", "B", "C"):
        insights.append(f"Rank <b>{rank}</b> — clears <b>{psc}/5</b> power baselines &amp; <b>{rsc}/5</b> rolling averages.")
    pvh = L.get("price_vs_hot_avg_pct")
    if pvh is not None:
        if pvh < -3:
            insights.append(f"🟢 Price <b>{pvh:.1f}%</b> below where institutions recently transacted — <b>discount entry</b>.")
        elif pvh > 3:
            insights.append(f"🔴 Price <b>+{pvh:.1f}%</b> above the recent institutional zone — extended.")
        else:
            insights.append(f"🟡 Price in the institutional cost zone ({pvh:+.1f}%).")
    nextp = L.get("next_p_above")
    gapn = L.get("gap_to_next_p_pct")
    if nextp and gapn is not None and -12 < gapn < 0:
        insights.append(f"🔥 <b>Near-break</b> — DVPT is only {gapn:.1f}% under the {nextp} power wall; a push above flips the rank up.")
    insight_html = ""
    if insights:
        items = "".join(f"<li>{x}</li>" for x in insights)
        insight_html = f"""
<div class="card" style="border-color:#1f6feb">
<div class="sub" style="margin:0 0 6px;color:#58a6ff">📌 READ — DVPT / institutional flow</div>
<ul style="margin:0;padding-left:18px;line-height:1.55">{items}</ul>
</div>
"""

    # --- pt14 quality + fundamentals (from cache; best-effort) ------------
    F = dict(fund) if fund else {}
    PS = dict(pscore) if pscore else {}
    pt14_html = ""
    if F or PS:
        def fv(k, suffix=""):
            v = F.get(k)
            return (f"{v}{suffix}" if v is not None else "—")
        tier = PS.get("tier")
        ns = PS.get("ns_base")
        tier_line = ""
        if tier:
            tier_line = f'<span class="pill p-SS">{_esc(tier)}</span> NS {_num(ns,1) if ns is not None else "—"}'
        pt14_html = f"""
<h2>Quality — patearn (pt14) {tier_line}</h2>
<div class="sub">Cached fundamentals snapshot. Run <code>/pt14 {_esc(sym)}</code> for the full 14-pattern breakdown.</div>
<div class="card" style="padding:6px 10px;">
<table>
<tbody>
<tr><td class="mut">Market cap</td><td>{("₹"+_num(F.get('market_cap_cr'),0)+" Cr") if F.get('market_cap_cr') else "—"}</td>
    <td class="mut">PE</td><td>{fv('pe')}</td></tr>
<tr><td class="mut">ROCE</td><td>{fv('roce','%')}</td>
    <td class="mut">ROE</td><td>{fv('roe','%')}</td></tr>
<tr><td class="mut">Sales gr 3y</td><td>{fv('sales_growth_3y','%')}</td>
    <td class="mut">Profit gr 3y</td><td>{fv('profit_growth_3y','%')}</td></tr>
<tr><td class="mut">OPM</td><td>{fv('opm_latest','%')}</td>
    <td class="mut">D/E</td><td>{fv('debt_to_equity')}</td></tr>
<tr><td class="mut">Promoter</td><td>{fv('promoter_holding','%')}</td>
    <td class="mut">Pledge</td><td>{fv('promoter_pledge','%')}</td></tr>
</tbody>
</table>
</div>
"""
    else:
        pt14_html = f"""
<h2>Quality — patearn (pt14)</h2>
<div class="card"><div class="sub" style="margin:0">No cached fundamentals yet. Run <code>/pt14 {_esc(sym)}</code> in Telegram (or it'll cache on first scoring) to populate PE / ROCE / growth / the 14-pattern tier here.</div></div>
"""

    # --- Relative strength vs Nifty 500 (D33a) ----------------------------
    # Reads the denormalized rs_vs_broad_* columns on the latest stock_signals
    # row (UPDATEd by src.automation.stock_rs). NULL → not backfilled yet.
    rs_today = L.get("rs_vs_broad_today")
    rs_state = L.get("rs_vs_broad_trend_state")
    rs_rank = L.get("rs_rank")
    if rs_today is None and rs_state is None:
        rs_html = """
<h2>Relative strength <span class="mut" style="font-size:13px">vs Nifty 500</span></h2>
<div class="card"><div class="sub" style="margin:0">RS not yet computed — run <code>python -m src.automation.stock_rs --backfill</code> (or <code>--symbol {0}</code>) to populate stock-vs-Nifty-500 relative strength. Use <b>/sectors</b> for the sector-rotation picture meanwhile.</div></div>
""".format(_esc(sym))
    else:
        rs_pill = (f'<span class="pill p-{rs_state}">{rs_state}</span>'
                   if rs_state else '<span class="pill p-C">—</span>')
        rs_strip = _rs_strip(
            L.get("rs_vs_broad_slope_1m"), L.get("rs_vs_broad_slope_3m"),
            L.get("rs_vs_broad_slope_6m"), L.get("rs_vs_broad_slope_12m"),
        )
        if rs_rank is not None:
            rank_html = (
                f'<div class="sub" style="margin:8px 0 4px">RS {rs_rank} / 99 — '
                f'stronger than {rs_rank}% of the market '
                f'(0.6·3m + 0.4·6m RS slope vs Nifty 500).</div>'
                f'<div class="card" style="margin-top:0"><div class="bar">'
                f'<span style="width:{rs_rank}%"></span></div></div>')
        else:
            rank_html = ('<div class="sub" style="margin:8px 0 4px">RS rank not '
                         'computed (outside the liquid universe, or insufficient '
                         '3m history).</div>')
        # D33b — stock-vs-PRIMARY-SECTOR RS (rs_vs_sector_* + the denormalized
        # primary_sector, from stock_rs). Shown alongside the broad read; absent
        # for a stock in no NSE sectoral index. "Is it leading its own pack?"
        sec_name = L.get("primary_sector")
        sec_state = L.get("rs_vs_sector_trend_state")
        sec_today = L.get("rs_vs_sector_today")
        has_sector = bool(sec_name) and (sec_today is not None or sec_state is not None)
        if has_sector:
            sec_pill = (f'<span class="pill p-{sec_state}">{sec_state}</span>'
                        if sec_state else '<span class="pill p-C">—</span>')
            sec_strip = _rs_strip(
                L.get("rs_vs_sector_slope_1m"), L.get("rs_vs_sector_slope_3m"),
                L.get("rs_vs_sector_slope_6m"), L.get("rs_vs_sector_slope_12m"),
            )
            sector_block = (
                f'<div class="sub" style="margin:12px 0 4px">vs sector '
                f'<b>{_esc(sec_name)}</b> — is it leading its own pack?</div>'
                f'<div class="chips" style="margin-bottom:6px">{sec_pill}</div>'
                f'<div class="card" style="margin-top:0">{sec_strip}</div>')
        else:
            sector_block = (
                '<div class="sub" style="margin:12px 0 4px">vs sector: '
                '<span class="mut">no NSE sectoral index covers this stock — '
                'broad RS only.</span></div>')
        # Reconciliation breakdown — the stock's own return vs the benchmark's
        # return, and the resulting RS, per window, so "RS ≈ stock − benchmark"
        # is verifiable on the page for BOTH the broad and sector reads. Stock
        # return uses the ADJUSTED `series`; benchmark return = index_signals
        # ret_* (same 30/90/180/365-day windows).
        recon_table = ""
        if series:
            with get_conn() as conn:
                n5row = conn.execute(
                    "SELECT ret_1m_pct r1, ret_3m_pct r3, ret_6m_pct r6, "
                    "ret_12m_pct r12 FROM index_signals WHERE index_name='Nifty 500' "
                    "ORDER BY trade_date DESC LIMIT 1"
                ).fetchone()
                secrow = conn.execute(
                    "SELECT ret_1m_pct r1, ret_3m_pct r3, ret_6m_pct r6, "
                    "ret_12m_pct r12 FROM index_signals WHERE index_name=? "
                    "ORDER BY trade_date DESC LIMIT 1", (sec_name,)
                ).fetchone() if has_sector else None
            n5 = dict(n5row) if n5row else {}
            sec = dict(secrow) if secrow else {}

            def _stk_ret(days):
                cut = (datetime.strptime(series[-1]["time"], "%Y-%m-%d")
                       - timedelta(days=days)).strftime("%Y-%m-%d")
                base = None
                for s in series:
                    if s["time"] <= cut:
                        base = s["close"]
                    else:
                        break
                now = series[-1]["close"]
                return (now / base - 1) * 100 if (base and base > 0 and now) else None

            rrows = ""
            for lbl, days, nk, brk, srk in (
                    ("1m", 30, "r1", "rs_vs_broad_slope_1m", "rs_vs_sector_slope_1m"),
                    ("3m", 90, "r3", "rs_vs_broad_slope_3m", "rs_vs_sector_slope_3m"),
                    ("6m", 180, "r6", "rs_vs_broad_slope_6m", "rs_vs_sector_slope_6m"),
                    ("12m", 365, "r12", "rs_vs_broad_slope_12m", "rs_vs_sector_slope_12m")):
                cells = (f'<td class="mut">{lbl}</td><td>{_pct(_stk_ret(days))}</td>'
                         f'<td>{_pct(n5.get(nk))}</td><td><b>{_pct(L.get(brk))}</b></td>')
                if has_sector:
                    cells += (f'<td>{_pct(sec.get(nk))}</td>'
                              f'<td><b>{_pct(L.get(srk))}</b></td>')
                rrows += f'<tr>{cells}</tr>'
            sec_head = (f'<th>{_esc(sec_name)}</th><th>RS·sector</th>'
                        if has_sector else '')
            recon_table = (
                '<div class="sub" style="margin:10px 0 4px">Reconcile — RS ≈ this '
                "stock's return minus the benchmark's return, per window:</div>"
                '<div class="card" style="padding:6px 10px;margin-top:0"><table>'
                f'<thead><tr><th>Window</th><th>{_esc(sym)}</th><th>Nifty 500</th>'
                f'<th>RS·broad</th>{sec_head}</tr></thead>'
                f'<tbody>{rrows}</tbody></table></div>')
        rs_html = f"""
<h2>Relative strength <span class="mut" style="font-size:13px">vs Nifty 500 + sector</span></h2>
<div class="sub" style="margin:0 0 4px">vs broad <b>Nifty 500</b> — is it beating the market?</div>
<div class="chips" style="margin-bottom:6px">{rs_pill}</div>
{rank_html}
<div class="sub" style="margin:8px 0 4px">RS-vs-Nifty-500 momentum across horizons (▲ outperforming, ▼ lagging):</div>
<div class="card" style="margin-top:0">{rs_strip}</div>
{sector_block}
{recon_table}
"""

    # --- Relative-strength OVERLAY (stock vs narrow sector vs broad) ---------
    # Three CLOSE-price series rebased to a common start (reuses the
    # /dash/compare rebase idiom). Stock line = the ADJUSTED `series` close (same
    # as the price chart). Narrow = primary_sector index; broad = 'Nifty 500'.
    # All resampled client-side for the D/W/M/Q toggle, so it's read ONCE here.
    rs_overlay_html = ""
    if series:
        rs_sym_name = sym
        rs_narrow_name = L.get("primary_sector")          # may be None
        d_lo, d_hi = series[0]["time"], series[-1]["time"]
        with get_conn() as conn:
            _pc = _cmp_picker(conn, L.get("trade_date"))
            valid_set = _pc["valid_set"]
            equity_set = _pc["equity_set"]
            # Robust sector (#1): if primary_sector isn't populated yet (e.g. mid
            # RS-recompute), derive the narrowest sectoral index from membership
            # so the sector line + same-sector peers still show.
            if not rs_narrow_name:
                rs_narrow_name = _narrow_sector(conn, sym)
            # Same-sector peer tickers for the quick-pick rail (#2).
            sector_peers = []
            if rs_narrow_name:
                sector_peers = [s for s in _sector_symbols(conn, rs_narrow_name)
                                if s != sym and s in equity_set][:12]
            # Overlay = explicit ?cmp= (index names or tickers), else the defaults:
            # the stock's sector + Nifty 500 + Nifty 50.
            if cmp:
                ov, ovseen = [], set()
                for c in cmp:
                    c = (c or "").strip()
                    cu = c.upper()
                    if c in valid_set and c not in ovseen:
                        ov.append(("idx", c)); ovseen.add(c)
                    elif cu in equity_set and cu != sym and cu not in ovseen:
                        ov.append(("stk", cu)); ovseen.add(cu)
                    if len(ov) >= _COMPARE_MAX - 1:
                        break
            else:
                ov = [("idx", n) for n in ("Nifty 500", "Nifty 50") if n in valid_set]
                if rs_narrow_name and rs_narrow_name in valid_set:
                    ov.insert(0, ("idx", rs_narrow_name))
            ov_idx = [n for k, n in ov if k == "idx"]
            ov_stk = [n for k, n in ov if k == "stk"]
            idx_levels: dict[str, list] = {}
            if ov_idx:
                ph = ",".join("?" for _ in ov_idx)
                for row in conn.execute(
                    f"""SELECT index_name, trade_date, close_value
                        FROM index_rows
                        WHERE index_name IN ({ph})
                          AND trade_date >= ? AND trade_date <= ?
                          AND close_value IS NOT NULL
                        ORDER BY index_name, trade_date""",
                    (*ov_idx, d_lo, d_hi),
                ).fetchall():
                    idx_levels.setdefault(row["index_name"], []).append(
                        {"t": row["trade_date"], "v": round(row["close_value"], 2)})
            stk_levels = _stock_levels(conn, ov_stk)

        # Stock first (palette 0), then each overlay that has data in the window.
        rs_series = [{
            "name": rs_sym_name,
            "color": _cmp_color(0),
            "level": [{"t": s["time"], "v": s["close"]}
                      for s in series if s["close"] is not None],
        }]
        ov_present = []
        for k, name in ov:
            if k == "idx":
                lvl = idx_levels.get(name)
            else:
                lvl = [p for p in (stk_levels.get(name) or []) if d_lo <= p["t"] <= d_hi]
            if not lvl:
                continue
            rs_series.append({
                "name": name,
                "color": _cmp_color(len(rs_series)),
                "level": lvl,
            })
            ov_present.append((k, name))

        # Need the stock + at least one benchmark to be meaningful.
        if len(rs_series) >= 2:
            rs_overlay_json = json.dumps(rs_series)

            def _so_href(items):
                return "/dash/stock?" + "&".join(
                    [f"sym={_q(sym)}"] + [f"cmp={_q(n)}" for _, n in items])

            stock_chip = (f'<span class="cmp-chip"><span class="cmp-sw" '
                          f'style="background:{_cmp_color(0)}"></span>'
                          f'<span><b>{_esc(sym)}</b></span></span>')
            chip_html = []
            for ci, (k, name) in enumerate(ov_present):
                rest = [it for it in ov_present if it != (k, name)]
                tag = "" if k == "idx" else ' <span class="cmp-tag">stk</span>'
                chip_html.append(
                    f'<span class="cmp-chip"><span class="cmp-sw" '
                    f'style="background:{_cmp_color(1 + ci)}"></span>'
                    f'<span>{_esc(name)}</span>{tag}'
                    f'<a class="cmp-x" href="{_esc(_so_href(rest))}" title="remove">✕</a></span>')
            at_cap = len(ov_present) >= _COMPARE_MAX - 1
            add_btn = ('<button class="chip" id="soAddBtn" type="button">+ Add</button>'
                       if not at_cap
                       else f'<span class="chip cmp-dim">max {_COMPARE_MAX - 1}</span>')
            so_rail = ('<div class="cmp-rail">' + stock_chip
                       + "".join(chip_html) + add_btn + '</div>')
            so_add = ""
            if not at_cap:
                peer_html = ""
                if sector_peers:
                    pchips = "".join(
                        f'<button type="button" class="chip cmp-sugg" data-name="{_esc(p)}">+ {_esc(p)}</button>'
                        for p in sector_peers)
                    peer_html = (
                        f'<div class="sub" style="margin:6px 0 4px"><b>{_esc(rs_narrow_name)}</b> peers — tap to stage:</div>'
                        f'<div id="soPeers" class="chips" style="margin-bottom:6px">{pchips}</div>')
                so_add = (
                    '<div id="soAddWrap" style="display:none">'
                    '<div class="search" style="margin-top:6px">'
                    '<input id="soSearch" placeholder="Add a ticker or index — LT, RELIANCE, Nifty Bank…" autocomplete="off"/>'
                    '<button class="dtx" id="soAddConfirm" type="button" disabled>Add</button></div>'
                    f'<div class="sub" style="margin:2px 0 6px">Tickers match from 2 letters, '
                    f'names from 4. Tap to stage, then <b>Add</b> (up to {_COMPARE_MAX - 1}).</div>'
                    + peer_html +
                    '<div id="soResults" class="chips" style="margin-top:6px"></div>'
                    '</div>')
            cmp_items_json = _pc["items_json"]
            sec_note = (f" + {_esc(rs_narrow_name)} (sector)"
                        if rs_narrow_name and not cmp else "")
            rs_overlay_html = f"""
<h2>Relative strength — overlay <a class="row" style="font-size:13px;font-weight:400" href="/dash/compare?sym={_q(sym)}&idx={_q('Nifty 500')}&idx={_q('Nifty 50')}">↗ open in Compare ⇄</a></h2>
<div class="sub"><b>{_esc(sym)}</b> rebased against your benchmarks (base 100, default Nifty 500 + Nifty 50{sec_note}) — above a line = outperforming it. Add any stock or index with <b>+ Add</b>.</div>
{so_rail}{so_add}
<div class="fbar" id="rsTfBar">
  <button class="fbtn on" data-rstf="d">Daily</button>
  <button class="fbtn" data-rstf="w">Weekly</button>
  <button class="fbtn" data-rstf="m">Monthly</button>
  <button class="fbtn" data-rstf="q">Quarterly</button>
</div>
<div class="fbar" id="rsRangeBar">
  <button class="fbtn" data-rsr="1">1Y</button>
  <button class="fbtn" data-rsr="2">2Y</button>
  <button class="fbtn" data-rsr="3">3Y</button>
  <button class="fbtn" data-rsr="5">5Y</button>
  <button class="fbtn on" data-rsr="0">Max</button>
</div>
<div class="cmp-anchor" id="rsAnchorLbl">REBASED FROM <b>start</b></div>
<div class="chartwrap"><div style="position:relative"><div id="rsOverlayChart" style="height:300px;margin-right:104px;"></div><div id="rsNames" style="position:absolute;top:0;right:0;bottom:0;width:104px;pointer-events:none;overflow:visible;"></div></div></div>
<div class="cmp-vals" id="rsVals"></div>
{_RS_OVERLAY_JS.replace("__CDN__", _LWC_CDN).replace("__SERIES__", rs_overlay_json)}
{_STOCK_CMP_PICKER_JS.replace("__ITEMS__", cmp_items_json).replace("__MAX__", str(_COMPARE_MAX)).replace("__SYM__", json.dumps(sym)).replace("__CUR__", json.dumps([n for _, n in ov_present]))}
"""

    chart_css = """
.rangebar { display:flex; gap:6px; margin:8px 0 4px; }
.rangebar button { background:#21262d; color:#c9d1d9; border:1px solid #30363d;
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
.cmp-anchor { font-size:12px; color:#8b949e; margin:6px 4px 2px; }
.cmp-vals { display:flex; gap:14px; flex-wrap:wrap; font-size:12px; font-variant-numeric:tabular-nums; padding:8px 4px 2px; }
.cmp-val { font-weight:600; }
.cmp-rail { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin:6px 0 8px; }
.cmp-chip { display:inline-flex; align-items:center; gap:6px; background:#161b22; border:1px solid #30363d; border-radius:14px; padding:5px 8px 5px 9px; font-size:13px; }
.cmp-chip.cmp-dim { opacity:.4; }
.cmp-sw { width:10px; height:10px; border-radius:50%; display:inline-block; }
.cmp-tag { font-size:9px; font-weight:700; color:#8b949e; background:#21262d; border-radius:4px; padding:1px 4px; letter-spacing:.4px; }
.cmp-x { color:#8b949e; text-decoration:none; font-size:12px; margin-left:1px; }
.cmp-x:hover { color:#f85149; }
button.cmp-sugg { cursor:pointer; font-family:inherit; }
.cmp-sugg.cmp-on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
"""

    cpr_html = _cpr_stock_panel(cpr_by_tf)   # CPR Structure panel (D53)

    # D54 — Track capture: build a frozen-snapshot preview for the action loop.
    _ix = _xpower(L)
    _kg = L.get("gap_to_key_p3m")
    _snap = {
        "date": L["trade_date"], "close": today_close,
        "conv": round(_conv_of(L.get("p_score"), L.get("rs_rank"))),
        "p": L.get("p_score"), "r": L.get("r_score"),
        "rank": L.get("trigger_rank"), "rs": L.get("rs_rank"),
        "xpow": round(_ix, 2) if _ix else None,
        "keygap": round(_kg, 1) if _kg is not None else None,
        "pt14": round(pscore["ns_base"]) if (pscore and pscore["ns_base"] is not None) else None,
        "tier": pscore["tier"] if pscore else None,
        "char": L.get("accum_character"),
    }
    if track:
        track_html = _TRACK_CSS + _capture_form(sym, _snap)
    else:
        track_html = (_TRACK_CSS + f'<a class="tbtn tbtn-go" href="/dash/stock?sym={_q(sym)}'
                      '&amp;track=1#track" style="text-decoration:none;display:inline-block;'
                      'margin:2px 0 12px">+ Track this stock</a>')

    body = f"""{search}
<style>{chart_css}</style>
<h2>{_esc(sym)} <span class="pill p-{rank}">{rank}</span> {ath}</h2>
<div class="sub">{L['trade_date']} · close ₹{_num(today_close,2)} · deliv {_num(L.get('deliv_per'),1)}%</div>
{track_html}
<div class="kpi">
  <div class="box"><div class="num">{L.get('r_score') or 0}/{L.get('p_score') or 0}</div><div class="lbl">r / p score</div></div>
  <div class="box"><div class="num">{int(L['delivery_value_per_trade'] or 0):,}</div><div class="lbl">DVPT today</div></div>
  <div class="box"><div class="num">{_num(L.get('ratio_today_vs_power_1m'))}</div><div class="lbl">vs power 1m</div></div>
</div>

{insight_html}
{inertia_html}
{character_html}

<div class="fbar" id="ivBar">
  <button class="fbtn on" data-ptf="d">Daily</button>
  <button class="fbtn" data-ptf="w">Weekly</button>
  <button class="fbtn" data-ptf="m">Monthly</button>
  <button class="fbtn" data-ptf="q">Quarterly</button>
</div>
<div class="rangebar">
  <button data-r="63">3M</button>
  <button data-r="126">6M</button>
  <button data-r="252">1Y</button>
  <button data-r="504">2Y</button>
  <button data-r="0" class="on">Max</button>
</div>
<div class="chartwrap">
  <div class="chartlbl">Price + institutional zones (split/bonus-adjusted){'  ⚠ recent corporate action — zone overlay approximate' if zone_action_recent else ''}</div>
  <div id="priceRdt" style="font-size:12px;color:#c9d1d9;font-variant-numeric:tabular-nums;min-height:16px;margin:2px 0 3px;"></div>
  <div id="priceChart" style="height:300px;"></div>
</div>
<div class="chartwrap">
  <div class="chartlbl">DVPT per trade — institutional spikes (amber = institutional-intensity day, r1m &gt; 1)</div>
  <div id="dvptChart" style="height:150px;"></div>
</div>
<div class="chartwrap">
  <div class="chartlbl">Delivery %</div>
  <div id="delivChart" style="height:120px;"></div>
</div>
<div class="chartwrap">
  <div class="chartlbl">Traded value (bar) + delivery value (bright = took delivery)</div>
  <div id="tvChart" style="height:130px;"></div>
</div>

{rs_overlay_html}

{zones_html}

{keyprice_html}

{pt14_html}

{rs_html}

{cpr_html}

<script src="{_LWC_CDN}"></script>
<script>
const DATA = {data_json};
(function(){{
  if (!window.LightweightCharts) {{ document.getElementById('priceChart').innerHTML='<div style=\\"color:#8b949e;padding:20px\\">Chart library failed to load (offline?).</div>'; return; }}
  const S = DATA.series;
  const common = {{
    layout: {{ background:{{color:'#161b22'}}, textColor:'#8b949e', fontSize:11 }},
    grid: {{ vertLines:{{color:'#21262d'}}, horzLines:{{color:'#21262d'}} }},
    timeScale: {{ borderColor:'#30363d', rightOffset:3 }},
    rightPriceScale: {{ borderColor:'#30363d' }},
    crosshair: {{ mode: 0 }},
    handleScroll:true, handleScale:true,
  }};
  const pEl=document.getElementById('priceChart');
  const vEl=document.getElementById('dvptChart');
  const dEl=document.getElementById('delivChart');
  const tEl=document.getElementById('tvChart');
  const pc=LightweightCharts.createChart(pEl, Object.assign({{height:300}}, common));
  const vc=LightweightCharts.createChart(vEl, Object.assign({{height:150}}, common));
  const dc=LightweightCharts.createChart(dEl, Object.assign({{height:120}}, common));
  const tc=LightweightCharts.createChart(tEl, Object.assign({{height:130}}, common));

  const candle=pc.addCandlestickSeries({{upColor:'#3fb950',downColor:'#f85149',wickUpColor:'#3fb950',wickDownColor:'#f85149',borderVisible:false}});
  candle.setData(S.map(d=>({{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close}})));
  DATA.zones.forEach(z=>{{ candle.createPriceLine({{price:z.price,color:z.color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:z.label}}); }});

  const dvpt=vc.addHistogramSeries({{priceFormat:{{type:'volume'}}}});
  dvpt.setData(S.map(d=>({{time:d.time,value:d.dvpt,color:(d.r1m!=null&&d.r1m>1)?'#d29922':'#30506b'}})));

  const deliv=dc.addLineSeries({{color:'#58a6ff',lineWidth:2}});
  deliv.setData(S.filter(d=>d.deliv!=null).map(d=>({{time:d.time,value:d.deliv}})));

  // 4th pane — total traded value (muted full bar) with delivery value drawn
  // ON TOP in a brighter colour. Since delivery ₹ ≤ turnover ₹, the bright bar
  // sits WITHIN the muted bar (both start at 0, overlaid not stacked-additive),
  // so the bright fraction = the delivered share of the day's turnover.
  // Option A — robust y-cap so a rare institutional spike (100-800x a normal
  // day) can't crush every normal day to a sliver. Cap the axis at ~the 98th
  // percentile of traded value; spike days clip at the top + get an amber ▲
  // marker (exact value still on hover). Uniform stocks: cap ~= max, no clip.
  const _tv=S.map(d=>d.tval).filter(v=>v!=null&&v>0).sort((a,b)=>a-b);
  let tvCap=_tv.length?_tv[Math.min(_tv.length-1,Math.floor(_tv.length*0.98))]:0;
  const _cap=()=>({{priceRange:{{minValue:0,maxValue:tvCap||1}}}});
  const tval=tc.addHistogramSeries({{priceFormat:{{type:'volume'}},color:'#30363d',autoscaleInfoProvider:_cap}});
  tval.setData(S.filter(d=>d.tval!=null).map(d=>({{time:d.time,value:d.tval}})));
  const dval=tc.addHistogramSeries({{priceFormat:{{type:'volume'}},color:'#2ea043',autoscaleInfoProvider:_cap}});
  dval.setData(S.filter(d=>d.dval!=null).map(d=>({{time:d.time,value:d.dval}})));
  if(tvCap>0){{
    const _mk=S.filter(d=>d.tval!=null&&d.tval>tvCap).map(d=>({{time:d.time,position:'aboveBar',color:'#d29922',shape:'arrowUp'}}));
    if(_mk.length) tval.setMarkers(_mk);
  }}

  // Sync time scales across the four charts. A reentrancy guard stops a
  // range click from ping-ponging range updates pc<->vc<->dc<->tc until float
  // convergence (the source of the range-switch slowness, worst on Max).
  const charts=[pc,vc,dc,tc];
  let syncing=false;
  charts.forEach(src=>{{
    src.timeScale().subscribeVisibleLogicalRangeChange(r=>{{
      if(!r||syncing) return;
      syncing=true;
      charts.forEach(t=>{{ if(t!==src) t.timeScale().setVisibleLogicalRange(r); }});
      syncing=false;
    }});
  }});

  // Apply the range to ALL charts directly under the guard (N direct
  // view-sets, zero feedback hops). fitContent() per-chart for Max.
  function setRange(n){{
    syncing=true;
    if(!n||n>=S.length){{
      charts.forEach(c=>c.timeScale().fitContent());
    }} else {{
      const from=S[S.length-n].time, to=S[S.length-1].time;
      charts.forEach(c=>c.timeScale().setVisibleRange({{from,to}}));
    }}
    syncing=false;
  }}
  document.querySelectorAll('.rangebar button').forEach(b=>{{
    b.onclick=()=>{{ document.querySelectorAll('.rangebar button').forEach(x=>x.classList.remove('on')); b.classList.add('on'); setRange(parseInt(b.dataset.r)); }};
  }});
  setRange(0);

  // --- D/W/M/Q interval toggle (resample ALL 4 panes together so they stay
  // synced; client-side, no MTF dependency). Candle = OHLC; DVPT pane = the
  // period's PEAK day (NOT an average — true period DVPT is the MTF engine's
  // job, doctrine D43-B); delivery % = period mean; traded/delivery value =
  // period sum (the y-cap recomputes per interval). Zone lines are horizontal,
  // so they're untouched by the interval.
  function isoWeekKey(s){{ const d=new Date(s+'T00:00:00Z'); const jd=(d.getUTCDay()+6)%7;
    d.setUTCDate(d.getUTCDate()-jd+3); const iy=d.getUTCFullYear();
    const j4=new Date(Date.UTC(iy,0,4)); const j4d=(j4.getUTCDay()+6)%7;
    j4.setUTCDate(j4.getUTCDate()-j4d+3); const wk=1+Math.round((d-j4)/(7*86400000));
    return iy+'-W'+('0'+wk).slice(-2); }}
  function pkey(s,tf){{ if(tf==='w') return isoWeekKey(s); if(tf==='m') return s.slice(0,7);
    if(tf==='q'){{ const y=s.slice(0,4),mo=parseInt(s.slice(5,7),10); return y+'-Q'+(Math.floor((mo-1)/3)+1); }}
    return s; }}
  function resampleBars(tf){{
    const mk=d=>({{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close,dvpt:(d.dvpt||0),
      hot:(d.r1m!=null&&d.r1m>1),delivSum:(d.deliv!=null?d.deliv:0),delivN:(d.deliv!=null?1:0),
      tval:(d.tval||0),dval:(d.dval||0)}});
    if(tf==='d') return S.map(mk);
    const out=[]; let k=null,c=null;
    for(const d of S){{ const kk=pkey(d.time,tf);
      if(kk!==k){{ if(c) out.push(c); k=kk; c=mk(d); }}
      else {{ c.high=Math.max(c.high,d.high); c.low=Math.min(c.low,d.low); c.close=d.close; c.time=d.time;
        if((d.dvpt||0)>c.dvpt) c.dvpt=d.dvpt||0; if(d.r1m!=null&&d.r1m>1) c.hot=true;
        if(d.deliv!=null){{ c.delivSum+=d.deliv; c.delivN++; }}
        c.tval+=(d.tval||0); c.dval+=(d.dval||0); }}
    }}
    if(c) out.push(c);
    return out;
  }}
  function setIv(tf){{
    const R=resampleBars(tf);
    syncing=true;
    candle.setData(R.map(d=>({{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close}})));
    dvpt.setData(R.map(d=>({{time:d.time,value:d.dvpt,color:d.hot?'#d29922':'#30506b'}})));
    deliv.setData(R.filter(d=>d.delivN>0).map(d=>({{time:d.time,value:d.delivSum/d.delivN}})));
    const tv=R.map(d=>d.tval).filter(v=>v!=null&&v>0).sort((a,b)=>a-b);
    tvCap=tv.length?tv[Math.min(tv.length-1,Math.floor(tv.length*0.98))]:0;
    tval.setData(R.filter(d=>d.tval!=null).map(d=>({{time:d.time,value:d.tval}})));
    dval.setData(R.filter(d=>d.dval!=null).map(d=>({{time:d.time,value:d.dval}})));
    tval.setMarkers(tvCap>0?R.filter(d=>d.tval!=null&&d.tval>tvCap).map(d=>({{time:d.time,position:'aboveBar',color:'#d29922',shape:'arrowUp'}})):[]);
    syncing=false;
  }}
  document.querySelectorAll('[data-ptf]').forEach(b=>{{
    b.onclick=()=>{{ document.querySelectorAll('[data-ptf]').forEach(x=>x.classList.toggle('on', x===b));
      setIv(b.dataset.ptf);
      const rb=document.querySelector('.rangebar button.on'); setRange(rb?parseInt(rb.dataset.r):0); }};
  }});

  // Debounced ResizeObserver: coalesce bursts (~100ms) and skip while syncing.
  let rzT=null;
  new ResizeObserver(()=>{{
    if(syncing) return;
    if(rzT) clearTimeout(rzT);
    rzT=setTimeout(()=>{{ charts.forEach(c=>c.applyOptions({{}})); }},100);
  }}).observe(pEl);

  // Crosshair value readout — hover ANY of the 4 panes to see that day's
  // OHLC + DVPT + delivery + traded/delivery value; latest day when off-chart.
  const rdt=document.getElementById('priceRdt');
  function tkey(t){{ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }}
  const byT={{}}; S.forEach(d=>byT[d.time]=d);
  function cr(v){{ return '₹'+Math.round(v).toLocaleString('en-IN'); }}
  function showR(d){{
    if(!d){{ rdt.innerHTML=''; return; }}
    let h='<b>'+d.time+'</b>&nbsp; O '+d.open+'&nbsp; H '+d.high+'&nbsp; L '+d.low
      +'&nbsp; <b>C '+d.close+'</b>'
      +(d.dvpt!=null?'&nbsp; · DVPT ₹'+Math.round(d.dvpt).toLocaleString('en-IN'):'')
      +(d.deliv!=null?'&nbsp; · Deliv '+d.deliv.toFixed(1)+'%':'');
    if(d.tval!=null){{
      h+='&nbsp; · Traded '+cr(d.tval);
      if(d.dval!=null) h+=' / Deliv '+cr(d.dval)
        +(d.tval>0?' ('+(d.dval/d.tval*100).toFixed(0)+'%)':'');
    }}
    rdt.innerHTML=h;
  }}
  [pc,vc,dc,tc].forEach(c=>c.subscribeCrosshairMove(p=>{{
    if(!p||!p.time){{ showR(S[S.length-1]); return; }}
    showR(byT[tkey(p.time)]||S[S.length-1]);
  }}));
  showR(S[S.length-1]);
}})();
</script>
"""
    return HTMLResponse(_shell(f"{sym} · patearn", body, "stock", L["trade_date"]))


# Ratio chart JS (plain template — no f-string; __DATA__ is replaced with the
# server JSON). Clones the stock page's lightweight-charts v4 approach: line
# series + client-side range buttons + markers + ResizeObserver.
_RATIO_CHART_JS = """
<script src="__CDN__"></script>
<script>
const DATA = __DATA__;
(function(){
  const host = document.getElementById('ratioChart');
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:#8b949e;padding:20px">Chart library failed to load (offline?).</div>'; return; }
  const D = DATA;
  const common = {
    layout: { background:{color:'#161b22'}, textColor:'#8b949e', fontSize:11 },
    grid: { vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'} },
    timeScale: { borderColor:'#30363d', rightOffset:3 },
    rightPriceScale: { borderColor:'#30363d' },
    crosshair: { mode: 0 },
    handleScroll:true, handleScale:true,
  };
  const chart = LightweightCharts.createChart(host, Object.assign({height:300}, common));
  const ratioLine = chart.addLineSeries({color:'#1f6feb',lineWidth:2,priceLineVisible:false});
  const ma50Line  = chart.addLineSeries({color:'#d29922',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  const ma200Line = chart.addLineSeries({color:'#6e7681',lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  ratioLine.setData(D.map(d=>({time:d.t,value:d.ratio})));
  ma50Line.setData(D.filter(d=>d.ma50!=null).map(d=>({time:d.t,value:d.ma50})));
  ma200Line.setData(D.filter(d=>d.ma200!=null).map(d=>({time:d.t,value:d.ma200})));

  // Markers: server up-cross (cross_50_today) + new-52w-high; client down-cross.
  const mk=[];
  for (let i=0;i<D.length;i++){
    const d=D[i];
    if (d.cross50) mk.push({time:d.t,position:'belowBar',color:'#3fb950',shape:'arrowUp',text:'↑50'});
    if (d.nh52)    mk.push({time:d.t,position:'aboveBar',color:'#3fb950',shape:'circle'});
    if (i>0){
      const p=D[i-1];
      if (d.ma50!=null && p.ma50!=null && d.ratio<d.ma50 && p.ratio>=p.ma50)
        mk.push({time:d.t,position:'aboveBar',color:'#f85149',shape:'arrowDown',text:'↓50'});
    }
  }
  mk.sort((a,b)=> a.time<b.time?-1:(a.time>b.time?1:0));
  ratioLine.setMarkers(mk);

  function setRange(n){
    if(!n||n>=D.length){ chart.timeScale().fitContent(); return; }
    const from=D[D.length-n].t, to=D[D.length-1].t;
    chart.timeScale().setVisibleRange({from,to});
  }
  document.querySelectorAll('.rangebar button').forEach(b=>{
    b.onclick=()=>{ document.querySelectorAll('.rangebar button').forEach(x=>x.classList.remove('on')); b.classList.add('on'); setRange(parseInt(b.dataset.r)); };
  });
  setRange(252);
  document.querySelectorAll('.rangebar button').forEach(x=>x.classList.remove('on'));
  const oneY=document.querySelector('.rangebar button[data-r="252"]'); if(oneY) oneY.classList.add('on');
  // Debounced ResizeObserver (~100ms) — avoid a redraw per resize tick.
  let rzT=null;
  new ResizeObserver(()=>{ if(rzT) clearTimeout(rzT); rzT=setTimeout(()=>{ chart.applyOptions({}); },100); }).observe(host);

  // Crosshair value readout — hover to see the ratio + its 50/200-MA at the
  // cursor; shows the latest when the cursor is off-chart.
  const rdt=document.getElementById('ratioRdt');
  function tkey(t){ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }
  function f4(v){ return v!=null?v.toFixed(4):'—'; }
  function showR(p){
    let t,r,m50,m200;
    if(p&&p.time&&p.seriesData){
      t=tkey(p.time);
      const a=p.seriesData.get(ratioLine); r=a?a.value:null;
      const b=p.seriesData.get(ma50Line);  m50=b?b.value:null;
      const c=p.seriesData.get(ma200Line); m200=c?c.value:null;
    } else {
      const last=D[D.length-1]; t=last.t; r=last.ratio; m50=last.ma50; m200=last.ma200;
    }
    rdt.innerHTML='<b>'+t+'</b>&nbsp; ratio <b>'+f4(r)+'</b>&nbsp; · 50-MA '+f4(m50)+'&nbsp; · 200-MA '+f4(m200);
  }
  chart.subscribeCrosshairMove(showR);
  showR(null);
})();
</script>
"""


@router.get("/dash/ratio", response_class=HTMLResponse)
def dash_ratio(idx: str = Query("", max_length=60),
               den: str = Query("Nifty 500", max_length=60)) -> HTMLResponse:
    idx = idx.strip()
    den = den.strip()
    if den not in ("Nifty 50", "Nifty 500"):
        den = "Nifty 500"
    _, idx_date = _latest_dates()

    if not idx:
        body = '<div class="empty">No index selected. Reach this page from a Markets or Sectors RS cell.</div>'
        return HTMLResponse(_shell("Ratio · patearn", body, "sectors", idx_date or ""))

    with get_conn() as conn:
        known = conn.execute(
            "SELECT 1 FROM index_rows WHERE index_name=? LIMIT 1", (idx,)).fetchone()
        if not known:
            body = f'<div class="empty">Unknown index <b>{_esc(idx)}</b>.</div>'
            return HTMLResponse(_shell("Ratio · patearn", body, "sectors", idx_date or ""))

        curve = conn.execute(
            """SELECT r.trade_date, r.ratio, s.ratio_ma_50, s.ratio_ma_200,
                      s.cross_50_today, s.new_52w_high
               FROM ratio_rows r
               LEFT JOIN ratio_signals s
                 ON s.numerator=r.numerator AND s.denominator=r.denominator
                    AND s.trade_date=r.trade_date
               WHERE r.numerator=? AND r.denominator=?
               ORDER BY r.trade_date ASC""",
            (idx, den),
        ).fetchall()
        if not curve:
            body = (f'<h2>{_esc(idx)} <span class="sub" style="margin:0">vs {_esc(den)}</span></h2>'
                    '<div class="empty">No ratio series (this is a broad/size index, not a sector).</div>')
            return HTMLResponse(_shell(f"{idx} ratio · patearn", body, "sectors", idx_date or ""))

        sig = conn.execute(
            """SELECT rs_vs_broad_trend_state st, ret_3m_pct r3,
                      ret_1d_pct r1d, ret_1w_pct r1w, ret_1m_pct r1m,
                      ret_6m_pct r6, ret_12m_pct r12,
                      pct_above_50d_avg pa50, pct_above_200d_avg pa200,
                      pct_off_52w_high off52h, pct_above_52w_low abv52l,
                      close_value iclose,
                      rs_vs_broad_today rs, rs_vs_broad_slope_1m s1,
                      rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6,
                      rs_vs_broad_slope_12m s12, rs_vs_broad_above_50ma a50,
                      rs_vs_broad_above_200ma a200, rs_vs_broad_new_52w_high nh
               FROM index_signals
               WHERE index_name=? ORDER BY trade_date DESC LIMIT 1""",
            (idx,),
        ).fetchone()
        S = dict(sig) if sig else {}

        # D49 — the index's OWN today snapshot (OHLC / valuation / volume), so the
        # index page shows "today's movement", not just the RS picture.
        irow = conn.execute(
            """SELECT open_value o, high_value h, low_value l, close_value close,
                      points_change pts, change_pct chg, volume vol,
                      turnover_cr tov, pe, pb, dividend_yield dy, trade_date td
               FROM index_rows WHERE index_name=? ORDER BY trade_date DESC LIMIT 1""",
            (idx,),
        ).fetchone()
        IR = dict(irow) if irow else {}

        # Cross-sector RS-momentum percentile (on-read).
        momrows = conn.execute(
            """WITH latest AS (SELECT MAX(trade_date) d FROM index_signals)
               SELECT index_name,
                      (0.6*COALESCE(rs_vs_broad_slope_3m,0)
                       +0.4*COALESCE(rs_vs_broad_slope_6m,0)) mom
               FROM index_signals, latest
               WHERE trade_date=latest.d AND broad_benchmark IS NOT NULL""",
        ).fetchall()

        # Top constituents by DVPT trigger.
        syms = _sector_symbols(conn, idx)
        consts = []
        if syms:
            sig_date2 = conn.execute(
                "SELECT MAX(trade_date) d FROM stock_signals").fetchone()
            sd = sig_date2["d"] if sig_date2 else None
            if sd:
                ph = ",".join("?" for _ in syms)
                consts = [dict(x) for x in conn.execute(
                    f"""SELECT s.symbol, s.trigger_rank rank, s.is_ath_dvpt ath,
                              s.p_score, s.r_score, s.price_vs_hot_avg_pct pvh,
                              s.rs_rank, s.accum_price_drift_3m drift3m,
                              b.close cmp, b.prev_close pc
                       FROM stock_signals s
                       JOIN bhavcopy_rows b
                         ON b.symbol=s.symbol AND b.trade_date=s.trade_date
                            AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
                       WHERE s.trade_date=? AND s.symbol IN ({ph})
                       ORDER BY COALESCE(s.is_ath_dvpt,0) DESC,
                                COALESCE(s.p_score,-1) DESC, COALESCE(s.r_score,-1) DESC
                       LIMIT 100""",
                    (sd, *syms),
                ).fetchall()]

    # --- Chart data (oldest→newest) ---
    cd = []
    for r in curve:
        cd.append({
            "t": r["trade_date"],
            "ratio": round(r["ratio"], 4) if r["ratio"] is not None else None,
            "ma50": round(r["ratio_ma_50"], 4) if r["ratio_ma_50"] is not None else None,
            "ma200": round(r["ratio_ma_200"], 4) if r["ratio_ma_200"] is not None else None,
            "cross50": 1 if r["cross_50_today"] else 0,
            "nh52": 1 if r["new_52w_high"] else 0,
        })
    data_json = json.dumps(cd)
    chart_js = (_RATIO_CHART_JS
                .replace("__CDN__", _LWC_CDN)
                .replace("__DATA__", data_json))

    st = S.get("st") or "—"
    strip = _rs_strip(S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12"))
    s1, s3, s6, s12 = S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12")
    r3 = S.get("r3")

    # --- RS-momentum percentile gauge ---
    my_mom = 0.6 * (s3 or 0) + 0.4 * (s6 or 0)
    moms = sorted(m["mom"] for m in momrows)
    n_mom = len(moms)
    pctl = 50
    if n_mom:
        below = sum(1 for m in moms if m < my_mom)
        pctl = max(1, min(99, round(below / n_mom * 99)))
    gauge_html = (
        '<h2>RS momentum</h2>'
        f'<div class="sub">{pctl}/99 — stronger than {pctl}% of sectors '
        f'(0.6·3m + 0.4·6m RS slope, ranked across {n_mom} sectors).</div>'
        f'<div class="card"><div class="bar"><span style="width:{pctl}%"></span></div></div>')

    # --- Absolute × Relative quadrant SVG ---
    # X = ret_3m_pct (abs), Y = rs_vs_broad_slope_3m (rel). Center origin; clamp.
    def _clamp(v, lo, hi):
        return lo if v < lo else (hi if v > hi else v)
    xv = r3 if r3 is not None else 0.0
    yv = s3 if s3 is not None else 0.0
    # Map ±15% to the half-width (75 px). Clamp dot inside the 10..170 box.
    px = _clamp(90 + (xv / 15.0) * 75.0, 12, 168)
    py = _clamp(90 - (yv / 15.0) * 75.0, 12, 168)
    quad_html = (
        '<h2>Absolute × Relative</h2>'
        '<div class="sub">X = 3m return (abs) · Y = 3m RS slope (vs Nifty 500). '
        'Top-right = leader; top-left = defensive; bottom-right = lazy laggard.</div>'
        '<div class="card" style="text-align:center">'
        f'<svg viewBox="0 0 180 180" width="180" height="180" '
        'style="max-width:100%" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="10" y="10" width="160" height="160" rx="6" fill="#0d1117" stroke="#30363d"/>'
        '<line x1="90" y1="10" x2="90" y2="170" stroke="#30363d" stroke-width="1"/>'
        '<line x1="10" y1="90" x2="170" y2="90" stroke="#30363d" stroke-width="1"/>'
        '<text x="160" y="24" fill="#484f58" font-size="7" text-anchor="end">LEADER</text>'
        '<text x="20" y="24" fill="#484f58" font-size="7">DEFENSIVE</text>'
        '<text x="160" y="164" fill="#484f58" font-size="7" text-anchor="end">LAZY LAGGARD</text>'
        '<text x="20" y="164" fill="#484f58" font-size="7">LAGGARD</text>'
        '<text x="172" y="93" fill="#6e7681" font-size="6" text-anchor="end">ret→</text>'
        '<text x="93" y="16" fill="#6e7681" font-size="6">RS↑</text>'
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#1f6feb" stroke="#79c0ff" stroke-width="1.5"/>'
        '</svg></div>')

    # --- Auto READ block (deterministic strings, no LLM) ---
    reads = []
    if S.get("a200"):
        reads.append("RS above its 200-day reference → structurally leading the broad market.")
    else:
        reads.append("RS below its 200-day reference → not yet structurally leading.")
    if cd and cd[-1]["cross50"]:
        reads.append("RS just crossed <b>above</b> its 50-day line → starting to outperform.")
    elif S.get("a50"):
        reads.append("RS holds above its 50-day line → near-term outperformance intact.")
    else:
        reads.append("RS below its 50-day line → near-term lagging the broad market.")
    if S.get("nh"):
        reads.append("New 52-week RS high → strongest relative position in a year.")

    def _dir(v):
        if v is None:
            return None
        return "rising" if v > 1 else ("falling" if v < -1 else "flat")
    d1, d3, d6, d12 = _dir(s1), _dir(s3), _dir(s6), _dir(s12)
    ups = sum(1 for d in (d1, d3, d6, d12) if d == "rising")
    dns = sum(1 for d in (d1, d3, d6, d12) if d == "falling")
    if d1 == "rising" and d12 in ("falling", "flat") and ups >= 2:
        reads.append("Short horizons rising while 12m lags → an <b>improving</b> rotation (laggard turning up).")
    elif d12 == "rising" and d1 in ("falling", "flat") and dns >= 2:
        reads.append("Long horizon up but short horizons rolling over → a <b>deteriorating</b> leader (trim).")
    elif ups == 4:
        reads.append("1m/3m/6m/12m RS all rising → a <b>persistent leader</b> across every horizon.")
    elif dns == 4:
        reads.append("1m/3m/6m/12m RS all falling → a <b>persistent laggard</b> across every horizon.")
    elif d1 == "rising" and d3 == "rising" and d6 == "rising" and d12 == "flat":
        reads.append("1m/3m/6m RS rising, 12m flat → a <b>maturing</b> rotation.")
    reads = reads[:4]
    read_items = "".join(f"<li>{x}</li>" for x in reads)
    read_html = (
        '<div class="card" style="border-color:#1f6feb">'
        '<div class="sub" style="margin:0 0 6px;color:#58a6ff">📌 READ — relative strength</div>'
        f'<ul style="margin:0;padding-left:18px;line-height:1.55">{read_items}</ul></div>')

    # --- Cross-flag pills ---
    pills = []
    pills.append('<span class="pill p-UPTREND">above 50-MA</span>' if S.get("a50")
                 else '<span class="pill p-DOWNTREND">below 50-MA</span>')
    pills.append('<span class="pill p-UPTREND">above 200-MA</span>' if S.get("a200")
                 else '<span class="pill p-DOWNTREND">below 200-MA</span>')
    if S.get("nh"):
        pills.append('<span class="pill p-BREAKOUT">new 52w RS high</span>')
    pill_row = '<div class="chips" style="margin-bottom:10px">' + "".join(pills) + '</div>'

    # --- Constituents table (D49: DVPT trigger + RS vs THIS index + today) ---
    if syms:
        idx_r3 = S.get("r3")
        crows = []
        for c in consts:
            rk = c["rank"] or "-"
            ath = "⚡" if c["ath"] else ""
            pvh = c["pvh"]
            entry = ("🟢" if pvh < -3 else ("🔴" if pvh > 3 else "🟡")) if pvh is not None else ""
            cmp_v, pc = c.get("cmp"), c.get("pc")
            dchg = ((cmp_v / pc - 1) * 100) if (cmp_v and pc) else None
            rr = c.get("rs_rank")
            drift = c.get("drift3m")
            # outperformance vs THIS index = stock 3m return − index 3m return
            excess = (drift - idx_r3) if (drift is not None and idx_r3 is not None) else None
            crows.append(
                f'<tr><td><a class="row" href="/dash/stock?sym={_esc(c["symbol"])}">'
                f'<span class="sym">{ath}{_esc(c["symbol"])}</span></a></td>'
                f'<td><span class="pill p-{rk}">{rk}</span></td>'
                f'<td class="mut">{c["r_score"] or 0}/{c["p_score"] or 0}</td>'
                f'<td>{_pct(pvh)} {entry}</td>'
                f'<td>{_num(cmp_v, 1) if cmp_v is not None else "—"}</td>'
                f'<td>{_pct(dchg)}</td>'
                f'<td>{rr if rr is not None else "—"}</td>'
                f'<td>{_pct(drift)}</td>'
                f'<td>{_pct(excess)}</td></tr>')
        if crows:
            consts_html = (
                '<h2>Constituents <span class="sub" style="margin:0">'
                'DVPT trigger + RS vs this index</span></h2>'
                '<div class="sub">Sorted by DVPT trigger — click any header to re-sort, type to filter, ⬇ export. '
                f'<b>vs idx</b> = the stock\'s 3m return minus {_esc(idx)}\'s 3m return '
                '(positive = outperforming the index). <b>RS rank</b> = 1–99 market strength.</div>'
                '<div class="card" style="padding:6px 10px;overflow-x:auto">'
                '<table class="dt" style="min-width:640px">'
                '<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>Δhot</th>'
                '<th>CMP</th><th>Δday</th><th>RS rank</th><th>3m</th><th>vs idx</th></tr></thead>'
                f'<tbody>{"".join(crows)}</tbody></table></div>')
        else:
            consts_html = ('<h2>Constituents</h2>'
                           '<div class="card"><div class="sub" style="margin:0">'
                           'No stock signals for the constituents on the latest day.</div></div>')
    else:
        consts_html = ('<h2>Constituents</h2>'
                       '<div class="card"><div class="sub" style="margin:0">'
                       'No membership on record for this index.</div></div>')

    # --- D49 index one-stop snapshot (today close / OHLC / valuation / returns) ---
    snapshot_html = ""
    if S or IR:
        iclose = IR.get("close")
        if iclose is None:
            iclose = S.get("iclose")

        def _v(x, d=2, suf=""):
            return f"{x:,.{d}f}{suf}" if x is not None else "—"

        pts = IR.get("pts")
        trend_pill = (f'<span class="pill p-{st}">{st[:5]}</span>'
                      if (st and st != "—") else "—")
        kpi = (
            '<div class="kpi">'
            f'<div class="box"><div class="num">{_v(iclose, 2)}</div>'
            f'<div class="lbl">close{(" " + ("%+.0f" % pts)) if pts is not None else ""}</div></div>'
            f'<div class="box"><div class="num">{_pct(IR.get("chg"))}</div><div class="lbl">today</div></div>'
            f'<div class="box"><div class="num" style="font-size:16px;padding-top:8px">'
            f'{_pct(S.get("r1m"))}</div><div class="lbl">1m return</div></div></div>')
        stats = (
            '<div class="card" style="padding:6px 10px"><table><tbody>'
            f'<tr><td class="mut">Open</td><td>{_v(IR.get("o"), 2)}</td>'
            f'<td class="mut">High</td><td>{_v(IR.get("h"), 2)}</td>'
            f'<td class="mut">Low</td><td>{_v(IR.get("l"), 2)}</td></tr>'
            f'<tr><td class="mut">Volume</td><td>{_v(IR.get("vol"), 0)}</td>'
            f'<td class="mut">Turnover</td><td>{("₹" + _v(IR.get("tov"), 0) + " Cr") if IR.get("tov") is not None else "—"}</td>'
            f'<td class="mut">Div yld</td><td>{_v(IR.get("dy"), 2, "%")}</td></tr>'
            f'<tr><td class="mut">P/E</td><td>{_v(IR.get("pe"), 2)}</td>'
            f'<td class="mut">P/B</td><td>{_v(IR.get("pb"), 2)}</td>'
            f'<td class="mut">Trend</td><td>{trend_pill}</td></tr>'
            '</tbody></table></div>')
        rets = " · ".join(
            f'{lbl} {_pct(S.get(k))}' for lbl, k in
            (("1d", "r1d"), ("1w", "r1w"), ("1m", "r1m"),
             ("3m", "r3"), ("6m", "r6"), ("12m", "r12")))
        techs = (f'{_pct(S.get("pa50"))} vs 50-DMA · {_pct(S.get("pa200"))} vs 200-DMA · '
                 f'{_pct(S.get("off52h"))} off 52w-high · {_pct(S.get("abv52l"))} above 52w-low')
        snapshot_html = (
            f'<h2>Today <span class="sub" style="margin:0">{_esc(IR.get("td") or "")}</span></h2>'
            + kpi + stats
            + f'<div class="sub" style="margin:6px 0 2px"><b>Returns</b> &nbsp;{rets}</div>'
            + f'<div class="sub" style="margin:0 0 10px"><b>Technicals</b> &nbsp;{techs}</div>')

    chip = f' <span class="pill p-{st}">{st[:5]}</span>' if st and st != "—" else ''
    other = "Nifty 50" if den == "Nifty 500" else "Nifty 500"
    chart_css = """
.rangebar { display:flex; gap:6px; margin:8px 0 4px; }
.rangebar button { background:#21262d; color:#c9d1d9; border:1px solid #30363d;
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
"""
    fbar = (
        '<div class="fbar">'
        f'<a class="fbtn {"on" if den=="Nifty 500" else ""}" '
        f'href="/dash/ratio?idx={_q(idx)}&den={_q("Nifty 500")}">vs Nifty 500</a>'
        f'<a class="fbtn {"on" if den=="Nifty 50" else ""}" '
        f'href="/dash/ratio?idx={_q(idx)}&den={_q("Nifty 50")}">vs Nifty 50</a>'
        f'<a class="fbtn" href="/dash/compare?idx={_q(idx)}'
        f'&idx={_q("Nifty 50")}&idx={_q("Nifty 500")}">Compare ⇄</a></div>')

    body = f"""
<style>{chart_css}</style>
<h2>{_esc(idx)}{chip} <span class="sub" style="margin:0">RS vs {_esc(den)}</span></h2>
<div class="sub" style="margin-bottom:10px">{strip} &nbsp; 3m RS {_pct(s3)} · ret 3m {_pct(r3)}</div>
{snapshot_html}
{fbar}
{read_html}
<div class="rangebar">
  <button data-r="63">3M</button>
  <button data-r="126">6M</button>
  <button data-r="252" class="on">1Y</button>
  <button data-r="0">Max</button>
</div>
<div class="chartwrap">
  <div class="chartlbl">{_esc(idx)} / {_esc(den)} ratio · blue=ratio · amber=50-MA · grey=200-MA · ↑50/↓50 crosses · ● new 52w high</div>
  <div id="ratioRdt" style="font-size:12px;color:#c9d1d9;font-variant-numeric:tabular-nums;min-height:16px;margin:2px 0 3px;"></div>
  <div id="ratioChart" style="height:300px;"></div>
</div>
{pill_row}
{gauge_html}
{quad_html}
{consts_html}
{chart_js}
"""
    return HTMLResponse(_shell(f"{idx} ratio · patearn", body, "sectors",
                               idx_date or ""))


# Multi-index compare chart JS (plain template — no f-string; placeholders are
# replaced with server JSON/config). Clones the ratio bootstrap, then adds:
# N line series, client-side rebase, a fluid forward-snapped anchor on
# subscribeVisibleTimeRangeChange (rAF-coalesced + anchor-gated +
# reentrancy-guarded), mode/base/range/pin controls, and a crosshair value row.
_COMPARE_CHART_JS = """
<script src="__CDN__"></script>
<script>
const SERIES = __SERIES__;
const CMODE0 = "__MODE__";        // 'rebase' | 'ratio'
const CBASE0 = "__BASE__";        // '100' | '0'
const CRANGE0 = __RANGE__;        // initial range in trading days
(function(){
  const host = document.getElementById('compareChart');
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:#8b949e;padding:20px">Chart library failed to load (offline?).</div>'; return; }
  if (!SERIES.length) { return; }
  const common = {
    layout: { background:{color:'#161b22'}, textColor:'#8b949e', fontSize:11 },
    grid: { vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'} },
    timeScale: { borderColor:'#30363d', rightOffset:3 },
    rightPriceScale: { borderColor:'#30363d' },
    crosshair: { mode: 0 },
    handleScroll:true, handleScale:true,
  };
  const chart = LightweightCharts.createChart(host, Object.assign({height:320}, common));

  let mode = (CMODE0==='ratio') ? 'ratio' : 'rebase';
  const base = '100';         // always base-100 (matches the stock RS overlay chart)
  let pinned = null;          // null => fluid; else a 'YYYY-MM-DD' anchor

  // Build a line series per data series; pick its raw array (level or ratio).
  function rawOf(s){ return (mode==='ratio') ? (s.ratio||[]) : (s.level||[]); }
  const lines = SERIES.map(s=>{
    const ls = chart.addLineSeries({color:s.color,lineWidth:2,priceLineVisible:false,lastValueVisible:true,crosshairMarkerVisible:true});
    return {def:s, ls:ls};
  });

  // 'YYYY-MM-DD' string comparison works lexicographically. The time-range
  // callback may hand back either a string or a {year,month,day} business day.
  function timeToStr(t){
    if (t==null) return null;
    if (typeof t === 'string') return t;
    if (typeof t === 'object' && t.year){
      const m=('0'+t.month).slice(-2), d=('0'+t.day).slice(-2);
      return t.year+'-'+m+'-'+d;
    }
    return String(t);
  }
  // First index in raw[] with time >= target (forward snap). raw sorted by time.
  function snapIdx(raw, target){
    if (!raw.length) return -1;
    if (target==null) return 0;
    let lo=0, hi=raw.length-1, ans=-1;
    while(lo<=hi){ const mid=(lo+hi)>>1;
      if (raw[mid].t >= target){ ans=mid; hi=mid-1; } else { lo=mid+1; }
    }
    return ans;
  }

  // Compute the common forward-snapped anchor date for the given left edge,
  // using the union of all series' first-eligible points (earliest snap wins
  // so every line shares ONE anchor day).
  function commonAnchor(from){
    let best=null;
    for (const l of lines){
      const raw=rawOf(l.def); const i=snapIdx(raw, from);
      if (i>=0){ const t=raw[i].t; if (best===null || t<best) best=t; }
    }
    return best;   // a 'YYYY-MM-DD' string or null
  }

  // Rebase every series to the anchor date and push to its line series.
  // base '100' => v/anchor*100 ; base '0' => (v/anchor-1)*100.
  // A series with no/zero value at the anchor drops out (setData([])) and its
  // chip dims. Ratio mode rebases the ratio to 100 too.
  let anchorDate = null;
  function applyRebase(anchor){
    anchorDate = anchor;
    for (const l of lines){
      const raw=rawOf(l.def);
      const chip=document.querySelector('.cmp-chip[data-i="'+l.def.i+'"]');
      let av=null;
      if (anchor!=null){
        const ai=snapIdx(raw, anchor);
        if (ai>=0) av=raw[ai].v;
      } else if (raw.length){ av=raw[0].v; }
      if (av==null || av===0){
        l.ls.setData([]);
        if(chip) chip.classList.add('cmp-dim');
        continue;
      }
      if(chip) chip.classList.remove('cmp-dim');
      const out=new Array(raw.length);
      const off=(base==='0')?1:0; const scl=(base==='0')?100:100;
      for (let k=0;k<raw.length;k++){
        const p=raw[k];
        out[k]={time:p.t, value:(off? ((p.v/av)-1)*scl : (p.v/av)*scl)};
      }
      l.ls.setData(out);
    }
    relabel(anchor);
    requestAnimationFrame(positionNames);
  }

  // --- fluid anchor: recompute on pan, rAF-coalesced + anchor-gated --------
  let raf=null, internalSet=false, lastAnchor=null, userInteracted=false;
  // Fluid re-anchor must respond ONLY to genuine user panning — never to the
  // layout-settling range-change events that fire during the first paint. Those
  // boot events would otherwise override the deterministic left-edge anchor with
  // a transient mid-window date (the "rebased mid-window on load" bug). Mark when
  // the user actually drives the chart so settle-time events stay inert.
  ['wheel','pointerdown','mousedown','touchstart'].forEach(ev=>
    host.addEventListener(ev,()=>{ userInteracted=true; },{passive:true,capture:true}));
  function scheduleRebase(from){
    if (pinned!==null) return;          // pinned anchor ignores panning
    if (internalSet) return;            // our own setData/ setVisibleRange
    if (!userInteracted) return;        // boot/layout settle (no pan) → keep edge anchor
    if (raf) return;
    raf=requestAnimationFrame(()=>{
      raf=null;
      const a=commonAnchor(from);
      if (a===lastAnchor) return;       // left-edge trading day unchanged → free
      lastAnchor=a;
      internalSet=true;
      applyRebase(a);
      internalSet=false;
    });
  }
  chart.timeScale().subscribeVisibleTimeRangeChange(r=>{
    if(!r) return;
    scheduleRebase(timeToStr(r.from));
    requestAnimationFrame(positionNames);
  });

  // --- range buttons (re-anchor fluid to the new left edge) ----------------
  // Union of ALL timestamps across both representations (mode-independent, so
  // range slicing is stable when the user toggles Rebased<->Ratio).
  const allT = (function(){
    const set={};
    for (const s of SERIES){
      for (const p of (s.level||[])) set[p.t]=1;
      for (const p of (s.ratio||[])) set[p.t]=1;
    }
    return Object.keys(set).sort();
  })();
  function setRange(n){
    internalSet=true;
    let edge;                              // the window's KNOWN left-edge date
    if(!n||n>=allT.length){ chart.timeScale().fitContent(); edge=allT.length?allT[0]:null; }
    else {
      edge=allT[allT.length-n]; const to=allT[allT.length-1];
      chart.timeScale().setVisibleRange({from:edge,to});
    }
    internalSet=false;
    if (pinned===null){
      // Anchor to the window's KNOWN left edge (deterministic). getVisibleRange
      // lags a frame on initial layout, which left the first paint rebased
      // mid-window until the user panned. Panning still re-anchors fluidly via
      // subscribeVisibleTimeRangeChange below.
      lastAnchor=commonAnchor(edge);
      internalSet=true; applyRebase(lastAnchor); internalSet=false;
    } else {
      applyRebase(pinned);
    }
  }
  document.querySelectorAll('.rangebar button').forEach(b=>{
    b.onclick=()=>{ document.querySelectorAll('.rangebar button').forEach(x=>x.classList.remove('on')); b.classList.add('on'); setRange(parseInt(b.dataset.r)); };
  });

  // --- live "REBASED FROM" label + pin state -------------------------------
  function relabel(anchor){
    const el=document.getElementById('cmpAnchorLbl');
    if(!el) return;
    const lock = (pinned!==null) ? ' 🔒' : '';
    el.innerHTML = anchor ? ('REBASED FROM <b>'+anchor+'</b>'+lock) : 'REBASED FROM <b>start</b>'+lock;
  }

  // --- mode toggle (swap raw + re-rebase, NO chart re-create) --------------
  document.querySelectorAll('[data-cmode]').forEach(b=>{
    b.onclick=()=>{
      mode = b.dataset.cmode;
      document.querySelectorAll('[data-cmode]').forEach(x=>x.classList.toggle('on', x===b));
      // Ratio mode → show denom switch + base is still meaningful for both.
      const dn=document.getElementById('cmpDenomBar'); if(dn) dn.style.display=(mode==='ratio')?'flex':'none';
      lastAnchor=null;
      const a = (pinned!==null) ? pinned : commonAnchor(curFrom());
      applyRebase(a);
    };
  });
  function curFrom(){
    const vr=chart.timeScale().getVisibleRange();
    return vr ? timeToStr(vr.from) : null;
  }
  // --- pin / reset anchor --------------------------------------------------
  const pinInput=document.getElementById('cmpPin');
  if(pinInput){ pinInput.onchange=()=>{
    const v=pinInput.value;
    if(v){ pinned=v; const a=commonAnchor(v); applyRebase(a||v); }
  }; }
  const resetBtn=document.getElementById('cmpReset');
  if(resetBtn){ resetBtn.onclick=()=>{
    pinned=null; if(pinInput) pinInput.value=''; lastAnchor=null;
    scheduleRebase(curFrom());
    // scheduleRebase is gated; force one immediately too
    const a=commonAnchor(curFrom()); internalSet=true; applyRebase(a); internalSet=false;
  }; }

  // --- crosshair value row -------------------------------------------------
  const valRow=document.getElementById('cmpVals');
  function fmtVal(v){ if(v==null) return '—'; return (base==='0'? (v>=0?'+':'')+v.toFixed(2)+'%' : v.toFixed(1)); }
  function renderVals(map){
    if(!valRow) return;
    const parts=[];
    for(const l of lines){
      let v=null;
      if(map){ const d=map.get(l.ls); if(d&&d.value!=null) v=d.value; }
      else { const dat=l.ls.data(); if(dat&&dat.length) v=dat[dat.length-1].value; }
      parts.push('<span class="cmp-val" style="color:'+l.def.color+'">●'+_e(l.def.name)+' '+fmtVal(v)+'</span>');
    }
    valRow.innerHTML=parts.join('');
  }
  function _e(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  chart.subscribeCrosshairMove(p=>{
    if(!p||!p.time||!p.seriesData){ renderVals(null); return; }
    renderVals(p.seriesData);
  });

  // --- boot ----------------------------------------------------------------
  // Seed data with internalSet ON so setData's auto-fit range change does NOT
  // schedule a stray rebase that could fire after setRange and override the
  // correct anchor (the race that pinned the first paint mid-window).
  internalSet=true; applyRebase(null); internalSet=false;
  setRange(CRANGE0);          // applies the window AND rebases to its known left edge
  renderVals(null);
  // Gutter name labels need the price scale laid out — priceToCoordinate returns
  // null until the first paint settles, so a single boot call renders nothing.
  // Retry across a few frames until every visible line's label is placed.
  (function ensureNames(tries){
    positionNames();
    const cont=document.getElementById('cmpNames');
    const want=lines.filter(l=>{ const d=l.ls.data(); return d&&d.length; }).length;
    if (cont && cont.children.length<want && tries>0)
      requestAnimationFrame(()=>ensureNames(tries-1));
  })(20);

  // Name labels in the right gutter, each aligned to its line's last-value pixel
  // (value badge stays on the axis; the name sits just outside it). Nearby labels
  // are nudged apart so they don't overlap. "Nifty " prefix dropped for brevity.
  function positionNames(){
    const cont=document.getElementById('cmpNames'); if(!cont) return;
    const items=[];
    for(const l of lines){ const dat=l.ls.data(); if(!dat||!dat.length) continue;
      const v=dat[dat.length-1].value; if(v==null) continue;
      const y=l.ls.priceToCoordinate(v); if(y==null) continue;
      items.push({name:l.def.name.replace(/^Nifty /,''),color:l.def.color,y:y}); }
    items.sort((a,b)=>a.y-b.y);
    for(let i=1;i<items.length;i++){ if(items[i].y-items[i-1].y<13) items[i].y=items[i-1].y+13; }
    cont.innerHTML=items.map(it=>'<span style="position:absolute;right:3px;top:'+it.y.toFixed(1)
      +'px;transform:translateY(-50%);white-space:nowrap;font-size:11px;font-weight:700;color:'
      +it.color+';text-shadow:0 0 3px #0e1116,0 0 2px #0e1116">'+_e(it.name)+'</span>').join('');
  }
  // Debounced ResizeObserver (~100ms); skip while we're mid internal set.
  let rzT=null;
  new ResizeObserver(()=>{ if(internalSet) return; if(rzT) clearTimeout(rzT); rzT=setTimeout(()=>{ chart.applyOptions({}); positionNames(); },100); }).observe(host);
})();
</script>
"""


# Sticky deterministic palette — index i → color (removing a line never recolors
# the others, because color is assigned by selection order at render time).
_COMPARE_PALETTE = ["#1f6feb", "#d29922", "#3fb950", "#f85149", "#a371f7", "#39c5cf",
                    "#ff7b72", "#e3b341", "#56d364", "#ffa657", "#79c0ff", "#ff9bce"]
# Soft cap — not a technical limit (the chart renders any number of series); it
# keeps the overlay readable + the URL sane. Colors are generated past the
# curated palette (golden-angle hue spacing), so it can be raised freely.
_COMPARE_MAX = 12


def _cmp_color(i: int) -> str:
    """Distinct line color for selection index i — curated palette first, then
    golden-angle HSL for any overflow (always visually separable)."""
    if i < len(_COMPARE_PALETTE):
        return _COMPARE_PALETTE[i]
    return f"hsl({int((i * 137.508) % 360)},70%,60%)"


def _stock_levels(conn, syms: list[str]) -> dict:
    """Split/bonus-adjusted close series per stock, for the compare overlay.

    Returns {symbol: [{"t": date, "v": adj_close}, ...]} oldest-first. Reuses
    adjust.adjusted_closes (the same back-adjustment the stock chart + RS use) so
    a split never fakes a relative-strength cliff. One batched query for all syms.
    """
    out: dict = {}
    if not syms:
        return out
    ph = ",".join("?" for _ in syms)
    grouped: dict = {}
    for row in conn.execute(
        f"""SELECT symbol, trade_date, close, prev_close
            FROM bhavcopy_rows
            WHERE symbol IN ({ph}) AND series='EQ'
              AND (segment='CM' OR segment IS NULL) AND close IS NOT NULL
            ORDER BY symbol, trade_date""", syms).fetchall():
        grouped.setdefault(row["symbol"], []).append(dict(row))
    for s, rows in grouped.items():
        adj = adjust.adjusted_closes(rows)
        out[s] = [{"t": rw["trade_date"], "v": round(a, 2)}
                  for rw, a in zip(rows, adj) if a is not None]
    return out


@router.get("/dash/compare", response_class=HTMLResponse)
def dash_compare(idx: list[str] = Query(default=[]),
                 sym: list[str] = Query(default=[]),
                 den: str = Query("Nifty 500"),
                 mode: str = Query("rebase"),
                 base: str = Query("100"),
                 r: int = Query(252)) -> HTMLResponse:
    """Overlay up to _COMPARE_MAX stocks AND/OR indices on one chart, each rebased
    to a common (fluid) anchor.

    Render-only: index levels out of index_rows/ratio_rows; stock lines = split/
    bonus-adjusted closes out of bhavcopy_rows (via adjust.py). URL is the source
    of truth (?idx=A&idx=B&sym=RELIANCE&den=&mode=&base=&r=). Bare URL (no idx/sym)
    defaults to Nifty 500 + Nifty 50.
    """
    den = (den or "").strip()
    if den not in ("Nifty 50", "Nifty 500"):
        den = "Nifty 500"
    mode = "ratio" if (mode or "").strip() == "ratio" else "rebase"
    base = "0" if (base or "").strip() == "0" else "100"
    try:
        r = int(r)
    except (TypeError, ValueError):
        r = 252
    if r not in (63, 126, 252, 504, 0):
        r = 252
    _, idx_date = _latest_dates()

    with get_conn() as conn:
        valid = [row["index_name"] for row in conn.execute(
            "SELECT DISTINCT index_name FROM index_rows ORDER BY index_name").fetchall()]
        valid_set = set(valid)
        # Picker universe also needs the full NSE equity list (symbol + name).
        equities = [(row["symbol"], row["company_name"] or "") for row in conn.execute(
            "SELECT symbol, company_name FROM nse_equity_list ORDER BY symbol").fetchall()]
        equity_set = {s for s, _ in equities}
        # Title-case gotcha: strip + drop unknowns, never case-munge. Cap, dedup.
        sel, seen = [], set()
        for n in idx:
            n = (n or "").strip()
            if n in valid_set and n not in seen:
                sel.append(n)
                seen.add(n)
            if len(sel) >= _COMPARE_MAX:
                break
        # Stocks — validated against the NSE equity allowlist (uppercased tickers).
        ssel, sseen = [], set()
        for s in sym:
            s = (s or "").strip().upper()
            if s and s in equity_set and s not in sseen:
                ssel.append(s)
                sseen.add(s)
            if len(sel) + len(ssel) >= _COMPARE_MAX:
                break
        # Default: bare /dash/compare → the two market benchmarks.
        if not sel and not ssel:
            sel = [n for n in ("Nifty 500", "Nifty 50") if n in valid_set]
            seen = set(sel)
        # Combined selection, ordered indices-first; colour = position.
        sel_items = [("idx", n) for n in sel] + [("stk", s) for s in ssel]

        levels, ratios = {}, {}
        if sel:
            ph = ",".join("?" for _ in sel)
            # Levels (any index) — ONE query, ordered (name, date).
            for row in conn.execute(
                f"""SELECT index_name, trade_date, close_value
                    FROM index_rows
                    WHERE index_name IN ({ph}) AND close_value IS NOT NULL
                    ORDER BY index_name, trade_date""",
                sel,
            ).fetchall():
                levels.setdefault(row["index_name"], []).append(
                    {"t": row["trade_date"], "v": round(row["close_value"], 2)})
            # Ratios vs the chosen denominator — ONE query (size indices get []).
            for row in conn.execute(
                f"""SELECT numerator, trade_date, ratio
                    FROM ratio_rows
                    WHERE denominator=? AND numerator IN ({ph}) AND ratio IS NOT NULL
                    ORDER BY numerator, trade_date""",
                (den, *sel),
            ).fetchall():
                ratios.setdefault(row["numerator"], []).append(
                    {"t": row["trade_date"], "v": round(row["ratio"], 4)})
        # Stock lines — split/bonus-adjusted closes (rebase-mode; no RS ratio).
        stock_levels = _stock_levels(conn, ssel)

        series = []
        for i, (kind, name) in enumerate(sel_items):
            if kind == "idx":
                lvl, rat = levels.get(name, []), ratios.get(name, [])
            else:
                lvl, rat = stock_levels.get(name, []), []
            series.append({
                "i": i,
                "name": name,
                "color": _cmp_color(i),
                "kind": kind,
                "level": lvl,
                "ratio": rat,
            })

    series_json = json.dumps(series)

    # --- Picker: active chips (legend) + [+ Add] reveal -> search + suggestions
    def _cmp_href(items, d=None, m=None):
        parts = [(f"idx={_q(n)}" if k == "idx" else f"sym={_q(n)}") for k, n in items]
        parts += [f"den={_q(d or den)}", f"mode={_q(m or mode)}",
                  f"base={_q(base)}", f"r={r}"]
        return "/dash/compare?" + "&".join(parts)

    def _chip(kind, name, i):
        color = _cmp_color(i)
        rest = [it for it in sel_items if it != (kind, name)]
        href = _cmp_href(rest)
        tag = "" if kind == "idx" else ' <span class="cmp-tag">stk</span>'
        return (f'<span class="cmp-chip" data-i="{i}">'
                f'<span class="cmp-sw" style="background:{color}"></span>'
                f'<span>{_esc(name)}</span>{tag}'
                f'<a class="cmp-x" href="{_esc(href)}" title="remove">✕</a></span>')

    active_chips = "".join(_chip(k, n, i) for i, (k, n) in enumerate(sel_items))

    # Suggestion chips (grouped). Now multi-select toggle buttons — the picker
    # JS stages a Set and the "Add" button navigates once with all of them.
    def _sugg_group(label, names):
        avail = [n for n in names if n in valid_set and n not in seen]
        if not avail:
            return ""
        chips = "".join(
            f'<button type="button" class="chip cmp-sugg" data-name="{_esc(n)}">'
            f'+ {_esc(n)}</button>' for n in avail)
        return f'<div class="ghdr">{_esc(label)}</div><div class="chips">{chips}</div>'

    at_cap = len(sel) >= _COMPARE_MAX
    sugg_html = ""
    if not at_cap:
        sugg_html = (_sugg_group("Broad / size", MAJOR_BROAD)
                     + _sugg_group("Sectors", MAJOR_SECTORS))
    # Picker data: indices + the full equity universe (symbol + company name),
    # tagged so the picker emits ?idx= or ?sym=. Filtered client-side.
    cmp_items = [{"v": n, "t": "idx"} for n in valid]
    cmp_items += [{"v": s, "t": "stk", "n": nm} for s, nm in equities]
    cmp_items_json = json.dumps(cmp_items)

    add_block = ""
    if not at_cap:
        add_block = (
            '<div id="cmpAddWrap" style="display:none">'
            '<div class="search" style="margin-top:6px">'
            '<input id="cmpSearch" placeholder="Type a ticker or index — LT, RELIANCE, Nifty Bank…" autocomplete="off"/>'
            '<button class="dtx" id="cmpAddConfirm" type="button" disabled>Add</button>'
            '</div>'
            f'<div class="sub" style="margin:2px 0 6px">Tickers match from 2 letters '
            f'(LT → LT, LTF, LTIM…), names from 4. Tap to stage, then <b>Add</b> '
            f'(up to {_COMPARE_MAX} total).</div>'
            f'<div id="cmpSugg">{sugg_html}</div>'
            '<div id="cmpResults" class="chips" style="margin-top:6px"></div>'
            '</div>')
        add_btn = '<button class="chip" id="cmpAddBtn" type="button">+ Add</button>'
    else:
        add_btn = f'<span class="chip cmp-dim">max {_COMPARE_MAX}</span>'

    picker_html = (
        '<div class="cmp-rail">' + active_chips + add_btn + '</div>' + add_block)

    # --- Presets (one-click querystrings) ---
    seed_sector = next((n for n in sel if n in MAJOR_SECTORS), None) \
        or next((n for n in MAJOR_SECTORS if n in valid_set), None)

    def _preset(names, m):
        names = [n for n in names if n in valid_set][:6]
        if not names:
            return None
        return "/dash/compare?" + "&".join(
            [f"idx={_q(x)}" for x in names] + [f"mode={m}", f"den={_q(den)}"])

    presets = []
    p1 = _preset([n for n in (seed_sector, "Nifty 50", "Nifty 500") if n], "rebase")
    if p1:
        presets.append(("Sector vs market (50 & 500)", p1))
    p2 = _preset(MAJOR_SECTORS[:5], "rebase")
    if p2:
        presets.append(("Sector race", p2))
    hh = [n for n in MAJOR_SECTORS if n in valid_set][:2]
    p3 = _preset(hh, "ratio")
    if p3:
        presets.append(("RS head-to-head", p3))
    preset_html = ""
    if presets:
        preset_html = (
            '<div class="cmp-presets">'
            + "".join(f'<a class="chip" href="{_esc(h)}">{_esc(lbl)}</a>'
                      for lbl, h in presets)
            + '</div>')

    chart_css = """
.rangebar { display:flex; gap:6px; margin:8px 0 4px; flex-wrap:wrap; }
.rangebar button { background:#21262d; color:#c9d1d9; border:1px solid #30363d;
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
.cmp-rail { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:8px; }
.cmp-chip { display:inline-flex; align-items:center; gap:6px; background:#161b22;
            border:1px solid #30363d; border-radius:14px; padding:5px 8px 5px 9px; font-size:13px; }
.cmp-chip.cmp-dim { opacity:.4; }
.cmp-sw { width:10px; height:10px; border-radius:50%; display:inline-block; }
.cmp-tag { font-size:9px; font-weight:700; color:#8b949e; background:#21262d;
           border-radius:4px; padding:1px 4px; letter-spacing:.4px; }
.cmp-x { color:#8b949e; text-decoration:none; font-size:12px; margin-left:1px; }
.cmp-x:hover { color:#f85149; }
.cmp-sugg.cmp-hide { display:none; }
button.cmp-sugg { cursor:pointer; font-family:inherit; }
.cmp-sugg.cmp-on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.cmp-presets { display:flex; gap:6px; flex-wrap:wrap; margin:2px 0 12px; }
.cmp-pin { display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:6px 0 2px; font-size:12px; color:#8b949e; }
.cmp-pin input[type=date] { background:#0d1117; border:1px solid #30363d; color:#e6edf3;
                            border-radius:6px; padding:3px 7px; font-size:12px; }
.cmp-anchor { font-size:12px; color:#8b949e; margin:6px 4px 2px; }
.cmp-vals { display:flex; gap:14px; flex-wrap:wrap; font-size:12px; font-variant-numeric:tabular-nums;
            padding:8px 4px 2px; }
.cmp-val { font-weight:600; }
"""

    # Empty state — still render the picker so the user can add indices.
    if not sel:
        body = (
            f'<style>{chart_css}</style>'
            '<h2>Compare ⇄</h2>'
            '<div class="sub">Overlay any stocks and indices, each rebased to a common '
            'start, to read who outperformed. Use <b>+ Add</b> to begin.</div>'
            + preset_html
            + picker_html
            + '<div class="empty">No indices selected. Use <b>+ Add</b> or a preset above.</div>'
            + _COMPARE_PICKER_JS.replace("__ITEMS__", cmp_items_json).replace("__MAX__", str(_COMPARE_MAX)))
        return HTMLResponse(_shell("Compare · patearn", body, "markets", idx_date or ""))

    # Note any selected series that has no data for the current mode.
    note = ""
    if mode == "ratio":
        empties = [s["name"] for s in series if not s["ratio"]]
        if empties:
            note = ('<div class="sub" style="color:#ffd99a;margin-bottom:8px">'
                    'No RS ratio for: ' + _esc(", ".join(empties))
                    + ' (broad/size indices have no ratio) — dropped in Ratio mode.</div>')
    else:
        empties = [s["name"] for s in series if not s["level"]]
        if empties:
            note = ('<div class="sub" style="color:#ffd99a;margin-bottom:8px">'
                    'No level data for: ' + _esc(", ".join(empties)) + '.</div>')

    def _ron(n):
        return "on" if r == n else ""
    range_bar = (
        '<div class="rangebar">'
        f'<button data-r="63" class="{_ron(63)}">3M</button>'
        f'<button data-r="126" class="{_ron(126)}">6M</button>'
        f'<button data-r="252" class="{_ron(252)}">1Y</button>'
        f'<button data-r="0" class="{_ron(0)}">Max</button></div>')

    mode_bar = (
        '<div class="fbar">'
        f'<button class="fbtn {"on" if mode=="rebase" else ""}" data-cmode="rebase">Rebased</button>'
        f'<button class="fbtn {"on" if mode=="ratio" else ""}" data-cmode="ratio">Ratio</button>'
        '</div>')
    # Denominator switch (ratio mode only) — reloads with ?den=.
    den_href = _cmp_href(sel_items, d="Nifty 50", m="ratio")
    den_href2 = _cmp_href(sel_items, d="Nifty 500", m="ratio")
    denom_bar = (
        f'<div class="fbar" id="cmpDenomBar" style="display:{"flex" if mode=="ratio" else "none"}">'
        f'<a class="fbtn {"on" if den=="Nifty 50" else ""}" href="{_esc(den_href)}">vs Nifty 50</a>'
        f'<a class="fbtn {"on" if den=="Nifty 500" else ""}" href="{_esc(den_href2)}">vs Nifty 500</a>'
        '</div>')
    pin_bar = (
        '<div class="cmp-pin">'
        '<span>📅 Pin anchor</span><input type="date" id="cmpPin"/>'
        '<button class="fbtn" id="cmpReset" type="button">⟳ Fluid</button></div>')

    chart_js = (_COMPARE_CHART_JS
                .replace("__CDN__", _LWC_CDN)
                .replace("__SERIES__", series_json)
                .replace("__MODE__", mode)
                .replace("__BASE__", base)
                .replace("__RANGE__", str(r)))

    body = (
        f'<style>{chart_css}</style>'
        '<h2>Compare ⇄</h2>'
        '<div class="sub" style="margin-bottom:8px">Overlay any stocks and indices — '
        'each indexed to <b>100</b> at a common start (the first visible day), so 122 = '
        '+22%. Pan to re-anchor, or 📅 pin a date. <b>Ratio</b> mode (indices) overlays '
        'each ÷ the benchmark instead.</div>'
        + preset_html
        + picker_html
        + note
        + mode_bar + denom_bar
        + range_bar
        + pin_bar
        + '<div class="cmp-anchor" id="cmpAnchorLbl">REBASED FROM <b>start</b></div>'
        '<div class="chartwrap"><div style="position:relative">'
        '<div id="compareChart" style="height:320px;margin-right:104px;"></div>'
        '<div id="cmpNames" style="position:absolute;top:0;right:0;bottom:0;width:104px;'
        'pointer-events:none;overflow:visible;"></div>'
        '</div></div>'
        '<div class="cmp-vals" id="cmpVals"></div>'
        + chart_js
        + _COMPARE_PICKER_JS.replace("__ITEMS__", cmp_items_json).replace("__MAX__", str(_COMPARE_MAX)))
    return HTMLResponse(_shell("Compare · patearn", body, "markets", idx_date or ""))


# Picker JS (plain template) — reveals the add box, filters suggestion chips by
# substring over ALL valid index names, and rewrites ?idx= via the chip hrefs.
# Add/remove is a full reload with the new querystring (toggles/range/anchor are
# client-instant; only the series set needs a reload).
_COMPARE_PICKER_JS = """
<script>
(function(){
  const ITEMS = __ITEMS__;                      // [{v:name, t:'idx'|'stk', n?:company}]
  const MAX=__MAX__;
  const btn=document.getElementById('cmpAddBtn');
  const wrap=document.getElementById('cmpAddWrap');
  const box=document.getElementById('cmpSearch');
  const sugg=document.getElementById('cmpSugg');
  const results=document.getElementById('cmpResults');
  const confirm=document.getElementById('cmpAddConfirm');
  if(btn&&wrap){ btn.onclick=()=>{ wrap.style.display=(wrap.style.display==='none')?'block':'none'; if(box) box.focus(); }; }
  const p0=new URL(window.location.href).searchParams;
  const already=new Set(p0.getAll('idx').concat(p0.getAll('sym')));  // already on chart
  const slots=MAX-already.size;                 // how many more can be added
  const picked=new Map();                       // name -> 'idx'|'stk' (staging)
  const seeded=new Set();                        // seeded index chips (avoid dupes)
  function refresh(){
    if(!confirm) return;
    confirm.disabled = picked.size===0;
    confirm.textContent = picked.size ? ('Add '+picked.size) : 'Add';
  }
  function toggle(name, type, el){
    if(picked.has(name)){ picked.delete(name); if(el) el.classList.remove('cmp-on'); }
    else { if(picked.size>=slots) return;        // respect the cap
           picked.set(name, type); if(el) el.classList.add('cmp-on'); }
    refresh();
  }
  function wire(el){ el.addEventListener('click', e=>{ e.preventDefault();
    toggle(el.dataset.name, el.dataset.type||'idx', el); }); }
  if(sugg) sugg.querySelectorAll('.cmp-sugg').forEach(el=>{ seeded.add(el.dataset.name); wire(el); });
  if(confirm){
    confirm.onclick=()=>{
      if(!picked.size) return;
      const p=new URL(window.location.href).searchParams;
      const items=[];                            // existing selection (keep order)
      p.getAll('idx').forEach(v=>items.push(['idx',v]));
      p.getAll('sym').forEach(v=>items.push(['sym',v]));
      for(const [name,type] of picked) items.push([type==='stk'?'sym':'idx', name]);
      const capped=items.slice(0,MAX);
      const den=p.get('den')||'Nifty 500', mode=p.get('mode')||'rebase',
            base=p.get('base')||'100', r=p.get('r')||'252';
      const parts=capped.map(it=>it[0]+'='+encodeURIComponent(it[1]));
      parts.push('den='+encodeURIComponent(den),'mode='+encodeURIComponent(mode),
                 'base='+encodeURIComponent(base),'r='+encodeURIComponent(r));
      window.location='/dash/compare?'+parts.join('&');
    };
  }
  // Indices: substring (few). Stocks: ticker prefix from 2 chars; symbol/company
  // substring from 4. Exact ticker first. Capped + debounced so it never blanks.
  function search(q){
    q=q.trim().toLowerCase();
    if(q.length<2) return [];
    const exact=[], prefix=[], sub=[];
    for(const it of ITEMS){
      if(already.has(it.v) || seeded.has(it.v)) continue;
      const v=it.v.toLowerCase();
      if(it.t==='idx'){ if(v.indexOf(q)>=0) sub.push(it); continue; }
      if(v===q) exact.push(it);
      else if(v.indexOf(q)===0) prefix.push(it);
      else if(q.length>=4 && (v.indexOf(q)>=0 || (it.n && it.n.toLowerCase().indexOf(q)>=0))) sub.push(it);
    }
    return exact.concat(prefix, sub).slice(0,30);
  }
  function render(list){
    if(!results) return;
    results.innerHTML='';
    list.forEach(it=>{
      const b=document.createElement('button'); b.type='button';
      b.className='chip cmp-sugg'; b.dataset.name=it.v; b.dataset.type=it.t;
      b.textContent='+ '+it.v+((it.t==='stk'&&it.n)?(' · '+it.n):'');
      if(picked.has(it.v)) b.classList.add('cmp-on');
      wire(b); results.appendChild(b);
    });
  }
  if(box){
    let t=null;
    box.addEventListener('input',()=>{
      const q=box.value.trim().toLowerCase();
      if(sugg) sugg.querySelectorAll('.cmp-sugg').forEach(a=>{
        if(a.parentNode===results) return;
        const nm=(a.dataset.name||'').toLowerCase();
        a.classList.toggle('cmp-hide', q!=='' && nm.indexOf(q)<0); });
      if(t) clearTimeout(t);
      t=setTimeout(()=>render(search(q)), 110);
    });
  }
  refresh();
})();
</script>
"""


# Stock-page RS-overlay picker — like the compare picker, but emits ?cmp= (the
# server detects index-name vs ticker) and keeps the page's own ?sym= pinned.
_STOCK_CMP_PICKER_JS = """
<script>
(function(){
  const ITEMS=__ITEMS__; const MAX=__MAX__; const SYM=__SYM__; const CUR=__CUR__;
  const btn=document.getElementById('soAddBtn');
  const wrap=document.getElementById('soAddWrap');
  const box=document.getElementById('soSearch');
  const results=document.getElementById('soResults');
  const confirm=document.getElementById('soAddConfirm');
  if(!btn||!wrap) return;
  btn.onclick=()=>{ wrap.style.display=(wrap.style.display==='none')?'block':'none'; if(box) box.focus(); };
  const already=new Set(CUR); already.add(SYM);
  const slots=(MAX-1)-CUR.length;
  const picked=new Set();
  function refresh(){ if(!confirm) return;
    confirm.disabled=picked.size===0;
    confirm.textContent=picked.size?('Add '+picked.size):'Add'; }
  function toggle(name, el){
    if(picked.has(name)){ picked.delete(name); if(el) el.classList.remove('cmp-on'); }
    else { if(picked.size>=slots) return; picked.add(name); if(el) el.classList.add('cmp-on'); }
    refresh(); }
  function wire(el){ el.addEventListener('click',e=>{ e.preventDefault(); toggle(el.dataset.name, el); }); }
  if(confirm){ confirm.onclick=()=>{
    if(!picked.size) return;
    const items=CUR.concat([...picked]).slice(0,MAX-1);
    const parts=['sym='+encodeURIComponent(SYM)].concat(items.map(v=>'cmp='+encodeURIComponent(v)));
    window.location='/dash/stock?'+parts.join('&'); }; }
  function search(q){
    q=q.trim().toLowerCase();
    if(q.length<2) return [];
    const exact=[],prefix=[],sub=[];
    for(const it of ITEMS){
      if(already.has(it.v)) continue;
      const v=it.v.toLowerCase();
      if(it.t==='idx'){ if(v.indexOf(q)>=0) sub.push(it); continue; }
      if(v===q) exact.push(it);
      else if(v.indexOf(q)===0) prefix.push(it);
      else if(q.length>=4 && (v.indexOf(q)>=0 || (it.n && it.n.toLowerCase().indexOf(q)>=0))) sub.push(it);
    }
    return exact.concat(prefix,sub).slice(0,30); }
  function render(list){
    if(!results) return; results.innerHTML='';
    list.forEach(it=>{ const b=document.createElement('button'); b.type='button';
      b.className='chip cmp-sugg'; b.dataset.name=it.v;
      b.textContent='+ '+it.v+((it.t==='stk'&&it.n)?(' · '+it.n):'');
      if(picked.has(it.v)) b.classList.add('cmp-on'); wire(b); results.appendChild(b); }); }
  if(box){ let t=null; box.addEventListener('input',()=>{
    const q=box.value; if(t) clearTimeout(t);
    t=setTimeout(()=>render(search(q)),110); }); }
  document.querySelectorAll('#soPeers .cmp-sugg').forEach(function(el){
    if(already.has(el.dataset.name)){ el.disabled=true; el.classList.add('cmp-dim'); }
    else wire(el); });
  refresh();
})();
</script>
"""


# --- PWA assets ------------------------------------------------------------

_MANIFEST = """{
  "name": "patearn — Indian Equity Signals",
  "short_name": "patearn",
  "description": "DVPT flow, layered triggers, sector relative strength.",
  "start_url": "/dash",
  "scope": "/dash",
  "display": "standalone",
  "background_color": "#0e1116",
  "theme_color": "#0e1116",
  "orientation": "portrait-primary",
  "icons": [
    { "src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" },
    { "src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable" }
  ]
}"""

_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="#0e1116"/>
<rect width="512" height="512" rx="96" fill="#161b22"/>
<g stroke="#1f6feb" stroke-width="34" stroke-linecap="round" fill="none">
  <path d="M120 360 L210 250 L290 300 L392 150"/>
</g>
<circle cx="392" cy="150" r="26" fill="#3fb950"/>
<text x="256" y="452" font-family="system-ui,Segoe UI,sans-serif" font-size="92"
      font-weight="800" fill="#e6edf3" text-anchor="middle">H</text>
</svg>"""

# Network-first service worker: always try fresh data, fall back to cache offline.
_SW_JS = """const CACHE = 'hermes-v2';
const SHELL = ['/dash', '/icon.svg', '/manifest.webmanifest', '/dash/offline'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) =>
    Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(()=>{});
      return res;
    }).catch(() =>
      caches.match(e.request).then((m) => m || caches.match('/dash/offline'))
    )
  );
});"""

_OFFLINE_HTML = """<!doctype html><html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Offline · patearn</title>
<style>body{font-family:system-ui,Segoe UI,sans-serif;background:#0e1116;color:#e6edf3;
display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;}
.mut{color:#8b949e;}</style></head>
<body><h1>📵 Offline</h1><p class="mut">patearn needs a connection for live data.</p>
<p class="mut">Reconnect and reopen.</p></body></html>"""


@router.get("/manifest.webmanifest")
def manifest() -> Response:
    return Response(content=_MANIFEST, media_type="application/manifest+json")


@router.get("/icon.svg")
def icon() -> Response:
    return Response(content=_ICON_SVG, media_type="image/svg+xml")


@router.get("/sw.js")
def service_worker() -> Response:
    # Served from root scope so it can control /dash/*
    return Response(content=_SW_JS, media_type="application/javascript",
                    headers={"Service-Worker-Allowed": "/"})


@router.get("/dash/offline", response_class=HTMLResponse)
def offline() -> HTMLResponse:
    return HTMLResponse(_OFFLINE_HTML)
