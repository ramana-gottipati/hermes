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

import csv
import io
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus

log = logging.getLogger("hermes.dashboard")

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from src.automation import adjust
from src.automation.signals import accum_character_read, is_near_key
from src.core.db import get_conn
from src.pat.web import render_pat
from src.web.wolfe_overlay import SNIPPET as _WF_SNIPPET
from src.web.cpr_overlay import SNIPPET as _CPR_SNIPPET
from src.web.indicators_overlay import SNIPPET as _MA_SNIPPET
from src.web.mep_overlay import SNIPPET as _MEP_SNIPPET
from src.web.stock_chart import SNIPPET as _STOCK_CHART_SNIPPET

router = APIRouter()


# --- Shared shell ----------------------------------------------------------

_THEME = "#0e1116"
_ACCENT = "#1f6feb"

_BASE_CSS = """
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin:0; padding:0; }
body { font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;
       background:var(--bg-1); color:var(--ink); padding:0 0 28px; min-height:100vh; }
header { position:sticky; top:0; z-index:10; background:#0e1116ee;
         backdrop-filter:blur(8px); border-bottom:1px solid var(--bg-3); }
.hrow1{display:flex;align-items:center;gap:10px;padding:9px 14px 6px;}
.hback{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;flex:none;
border:1px solid var(--line-2);border-radius:8px;color:var(--ink);text-decoration:none;font-size:18px;line-height:1;}
.hback:hover{border-color:#484f58;background:var(--bg-2);}
.hrow2{padding:0 8px;}
header .logo { font-size:18px; font-weight:800; letter-spacing:.5px; }
header .dot { width:8px; height:8px; border-radius:50%; background:#2ea043; }
header .date { color:var(--ink-2); font-size:12px; }
header .brand{display:flex;align-items:center;gap:8px;text-decoration:none;color:inherit;flex:none;}
.wsnav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;}
.wsnav::-webkit-scrollbar{display:none;}
.wsnav a{padding:8px 13px;color:var(--ink-2);text-decoration:none;font-size:13px;font-weight:600;white-space:nowrap;border-bottom:2px solid transparent;}
.wsnav a.on{color:var(--ink);border-bottom-color:#3fb950;}
.wsnav a:hover{color:var(--ink);}
.hrow3{padding:0 8px;border-top:1px solid var(--bg-2);}
.subnav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;}
.subnav::-webkit-scrollbar{display:none;}
.subnav a{padding:6px 11px;color:var(--ink-3);text-decoration:none;font-size:12px;font-weight:600;white-space:nowrap;border-bottom:2px solid transparent;}
.subnav a.on{color:var(--ink);border-bottom-color:#1f6feb;}
.subnav a:hover{color:var(--ink);}
.subnav .sgrp{padding:6px 3px 6px 8px;color:#484f58;font-size:11px;font-weight:700;white-space:nowrap;align-self:center;text-transform:uppercase;letter-spacing:.4px;}
.wrap { padding:16px; max-width:760px; margin:0 auto; }
h2 { font-size:16px; margin:18px 0 10px; color:var(--ink); }
.sub { color:var(--ink-2); font-size:12px; margin:-6px 0 12px; }
.card { background:var(--bg-2); border:1px solid var(--line-2); border-radius:10px;
        padding:14px; margin-bottom:10px; }
.kpi { display:flex; gap:10px; flex-wrap:wrap; }
.kpi .box { flex:1; min-width:120px; background:var(--bg-2); border:1px solid var(--line-2);
            border-radius:10px; padding:14px; }
.kpi .num { font-size:24px; font-weight:800; }
.kpi .lbl { color:var(--ink-2); font-size:12px; margin-top:2px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; color:var(--ink-2); font-weight:600; padding:8px 6px;
     border-bottom:1px solid var(--line-2); font-size:11px; text-transform:uppercase;
     letter-spacing:.4px; }
td { padding:9px 6px; border-bottom:1px solid var(--bg-3); }
tr:last-child td { border-bottom:none; }
.sym { font-weight:700; }
/* positive / negative numeric text — the site's ONE value-green/red (was the legacy
   GitHub #3fb950 / #f85149, the most pervasive green on every board's % cells). */
.pos { color:var(--up); } .neg { color:var(--down); } .mut { color:var(--ink-2); }
.pill { display:inline-block; font-size:10px; font-weight:700; padding:2px 7px;
        border-radius:9px; letter-spacing:.4px; }
/* RS-state + DVPT-rank pills — unified to the institutional value palette: ONE green
   (var(--up) #3fd486) and ONE red (var(--down)), translucent-dim backgrounds to match
   the site's .uk-pill treatment. Replaces the legacy GitHub greens (#7ee787/#1f6f3a/
   #225c33) and reds so dashboard pills read the same green as the rest of the site. */
.p-SS{background:var(--up-dim);color:var(--up);} .p-S{background:var(--up-dim);color:var(--up);}
.p-A{background:#2b4f6f;color:#79c0ff;} .p-B{background:#3a3f4b;color:var(--ink);}
.p-C{background:var(--line-2);color:var(--ink-2);} .p-BREAKOUT{background:var(--up-dim);color:var(--up);}
.p-UPTREND{background:var(--up-dim);color:var(--up);} .p-CONSOLIDATING{background:rgba(246,183,60,.14);color:var(--warn);}
.p-DOWNTREND{background:var(--down-dim);color:var(--down);} .p-BREAKDOWN{background:var(--down-dim);color:var(--down);}
/* D43 accumulation/distribution character pills */
.ca-acc{background:var(--up-dim);color:var(--up);} .ca-dist{background:var(--down-dim);color:var(--down);}
.ca-cons{background:#3a3417;color:#ffd99a;} .ca-neu{background:var(--line-2);color:var(--ink-2);}
/* Session 33 — THEME tag chips + the themes browse + accumulating-only filter */
.tchip{display:inline-block;font-size:10px;font-weight:600;padding:2px 7px;border-radius:9px;
  background:#15324a;color:#9ecbff;border:1px solid #1f4d72;margin:1px 3px 1px 0;
  text-decoration:none;line-height:1.6;white-space:nowrap;}
.tchip:hover{background:#1f4d72;color:#cfe8ff;}
.tchip.prop{background:#2b2410;color:#ffd99a;border-color:#5a4a1f;}
.tchip.more{background:var(--bg-3);color:var(--ink-2);border-color:var(--line-2);}
.tchip .tq{opacity:.7;margin-left:1px;}
.theme-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px;}
.trow{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:6px;
  text-decoration:none;color:inherit;border-bottom:1px solid var(--bg-3);}
.trow:last-child{border-bottom:none;} .trow:hover{background:var(--bg-2);}
.trow .tn{font-weight:700;color:var(--ink);min-width:118px;}
.trow .tb{flex:1;font-size:11px;color:var(--ink-2);}
.trow .tc{font-weight:700;color:#58a6ff;min-width:54px;text-align:right;}
.accfilter{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink);
  margin:10px 0 6px;cursor:pointer;user-select:none;}
.ptbl.acc-only tbody tr:not(.is-acc){display:none;}
nav { position:fixed; bottom:0; left:0; right:0; background:var(--bg-1);
      border-top:1px solid var(--bg-3); display:flex; }
nav a { flex:1; text-align:center; padding:10px 4px; color:var(--ink-2);
        text-decoration:none; font-size:11px; }
nav a.active { color:#58a6ff; }
nav a .ic { font-size:20px; display:block; }
input,button { font-family:inherit; }
.search { display:flex; gap:8px; margin-bottom:14px; }
.search input { flex:1; background:var(--bg-1); border:1px solid var(--line-2); color:var(--ink);
                padding:11px 12px; border-radius:8px; font-size:15px; }
.search button { background:#1f6feb; border:none; color:#fff; padding:0 18px;
                 border-radius:8px; font-weight:700; font-size:14px; }
.zone { display:flex; justify-content:space-between; padding:7px 0;
        border-bottom:1px solid var(--bg-3); font-size:14px; }
.zone .lbl { color:var(--ink-2); width:54px; }
.zone .val { font-variant-numeric:tabular-nums; }
.empty { color:var(--ink-2); text-align:center; padding:48px 16px; }
a.row { color:inherit; text-decoration:none; display:block; }
.hsearch { margin-left:auto; flex:none; }
.hsearch input { background:var(--bg-1); border:1px solid var(--line-2); color:var(--ink);
                 padding:6px 10px; border-radius:7px; font-size:13px; width:110px; }
.banner { border-radius:10px; padding:12px 14px; margin-bottom:12px; font-weight:700;
          display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.banner small { font-weight:400; opacity:.9; }
.b-on{background:var(--up-dim);color:var(--ok);border:1px solid rgba(var(--up-rgb),.35);}
.b-off{background:var(--down-dim);color:var(--off);border:1px solid rgba(var(--down-rgb),.35);}
.b-neu{background:#3a3417;color:#ffd99a;border:1px solid #5a4a1f;}
.majgrid { display:grid; grid-template-columns:1fr; gap:8px; }
@media(min-width:560px){ .majgrid{ grid-template-columns:1fr 1fr; } }
.maj { background:var(--bg-2); border:1px solid var(--line-2); border-left:3px solid #1f6feb;
       border-radius:8px; padding:10px 12px; display:block; color:inherit; text-decoration:none; }
.maj .nm { font-weight:700; font-size:14px; }
.maj .rr { display:flex; gap:14px; margin-top:5px; font-size:12px; color:var(--ink-2);
           font-variant-numeric:tabular-nums; flex-wrap:wrap; }
.fbar { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
.fbtn { background:var(--bg-2); border:1px solid var(--line-2); color:var(--ink-2); padding:5px 11px;
        border-radius:14px; font-size:12px; cursor:pointer; }
.fbtn.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chips { display:flex; gap:6px; flex-wrap:wrap; }
.chip { background:var(--bg-2); border:1px solid var(--line-2); border-radius:8px; padding:7px 10px;
        font-size:13px; color:inherit; text-decoration:none; }
.ghdr { font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:var(--ink-2);
        margin:16px 0 8px; font-weight:700; }
.hstrip{display:inline-flex;gap:2px;vertical-align:middle;}
.hstrip .c{width:20px;height:24px;border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px;line-height:1;font-weight:700;}
.hstrip .c small{font-size:7px;opacity:.7;margin-top:1px;font-weight:600;}
/* RS-momentum heat strip — up greens / down reds unified to the value palette
   (was GitHub #7ee787 / #ffa198); the bg darkens by intensity (su brighter than mu). */
.hs-su{background:#1f6f3a;color:var(--up);} .hs-mu{background:#225c33;color:var(--up);}
.hs-fl{background:#5a4a1f;color:#ffd99a;} .hs-md{background:#6f2b2b;color:var(--down);}
.hs-sd{background:#8f1f1f;color:var(--down);} .hs-nd{background:var(--bg-3);color:#484f58;}
.bar{height:7px;background:var(--bg-3);border-radius:4px;overflow:hidden;} .bar>span{display:block;height:100%;background:#1f6feb;}
.grp{color:#58a6ff;} th.rsgrp{border-left:1px solid var(--line-2);} td.rsgrp{border-left:1px solid var(--line-2);}
.dttool{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.dtf{flex:1;min-width:120px;background:var(--bg-1);border:1px solid var(--line-2);color:var(--ink);padding:6px 10px;border-radius:7px;font-size:13px}
.dtx{background:#238636;border:none;color:#fff;padding:6px 12px;border-radius:7px;font-weight:700;font-size:12px;cursor:pointer}
.dtcount{color:var(--ink-2);font-size:12px}
table.dt thead th{cursor:pointer;user-select:none;position:sticky;top:0;background:var(--bg-1);z-index:1}
table.dt thead th.sorta::after{content:" ▲"} table.dt thead th.sortd::after{content:" ▼"}
tr.dt-hide{display:none!important}
/* D33d — strategy thesis badge (stamped on every board) + strategy hub cards */
.sbadge{display:flex;align-items:flex-start;gap:9px;border-radius:9px;padding:9px 12px;margin-bottom:12px;border:1px solid var(--line-2);font-size:12px;}
.sbadge .tag{font-size:10px;font-weight:800;letter-spacing:.5px;white-space:nowrap;padding:2px 8px;border-radius:8px;}
.sbadge .th{color:var(--ink);opacity:.92;line-height:1.35;}
.sb-POS{background:#0d1f33;border-color:#1f4d7a;} .sb-POS .tag{background:#1f6feb;color:#fff;}
.sb-RS{background:#0f2417;border-color:#1f6f3a;} .sb-RS .tag{background:#2ea043;color:#fff;}
.sb-QUAL{background:#241f0d;border-color:#5a4a1f;} .sb-QUAL .tag{background:#bb8009;color:#fff;}
.scards{display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:6px;}
@media(min-width:560px){.scards{grid-template-columns:1fr 1fr 1fr;}}
.scard{display:block;background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:12px;color:inherit;text-decoration:none;border-top:3px solid var(--line-2);}
.scard.sc-POS{border-top-color:#1f6feb;} .scard.sc-RS{border-top-color:var(--cat-rs);} .scard.sc-QUAL{border-top-color:#bb8009;}
.scard.sc-CPR{border-top-color:#8957e5;}
.scard .nm{font-weight:800;font-size:14px;} .scard .th{color:var(--ink-2);font-size:11px;margin:4px 0 8px;line-height:1.3;}
.scard .ct{font-size:13px;font-weight:700;color:var(--ink);} .scard .ct small{color:var(--ink-2);font-weight:400;}
/* CPR (Structure pillar, D53) — pattern glyphs, ★ conviction tier, D·W·M strip */
.cpg{font-weight:800;font-size:12px;} .cp-bull{color:var(--up);} .cp-bear{color:var(--down);} .cp-none{color:var(--ink-3);}
.cp-tier{color:#e3b341;font-weight:800;letter-spacing:1px;white-space:nowrap;}
.cprstrip{display:inline-flex;gap:3px;vertical-align:middle;}
.cprstrip .c{min-width:30px;padding:2px 4px;border-radius:4px;background:var(--bg-2);border:1px solid var(--bg-3);display:flex;flex-direction:column;align-items:center;line-height:1.15;}
.cprstrip .c .w{font-size:11px;font-weight:700;font-variant-numeric:tabular-nums;}
.cprstrip .c small{font-size:7px;opacity:.6;font-weight:600;}
.cprstrip .c.nw{background:#10241a;border-color:#1f6f3a;} .cprstrip .c.nw .w{color:#7ee787;}
.cprstrip .c.up{box-shadow:inset 0 -2px 0 var(--up);} .cprstrip .c.dn{box-shadow:inset 0 -2px 0 var(--down);}
.cprpanel{background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;padding:12px;margin-bottom:6px;}
.cprpanel table{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;}
.cprpanel th,.cprpanel td{text-align:right;padding:5px 8px;border-bottom:1px solid var(--bg-3);white-space:nowrap;}
.cprpanel th:first-child,.cprpanel td:first-child{text-align:left;}
.cprverdict{margin-top:9px;font-size:13px;color:var(--ink);line-height:1.4;}
.tabbar{display:flex;gap:6px;margin:4px 0 12px;border-bottom:1px solid var(--line-2);}
.tabbar a{padding:7px 14px;font-size:13px;font-weight:700;color:var(--ink-2);text-decoration:none;border-bottom:2px solid transparent;}
.tabbar a.on{color:var(--ink);border-bottom-color:#8957e5;}
/* D54 — full-bleed data workspace with a COMFORTABLE gutter (D-UI-10) */
.wrap.wide{max-width:1900px;margin:0 auto;padding:14px clamp(12px,4vw,56px);}
/* D54 — frozen-pane data grid: ONE scroll viewport owns BOTH axes so the header
   band AND the Symbol column stay fixed while scrolling down AND across. */
.scrwrap{overflow:auto;max-height:calc(100vh - 230px);border:1px solid var(--line-2);border-radius:10px;background:var(--bg-1);-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}
table.scr{width:100%;min-width:max-content;border-collapse:separate;border-spacing:0;font-size:12px;table-layout:fixed;}
table.scr th,table.scr td{white-space:nowrap;border-bottom:1px solid #1c2128;padding:6px 10px;text-align:right;}
table.scr th.l,table.scr td.l{text-align:left;}
table.scr td.num,table.scr th.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum";}
table.scr td.bold{font-weight:700;}
table.scr td.gsep,table.scr th.gsep{border-left:1px solid #262c36;}
table.scr thead tr.sgrp th{position:sticky;top:0;z-index:3;height:26px;background:var(--bg-1);color:var(--ink-3);font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;text-align:left;border-bottom:1px solid var(--line-2);border-left:1px solid #262c36;padding:0 10px;}
table.scr thead tr.scol th{position:sticky;top:26px;z-index:3;background:var(--bg-1);color:var(--ink-2);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid var(--line-2);cursor:pointer;padding:6px 10px;}
table.scr .fz{position:sticky;left:0;z-index:2;background:var(--bg-1);border-right:1px solid var(--line-2);text-align:left;}
table.scr thead tr.sgrp th.fz,table.scr thead tr.scol th.fz{z-index:6;}
table.scr tbody .fz{font-weight:700;}
table.scr tbody tr:nth-child(even) td{background:rgba(255,255,255,.014);}
table.scr tbody tr:nth-child(even) td.fz{background:#0f151b;}
table.scr tbody tr:hover td{background:#1c2230!important;}
.scrwrap.scrolled table.scr .fz{box-shadow:8px 0 12px -6px rgba(0,0,0,.55);}
.h-pos3{background:rgba(63,185,80,.22)!important;} .h-pos2{background:rgba(63,185,80,.13)!important;} .h-pos1{background:rgba(63,185,80,.06)!important;}
.h-neg1{background:rgba(248,81,73,.07)!important;} .h-neg2{background:rgba(248,81,73,.14)!important;} .h-neg3{background:rgba(248,81,73,.22)!important;}
/* column-group hide = ONE class on the table (single reflow, no per-cell JS) */
table.scr.hide-conv .g-conv,table.scr.hide-pos .g-pos,table.scr.hide-mep .g-mep,table.scr.hide-key .g-key,table.scr.hide-char .g-char,table.scr.hide-rs .g-rs,table.scr.hide-cpr .g-cpr,table.scr.hide-cci .g-cci,table.scr.hide-themes .g-themes,table.scr.hide-qual .g-qual,table.scr.hide-ctx .g-ctx{display:none;}
/* LAG FIX (the Nifty-500 toggle hang): with table-layout:fixed the columns no longer
   re-solve their widths from 498 rows of content on every toggle. A JS-built <colgroup>
   gives each column an explicit width + tags it with its group; collapsing the col to 0
   here removes the gap a hidden group would otherwise leave under fixed layout. */
table.scr.hide-conv col.cg-conv,table.scr.hide-pos col.cg-pos,table.scr.hide-mep col.cg-mep,table.scr.hide-key col.cg-key,table.scr.hide-char col.cg-char,table.scr.hide-rs col.cg-rs,table.scr.hide-cpr col.cg-cpr,table.scr.hide-cci col.cg-cci,table.scr.hide-themes col.cg-themes,table.scr.hide-qual col.cg-qual,table.scr.hide-ctx col.cg-ctx{width:0!important;}
/* CPR-confirmed gate: show only rows carrying a CPR reversal tier (one class) */
table.scr.cpr-only tbody tr:not(.has-cpr){display:none;}
/* D54 Phase 2 — "the instrument": inline static micro-viz readouts (D-UI-16).
   The viz sits BESIDE the kept sortable numeric columns (D-UI-1). */
.mv{vertical-align:middle;display:inline-block;}
table.scr td.inst{padding:3px 8px 3px 10px;}
.kt-in{color:var(--series-4);} .kt-ext{color:#d29922;} .kt-disc{color:#58a6ff;}
/* Row windowing (perf hand-off Step 2) — Ramana confirmed the 498-row × 4-SVG
   grid scrolls heavy, so the browser now skips layout+paint of OFF-SCREEN rows.
   `contain-intrinsic-size:auto` makes it REMEMBER each row's real size once seen,
   so the scrollbar stays stable. The column-width jitter that first made me defer
   this is killed by pinning the frozen Symbol column + flooring numeric cells, so
   widths can't shift as rows page in. All additive CSS, reversible. */
/* NB: exclude the virtualizer's .vspacer rows — content-visibility on a tall
   off-screen spacer can collapse its height and drift the scroll. Data rows keep
   it (harmless once virtualized; a cushion if the virtualizer ever safety-nets). */
table.scr tbody tr:not(.vspacer){content-visibility:auto;contain-intrinsic-size:auto 34px;}
table.scr .fz{width:116px;min-width:116px;max-width:116px;overflow:hidden;text-overflow:ellipsis;}
table.scr td.num,table.scr th.num{min-width:46px;}
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
    "markets": "markets", "sectors": "markets", "rs": "markets", "ratio": "markets", "compare": "markets",
    # Leaders/"Strength" is Markets content (RS), per src.web.lens_registry — NOT Strategies.
    "leaders": "markets", "laggards": "markets",
    "themes": "themes", "theme": "themes", "tags-review": "themes",
    "screener": "screener",
    "strategies": "strategies", "scan": "strategies", "stocks": "strategies",
    "conviction": "strategies",
    "workbench": "strategies", "stock": "strategies", "cpr": "strategies",
    "mep": "strategies", "launchpad": "strategies", "concalls": "strategies", "wolfe": "strategies",
    "dashboard": "tracker", "portfolios": "tracker", "watchlists": "tracker",
    "performance": "tracker", "tracker": "tracker", "track": "tracker",
    "pat": "pat",
}


def _nav(active: str) -> str:
    cur = _WS.get(active, active)
    items = [("markets", "/dash/markets", "Markets"),
             ("themes", "/dash/themes", "Themes"),
             ("screener", "/dash/screener", "Screener"),
             ("strategies", "/dash/strategies", "Strategies"),
             ("tracker", "/dash/dashboard", "Tracker"),
             ("pat", "/dash/pat", "Pat")]
    out = ['<div class="wsnav">']
    for key, href, label in items:
        out.append(f'<a class="{"on" if key == cur else ""}" href="{href}">{label}</a>')
    out.append('</div>')
    return "".join(out)


# Per-workspace sub-navigation (D-UI-18) — rendered by _shell beneath the top
# workspace tabs so every page exposes its sibling screens (the biggest
# findability fix). Tracker keeps its own _track_subnav, Pat its own in-page
# nav, the Screener its scope/view bar — those (and home) render no strip here.
# Markets' Rotation group surfaces the three rotation lenses, de-orphaning
# /dash/rsband. Purely additive: every route keeps its URL (D-UI-24).
_SUBNAV = {
    "markets": [
        ({"markets"}, "/dash/markets", "Overview"),
        ({"sectors", "rs"}, "/dash/sectors", "Sectors"),
        ({"leaders", "laggards"}, "/dash/leaders", "Strength"),
        (None, None, "Rotation"),
        ({"rrg"}, "/dash/rrg", "Map"),
        ({"rotation"}, "/dash/rotation", "Weather"),
        ({"rsband"}, "/dash/rsband", "Band"),
        ({"compare"}, "/dash/compare", "Compare"),
    ],
    "strategies": [
        ({"strategies"}, "/dash/strategies", "Hub"),
        ({"conviction"}, "/dash/conviction", "Conviction"),
        ({"stocks", "scan", "stock"}, "/dash/stocks", "Positioning"),
        ({"mep"}, "/dash/mep", "Accumulation"),
        ({"cpr"}, "/dash/cpr", "Structure"),
        ({"workbench"}, "/dash/workbench", "Workbench"),
        ({"concalls"}, "/dash/concalls", "Credibility"),
        ({"launchpad"}, "/dash/launchpad", "Launchpad"),
        ({"wolfe"}, "/dash/wolfe", "Wolfe"),
    ],
    "themes": [
        ({"themes", "theme"}, "/dash/themes", "Browse"),
        ({"tags-review"}, "/dash/tags-review", "Review"),
    ],
}


def _subnav(active: str) -> str:
    items = _SUBNAV.get(_WS.get(active, active))
    if not items:
        return ""
    out = ['<div class="subnav">']
    for keys, href, label in items:
        if href is None:
            out.append(f'<span class="sgrp">{label}</span>')
        else:
            on = "on" if keys and active in keys else ""
            out.append(f'<a class="{on}" href="{href}">{label}</a>')
    out.append('</div>')
    return "".join(out)


def _shell(title: str, body: str, active: str, latest_date: str = "", wide: bool = False) -> str:
    # In-app Back on every page EXCEPT home (active="dash") — home is the root, so
    # there's nothing to go back to. history.back() with a /dash fallback (never strands).
    back_btn = ("" if active == "dash" else
                '<a class="hback" href="/dash" title="Back" aria-label="Back" '
                'onclick="if(window.history.length>1){window.history.back();return false;}">&#8592;</a>')
    sub = _subnav(active)
    subrow = f'<div class="hrow3">{sub}</div>' if sub else ''
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
    {back_btn}
    <a href="/dash" class="brand"><span class="dot"></span><span class="logo">pat<span style="color:#3fb950">e</span>arn</span></a>
    <form class="hsearch" action="/dash/stock" method="get" autocomplete="off">
      <input name="sym" placeholder="search ticker…" autocapitalize="characters"/>
    </form>
  </div>
  <div class="hrow2">{_nav(active)}</div>
  {subrow}
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
    # CL-CHR-11: escape `"` too (→ &quot;). `_esc` is used inside double-quoted href/title
    # attributes across dashboard + cockpit (cockpit imports it as D._esc); a stored URL or
    # name with a `"` would otherwise break out of the attribute. `&` stays first so the
    # `&quot;` we introduce is not itself re-escaped. JS single-quote contexts (onclick='…')
    # are unaffected — we don't touch `'`.
    return ((str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _q(s) -> str:
    return quote_plus(str(s) if s is not None else "")


# CL-DASH-15: a corrupt snapshot_json/alerts_json used to vanish into a bare `except: {}`.
# Parse through here instead: a malformed blob is COUNTED + logged at WARNING (so silent
# data corruption surfaces in the logs) while the caller still degrades to {} and renders.
_JSON_PARSE_FAILURES = {"snapshot_json": 0, "alerts_json": 0}


def _load_json_field(raw, field: str, default):
    """Parse a stored JSON column; on failure log+count and return `default`. Empty/NULL is
    a normal empty value (not a failure)."""
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        _JSON_PARSE_FAILURES[field] = _JSON_PARSE_FAILURES.get(field, 0) + 1
        log.warning("corrupt %s (#%d this process): %s", field,
                    _JSON_PARSE_FAILURES[field], e)
        return default


def _tag_chips(labels, link: bool = True, proposed=(), wrap: bool = False, cap=None) -> str:
    """Render theme labels as small chips (session 33). `proposed` = labels that
    are AI-proposed (not yet approved) — styled distinctly + marked with '?'.
    `cap` shows the first N then a '+M' chip. `wrap` boxes them in a .chips row.
    Canonical chip renderer — reused by the stock page, screener, participant
    tables and the themes pages (cockpit calls D._tag_chips)."""
    labels = list(labels or [])
    if not labels:
        return ""
    proposed = set(proposed or ())
    extra = 0
    if cap and len(labels) > cap:
        extra = len(labels) - cap
        labels = labels[:cap]
    parts = []
    for lab in labels:
        is_prop = lab in proposed
        cls = "tchip prop" if is_prop else "tchip"
        txt = _esc(lab) + ('<span class="tq">?</span>' if is_prop else "")
        if link:
            parts.append(f'<a class="{cls}" href="/dash/theme?tag={_q(lab)}">{txt}</a>')
        else:
            parts.append(f'<span class="{cls}">{txt}</span>')
    if extra:
        parts.append(f'<span class="tchip more">+{extra}</span>')
    inner = "".join(parts)
    return f'<div class="chips">{inner}</div>' if wrap else inner


# NaN/inf render as the em-dash, same as None — a NaN slips through `is not None`
# (e.g. a 0/0 ratio upstream) and would otherwise print literal "nan%"/"inf".
# `v != v` is True only for NaN; the inf check catches ±inf without importing math.
def _nonfinite(v) -> bool:
    return v is None or v != v or v in (float("inf"), float("-inf"))


def _pct(v, decimals=1) -> str:
    if _nonfinite(v):
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    return f'<span class="{cls}">{v:+.{decimals}f}%</span>'


def _num(v, decimals=2) -> str:
    if _nonfinite(v):
        return '<span class="mut">—</span>'
    return f"{v:,.{decimals}f}"


def _safe_int(v, default=0) -> int:
    """int() that never raises on NaN/inf/None/junk (which would 500 a page).
    A NaN/inf DVPT or delivery-value sneaks through SQLite as a float and would
    blow up a plain int(); coerce defensively to `default`."""
    if _nonfinite(v):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# RS trend-state labels are stored as the uppercase enum (UPTREND / BREAKOUT /
# CONSOLIDATING / DOWNTREND / BREAKDOWN) — used BOTH as the .p-{STATE} CSS class
# AND, historically, sliced to 5 chars for the visible text ("UPTRE"/"BREAK"/…),
# which read as broken. This renders the whole word (title-case) for the user while
# the class stays the raw enum. Passes through "—"/empty and any unknown value.
def _state_label(st) -> str:
    s = ("" if st is None else str(st)).strip()
    if not s or s == "—":
        return s or "—"
    return s.replace("_", " ").title()


def _rs_strip(s1, s3, s6, s12, s18=None, s24=None) -> str:
    """Multi-timeframe RS heat strip from the slope_% of the ratio.

    Per cell: None→grey ·; ≥+3 strong-up ▲; >+1 mild-up ▲; |x|≤1 flat ▬;
    <-1 mild-down ▼; ≤-3 strong-down ▼. Renders [1m][3m][6m][12m] left→right, and
    — when the long windows are supplied — [18m][24m] too (base depth / run height).
    """
    cells = []
    pairs = [(s1, "1m"), (s3, "3m"), (s6, "6m"), (s12, "12m")]
    if s18 is not None or s24 is not None:
        pairs += [(s18, "18m"), (s24, "24m")]
    for v, lbl in pairs:
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


def _idx_ret(conn, index_name, anchor_date, days) -> "float | None":
    """An index's %-return over `days` calendar days ending at anchor_date, read
    on the fly from index_rows close_value. Used for the 18m/24m reconcile windows
    that index_signals doesn't pre-compute (it stops at ret_12m)."""
    from datetime import datetime as _dt, timedelta as _td
    cut = (_dt.strptime(anchor_date, "%Y-%m-%d") - _td(days=days)).strftime("%Y-%m-%d")
    now = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND trade_date<=? "
                       "ORDER BY trade_date DESC LIMIT 1", (index_name, anchor_date)).fetchone()
    base = conn.execute("SELECT close_value FROM index_rows WHERE index_name=? AND trade_date<=? "
                        "ORDER BY trade_date DESC LIMIT 1", (index_name, cut)).fetchone()
    if now and base and base["close_value"]:
        return (now["close_value"] / base["close_value"] - 1) * 100
    return None


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


def _cci_latest_by_sym(conn, symbols) -> dict:
    """{sym: latest concall_scores row} for the given symbols (Management Credibility
    group, P5). One grouped MAX-join, keyed IN fetch. Empty {} if no CCI data yet."""
    syms = list(symbols)
    if not syms:
        return {}
    ph = ",".join("?" for _ in syms)
    try:
        rows = conn.execute(
            f"""SELECT s.* FROM concall_scores s
                JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x
                  ON x.symbol=s.symbol AND x.m=s.last_updated
                WHERE s.symbol IN ({ph})""", syms).fetchall()
    except Exception:
        return {}
    return {r["symbol"]: dict(r) for r in rows}


def _cci_screener_cells(sc) -> tuple:
    """The 4 screener CCI-group <td>s (Management Credibility) for one symbol + a
    has-cci flag. Measurable-led (D61): tier · forward · deterioration · ⛔veto —
    the avoid-tape essentials beside the other pillars; the deep ledger lives on the
    stock dossier + /dash/concalls. '—' cells when the name has no concall data."""
    if not sc:
        return ('<td class="l gsep g-cci mut">—</td><td class="g-cci mut">—</td>'
                '<td class="num g-cci mut">—</td><td class="g-cci mut">—</td>'
                '<td class="num g-cci mut">—</td>'), False
    tier = sc.get("tier") or "—"
    tcls = "pos" if tier in ("A+", "A") else ("neg" if tier == "D" else "mut")
    det = sc.get("deterioration_score") or 0
    det_td = (f'<td class="num g-cci"><span class="neg">{int(det)}</span></td>'
              if det else '<td class="num g-cci mut">0</td>')
    if sc.get("veto_active"):
        veto_td = (f'<td class="g-cci l"><span class="neg" '
                   f'title="{_esc(sc.get("veto_reason") or "")}">⛔</span></td>')
    else:
        veto_td = '<td class="g-cci l mut">—</td>'
    nc = sc.get("n_concalls") or 0
    nc_td = (f'<td class="num g-cci">{nc}</td>' if nc else '<td class="num g-cci mut">0</td>')
    tds = (f'<td class="l gsep g-cci"><span class="{tcls}">{_esc(tier)}</span></td>'
           f'<td class="g-cci l">{_cci_fwd(sc.get("forward_direction"))}</td>'
           + det_td + veto_td + nc_td)
    return tds, True


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


# --- "The instrument" — inline static micro-viz (D54 Phase 2, D-UI-16) -------
# Each returns a self-contained inline SVG string computed ONCE in Python (no
# per-cell JS, no chart lib — lighter, server-rendered). They turn the buried
# 88-col stock_signals data into scannable shapes that sit BESIDE the raw values
# (the sortable numeric columns are kept — D-UI-1). All degrade to "—" on NULL.
_KEY_BAND = (-1.0, 5.0)   # the −1…+5% launch band (mirrors signals.py D44)


