"""
screener_plus.py — Lane B · the STREAMLINED screener at /dash/screen2.

ONE wide, configurable, frozen-pane screener that unifies what is otherwise
scattered across the per-strategy lenses. The streamlining over /dash/screener:
  * a CONFLUENCE lead column (0–5) — how many pillars align right now
    (DVPT positioning · MEP accumulation · RS strength · CPR structure · CCI
    credibility) — with a ★ when ≥4 align. Sort once, see everything that lines up.
  * one-click column-GROUP toggle chips (show/hide each strategy's block) so the
    grid is as wide or as tight as the question needs — persisted across reloads.
  * SAVED SCREENS — name a (scope + visible-groups) combo and reload it instantly.
  * a single frozen top header AND frozen Symbol column; client-side sort / text
    filter / CSV export. Server-rendered HTML + vanilla JS (data-first-light-ui).

Ownership / isolation (plan §1, Lane B): NEW self-contained module. Imports only
ui_kit (chrome), v2_surfaces (nav, best-effort), and src.core.db (precomputed
reads). Touches no parallel-owned file. Self-mounts via `router`. PRECOMPUTED
tables only (stock_signals, mep_signals, cpr_signals, concall_scores) —
never recompute a strategy on read.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.web import ui_kit as K

log = logging.getLogger("hermes.screen2")
router = APIRouter()

_BROAD = ["Nifty 50", "Nifty Next 50", "Nifty Midcap 150",
          "Nifty Smallcap 250", "Nifty 500"]
_SECTORS = ["Nifty Bank", "Nifty Financial Services", "Nifty IT", "Nifty Auto",
            "Nifty Pharma", "Nifty FMCG", "Nifty Metal", "Nifty Energy",
            "Nifty Realty", "Nifty Media", "Nifty Infrastructure",
            "Nifty Commodities", "Nifty Healthcare Index", "Nifty Consumer Durables",
            "Nifty Oil & Gas", "Nifty India Defence", "Nifty Private Bank",
            "Nifty Chemicals"]

# column groups (key -> label) — also the toggle-chip legend
_GROUPS = [
    ("conf", "Confluence"), ("pos", "Positioning · DVPT"), ("mep", "Accumulation · MEP"),
    ("rs", "Relative strength"), ("cpr", "Structure · CPR"),
    ("cci", "Credibility · CCI"), ("ctx", "Context"),
]

_LIQ = ("b.series='EQ' AND (b.segment='CM' OR b.segment IS NULL) "
        "AND b.value > 10000000 AND b.close > 20 "
        "AND s.symbol IN (SELECT symbol FROM nse_equity_list)")


# ── nav / sub-nav (best-effort full site nav) ────────────────────────────────
def _nav_html(active: str) -> str:
    try:
        from src.web import v2_surfaces as V
        return K.nav_links(V.site_nav(active))
    except Exception:  # noqa: BLE001
        return ""


def _sub() -> str:
    return K.subnav([
        ("Screen", "/dash/screener", False),
        ("Screen+", "/dash/screen2", True),
        ("Themes / Baskets", "/dash/themes", False),
        ("Strategist", "/dash/strategist", False),
        ("Workbench", "/dash/workbench", False),
    ])


# ── data helpers ─────────────────────────────────────────────────────────────
def _latest(conn, table, col="trade_date"):
    try:
        r = conn.execute(f"SELECT MAX({col}) d FROM {table}").fetchone()
        return r["d"] if r else None
    except Exception:  # noqa: BLE001
        return None


def _sector_symbols(conn, sector):
    try:
        rows = conn.execute(
            """SELECT symbol FROM stock_index_membership
               WHERE index_name=? AND snapshot_date=(
                   SELECT MAX(snapshot_date) FROM stock_index_membership WHERE index_name=?)
               ORDER BY symbol""", (sector, sector)).fetchall()
        return [r["symbol"] for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _cpr_by_tf(conn, syms, tf):
    """{sym: row} latest cpr_signals for a timeframe over the given symbols."""
    out = {}
    if not syms:
        return out
    try:
        mx = conn.execute(
            "SELECT MAX(period_end_date) d FROM cpr_signals WHERE timeframe=?", (tf,)).fetchone()
        if not mx or not mx["d"]:
            return out
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT * FROM cpr_signals
                    WHERE timeframe=? AND period_end_date=? AND symbol IN ({ph})""",
                [tf, mx["d"], *syms]).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("cpr lookup failed: %s", e)
    return out


