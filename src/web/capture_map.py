"""/dash/capture-map — the up-capture x down-capture "all-weather" map (flagship C).

Two columns in a table hide the DIAGONAL: a sector that takes 110% of the rallies and
115% of the falls is just high-beta, not strong. The scatter shows every index as one
dot against the market crosshair (100/100) and the beta diagonal (up == down), so the
prize quadrant — participates in rallies, defends in falls — is visible pre-attentively,
and the worst-of-both corner can't hide behind a decent up-capture number.

ISOLATED + ADDITIVE (the momentum_pane / divergence_board / cycle_clock pattern):
self-contained router, server-SVG, reads ONLY the nightly ``capture_signals`` snapshot
(no new compute, no storage — honours the space rule). Defensive empty-state.
DESCRIPTIVE — a behaviour track record, never a ranker. Pure read, ₹0, no LLM.

Public: router (GET /dash/capture-map) · map_html(conn, den, h) for embedding.
"""
from __future__ import annotations

import html
from contextlib import nullcontext
from urllib.parse import quote_plus

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.web import glossary as G   # `?` hover-help on the capture terms

router = APIRouter()

_DENS = ("Nifty 500", "Nifty 50")
_HORIZONS = {"63": "3m", "126": "6m", "252": "12m"}

# quadrant vs the market crosshair (up>=1, down<1) → (label, dot colour, blurb).
# Directional tokens are honest here: the quadrants ARE better/worse vs the market.
_QUAD = {
    (True, True):   ("All-weather", "var(--up)", "joins rallies, falls less"),
    (False, True):  ("Low-beta", "var(--ink-2)", "damped both ways"),
    (True, False):  ("High-beta", "var(--warn)", "amplified both ways"),
    (False, False): ("Worst of both", "var(--down)", "lags rallies, falls harder"),
}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _quad(uc: float, dc: float):
    return _QUAD[(uc >= 1.0, dc < 1.0)]


def _fetch(conn, den: str, h: str) -> list[dict]:
    rows = conn.execute(
        f"SELECT numerator, up_capture_{h} uc, down_capture_{h} dc "
        f"FROM capture_signals WHERE denominator=? "
        f"AND trade_date=(SELECT MAX(trade_date) FROM capture_signals WHERE denominator=?)",
        (den, den)).fetchall()
    out = []
    for r in rows:
        uc, dc = r["uc"], r["dc"]
        if uc is None or dc is None or r["numerator"] == den:
            continue
        out.append({"n": r["numerator"], "uc": float(uc), "dc": float(dc),
                    "sp": float(uc) - float(dc)})
    out.sort(key=lambda x: x["sp"], reverse=True)
    return out


def _short(n: str) -> str:
    return n.replace("NIFTY", "Nifty").replace("Nifty ", "").replace(" Index", "")


