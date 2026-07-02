"""RS momentum pane — RSI-of-RS + divergence + per-stock RRG four-quadrant + benchmark
switch (roadmap Phase 1, enhanced 2026-07-02 per Ramana's dossier feedback).

Gives a STOCK the SAME rotation analysis the index gets: RS vs a chosen benchmark
(Nifty 500 · its OWN SECTOR · Nifty 50), the four-quadrant RRG (Leading / Improving /
Weakening / Lagging — "is it a leader?"), the RSI-of-RS oscillator (with the live value
+ dated x-axis) and RS/RSI divergence. Isolated, server-SVG, on-read (space rule: the RS
line is stored; RSI/RRG are computed, stored NOWHERE). Reuses rrg._rs_ratio_momentum +
mini_rrg — the exact engine behind the index RRG. DESCRIPTIVE only.

Public: detect_divergence · pane_svg · card_html(sym, conn=…, bench=…) · router(/dash/momentum)
"""
from __future__ import annotations

import html
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

_DIV_COL = {"bullish": "var(--up)", "bearish": "var(--down)"}
_DIV_GLOSS = {"bullish": "RS lower low, RSI higher low — early turn up",
              "bearish": "RS higher high, RSI lower high — early roll-over"}
# RRG quadrant → (label, colour, plain-English "is it a leader?")
_QV = {"Leading":   ("Leader", "var(--up)", "strong & strengthening"),
       "Improving": ("Improving", "var(--accent)", "weak but strengthening — early turn"),
       "Weakening": ("Weakening", "var(--warn)", "strong but fading"),
       "Lagging":   ("Lagging", "var(--down)", "weak & weakening")}
_BENCHES = (("broad", "Nifty 500"), ("sector", "Sector"), ("nifty50", "Nifty 50"))


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _short(nm: str) -> str:
    return str(nm).replace("Nifty ", "").replace(" Index", "")


# ── divergence detection (pure) ───────────────────────────────────────────────
def _pivots(y, kind: str, w: int) -> list[int]:
    out = []
    for i in range(w, len(y) - w):
        seg = y[i - w:i + w + 1]
        if kind == "low" and y[i] == min(seg):
            out.append(i)
        elif kind == "high" and y[i] == max(seg):
            out.append(i)
    return out


def detect_divergence(rs, rsi, *, w: int = 3) -> dict:
    if not rs or len(rs) != len(rsi) or len(rs) < (2 * w + 2):
        return {"type": None}
    cands = []
    lows = _pivots(rs, "low", w)
    if len(lows) >= 2 and rs[lows[-1]] < rs[lows[-2]] and rsi[lows[-1]] > rsi[lows[-2]]:
        cands.append({"type": "bullish", "i1": lows[-2], "i2": lows[-1]})
    highs = _pivots(rs, "high", w)
    if len(highs) >= 2 and rs[highs[-1]] > rs[highs[-2]] and rsi[highs[-1]] < rsi[highs[-2]]:
        cands.append({"type": "bearish", "i1": highs[-2], "i2": highs[-1]})
    if not cands:
        return {"type": None}
    return max(cands, key=lambda c: c["i2"])


