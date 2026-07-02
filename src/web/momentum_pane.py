"""RSI-of-RS momentum pane + RS/RSI divergence — the momentum layer of the
RS-momentum-divergence roadmap (docs/rs-momentum-divergence-roadmap.md, Phase 1).

SURGICAL + ADDITIVE + ISOLATED (the credibility_fingerprint.py / rsband_view.py
pattern): a self-contained module with ZERO edits to existing files. It renders the
RSI-of-RS oscillator docked UNDER the RS line and auto-marks divergences (RS lower-low
while RSI higher-low = bullish/early recovery; the mirror on highs = bearish/early
rolling-over). Server-rendered SVG (no chart-engine coupling → cannot break the price
chart). Pure renderer + divergence detector are dependency-free + self-tested; the DB
fetch is defensive and degrades to an empty-state, so it can never break a host page.

Data (already computed nightly — no new compute for Phase 1):
  * rs_extras(numerator, denominator='Nifty 500') → rs_ratio + rsi_of_rs (sectors/indices)
  * stock_signals(symbol) → rs_vs_broad_today (the RS line) + rsi_of_rs (stocks)
Design follows the client-grade conventions from the best-in-class audit: 30/50/70
banding, dashed DIRECTIONAL divergence line (green bull / red bear), hover gloss.

DESCRIPTIVE ONLY — momentum/divergence characterization, never a buy signal.

Public API:
    detect_divergence(rs, rsi)      -> {'type': 'bullish'|'bearish'|None, 'i1','i2'}
    pane_svg(dates, rs, rsi, div)   -> the two-pane SVG (RS line + RSI oscillator)
    card_html(sym, conn=…)          -> dossier-embeddable card (fetches; empty-state safe)
    router  (GET /dash/momentum)    -> standalone page (mounted via v2_surfaces)
"""
from __future__ import annotations

import html
from contextlib import nullcontext

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

_DIV_COL = {"bullish": "var(--up)", "bearish": "var(--down)"}
_DIV_GLOSS = {"bullish": "RS lower low, RSI higher low — early turn up",
              "bearish": "RS higher high, RSI lower high — early roll-over"}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


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
    """Compare the last two RS pivots against RSI-of-RS at those pivots. Bullish: RS
    LOWER low but RSI HIGHER low. Bearish: RS HIGHER high but RSI LOWER high. Returns
    the more recent of the two (same heuristic as rrg._divergence)."""
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


# ── the two-pane renderer (RS line on top, RSI-of-RS oscillator beneath) ───────
def pane_svg(dates, rs, rsi, div: dict | None = None) -> str:
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

    out = ['<svg width="100%" viewBox="0 0 728 316" role="img" '
           'xmlns="http://www.w3.org/2000/svg" '
           'aria-label="RS line with RSI-of-RS oscillator and divergence">']
    out.append('<text x="44" y="16" style="fill:var(--ink-2);font:400 12px system-ui">'
               'RS vs Nifty 500</text>')
    out.append('<text x="44" y="170" style="fill:var(--ink-2);font:400 12px system-ui">'
               'RSI of RS · 0–100</text>')
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


# ── horizon sweep + staged recovery (compact, on-read; space-optimal) ─────────
_HZ = ((5, "1w"), (10, "2w"), (21, "1m"), (63, "3m"), (126, "6m"), (252, "12m"))


def _rs_pcts(rs):
    """[(label, %Δ of the RS line over the horizon), …] — RS %Δ = beat/lag vs Nifty."""
    out = []
    for n, lab in _HZ:
        v = (rs[-1] / rs[-1 - n] - 1.0) * 100.0 if len(rs) > n and rs[-1 - n] else None
        out.append((lab, v))
    return out


def _stage(pcts):
    """Staged recovery from the sweep: a turn climbs 1w→2w→1m→3m→6m/12m."""
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
           'aria-label="RS beat or lag vs Nifty across horizons">']
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


# ── RS series + on-read RSI ───────────────────────────────────────────────────
# SPACE-OPTIMAL (mandatory rule): the RS line is ALREADY fully stored
# (stock_signals.rs_vs_broad_today, ratio_rows.ratio); RSI is trivially derivable, so we
# COMPUTE it on-read and store NOTHING. Storing RSI across ~5.9M rows would add GBs to the
# 16GB production DB for zero information gain. Derivable series are never persisted.
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


