"""seasonal_screen_view.py — two read-only companions to the Seasonal tape lens (src/web/seasonal_view.py):

1. /dash/seasonal-screen — a This-Month RANKED base-rate view over the descriptive seasonal
   base-rates (seasonal_cells, axis='month'). D122 (2026-07-13, Ramana-authorized amendment of
   the gate-10 / no-cross-entity-ranking doctrine — see seasonal_tape.py docstring exception):
   this surface now defaults to a ranked "bullish/bearish this month" ordering (sort=hit,
   dir=desc, lean=hot), with explicit view-mode toggles for Bullish / Bearish / Lookup (A-Z).
   This remains a DISPLAY-layer amendment only — still descriptive, still NOT certified, NOT
   tradeable; kept honest by a hard, non-dismissable banner naming what this is (and is not),
   plus a rank column and lean arrow. Every row shows the Wilson 95% confidence interval
   prominently, so most rows visibly read "indistinguishable from chance" even while ranked —
   the point of the whole page. Frozen z-family hashes are unaffected (this file never touches
   _canon_spec/GATES/frozen_family_hash*).

   D122+ (2026-07-13) — ranking made confidence-aware instead of raw-percent (why: a raw hit-%
   rewards tiny samples — a lucky 3/3 outranks a proven 30/32 — and ties fell back to arbitrary
   DB row order). The default "hit" sort now ranks by the Wilson LOWER bound (bullish) / UPPER
   bound (bearish) of the hit-rate, with the mean residual (magnitude) as the tie-break; two new
   sortable dimensions accompany it: "Strength t" (the residual t-stat = mean/(sd/sqrt(n)), fusing
   size + consistency + sample from the per-year seasonal_stack) and a per-name month-rank column
   (where THIS month sits among the entity's own 12 by mean residual — #1 = its hottest month, so
   the reader can tell a name that is genuinely July-special from one that just drifts up all year).
   Still DISPLAY-only + descriptive; nothing here becomes a signal. Optional `index=<Name>` (scope=stock only) filters the
   screen to that index's current constituents (`stock_index_membership`, latest snapshot) — the
   index -> constituent-stocks drill reachable from an index/sector tape page's scan-CTA; guarded
   table-exists, silently ignored if the table or the named index isn't there.

2. /dash/seasonal-divergence — do two indices move together on the calendar, and where do they
   diverge? Reads seasonal_cells (scope='index', the cross-year SCRIPT) and seasonal_stack
   (scope='index', the current elapsed year) — both already-persisted bounded snapshots.
   0 certified cells is rendered as "descriptive / grey", NEVER as "no data" — certification and
   data-coverage are different things.

Both pages (plus /dash/seasonal-tape) share a top-of-page sub-nav strip (`_subnav()`, duplicated
per-module by design — no cross-module import) so the scan/tape/divergence trio is discoverable
from any one of the three.

FIX-2 (no web-process DB writes): both routes are READ-ONLY at request time — they only SELECT
from the bounded snapshot tables the nightly backfill already wrote; neither route ever computes
an on-demand entity in memory nor writes to hermes.db.

DESCRIPTIVE-ONLY FENCE: neither route reads seasonal_outlook, and neither ever renders a forward-
return/expected-move column, a '1M'-style horizon pill, or a traffic-light glyph (🟢/🟡/⚪) — those
stay exclusive to the full /dash/seasonal-tape page. Base rates over history, never a forecast.
"""
from __future__ import annotations

import math
import sqlite3
import statistics
from datetime import date
from urllib.parse import quote, urlencode

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.db import DB_PATH
from src.web.dashboard import _shell, _esc
from src.web import infographics as ifx
from src.automation.seasonal_tape import wilson_ci, BROAD_INDICES

router = APIRouter()

_DB_PATH = str(DB_PATH)                              # overridable in _selftest (read-only)

_MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
_FISCAL_ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
_CAL_ORDER = list(range(1, 13))
_CAP = 300                                           # row cap for the screen (never a top-N-by-hit slice)

_CSS = """
<style>
.ssc-banner{border-left:3px solid var(--warn);background:rgba(var(--warn-rgb),.07);border-radius:0 12px 12px 0;
  padding:12px 16px;margin:2px 0 14px;font-size:13px;color:var(--ink);line-height:1.55;max-width:1160px;}
.ssc-banner b{color:var(--ink);}
.ssc-banner .n{color:var(--ink-2);font-size:12px;margin-top:4px;display:block;}
.ssc-ctrl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:6px 0 6px;}
.ssc-ctrl a{padding:4px 12px;border:1px solid var(--line-2);border-radius:15px;color:var(--ink);font-size:12px;text-decoration:none;}
.ssc-ctrl a.on{background:#1f6feb;border-color:#1f6feb;color:#fff;font-weight:600;}
.ssc-ctrl .lbl{font-size:11px;color:var(--ink-3);margin-right:2px;}
.ssc-search{display:flex;gap:6px;align-items:center;margin:4px 0 10px;}
.ssc-search input{background:var(--bg-2);border:1px solid var(--line-2);border-radius:8px;color:var(--ink);
  font-size:12.5px;padding:5px 9px;min-width:180px;}
.ssc-search button{background:var(--bg-2);border:1px solid var(--line-2);border-radius:8px;color:var(--ink);
  font-size:12px;padding:5px 12px;cursor:pointer;}
.ssc-panel{background:var(--bg-1);border:1px solid var(--line);border-radius:13px;padding:15px 17px;margin:0 0 15px;}
.ssc-h{font-size:15px;font-weight:700;margin:0 0 3px;color:var(--ink);}
.ssc-h small{font-weight:400;color:var(--ink-3);font-size:12px;}
table.ssc-t{border-collapse:collapse;width:100%;font-size:12.5px;}
table.ssc-t th{text-align:left;color:var(--ink-3);font-weight:600;font-size:11px;padding:6px 10px;
  border-bottom:1px solid var(--line-2);white-space:nowrap;}
table.ssc-t th a{color:var(--ink-3);text-decoration:none;border-bottom:1px dotted var(--line-3);}
table.ssc-t th a:hover{color:var(--ink);}
table.ssc-t td{padding:6px 10px;border-bottom:1px solid var(--line-3);color:var(--ink);vertical-align:top;}
table.ssc-t td.sym a{color:var(--accent-cy);text-decoration:none;font-weight:600;}
table.ssc-t td.ci{color:var(--ink-2);font-variant-numeric:tabular-nums;font-size:11.5px;}
table.ssc-t td.z{font-variant-numeric:tabular-nums;}
table.ssc-t td.status{color:var(--ink-3);font-size:11.5px;}
table.ssc-t tr:hover td{background:var(--bg-2);}
.ssc-note{color:var(--ink-3);font-size:11.5px;margin-top:8px;}
.ssc-empty{color:var(--ink-2);font-size:13px;line-height:1.6;}
.ssc-subnav{margin:2px 0 12px;}
</style>
"""


