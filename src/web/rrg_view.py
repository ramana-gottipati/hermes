"""/dash/rrg — multi-sector Relative Rotation Graph + RS-depth table.

The read surface for the RS-deepening work (session 20). ISOLATED on purpose:
a self-contained APIRouter in its OWN module so it mounts via one line in
main.py WITHOUT editing the (parallel-session-held) dashboard.py. It reuses the
shared page shell (`_shell`) from dashboard.py for chrome + CSS consistency —
that helper is import-safe (no side effects, no circular import).

Data source: the new ``rs_extras`` / ``capture_signals`` tables (rrg.py /
capture.py). If the nightly job hasn't populated them yet, it falls back to the
on-read ``current_all()`` computed straight from ``ratio_rows`` / ``index_rows``
— so the page works immediately, empty-state only when there is no index data
at all. No LLM, no schema change to existing tables.

When dashboard.py is free, the same picture/helpers get woven into the existing
surfaces (Home / sectors / markets / ratio) per the design doc; this page is the
standalone home for the rotation map either way.
"""

from __future__ import annotations

import html
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.automation import capture, rrg
from src.core.db import get_conn
from src.web.dashboard import _shell   # chrome + CSS (import-safe; see investigation)

# Curated economic-sector whitelist (same set /dash/sectors & /dash/rs use), so the
# map shows ~19 readable dots instead of all ~170 NSE indices. Defensive import:
# an older dashboard.py without it just means "show everything" (never a crash).
try:
    from src.web.dashboard import REAL_SECTORS as _REAL_SECTORS
except Exception:
    _REAL_SECTORS = None

router = APIRouter()


def _esc(s) -> str:
    """HTML-escape DB-sourced text (index names) before interpolation — guards the
    SVG/text, the data-html tooltip attribute, and the table against e.g. an
    ampersand in 'Nifty Oil & Gas'."""
    return html.escape(str(s), quote=True)

BENCHMARKS = ("Nifty 500", "Nifty 50")
# Dashboard dark-theme accent palette (matches _BASE_CSS / compare presets).
QCOLOR = {"Leading": "#3fb950", "Weakening": "#d29922",
          "Lagging": "#f85149", "Improving": "#58a6ff"}


def _n(v, dp: int = 1) -> str:
    return "—" if v is None else f"{v:.{dp}f}"


def _flags(r: dict) -> str:
    out = []
    if r.get("improving_entry"):
        out.append('<span class="pill" style="color:#58a6ff">↗ base turn</span>')
    if r.get("weakening_warning"):
        out.append('<span class="pill" style="color:#d29922">↘ rolling over</span>')
    if r.get("rsi_oversold_turn"):
        out.append('<span class="pill">RSI turn</span>')
    if r.get("rs_div_bull"):
        out.append('<span class="pill" style="color:#3fb950">bull div</span>')
    if r.get("rs_div_bear"):
        out.append('<span class="pill" style="color:#f85149">bear div</span>')
    if r.get("mansfield_cross_up"):
        out.append('<span class="pill" style="color:#3fb950">MRS+</span>')
    if r.get("mansfield_cross_down"):
        out.append('<span class="pill" style="color:#f85149">MRS−</span>')
    return " ".join(out) or '<span class="sub">—</span>'


def _empty() -> str:
    return (
        '<h2>Relative rotation — sectors</h2>'
        '<div class="card"><div class="sub">No relative-strength data yet.</div>'
        '<p style="color:#c9d1d9;line-height:1.5">This view reads sector RS ratios '
        'from <code>ratio_rows</code>. Once index data is ingested, run the nightly '
        'jobs to populate it:</p>'
        '<pre style="background:#0d1117;border:1px solid #30363d;border-radius:6px;'
        'padding:10px;overflow:auto">python -m src.automation.rrg\n'
        'python -m src.automation.capture</pre></div>')


def _controls(den: str) -> str:
    def pill(b: str) -> str:
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if b == den else ""
        return (f'<a href="/dash/rrg?den={quote_plus(b)}" class="pill" '
                f'style="text-decoration:none;margin-right:6px;{on}">vs {_esc(b)}</a>')
    return (
        '<h2>Relative rotation — sectors</h2>'
        f'<div class="sub">JdK RS-Ratio (x) × RS-Momentum (y), normalised ~100, '
        f'vs {den}. Strength rotates clockwise: improving → leading → weakening → lagging.</div>'
        f'<div style="margin:10px 0">{"".join(pill(b) for b in BENCHMARKS)}</div>')


