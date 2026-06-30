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

import datetime
import html
import json
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.automation import adjust, capture, rrg
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
# RRG quadrants are DIRECTIONAL → design tokens: Leading=up, Lagging=down,
# Improving=accent, Weakening=warn. NOTE: these are CSS var() strings — valid in
# CSS (style="color:…") but INVALID as raw SVG fill=/stroke= attributes, so SVG
# consumers below inject them via style="fill:…"/style="stroke:…".
QCOLOR = {"Leading": "var(--up)", "Weakening": "var(--warn)",
          "Lagging": "var(--down)", "Improving": "var(--accent)"}


def _n(v, dp: int = 1) -> str:
    return "—" if v is None else f"{v:.{dp}f}"


def _json_for_script(obj) -> str:
    """json.dumps for embedding inside an inline <script> block. json.dumps does NOT
    escape <, >, & — so a name carrying '</script>' (latent today: sector names come
    from a closed DB allowlist; LIVE once the animated map feeds constituent SYMBOLS,
    CL-VIEW-02 L752) would break out of the script tag. Escape the three HTML-significant
    chars to their \\uXXXX forms; numeric data + current names never contain them, so the
    rendered map/tooltip is byte-identical — this is pure defense-in-depth."""
    return (json.dumps(obj)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def _flags(r: dict) -> str:
    out = []
    if r.get("improving_entry"):
        out.append('<span class="pill" style="color:var(--accent)">↗ base turn</span>')
    if r.get("weakening_warning"):
        out.append('<span class="pill" style="color:var(--warn)">↘ rolling over</span>')
    if r.get("rsi_oversold_turn"):
        out.append('<span class="pill">RSI turn</span>')
    if r.get("rs_div_bull"):
        out.append('<span class="pill" style="color:var(--up)">bull div</span>')
    if r.get("rs_div_bear"):
        out.append('<span class="pill" style="color:var(--down)">bear div</span>')
    if r.get("mansfield_cross_up"):
        out.append('<span class="pill" style="color:var(--up)">MRS+</span>')
    if r.get("mansfield_cross_down"):
        out.append('<span class="pill" style="color:var(--down)">MRS−</span>')
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


def _svg(rows: list[dict], caps: dict, tails: dict, link_fn=None) -> str:
    plot_l, plot_r, plot_t, plot_b = 46, 748, 16, 438
    devs = []
    for r in rows:
        if r["rs_ratio"] is not None:
            devs.append(abs(r["rs_ratio"] - 100))
        if r["rs_momentum"] is not None:
            devs.append(abs(r["rs_momentum"] - 100))
    for _tl in (tails or {}).values():            # fit the plot to the TAILS too (long stock journeys)
        for p in _tl:
            if p.get("rs_ratio") is not None:
                devs.append(abs(p["rs_ratio"] - 100))
            if p.get("rs_momentum") is not None:
                devs.append(abs(p["rs_momentum"] - 100))
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
    s.append(f'<rect x="{plot_l}" y="{plot_t}" width="{cx-plot_l:.0f}" height="{cy-plot_t:.0f}" style="fill:var(--accent)" fill-opacity="0.06"/>')
    s.append(f'<rect x="{cx:.0f}" y="{plot_t}" width="{plot_r-cx:.0f}" height="{cy-plot_t:.0f}" style="fill:var(--up)" fill-opacity="0.06"/>')
    s.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{plot_r-cx:.0f}" height="{plot_b-cy:.0f}" style="fill:var(--warn)" fill-opacity="0.06"/>')
    s.append(f'<rect x="{plot_l}" y="{cy:.0f}" width="{cx-plot_l:.0f}" height="{plot_b-cy:.0f}" style="fill:var(--down)" fill-opacity="0.06"/>')
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
            s.append(f'<polyline points="{pts}" fill="none" style="stroke:{col}" '
                     f'stroke-width="2" stroke-opacity="0.3" stroke-linecap="round"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" style="fill:{col}" '
                 f'fill-opacity="0.85" stroke="#0d1117" stroke-width="1.4"/>')
        s.append(f'<text x="{x:.1f}" y="{y-rad-3:.1f}" fill="#e6edf3" font-size="9" '
                 f'text-anchor="middle">{_esc(num.replace("Nifty ", ""))}</text>')
        dc = cap.get("down_capture_63") if cap else None
        tip = (f"<b>{_esc(num)}</b><br>{_esc(q)} · RS-ratio {_n(rr)} · RS-mom {_n(rm)}<br>"
               f"RSI-of-RS {_n(r.get('rsi_of_rs'))} · Mansfield {_n(r.get('mansfield'),2)}<br>"
               f"down-capture {_n(dc,2)} · up-capture {_n(uc,2)}")
        hit = (f'<circle class="hit" cx="{x:.1f}" cy="{y:.1f}" r="{rad+9:.1f}" '
               f'fill="transparent" style="cursor:pointer" data-html="{tip}"/>')
        s.append(f'<a href="{link_fn(num)}">{hit}</a>' if link_fn else hit)
    s.append('</svg>')
    return (
        '<div id="rrgwrap" style="position:relative">'
        + "".join(s)
        + '<div id="rrgtip" style="position:absolute;display:none;pointer-events:none;'
        'background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 9px;'
        'font-size:12px;color:#e6edf3;max-width:260px;line-height:1.4;z-index:5"></div></div>'
        '<div class="sub" style="margin:6px 0 14px">Dot size = upside capture · '
        'tail = the RS-Ratio × RS-Momentum journey over the selected window · '
        'hover for detail.</div>'
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
            dc_html = f'<span style="color:var(--up)">{dc:.2f} ↑rose</span>'
        elif dc < 1:
            dc_html = f'<span style="color:var(--up)">{dc:.2f}</span>'
        else:
            dc_html = f'<span style="color:var(--down)">{dc:.2f}</span>'
        decol = ("var(--up)" if (de is not None and de > 0)
                 else ("var(--down)" if de is not None else "#8b949e"))
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


# ── constituent drill-down: the stocks INSIDE one index, vs the benchmark ─────
_CONSTITUENT_CAP = 50    # cap members plotted (bounds the on-read compute)
_WINDOW = 420            # trailing sessions per stock (enough for JdK norm + tail)


def _members(index_name: str, conn) -> list[str]:
    """The latest-snapshot member symbols of one index (case-insensitive match
    on the index name, so a 'Nifty IT' dot resolves to its membership rows)."""
    rows = conn.execute(
        "SELECT m.symbol FROM stock_index_membership m WHERE UPPER(m.index_name)=UPPER(?) "
        "AND m.snapshot_date=(SELECT MAX(snapshot_date) FROM stock_index_membership "
        "WHERE UPPER(index_name)=UPPER(?))", (index_name, index_name)).fetchall()
    return [r["symbol"] for r in rows]


def _constituent_data(index_name: str, den: str, conn):
    """On-read: each member stock's JdK RS-Ratio / RS-Momentum / RSI-of-RS vs
    `den`, from a trailing window of ADJUSTED closes (split-safe). Same row shape
    as the sector rows, so _svg/_table render it unchanged. Returns (rows, tails)."""
    brows = conn.execute(
        "SELECT trade_date, close_value FROM index_rows WHERE index_name=? "
        "AND close_value>0 ORDER BY trade_date ASC", (den,)).fetchall()
    broad = {r["trade_date"]: r["close_value"] for r in brows}
    if not broad:
        return [], {}
    rows, tails = [], {}
    for sym in _members(index_name, conn)[:_CONSTITUENT_CAP]:
        braw = conn.execute(
            "SELECT trade_date, close, prev_close FROM bhavcopy_rows WHERE symbol=? "
            "AND series='EQ' AND (segment='CM' OR segment IS NULL) "
            "ORDER BY trade_date DESC LIMIT ?", (sym, _WINDOW)).fetchall()
        if len(braw) < 80:
            continue
        braw = [dict(r) for r in reversed(braw)]          # oldest → newest
        adj = adjust.adjusted_closes(braw)
        # CL-VIEW-14: bind the benchmark close once per row instead of two dict lookups.
        ratio = [a / bv for r, a in zip(braw, adj)
                 for bv in (broad.get(r["trade_date"], 0),) if a and a > 0 and bv > 0]
        if len(ratio) < 80:
            continue
        rr, rm = rrg._rs_ratio_momentum(ratio)
        if rr[-1] is None or rm[-1] is None:
            continue
        rsi = rrg._rsi_series(ratio)
        rows.append({"numerator": sym, "rs_ratio": rr[-1], "rs_momentum": rm[-1],
                     "quadrant": rrg.quadrant(rr[-1], rm[-1]),
                     "rsi_of_rs": rsi[-1] if rsi else None})
        tails[sym] = [{"rs_ratio": rr[i], "rs_momentum": rm[i]}
                      for i in range(len(ratio))
                      if rr[i] is not None and rm[i] is not None][-8:]
    rows.sort(key=lambda d: d["rs_momentum"] if d["rs_momentum"] is not None else -1e9,
              reverse=True)
    return rows, tails


def _back_link() -> str:
    return ('<a class="row" style="display:inline;color:#58a6ff;text-decoration:none" '
            'href="/dash/rrg">← Back to sectors</a>')


def _constituent_head(index_name: str, ben: str, vs: str = "sector") -> str:
    def pill(v, label):
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if v == vs else ""
        return (f'<a href="/dash/rrg?idx={quote_plus(index_name)}&vs={v}" class="pill" '
                f'style="text-decoration:none;margin-right:6px;{on}">{label}</a>')
    toggle = pill("sector", "vs " + _esc(index_name)) + pill("broad", "vs Nifty 500")
    return (_back_link()
            + f'<h2 style="margin-top:6px">{_esc(index_name)} — constituents '
            f'<span class="sub" style="margin:0">vs {_esc(ben)} · click a stock for its page</span></h2>'
            f'<div style="margin:6px 0">{toggle}</div>'
            '<div class="sub">Each dot is a member stock on its own RS-Ratio × RS-Momentum. '
            'Top-right = leading · top-left = basing &amp; turning up · bottom = lagging. '
            '<b>vs the sector</b> = which participants lead/lag the sector (spreads them); '
            '<b>vs Nifty 500</b> = each stock vs the broad market.</div>')


def _constituent_table(rows: list[dict], den: str) -> str:
    head = ("<thead><tr><th>Stock</th><th>Quadrant</th><th>RS-ratio</th>"
            "<th>RS-mom</th><th>RSI-of-RS</th></tr></thead>")
    body = []
    for r in rows:
        sym = r["numerator"]
        q = r["quadrant"] or "—"
        col = QCOLOR.get(q, "#8b949e")
        body.append(
            f'<tr><td><a href="/dash/stock?sym={quote_plus(sym)}" '
            f'style="color:#58a6ff;text-decoration:none">{_esc(sym)}</a></td>'
            f'<td style="color:{col}">{_esc(q)}</td>'
            f'<td>{_n(r["rs_ratio"])}</td><td>{_n(r["rs_momentum"])}</td>'
            f'<td>{_n(r.get("rsi_of_rs"))}</td></tr>')
    return f'<table class="dt">{head}<tbody>{"".join(body)}</tbody></table>'


def _empty_constituents(index_name: str) -> str:
    return (_back_link()
            + f'<h2 style="margin-top:6px">{_esc(index_name)} — constituents</h2>'
            '<div class="card"><div class="sub">No constituent RS yet for this index — '
            'membership or price history is missing. The sector-level map is on '
            '<a class="row" style="display:inline" href="/dash/rrg">/dash/rrg</a>.</div></div>')


# ── selectable RRG tails — RESAMPLED by period so longer windows plot fewer, ──
# period-CLOSE points (daily JdK zig-zags too much to animate smoothly/slowly).
_SECTOR_TAIL_SESSIONS = {"3": 63, "6": 126, "12": 252, "24": 504}
_SECTOR_TAILS = ("3", "6", "12", "24")
# Cadence per window: 3m daily · 6m/12m WEEKLY · 24m MONTHLY closes (Ramana's call —
# fewer "rotations/parkings" on the long views → a smooth, slow, trackable Play).
_TAIL_CADENCE = {"3": "D", "6": "W", "12": "W", "24": "M"}


def _period_key(date_str: str, cad: str):
    """Group key for a 'YYYY-MM-DD' date at the cadence: month (YYYY-MM) or ISO week."""
    if cad == "M":
        return date_str[:7]
    d = datetime.date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]))
    iso = d.isocalendar()
    return (iso[0], iso[1])


