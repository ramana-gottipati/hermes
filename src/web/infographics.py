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
                title_at: list | None = None, cell_link=None) -> str:
    """cells: list of (label, value). value>0 green / <0 red, |value| = intensity
    (normalised by vmax, default = max|value|). Iconic breadth/regime strip.
    title_at: optional list of (frac 0..1, text) era annotations under the strip.
    cell_link(i)->href makes each bar a click-through (SVG <a>) — the drill-down seam."""
    cells = [(lab, v) for lab, v in cells if v is not None]
    if not cells:
        return _empty(w, h)
    vmax = vmax or max((abs(v) for _, v in cells), default=1.0) or 1.0
    n = len(cells)
    bw = w / n
    top, band = 2, h - 20
    bars = []
    for i, (lab, v) in enumerate(cells):
        x = i * bw
        href = cell_link(i) if cell_link else None
        tip = f'{_esc(lab)}{" · click to break down" if href else ""}'
        rect = (f'<rect x="{x:.2f}" y="{top}" width="{bw+0.6:.2f}" height="{band}" '
                f'fill="{signed_fill(v/vmax)}"><title>{tip}</title></rect>')
        bars.append(f'<a href="{_esc(href)}">{rect}</a>' if href else rect)
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
    # Codex D8-F4: split into CONTIGUOUS non-None runs so a None renders as a REAL
    # gap, not a straight line bridging across dates that had no data. Each run gets
    # its own polyline; each area closes to the baseline independently.
    segs, cur = [], []
    for i, v in enumerate(vals):
        if v is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append((X(i), Y(v)))
    if cur:
        segs.append(cur)
    line_segs = [s for s in segs if len(s) >= 2]

    def _pstr(seg):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in seg)

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
        out.append(f'<defs><clipPath id="_ca_up"><rect x="0" y="{mt}" width="{w}" '
                   f'height="{yb-mt:.1f}"/></clipPath><clipPath id="_ca_dn"><rect x="0" '
                   f'y="{yb:.1f}" width="{w}" height="{mt+ph-yb:.1f}"/></clipPath></defs>')
        for seg in line_segs:
            area = f"{seg[0][0]:.1f},{yb:.1f} " + _pstr(seg) + f" {seg[-1][0]:.1f},{yb:.1f}"
            out.append(f'<polygon points="{area}" fill="rgba(var(--up-rgb),0.16)" clip-path="url(#_ca_up)"/>')
            out.append(f'<polygon points="{area}" fill="rgba(var(--down-rgb),0.16)" clip-path="url(#_ca_dn)"/>')
        out.append(f'<line x1="{ml}" y1="{yb:.1f}" x2="{ml+pw}" y2="{yb:.1f}" '
                   f'stroke="var(--ink-4)" stroke-width="0.75" stroke-dasharray="3 3"/>')
        for seg in line_segs:
            out.append(f'<polyline points="{_pstr(seg)}" fill="none" stroke="var(--ink-2)" stroke-width="1.1"/>')
    else:
        for seg in line_segs:
            out.append(f'<polygon points="{seg[0][0]:.1f},{mt+ph} {_pstr(seg)} {seg[-1][0]:.1f},{mt+ph}" '
                       f'fill="{color}" opacity="0.14"/>')
            out.append(f'<polyline points="{_pstr(seg)}" fill="none" stroke="{color}" stroke-width="1.4"/>')
    if last_dot and line_segs:
        lx, ly = line_segs[-1][-1]
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
              na=None, cell_link=None, unit: str = "") -> str:
    """values: list-of-rows (len row_labels) each len col_labels; None→greyed 'n/a' cell.
    cell_link(i,j)->href makes a populated cell a click-through (SVG <a>) — the drill-down seam.
    unit is appended to the hover tooltip's value (e.g. '%')."""
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
            tip = f'{_esc(rl)} · {_esc(col_labels[j])}: {_num(v, 2)}{_esc(unit)}'
            href = cell_link(i, j) if cell_link else None
            if href:
                tip += " · click to break down"
            cell = (f'<rect x="{x:.1f}" y="{y}" width="{cw-1.5:.1f}" height="{cell_h-1.5}" '
                    f'fill="{fill}" rx="2"><title>{tip}</title></rect>'
                    f'<text x="{x+cw/2:.1f}" y="{y+cell_h/2+3:.1f}" fill="var(--ink)" '
                    f'font-size="9.5" text-anchor="middle" style="font-variant-numeric:tabular-nums" '
                    f'pointer-events="none">{_num(v,fmt)}</text>')
            out.append(f'<a href="{_esc(href)}">{cell}</a>' if href else cell)
    out.append("</svg>")
    return "".join(out)


