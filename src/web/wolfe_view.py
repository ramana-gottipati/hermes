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
                f"<title>{title}</title><style>body{{background:var(--bg-1);color:var(--ink);"
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
# Directional candle / wave colours. _BULL/_BEAR are used as SVG fill=/stroke=
# ATTRIBUTES in _chart_svg, where CSS var() is invalid — so these carry the
# canonical literal hex (#3fd486 up / #ff6a7a down). HTML-context directional
# colour (summary rows, scanner cells) uses _UP_VAR/_DN_VAR = var(--up)/var(--down).
_BULL, _BEAR = "#3fd486", "#ff6a7a"
_UP_VAR, _DN_VAR = "var(--up)", "var(--down)"
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


def _summary(d, wi, sym, idx, sort=""):
    if not d["waves"]:
        return ('<div class="sub">No Wolfe setup in view — the detector found no valid '
                '1·3·5 structure at these swing scales.</div>')
    base = (f'sym={_q(sym)}' if sym else f'idx={_q(idx)}') + ('&sort=q' if sort == 'q' else '')
    alltime = sort == 'q'
    toggle = (
        '<span style="color:var(--ink-3)">sort:</span> '
        + (f'<a href="/dash/wolfe?{(f"sym={_q(sym)}" if sym else f"idx={_q(idx)}")}" style="color:#58a6ff">⚡ current-first</a>'
           if alltime else '<b title="rank_attention = Q × 0.5^(age/60) — §B quality decayed by recency (D99); '
           'Q itself never changes">⚡ current-first</b>')
        + ' · '
        + ('<b title="pure §B quality, timeless — the all-time view">Q all-time</b>' if alltime else
           f'<a href="/dash/wolfe?{(f"sym={_q(sym)}" if sym else f"idx={_q(idx)}")}&sort=q" style="color:#58a6ff" '
           f'title="pure §B quality, timeless — the all-time view">Q all-time</a>'))
    out = ['<div style="font-size:13px;margin:4px 0 12px">',
           '<div style="color:var(--ink-2);margin-bottom:5px">Setups (★ <b style="color:#58a6ff">EDGE</b> = the validated '
           'winner-profile · <a href="/dash/wolfe/scan" style="color:#58a6ff">open the scanner ›</a>) · '
           + toggle +
           '; hover a row for the p1·B·C·F·G·H·I·D breakdown; click to draw:</div>']
    for i, w in enumerate(d["waves"]):
        col = _UP_VAR if w["direction"] == "BULL" else _DN_VAR
        sel = (i == wi)
        z = w["zone"]
        zs = f'zone {_fmt(z["low"])}–{_fmt(z["high"])}' if z else 'zone —'
        ups = f' · up {w["upside_pct"]}%' if w["upside_pct"] is not None else ''
        rrs = f' · R:R {w["rr"]}' if w["rr"] else ''
        mark = ' ◀ drawn' if sel else ''
        wp = wolfe.is_winner_profile(w.get("score"))
        wpb = ('<span style="background:#1f6feb;color:#fff;font-size:10px;padding:0 5px;border-radius:4px;'
               'margin-right:5px" title="reachable-EPA winner-profile — the validated edge">★ EDGE</span>') if wp else ''
        sc = w.get("score") or {}
        stq, lnq = wolfe.score_split(sc)
        split = (f'<span style="color:var(--ink-2);font-size:11px" '
                 f'title="§B split — STR = shape (p1×2 + pts-2/3/4 + rail touches, max 11), '
                 f'LND = landing (C zone · F gap · G 4.618 · I RSI · D upside, max 13). '
                 f'⚠ LND inverts as a trade filter — the validated profile prefers low D/F.">'
                 f' = STR {stq:g}/11 · LND {lnq:g}/13</span>') if stq is not None else ''
        chip_title = (f'§B  p1×2={sc.get("p1",0)*2}  B={sc.get("B",0)}  C={sc.get("C",0)}  '
                      f'F={sc.get("F",0)}  G={sc.get("G",0)}  H={sc.get("H",0)}  I={sc.get("I",0)}  '
                      f'D={sc.get("D",0)}    ·    attn {w.get("rank_attention")} '
                      f'(Q × 0.5^(age/60), D99)    ·    source {w.get("source","")}') if sc else ''
        p4d = w["pivots"][3]["date"]
        bdr = "#1f6feb" if wp else col
        style = (f'background:#1c2430;border-left:3px solid {bdr};' if (sel or wp) else 'border-left:3px solid transparent;')
        out.append(
            f'<a href="/dash/wolfe?{base}&w={i}" title="{_esc(chip_title)}" '
            f'style="display:block;{style}padding:4px 8px;margin:1px 0;'
            f'border-radius:4px;text-decoration:none;color:var(--ink)">'
            f'{wpb}<b style="color:{col}">{w["direction"]} Wolfe</b> · {w["state"]} · '
            f'<span style="color:var(--ink-2)">pt4 {_esc(p4d)}</span> · {zs}{ups}{rrs} · '
            f'<b style="color:{col}">Q{w.get("quality_total",0)}</b>{split}'
            + (f' · <span style="color:var(--ink-2)" title="bars since point 5 (point 4 while forming) — '
               f'recency is its own field, never baked into Q (D99)">{w["age"]}b '
               f'<b>{w.get("fresh_tier","")}</b></span>' if w.get("age") is not None else '')
            + (f' · <span style="color:var(--ink-2);font-size:11px" title="attention rank = Q × 0.5^(age/60) — '
               f'the current-first sort key (D99)">attn {w["rank_attention"]:g}</span>'
               if w.get("rank_attention") is not None else '')
            + f'<span style="color:var(--ink-3);font-size:11px"> {_esc(w.get("source",""))}</span>'
            f'<span style="color:{col}">{mark}</span></a>')
    out.append('</div>')
    return "".join(out)


