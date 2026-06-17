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

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from src.core.db import get_conn

router = APIRouter()


# --- Shared shell ----------------------------------------------------------

_THEME = "#0e1116"
_ACCENT = "#1f6feb"

_BASE_CSS = """
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin:0; padding:0; }
body { font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;
       background:#0e1116; color:#e6edf3; padding:0 0 72px; min-height:100vh; }
header { position:sticky; top:0; z-index:10; background:#0e1116cc;
         backdrop-filter:blur(8px); border-bottom:1px solid #21262d;
         padding:14px 16px; display:flex; align-items:center; gap:10px; }
header .logo { font-size:18px; font-weight:800; letter-spacing:.5px; }
header .dot { width:8px; height:8px; border-radius:50%; background:#2ea043; }
header .date { margin-left:auto; color:#8b949e; font-size:12px; }
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
.hsearch { margin-left:8px; }
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
    table.parentNode.insertBefore(tool, table);

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


def _nav(active: str) -> str:
    items = [
        ("dash", "/dash", "📊", "Home"),
        ("markets", "/dash/markets", "🌐", "Markets"),
        ("sectors", "/dash/sectors", "🔁", "Sectors"),
        ("stocks", "/dash/stocks", "🔎", "Stocks"),
        ("stock", "/dash/stock", "💧", "Stock"),
    ]
    out = ['<nav>']
    for key, href, ic, label in items:
        cls = "active" if key == active else ""
        out.append(f'<a class="{cls}" href="{href}"><span class="ic">{ic}</span>{label}</a>')
    out.append('</nav>')
    return "".join(out)


def _shell(title: str, body: str, active: str, latest_date: str = "") -> str:
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
  <span class="dot"></span><span class="logo">HERMES</span>
  <span class="date">{latest_date}</span>
  <form class="hsearch" action="/dash/stock" method="get" autocomplete="off">
    <input name="sym" placeholder="ticker…" autocapitalize="characters"/>
  </form>
</header>
<div class="wrap">
{body}
</div>
{_nav(active)}
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


# --- Data helpers ----------------------------------------------------------

_SCAN_FILTERS = """
  AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
  AND b.value > 10000000 AND b.close > 20
  AND s.symbol NOT LIKE '%ETF%' AND s.symbol NOT LIKE '%IETF%'
  AND s.symbol NOT LIKE '%BEES%' AND s.symbol NOT LIKE '%GOLD%'
  AND s.symbol NOT LIKE '%SILVER%' AND s.symbol NOT LIKE 'MON%'
  AND s.symbol NOT LIKE 'NIFTY%' AND s.symbol NOT LIKE 'BANK%ADD'
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


# --- Routes ----------------------------------------------------------------