def _rs_series(sym: str, conn, *, window: int = 180):
    """Trailing (dates, rs_line[]) from the already-populated RS series: stocks →
    stock_signals.rs_vs_broad_today ; sectors/indices → ratio_rows.ratio (vs Nifty 500).
    None if neither has enough history. Pure read — no storage."""
    for sql, args in (
        ("SELECT trade_date, rs_vs_broad_today FROM stock_signals "
         "WHERE symbol=? AND rs_vs_broad_today IS NOT NULL ORDER BY trade_date", (sym,)),
        ("SELECT trade_date, ratio FROM ratio_rows "
         "WHERE numerator=? AND denominator='Nifty 500' AND ratio IS NOT NULL "
         "ORDER BY trade_date", (sym,)),
    ):
        try:
            rows = conn.execute(sql, args).fetchall()
        except Exception:  # noqa: BLE001
            rows = []
        if len(rows) >= 30:
            rows = rows[-window:] if window else rows
            return ([r[0] for r in rows], [float(r[1]) for r in rows])
    return None


def _fetch(sym: str, conn, *, period: int = 14, window: int = 180):
    """(dates, rs_line[], rsi[]) or None — RSI computed on-read (Wilder) from the RS line."""
    ser = _rs_series(sym, conn, window=window)
    if ser is None:
        return None
    dates, rs = ser
    rsi = _wilder_rsi(rs, period)
    idx = [i for i in range(len(rs)) if rsi[i] is not None]
    if len(idx) < 8:
        return None
    return ([dates[i] for i in idx], [rs[i] for i in idx], [rsi[i] for i in idx])


def card_html(sym: str, conn=None) -> str:
    """Dossier-embeddable card. Safe to call with or without a live connection."""
    sym = (sym or "").strip().upper()
    cm = nullcontext(conn) if conn is not None else _open()
    with cm as c:
        data = _fetch(sym, c) if c is not None else None
    if not data:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">'
                f'{_esc(sym)} — RS momentum</div><div class="sub" style="margin:0">'
                'No RS/RSI series on record for this name yet (needs the nightly RS '
                'compute). This card is inert until then — it changes nothing.</div></div>')
    dates, rs, rsi = data
    div = detect_divergence(rs, rsi)
    st, stcol = _stage(_rs_pcts(rs))
    pills = [f'<span class="pill" style="border-color:{stcol};color:{stcol}">Stage: {_esc(st)}</span>']
    if div.get("type"):
        col = _DIV_COL[div["type"]]
        pills.append(f'<span class="pill" style="border-color:{col};color:{col}">'
                     f'{div["type"].title()} divergence — early</span>')
    return (
        '<div class="card">'
        f'<div class="h2" style="margin:0 0 2px">{_esc(sym)} — RS momentum</div>'
        '<div class="sub" style="margin:0 0 8px">Beat/lag vs Nifty by horizon, RSI of the RS '
        'line, and RS/RSI divergence — momentum turns before price. <b>Descriptive.</b></div>'
        f'<div style="margin:0 0 6px">{" ".join(pills)}</div>'
        f'{horizon_strip_svg(rs)}'
        f'{pane_svg(dates, rs, rsi, div)}'
        '</div>'
    )


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/momentum", response_class=HTMLResponse)
def momentum_page(sym: str = Query("")):
    sym = (sym or "").strip().upper()
    body = card_html(sym) if sym else (
        '<div class="card"><div class="h2">RS momentum</div>'
        '<div class="sub">Pass ?sym=TICKER.</div></div>')
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell(f"{sym} — RS momentum" if sym else "RS momentum",
                                   body, active="markets", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    rs = [10, 9, 8, 7, 6, 7, 8, 7, 6, 5, 6, 7, 8]
    rsi = [40, 36, 33, 30, 28, 33, 38, 35, 33, 34, 40, 45, 50]
    d = detect_divergence(rs, rsi)
    assert d["type"] == "bullish", d
    assert pane_svg(list(range(len(rs))), rs, rsi, d).startswith("<svg")
    assert detect_divergence([1, 2, 3], [1, 2, 3])["type"] is None
    assert '<div class="card"' in card_html("NOSUCHSYM")   # empty-state, no crash
    print("momentum_pane selftest: OK")


if __name__ == "__main__":
    _selftest()
