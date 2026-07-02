"""/dash/cycle-clock — the RS rotation LIFECYCLE clock (roadmap flagship B).

Each sector placed on the rotation loop by its RRG coordinates (RS-Ratio × RS-Momentum,
100-centred), coloured by weather-phase, with a clockwise VELOCITY vector whose length ∝
momentum (speed) and a hover RSI-of-RS read. The lifecycle framing (Recovery → Tailwind →
Rolling-over → Headwind, clockwise) complements the RRG scatter: same data, read as a loop
with direction-of-travel, which the 2×2 weather grid throws away.

ISOLATED + ADDITIVE (the momentum_pane / divergence_board pattern): self-contained router,
server-SVG, reads ONLY the already-computed rs_extras snapshot (no new compute, no storage
— honours the space rule). Defensive empty-state. DESCRIPTIVE. Pure read, ₹0, no LLM.

Public: router (GET /dash/cycle-clock) · clock_html(conn) for embedding.
"""
from __future__ import annotations

import html
import math
from contextlib import nullcontext

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_BENCH = "Nifty 500"
# quadrant sign (dx>=0, dy>=0) → (weather label, colour). dx = RS-Ratio-100 (x),
# dy = RS-Momentum-100 (y, up). UR=Leading→Tailwind, UL=Improving→Recovery,
# LL=Lagging→Headwind, LR=Weakening→Rolling-over.
_PHASE = {
    (True, True):  ("Tailwind", "var(--up)"),
    (False, True): ("Recovery", "#7fdcae"),
    (False, False): ("Headwind", "var(--down)"),
    (True, False): ("Rolling-over", "var(--warn)"),
}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _short(nm: str) -> str:
    return str(nm).replace("Nifty ", "").replace(" Index", "")


def _fetch(conn):
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(rs_extras)").fetchall()}
    except Exception:  # noqa: BLE001
        return []
    if not {"numerator", "rs_ratio", "rs_momentum"} <= cols:
        return []
    rsi_sel = "rsi_of_rs" if "rsi_of_rs" in cols else "NULL"
    try:
        rows = conn.execute(
            f"SELECT numerator, rs_ratio, rs_momentum, {rsi_sel} FROM rs_extras "
            f"WHERE denominator=? AND rs_ratio IS NOT NULL AND rs_momentum IS NOT NULL",
            (_BENCH,)).fetchall()
    except Exception:  # noqa: BLE001
        return []
    return [{"n": r[0], "rr": float(r[1]), "mm": float(r[2]), "rsi": r[3]} for r in rows]