def _subnav(active: str) -> str:
    """Shared sub-nav strip for the three seasonal surfaces (tape / this-month screen / index
    divergence) — rendered at the top of each page so the trio is discoverable from any one of
    them. Deliberately duplicated from seasonal_view.py's identical helper (no cross-module
    import, avoids an import cycle)."""
    links = (
        ("screen", "🔍 Scan this month", "/dash/seasonal-screen"),
        ("tape", "📅 Seasonal tape", "/dash/seasonal-tape"),
        ("divergence", "⚖ Index divergence", "/dash/seasonal-divergence"),
    )
    chips = "".join(
        f'<a class="{"on" if key == active else ""}" href="{href}">{lbl}</a>'
        for key, lbl, href in links)
    return f'<div class="ssc-ctrl ssc-subnav">{chips}</div>'


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    return bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def _index_members(index_name: str, con: sqlite3.Connection):
    """Current members (upper-cased symbols) + the canonical stored `index_name` spelling for a
    case-insensitive match against `stock_index_membership` at its latest snapshot_date — the
    index -> constituent-stocks drill from the tape page. Returns (None, None) when the table is
    absent or the index has no membership rows: an honest guard, the caller then ignores the
    filter entirely rather than fabricating an empty screen."""
    if not _has_table(con, "stock_index_membership"):
        return None, None
    rows = con.execute(
        "SELECT symbol, index_name FROM stock_index_membership WHERE UPPER(index_name)=UPPER(?) "
        "AND snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership "
        "WHERE UPPER(index_name)=UPPER(?))", (index_name, index_name)).fetchall()
    if not rows:
        return None, None
    return {r["symbol"].upper() for r in rows}, rows[0]["index_name"]