def _mv_ladder(dvpt, p1, p2, p3, p6, p12) -> str:
    """DVPT-vs-power ladder: a track with 5 notches (P1M…P12M, green = beaten by
    today's DVPT), a green fill to today + a ▲ marker. Surfaces power_dvpt_* +
    p_score as one shape (the rank pill + ×power ride the adjacent columns)."""
    if not dvpt:
        return '<span class="mut">—</span>'
    ps = [p1, p2, p3, p6, p12]
    vals = [v for v in ps if v]
    maxv = max([dvpt] + vals)
    if not maxv:
        return '<span class="mut">—</span>'
    W, x0, x1, ty, th = 116, 3, 104, 15, 6
    def sx(v):
        return x0 + (v / maxv) * (x1 - x0)
    ticks = "".join(
        f'<line x1="{sx(v):.1f}" y1="{ty-4}" x2="{sx(v):.1f}" y2="{ty+th+4}" '
        f'style="stroke:{"var(--up)" if dvpt >= v else "var(--ink-3)"}" stroke-width="1"/>'
        for v in ps if v)
    fw, tx = sx(dvpt) - x0, sx(dvpt)
    return (f'<svg class="mv" width="{W}" height="26" viewBox="0 0 {W} 26" aria-hidden="true">'
            f'<rect x="{x0}" y="{ty}" width="{x1-x0}" height="{th}" rx="3" style="fill:var(--bg-3)"/>'
            f'<rect x="{x0}" y="{ty}" width="{fw:.1f}" height="{th}" rx="3" style="fill:var(--up)"/>'
            f'{ticks}<path d="M{tx-4:.1f},{ty-8} L{tx+4:.1f},{ty-8} L{tx:.1f},{ty-2} Z" '
            f'style="fill:var(--up)"/></svg>')


def _mv_keyband(gap) -> str:
    """Key-price launch-band gauge: a ±15% axis with the −1…+5% launch band shaded;
    a coloured marker at gap_to_key_p3m (green in-band 🎯 / amber extended / blue
    discount). Surfaces the value-weighted institutional key-price entry read."""
    if gap is None:
        return '<span class="mut">—</span>'
    W, x0, x1, ay, lo, hi = 90, 3, 87, 14, -15.0, 15.0
    def sx(v):
        return x0 + ((max(lo, min(hi, v)) - lo) / (hi - lo)) * (x1 - x0)
    inb = _KEY_BAND[0] <= gap <= _KEY_BAND[1]
    col = "var(--up)" if inb else ("var(--warn)" if gap > _KEY_BAND[1] else "var(--accent)")
    b0, b1, m, z = sx(_KEY_BAND[0]), sx(_KEY_BAND[1]), sx(gap), sx(0)
    return (f'<svg class="mv" width="{W}" height="26" viewBox="0 0 {W} 26" aria-hidden="true">'
            f'<rect x="{x0}" y="{ay-4}" width="{x1-x0}" height="8" rx="2" style="fill:var(--bg-2);stroke:var(--bg-3)"/>'
            f'<rect x="{b0:.1f}" y="{ay-4}" width="{b1-b0:.1f}" height="8" fill="#16341f"/>'
            f'<line x1="{z:.1f}" y1="{ay-6}" x2="{z:.1f}" y2="{ay+6}" style="stroke:var(--ink-3)" stroke-dasharray="1 1"/>'
            f'<line x1="{m:.1f}" y1="{ay-7}" x2="{m:.1f}" y2="{ay+7}" style="stroke:{col}" stroke-width="2"/>'
            f'<circle cx="{m:.1f}" cy="{ay}" r="2.4" style="fill:{col}"/></svg>')


def _mv_triglyph(tcr, duo, hh) -> str:
    """Character triglyph (D43): 3 diverging micro-bars composing the ACCUM/DIST
    read — WHO (trade-count concentration), WHICH-WAY (delivery up/down skew),
    CONTEXT (distance from 52w high). Right/green = the accumulation lean."""
    def cl(v):
        return max(-1.0, min(1.0, v))
    axes = [cl((1 - tcr) * 1.4) if tcr is not None else None,   # WHO: <1 concentrating
            cl((duo - 1) * 1.0) if duo is not None else None,   # WAY: >1 up-skew
            cl((hh + 10) / 10) if hh is not None else None]     # CTX: near 52w-high
    W, cx, half, bh, ys = 42, 21, 17, 5, (5, 12, 19)
    bars = []
    for s, y in zip(axes, ys):
        if s is None:
            bars.append(f'<rect x="{cx-1}" y="{y-1}" width="2" height="2" style="fill:var(--line-2)"/>')
            continue
        w = abs(s) * half
        x = cx if s >= 0 else cx - w
        col = "var(--ink-4)" if abs(s) < 0.12 else ("var(--up)" if s > 0 else "var(--down)")
        bars.append(f'<rect x="{x:.1f}" y="{y-2.5:.0f}" width="{max(w,1):.1f}" '
                    f'height="{bh}" rx="1" style="fill:{col}"/>')
    return (f'<svg class="mv" width="{W}" height="26" viewBox="0 0 {W} 26" aria-hidden="true">'
            f'<line x1="{cx}" y1="2" x2="{cx}" y2="24" style="stroke:var(--line-2)"/>{"".join(bars)}</svg>')


def _mv_rsspark(b1, b3, b6, b12) -> str:
    """RS sparkline: the rs-vs-broad slope trajectory 12m→1m (oldest→newest) as a
    tiny polyline — green rising / red falling. Pairs with the heat strip; degrades
    to a dot when slopes are NULL (e.g. mid RS-recompute)."""
    have = [(i, v) for i, v in ((0, b12), (1, b6), (2, b3), (3, b1)) if v is not None]
    if len(have) < 2:
        return '<span class="mut" style="font-size:11px">·</span>'
    vs = [v for _, v in have] + [0.0]
    mn, mx = min(vs), max(vs)
    W, x0, x1, y0, y1 = 50, 2, 48, 3, 19
    def sx(i):
        return x0 + (i / 3) * (x1 - x0)
    def sy(v):
        return (y0 + y1) / 2 if mx == mn else y1 - ((v - mn) / (mx - mn)) * (y1 - y0)
    d = " ".join(f'{"L" if k else "M"}{sx(i):.1f},{sy(v):.1f}'
                 for k, (i, v) in enumerate(have))
    last = b1 if b1 is not None else have[-1][1]
    col = "var(--up)" if last > 0 else "var(--down)"
    return (f'<svg class="mv" width="{W}" height="22" viewBox="0 0 {W} 22" aria-hidden="true">'
            f'<line x1="{x0}" y1="{sy(0):.1f}" x2="{x1}" y2="{sy(0):.1f}" style="stroke:var(--line-2)" '
            f'stroke-dasharray="2 2"/><path d="{d}" fill="none" style="stroke:{col}" stroke-width="1.5"/></svg>')


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
    from src.web.cockpit import render_home
    return HTMLResponse(_shell("patearn — Indian-equity strategy cockpit",
                               render_home(sig_date, idx_date), "dash", sig_date or "", wide=True))


@router.get("/dash/mep", response_class=HTMLResponse)
def dash_mep(dir: str = Query("")) -> HTMLResponse:
    """MEP — SIGNED accumulation AND distribution (descriptor, D62). The real
    destination behind every accumulation/distribution link; DVPT keeps /dash/stocks.
    ``dir=accum|distrib`` pre-selects one side so the Net-accumulation / Distribution-
    watch home cards land on THEIR rows. Full-bleed cockpit render (cockpit.render_mep)."""
    from src.web.cockpit import render_mep
    sig_date, _ = _latest_dates()
    return HTMLResponse(_shell("Accumulation & Distribution · MEP · patearn",
                               render_mep(focus=dir), "mep", sig_date or "", wide=True))


@router.get("/dash/conviction", response_class=HTMLResponse)
def dash_conviction(limit: int = Query(60, ge=10, le=200)) -> HTMLResponse:
    """D45 — the cross-pillar Conviction shortlist: RS leader (D33c) + institutions
    accumulating now (D43 ACCUMULATION) + the D44 entry read, with pt14 quality as
    confirmation. Read-only synthesis over existing data; sortable/exportable `.dt`.
    Full-bleed cockpit render (cockpit.render_conviction); legacy body kept dead."""
    from src.web.cockpit import render_conviction
    sig_date, _ = _latest_dates()
    return HTMLResponse(_shell("Conviction · patearn", render_conviction(limit),
                               "conviction", sig_date or "", wide=True))


