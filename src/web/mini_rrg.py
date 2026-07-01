"""Compact single-element Relative Rotation Graph — RS-Ratio × RS-Momentum on the
JdK quadrants, with a fading comet tail. The inline "one index, its rotation
journey" glance.

This shares the canonical vocabulary + geometry with /dash/rrg (``rrg_view._svg``)
and the ``rs_extras`` "Quadrant" read, so the inline mini-quad, the RS-depth panel,
and the full RRG all speak ONE language: improving → leading → weakening → lagging.
It replaces the older bespoke "X = 3m return · Y = 3m RS slope" quad whose
LEADER / DEFENSIVE / LAGGARD / LAZY-LAGGARD labels could disagree with the depth
panel (different axes). (D68 — rotation-vocabulary unification.)

Pure renderer. The caller fetches the points via ``rrg.tail(num, den, n, conn)``
(oldest→newest list of ``{rs_ratio, rs_momentum, quadrant}``) while it holds a DB
connection, then hands them here. Returns a ready ``<div class="card">…</div>`` —
including a graceful empty-state card when there is no rotation series yet.
"""

from __future__ import annotations

import html

from src.automation import rrg

# Directional rotation quadrants → design tokens (RRG ruling, reconciled with
# rrg_view.QCOLOR): Leading→up, Lagging→down, Improving→accent, Weakening→warn.
# These are consumed in Python and injected via inline ``style=`` (var() is invalid
# in a raw SVG fill=/stroke= attribute), so all consumption sites use style="fill:…".
_QCOLOR = {"Leading": "var(--up)", "Weakening": "var(--warn)",
           "Lagging": "var(--down)", "Improving": "var(--accent)"}


def mini_rrg_card(full_tail, den: str = "Nifty 500", *, tail_label: str = "",
                  max_pts: int = 14, size: int = 170) -> str:
    """Render a single index/stock's rotation journey as a compact RRG card.

    full_tail : oldest→newest [{rs_ratio, rs_momentum, quadrant?}] (from rrg.tail).
    den       : benchmark label, for the caption.
    tail_label: human window label, e.g. "last ~6 months" ('' hides the note).
    """
    pts = [p for p in (full_tail or [])
           if p.get("rs_ratio") is not None and p.get("rs_momentum") is not None]
    if not pts:
        return ('<div class="card"><div class="sub" style="margin:0">No rotation '
                'series on record for this index yet.</div></div>')
    # Sample down to keep the tail readable, but always keep today's point.
    step = max(1, len(pts) // max_pts)
    seg = pts[::step]
    if seg[-1] is not pts[-1]:
        seg.append(pts[-1])
    # Fit the box to the journey (same rule as rrg_view._svg).
    devs = ([abs(p["rs_ratio"] - 100) for p in seg]
            + [abs(p["rs_momentum"] - 100) for p in seg])
    half = max(6.0, min(34.0, (max(devs) if devs else 6.0) * 1.15))
    lo, hi = 100 - half, 100 + half
    L, R, T, B = 12, 168, 12, 168

    def mx(v):
        return max(L + 2, min(R - 2, L + (v - lo) / (hi - lo) * (R - L)))

    def my(v):
        return max(T + 2, min(B - 2, B - (v - lo) / (hi - lo) * (B - T)))

    cx, cy = mx(100), my(100)
    cur = seg[-1]
    q = cur.get("quadrant") or rrg.quadrant(cur["rs_ratio"], cur["rs_momentum"]) or "—"
    col = _QCOLOR.get(q, "#1f6feb")

    p = [f'<svg viewBox="0 0 180 180" width="{size}" height="{size}" style="max-width:100%" '
         f'xmlns="http://www.w3.org/2000/svg" role="img" '
         f'aria-label="Relative rotation graph, currently {html.escape(q)}">']
    # quadrant tints — improving (TL/accent), leading (TR/up), weakening (BR/warn), lagging (BL/down)
    p.append(f'<rect x="{L}" y="{T}" width="{cx - L:.0f}" height="{cy - T:.0f}" style="fill:var(--accent);fill-opacity:0.06"/>')
    p.append(f'<rect x="{cx:.0f}" y="{T}" width="{R - cx:.0f}" height="{cy - T:.0f}" style="fill:var(--up);fill-opacity:0.06"/>')
    p.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{R - cx:.0f}" height="{B - cy:.0f}" style="fill:var(--warn);fill-opacity:0.06"/>')
    p.append(f'<rect x="{L}" y="{cy:.0f}" width="{cx - L:.0f}" height="{B - cy:.0f}" style="fill:var(--down);fill-opacity:0.06"/>')
    p.append(f'<rect x="{L}" y="{T}" width="{R - L}" height="{B - T}" rx="6" fill="none" style="stroke:var(--line-2)"/>')
    p.append(f'<line x1="{cx:.0f}" y1="{T}" x2="{cx:.0f}" y2="{B}" style="stroke:var(--line-2)" stroke-dasharray="3 3"/>')
    p.append(f'<line x1="{L}" y1="{cy:.0f}" x2="{R}" y2="{cy:.0f}" style="stroke:var(--line-2)" stroke-dasharray="3 3"/>')
    p.append(f'<text x="{L + 4}" y="{T + 10}" style="fill:var(--ink-3)" font-size="7">improving</text>')
    p.append(f'<text x="{R - 4}" y="{T + 10}" style="fill:var(--ink-3)" font-size="7" text-anchor="end">leading</text>')
    p.append(f'<text x="{R - 4}" y="{B - 4}" style="fill:var(--ink-3)" font-size="7" text-anchor="end">weakening</text>')
    p.append(f'<text x="{L + 4}" y="{B - 4}" style="fill:var(--ink-3)" font-size="7">lagging</text>')
    # comet tail (older = fainter/smaller), then today's dot on top
    if len(seg) >= 2:
        poly = " ".join(f"{mx(d['rs_ratio']):.1f},{my(d['rs_momentum']):.1f}" for d in seg)
        p.append(f'<polyline points="{poly}" fill="none" style="stroke:{col}" stroke-opacity="0.30" '
                 'stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/>')
        n = len(seg)
        for i, d in enumerate(seg[:-1]):
            f = (i + 1) / n
            p.append(f'<circle cx="{mx(d["rs_ratio"]):.1f}" cy="{my(d["rs_momentum"]):.1f}" '
                     f'r="{1.3 + 2.2 * f:.1f}" style="fill:{col}" fill-opacity="{0.16 + 0.5 * f:.2f}"/>')
    p.append(f'<circle cx="{mx(cur["rs_ratio"]):.1f}" cy="{my(cur["rs_momentum"]):.1f}" r="5" '
             f'style="fill:{col}" stroke="#0d1117" stroke-width="1.4"/>')
    p.append('</svg>')

    tnote = f' · tail: {html.escape(tail_label)} (faint &rarr; now)' if tail_label else ''
    cap = (f'<div class="sub" style="margin:6px 0 0">RS-Ratio &times; RS-Momentum vs '
           f'{html.escape(str(den))} · <span style="color:{col}">{html.escape(q)}</span>{tnote}</div>')
    return f'<div class="card" style="text-align:center">{"".join(p)}{cap}</div>'
