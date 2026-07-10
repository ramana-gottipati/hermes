"""infographics.py — shared inline-SVG primitives for Patearn's "diverse charts" estate.

Why this module exists
----------------------
The deep-data insight lenses (Market Internals, FII positioning tape, sector-economics
heatmap, the launchpad track record, the "what moves" fingerprint) all need chart forms
the codebase did not yet have a reusable vocabulary for: signed heat-ribbons, stacked
streamgraphs, labelled heat-grids, diverging z-bars, MFE/MAE floating bars, and percentile
gauges. Each page used to hand-roll SVG. This module gives ONE tested, theme-aware set of
primitives so the new visuals read as one system (premium-visuals program) and light/dark/
print all work automatically (every colour is a CSS `var()` from ui_tokens).

Design contract
---------------
* **Value colour is directional only.** Signed helpers (`heat_ribbon`, `spark_area(signed=)`,
  `diverging_bars`) map +→--up / -→--down — that is a *verdict* (advance/decline, accum/
  distrib, elevated/suppressed). Non-directional intensity (`heat_grid`) uses a neutral
  sequential ramp (`--series-*`/cyan→amber), NEVER green=good, so the colour gate stays clean.
* Pure functions → SVG strings. No `src` imports (leaf module, like ui_tokens/glossary):
  safe to import from any view. Callers wrap the returned `<svg>` in their own container.
* Every function degrades to a tiny honest empty-state `<svg>` on empty/degenerate input —
  never raises, so a view can always render.

All sizes are in a `viewBox` user space; the SVG scales to its container (max-width:100%).
"""
from __future__ import annotations

from html import escape as _html_escape


def _esc(s: object) -> str:
    return _html_escape(str(s), quote=True)


def _num(x: float, nd: int = 2) -> str:
    """Compact fixed-point without a trailing '.0' explosion; '' for None/NaN."""
    if x is None:
        return ""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return _esc(x)
    if f != f:  # NaN
        return ""
    s = f"{f:.{nd}f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def _lin(x: float, d0: float, d1: float, r0: float, r1: float) -> float:
    if d1 == d0:
        return (r0 + r1) / 2.0
    return r0 + (x - d0) * (r1 - r0) / (d1 - d0)


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _ord(n: float) -> str:
    """1→'1st', 22→'22nd', 31→'31st', 11..13→'th'. Shared ordinal for pctile labels."""
    i = int(round(n))
    suf = "th" if 10 <= (i % 100) <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suf}"


def _empty(w: int, h: int, msg: str = "no data") -> str:
    return (f'<svg viewBox="0 0 {w} {h}" class="ifx" role="img" '
            f'preserveAspectRatio="xMidYMid meet" style="max-width:100%;height:auto">'
            f'<text x="{w//2}" y="{h//2}" text-anchor="middle" '
            f'fill="var(--ink-3)" font-size="12" font-style="italic">{_esc(msg)}</text></svg>')


def _open(w: int, h: int, extra: str = "") -> str:
    return (f'<svg viewBox="0 0 {w} {h}" class="ifx" role="img" '
            f'preserveAspectRatio="xMidYMid meet" style="max-width:100%;height:auto" {extra}>')


# ── signed / sequential colour ────────────────────────────────────────────────
def signed_fill(t: float, lo: float = 0.10, hi: float = 0.85) -> str:
    """Signed value t∈[-1,1] → an rgba tint on the value contract (+green/-red).
    |t| drives alpha lo..hi so magnitude reads as intensity. t==0 → faint neutral."""
    t = _clamp(t, -1.0, 1.0)
    a = lo + (hi - lo) * min(1.0, abs(t))
    if t > 0.0:
        return f"rgba(var(--up-rgb),{a:.3f})"
    if t < 0.0:
        return f"rgba(var(--down-rgb),{a:.3f})"
    return "rgba(var(--warn-rgb),0.10)"


# 6-stop perceptual-ish sequential ramp (cyan→teal→amber→orange), NOT a value hue.
_SEQ = ("#123b46", "#175e63", "#2f8f7f", "#7bb26a", "#d6b13f", "#f0883e")