# JdK smoothing/normalisation params PER cadence (periods, not days): weekly & monthly
# are scaled down from the daily (10,60) so the calendar window is comparable.
_CADENCE_JDK = {"W": (5, 26, 5, 26), "M": (3, 12, 3, 12)}   # (smooth, norm, mom_smooth, mom_norm)


def _rrg_jdk(ratio, smooth, norm, mom_smooth, mom_norm):
    """JdK RS-Ratio + RS-Momentum on a (resampled) series — mirrors
    rrg._rs_ratio_momentum but TIMEFRAME-NATIVE (explicit periods), reusing the same
    primitive EMA/normaliser so a single day can't jerk a long-window dot."""
    jdk = rrg._ema(ratio, smooth)
    rs_ratio = rrg._normalise_100(jdk, norm)
    start = next((i for i, v in enumerate(jdk) if v is not None), None)
    rs_mom = [None] * len(ratio)
    if start is not None and len(jdk) - start >= 2:
        valid = [v for v in jdk[start:] if v is not None]
        roc = [0.0] + [(valid[i] / valid[i - 1] - 1.0) * 100.0 if valid[i - 1] else 0.0
                       for i in range(1, len(valid))]
        mom_ema = rrg._ema(roc, mom_smooth)
        mom_full = [None] * len(ratio)
        for i, v in enumerate(mom_ema):
            mom_full[start + i] = v
        rs_mom = rrg._normalise_100(mom_full, mom_norm)
    return rs_ratio, rs_mom