# ── the scatter (server-SVG; colours in style=, never SVG attributes) ─────────
def _svg(pts: list[dict]) -> str:
    W, H, PAD = 720, 480, 46
    xs = [p["dc"] * 100 for p in pts] + [100.0]
    ys = [p["uc"] * 100 for p in pts] + [100.0]
    x0, x1 = min(xs) - 6, max(xs) + 6
    y0, y1 = min(ys) - 6, max(ys) + 6

    def X(v):
        return PAD + (v - x0) / (x1 - x0) * (W - 2 * PAD)

    def Y(v):
        return H - PAD - (v - y0) / (y1 - y0) * (H - 2 * PAD)

    def _txt(x, y, s, size=10, ink="var(--ink-2)", anchor="middle", w=""):
        wt = f"font-weight:{w};" if w else ""
        return (f'<text x="{x:.0f}" y="{y:.0f}" style="font:{size}px ui-monospace,monospace;'
                f'fill:{ink};{wt}text-anchor:{anchor}">{_esc(s)}</text>')

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
         'style="width:100%;max-width:860px;height:auto;display:block">']
    # prize / hazard quadrant tints (subtle, behind everything)
    o.append(f'<rect x="{X(x0):.0f}" y="{Y(y1):.0f}" width="{X(min(100, x1)) - X(x0):.0f}" '
             f'height="{Y(max(100, y0)) - Y(y1):.0f}" style="fill:rgba(63,185,80,.06)"/>')
    o.append(f'<rect x="{X(max(100, x0)):.0f}" y="{Y(min(100, y1)):.0f}" '
             f'width="{X(x1) - X(max(100, x0)):.0f}" '
             f'height="{Y(y0) - Y(min(100, y1)):.0f}" style="fill:rgba(248,81,73,.06)"/>')
    # the market crosshair (100/100) + the beta diagonal (up == down)
    o.append(f'<line x1="{X(100):.0f}" y1="{Y(y0):.0f}" x2="{X(100):.0f}" y2="{Y(y1):.0f}" '
             'style="stroke:var(--line-2);stroke-dasharray:4 3"/>')
    o.append(f'<line x1="{X(x0):.0f}" y1="{Y(100):.0f}" x2="{X(x1):.0f}" y2="{Y(100):.0f}" '
             'style="stroke:var(--line-2);stroke-dasharray:4 3"/>')
    dlo, dhi = max(x0, y0), min(x1, y1)
    o.append(f'<line x1="{X(dlo):.0f}" y1="{Y(dlo):.0f}" x2="{X(dhi):.0f}" y2="{Y(dhi):.0f}" '
             'style="stroke:var(--line-2)"/>')
    o.append(_txt(X(dhi) - 8, Y(dhi) + 12, "up = down (pure beta)", 9, anchor="end"))
    # quadrant captions
    o.append(_txt(X(x0) + 4, Y(y1) + 12, "ALL-WEATHER — joins up, defends down", 9,
                  "var(--up)", anchor="start", w="700"))
    o.append(_txt(X(x1) - 4, Y(y0) - 6, "WORST OF BOTH", 9, "var(--down)",
                  anchor="end", w="700"))
    # dots (hover title carries the numbers; extremes get inline labels)
    lab_n = {p["n"] for p in pts[:4]} | {p["n"] for p in pts[-3:]}
    for p in pts:
        _, col, blurb = _quad(p["uc"], p["dc"])
        cx, cy = X(p["dc"] * 100), Y(p["uc"] * 100)
        tip = (f'{p["n"]} — up-capture {p["uc"] * 100:.0f}% · down-capture '
               f'{p["dc"] * 100:.0f}% · spread {p["sp"] * 100:+.0f} ({blurb})')
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" '
                 f'style="fill:{col};fill-opacity:.75;stroke:var(--bg-1);stroke-width:1">'
                 f'<title>{_esc(tip)}</title></circle>')
        if p["n"] in lab_n:
            o.append(_txt(cx + 7, cy + 3, _short(p["n"]), 9, "var(--ink-2)", anchor="start"))
    # axes
    o.append(_txt(W / 2, H - 8, "down-capture % of benchmark falls  (left = defends)", 10))
    o.append(f'<text x="14" y="{H / 2:.0f}" transform="rotate(-90 14 {H / 2:.0f})" '
             'style="font:10px ui-monospace,monospace;fill:var(--ink-2);text-anchor:middle">'
             'up-capture % of benchmark rallies  (up = participates)</text>')
    o.append('</svg>')
    return "".join(o)


def _table(pts: list[dict], den: str) -> str:
    head = ("<thead><tr><th>Index</th>"
            f"<th>{G.gloss('Up-capture', 'Up-cap')}</th>"
            f"<th>{G.gloss('Down-capture', 'Down-cap')}</th>"
            f"<th>{G.gloss('Capture spread', 'Spread')}</th>"
            "<th>Read</th></tr></thead>")
    trs = []
    for p in pts:
        q, col, _ = _quad(p["uc"], p["dc"])
        trs.append(
            f'<tr><td><a class="row" href="/dash/rsband?idx={quote_plus(p["n"])}'
            f'&den={quote_plus(den)}">{_esc(_short(p["n"]))}</a></td>'
            f'<td>{p["uc"] * 100:.0f}%</td><td>{p["dc"] * 100:.0f}%</td>'
            f'<td>{p["sp"] * 100:+.0f}</td>'
            f'<td><span class="pill" style="border-color:{col};color:{col}">{q}</span></td></tr>')
    return (f'<div style="max-height:420px;overflow:auto;margin-top:10px">'
            f'<table class="dt" style="width:100%">{head}<tbody>{"".join(trs)}</tbody>'
            '</table></div>')