def seq_fill(t: float) -> str:
    """Non-directional intensity t∈[0,1] → sequential ramp colour (interpolated)."""
    t = _clamp(t, 0.0, 1.0)
    n = len(_SEQ) - 1
    i = int(t * n)
    if i >= n:
        return _SEQ[n]
    f = t * n - i
    c0, c1 = _SEQ[i], _SEQ[i + 1]
    r0, g0, b0 = int(c0[1:3], 16), int(c0[3:5], 16), int(c0[5:7], 16)
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    return (f"rgb({int(r0+(r1-r0)*f)},{int(g0+(g1-g0)*f)},{int(b0+(b1-b0)*f)})")


# ── 1. signed heat-ribbon — one thin bar per period, colour = signed value ─────
def heat_ribbon(cells: list, w: int = 1100, h: int = 46, vmax: float | None = None,
                title_at: list | None = None) -> str:
    """cells: list of (label, value). value>0 green / <0 red, |value| = intensity
    (normalised by vmax, default = max|value|). Iconic breadth/regime strip.
    title_at: optional list of (frac 0..1, text) era annotations under the strip."""
    cells = [(lab, v) for lab, v in cells if v is not None]
    if not cells:
        return _empty(w, h)
    vmax = vmax or max((abs(v) for _, v in cells), default=1.0) or 1.0
    n = len(cells)
    bw = w / n
    top, band = 2, h - 20
    bars = []
    for i, (_, v) in enumerate(cells):
        x = i * bw
        bars.append(f'<rect x="{x:.2f}" y="{top}" width="{bw+0.6:.2f}" height="{band}" '
                    f'fill="{signed_fill(v/vmax)}"/>')
    # baseline midline
    mid = top + band / 2
    out = [_open(w, h), "".join(bars),
           f'<line x1="0" y1="{mid:.1f}" x2="{w}" y2="{mid:.1f}" stroke="var(--line-3)" '
           f'stroke-width="0.5" stroke-dasharray="2 3" opacity="0.5"/>']
    if title_at:
        for frac, txt in title_at:
            x = _clamp(frac, 0, 1) * w
            out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+band}" '
                       f'stroke="var(--ink-4)" stroke-width="0.75"/>')
            out.append(f'<text x="{x+3:.1f}" y="{h-6}" fill="var(--ink-3)" font-size="10">'
                       f'{_esc(txt)}</text>')
    else:
        out.append(f'<text x="2" y="{h-6}" fill="var(--ink-3)" font-size="10">'
                   f'{_esc(cells[0][0])}</text>')
        out.append(f'<text x="{w-2}" y="{h-6}" fill="var(--ink-3)" font-size="10" '
                   f'text-anchor="end">{_esc(cells[-1][0])}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 2. spark_area — line + area, optional signed two-tone about a baseline ─────
def spark_area(values: list, w: int = 1100, h: int = 150, color: str = "var(--chart-line)",
               signed: bool = False, baseline: float | None = None, labels: list | None = None,
               y0: float | None = None, y1: float | None = None, last_dot: bool = True,
               band: tuple | None = None) -> str:
    """values: list of floats (None allowed → gap). If signed, fill is green above /
    red below `baseline` (default 0). band=(lo_list,hi_list) draws a faint envelope."""
    vals = list(values)
    real = [v for v in vals if v is not None]
    if len(real) < 2:
        return _empty(w, h)
    lo = y0 if y0 is not None else min(real)
    hi = y1 if y1 is not None else max(real)
    if band:
        lo = min(lo, min(v for v in band[0] if v is not None))
        hi = max(hi, max(v for v in band[1] if v is not None))
    if hi == lo:
        hi = lo + 1
    pad = (hi - lo) * 0.08
    lo -= pad
    hi += pad
    ml, mr, mt, mb = 4, 4, 8, 16
    pw, ph = w - ml - mr, h - mt - mb
    n = len(vals)

    def X(i):
        return ml + _lin(i, 0, n - 1, 0, pw)

    def Y(v):
        return mt + _lin(v, lo, hi, ph, 0)

    base = baseline if baseline is not None else 0.0
    yb = _clamp(Y(base), mt, mt + ph)
    pts = [(X(i), Y(v)) for i, v in enumerate(vals) if v is not None]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    out = [_open(w, h)]
    # optional envelope band
    if band:
        blo, bhi = band
        bp = [(X(i), Y(bhi[i])) for i in range(n) if i < len(bhi) and bhi[i] is not None]
        bp += [(X(i), Y(blo[i])) for i in range(n - 1, -1, -1) if i < len(blo) and blo[i] is not None]
        if len(bp) > 2:
            out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in bp)}" '
                       f'fill="{color}" opacity="0.10"/>')
    if signed:
        # two clip halves so the area is green above / red below the baseline
        area = f"{ml},{yb:.1f} " + line + f" {ml+pw},{yb:.1f}"
        out.append(f'<defs><clipPath id="_ca_up"><rect x="0" y="{mt}" width="{w}" '
                   f'height="{yb-mt:.1f}"/></clipPath><clipPath id="_ca_dn"><rect x="0" '
                   f'y="{yb:.1f}" width="{w}" height="{mt+ph-yb:.1f}"/></clipPath></defs>')
        out.append(f'<polygon points="{area}" fill="rgba(var(--up-rgb),0.16)" clip-path="url(#_ca_up)"/>')
        out.append(f'<polygon points="{area}" fill="rgba(var(--down-rgb),0.16)" clip-path="url(#_ca_dn)"/>')
        out.append(f'<line x1="{ml}" y1="{yb:.1f}" x2="{ml+pw}" y2="{yb:.1f}" '
                   f'stroke="var(--ink-4)" stroke-width="0.75" stroke-dasharray="3 3"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="var(--ink-2)" stroke-width="1.1"/>')
    else:
        out.append(f'<polygon points="{ml},{mt+ph} {line} {ml+pw},{mt+ph}" '
                   f'fill="{color}" opacity="0.14"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.4"/>')
    if last_dot and pts:
        lx, ly = pts[-1]
        out.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{color}"/>')
    if labels:
        for frac, txt in labels:
            x = ml + _clamp(frac, 0, 1) * pw
            out.append(f'<text x="{x:.1f}" y="{h-4}" fill="var(--ink-3)" font-size="10" '
                       f'text-anchor="middle">{_esc(txt)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 3. stream — stacked area bands (share-of-total or absolute) ────────────────
def stream(dates: list, bands: list, w: int = 1100, h: int = 170, normalize: bool = True) -> str:
    """bands: list of (label, color, values[]) aligned to `dates`. normalize→100% stack."""
    bands = [(lab, col, list(v)) for lab, col, v in bands if any(x is not None for x in v)]
    if not bands or not dates:
        return _empty(w, h)
    n = len(dates)
    ml, mr, mt, mb = 4, 4, 8, 4
    pw, ph = w - ml - mr, h - mt - mb
    # per-index totals for normalisation
    tot = [0.0] * n
    for _, _, v in bands:
        for i in range(n):
            tot[i] += (v[i] or 0.0) if i < len(v) else 0.0

    def X(i):
        return ml + _lin(i, 0, n - 1, 0, pw)

    cum = [0.0] * n
    out = [_open(w, h)]
    for lab, col, v in bands:
        top_pts, bot_pts = [], []
        for i in range(n):
            val = (v[i] or 0.0) if i < len(v) else 0.0
            denom = tot[i] if (normalize and tot[i]) else 1.0
            frac_lo = cum[i] / (tot[i] if (normalize and tot[i]) else max(tot) or 1.0)
            cum[i] += val
            frac_hi = cum[i] / (tot[i] if (normalize and tot[i]) else max(tot) or 1.0)
            top_pts.append((X(i), mt + ph - frac_hi * ph))
            bot_pts.append((X(i), mt + ph - frac_lo * ph))
        poly = top_pts + bot_pts[::-1]
        out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in poly)}" '
                   f'fill="{col}" opacity="0.85"><title>{_esc(lab)}</title></polygon>')
    out.append("</svg>")
    return "".join(out)