def _cci_by_sym(conn, syms):
    out = {}
    if not syms:
        return out
    try:
        ph = ",".join("?" for _ in syms)
        for r in conn.execute(
                f"""SELECT s.* FROM concall_scores s
                    JOIN (SELECT symbol, MAX(last_updated) m FROM concall_scores GROUP BY symbol) x
                      ON x.symbol=s.symbol AND x.m=s.last_updated
                    WHERE s.symbol IN ({ph})""", syms).fetchall():
            out[r["symbol"]] = dict(r)
    except Exception as e:  # noqa: BLE001
        log.warning("cci lookup failed: %s", e)
    return out


# ── cell formatters ──────────────────────────────────────────────────────────
def _num(v, dp=2):
    return f"{v:,.{dp}f}" if isinstance(v, (int, float)) else "—"


def _pct(v, dp=1):
    return f"{v:+.{dp}f}%" if isinstance(v, (int, float)) else "—"


def _trend_pill(st):
    if not st:
        return '<span class="mut">—</span>'
    kind = "up" if "STRONG_UP" in st or st in ("UPTREND", "UP") else \
           "down" if "DOWN" in st else "neutral"
    return K.pill(st.replace("_", " ").title(), kind)


def _mep_pill(st):
    if not st:
        return '<span class="mut">—</span>'
    kind = "up" if "ACCUM" in st else "down" if "DISTRIB" in st else "neutral"
    return K.pill(st.replace("_", " ").title(), kind)


def _tier_pill(t):
    if not t:
        return '<span class="mut">—</span>'
    kind = "cred" if t in ("A+", "A") else "warn" if t == "B" else "down" if t in ("D",) else "neutral"
    return K.pill(t, kind)