def _resample_ratio(dates, ratio, cad):
    """Collapse a daily (date, ratio) series to one point per week/month CLOSE."""
    od, orr, last = [], [], None
    for d, r in zip(dates, ratio):
        k = _period_key(d, cad)
        if k != last:
            od.append(d); orr.append(r); last = k
        else:
            od[-1] = d; orr[-1] = r        # keep the period's LAST (close)
    return od, orr


def _sector_tail(num: str, den: str, months: str, conn) -> list[dict]:
    """One sector pair's RRG tail, computed TIMEFRAME-NATIVE: 3m on daily closes, 6m/12m
    on WEEKLY closes, 24m on MONTHLY closes — the JdK RS-Ratio/Momentum is RECOMPUTED on
    the resampled series (cadence-scaled smoothing via `_rrg_jdk`), not just sampled. So
    a long-window dot reflects weekly/monthly performance — a single day can't jerk it —
    and it updates per period. On-read from ratio_rows; oldest → newest, LAST point = now."""
    months = str(months)
    n = _SECTOR_TAIL_SESSIONS.get(months, 252)
    cad = _TAIL_CADENCE.get(months, "D")
    rows = conn.execute(
        "SELECT trade_date, ratio FROM ratio_rows "
        "WHERE numerator=? AND denominator=? AND ratio IS NOT NULL "
        "ORDER BY trade_date ASC", (num, den)).fetchall()
    dates = [r["trade_date"] for r in rows]
    ratio = [r["ratio"] for r in rows]
    if cad == "D":                                    # 3m — daily JdK (proven params)
        if len(ratio) < rrg.NORM_WIN + rrg.SMOOTH_SPAN:
            return []
        rr, rm = rrg._rs_ratio_momentum(ratio)
        pts = [(rr[i], rm[i]) for i in range(len(ratio)) if rr[i] is not None and rm[i] is not None]
        seg = pts[-n:] if len(pts) > n else pts
    else:                                             # 6m/12m weekly · 24m monthly closes
        rdates, rratio = _resample_ratio(dates, ratio, cad)
        sm, nm, _ms, _mn = _CADENCE_JDK[cad]
        if len(rratio) < sm + nm:
            return []
        rr, rm = _rrg_jdk(rratio, *_CADENCE_JDK[cad])
        pts = [(rr[i], rm[i]) for i in range(len(rratio)) if rr[i] is not None and rm[i] is not None]
        nper = round(int(months) * 52 / 12) if cad == "W" else int(months)
        seg = pts[-nper:] if len(pts) > nper else pts
    return [{"rs_ratio": r, "rs_momentum": m} for (r, m) in seg]


def _tail_selector(den: str, active: str, base: str, view: str = "") -> str:
    """A 3/6/12/24-month RRG tail-length control (rounded pills). Links to `base`
    keeping den (+ optional view=) so the choice sticks across the reload."""
    active = active if active in _SECTOR_TAILS else "12"
    vq = f"view={quote_plus(view)}&" if view else ""
    cells = []
    for m in _SECTOR_TAILS:
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if m == active else ""
        cells.append(
            f'<a href="{base}?{vq}den={quote_plus(den)}&tail={m}" class="pill" '
            f'style="text-decoration:none;margin-right:5px;{on}">{m}m</a>')
    return ('<div style="margin:8px 0;display:flex;align-items:center;gap:4px;flex-wrap:wrap">'
            '<span class="sub" style="margin:0 8px 0 0">timeframe</span>'
            + "".join(cells)
            + '<span class="sub" style="margin:0 0 0 8px;font-size:11px">3m daily &middot; '
              '6m/12m weekly &middot; 24m monthly</span></div>')


