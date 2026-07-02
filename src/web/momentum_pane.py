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


# ── DB fetch (defensive; uses the already-computed nightly series) ─────────────
def _fetch(sym: str, conn):
    """(dates, rs_line[], rsi[]) or None. Prefers rs_extras (rs_ratio + rsi_of_rs), falls
    back to stock_signals (rs_vs_broad_today + rsi_of_rs). Defensive: any miss → None →
    empty-state, so a host page can never break."""
    try:
        rows = conn.execute(
            "SELECT trade_date, rs_ratio, rsi_of_rs FROM rs_extras "
            "WHERE numerator=? AND denominator='Nifty 500' "
            "AND rs_ratio IS NOT NULL AND rsi_of_rs IS NOT NULL ORDER BY trade_date",
            (sym,)).fetchall()
    except Exception:  # noqa: BLE001
        rows = []
    if len(rows) >= 8:
        return ([r[0] for r in rows], [float(r[1]) for r in rows], [float(r[2]) for r in rows])
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_signals)").fetchall()}
    except Exception:  # noqa: BLE001
        return None
    rs_col = next((c for c in ("rs_vs_broad_today", "rs_vs_broad", "rs_ratio") if c in cols), None)
    if "rsi_of_rs" not in cols or rs_col is None:
        return None
    try:
        rows = conn.execute(
            f"SELECT trade_date, {rs_col}, rsi_of_rs FROM stock_signals "
            f"WHERE symbol=? AND {rs_col} IS NOT NULL AND rsi_of_rs IS NOT NULL "
            f"ORDER BY trade_date", (sym,)).fetchall()
    except Exception:  # noqa: BLE001
        return None
    if len(rows) < 8:
        return None
    return ([r[0] for r in rows], [float(r[1]) for r in rows], [float(r[2]) for r in rows])


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
    tag_block = ""
    if div.get("type"):
        col = _DIV_COL[div["type"]]
        tag_block = (f'<div style="margin:0 0 8px"><span class="pill" '
                     f'style="border-color:{col};color:{col}">'
                     f'{div["type"].title()} divergence — early</span></div>')
    return (
        '<div class="card">'
        f'<div class="h2" style="margin:0 0 2px">{_esc(sym)} — RS momentum</div>'
        '<div class="sub" style="margin:0 0 8px">RSI of the RS line — momentum turns '
        'before price. <b>Descriptive.</b></div>'
        f'{tag_block}{pane_svg(dates, rs, rsi, div)}'
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