def _svg(rows: list[dict], caps: dict, tails: dict) -> str:
    plot_l, plot_r, plot_t, plot_b = 46, 748, 16, 438
    devs = []
    for r in rows:
        if r["rs_ratio"] is not None:
            devs.append(abs(r["rs_ratio"] - 100))
        if r["rs_momentum"] is not None:
            devs.append(abs(r["rs_momentum"] - 100))
    half = max(6.0, min(34.0, (max(devs) if devs else 6.0) * 1.15))
    lo, hi = 100 - half, 100 + half

    def mx(v):
        x = plot_l + (v - lo) / (hi - lo) * (plot_r - plot_l)
        return max(plot_l + 2, min(plot_r - 2, x))

    def my(v):
        y = plot_b - (v - lo) / (hi - lo) * (plot_b - plot_t)
        return max(plot_t + 2, min(plot_b - 2, y))

    cx, cy = mx(100), my(100)
    s = ['<svg id="rrgsvg" viewBox="0 0 760 480" width="100%" '
         'style="max-width:760px" xmlns="http://www.w3.org/2000/svg">']
    # quadrant tints
    s.append(f'<rect x="{plot_l}" y="{plot_t}" width="{cx-plot_l:.0f}" height="{cy-plot_t:.0f}" fill="#58a6ff" fill-opacity="0.06"/>')
    s.append(f'<rect x="{cx:.0f}" y="{plot_t}" width="{plot_r-cx:.0f}" height="{cy-plot_t:.0f}" fill="#3fb950" fill-opacity="0.06"/>')
    s.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{plot_r-cx:.0f}" height="{plot_b-cy:.0f}" fill="#d29922" fill-opacity="0.06"/>')
    s.append(f'<rect x="{plot_l}" y="{cy:.0f}" width="{cx-plot_l:.0f}" height="{plot_b-cy:.0f}" fill="#f85149" fill-opacity="0.06"/>')
    s.append(f'<rect x="{plot_l}" y="{plot_t}" width="{plot_r-plot_l}" height="{plot_b-plot_t}" fill="none" stroke="#30363d"/>')
    s.append(f'<line x1="{cx:.0f}" y1="{plot_t}" x2="{cx:.0f}" y2="{plot_b}" stroke="#30363d" stroke-dasharray="3 3"/>')
    s.append(f'<line x1="{plot_l}" y1="{cy:.0f}" x2="{plot_r}" y2="{cy:.0f}" stroke="#30363d" stroke-dasharray="3 3"/>')
    # corner labels
    s.append(f'<text x="{plot_l+6}" y="{plot_t+14}" fill="#6e7681" font-size="9">improving</text>')
    s.append(f'<text x="{plot_r-6}" y="{plot_t+14}" fill="#6e7681" font-size="9" text-anchor="end">leading</text>')
    s.append(f'<text x="{plot_r-6}" y="{plot_b-6}" fill="#6e7681" font-size="9" text-anchor="end">weakening</text>')
    s.append(f'<text x="{plot_l+6}" y="{plot_b-6}" fill="#6e7681" font-size="9">lagging</text>')
    s.append(f'<text x="{(plot_l+plot_r)/2:.0f}" y="{plot_b+16}" fill="#8b949e" font-size="9" text-anchor="middle">RS-Ratio →</text>')
    s.append(f'<text x="14" y="{(plot_t+plot_b)/2:.0f}" fill="#8b949e" font-size="9" text-anchor="middle" transform="rotate(-90 14 {(plot_t+plot_b)/2:.0f})">RS-Momentum ↑</text>')

    for r in rows:
        rr, rm = r["rs_ratio"], r["rs_momentum"]
        if rr is None or rm is None:
            continue
        num = r["numerator"]
        q = r["quadrant"] or rrg.quadrant(rr, rm)
        col = QCOLOR.get(q, "#1f6feb")
        x, y = mx(rr), my(rm)
        cap = caps.get(num)
        uc = cap.get("up_capture_63") if cap else None
        rad = 6.0 if uc is None else 5.0 + max(0.0, min(1.0, (uc - 0.5) / 1.1)) * 9.0
        # tail
        tl = [p for p in (tails.get(num) or [])
              if p["rs_ratio"] is not None and p["rs_momentum"] is not None]
        if len(tl) >= 2:
            pts = " ".join(f"{mx(p['rs_ratio']):.1f},{my(p['rs_momentum']):.1f}" for p in tl)
            s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" '
                     f'stroke-width="2" stroke-opacity="0.3" stroke-linecap="round"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}" '
                 f'fill-opacity="0.85" stroke="#0d1117" stroke-width="1.4"/>')
        s.append(f'<text x="{x:.1f}" y="{y-rad-3:.1f}" fill="#e6edf3" font-size="9" '
                 f'text-anchor="middle">{_esc(num.replace("Nifty ", ""))}</text>')
        dc = cap.get("down_capture_63") if cap else None
        tip = (f"<b>{_esc(num)}</b><br>{_esc(q)} · RS-ratio {_n(rr)} · RS-mom {_n(rm)}<br>"
               f"RSI-of-RS {_n(r.get('rsi_of_rs'))} · Mansfield {_n(r.get('mansfield'),2)}<br>"
               f"down-capture {_n(dc,2)} · up-capture {_n(uc,2)}")
        s.append(f'<circle class="hit" cx="{x:.1f}" cy="{y:.1f}" r="{rad+9:.1f}" '
                 f'fill="transparent" style="cursor:pointer" data-html="{tip}"/>')
    s.append('</svg>')
    return (
        '<div id="rrgwrap" style="position:relative">'
        + "".join(s)
        + '<div id="rrgtip" style="position:absolute;display:none;pointer-events:none;'
        'background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 9px;'
        'font-size:12px;color:#e6edf3;max-width:260px;line-height:1.4;z-index:5"></div></div>'
        '<div class="sub" style="margin:6px 0 14px">Dot size = upside capture · '
        'tail = last 8 smoothed sessions · hover for detail. '
        'Tails are smoothed-daily; weekly/monthly resampling is a follow-up.</div>'
        '<script>(function(){var t=document.getElementById("rrgtip"),'
        'w=document.getElementById("rrgwrap");if(!t||!w)return;'
        'w.querySelectorAll(".hit").forEach(function(c){'
        'c.addEventListener("mouseenter",function(){t.innerHTML=c.getAttribute("data-html");t.style.display="block";});'
        'c.addEventListener("mousemove",function(e){var b=w.getBoundingClientRect();'
        't.style.left=Math.min(e.clientX-b.left+12,b.width-200)+"px";t.style.top=(e.clientY-b.top+12)+"px";});'
        'c.addEventListener("mouseleave",function(){t.style.display="none";});});})();</script>')


