"""/dash/wolfe — Wolfe-wave chart overlay (Phase 3 surface).

Correct convention: 1·3·5 same-extreme, 5 overshoots the 1-3 line, EPA = 1-4 line.
Draws ONE wave at a time (the selected rank, default best), framed tightly to that
wave so it is legible — the ranked list lets you switch which one is drawn. Server
SVG; overlay toggled by a checkbox. New, self-contained module.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

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
                f"<title>{title}</title><style>body{{background:#0d1117;color:#e6edf3;"
                "font-family:system-ui,sans-serif;margin:0;padding:16px}</style></head>"
                f"<body>{body}</body></html>")

router = APIRouter()


@router.get("/dash/wolfe/overlay")
def wolfe_overlay(sym: str = Query("", max_length=24), idx: str = Query("", max_length=48)):
    """JSON: the most-recent Wolfe wave shaped for the stock page's chart overlay."""
    sym = sym.strip().upper()
    idx = idx.strip()
    if not sym and not idx:
        return JSONResponse(None)
    with get_conn() as conn:
        return JSONResponse(wolfe.overlay_for(conn, sym=sym or None, idx=idx or None))

_W, _H = 1000, 460
_PADL, _PADR, _PADT, _PADB = 58, 108, 18, 30
_BG, _GRID, _AXT = "#161b22", "#21262d", "#8b949e"
_PRICE = "#58a6ff"
_BULL, _BEAR = "#3fb950", "#f85149"
_BAND, _BANDS = "#d29922", "#bb8009"


def _fmt(v):
    return f"{v:,.1f}" if abs(v) >= 100 else f"{v:.2f}"


def _clip(x0, y0, x1, y1):
    xmin, xmax, ymin, ymax = _PADL, _W - _PADR, _PADT, _H - _PADB
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                if t > u1:
                    return None
                u0 = max(u0, t)
            else:
                if t < u0:
                    return None
                u1 = min(u1, t)
    return (x0 + u0 * dx, y0 + u0 * dy, x0 + u1 * dx, y0 + u1 * dy)