@router.get("/dash/pat", response_class=HTMLResponse)
def dash_pat(request: Request, flow: str = Query(""), explain: str = Query(""), q: str = Query(""),
             sector: str = Query(""), strength: str = Query(""), entry: str = Query(""),
             align: str = Query(""), val: str = Query(""), qual: str = Query(""),
             grow: str = Query(""), bs: str = Query(""), own: str = Query(""),
             sym: str = Query(""), new: str = Query("")):
    """Pat — natural-language guided search + the data glossary (src/pat).

    L1↔L4 contract (src/pat/threads.py): forward a per-browser ``pat_tid`` cookie into
    render_pat so Pat has TRUE multi-turn memory — mint one on first visit, persist it
    httponly + samesite=lax for 30 days. The cookie is the only added state; render_pat
    stays inert for the default tid="" everywhere else. ``new=1`` (the 'start over' chip)
    clears the thread inside render_pat before rendering. A malformed/forged cookie is
    rejected (``threads._valid``) and replaced with a fresh server-minted id."""
    from src.pat import threads as _threads
    tid = _threads._valid(request.cookies.get("pat_tid", "")) or _threads.new_tid()
    with get_conn() as conn:
        body = render_pat(flow=flow, explain=explain, q=q, sector=sector,
                          strength=strength, entry=entry, align=align,
                          val=val, qual=qual, grow=grow, bs=bs, own=own, sym=sym,
                          conn=conn, tid=tid, new=new)
    resp = HTMLResponse(_shell("Pat — patearn", body, "pat"))
    resp.set_cookie("pat_tid", tid, max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
    return resp


@router.get("/dash/markets", response_class=HTMLResponse)
def dash_markets() -> HTMLResponse:
    _, idx_date = _latest_dates()
    from src.web.cockpit import render_markets
    return HTMLResponse(_shell("Markets · patearn", render_markets(idx_date),
                               "markets", idx_date or "", wide=True))


@router.get("/dash/sectors", response_class=HTMLResponse)
def dash_sectors() -> HTMLResponse:
    """Full-bleed cockpit render (cockpit.render_sectors); legacy body kept dead."""
    from src.web.cockpit import render_sectors
    _, idx_date = _latest_dates()
    return HTMLResponse(_shell("Sectors · patearn", render_sectors(), "sectors", idx_date or "", wide=True))


@router.get("/dash/rs", response_class=HTMLResponse)
def dash_rs() -> RedirectResponse:
    """Legacy cross-sector RS cockpit — SUPERSEDED by the canonical /dash/rs-hub.
    Redirect (the lens registry already aliases `rs`→rs-hub); orphaned-screen panel
    decision 2026-07-02 to collapse the duplicate RS surface. Legacy render in git."""
    return RedirectResponse("/dash/rs-hub", status_code=307)


@router.get("/dash/leaders", response_class=HTMLResponse)
def dash_leaders() -> HTMLResponse:
    """D33c composite screen — 'strong-in-strong' leaders + 'weak-in-weak'
    laggards: a stock whose RS vs its sector AND vs the broad market AND its
    sector's own RS vs broad are ALL aligned (up = leader, down = laggard).
    Full-bleed cockpit render (cockpit.render_leaders); legacy body kept dead."""
    from src.web.cockpit import render_leaders
    sig_date, _ = _latest_dates()
    return HTMLResponse(_shell("Leaders · patearn", render_leaders(), "leaders", sig_date or "", wide=True))


@router.get("/dash/scan", response_class=HTMLResponse)
def dash_scan(limit: int = Query(25, ge=5, le=60)) -> RedirectResponse:
    # Legacy DVPT trigger scan → SUPERSEDED by /dash/stocks (Positioning); the lens
    # registry already aliases `scan`→stocks. Orphaned-screen panel decision 2026-07-02
    # to remove the ranked-list duplicate (also drops a prescriptive framing). Legacy
    # body below is retained (unreachable) for git-diff clarity.
    return RedirectResponse("/dash/stocks", status_code=307)
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
<table class="dt">
<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>Close</th><th>Δhot</th><th>Near-P</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""
    return HTMLResponse(_shell("Scan · patearn", body, "scan", sig_date or ""))


@router.get("/dash/stocks", response_class=HTMLResponse)
def dash_stocks(sector: str = Query(""), limit: int = Query(40, ge=10, le=120),
                period: str = Query("d"), view: str = Query("")) -> HTMLResponse:
    sig_date, _ = _latest_dates()
    sector = sector.strip()
    view = view.strip().lower()   # "stealth" = the Stealth-accumulation card's full screen
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
                # shared column list for BOTH the default and the stealth view, so
                # the extra (default-hidden) columns are declared in exactly one place.
                _SEL = """s.symbol, s.trigger_rank rank, s.r_score, s.p_score,
                              s.is_ath_dvpt ath, s.price_vs_hot_avg_pct pvh,
                              s.next_p_above nextp, s.gap_to_next_p_pct gap, b.close,
                              s.accum_character ch, s.delivery_value_today dvt,
                              s.trade_count_ratio_1m_6m tcr,
                              s.delivery_value_per_trade dvpt,
                              s.power_dvpt_1m p1, s.power_dvpt_3m p3,
                              s.power_dvpt_6m p6, s.power_dvpt_12m p12,
                              s.gap_to_key_p1m gk1, s.gap_to_key_p3m gk3,
                              s.gap_to_key_p6m gk6, s.gap_to_key_p12m gk12,
                              s.rs_rank rsr, s.rs_vs_broad_today rsb, s.rs_vs_sector_today rss,
                              s.pct_from_52w_high p52, s.accum_price_drift_3m adr,
                              s.deliv_updown_ratio_3m dur, s.key_price_p3m kp3, s.key_price_p6m kp6"""
                if view == "stealth":
                    # AUD backlink fix: the "Stealth accumulation" home card's FULL
                    # screen must show the SAME population it teases — accumulation
                    # character + A+ pressure + concentrated churn + still ≥10% off the
                    # 52w-high — NOT the generic delivery-pivot top-N (which drops the
                    # card's symbols entirely). Mirrors cockpit.render_home's query.
                    rows = [dict(r) for r in conn.execute(
                        f"""SELECT {_SEL}
                           FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                           WHERE s.trade_date=? AND s.accum_character='ACCUMULATION'
                             AND COALESCE(s.p_score,0)>=3
                             AND COALESCE(s.trade_count_ratio_1m_6m,99)<=1.1
                             AND s.pct_from_52w_high<=-10 {_SCAN_FILTERS}
                           ORDER BY COALESCE(s.p_score,-1) DESC,
                                    COALESCE(s.pct_from_52w_high,0) ASC
                           LIMIT ?""",
                        (sig_date, limit)).fetchall()]
                else:
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
                        f"""SELECT {_SEL}
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
    elif view == "stealth":
        head = ('<h2>🕵 Stealth accumulation</h2>'
                '<div class="sub">Quiet, concentrated accumulation still ≥10% off the 52-week high — '
                'the full list behind the home card (accumulation character · A+ pressure · low churn). '
                '<a class="row" style="display:inline" href="/dash/stocks">← all stocks</a></div>')
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
                         f'<a class="row" style="display:inline" href="/dash/index?idx={_q(sector)}">'
                         f'See its index page →</a></div>')
            else:
                head += (f'<div class="card sub">No constituents tracked for this index — it\'s a '
                         f'factor/thematic index, not a sector. '
                         f'<a class="row" style="display:inline" href="/dash/index?idx={_q(sector)}">'
                         f'See its index page →</a></div>')
    else:
        # Heading matches the nav lens label "Stocks" (lens_registry Lens("stocks",
        # "Stocks",…)) so nav-highlight, <h2> and <title> all read one name. The DVPT
        # "positioning" concept lives in the POSITIONING badge strapline below, not here.
        head = ('<h2>Stocks</h2>'
                '<div class="sub">Layered DVPT triggers (today). Filter, then tap a symbol.</div>')

    js = ""
    if period == "d":
        # formatters for the extra (default-hidden) columns — mirror Workbench.
        def _kpf(v):
            return f'₹{v:,.1f}' if v is not None else '—'

        def _nfx(v, d=0):
            return _num(v, d) if v is not None else '—'

        def _gapx(g):
            if g is None:
                return '<td class="mut">—</td>'
            sty = ' style="background:var(--up-dim);color:var(--up);font-weight:700"' if is_near_key(g) else ''
            return f'<td{sty}>{g:+.1f}%</td>'
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
            pow3_cr = f'{r["p3"]/1e7:,.1f}' if r["p3"] else "—"
            extra = (
                f'<td class="mut">{_nfx(r["rsr"],0)}</td>'
                f'<td class="mut">{_nfx(r["rsb"],2)}</td>'
                f'<td class="mut">{_nfx(r["rss"],2)}</td>'
                f'<td>{_pct(r["p52"]) if r["p52"] is not None else "—"}</td>'
                f'<td class="mut">{_nfx(r["adr"],2)}</td>'
                f'<td class="mut">{_nfx(r["dur"],2)}</td>'
                f'<td class="mut">{_nfx(r["dvpt"],0)}</td>'
                f'<td class="mut">{pow3_cr}</td>'
                f'<td class="mut">{_nfx(r["tcr"],2)}</td>'
                f'<td>{_kpf(r["kp3"])}</td>' + _gapx(r["gk3"])
                + f'<td>{_kpf(r["kp6"])}</td>' + _gapx(r["gk6"]))
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
                f'<td class="mut">{near}</td>' + extra + '</tr>')
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
            table = (pills + '<div class="card" style="padding:6px 10px;overflow-x:auto"><table id="stbl" class="dt">'
                     '<thead><tr><th>Symbol</th><th>Rank</th><th>r/p</th><th>×pow</th><th>Close</th>'
                     '<th>Δhot</th><th>Character</th><th>Deliv ₹Cr</th><th>Near-P</th>'
                     '<th data-tcoff>RS#</th><th data-tcoff>RS·brd</th><th data-tcoff>RS·sec</th>'
                     '<th data-tcoff>52w-hi</th><th data-tcoff>Drift3m</th><th data-tcoff>Up/Dn3m</th>'
                     '<th data-tcoff>DVPT ₹</th><th data-tcoff>Pow3m Cr</th><th data-tcoff>Churn</th>'
                     '<th data-tcoff>Key3m</th><th data-tcoff>Gap3m</th><th data-tcoff>Key6m</th>'
                     '<th data-tcoff>Gap6m</th></tr></thead>'
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
    # Stealth (view=="stealth") is its OWN destination (lens "stealth") — highlight it and
    # title it accordingly whether reached via the canonical /dash/strategies/stealth or the
    # legacy /dash/stocks?view=stealth. Otherwise this is the Stocks list (lens "stocks").
    _active = "stealth" if view == "stealth" else "stocks"
    _title = "Stealth accumulation · patearn" if view == "stealth" else "Stocks · patearn"
    return HTMLResponse(_shell(_title, body, _active, sig_date or "", wide=True))


@router.get("/dash/stealth", response_class=HTMLResponse)
def dash_stealth() -> HTMLResponse:
    """Stealth accumulation as a FIRST-CLASS destination (D80): its own nested link
    /dash/strategies/stealth + an Accumulation sub-nav entry — replacing the old
    /dash/stocks?view=stealth orphan (a view with no nav door). Reuses the dash_stocks
    stealth render verbatim (one query, no duplication); the legacy ?view=stealth URL
    keeps working and also highlights Stealth."""
    # pass every arg explicitly — a direct call must not receive the Query() defaults.
    return dash_stocks(sector="", limit=40, period="d", view="stealth")


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
        sty = ' style="background:var(--up-dim);color:var(--up);font-weight:700"' if is_near_key(g) else ''
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
    return HTMLResponse(_shell("Workbench · patearn", body, "workbench", sig_date or "", wide=True))


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
    rows, pt, n_members, cpr_by_tf, cci_by_sym = [], {}, None, {}, {}
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
                          s.power_dvpt_2m p2,
                          s.power_dvpt_3m p3, s.power_dvpt_6m p6, s.power_dvpt_12m p12,
                          s.delivery_value_today dvt, b.deliv_per,
                          s.accum_character ch, s.price_vs_hot_avg_pct pvh,
                          s.turnover_surge_1m su1, s.rs_rank,
                          s.rs_vs_broad_trend_state rsbt, s.rs_vs_broad_slope_1m b1,
                          s.rs_vs_broad_slope_3m b3, s.rs_vs_broad_slope_6m b6,
                          s.rs_vs_broad_slope_12m b12,
                          s.rs_vs_broad_slope_18m b18, s.rs_vs_broad_slope_24m b24,
                          s.rs_vs_sector_trend_state rsst,
                          s.gap_to_key_p3m g3, s.gap_to_key_p6m g6, s.gap_to_key_p12m g12,
                          s.trade_count_ratio_1m_6m tcr, s.deliv_updown_ratio_3m duo,
                          s.accum_price_drift_3m apd, s.turnover_surge_3m su3,
                          s.turnover_surge_1y suy, s.next_p_above npa, s.gap_to_next_p_pct gnp,
                          {conv} conv,
                          m.mep_score mep_sc, m.mep_state mep_st,
                          m.mep_score_smooth mep_ph, m.mep_state_smooth mep_phst
                   FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                   LEFT JOIN mep_signals m ON m.symbol=s.symbol AND m.trade_date=s.trade_date
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
                cci_by_sym = _cci_latest_by_sym(conn, syms)  # Management Credibility group (CCI, P5)
                from src.automation import theme_tags as TT
                tags_by_sym = TT.approved_tags_for(conn, syms)  # session 33 — multi-label Themes group

    from src.web.cockpit import _mv_adbar, _mep_pill

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
        cci_tds, has_cci = _cci_screener_cells(cci_by_sym.get(r["symbol"]))
        _labs = tags_by_sym.get(r["symbol"], [])
        # show 2 chips + "+N"; the overflow labels go in a hidden span so the
        # screener text-filter (matches row textContent) still finds them.
        themes_cell = ((_tag_chips(_labs, cap=2)
                        + (f'<span style="display:none">{_esc(" ".join(_labs[2:]))}</span>' if len(_labs) > 2 else ''))
                       if _labs else '<span class="mut">—</span>')
        # screener leads with the smoothed PHASE (the held regime); daily score kept
        # as the Score cell's tooltip (data-first, no column added → no realignment)
        msc, mst = r.get("mep_sc"), r.get("mep_st")
        mph, mphst = r.get("mep_ph"), r.get("mep_phst")
        mphv = mph if mph is not None else msc
        if mphv is not None:
            _dtt = ("%+.2f" % msc) if msc is not None else "—"
            mep_score_td = (f'<td class="num g-mep" title="phase score (today {_dtt})" '
                            f'style="color:{"var(--up)" if mphv>=0 else "var(--down)"}">{mphv:+.2f}</td>')
        else:
            mep_score_td = '<td class="num g-mep mut">—</td>'
        mep_cells = (f'<td class="inst l gsep g-mep">{_mv_adbar(mphv)}</td>'
                     + mep_score_td + f'<td class="l g-mep">{_mep_pill(mphst or mst)}</td>')
        g3 = r["g3"]
        g3_tint = " h-pos2" if (g3 is not None and _KEY_BAND[0] <= g3 <= _KEY_BAND[1]) else ""
        # Overhead = the next pivot ABOVE (npa is a LABEL: P1M/P3M/P12M — which power-delivery
        # level is overhead — NOT a price, so _esc not _num). The raw "P3M" code reads like an
        # error to a user, so relabel to plain English ("3M pivot +4.2%" = the 3-month power
        # level sits +4.2% above). Breakout / near-52w-high names have none → that's not missing
        # data, it's "no overhead resistance" (constructive), so render it as a signal, not a
        # dead dash. Genuine mid-range no-pivot stays "—".
        if r["npa"]:
            _npa_lbl = str(r["npa"])
            _npa_lbl = (_npa_lbl[1:] + " pivot") if _npa_lbl[:1] == "P" else _npa_lbl
            nearp = f'<span title="next power-delivery level overhead">{_esc(_npa_lbl)}</span> {_pct(r["gnp"])}'
        elif r["hh"] is not None and r["hh"] >= -2.0:
            nearp = ('<span class="pos" title="no pivot above — at/near 52w high, '
                     'no overhead resistance">clear</span>')
        else:
            nearp = '<span class="mut">—</span>'
        char_cell = (f'<span style="display:inline-flex;align-items:center;gap:6px">'
                     f'{_mv_triglyph(r["tcr"], r["duo"], r["hh"])}{_char_pill(r["ch"])}</span>')
        trs.append(
            f'<tr class="{"has-cpr" if has_cpr else ""}">'
            f'<td class="fz l"><a class="row" href="/dash/stock?sym={_esc(r["symbol"])}">'
            f'<span class="sym">{ath}{_esc(r["symbol"])}</span></a></td>'
            f'<td class="l mut">{_esc(r["sector"]) or "—"}</td>'
            f'<td class="num">{_num(r["close"], 1)}</td>'
            f'<td class="num bold gsep g-conv{h_conv(cv)}">{star}{f"{cv:.0f}" if cv is not None else "—"}</td>'
            f'<td class="g-conv"><span class="pill p-{rank}">{rank}</span></td>'
            f'<td class="inst l gsep g-pos">{_mv_ladder(r["dvpt"], r["p1"], r["p2"], r["p3"], r["p6"], r["p12"])}</td>'
            f'<td class="num mut g-pos">{r["p_score"] if r["p_score"] is not None else "—"}</td>'
            f'<td class="num mut g-pos">{r["r_score"] if r["r_score"] is not None else "—"}</td>'
            f'<td class="num g-pos"><b>{(f"{ix:.1f}×" if ix else "—")}</b></td>'
            f'<td class="num g-pos">{_num(r["su1"], 2)}</td>'
            f'<td class="num g-pos">{_num(r["su3"], 2)}</td>'
            f'<td class="num g-pos">{_num(r["suy"], 2)}</td>'
            f'<td class="num g-pos">{dlv}</td>'
            f'<td class="num g-pos">{dvt_cr}</td>'
            + mep_cells +
            f'<td class="inst l gsep g-key">{_mv_keyband(g3)}</td>'
            f'<td class="num g-key{g3_tint}">{_pct(g3)}</td>'
            f'<td class="num g-key">{_pct(r["g6"])}</td>'
            f'<td class="num g-key">{_pct(r["g12"])}</td>'
            f'<td class="inst l gsep g-char">{char_cell}</td>'
            f'<td class="num g-char">{_num(r["tcr"], 2)}</td>'
            f'<td class="num g-char">{_num(r["duo"], 2)}</td>'
            f'<td class="num g-char">{_pct(r["apd"])}</td>'
            f'<td class="inst l gsep g-rs">{_mv_rsspark(r["b1"], r["b3"], r["b6"], r["b12"])}</td>'
            f'<td class="num g-rs">{r["rs_rank"] if r["rs_rank"] is not None else "—"}</td>'
            f'<td class="l g-rs">{trend_pill(r["rsbt"])}</td>'
            f'<td class="l g-rs">{_rs_strip(r["b1"], r["b3"], r["b6"], r["b12"], r.get("b18"), r.get("b24"))}</td>'
            f'<td class="l g-rs">{trend_pill(r["rsst"])}</td>'
            + cpr_tds + cci_tds +
            f'<td class="inst l gsep g-themes" style="white-space:nowrap;overflow:hidden">{themes_cell}</td>'
            f'<td class="num gsep g-qual">{qsc}</td>'
            f'<td class="l mut g-qual">{tier}</td>'
            f'<td class="num gsep g-ctx{h_52(r["hh"])}">{_pct(r["hh"])}</td>'
            f'<td class="num g-ctx">{_pct(r["pvh"])}</td>'
            f'<td class="num g-ctx">{nearp}</td>'
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
            '<th class="l gsep g-conv" colspan="2">conviction</th>'
            '<th class="l gsep g-pos" colspan="9">positioning · dvpt</th>'
            '<th class="l gsep g-mep" colspan="3">accumulation · mep</th>'
            '<th class="l gsep g-key" colspan="4">key price</th>'
            '<th class="l gsep g-char" colspan="4">character</th>'
            '<th class="l gsep g-rs" colspan="5">relative strength</th>'
            '<th class="l gsep g-cpr" colspan="7">structure · cpr</th>'
            '<th class="l gsep g-cci" colspan="5">credibility · cci</th>'
            '<th class="l gsep g-themes" colspan="1">themes</th>'
            '<th class="l gsep g-qual" colspan="2">quality</th>'
            '<th class="l gsep g-ctx" colspan="3">context</th></tr>'
            '<tr class="scol">'
            '<th class="fz l">Symbol</th><th class="l">Sector</th><th class="num">CMP</th>'
            '<th class="num gsep g-conv">Conv</th><th class="g-conv">Rank</th>'
            '<th class="l gsep g-pos">DVPT vs power</th><th class="num g-pos">p</th><th class="num g-pos">r</th>'
            '<th class="num g-pos">×Pow</th><th class="num g-pos">Surge1m</th><th class="num g-pos">Surge3m</th>'
            '<th class="num g-pos">Surge1y</th><th class="num g-pos">Deliv%</th><th class="num g-pos">Val₹Cr</th>'
            '<th class="l gsep g-mep">Accum</th><th class="num g-mep">Phase sc</th><th class="l g-mep">Phase</th>'
            '<th class="l gsep g-key">Launch band</th><th class="num g-key">Gap3m</th><th class="num g-key">Gap6m</th><th class="num g-key">Gap12m</th>'
            '<th class="l gsep g-char">Character</th><th class="num g-char">WHO</th><th class="num g-char">WAY</th><th class="num g-char">Drift</th>'
            '<th class="l gsep g-rs">RS trend</th><th class="num g-rs">RS#</th><th class="l g-rs">Broad</th><th class="l g-rs">Heat</th><th class="l g-rs">Sector</th>'
            '<th class="num gsep g-cpr">D%</th><th class="num g-cpr">W%</th><th class="num g-cpr">M%</th>'
            '<th class="l g-cpr">D·W·M</th><th class="g-cpr">Rnk</th><th class="l g-cpr">Str</th><th class="num g-cpr">Comp%</th>'
            '<th class="l gsep g-cci">Cred</th><th class="l g-cci">Fwd</th><th class="num g-cci">Deter</th><th class="l g-cci">Veto</th><th class="num g-cci">#C</th>'
            '<th class="l gsep g-themes">Themes</th>'
            '<th class="num gsep g-qual">pt14</th><th class="l g-qual">Tier</th>'
            '<th class="num gsep g-ctx">52w%</th><th class="num g-ctx">Δhot%</th>'
            '<th class="num g-ctx" title="next power-delivery pivot overhead (resistance) + gap %">Overhead</th></tr></thead>')
        grid = (f'<div class="scrwrap"><table class="scr">{thead}'
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
        'Header band &amp; Symbol column stay frozen — scroll down and across.</div>'
        '<div class="sub" style="margin-top:-4px">Each group leads with an <b>instrument</b> that '
        'turns the buried numbers into a shape — the <b>DVPT-vs-power ladder</b>, the <b>launch-band gauge</b> '
        '(green = the −1…+5% entry band), the <b>character triglyph</b> (WHO·WAY·CTX → ACCUM/DIST) and the '
        '<b>RS spark</b> — with every raw value kept beside it. Hide a group to scan just its instruments.</div>')
    view_bar = '<div class="fbar" id="vbar" style="align-items:center;margin-bottom:8px"></div>'
    from src.web.cockpit import SCREENER_VIRT_JS
    body = intro + scope_bar + view_bar + grid + _SCREENER_JS + SCREENER_VIRT_JS
    return HTMLResponse(_shell("Screener · patearn", body, "screener", sig_date or "", wide=True))


# Screener view-controls: column-group toggle chips + saved views (localStorage).
# Toggles whole groups by walking the sgrp colspans -> column indexes (so the
# colspan'd group header hides cleanly with its columns). Plain template.
_SCREENER_JS = """
<script>
(function(){
  var tbl=document.querySelector('table.scr'); if(!tbl) return;
  // LAG FIX: build a fixed-width <colgroup> from the first body row's cell types, so
  // table-layout:fixed has explicit per-column widths. Toggling a strategy group then
  // costs ONE cheap reflow instead of re-measuring all 498 rows (that was the hang).
  (function(){
    if(tbl.querySelector('colgroup.cg')) return;
    var row=tbl.querySelector('tbody tr'); if(!row) return;
    var cg=document.createElement('colgroup'); cg.className='cg';
    Array.prototype.forEach.call(row.children,function(td){
      var c=document.createElement('col');
      c.style.width=(td.classList.contains('fz')?116:td.classList.contains('inst')?136:td.classList.contains('num')?76:112)+'px';
      var g=null; td.classList.forEach(function(k){ if(k.lastIndexOf('g-',0)===0) g=k.slice(2); });
      if(g) c.className='cg-'+g;
      cg.appendChild(c);
    });
    tbl.insertBefore(cg, tbl.firstChild);
  })();
  var vbar=document.getElementById('vbar'); if(!vbar) return;
  var TOG=[['conv','Conviction'],['pos','Positioning'],['mep','Accumulation'],['key','Key price'],['char','Character'],['rs','RS'],['cpr','CPR'],['cci','Credibility'],['themes','Themes'],['qual','Quality'],['ctx','Context']];
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


def _cci_fwd(v) -> str:
    v = (v or "FLAT").upper()
    if v == "UP":
        return '<span class="pos">UP ↑</span>'
    if v in ("DOWN", "AVOID"):
        return f'<span class="neg">{v} ↓</span>'
    return '<span class="mut">FLAT</span>'


def _cci_num(v, suffix="") -> str:
    return f"{v:.0f}{suffix}" if isinstance(v, (int, float)) else '<span class="mut">—</span>'


_CCI_DETERMINISTIC_FLAGS = ("guidance_walkback", "stopped_disclosing", "promise_quietly_dropped",
                            "metric_definition_change", "capex_slippage")


def _cci_status_pill(st: str) -> str:
    st = st or "OPEN"
    if st in ("MET",):
        return f'<span class="pos">{_esc(st)}</span>'
    if st in ("MISSED", "ABANDONED", "RESTATED"):
        return f'<span class="neg">{_esc(st)}</span>'
    if st == "PARTIAL":
        return f'<span style="color:#d29922">{_esc(st)}</span>'
    return f'<span class="mut">{_esc(st)}</span>'


def _cci_bar(label: str, v, invert: bool = False) -> str:
    """A compact 0-100 axis bar (AI read — informational, never ranked). invert =
    higher-is-worse (evasion / promo)."""
    if v is None:
        return ""
    good = (100 - v) if invert else v
    col = "var(--up)" if good >= 66 else ("var(--warn)" if good >= 40 else "var(--down)")
    return (f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;font-size:12px">'
            f'<span style="width:130px;color:var(--ink-2)">{label}</span>'
            f'<span style="flex:1;max-width:150px;background:var(--bg-3);border-radius:3px;height:7px">'
            f'<span style="display:block;height:7px;border-radius:3px;width:{int(v)}%;background:{col}"></span></span>'
            f'<span style="width:26px;text-align:right;color:var(--ink)">{int(v)}</span></div>')


def _mep_stock_panel(sym: str) -> str:
    """Per-stock MEP dossier — guarded wrapper. ANY failure (incl. a `mep_signals`
    schema drift making a by-key column read raise) degrades to an empty panel, never
    a 500 of the whole stock page — mirrors the CPR/CCI panels' graceful-empty contract."""
    try:
        return _mep_stock_panel_inner(sym)
    except Exception:
        return ""


def _mep_stock_panel_inner(sym: str) -> str:
    """Per-stock MEP (signed accumulation/distribution) dossier — descriptor-only
    (D62). The signed verdict, then the four SIGNED terms each with its within-stock
    z-score and raw value (data-first), two context terms, and DVPT's side-blind
    character shown as a CONFIRMATION sub-row (DVPT's surviving role). '' when the
    stock has no MEP data (graceful, like the CPR/CCI panels). Pure static HTML/SVG
    — no chart, no width-measuring JS, so it renders correctly while hidden."""
    try:
        with get_conn() as conn:
            m = conn.execute(
                "SELECT * FROM mep_signals WHERE symbol=? ORDER BY trade_date DESC LIMIT 1",
                (sym,)).fetchone()
            ch = conn.execute(
                "SELECT accum_character FROM stock_signals WHERE symbol=? "
                "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    except Exception:
        return ""
    if not m or m["mep_score"] is None:
        return ""
    # F&O OI — the IDENTITY channel (separate guarded query so a missing table
    # never blanks the MEP panel)
    fo = None
    try:
        with get_conn() as conn:
            fo = conn.execute("SELECT * FROM fno_oi_signals WHERE symbol=? "
                              "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    except Exception:
        fo = None
    from src.web.cockpit import _mv_adbar, _mep_pill
    sc, st = m["mep_score"], m["mep_state"]                  # daily (granular pressure)
    ph = m["mep_score_smooth"] if "mep_score_smooth" in m.keys() else None
    phst = m["mep_state_smooth"] if "mep_state_smooth" in m.keys() else None
    phv = ph if ph is not None else sc
    phstv = phst or st
    pcol = "var(--up)" if phv >= 0 else "var(--down)"
    scol = "var(--up)" if sc >= 0 else "var(--down)"
    # days held in the current phase = consecutive most-recent rows of the same phase
    held = None
    try:
        with get_conn() as conn:
            recent = [r["mep_state_smooth"] for r in conn.execute(
                "SELECT mep_state_smooth FROM mep_signals WHERE symbol=? "
                "ORDER BY trade_date DESC LIMIT 400", (sym,)).fetchall()]
        if recent and recent[0] is not None:
            held = 0
            for s in recent:
                if s == recent[0]:
                    held += 1
                else:
                    break
    except Exception:
        held = None
    # F&O identity chip — a VISIBLE component in the KPI row (not just the line below)
    _fq = {"LONG_BUILDUP": ("#2ea043", "Long Buildup"), "SHORT_COVER": ("#3fb950", "Short Cover"),
           "SHORT_BUILDUP": ("#f85149", "Short Buildup"), "LONG_UNWIND": ("#f0883e", "Long Unwind"),
           "FLAT": ("var(--ink-2)", "Flat")}.get((fo["quadrant"] if fo else None) or "", None)
    fno_box = ""
    if _fq:
        fno_box = (f'<div class="box"><div class="num"><span style="display:inline-block;padding:1px 6px;'
                   f'border-radius:6px;font-size:10.5px;font-weight:700;color:{_fq[0]};'
                   f'border:1px solid {_fq[0]}55;background:{_fq[0]}14">{_fq[1]}</span></div>'
                   f'<div class="lbl">F&amp;O positioning</div></div>')
    chips = (
        '<div class="kpi">'
        f'<div class="box"><div class="num">{_mep_pill(phstv)}</div><div class="lbl">phase (headline)</div></div>'
        f'<div class="box"><div class="num" style="color:{pcol}">{phv:+.2f}</div><div class="lbl">phase score</div></div>'
        f'<div class="box"><div class="num">{_mv_adbar(phv)}</div><div class="lbl">accum &harr; distrib</div></div>'
        f'<div class="box"><div class="num">{(str(held)+"d") if held else "—"}</div><div class="lbl">held in phase</div></div>'
        f'<div class="box"><div class="num">{m["data_points_used"] if "data_points_used" in m.keys() else "—"}</div><div class="lbl">history days</div></div>'
        + fno_box +
        '</div>'
        f'<div class="sub" style="margin-top:6px">Today (daily, granular): '
        f'<b style="color:{scol}">{sc:+.2f}</b> &nbsp;{_mep_pill(st)} '
        f'<span class="mut">— the raw single-day score; the phase above is its ~15-day '
        f'smoothed, hysteresis-banded regime (holds for weeks, not the daily flip).</span></div>')

    def _trow(name, z, raw):
        zt = f'{z:+.2f}' if z is not None else '—'
        rt = f'{raw:+.3f}' if raw is not None else '—'
        zc = ("var(--up)" if z >= 0 else "var(--down)") if z is not None else "var(--ink-2)"
        return (f'<tr><td class="l">{name}</td>'
                f'<td class="r" style="color:{zc}">{zt}</td><td class="r mut">{rt}</td></tr>')
    terms = (
        '<table class="ck-t" style="margin-top:8px"><tbody>'
        '<tr><td class="l mut">signed term</td><td class="r mut">z vs own history</td><td class="r mut">raw</td></tr>'
        + _trow("Pressure — close vs VWAP", m["z_pressure"], m["pressure"])
        + _trow("Close-location (CLV)", m["z_clv"], m["clv"])
        + _trow("Drift — 22d adj return", m["z_drift"], m["drift_22d"])
        + _trow("Up/down volume skew — 22d", m["z_updown"], m["updown_vol_22d"])
        + '</tbody></table>')
    comp, ami = m["compression"], m["amihud_22d"]
    ctx = (f'<div class="sub" style="margin-top:8px">Context (not summed into the score): '
           f'compression <b>{f"{comp:.2f}" if comp is not None else "—"}</b> (short/long ATR — lower = coiled) · '
           f'Amihud illiquidity <b>{f"{ami:.2e}" if ami is not None else "—"}</b>.</div>')
    dvpt_conf = ''
    if ch and ch["accum_character"]:
        dvpt_conf = (f'<div class="sub" style="margin-top:4px">DVPT character '
                     f'(side-blind — <b>confirmation</b>): <b>{_esc(ch["accum_character"])}</b>. '
                     f'MEP leads with the signed read; DVPT confirms the delivery footprint.</div>')
    # F&O OI — the IDENTITY channel: directly OBSERVED positioning vs MEP/DVPT's
    # inference from the tape. The four-quadrant map + PCR (descriptor — D62).
    fno_line = ''
    if fo and fo["quadrant"]:
        _qc = {"LONG_BUILDUP": "#2ea043", "SHORT_COVER": "#3fb950",
               "SHORT_BUILDUP": "#f85149", "LONG_UNWIND": "#f0883e",
               "FLAT": "var(--ink-2)"}.get(fo["quadrant"], "var(--ink-2)")
        _qlabel = fo["quadrant"].replace("_", " ").title()
        _oichg = f'{fo["fut_oi_chg_pct"]:+.1f}%' if fo["fut_oi_chg_pct"] is not None else "—"
        _pcr = f'{fo["pcr"]:.2f}' if fo["pcr"] is not None else "—"
        fno_line = (f'<div class="sub" style="margin-top:4px">F&amp;O positioning '
                    f'(<b>identity</b> — directly observed, not inferred): '
                    f'<b style="color:{_qc}">{_esc(_qlabel)}</b> · futures OI {_oichg} · PCR {_pcr}. '
                    f'The one channel that names the strong hand — descriptor until DSR-gated.</div>')
    foot = ('<div class="sub mut" style="margin-top:8px;font-size:11px">Descriptor only (D62) — a signed '
            'character / confirmation lens, SIGNED where DVPT is side-blind, standardised vs the stock&#39;s '
            'own trailing history. Not a stock picker (its predictive role failed the DSR gate).</div>')
    return ('<h3 style="margin:4px 0 8px">Accumulation · MEP '
            '<span class="sub" style="margin:0;font-weight:400">signed accumulation / distribution</span></h3>'
            + chips + terms + ctx + dvpt_conf + fno_line + foot)


_FNO_QC = {"LONG_BUILDUP": ("#2ea043", "Long Buildup"), "SHORT_COVER": ("#3fb950", "Short Cover"),
           "SHORT_BUILDUP": ("#f85149", "Short Buildup"), "LONG_UNWIND": ("#f0883e", "Long Unwind"),
           "FLAT": ("#8b949e", "Flat")}


def _fno_read(q, doi, oi_5d, streak) -> str:
    """Plain-English synthesis of the current F&O positioning."""
    if not q:
        return ""
    base = {
        "LONG_BUILDUP": "Fresh longs — price up on rising OI. Buyers adding risk (accumulation).",
        "SHORT_BUILDUP": "Fresh shorts — price down on rising OI. Sellers pressing (distribution).",
        "LONG_UNWIND": "Longs exiting — price down on falling OI. Bulls booking out, not fresh shorts.",
        "SHORT_COVER": "Short covering — price up on falling OI. A relief bounce, not fresh buying.",
        "FLAT": "No decisive OI/price move today.",
    }.get(q, "")
    extra = ""
    if streak >= 3 and q in ("LONG_BUILDUP", "SHORT_BUILDUP"):
        extra = (f" Sustained {streak} days — a persistent "
                 f"{'accumulation' if q == 'LONG_BUILDUP' else 'distribution'} footprint.")
    if oi_5d is not None and abs(oi_5d) >= 10:
        extra += f" Futures OI {oi_5d:+.0f}% over 5 days."
    return f"<b>{base}</b>{extra}"


def _fno_spark(series) -> str:
    """Static OI sparkline (oldest→newest). Fixed viewBox so it renders while the
    tab is still hidden (the charts-incident lesson — no width-measuring JS)."""
    pts = [v for v in series if v is not None]
    if len(pts) < 2:
        return '<span class="mut">Futures-OI trend — insufficient history.</span>'
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1
    n = len(pts)
    coords = " ".join(f"{i/(n-1)*100:.1f},{26 - (v-lo)/rng*24:.1f}" for i, v in enumerate(pts))
    col = "var(--up)" if pts[-1] >= pts[0] else "var(--down)"
    return (f'<div style="font-size:11px;color:var(--ink-2);margin-bottom:2px">Futures-OI trend '
            f'(last {n} days, oldest→newest)</div>'
            f'<svg width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none" '
            f'style="display:block">'
            f'<polyline points="{coords}" fill="none" style="stroke:{col}" stroke-width="1.2"/></svg>')


def _fno_levels_bar(spot, sup, res, mp) -> str:
    """Static option-chain map: put-wall (support), call-wall (resistance), max-pain
    and spot on one horizontal axis. SVG ticks (no text → no distortion) + an HTML
    value row. Renders while hidden."""
    vals = [v for v in (spot, sup, res, mp) if v]
    if not spot or len(set(vals)) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.10 or (hi * 0.01)
    lo -= pad
    hi += pad
    rng = (hi - lo) or 1

    def _x(v):
        return max(1.0, min(99.0, (v - lo) / rng * 100))

    def tick(v, col):
        return (f'<line x1="{_x(v):.1f}" y1="3" x2="{_x(v):.1f}" y2="17" style="stroke:{col}" stroke-width="1.4"/>'
                if v else "")
    svg = (f'<svg width="100%" height="20" viewBox="0 0 100 20" preserveAspectRatio="none" style="display:block">'
           f'<line x1="0" y1="10" x2="100" y2="10" style="stroke:var(--line-2)" stroke-width="0.6"/>'
           f'{tick(sup, "var(--up)")}{tick(res, "var(--down)")}{tick(mp, "#d29922")}'
           f'<line x1="{_x(spot):.1f}" y1="1" x2="{_x(spot):.1f}" y2="19" style="stroke:var(--ink)" stroke-width="1.4"/>'
           f'</svg>')
    def lab(c, name, v):
        return (f'<span style="color:{c}">{name} <b>{v:,.0f}</b></span>' if v else "")
    row = ('<div class="sub" style="display:flex;gap:14px;flex-wrap:wrap;margin-top:3px;font-size:11px">'
           + " ".join(x for x in (lab("var(--up)", "▎support", sup), lab("var(--ink)", "▎spot", spot),
                                  lab("#d29922", "▎max-pain", mp), lab("var(--down)", "▎resistance", res)) if x)
           + '</div>')
    return svg + row


def _fno_stock_panel(sym: str) -> str:
    """Deep F&O Open-Interest dossier — the IDENTITY channel that DIRECTLY OBSERVES
    positioning (MEP/DVPT only infer it from the price tape). Current four-quadrant
    read + the OI/price trajectory over the recent window + the quadrant streak +
    PCR + a plain-English synthesis + the day-by-day history. '' for non-F&O names
    (no single-stock future). Descriptor-only (D62). Pure static HTML/SVG."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT trade_date, fut_oi, fut_oi_chg, fut_oi_chg_pct, und_price, "
                "price_chg_pct, quadrant, call_oi, put_oi, pcr, n_fut_contracts, "
                "fut_price, basis_pct, max_pain, sup_strike, res_strike "
                "FROM fno_oi_signals WHERE symbol=? ORDER BY trade_date DESC LIMIT 90", (sym,)).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    R = [dict(r) for r in rows]          # newest first
    cur = R[0]
    q = cur["quadrant"]
    qcol, qlbl = _FNO_QC.get(q or "", ("#8b949e", q or "—"))

    streak = 0
    for r in R:
        if q and r["quadrant"] == q:
            streak += 1
        else:
            break

    def _oi_back(n):
        if len(R) > n and R[n]["fut_oi"] and R[n]["fut_oi"] > 0 and cur["fut_oi"]:
            return (cur["fut_oi"] / R[n]["fut_oi"] - 1) * 100
        return None
    oi_5d, oi_20d = _oi_back(5), _oi_back(20)
    oi_60d = _oi_back(min(60, len(R) - 1)) if len(R) > 1 else None
    # cumulative positioning: net bullish-OI vs bearish-OI days over the last 20
    _BULL = {"LONG_BUILDUP", "SHORT_COVER"}
    _BEAR = {"SHORT_BUILDUP", "LONG_UNWIND"}
    win = R[:20]
    bull_d = sum(1 for r in win if r["quadrant"] in _BULL)
    bear_d = sum(1 for r in win if r["quadrant"] in _BEAR)
    net_bias = bull_d - bear_d
    # OI percentile within the available window (crowdedness of positioning)
    ois = [r["fut_oi"] for r in R if r["fut_oi"] is not None]
    oi_pct = (round(sum(1 for x in ois if x <= cur["fut_oi"]) / len(ois) * 100)
              if ois and cur["fut_oi"] is not None else None)
    basis = cur["basis_pct"]
    spot = cur["und_price"]

    def _f(v, d=1, sign=False):
        if v is None:
            return "—"
        return f"{v:+.{d}f}" if sign else f"{v:.{d}f}"

    def _oi(v):
        if v is None:
            return "—"
        if v >= 1e7:
            return f"{v/1e7:.2f}Cr"
        if v >= 1e5:
            return f"{v/1e5:.2f}L"
        return f"{v:,.0f}"

    def _pcell(v):
        if v is None:
            return '<span class="mut">—</span>'
        return f'<span style="color:{"var(--up)" if v >= 0 else "var(--down)"}">{v:+.1f}%</span>'

    chips = (
        '<div class="kpi">'
        f'<div class="box"><div class="num"><span style="display:inline-block;padding:1px 7px;'
        f'border-radius:6px;font-size:12px;font-weight:700;color:{qcol};border:1px solid {qcol}55;'
        f'background:{qcol}14">{_esc(qlbl)}</span></div><div class="lbl">positioning</div></div>'
        f'<div class="box"><div class="num">{_oi(cur["fut_oi"])}</div><div class="lbl">futures OI</div></div>'
        f'<div class="box"><div class="num" style="color:{"var(--up)" if (cur["fut_oi_chg_pct"] or 0) >= 0 else "var(--down)"}">'
        f'{_f(cur["fut_oi_chg_pct"], 1, True)}%</div><div class="lbl">ΔOI today</div></div>'
        f'<div class="box"><div class="num" style="color:{"var(--up)" if (basis or 0) >= 0 else "var(--down)"}">'
        f'{_f(basis, 2, True)}%</div><div class="lbl">basis fut−spot</div></div>'
        f'<div class="box"><div class="num">{_f(cur["pcr"], 2)}</div><div class="lbl">PCR put/call</div></div>'
        f'<div class="box"><div class="num">{streak}d</div><div class="lbl">in {_esc(qlbl.lower())}</div></div>'
        '</div>')

    # --- cumulative positioning (the multi-week net read, not just today) ---
    nb_col = "var(--up)" if net_bias > 0 else ("var(--down)" if net_bias < 0 else "var(--ink-2)")
    cum_chips = (
        '<div class="kpi" style="margin-top:6px">'
        f'<div class="box"><div class="num">{_f(oi_5d, 1, True)}%</div><div class="lbl">OI 5-day</div></div>'
        f'<div class="box"><div class="num">{_f(oi_20d, 1, True)}%</div><div class="lbl">OI 20-day</div></div>'
        f'<div class="box"><div class="num">{_f(oi_60d, 1, True)}%</div><div class="lbl">OI ~60-day</div></div>'
        f'<div class="box"><div class="num" style="color:{nb_col}">{net_bias:+d}</div>'
        f'<div class="lbl">net bias 20d ({bull_d}↑/{bear_d}↓)</div></div>'
        f'<div class="box"><div class="num">{(str(oi_pct) + "%") if oi_pct is not None else "—"}</div>'
        f'<div class="lbl">OI percentile</div></div>'
        '</div>')

    # cumulative verdict
    cum_dir = ("net long accumulation" if (net_bias > 1 and (oi_20d or 0) > 0)
               else "net short / distribution" if (net_bias < -1 and (oi_20d or 0) > 0)
               else "positions unwinding" if (oi_20d or 0) < -3
               else "range-bound / two-way")
    cum_read = (f'<b>Cumulative ({len(win)}d):</b> {cum_dir} — open interest '
                f'{_f(oi_20d, 0, True)}% over 20 days, {bull_d} bullish-OI vs {bear_d} bearish-OI days. '
                f'OI sits in the {oi_pct}th percentile of its recent range.'
                if oi_pct is not None else f'<b>Cumulative:</b> {cum_dir}.')

    # option-chain levels (the writers' map) — current expiry
    levels = _fno_levels_bar(spot, cur["sup_strike"], cur["res_strike"], cur["max_pain"])
    levels_block = ((f'<div class="sub" style="margin:10px 0 2px">Option-chain levels '
                     f'<span class="mut">(near expiry — put wall = support, call wall = resistance, '
                     f'max-pain = expiry magnet)</span></div>'
                     f'<div class="card" style="margin-top:0;padding:8px 10px">{levels}</div>')
                    if levels else "")

    read = _fno_read(q, cur["fut_oi_chg_pct"], oi_5d, streak)
    spark = _fno_spark([r["fut_oi"] for r in reversed(R)])

    hrows = ""
    for r in R[:15]:
        qc2, ql2 = _FNO_QC.get(r["quadrant"] or "", ("#8b949e", r["quadrant"] or "—"))
        hrows += (f'<tr><td class="l mut">{_esc(r["trade_date"])}</td>'
                  f'<td class="r">{_pcell(r["price_chg_pct"])}</td>'
                  f'<td class="r mut">{_oi(r["fut_oi"])}</td>'
                  f'<td class="r">{_pcell(r["fut_oi_chg_pct"])}</td>'
                  f'<td class="l"><span style="color:{qc2}">{_esc(ql2)}</span></td>'
                  f'<td class="r mut">{_f(r["pcr"], 2)}</td></tr>')
    hist = ('<table class="ck-t" style="margin-top:8px"><thead>'
            '<tr><th class="l">Date</th><th class="r">Price</th><th class="r">Fut OI</th>'
            '<th class="r">ΔOI</th><th class="l">Quadrant</th><th class="r">PCR</th></tr></thead>'
            f'<tbody>{hrows}</tbody></table>')

    legend = ('<div class="sub mut" style="margin-top:8px;font-size:11px">'
              '↑price ↑OI = <b style="color:var(--up)">long buildup</b> · '
              '↓price ↑OI = <b style="color:var(--down)">short buildup</b> · '
              '↓price ↓OI = <b style="color:#f0883e">long unwind</b> · '
              '↑price ↓OI = <b style="color:var(--up)">short cover</b>.</div>')
    foot = ('<div class="sub mut" style="margin-top:6px;font-size:11px">Stock-futures OI summed across '
            'expiries vs the cash price move; PCR from stock options. The one channel that names the '
            'strong hand — but DESCRIPTOR-ONLY (D62): it must clear the DSR gate before it ranks or picks.</div>')

    return ('<h3 style="margin:4px 0 8px">F&amp;O Open Interest '
            '<span class="sub" style="margin:0;font-weight:400">identity channel — directly observed '
            'positioning</span></h3>'
            + chips
            + f'<div class="sub" style="margin:6px 0 2px">{read}</div>'
            + cum_chips
            + f'<div class="sub" style="margin:6px 0 2px">{cum_read}</div>'
            + levels_block
            + f'<div class="card" style="margin-top:8px;padding:8px 10px">{spark}</div>'
            + hist + legend + foot)


def _cci_stock_panel(sym: str) -> str:
    """Per-stock Management-Credibility (CCI) dossier. Measurable verdict on top
    (tier / forward / guidance-accuracy / quantification / deterioration / ⛔veto),
    then the PROMISE LEDGER (MET/MISSED/OPEN + variance — the follow-through Ramana
    asked for), the deterministic deterioration timeline, the expectation-vs-actual
    log, the negative-EBITDA ledger, and LAST the behaviour axes shown as an
    'AI read — NOT ranked' (D61). Returns '' when the stock has no concall data yet
    (panel omitted, graceful — like the CPR panel)."""
    try:
        with get_conn() as conn:
            sc = conn.execute(
                "SELECT * FROM concall_scores WHERE symbol=? ORDER BY last_updated DESC LIMIT 1",
                (sym,)).fetchone()
            gd = [dict(r) for r in conn.execute(
                "SELECT source_period, statement_type, horizon, claim_text, quantified_target, unit, "
                "status, resolved_period, variance_pct, confidence_language "
                "FROM concall_guidance WHERE symbol=? "
                "ORDER BY (status IN ('MET','MISSED','PARTIAL')) DESC, id DESC", (sym,)).fetchall()]
            beh = conn.execute(
                "SELECT * FROM concall_behavior WHERE symbol=? ORDER BY id DESC LIMIT 1", (sym,)).fetchone()
            rf = [dict(r) for r in conn.execute(
                "SELECT period_label, prior_period, flag_type, severity, evidence, model_version "
                "FROM concall_redflags WHERE symbol=? ORDER BY id DESC LIMIT 14", (sym,)).fetchall()]
            eva = [dict(r) for r in conn.execute(
                "SELECT period_label, metric, classification, mgmt_expectation, headwind_adjusted, evidence "
                "FROM concall_expectations_vs_actual WHERE symbol=? ORDER BY id DESC LIMIT 10", (sym,)).fetchall()]
            ew = [dict(r) for r in conn.execute(
                "SELECT period_label, ebitda, ebitda_margin, periods_in_red "
                "FROM concall_ebitda_watch WHERE symbol=? ORDER BY id DESC LIMIT 8", (sym,)).fetchall()]
            ncalls = conn.execute("SELECT COUNT(*) n FROM concalls WHERE symbol=? AND parse_status='OK'",
                                  (sym,)).fetchone()["n"]
    except Exception:
        return ""
    if not sc and not gd and not beh:
        return ""
    S = dict(sc) if sc else {}

    # --- veto banner (the exogenous integrity gate, in front of everything) ---
    veto = ""
    if S.get("veto_active"):
        veto = (f'<div style="border:1px solid var(--down);background:rgba(var(--down-rgb),.09);border-radius:6px;'
                f'padding:8px 10px;margin:6px 0;color:var(--down);font-size:13px">⛔ <b>VETO</b> — '
                f'{_esc(S.get("veto_reason") or "forensic disqualifier")}. Credibility capped regardless '
                f'of how the call sounded (forensic gate, debate #1).</div>')

    # --- measurable verdict chips ---
    ga = S.get("guidance_accuracy_score")
    ga_txt = (f'{ga:.0f}% <span class="mut">({S.get("n_promises_resolved") or 0})</span>'
              if ga is not None else '<span class="mut">unproven</span>')
    det = S.get("deterioration_score") or 0
    det_cell = (f'<span class="neg">{int(det)}</span>' if det else '<span class="mut">0</span>')
    tier = S.get("tier") or "—"
    tcls = "pos" if tier in ("A+", "A") else ("neg" if tier == "D" else "mut")
    chips = (
        '<div class="kpi">'
        f'<div class="box"><div class="num"><span class="{tcls}">{_esc(tier)}</span></div><div class="lbl">tier</div></div>'
        f'<div class="box"><div class="num">{_cci_num(S.get("composite_score"))}</div><div class="lbl">score</div></div>'
        f'<div class="box"><div class="num">{_cci_fwd(S.get("forward_direction"))}</div><div class="lbl">forward</div></div>'
        f'<div class="box"><div class="num">{ga_txt}</div><div class="lbl">guidance acc.</div></div>'
        f'<div class="box"><div class="num">{_cci_num(S.get("quantification_rate"), "%")}</div><div class="lbl">quantif (transp.)</div></div>'
        f'<div class="box"><div class="num">{det_cell}</div><div class="lbl">deterioration</div></div>'
        f'<div class="box"><div class="num">{ncalls}</div><div class="lbl">#calls extracted</div></div>'
        f'<div class="box"><div class="num">{S.get("n_promises_resolved") or 0}</div><div class="lbl">promises settled</div></div>'
        '</div>')

    # --- promise ledger (the follow-through tracker) ---
    led = ""
    if gd:
        trs = []
        for g in gd[:24]:
            st = (g["status"] or "OPEN")
            tgt = g["quantified_target"]
            tgt_txt = (f'{tgt:g} {_esc(g["unit"] or "")}'.strip() if tgt is not None else "—")
            var = g["variance_pct"]
            res = (f'{_esc(g["resolved_period"] or "")} '
                   f'{("%+.1f" % var) if var is not None else ""}' if st in ("MET", "MISSED", "PARTIAL") else "—")
            trs.append(
                f'<tr><td class="mut">{_esc(g["source_period"] or "")}</td>'
                f'<td>{_esc(g["statement_type"] or "")}</td>'
                f'<td class="mut">{_esc(g["horizon"] or "")}</td>'
                f'<td class="l" title="{_esc(g["confidence_language"] or "")}">{_esc((g["claim_text"] or "")[:110])}</td>'
                f'<td class="num">{tgt_txt}</td>'
                f'<td>{_cci_status_pill(st)}</td>'
                f'<td class="mut">{res}</td></tr>')
        n_more = f' <span class="mut">(+{len(gd)-24} more)</span>' if len(gd) > 24 else ""
        led = ('<div style="font-weight:600;margin:10px 0 4px">Promise ledger '
               f'<span class="mut" style="font-weight:400">— follow-through, MET/MISSED settled vs actuals{n_more}</span></div>'
               '<table class="dt"><thead><tr><th>Said</th><th>Type</th><th>Horizon</th><th class="l">Promise</th>'
               '<th>Target</th><th>Status</th><th>Resolved Δ</th></tr></thead><tbody>'
               + "".join(trs) + "</tbody></table>")

    # --- deterioration / red-flag timeline (deterministic flags marked ★) ---
    flagh = ""
    if rf:
        items = []
        for f in rf:
            is_det = (f.get("model_version") == "cci-diff-v1") or (f["flag_type"] in _CCI_DETERMINISTIC_FLAGS)
            mark = '<span class="neg" title="deterministic — drives the rank">★</span> ' if is_det else ''
            sev = f.get("severity")
            prior = f' <span class="mut">(vs {_esc(f["prior_period"])})</span>' if f.get("prior_period") else ""
            items.append(
                f'<li style="margin:3px 0"><span class="mut">{_esc(f["period_label"] or "")}</span> '
                f'{mark}<b>{_esc(f["flag_type"] or "")}</b>{(" · sev %d" % sev) if sev else ""}{prior}'
                f'<br><span class="mut" style="font-size:12px">{_esc((f["evidence"] or "")[:160])}</span></li>')
        flagh = ('<div style="font-weight:600;margin:10px 0 4px">Deterioration &amp; red-flag timeline '
                 '<span class="mut" style="font-weight:400">— ★ = deterministic (ranked); others = AI read (context)</span></div>'
                 '<ul style="margin:0;padding-left:16px;list-style:square">' + "".join(items) + "</ul>")

    # --- expectation vs actual (in-line / understated / overstated / CONCEALED) ---
    evah = ""
    if eva:
        trs = []
        for e in eva:
            cls = (e["classification"] or "").upper()
            ccls = ("neg" if cls in ("MISS", "OVERSTATED", "CONCEALED") else
                    "pos" if cls in ("BEAT", "UNDERSTATED") else "mut")
            hw = ' <span class="pos" title="warned of a headwind yet delivered">⚑hw</span>' if e.get("headwind_adjusted") else ""
            trs.append(
                f'<tr><td class="mut">{_esc(e["period_label"] or "")}</td><td>{_esc(e["metric"] or "")}</td>'
                f'<td><span class="{ccls}">{_esc(cls or "—")}</span>{hw}</td>'
                f'<td class="l">{_esc((e["mgmt_expectation"] or "")[:90])}</td></tr>')
        evah = ('<div style="font-weight:600;margin:10px 0 4px">Expectation vs actual '
                '<span class="mut" style="font-weight:400">— AI read (context, not ranked)</span></div>'
                '<table class="dt"><thead><tr><th>Period</th><th>Metric</th><th>Read</th><th class="l">Mgmt had said</th>'
                '</tr></thead><tbody>' + "".join(trs) + "</tbody></table>")

    # --- negative-EBITDA ledger (suppressed for lenders upstream) ---
    ewh = ""
    if ew:
        trs = "".join(
            f'<tr><td class="mut">{_esc(w["period_label"] or "")}</td><td class="num neg">{_num(w["ebitda"],0)}</td>'
            f'<td class="num">{_num(w["ebitda_margin"],1)}%</td><td class="num">{w["periods_in_red"] or "—"}</td></tr>'
            for w in ew)
        ewh = ('<div style="font-weight:600;margin:10px 0 4px">Negative / weak-EBITDA ledger</div>'
               '<table class="dt"><thead><tr><th>Period</th><th>EBITDA ₹cr</th><th>Margin</th><th>Qtrs in red</th>'
               '</tr></thead><tbody>' + trs + "</tbody></table>")

    # --- behaviour axes (AI read — NOT ranked, per D61) ---
    behh = ""
    if beh:
        B = dict(beh)
        bars = (_cci_bar("credibility", B.get("credibility")) + _cci_bar("transparency", B.get("transparency"))
                + _cci_bar("courage", B.get("courage")) + _cci_bar("issue handling", B.get("issue_handling"))
                + _cci_bar("consistency", B.get("consistency")) + _cci_bar("specificity", B.get("specificity"))
                + _cci_bar("evasion", B.get("evasion"), invert=True)
                + _cci_bar("promotional", B.get("promo_vs_conservative"), invert=True))
        ev = _esc((B.get("evidence") or "")[:240])
        behh = ('<div style="font-weight:600;margin:10px 0 4px">Behaviour axes '
                '<span class="mut" style="font-weight:400">— an <b>AI read for context, NOT a ranking input</b> (D61)</span></div>'
                + bars + (f'<div class="mut" style="font-size:11px;margin-top:4px">“{ev}”</div>' if ev else ""))

    foot = ('<div class="mut" style="font-size:11px;margin-top:10px">Ranking uses <b>measurable items only</b> '
            '(D61): guidance accuracy, quantification %, the ⛔ veto, and deterministic deterioration (★). '
            'Behaviour / expectation reads inform but do not rank. <b>Pilot</b> — carried until the falsification '
            'gates clear. <a class="row" style="display:inline" href="/dash/concalls">Full CCI board →</a></div>')

    asof = f' · as of {_esc(S.get("as_of_period"))}' if S.get("as_of_period") else ""
    from src.web.cockpit import cci_state
    _st, _tone = cci_state(S)
    _stcol = {"pos": "var(--ok)", "mut": "var(--ink-2)", "stale": "var(--warn)"}.get(_tone, "var(--ink-2)")
    state_badge = (f' <span style="font-size:11px;font-weight:700;color:{_stcol};border:1px solid {_stcol};'
                   f'border-radius:8px;padding:1px 7px">{_st}</span>' if _st else "")
    return ('<div class="ccipanel" style="border:1px solid var(--line-2);border-radius:8px;padding:14px;margin:14px 0;background:var(--bg-1)">'
            f'<h3 style="margin:0 0 6px">Management Credibility{state_badge} '
            f'<span class="mut" style="font-size:12px;font-weight:400">CCI · concall intelligence{asof}</span></h3>'
            + veto + chips + led + flagh + evah + ewh + behh + foot + '</div>')


@router.get("/dash/concalls", response_class=HTMLResponse)
def dash_concalls(view: str = Query("avoid")) -> HTMLResponse:
    """CCI — Management Credibility (the concall-intelligence pillar). Two views:
    'avoid' = the deterioration tape (worst-first: walk-backs, concealment, vetoes);
    'leaders' = credibility leaders (veto-excluded, proven track record on top).
    Data-first: the raw behaviour axes sit beside every verdict (D-UI-1); reuses
    table.dt (_DT_JS sort/filter/CSV). PILOT screen — carried until the falsification
    gates clear (docs/concall-intelligence-debate.md). Full-bleed cockpit render
    (cockpit.render_concalls); the legacy inline body below is kept as dead code."""
    from src.web.cockpit import render_concalls
    sig_date, _ = _latest_dates()
    return HTMLResponse(_shell("Management Credibility · patearn", render_concalls(view),
                               "concalls", sig_date or "", wide=True))


@router.get("/dash/strategies", response_class=HTMLResponse)
def dash_strategies() -> RedirectResponse:
    """Legacy strategy hub — MERGED into /dash/strategist (the registry aliases
    `strategies`→strategist). Redirect; orphaned-screen panel decision 2026-07-02.
    Legacy cockpit render retained in git history."""
    return RedirectResponse("/dash/strategist", status_code=307)


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
        return HTMLResponse(_shell("CPR · patearn", body, "cpr", wide=True))

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
                               latest.get("D") or latest.get("W") or "", wide=True))


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
.snap{display:inline-block;background:var(--bg-1);border:1px solid var(--line-2);border-radius:7px;padding:2px 7px;margin:2px 4px 2px 0;font-size:11px;color:var(--ink);font-variant-numeric:tabular-nums}
.snap i{color:var(--ink-3);font-style:normal;margin-right:3px}
.tbtn{background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink);padding:5px 11px;border-radius:7px;font-size:12px;cursor:pointer;font-family:inherit}
.tbtn-go{background:#238636;border-color:#238636;color:#fff;font-weight:700}
.thq{color:#58a6ff;cursor:help;font-size:17px;line-height:1}
.trk-bar{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:12px}
.trk-lbl{width:170px;flex:none;color:var(--ink)}
.trk-val{width:48px;flex:none;text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.cap{background:var(--bg-2);border:1px solid #1f4d7a;border-radius:10px;padding:14px;margin:12px 0}
.cap label{display:block;color:var(--ink-2);font-size:11px;margin-bottom:4px}
.cap .field{background:var(--bg-1);border:1px solid var(--line-2);color:var(--ink);border-radius:7px;padding:8px 10px;font-size:13px;width:100%;font-family:inherit}
.cap .row2{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.cap textarea.field{min-height:48px;resize:vertical}
.ac-box{position:absolute;left:0;right:0;top:100%;z-index:30;background:var(--bg-1);border:1px solid var(--line-2);border-top:none;border-radius:0 0 7px 7px;max-height:260px;overflow:auto}
.ac-it{padding:6px 10px;cursor:pointer;font-size:13px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ac-it:hover,.ac-it.on{background:#1f6feb;color:#fff}
.ac-n{color:var(--ink-2);font-size:11px;margin-left:6px}
.ac-it:hover .ac-n,.ac-it.on .ac-n{color:#cde3ff}
.ckrow{display:flex;flex-wrap:wrap;gap:6px 14px;padding:8px 10px;background:var(--bg-1);border:1px solid var(--line-2);border-radius:7px}
.ck{display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--ink);cursor:pointer;white-space:nowrap}
.ck input{accent-color:#1f6feb;cursor:pointer;margin:0}
</style>"""

# Shows/hides the free-text "your own strategy" input when the "Manual" strategy
# CHECKBOX (marked data-cs) is ticked. Strategy is now a multi-select checkbox
# group (pick any number of presets + Manual), joined server-side into one
# comma-separated string. One definition, included with each form.
_CS_JS = ("<script>function _csToggle(s){var f=s.form;if(!f)return;"
          "var w=f.querySelector('.cs-wrap');if(!w)return;"
          "var on=!!s.checked;w.style.display=on?'':'none';"
          "if(!on){var i=w.querySelector('input');if(i)i.value='';}}"
          "document.addEventListener('DOMContentLoaded',function(){"
          "document.querySelectorAll('input[data-cs]').forEach(_csToggle);});</script>")


def _strategy_field(selected=(), manual_text=""):
    """The multi-select Strategy chooser shared by all Track forms: one checkbox per
    preset in `_TRACK_STRATEGIES` + a "Manual" box that reveals a free-text basis.
    `selected` = preset labels to pre-tick; `manual_text` = free-text to pre-fill
    (also ticks Manual). Checkboxes all POST under name="strategy" (a list), combined
    server-side by `_join_strategies` into the single comma-joined `strategy` column."""
    sel = set(selected or ())
    manual_on = bool((manual_text or "").strip()) or ("Manual" in sel)
    boxes = []
    for s in _TRACK_STRATEGIES:
        on = " checked" if (s in sel or (s == "Manual" and manual_on)) else ""
        extra = ' data-cs onchange="_csToggle(this)"' if s == "Manual" else ""
        boxes.append(
            f'<label class="ck"><input type="checkbox" name="strategy" '
            f'value="{_esc(s)}"{on}{extra}/>{_esc(s)}</label>')
    cs_disp = "" if manual_on else "none"
    return (
        '<label>Strategy <span class="mut" style="font-weight:400">· pick any number</span></label>'
        f'<div class="ckrow">{"".join(boxes)}</div>'
        f'<div class="cs-wrap" style="display:{cs_disp};margin-top:8px">'
        '<label>Your strategy / basis</label>'
        f'<input name="strategy_custom" class="field" maxlength="60" value="{_esc(manual_text)}" '
        'placeholder="name your own — e.g. 52w-high breakout, earnings surprise"/></div>')


def _join_strategies(picks, custom):
    """Combine the multi-select strategy checkboxes (`picks`, a list) + the optional
    Manual free-text (`custom`) into ONE comma-joined string, order-preserving and
    deduped. "Manual" is a marker for the free-text, never a stored label. Falls back
    to "Manual" when nothing was chosen (the column is NOT NULL)."""
    parts = []
    for s in (picks or []):
        s = (s or "").strip()
        if s and s != "Manual":
            parts.append(s)
    c = (custom or "").strip()[:60]
    if c:
        parts.append(c)
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return ", ".join(out) or "Manual"

# Portfolio entry helper: when List='open', reveals the optional entry date+price
# override, auto-fills the price from /dash/track/quote, and shows the valid OHLC
# range for the chosen date so an impossible price can't be entered.
_ENTRY_JS = (
    "<script>(function(){"
    "function E(f){return{sym:f.querySelector('[name=symbol]'),st:f.querySelector('[name=status]'),"
    "d:f.querySelector('[name=entry_date]'),p:f.querySelector('[name=entry_price]'),"
    "w:f.querySelector('.ent-wrap'),h:f.querySelector('.ent-hint')};}"
    "function tog(f){var e=E(f);if(!e.w)return;e.w.style.display=(e.st&&e.st.value==='open')?'':'none';}"
    "function quote(f){var e=E(f);if(!e.w||!e.sym)return;if(!(e.st&&e.st.value==='open'))return;"
    "var s=(e.sym.value||'').trim().toUpperCase();if(!s){if(e.h)e.h.textContent='';return;}"
    "var d=(e.d&&e.d.value)||'';"
    "fetch('/dash/track/quote?sym='+encodeURIComponent(s)+'&date='+encodeURIComponent(d))"
    ".then(function(r){return r.json();}).then(function(j){"
    "if(!j.ok){if(e.h)e.h.textContent='No price data for '+s+(d?(' on/before '+d):'')+'.';return;}"
    "if(e.h)e.h.innerHTML='Auto ₹'+j.close+' (close '+j.date+') · valid ₹'+j.low+'–₹'+j.high;"
    "if(e.p&&(!e.p.value||e.p.dataset.auto==='1')){e.p.value=j.close;e.p.dataset.auto='1';}"
    "}).catch(function(){});}"
    "function init(f){if(!f.querySelector('.ent-wrap'))return;tog(f);var e=E(f);"
    "if(e.st)e.st.addEventListener('change',function(){tog(f);quote(f);});"
    "if(e.sym){e.sym.addEventListener('blur',function(){quote(f);});"
    "e.sym.addEventListener('change',function(){quote(f);});}"
    "if(e.p)e.p.addEventListener('input',function(){e.p.dataset.auto='0';});"
    "if(e.d)e.d.addEventListener('change',function(){quote(f);});"
    "quote(f);}"
    "document.addEventListener('DOMContentLoaded',function(){"
    "document.querySelectorAll('form.cap').forEach(init);});})();</script>")

# Ticker autocomplete for the add box: a self-contained dropdown over the equity
# universe (symbol prefix from 2 chars + company-name substring from 3). Reads
# window._ACITEMS (a [{s:SYMBOL,n:Company}] list embedded once per page).
_AC_JS = (
    "<script>(function(){var IT=window._ACITEMS||[];"
    "function mk(inp){if(inp._ac)return;inp._ac=1;"
    "var p=inp.parentNode;p.style.position='relative';"
    "var b=document.createElement('div');b.className='ac-box';b.style.display='none';p.appendChild(b);"
    "var idx=-1,cur=[];"
    "function close(){b.style.display='none';idx=-1;}"
    "function pick(s){inp.value=s;close();inp.dispatchEvent(new Event('change',{bubbles:true}));}"
    "function render(L){cur=L;if(!L.length){close();return;}"
    "b.innerHTML=L.map(function(o,i){return '<div class=ac-it data-i='+i+'><b>'+o.s+'</b><span class=ac-n>'+o.n+'</span></div>';}).join('');"
    "b.style.display='';idx=-1;"
    "Array.prototype.forEach.call(b.children,function(el){el.addEventListener('mousedown',function(e){e.preventDefault();pick(cur[+el.getAttribute('data-i')].s);});});}"
    "function filt(){var q=(inp.value||'').trim().toUpperCase();if(q.length<2){close();return;}"
    "var pre=[],sub=[],nm=[];for(var i=0;i<IT.length;i++){var o=IT[i];"
    "if(o.s.indexOf(q)===0){pre.push(o);}else if(q.length>=3&&o.s.indexOf(q)>0){sub.push(o);}"
    "else if(q.length>=3&&o.n.toUpperCase().indexOf(q)>=0){nm.push(o);}"
    "if(pre.length>=25)break;}render(pre.concat(sub,nm).slice(0,25));}"
    "var t;inp.addEventListener('input',function(){clearTimeout(t);t=setTimeout(filt,110);});"
    "inp.addEventListener('keydown',function(e){if(b.style.display==='none')return;var its=b.children;"
    "if(e.key==='ArrowDown'){idx=Math.min(idx+1,its.length-1);e.preventDefault();}"
    "else if(e.key==='ArrowUp'){idx=Math.max(idx-1,0);e.preventDefault();}"
    "else if(e.key==='Enter'){if(idx>=0&&cur[idx]){pick(cur[idx].s);e.preventDefault();}return;}"
    "else if(e.key==='Escape'){close();return;}else return;"
    "Array.prototype.forEach.call(its,function(el,i){el.className='ac-it'+(i===idx?' on':'');});});"
    "inp.addEventListener('blur',function(){setTimeout(close,150);});}"
    "document.addEventListener('DOMContentLoaded',function(){"
    "document.querySelectorAll('input[data-ac]').forEach(mk);});})();</script>")


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


def _capture_snapshot(conn, sym, as_of=None):
    """Signal row + close -> (entry_price = close, frozen snapshot dict, trade_date).
    `as_of` (YYYY-MM-DD) freezes it as it stood on/before that date (for a backdated
    entry); default = latest. Used both to FREEZE at add time and to read LIVE."""
    if as_of:
        L = conn.execute("SELECT * FROM stock_signals WHERE symbol=? AND trade_date<=? "
                         "ORDER BY trade_date DESC LIMIT 1", (sym, as_of)).fetchone()
    else:
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


def _ohlc_on(conn, sym, date=None):
    """The EQ OHLC row for `sym` on `date` (the latest trading day on/before it), or
    the latest overall when date is None. Returns dict(trade_date,open,high,low,close)
    or None. Backs the entry auto-fill + the impossible-price validation."""
    base = ("SELECT trade_date, open, high, low, close FROM bhavcopy_rows "
            "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) ")
    if date:
        r = conn.execute(base + "AND trade_date<=? ORDER BY trade_date DESC LIMIT 1",
                         (sym, date)).fetchone()
    else:
        r = conn.execute(base + "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    return dict(r) if r else None


def _entry_in_day_range(lo, hi, px) -> bool:
    """Did `px` plausibly trade within the day's [lo,hi]? CL-DASH-10: the old check used a
    FIXED ±0.05 absolute band — meaningless across price scales (₹0.05 is nothing on a
    ₹5,000 stock and huge on a ₹3 stock). Use a RELATIVE tolerance: the larger of a tiny
    absolute floor (rounding) and 0.1% of the high (tick/feed noise), so the slack scales
    with the price. Returns True when lo/hi are unknown (can't validate → don't block)."""
    if lo is None or hi is None or px is None:
        return True
    tol = max(0.05, hi * 0.001)
    return (lo - tol) <= px <= (hi + tol)


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
    # The Tracker workspace's four segments: Dashboard (live cockpit), Portfolios
    # & Watchlists (the two list tiers), Performance (the over-time scoreboard).
    items = [("dashboard", "/dash/dashboard", "Dashboard"),
             ("portfolios", "/dash/portfolios", "Portfolios"),
             ("watchlists", "/dash/watchlists", "Watchlists"),
             ("performance", "/dash/performance", "Performance"),
             ("import", "/dash/import", "Import")]
    out = ['<div class="fbar" style="margin-bottom:12px">']
    for k, h, lbl in items:
        out.append(f'<a class="fbtn{" on" if k == active else ""}" href="{h}">{lbl}</a>')
    out.append("</div>")
    return "".join(out)


def _book_chips(base, books, sel):
    """Book filter chips on the Portfolios/Watchlists pages (named books)."""
    out = [f'<div class="fbar" style="margin:0 0 12px"><a class="fbtn{"" if sel else " on"}" href="{base}">All books</a>']
    for b in books:
        out.append(f'<a class="fbtn{" on" if b == sel else ""}" href="{base}?book={_q(b)}">{_esc(b)}</a>')
    out.append("</div>")
    return "".join(out)


def _rpl(v):
    """Coloured absolute ₹ P&L cell (qty × price move), signed + compact."""
    if v is None:
        return '<span class="mut">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "mut")
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f'<span class="{cls}">{sign}{_rupee(abs(v))}</span>'


def _rawnum(v):
    """Bare number for pre-filling an <input value> (no commas/spans); '' if None."""
    return "" if v is None else f"{v:g}"


# === Tracker enrichment (Steps 2-4) ========================================
# Sector · market-cap tier · live thesis-health · dividends · XIRR · equity
# curve / drawdown · allocation. Shared by Portfolios / Performance / Dashboard.
# All read-only point lookups; a tracked book is small (tens of rows) so
# per-symbol queries — cached per request via plain dicts — are cheap.

# Size tiers from index membership — denser + cleaner than the sparse
# fundamentals.market_cap_cr. First match wins, large→small.
_MCAP_TIER_IDX = (
    ("Large", ("Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200")),
    ("Mid",   ("Nifty Midcap 150", "Nifty Midcap 100", "Nifty Midcap 50")),
    ("Small", ("Nifty Smallcap 250", "Nifty Smallcap 100", "Nifty Smallcap 50")),
)
_TIER_CSS = {"Large": "p-A", "Mid": "p-B", "Small": "p-C"}


def _membership(conn, sym):
    """The set of index names `sym` currently belongs to (latest snapshot)."""
    try:
        return {r["index_name"] for r in conn.execute(
            "SELECT DISTINCT index_name FROM stock_index_membership WHERE symbol=? "
            "AND snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership "
            "WHERE symbol=?)", (sym, sym)).fetchall()}
    except Exception:
        return set()


def _enrich(conn, symbols):
    """Batch {sym: {sector, tier, mcap_cr, sig}} for a set of symbols. sig = the
    latest stock_signals row (accum_character, rs_rank, RS trend, key-gaps).
    sector = primary_sector (the narrowest sectoral index) with a membership
    fallback; tier = Large/Mid/Small from membership, fundamentals as backup."""
    out = {}
    for sym in set(symbols):
        sig = conn.execute("SELECT * FROM stock_signals WHERE symbol=? "
                           "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
        sig = dict(sig) if sig else {}
        mem = _membership(conn, sym)
        sec = sig.get("primary_sector")
        if not sec:
            cands = [ix for ix in mem if ix in REAL_SECTORS]
            sec = (min(cands, key=lambda ix: len(_sector_symbols(conn, ix)) or 99999)
                   if cands else None)
        tier = next((lbl for lbl, idxs in _MCAP_TIER_IDX if mem & set(idxs)), None)
        try:
            mcr = conn.execute("SELECT market_cap_cr FROM fundamentals WHERE symbol=?",
                               (sym,)).fetchone()
            mcr = mcr["market_cap_cr"] if mcr else None
        except Exception:
            mcr = None
        if not tier and mcr:
            tier = "Large" if mcr >= 50000 else ("Mid" if mcr >= 15000 else "Small")
        out[sym] = {"sector": sec, "tier": tier, "mcap_cr": mcr, "sig": sig}
    return out


def _sector_short(name):
    """'Nifty Private Bank' -> 'Private Bank' for compact cells."""
    if not name:
        return None
    return name[6:].strip() if name.startswith("Nifty ") else name


def _day_delta(conn, sym):
    """(close, day_change_pct, prev_close) from the latest EQ bhav row. EOD —
    last close vs the prior close, not a live tick."""
    r = conn.execute("SELECT close, prev_close FROM bhavcopy_rows WHERE symbol=? "
                     "AND series='EQ' AND (segment='CM' OR segment IS NULL) "
                     "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
    # A legit 0 close is real data, not "missing" — only None means no row/value.
    # (The day-change divisor below still guards a 0 prev_close: undefined, not no-data.)
    if not r or r["close"] is None:
        return None, None, None
    pc = r["prev_close"]
    dc = ((r["close"] - pc) / pc * 100.0) if pc else None
    return r["close"], dc, pc


def _dist_pct(cmp_, level, up_is_far):
    """Signed distance from CMP to a target/stop, as % of CMP. For a target
    (up_is_far=True) positive = upside remaining; for a stop (up_is_far=False)
    positive = cushion still above the stop (negative = breached)."""
    if not (cmp_ and level):
        return None
    return ((level - cmp_) if up_is_far else (cmp_ - level)) / cmp_ * 100.0


_DIV_RE = re.compile(
    r'(?:dividend|div\b)[^0-9]*?(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)', re.I)


def _dividend_per_share(row):
    """Best-effort ₹/share for a corporate_actions dividend row: ratio_to when
    present (NSE often parks the amount there), else a parse of `details`."""
    rt = row.get("ratio_to")
    if rt:
        try:
            return float(rt)
        except (TypeError, ValueError):
            pass
    m = _DIV_RE.search(row.get("details") or "")
    return float(m.group(1)) if m else None


def _dividends_since(conn, sym, since_date, qty):
    """Total ₹ dividends for `qty` shares with ex-date in [since_date, today],
    and the event count. corporate_actions is currently unpopulated, so this
    returns (0.0, 0) gracefully until that feed is ingested."""
    if not (since_date and qty):
        return 0.0, 0
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT action_type, ratio_to, details, ex_date FROM corporate_actions "
            "WHERE symbol=? AND ex_date>=? AND ex_date<=date('now') "
            "AND (lower(action_type) LIKE '%div%' OR lower(details) LIKE '%dividend%')",
            (sym, since_date[:10])).fetchall()]
    except Exception:
        return 0.0, 0
    tot, n = 0.0, 0
    for r in rows:
        dps = _dividend_per_share(r)
        if dps:
            tot += dps * qty
            n += 1
    return tot, n


# --- Live thesis-health (the Patearn differentiator) -----------------------
# "Is my thesis still valid?" — read the frozen-at-entry snapshot against the
# live signal row. Flags drive both the Portfolios health cell and the
# Dashboard "needs attention" board. Thresholds are deliberate defaults (a
# decision, recorded in PROJECT_STATE): RS decay = drop ≥10 rank pts OR now <40;
# conviction drop ≥10; DISTRIBUTION character is always a flag.
_HEALTH_FLAG_LABEL = {
    "dist":      ("🔴 distributing", "neg"),
    "rs_decay":  ("RS decaying", "neg"),
    "rs_weak":   ("RS weak (<40)", "neg"),
    "conv_drop": ("conviction ↓", "neg"),
    "near_stop": ("near stop", "neg"),
    "below_stop": ("below stop", "neg"),
}


def _thesis_flags(thn, sig, cmp_=None, stop=None):
    """Set of issue codes for a holding. thn = frozen snapshot dict (then),
    sig = live stock_signals row (now). Optional cmp_/stop add stop proximity."""
    flags = set()
    if not sig:
        sig = {}
    char = sig.get("accum_character")
    rs_now = sig.get("rs_rank")
    rs_then = thn.get("rs") if thn else None
    conv_now = (round(_conv_of(sig.get("p_score"), sig.get("rs_rank")))
                if sig.get("p_score") is not None or sig.get("rs_rank") is not None else None)
    conv_then = thn.get("conv") if thn else None
    if char == "DISTRIBUTION":
        flags.add("dist")
    if rs_now is not None:
        if rs_now < 40:
            flags.add("rs_weak")
        if rs_then is not None and rs_now <= rs_then - 10:
            flags.add("rs_decay")
    if conv_then is not None and conv_now is not None and conv_now <= conv_then - 10:
        flags.add("conv_drop")
    if cmp_ and stop:
        if cmp_ <= stop:
            flags.add("below_stop")
        elif (cmp_ - stop) / cmp_ * 100.0 <= 3.0:
            flags.add("near_stop")
    return flags


def _health_cell(thn, sig, cmp_=None, stop=None):
    """Compact thesis-health cell: character pill + RS rank + conviction drift,
    with a warning tint when any flag fires. Data-first — shows the live values,
    not just a verdict."""
    if not sig:
        return '<span class="mut">—</span>'
    flags = _thesis_flags(thn, sig, cmp_, stop)
    char = sig.get("accum_character")
    rs_now = sig.get("rs_rank")
    rs_then = thn.get("rs") if thn else None
    conv_now = round(_conv_of(sig.get("p_score"), sig.get("rs_rank")))
    conv_then = thn.get("conv") if thn else None
    bits = [_char_pill(char, dash_if_none=False) or '']
    if rs_now is not None:
        rs_cls = "neg" if ("rs_decay" in flags or "rs_weak" in flags) else "mut"
        rs_txt = (f'{rs_then}→{rs_now}' if rs_then is not None else f'{rs_now}')
        bits.append(f'<span class="snap"><i>RS</i><span class="{rs_cls}">{rs_txt}</span></span>')
    if conv_now is not None:
        bits.append(f'<span class="snap"><i>conv</i>{_then_now(conv_then, conv_now)}</span>')
    warn = [l for k, (l, _) in _HEALTH_FLAG_LABEL.items() if k in flags]
    if warn:
        bits.append(f'<span class="snap" style="background:var(--down-dim);border-color:rgba(var(--down-rgb),.35);color:var(--down)">⚠ {", ".join(warn)}</span>')
    return "".join(b for b in bits if b)


# --- XIRR (money-weighted return) — Newton + bisection, no scipy -----------
def _xirr(flows, guess=0.15):
    """Annualized money-weighted return for [(date, amount)] cash flows —
    outflows negative (buys), inflows positive (sells / current value). Returns
    a fraction (0.2 = 20%) or None if unsolvable (e.g. all-same-sign)."""
    flows = [(d, a) for d, a in flows if d and a]
    if len(flows) < 2 or not (any(a < 0 for _, a in flows) and any(a > 0 for _, a in flows)):
        return None
    try:
        t0 = min(datetime.fromisoformat(d[:10]) for d, _ in flows)
        yrs = [(datetime.fromisoformat(d[:10]) - t0).days / 365.0 for d, _ in flows]
    except Exception:
        return None
    amts = [a for _, a in flows]

    def npv(r):
        return sum(a / (1.0 + r) ** t for a, t in zip(amts, yrs))

    def dnpv(r):
        return sum(-t * a / (1.0 + r) ** (t + 1) for a, t in zip(amts, yrs))

    r = guess
    for _ in range(100):
        d = dnpv(r)
        if abs(d) < 1e-12:
            break
        nr = r - npv(r) / d
        if nr <= -0.9999:
            nr = (r - 0.9999) / 2
        if abs(nr - r) < 1e-7:
            return nr if -0.9999 < nr < 100 else None
        r = nr
    lo, hi = -0.9999, 100.0
    flo = npv(lo)
    if flo * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if abs(fm) < 1e-7:
            return mid
        if flo * fm < 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def _portfolio_xirr(conn, rows, cmps):
    """XIRR over holdings: buy = −qty·entry on date_added; closed sell =
    +qty·exit on exit_date; still-open = +qty·CMP today (synthetic liquidation).
    Skips rows without qty (can't weight a cash flow without a share count)."""
    flows = []
    today = datetime.now().strftime("%Y-%m-%d")
    for r in rows:
        q = r.get("qty")
        if not q:
            continue
        ep, da = r.get("entry_price"), (r.get("date_added") or "")[:10]
        if ep and da:
            flows.append((da, -q * ep))
        if r.get("status") == "closed" and r.get("exit_price") and r.get("exit_date"):
            flows.append(((r["exit_date"] or "")[:10], q * r["exit_price"]))
        elif r.get("status") != "closed":
            c = cmps.get(r["symbol"])
            if c:
                flows.append((today, q * c))
    return _xirr(flows)


# --- Equity curve + max drawdown -------------------------------------------
def _equity_curve(conn, rows, max_days=400):
    """Daily [(date, port_value, bench_value)] from the earliest entry to the
    latest trading day, over OPEN holdings that carry qty. port_value =
    Σ qty·close (forward-filled across non-trading gaps); bench = Nifty 500
    close. Capped to the last `max_days` trading days for cost."""
    holds = [(r["symbol"], r["qty"], (r["date_added"] or "")[:10])
             for r in rows if r.get("qty") and r.get("entry_price") and r.get("date_added")]
    if not holds:
        return []
    start = min(d for _, _, d in holds)
    cal = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM index_rows WHERE index_name='Nifty 500' "
        "AND trade_date>=? ORDER BY trade_date", (start,)).fetchall()]
    if not cal:
        return []
    if len(cal) > max_days:
        cal = cal[-max_days:]
    closes = {}
    for sym, _, _ in holds:
        closes[sym] = {r["trade_date"]: r["close"] for r in conn.execute(
            "SELECT trade_date, close FROM bhavcopy_rows WHERE symbol=? AND series='EQ' "
            "AND (segment='CM' OR segment IS NULL) AND trade_date>=? ORDER BY trade_date",
            (sym, cal[0])).fetchall()}
    bench = {r["trade_date"]: r["close_value"] for r in conn.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name='Nifty 500' "
        "AND trade_date>=? ORDER BY trade_date", (cal[0],)).fetchall()}
    series, last, lastb = [], {s: None for s, _, _ in holds}, None
    for d in cal:
        val, ok = 0.0, False
        for sym, q, da in holds:
            if d < da:
                continue
            c = closes[sym].get(d, last[sym])
            last[sym] = c
            if c:
                val += q * c
                ok = True
        lastb = bench.get(d, lastb)
        if ok:
            series.append((d, val, lastb))
    return series


def _max_drawdown(series):
    """Max peak-to-trough drawdown % (≤0) over [(date, value, ...)], plus the
    peak and trough dates. (None, None, None) for an empty series."""
    peak = peak_d = None
    worst, wp, wt = 0.0, None, None
    for row in series:
        d, v = row[0], row[1]
        if v is None:
            continue
        if peak is None or v > peak:
            peak, peak_d = v, d
        if peak:
            dd = (v - peak) / peak * 100.0
            if dd < worst:
                worst, wp, wt = dd, peak_d, d
    return (worst if series else None), wp, wt


def _curve_svg(series, w=920, h=140):
    """Inline SVG: portfolio value vs Nifty 500, both rebased to 100 at day 1."""
    pts = [(s[0], s[1], s[2]) for s in series if s[1] is not None]
    if len(pts) < 2:
        return '<div class="sub">Add quantity to your open positions to plot an equity curve.</div>'
    base_p = pts[0][1] or 1.0
    bvals = [p[2] for p in pts if p[2]]
    base_b = bvals[0] if bvals else None
    pser = [p[1] / base_p * 100.0 for p in pts]
    bser = [(p[2] / base_b * 100.0 if (p[2] and base_b) else None) for p in pts]
    allv = pser + [b for b in bser if b is not None]
    lo, hi = min(allv), max(allv)
    rng = (hi - lo) or 1.0
    n = len(pts)

    def x(i):
        return 8 + (i / (n - 1)) * (w - 16)

    def y(v):
        return h - 18 - (v - lo) / rng * (h - 30)

    def path(ser):
        d, pen = [], False
        for i, v in enumerate(ser):
            if v is None:
                pen = False
                continue
            d.append(("M" if not pen else "L") + f"{x(i):.1f},{y(v):.1f}")
            pen = True
        return " ".join(d)
    base_y = y(100.0)
    end_p = pser[-1]
    end_b = next((b for b in reversed(bser) if b is not None), None)
    leg = (f'<text x="{w-6}" y="14" text-anchor="end" font-size="11" fill="#3fb950">'
           f'portfolio {end_p:.0f}</text>')
    if end_b is not None:
        leg += (f'<text x="{w-6}" y="28" text-anchor="end" font-size="11" style="fill:var(--ink-2)">'
                f'Nifty 500 {end_b:.0f}</text>')
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="none" '
        f'style="background:var(--bg-1);border:1px solid var(--bg-3);border-radius:10px">'
        f'<line x1="8" y1="{base_y:.1f}" x2="{w-8}" y2="{base_y:.1f}" style="stroke:var(--line-2)" stroke-dasharray="3 3"/>'
        f'<path d="{path(bser)}" fill="none" style="stroke:var(--ink-3)" stroke-width="1.4"/>'
        f'<path d="{path(pser)}" fill="none" stroke="#3fb950" stroke-width="1.8"/>'
        f'{leg}</svg>')


# --- Allocation / concentration --------------------------------------------
def _alloc_bars(title, pairs, total, href_fn=None):
    """Horizontal allocation bars from [(label, value)] pairs (auto-sorted desc,
    % of total shown). Compact, data-first."""
    agg = {}
    for k, v in pairs:
        if v:
            agg[k] = agg.get(k, 0.0) + v
    if not agg or not total:
        return ''
    rows = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    out = [f'<div class="ghdr">{title}</div>']
    for k, v in rows:
        pc = v / total * 100.0
        lbl = _esc(k)
        if href_fn:
            lbl = f'<a href="{href_fn(k)}" style="color:inherit;text-decoration:none">{lbl}</a>'
        out.append(
            '<div class="trk-bar">'
            f'<span class="trk-lbl" style="width:150px">{lbl}</span>'
            f'<span class="bar" style="flex:1;height:14px"><span style="width:{pc:.0f}%"></span></span>'
            f'<span class="trk-val" style="width:96px">{_rupee(v)}</span>'
            f'<span class="mut" style="width:46px;text-align:right;font-size:11px">{pc:.0f}%</span>'
            '</div>')
    return "".join(out)


def _concentration(values):
    """Concentration of a book: largest single position + top-3/5/10 share of
    total. Returns [(label, pct)] for the buckets that apply (≥2 holdings)."""
    vals = sorted([v for v in values if v], reverse=True)
    total = sum(vals)
    if not total or len(vals) < 2:
        return []
    out = [("Largest", vals[0] / total * 100.0)]
    for n in (3, 5, 10):
        if len(vals) >= n:
            out.append((f"Top {n}", sum(vals[:n]) / total * 100.0))
    return out


def _company_core(name):
    """Distinctive core of a company name for news matching: drop the Ltd/Limited
    suffix + punctuation. None if too short to match safely."""
    if not name:
        return None
    s = re.sub(r'\b(Ltd|Limited|Ltd\.)\b\.?', '', name, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(' .,-&')
    return s if len(s) >= 4 else None


def _holdings_news(conn, symbols, limit=12, days=45):
    """Best-effort recent news for held/watched names. sent_news isn't ticker-
    tagged, so match the company-name core (and a ≥5-char first word / ticker)
    against the headline text. Returns [(symbol, news_row)] newest-first, deduped."""
    if not symbols:
        return []
    info = {}
    for sym in symbols:
        row = conn.execute("SELECT company_name FROM nse_equity_list WHERE symbol=?",
                           (sym,)).fetchone()
        nm = row["company_name"] if row else None
        toks = set()
        core = _company_core(nm)
        if core:
            toks.add(core.lower())
        if nm:
            fw = re.sub(r'[^A-Za-z0-9]', '', nm.split()[0]) if nm.split() else ''
            if len(fw) >= 5:
                toks.add(fw.lower())
        if len(sym) >= 5:
            toks.add(sym.lower())
        if toks:
            info[sym] = toks
    if not info:
        return []
    try:
        news = [dict(r) for r in conn.execute(
            "SELECT title, url, source, sent_at FROM sent_news WHERE sent_at>=date('now',?) "
            "ORDER BY sent_at DESC LIMIT 500", (f'-{days} days',)).fetchall()]
    except Exception:
        return []
    out, seen = [], set()
    for n in news:
        tl = (n["title"] or "").lower()
        for sym, toks in info.items():
            if n["url"] in seen:
                continue
            if any(t in tl for t in toks):
                seen.add(n["url"])
                out.append((sym, n))
                break
        if len(out) >= limit:
            break
    return out


def _upcoming_actions(conn, symbols, days=45):
    """Corporate actions (ex-date today..+days) for the given symbols. Empty until
    the corporate_actions feed is ingested."""
    if not symbols:
        return []
    try:
        ph = ",".join("?" * len(symbols))
        return [dict(r) for r in conn.execute(
            f"SELECT symbol, action_type, ex_date, details FROM corporate_actions "
            f"WHERE ex_date>=date('now') AND ex_date<=date('now',?) AND symbol IN ({ph}) "
            f"ORDER BY ex_date", [f'+{days} days'] + list(symbols)).fetchall()]
    except Exception:
        return []


def _split_strats(raw):
    """Split a Track position's strategy field into its component strategies.
    Multi-strategy positions store a comma-joined string (D77); single-strategy
    and free-text values pass through unchanged. Returns an order-preserving,
    de-duplicated list (so one position is never counted twice for the same
    strategy); a blank field yields an empty list."""
    parts, seen = [], set()
    for p in (raw or "").split(","):
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            parts.append(p)
    return parts


def _attrib_bars(title, pairs, top_n=8):
    """Signed ₹ return-attribution bars (green + / red −), sorted high→low, capped
    to the extreme movers (top contributors + detractors). % is share of total
    absolute P&L. Skips entries with no ₹ value (positions without qty)."""
    agg = {}
    for k, v in pairs:
        if v is not None:
            agg[k] = agg.get(k, 0.0) + v
    agg = {k: v for k, v in agg.items() if v}
    if not agg:
        return ''
    tot = sum(abs(v) for v in agg.values()) or 1.0
    mx = max(abs(v) for v in agg.values()) or 1.0
    rows = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    if len(rows) > top_n:
        half = top_n // 2
        rows = rows[:half] + rows[-half:]
    out = [f'<div class="ghdr">{title}</div>']
    for k, v in rows:
        col = "var(--up)" if v > 0 else "var(--down)"
        out.append(
            '<div class="trk-bar">'
            f'<span class="trk-lbl" style="width:150px">{_esc(k)}</span>'
            f'<span class="bar" style="flex:1;height:14px"><span style="width:{abs(v)/mx*100:.0f}%;background:{col}"></span></span>'
            f'<span class="trk-val" style="width:96px">{_rpl(v)}</span>'
            f'<span class="mut" style="width:46px;text-align:right;font-size:11px">{v/tot*100:+.0f}%</span>'
            '</div>')
    return "".join(out)


# --- Watchlist alerts engine (Step 5) — EOD-evaluated, in-app surfaced -------
# Rules live in stocks_in_play.alerts_json (a JSON list of {"t": type, "v": num}).
# Evaluated on page-load — the daily bhav ingest is the natural cadence. Telegram
# push stays deferred (the bot is network-blocked); firing rules surface in-app on
# Watchlists + Dashboard. "Ready to act" is automatic (zero-config) off live signals.
_ALERT_DEFS = [
    ("cross_up",     "Price ≥",                   True,  "₹"),
    ("cross_down",   "Price ≤",                   True,  "₹"),
    ("pct_since",    "Move since add ≥",          True,  "%"),
    ("near_52h",     "Near 52w high (within)",    True,  "%"),
    ("near_52l",     "Near 52w low (within)",     True,  "%"),
    ("rs_above",     "RS rank ≥",                 True,  ""),
    ("char_accum",   "Character flips to ACCUM",  False, ""),
    ("dvpt_trigger", "DVPT trigger fires (SS/S/A)", False, ""),
    ("near_target",  "Near target (within)",      True,  "%"),
    ("near_stop",    "Near / below stop (within)", True, "%"),
]


def _fiftytwo(conn, sym, cache):
    """(52w high, 52w low) of close over the last ~252 trading days; cached."""
    if sym in cache:
        return cache[sym]
    r = conn.execute(
        "SELECT MAX(close) hi, MIN(close) lo FROM (SELECT close FROM bhavcopy_rows "
        "WHERE symbol=? AND series='EQ' AND (segment='CM' OR segment IS NULL) "
        "ORDER BY trade_date DESC LIMIT 252)", (sym,)).fetchone()
    out = (r["hi"], r["lo"]) if r else (None, None)
    cache[sym] = out
    return out


def _eval_alerts(row, sig, cmp_, thn, f52):
    """The list of fired-rule messages for `row` right now. EOD — 'crosses' is read
    as 'has reached/passed' at the close. f52 = callable(sym)->(52w_hi, 52w_lo)."""
    rules = _load_json_field(row.get("alerts_json"), "alerts_json", [])  # CL-DASH-15
    if not rules:
        return []
    sig = sig or {}
    then = (thn or {}).get("close")
    out = []
    for rule in rules:
        t, v = rule.get("t"), rule.get("v")
        try:
            if t == "cross_up" and cmp_ and v is not None and cmp_ >= v:
                out.append(f"price ₹{cmp_:.1f} ≥ ₹{v:g}")
            elif t == "cross_down" and cmp_ and v is not None and cmp_ <= v:
                out.append(f"price ₹{cmp_:.1f} ≤ ₹{v:g}")
            elif t == "pct_since" and cmp_ and then and v is not None:
                ch = (cmp_ - then) / then * 100.0
                if abs(ch) >= v:
                    out.append(f"{ch:+.1f}% since add")
            elif t == "near_52h" and cmp_ and v is not None:
                hi = f52(row["symbol"])[0]
                if hi and (hi - cmp_) / hi * 100.0 <= v:
                    out.append(f"within {v:g}% of 52w high ₹{hi:.0f}")
            elif t == "near_52l" and cmp_ and v is not None:
                lo = f52(row["symbol"])[1]
                if lo and (cmp_ - lo) / lo * 100.0 <= v:
                    out.append(f"within {v:g}% of 52w low ₹{lo:.0f}")
            elif t == "rs_above" and v is not None and (sig.get("rs_rank") or 0) >= v:
                out.append(f"RS rank {sig.get('rs_rank')} ≥ {v:g}")
            elif t == "char_accum" and sig.get("accum_character") == "ACCUMULATION":
                out.append("character ACCUM")
            elif t == "dvpt_trigger" and sig.get("trigger_rank") in ("SS", "S", "A"):
                out.append(f"DVPT trigger {sig.get('trigger_rank')}")
            elif t == "near_target" and cmp_ and v is not None and row.get("price_target"):
                tg = row["price_target"]
                if cmp_ >= tg or (tg - cmp_) / cmp_ * 100.0 <= v:
                    out.append(f"within {v:g}% of target ₹{tg:g}")
            elif t == "near_stop" and cmp_ and v is not None and row.get("stop_loss"):
                st = row["stop_loss"]
                if cmp_ <= st or (cmp_ - st) / cmp_ * 100.0 <= v:
                    out.append(f"near/below stop ₹{st:g}")
        except Exception:
            continue
    return out


def _ready_to_act(sig):
    """Automatic 'a strong setup is live NOW' read for a watch item (zero-config):
    a fresh DVPT trigger, ACCUMULATION near the institutional key price or with
    strong RS, or an RS leader. Returns a short reason or None."""
    if not sig:
        return None
    char = sig.get("accum_character")
    rs = sig.get("rs_rank") or 0
    tr = sig.get("trigger_rank")
    reasons = []
    if tr in ("SS", "S"):
        reasons.append(f"DVPT trigger {tr}")
    if char == "ACCUMULATION" and is_near_key(sig.get("gap_to_key_p3m")):
        reasons.append("ACCUM near key price")
    if char == "ACCUMULATION" and rs >= 70:
        reasons.append(f"ACCUM + RS {rs}")
    if rs >= 85 and char != "DISTRIBUTION":
        reasons.append(f"RS leader {rs}")
    seen = list(dict.fromkeys(reasons))
    return " · ".join(seen) if seen else None


def _alert_badges(firing, ready):
    """Compact cell: a green 'ready to act' badge + amber firing-alert chips."""
    bits = []
    if ready:
        bits.append(f'<span class="snap" style="background:var(--up-dim);border-color:rgba(var(--up-rgb),.35);color:var(--up)">⚡ {_esc(ready)}</span>')
    for m in firing:
        bits.append(f'<span class="snap" style="background:#3a3417;border-color:#5a4a1f;color:#ffd99a">🔔 {_esc(m)}</span>')
    return "".join(bits) or '<span class="mut">—</span>'


def _alerts_form(row):
    """Per-item alert editor (POSTs /dash/track/alerts/save). Tick a rule + set a
    threshold; pre-filled from the saved alerts_json."""
    existing = {r["t"]: r.get("v")   # CL-DASH-15: parse via the counted/logged helper
                for r in _load_json_field(row["alerts_json"], "alerts_json", [])}
    lines = []
    for t, lbl, needs, unit in _ALERT_DEFS:
        chk = " checked" if t in existing else ""
        vinput = ""
        if needs:
            vv = _rawnum(existing.get(t)) if existing.get(t) is not None else ""
            vinput = (f'<input name="v_{t}" class="field" inputmode="decimal" style="width:110px" '
                      f'value="{vv}" placeholder="{unit or "value"}"/>')
        lines.append(
            '<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--bg-3)">'
            f'<label style="flex:1;display:flex;align-items:center;gap:8px;margin:0;cursor:pointer">'
            f'<input type="checkbox" name="on_{t}"{chk}/> {lbl}</label>{vinput}</div>')
    return (
        '<form class="cap" method="post" action="/dash/track/alerts/save">'
        f'<input type="hidden" name="id" value="{row["id"]}"/>'
        f'<div style="font-weight:600;margin-bottom:6px">Alerts for {_esc(row["symbol"])}</div>'
        '<div class="sub" style="margin:0 0 10px">EOD-evaluated on page-load; firing rules show on '
        'Watchlists + the Dashboard. <span class="mut">Telegram push deferred (bot network-blocked).</span></div>'
        + "".join(lines)
        + '<div style="margin-top:12px"><button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Save alerts</button>'
        f'<a class="tbtn" href="/dash/watchlists" style="text-decoration:none;margin-left:8px">Cancel</a></div>'
        '</form>')


def _capture_form(sym, snap):
    """The inline Track capture form (server-rendered; POSTs to /dash/track).
    Entry price + date + the frozen snapshot are captured SERVER-SIDE on submit
    (never trusted from the client) — this only previews what will be saved."""
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
        '<option value="watch">Watchlist · an idea</option></select></div></div>'
        f'<div style="margin-bottom:10px">{_strategy_field()}</div>'
        '<div class="ent-wrap" style="margin-bottom:10px">'
        '<div class="row2" style="margin-bottom:6px">'
        '<div style="flex:1"><label>Entry date (optional)</label>'
        '<input type="date" name="entry_date" class="field"/></div>'
        '<div style="flex:1"><label>Entry price ₹ (optional)</label>'
        '<input name="entry_price" class="field" inputmode="decimal" placeholder="auto = close"/></div>'
        '<div style="flex:1"><label>Qty (optional)</label>'
        '<input name="qty" class="field" inputmode="decimal" placeholder="shares"/></div></div>'
        '<div class="ent-hint mut" style="font-size:11px"></div></div>'
        '<div style="margin-bottom:10px"><label>Thesis — why now?</label>'
        '<textarea name="thesis" class="field" placeholder="e.g. p_score 5, fresh ACCUM off a base, '
        'close inside the key-price launch band"></textarea></div>'
        '<div class="row2">'
        '<div style="flex:1"><label>Target (optional)</label><input name="target" class="field" placeholder="₹"/></div>'
        '<div style="flex:1"><label>Stop (optional)</label><input name="stop" class="field" placeholder="₹"/></div></div>'
        '<div style="background:var(--bg-1);border:1px solid var(--bg-3);border-radius:8px;padding:10px;margin-bottom:12px">'
        '<div class="mut" style="font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">'
        f'Frozen snapshot · saved as of {_esc(asof)}</div>{_snap_chips(snap)}</div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Save</button>'
        f'<a class="tbtn" href="/dash/stock?sym={_q(sym)}" style="text-decoration:none;margin-left:8px">Cancel</a>'
        '</form>' + _CS_JS + _ENTRY_JS)


def _is_listed(conn, sym):
    """True unless we can POSITIVELY confirm `sym` is neither an NSE-listed equity
    nor has any signal history (i.e. a typo). Permissive on any lookup error so a
    missing table never blocks a legitimate add."""
    try:
        if conn.execute("SELECT 1 FROM nse_equity_list WHERE symbol=? LIMIT 1",
                        (sym,)).fetchone():
            return True
    except Exception:
        pass
    try:
        return bool(conn.execute("SELECT 1 FROM stock_signals WHERE symbol=? LIMIT 1",
                                 (sym,)).fetchone())
    except Exception:
        return True


_EQ_AC = {"key": None, "json": "[]"}


def _equities_ac_json():
    """Cached [{s,n}] equity universe (symbol + company name) for the add-box
    ticker autocomplete; rebuilt when the universe changes. The cache key is a
    fingerprint — COUNT(*) alone would serve STALE names through a rename that keeps
    the row count constant, so we also fold in MAX(rowid) (catches inserts / deletes /
    a re-ingested master where rowids advance) and SUM(LENGTH(company_name)) (catches
    an in-place name edit of the same rowid). All three are O(1) aggregates."""
    try:
        with get_conn() as conn:
            key = tuple(conn.execute(
                "SELECT COUNT(*), MAX(rowid), "
                "COALESCE(SUM(LENGTH(company_name)), 0) FROM nse_equity_list").fetchone())
            if _EQ_AC["key"] != key:
                rows = conn.execute("SELECT symbol, company_name FROM nse_equity_list "
                                    "ORDER BY symbol").fetchall()
                _EQ_AC.update(key=key, json=json.dumps(
                    [{"s": r["symbol"], "n": (r["company_name"] or "")} for r in rows]))
    except Exception:
        return "[]"
    return _EQ_AC["json"]


def _add_box(default_status, ac_json="[]", books=()):
    """Inline '+ Add a stock' quick-capture rendered directly on the Portfolios /
    Watchlists pages — so you can add without first opening a stock page. POSTs to
    the same /dash/track endpoint (entry price + frozen snapshot captured
    SERVER-SIDE); the symbol is typed and validated server-side via _is_listed.
    `books` = existing book names → a datalist for the named-book field."""
    bkopts = "".join(f'<option value="{_esc(b)}"></option>' for b in books)
    sel_open = " selected" if default_status == "open" else ""
    sel_watch = " selected" if default_status == "watch" else ""
    return (
        '<form class="cap" method="post" action="/dash/track" style="margin:0 0 14px">'
        '<div style="font-weight:600;margin-bottom:10px">+ Add a stock</div>'
        '<div class="row2">'
        '<div style="flex:2;min-width:160px"><label>NSE ticker</label>'
        '<input name="symbol" class="field" placeholder="e.g. BANDHANBNK or Bandhan" '
        'data-ac autocapitalize="characters" autocomplete="off" required/></div>'
        f'<div style="flex:1;min-width:110px"><label>List</label>'
        f'<select name="status" class="field"><option value="open"{sel_open}>Portfolio</option>'
        f'<option value="watch"{sel_watch}>Watchlist</option></select></div>'
        f'<div style="flex:1;min-width:110px"><label>Book</label>'
        f'<input name="book" class="field" list="bklist" value="Main" maxlength="40" placeholder="Main"/>'
        f'<datalist id="bklist">{bkopts}</datalist></div></div>'
        f'<div style="margin-bottom:10px">{_strategy_field()}</div>'
        f'<div class="ent-wrap" style="margin-bottom:10px;display:{"" if default_status == "open" else "none"}">'
        '<div class="row2" style="margin-bottom:6px">'
        '<div style="flex:1;min-width:130px"><label>Entry date (optional)</label>'
        '<input type="date" name="entry_date" class="field"/></div>'
        '<div style="flex:1;min-width:130px"><label>Entry price ₹ (optional)</label>'
        '<input name="entry_price" class="field" inputmode="decimal" placeholder="auto = close"/></div>'
        '<div style="flex:1;min-width:130px"><label>Qty (optional)</label>'
        '<input name="qty" class="field" inputmode="decimal" placeholder="shares"/></div></div>'
        '<div class="ent-hint mut" style="font-size:11px"></div></div>'
        '<div style="margin-bottom:10px"><label>Thesis — why now? (optional)</label>'
        '<input name="thesis" class="field" placeholder="e.g. fresh ACCUM off a base, p_score 5"/></div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Add</button>'
        '<a class="tbtn" href="/dash/import" style="text-decoration:none;margin-left:8px">⤓ Import file</a>'
        '</form>' + _CS_JS + _ENTRY_JS
        + f'<script>window._ACITEMS={ac_json};</script>' + _AC_JS)


def _edit_form(r, books):
    """Pre-filled form to EDIT a saved holding (POSTs /dash/track/update)."""
    sym = r["symbol"]
    # The stored strategy is a comma-joined multi-select: split it back into the
    # preset checkboxes we recognise + any leftover tokens (a hand-typed basis) that
    # pre-fill the Manual free-text.
    stored = [t.strip() for t in (r["strategy"] or "").split(",") if t.strip()]
    presets = set(_TRACK_STRATEGIES)
    sel = [t for t in stored if t in presets]
    manual_text = ", ".join(t for t in stored if t not in presets)
    bkopts = "".join(f'<option value="{_esc(b)}"></option>' for b in books)
    st = r["status"]
    o_sel = " selected" if st == "open" else ""
    w_sel = " selected" if st == "watch" else ""
    back = "/dash/watchlists" if st == "watch" else "/dash/portfolios"
    return (
        '<form class="cap" method="post" action="/dash/track/update">'
        f'<input type="hidden" name="id" value="{r["id"]}"/>'
        f'<div style="font-weight:600;margin-bottom:10px">Edit {_esc(sym)}</div>'
        '<div class="row2">'
        f'<div style="flex:1;min-width:110px"><label>List</label>'
        f'<select name="status" class="field"><option value="open"{o_sel}>Portfolio</option>'
        f'<option value="watch"{w_sel}>Watchlist</option></select></div>'
        f'<div style="flex:1;min-width:110px"><label>Book</label>'
        f'<input name="book" class="field" list="bklist" value="{_esc(r.get("book") or "Main")}" maxlength="40"/>'
        f'<datalist id="bklist">{bkopts}</datalist></div></div>'
        f'<div style="margin-bottom:10px">{_strategy_field(selected=sel, manual_text=manual_text)}</div>'
        '<div class="row2">'
        f'<div style="flex:1"><label>Entry date</label><input type="date" name="entry_date" class="field" value="{_esc((r["date_added"] or "")[:10])}"/></div>'
        f'<div style="flex:1"><label>Entry price ₹</label><input name="entry_price" class="field" inputmode="decimal" value="{_rawnum(r["entry_price"])}"/></div>'
        f'<div style="flex:1"><label>Qty</label><input name="qty" class="field" inputmode="decimal" value="{_rawnum(r.get("qty"))}"/></div></div>'
        '<div class="row2">'
        f'<div style="flex:1"><label>Target ₹</label><input name="target" class="field" inputmode="decimal" value="{_rawnum(r["price_target"])}"/></div>'
        f'<div style="flex:1"><label>Stop ₹</label><input name="stop" class="field" inputmode="decimal" value="{_rawnum(r["stop_loss"])}"/></div></div>'
        f'<div style="margin-bottom:10px"><label>Thesis</label><textarea name="thesis" class="field">{_esc(r["entry_thesis"] or "")}</textarea></div>'
        f'<div style="margin-bottom:10px"><label>Notes <span class="mut" style="font-weight:400">(your running log)</span></label><textarea name="notes" class="field">{_esc(r.get("notes") or "")}</textarea></div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Save changes</button>'
        f'<a class="tbtn" href="{back}" style="text-decoration:none;margin-left:8px">Cancel</a>'
        '</form>' + _CS_JS)


@router.post("/dash/track")
def dash_track(symbol: str = Form(...), strategy: List[str] = Form(default=[]),
               status: str = Form("open"), thesis: str = Form(""),
               target: str = Form(""), stop: str = Form(""),
               strategy_custom: str = Form(""), book: str = Form("Main"), qty: str = Form(""),
               entry_date: str = Form(""), entry_price: str = Form("")) -> RedirectResponse:
    sym = (symbol or "").upper().strip()
    status = status if status in ("watch", "open") else "open"
    dest = "/dash/watchlists" if status == "watch" else "/dash/portfolios"
    # Strategy = any number of preset checkboxes + the user's own free-text basis
    # (Manual), combined into one comma-joined string.
    strat = _join_strategies(strategy, strategy_custom)
    bk = (book or "Main").strip()[:40] or "Main"

    def _f(x):
        try:
            return float(str(x).replace(",", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            return None
    if not sym:
        return RedirectResponse(f"{dest}?err={_q('Enter a ticker to add.')}", status_code=303)
    with get_conn() as conn:
        if not _is_listed(conn, sym):
            return RedirectResponse(
                f"{dest}?err={_q(sym + ' is not a recognized NSE equity — check the ticker.')}",
                status_code=303)
        if status == "open":
            # A Portfolio position needs an entry. Resolve the entry day's OHLC (a
            # custom date snaps to the last trading day on/before it). The price is
            # the user's — validated to that day's [low, high] so a price that never
            # traded can't be saved — else the auto close. date_added = entry date.
            d_in = (entry_date or "").strip()
            o = _ohlc_on(conn, sym, d_in or None)
            if not o:
                return RedirectResponse(
                    f"{dest}?err={_q(sym + ' has no price data on/before ' + (d_in or 'the latest day') + '.')}",
                    status_code=303)
            td, lo, hi, close = o["trade_date"], o["low"], o["high"], o["close"]
            ep_in = _f(entry_price)
            if ep_in is None:
                ep = close
            elif not _entry_in_day_range(lo, hi, ep_in):   # CL-DASH-10: relative band
                return RedirectResponse(
                    f"{dest}?err={_q(f'{sym} traded ₹{lo:g}–₹{hi:g} on {td}. ₹{ep_in:g} never traded that day — enter a price in that range.')}",
                    status_code=303)
            else:
                ep = ep_in
            snap = _capture_snapshot(conn, sym, as_of=td)[1]
            conn.execute(
                "INSERT INTO stocks_in_play(symbol,strategy,book,status,date_added,entry_price,qty,"
                "price_target,stop_loss,entry_thesis,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (sym, strat, bk, status, td, ep, _f(qty),
                 _f(target), _f(stop), (thesis or "").strip() or None,
                 json.dumps(snap) if snap else None))
        else:
            # A Watchlist idea: no entry, no commitment. The snapshot still records
            # the as-of price for reference; date_added defaults to now.
            snap = _capture_snapshot(conn, sym)[1]
            conn.execute(
                "INSERT INTO stocks_in_play(symbol,strategy,book,status,entry_price,qty,"
                "price_target,stop_loss,entry_thesis,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (sym, strat, bk, status, None, _f(qty),
                 _f(target), _f(stop), (thesis or "").strip() or None,
                 json.dumps(snap) if snap else None))
    return RedirectResponse(f"{dest}?added={_q(sym)}", status_code=303)


@router.get("/dash/track/quote")
def dash_track_quote(sym: str = Query(""), date: str = Query("")):
    """Read-only helper for the entry form: the EQ OHLC for `sym` on/before `date`
    (latest if blank). Powers the auto-fill price + the visible valid range."""
    s = (sym or "").upper().strip()
    if not s:
        return {"ok": False}
    with get_conn() as conn:
        o = _ohlc_on(conn, s, (date or "").strip() or None)
    if not o:
        return {"ok": False, "sym": s}
    return {"ok": True, "sym": s, "date": o["trade_date"],
            "close": o["close"], "low": o["low"], "high": o["high"]}


@router.post("/dash/track/close")
def dash_track_close(id: int = Form(...), reason: str = Form("")) -> RedirectResponse:
    # Never write a NULL-price close: a bad/foreign id (no row) or an uncapturable
    # snapshot (ep is None) would otherwise close the position with exit_price=NULL,
    # which a later reopen could resurrect — corrupting realised-P/L and XIRR. Only
    # UPDATE when the row exists AND we have an exit price; otherwise surface the error.
    with get_conn() as conn:
        row = conn.execute("SELECT symbol FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        ep = _capture_snapshot(conn, row["symbol"])[0] if row else None
        if not row:
            return RedirectResponse(
                f"/dash/performance?err={_q('That holding no longer exists — nothing closed.')}",
                status_code=303)
        if ep is None:
            return RedirectResponse(
                f"/dash/performance?err={_q('No closing price available for ' + str(row['symbol']) + ' — not closed (would corrupt P/L). Try again once an EOD price is in.')}",
                status_code=303)
        conn.execute("UPDATE stocks_in_play SET status='closed', exit_date=datetime('now'), "
                     "exit_price=?, exit_reason=? WHERE id=?",
                     (ep, (reason or "").strip() or None, id))
    return RedirectResponse("/dash/performance?closed=1", status_code=303)


@router.post("/dash/track/reopen")
def dash_track_reopen(id: int = Form(...)) -> RedirectResponse:
    # Undo a fat-fingered close: closed → open again, clearing the exit fields.
    with get_conn() as conn:
        conn.execute("UPDATE stocks_in_play SET status='open', exit_date=NULL, "
                     "exit_price=NULL, exit_reason=NULL WHERE id=?", (id,))
    return RedirectResponse("/dash/portfolios", status_code=303)


@router.get("/dash/track/edit", response_class=HTMLResponse)
def dash_track_edit(id: int = Query(...)) -> HTMLResponse:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        books = [r[0] for r in conn.execute(
            "SELECT DISTINCT book FROM stocks_in_play ORDER BY book").fetchall()]
    if not row:
        body = _TRACK_CSS + _track_subnav("portfolios") + '<div class="empty">That holding no longer exists.</div>'
        return HTMLResponse(_shell("Edit · patearn", body, "portfolios"))
    row = dict(row)
    active = "watchlists" if row["status"] == "watch" else "portfolios"
    body = _TRACK_CSS + _track_subnav(active) + '<h2>Edit holding</h2>' + _edit_form(row, books)
    return HTMLResponse(_shell("Edit · patearn", body, active))


@router.post("/dash/track/update")
def dash_track_update(id: int = Form(...), status: str = Form("open"),
                      book: str = Form("Main"), strategy: List[str] = Form(default=[]),
                      strategy_custom: str = Form(""), qty: str = Form(""),
                      entry_date: str = Form(""), entry_price: str = Form(""),
                      target: str = Form(""), stop: str = Form(""),
                      thesis: str = Form(""), notes: str = Form("")) -> RedirectResponse:
    status = status if status in ("watch", "open") else "open"
    dest = "/dash/watchlists" if status == "watch" else "/dash/portfolios"
    strat = _join_strategies(strategy, strategy_custom)
    bk = (book or "Main").strip()[:40] or "Main"

    def _f(x):
        try:
            return float(str(x).replace(",", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            return None
    with get_conn() as conn:
        row = conn.execute("SELECT symbol FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        if not row:
            return RedirectResponse(dest, status_code=303)
        sym = row["symbol"]
        ep = None
        td = None
        if status == "open":
            # Re-validate the (possibly edited) entry price against that day's OHLC.
            o = _ohlc_on(conn, sym, (entry_date or "").strip() or None)
            if o:
                td, lo, hi, close = o["trade_date"], o["low"], o["high"], o["close"]
                ep_in = _f(entry_price)
                if ep_in is None:
                    ep = close
                elif not _entry_in_day_range(lo, hi, ep_in):   # CL-DASH-10: relative band
                    return RedirectResponse(
                        f"{dest}?err={_q(f'{sym} traded ₹{lo:g}–₹{hi:g} on {td}. ₹{ep_in:g} never traded that day — enter a price in that range.')}",
                        status_code=303)
                else:
                    ep = ep_in
            else:
                ep = _f(entry_price)
        sets = "strategy=?, book=?, status=?, qty=?, price_target=?, stop_loss=?, entry_thesis=?, notes=?"
        vals = [strat, bk, status, _f(qty), _f(target), _f(stop), (thesis or "").strip() or None,
                (notes or "").strip() or None]
        if status == "open":
            sets += ", entry_price=?, date_added=COALESCE(?, date_added)"
            vals += [ep, td]
        else:
            sets += ", entry_price=NULL"
        vals.append(id)
        conn.execute(f"UPDATE stocks_in_play SET {sets} WHERE id=?", vals)
    return RedirectResponse(dest, status_code=303)


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
        row = conn.execute("SELECT status FROM stocks_in_play WHERE id=?", (id,)).fetchone()
        dest = "/dash/watchlists" if (row and row["status"] == "watch") else "/dash/portfolios"
        conn.execute("DELETE FROM stocks_in_play WHERE id=?", (id,))
    return RedirectResponse(dest, status_code=303)


@router.get("/dash/track/alerts", response_class=HTMLResponse)
def dash_track_alerts(id: int = Query(...)) -> HTMLResponse:
    """Per-item alert editor (Step 5)."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM stocks_in_play WHERE id=?", (id,)).fetchone()
    if not row:
        body = _TRACK_CSS + _track_subnav("watchlists") + '<div class="empty">That item no longer exists.</div>'
        return HTMLResponse(_shell("Alerts · patearn", body, "watchlists"))
    row = dict(row)
    active = "watchlists" if row["status"] == "watch" else "portfolios"
    body = _TRACK_CSS + _track_subnav(active) + "<h2>Alerts</h2>" + _alerts_form(row)
    return HTMLResponse(_shell("Alerts · patearn", body, active))


@router.post("/dash/track/alerts/save")
async def dash_track_alerts_save(request: Request) -> RedirectResponse:
    """Build alerts_json from the editor's dynamic on_<t>/v_<t> fields and save it.
    A value rule ticked without a valid threshold is dropped (it needs a number)."""
    form = await request.form()
    try:
        rid = int(str(form.get("id")))
    except (TypeError, ValueError):
        return RedirectResponse("/dash/watchlists", status_code=303)
    rules = []
    for t, _lbl, needs, _unit in _ALERT_DEFS:
        if not form.get(f"on_{t}"):
            continue
        rule = {"t": t}
        if needs:
            try:
                rule["v"] = float(str(form.get(f"v_{t}", "")).replace(",", "").replace("₹", "").strip())
            except (TypeError, ValueError):
                continue
        rules.append(rule)
    dest = "/dash/watchlists"
    with get_conn() as conn:
        r = conn.execute("SELECT status FROM stocks_in_play WHERE id=?", (rid,)).fetchone()
        if r:
            dest = "/dash/watchlists" if r["status"] == "watch" else "/dash/portfolios"
            conn.execute("UPDATE stocks_in_play SET alerts_json=? WHERE id=?",
                         (json.dumps(rules) if rules else None, rid))
    return RedirectResponse(dest, status_code=303)


@router.get("/dash/tracker/portfolios", response_class=HTMLResponse)
def dash_portfolios(added: str = Query(""), err: str = Query(""), book: str = Query("")) -> HTMLResponse:
    sel_book = book.strip()
    with get_conn() as conn:
        allrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='open' "
            "ORDER BY book, strategy, date_added DESC").fetchall()]
        books = [r[0] for r in conn.execute(
            "SELECT DISTINCT book FROM stocks_in_play WHERE status='open' ORDER BY book").fetchall()]
        ac = _equities_ac_json()
        rows = [r for r in allrows if (r.get("book") or "Main") == sel_book] if sel_book else allrows
        syms = {r["symbol"] for r in rows}
        live, dd = {}, {}
        for sym in syms:
            ep, snap, _ = _capture_snapshot(conn, sym)
            live[sym] = (ep, snap)
            dd[sym] = _day_delta(conn, sym)
        enr = _enrich(conn, syms)
        divs = {r["id"]: _dividends_since(conn, r["symbol"], r.get("date_added") or "", r.get("qty"))
                for r in rows}
        cmps = {s: live[s][0] for s in syms}
        xirr = _portfolio_xirr(conn, rows, cmps)
    intro = ('<h2>Portfolios</h2><div class="sub"><b>Positions you\'ve committed to</b> — money in: '
             'a frozen entry, live P/L, target/stop distance, and a live <b>thesis-health</b> read '
             '(is the strong hand still accumulating; is RS holding; has conviction drifted since you '
             'bought). Keep several named books. <span class="mut">Just watching? Use the '
             '<a href="/dash/watchlists" style="color:#58a6ff;text-decoration:none">Watchlist</a>; '
             'the scorecard is under '
             '<a href="/dash/performance" style="color:#58a6ff;text-decoration:none">Performance</a>.</span></div>')
    flash = (f'<div class="banner b-on">Added <b>{_esc(added)}</b> to your portfolio.</div>'
             if added else "")
    if err:
        flash += f'<div class="banner b-off">{_esc(err)}</div>'
    chips = _book_chips("/dash/portfolios", books, sel_book) if books else ""
    addbox = _add_box("open", ac, books)
    if not rows:
        empty = ('<div class="empty">No open positions'
                 + (f' in <b>{_esc(sel_book)}</b>' if sel_book else '')
                 + ' yet. Add one above, or open any stock and hit <b>+ Track</b> → <b>Portfolio</b>.</div>')
        body = _TRACK_CSS + _track_subnav("portfolios") + intro + flash + addbox + chips + empty
        return HTMLResponse(_shell("Portfolios · patearn", body, "portfolios", wide=True))
    # ---- header KPIs over the displayed rows ----
    inv = cur = 0.0
    pls, day_num, day_den, tot_div = [], 0.0, 0.0, 0.0
    hold_vals = []   # (sector, tier, value) for allocation / concentration
    for r in rows:
        sym = r["symbol"]
        cmp_, _ = live.get(sym, (None, {}))
        ep, q = r["entry_price"], r.get("qty")
        if cmp_ and ep:
            pls.append((cmp_ - ep) / ep * 100.0)
        if q and ep:
            inv += q * ep
            if cmp_:
                cur += q * cmp_
                _, _dcp, pc = dd.get(sym, (None, None, None))
                if pc:
                    day_num += q * (cmp_ - pc)
                    day_den += q * pc
                e = enr.get(sym, {})
                hold_vals.append((_sector_short(e.get("sector")) or "—",
                                  e.get("tier") or "—", q * cmp_))
        tot_div += divs.get(r["id"], (0.0, 0))[0]
    rpl_tot = (cur - inv) if inv else None
    pl_pct = (rpl_tot / inv * 100.0) if inv else (sum(pls) / len(pls) if pls else None)
    day_pct = (day_num / day_den * 100.0) if day_den else None
    pl_extra = f' <span style="font-size:13px">{_pct(pl_pct)}</span>' if pl_pct is not None else ''
    xirr_cell = f'{xirr*100:+.1f}%' if xirr is not None else '<span class="mut">—</span>'

    def kc(lbl, val):
        return f'<div class="box"><div class="num">{val}</div><div class="lbl">{lbl}</div></div>'
    hdr = ('<div class="kpi" style="margin-bottom:12px">'
           + kc("positions", len(rows))
           + kc("invested", _rupee(inv) if inv else '<span class="mut">—</span>')
           + kc("value", _rupee(cur) if cur else '<span class="mut">—</span>')
           + kc("₹ P&amp;L", _rpl(rpl_tot) + pl_extra)
           + kc("day Δ", _pct(day_pct))
           + kc("XIRR", xirr_cell)
           + '</div>')
    # ---- per-holding rows ----
    today = datetime.now().strftime("%Y-%m-%d")
    trs = []
    for r in rows:
        sym = r["symbol"]
        cmp_, _nowsnap = live.get(sym, (None, {}))
        e = enr.get(sym, {})
        sig = e.get("sig") or {}
        ep, q = r["entry_price"], r.get("qty")
        pl = ((cmp_ - ep) / ep * 100.0) if (cmp_ and ep) else None
        _, dcp, _pc = dd.get(sym, (None, None, None))
        thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
        invv = (q * ep) if (q and ep) else None
        rpl = (q * (cmp_ - ep)) if (q and cmp_ is not None and ep) else None
        tdist = _dist_pct(cmp_, r["price_target"], True)
        sdist = _dist_pct(cmp_, r["stop_loss"], False)
        dheld = _days_between(r["date_added"], today)
        dv_tot, dv_n = divs.get(r["id"], (0.0, 0))
        thesis = r["entry_thesis"] or ""
        sec = _sector_short(e.get("sector"))
        tier = e.get("tier")
        sec_cell = _esc(sec) if sec else '<span class="mut">—</span>'
        tier_cell = (f'<span class="pill {_TIER_CSS.get(tier, "p-C")}">{tier}</span>'
                     if tier else '<span class="mut">—</span>')
        q_cell = _num(q, 0) if q else '<span class="mut">—</span>'
        inv_cell = _rupee(invv) if invv else '<span class="mut">—</span>'
        tgt_cell = (f'{_num(r["price_target"], 1)} <span class="mut" style="font-size:11px">{_pct(tdist)}</span>'
                    if r["price_target"] is not None else '<span class="mut">—</span>')
        stop_cell = (f'{_num(r["stop_loss"], 1)} <span class="mut" style="font-size:11px">{_pct(sdist)}</span>'
                     if r["stop_loss"] is not None else '<span class="mut">—</span>')
        days_cell = f'{dheld}d' if dheld is not None else '<span class="mut">—</span>'
        div_cell = (f'{_rupee(dv_tot)} <span class="mut" style="font-size:11px">×{dv_n}</span>'
                    if dv_tot else '<span class="mut">—</span>')
        health = _health_cell(thn, sig, cmp_, r["stop_loss"])
        trs.append(
            '<tr>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_q(sym)}"><span class="sym">{_esc(sym)}</span></a></td>'
            f'<td class="l">{sec_cell}</td>'
            f'<td class="l">{tier_cell}</td>'
            f'<td class="l mut">{_esc(r.get("book") or "Main")}</td>'
            f'<td class="l mut">{_esc(r["strategy"])}</td>'
            f'<td class="mut">{_esc((r["date_added"] or "")[:10])}</td>'
            f'<td class="num">{_num(ep, 1)}</td>'
            f'<td class="num">{q_cell}</td>'
            f'<td class="num">{inv_cell}</td>'
            f'<td class="num">{_num(cmp_, 1)}</td>'
            f'<td class="num">{_pct(dcp)}</td>'
            f'<td class="num">{_pct(pl)}</td>'
            f'<td class="num">{_rpl(rpl)}</td>'
            f'<td class="num">{tgt_cell}</td>'
            f'<td class="num">{stop_cell}</td>'
            f'<td class="num">{days_cell}</td>'
            f'<td class="l">{health}</td>'
            f'<td class="num">{div_cell}</td>'
            f'<td class="l"><a class="tbtn" href="/dash/track/edit?id={r["id"]}" style="text-decoration:none">Edit</a> {_id_form("/dash/track/close", r["id"], "Close", confirm="Close this position?")}</td>'
            '</tr>')
    head = ('<table class="dt"><thead><tr>'
            '<th>Symbol</th><th>Sector</th><th>Cap</th><th>Book</th><th>Strategy</th><th>Entry date</th>'
            '<th>Entry ₹</th><th>Qty</th><th>Invested</th><th>CMP</th><th>Day Δ</th><th>P/L</th>'
            '<th>₹ P&amp;L</th><th>Target</th><th>Stop</th><th>Days</th><th>Thesis health</th>'
            '<th>Div</th><th></th></tr></thead><tbody>')
    table = head + "".join(trs) + "</tbody></table>"
    bq = f"&book={_q(sel_book)}" if sel_book else ""
    exp = ('<div style="display:flex;justify-content:flex-end;margin:0 0 8px">'
           f'<a class="tbtn" href="/dash/track/export?status=open{bq}" style="text-decoration:none">⬇ Export CSV</a></div>')
    # ---- allocation / concentration over displayed rows that carry value ----
    alloc = ''
    if hold_vals:
        tot = sum(v for *_, v in hold_vals)
        sec_b = _alloc_bars("By sector", [(s, v) for s, _t, v in hold_vals], tot)
        cap_b = _alloc_bars("By market-cap", [(t, v) for _s, t, v in hold_vals], tot)
        conc = _concentration([v for *_, v in hold_vals])
        conc_html = ''
        if conc:
            conc_html = ('<div class="ghdr">Concentration</div><div class="chips">'
                         + "".join(f'<span class="chip">{lbl} · <b>{pc:.0f}%</b></span>'
                                   for lbl, pc in conc) + '</div>')
        if sec_b or cap_b or conc_html:
            alloc = ('<details style="margin-top:16px"><summary class="ghdr" style="cursor:pointer">'
                     '▸ Allocation &amp; concentration</summary>'
                     '<div style="margin-top:8px">' + sec_b + cap_b + conc_html + '</div></details>')
    body = (_TRACK_CSS + _track_subnav("portfolios") + intro + flash + addbox + chips
            + hdr + exp + table + alloc)
    return HTMLResponse(_shell("Portfolios · patearn", body, "portfolios", wide=True))


@router.get("/dash/tracker/watchlists", response_class=HTMLResponse)
def dash_watchlists(added: str = Query(""), err: str = Query(""), book: str = Query("")) -> HTMLResponse:
    sel_book = book.strip()
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        allrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='watch' ORDER BY book, date_added DESC").fetchall()]
        books = [r[0] for r in conn.execute(
            "SELECT DISTINCT book FROM stocks_in_play WHERE status='watch' ORDER BY book").fetchall()]
        ac = _equities_ac_json()
        rows = [r for r in allrows if (r.get("book") or "Main") == sel_book] if sel_book else allrows
        syms = {r["symbol"] for r in rows}
        live = {}
        for sym in syms:
            c, snap, _ = _capture_snapshot(conn, sym)
            live[sym] = (c, snap)
        enr = _enrich(conn, syms)
        f52c = {}
        # evaluate alerts + ready-to-act per row (needs conn for the 52w lookup)
        alerts = {}
        for r in rows:
            sym = r["symbol"]
            sig = (enr.get(sym) or {}).get("sig") or {}
            thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
            firing = _eval_alerts(r, sig, live.get(sym, (None, {}))[0], thn,
                                  lambda s: _fiftytwo(conn, s, f52c))
            alerts[r["id"]] = (firing, _ready_to_act(sig))
    intro = ('<h2>Watchlists</h2><div class="sub"><b>Ideas you\'re watching</b> — no entry, no '
             'commitment yet. Each shows live signals, a ⚡ <b>ready-to-act</b> read when a strong '
             'setup is live, and any 🔔 <b>alerts</b> you set firing. <b>Promote</b> when you act. '
             '<span class="mut">Already committed? That belongs in the '
             '<a href="/dash/portfolios" style="color:#58a6ff;text-decoration:none">Portfolio</a>.</span></div>')
    flash = (f'<div class="banner b-on">Added <b>{_esc(added)}</b> to your watchlist.</div>'
             if added else "")
    if err:
        flash += f'<div class="banner b-off">{_esc(err)}</div>'
    chips = _book_chips("/dash/watchlists", books, sel_book) if books else ""
    addbox = _add_box("watch", ac, books)
    if not rows:
        empty = ('<div class="empty">No watchlist items'
                 + (f' in <b>{_esc(sel_book)}</b>' if sel_book else '')
                 + ' yet. Add one above, or on any stock page hit <b>+ Track</b> → <b>Watchlist</b>.</div>')
        body = _TRACK_CSS + _track_subnav("watchlists") + intro + flash + addbox + chips + empty
        return HTMLResponse(_shell("Watchlists · patearn", body, "watchlists", wide=True))
    # "ready to act" banner — the watch items now firing a strong setup
    ready_syms = [r["symbol"] for r in rows if alerts.get(r["id"], ([], None))[1]]
    ready_banner = ''
    if ready_syms:
        ready_banner = ('<div class="banner b-on">⚡ <b>Ready to act</b> — '
                        + ", ".join(f'<a href="/dash/stock?sym={_q(s)}" style="color:inherit">{_esc(s)}</a>'
                                    for s in ready_syms[:12])
                        + ' show a strong setup live now.</div>')
    trs = []
    for r in rows:
        sym = r["symbol"]
        cmp_, snap = live.get(sym, (None, {}))
        e = enr.get(sym, {})
        thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
        then = thn.get("close")     # frozen close on the day it was added
        chg = ((cmp_ - then) / then * 100.0) if (cmp_ and then) else None
        dwatch = _days_between(r["date_added"], today)
        sec = _sector_short(e.get("sector"))
        sec_cell = _esc(sec) if sec else '<span class="mut">—</span>'
        dw_cell = f'{dwatch}d' if dwatch is not None else '<span class="mut">—</span>'
        firing, ready = alerts.get(r["id"], ([], None))
        trs.append(
            '<tr>'
            f'<td class="l"><a class="row" href="/dash/stock?sym={_q(sym)}"><span class="sym">{_esc(sym)}</span></a></td>'
            f'<td class="l">{sec_cell}</td>'
            f'<td class="l mut">{_esc(r.get("book") or "Main")}</td>'
            f'<td class="l mut">{_esc(r["strategy"])}</td>'
            f'<td class="mut">{_esc((r["date_added"] or "")[:10])}</td>'
            f'<td class="num">{dw_cell}</td>'
            f'<td class="num">{_num(then, 1)}</td>'
            f'<td class="num">{_num(cmp_, 1)}</td>'
            f'<td class="num">{_pct(chg)}</td>'
            f'<td class="num">{_num(r.get("price_target"), 1)}</td>'
            f'<td class="num">{_num(r.get("stop_loss"), 1)}</td>'
            f'<td class="l">{_snap_chips(snap)}</td>'
            f'<td class="l">{_alert_badges(firing, ready)}</td>'
            f'<td class="l"><a class="tbtn" href="/dash/track/alerts?id={r["id"]}" style="text-decoration:none">Alerts</a> '
            f'<a class="tbtn" href="/dash/track/edit?id={r["id"]}" style="text-decoration:none">Edit</a> '
            f'{_id_form("/dash/track/promote", r["id"], "Promote", cls="tbtn tbtn-go")}'
            f'{_id_form("/dash/track/remove", r["id"], "Remove", confirm="Remove from watchlist?")}</td>'
            '</tr>')
    head = ('<table class="dt"><thead><tr><th>Symbol</th><th>Sector</th><th>Book</th><th>Strategy</th><th>Added</th>'
            '<th>Days</th><th>Price then</th><th>CMP</th><th>Chg %</th><th>Target</th><th>Stop</th>'
            '<th>Live signals</th><th>Signal / alerts</th><th></th></tr></thead><tbody>')
    bq = f"&book={_q(sel_book)}" if sel_book else ""
    exp = ('<div style="display:flex;justify-content:flex-end;margin:0 0 8px">'
           f'<a class="tbtn" href="/dash/track/export?status=watch{bq}" style="text-decoration:none">⬇ Export CSV</a></div>')
    body = (_TRACK_CSS + _track_subnav("watchlists") + intro + flash + ready_banner + addbox + chips
            + exp + head + "".join(trs) + "</tbody></table>")
    return HTMLResponse(_shell("Watchlists · patearn", body, "watchlists", wide=True))


@router.get("/dash/tracker/performance", response_class=HTMLResponse)
def dash_performance(just_closed: str = Query("", alias="closed"),
                     err: str = Query("")) -> HTMLResponse:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        openrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='open'").fetchall()]
        closed = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='closed' "
            "AND entry_price>0 AND exit_price IS NOT NULL ORDER BY exit_date DESC").fetchall()]
        syms = {r["symbol"] for r in openrows} | {r["symbol"] for r in closed}
        cmps = {r["symbol"]: _capture_snapshot(conn, r["symbol"])[0] for r in openrows}
        enr = _enrich(conn, syms)
        # Hit-rate by strategy — split each position's comma-joined strategy
        # (D77 multi-select) and attribute it to EACH component, so a combo like
        # "DVPT accumulation, RS leader" lands in both rows. Single-strategy and
        # free-text values pass through unchanged; blanks fall back to "—".
        _sagg = {}
        for r in closed:
            ep, xp = r["entry_price"], r["exit_price"]
            if not ep:
                continue
            ret, win = (xp - ep) / ep * 100.0, (1.0 if xp > ep else 0.0)
            for k in (_split_strats(r["strategy"]) or ["—"]):
                a = _sagg.setdefault(k, {"n": 0, "wins": 0.0, "ret": 0.0})
                a["n"] += 1
                a["wins"] += win
                a["ret"] += ret
        bystrat = sorted(
            [{"k": k, "n": a["n"], "hit": a["wins"] / a["n"] * 100,
              "avg_ret": a["ret"] / a["n"]} for k, a in _sagg.items()],
            key=lambda x: x["n"], reverse=True)
        bybook = [dict(r) for r in conn.execute(
            "SELECT book k, COUNT(*) n, "
            "AVG(CASE WHEN exit_price>entry_price THEN 1.0 ELSE 0 END)*100 hit, "
            "AVG((exit_price-entry_price)/entry_price*100) avg_ret "
            "FROM stocks_in_play WHERE status='closed' AND entry_price>0 "
            "AND exit_price IS NOT NULL GROUP BY book ORDER BY n DESC").fetchall()]
        excess = []
        for r in closed:
            br = _benchmark_return(conn, "Nifty 500", r["date_added"], r["exit_date"])
            if br is not None:
                pr = (r["exit_price"] - r["entry_price"]) / r["entry_price"] * 100.0
                excess.append(pr - br)
        xirr = _portfolio_xirr(conn, openrows + closed, cmps)
        curve = _equity_curve(conn, openrows)

    # ---- per-position records (₹ needs qty; % always when priced) ----
    def rec(r, is_open):
        ep, q = r["entry_price"], r.get("qty")
        px = cmps.get(r["symbol"]) if is_open else r.get("exit_price")
        e = enr.get(r["symbol"], {})
        d_end = None if is_open else r.get("exit_date")
        return {"sym": r["symbol"], "book": r.get("book") or "Main", "strat": r["strategy"],
                "sector": _sector_short(e.get("sector")) or "—",
                "pl_pct": ((px - ep) / ep * 100.0) if (px and ep) else None,
                "pl_rs": (q * (px - ep)) if (q and px and ep) else None,
                "open": is_open, "days": _days_between(r["date_added"], d_end or today), "row": r}
    recs = [rec(r, True) for r in openrows] + [rec(r, False) for r in closed]
    ur = [x["pl_rs"] for x in recs if x["open"] and x["pl_rs"] is not None]
    rl = [x["pl_rs"] for x in recs if not x["open"] and x["pl_rs"] is not None]
    unreal = sum(ur) if ur else None
    real = sum(rl) if rl else None
    total_pl = ((unreal or 0.0) + (real or 0.0)) if (ur or rl) else None
    invested = sum((r.get("qty") or 0) * (r["entry_price"] or 0)
                   for r in openrows + closed if r.get("qty") and r["entry_price"]) or None
    abs_ret = (total_pl / invested * 100.0) if (total_pl is not None and invested) else None
    cagr = None
    edates = [(r["date_added"] or "")[:10] for r in openrows + closed if r.get("date_added")]
    if abs_ret is not None and invested and edates:
        yrs = _days_between(min(edates), today)
        yrs = (yrs / 365.0) if yrs else None
        if yrs and yrs > 0.08:
            cagr = (((invested + total_pl) / invested) ** (1 / yrs) - 1) * 100.0
    opl = [x["pl_pct"] for x in recs if x["open"] and x["pl_pct"] is not None]
    open_mtm = (sum(opl) / len(opl)) if opl else None
    overall_hit = (sum(1 for r in closed if r["exit_price"] > r["entry_price"]) / len(closed) * 100.0) if closed else None
    avg_excess = (sum(excess) / len(excess)) if excess else None
    cl_days = [x["days"] for x in recs if not x["open"] and x["days"] is not None]
    avg_hold = (sum(cl_days) / len(cl_days)) if cl_days else None
    dd, dd_p, dd_t = _max_drawdown(curve)

    def card(lbl, val):
        return f'<div class="box"><div class="num">{val}</div><div class="lbl">{lbl}</div></div>'

    def pctval(v, suffix="%"):
        return (f'{v:+.1f}{suffix}' if v is not None else '<span class="mut">—</span>')
    plcard = _rpl(total_pl) + (f' <span style="font-size:13px">{_pct(abs_ret)}</span>' if abs_ret is not None else '')
    cards = ('<div class="kpi">'
             + card("open", len(openrows))
             + card("closed", len(closed))
             + card("total ₹ P&amp;L", plcard)
             + card("realized", _rpl(real))
             + card("unrealized", _rpl(unreal))
             + card("XIRR", pctval(xirr * 100 if xirr is not None else None))
             + card("CAGR", pctval(cagr))
             + card("open MTM", _pct(open_mtm))
             + card("hit-rate", (f"{overall_hit:.0f}%" if overall_hit is not None else '<span class="mut">—</span>'))
             + card("avg excess vs N500", _pct(avg_excess))
             + card("avg hold", (f"{avg_hold:.0f}d" if avg_hold is not None else '<span class="mut">—</span>'))
             + card("max drawdown", (f'<span class="neg">{dd:.1f}%</span>' if dd is not None else '<span class="mut">—</span>'))
             + '</div>')

    # ---- equity curve vs Nifty 500 ----
    curve_html = ('<div class="ghdr" style="margin-top:18px">Equity curve vs Nifty 500 '
                  '<span class="mut" style="text-transform:none;font-weight:400">(both rebased to 100 at the first held day)</span></div>'
                  + _curve_svg(curve))
    if dd is not None and dd_p:
        curve_html += (f'<div class="sub" style="margin-top:6px">Max drawdown '
                       f'<span class="neg">{dd:.1f}%</span> · peak {dd_p} → trough {dd_t}</div>')

    # ---- hit-rate bars (by strategy + by book) ----
    def hr_bars(rows, title):
        if not rows:
            return ''
        out = [f'<div class="ghdr">{title}</div>']
        for s in rows:
            hit = s["hit"] or 0
            out.append(
                '<div class="trk-bar">'
                f'<span class="trk-lbl">{_esc(s["k"])} <i class="mut">n={s["n"]}</i></span>'
                f'<span class="bar" style="flex:1;height:16px"><span style="width:{hit:.0f}%;background:var(--up)"></span></span>'
                f'<span class="trk-val">{hit:.0f}%</span>'
                f'<span class="mut" style="width:74px;text-align:right;font-size:11px">{_pct(s["avg_ret"])}</span>'
                '</div>')
        return "".join(out)
    if bystrat or bybook:
        hits_html = ('<div style="margin-top:16px">' + hr_bars(bystrat, "Hit-rate by strategy")
                     + hr_bars(bybook, "Hit-rate by book") + '</div>')
    else:
        hits_html = ('<div class="sub" style="margin-top:14px">No closed positions yet — hit-rate, '
                     'attribution and the closed-trades log fill in once you close trades.</div>')

    # ---- return attribution (needs qty on positions) ----
    attrib = ''
    if any(x["pl_rs"] is not None for x in recs):
        attrib = ('<details open style="margin-top:18px"><summary class="ghdr" style="cursor:pointer">'
                  '▸ Return attribution (₹ P&amp;L contribution)</summary><div style="margin-top:8px">'
                  + _attrib_bars("By holding", [(x["sym"], x["pl_rs"]) for x in recs])
                  + _attrib_bars("By sector", [(x["sector"], x["pl_rs"]) for x in recs])
                  + _attrib_bars("By book", [(x["book"], x["pl_rs"]) for x in recs])
                  + _attrib_bars("By strategy", [(k, x["pl_rs"]) for x in recs
                                                 for k in (_split_strats(x["strat"]) or ["—"])])
                  + '</div></details>')
    elif openrows or closed:
        attrib = ('<div class="sub" style="margin-top:14px">Add <b>quantity</b> to your positions to '
                  'unlock ₹ return attribution and the equity curve.</div>')

    # ---- closed-trades log ----
    clog = ''
    if closed:
        trs = []
        for r in closed:
            ep, xp, q = r["entry_price"], r["exit_price"], r.get("qty")
            pl_pct = ((xp - ep) / ep * 100.0) if (ep and xp) else None
            pl_rs = (q * (xp - ep)) if (q and ep and xp) else None
            days = _days_between(r["date_added"], r["exit_date"])
            e = enr.get(r["symbol"], {})
            sec = _sector_short(e.get("sector"))
            sec_cell = _esc(sec) if sec else '<span class="mut">—</span>'
            q_cell = _num(q, 0) if q else '<span class="mut">—</span>'
            days_cell = f'{days}d' if days is not None else '—'
            trs.append(
                '<tr>'
                f'<td class="l"><a class="row" href="/dash/stock?sym={_q(r["symbol"])}"><span class="sym">{_esc(r["symbol"])}</span></a></td>'
                f'<td class="l">{sec_cell}</td>'
                f'<td class="l mut">{_esc(r.get("book") or "Main")}</td>'
                f'<td class="l mut">{_esc(r["strategy"])}</td>'
                f'<td class="mut">{_esc((r["date_added"] or "")[:10])}</td>'
                f'<td class="mut">{_esc((r["exit_date"] or "")[:10])}</td>'
                f'<td class="num">{days_cell}</td>'
                f'<td class="num">{_num(ep, 1)}</td>'
                f'<td class="num">{_num(xp, 1)}</td>'
                f'<td class="num">{q_cell}</td>'
                f'<td class="num">{_rpl(pl_rs)}</td>'
                f'<td class="num">{_pct(pl_pct)}</td>'
                f'<td class="l mut">{_esc(r.get("exit_reason") or "—")}</td>'
                f'<td class="l">{_id_form("/dash/track/reopen", r["id"], "Reopen", confirm="Reopen this trade (back to open positions)?")}</td>'
                '</tr>')
        clog = ('<div style="display:flex;justify-content:space-between;align-items:center;margin-top:18px">'
                '<div class="ghdr" style="margin:0">Closed-trades log</div>'
                '<a class="tbtn" href="/dash/track/export?status=closed" style="text-decoration:none">⬇ Export CSV</a></div>'
                # 14-col table > a 380px phone — scroll it INSIDE its own wrapper so the
                # PAGE doesn't horizontally scroll (mirrors the screener's .scrwrap pattern).
                '<div style="overflow-x:auto;-webkit-overflow-scrolling:touch">'
                '<table class="dt"><thead><tr><th>Symbol</th><th>Sector</th><th>Book</th><th>Strategy</th>'
                '<th>Entry date</th><th>Exit date</th><th>Days</th><th>Entry ₹</th><th>Exit ₹</th><th>Qty</th>'
                '<th>₹ P&amp;L</th><th>Return</th><th>Reason</th><th></th></tr></thead><tbody>'
                + "".join(trs) + '</tbody></table></div>')

    intro = ('<h2>Performance</h2><div class="sub"><b>Your scoreboard</b> — how your committed ideas '
             'actually performed: money-weighted <b>XIRR</b>, realized vs unrealized, the equity curve '
             'vs Nifty 500, return attribution, and the closed-trades log. <span class="mut">'
             'Auto-computed from your '
             '<a href="/dash/portfolios" style="color:#58a6ff;text-decoration:none">Portfolio</a> + '
             'closed trades — it fills itself as you take and close positions. EOD data; '
             '₹ metrics need quantity on the position.</span></div>')
    body = (_TRACK_CSS + _track_subnav("performance")
            + (f'<div class="banner b-off">{_esc(err)}</div>' if err else '')
            + ('<div class="banner b-on">&#10003; Position closed &#8212; logged to your scoreboard below.</div>'
               if just_closed == "1" else '')
            + intro + cards + curve_html
            + hits_html + attrib + clog)
    return HTMLResponse(_shell("Performance · patearn", body, "performance", wide=True))


@router.get("/dash/tracker")
def dash_tracker_redirect() -> RedirectResponse:
    # The Tracker umbrella lands on its Dashboard cockpit (the first tab).
    return RedirectResponse("/dash/tracker/dashboard", status_code=307)


# ── Tracker tab URLs live under /dash/tracker/* (D79) so the address mirrors the
# nav hierarchy (Tracker › Dashboard/Portfolios/Watchlists/Performance/Import).
# The old flat /dash/<tab> URLs stay alive as 307 redirects to the nested canonical
# path — query string preserved — so every existing link, bookmark and internal
# redirect keeps working (no page is rerouted away or orphaned).
def _tracker_compat(request: Request, tab: str) -> RedirectResponse:
    q = request.url.query
    return RedirectResponse(f"/dash/tracker/{tab}" + (f"?{q}" if q else ""),
                            status_code=307)


@router.get("/dash/dashboard")
def _compat_dashboard(request: Request) -> RedirectResponse:
    return _tracker_compat(request, "dashboard")


@router.get("/dash/portfolios")
def _compat_portfolios(request: Request) -> RedirectResponse:
    return _tracker_compat(request, "portfolios")


@router.get("/dash/watchlists")
def _compat_watchlists(request: Request) -> RedirectResponse:
    return _tracker_compat(request, "watchlists")


@router.get("/dash/performance")
def _compat_performance(request: Request) -> RedirectResponse:
    return _tracker_compat(request, "performance")


@router.get("/dash/import")
def _compat_import(request: Request) -> RedirectResponse:
    return _tracker_compat(request, "import")


@router.get("/dash/tracker/dashboard", response_class=HTMLResponse)
def dash_dashboard() -> HTMLResponse:
    """The Tracker cockpit: totals · needs-attention red flags · movers · allocation
    · contributors · news · upcoming corporate actions · every book at a glance."""
    with get_conn() as conn:
        openrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='open'").fetchall()]
        watchrows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status='watch'").fetchall()]
        osyms = {r["symbol"] for r in openrows}
        allsyms = osyms | {r["symbol"] for r in watchrows}
        live = {s: _capture_snapshot(conn, s) for s in osyms}
        cmps = {s: live[s][0] for s in osyms}
        dd = {s: _day_delta(conn, s) for s in osyms}
        enr = _enrich(conn, allsyms)
        xirr = _portfolio_xirr(conn, openrows, cmps)
        news = _holdings_news(conn, allsyms)
        upact = _upcoming_actions(conn, allsyms)
        # --- alerts firing + ready-to-act (Step 5) ---
        wcmps = {s: _capture_snapshot(conn, s)[0] for s in (allsyms - osyms)}
        f52c, fired, ready_now = {}, [], []
        for r in (openrows + watchrows):
            sym = r["symbol"]
            sig = (enr.get(sym) or {}).get("sig") or {}
            thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
            cmp_a = cmps.get(sym) if r["status"] == "open" else wcmps.get(sym)
            fr = _eval_alerts(r, sig, cmp_a, thn, lambda s: _fiftytwo(conn, s, f52c))
            if fr:
                fired.append((sym, r["status"], fr))
            if r["status"] == "watch":
                rdy = _ready_to_act(sig)
                if rdy:
                    ready_now.append((sym, rdy))

    def _pl(r):
        c, ep = cmps.get(r["symbol"]), r["entry_price"]
        return ((c - ep) / ep * 100.0) if (c and ep) else None
    opl = [x for x in (_pl(r) for r in openrows) if x is not None]
    open_mtm = (sum(opl) / len(opl)) if opl else None
    bk, hold_value, day_num, day_den = {}, {}, 0.0, 0.0
    for r in openrows:
        b = r.get("book") or "Main"
        d = bk.setdefault(b, {"open": 0, "watch": 0, "pl": [], "inv": 0.0, "cur": 0.0})
        d["open"] += 1
        p = _pl(r)
        if p is not None:
            d["pl"].append(p)
        q, ep, c = r.get("qty"), r["entry_price"], cmps.get(r["symbol"])
        if q and ep:
            d["inv"] += q * ep
            if c:
                d["cur"] += q * c
                hold_value[r["id"]] = q * c
                _, _dcp, pc = dd.get(r["symbol"], (None, None, None))
                if pc:
                    day_num += q * (c - pc)
                    day_den += q * pc
    for r in watchrows:
        bk.setdefault(r.get("book") or "Main",
                      {"open": 0, "watch": 0, "pl": [], "inv": 0.0, "cur": 0.0})["watch"] += 1
    book_val = {}
    for r in openrows:
        v = hold_value.get(r["id"])
        if v:
            book_val[r.get("book") or "Main"] = book_val.get(r.get("book") or "Main", 0.0) + v
    tot_inv = sum(d["inv"] for d in bk.values())
    tot_cur = sum(d["cur"] for d in bk.values())
    tot_rpl = (tot_cur - tot_inv) if tot_inv else None
    tot_plpct = (tot_rpl / tot_inv * 100.0) if tot_inv else None
    day_pct = (day_num / day_den * 100.0) if day_den else None

    def card(lbl, val):
        return f'<div class="box"><div class="num">{val}</div><div class="lbl">{lbl}</div></div>'
    pl_extra = f' <span style="font-size:13px">{_pct(tot_plpct)}</span>' if tot_plpct is not None else ''
    cards = ('<div class="kpi">'
             + card("books", len(bk))
             + card("open positions", len(openrows))
             + card("invested", _rupee(tot_inv) if tot_inv else '<span class="mut">—</span>')
             + card("value", _rupee(tot_cur) if tot_cur else '<span class="mut">—</span>')
             + card("₹ P&amp;L", _rpl(tot_rpl) + pl_extra)
             + card("day Δ", _pct(day_pct))
             + card("open MTM", _pct(open_mtm))
             + card("XIRR", (f'{xirr*100:+.1f}%' if xirr is not None else '<span class="mut">—</span>'))
             + card("watchlist ideas", len(watchrows))
             + '</div>')
    intro = ('<h2>Dashboard</h2><div class="sub"><b>Your cockpit</b> — totals, what needs attention '
             'right now, today\'s movers, where you\'re concentrated, news, and upcoming corporate '
             'actions. <span class="mut">EOD data; full scorecard under '
             '<a href="/dash/performance" style="color:#58a6ff;text-decoration:none">Performance</a>. '
             'Add quantity on a position to unlock ₹ figures.</span></div>')

    # ---- needs attention (Patearn red flags) ----
    sev = {"below_stop": 0, "dist": 1, "near_stop": 2, "rs_decay": 3, "rs_weak": 4, "conv_drop": 5, "conc": 6}
    att = []
    for r in openrows:
        sym = r["symbol"]
        cmp_ = cmps.get(sym)
        sig = (enr.get(sym) or {}).get("sig") or {}
        thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
        fl = set(_thesis_flags(thn, sig, cmp_, r["stop_loss"]))
        v, btot = hold_value.get(r["id"]), book_val.get(r.get("book") or "Main")
        conc_pct = (v / btot * 100.0) if (v and btot) else None
        if conc_pct is not None and conc_pct > 30 and len(book_val) and len([1 for rr in openrows if (rr.get("book") or "Main") == (r.get("book") or "Main")]) > 1:
            fl.add("conc")
        if fl:
            labels = [_HEALTH_FLAG_LABEL[k][0] for k in fl if k in _HEALTH_FLAG_LABEL]
            if "conc" in fl:
                labels.append(f"{conc_pct:.0f}% of {r.get('book') or 'Main'}")
            att.append((min(sev.get(k, 9) for k in fl), r, cmp_, labels))
    att.sort(key=lambda x: x[0])
    if att:
        trs = []
        for _s, r, cmp_, labels in att:
            sym = r["symbol"]
            stop_cell = _num(r["stop_loss"], 1) if r["stop_loss"] is not None else '<span class="mut">—</span>'
            trs.append(
                '<tr>'
                f'<td class="l"><a class="row" href="/dash/stock?sym={_q(sym)}"><span class="sym">{_esc(sym)}</span></a></td>'
                f'<td class="l mut">{_esc(r.get("book") or "Main")}</td>'
                f'<td class="num">{_num(cmp_, 1)}</td>'
                f'<td class="num">{stop_cell}</td>'
                f'<td class="l"><span class="neg">{_esc(", ".join(labels))}</span></td>'
                f'<td class="l"><a class="tbtn" href="/dash/track/edit?id={r["id"]}" style="text-decoration:none">Review</a></td>'
                '</tr>')
        attention = ('<div class="ghdr" style="margin-top:16px">⚠ Needs attention '
                     f'<span class="mut" style="text-transform:none;font-weight:400">({len(att)})</span></div>'
                     '<table class="dt"><thead><tr><th>Symbol</th><th>Book</th><th>CMP</th><th>Stop</th>'
                     '<th>Flags</th><th></th></tr></thead><tbody>' + "".join(trs) + '</tbody></table>')
    elif openrows:
        attention = ('<div class="ghdr" style="margin-top:16px">Needs attention</div>'
                     '<div class="banner b-on">✓ Nothing flagged — no DISTRIBUTION, RS decay, '
                     'stop breaches, or over-concentration across your open positions.</div>')
    else:
        attention = ''

    # ---- alerts firing + ready to act (Step 5) ----
    alerts_html = ''
    if ready_now:
        chips_r = "".join(
            f'<a class="chip" href="/dash/stock?sym={_q(s)}" style="text-decoration:none">'
            f'<b>{_esc(s)}</b> <span class="mut">{_esc(rdy)}</span></a>' for s, rdy in ready_now[:12])
        alerts_html += ('<div class="ghdr" style="margin-top:18px">⚡ Ready to act '
                        f'<span class="mut" style="text-transform:none;font-weight:400">({len(ready_now)})</span></div>'
                        '<div class="chips">' + chips_r + '</div>')
    if fired:
        items = []
        for sym, st, msgs in fired:
            tier = "watch" if st == "watch" else "position"
            items.append(
                '<div style="padding:6px 0;border-bottom:1px solid var(--bg-3)">'
                f'<a class="sym" href="/dash/stock?sym={_q(sym)}" style="color:#58a6ff;text-decoration:none">{_esc(sym)}</a> '
                f'<span class="mut" style="font-size:11px">({tier})</span> '
                + " ".join(f'<span class="snap" style="background:#3a3417;border-color:#5a4a1f;color:#ffd99a">🔔 {_esc(m)}</span>' for m in msgs)
                + '</div>')
        alerts_html += ('<div class="ghdr" style="margin-top:16px">🔔 Alerts firing '
                        f'<span class="mut" style="text-transform:none;font-weight:400">({len(fired)})</span></div>'
                        + "".join(items))

    # ---- today's movers (EOD) ----
    movers = ''
    mv = sorted([(s, dd[s][1]) for s in osyms if dd.get(s) and dd[s][1] is not None],
                key=lambda x: x[1], reverse=True)
    if mv:
        ups = [m for m in mv if m[1] > 0][:5]
        downs = [m for m in mv if m[1] < 0][-5:][::-1]

        def mv_chips(items):
            return "".join(
                f'<a class="chip" href="/dash/stock?sym={_q(s)}" style="text-decoration:none">'
                f'<b>{_esc(s)}</b> {_pct(v)}</a>' for s, v in items) or '<span class="mut">—</span>'
        movers = ('<div class="ghdr" style="margin-top:18px">Today\'s movers '
                  '<span class="mut" style="text-transform:none;font-weight:400">(EOD)</span></div>'
                  '<div style="display:flex;gap:24px;flex-wrap:wrap">'
                  '<div style="flex:1;min-width:240px"><div class="sub" style="margin:0 0 6px">Gainers</div>'
                  '<div class="chips">' + mv_chips(ups) + '</div></div>'
                  '<div style="flex:1;min-width:240px"><div class="sub" style="margin:0 0 6px">Losers</div>'
                  '<div class="chips">' + mv_chips(downs) + '</div></div></div>')

    # ---- allocation + concentration + contributors (need ₹ values) ----
    alloc = ''
    vlist = [(r, hold_value.get(r["id"])) for r in openrows if hold_value.get(r["id"])]
    if vlist:
        tot = sum(v for _r, v in vlist)
        sec_pairs, cap_pairs, book_pairs, contrib = [], [], [], []
        for r, v in vlist:
            e = enr.get(r["symbol"], {})
            sec_pairs.append((_sector_short(e.get("sector")) or "—", v))
            cap_pairs.append((e.get("tier") or "—", v))
            book_pairs.append((r.get("book") or "Main", v))
            ep = r["entry_price"]
            c = cmps.get(r["symbol"])
            if r.get("qty") and ep and c:
                contrib.append((r["symbol"], r["qty"] * (c - ep)))
        conc = _concentration([v for _r, v in vlist])
        conc_html = ('<div class="ghdr">Concentration</div><div class="chips">'
                     + "".join(f'<span class="chip">{lbl} · <b>{pc:.0f}%</b></span>'
                               for lbl, pc in conc) + '</div>') if conc else ''
        contrib_html = (_attrib_bars("Top contributors / detractors (₹)", contrib, top_n=6)
                        + '<div class="sub" style="margin-top:4px">Full attribution under '
                        '<a href="/dash/performance" style="color:#58a6ff;text-decoration:none">Performance</a>.</div>'
                        if contrib else '')
        alloc = ('<details open style="margin-top:18px"><summary class="ghdr" style="cursor:pointer">'
                 '▸ Allocation, concentration &amp; contributors</summary><div style="margin-top:8px">'
                 + _alloc_bars("By sector", sec_pairs, tot)
                 + _alloc_bars("By book", book_pairs, tot)
                 + _alloc_bars("By market-cap", cap_pairs, tot)
                 + conc_html + contrib_html + '</div></details>')

    # ---- news for held + watched ----
    news_html = ''
    if news:
        items = []
        for sym, n in news:
            items.append(
                '<div style="padding:7px 0;border-bottom:1px solid var(--bg-3)">'
                f'<a class="sym" href="/dash/stock?sym={_q(sym)}" style="color:#58a6ff;text-decoration:none">{_esc(sym)}</a> '
                f'<a href="{_esc(n["url"])}" target="_blank" rel="noopener" style="color:var(--ink);text-decoration:none">{_esc(n["title"])}</a> '
                f'<span class="mut" style="font-size:11px">· {_esc(n["source"])} · {_esc((n["sent_at"] or "")[:10])}</span></div>')
        news_html = ('<details style="margin-top:18px"><summary class="ghdr" style="cursor:pointer">'
                     f'▸ News for your names <span class="mut" style="text-transform:none;font-weight:400">({len(news)})</span></summary>'
                     '<div style="margin-top:6px">' + "".join(items) + '</div></details>')

    # ---- upcoming corporate actions ----
    corp_html = ''
    if upact:
        items = []
        for a in upact:
            items.append(
                '<div style="padding:6px 0;border-bottom:1px solid var(--bg-3)">'
                f'<span class="sym">{_esc(a["symbol"])}</span> '
                f'<span class="mut">{_esc(a["action_type"])}</span> · ex {_esc(a["ex_date"])} '
                f'<span class="mut" style="font-size:11px">{_esc(a.get("details") or "")}</span></div>')
        corp_html = ('<div class="ghdr" style="margin-top:18px">Upcoming corporate actions</div>'
                     + "".join(items))

    # ---- books table ----
    if bk:
        trs = []
        for b, d in sorted(bk.items()):
            avg = (sum(d["pl"]) / len(d["pl"])) if d["pl"] else None
            rpl = (d["cur"] - d["inv"]) if d["inv"] else None
            inv_cell = _rupee(d["inv"]) if d["inv"] else '<span class="mut">—</span>'
            trs.append(
                '<tr>'
                f'<td class="l"><a class="row" href="/dash/portfolios?book={_q(b)}"><span class="sym">{_esc(b)}</span></a></td>'
                f'<td class="num">{d["open"]}</td>'
                f'<td class="num">{_pct(avg)}</td>'
                f'<td class="num">{inv_cell}</td>'
                f'<td class="num">{_rpl(rpl)}</td>'
                f'<td class="num">{d["watch"]}</td>'
                f'<td class="l"><a class="tbtn" href="/dash/portfolios?book={_q(b)}" style="text-decoration:none">Open</a></td>'
                '</tr>')
        table = ('<div class="ghdr" style="margin-top:18px">Books</div>'
                 '<table class="dt"><thead><tr><th>Book</th><th>Open</th><th>Avg P/L</th>'
                 '<th>Invested</th><th>₹ P&amp;L</th><th>Watch</th><th></th></tr></thead><tbody>'
                 + "".join(trs) + "</tbody></table>")
    else:
        table = ('<div class="empty">No books yet. Add a position in '
                 '<a href="/dash/portfolios" style="color:#58a6ff;text-decoration:none">Portfolios</a> '
                 'or an idea in '
                 '<a href="/dash/watchlists" style="color:#58a6ff;text-decoration:none">Watchlists</a>.</div>')
    body = (_TRACK_CSS + _track_subnav("dashboard") + intro + cards + attention + alerts_html
            + movers + alloc + news_html + corp_html + table)
    return HTMLResponse(_shell("Dashboard · patearn", body, "dashboard", wide=True))


# === Smart CSV / Excel importer ============================================
# Upload ANY layout -> auto-detect columns (value-based symbol match against the
# NSE universe + header synonyms + value fallbacks) -> confirm on a review
# screen -> import into a named book. Import TRUSTS the file's cost basis (an
# averaged buy price legitimately won't sit inside one day's OHLC), so unlike
# manual entry it does NOT reject out-of-range prices.

# Field order matters: _detect_mapping iterates these and the first field to find a
# column claims it. `strategy` is checked BEFORE `entry_price` on purpose — the
# substring "rate" lives inside "st-RATE-gy", so otherwise entry_price would steal
# a "Strategy" column that precedes the real price column.
_IMP_SYN = {
    "symbol": ("symbol", "ticker", "scrip", "scripname", "stock", "instrument",
               "nsecode", "tradingsymbol", "security", "company", "name"),
    "strategy": ("strategy", "remarks", "remark", "notes", "note", "basis",
                 "tag", "category", "thesis"),
    "qty": ("qty", "quantity", "shares", "units", "holdingqty", "nos", "noofshares"),
    "entry_price": ("avgprice", "avgcost", "averagecost", "buyprice", "buyrate",
                    "purchaseprice", "price", "rate", "cost", "nav", "avg"),
    "entry_date": ("buydate", "purchasedate", "entrydate", "tradedate",
                   "transactiondate", "dateofpurchase", "date"),
}
_IMP_FIELDS = [("symbol", "Symbol *"), ("entry_date", "Entry date"),
               ("entry_price", "Entry price"), ("qty", "Qty"), ("strategy", "Strategy / note")]


def _imp_norm(h):
    return re.sub(r"[^a-z0-9]", "", str(h or "").lower())


def _imp_date(s):
    s = (s or "").strip().split(" ")[0].split("T")[0]
    if not s:
        return None
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y",
              "%d-%b-%y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, f).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _imp_num(s):
    try:
        return float(str(s).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


# Hard cap on the import upload — generous for any real holdings sheet (500 rows is
# tiny), tight enough that a zip-bomb .xlsx can't OOM the single VPS before parse.
_MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def _parse_upload(filename, data):
    """(headers, rows) from CSV or XLSX bytes; rows = list[list[str]], header = row 0."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        allr = [list(r) for r in wb.active.iter_rows(values_only=True)]
    else:
        text = data.decode("utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except Exception:
            dialect = csv.excel
        allr = list(csv.reader(io.StringIO(text), dialect))
    norm = []
    for r in allr:
        cells = ["" if c is None else str(c).strip() for c in r]
        if any(cells):
            norm.append(cells)
    if not norm:
        return [], []
    return norm[0], norm[1:]


def _detect_mapping(headers, rows, eqset, eqnames):
    """Best-guess {field: col_index}. Symbol is found by VALUE (which column's
    values match the NSE universe) so it's robust to any header name."""
    nh = [_imp_norm(h) for h in headers]
    mp = {}
    sample = rows[:60]
    best, best_hits = None, 0
    for ci in range(len(headers)):
        hits = sum(1 for r in sample
                   if ci < len(r) and r[ci] and (r[ci].upper() in eqset or r[ci].upper() in eqnames))
        if hits > best_hits:
            best_hits, best = hits, ci
    if best is not None and best_hits >= max(1, len(sample) // 5):
        mp["symbol"] = best
    for field, syns in _IMP_SYN.items():
        if field in mp:
            continue
        for ci, h in enumerate(nh):
            if h and any(s in h for s in syns) and ci not in mp.values():
                mp[field] = ci
                break
    if "entry_date" not in mp:                       # value fallback: a date-like column
        for ci in range(len(headers)):
            if ci in mp.values():
                continue
            if sum(1 for r in sample if ci < len(r) and _imp_date(r[ci])) >= max(1, len(sample) // 2):
                mp["entry_date"] = ci
                break
    return mp


def _imp_review(headers, rows, mp, status, book):
    def colopts(sel):
        return "".join(
            f'<option value="{i}"{" selected" if sel == i else ""}>{_esc(h or ("Col " + str(i + 1)))}</option>'
            for i, h in enumerate(headers))
    selects = "".join(
        f'<div style="flex:1;min-width:150px"><label>{lbl}</label>'
        f'<select name="map_{fld}" class="field"><option value="-1"{" selected" if mp.get(fld, -1) == -1 else ""}>'
        f'— none —</option>{colopts(mp.get(fld, -1))}</select></div>'
        for fld, lbl in _IMP_FIELDS)
    thead = "".join(f'<th>{_esc(h or ("Col " + str(i + 1)))}</th>' for i, h in enumerate(headers))
    prev = "".join(
        "<tr>" + "".join(f'<td class="l mut">{_esc(r[i]) if i < len(r) else ""}</td>'
                         for i in range(len(headers))) + "</tr>"
        for r in rows[:8])
    return (
        '<form class="cap" method="post" action="/dash/import/commit">'
        f'<textarea name="rows_json" style="display:none">{_esc(json.dumps(rows))}</textarea>'
        f'<input type="hidden" name="status" value="{_esc(status)}"/>'
        f'<input type="hidden" name="book" value="{_esc(book)}"/>'
        '<div style="font-weight:600;margin-bottom:6px">Confirm the column mapping</div>'
        f'<div class="sub" style="margin-bottom:10px">Importing <b>{len(rows)}</b> rows into '
        f'<b>{_esc(book)}</b> ({"Portfolio" if status == "open" else "Watchlist"}). We guessed the '
        'columns below from your file — fix any that are wrong. Unrecognised tickers are skipped.</div>'
        f'<div class="row2">{selects}</div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Import</button>'
        '<a class="tbtn" href="/dash/import" style="text-decoration:none;margin-left:8px">Cancel</a>'
        '</form>'
        '<div class="ghdr" style="margin-top:14px">Preview (first 8 rows)</div>'
        f'<table class="dt"><thead><tr>{thead}</tr></thead><tbody>{prev}</tbody></table>')


@router.get("/dash/tracker/import", response_class=HTMLResponse)
def dash_import() -> HTMLResponse:
    form = (
        '<form class="cap" method="post" action="/dash/import/preview" enctype="multipart/form-data">'
        '<div style="font-weight:600;margin-bottom:8px">Import holdings from a file</div>'
        '<div class="sub" style="margin-bottom:10px">CSV or Excel (.xlsx), <b>any layout</b> — we '
        'auto-detect the columns (the ticker column is found by matching your values to the NSE list) '
        'and let you confirm before saving. We read <b>Symbol · Entry date · Entry price · Qty · '
        'Strategy/note</b>. New to it? '
        '<a href="/dash/import/template.csv" style="color:#58a6ff;text-decoration:none">⬇ Download a template</a>, '
        'fill it in, and upload it back.</div>'
        '<div class="row2">'
        '<div style="flex:1;min-width:120px"><label>List</label>'
        '<select name="status" class="field"><option value="open">Portfolio</option>'
        '<option value="watch">Watchlist</option></select></div>'
        '<div style="flex:1;min-width:120px"><label>Book</label>'
        '<input name="book" class="field" value="Main" maxlength="40"/></div></div>'
        '<div style="margin-bottom:10px"><label>File</label>'
        '<input type="file" name="file" class="field" accept=".csv,.xlsx,.xlsm,text/csv" required/></div>'
        '<button class="tbtn tbtn-go" type="submit" style="padding:9px 18px">Upload &amp; preview</button>'
        '<a class="tbtn" href="/dash/portfolios" style="text-decoration:none;margin-left:8px">Cancel</a>'
        '</form>')
    body = _TRACK_CSS + _track_subnav("import") + '<h2>Import</h2>' + form
    return HTMLResponse(_shell("Import · patearn", body, "portfolios"))


def _csvnum(v, d=2):
    """Plain CSV number (rounded, trailing zeros dropped); '' for None."""
    return "" if v is None else f"{round(v, d):g}"


@router.get("/dash/import/template.csv")
def dash_import_template() -> Response:
    """A ready-to-fill CSV in exactly the layout the importer reads, with two
    example rows. Download → fill → upload back via /dash/import."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Symbol", "Entry Date", "Entry Price", "Qty", "Strategy"])
    w.writerow(["RELIANCE", "2026-01-15", "1320.50", "25", "Quality"])
    w.writerow(["BANDHANBNK", "2026-02-03", "190", "100", "RS leader"])
    return Response(content=out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="patearn-import-template.csv"'})


@router.get("/dash/track/export")
def dash_track_export(status: str = Query("open"), book: str = Query("")) -> Response:
    """Download the current Portfolio / Watchlist as a clean CSV (respects the
    ?book= filter). Importer-friendly leading columns so it round-trips back in."""
    status = status if status in ("open", "watch", "closed") else "open"
    sel = book.strip()
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM stocks_in_play WHERE status=? ORDER BY book, date_added DESC",
            (status,)).fetchall()]
        if sel:
            rows = [r for r in rows if (r.get("book") or "Main") == sel]
        cmps = {s: _capture_snapshot(conn, s)[0] for s in {r["symbol"] for r in rows}}
    out = io.StringIO()
    w = csv.writer(out)
    if status == "watch":
        # Importer-friendly leading columns (Symbol · date · Strategy) so a re-upload
        # auto-detects; analytics columns trail.
        w.writerow(["Symbol", "Added Date", "Strategy", "Book", "Price When Added",
                    "CMP", "Change % Since Added", "Target", "Stop", "Thesis"])
        for r in rows:
            thn = _load_json_field(r["snapshot_json"], "snapshot_json", {})  # CL-DASH-15
            then, cmp_ = thn.get("close"), cmps.get(r["symbol"])
            chg = ((cmp_ - then) / then * 100.0) if (cmp_ and then) else None
            w.writerow([r["symbol"], (r["date_added"] or "")[:10], r["strategy"], r.get("book") or "Main",
                        _csvnum(then), _csvnum(cmp_), _csvnum(chg, 1),
                        _csvnum(r["price_target"]), _csvnum(r["stop_loss"]), r["entry_thesis"] or ""])
    else:
        # Leading columns mirror the import template (Symbol · Entry Date · Entry
        # Price · Qty · Strategy) so an exported file re-imports cleanly.
        w.writerow(["Symbol", "Entry Date", "Entry Price", "Qty", "Strategy", "Book", "CMP",
                    "P/L %", "Invested", "Target", "Stop", "Days Held", "Thesis"]
                   + (["Exit Date", "Exit Price", "Exit Reason"] if status == "closed" else []))
        for r in rows:
            ep, q = r["entry_price"], r.get("qty")
            cmp_ = (r.get("exit_price") if status == "closed" else cmps.get(r["symbol"]))
            pl = ((cmp_ - ep) / ep * 100.0) if (cmp_ and ep) else None
            inv = (q * ep) if (q and ep) else None
            end = (r.get("exit_date") or today) if status == "closed" else today
            days = _days_between(r["date_added"], end)
            base = [r["symbol"], (r["date_added"] or "")[:10], _csvnum(ep), _csvnum(q, 0), r["strategy"],
                    r.get("book") or "Main", _csvnum(cmp_), _csvnum(pl, 1), _csvnum(inv, 0),
                    _csvnum(r["price_target"]), _csvnum(r["stop_loss"]),
                    (str(days) if days is not None else ""), r["entry_thesis"] or ""]
            if status == "closed":
                base += [(r.get("exit_date") or "")[:10], _csvnum(r.get("exit_price")), r.get("exit_reason") or ""]
            w.writerow(base)
    tag = re.sub(r"[^A-Za-z0-9]+", "-", sel).strip("-") if sel else "all"
    fname = f"patearn-{status}-{tag}-{today}.csv"
    return Response(content=out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


def _imp_err(msg):
    body = (_TRACK_CSS + _track_subnav("import") + '<h2>Import</h2>'
            + f'<div class="banner b-off">{_esc(msg)}</div>'
            + '<div class="empty"><a href="/dash/import" style="color:#58a6ff;text-decoration:none">← Try again</a></div>')
    return HTMLResponse(_shell("Import · patearn", body, "portfolios"))


@router.post("/dash/import/preview", response_class=HTMLResponse)
async def dash_import_preview(file: UploadFile = File(...), status: str = Form("open"),
                             book: str = Form("Main")) -> HTMLResponse:
    status = status if status in ("watch", "open") else "open"
    bk = (book or "Main").strip()[:40] or "Main"
    # Cap the upload BEFORE buffering/parsing: a tiny zip-bomb .xlsx can decompress
    # to gigabytes and OOM the single VPS inside openpyxl. Read one byte past the cap
    # so we can detect over-size without ever holding the whole oversized payload.
    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        return _imp_err(f"That file is too large (limit {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB). "
                        "A holdings sheet should be well under that — check it's the right file.")
    try:
        headers, rows = _parse_upload(file.filename, data)
    except Exception as e:
        return _imp_err(f"Could not read that file: {str(e)[:160]}")
    rows = rows[:500]
    if not headers or not rows:
        return _imp_err("No data rows found in the file.")
    with get_conn() as conn:
        eqset = {r[0] for r in conn.execute("SELECT symbol FROM nse_equity_list").fetchall()}
        eqnames = {(r[0] or "").upper() for r in conn.execute(
            "SELECT company_name FROM nse_equity_list").fetchall()}
    mp = _detect_mapping(headers, rows, eqset, eqnames)
    body = _TRACK_CSS + _track_subnav("import") + '<h2>Import — review</h2>' + _imp_review(headers, rows, mp, status, bk)
    return HTMLResponse(_shell("Import · patearn", body, "portfolios"))


@router.post("/dash/import/commit")
def dash_import_commit(rows_json: str = Form("[]"), status: str = Form("open"),
                       book: str = Form("Main"), map_symbol: str = Form("-1"),
                       map_entry_date: str = Form("-1"), map_entry_price: str = Form("-1"),
                       map_qty: str = Form("-1"), map_strategy: str = Form("-1")) -> RedirectResponse:
    status = status if status in ("watch", "open") else "open"
    dest = "/dash/watchlists" if status == "watch" else "/dash/portfolios"
    bk = (book or "Main").strip()[:40] or "Main"
    try:
        rows = json.loads(rows_json or "[]")
    except Exception:
        rows = []

    def _i(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return -1
    cs, cd, cp, cq, cstr = (_i(map_symbol), _i(map_entry_date), _i(map_entry_price),
                            _i(map_qty), _i(map_strategy))
    if cs < 0:
        return RedirectResponse(f"{dest}?err={_q('Pick the Symbol column before importing.')}", status_code=303)

    def cell(r, ci):
        return str(r[ci]).strip() if (0 <= ci < len(r) and r[ci] is not None) else ""
    inserted, skipped, bad_dates = 0, [], []
    with get_conn() as conn:
        for r in rows:
            if not isinstance(r, list):
                continue
            sym = cell(r, cs).upper()
            if not sym:
                continue
            if not _is_listed(conn, sym):
                skipped.append(sym)
                continue
            strat = ((cell(r, cstr) if cstr >= 0 else "") or "Imported")[:60]
            q = _imp_num(cell(r, cq)) if cq >= 0 else None
            if status == "open":
                # Entry date drives P/L-since + XIRR — NEVER fabricate it. If the user
                # mapped a date column but the row's value won't parse, SKIP + surface
                # the row rather than silently stamping today (or the latest bhav date).
                date_cell = cell(r, cd) if cd >= 0 else ""
                d_in = _imp_date(date_cell) if date_cell else None
                if date_cell and d_in is None:
                    bad_dates.append(sym)
                    continue
                o = _ohlc_on(conn, sym, d_in or None)
                # Import TRUSTS the file's cost basis (averaged price may sit outside
                # one day's OHLC); fall back to that day's close only if price absent.
                ep_in = _imp_num(cell(r, cp)) if cp >= 0 else None
                ep = ep_in if ep_in is not None else (o["close"] if o else None)
                # Date precedence: the parsed user date (real, even if no bhav row on
                # it) → else the matched bhav trade_date. Only when NO date was given
                # at all and there's no bhav row do we fall back to today (a watch-like
                # "as of now" add, not a fabricated historical entry).
                td = (d_in or (o["trade_date"] if o else None)
                      or datetime.utcnow().strftime("%Y-%m-%d"))
                snap = _capture_snapshot(conn, sym, as_of=td)[1]
                conn.execute(
                    "INSERT INTO stocks_in_play(symbol,strategy,book,status,date_added,entry_price,qty,"
                    "price_target,stop_loss,entry_thesis,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (sym, strat, bk, "open", td, ep, q, None, None, None,
                     json.dumps(snap) if snap else None))
            else:
                snap = _capture_snapshot(conn, sym)[1]
                conn.execute(
                    "INSERT INTO stocks_in_play(symbol,strategy,book,status,entry_price,qty,"
                    "price_target,stop_loss,entry_thesis,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (sym, strat, bk, "watch", None, q, None, None, None,
                     json.dumps(snap) if snap else None))
            inserted += 1
    url = f"{dest}?book={_q(bk)}&added={_q(str(inserted) + ' holdings')}"
    errs = []
    if skipped:
        uniq = list(dict.fromkeys(skipped))
        errs.append(f"{len(skipped)} row(s) skipped — ticker not recognised: {', '.join(uniq[:8])}")
    if bad_dates:
        uniqd = list(dict.fromkeys(bad_dates))
        errs.append(f"{len(bad_dates)} row(s) skipped — entry date unreadable (not imported, to keep P/L correct): {', '.join(uniqd[:8])}")
    if errs:
        url += f"&err={_q(' · '.join(errs))}"
    return RedirectResponse(url, status_code=303)


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
// W2: lazy boot — the RS overlay lives in a hidden tab, so initialising it at
// load would size to a 0-width container. The Relative-Strength tab calls this
// on FIRST open (container visible → correct sizing); guarded against re-boot.
window.__bootRS = function(){
  const host = document.getElementById('rsOverlayChart');
  if (!host) return;
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:var(--ink-2);padding:20px">Chart library failed to load (offline?).</div>'; return; }
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
      +it.color+';text-shadow:0 0 3px var(--bg-1),0 0 2px var(--bg-1)">'+_e(it.name)+'</span>').join('');
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
};
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
    # CL-DASH-19: cap the compare-overlay list at the source. A hand-crafted URL can repeat
    # ?cmp= arbitrarily; the downstream loop already stops at _COMPARE_MAX, but the raw list
    # is materialised first. Slice generously (well above _COMPARE_MAX) so legitimate use is
    # untouched while an abusive payload can't balloon memory.
    if cmp:
        cmp = cmp[:64]
    _wolfe_btn = (
        f'<a href="/dash/wolfe?sym={_q(sym)}" style="display:inline-block;margin:8px 0 0;padding:6px 12px;'
        f'background:var(--bg-3);border:1px solid var(--line-2);border-radius:6px;color:var(--ink);'
        f'text-decoration:none;font-size:13px">⌁ Wolfe wave</a>' if sym else '')
    search = f"""
<form class="search" action="/dash/stock" method="get">
  <input name="sym" placeholder="Enter NSE ticker — e.g. BANDHANBNK" value="{_esc(sym)}" autocapitalize="characters" autocomplete="off"/>
  <button type="submit">Go</button>
</form>{_wolfe_btn}
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
        # FULL daily history (candles + DVPT + delivery), oldest-first after the
        # reverse below. No row cap — "Max" must mean max: the bhav archive runs
        # back to 2004 and even the deepest name (RELIANCE, ~5.4k rows) is served
        # instantly by idx_bhav_sym_date. The old LIMIT 1300 silently truncated
        # every chart to ~5 years, anchoring "Max" at ~2021. The client-side
        # range buttons (3M/6M/1Y/2Y/Max) still slice this for the default view.
        rows = conn.execute(
            """SELECT b.trade_date, b.open, b.high, b.low, b.close, b.prev_close,
                      b.deliv_per, b.value, b.deliv_qty,
                      s.delivery_value_per_trade dvpt, s.ratio_today_vs_power_1m r1m
               FROM bhavcopy_rows b
               LEFT JOIN stock_signals s USING (symbol, trade_date)
               WHERE b.symbol=? AND b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL)
               ORDER BY b.trade_date DESC""",
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
        try:  # capital-allocation (C) — descriptive dossier fact, latest per symbol (S77b consumption)
            ca = conn.execute(
                "SELECT ca_score, ca_tier FROM capital_allocation_scores WHERE symbol=? "
                "ORDER BY as_of DESC LIMIT 1", (sym,)).fetchone()
        except Exception:
            ca = None
        try:
            cpr_by_tf = _cpr_latest_by_tf(conn, [sym]).get(sym, {})   # CPR Structure panel (D53)
        except Exception:
            cpr_by_tf = {}
        try:
            cci_row = _cci_latest_by_sym(conn, [sym]).get(sym, {})    # CCI verdict tile + dossier (W3)
        except Exception:
            cci_row = {}
        # Full company name for the chart titles (so each chart self-identifies
        # the scrip without scrolling back to the page header).
        try:
            _cn = conn.execute(
                "SELECT company_name FROM nse_equity_list WHERE symbol=?", (sym,)).fetchone()
            company_name = (_cn["company_name"] if _cn else "") or ""
        except Exception:
            company_name = ""

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
            "dvpt": _safe_int(r["dvpt"]),
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
    # CL-DASH-13: the window is TIED to the longest zone lookback (P12M / R12M = 12 months
    # ≈ 252 trading sessions, + ~12 sessions slack) instead of a bare magic 264, so if the
    # zone horizon ever changes this single constant moves with it.
    _ZONE_LOOKBACK_SESSIONS = 252 + 12   # longest zone (12m) + a small calendar-drift buffer
    zone_action_recent = (any(f != 1.0 for f in factors[-_ZONE_LOOKBACK_SESSIONS:])
                          if n else False)

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
        col = "#f0883e" if mult >= 1.5 else ("#3fb950" if mult >= 1 else "var(--ink-2)")
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
                   f'margin:2px 0 4px;background:var(--bg-3)">'
                   f'<span style="width:{up_pct:.0f}%;background:var(--up)"></span>'
                   f'<span style="width:{100 - up_pct:.0f}%;background:var(--down)"></span></div>'
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
            warn = ('<div class="card" style="border-color:rgba(var(--down-rgb),.35);background:rgba(var(--down-rgb),.08);margin-top:8px">'
                    '<div class="sub" style="margin:0;color:var(--down)">⚠️ Heavy delivery, but on '
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
        ca_sc = _num(ca["ca_score"], 0) if (ca and ca["ca_score"] is not None) else "—"
        ca_ti = _esc(ca["ca_tier"]) if (ca and ca["ca_tier"]) else "—"
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
<tr><td class="mut">Cap-alloc (C)*</td><td>{ca_sc}</td>
    <td class="mut">C-tier</td><td>{ca_ti}</td></tr>
</tbody>
</table>
<div class="sub" style="font-size:11px;margin-top:2px">*Capital-allocation (C): ROIIC / ROCE level+trend / dilution / debt-funding composite (0-100) + cross-sectional tier. Descriptive; derived from Screener.in fundamentals, migrating to BSE/NSE XBRL (primary-source policy).</div>
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
            L.get("rs_vs_broad_slope_18m"), L.get("rs_vs_broad_slope_24m"),
        )
        if rs_rank is not None:
            rank_html = (
                f'<div class="card" style="display:flex;align-items:center;gap:12px;margin-top:8px">'
                f'<div style="font-size:28px;font-weight:700;line-height:1;white-space:nowrap">{rs_rank}'
                f'<span class="sub" style="margin:0;font-size:14px">/99</span></div>'
                f'<div style="flex:1;min-width:0">'
                f'<div class="bar" style="margin:0 0 4px"><span style="width:{rs_rank}%"></span></div>'
                f'<div class="sub" style="margin:0;font-size:11px;line-height:1.3">RS rank — stronger than '
                f'{rs_rank}% of the market (0.6·3m + 0.4·6m RS slope vs Nifty 500)</div></div></div>')
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
                L.get("rs_vs_sector_slope_18m"), L.get("rs_vs_sector_slope_24m"),
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
            _anchor = series[-1]["time"]
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
                # 18m/24m benchmark returns aren't pre-computed (index_signals stops
                # at ret_12m) — derive them on-read so the reconcile stays honest.
                n5["r18"] = _idx_ret(conn, "Nifty 500", _anchor, 545)
                n5["r24"] = _idx_ret(conn, "Nifty 500", _anchor, 730)
                if has_sector and sec_name:
                    sec["r18"] = _idx_ret(conn, sec_name, _anchor, 545)
                    sec["r24"] = _idx_ret(conn, sec_name, _anchor, 730)

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
                    ("12m", 365, "r12", "rs_vs_broad_slope_12m", "rs_vs_sector_slope_12m"),
                    ("18m", 545, "r18", "rs_vs_broad_slope_18m", "rs_vs_sector_slope_18m"),
                    ("24m", 730, "r24", "rs_vs_broad_slope_24m", "rs_vs_sector_slope_24m")):
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
    # RS momentum pane (RSI-of-RS + divergence) docked under the RS overlay — additive,
    # isolated (src/web/momentum_pane.py); self-fetches its own conn + degrades to an
    # empty-state, so it can never break this page.
    momentum_html = ""
    try:
        from src.web import momentum_pane as _mompane
        momentum_html = _mompane.card_html(sym)
    except Exception:  # noqa: BLE001
        momentum_html = ""
    # AUD-41/77: descriptive sector-state context on the dossier — the stock's OWN RS phase +
    # its sector's RS phase (index_signals, identity join on primary_sector), with links into
    # the sector's index surfaces. Phase is a LABEL only (descriptive, never a gate/ranker —
    # C10). Fail-safe to '' so it can never break this sacred page.
    sector_ctx_html = ""
    try:
        from urllib.parse import quote_plus as _qp
        _secn = L.get("primary_sector")
        with get_conn() as _cx:
            _sp = _cx.execute("SELECT rs_phase FROM stock_signals WHERE symbol=? AND rs_phase IS NOT NULL "
                              "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
            _stock_phase = _sp[0] if _sp else None
            _sec_phase = None
            if _secn:
                _ip = _cx.execute("SELECT rs_phase FROM index_signals WHERE index_name=? COLLATE NOCASE "
                                  "AND rs_phase IS NOT NULL ORDER BY trade_date DESC LIMIT 1",
                                  (_secn,)).fetchone()
                _sec_phase = _ip[0] if _ip else None
        if _stock_phase or _sec_phase:
            _bits = []
            if _stock_phase:
                _bits.append(f'{_esc(sym)}: <span class="pill">{_esc(_stock_phase)}</span>')
            if _secn:
                _enc = _qp(_secn)
                _seclink = (f'<a href="/dash/rrg?idx={_enc}">{_esc(_secn)}</a> '
                            f'<span class="mut">(<a href="/dash/sector-momentum">momentum</a>)</span>')
                _bits.append(f'sector {_seclink}: <span class="pill">{_esc(_sec_phase)}</span>'
                             if _sec_phase else f'sector {_seclink}')
            sector_ctx_html = ('<div class="card" style="margin:8px 0"><div class="sub" style="margin:0">'
                               '<b>Sector context</b> — ' + ' &nbsp;·&nbsp; '.join(_bits) + '</div></div>')
    except Exception:  # noqa: BLE001
        sector_ctx_html = ""
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
.rangebar button { background:var(--bg-3); color:var(--ink); border:1px solid var(--line-2);
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:var(--bg-2); border:1px solid var(--line-2); border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:var(--ink-2); font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
.cmp-anchor { font-size:12px; color:var(--ink-2); margin:6px 4px 2px; }
.cmp-vals { display:flex; gap:14px; flex-wrap:wrap; font-size:12px; font-variant-numeric:tabular-nums; padding:8px 4px 2px; }
.cmp-val { font-weight:600; }
.cmp-rail { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin:6px 0 8px; }
.cmp-chip { display:inline-flex; align-items:center; gap:6px; background:var(--bg-2); border:1px solid var(--line-2); border-radius:14px; padding:5px 8px 5px 9px; font-size:13px; }
.cmp-chip.cmp-dim { opacity:.4; }
.cmp-sw { width:10px; height:10px; border-radius:50%; display:inline-block; }
.cmp-tag { font-size:9px; font-weight:700; color:var(--ink-2); background:var(--bg-3); border-radius:4px; padding:1px 4px; letter-spacing:.4px; }
.cmp-x { color:var(--ink-2); text-decoration:none; font-size:12px; margin-left:1px; }
.cmp-x:hover { color:#f85149; }
button.cmp-sugg { cursor:pointer; font-family:inherit; }
.cmp-sugg.cmp-on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
"""

    cpr_html = _cpr_stock_panel(cpr_by_tf)   # CPR Structure panel (D53)
    cci_html = _cci_stock_panel(sym)         # Management Credibility dossier (CCI, P5)
    # Flagship A (premium visuals): the promise-vs-delivery FINGERPRINT rides the CCI
    # tab (Session-68 plan) with a link out to the full /dash/credibility page — the
    # movement view of the same settled promises the ledger below lists. Defensive:
    # a fingerprint failure must never break the dossier; empty-state is graceful.
    try:
        from src.web import credibility_fingerprint as _credfp
        cci_html = (
            _credfp.card_html(sym)
            + f'<div class="sub" style="margin:4px 0 12px"><a class="row" style="display:inline" '
              f'href="/dash/credibility?sym={quote_plus(sym)}">Full credibility fingerprint →</a></div>'
            + cci_html)
    except Exception:
        pass
    mep_html = _mep_stock_panel(sym)         # MEP signed accumulation/distribution dossier (D62)
    fno_html = _fno_stock_panel(sym)         # F&O Open-Interest identity channel ('' if no future)
    # Per-stock news timeline — the embed the news_view module was built for ("a Wire
    # rail with a ONE-LINE embed call"), finally wired as the dossier's News tab so the
    # content is reachable in-page (de-orphans /dash/news). Defensive: a news failure
    # must never break the dossier, so fall back to an empty pane.
    try:
        from src.web.news_view import render_stock_timeline as _render_news
        news_html = _render_news(sym)
    except Exception:                        # noqa: BLE001
        news_html = '<div class="sub mut" style="margin:12px 0">News timeline unavailable.</div>'

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

    # --- W2: cockpit verdict count-strip (7 tiles) + tabbed sub-nav -----------
    from src.web.cockpit import _CKPT_CSS as _CK, _ck_tile, _ck_strip, cci_state
    day_chg = None
    # Distinguish a real prior close from missing data (truthiness dropped a legit 0);
    # still skip a 0 divisor (a % change off zero is undefined, not "no data").
    if (len(series) >= 2 and series[-2]["close"] is not None
            and series[-1]["close"] is not None and series[-2]["close"] != 0):
        day_chg = (series[-1]["close"] / series[-2]["close"] - 1) * 100
    _conv = round(_conv_of(L.get("p_score"), L.get("rs_rank")))
    _xp = L.get("ratio_today_vs_power_1m")
    _ns, _tier = PS.get("ns_base"), PS.get("tier")
    _ct = cci_row.get("tier")
    _ncalls = cci_row.get("n_concalls") or 0
    _nset = cci_row.get("n_promises_resolved") or 0
    _ccist, _ = cci_state(cci_row)
    _p52 = L.get("pct_from_52w_high")
    _rsr = L.get("rs_rank")
    # MEP phase + F&O positioning for the header (accumulation at-a-glance, both together)
    _mph = _fq_hdr = None
    try:
        with get_conn() as _mc:
            _mr = _mc.execute("SELECT mep_state_smooth FROM mep_signals WHERE symbol=? "
                              "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
            _fr = _mc.execute("SELECT quadrant FROM fno_oi_signals WHERE symbol=? "
                              "ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
        _mph = _mr["mep_state_smooth"] if _mr else None
        _fq_hdr = _fr["quadrant"] if _fr else None
    except Exception:
        _mph = _fq_hdr = None
    _mph_lbl = {"STRONG_ACCUM": "STR ACC", "ACCUM": "ACCUM", "NEUTRAL": "NEUTRAL",
                "DISTRIB": "DISTRIB", "STRONG_DISTRIB": "STR DIST"}.get(_mph or "", "—")
    _fq_sub = ("F&amp;O " + _fq_hdr.replace("_", " ").title()) if _fq_hdr else "no F&amp;O future"
    verdict_strip = _ck_strip([
        _ck_tile(f"₹{_num(today_close, 1)}", "CMP", "#58a6ff", f"{_pct(day_chg)} today"),
        _ck_tile(f"{_conv}/100" if _conv is not None else "—", "Conviction", "#d2a8ff",
                 f"p{L.get('p_score') or 0}/5 · RS {_rsr if _rsr is not None else '—'}/99"),
        _ck_tile(f"{_rsr}/99" if _rsr is not None else "—", "RS rank", "#3fb950", "broad universe"),
        _ck_tile(f"{rank}{' ⚡' if L.get('is_ath_dvpt') else ''}", "DVPT trigger", "#f0883e",
                 (f"{_xp:.1f}× power-1m" if _xp is not None else "no spike")),
        _ck_tile(_mph_lbl, "Accum/Distrib · MEP", "#db61a2", _fq_sub),
        _ck_tile(_esc(_tier) if _tier else "—", "Quality · pt14", "#d29922",
                 (f"NS {_num(_ns, 1)}" if _ns is not None else "unscored")),
        _ck_tile(_esc(_ct) if _ct else "—", "Mgmt cred · CCI", "#39c5cf",
                 # Two distinct counts, not a fraction: promises resolved + concalls read.
                 # "N/M settled" read ambiguously (looked like a ratio); label each explicitly.
                 (f"{_ccist or 'pilot'} · {_nset} settled · {_ncalls} calls" if cci_row else "no concall data")),
        _ck_tile(_pct(_p52), "vs 52w-high", "var(--ink-2)", "today's close"),
    ])

    # --- THEME tags (session 33) — multi-label, always visible in the header ---
    from src.automation import theme_tags as TT
    with get_conn() as _tc:
        _stock_tags = TT.tags_with_provenance(_tc, sym)
    if _stock_tags:
        _prop = [t["tag"] for t in _stock_tags if not t["approved"]]
        _all = [t["tag"] for t in _stock_tags if t["approved"]] + _prop
        themes_line = ('<div class="sub" style="margin:8px 0 2px">Themes '
                       f'<a class="row" style="display:inline;font-size:11px" href="/dash/tags-review?sym={_q(sym)}">+ tag</a></div>'
                       '<div class="chips" style="margin-bottom:10px">'
                       + _tag_chips(_all, proposed=set(_prop)) + '</div>')
    else:
        themes_line = ('<div class="sub" style="margin:8px 0 10px">Themes: <span class="mut">none yet</span> '
                       f'<a class="row" style="display:inline;font-size:11px" href="/dash/tags-review?sym={_q(sym)}">+ add</a></div>')

    from src.web import glossary as G   # `?` hover-help on the dossier tab families
    _TABGLOSS = {"pos": "DVPT", "mep": "MEP phase", "rs": "RS rank",
                 "qual": "ns_base", "cpr": "pattern", "cci": "Credibility composite"}
    def _stab(k, lbl, on):
        oncls = ' class="on"' if on else ''
        disp = G.gloss(_TABGLOSS[k], lbl) if k in _TABGLOSS else lbl
        return f'<a href="#{k}" data-stab="{k}"{oncls}>{disp}</a>'
    _tabs = [("price", "Price"), ("pos", "Positioning · DVPT"), ("mep", "Accumulation · MEP"),
             ("rs", "Relative Strength"),
             ("qual", "Quality"), ("cpr", "Structure · CPR"), ("cci", "Credibility · CCI"),
             ("news", "News")]
    if fno_html:                              # F&O tab only for single-stock-futures names
        _tabs.append(("fno", "F&O · OI"))
    fno_pane = (f'<div class="tabpane" data-tab="fno" style="display:none">{fno_html}</div>'
                if fno_html else "")
    tabbar = ('<div class="tabbar" id="stabbar" style="position:sticky;top:0;background:var(--bg-1);z-index:5">'
              + "".join(_stab(k, l, i == 0) for i, (k, l) in enumerate(_tabs)) + '</div>')
    tab_js = """
<script>
(function(){
  var bar=document.getElementById('stabbar'); if(!bar) return;
  var hdr=document.querySelector('header'); if(hdr) bar.style.top=hdr.offsetHeight+'px';
  var panes={}; document.querySelectorAll('.tabpane').forEach(function(p){panes[p.dataset.tab]=p;});
  var booted={};
  function reveal(k){
    if(k==='rs' && !booted.rs && window.__bootRS){ booted.rs=1; try{ window.__bootRS(); }catch(e){ console.error('RS overlay boot failed', e); } }
  }
  function show(k){
    if(!panes[k]) k='price';
    Object.keys(panes).forEach(function(t){ panes[t].style.display=(t===k)?'':'none'; });
    bar.querySelectorAll('a[data-stab]').forEach(function(a){ a.classList.toggle('on', a.dataset.stab===k); });
    reveal(k);
  }
  bar.querySelectorAll('a[data-stab]').forEach(function(a){
    a.addEventListener('click', function(e){ e.preventDefault(); var k=a.dataset.stab;
      show(k); if(history.replaceState) history.replaceState(null,'','#'+k); });
  });
  var h=(location.hash||'').replace('#',''); show(panes[h]?h:'price');
})();
</script>
"""

    # h2 bits — render the DVPT-rank pill ONLY when there's a REAL rank. trigger_rank is
    # the sentinel string "-" (NOT NULL) for unranked names like RELIANCE, so gate on the
    # display value not being that placeholder — otherwise the headline showed a stray
    # "RELIANCE - · …" pill. ⚡ ATH badge only when truthy. Each piece carries its own
    # leading space so an absent piece leaves no double-gap or dash.
    _rank_pill = (f' <span class="pill p-{rank}">{rank}</span>'
                  if str(rank).strip() not in ("", "-") else '')
    _ath_bit = f' {ath}' if ath else ''
    _name_bit = (' · ' + _esc(company_name)) if company_name else ''
    body = f"""{search}
<style>{chart_css}</style>
{G.css()}
{_CK}
<div class="sub" style="margin:0 0 6px">&#8592; <a class="row" style="display:inline" href="/dash/screener">Screener</a> · <a class="row" style="display:inline" href="/dash/conviction">Conviction</a></div>
<h2>{_esc(sym)}{_rank_pill}{_ath_bit}{_name_bit}</h2>
<div class="sub">{L['trade_date']} · close ₹{_num(today_close,2)} · deliv {_num(L.get('deliv_per'),1)}%</div>
{verdict_strip}
{themes_line}
{track_html}
{tabbar}
<div class="tabpane" data-tab="price">
<div class="kpi">
  <div class="box"><div class="num">{L.get('r_score') or 0}/{L.get('p_score') or 0}</div><div class="lbl">r / p score</div></div>
  <div class="box"><div class="num">{_safe_int(L.get('delivery_value_per_trade')):,}</div><div class="lbl">DVPT today</div></div>
  <div class="box"><div class="num">{_num(L.get('ratio_today_vs_power_1m'))}</div><div class="lbl">vs power 1m</div></div>
</div>
<div class="fbar" id="ctBar">
  <button class="fbtn on" data-ctype="candle">Candles</button>
  <button class="fbtn" data-ctype="line">Line</button>
</div>
<div class="fbar"><label class="fbtn" style="cursor:pointer;display:inline-flex;align-items:center;gap:6px"><input type="checkbox" id="wfChk" style="margin:0">Wolfe wave</label><span id="wfLbl" style="color:var(--ink-2);font-size:12px;margin-left:8px"></span></div>
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
  <button data-r="1260">5Y</button>
  <button data-r="0" class="on">Max</button>
</div>
<div class="chartwrap">
  <div class="chartlbl"><b style="color:var(--ink)">{_esc(sym)}</b>{(' · '+_esc(company_name)) if company_name else ''} — price + institutional zones (split/bonus-adjusted){'  ⚠ recent corporate action — zone overlay approximate' if zone_action_recent else ''}</div>
  <div id="priceRdt" style="font-size:12px;color:var(--ink);font-variant-numeric:tabular-nums;min-height:16px;margin:2px 0 3px;"></div>
  <div id="priceChart" style="height:300px;"></div>
</div>
{_WF_SNIPPET}
{_CPR_SNIPPET}
{_MA_SNIPPET}
{_MEP_SNIPPET}
<div class="chartwrap">
  <div class="chartlbl"><b style="color:var(--ink)">{_esc(sym)}</b> · DVPT per trade — institutional spikes (amber = institutional-intensity day, r1m &gt; 1)</div>
  <div id="dvptChart" style="height:150px;"></div>
</div>
<div class="chartwrap">
  <div class="chartlbl"><b style="color:var(--ink)">{_esc(sym)}</b> · Delivery %</div>
  <div id="delivChart" style="height:120px;"></div>
</div>
<div class="chartwrap">
  <div class="chartlbl"><b style="color:var(--ink)">{_esc(sym)}</b> · Traded value (bar) + delivery value (bright = took delivery)</div>
  <div id="tvChart" style="height:130px;"></div>
</div>
</div><!-- /tab price -->
<div class="tabpane" data-tab="pos" style="display:none">
{insight_html}
{inertia_html}
{character_html}
{zones_html}
{keyprice_html}
</div>
<div class="tabpane" data-tab="mep" style="display:none">
{mep_html}
</div>
<div class="tabpane" data-tab="rs" style="display:none">
{rs_html}
{sector_ctx_html}
{rs_overlay_html}
{momentum_html}
</div>
<div class="tabpane" data-tab="qual" style="display:none">
{pt14_html}
</div>
<div class="tabpane" data-tab="cpr" style="display:none">
{cpr_html}
</div>
<div class="tabpane" data-tab="cci" style="display:none">
{cci_html}
</div>
<div class="tabpane" data-tab="news" style="display:none">
{news_html}
</div>
{fno_pane}

<script src="{_LWC_CDN}"></script>
<script>window.__wfdata={data_json};</script>
{_STOCK_CHART_SNIPPET}
{tab_js}
"""
    return HTMLResponse(_shell(f"{sym} · patearn", body, "stock", L["trade_date"], wide=True))


# Ratio chart JS (plain template — no f-string; __DATA__ is replaced with the
# server JSON). Clones the stock page's lightweight-charts v4 approach: line
# series + client-side range buttons + markers + ResizeObserver.
_RATIO_CHART_JS = """
<script src="__CDN__"></script>
<script>
const DATA = __DATA__;
(function(){
  const host = document.getElementById('ratioChart');
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:var(--ink-2);padding:20px">Chart library failed to load (offline?).</div>'; return; }
  const D = DATA;
  const common = {
    layout: { background:{color:'#161b22'}, textColor:'#8b949e', fontSize:11 },
    grid: { vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'} },
    timeScale: { borderColor:'#30363d', rightOffset:3 },
    rightPriceScale: { borderColor:'#30363d' },
    crosshair: { mode: 0 },
    handleScroll:true, handleScale:true,
  };
  // Bound the chart to its container (like the other bounded charts): a clamped,
  // FIXED height set once at init, and an explicit starting width = the host's real
  // content box. The ResizeObserver below then re-applies WIDTH ONLY on resize so the
  // canvas tracks its column at narrow (mobile) widths without overflowing the page.
  // (Height is never re-written inside the observer — mutating the observed element's
  //  box from its own callback risks a resize feedback loop.)
  const CH_H = Math.max(220, Math.min(300, Math.round(window.innerHeight*0.42)));
  host.style.height = CH_H + 'px';
  const chart = LightweightCharts.createChart(host, Object.assign(
    {width: Math.max(0, host.clientWidth), height: CH_H}, common));
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
    if (d.cross50) mk.push({time:d.t,position:'belowBar',color:'#3fd486',shape:'arrowUp',text:'↑50'});
    if (d.nh52)    mk.push({time:d.t,position:'aboveBar',color:'#3fd486',shape:'circle'});
    if (i>0){
      const p=D[i-1];
      if (d.ma50!=null && p.ma50!=null && d.ratio<d.ma50 && p.ratio>=p.ma50)
        mk.push({time:d.t,position:'aboveBar',color:'#ff6a7a',shape:'arrowDown',text:'↓50'});
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
  // Keep the canvas bound to its column: on resize, explicitly resize the chart to the
  // host's current content width (chart.resize is the call that actually re-lays-out the
  // canvas in this LWC build; applyOptions({width}) alone does not). Height is the fixed
  // clamped CH_H. We observe the STABLE parent (.chartwrap, whose box we never mutate)
  // and only call resize() — so there is no resize feedback loop. This stops the chart
  // overflowing the page at narrow (mobile) widths.
  let rzT=null, lastW=host.clientWidth;
  function fit(){
    const w=host.clientWidth;
    if(w>0 && w!==lastW){ lastW=w; chart.resize(w, CH_H); }  // width-gated → a resize() can't re-trigger itself
  }
  new ResizeObserver(()=>{ if(rzT) clearTimeout(rzT); rzT=setTimeout(fit,120); }).observe(host.parentElement || host);
  window.addEventListener('resize', ()=>{ if(rzT) clearTimeout(rzT); rzT=setTimeout(fit,120); });

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


@router.get("/dash/launchpad", response_class=HTMLResponse)
def dash_launchpad() -> HTMLResponse:
    """Live Launchpad setup screen (cockpit.render_launchpad) — the D56 validated
    explosive-move precursors over today's liquid universe, computed render-time."""
    sig_date, idx_date = _latest_dates()
    from src.web.cockpit import render_launchpad
    return HTMLResponse(_shell("Launchpad · patearn",
                               render_launchpad(sig_date, idx_date),
                               "launchpad", sig_date or "", wide=True))


@router.get("/dash/index", response_class=HTMLResponse)
def dash_index(idx: str = Query("", max_length=60)) -> HTMLResponse:
    """Full-bleed single-index detail page (cockpit.render_index_detail). The new
    primary destination for every index/sector handle across the dashboard — a
    rigorous two-axis trend verdict + own-price chart + valuation + the bottom-up
    constituent roll-up. /dash/ratio stays as the linked full RS-ratio sub-page."""
    sig_date, idx_date = _latest_dates()
    from src.web.cockpit import render_index_detail
    return HTMLResponse(_shell(f"{idx or 'Index'} · patearn",
                               render_index_detail(idx, idx_date, sig_date),
                               "markets", idx_date or "", wide=True))


@router.get("/dash/themes", response_class=HTMLResponse)
def dash_themes() -> HTMLResponse:
    """Themes browse — the multi-label thematic tag layer (session 33). ADDITIVE:
    a lens beside Markets/Sectors. Data = company_tags + src.automation.theme_tags."""
    _, idx_date = _latest_dates()
    from src.web.cockpit import render_themes
    return HTMLResponse(_shell("Themes · patearn", render_themes(idx_date),
                               "themes", idx_date or "", wide=True))


@router.get("/dash/theme", response_class=HTMLResponse)
def dash_theme(tag: str = Query("", max_length=60)) -> HTMLResponse:
    """One theme's participants drill (/dash/theme?tag=Infrastructure)."""
    sig_date, idx_date = _latest_dates()
    from src.web.cockpit import render_theme_detail
    return HTMLResponse(_shell(f"{tag or 'Theme'} · patearn",
                               render_theme_detail(tag, idx_date, sig_date),
                               "themes", idx_date or "", wide=True))


@router.get("/dash/tags-review", response_class=HTMLResponse)
def dash_tags_review(added: str = Query("", max_length=60),
                     err: str = Query("", max_length=60),
                     sym: str = Query("", max_length=20)) -> HTMLResponse:
    """Approve AI-proposed theme tags + hand-add/remove tags (session 33)."""
    _, idx_date = _latest_dates()
    from src.web.cockpit import render_tags_review
    return HTMLResponse(_shell("Review tags · patearn",
                               render_tags_review(added, err, sym),
                               "tags-review", idx_date or "", wide=True))


@router.post("/dash/tags")
def dash_tags_act(action: str = Form(...), symbol: str = Form(""),
                  tag: str = Form(""), nxt: str = Form("/dash/tags-review")) -> RedirectResponse:
    """Approve / reject an AI proposal, or add / remove a manual theme tag.
    Index-seeded facts are immutable here (remove targets source='ramana' only)."""
    from src.automation import theme_tags as TT
    symbol = (symbol or "").upper().strip()
    tag = (tag or "").strip()
    ok = True
    try:
        with get_conn() as conn:
            if action == "approve" and symbol and tag:
                TT.approve(conn, symbol, tag)
            elif action == "reject" and symbol and tag:
                TT.reject(conn, symbol, tag)
            elif action == "unreject" and symbol and tag:
                TT.unreject(conn, symbol, tag)
            elif action == "add" and symbol and tag and TT.vocab_entry(tag) is not None:
                TT.add_manual(conn, symbol, tag)
            elif action == "remove" and symbol and tag:
                conn.execute("DELETE FROM company_tags WHERE symbol=? AND tag=? AND source='ramana'",
                             (symbol, tag))
                conn.commit()
            elif action == "approve_theme" and tag:           # bulk: all pending for a theme
                TT.approve_all_for_theme(conn, tag)
            elif action == "approve_symbol" and symbol:       # bulk: all pending for a company
                TT.approve_all_for_symbol(conn, symbol)
            else:
                ok = False
    except Exception:
        ok = False
    if not nxt.startswith("/dash/"):
        nxt = "/dash/tags-review"
    sep = "&" if "?" in nxt else "?"
    return RedirectResponse(f"{nxt}{sep}{'added' if ok else 'err'}={_q(tag or symbol)}", status_code=303)


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
        return HTMLResponse(_shell("Ratio · patearn", body, "sectors", idx_date or "", wide=True))

    with get_conn() as conn:
        known = conn.execute(
            "SELECT 1 FROM index_rows WHERE index_name=? LIMIT 1", (idx,)).fetchone()
        if not known:
            body = f'<div class="empty">Unknown index <b>{_esc(idx)}</b>.</div>'
            return HTMLResponse(_shell("Ratio · patearn", body, "sectors", idx_date or "", wide=True))

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
            return HTMLResponse(_shell(f"{idx} ratio · patearn", body, "ratio", idx_date or "", wide=True))

        sig = conn.execute(
            """SELECT rs_vs_broad_trend_state st, ret_3m_pct r3,
                      ret_1d_pct r1d, ret_1w_pct r1w, ret_1m_pct r1m,
                      ret_6m_pct r6, ret_12m_pct r12,
                      pct_above_50d_avg pa50, pct_above_200d_avg pa200,
                      pct_off_52w_high off52h, pct_above_52w_low abv52l,
                      close_value iclose,
                      rs_vs_broad_today rs, rs_vs_broad_slope_1m s1,
                      rs_vs_broad_slope_3m s3, rs_vs_broad_slope_6m s6,
                      rs_vs_broad_slope_12m s12,
                      rs_vs_broad_slope_18m s18, rs_vs_broad_slope_24m s24,
                      rs_vs_broad_above_50ma a50,
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

        # Rotation tail for the mini-RRG (canonical RS-Ratio × RS-Momentum vs den).
        from src.automation import rrg
        idx_tail = rrg.tail(idx, den, n=130, conn=conn)

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
    strip = _rs_strip(S.get("s1"), S.get("s3"), S.get("s6"), S.get("s12"), S.get("s18"), S.get("s24"))
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
        f'<div class="card" style="display:flex;align-items:center;gap:12px">'
        f'<div style="font-size:28px;font-weight:700;line-height:1;white-space:nowrap">{pctl}'
        f'<span class="sub" style="margin:0;font-size:14px">/99</span></div>'
        f'<div style="flex:1;min-width:0">'
        f'<div class="bar" style="margin:0 0 4px"><span style="width:{pctl}%"></span></div>'
        f'<div class="sub" style="margin:0;font-size:11px;line-height:1.3">stronger than {pctl}% of sectors '
        f'(0.6·3m + 0.4·6m slope, ranked across {n_mom} sectors)</div></div></div>')

    # --- Relative rotation (mini-RRG) — canonical RS-Ratio × RS-Momentum + JdK
    # quadrants + tail, shared with the depth panel and /dash/rrg (D68). Replaces the
    # old return×slope "Absolute × Relative" quad whose labels could disagree with it.
    from src.web.mini_rrg import mini_rrg_card
    quad_html = (
        '<h2>Relative rotation</h2>'
        f'<div class="sub">RS-Ratio &times; RS-Momentum vs {_esc(den)}, JdK-normalised ~100 — '
        'the same read as the depth panel and the full RRG '
        '(improving &rarr; leading &rarr; weakening &rarr; lagging).</div>'
        + mini_rrg_card(idx_tail, den=den, tail_label="last ~6 months", size=280))

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
        trend_pill = (f'<span class="pill p-{st}">{_state_label(st)}</span>'
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

    chip = f' <span class="pill p-{st}">{_state_label(st)}</span>' if st and st != "—" else ''
    other = "Nifty 50" if den == "Nifty 500" else "Nifty 500"
    chart_css = """
.rangebar { display:flex; gap:6px; margin:8px 0 4px; }
.rangebar button { background:var(--bg-3); color:var(--ink); border:1px solid var(--line-2);
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:var(--bg-2); border:1px solid var(--line-2); border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:var(--ink-2); font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
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
  <div id="ratioRdt" style="font-size:12px;color:var(--ink);font-variant-numeric:tabular-nums;min-height:16px;margin:2px 0 3px;"></div>
  <div id="ratioChart" style="height:300px;"></div>
</div>
{pill_row}
{gauge_html}
{quad_html}
{consts_html}
{chart_js}
"""
    return HTMLResponse(_shell(f"{idx} ratio · patearn", body, "ratio",
                               idx_date or "", wide=True))


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
  if (!window.LightweightCharts) { host.innerHTML='<div style="color:var(--ink-2);padding:20px">Chart library failed to load (offline?).</div>'; return; }
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
      +it.color+';text-shadow:0 0 3px var(--bg-1),0 0 2px var(--bg-1)">'+_e(it.name)+'</span>').join('');
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
.rangebar button { background:var(--bg-3); color:var(--ink); border:1px solid var(--line-2);
                   border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }
.rangebar button.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.chartwrap { background:var(--bg-2); border:1px solid var(--line-2); border-radius:10px; padding:8px; margin-bottom:6px; }
.chartlbl { color:var(--ink-2); font-size:11px; text-transform:uppercase; letter-spacing:.4px; margin:2px 4px 4px; }
.cmp-rail { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:8px; }
.cmp-chip { display:inline-flex; align-items:center; gap:6px; background:var(--bg-2);
            border:1px solid var(--line-2); border-radius:14px; padding:5px 8px 5px 9px; font-size:13px; }
.cmp-chip.cmp-dim { opacity:.4; }
.cmp-sw { width:10px; height:10px; border-radius:50%; display:inline-block; }
.cmp-tag { font-size:9px; font-weight:700; color:var(--ink-2); background:var(--bg-3);
           border-radius:4px; padding:1px 4px; letter-spacing:.4px; }
.cmp-x { color:var(--ink-2); text-decoration:none; font-size:12px; margin-left:1px; }
.cmp-x:hover { color:#f85149; }
.cmp-sugg.cmp-hide { display:none; }
button.cmp-sugg { cursor:pointer; font-family:inherit; }
.cmp-sugg.cmp-on { background:#1f6feb; border-color:#1f6feb; color:#fff; }
.cmp-presets { display:flex; gap:6px; flex-wrap:wrap; margin:2px 0 12px; }
.cmp-pin { display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:6px 0 2px; font-size:12px; color:var(--ink-2); }
.cmp-pin input[type=date] { background:var(--bg-1); border:1px solid var(--line-2); color:var(--ink);
                            border-radius:6px; padding:3px 7px; font-size:12px; }
.cmp-anchor { font-size:12px; color:var(--ink-2); margin:6px 4px 2px; }
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
        return HTMLResponse(_shell("Compare · patearn", body, "compare", idx_date or "", wide=True))

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
    return HTMLResponse(_shell("Compare · patearn", body, "compare", idx_date or "", wide=True))


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

# CL-DASH-12: PWA icon = the patearn header mark (uptrend line + the cyan/green dot), NOT
# the legacy Hermes "H" glyph. The brand is patearn; the bare "H" was a leftover. The line
# rises and centres so the mark reads at any size; the dot is the same accent the topbar
# logo uses. (Hermes survives only as the Nous agent name, not the product brand.)
_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="#0e1116"/>
<rect width="512" height="512" rx="96" fill="#161b22"/>
<g stroke="#1f6feb" stroke-width="40" stroke-linecap="round" stroke-linejoin="round" fill="none">
  <path d="M104 372 L208 248 L296 312 L408 156"/>
</g>
<circle cx="408" cy="156" r="34" fill="#3fb950"/>
</svg>"""

# Network-first service worker: always try fresh data, fall back to cache offline.
_SW_JS = """const CACHE = 'hermes-v3';
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
  // Page navigations (Back/Forward, links, typed URLs): do NOT intercept — let
  // the browser handle them natively so its back/forward cache (bfcache) works,
  // giving instant Back/Forward instead of a full server re-fetch + re-render. A
  // network-first SW that intercepts navigations disables bfcache (the cause of
  // the sluggish Back/Forward on heavy pages). The SW now only caches assets.
  if (e.request.mode === 'navigate') return;
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
