"""/dash/wolfe/trades — the Wolfe "Open trades — remaining ROI" filterable view.

A NEW additive surface (docs/wolfe-open-trades-PLAN.md, 2026-07-12). The fresh
scanner (/dash/wolfe/scan) is age-capped at ≤15 bars, so it shows only the just-
printed calls. This view surfaces EVERY OPEN winner-profile trade — point 5 printed,
EPA (1-4) target not yet reached, ANY age — ranked by REMAINING ROI from the current
price (run% / risk% / R:R), with 9 top-of-page filters that the persist/script honor
too (filtering is a server-side WHERE over the nightly snapshot, never front-end only).

Descriptive-only. Wolfe carries no buy/sell signal. The validated +edge is measured on
FRESH ≤15d winner-profile entries; older open trades have run left but no validated
entry-edge → they are BADGED ("open · judge the run"), never hidden. Q = structural
strength; ✓edge = the tradeable filter — they differ on purpose.

Additive: this module never touches detection, §A geometry, §B scoring, winner_scan,
the crossing rule, or point-4. Its router is included onto wolfe_view's already-mounted
router (durable-include pattern) so it needs no v2_surfaces / lens_registry edit.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.core.db import get_conn
from src.automation import wolfe

try:
    from src.web.dashboard import _shell, _esc, _q
except Exception:  # pragma: no cover
    from urllib.parse import quote_plus

    def _esc(s):
        return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _q(s):
        return quote_plus(str(s) if s is not None else "")

    def _shell(title, body, active, latest_date="", wide=False):
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{title}</title></head><body>{body}</body></html>")

router = APIRouter()

_UP, _DN = "var(--up)", "var(--down)"

# (value, label) option lists for the 9 filter dropdowns. `value` = the query param.
_SIZE_OPTS = [("all", "All sizes"), ("N50", "Nifty 50"), ("Next50", "Next 50"),
              ("Mid150", "Midcap 150"), ("Small250", "Smallcap 250"),
              ("Micro250", "Microcap 250")]
_DIR_OPTS = [("all", "Both sides"), ("bull", "Bull only"), ("bear", "Bear only")]
_AGE_OPTS = [("all", "Any age"), ("15", "≤ 15d (✓ validated)"), ("30", "≤ 30d"),
             ("60", "≤ 60d"), ("120", "≤ 120d")]
_Q_OPTS = [("any", "Any strength"), ("15", "Q ≥ 15"), ("18", "Q ≥ 18"),
           ("21", "Q ≥ 21"), ("top20", "Top 20 only")]
_ROOM_OPTS = [("any", "Any room"), ("10", "≥ 10% left"), ("20", "≥ 20%"),
              ("30", "≥ 30%"), ("50", "≥ 50%")]
_STATUS_OPTS = [("all", "In zone + watching"), ("in", "Actionable now (in zone)"),
                ("watch", "Watching")]
_LIQ_OPTS = [("any", "Any liquidity"), ("1", "≥ ₹1 cr traded"), ("5", "≥ ₹5 cr"),
             ("25", "≥ ₹25 cr"), ("100", "≥ ₹100 cr")]
_RR_OPTS = [("any", "Any R:R"), ("1.5", "R:R ≥ 1.5"), ("2", "R:R ≥ 2"), ("3", "R:R ≥ 3")]

_FILTER_KEYS = ("size", "sector", "dir", "maxage", "minq", "minroom",
                "status", "minliq", "minrr")


def _sector_opts(conn):
    """Sector dropdown = the live company_tags vocabulary (multi-label, approved)."""
    opts = [("all", "All sectors")]
    try:
        for tag, c in conn.execute(
                "SELECT tag, COUNT(DISTINCT symbol) c FROM company_tags "
                "WHERE approved=1 GROUP BY tag ORDER BY tag").fetchall():
            opts.append((tag, f"{tag} ({c})"))
    except Exception:
        pass
    return opts


def _sel(name, opts, cur, extra=""):
    """A GET <select> that auto-submits its form on change."""
    cur = (cur or opts[0][0])
    body = "".join(
        f'<option value="{_esc(v)}"{" selected" if str(v) == str(cur) else ""}>{_esc(lbl)}</option>'
        for v, lbl in opts)
    return (f'<label class="wtf"><span>{_esc(extra)}</span>'
            f'<select name="{name}" onchange="this.form.submit()">{body}</select></label>')


def _qs(params, **override):
    """Build a querystring from the current filter params + overrides (for sort/cross links)."""
    p = dict(params)
    p.update(override)
    keep = [(k, v) for k, v in p.items() if v not in (None, "")]
    return "&amp;".join(f"{k}={_q(v)}" for k, v in keep)


def _num(v):
    return f"{v:,.1f}" if (isinstance(v, (int, float)) and abs(v) >= 100) else (
        f"{v:.2f}" if isinstance(v, (int, float)) else "—")


def _liq_cell(r):
    tv, dp = r.get("tv_cr"), r.get("deliv_pct")
    if tv is None:
        return '<span style="color:var(--ink-3)" title="no liquidity data">—</span>'
    thin = tv < 5.0                                    # the systematized TIRUPATIFL lesson
    col = "var(--down)" if thin else "var(--ink-2)"
    dps = f' · {dp:.0f}%del' if dp is not None else ""
    warn = ' ⚠' if thin else ""
    return (f'<span style="color:{col}" title="traded value today (₹ crore) · delivery %'
            f'{" — thin/illiquid, gap-prone" if thin else ""}">₹{tv:,.1f} cr{dps}{warn}</span>')


@router.get("/dash/wolfe/trades", response_class=HTMLResponse)
def wolfe_trades(universe: str = Query("nifty500", max_length=24),
                 size: str = Query("", max_length=12),
                 sector: str = Query("", max_length=40),
                 dir: str = Query("", max_length=8),
                 maxage: str = Query("", max_length=6),
                 minq: str = Query("", max_length=8),
                 minroom: str = Query("", max_length=6),
                 status: str = Query("", max_length=8),
                 minliq: str = Query("", max_length=8),
                 minrr: str = Query("", max_length=6),
                 sort: str = Query("run", max_length=6)):
    """Open winner-profile trades, ranked by remaining ROI, with 9 server-side filters.
    Reads the nightly wolfe_open_signals snapshot (instant); a live open_scan over the
    universe is minutes-long, so when the snapshot is absent we show a build notice."""
    uni = universe or "nifty500"
    params = {"universe": uni, "size": size, "sector": sector, "dir": dir,
              "maxage": maxage, "minq": minq, "minroom": minroom, "status": status,
              "minliq": minliq, "minrr": minrr, "sort": sort}
    with get_conn() as conn:
        snap = wolfe.latest_open_scan(conn, universe=uni)
        sector_opts = _sector_opts(conn)

    if not snap:
        note = ('<h2>Open trades — remaining ROI</h2>'
                '<div class="sub" style="margin:10px 0">The nightly open-trades snapshot '
                'has not been built yet for this universe. It rides the '
                '<code>hermes-wolfe-scan</code> timer (<code>python -m src.automation.wolfe '
                '--persist-open</code>) — check back after the next nightly run, or open the '
                '<a href="/dash/wolfe/scan" style="color:#58a6ff">fresh winner-profile scanner ›</a> '
                'in the meantime.</div>')
        return HTMLResponse(_shell("Open trades — Wolfe", note, "wolfe", wide=True))

    all_rows = snap["rows"]
    total_open = len(all_rows)
    rows = wolfe.filter_open_rows(
        all_rows, size=size, sector=sector, direction=dir, maxage=maxage,
        minq=minq, minroom=minroom, status=status, minliq=minliq, minrr=minrr)
    rows = wolfe.sort_open_rows(rows, sort)
    nin = sum(1 for r in rows if r.get("in_zone") and not r.get("invalid"))  # actionable = in zone, not blown

    # ── filter bar (one GET form; each select auto-submits) ──────────────────
    fbar = (
        f'<form method="get" action="/dash/wolfe/trades" class="wtbar">'
        f'<input type="hidden" name="universe" value="{_esc(uni)}"/>'
        f'<input type="hidden" name="sort" value="{_esc(sort)}"/>'
        + _sel("size", _SIZE_OPTS, size, "Size")
        + _sel("sector", sector_opts, sector, "Sector")
        + _sel("dir", _DIR_OPTS, dir, "Direction")
        + _sel("maxage", _AGE_OPTS, maxage, "Max age")
        + _sel("minq", _Q_OPTS, minq, "Strength")
        + _sel("minroom", _ROOM_OPTS, minroom, "Room to EPA")
        + _sel("status", _STATUS_OPTS, status, "Status")
        + _sel("minliq", _LIQ_OPTS, minliq, "Min liquidity")
        + _sel("minrr", _RR_OPTS, minrr, "Min R:R")
        + f'<a class="wtclear" href="/dash/wolfe/trades?universe={_q(uni)}">clear</a>'
        + '</form>')

    # ── sort links (carry the current filters) ───────────────────────────────
    def _slink(key, label):
        on = ' style="color:#eaf1f9;font-weight:600"' if sort == key else ' style="color:#58a6ff"'
        return f'<a href="/dash/wolfe/trades?{_qs(params, sort=key)}"{on}>{label}</a>'
    sortbar = ('<b>Sort:</b> ' + _slink("run", "most room (run%)") + ' · '
               + _slink("rr", "best R:R") + ' · ' + _slink("q", "strongest (Q)")
               + ' · ' + _slink("age", "freshest"))

    # ── rows ─────────────────────────────────────────────────────────────────
    trs = []
    for r in rows:
        bull = r["dir"] == "BULL"
        col = _UP if bull else _DN
        edge = (r.get("age") is not None and r["age"] <= 15)
        badge = ('<span style="background:#1f6feb;color:#fff;font-size:10px;padding:0 5px;'
                 'border-radius:4px" title="fresh ≤15d — the OOS-validated winner-profile entry-edge">★ edge</span>'
                 if edge else
                 '<span style="color:var(--ink-3);font-size:10.5px" title="older open trade — run '
                 'still left, but no validated entry-edge; judge the run">open</span>')
        if r.get("invalid"):
            status_cell = '<span style="color:var(--down)" title="price has fallen through the stop — setup broken">✗ stop</span>'
        elif r.get("in_zone"):
            status_cell = '<span style="color:var(--up);font-weight:700" title="price in the entry zone now">● IN</span>'
        else:
            status_cell = '<span style="color:var(--ink-3)" title="not yet in the entry zone">watch</span>'
        tags = ", ".join(r.get("tags") or []) or (r.get("psector") or "—")
        tags_short = tags if len(tags) <= 26 else tags[:24] + "…"
        rr = r.get("rr")
        rr_s = (f'<b style="color:{col}">{rr:.2f}</b>' if rr is not None
                else '<span style="color:var(--ink-3)">—</span>')
        run_s = (f'{r["run"]:+.1f}%' if r.get("run") is not None else "—")
        risk_s = (f'{r["risk"]:.1f}%' if r.get("risk") is not None else "—")
        rs = r.get("rs")
        rs_s = f'{rs:.0f}' if isinstance(rs, (int, float)) else "—"
        dim = ' opacity:0.6;' if r.get("invalid") else ''
        trs.append(
            # _q percent-encodes the symbol → safe inside the single-quoted JS string.
            f'<tr onclick="location.href=\'/dash/wolfe?sym={_q(r["sym"])}&pick=winner\'" '
            f'style="cursor:pointer;border-top:1px solid var(--line-2);{dim}" '
            f'onmouseover="this.style.background=\'#1c2430\'" onmouseout="this.style.background=\'transparent\'">'
            f'<td style="padding:6px 10px"><b style="color:{col}">{_esc(r["sym"])}</b></td>'
            f'<td style="color:{col};font-weight:600">{r["dir"]}</td>'
            f'<td style="color:var(--ink-2)" title="{_esc(tags)}">{_esc(tags_short)}</td>'
            f'<td style="color:var(--ink-3)">{_esc(r.get("size") or "—")}</td>'
            f'<td>{_liq_cell(r)}</td>'
            f'<td>{status_cell}</td>'
            f'<td>{_num(r["cmp"])}</td>'
            f'<td style="color:var(--ink-2)">{_num(r["zlo"])}–{_num(r["zhi"])}</td>'
            f'<td style="color:var(--down)">{_num(r["sl"])}</td>'
            f'<td>{_num(r["t1"]) if r.get("t1") else "—"}</td>'
            f'<td style="color:var(--up)">{_num(r["epa"])}</td>'
            f'<td style="color:{_UP};font-weight:600">{run_s}</td>'
            f'<td style="color:var(--ink-2)">{risk_s}</td>'
            f'<td style="text-align:center">{rr_s}</td>'
            f'<td style="text-align:center"><b style="color:{col}">{_num_q(r.get("Q"))}</b></td>'
            f'<td style="text-align:center;color:var(--ink-2)">{rs_s}</td>'
            f'<td style="color:var(--ink-3)" title="setup: point 5 on {_esc(r.get("p5date") or "")}">{r.get("age")}d</td>'
            f'<td style="text-align:center">{badge}</td></tr>')
    if not rows:
        trs = ['<tr><td colspan="18" style="padding:14px;color:var(--ink-2)">No open trades match '
               'these filters — loosen a dropdown or <a href="/dash/wolfe/trades?universe='
               + _q(uni) + '" style="color:#58a6ff">clear all</a>.</td></tr>']

    head = ("symbol", "dir", "sector", "size", "liquidity / deliv", "status", "CMP",
            "entry zone", "stop", "T1", "EPA", "run %", "risk %", "R:R",
            f"Q/{wolfe._QUALITY_MAX}", "RS", "age", "")

    sd = _esc(snap.get("scan_date") or "—")
    ca = _esc((snap.get("computed_at") or "")[:16])
    body = (
        _CSS
        + '<h2>Open trades <span style="color:var(--ink-2);font-size:15px;font-weight:400">— remaining ROI, ranked</span></h2>'
        '<div class="sub" style="margin-bottom:8px">Every <b>OPEN</b> winner-profile Wolfe setup — '
        'point 5 printed, the EPA (1-4) target <b>not yet reached</b>, so run is still left — at <b>any age</b>, '
        'ranked by how much room is left from the current price. '
        '<b style="color:var(--up)">run%</b> = move to the EPA target from CMP · '
        '<b>risk%</b> = distance to the stop · <b>R:R</b> = reward:risk if you enter now. '
        '<span style="color:#1f6feb;font-weight:600">★ edge</span> = fresh ≤15d (the OOS-validated entry-edge); '
        '<span style="color:var(--ink-3)">open</span> = older, run left but <i>no validated entry-edge — judge the run</i>. '
        'Q = structural strength (the ★edge filter differs on purpose). '
        '<i>Descriptive — not a buy/sell signal.</i></div>'
        f'<div class="sub" style="margin-bottom:8px;font-size:12px">{sortbar}</div>'
        + fbar
        + f'<div style="color:var(--ink-2);font-size:13px;margin:8px 0 10px">{_esc(uni)} · '
          f'as-of <b>{sd}</b> <span style="color:var(--ink-3)">(nightly snapshot'
          f'{(" · computed " + ca) if ca else ""})</span> · '
          f'<b>{len(rows)} of {total_open} open trades</b> · {nin} actionable now'
          ' &nbsp;|&nbsp; <a href="/dash/wolfe/scan?universe=' + _q(uni) + '" style="color:#58a6ff">fresh scanner ›</a>'
          '</div>'
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<thead><tr style="color:var(--ink-2);text-align:left">'
        + "".join(f'<th style="padding:6px 10px;white-space:nowrap">{h}</th>' for h in head)
        + '</tr></thead><tbody>' + "".join(trs) + '</tbody></table></div>')
    return HTMLResponse(_shell("Open trades — Wolfe", body, "wolfe", wide=True))


def _num_q(v):
    """Q may be a float (§B total) — show a clean integer-ish value."""
    if v is None:
        return ""
    try:
        return f"{float(v):g}"
    except Exception:
        return _esc(v)


_CSS = """<style>
.wtbar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:flex-end;margin:6px 0 2px;
  padding:10px;background:#0e141c;border:1px solid #1c2937;border-radius:8px}
.wtf{display:flex;flex-direction:column;gap:3px;font-size:11px;color:#7d93a8}
.wtf span{letter-spacing:.03em}
.wtf select{font:inherit;font-size:12.5px;background:#0b0f17;color:#cdd9e5;
  border:1px solid #27384a;border-radius:6px;padding:5px 7px;min-width:120px}
.wtf select:hover{border-color:#4d9dff}
.wtclear{align-self:flex-end;font-size:12px;color:#7d93a8;text-decoration:none;
  padding:6px 8px;border:1px solid #27384a;border-radius:6px}
.wtclear:hover{color:#eaf1f9;border-color:#4d9dff}
</style>"""