def _svg(items) -> str:
    if not items:
        return ""
    cx, cy, R = 340, 214, 168
    inner = R - 22
    maxmag = max((math.hypot(it["rr"] - 100, it["mm"] - 100) for it in items), default=1.0) or 1.0
    out = ['<svg width="100%" viewBox="0 0 680 448" role="img" '
           'xmlns="http://www.w3.org/2000/svg" '
           'aria-label="RS rotation lifecycle clock — sectors by phase with velocity">',
           '<defs><marker id="cvel" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
           'markerHeight="5" orient="auto"><path d="M2 1L8 5L2 9" fill="none" '
           'stroke="context-stroke" stroke-width="1.5"/></marker></defs>']
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" style="fill:none;stroke:var(--line-2);stroke-width:0.5"/>')
    out.append(f'<line x1="{cx - R}" y1="{cy}" x2="{cx + R}" y2="{cy}" '
               f'style="stroke:var(--line);stroke-width:0.5" stroke-dasharray="3 3"/>')
    out.append(f'<line x1="{cx}" y1="{cy - R}" x2="{cx}" y2="{cy + R}" '
               f'style="stroke:var(--line);stroke-width:0.5" stroke-dasharray="3 3"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" style="fill:var(--ink-3)"/>')
    for lab, col, x, y, anch in (
        ("Tailwind", "var(--up)", cx + R - 6, cy - R + 16, "end"),
        ("Recovery", "#7fdcae", cx - R + 6, cy - R + 16, "start"),
        ("Headwind", "var(--down)", cx - R + 6, cy + R - 6, "start"),
        ("Rolling-over", "var(--warn)", cx + R - 6, cy + R - 6, "end"),
    ):
        out.append(f'<text x="{x}" y="{y}" text-anchor="{anch}" '
                   f'style="fill:{col};font:500 13px system-ui">{lab}</text>')
    scored = sorted(items, key=lambda it: math.hypot(it["rr"] - 100, it["mm"] - 100), reverse=True)
    labelset = {id(it) for it in scored[:10]}
    for it in items:
        dx, dy = it["rr"] - 100, it["mm"] - 100
        px = cx + dx / maxmag * inner
        py = cy - dy / maxmag * inner
        lab, col = _PHASE[(dx >= 0, dy >= 0)]
        ox, oy = px - cx, py - cy
        mag = math.hypot(ox, oy) or 1.0
        L = 10 + 12 * min(1.0, mag / inner)          # arrow length ∝ momentum (speed)
        ax, ay = px + (-oy) / mag * L, py + ox / mag * L   # clockwise tangent (screen)
        rsi = it.get("rsi")
        title = f'{_esc(it["n"])} · {lab}' + (f' · RSI {float(rsi):.0f}' if rsi is not None else "")
        out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" '
                   f'style="stroke:{col};stroke-width:1.5;opacity:0.65" marker-end="url(#cvel)"/>')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" style="fill:{col}">'
                   f'<title>{title}</title></circle>')
        if id(it) in labelset:
            out.append(f'<text x="{px + 7:.1f}" y="{py + 3:.1f}" '
                       f'style="fill:var(--ink-2);font:400 11px system-ui">{_esc(_short(it["n"]))}</text>')
    out.append('</svg>')
    return "".join(out)


def clock_html(conn) -> str:
    items = _fetch(conn)
    if not items:
        return ('<div class="card"><div class="h2" style="margin:0 0 4px">Rotation lifecycle '
                'clock</div><div class="sub" style="margin:0">No RRG snapshot on record yet '
                '(needs the nightly rrg compute → rs_extras). Inert until then.</div></div>')
    return (
        '<div class="card"><div class="h2" style="margin:0 0 2px">Rotation lifecycle clock</div>'
        '<div class="sub" style="margin:0 0 6px">Sectors on the rotation loop vs Nifty 500 — '
        'phase + <b>direction &amp; speed of travel</b> (arrow ∝ momentum), clockwise: Recovery → '
        'Tailwind → Rolling-over → Headwind. Hover for RSI-of-RS. <b>Descriptive.</b></div>'
        f'{_svg(items)}</div>')


def _open():
    try:
        from src.core.db import get_conn
        return get_conn()
    except Exception:  # noqa: BLE001
        return nullcontext(None)


@router.get("/dash/cycle-clock", response_class=HTMLResponse)
def cycle_clock_page():
    with _open() as conn:
        body = clock_html(conn) if conn is not None else clock_html(None)
    try:
        from src.web.dashboard import _shell
        return HTMLResponse(_shell("Rotation lifecycle clock", body, active="markets", wide=True))
    except Exception:  # noqa: BLE001
        return HTMLResponse(body)


def _selftest() -> None:
    items = [{"n": "Nifty IT", "rr": 103.0, "mm": 102.0, "rsi": 61.0},
             {"n": "Nifty Pharma", "rr": 97.0, "mm": 101.5, "rsi": 40.0},
             {"n": "Nifty Bank", "rr": 96.0, "mm": 98.0, "rsi": 33.0}]
    s = _svg(items)
    assert s.startswith("<svg") and "Tailwind" in s and "url(#cvel)" in s, "svg"
    assert '<div class="card"' in clock_html(None)   # empty-state safe
    print("cycle_clock selftest: OK")


if __name__ == "__main__":
    _selftest()
