"""Hermes web dashboard + installable PWA (D33-web).

A mobile/desktop browser dashboard over the same SQLite data the Telegram bot
uses. Served by the existing FastAPI app on :8000. Designed to be installed as
a Progressive Web App (PWA) — Chrome/Edge show an "Install" button when served
over HTTPS, giving it its own icon and frameless window.

Views:
  /dash            — overview (status + nav)
  /dash/sectors    — D32 sector-rotation dashboard
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
from datetime import datetime
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
                """SELECT index_name nm, rs_vs_broad_trend_state st, rs_vs_broad_slope_3m s3
                   FROM index_signals WHERE trade_date=? AND broad_benchmark IS NOT NULL
                   ORDER BY COALESCE(rs_vs_broad_slope_3m,-999) DESC LIMIT 5""",
                (idx_date,),
            ).fetchall()]
            weak_sectors = [dict(x) for x in conn.execute(
                """SELECT index_name nm, rs_vs_broad_trend_state st, rs_vs_broad_slope_3m s3
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
            out.append(f'<tr><td class="sym">{_esc(r["nm"])}</td>'
                       f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                       f'<td>{_pct(r["s3"])}</td></tr>')
        return "".join(out)

    sectors_block = ""
    if top_sectors:
        sectors_block = (
            '<h2>Top sectors <span class="sub" style="margin:0">by 3m RS</span></h2>'
            '<div class="card" style="padding:6px 10px;"><table>'
            '<thead><tr><th>Sector</th><th>Trend</th><th>RS 3m</th></tr></thead>'
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
        return (f'<a class="maj" href="/dash/stocks?sector={_q(v["nm"])}">'
                f'<div class="nm">{_esc(v["nm"])}{chip}</div>'
                f'<div class="rr"><span>{_num(v["close"],0)}</span>'
                f'<span>1d {_pct(v["r1d"])}</span>'
                f'<span>1m {_pct(v["r1m"])}</span>'
                f'<span>3m {_pct(v["r3m"])}</span></div></a>')

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
            f'<td>{_pct(v["r3m"])}</td><td>{chip}</td></tr>')

    js = ("<script>function mflt(g,el){"
          "document.querySelectorAll('#mbundle tr[data-grp]').forEach(function(r){"
          "r.style.display=(g==='all'||r.dataset.grp===g)?'':'none';});"
          "document.querySelectorAll('#mbar .fbtn').forEach(function(b){"
          "b.classList.remove('on');});el.classList.add('on');}</script>")

    body = (
        '<h2>Major indexes &amp; sectors</h2>'
        '<div class="sub">Broad market + core sectors. Tap any → its stocks.</div>'
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
        '<div class="card" style="padding:6px 10px;"><table id="mbundle">'
        '<thead><tr><th>Index</th><th>1d</th><th>1m</th><th>3m</th><th>Trend</th></tr></thead>'
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
            trs.append(
                f'<tr><td><a class="row" href="/dash/stocks?sector={_q(r["index_name"])}">'
                f'<span class="sym">{_esc(r["index_name"])}</span></a></td>'
                f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                f'<td>{_pct(r["s1"])}</td><td>{_pct(r["s3"])}</td>'
                f'<td>{_pct(r["r3"])}</td></tr>'
            )
        body = f"""
<h2>Sector rotation</h2>
<div class="sub">RS vs Nifty 500. Sorted strongest trend first. Tap a sector → its stocks.</div>
<div class="card" style="padding:6px 10px;">
<table>
<thead><tr><th>Index</th><th>Trend</th><th>RS 1m</th><th>RS 3m</th><th>Ret 3m</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("Sectors — Hermes", body, "sectors", idx_date or ""))


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
        table = (pills + '<div class="card" style="padding:6px 10px;"><table id="stbl">'
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

    # --- Relative strength (D32/D33) — honest status ----------------------
    rs_html = f"""
<h2>Relative strength</h2>
<div class="card"><div class="sub" style="margin:0">Stock-vs-sector and stock-vs-Nifty ratio dynamics (D33) are not wired yet — the index/sector ratio layer (D32) exists, but per-stock membership + RS is the next build. Use <b>/sectors</b> for the sector-rotation picture meanwhile.</div></div>
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

  // Sync time scales across the three charts.
  const charts=[pc,vc,dc];
  charts.forEach(src=>{{
    src.timeScale().subscribeVisibleLogicalRangeChange(r=>{{
      if(!r) return;
      charts.forEach(t=>{{ if(t!==src) t.timeScale().setVisibleLogicalRange(r); }});
    }});
  }});

  function setRange(n){{
    if(!n||n>=S.length){{ pc.timeScale().fitContent(); return; }}
    const from=S[S.length-n].time, to=S[S.length-1].time;
    pc.timeScale().setVisibleRange({{from,to}});
  }}
  document.querySelectorAll('.rangebar button').forEach(b=>{{
    b.onclick=()=>{{ document.querySelectorAll('.rangebar button').forEach(x=>x.classList.remove('on')); b.classList.add('on'); setRange(parseInt(b.dataset.r)); }};
  }});
  setRange(0);
  new ResizeObserver(()=>{{ charts.forEach(c=>c.applyOptions({{}})); }}).observe(pEl);
}})();
</script>
"""
    return HTMLResponse(_shell(f"{sym} — Hermes", body, "stock", L["trade_date"]))


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