# ── the two-pane renderer (RS line + RSI oscillator, dated x-axis, live RSI) ────
def pane_svg(dates, rs, rsi, div: dict | None = None, label: str = "Nifty 500") -> str:
    n = len(rs or [])
    if n < 2 or len(rsi or []) != n:
        return ""
    div = div or {"type": None}
    L, R = 44, 704
    rs_top, rs_bot = 24, 150
    ri_top, ri_bot = 176, 300

    def X(i):
        return L + (R - L) * i / (n - 1)

    lo, hi = min(rs), max(rs)
    rng = (hi - lo) or 1.0

    def Yrs(v):
        return rs_bot - (v - lo) / rng * (rs_bot - rs_top)

    def Yri(v):
        v = max(0.0, min(100.0, v))
        return ri_bot - v / 100.0 * (ri_bot - ri_top)

    out = ['<svg width="100%" viewBox="0 0 728 334" role="img" '
           'xmlns="http://www.w3.org/2000/svg" '
           f'aria-label="RS line vs {_esc(label)} with RSI-of-RS oscillator, divergence and dates">']
    out.append(f'<text x="44" y="16" style="fill:var(--ink-2);font:400 12px system-ui">'
               f'RS vs {_esc(label)}</text>')
    out.append(f'<text x="44" y="170" style="fill:var(--ink-2);font:400 12px system-ui">'
               f'RSI of RS · 0–100 · <tspan style="fill:#9085e9;font-weight:600">now '
               f'{rsi[-1]:.0f}</tspan></text>')
    for lvl in (70, 50, 30):
        y = Yri(lvl)
        out.append(f'<line x1="{L}" y1="{y:.0f}" x2="{R}" y2="{y:.0f}" '
                   f'style="stroke:var(--line);stroke-width:0.5" stroke-dasharray="3 3"/>')
        out.append(f'<text x="{R + 6}" y="{y + 3:.0f}" '
                   f'style="fill:var(--ink-3);font:400 11px system-ui">{lvl}</text>')
    rs_pts = " ".join(f'{X(i):.1f},{Yrs(rs[i]):.1f}' for i in range(n))
    ri_pts = " ".join(f'{X(i):.1f},{Yri(rsi[i]):.1f}' for i in range(n))
    out.append(f'<polyline points="{rs_pts}" style="fill:none;stroke:#2a78d6;stroke-width:2"/>')
    out.append(f'<polyline points="{ri_pts}" style="fill:none;stroke:#9085e9;stroke-width:2"/>')
    # live end-dots + the RSI value on the chart
    out.append(f'<circle cx="{X(n - 1):.1f}" cy="{Yrs(rs[-1]):.1f}" r="3.5" style="fill:#2a78d6"/>')
    out.append(f'<circle cx="{X(n - 1):.1f}" cy="{Yri(rsi[-1]):.1f}" r="3.5" style="fill:#9085e9"/>')
    out.append(f'<text x="{X(n - 1) - 6:.1f}" y="{Yri(rsi[-1]) - 6:.1f}" text-anchor="end" '
               f'style="fill:#9085e9;font:600 11px system-ui">{rsi[-1]:.0f}</text>')
    # dated x-axis (shared): ~5 ticks, YYYY-MM
    ticks = sorted({0, n // 4, n // 2, 3 * n // 4, n - 1})
    for i in ticks:
        out.append(f'<text x="{X(i):.1f}" y="326" text-anchor="middle" '
                   f'style="fill:var(--ink-3);font:400 10px system-ui">{_esc(str(dates[i])[:7])}</text>')
    if div.get("type"):
        col = _DIV_COL[div["type"]]
        for key in ("i1", "i2"):
            i = div[key]
            out.append(f'<circle cx="{X(i):.1f}" cy="{Yrs(rs[i]):.1f}" r="4" style="fill:{col}"/>')
            out.append(f'<circle cx="{X(i):.1f}" cy="{Yri(rsi[i]):.1f}" r="4" style="fill:{col}"/>')
        xi = X(div["i2"])
        gloss = _esc(_DIV_GLOSS[div["type"]])
        out.append(f'<line x1="{xi:.1f}" y1="{Yrs(rs[div["i2"]]):.1f}" '
                   f'x2="{xi:.1f}" y2="{Yri(rsi[div["i2"]]):.1f}" '
                   f'style="stroke:{col};stroke-width:1.2;stroke-opacity:0.7" '
                   f'stroke-dasharray="4 2"><title>{gloss}</title></line>')
        out.append(f'<text x="{xi + 8:.1f}" y="164" '
                   f'style="fill:{col};font:500 12px system-ui">{div["type"]} divergence</text>')
    out.append('</svg>')
    return "".join(out)


# ── horizon sweep + staged recovery (beat/lag vs the CHOSEN benchmark) ─────────
_HZ = ((5, "1w"), (10, "2w"), (21, "1m"), (63, "3m"), (126, "6m"), (252, "12m"))


def _rs_pcts(rs):
    out = []
    for n, lab in _HZ:
        v = (rs[-1] / rs[-1 - n] - 1.0) * 100.0 if len(rs) > n and rs[-1 - n] else None
        out.append((lab, v))
    return out


def _stage(pcts):
    d = dict(pcts)

    def beat(l):
        return (d.get(l) or 0) > 0
    if beat("1m") and beat("3m") and beat("1w"):
        return ("Leading", "var(--up)") if beat("6m") and beat("12m") else ("Confirmed", "var(--up)")
    if beat("1m") and beat("1w"):
        return "Recovery", "var(--up)"
    if beat("2w") and beat("1w"):
        return "Building", "var(--warn)"
    if beat("1w"):
        return "Early watch", "var(--warn)"
    return "No turn", "var(--ink-2)"


def horizon_strip_svg(rs) -> str:
    pcts = _rs_pcts(rs)
    n, W, Lp = len(pcts), 728, 8
    cw = (W - Lp * 2) / n
    out = [f'<svg width="100%" viewBox="0 0 {W} 58" role="img" '
           'aria-label="RS beat or lag vs the benchmark across horizons">']
    for i, (lab, v) in enumerate(pcts):
        x = Lp + i * cw
        col = "var(--up)" if (v is not None and v > 0) else (
            "var(--down)" if v is not None else "var(--line)")
        out.append(f'<rect x="{x + 2:.1f}" y="6" width="{cw - 4:.1f}" height="30" rx="4" '
                   f'style="fill:{col};opacity:0.9"/>')
        txt = f'{v:+.1f}%' if v is not None else "—"
        out.append(f'<text x="{x + cw / 2:.1f}" y="25" text-anchor="middle" '
                   f'style="fill:#fff;font:600 11px system-ui">{txt}</text>')
        out.append(f'<text x="{x + cw / 2:.1f}" y="50" text-anchor="middle" '
                   f'style="fill:var(--ink-3);font:400 11px system-ui">{_esc(lab)}</text>')
    out.append('</svg>')
    return "".join(out)


# ── RS series (per benchmark) + on-read RSI + per-stock RRG ────────────────────
def _wilder_rsi(vals, period: int):
    out = [None] * len(vals)
    if len(vals) <= period:
        return out
    g = l = 0.0
    for i in range(1, period + 1):
        d = vals[i] - vals[i - 1]
        g += max(d, 0.0)
        l += max(-d, 0.0)
    ag, al = g / period, l / period
    out[period] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(period + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def _safe(conn, sql, args):
    try:
        return conn.execute(sql, args).fetchall()
    except Exception:  # noqa: BLE001
        return []


def _bench_series(sym: str, conn, bench: str, *, window: int = 756):
    """(dates, ratio[], bench_label) for the chosen benchmark, or None. Pure read.
    broad→Nifty 500 (stored) · sector→own sector (stored) · nifty50→derived
    (rs_vs_broad × Nifty500/Nifty50). Space rule: nothing persisted."""
    sym = (sym or "").strip().upper()

    def _take(rows, fn, label):
        if len(rows) < 30:
            return None
        rows = rows[-window:] if window else rows
        return ([r[0] for r in rows], [fn(r) for r in rows], label)

    if bench == "sector":
        psec = _safe(conn, "SELECT primary_sector FROM stock_signals WHERE symbol=? AND "
                     "primary_sector IS NOT NULL ORDER BY trade_date DESC LIMIT 1", (sym,))
        label = _short(psec[0][0]) if psec and psec[0][0] else "its sector"
        return _take(_safe(conn, "SELECT trade_date, rs_vs_sector_today FROM stock_signals "
                           "WHERE symbol=? AND rs_vs_sector_today IS NOT NULL ORDER BY trade_date",
                           (sym,)), lambda r: float(r[1]), label)
    if bench == "nifty50":
        return _take(_safe(conn,
                     "SELECT s.trade_date, s.rs_vs_broad_today, i5.close_value, i50.close_value "
                     "FROM stock_signals s "
                     "JOIN index_rows i5 ON i5.index_name='Nifty 500' AND i5.trade_date=s.trade_date "
                     "JOIN index_rows i50 ON i50.index_name='Nifty 50' AND i50.trade_date=s.trade_date "
                     "WHERE s.symbol=? AND s.rs_vs_broad_today IS NOT NULL AND i5.close_value>0 "
                     "AND i50.close_value>0 ORDER BY s.trade_date", (sym,)),
                     lambda r: float(r[1]) * float(r[2]) / float(r[3]), "Nifty 50")
    ser = _take(_safe(conn, "SELECT trade_date, rs_vs_broad_today FROM stock_signals "
                      "WHERE symbol=? AND rs_vs_broad_today IS NOT NULL ORDER BY trade_date",
                      (sym,)), lambda r: float(r[1]), "Nifty 500")
    if ser:
        return ser
    return _take(_safe(conn, "SELECT trade_date, ratio FROM ratio_rows WHERE numerator=? AND "
                       "denominator='Nifty 500' AND ratio IS NOT NULL ORDER BY trade_date",
                       (sym,)), lambda r: float(r[1]), "Nifty 500")


def _rrg(rs):
    """(current_quadrant, tail[{rs_ratio,rs_momentum,quadrant}]) from the RS ratio series —
    the SAME rrg engine the index uses."""
    try:
        from src.automation import rrg
    except Exception:  # noqa: BLE001
        return None, []
    rr, rm = rrg._rs_ratio_momentum(rs)
    tail = [{"trade_date": None, "rs_ratio": rr[i], "rs_momentum": rm[i],
             "quadrant": rrg.quadrant(rr[i], rm[i])}
            for i in range(len(rs)) if rr[i] is not None and rm[i] is not None]
    return (tail[-1]["quadrant"] if tail else None), tail


def _rrg_card(tail, label: str) -> str:
    if len(tail) < 3:
        return ""
    try:
        from src.web.mini_rrg import mini_rrg_card
        return mini_rrg_card(tail, den=label, tail_label=f"rotation vs {label}",
                             max_pts=14, size=200)
    except Exception:  # noqa: BLE001
        return ""


def _bench_toggle(sym: str, active: str) -> str:
    out = []
    for key, lab in _BENCHES:
        on = "border-color:var(--accent);color:var(--accent)" if key == active else ""
        out.append(f'<a class="pill" style="{on}" '
                   f'href="/dash/momentum?sym={quote_plus(sym)}&amp;bench={key}">{lab}</a>')
    return f'<div style="margin:0 0 8px;font-size:12px;color:var(--ink-2)">Compare vs: {" ".join(out)}</div>'


# ── the card ──────────────────────────────────────────────────────────────────
def card_html(sym: str, conn=None, bench: str = "broad") -> str:
    sym = (sym or "").strip().upper()
    bench = bench if bench in ("broad", "sector", "nifty50") else "broad"
    cm = nullcontext(conn) if conn is not None else _open()
    with cm as c:
        ser = _bench_series(sym, c, bench, window=756) if c is not None else None

    if not ser:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">'
                f'{_esc(sym)} — RS momentum</div>'
                f'{_bench_toggle(sym, bench)}'
                '<div class="sub" style="margin:0">No RS series on record for this name vs '
                f'this benchmark yet ({_esc(bench)}). Needs the nightly RS compute.</div></div>')
    dates, rs, label = ser
    rsi = _wilder_rsi(rs, 14)
    vidx = [i for i in range(len(rs)) if rsi[i] is not None]
    if len(vidx) < 8:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">'
                f'{_esc(sym)} — RS momentum vs {_esc(label)}</div>{_bench_toggle(sym, bench)}'
                '<div class="sub" style="margin:0">Not enough history to draw the pane.</div></div>')
    disp = vidx[-180:]
    d_dates = [dates[i] for i in disp]
    d_rs = [rs[i] for i in disp]
    d_rsi = [rsi[i] for i in disp]
    div = detect_divergence(d_rs, d_rsi)
    st, stcol = _stage(_rs_pcts(d_rs))
    quad, tail = _rrg(rs)

    pills = [f'<span class="pill" style="border-color:{stcol};color:{stcol}">Stage: {_esc(st)}</span>']
    qv = _QV.get(quad)
    if qv:
        pills.append(f'<span class="pill" style="border-color:{qv[1]};color:{qv[1]}">'
                     f'{_esc(sym)} is a {qv[0]} vs {_esc(label)} — {qv[2]}</span>')
    pills.append(f'<span class="pill" style="border-color:#9085e9;color:#9085e9">RSI {d_rsi[-1]:.0f}</span>')
    if div.get("type"):
        col = _DIV_COL[div["type"]]
        pills.append(f'<span class="pill" style="border-color:{col};color:{col}">'
                     f'{div["type"].title()} divergence — early</span>')
    return (
        '<div class="card">'
        f'<div class="h2" style="margin:0 0 2px">{_esc(sym)} — RS momentum &amp; rotation vs {_esc(label)}</div>'
        '<div class="sub" style="margin:0 0 8px">Four-quadrant rotation (is it a leader?), beat/lag '
        'by horizon, RSI of the RS line and RS/RSI divergence — momentum turns before price. '
        '<b>Descriptive.</b></div>'
        f'{_bench_toggle(sym, bench)}'
        f'<div style="margin:0 0 8px">{" ".join(pills)}</div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start">'
        f'<div style="flex:0 0 auto">{_rrg_card(tail, label)}</div>'
        f'<div style="flex:1;min-width:280px">{horizon_strip_svg(d_rs)}</div></div>'
        f'{pane_svg(d_dates, d_rs, d_rsi, div, label)}'
        '</div>'
    )


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/momentum", response_class=HTMLResponse)
def momentum_page(sym: str = Query(""), bench: str = Query("broad")):
    sym = (sym or "").strip().upper()
    body = card_html(sym, bench=bench) if sym else (
        '<div class="card"><div class="h2">RS momentum</div>'
        '<div class="sub">Pass ?sym=TICKER (&bench=broad|sector|nifty50).</div></div>')
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell(f"{sym} — RS momentum" if sym else "RS momentum",
                                   body, active="markets", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    import math
    rs = [10, 9, 8, 7, 6, 7, 8, 7, 6, 5, 6, 7, 8]
    rsi = [40, 36, 33, 30, 28, 33, 38, 35, 33, 34, 40, 45, 50]
    d = detect_divergence(rs, rsi)
    assert d["type"] == "bullish", d
    assert pane_svg([f"2026-{i:02d}-01" for i in range(1, 14)], rs, rsi, d, "Sector").startswith("<svg")
    ser = [100 * (1 + 0.0008 * i + 0.03 * math.sin(i / 11)) for i in range(300)]
    q, tail = _rrg(ser)
    assert q in ("Leading", "Improving", "Weakening", "Lagging"), q
    assert '<div class="card"' in card_html("NOSUCHSYM")
    print("momentum_pane selftest: OK")


if __name__ == "__main__":
    _selftest()