def _leg(name, val, ok, rule):
    """One winner-profile leg chip: value + ✓/✗, tooltip = the rule (D98 watch)."""
    if val is None:
        return ''
    col = 'var(--up)' if ok else 'var(--down)'
    return (f'<span style="color:{col};white-space:nowrap" title="{rule}">'
            f'{name}{val:g}{"✓" if ok else "✗"}</span>')


def _fail_legs(r):
    """Why-it-fails chips for a structure-watch row: the THREE profile legs (D/p1/F)
    with pass-fail state; C (zone landing) shown muted as CONTEXT — it is NOT a leg
    of the validated filter (panel condition, D98)."""
    d, p1, fz, c = r.get("D"), r.get("p1"), r.get("F"), r.get("C")
    parts = [_leg('D', d, d is not None and d <= 1,
                  'winner profile needs D ≤ 1 — upside to EPA under 20% (reachable)'),
             _leg('p1', p1, p1 is not None and p1 >= 2,
                  'winner profile needs p1 ≥ 2 — a strong fractal point-1'),
             _leg('F', fz, fz is not None and fz <= 2,
                  'winner profile needs F ≤ 2 — not the narrowest zone')]
    if c is not None:
        parts.append(f'<span style="color:var(--ink-3)" '
                     f'title="point-5 zone landing — context, NOT a profile leg">C{c:g}</span>')
    if (d is not None and d <= 1 and p1 is not None and p1 >= 2
            and fz is not None and fz <= 2 and r.get("zlo") is None):
        parts.append('<span style="color:#d29922" title="passes all three profile legs but has '
                     'no fib confluence — the scanner requires the zone (it is the entry/stop)">'
                     'zone-less winner</span>')
    return '&nbsp; '.join(p for p in parts if p)