# ── 4. heat_grid — labelled matrix (sector×year, month×year) sequential ramp ───
def heat_grid(row_labels: list, col_labels: list, values: list, w: int = 1100,
              cell_h: int = 26, vmin: float | None = None, vmax: float | None = None,
              fmt: int = 0, row_w: int = 118, signed: bool = False,
              na=None) -> str:
    """values: list-of-rows (len row_labels) each len col_labels; None→greyed 'n/a' cell."""
    if not row_labels or not col_labels:
        return _empty(w, 60)
    flat = [x for row in values for x in row if x is not None]
    if not flat:
        return _empty(w, 60)
    vmin = vmin if vmin is not None else min(flat)
    vmax = vmax if vmax is not None else max(flat)
    rng = (vmax - vmin) or 1.0
    nc = len(col_labels)
    top = 18
    cw = (w - row_w) / nc
    h = top + cell_h * len(row_labels) + 4
    out = [_open(w, h)]
    for j, cl in enumerate(col_labels):
        x = row_w + j * cw + cw / 2
        out.append(f'<text x="{x:.1f}" y="12" fill="var(--ink-3)" font-size="10" '
                   f'text-anchor="middle">{_esc(cl)}</text>')
    for i, rl in enumerate(row_labels):
        y = top + i * cell_h
        out.append(f'<text x="{row_w-6}" y="{y+cell_h/2+3:.1f}" fill="var(--ink-2)" '
                   f'font-size="11" text-anchor="end">{_esc(rl)}</text>')
        row = values[i] if i < len(values) else []
        for j in range(nc):
            v = row[j] if j < len(row) else None
            x = row_w + j * cw
            if v is None:
                out.append(f'<rect x="{x:.1f}" y="{y}" width="{cw-1.5:.1f}" height="{cell_h-1.5}" '
                           f'fill="var(--bg-3)" opacity="0.4" rx="2"/>')
                continue
            t = (v - vmin) / rng
            fill = signed_fill((v / (max(abs(vmin), abs(vmax)) or 1))) if signed else seq_fill(t)
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{cw-1.5:.1f}" height="{cell_h-1.5}" '
                       f'fill="{fill}" rx="2"><title>{_esc(rl)} · {_esc(cl if False else col_labels[j])}: {_num(v,2)}</title></rect>')
            out.append(f'<text x="{x+cw/2:.1f}" y="{y+cell_h/2+3:.1f}" fill="var(--ink)" '
                       f'font-size="9.5" text-anchor="middle" style="font-variant-numeric:tabular-nums">'
                       f'{_num(v,fmt)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 5. diverging_bars — signed horizontal bars from a centre 0 ────────────────
def diverging_bars(items: list, w: int = 620, bar_h: int = 20, vmax: float | None = None,
                   label_w: int = 172, unit: str = "") -> str:
    """items: list of (label, value). +→green right / -→red left. For z-profiles, nets."""
    items = [(l, v) for l, v in items if v is not None]
    if not items:
        return _empty(w, 60)
    vmax = vmax or max((abs(v) for _, v in items), default=1.0) or 1.0
    cx = label_w + (w - label_w) / 2
    half = (w - label_w) / 2 - 8
    h = 6 + bar_h * len(items) + 4
    out = [_open(w, h)]
    out.append(f'<line x1="{cx}" y1="4" x2="{cx}" y2="{h-4}" stroke="var(--line-3)" stroke-width="1"/>')
    for i, (lab, v) in enumerate(items):
        y = 6 + i * bar_h
        bl = _clamp(v / vmax, -1, 1) * half
        col = "var(--up)" if v >= 0 else "var(--down)"
        x = cx if v >= 0 else cx + bl
        out.append(f'<rect x="{x:.1f}" y="{y+2}" width="{abs(bl):.1f}" height="{bar_h-6}" '
                   f'rx="2" fill="{col}" opacity="0.85"/>')
        out.append(f'<text x="{label_w-8}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-2)" '
                   f'font-size="11" text-anchor="end">{_esc(lab)}</text>')
        vx = cx + bl + (5 if v >= 0 else -5)
        anc = "start" if v >= 0 else "end"
        out.append(f'<text x="{vx:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-3)" font-size="10" '
                   f'text-anchor="{anc}" style="font-variant-numeric:tabular-nums">{_num(v,2)}{_esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 6. floating_bars — MFE/MAE style [lo..hi] bars on a shared signed scale ────
def floating_bars(items: list, w: int = 620, bar_h: int = 26, label_w: int = 150,
                  vlo: float | None = None, vhi: float | None = None) -> str:
    """items: list of (label, lo, hi, end_text). Bar spans lo..hi; zero line marked.
    lo (e.g. MAE, negative) red end, hi (MFE, positive) green end."""
    items = [it for it in items if it[1] is not None and it[2] is not None]
    if not items:
        return _empty(w, 60)
    vlo = vlo if vlo is not None else min(it[1] for it in items)
    vhi = vhi if vhi is not None else max(it[2] for it in items)
    if vhi == vlo:
        vhi = vlo + 1
    plot_l = label_w
    pw = w - plot_l - 46

    def X(v):
        return plot_l + _lin(v, vlo, vhi, 0, pw)

    zx = X(0)
    h = 6 + bar_h * len(items) + 4
    out = [_open(w, h)]
    out.append(f'<line x1="{zx:.1f}" y1="4" x2="{zx:.1f}" y2="{h-4}" stroke="var(--line-3)" '
               f'stroke-width="1" stroke-dasharray="2 3"/>')
    for i, it in enumerate(items):
        lab, lo, hi = it[0], it[1], it[2]
        end = it[3] if len(it) > 3 else ""
        y = 6 + i * bar_h
        x0, x1 = X(lo), X(hi)
        out.append(f'<defs><linearGradient id="_fb{i}" x1="0" x2="1">'
                   f'<stop offset="0" stop-color="var(--down)"/>'
                   f'<stop offset="{_clamp((zx-x0)/max(x1-x0,1),0,1):.2f}" stop-color="var(--warn)"/>'
                   f'<stop offset="1" stop-color="var(--up)"/></linearGradient></defs>')
        out.append(f'<rect x="{x0:.1f}" y="{y+3}" width="{x1-x0:.1f}" height="{bar_h-9}" rx="3" '
                   f'fill="url(#_fb{i})" opacity="0.9"/>')
        out.append(f'<text x="{label_w-8}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-2)" '
                   f'font-size="11" text-anchor="end">{_esc(lab)}</text>')
        out.append(f'<text x="{x0-4:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--down)" font-size="9.5" '
                   f'text-anchor="end" style="font-variant-numeric:tabular-nums">{_num(lo,1)}</text>')
        out.append(f'<text x="{x1+4:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--up)" font-size="9.5" '
                   f'text-anchor="start" style="font-variant-numeric:tabular-nums">+{_num(hi,1)}</text>')
        if end:
            out.append(f'<text x="{w-2}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-3)" font-size="9.5" '
                       f'text-anchor="end">{_esc(end)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 7. pct_gauge — where a value sits in its own history (violin + marker) ─────
def pct_gauge(value: float, dist: list, w: int = 480, h: int = 64, label: str = "",
              vfmt: int = 2) -> str:
    """dist: the historical sample. Renders a faint density track + a marker at `value`
    with its percentile — 'more X than N% of history'. Descriptive positioning gauge."""
    d = sorted(v for v in dist if v is not None)
    if len(d) < 5 or value is None:
        return _empty(w, h)
    lo, hi = d[0], d[-1]
    if hi == lo:
        hi = lo + 1
    ml, mr = 8, 8
    pw = w - ml - mr
    yb = h - 20
    # histogram density (24 bins) as a faint area
    nb = 24
    counts = [0] * nb
    for v in d:
        b = int(_clamp((v - lo) / (hi - lo) * nb, 0, nb - 1))
        counts[b] += 1
    cmax = max(counts) or 1
    pts = [(ml, yb)]
    for b in range(nb):
        x = ml + (b + 0.5) / nb * pw
        y = yb - (counts[b] / cmax) * (yb - 8)
        pts.append((x, y))
    pts.append((ml + pw, yb))
    below = sum(1 for v in d if v <= value)
    pct = 100.0 * below / len(d)
    mx = ml + _lin(_clamp(value, lo, hi), lo, hi, 0, pw)
    out = [_open(w, h)]
    out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" '
               f'fill="var(--series-6)" opacity="0.16"/>')
    out.append(f'<line x1="{ml}" y1="{yb}" x2="{ml+pw}" y2="{yb}" stroke="var(--line-2)" stroke-width="1"/>')
    out.append(f'<line x1="{mx:.1f}" y1="6" x2="{mx:.1f}" y2="{yb}" stroke="var(--accent)" stroke-width="2"/>')
    out.append(f'<circle cx="{mx:.1f}" cy="6" r="3" fill="var(--accent)"/>')
    out.append(f'<text x="{ml}" y="{h-4}" fill="var(--ink-3)" font-size="9.5">{_num(lo,vfmt)}</text>')
    out.append(f'<text x="{ml+pw}" y="{h-4}" fill="var(--ink-3)" font-size="9.5" text-anchor="end">{_num(hi,vfmt)}</text>')
    anc = "start" if pct < 55 else "end"
    tx = mx + (5 if pct < 55 else -5)
    out.append(f'<text x="{tx:.1f}" y="{h-4}" fill="var(--accent-2)" font-size="10" '
               f'text-anchor="{anc}" style="font-variant-numeric:tabular-nums">'
               f'{_esc(label)} {pct:.0f}th pct</text>')
    out.append("</svg>")
    return "".join(out)


def _selftest() -> int:
    import re
    seq = [signed_fill(-1), signed_fill(0), signed_fill(1), seq_fill(0), seq_fill(.5), seq_fill(1)]
    assert all(c for c in seq)
    charts = {
        "heat_ribbon": heat_ribbon([("2020", -0.9), ("2021", 0.6), ("2022", -0.3), ("2023", 0.8)]),
        "spark_area": spark_area([1, 3, 2, 5, 4, 6.0]),
        "spark_signed": spark_area([-2, 1, -3, 2, 4, -1.0], signed=True),
        "stream": stream(["a", "b", "c"], [("x", "var(--series-1)", [1, 2, 3]),
                                            ("y", "var(--series-2)", [3, 2, 1])]),
        "heat_grid": heat_grid(["Pharma", "IT"], ["FY20", "FY25"], [[25.6, 17.0], [31.9, 31.6]], fmt=1),
        "diverging": diverging_bars([("ret_252d", 0.88), ("deliv_per_s", -0.50)]),
        "floating": floating_bars([("event", -11.0, 48.4, "big50 38%"), ("baseline", -18.0, 11.0, "")]),
        "gauge": pct_gauge(0.119, [i / 100 for i in range(500)], label="FII net-short"),
    }
    for name, svg in charts.items():
        assert svg.startswith("<svg") and svg.endswith("</svg>"), name
        assert svg.count("<svg") == 1 and svg.count("</svg>") == 1, name
        # rough well-formedness: balanced-ish angle brackets, no unescaped stray
        assert svg.count("<") == svg.count(">"), f"unbalanced tags in {name}"
    # empty-state degrade
    for fn in (lambda: heat_ribbon([]), lambda: spark_area([1]), lambda: stream([], []),
               lambda: heat_grid([], [], []), lambda: diverging_bars([]),
               lambda: floating_bars([]), lambda: pct_gauge(1, [])):
        s = fn()
        assert s.startswith("<svg") and "no data" in s
    print("infographics selftest OK — 8 primitives render valid SVG; empty-states degrade")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