def _table(rows: list[dict], caps: dict, den: str) -> str:
    head = ("<thead><tr><th>Sector</th><th>Quadrant</th><th>RS-ratio</th>"
            "<th>RS-mom</th><th>RSI-of-RS</th><th>Mansfield</th>"
            "<th>Falls-less Δ%</th><th>Down-cap</th><th>Up-cap</th><th>Signals</th></tr></thead>")
    body = []
    for r in rows:
        num = r["numerator"]
        q = r["quadrant"] or rrg.quadrant(r["rs_ratio"], r["rs_momentum"]) or "—"
        col = QCOLOR.get(q, "#8b949e")
        cap = caps.get(num) or {}
        dc, uc, de = (cap.get("down_capture_63"), cap.get("up_capture_63"),
                      cap.get("down_excess_63"))
        # down-capture: <1 falls less (green); <0 means it ROSE while the market
        # fell (the strongest defensive read — label it, don't show a bare number);
        # >1 falls harder (red). down_excess Δ% is the robust, sign-clean primary.
        if dc is None:
            dc_html = '<span style="color:#8b949e">—</span>'
        elif dc < 0:
            dc_html = f'<span style="color:#3fb950">{dc:.2f} ↑rose</span>'
        elif dc < 1:
            dc_html = f'<span style="color:#3fb950">{dc:.2f}</span>'
        else:
            dc_html = f'<span style="color:#f85149">{dc:.2f}</span>'
        decol = ("#3fb950" if (de is not None and de > 0)
                 else ("#f85149" if de is not None else "#8b949e"))
        link = f'/dash/ratio?idx={quote_plus(num)}&den={quote_plus(den)}'
        body.append(
            f'<tr><td><a href="{link}" style="color:#58a6ff;text-decoration:none">{_esc(num)}</a></td>'
            f'<td style="color:{col}">{_esc(q)}</td>'
            f'<td>{_n(r["rs_ratio"])}</td><td>{_n(r["rs_momentum"])}</td>'
            f'<td>{_n(r.get("rsi_of_rs"))}</td><td>{_n(r.get("mansfield"),2)}</td>'
            f'<td style="color:{decol}">{_n(de,2)}</td>'
            f'<td>{dc_html}</td><td>{_n(uc,2)}</td>'
            f'<td>{_flags(r)}</td></tr>')
    return (f'<table class="dt">{head}<tbody>{"".join(body)}</tbody></table>')


@router.get("/dash/rrg", response_class=HTMLResponse)
def rrg_page(den: str = Query("Nifty 500", max_length=40)) -> HTMLResponse:
    den = den if den in BENCHMARKS else "Nifty 500"
    with get_conn() as conn:
        rows = rrg.latest_all(den, conn=conn) or rrg.current_all(den, conn=conn)
        if _REAL_SECTORS:                 # curate to readable economic sectors
            keep = set(_REAL_SECTORS)
            _filt = [r for r in rows if r["numerator"] in keep]
            if _filt:
                rows = _filt
        caps_list = capture.latest_all(den, conn=conn) or capture.current_all(den, conn=conn)
        caps = {c["numerator"]: c for c in caps_list}
        tails = {}
        for r in rows:                    # one bad ratio_rows row can't 500 the page
            try:
                tails[r["numerator"]] = rrg.tail(r["numerator"], den, 8, conn=conn)
            except Exception:
                tails[r["numerator"]] = []
    if not rows:
        body = _empty()
    else:
        body = _controls(den) + _svg(rows, caps, tails) + _table(rows, caps, den)
    return HTMLResponse(_shell("Relative rotation — sectors", body, active="markets", wide=True))