def _fetch(den: str, conn, months: str = "12"):
    """Fetch (rows, caps, tails) for one benchmark — stored path with on-read
    fallback, curated to REAL_SECTORS. Shared by the full page and the embed.
    `months` (3/6/12/24) sets the RRG tail horizon (downsampled in _sector_tail)."""
    rows = rrg.latest_all(den, conn=conn) or rrg.current_all(den, conn=conn, only=_REAL_SECTORS)
    if _REAL_SECTORS:                     # curate the stored path (all ~170 indices) too
        keep = set(_REAL_SECTORS)
        _filt = [r for r in rows if r["numerator"] in keep]
        if _filt:
            rows = _filt
    caps_list = capture.latest_all(den, conn=conn) or capture.current_all(den, conn=conn, only=_REAL_SECTORS)
    caps = {c["numerator"]: c for c in caps_list}
    tails = {}
    for r in rows:                        # one bad ratio_rows row can't 500 the page
        try:
            tails[r["numerator"]] = _sector_tail(r["numerator"], den, months, conn)
        except Exception:
            tails[r["numerator"]] = []
    return rows, caps, tails


# ── animated all-sectors RRG (Play = watch the rotation; short tapered tails) ──
# 19 stable, distinct per-sector identity colours (bright on the dark bg). Colour =
# WHO the sector is (never changes as it moves); position = its momentum state.
_RRG_PALETTE = [
    "#ff6b6b", "#4dabf7", "#ffd43b", "#51cf66", "#cc5de8", "#ff922b", "#22b8cf",
    "#f783ac", "#a9e34b", "#748ffc", "#fab005", "#38d9a9", "#e599f7", "#66d9e8",
    "#ff8787", "#9775fa", "#69db7c", "#ffa94d", "#63e6be", "#da77f2", "#ffc078",
]