def _chart_svg(d, wi=0, show=True):
    """Draw ONLY the selected wave (wi), framed to it. Falls back to a plain price
    chart when there are no waves."""
    highs, lows, closes, dates, n = d["highs"], d["lows"], d["closes"], d["dates"], d["n"]
    opens = d.get("opens", closes)
    waves = d["waves"]

    def frame(x0, x1, hi=(), lo=()):
        pmax = max(list(highs[x0:x1 + 1]) + list(hi))
        pmin = min(list(lows[x0:x1 + 1]) + list(lo))
        sp = (pmax - pmin) or 1.0
        return pmax + sp * 0.08, pmin - sp * 0.08

    # ---- window + price range -------------------------------------------- #
    if not waves:
        x0, x1 = max(0, n - 160), n - 1
        pmax, pmin = frame(x0, x1)
        w = None
    else:
        w = waves[max(0, min(wi, len(waves) - 1))]
        p = w["pivots"]
        p5 = w["p5"]
        p1 = p[0]
        last = p5["idx"] if p5 else p[3]["idx"]
        span = max(20, last - p1["idx"])
        x0 = max(0, int(p1["idx"] - 0.18 * span))
        x1 = min(n - 1, int(last + 0.85 * span))
        if x1 - x0 < 20:
            x1 = min(n - 1, x0 + 20)
        hi = [pt["price"] for pt in p] + ([p5["price"]] if p5 else [])
        lo = list(hi)
        if w["zone"]:
            hi.append(w["zone"]["high"])
            lo.append(w["zone"]["low"])
        if w["target"] is not None:
            hi.append(w["target"])
            lo.append(w["target"])
        pmax, pmin = frame(x0, x1, hi, lo)

    def X(i):
        return _PADL + (i - x0) / max(1, (x1 - x0)) * (_W - _PADL - _PADR)

    def Y(v):
        return _PADT + (pmax - v) / (pmax - pmin) * (_H - _PADT - _PADB)

    def at(s, ax, ap, t):
        return ap + s * (t - ax)

    S = [f'<svg viewBox="0 0 {_W} {_H}" width="100%" style="background:{_BG};border-radius:8px" '
         f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui">',
         '<defs><marker id="wfar" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" '
         'orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" '
         'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>']
    for g in range(5):
        v = pmin + (pmax - pmin) * g / 4
        y = Y(v)
        S.append(f'<line x1="{_PADL}" y1="{y:.1f}" x2="{_W-_PADR}" y2="{y:.1f}" stroke="{_GRID}"/>')
        S.append(f'<text x="{_PADL-6}" y="{y+3:.1f}" text-anchor="end" fill="{_AXT}" font-size="11">{_fmt(v)}</text>')
    for g in range(6):
        i = x0 + round((x1 - x0) * g / 5)
        S.append(f'<text x="{X(i):.1f}" y="{_H-8}" text-anchor="middle" fill="{_AXT}" font-size="10">{_esc(dates[i])}</text>')
    # price: CANDLESTICKS for stocks (so the pivots sit on the real high/low spikes —
    # a close-only line hides the wicks and makes the wave look wrong), a line for
    # indices (no OHLC). Muted when a wave is overlaid so the structure stands out.
    if d.get("has_ohlc"):
        op = 0.55 if w else 0.95
        bw = max(1.2, (_W - _PADL - _PADR) / max(1, (x1 - x0 + 1)) * 0.62)
        for i in range(x0, x1 + 1):
            cx = X(i)
            up = closes[i] >= opens[i]
            col = _BULL if up else _BEAR
            S.append(f'<line x1="{cx:.1f}" y1="{Y(highs[i]):.1f}" x2="{cx:.1f}" y2="{Y(lows[i]):.1f}" '
                     f'stroke="{col}" stroke-width="0.9" opacity="{op}"/>')
            yo, yc = Y(opens[i]), Y(closes[i])
            top, h = min(yo, yc), max(1.0, abs(yc - yo))
            S.append(f'<rect x="{cx-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                     f'fill="{col}" opacity="{op}"/>')
    else:
        pts = " ".join(f"{X(i):.1f},{Y(closes[i]):.1f}" for i in range(x0, x1 + 1))
        S.append(f'<polyline points="{pts}" fill="none" stroke="{_PRICE}" stroke-width="1.4" '
                 f'opacity="{"0.55" if w else "1"}"/>')

    if w:
        col = _BULL if w["direction"] == "BULL" else _BEAR
        p = w["pivots"]
        p5 = w["p5"]
        p1 = p[0]
        last = p5["idx"] if p5 else p[3]["idx"]
        span = max(20, last - p1["idx"])
        disp = "" if show else "none"
        S.append(f'<g id="wfGroup" style="display:{disp}">')
        # 1-3 line (segment, just past 5)
        seg = min(x1, last + int(0.12 * span))
        c = _clip(X(p1["idx"]), Y(p1["price"]), X(seg), Y(at(w["line13_slope"], p1["idx"], p1["price"], seg)))
        if c:
            S.append(f'<line x1="{c[0]:.1f}" y1="{c[1]:.1f}" x2="{c[2]:.1f}" y2="{c[3]:.1f}" '
                     f'stroke="{_BANDS}" stroke-width="1.2" stroke-dasharray="5 3"/>')
            S.append(f'<text x="{c[2]+4:.1f}" y="{c[3]+3:.1f}" fill="{_BANDS}" font-size="10">1-3 line</text>')
        # EPA 1-4 target (to the right edge) — ONLY after point 5 is confirmed
        # (Ramana: no projection until the wave properly completes at 5).
        c = _clip(X(p1["idx"]), Y(p1["price"]), X(x1), Y(at(w["epa_slope"], p1["idx"], p1["price"], x1))) if p5 else None
        if c:
            S.append(f'<line x1="{c[0]:.1f}" y1="{c[1]:.1f}" x2="{c[2]:.1f}" y2="{c[3]:.1f}" '
                     f'stroke="{col}" stroke-width="1.8"/>')
            ly = c[3] + (14 if c[3] < _PADT + 18 else -6)
            S.append(f'<text x="{c[2]-3:.1f}" y="{ly:.1f}" text-anchor="end" fill="{col}" '
                     f'font-size="11" font-weight="600">EPA target</text>')
        # Ramana's Fib method: a standard extension fan on each thrust leg (1-2 & 3-4),
        # projected toward the overshoot, + the STRONG OVERLAP zones (the targets).
        P = [pt["price"] for pt in p]
        e12, e34, fzones = wolfe.fib_zones(P[0], P[1], P[2], P[3], direction=w["direction"])

        def _fan(grid, fcol):
            for r, v in grid.items():
                yy = Y(v)
                if _PADT <= yy <= _H - _PADB:
                    S.append(f'<line x1="{_PADL}" y1="{yy:.1f}" x2="{_W-_PADR}" y2="{yy:.1f}" '
                             f'stroke="{fcol}" stroke-width="0.6" opacity="0.45"/>')
                    S.append(f'<text x="{_W-_PADR+3:.1f}" y="{yy+3:.1f}" fill="{fcol}" font-size="8" '
                             f'opacity="0.85">{r}</text>')
        _fan(e12, _PRICE)        # leg 1-2 fan (blue)
        _fan(e34, _BAND)         # leg 3-4 fan (amber)
        # overlap zones — the targets — bold, labelled price (r12 ∩ r34)
        for zi, z in enumerate(fzones):
            yy = Y(z["price"])
            if not (_PADT <= yy <= _H - _PADB):
                continue
            S.append(f'<line x1="{_PADL}" y1="{yy:.1f}" x2="{_W-_PADR}" y2="{yy:.1f}" '
                     f'stroke="{col}" stroke-width="{2.0 if zi == 0 else 1.3}"/>')
            S.append(f'<text x="{_PADL+5:.1f}" y="{yy-3:.1f}" fill="{col}" font-size="10" '
                     f'font-weight="600">{_fmt(z["price"])} ({z["r12"]}∩{z["r34"]})</text>')
        # the 1-2-3-4-5 structure (bold)
        zpts = list(p) + ([p5] if p5 else [])
        zz = " ".join(f"{X(pt['idx']):.1f},{Y(pt['price']):.1f}" for pt in zpts)
        S.append(f'<polyline points="{zz}" fill="none" stroke="{col}" stroke-width="2.4" stroke-linejoin="round"/>')
        for j, pt in enumerate(p, 1):
            cx, cy = X(pt["idx"]), Y(pt["price"])
            up = pt["kind"] == "H"
            S.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{_BG}" stroke="{col}" stroke-width="2"/>')
            S.append(f'<text x="{cx:.1f}" y="{(cy-10) if up else (cy+17):.1f}" text-anchor="middle" '
                     f'fill="{col}" font-size="12" font-weight="700">{j}</text>')
        if p5:
            cx, cy = X(p5["idx"]), Y(p5["price"])
            up = w["direction"] == "BEAR"
            S.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{_BG}" stroke="{col}" stroke-width="2.6"/>')
            S.append(f'<text x="{cx:.1f}" y="{(cy-12) if up else (cy+19):.1f}" text-anchor="middle" '
                     f'fill="{col}" font-size="12" font-weight="700">5</text>')
        S.append('</g>')
    S.append('</svg>')
    return "".join(S)


def _form(sym="", idx=""):
    return (
        '<form method="get" action="/dash/wolfe" style="margin:8px 0 14px">'
        f'<input name="sym" value="{_esc(sym)}" placeholder="stock e.g. RELIANCE" '
        'autocapitalize="characters" style="padding:6px 8px;margin-right:6px"/>'
        f'<input name="idx" value="{_esc(idx)}" placeholder="or index e.g. Nifty IT" '
        'style="padding:6px 8px;margin-right:6px"/>'
        '<button type="submit">Chart</button></form>')


def _summary(d, wi, sym, idx):
    if not d["waves"]:
        return ('<div class="sub">No Wolfe setup in view — the detector found no valid '
                '1·3·5 structure at these swing scales.</div>')
    base = f'sym={_q(sym)}' if sym else f'idx={_q(idx)}'
    out = ['<div style="font-size:13px;margin:4px 0 12px">',
           '<div style="color:#8b949e;margin-bottom:5px">Setups, best first — click one to draw it:</div>']
    for i, w in enumerate(d["waves"]):
        col = _BULL if w["direction"] == "BULL" else _BEAR
        sel = (i == wi)
        z = w["zone"]
        zs = f'zone {_fmt(z["low"])}–{_fmt(z["high"])}' if z else 'zone —'
        ups = f' · up {w["upside_pct"]}%' if w["upside_pct"] is not None else ''
        rrs = f' · R:R {w["rr"]}' if w["rr"] else ''
        mark = ' ◀ drawn' if sel else ''
        style = (f'background:#1c2430;border-left:3px solid {col};' if sel else 'border-left:3px solid transparent;')
        out.append(
            f'<a href="/dash/wolfe?{base}&w={i}" style="display:block;{style}padding:4px 8px;margin:1px 0;'
            f'border-radius:4px;text-decoration:none;color:#e6edf3">'
            f'<b style="color:{col}">{w["wolfe_rank"]} · {w["rank_tier"]}</b> · '
            f'<b style="color:{col}">{w["direction"]}</b> · {w["state"]} · q{w["quality"]} · '
            f'sym {w["sym_price"]} · {zs}{ups}{rrs}<span style="color:{col}">{mark}</span></a>')
    out.append('</div>')
    return "".join(out)


@router.get("/dash/wolfe", response_class=HTMLResponse)
def wolfe_page(sym: str = Query("", max_length=24),
               idx: str = Query("", max_length=48),
               w: int = Query(0, ge=0)):
    sym = sym.strip().upper()
    idx = idx.strip()
    if not sym and not idx:
        body = ('<h2>Wolfe wave</h2>'
                '<div class="sub">Pick a stock or index. The detector ranks every 1·3·5 setup; '
                'the chart draws the selected one (top-ranked by default).</div>' + _form())
        return HTMLResponse(_shell("Wolfe wave", body, "wolfe"))

    with get_conn() as conn:
        d = wolfe.analyze(conn, sym=sym or None, idx=idx or None)
    if not d:
        body = (f'<h2>Wolfe wave</h2><div class="empty">No price history for '
                f'<b>{_esc(sym or idx)}</b>.</div>' + _form(sym, idx))
        return HTMLResponse(_shell("Wolfe wave", body, "wolfe"))

    body = (
        f'<h2>{_esc(d["label"])} — Wolfe wave</h2>'
        + _form(sym, idx)
        + _summary(d, w, sym, idx)
        + '<div class="card" style="padding:12px">'
        + f'<label style="display:inline-flex;align-items:center;gap:7px;cursor:pointer;'
          f'font-size:14px;margin-bottom:10px;user-select:none">'
          f'<input type="checkbox" id="wfToggle" checked style="cursor:pointer;width:16px;height:16px"/>'
          f'<b>Wolfe wave overlay</b> <span style="color:{_AXT};font-weight:400">'
          f'(drawing the selected setup — untick to see price alone)</span></label>'
        + _chart_svg(d, wi=w, show=True)
        + '</div>'
        + '<script>(function(){var cb=document.getElementById("wfToggle"),'
          'g=document.getElementById("wfGroup");if(cb&&g){cb.addEventListener("change",'
          'function(){g.style.display=this.checked?"":"none";});}})();</script>')
    return HTMLResponse(_shell(f'{d["label"]} — Wolfe', body, "wolfe", wide=True))