@router.get("/dash/wolfe/scan", response_class=HTMLResponse)
def wolfe_scan(universe: str = Query("nifty500", max_length=24),
               fresh: int = Query(15, ge=1, le=180),
               asof: str = Query("", max_length=12),
               refresh: int = Query(0, ge=0, le=1),
               wall: int = Query(0, ge=0, le=1)):
    """The winner-profile SCANNER — the OOS-validated reachable-EPA edge across the universe.
    Each row is clickable → /dash/wolfe?sym=…&pick=winner (draws that stock's winner wave).

    Reads the nightly-persisted snapshot (wolfe_signals) for an INSTANT page; falls back to
    a live winner_scan when there's no snapshot, when `?refresh=1`, or for an `?asof=` replay
    (PIT replays are always computed live)."""
    uni = universe or "nifty500"
    cached = None
    with get_conn() as conn:
        if not refresh and not asof:
            cached = wolfe.latest_scan(conn, universe=uni)
        if cached:
            cands, eff_fresh = cached["rows"], cached.get("fresh") or fresh
        else:
            cands = wolfe.winner_scan(conn, universe=uni, fresh=fresh, asof=(asof or None))
            eff_fresh = fresh
        # D98 structure watch — nightly snapshot only (no ~30s live fallback);
        # an ?asof= replay hides it (the watch snapshot is not PIT-replayable).
        watch = wolfe.latest_watch(conn, universe=uni) if not asof else None
    nin = sum(1 for c in cands if c["in_zone"])
    trs = []
    for c in cands:
        col = _UP_VAR if c["dir"] == "BULL" else _DN_VAR
        tag = ('<span style="color:var(--up);font-size:11px" title="OOS-validated regime-robust long selection edge">✓ edge</span>'
               if c["dir"] == "BULL" else
               '<span style="color:#d29922;font-size:11px" title="regime-dependent / tail-only — reliable mainly when the broad tape is already weak; not a standalone edge">⚠ tail</span>')
        t1s = _fmt(c["t1"]) if c["t1"] else "—"
        status = ('<span style="color:var(--up);font-weight:700">● IN</span>' if c["in_zone"]
                  else '<span style="color:var(--ink-3)">watch</span>')
        trs.append(
            # CL-VIEW-09: the symbol sits in a single-quoted JS string inside a double-
            # quoted attribute. SAFETY INVARIANT: _q (urllib quote_plus) percent-encodes,
            # so the value can never contain `'`, `"` or whitespace to break out. Do NOT
            # swap _q for _esc here — _esc leaves quotes/spaces intact and would break the JS.
            f'<tr onclick="location.href=\'/dash/wolfe?sym={_q(c["sym"])}&pick=winner\'" '
            f'style="cursor:pointer;border-top:1px solid var(--line-2)" '
            f'onmouseover="this.style.background=\'#1c2430\'" onmouseout="this.style.background=\'transparent\'">'
            f'<td style="padding:6px 10px"><b style="color:{col}">{_esc(c["sym"])}</b></td>'
            f'<td style="color:{col};font-weight:600">{c["dir"]}<br>{tag}</td>'
            f'<td>{status}</td><td style="color:var(--ink-2)">{c["age"]}d</td>'
            f'<td>{_fmt(c["cmp"])}</td><td>{_fmt(c["zlo"])}–{_fmt(c["zhi"])}</td>'
            f'<td style="color:var(--down)">{_fmt(c["sl"])}</td>'
            f'<td>{t1s}</td><td style="color:var(--up)">{_fmt(c["epa"])}</td>'
            f'<td>{c["up"]:.0f}%</td>'
            f'<td style="color:var(--ink-2)" title="§B read-quality, split STR (shape: p1×2+B+H, max 11) '
            f'+ LND (landing: C+F+G+I+D, max 13). ⚠ LND inverts as a trade filter — the validated profile '
            f'prefers LOW D/F, so winners here show low LND by design.">Q{c["Q"]:g}'
            + (f' <span style="color:var(--ink-3);font-size:11px">= {c["str"]:g}+{c["lnd"]:g}</span>'
               if c.get("str") is not None else '')
            + '</td></tr>')
    if not cands:
        trs = ['<tr><td colspan="11" style="padding:14px;color:var(--ink-2)">No fresh winner-profile setups right now — '
               'try <a href="/dash/wolfe/scan?fresh=30" style="color:#58a6ff">fresh 30</a> or '
               '<a href="/dash/wolfe/scan?universe=inclusive" style="color:#58a6ff">the wider universe</a>.</td></tr>']
    head = ('symbol', 'dir', 'status', 'age', 'CMP', 'entry zone', 'stop', 'T1', 'EPA', 'up', 'Q = STR+LND')
    # ---- D98: STRUCTURE WATCH — the scan's complement (descriptive, NO edge) ---- #
    wrows_all = (watch or {}).get("rows") or []
    _WATCH_SHOW = 30          # default display slice — NEVER a silent cap (counted link below)
    wrows = wrows_all if wall else wrows_all[:_WATCH_SHOW]
    wtrs = []
    for r in wrows:
        col = _UP_VAR if r["dir"] == "BULL" else _DN_VAR
        zone = (f'{_fmt(r["zlo"])}–{_fmt(r["zhi"])}' if r["zlo"] is not None else
                '<span style="color:var(--ink-3)" title="no fib-extension confluence — the '
                'legs&#39; 1-2 and 3-4 grids never agree within 2%">no zone</span>')
        split = (f'{r["str"]:g}/11 · {r["lnd"]:g}/13' if r.get("str") is not None else '—')
        qv = f'{r["Q"]:g}' if r.get("Q") is not None else '—'
        wtrs.append(
            f'<tr onclick="location.href=\'/dash/wolfe?sym={_q(r["sym"])}&pick=watch\'" '
            f'style="cursor:pointer;border-top:1px solid var(--line-2)" '
            f'onmouseover="this.style.background=\'#1c2430\'" onmouseout="this.style.background=\'transparent\'">'
            f'<td style="padding:6px 10px"><b style="color:{col}">{_esc(r["sym"])}</b></td>'
            f'<td style="color:{col};font-weight:600">{r["dir"]}</td>'
            f'<td style="color:var(--ink-2)">{r["age"]}d</td>'
            f'<td>{_fmt(r["cmp"])}</td><td>{zone}</td>'
            f'<td style="color:var(--ink-2)">{_fmt(r["epa"])}</td>'
            f'<td style="color:var(--ink-2)">{r["up"]:.0f}%</td>'
            f'<td title="§B split — STR = shape (p1×2 + pts-2/3/4 + rail), LND = landing '
            f'(C zone · F gap · G 4.618 · I RSI · D upside)">Q{qv} = <b>{split}</b></td>'
            f'<td style="font-size:12px">{_fail_legs(r)}</td></tr>')
    whead = ('symbol', 'dir', 'age', 'CMP', 'fib zone', 'EPA', 'EPA dist', 'Q = STR+LND', 'why not in the scan')
    watch_html = (
        '<h3 style="margin:26px 0 4px">Structure watch '
        '<span style="color:var(--ink-2);font-size:14px;font-weight:400">— textbook shape, no validated edge</span></h3>'
        '<div class="sub" style="margin-bottom:6px">Fresh confirmed waves whose <b>shape</b> is near-perfect '
        '(STR ≥ 10/11) but which the scanner above does not show — the edge filter&#39;s rejects, listed so a '
        'textbook wedge is never invisible (the TCS Jul-01 miss, D96/D98). <b>No edge claim:</b> the raw Wolfe '
        'lens is falsified as a trade signal (median −2% net per trade — a tail game); only the winner profile '
        'above carries the validated edge. Each row shows <b>why</b> it is not on the scan: the three profile '
        'legs D · p1 · F with ✓/✗ (C is context, not a leg). <b>EPA dist</b> = distance from CMP to the EPA '
        'target (far EPA = the D✗ that usually fails these). Sorted freshest-first, never by Q. '
        '<i>Descriptive — a reading surface, not a signal.</i></div>'
        + (
            f'<div style="color:var(--ink-2);font-size:13px;margin-bottom:8px">'
            f'<b>{len(wrows_all)}</b> waves (one per symbol+direction) · as-of '
            f'<b>{_esc((watch or {}).get("scan_date") or "—")}</b> '
            f'<span style="color:var(--ink-3)">(nightly snapshot — ↻ refresh above applies to the scanner only)</span>'
            + (f' · showing the {len(wrows)} freshest — '
               f'<a href="/dash/wolfe/scan?universe={_q(uni)}&amp;wall=1" style="color:#58a6ff">show all {len(wrows_all)}</a>'
               if len(wrows_all) > len(wrows) else '')
            + '</div>'
            '<table style="width:100%;border-collapse:collapse;font-size:13px">'
            '<thead><tr style="color:var(--ink-2);text-align:left">'
            + "".join(f'<th style="padding:6px 10px">{h}</th>' for h in whead)
            + '</tr></thead><tbody>'
            + ("".join(wtrs) or '<tr><td colspan="9" style="padding:12px;color:var(--ink-2)">'
                                'No fresh strong-shape rejects right now.</td></tr>')
            + '</tbody></table>'
            if watch is not None else
            '<div style="color:var(--ink-3);font-size:13px">Snapshot pending — the nightly Wolfe scan '
            '(16:00 UTC) materialises the watch; until then this section is empty'
            + (' (PIT replays show the scanner only).' if asof else '.') + '</div>'
        ))
    body = (
        '<h2>Wolfe scanner <span style="color:var(--ink-2);font-size:15px;font-weight:400">— winner-profile, read by side</span></h2>'
        '<div class="sub" style="margin-bottom:6px">Selection — <b>reachable EPA + strong point-1 + not-narrowest '
        'zone</b> — that survived <b>true out-of-sample</b> (fit 2004-14 / tested untouched 2015-26, survivorship-aware) '
        'plus a beta/regime control. <b>Read by side:</b> '
        '<span style="color:var(--up);font-weight:600">BULL ✓ edge</span> = a regime-robust long selection edge (holds '
        'even when the market falls); '
        '<span style="color:#d29922;font-weight:600">BEAR ⚠ tail</span> = regime-dependent / tail-only — reliable '
        'mainly when the broad tape is already weak, not on its own. The edge is in the <b>selection</b>, not the '
        'stop/target. <b>Click a row</b> to see its wave on the chart. '
        '<span style="color:var(--up)">● IN</span> = price in the entry zone now. Setups with no fib-extension '
        'confluence cannot be listed here (the zone is the entry/stop) — strong-shape ones surface in the '
        'Structure watch below. <i>Descriptive — not a buy/sell signal.</i></div>'
        f'<div style="color:var(--ink-2);font-size:13px;margin-bottom:10px">{_esc(universe)} · '
        + (f'as-of <b>{_esc(cached["scan_date"] or "—")}</b> '
           f'<span style="color:var(--ink-3)">(nightly snapshot{(" · computed " + _esc(cached["computed_at"][:16])) if cached.get("computed_at") else ""})</span> · '
           f'<a href="/dash/wolfe/scan?universe={_q(uni)}&amp;refresh=1" style="color:#58a6ff" title="recompute live now">↻ refresh</a>'
           if cached else
           f'as-of {_esc(asof or "today")} <span style="color:var(--ink-3)">(live)</span>')
        + f' · fresh ≤ {eff_fresh} bars · <b>{len(cands)} candidates · {nin} actionable now</b>'
        ' &nbsp;|&nbsp; <a href="/dash/wolfe/scan?universe=inclusive" style="color:#58a6ff">inclusive</a>'
        ' · <a href="/dash/wolfe/scan?fresh=30" style="color:#58a6ff">fresh 30</a>'
        ' &nbsp;|&nbsp; <a href="/dash/harmonic" style="color:#f778ba">Harmonic scanner ›</a></div>'
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<thead><tr style="color:var(--ink-2);text-align:left">'
        + "".join(f'<th style="padding:6px 10px">{h}</th>' for h in head)
        + '</tr></thead><tbody>' + "".join(trs) + '</tbody></table>'
        + watch_html)
    return HTMLResponse(_shell("Wolfe scanner", body, "wolfe", wide=True))