_RRG_PLAY_JS = r"""
(function(){
var D=__DATA__; if(!D.length) return;
var INK='#e6edf3',LINK=__LINK__,GHOST='#6e7681';
var L=46,R=748,T=16,B=438,DR=7;          // DR = uniform dot radius (size = no hidden encoding)
var SPD={slow:18000,med:10000,fast:5000},STEP=SPD.slow;   // TOTAL ms for the whole journey
function esc(x){return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
var devs=[6];
D.forEach(function(s){(s.pts||[]).forEach(function(p){devs.push(Math.abs(p[0]-100));devs.push(Math.abs(p[1]-100));});});
var half=Math.max(6,Math.min(34,Math.max.apply(null,devs)*1.15)),lo=100-half,hi=100+half;
function MX(v){return Math.max(L+2,Math.min(R-2,L+(v-lo)/(hi-lo)*(R-L)));}
function MY(v){return Math.max(T+2,Math.min(B-2,B-(v-lo)/(hi-lo)*(B-T)));}
function ds(p,mx){if(p.length<=mx)return p;var st=Math.ceil(p.length/mx),o=[];for(var i=0;i<p.length;i+=st)o.push(p[i]);if(o[o.length-1]!==p[p.length-1])o.push(p[p.length-1]);return o;}
function ln(a,b,col,w,o){return '<line x1="'+MX(a[0]).toFixed(1)+'" y1="'+MY(a[1]).toFixed(1)+'" x2="'+MX(b[0]).toFixed(1)+'" y2="'+MY(b[1]).toFixed(1)+'" stroke="'+col+'" stroke-width="'+w+'" stroke-opacity="'+o+'" stroke-linecap="round"/>';}
function path(d,col,w,o){return d?'<path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="'+w+'" stroke-opacity="'+o+'" stroke-linecap="round" stroke-linejoin="round"/>':'';}
// Catmull-Rom → cubic-bezier: a SMOOTH curve through the points (no sharp corners).
function smooth(pts){if(!pts||pts.length<2)return '';var P=pts.map(function(p){return [MX(p[0]),MY(p[1])];});
 if(P.length===2)return 'M'+P[0][0].toFixed(1)+','+P[0][1].toFixed(1)+' L'+P[1][0].toFixed(1)+','+P[1][1].toFixed(1);
 var d='M'+P[0][0].toFixed(1)+','+P[0][1].toFixed(1);
 for(var i=0;i<P.length-1;i++){var p0=P[i-1]||P[i],p1=P[i],p2=P[i+1],p3=P[i+2]||P[i+1];
  var c1x=p1[0]+(p2[0]-p0[0])/6,c1y=p1[1]+(p2[1]-p0[1])/6,c2x=p2[0]-(p3[0]-p1[0])/6,c2y=p2[1]-(p3[1]-p1[1])/6;
  d+=' C'+c1x.toFixed(1)+','+c1y.toFixed(1)+' '+c2x.toFixed(1)+','+c2y.toFixed(1)+' '+p2[0].toFixed(1)+','+p2[1].toFixed(1);}
 return d;}
function dotC(x,y,col,op){return '<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="'+DR+'" fill="'+col+'" fill-opacity="'+(op==null?0.95:op)+'" stroke="#0d1117" stroke-width="1.4"/>';}
// label with a dark halo (paint-order:stroke) so names stay readable over any dot/zone
function lbl(x,y,t,op){return '<text x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" fill="'+INK+'" fill-opacity="'+(op==null?1:op)+'" font-size="9" text-anchor="middle" style="paint-order:stroke;stroke:#0d1117;stroke-width:2.6px;stroke-linejoin:round">'+esc(t)+'</text>';}
var svg=document.getElementById('rrgsvg'),tip=document.getElementById('rrgtip'),wrap=document.getElementById('rrgwrap');
var cx=MX(100),cy=MY(100),raf=null;
function grid(){var s='';
 s+='<rect x="'+L+'" y="'+T+'" width="'+(cx-L)+'" height="'+(cy-T)+'" style="fill:var(--accent)" fill-opacity="0.05"/>';
 s+='<rect x="'+cx+'" y="'+T+'" width="'+(R-cx)+'" height="'+(cy-T)+'" style="fill:var(--up)" fill-opacity="0.05"/>';
 s+='<rect x="'+cx+'" y="'+cy+'" width="'+(R-cx)+'" height="'+(B-cy)+'" style="fill:var(--warn)" fill-opacity="0.05"/>';
 s+='<rect x="'+L+'" y="'+cy+'" width="'+(cx-L)+'" height="'+(B-cy)+'" style="fill:var(--down)" fill-opacity="0.05"/>';
 s+='<rect x="'+L+'" y="'+T+'" width="'+(R-L)+'" height="'+(B-T)+'" fill="none" stroke="#30363d"/>';
 s+='<line x1="'+cx+'" y1="'+T+'" x2="'+cx+'" y2="'+B+'" stroke="#30363d" stroke-dasharray="3 3"/>';
 s+='<line x1="'+L+'" y1="'+cy+'" x2="'+R+'" y2="'+cy+'" stroke="#30363d" stroke-dasharray="3 3"/>';
 s+='<text x="'+(L+6)+'" y="'+(T+14)+'" fill="'+GHOST+'" font-size="10">improving</text>';
 s+='<text x="'+(R-6)+'" y="'+(T+14)+'" fill="'+GHOST+'" font-size="10" text-anchor="end">leading</text>';
 s+='<text x="'+(R-6)+'" y="'+(B-6)+'" fill="'+GHOST+'" font-size="10" text-anchor="end">weakening</text>';
 s+='<text x="'+(L+6)+'" y="'+(B-6)+'" fill="'+GHOST+'" font-size="10">lagging</text>';
 s+='<text x="'+((L+R)/2)+'" y="'+(B+16)+'" fill="#8b949e" font-size="9" text-anchor="middle">RS-Ratio →</text>';
 s+='<text x="14" y="'+((T+B)/2)+'" fill="#8b949e" font-size="9" text-anchor="middle" transform="rotate(-90 14 '+((T+B)/2)+')">RS-Momentum ↑</text>';
 return s;}
function interp(p,f){var n=p.length;if(!n)return null;if(n===1)return p[0];var x=f*(n-1),i=Math.floor(x),t=x-i;if(i>=n-1)return p[n-1];return [p[i][0]+(p[i+1][0]-p[i][0])*t,p[i][1]+(p[i+1][1]-p[i][1])*t];}
// RESTING = clean dots (STABLE per-sector colour) + a tiny recent-heading stub + de-collided labels.
function layout(){var a=D.map(function(sec){return {x:MX(sec.now[0]),y:MY(sec.now[1]),ly:MY(sec.now[1])-DR-4,leader:false};});
 var order=a.map(function(_,i){return i;}).sort(function(i,j){return a[i].ly-a[j].ly;}),lastY=-1e9,GAP=11;
 order.forEach(function(i){var it=a[i];if(it.ly<lastY+GAP){it.ly=lastY+GAP;it.leader=true;}lastY=it.ly;});
 return a;}
function dotsLayer(){var lay=layout(),s='';
 D.forEach(function(sec,idx){var col=sec.col,q=lay[idx],stub=(sec.pts||[]).slice(-3);
  s+='<g class="hit" data-i="'+idx+'" style="cursor:'+(LINK?'pointer':'default')+'">';
  s+=path(smooth(stub),col,1.8,0.5);     // resting: only the last couple of movements, smoothed
  if(q.leader)s+='<line x1="'+q.x.toFixed(1)+'" y1="'+(q.y-DR-1).toFixed(1)+'" x2="'+q.x.toFixed(1)+'" y2="'+(q.ly+2).toFixed(1)+'" stroke="'+GHOST+'" stroke-width="0.7" stroke-opacity="0.6"/>';
  s+=dotC(q.x,q.y,col,0.95)+lbl(q.x,q.ly,sec.k,1);
  s+='<circle cx="'+q.x.toFixed(1)+'" cy="'+q.y.toFixed(1)+'" r="'+(DR+10)+'" fill="transparent"/></g>';});
 return s;}
function staticView(){if(raf){cancelAnimationFrame(raf);raf=null;}svg.innerHTML='<g>'+grid()+'</g><g id="dl">'+dotsLayer()+'</g><g id="ov" style="pointer-events:none"></g>';wire();}
// HOVER a sector → trace ITS full journey (dim the rest); overlay layer, zero re-wire.
function hi(idx){var dl=document.getElementById('dl'),ov=document.getElementById('ov');if(!dl||!ov)return;dl.style.opacity='0.20';
 var sec=D[idx],col=sec.col,pts=ds(sec.pts||[],30),X=MX(sec.now[0]),Y=MY(sec.now[1]),s='';
 s+=path(smooth(pts),col,2,0.62);        // hover: the full journey, smoothed
 s+='<circle cx="'+X.toFixed(1)+'" cy="'+Y.toFixed(1)+'" r="'+(DR+3)+'" fill="none" stroke="#e6edf3" stroke-width="1.5"/>';
 s+=dotC(X,Y,col,1)+lbl(X,Y-DR-4,sec.k,1);ov.innerHTML=s;}
function unhi(){var dl=document.getElementById('dl'),ov=document.getElementById('ov');if(dl)dl.style.opacity='1';if(ov)ov.innerHTML='';}
function wire(){Array.prototype.forEach.call(svg.querySelectorAll('.hit'),function(g){var idx=+g.getAttribute('data-i'),sec=D[idx];
 g.addEventListener('mouseenter',function(){hi(idx);var h='<b>'+esc(sec.n)+'</b><br>'+sec.q+' · RS-ratio '+sec.now[0].toFixed(1)+' · RS-mom '+sec.now[1].toFixed(1);if(sec.rsi!=null)h+='<br>RSI-of-RS '+sec.rsi.toFixed(1);if(sec.mans!=null)h+=' · Mansfield '+sec.mans.toFixed(2);var cap='';if(sec.dc!=null)cap+='down-cap '+sec.dc.toFixed(2);if(sec.uc!=null)cap+=(cap?' · ':'')+'up-cap '+sec.uc.toFixed(2);if(cap)h+='<br>'+cap;tip.innerHTML=h;tip.style.display='block';});
 g.addEventListener('mousemove',function(e){var b=wrap.getBoundingClientRect();tip.style.left=Math.min(e.clientX-b.left+12,b.width-210)+'px';tip.style.top=(e.clientY-b.top+12)+'px';});
 g.addEventListener('mouseleave',function(){unhi();tip.style.display='none';});
 if(LINK)g.addEventListener('click',function(){window.location.href='/dash/rrg?idx='+encodeURIComponent(sec.n);});});}
// PLAY = slow (default), names stay ON, each dot keeps its OWN colour the whole way.
function play(){if(raf)cancelAnimationFrame(raf);tip.style.display='none';var ovx=document.getElementById('ov');if(ovx)ovx.innerHTML='';
 var trails=D.map(function(){return [];}),t0=null,dur=STEP;          // fixed total duration
 function step(ts){if(!t0)t0=ts;var k=Math.min(1,(ts-t0)/dur),s=grid();
  D.forEach(function(sec,idx){var pts=sec.pts||[];if(!pts.length)return;var p=interp(pts,k);if(!p)return;var col=sec.col,tr=trails[idx];tr.push(p);if(tr.length>12)tr.shift();
   s+=path(smooth(tr),col,2,0.42);       // play: a smooth comet trail behind the dot
   s+=dotC(MX(p[0]),MY(p[1]),col,0.97);});
  D.forEach(function(sec){var pts=sec.pts||[];if(!pts.length)return;var p=interp(pts,k);if(!p)return;s+=lbl(MX(p[0]),MY(p[1])-DR-4,sec.k,1);});
  svg.innerHTML='<g>'+s+'</g>';if(k<1)raf=requestAnimationFrame(step);else staticView();}
 raf=requestAnimationFrame(step);}
function setSpd(key){STEP=SPD[key]||SPD.slow;Array.prototype.forEach.call(document.querySelectorAll('#rrgspeed button'),function(b){var on=b.getAttribute('data-spd')===key;b.style.background=on?'#1f6feb':'transparent';b.style.color=on?'#fff':'#8b949e';});play();}
var pb=document.getElementById('rrgplay');if(pb)pb.addEventListener('click',play);
var sp=document.getElementById('rrgspeed');if(sp)sp.addEventListener('click',function(e){var b=e.target.closest('button');if(b)setSpd(b.getAttribute('data-spd'));});
staticView();
})();
"""