# ── the page ─────────────────────────────────────────────────────────────────
@router.get("/dash/screen2", response_class=HTMLResponse)
def dash_screen2(scope: str = Query("Nifty 500"),
                 limit: int = Query(600, ge=50, le=2000)) -> HTMLResponse:
    scope = (scope or "Nifty 500").strip()
    is_all = scope.lower() == "all"
    is_watch = scope.lower() in ("watch", "watchlist")
    rows: list[dict] = []
    sig_date = None
    cpr_d = cpr_w = cci = {}
    n_members = None

    try:
        with get_conn() as conn:
            sig_date = _latest(conn, "stock_signals")
            if sig_date:
                if is_all:
                    scope_syms = None
                elif is_watch:
                    scope_syms = [r["symbol"] for r in conn.execute(
                        "SELECT symbol FROM watchlist ORDER BY symbol").fetchall()]
                else:
                    scope_syms = _sector_symbols(conn, scope)
                n_members = len(scope_syms) if scope_syms is not None else None

                clause, params = "", [sig_date]
                if scope_syms is not None:
                    use = scope_syms or ["\x00"]
                    clause = " AND s.symbol IN (" + ",".join("?" for _ in use) + ")"
                    params += use
                params.append(limit)

                conv = "(0.55*COALESCE(s.p_score,0)/5.0*100.0 + 0.45*COALESCE(s.rs_rank,0))"
                rows = [dict(r) for r in conn.execute(
                    f"""SELECT s.symbol, s.primary_sector sector, b.close,
                               s.pct_from_52w_high hh, s.trigger_rank rank,
                               s.p_score, s.r_score, s.ratio_today_vs_power_1m x1,
                               b.deliv_per, s.accum_character ch, s.turnover_surge_1m su1,
                               s.rs_rank, s.rs_vs_broad_trend_state rsbt,
                               s.rs_vs_broad_slope_1m b1, s.rs_vs_broad_slope_3m b3,
                               s.rs_vs_broad_slope_6m b6, s.rs_vs_broad_slope_12m b12,
                               {conv} conv,
                               m.mep_score_smooth mep_ph, m.mep_state_smooth mep_st
                        FROM stock_signals s JOIN bhavcopy_rows b USING (symbol, trade_date)
                        LEFT JOIN mep_signals m ON m.symbol=s.symbol AND m.trade_date=s.trade_date
                        WHERE s.trade_date=? AND s.delivery_value_per_trade IS NOT NULL
                          AND {_LIQ}{clause}
                        ORDER BY conv DESC, COALESCE(s.p_score,-1) DESC LIMIT ?""",
                    params).fetchall()]

                if rows:
                    syms = [r["symbol"] for r in rows]
                    cpr_d = _cpr_by_tf(conn, syms, "D")
                    cpr_w = _cpr_by_tf(conn, syms, "W")
                    cci = _cci_by_sym(conn, syms)
    except Exception as e:  # noqa: BLE001
        log.warning("screen2 query failed: %s", e)

    # ── build rows with the confluence score ──
    trs = []
    for r in rows:
        sym = r["symbol"]
        cd = cpr_d.get(sym, {})
        cw = cpr_w.get(sym, {})
        cc = cci.get(sym, {})

        # confluence pillars (each 0/1) — the unifying read
        p_pos = 1 if (r.get("p_score") or 0) >= 4 else 0
        p_mep = 1 if (r.get("mep_st") or "") in ("ACCUM", "STRONG_ACCUM") else 0
        p_rs = 1 if (r.get("rs_rank") or 0) >= 80 else 0
        p_cpr = 1 if (cd.get("pattern") == "BULL_U") else 0
        p_cci = 1 if (cc.get("tier") or "") in ("A+", "A") else 0
        confl = p_pos + p_mep + p_rs + p_cpr + p_cci
        star = "★ " if confl >= 4 else ""
        dots = "".join(
            f'<span class="cd {"on" if on else ""}" title="{lbl}"></span>'
            for lbl, on in [("DVPT", p_pos), ("MEP", p_mep), ("RS", p_rs),
                            ("CPR", p_cpr), ("CCI", p_cci)])

        rank = r.get("rank") or "-"
        mep_ph = r.get("mep_ph")
        mep_ph_td = (f'<td class="num cg-mep" data-v="{mep_ph if mep_ph is not None else -99}" '
                     f'style="color:{"var(--up)" if (mep_ph or 0)>=0 else "var(--down)"}">'
                     f'{mep_ph:+.2f}</td>' if mep_ph is not None
                     else '<td class="num cg-mep mut" data-v="-99">—</td>')
        cpr_dpat = cd.get("pattern") or "—"
        cpr_wpat = cw.get("pattern") or "—"
        cp = cd.get("compression_pctile")
        x1v = r.get("x1")
        x1_txt = f"{x1v:.1f}×" if x1v else "—"
        dpv = r.get("deliv_per")
        dp_txt = f"{dpv:.1f}%" if dpv is not None else "—"

        trs.append(
            f'<tr>'
            # identity (always visible)
            f'<td class="sym"><a href="/dash/stock?sym={K.esc(sym)}">{K.esc(sym)}</a></td>'
            f'<td class="l mut">{K.esc(r.get("sector") or "—")}</td>'
            f'<td class="num" data-v="{r.get("close") or 0}">{_num(r.get("close"),1)}</td>'
            # confluence (lead)
            f'<td class="num cg-conf confl c{confl}" data-v="{confl}"><b>{star}{confl}</b>'
            f'<span class="dots">{dots}</span></td>'
            # positioning · dvpt
            f'<td class="cg-pos" data-v="{rank}"><span class="uk-pill neutral">{K.esc(str(rank))}</span></td>'
            f'<td class="num cg-pos" data-v="{r.get("p_score") if r.get("p_score") is not None else -1}">{r.get("p_score") if r.get("p_score") is not None else "—"}</td>'
            f'<td class="num cg-pos" data-v="{r.get("r_score") if r.get("r_score") is not None else -1}">{r.get("r_score") if r.get("r_score") is not None else "—"}</td>'
            f'<td class="num cg-pos" data-v="{x1v or 0}">{x1_txt}</td>'
            f'<td class="num cg-pos" data-v="{dpv or 0}">{dp_txt}</td>'
            # mep
            + mep_ph_td +
            f'<td class="l cg-mep" data-v="{r.get("mep_ph") or -99}">{_mep_pill(r.get("mep_st"))}</td>'
            # rs
            f'<td class="num cg-rs" data-v="{r.get("rs_rank") if r.get("rs_rank") is not None else -1}"><b>{r.get("rs_rank") if r.get("rs_rank") is not None else "—"}</b></td>'
            f'<td class="l cg-rs" data-v="{K.esc(r.get("rsbt") or "")}">{_trend_pill(r.get("rsbt"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b1") or 0}">{_pct(r.get("b1"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b3") or 0}">{_pct(r.get("b3"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b6") or 0}">{_pct(r.get("b6"))}</td>'
            f'<td class="num cg-rs" data-v="{r.get("b12") or 0}">{_pct(r.get("b12"))}</td>'
            # cpr
            f'<td class="l cg-cpr" data-v="{K.esc(cpr_dpat)}">{_cpr_pat(cpr_dpat)}</td>'
            f'<td class="num cg-cpr" data-v="{cp or 0}">{(f"{cp*100:.0f}%") if cp is not None else "—"}</td>'
            f'<td class="l cg-cpr" data-v="{K.esc(cpr_wpat)}">{_cpr_pat(cpr_wpat)}</td>'
            # cci
            f'<td class="num cg-cci" data-v="{cc.get("composite_score") or -1}">{_num(cc.get("composite_score"),0)}</td>'
            f'<td class="l cg-cci" data-v="{K.esc(cc.get("tier") or "")}">{_tier_pill(cc.get("tier"))}</td>'
            f'<td class="l cg-cci mut" data-v="{K.esc(cc.get("credibility_trend") or "")}">{K.esc((cc.get("credibility_trend") or "—").title())}</td>'
            # context
            f'<td class="num cg-ctx" data-v="{r.get("su1") or 0}">{_num(r.get("su1"),2)}</td>'
            f'<td class="num cg-ctx" data-v="{r.get("hh") or -999}">{_pct(r.get("hh"))}</td>'
            f'<td class="l cg-ctx mut" data-v="{K.esc(r.get("ch") or "")}">{K.esc((r.get("ch") or "—"))}</td>'
            '</tr>')

    # ── header (two rows: group band + column names) ──
    grp_band = (
        '<tr class="grp">'
        '<th class="sym">stock</th><th colspan="2">identity</th>'
        '<th class="cg-conf gl" colspan="1">confluence</th>'
        '<th class="cg-pos gl" colspan="5">positioning · dvpt</th>'
        '<th class="cg-mep gl" colspan="2">accumulation · mep</th>'
        '<th class="cg-rs gl" colspan="6">relative strength</th>'
        '<th class="cg-cpr gl" colspan="3">structure · cpr</th>'
        '<th class="cg-cci gl" colspan="3">credibility · cci</th>'
        '<th class="cg-ctx gl" colspan="3">context</th></tr>')
    cols = ['Symbol', 'Sector', 'CMP', 'Confl',
            'Rank', 'P', 'R', '×1m', 'Dlv%',
            'Phase', 'State',
            'RS#', 'Trend', '1m', '3m', '6m', '12m',
            'D', 'Cmpr', 'W',
            'CCI', 'Tier', 'Trend',
            'Surge', '%52wH', 'Char']
    col_groups = ['', '', '', 'cg-conf',
                  'cg-pos', 'cg-pos', 'cg-pos', 'cg-pos', 'cg-pos',
                  'cg-mep', 'cg-mep',
                  'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs', 'cg-rs',
                  'cg-cpr', 'cg-cpr', 'cg-cpr',
                  'cg-cci', 'cg-cci', 'cg-cci',
                  'cg-ctx', 'cg-ctx', 'cg-ctx']
    col_band = '<tr class="col">' + "".join(
        f'<th class="{("sym" if i==0 else "")} {g}" data-c="{i}">{K.esc(c)}</th>'
        for i, (c, g) in enumerate(zip(cols, col_groups))) + '</tr>'
    thead = f'<thead>{grp_band}{col_band}</thead>'
    tbody = "".join(trs)

    # ── controls: scope chips + group toggles + saved screens + filter ──
    def _schip(name, label=None):
        on = " on" if scope.lower() == name.lower() else ""
        return (f'<a class="uk-pill {"acc" if on else "neutral"}" '
                f'href="/dash/screen2?scope={_q(name)}">{K.esc(label or name)}</a>')
    chips = "".join(_schip(n) for n in _BROAD) + _schip("all", "All") + _schip("watch", "★ Watch")
    sec_opts = "".join(
        f'<option value="{K.esc(s)}"{" selected" if scope.lower()==s.lower() else ""}>{K.esc(s)}</option>'
        for s in _SECTORS)
    sec_sel = ('<select id="secSel" onchange="if(this.value)location=\'/dash/screen2?scope=\'+encodeURIComponent(this.value)">'
               f'<option value="">Sector ▾</option>{sec_opts}</select>')

    grp_chips = "".join(
        f'<button type="button" class="gchip on" data-g="cg-{k}">{K.esc(lbl)}</button>'
        for k, lbl in _GROUPS)

    shown = len(rows)
    if is_all:
        sub_lbl = f'All liquid equity · top <b>{shown}</b> by conviction (cap {limit})'
    elif is_watch:
        sub_lbl = f'Watchlist · <b>{shown}</b> stocks'
    else:
        mem = f'{n_members} members · ' if n_members else ''
        sub_lbl = f'<b>{K.esc(scope)}</b> · {mem}<b>{shown}</b> shown (liquid)'

    head = (
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        '<h1 class="uk-h1">Screen+</h1>'
        + K.badge(f"as of {str(sig_date)[:10] if sig_date else '—'} · precomputed")
        + '</div>'
        f'<div class="sec" style="margin-bottom:14px">{sub_lbl} · '
        'confluence = pillars aligned now (DVPT · MEP · RS · CPR · CCI). '
        'Toggle groups, sort any column, save a screen.</div>')

    controls = (
        '<div class="s2-bar">' + chips + sec_sel + '</div>'
        '<div class="s2-bar"><span class="s2-lbl">Groups</span>' + grp_chips + '</div>'
        '<div class="s2-bar">'
        '<input id="s2filter" placeholder="Filter rows… (symbol, sector, state)" />'
        '<span class="s2-lbl">Saved</span>'
        '<select id="s2load"><option value="">Load screen…</option></select>'
        '<button type="button" id="s2save" class="gchip">＋ Save current</button>'
        '<button type="button" id="s2del" class="gchip">Delete</button>'
        '<button type="button" id="s2csv" class="gchip">⬇ CSV</button>'
        '<span id="s2count" class="s2-lbl"></span></div>')

    table = (f'<div class="uk-tw" id="s2wrap" style="max-height:80vh">'
             f'<table class="uk-t s2" id="s2tbl">{thead}<tbody>{tbody}</tbody></table></div>')
    if not trs:
        table = ('<div class="uk-card">No rows for this scope on the latest date. '
                 'Try a broader scope, or this host may not have signals computed yet.</div>')

    body = _CSS + head + controls + table + _JS
    return HTMLResponse(K.shell("Screen+ · patearn", body,
                                active="screener", sub=_sub(), nav_html=_nav_html("screener")))