# ── 5. diverging_bars — signed horizontal bars from a centre 0 ────────────────
def diverging_bars(items: list, w: int = 620, bar_h: int = 20, vmax: float | None = None,
                   label_w: int = 172, unit: str = "", show_values: bool = True,
                   pos_color: str = "var(--up)", neg_color: str = "var(--down)") -> str:
    """items: list of (label, value). +→pos_color right / -→neg_color left. Default is the
    value contract (green/red) for signed VERDICTS (net flows). For a non-directional signed
    profile (e.g. a z-fingerprint: 'elevated vs suppressed', NOT good vs bad) pass a neutral
    categorical pair so it can't be misread as bullish/bearish."""
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
        col = pos_color if v >= 0 else neg_color
        x = cx if v >= 0 else cx + bl
        out.append(f'<rect x="{x:.1f}" y="{y+2}" width="{abs(bl):.1f}" height="{bar_h-6}" '
                   f'rx="2" fill="{col}" opacity="0.85"><title>{_esc(lab)}: {_num(v,2)}{_esc(unit)}</title></rect>')
        out.append(f'<text x="{label_w-8}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-2)" '
                   f'font-size="11" text-anchor="end">{_esc(lab)}</text>')
        if show_values:
            vx = cx + bl + (5 if v >= 0 else -5)
            anc = "start" if v >= 0 else "end"
            out.append(f'<text x="{vx:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-3)" font-size="10" '
                       f'text-anchor="{anc}" style="font-variant-numeric:tabular-nums">{_num(v,2)}{_esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── 6. floating_bars — MFE/MAE style [lo..hi] bars on a shared signed scale ────
def floating_bars(items: list, w: int = 620, bar_h: int = 26, label_w: int = 150,
                  vlo: float | None = None, vhi: float | None = None, unit: str = "",
                  bar_link=None) -> str:
    """items: list of (label, lo, hi, end_text). Bar spans lo..hi; zero line marked.
    lo (e.g. MAE, negative) red end, hi (MFE, positive) green end."""
    items = [it for it in items if it[1] is not None and it[2] is not None]
    if not items:
        return _empty(w, 60)
    vlo = vlo if vlo is not None else min(it[1] for it in items)
    vhi = vhi if vhi is not None else max(it[2] for it in items)
    if vhi == vlo:
        vhi = vlo + 1
    # left gutter so the leftmost bar's dip (lo) value label clears the row label;
    # right gutter for the rise (hi) label. Both keep numeric labels from overprinting.
    plot_l = label_w + 44
    pw = w - plot_l - 52

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
        href = bar_link(i) if bar_link else None
        rect = (f'<rect x="{x0:.1f}" y="{y+3}" width="{x1-x0:.1f}" height="{bar_h-9}" rx="3" '
                f'fill="url(#_fb{i})" opacity="0.9"><title>{_esc(lab)}: dips {_num(lo,1)}{_esc(unit)}, '
                f'rises +{_num(hi,1)}{_esc(unit)}{" · click to break down" if href else ""}</title></rect>')
        out.append(f'<a href="{_esc(href)}">{rect}</a>' if href else rect)
        out.append(f'<text x="{label_w-8}" y="{y+bar_h/2+3:.1f}" fill="var(--ink-2)" '
                   f'font-size="11" text-anchor="end">{_esc(lab)}</text>')
        out.append(f'<text x="{x0-4:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--down)" font-size="9.5" '
                   f'text-anchor="end" style="font-variant-numeric:tabular-nums">{_num(lo,1)}{_esc(unit)}</text>')
        out.append(f'<text x="{x1+4:.1f}" y="{y+bar_h/2+3:.1f}" fill="var(--up)" font-size="9.5" '
                   f'text-anchor="start" style="font-variant-numeric:tabular-nums">+{_num(hi,1)}{_esc(unit)}</text>')
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
    out.append(f'<line x1="{mx:.1f}" y1="6" x2="{mx:.1f}" y2="{yb}" stroke="var(--accent)" stroke-width="2">'
               f'<title>{_esc(label)} = {_num(value, vfmt)} — {pct:.0f}th percentile of {len(d)} readings</title></line>')
    out.append(f'<circle cx="{mx:.1f}" cy="6" r="3" fill="var(--accent)"/>')
    out.append(f'<text x="{ml}" y="{h-4}" fill="var(--ink-3)" font-size="9.5">{_num(lo,vfmt)}</text>')
    out.append(f'<text x="{ml+pw}" y="{h-4}" fill="var(--ink-3)" font-size="9.5" text-anchor="end">{_num(hi,vfmt)}</text>')
    anc = "start" if pct < 55 else "end"
    tx = mx + (5 if pct < 55 else -5)
    out.append(f'<text x="{tx:.1f}" y="{h-4}" fill="var(--accent-2)" font-size="10" '
               f'text-anchor="{anc}" style="font-variant-numeric:tabular-nums">'
               f'{_esc(label)} {pct:.0f}th percentile</text>')
    out.append("</svg>")
    return "".join(out)


# ── readability scaffold — the beginner on-ramp layer (additive, one design system) ──
# Used by the deep-data lenses so "plain English" + "bottom line" read identically everywhere.
def readability_css() -> str:
    """A <style> block for the .rd-bottom (takeaway band) + .rd-plain (in-plain-English line).
    Include once per page (theme-aware via tokens). Additive — never restyles existing content."""
    return (
        "<style>"
        ".rd-bottom{display:flex;gap:12px;align-items:baseline;"
        "background:linear-gradient(90deg,rgba(var(--up-rgb),.07),rgba(var(--up-rgb),.015));"
        "border:1px solid var(--line-2);border-left:3px solid var(--up);border-radius:0 12px 12px 0;"
        "padding:12px 16px;margin:2px 0 16px;max-width:1120px;}"
        ".rd-bottom .rd-lbl{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;"
        "color:var(--up);font-weight:700;white-space:nowrap;flex:none;padding-top:3px;}"
        ".rd-bottom .rd-txt{font-size:14.5px;line-height:1.55;color:var(--ink);}"
        ".rd-bottom .rd-txt b{color:var(--ink);}"
        ".rd-plain{display:flex;gap:9px;align-items:baseline;margin:7px 0 11px;padding-left:11px;"
        "border-left:2px solid var(--accent-cy);max-width:1080px;}"
        ".rd-plain .rd-lbl{font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;"
        "color:var(--accent-cy);font-weight:700;white-space:nowrap;flex:none;padding-top:2px;}"
        ".rd-plain .rd-txt{font-size:12.5px;line-height:1.5;color:var(--ink-2);}"
        ".rd-plain .rd-txt b{color:var(--ink);}"
        ".rd-tech{color:var(--ink-3);font-size:10px;font-weight:400;display:block;margin-top:1px;}"
        ".rd-htr{margin:-4px 0 14px;font-size:12px;}"
        ".rd-htr a{color:var(--accent-cy);text-decoration:none;border-bottom:1px dotted var(--accent-cy);}"
        ".rd-htr a:hover{border-bottom-style:solid;}"
        ".rd-fence{display:flex;gap:9px;align-items:baseline;margin:8px 0 12px;padding:8px 12px;"
        "background:var(--bg-2);border:1px solid var(--line-2);border-left:2px solid var(--ink-3);"
        "border-radius:0 8px 8px 0;max-width:1080px;}"
        ".rd-fence .rd-lbl{font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;"
        "color:var(--ink-3);font-weight:700;white-space:nowrap;flex:none;padding-top:2px;}"
        ".rd-fence .rd-txt{font-size:12px;line-height:1.5;color:var(--ink-2);}"
        ".rd-fence .rd-txt a{color:var(--accent-cy);text-decoration:none;}"
        # .rd-related — the sibling-lens cross-link chip row (S-B1). A pill strip that reads as
        # secondary chrome (muted until hover), sits just under the how-to-read link.
        ".rd-related{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:-2px 0 14px;max-width:1120px;}"
        ".rd-related .rd-lbl{font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;"
        "color:var(--ink-3);font-weight:700;white-space:nowrap;}"
        ".rd-related a{font-size:11.5px;color:var(--ink-2);text-decoration:none;background:var(--bg-2);"
        "border:1px solid var(--line-2);border-radius:999px;padding:3px 10px;"
        "transition:color .12s,border-color .12s,background .12s;}"
        ".rd-related a:hover{color:var(--ink);border-color:var(--accent);background:var(--bg-3);}"
        ".rd-related .rd-rel-note{font-size:11px;color:var(--ink-3);}"
        "</style>")


def how_to_read_link(href: str = "/dash/reading-guide") -> str:
    """A small 'New here? How to read these charts' link — sits under the bottom-line on each
    user-facing lens, pointing at the visual reading guide."""
    return f'<div class="rd-htr"><a href="{href}">New here? How to read these charts →</a></div>'


def bottom_line(text_html: str) -> str:
    """The single-sentence takeaway band — sits at the top of a page, above the intro."""
    return f'<div class="rd-bottom"><span class="rd-lbl">Bottom line</span><span class="rd-txt">{text_html}</span></div>'


def plain(text_html: str) -> str:
    """The 'in plain English' translation line — sits under a chart's technical caption."""
    return f'<div class="rd-plain"><span class="rd-lbl">In plain English</span><span class="rd-txt">{text_html}</span></div>'


def demo_framing() -> str:
    """The falsification-forward framing sentence (UX audit S-A, Codex R2): shown wherever
    failed or uncertified studies are published, so the honesty posture reads as a moat —
    never as "nothing here works". One wording, shared. Complements fence() below: fence()
    single-sources the short "not advice / not a signal" boundary CLAUSE; this is the longer
    "why we publish failures" framing block."""
    return ('<div class="rd-plain" style="margin-top:4px"><span class="rd-lbl">Why we publish this</span>'
            '<span class="rd-txt">We publish failures and uncertified reads so descriptive context is '
            'never mistaken for alpha — the honest boundary IS the product.</span></div>')


# ── the descriptive-only fence — ONE sanctioned vocabulary (S-C, replaces the ≥9 accidental
#    hand-written phrasings that had drifted across ~24 rendered sites). Every user-facing lens
#    carries a boundary telling the reader what the page is NOT (advice / a signal / a pick). This
#    dict is the single source of that wording. Add a KIND here — never hand-write a fence again.
_FENCE_COPY = {
    "not_advice":   "descriptive, not advice",              # disclosures / filings (insider, SAST, SHP, ratings)
    "arithmetic":   "arithmetic, not advice",               # calculators (buyback)
    "not_signal":   "descriptive, not a signal",            # state reads (move-anatomy; internals keeps its bespoke 'point-in-time' line)
    "context":      "context, not a signal",                # short inline positioning/headline notes (participants, MEP headlines)
    "not_reco":     "descriptive, not a recommendation",    # screens / rankings (launchpad, screen+, seasonal-screen)
    "not_buy":      "descriptive, not a buy call",          # directional verdict, bullish side (strategist)
    "not_sell":     "descriptive, not a sell call",         # directional verdict, bearish side (strategist)
    "not_buy_sell": "descriptive, not a buy/sell signal",   # chart overlays (harmonic, MACD, compare)
    "not_tradeable": "descriptive calendar context — never a signal",  # seasonal (net-of-cost caveat)
}


def fence(kind: str, detail: str = "", *, sep: str = " · ", cap: bool = False) -> str:
    """The canonical descriptive-only boundary CLAUSE for a lens — single source of the fence
    wording (S-C; migrated the ≥9 hand-written variants here). Returns just the phrase text so it
    drops into ANY existing markup byte-preservingly: an <h2> <small> subtitle tail, a note <div>,
    an <li> lead, a title= tooltip. `detail` is an optional page-specific lead-in
    (e.g. "broadcast-date anchored") kept verbatim BEFORE the boundary (nothing-discarded).
    `cap` upper-cases the first letter for sentence-initial use ("Descriptive, not advice").
    `kind` MUST be a sanctioned key — an unknown key raises KeyError by design, so a new page
    can't quietly invent a 10th phrasing (add a kind to _FENCE_COPY instead)."""
    phrase = _FENCE_COPY[kind]
    out = f"{detail}{sep}{phrase}" if detail else phrase
    return (out[:1].upper() + out[1:]) if cap else out


def fence_note(kind: str, detail: str = "", extra_html: str = "") -> str:
    """A standard rendered 'honest boundary' note — the SHARED VISUAL for pages that want the
    fence as its own element (rather than a clause inside other markup). `extra_html` appends a
    trailing link etc. Uses the .rd-fence style from readability_css(). New pages should prefer
    this; the pre-sprint pages embed fence() as a clause and are left visually unchanged."""
    body = fence(kind, detail, cap=True)
    return (f'<div class="rd-fence"><span class="rd-lbl">Honest boundary</span>'
            f'<span class="rd-txt">{body}.{(" " + extra_html) if extra_html else ""}</span></div>')


# ── "Related lenses" cross-reference (UX audit S-B1, items 4 / 8 / 9) ─────────────────
# The left rail already GROUPS siblings; this adds the CROSS-GROUP connective tissue the rail
# cannot express — e.g. the All-weather map (a "Strength & momentum" lens) shares its columns
# with RRG and RS-Band (a "Rotation" lens). Curated adjacency (NOT group-derived) so it can
# carry those cross-group relations; labels + routes resolve from lens_registry so the strip can
# never drift from the nav. Rendered once near the top of a family page — the generalisation of
# the seasonal trio's `_subnav` strip to the RS/rotation family (item 9).
_RELATED: dict[str, tuple[str, ...]] = {
    # RS / rotation / strength cluster — different views of the same relative-strength data.
    "rrg":          ("rotation", "rsband", "cycle-clock", "capture-map"),
    "rotation":     ("rrg", "rsband", "cycle-clock"),
    "rsband":       ("rrg", "rotation", "cycle-clock", "capture-map"),
    "cycle-clock":  ("rrg", "rotation", "rsband"),
    "capture-map":  ("rrg", "rsband", "rs-hub"),
    "momentum-scan": ("leaders", "divergence", "rs-hub"),
    # sector strength (share prices) ⇄ sector economics (business quality) — two sides of one coin.
    "sector-economics": ("sectors", "sector-momentum"),
    "sectors":      ("sector-economics", "sector-momentum"),
    # Ownership & filings — the SEBI disclosure feeds, one family (read one, the others are next door).
    "insider":      ("ratings", "sast", "shp"),
    "ratings":      ("insider", "sast", "shp"),
    "sast":         ("insider", "ratings", "shp"),
    "shp":          ("insider", "ratings", "sast"),
    # Patterns — the two chart-pattern scanners.
    "harmonic-scan": ("wolfe-scan",),
    "wolfe-scan":    ("harmonic-scan",),
}


def related_strip(key: str, note: str = "") -> str:
    """A compact 'Related' chip row linking a page to its curated sibling lenses (S-B1).
    Labels + routes come from lens_registry so it never drifts; an unknown key, a stale
    reference, or a missing registry is skipped SILENTLY (never a dead link, never a 500),
    so any page can call it unconditionally. `note` is an optional one-line context lead
    (e.g. "different views of the same relative-strength data"). Uses the .rd-related style
    from readability_css(). Returns '' when the key has no adjacency."""
    keys = _RELATED.get(key)
    if not keys:
        return ""
    try:
        from src.web import lens_registry as _LR
    except Exception:  # noqa: BLE001 — registry unavailable → no strip, never fatal
        return ""
    chips = []
    for k in keys:
        ln = _LR.BY_KEY.get(k)
        if not ln or not ln.route:
            continue
        chips.append('<a href="%s">%s</a>' % (ln.route, ln.label))
    if not chips:
        return ""
    lead = ('<span class="rd-rel-note">%s</span>' % note) if note else ""
    return ('<div class="rd-related"><span class="rd-lbl">Related</span>'
            + "".join(chips) + lead + "</div>")


def _selftest() -> int:
    import re
    assert readability_css().startswith("<style>") and "rd-bottom" in readability_css()
    # .rd-related is single-sourced in the scaffold CSS (every family page already loads it).
    assert "rd-related" in readability_css()
    # related_strip: resolves labels/routes from the registry, carries the optional note, and
    # is skip-safe for an unknown key. Every _RELATED target must be a real, routed lens.
    from src.web import lens_registry as _LR
    for _k, _targets in _RELATED.items():
        assert _LR.BY_KEY.get(_k), "related-strip source key not a lens: %s" % _k
        for _t in _targets:
            _ln = _LR.BY_KEY.get(_t)
            assert _ln and _ln.route, "related-strip target not a routed lens: %s->%s" % (_k, _t)
    _rs = related_strip("capture-map", note="one dataset")
    assert 'class="rd-related"' in _rs and "/dash/rrg" in _rs and "one dataset" in _rs
    assert related_strip("no-such-lens") == "", "unknown key must render nothing"
    assert 'class="rd-bottom"' in bottom_line("x") and 'class="rd-plain"' in plain("y")
    # fence: every sanctioned kind renders; detail is kept verbatim before the boundary; the
    # rendered note wraps the clause; an unknown kind is a hard error (can't invent a 10th phrasing).
    assert "rd-fence" in readability_css()
    for _k in _FENCE_COPY:
        assert fence(_k) == _FENCE_COPY[_k]
        assert fence(_k, "anchored here").startswith("anchored here · ")
        assert fence(_k, cap=True)[:1].isupper()
        assert 'class="rd-fence"' in fence_note(_k)
    assert fence("not_advice") == "descriptive, not advice"
    assert fence("arithmetic", cap=True) == "Arithmetic, not advice"
    try:
        fence("bogus_kind"); raise AssertionError("unknown fence kind must raise")
    except KeyError:
        pass
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
