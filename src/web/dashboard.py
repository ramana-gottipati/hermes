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

from datetime import datetime

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
"""


def _nav(active: str) -> str:
    items = [
        ("dash", "/dash", "📊", "Home"),
        ("sectors", "/dash/sectors", "🔁", "Sectors"),
        ("scan", "/dash/scan", "🔎", "Scan"),
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


# --- Routes ----------------------------------------------------------------

@router.get("/dash", response_class=HTMLResponse)
def dash_home() -> HTMLResponse:
    sig_date, idx_date = _latest_dates()
    with get_conn() as conn:
        counts = {"SS": 0, "S": 0, "A": 0}
        if sig_date:
            for r in conn.execute(
                """SELECT trigger_rank, COUNT(*) n FROM stock_signals s
                   JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.trigger_rank IN ('SS','S','A')
                   """ + _SCAN_FILTERS + " GROUP BY trigger_rank",
                (sig_date,),
            ).fetchall():
                counts[r["trigger_rank"]] = r["n"]
            ath = conn.execute(
                """SELECT COUNT(*) n FROM stock_signals s
                   JOIN bhavcopy_rows b USING (symbol, trade_date)
                   WHERE s.trade_date=? AND s.is_ath_dvpt=1 """ + _SCAN_FILTERS,
                (sig_date,),
            ).fetchone()["n"]
        else:
            ath = 0
        breakouts = 0
        if idx_date:
            breakouts = conn.execute(
                """SELECT COUNT(*) n FROM index_signals
                   WHERE trade_date=? AND rs_vs_broad_trend_state IN ('BREAKOUT','UPTREND')""",
                (idx_date,),
            ).fetchone()["n"]

    body = f"""
<div class="kpi">
  <div class="box"><div class="num">{counts['SS']+counts['S']}</div><div class="lbl">SS+S triggers today</div></div>
  <div class="box"><div class="num">{ath}</div><div class="lbl">ATH-DVPT today</div></div>
  <div class="box"><div class="num">{breakouts}</div><div class="lbl">sector breakouts/uptrend</div></div>
</div>
<h2>Quick views</h2>
<a class="row card" href="/dash/scan">🔎 <b>Scan</b> — layered DVPT triggers (rank SS→C, ATH, discount entry)</a>
<a class="row card" href="/dash/sectors">🔁 <b>Sectors</b> — relative-strength rotation vs Nifty 500</a>
<a class="row card" href="/dash/stock">💧 <b>Stock</b> — DVPT flow + institutional price zones for any ticker</a>
<h2>Data freshness</h2>
<div class="card">
  Stock signals: <b>{sig_date or '—'}</b><br>
  Index signals: <b>{idx_date or '—'}</b>
</div>
<div class="sub">Read-only mirror of the same data the Telegram bot uses. Updated nightly 7:30 PM IST.</div>
"""
    return HTMLResponse(_shell("Hermes", body, "dash", sig_date or ""))


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
                f'<tr><td class="sym">{_esc(r["index_name"])}</td>'
                f'<td><span class="pill p-{st}">{st[:5]}</span></td>'
                f'<td>{_pct(r["s1"])}</td><td>{_pct(r["s3"])}</td>'
                f'<td>{_pct(r["r3"])}</td></tr>'
            )
        body = f"""
<h2>Sector rotation</h2>
<div class="sub">RS vs Nifty 500. Sorted strongest trend first, then 3m RS slope.</div>
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
        body = search + '<div class="empty">Enter a ticker to see DVPT flow + institutional price zones.</div>'
        return HTMLResponse(_shell("Stock — Hermes", body, "stock"))

    with get_conn() as conn:
        latest = conn.execute(
            """SELECT s.*, b.close, b.deliv_per
               FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
               WHERE s.symbol=? AND b.series='EQ'
               ORDER BY s.trade_date DESC LIMIT 1""",
            (sym,),
        ).fetchone()
        hist = conn.execute(
            """SELECT s.trade_date, b.close, b.deliv_per,
                      s.delivery_value_per_trade dvpt, s.ratio_today_vs_power_1m r1m
               FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
               WHERE s.symbol=? AND b.series='EQ'
               ORDER BY s.trade_date DESC LIMIT 15""",
            (sym,),
        ).fetchall()

    if not latest:
        body = search + f'<div class="empty">No data for <b>{_esc(sym)}</b>. Check the ticker.</div>'
        return HTMLResponse(_shell("Stock — Hermes", body, "stock"))

    L = dict(latest)
    rank = L.get("trigger_rank") or "-"
    ath = "⚡ ATH-DVPT" if L.get("is_ath_dvpt") else ""
    today_close = L.get("close")

    # Institutional price zones (D31)
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

    hist_rows = "".join(
        f'<tr><td class="mut">{h["trade_date"]}</td><td>{_num(h["close"],1)}</td>'
        f'<td>{_num(h["deliv_per"],1)}%</td>'
        f'<td>{int(h["dvpt"]):,}</td><td>{_num(h["r1m"])}</td></tr>'
        for h in hist
    )

    body = f"""{search}
<h2>{_esc(sym)} <span class="pill p-{rank}">{rank}</span> {ath}</h2>
<div class="sub">{L['trade_date']} · close ₹{_num(today_close,2)} · deliv {_num(L.get('deliv_per'),1)}%</div>
<div class="kpi">
  <div class="box"><div class="num">{L.get('r_score') or 0}/{L.get('p_score') or 0}</div><div class="lbl">r / p score</div></div>
  <div class="box"><div class="num">{int(L['delivery_value_per_trade'] or 0):,}</div><div class="lbl">DVPT today</div></div>
  <div class="box"><div class="num">{_num(L.get('ratio_today_vs_power_1m'))}</div><div class="lbl">vs power 1m</div></div>
</div>
{zones_html}
<h2>Last {len(hist)} days</h2>
<div class="card" style="padding:6px 10px;">
<table>
<thead><tr><th>Date</th><th>Close</th><th>Deliv</th><th>DVPT</th><th>r1m</th></tr></thead>
<tbody>{hist_rows}</tbody>
</table>
</div>
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
_SW_JS = """const CACHE = 'hermes-v1';
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