def _sectors_rrg_block(rows: list[dict], caps: dict, tails: dict, den: str, months: str,
                       tail_base=None, tail_view: str = "", dot_link: bool = True) -> str:
    """The all-sectors RRG, JS-rendered with a **Play** that animates the rotation
    (comet trails) + short tapered static tails (de-spaghetti'd vs the old static
    polylines). Selector (if tail_base) + Play + scatter + hover. Used by the /dash/rrg
    sector page and the /dash/rsband RRG tab; constituents/single-stock keep _svg."""
    # STABLE per-sector identity colour (by sorted name → a sector keeps its colour
    # across renders/sessions; it never changes as the dot moves through quadrants).
    names = sorted({r["numerator"] for r in rows
                    if r["rs_ratio"] is not None and r["rs_momentum"] is not None})
    cmap = {nm: _RRG_PALETTE[i % len(_RRG_PALETTE)] for i, nm in enumerate(names)}
    data = []
    for r in rows:
        num = r["numerator"]
        tl = [[p["rs_ratio"], p["rs_momentum"]] for p in (tails.get(num) or [])
              if p.get("rs_ratio") is not None and p.get("rs_momentum") is not None]
        if not tl:
            continue                       # no timeframe-native tail (insufficient history)
        now = tl[-1]                        # NOW = latest cadence point (the weekly/monthly close)
        cap = caps.get(num) or {}
        data.append({
            # strip "Nifty " AND " Index" to match the Lanes labels exactly (e.g.
            # "Nifty Healthcare Index" → "Healthcare", not "Healthcare Index").
            "k": num.replace("Nifty ", "").replace(" Index", ""), "n": num,
            "col": cmap.get(num, "#58a6ff"),
            "q": rrg.quadrant(now[0], now[1]) or "Lagging",
            "now": [round(now[0], 2), round(now[1], 2)],
            "pts": [[round(a, 2), round(b, 2)] for a, b in tl],
            "uc": cap.get("up_capture_63"), "dc": cap.get("down_capture_63"),
            "rsi": r.get("rsi_of_rs"), "mans": r.get("mansfield"),
        })
    sel = _tail_selector(den, months, tail_base, tail_view) if tail_base else ""
    js = (_RRG_PLAY_JS.replace("__DATA__", _json_for_script(data))
          .replace("__LINK__", "1" if dot_link else "0"))

    def _spd(key, label, on):
        st = ("background:#1f6feb;color:#fff;" if on else "background:transparent;color:#8b949e;")
        return (f'<button data-spd="{key}" style="{st}border:0;border-right:1px solid #30363d;'
                f'padding:5px 12px;font-size:13px;cursor:pointer">{label}</button>')
    speed = ('<span class="sub" style="margin:0">speed</span>'
             '<span id="rrgspeed" style="display:inline-flex;border:1px solid #30363d;'
             'border-radius:6px;overflow:hidden">'
             + _spd("slow", "Slow", True) + _spd("med", "Med", False)
             + _spd("fast", "Fast", False).replace("border-right:1px solid #30363d;", "") + '</span>')
    return (
        sel
        + '<div class="card" style="padding:8px 10px">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px">'
        '<button id="rrgplay" style="background:transparent;color:#e6edf3;border:1px solid #30363d;'
        'border-radius:6px;padding:5px 14px;font-size:13px;cursor:pointer">&#9658; Play rotation</button>'
        + speed +
        '<span class="sub" style="margin:0">each sector keeps its own <b>colour + name</b> &middot; '
        '<b>hover</b> one to trace its journey &middot; <b>Play</b> (slow) to watch them rotate</span></div>'
        '<div id="rrgwrap" style="position:relative">'
        '<svg id="rrgsvg" viewBox="0 0 760 480" width="100%" style="max-width:760px" '
        'xmlns="http://www.w3.org/2000/svg"></svg>'
        '<div id="rrgtip" style="position:absolute;display:none;pointer-events:none;background:#161b22;'
        'border:1px solid #30363d;border-radius:6px;padding:6px 9px;font-size:12px;color:#e6edf3;'
        'max-width:240px;line-height:1.4;z-index:5"></div></div>'
        '<div class="sub" style="margin:4px 0 0"><b>Colour + label = the sector</b> (stable as it moves) '
        '&middot; <b>position = its state</b> — the tinted zones are improving / leading / weakening / '
        'lagging &middot; the <b>timeframe</b> sets the whole map (3m daily &middot; 6m/12m weekly &middot; '
        '24m monthly) — a longer timeframe shows the bigger trend and a single day can&#39;t jerk it '
        '&middot; short stub = recent heading.</div>'
        '</div>'
        + '<script>' + js + '</script>')