def _cpr_pat(p):
    if not p or p == "—":
        return '<span class="mut">—</span>'
    if p == "BULL_U":
        return K.pill("Bull-U", "up")
    if p == "BEAR_INVU":
        return K.pill("Bear-∩", "down")
    return f'<span class="mut">{K.esc(p)}</span>'


def _q(s):
    from urllib.parse import quote
    return quote(str(s))


_CSS = """<style>
.s2-bar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:9px}
.s2-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink-3);margin-left:6px}
.gchip{font:inherit;font-size:12px;cursor:pointer;border:1px solid var(--line-2);background:var(--bg-1);
  color:var(--ink-3);border-radius:8px;padding:5px 11px;transition:var(--t)}
.gchip:hover{border-color:var(--accent);color:var(--ink)}
.gchip.on{background:var(--accent-dim);color:var(--accent);border-color:transparent}
#s2filter,#secSel,#s2load{font:inherit;font-size:12.5px;background:var(--bg-1);color:var(--ink);
  border:1px solid var(--line-2);border-radius:8px;padding:6px 10px}
#s2filter{min-width:240px}
table.s2 th{cursor:pointer;user-select:none}
table.s2 th.gl{text-align:center;color:var(--ink-2);border-left:1px solid var(--line-2)}
table.s2 tr.grp th{background:var(--bg-3);font-size:10px}
table.s2 td.confl{font-weight:600}
table.s2 td.confl b{font-size:13px}
table.s2 td.confl .dots{display:inline-flex;gap:2px;margin-left:6px;vertical-align:middle}
table.s2 td.confl .cd{width:5px;height:5px;border-radius:50%;background:var(--line-2);display:inline-block}
table.s2 td.confl .cd.on{background:var(--accent-cy);box-shadow:0 0 5px var(--accent-cy)}
table.s2 td.confl.c4,table.s2 td.confl.c5{color:var(--accent-cy)}
table.s2 td.confl.c3{color:var(--accent)}
/* group hide classes (toggled on the wrapper) */
.h-conf .cg-conf,.h-pos .cg-pos,.h-mep .cg-mep,.h-rs .cg-rs,
.h-cpr .cg-cpr,.h-cci .cg-cci,.h-ctx .cg-ctx{display:none}
</style>"""