# ── the reusable body ─────────────────────────────────────────────────────────
def map_html(conn=None, den: str = "Nifty 500", h: str = "63") -> str:
    den = den if den in _DENS else "Nifty 500"
    h = h if h in _HORIZONS else "63"
    cm = nullcontext(conn) if conn is not None else _open()
    with cm as c:
        try:
            pts = _fetch(c, den, h) if c is not None else []
        except Exception:  # noqa: BLE001 — table absent locally → graceful empty-state
            pts = []

    def chips(cur, opts, param, other):
        out = []
        for v, lbl in opts:
            on = " on" if v == cur else ""
            out.append(f'<a class="fbtn{on}" href="/dash/capture-map?{param}='
                       f'{quote_plus(v)}&{other}">{_esc(lbl)}</a>')
        return "".join(out)

    bar = ('<div class="fbar" style="margin:6px 0">'
           + chips(den, [(d, d) for d in _DENS], "den", f"h={h}")
           + '<span style="width:14px;display:inline-block"></span>'
           + chips(h, list(_HORIZONS.items()), "h", f"den={quote_plus(den)}")
           + '</div>')
    sub = ('<div class="sub" style="margin:0 0 8px">Every index dot = how much of the '
           f'benchmark’s rallies and falls it took on over the last {_HORIZONS[h]} '
           '(100 = moved with the market). The prize quadrant joins the rallies and '
           'defends the falls — two table columns hide this diagonal. '
           '<b>Descriptive track record — not a forward signal.</b></div>')
    if not pts:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">All-weather '
                'capture map</div>' + sub + bar +
                '<div class="sub" style="margin:0">No capture snapshot on record for '
                f'{_esc(den)} yet — the nightly RS compute (src/automation/capture.py) '
                'fills <code>capture_signals</code>.</div></div>')
    n_prize = sum(1 for p in pts if p["uc"] >= 1.0 and p["dc"] < 1.0)
    pills = (f'<span class="pill">{len(pts)} indices</span> '
             f'<span class="pill" style="border-color:var(--up);color:var(--up)">'
             f'{n_prize} all-weather</span>')
    return ('<div class="card">'
            '<div class="h2" style="margin:0 0 2px">All-weather capture map</div>'
            + sub + bar + f'<div style="margin:0 0 8px">{pills}</div>'
            + _svg(pts) + _table(pts, den) + '</div>' + G.css())


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/capture-map", response_class=HTMLResponse)
def capture_map_page(den: str = Query("Nifty 500", max_length=40),
                     h: str = Query("63", max_length=4)):
    body = map_html(None, den, h)
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell("All-weather capture map", body,
                                   active="capture-map", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    pts = [{"n": "Nifty IT Index", "uc": 1.12, "dc": 0.84, "sp": 0.28},
           {"n": "Nifty Realty Index", "uc": 0.9, "dc": 1.3, "sp": -0.4}]
    s = _svg(pts)
    assert s.startswith("<svg") and "ALL-WEATHER" in s
    assert 'fill="var(' not in s and 'stroke="var(' not in s   # the screen2 lesson
    assert _quad(1.1, 0.9)[0] == "All-weather" and _quad(0.9, 1.1)[0] == "Worst of both"
    assert "capture map" in map_html(nullcontext(None).__enter__())   # empty-state, no crash
    t = _table(pts, "Nifty 500")
    assert "rsband?idx=Nifty+IT+Index" in t
    print("capture_map selftest: OK")


if __name__ == "__main__":
    _selftest()