def _pearson(xs: list, ys: list) -> float | None:
    """Tiny pure-python Pearson r over paired (non-None) samples; None if <2 pairs or no variance."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    n = len(pairs)
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    sxx = sum((p[0] - mx) ** 2 for p in pairs)
    syy = sum((p[1] - my) ** 2 for p in pairs)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


# ── /dash/seasonal-screen ──────────────────────────────────────────────────────────
@router.get("/dash/seasonal-screen", response_class=HTMLResponse)
def dash_seasonal_screen(month: int = 0, scope: str = "stock", sort: str = "hit",
                          dir: str = "desc", min_years: int = 15, q: str = "",
                          lean: str = "hot", index: str = "") -> HTMLResponse:
    scope = scope if scope in ("index", "sector", "stock") else "stock"
    sort = sort if sort in ("sym", "hit", "z", "years", "strength") else "sym"
    dir = dir if dir in ("asc", "desc") else "asc"
    lean = lean if lean in ("all", "hot", "cold") else "all"
    m = month if month in _CAL_ORDER else date.today().month
    min_years = max(0, min_years or 0)
    index = (index or "").strip()
    body = [_CSS, ifx.readability_css()]
    try:
        con = _ro(_DB_PATH)
        try:
            if not _has_table(con, "seasonal_cells"):
                raise LookupError("no snapshot")
            rows = con.execute(
                "SELECT entity, script_z, n_years, hit_rate, colored FROM seasonal_cells "
                "WHERE scope=? AND axis='month' AND cell=?", (scope, m)).fetchall()
            # index -> constituent-stocks drill (D-seasonal-nav): only meaningful for scope=stock;
            # guarded table-exists — an absent table or an unmatched index silently no-ops the
            # filter rather than raising or emptying the whole screen.
            members, index_canon = (
                _index_members(index, con) if (index and scope == "stock") else (None, None))
            # month-rank context: where does THIS month sit among each entity's own 12 months by
            # mean residual? (answers "is this month even special for this name, or up all year")
            allm = con.execute(
                "SELECT entity, cell, script_z FROM seasonal_cells "
                "WHERE scope=? AND axis='month' AND script_z IS NOT NULL", (scope,)).fetchall()
            # strength = t-stat that the mean residual clears zero — needs the per-year stack for m
            stk = con.execute(
                "SELECT entity, mean_z FROM seasonal_stack "
                "WHERE scope=? AND axis='month' AND cell=?", (scope, m)).fetchall()
        finally:
            con.close()
        if not rows:
            raise LookupError("no coverage")

        # per-entity rank of month m among its own populated months (1 = this name's hottest month)
        by_ent: dict = {}
        for r in allm:
            by_ent.setdefault(r["entity"], []).append((r["cell"], r["script_z"]))
        mrank: dict = {}
        for ent, pairs in by_ent.items():
            tgt = next((sz for c, sz in pairs if c == m), None)
            if tgt is not None:
                rank = 1 + sum(1 for _c, sz in pairs if sz > tgt)
                mrank[ent] = (rank, len(pairs))

        # per-entity strength t = mean / (sd / sqrt(n)) over the per-year residuals (>=2 years, sd>0)
        st_vals: dict = {}
        for r in stk:
            if r["mean_z"] is not None:
                st_vals.setdefault(r["entity"], []).append(r["mean_z"])
        stt: dict = {}
        for ent, vv in st_vals.items():
            if len(vv) >= 2:
                sd = statistics.stdev(vv)
                if sd > 0:
                    stt[ent] = statistics.fmean(vv) / (sd / math.sqrt(len(vv)))

        qlow = (q or "").strip().upper()
        recs = []
        for r in rows:
            ent = r["entity"]
            if members is not None and ent.upper() not in members:
                continue
            if qlow and qlow not in ent.upper():
                continue
            ny = r["n_years"] or 0
            if ny < min_years:
                continue
            sz = r["script_z"]
            if lean == "hot" and not (sz is not None and sz > 0):
                continue
            if lean == "cold" and not (sz is not None and sz < 0):
                continue
            hr = r["hit_rate"]
            k = round((hr or 0.0) * ny) if (hr is not None and ny) else None
            lo, hi = wilson_ci(k, ny) if (k is not None and ny) else (None, None)
            recs.append({"entity": ent, "z": sz, "years": ny, "hit": hr, "k": k,
                         "lo": lo, "hi": hi, "colored": bool(r["colored"]),
                         "strength": stt.get(ent), "mrank": mrank.get(ent)})

        total = len(recs)
        # D122+ (2026-07-13): confidence-adjusted ranking. The headline "hit" sort ranks by the
        # Wilson LOWER bound (bullish, dir=desc) / UPPER bound (bearish, dir=asc) of the hit-rate —
        # so many years of a steady rate outrank a lucky 3/3 — with the mean residual (magnitude) as
        # the tie-break (answers "two names both 19/19, which is stronger?" -> the bigger mover).
        # "z" ranks by magnitude first (reliability as tie-break); "strength" by the residual t-stat.
        _big = float("inf")

        def _key(d):
            z = d["z"] if d["z"] is not None else 0.0
            lo = d["lo"] if d["lo"] is not None else 0.0
            hi = d["hi"] if d["hi"] is not None else 1.0
            if sort == "sym":
                return (d["entity"].upper(),)
            if sort == "years":
                return (d["years"], lo)
            if sort == "z":
                return (z, lo if dir == "desc" else hi)
            if sort == "strength":
                st = d["strength"]
                if st is None:
                    st = -_big if dir == "desc" else _big
                return (st, z)
            # sort == "hit": confidence-adjusted reliability, direction-aware magnitude tie-break
            return (lo, z) if dir == "desc" else (hi, z)
        recs.sort(key=_key, reverse=(dir == "desc"))
        shown = recs[:_CAP]

        month_name = _MONTH_ABBR.get(m, str(m))
        if members is not None:
            body.append(f'<h2 style="margin:0 0 2px">Stocks in {_esc(index_canon)} '
                        f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">ranked '
                        f'{_esc(month_name)} base-rates</small></h2>')
        else:
            body.append('<h2 style="margin:0 0 2px">This-month screen '
                        f'<small style="color:var(--ink-3);font-size:12px;font-weight:400">ranked '
                        f'{month_name} base-rates, {scope}-level, over history</small></h2>')
        body.append(_subnav("screen"))

        # D122 (2026-07-13, Ramana-authorized): ranked display-layer amendment — still honest,
        # still not certified/not tradeable, CI kept prominent.
        if members is not None:
            covered_syms = {r["entity"].upper() for r in rows if r["entity"].upper() in members}
            member_note = f' {len(covered_syms)} of {len(members)} {_esc(index_canon)} members covered.'
        else:
            member_note = ''
        body.append(
            '<div class="ssc-banner"><b>Ranked by historical BASE-RATE for this month '
            '(confidence-adjusted — Wilson lower bound, ties on the size of the move), the '
            'descriptive ordering you asked for (D122), NOT a certified signal and NOT '
            'tradeable. Check the 95% CI: when it straddles 50% the lean is noise, and most rows '
            'do. Ordering ≠ recommendation.</b>'
            f'<span class="n">{total} {scope} entities covered for {_esc(month_name)}'
            f'{" (min " + str(min_years) + "y history)" if min_years else ""}.{member_note}</span></div>')
        body.append(ifx.how_to_read_link())

        def _qs(**over) -> str:
            cur = {"month": m, "scope": scope, "sort": sort, "dir": dir,
                   "min_years": min_years, "q": q, "lean": lean, "index": index}
            cur.update(over)
            return "/dash/seasonal-screen?" + urlencode(cur)

        scope_tabs = "".join(
            f'<a class="{"on" if scope==s else ""}" href="{_qs(scope=s)}">{lbl}</a>'
            for s, lbl in (("stock", "Stock"), ("index", "Index"), ("sector", "Sector")))
        if index:
            clear_label = index_canon if members is not None else index
            scope_tabs += f'<a href="{_qs(index="")}">✕ clear index filter ({_esc(clear_label)})</a>'
        month_tabs = "".join(
            f'<a class="{"on" if mm==m else ""}" href="{_qs(month=mm)}">{_MONTH_ABBR[mm]}</a>'
            for mm in _CAL_ORDER)
        # D122: mode presets set (lean, sort, dir) together — Bullish/Bearish are ranked views,
        # Lookup is the original alphabetical non-ranked view. Active mode = exact (lean,sort,dir) match.
        _modes = (
            ("hot", "hit", "desc", "▲ Bullish (most-up)"),
            ("cold", "hit", "asc", "▼ Bearish (most-down)"),
            ("all", "sym", "asc", "Lookup (A–Z)"),
        )
        mode_tabs = "".join(
            f'<a class="{"on" if (lean, sort, dir) == (lv, sr, dr) else ""}" '
            f'href="{_qs(lean=lv, sort=sr, dir=dr)}">{lbl}</a>'
            for lv, sr, dr, lbl in _modes)
        body.append(f'<div class="ssc-ctrl"><span class="lbl">scope</span>{scope_tabs}</div>')
        body.append(f'<div class="ssc-ctrl"><span class="lbl">month</span>{month_tabs}</div>')
        body.append(f'<div class="ssc-ctrl"><span class="lbl">view</span>{mode_tabs}</div>')
        body.append(
            f'<form class="ssc-search" method="get" action="/dash/seasonal-screen">'
            f'<input type="hidden" name="month" value="{m}"/>'
            f'<input type="hidden" name="scope" value="{_esc(scope)}"/>'
            f'<input type="hidden" name="sort" value="{_esc(sort)}"/>'
            f'<input type="hidden" name="dir" value="{_esc(dir)}"/>'
            f'<input type="hidden" name="min_years" value="{min_years}"/>'
            f'<input type="hidden" name="lean" value="{_esc(lean)}"/>'
            f'<input type="text" name="q" placeholder="search symbol/entity…" value="{_esc(q)}"/>'
            f'<button type="submit">Search</button></form>')

        def _hdr(col: str, label: str) -> str:
            nd = "desc" if (sort == col and dir == "asc") else "asc"
            return f'<a href="{_qs(sort=col, dir=nd)}">{label}</a>'

        rows_html = ""
        for i, d in enumerate(shown, 1):
            link = (f'/dash/stock?sym={_esc(d["entity"])}#seasonal' if scope == "stock"
                    else f'/dash/seasonal-tape?scope={scope}&entity={quote(d["entity"])}')
            if d["k"] is not None and d["years"]:
                hit_txt = f'{d["k"]}/{d["years"]} ({100.0*d["hit"]:.0f}%)'
            else:
                hit_txt = "—"
            ci_txt = f'{d["lo"]*100:.0f}–{d["hi"]*100:.0f}%' if d["lo"] is not None else "—"
            z_txt = f'{d["z"]:+.2f}σ' if d["z"] is not None else "—"
            status = "certified" if d["colored"] else "grey / not gated"
            st = d["strength"]
            st_txt = f'{st:+.1f}' if st is not None else "—"
            mr = d["mrank"]
            if mr:
                mr_txt = f'#{mr[0]}/{mr[1]}'
                mr_style = ('color:var(--pos);font-weight:600' if mr[0] == 1
                            else 'color:var(--ink-2)')
            else:
                mr_txt, mr_style = "—", 'color:var(--ink-3)'
            z = d["z"]
            if z is not None and z > 0:
                lean_arrow = '<span style="color:var(--pos)">▲</span>'
            elif z is not None and z < 0:
                lean_arrow = '<span style="color:var(--neg)">▼</span>'
            else:
                lean_arrow = '<span style="color:var(--ink-3)">·</span>'
            rows_html += (
                '<tr>'
                f'<td class="rk" style="color:var(--ink-3);font-variant-numeric:tabular-nums">{i}</td>'
                f'<td class="sym">{lean_arrow} <a href="{_esc(link)}">{_esc(d["entity"])}</a></td>'
                f'<td>{_esc(hit_txt)}</td>'
                f'<td class="ci">{_esc(ci_txt)}</td>'
                f'<td class="z">{_esc(z_txt)}</td>'
                f'<td class="z">{_esc(st_txt)}</td>'
                f'<td class="z" style="{mr_style}">{_esc(mr_txt)}</td>'
                f'<td>{d["years"]}</td>'
                f'<td class="status">{_esc(status)}</td>'
                '</tr>')

        if rows_html:
            body.append(
                '<div class="ssc-panel"><div class="ssc-h">Base rates for '
                f'{_esc(month_name)} <small>— ranked by confidence-adjusted hit-rate (Wilson lower '
                'bound), ties on move size; column headers re-sort, not a recommendation</small></div>'
                + ifx.plain('Every row is a per-entity historical base-rate for this one calendar '
                            'month. Ranked by the <b>lower bound</b> of the 95% interval, not the raw '
                            '%, so many steady years outrank a lucky 3/3; ties break on the <b>mean '
                            'residual</b> (how big the move is). <b>Strength t</b> fuses size, '
                            'consistency and sample into one number (t &gt; 2 ≈ hard to call luck). '
                            'The <b>rank</b> column is where this month sits among the name’s own 12 '
                            '— #1 = its hottest month, not just hot in isolation. When the interval '
                            'straddles 50%, the lean is noise — most rows do.')
                + '<div style="overflow-x:auto"><table class="ssc-t"><thead><tr>'
                '<th>#</th>'
                f'<th>{_hdr("sym", "Symbol")}</th>'
                f'<th>{_hdr("hit", "Hist hit-rate k/n (P%)")}</th>'
                '<th>95% CI lo–hi%</th>'
                f'<th>{_hdr("z", "Mean residual")}</th>'
                f'<th>{_hdr("strength", "Strength t")}</th>'
                f'<th>{_esc(month_name)} rank</th>'
                f'<th>{_hdr("years", "Years")}</th>'
                '<th>Status</th>'
                '</tr></thead><tbody>' + rows_html + '</tbody></table></div>'
                + f'<div class="ssc-note">Showing 1–{len(shown)} of {total} total'
                  f'{" (narrow with the search box to see more)" if total > len(shown) else ""}.</div>'
                + '</div>')
        else:
            body.append('<div class="ssc-panel ssc-empty">No entity matches these filters for '
                        f'{_esc(month_name)}.</div>')
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>This-month screen</h2>' + _subnav("screen") +
            '<div class="ssc-empty">The seasonal snapshot '
            '(<code>seasonal_cells</code>) is not populated for this scope on this host. '
            'Run the seasonal tape backfill on the box. This surface is read-only and never '
            'fabricates data.</div>')
    return HTMLResponse(_shell("This-month screen · patearn", "".join(body), "seasonal-screen", "", wide=True))


# ── /dash/seasonal-divergence ──────────────────────────────────────────────────────
def _index_entities(db_path: str) -> tuple:
    """Populated index entities, ordered by the frozen BROAD_INDICES canon (falls back to
    alphabetical for anything outside it) — pair chips are never a ranking, just a stable list."""
    try:
        con = _ro(db_path)
    except sqlite3.OperationalError:
        return ()
    try:
        if not _has_table(con, "seasonal_cells"):
            return ()
        rows = con.execute(
            "SELECT DISTINCT entity FROM seasonal_cells WHERE scope='index' ORDER BY entity").fetchall()
        have = [r["entity"] for r in rows]
    finally:
        con.close()
    canon_order = {n.upper(): i for i, n in enumerate(BROAD_INDICES)}
    have.sort(key=lambda e: (canon_order.get(e.upper(), len(BROAD_INDICES)), e.upper()))
    return tuple(have)


def _index_month_script(entity: str, db_path: str) -> dict:
    """{month: (script_z, colored, n_years)} from seasonal_cells, scope='index', axis='month'."""
    con = _ro(db_path)
    try:
        rows = con.execute(
            "SELECT cell, script_z, colored, n_years FROM seasonal_cells "
            "WHERE scope='index' AND entity=? AND axis='month'", (entity,)).fetchall()
    finally:
        con.close()
    return {r["cell"]: (r["script_z"], bool(r["colored"]), r["n_years"]) for r in rows}


def _index_current_year(entity: str, db_path: str):
    """(year, {month: (mean_z, n_obs)}) for the LATEST year in seasonal_stack, scope='index'."""
    con = _ro(db_path)
    try:
        r = con.execute(
            "SELECT MAX(year) FROM seasonal_stack WHERE scope='index' AND entity=? AND axis='month'",
            (entity,)).fetchone()
        y = r[0] if r else None
        if y is None:
            return None, {}
        rows = con.execute(
            "SELECT cell, mean_z, n_obs FROM seasonal_stack "
            "WHERE scope='index' AND entity=? AND axis='month' AND year=?", (entity, y)).fetchall()
    finally:
        con.close()
    return y, {r["cell"]: (r["mean_z"], r["n_obs"]) for r in rows}


@router.get("/dash/seasonal-divergence", response_class=HTMLResponse)
def dash_seasonal_divergence(a: str = "Nifty 200", b: str = "Nifty 50", cal: str = "fy") -> HTMLResponse:
    order = _CAL_ORDER if cal == "cy" else _FISCAL_ORDER
    body = [_CSS, ifx.readability_css()]
    try:
        ents = _index_entities(_DB_PATH)
        if not ents:
            raise LookupError("no snapshot")
        emap = {e.upper(): e for e in ents}
        a_r = emap.get((a or "").strip().upper()) or ents[0]
        default_b = ents[1] if len(ents) > 1 else ents[0]
        b_r = emap.get((b or "").strip().upper()) or default_b
        if b_r == a_r and len(ents) > 1:
            b_r = next((e for e in ents if e != a_r), b_r)

        sa = _index_month_script(a_r, _DB_PATH)
        sb = _index_month_script(b_r, _DB_PATH)
        if not sa or not sb:
            raise LookupError("no coverage")

        body.append('<h2 style="margin:0 0 2px">Index divergence '
                    '<small style="color:var(--ink-3);font-size:12px;font-weight:400">do two '
                    'indices move together on the calendar, and where do they diverge?</small></h2>')
        body.append(_subnav("divergence"))
        body.append(ifx.bottom_line(
            f'Comparing <b>{_esc(a_r)}</b> vs <b>{_esc(b_r)}</b> across the calendar. This is '
            'descriptive co-movement history, <b>never</b> a signal or a trade.'))
        body.append(ifx.how_to_read_link())

        a_chips = "".join(
            f'<a class="{"on" if e==a_r else ""}" href="/dash/seasonal-divergence?a={quote(e)}&b={quote(b_r)}&cal={cal}">{_esc(e)}</a>'
            for e in ents)
        b_chips = "".join(
            f'<a class="{"on" if e==b_r else ""}" href="/dash/seasonal-divergence?a={quote(a_r)}&b={quote(e)}&cal={cal}">{_esc(e)}</a>'
            for e in ents)
        cal_tabs = "".join(
            f'<a class="{"on" if cal==c else ""}" href="/dash/seasonal-divergence?a={quote(a_r)}&b={quote(b_r)}&cal={c}">{lbl}</a>'
            for c, lbl in (("fy", "Apr–Mar"), ("cy", "Jan–Dec")))
        body.append(f'<div class="ssc-ctrl"><span class="lbl">A</span>{a_chips}</div>')
        body.append(f'<div class="ssc-ctrl"><span class="lbl">B</span>{b_chips}</div>')
        body.append(f'<div class="ssc-ctrl"><span class="lbl">calendar</span>{cal_tabs}</div>')

        col_labels = [_MONTH_ABBR[m] for m in order]
        z_a = [sa.get(m, (None, False, 0))[0] for m in order]
        z_b = [sb.get(m, (None, False, 0))[0] for m in order]
        pair_n = sum(1 for x, y in zip(z_a, z_b) if x is not None and y is not None)
        same_dir = sum(1 for x, y in zip(z_a, z_b) if x is not None and y is not None and (x > 0) == (y > 0))
        r = _pearson(z_a, z_b)
        r_txt = f'{r:+.2f}' if r is not None else '—'
        body.append(
            '<div class="ssc-panel"><div class="ssc-h">Do they move together? '
            f'<small>— {same_dir} of {pair_n} comparable months ran the same direction; '
            f'Pearson r = {r_txt}</small></div>'
            + ifx.plain('Two rows, one per index, one column per calendar month. Same colour in '
                        'both rows for a month = the two indices historically leaned the same way '
                        'that month.')
            + ifx.heat_grid([a_r, b_r], col_labels, [z_a, z_b], w=1060, cell_h=26, row_w=130,
                            signed=True, fmt=2, unit="σ", vmin=-2.5, vmax=2.5)
            + '</div>')

        deltas = [(x - y) if (x is not None and y is not None) else None for x, y in zip(z_a, z_b)]
        ribbon_cells = [(col_labels[i], deltas[i]) for i in range(len(order))]
        top3 = sorted(
            ((abs(d), col_labels[i], d) for i, d in enumerate(deltas) if d is not None),
            key=lambda t: t[0], reverse=True)[:3]
        words = ", ".join(f'{lbl} ({d:+.2f}σ)' for _absd, lbl, d in top3) if top3 else "none computable"
        body.append(
            '<div class="ssc-panel"><div class="ssc-h">Where A diverges from B '
            f'<small>— per-month script(A) − script(B); largest: {_esc(words)}</small></div>'
            + ifx.plain(f'Where the two entities\' historical calendar residuals pull apart the '
                        f'most. <b>{_esc(a_r)}</b> above baseline vs <b>{_esc(b_r)}</b> — a widening '
                        'bar is a bigger historical gap, not a forecast.')
            + ifx.heat_ribbon(ribbon_cells, w=1060, h=42)
            + '</div>')

        yr, cur = _index_current_year(a_r, _DB_PATH)
        cells3 = []
        for m in order:
            mz, n_obs = cur.get(m, (None, 0))
            script_z, _col, _ny = sa.get(m, (None, False, 0))
            if mz is not None and script_z is not None and n_obs >= 3:
                cells3.append((_MONTH_ABBR[m], mz - script_z))
            else:
                cells3.append((_MONTH_ABBR[m], None))
        yr_txt = str(yr) if yr else "this year"
        body.append(
            '<div class="ssc-panel"><div class="ssc-h">Where THIS year diverges from its usual path '
            f'({_esc(a_r)}) <small>— {_esc(yr_txt)} elapsed months vs the multi-year consensus</small></div>'
            + ifx.plain(f'{_esc(a_r)}’s residual so far this year, minus its own long-run '
                        'calendar consensus, month by month (only months with ≥3 comparable '
                        'observations are shown). YTD vs the multi-year consensus — a break '
                        'to ASK about, never a trade.')
            + ifx.heat_ribbon(cells3, w=1060, h=42)
            + '</div>')

        cert_a = sum(1 for m in order if sa.get(m, (None, False, 0))[1])
        cert_b = sum(1 for m in order if sb.get(m, (None, False, 0))[1])
        if cert_a == 0 and cert_b == 0:
            cert_note = ('Neither index has a certified calendar month right now — this stays '
                          'descriptive/grey throughout (0 certified is not the same as no data).')
        else:
            cert_note = (f'{cert_a} of 12 months certified for {_esc(a_r)}, {cert_b} for '
                        f'{_esc(b_r)} — the rest are descriptive/grey, not tradeable.')
        body.append(f'<div class="ssc-note">{cert_note}</div>')
    except Exception:  # noqa: BLE001 — honest empty state, never 500
        body.append(
            '<h2>Index divergence</h2>' + _subnav("divergence") +
            '<div class="ssc-empty">The seasonal snapshot '
            '(<code>seasonal_cells</code> / <code>seasonal_stack</code>, scope=index) is not '
            'populated on this host. This surface is read-only and never fabricates data.</div>')
    return HTMLResponse(_shell("Index divergence · patearn", "".join(body), "seasonal-divergence", "", wide=True))


def wire(app):
    """Idempotent self-mount (v2_surfaces._ROUTER_SPECS calls this)."""
    try:
        paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
        if "/dash/seasonal-screen" not in paths and "/dash/seasonal-divergence" not in paths:
            app.include_router(router)
    except Exception:  # noqa: BLE001
        pass
    return app


def _selftest() -> int:
    """Populate a temp snapshot via the real engine backfill (index + sector), point both routes
    at it, and assert: both routes 200, no forward-return/expected-move/'1M'/traffic-light token
    leaks, and the screen's default ordering is the D122 RANKED base-rate view (sort=hit desc,
    lean=hot) kept honest by the amended banner + Wilson CI, never a bare unlabeled leaderboard."""
    import os
    import re
    import tempfile
    import random
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.automation import seasonal_tape as ST

    global _DB_PATH
    tmp = os.path.join(tempfile.gettempdir(), "seasonal_screen_view_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("CREATE TABLE index_rows(index_name TEXT, trade_date TEXT, close_value REAL);")
    rng = random.Random(7)
    mlvl, alvl, slvl = 1000.0, 900.0, 500.0
    for y in range(2001, 2026):
        for mo in range(1, 13):
            for dd in range(1, 21):
                try:
                    d = date(y, mo, dd)
                except ValueError:
                    continue
                if d.weekday() >= 5:
                    continue
                mr = rng.gauss(0.0004, 0.010)
                ar = 0.9 * mr + rng.gauss(0.0, 0.006) + (0.003 if mo == 3 else 0.0)
                sr = 1.1 * mr + rng.gauss(0.0, 0.008) + (0.004 if mo in (10, 11) else 0.0)
                mlvl *= (1 + mr); alvl *= (1 + ar); slvl *= (1 + sr)
                con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty 500", d.isoformat(), mlvl))
                con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty 200", d.isoformat(), alvl))
                con.execute("INSERT INTO index_rows VALUES (?,?,?)", ("Nifty Auto", d.isoformat(), slvl))
    con.commit(); con.close()
    ST.backfill(tmp, tmp, scope="all", limit=None)

    saved = _DB_PATH
    _DB_PATH = tmp
    try:
        app = FastAPI(); app.include_router(router); c = TestClient(app)

        # -- screen: index scope, NEW default (D122: ranked by hit-rate desc, lean=hot) -
        # month=6 is chosen because BOTH synthetic index entities carry a positive script_z
        # there (Nifty 500 68% hit, Nifty 200 50% hit) so both survive the lean=hot filter
        # and the hit-rate-desc ranking is directly observable.
        r1 = c.get("/dash/seasonal-screen?scope=index&month=6")
        assert r1.status_code == 200 and "This-month screen" in r1.text, r1.status_code
        assert "Ranked by historical BASE-RATE" in r1.text and "D122" in r1.text, \
            "D122 ranked-doctrine banner missing"
        assert "NOT a certified signal" in r1.text and "NOT tradeable" in r1.text, \
            "honest banner (not certified / not tradeable) missing"
        assert "95% CI" in r1.text, "Wilson CI column missing"
        i500, i200 = r1.text.find("Nifty 500"), r1.text.find("Nifty 200")
        assert i500 != -1 and i200 != -1 and i500 < i200, \
            "default screen order must now be RANKED by hit-rate desc (D122): Nifty 500 " \
            "(68% hit) before Nifty 200 (50% hit), never alphabetical-only"

        # -- D122+ confidence-adjusted ranking + the two new dimensions -------------------
        assert "Strength t" in r1.text, "Strength (t-stat) column missing"
        assert "Jun rank" in r1.text, "per-name month-rank column missing (month=6 -> Jun)"
        assert "confidence-adjusted" in r1.text and "lower bound" in r1.text.lower(), \
            "confidence-adjusted (Wilson lower-bound) ranking not disclosed on the page"
        r1s = c.get("/dash/seasonal-screen?scope=index&month=6&sort=strength&dir=desc&lean=hot")
        assert r1s.status_code == 200 and "Strength t" in r1s.text, "sort=strength failed"

        # -- screen: sector scope + current-month default (month=0); lean=all so the assertion
        # below is not itself coupled to the sign of Nifty Auto's script_z on any given run day --
        r2 = c.get("/dash/seasonal-screen?scope=sector&lean=all")
        assert r2.status_code == 200 and "Nifty Auto" in r2.text, "sector scope failed"

        # -- screen: optional lean/sort convenience must not error ----------------------
        r3 = c.get("/dash/seasonal-screen?scope=index&lean=hot&sort=hit&dir=desc")
        assert r3.status_code == 200, "lean/sort convenience failed"

        # -- screen: honest-empty for an uncovered scope (no stock snapshot in tmp db) --
        r4 = c.get("/dash/seasonal-screen?scope=stock")
        assert r4.status_code == 200, "honest-empty path must still 200"

        # -- screen: index -> constituent-stocks drill (D-seasonal-nav) — plant 3 stock-scope
        # seasonal_cells rows (month=6) + a stock_index_membership table binding 2 of them to
        # "Nifty 50"; ZIDXC carries the HIGHEST hit-rate but is NOT a member, so its exclusion
        # (not its ranking) proves the filter actually filters. Symbols are deliberately unique
        # (not "MEMA"/"OUTC" etc.) to avoid an accidental substring collision with unrelated page
        # chrome text (e.g. "MEMB" inside "REMEMBER").
        con3 = sqlite3.connect(tmp)
        con3.executescript(
            "CREATE TABLE IF NOT EXISTS stock_index_membership("
            "symbol TEXT, index_name TEXT, snapshot_date TEXT, weight_pct REAL);")
        for sym, z, hr in (("ZIDXA", 0.5, 0.7), ("ZIDXB", 0.3, 0.5), ("ZIDXC", 0.4, 0.9)):
            con3.execute(
                "INSERT OR REPLACE INTO seasonal_cells (scope,entity,axis,cell,script_z,n_years,"
                "hit_rate,conf,colored,signed,emp_p_block,emp_p_phase,null_p95,sign_stable,"
                "fdr_pass,mechanism,pledged_sign,gate_flags) VALUES "
                "('stock',?,'month',6,?,20,?,0.1,0,0,0.5,0.5,0.5,0,0,NULL,NULL,'OK')", (sym, z, hr))
        con3.executemany(
            "INSERT INTO stock_index_membership (symbol, index_name, snapshot_date, weight_pct) "
            "VALUES (?,?,?,?)",
            [("ZIDXA", "Nifty 50", "2026-01-01", None), ("ZIDXB", "Nifty 50", "2026-01-01", None),
             ("ZIDXC", "Nifty Next 50", "2026-01-01", None)])
        con3.commit(); con3.close()

        r7 = c.get("/dash/seasonal-screen?scope=stock&month=6&index=Nifty 50")
        assert r7.status_code == 200, r7.status_code
        assert "Stocks in Nifty 50" in r7.text, "index-named header missing"
        assert "ZIDXA" in r7.text and "ZIDXB" in r7.text, "index members missing from the screen"
        assert "ZIDXC" not in r7.text, "non-member must be excluded by the index filter"
        assert "2 of 2 Nifty 50 members covered" in r7.text, "member-coverage count missing"
        assert "clear index filter" in r7.text, "clear-filter chip missing"
        # still the D122 ranked default (sort=hit desc) even WITH the index filter applied — no
        # explicit sort/lean/dir passed in this request.
        im_a, im_b = r7.text.find("ZIDXA"), r7.text.find("ZIDXB")
        assert im_a != -1 and im_b != -1 and im_a < im_b, \
            "index-filtered screen must still default to ranked-by-hit-rate (ZIDXA 70% before ZIDXB 50%)"

        # an index that isn't in stock_index_membership -> guarded, filter silently ignored
        # (never a 500, never an empty screen for a typo'd/unknown index name)
        r8 = c.get("/dash/seasonal-screen?scope=stock&month=6&index=NoSuchIndex")
        assert r8.status_code == 200 and "ZIDXC" in r8.text, \
            "unmatched index must silently ignore the filter, not empty the screen"
        assert "This-month screen" in r8.text, "ignored-filter screen keeps the plain header"

        # -- D122+ tie-break: at the SAME hit-rate, the bigger mean residual (mover) must win —
        # the user's exact "two names both 18/19, which is stronger?" case. ZTIEA/ZTIEB are both
        # 18/19 (identical Wilson bounds) but ZTIEB moves +0.5σ vs ZTIEA +0.2σ, so ZTIEB ranks up.
        con4 = sqlite3.connect(tmp)
        for sym, z, hr in (("ZTIEA", 0.2, 0.95), ("ZTIEB", 0.5, 0.95)):
            con4.execute(
                "INSERT OR REPLACE INTO seasonal_cells (scope,entity,axis,cell,script_z,n_years,"
                "hit_rate,conf,colored,signed,emp_p_block,emp_p_phase,null_p95,sign_stable,"
                "fdr_pass,mechanism,pledged_sign,gate_flags) VALUES "
                "('stock',?,'month',6,?,19,?,0.1,0,0,0.5,0.5,0.5,0,0,NULL,NULL,'OK')", (sym, z, hr))
        con4.commit(); con4.close()
        r9 = c.get("/dash/seasonal-screen?scope=stock&month=6&sort=hit&dir=desc&lean=hot&q=ZTIE")
        assert r9.status_code == 200
        t_b, t_a = r9.text.find("ZTIEB"), r9.text.find("ZTIEA")
        assert t_b != -1 and t_a != -1 and t_b < t_a, \
            "tie-break failed: at equal hit-rate (both 18/19) the bigger mean residual " \
            "(ZTIEB +0.5σ) must rank above the smaller (ZTIEA +0.2σ)"

        # -- divergence: two populated broad indices -------------------------------------
        r5 = c.get("/dash/seasonal-divergence?a=Nifty 500&b=Nifty 200")
        assert r5.status_code == 200 and "Index divergence" in r5.text, r5.status_code
        assert "Do they move together" in r5.text and "Pearson r" in r5.text
        assert "Where A diverges from B" in r5.text
        assert "Where THIS year diverges" in r5.text

        # -- honest-empty for divergence with no index snapshot --------------------------
        saved2 = _DB_PATH
        _DB_PATH = os.path.join(tempfile.gettempdir(), "seasonal_screen_view_selftest_empty.db")
        sqlite3.connect(_DB_PATH).close()
        r6 = c.get("/dash/seasonal-divergence")
        assert r6.status_code == 200, "divergence honest-empty must still 200"
        os.remove(_DB_PATH)
        _DB_PATH = saved2

        # -- D-seasonal-nav: sub-nav trio (all 3 links) renders on the screen AND divergence pages
        for text in (r1.text, r7.text, r5.text):
            assert ("🔍 Scan this month" in text and "📅 Seasonal tape" in text
                    and "⚖ Index divergence" in text), "seasonal sub-nav trio missing"

        # -- DESCRIPTIVE-ONLY FENCE: no forward-return / expected-move / horizon-pill /
        # traffic-light leaks on ANY route/state, including the new index-filtered ones.
        for text in (r1.text, r1s.text, r2.text, r3.text, r5.text, r7.text, r8.text, r9.text):
            low = text.lower()
            for token in ("expected move", "forward return"):
                assert token not in low, f"leaked forbidden token {token!r}"
            for token in ("1M", "\U0001F7E2", "\U0001F7E1", "⚪"):
                assert token not in text, f"leaked forbidden token {token!r}"

        print("seasonal_screen_view selftest OK — screen defaults to CONFIDENCE-ADJUSTED ranked "
              "base-rate view (D122+: Wilson lower-bound, ties on mean residual) with Strength-t "
              "sort + per-name month-rank columns; equal-hit-rate tie-break resolves by mover size; "
              "honest banner + Wilson CI, both routes 200 + honest-empty, no forward-return/"
              "expected-move/1M/traffic-light leaks; sub-nav trio + index->constituent-stocks drill "
              "(filter/header/coverage/clear-chip) wired")
    finally:
        _DB_PATH = saved
        if os.path.exists(tmp):
            os.remove(tmp)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