_JS = """<script>(function(){
var wrap=document.getElementById('s2wrap'), tbl=document.getElementById('s2tbl');
if(!tbl) return;
var KEY='s2_hidden_v1', SKEY='s2_screens_v1';
function getHidden(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}}}
function setHidden(h){localStorage.setItem(KEY,JSON.stringify(h))}
function applyHidden(){var h=getHidden();
  ['conf','pos','mep','rs','cpr','cci','ctx'].forEach(function(g){
    wrap.classList.toggle('h-'+g, !!h['cg-'+g]);
    var b=document.querySelector('.gchip[data-g="cg-'+g+'"]'); if(b) b.classList.toggle('on', !h['cg-'+g]);
  });}
document.querySelectorAll('.gchip[data-g]').forEach(function(b){
  b.addEventListener('click',function(){var g=b.getAttribute('data-g');var h=getHidden();
    h[g]=!h[g]; setHidden(h); applyHidden();});});
applyHidden();

// sort
var tb=tbl.tBodies[0];
function rowsArr(){return Array.prototype.slice.call(tb.rows);}
function val(td){if(!td)return '';var d=td.getAttribute('data-v');
  if(d!==null){var f=parseFloat(d); return isNaN(f)?d.toLowerCase():f;} return (td.textContent||'').trim().toLowerCase();}
var sortState={};
tbl.querySelectorAll('tr.col th').forEach(function(th,i){
  th.addEventListener('click',function(){
    var asc=!(sortState[i]); sortState={}; sortState[i]=asc;
    var rs=rowsArr();
    rs.sort(function(a,b){var x=val(a.cells[i]),y=val(b.cells[i]);
      if(x<y)return asc?-1:1; if(x>y)return asc?1:-1; return 0;});
    rs.forEach(function(r){tb.appendChild(r);});
  });});

// filter
var fi=document.getElementById('s2filter'), cnt=document.getElementById('s2count');
function recount(){var n=0;rowsArr().forEach(function(r){if(r.style.display!=='none')n++;});
  if(cnt)cnt.textContent=n+' rows';}
function doFilter(){var q=(fi.value||'').toLowerCase();
  rowsArr().forEach(function(r){r.style.display=(!q||r.textContent.toLowerCase().indexOf(q)>=0)?'':'none';});
  recount();}
if(fi)fi.addEventListener('input',doFilter);
recount();

// saved screens (scope + hidden groups)
var scope=new URLSearchParams(location.search).get('scope')||'Nifty 500';
function getScreens(){try{return JSON.parse(localStorage.getItem(SKEY)||'{}')}catch(e){return {}}}
function setScreens(s){localStorage.setItem(SKEY,JSON.stringify(s))}
var sel=document.getElementById('s2load');
function refreshSel(){if(!sel)return;var s=getScreens();
  sel.innerHTML='<option value="">Load screen…</option>'+Object.keys(s).map(function(k){
    return '<option value="'+k.replace(/"/g,'&quot;')+'">'+k+'</option>';}).join('');}
refreshSel();
var sv=document.getElementById('s2save');
if(sv)sv.addEventListener('click',function(){var name=prompt('Name this screen:');if(!name)return;
  var s=getScreens(); s[name]={scope:scope,hidden:getHidden()}; setScreens(s); refreshSel();
  if(sel)sel.value=name;});
if(sel)sel.addEventListener('change',function(){var v=sel.value;if(!v)return;var s=getScreens()[v];if(!s)return;
  setHidden(s.hidden||{}); location='/dash/screen2?scope='+encodeURIComponent(s.scope||'Nifty 500');});
var del=document.getElementById('s2del');
if(del)del.addEventListener('click',function(){var v=sel&&sel.value;if(!v){alert('Pick a screen to delete.');return;}
  var s=getScreens(); delete s[v]; setScreens(s); refreshSel();});

// CSV (visible columns + visible rows)
var csv=document.getElementById('s2csv');
if(csv)csv.addEventListener('click',function(){
  function visCols(){var out=[];tbl.querySelectorAll('tr.col th').forEach(function(th,i){
    if(th.offsetParent!==null)out.push(i);});return out;}
  var cols=visCols(), lines=[];
  var hdr=[];tbl.querySelectorAll('tr.col th').forEach(function(th,i){if(cols.indexOf(i)>=0)hdr.push('"'+(th.textContent||'').trim()+'"');});
  lines.push(hdr.join(','));
  rowsArr().forEach(function(r){if(r.style.display==='none')return;var c=[];
    cols.forEach(function(i){var td=r.cells[i];var d=td&&td.getAttribute('data-v');
      var t=(d!==null&&d!==undefined)?d:(td?td.textContent.trim():'');c.push('"'+String(t).replace(/"/g,'""')+'"');});
    lines.push(c.join(','));});
  var blob=new Blob([lines.join('\\n')],{type:'text/csv'});var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='screen2_'+scope.replace(/[^a-z0-9]+/gi,'_')+'.csv';a.click();});
})();</script>"""


def wire(app):
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/screen2" not in paths:
            app.include_router(router)
    except Exception as e:  # noqa: BLE001
        log.warning("screen2 wire skipped: %s", e)
    return app


def _selftest() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    r = c.get("/dash/screen2")
    assert r.status_code == 200, r.status_code
    assert "Screen+" in r.text and "s2tbl" in r.text
    assert "confluence" in r.text.lower()
    r2 = c.get("/dash/screen2?scope=all&limit=50")
    assert r2.status_code == 200
    print("screener_plus selftest OK — /dash/screen2 200, table + confluence render")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