@router.get("/dash", response_class=HTMLResponse)
def dash_home() -> HTMLResponse:
    sig_date, idx_date = _latest_dates()
    nifty, breadth, lead = {}, None, None
    top_sectors, weak_sectors, top_stocks = [], [], []
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
                """SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12
                   FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL
                   ORDER BY COALESCE(rs_vs_broad_slope_3m,-999) DESC LIMIT 5""",
                (idx_date,),
            ).fetchall()]
            weak_sectors = [dict(x) for x in conn.execute(
                """SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12
                   FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL
                   ORDER BY COALESCE(rs_vs_broad_slope_3m,999) ASC LIMIT 3""",
                (idx_date,),
            ).fetchall()]
        if sig_date:
            top_stocks = [dict(x) for x in conn.execute(
                f"""SELECT s.symbol, s.trigger_rank rank, s.is_ath_dvpt ath,
                           s.price_vs_hot_avg_pct pvh
                    FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                    WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                    {_SCAN_FILTERS}
                    ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC,
                             COALESCE(s.r_score,-1) DESC LIMIT 5""",
                (sig_date,),
            ).fetchall()]

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
                     f'<td><span class="pill p-{rank}">{rank}</span></td>'
                     f'<td>{_pct(pvh)} {entry}</td></tr>')
    stocks_block = ""
    if srows:
        stocks_block = (
            '<h2>Top trigger stocks</h2>'
            '<div class="card" style="padding:6px 10px;"><table>'
            '<thead><tr><th>Symbol</th><th>Rank</th><th>Δhot</th></tr></thead>'
            f'<tbody>{"".join(srows)}</tbody></table></div>'
            '<a class="row sub" href="/dash/stocks">See all triggers →</a>')

    body = (f'{search}{banner}{kpis}{sectors_block}{stocks_block}'
            '<h2>Data freshness</h2>'
            f'<div class="card">Stock signals: <b>{sig_date or "—"}</b><br>'
            f'Index signals: <b>{idx_date or "—"}</b></div>'
            '<div class="sub">Read-only mirror of the Telegram bot data. '
            'Updated nightly 7:30 PM IST.</div>')
    return HTMLResponse(_shell("Hermes", body, "dash", sig_date or ""))


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
        return HTMLResponse(_shell("Markets — Hermes",
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
    return HTMLResponse(_shell("Markets — Hermes", body, "markets", idx_date or ""))


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
<h2>Sector rotation</h2>
<div class="sub">Sorted strongest RS trend first. Tap a name → its stocks; tap the strip → the ratio chart. <a class="row" style="display:inline" href="/dash/rs">Full RS ranking →</a> · <a class="row" style="display:inline" href="/dash/compare?idx=Nifty+50&idx=Nifty+500">⇄ Compare indices</a></div>
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
    return HTMLResponse(_shell("Sectors — Hermes", body, "sectors", idx_date or ""))


@router.get("/dash/rs", response_class=HTMLResponse)
def dash_rs() -> HTMLResponse:
    """Cross-sector RS-momentum ranking (on-read; 0.6·slope_3m + 0.4·slope_6m)."""
    _, idx_date = _latest_dates()
    rows = []
    if idx_date:
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(
                """SELECT index_name nm, rs_vs_broad_trend_state st,
                          rs_vs_broad_slope_1m s1, rs_vs_broad_slope_3m s3,
                          rs_vs_broad_slope_6m s6, rs_vs_broad_slope_12m s12,
                          (0.6*COALESCE(rs_vs_broad_slope_3m,0)
                           +0.4*COALESCE(rs_vs_broad_slope_6m,0)) mom
                   FROM index_signals
                   WHERE trade_date=? AND broad_benchmark IS NOT NULL
                   ORDER BY mom DESC""",
                (idx_date,),
            ).fetchall()]
    if not rows:
        body = '<div class="empty">No index signals yet. Run the index backfill on the VPS.</div>'
        return HTMLResponse(_shell("RS ranking — Hermes", body, "sectors", idx_date or ""))

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
<h2>RS-momentum ranking</h2>
<div class="sub">All sectors by RS momentum (0.6·3m + 0.4·6m slope vs Nifty 500), strongest first. Tap a sector → its ratio chart. <a class="row" style="display:inline" href="/dash/sectors">← Sector rotation</a></div>
<div class="card" style="padding:6px 10px;">
<table class="dt">
<thead><tr><th>#</th><th>Sector</th><th>1m/3m/6m/12m</th><th>Mom</th><th>Trend</th><th>Pctl</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("RS ranking — Hermes", body, "sectors", idx_date or ""))


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
    return HTMLResponse(_shell("Scan — Hermes", body, "scan", sig_date or ""))


@router.get("/dash/stocks", response_class=HTMLResponse)
def dash_stocks(sector: str = Query(""), limit: int = Query(40, ge=10, le=120)) -> HTMLResponse:
    sig_date, _ = _latest_dates()
    sector = sector.strip()
    rows, watch, sector_syms = [], [], []
    with get_conn() as conn:
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
                          s.next_p_above nextp, s.gap_to_next_p_pct gap, b.close
                   FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                   {_SCAN_FILTERS}{sector_clause}
                   ORDER BY COALESCE(s.is_ath_dvpt,0) DESC, COALESCE(s.p_score,-1) DESC,
                            COALESCE(s.r_score,-1) DESC, {rank_order} ASC,
                            COALESCE(s.ratio_today_vs_power_1m,0) DESC
                   LIMIT ?""",
                params,
            ).fetchall()]
        watch = [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]

    search = ('<form class="search" action="/dash/stock" method="get" autocomplete="off">'
              '<input name="sym" placeholder="Enter NSE ticker — e.g. RELIANCE" '
              'autocapitalize="characters"/><button type="submit">Go</button></form>')

    if sector:
        head = (f'<h2>Stocks in {_esc(sector)}</h2>'
                f'<div class="sub">{len(sector_syms)} constituents · by trigger strength · '
                f'<a class="row" style="display:inline" href="/dash/stocks">clear ↺</a></div>')
        if not sector_syms:
            head += '<div class="card sub">No membership on record for this index.</div>'
    else:
        head = ('<h2>Stock screen</h2>'
                '<div class="sub">Layered DVPT triggers. Filter, then tap a symbol.</div>')

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
        flags = (f'data-ss="{1 if rank == "SS" else 0}" '
                 f'data-aplus="{1 if (r["p_score"] or 0) >= 3 else 0}" '
                 f'data-ath="{1 if r["ath"] else 0}" '
                 f'data-disc="{1 if (pvh is not None and pvh < -3) else 0}" '
                 f'data-near="{near_flag}"')
        trs.append(
            f'<tr {flags}><td><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
            f'<td><span class="pill p-{rank}">{rank}</span></td>'
            f'<td class="mut">{r["r_score"] or 0}/{r["p_score"] or 0}</td>'
            f'<td>{_num(r["close"], 1)}</td>'
            f'<td>{_pct(pvh)} {entry}</td>'
            f'<td class="mut">{near}</td></tr>')

    if trs:
        pills = ('<div id="sbar" class="fbar">'
                 "<button class=\"fbtn on\" onclick=\"sflt('all',this)\">All</button>"
                 "<button class=\"fbtn\" onclick=\"sflt('ss',this)\">SS</button>"
                 "<button class=\"fbtn\" onclick=\"sflt('aplus',this)\">A+</button>"
                 "<button class=\"fbtn\" onclick=\"sflt('ath',this)\">⚡ ATH</button>"
                 "<button class=\"fbtn\" onclick=\"sflt('disc',this)\">🟢 Discount</button>"
                 "<button class=\"fbtn\" onclick=\"sflt('near',this)\">🔥 Near-break</button></div>")
        table = (pills + '<div class="card" style="padding:6px 10px;"><table id="stbl" class="dt">'
                 '<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>Close</th>'
                 '<th>Δhot</th><th>Near-P</th></tr></thead>'
                 f'<tbody>{"".join(trs)}</tbody></table></div>')
    else:
        table = '<div class="empty">No stocks match.</div>'

    watch_block = ""
    if watch:
        chips = "".join(f'<a class="chip" href="/dash/stock?sym={_esc(s)}">{_esc(s)}</a>'
                        for s in watch)
        watch_block = f'<h2>Watchlist</h2><div class="chips">{chips}</div>'

    js = ("<script>function sflt(f,el){"
          "document.querySelectorAll('#stbl tr[data-ss]').forEach(function(r){"
          "r.style.display=(f==='all'||r.dataset[f]==='1')?'':'none';});"
          "document.querySelectorAll('#sbar .fbtn').forEach(function(b){"
          "b.classList.remove('on');});el.classList.add('on');}</script>")

    body = search + head + table + watch_block + (js if trs else "")
    return HTMLResponse(_shell("Stocks — Hermes", body, "stocks", sig_date or ""))


_LWC_CDN = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"


@router.get("/dash/stock", response_class=HTMLResponse)
def dash_stock(sym: str = Query("", max_length=20)) -> HTMLResponse:
    sym = sym.upper().strip()
    search = f"""
<form class="search" action="/dash/stock" method="get">
  <input name="sym" placeholder="Enter NSE ticker — e.g. BANDHANBNK" value="{_esc(sym)}" autocapitalize="characters" autocomplete="off"/>
  <button type="submit">Go</button>
</form>
"""
    if not sym:
        body = search + '<div class="empty">Enter a ticker for the full chart — price, DVPT spikes, delivery, and institutional zones.</div>'
        return HTMLResponse(_shell("Stock — Hermes", body, "stock"))

    with get_conn() as conn:
        latest = conn.execute(
            """SELECT s.*, b.close, b.deliv_per
               FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
               WHERE s.symbol=? AND b.series='EQ'
               ORDER BY s.trade_date DESC LIMIT 1""",
            (sym,),
        ).fetchone()
        # Up to 5 years of daily candles + DVPT + delivery for the charts (oldest first)
        rows = conn.execute(
            """SELECT b.trade_date, b.open, b.high, b.low, b.close, b.prev_close,
                      b.deliv_per, b.value,
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

    if not latest or not rows:
        body = search + f'<div class="empty">No data for <b>{_esc(sym)}</b>. Check the ticker.</div>'
        return HTMLResponse(_shell("Stock — Hermes", body, "stock"))

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
        series.append({
            "time": r["trade_date"],
            "open": o, "high": hi, "low": lo, "close": c,
            "prev_close": r["prev_close"],
            "dvpt": int(r["dvpt"]) if r["dvpt"] is not None else 0,
            "deliv": round(r["deliv_per"], 1) if r["deliv_per"] is not None else None,
            "r1m": round(r["r1m"], 2) if r["r1m"] is not None else None,
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

    chart_css = """
.rangebar { display:flex; gap:6px; margin:8px 0 4px; }
.rangebar button { background:#21262d; color:#c9d1d9; border:1px solid #30363d;
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
"""

    body = f"""{search}
<style>{chart_css}</style>
<h2>{_esc(sym)} <span class="pill p-{rank}">{rank}</span> {ath}</h2>
<div class="sub">{L['trade_date']} · close ₹{_num(today_close,2)} · deliv {_num(L.get('deliv_per'),1)}%</div>
<div class="kpi">
  <div class="box"><div class="num">{L.get('r_score') or 0}/{L.get('p_score') or 0}</div><div class="lbl">r / p score</div></div>
  <div class="box"><div class="num">{int(L['delivery_value_per_trade'] or 0):,}</div><div class="lbl">DVPT today</div></div>
  <div class="box"><div class="num">{_num(L.get('ratio_today_vs_power_1m'))}</div><div class="lbl">vs power 1m</div></div>
</div>

{insight_html}
{inertia_html}

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

{zones_html}

{pt14_html}

{rs_html}

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
  const pc=LightweightCharts.createChart(pEl, Object.assign({{height:300}}, common));
  const vc=LightweightCharts.createChart(vEl, Object.assign({{height:150}}, common));
  const dc=LightweightCharts.createChart(dEl, Object.assign({{height:120}}, common));

  const candle=pc.addCandlestickSeries({{upColor:'#3fb950',downColor:'#f85149',wickUpColor:'#3fb950',wickDownColor:'#f85149',borderVisible:false}});
  candle.setData(S.map(d=>({{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close}})));
  DATA.zones.forEach(z=>{{ candle.createPriceLine({{price:z.price,color:z.color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:z.label}}); }});

  const dvpt=vc.addHistogramSeries({{priceFormat:{{type:'volume'}}}});
  dvpt.setData(S.map(d=>({{time:d.time,value:d.dvpt,color:(d.r1m!=null&&d.r1m>1)?'#d29922':'#30506b'}})));

  const deliv=dc.addLineSeries({{color:'#58a6ff',lineWidth:2}});
  deliv.setData(S.filter(d=>d.deliv!=null).map(d=>({{time:d.time,value:d.deliv}})));

  // Sync time scales across the three charts. A reentrancy guard stops a
  // range click from ping-ponging range updates pc<->vc<->dc until float
  // convergence (the source of the range-switch slowness, worst on Max).
  const charts=[pc,vc,dc];
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
  // Debounced ResizeObserver: coalesce bursts (~100ms) and skip while syncing.
  let rzT=null;
  new ResizeObserver(()=>{{
    if(syncing) return;
    if(rzT) clearTimeout(rzT);
    rzT=setTimeout(()=>{{ charts.forEach(c=>c.applyOptions({{}})); }},100);
  }}).observe(pEl);

  // Crosshair value readout — hover ANY of the 3 panes to see that day's
  // OHLC + DVPT + delivery; shows the latest day when the cursor is off-chart.
  const rdt=document.getElementById('priceRdt');
  function tkey(t){{ return (typeof t==='object'&&t)?(t.year+'-'+('0'+t.month).slice(-2)+'-'+('0'+t.day).slice(-2)):t; }}
  const byT={{}}; S.forEach(d=>byT[d.time]=d);
  function showR(d){{
    if(!d){{ rdt.innerHTML=''; return; }}
    rdt.innerHTML='<b>'+d.time+'</b>&nbsp; O '+d.open+'&nbsp; H '+d.high+'&nbsp; L '+d.low
      +'&nbsp; <b>C '+d.close+'</b>'
      +(d.dvpt!=null?'&nbsp; · DVPT ₹'+Math.round(d.dvpt).toLocaleString('en-IN'):'')
      +(d.deliv!=null?'&nbsp; · Deliv '+d.deliv.toFixed(1)+'%':'');
  }}
  [pc,vc,dc].forEach(c=>c.subscribeCrosshairMove(p=>{{
    if(!p||!p.time){{ showR(S[S.length-1]); return; }}
    showR(byT[tkey(p.time)]||S[S.length-1]);
  }}));
  showR(S[S.length-1]);
}})();
</script>
"""
    return HTMLResponse(_shell(f"{sym} — Hermes", body, "stock", L["trade_date"]))


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
        return HTMLResponse(_shell("Ratio — Hermes", body, "sectors", idx_date or ""))

    with get_conn() as conn:
        known = conn.execute(
            "SELECT 1 FROM index_rows WHERE index_name=? LIMIT 1", (idx,)).fetchone()
        if not known:
            body = f'<div class="empty">Unknown index <b>{_esc(idx)}</b>.</div>'
            return HTMLResponse(_shell("Ratio — Hermes", body, "sectors", idx_date or ""))

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
            return HTMLResponse(_shell(f"{idx} ratio — Hermes", body, "sectors", idx_date or ""))

        sig = conn.execute(
            """SELECT rs_vs_broad_trend_state st, ret_3m_pct r3,
                      rs_vs_broad_today rs, rs_vs_broad_slope_1m s1,
                      rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6,
                      rs_vs_broad_slope_12m s12, rs_vs_broad_above_50ma a50,
                      rs_vs_broad_above_200ma a200, rs_vs_broad_new_52w_high nh
               FROM index_signals
               WHERE index_name=? ORDER BY trade_date DESC LIMIT 1""",
            (idx,),
        ).fetchone()
        S = dict(sig) if sig else {}

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
                    f"""SELECT symbol, trigger_rank rank, is_ath_dvpt ath,
                              p_score, r_score, price_vs_hot_avg_pct pvh
                       FROM stock_signals
                       WHERE trade_date=? AND symbol IN ({ph})
                       ORDER BY COALESCE(is_ath_dvpt,0) DESC,
                                COALESCE(p_score,-1) DESC, COALESCE(r_score,-1) DESC
                       LIMIT 8""",
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

    # --- Top constituents table ---
    if syms:
        crows = []
        for c in consts:
            rk = c["rank"] or "-"
            ath = "⚡" if c["ath"] else ""
            pvh = c["pvh"]
            entry = ("🟢" if pvh < -3 else ("🔴" if pvh > 3 else "🟡")) if pvh is not None else ""
            crows.append(
                f'<tr><td><a class="row" href="/dash/stock?sym={_esc(c["symbol"])}">'
                f'<span class="sym">{ath}{_esc(c["symbol"])}</span></a></td>'
                f'<td><span class="pill p-{rk}">{rk}</span></td>'
                f'<td class="mut">{c["r_score"] or 0}/{c["p_score"] or 0}</td>'
                f'<td>{_pct(pvh)} {entry}</td></tr>')
        if crows:
            consts_html = (
                '<h2>Top constituents <span class="sub" style="margin:0">by DVPT trigger</span></h2>'
                '<div class="card" style="padding:6px 10px;"><table>'
                '<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>Δhot</th></tr></thead>'
                f'<tbody>{"".join(crows)}</tbody></table></div>')
        else:
            consts_html = ('<h2>Top constituents</h2>'
                           '<div class="card"><div class="sub" style="margin:0">'
                           'No stock signals for the constituents on the latest day.</div></div>')
    else:
        consts_html = ('<h2>Top constituents</h2>'
                       '<div class="card"><div class="sub" style="margin:0">'
                       'No membership on record for this index.</div></div>')

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
        f'<a class="fbtn" href="/dash/compare?idx={_q(idx)}">Compare ⇄</a></div>')

    body = f"""
<style>{chart_css}</style>
<h2>{_esc(idx)}{chip} <span class="sub" style="margin:0">RS vs {_esc(den)}</span></h2>
<div class="sub" style="margin-bottom:10px">{strip} &nbsp; 3m RS {_pct(s3)} · ret 3m {_pct(r3)}</div>
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
    return HTMLResponse(_shell(f"{idx} ratio — Hermes", body, "sectors",
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
  let base = (CBASE0==='0') ? '0' : '100';
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
  }

  // --- fluid anchor: recompute on pan, rAF-coalesced + anchor-gated --------
  let raf=null, internalSet=false, lastAnchor=null;
  function scheduleRebase(from){
    if (pinned!==null) return;          // pinned anchor ignores panning
    if (internalSet) return;            // our own setData/ setVisibleRange
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
    if(!n||n>=allT.length){ chart.timeScale().fitContent(); }
    else {
      const from=allT[allT.length-n], to=allT[allT.length-1];
      chart.timeScale().setVisibleRange({from,to});
    }
    internalSet=false;
    if (pinned===null){
      // re-anchor fluid to whatever the new left edge snapped to
      const vr=chart.timeScale().getVisibleRange();
      const from = vr ? timeToStr(vr.from) : (n&&n<allT.length?allT[allT.length-n]:null);
      lastAnchor=null; scheduleRebase(from);
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
  // --- base toggle (rebased geometry; relabel/offset, instant) -------------
  document.querySelectorAll('[data-cbase]').forEach(b=>{
    b.onclick=()=>{
      base = b.dataset.cbase;
      document.querySelectorAll('[data-cbase]').forEach(x=>x.classList.toggle('on', x===b));
      applyRebase(pinned!==null?pinned:anchorDate);
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
  // Initial draw (fitContent first so anchor at series start), then range.
  applyRebase(null);
  setRange(CRANGE0);
  renderVals(null);

  // Debounced ResizeObserver (~100ms); skip while we're mid internal set.
  let rzT=null;
  new ResizeObserver(()=>{ if(internalSet) return; if(rzT) clearTimeout(rzT); rzT=setTimeout(()=>{ chart.applyOptions({}); },100); }).observe(host);
})();
</script>
"""


# Sticky deterministic palette — index i → color (removing a line never recolors
# the others, because color is assigned by selection order at render time).
_COMPARE_PALETTE = ["#1f6feb", "#d29922", "#3fb950", "#f85149", "#a371f7", "#58a6ff"]


@router.get("/dash/compare", response_class=HTMLResponse)
def dash_compare(idx: list[str] = Query(default=[]),
                 den: str = Query("Nifty 500"),
                 mode: str = Query("rebase"),
                 base: str = Query("100"),
                 r: int = Query(252)) -> HTMLResponse:
    """Overlay ≤6 indices on one chart, each rebased to a common (fluid) anchor.

    Render-only (D40): RAW values out of index_rows/ratio_rows, rebased client-
    side. URL is the source of truth (?idx=A&idx=B&den=&mode=&base=&r=).
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
        # Title-case gotcha: strip + drop unknowns, never case-munge. Cap 6, dedup.
        sel, seen = [], set()
        for n in idx:
            n = (n or "").strip()
            if n in valid_set and n not in seen:
                sel.append(n)
                seen.add(n)
            if len(sel) >= 6:
                break

        series = []
        if sel:
            ph = ",".join("?" for _ in sel)
            # Levels (any index) — ONE query, ordered (name, date).
            levels = {}
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
            ratios = {}
            for row in conn.execute(
                f"""SELECT numerator, trade_date, ratio
                    FROM ratio_rows
                    WHERE denominator=? AND numerator IN ({ph}) AND ratio IS NOT NULL
                    ORDER BY numerator, trade_date""",
                (den, *sel),
            ).fetchall():
                ratios.setdefault(row["numerator"], []).append(
                    {"t": row["trade_date"], "v": round(row["ratio"], 4)})
            for i, name in enumerate(sel):
                series.append({
                    "i": i,
                    "name": name,
                    "color": _COMPARE_PALETTE[i % len(_COMPARE_PALETTE)],
                    "level": levels.get(name, []),
                    "ratio": ratios.get(name, []),
                })

    series_json = json.dumps(series)

    # --- Picker: active chips (legend) + [+ Add] reveal -> search + suggestions
    def _chip(name, i):
        color = _COMPARE_PALETTE[i % len(_COMPARE_PALETTE)]
        rest = [x for x in sel if x != name]
        href = "/dash/compare?" + "&".join(
            [f"idx={_q(x)}" for x in rest]
            + [f"den={_q(den)}", f"mode={_q(mode)}", f"base={_q(base)}", f"r={r}"])
        return (f'<span class="cmp-chip" data-i="{i}">'
                f'<span class="cmp-sw" style="background:{color}"></span>'
                f'<span>{_esc(name)}</span>'
                f'<a class="cmp-x" href="{_esc(href)}" title="remove">✕</a></span>')

    active_chips = "".join(_chip(n, i) for i, n in enumerate(sel))

    # Suggestion chips (grouped) — adding appends to ?idx=. Skip already-selected.
    def _add_href(name):
        nxt = sel + [name]
        return "/dash/compare?" + "&".join(
            [f"idx={_q(x)}" for x in nxt]
            + [f"den={_q(den)}", f"mode={_q(mode)}", f"base={_q(base)}", f"r={r}"])

    def _sugg_group(label, names):
        avail = [n for n in names if n in valid_set and n not in seen]
        if not avail:
            return ""
        chips = "".join(
            f'<a class="chip cmp-sugg" data-name="{_esc(n)}" href="{_esc(_add_href(n))}">'
            f'+ {_esc(n)}</a>' for n in avail)
        return f'<div class="ghdr">{_esc(label)}</div><div class="chips">{chips}</div>'

    at_cap = len(sel) >= 6
    sugg_html = ""
    if not at_cap:
        sugg_html = (_sugg_group("Broad / size", MAJOR_BROAD)
                     + _sugg_group("Sectors", MAJOR_SECTORS))
    # All valid names as data for the substring filter (any index addable).
    all_names_json = json.dumps(valid)

    add_block = ""
    if not at_cap:
        add_block = (
            '<div id="cmpAddWrap" style="display:none">'
            '<div class="search" style="margin-top:6px">'
            '<input id="cmpSearch" placeholder="Filter indices to add…" autocomplete="off"/>'
            '</div>'
            f'<div id="cmpSugg">{sugg_html}</div>'
            '</div>')
        add_btn = '<button class="chip" id="cmpAddBtn" type="button">+ Add</button>'
    else:
        add_btn = '<span class="chip cmp-dim">max 6</span>'

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
.cmp-x { color:#8b949e; text-decoration:none; font-size:12px; margin-left:1px; }
.cmp-x:hover { color:#f85149; }
.cmp-sugg.cmp-hide { display:none; }
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
            '<h2>Compare indices ⇄</h2>'
            '<div class="sub">Overlay up to 6 indices, each rebased to a common '
            'start, to read who outperformed. Pick indices to begin.</div>'
            + preset_html
            + picker_html
            + '<div class="empty">No indices selected. Use <b>+ Add</b> or a preset above.</div>'
            + _COMPARE_PICKER_JS.replace("__NAMES__", all_names_json))
        return HTMLResponse(_shell("Compare — Hermes", body, "markets", idx_date or ""))

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
        f'<button class="fbtn {"on" if mode=="rebase" else ""}" data-cmode="rebase">Rebased %</button>'
        f'<button class="fbtn {"on" if mode=="ratio" else ""}" data-cmode="ratio">Ratio</button>'
        '</div>')
    base_bar = (
        '<div class="fbar">'
        f'<button class="fbtn {"on" if base=="100" else ""}" data-cbase="100">Base 100</button>'
        f'<button class="fbtn {"on" if base=="0" else ""}" data-cbase="0">Base 0%</button>'
        '</div>')
    # Denominator switch (ratio mode only) — reloads with ?den=.
    den_href = "/dash/compare?" + "&".join(
        [f"idx={_q(x)}" for x in sel]
        + [f"den={_q('Nifty 50')}", f"mode=ratio", f"base={_q(base)}", f"r={r}"])
    den_href2 = "/dash/compare?" + "&".join(
        [f"idx={_q(x)}" for x in sel]
        + [f"den={_q('Nifty 500')}", f"mode=ratio", f"base={_q(base)}", f"r={r}"])
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
        '<h2>Compare indices ⇄</h2>'
        '<div class="sub" style="margin-bottom:8px">Each line rebased to a common '
        'start (the first visible day) — pan to re-anchor, or 📅 pin a date. '
        'Rebased % overlays index levels; Ratio overlays each ÷ the benchmark.</div>'
        + preset_html
        + picker_html
        + note
        + mode_bar + base_bar + denom_bar
        + range_bar
        + pin_bar
        + '<div class="cmp-anchor" id="cmpAnchorLbl">REBASED FROM <b>start</b></div>'
        '<div class="chartwrap"><div id="compareChart" style="height:320px;"></div></div>'
        '<div class="cmp-vals" id="cmpVals"></div>'
        + chart_js
        + _COMPARE_PICKER_JS.replace("__NAMES__", all_names_json))
    return HTMLResponse(_shell("Compare — Hermes", body, "markets", idx_date or ""))


# Picker JS (plain template) — reveals the add box, filters suggestion chips by
# substring over ALL valid index names, and rewrites ?idx= via the chip hrefs.
# Add/remove is a full reload with the new querystring (toggles/range/anchor are
# client-instant; only the series set needs a reload).
_COMPARE_PICKER_JS = """
<script>
(function(){
  const NAMES = __NAMES__;
  const btn=document.getElementById('cmpAddBtn');
  const wrap=document.getElementById('cmpAddWrap');
  const box=document.getElementById('cmpSearch');
  const sugg=document.getElementById('cmpSugg');
  if(btn&&wrap){ btn.onclick=()=>{ wrap.style.display=(wrap.style.display==='none')?'block':'none'; if(box) box.focus(); }; }
  function curParams(){
    const u=new URL(window.location.href);
    return u.searchParams;
  }
  function buildHref(name){
    const p=curParams(); const sel=p.getAll('idx');
    if(sel.indexOf(name)>=0 || sel.length>=6) return null;
    sel.push(name);
    const den=p.get('den')||'Nifty 500', mode=p.get('mode')||'rebase',
          base=p.get('base')||'100', r=p.get('r')||'252';
    const parts=sel.map(s=>'idx='+encodeURIComponent(s));
    parts.push('den='+encodeURIComponent(den),'mode='+encodeURIComponent(mode),
               'base='+encodeURIComponent(base),'r='+encodeURIComponent(r));
    return '/dash/compare?'+parts.join('&');
  }
  if(box&&sugg){
    box.addEventListener('input',()=>{
      const q=box.value.trim().toLowerCase();
      // Filter the seeded suggestion chips by substring.
      sugg.querySelectorAll('.cmp-sugg').forEach(a=>{
        const nm=(a.dataset.name||'').toLowerCase();
        a.classList.toggle('cmp-hide', q!=='' && nm.indexOf(q)<0);
      });
      // If the query matches names not in the seed list, append dynamic chips.
      let dyn=document.getElementById('cmpDyn');
      if(!dyn){ dyn=document.createElement('div'); dyn.id='cmpDyn'; dyn.className='chips'; sugg.appendChild(dyn); }
      dyn.innerHTML='';
      if(q!==''){
        const seeded={}; sugg.querySelectorAll('.cmp-sugg').forEach(a=>seeded[a.dataset.name]=1);
        const hits=NAMES.filter(n=>n.toLowerCase().indexOf(q)>=0 && !seeded[n]).slice(0,12);
        hits.forEach(n=>{ const h=buildHref(n); if(!h) return;
          const a=document.createElement('a'); a.className='chip'; a.href=h; a.textContent='+ '+n; dyn.appendChild(a); });
      }
    });
  }
})();
</script>
"""


# --- PWA assets ------------------------------------------------------------

_MANIFEST = """{
  "name": "Hermes — Indian Equity Signals",
  "short_name": "Hermes",
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
<title>Offline — Hermes</title>
<style>body{font-family:system-ui,Segoe UI,sans-serif;background:#0e1116;color:#e6edf3;
display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;}
.mut{color:#8b949e;}</style></head>
<body><h1>📵 Offline</h1><p class="mut">Hermes needs a connection for live data.</p>
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