def render_sectors_map(den: str = "Nifty 500", conn=None, months: str = "12",
                       tail_base=None, tail_view: str = "") -> str:
    """The RRG map block (heading + animated Play scatter + hover) for the /dash/rsband
    RRG tab (and embeds). Returns '' when there's no data. Self-contained (own JS);
    reuses the host page's dark CSS. Manages its own conn. `months` (3/6/12/24) = tail
    horizon; if `tail_base` is given a tail-length selector links to it (`tail_view`
    carried as ?view=)."""
    # CL-VIEW-10: `with` (own → get_conn(); passed-in → nullcontext) so a real exception
    # propagates with its traceback instead of being swallowed by __exit__(None,None,None).
    own = conn is None
    with (get_conn() if own else nullcontext(conn)) as conn:
        den = den if den in BENCHMARKS else "Nifty 500"
        months = months if months in _SECTOR_TAILS else "12"
        rows, caps, tails = _fetch(den, conn, months)
    if not rows:
        return ""
    return (
        '<h2 style="margin-top:2px">Rotation map '
        f'<span class="sub" style="margin:0">JdK RS-Ratio × RS-Momentum · vs {_esc(den)} · Play the rotation</span></h2>'
        + _sectors_rrg_block(rows, caps, tails, den, months,
                             tail_base=tail_base, tail_view=tail_view, dot_link=True)
        + '<div class="sub" style="margin:6px 0 0">Improving (top-left) = base turning up · '
          'Leading (top-right) = strong &amp; gaining · Weakening (bottom-right) = lazy laggard · '
          'Lagging (bottom-left) = weak &amp; falling. '
          '<a class="row" style="display:inline" href="/dash/rrg">Full map + table + benchmark toggle →</a></div>')


# ── single-stock RRG: one stock's RS-Ratio×RS-Momentum journey (the tail) ──────
_STOCK_RRG_WINDOW = 780      # ~3y sessions: a 24m tail + the JdK normalisation lead-in
_TAIL_SESSIONS = {"3": 63, "6": 126, "12": 252, "24": 504}
# (label, text-colour, background-tint) — DIRECTIONAL quadrant tokens. The bg tint
# replaces the old "{hex}22" alpha-suffix trick (invalid on var()): use the rgb
# token at ~0.13 alpha (≈0x22), and --accent-dim for the accent quadrant.
_LEAD_LABEL = {
    "Leading":   ("Leader — strong &amp; gaining", "var(--up)", "rgba(var(--up-rgb),.13)"),
    "Improving": ("Improving — basing, turning up", "var(--accent)", "var(--accent-dim)"),
    "Weakening": ("Weakening — leader rolling over", "var(--warn)", "rgba(var(--warn-rgb),.13)"),
    "Lagging":   ("Laggard — weak &amp; falling", "var(--down)", "rgba(var(--down-rgb),.13)"),
}