@router.get("/dash/wolfe", response_class=HTMLResponse)
def wolfe_page(sym: str = Query("", max_length=24),
               idx: str = Query("", max_length=48),
               w: int = Query(0, ge=0),
               pick: str = Query("", max_length=12),
               sort: str = Query("", max_length=12)):
    sym = sym.strip().upper()
    idx = idx.strip()
    sort = "q" if sort == "q" else ""          # D99: default = current-first (attention)
    if not sym and not idx:
        body = ('<h2>Wolfe wave</h2>'
                '<div class="sub">Pick a stock or index, or open the '
                '<a href="/dash/wolfe/scan" style="color:#58a6ff">winner-profile scanner ›</a>. '
                'The detector ranks every 1·3·5 setup; the chart draws the selected one.</div>' + _form())
        return HTMLResponse(_shell("Wolfe wave", body, "wolfe"))

    with get_conn() as conn:
        d = wolfe.analyze(conn, sym=sym or None, idx=idx or None,
                          sort=("q" if sort == "q" else "attention"))
    if not d:
        body = (f'<h2>Wolfe wave</h2><div class="empty">No price history for '
                f'<b>{_esc(sym or idx)}</b>.</div>' + _form(sym, idx))
        return HTMLResponse(_shell("Wolfe wave", body, "wolfe"))

    if pick == "winner" and d.get("waves"):       # from the scanner → draw the freshest winner-profile setup
        wps = [(i, ww) for i, ww in enumerate(d["waves"]) if wolfe.is_winner_profile(ww.get("score"))]
        if wps:
            w = max(wps, key=lambda iw: iw[1]["pivots"][3]["idx"])[0]
    elif pick == "watch" and d.get("waves"):      # from the structure watch → the freshest strong-shape confirmed wave
        wps = [(i, ww) for i, ww in enumerate(d["waves"])
               if ww["state"] == "CONFIRMED" and ww.get("p5")
               and (wolfe.score_split(ww.get("score"))[0] or 0) >= wolfe._WATCH_MIN_STRUCTURE]
        if wps:
            w = max(wps, key=lambda iw: iw[1]["p5"]["idx"])[0]

    body = (
        f'<h2>{_esc(d["label"])} — Wolfe wave</h2>'
        + _form(sym, idx)
        + _summary(d, w, sym, idx, sort)
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


# Mount the sibling HARMONIC lane (D72) onto THIS already-included router, so /dash/harmonic
# + /dash/harmonic/overlay go live without a main.py edit and survive a redeploy (committed).
# Harmonic and Wolfe are siblings (both XABCD-family geometric patterns) — see
# docs/harmonic-pattern-design.md.
try:
    from src.web.harmonic_view import router as _harmonic_router
    router.include_router(_harmonic_router)
except Exception:  # pragma: no cover - never let the harmonic lane break the Wolfe routes
    pass

# Mount the server-side DRAWING STORE (/dash/drawings GET+POST) onto THIS router too,
# so the on-chart drawing engine's persistence goes live without a main.py edit and
# survives a redeploy (committed) — same durable include pattern as harmonic above.
try:
    from src.web.drawings_store import router as _drawings_router
    router.include_router(_drawings_router)
except Exception:  # pragma: no cover - never let the drawing store break the Wolfe routes
    pass