def _stock_rrg(sym: str, den: str, conn):
    """One stock's full RS-Ratio/RS-Momentum series vs `den` (adjusted bhavcopy ÷
    benchmark). Returns (latest-row, full_path) where full_path is the list of
    (rs_ratio, rs_momentum) points for the tail. (None, []) if too short."""
    brows = conn.execute("SELECT trade_date, close_value FROM index_rows WHERE index_name=? "
                         "AND close_value>0 ORDER BY trade_date ASC", (den,)).fetchall()
    broad = {r["trade_date"]: r["close_value"] for r in brows}
    if not broad:
        return None, []
    braw = conn.execute("SELECT trade_date, close, prev_close FROM bhavcopy_rows WHERE symbol=? "
                        "AND series='EQ' AND (segment='CM' OR segment IS NULL) "
                        "ORDER BY trade_date DESC LIMIT ?", (sym, _STOCK_RRG_WINDOW)).fetchall()
    if len(braw) < 120:
        return None, []
    braw = [dict(r) for r in reversed(braw)]
    adj = adjust.adjusted_closes(braw)
    # CL-VIEW-14: bind the benchmark close once per row instead of two dict lookups.
    ratio = [a / bv for r, a in zip(braw, adj)
             for bv in (broad.get(r["trade_date"], 0),) if a and a > 0 and bv > 0]
    if len(ratio) < 120:
        return None, []
    rr, rm = rrg._rs_ratio_momentum(ratio)
    if rr[-1] is None or rm[-1] is None:
        return None, []
    rsi = rrg._rsi_series(ratio)
    mans = rrg._mansfield_series(ratio)
    row = {"numerator": sym, "rs_ratio": rr[-1], "rs_momentum": rm[-1],
           "quadrant": rrg.quadrant(rr[-1], rm[-1]),
           "rsi_of_rs": rsi[-1] if rsi else None, "mansfield": mans[-1] if mans else None}
    full = [(rr[i], rm[i]) for i in range(len(ratio)) if rr[i] is not None and rm[i] is not None]
    return row, full


def _stock_rrg_page(sym: str, den: str, tail: str) -> str:
    tail = tail if tail in _TAIL_SESSIONS else "12"
    with get_conn() as conn:
        row, full = _stock_rrg(sym, den, conn)
    back = (f'<a class="row" style="display:inline;color:#58a6ff;text-decoration:none" '
            f'href="/dash/rsband?sym={quote_plus(sym)}">&#8592; {_esc(sym)} band</a>')
    if not row:
        return (back + f'<h2 style="margin-top:6px">{_esc(sym)} — rotation</h2>'
                '<div class="card"><div class="sub">Not enough price history for a rotation tail yet.</div></div>')
    n = _TAIL_SESSIONS[tail]
    seg = full[-n:] if len(full) > n else full
    step = max(1, len(seg) // 64)
    tailpts = [{"rs_ratio": p[0], "rs_momentum": p[1]} for p in seg[::step]]
    if seg and (not tailpts or (tailpts[-1]["rs_ratio"], tailpts[-1]["rs_momentum"]) != seg[-1]):
        tailpts.append({"rs_ratio": seg[-1][0], "rs_momentum": seg[-1][1]})
    q = row["quadrant"] or "—"
    lab, lcol, lbg = _LEAD_LABEL.get(q, ("—", "#8b949e", "#8b949e22"))

    def tpill(t, label):
        on = "background:#1f6feb;border-color:#1f6feb;color:#fff;" if t == tail else ""
        return (f'<a href="/dash/rrg?sym={quote_plus(sym)}&tail={t}" class="pill" '
                f'style="text-decoration:none;margin-right:6px;{on}">{label}</a>')
    head = (back + f'<h2 style="margin-top:6px">{_esc(sym)} — relative rotation '
            f'<span class="sub" style="margin:0">RS-Ratio &times; RS-Momentum vs {_esc(den)} · its journey</span></h2>'
            f'<div style="margin:4px 0 8px"><span class="pill" style="background:{lbg};color:{lcol}">{lab}</span>'
            f'<span class="sub" style="margin-left:12px">tail: {tpill("3", "3m")}{tpill("6", "6m")}{tpill("12", "12m")}{tpill("24", "24m")}</span></div>')
    foot = (f'<div class="sub" style="margin-top:8px">The dot is today; the tail traces the last {tail} months '
            'of its relative-strength journey (clockwise: improving → leading → weakening → lagging). '
            f'<a class="row" style="display:inline" href="/dash/rsband?sym={quote_plus(sym)}">Its support/resistance band →</a> · '
            f'<a class="row" style="display:inline" href="/dash/stock?sym={quote_plus(sym)}">Full stock page →</a></div>')
    return head + _svg([row], {}, {sym: tailpts}, link_fn=None) + foot


@router.get("/dash/rrg", response_class=HTMLResponse)
def rrg_page(den: str = Query("Nifty 500", max_length=40),
             idx: str = Query("", max_length=60),
             vs: str = Query("sector", max_length=10),
             sym: str = Query("", max_length=30),
             tail: str = Query("12", max_length=2)) -> HTMLResponse:
    den = den if den in BENCHMARKS else "Nifty 500"
    if sym:                               # SINGLE-STOCK rotation (its journey tail)
        return HTMLResponse(_shell(f"{sym} — rotation", _stock_rrg_page(sym, den, tail),
                                   active="markets", wide=True))
    if idx:                               # DRILL-DOWN: the stocks inside one index
        # Default benchmark = the SECTOR itself (which participants lead/lag the
        # sector → spreads them across quadrants); vs=broad = vs Nifty 500.
        ben = "Nifty 500" if vs == "broad" else idx
        with get_conn() as conn:
            rows, tails = _constituent_data(idx, ben, conn)
        if not rows:
            body = _empty_constituents(idx)
        else:
            body = (_constituent_head(idx, ben, vs)
                    + _svg(rows, {}, tails, link_fn=lambda s: "/dash/stock?sym=" + quote_plus(s))
                    + _constituent_table(rows, ben))
        return HTMLResponse(_shell(f"{idx} — rotation", body, active="markets", wide=True))
    months = tail if tail in _SECTOR_TAILS else "12"      # sector level — selectable tail
    with get_conn() as conn:
        rows, caps, tails = _fetch(den, conn, months)
    if not rows:
        body = _empty()
    else:
        body = (_controls(den)
                + _sectors_rrg_block(rows, caps, tails, den, months,
                                     tail_base="/dash/rrg", tail_view="", dot_link=True)
                + _table(rows, caps, den))
    return HTMLResponse(_shell("Relative rotation — sectors", body, active="markets", wide=True))
