"""src/web/home/internals_pages.py — the Graphite Markets estate (lane W2-A of the cutover).

FOUR consolidated, evidence-linked Graphite pages that carry ELEVEN classic Markets lenses into
the new experience. Consolidation, not transliteration: the classic estate answered the same
question from many doors, so each page here is ONE question with its evidence stacked under it.

    /dash/home/internals   How healthy is the market beneath the index?
                           <- market-internals · divergence
    /dash/home/flows       Who is positioned, and how crowded is the book?
                           <- participants · fno   (+ the home's own FII/DII cash reads)
    /dash/home/events      What is scheduled, what just happened, what is restricted?
                           <- actions · results-reactions · event-cadence · buyback-calc ·
                              surveillance · band-locks
    /dash/home/attention   What changed that deserves my attention?
                           <- attention   (the depth behind the home's "What changed today")

Each is a DECLARED CHILD of the Graphite home (registered in
`tests/test_dash_route_registry.INTERNAL_DEV`, no `lens_registry` entry — nav is generated from
the registry and adding one now would drift the classic nav; registering a lens IS the cutover).
The classic lenses stay live and byte-untouched at their own routes.

House rules honoured here: fixed-size boxes that scroll INTERNALLY (never a flat endless page) ·
Free is a complete, honest page and Pro adds the REFERENCE layer (`C.ref_chip` / `C.pro_more` /
`C.pro_teaser`) · every view is URL-addressable and every table has a server CSV (`?format=csv`)
· plain English first · symbols deep-link to the Graphite stock page · descriptive-only fences
travel WITH their surface, never in a footnote.

Isolation: renders only through `components as C` + a lane-scoped `.gw2-*` stylesheet passed via
`shell(extra_head=)`; imports no preview/legacy render module (gate: tests/test_home_isolation).
All data comes from `internals_reads` (which itself reuses the home's `reads.*` wherever a read
already exists). A heavy or edge read must never 500 a page — every route is defensive.
"""
from __future__ import annotations

import datetime as _dt

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.web.home import components as C
from src.web.home import internals_reads as R
from src.web.home import shell

router = APIRouter()

# ── the lane's cross-links: the four pages are each other's siblings until W6 wires nav ──────
PAGES = (
    ("internals", "/dash/home/internals", "Market internals"),
    ("flows", "/dash/home/flows", "Flows &amp; positioning"),
    ("events", "/dash/home/events", "Events &amp; restrictions"),
    ("attention", "/dash/home/attention", "What changed"),
)

# W6 WIRED THE NAV (2026-07-27) — the line above said "until W6 wires nav", and this is that.
# The Markets top-bar door lands on `internals`, so this strip is the ONLY inbound path to the rest
# of the Markets estate. W2-B (strength · sectors) and W2-C (seasonal · patterns · own-history ·
# anatomy · compare) each shipped their pages cross-linked to EACH OTHER but with nothing linking
# INTO the group — measured, not assumed: rendered on the box, `/dash/home/internals` emitted zero
# hrefs to any of the seven. Post-cutover that is seven finished pages a reader cannot reach, so
# they join the strip as a second row of cross-links. `scripts/nav_integrity_gate.py` contract D
# now fails the build if a future Graphite page ships without an inbound link.
CROSS = (
    ("/dash/home/rotation", "Sector rotation"),
    ("/dash/home/strength", "Relative strength"),
    ("/dash/home/sectors", "Sectors"),
    ("/dash/home/seasonal", "Seasonal"),
    ("/dash/home/patterns", "Patterns"),
    ("/dash/home/own-history", "Own history"),
    ("/dash/home/anatomy", "Move anatomy"),
    ("/dash/home/compare", "Compare"),
)


def _subnav(current: str) -> str:
    out = ['<nav class="gw2-sub" aria-label="Markets depth">']
    for key, href, label in PAGES:
        cur = ' aria-current="page"' if key == current else ""
        out.append('<a href="' + href + '"' + cur + ">" + label + "</a>")
    for href, label in CROSS:
        out.append('<a class="gw2-sub-x" href="' + href + '">' + label + "</a>")
    out.append("</nav>")
    return "".join(out)


# ── lane-scoped stylesheet (never touches components.css(); passed as extra_head) ────────────
_CSS = """<style>/* gw2-markets */
:root[data-ui-g] .gw2-sub{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}
:root[data-ui-g] .gw2-sub a{font:600 11.5px/1 var(--font);letter-spacing:.03em;color:var(--ink-2);
  background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r-pill);padding:7px 13px;text-decoration:none}
:root[data-ui-g] .gw2-sub a[aria-current="page"]{color:var(--on-accent);background:var(--accent);border-color:var(--accent)}
:root[data-ui-g] .gw2-sub a:hover{color:var(--ink);text-decoration:none}
:root[data-ui-g] .gw2-sub a[aria-current="page"]:hover{color:var(--on-accent)}
:root[data-ui-g] .gw2-seg{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 10px}
:root[data-ui-g] .gw2-seg a{font:600 11px/1 var(--mono);color:var(--ink-3);background:var(--bg-0);
  border:1px solid var(--line);border-radius:var(--r-pill);padding:5px 11px;text-decoration:none}
:root[data-ui-g] .gw2-seg a.on{color:var(--ink);background:var(--bg-3);border-color:var(--line-2)}
:root[data-ui-g] .gw2-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:9px;margin:0 0 12px}
:root[data-ui-g] .gw2-tile{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 12px}
:root[data-ui-g] .gw2-tile .n{font:800 22px/1.05 var(--mono);font-variant-numeric:tabular-nums}
:root[data-ui-g] .gw2-tile .l{font-size:11.5px;font-weight:700;margin-top:5px;color:var(--ink)}
:root[data-ui-g] .gw2-tile .s{font-size:10.5px;color:var(--ink-3);margin-top:2px;line-height:1.4}
:root[data-ui-g] .gw2-scroll{max-height:340px;overflow-y:auto;overflow-x:auto;scrollbar-width:thin;
  scrollbar-color:var(--line-2) transparent;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--bg-0)}
:root[data-ui-g] .gw2-scroll.sm{max-height:220px}
:root[data-ui-g] .gw2-scroll.lg{max-height:440px}
:root[data-ui-g] table.gw2-t{width:100%;border-collapse:collapse;font-size:12.5px}
:root[data-ui-g] table.gw2-t th{position:sticky;top:0;z-index:1;background:var(--bg-1);color:var(--ink-3);
  font:600 10px/1.6 var(--font);letter-spacing:.06em;text-transform:uppercase;text-align:right;padding:7px 9px;
  border-bottom:1px solid var(--line-2);white-space:nowrap}
:root[data-ui-g] table.gw2-t td{padding:5px 9px;text-align:right;border-bottom:1px solid var(--line);
  font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink-2)}
:root[data-ui-g] table.gw2-t th.l,:root[data-ui-g] table.gw2-t td.l{text-align:left}
:root[data-ui-g] table.gw2-t td.k{color:var(--ink);font-weight:700}
:root[data-ui-g] table.gw2-t tr:last-child td{border-bottom:0}
:root[data-ui-g] .gw2-pill{display:inline-block;font:700 10px/1.5 var(--mono);padding:1px 7px;
  border-radius:var(--r-pill);background:var(--bg-3);border:1px solid var(--line-2);color:var(--ink-2)}
:root[data-ui-g] .gw2-pill.up{color:var(--up);border-color:var(--up)}
:root[data-ui-g] .gw2-pill.dn{color:var(--down);border-color:var(--down)}
:root[data-ui-g] .gw2-pill.wn{color:var(--warn);border-color:var(--warn)}
:root[data-ui-g] .up{color:var(--up)} :root[data-ui-g] .dn{color:var(--down)}
:root[data-ui-g] .gw2-h3{font:700 13px/1.4 var(--font);margin:16px 0 6px;color:var(--ink)}
:root[data-ui-g] .gw2-h3 small{font-weight:400;color:var(--ink-3);font-size:11.5px;margin-left:6px}
:root[data-ui-g] .gw2-read{background:var(--bg-0);border:1px solid var(--line);border-left:3px solid var(--warn);
  border-radius:var(--r-sm);padding:9px 13px;margin:10px 0 4px;font-size:12.5px;color:var(--ink-2);line-height:1.55}
:root[data-ui-g] .gw2-read b{color:var(--ink)}
:root[data-ui-g] .gw2-chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
:root[data-ui-g] .gw2-chip{background:var(--bg-0);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:8px 11px;font-size:11.5px;color:var(--ink-2);max-width:330px;line-height:1.5}
:root[data-ui-g] .gw2-chip .h{display:block;font:700 9.5px/1 var(--mono);letter-spacing:.08em;
  text-transform:uppercase;color:var(--accent);margin-bottom:4px}
:root[data-ui-g] .gw2-chip b{color:var(--ink)}
:root[data-ui-g] .gw2-svg{width:100%;height:auto;display:block;background:var(--bg-0);
  border:1px solid var(--line);border-radius:var(--r-sm)}
:root[data-ui-g] .gw2-lbl{font:600 10.5px/1.5 var(--mono);letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink-3);margin:11px 0 3px}
:root[data-ui-g] .gw2-two{display:grid;grid-template-columns:minmax(0,1fr);gap:14px}
@media(min-width:900px){:root[data-ui-g] .gw2-two{grid-template-columns:repeat(2,minmax(0,1fr))}}
:root[data-ui-g] .gw2-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px;margin:0 0 10px}
:root[data-ui-g] .gw2-form label{display:block;font-size:11px;color:var(--ink-3);margin-bottom:3px}
:root[data-ui-g] .gw2-form input{width:100%;background:var(--bg-0);border:1px solid var(--line-2);
  border-radius:var(--r-sm);color:var(--ink);font:600 13px var(--mono);padding:7px 9px}
:root[data-ui-g] .gw2-out{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:9px}
:root[data-ui-g] .gw2-csv{font-size:11px;color:var(--ink-3);margin:7px 0 0}
</style>"""


# ── small render atoms (lane-owned; nothing here reaches into components' privates) ──────────
def _sym(s) -> str:
    """A symbol that deep-links to the GRAPHITE stock page (the W1 lane's route). `sym=`, never
    `symbol=` — the site-wide query-key convention."""
    e = C.esc(s)
    return '<a href="/dash/home/stock?sym=' + e + '">' + e + "</a>"


def _n(v, dp: int = 2, suffix: str = "") -> str:
    try:
        return f"{float(v):,.{dp}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _sn(v, dp: int = 2, suffix: str = "") -> str:
    """A SIGNED number with up/down colour (signed values are the only place colour is a fact)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '<span class="g-num">—</span>'
    cls = "up" if f >= 0 else "dn"
    return '<span class="g-num ' + cls + '">' + f"{f:+,.{dp}f}{suffix}" + "</span>"


def _scroll(inner: str, size: str = "") -> str:
    return '<div class="gw2-scroll' + ((" " + size) if size else "") + '">' + inner + "</div>"


def _table(heads, body_rows: str) -> str:
    """heads = [(label, align)] with align 'l' or 'r'."""
    th = "".join('<th class="l">' + h + "</th>" if a == "l" else "<th>" + h + "</th>"
                 for h, a in heads)
    return ('<table class="gw2-t"><thead><tr>' + th + "</tr></thead><tbody>"
            + body_rows + "</tbody></table>")


def _tile(label: str, big: str, sub: str = "", ref_html: str = "") -> str:
    return ('<div class="gw2-tile"><div class="n">' + big + '</div><div class="l">' + C.esc(label)
            + "</div>" + ('<div class="s">' + C.esc(sub) + "</div>" if sub else "")
            + ref_html + "</div>")


def _seg(base: str, param: str, options, active, extra: str = "") -> str:
    """A URL-addressable segmented control (server-side links — state lives in the URL, always
    shareable, no JS)."""
    out = ['<div class="gw2-seg" role="group">']
    for val, label in options:
        on = str(val) == str(active)
        href = base + "?" + param + "=" + C.esc(str(val)) + (("&" + extra) if extra else "")
        out.append('<a' + (' class="on" aria-current="true"' if on else "") + ' href="' + href
                   + '">' + C.esc(label) + "</a>")
    out.append("</div>")
    return "".join(out)


def _csv_note(route: str, qs: str = "") -> str:
    href = route + "?format=csv" + (("&" + qs) if qs else "")
    return ('<p class="gw2-csv">Every number on this page is read from primary exchange data · '
            '<a href="' + href + '">download this view as CSV →</a></p>')


def _roll(vals, k: int) -> list:
    """Centred-trailing moving average that preserves None gaps — the classic smoothing."""
    out, buf = [], []
    for v in vals:
        f = R._f(v)
        if f is not None:
            buf.append(f)
            if len(buf) > k:
                buf.pop(0)
        out.append(sum(buf) / len(buf) if buf else None)
    return out


def _series_svg(vals, h: int = 96, signed: bool = False, tone: str = "acc",
                label: str = "") -> str:
    """A server-computed SVG strip for a numeric series (DOM-safe: no client interpolation).
    `signed=True` draws a zero baseline and colours above/below."""
    pts = [(i, R._f(v)) for i, v in enumerate(vals)]
    pts = [(i, v) for i, v in pts if v is not None]
    if len(pts) < 2:
        return C.empty("Not enough history to draw this yet.")
    W = 900.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    lo, hi = min(ys), max(ys)
    if signed:
        m = max(abs(lo), abs(hi)) or 1.0
        lo, hi = -m, m
    if hi == lo:
        hi = lo + 1.0

    def X(i):
        return (i - x0) / ((x1 - x0) or 1) * W

    def Y(v):
        return h - (v - lo) / (hi - lo) * h

    line = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in pts)
    base = Y(0.0) if signed else h
    fill = ('<polygon points="%.1f,%.1f %s %.1f,%.1f" fill="var(--%s)" opacity=".14"/>'
            % (X(pts[0][0]), base, line, X(pts[-1][0]), base,
               "up" if tone == "up" else ("accent" if tone == "acc" else tone)))
    zero = ('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--line-2)" stroke-width="1"/>'
            % (base, W, base)) if signed else ""
    col = "var(--%s)" % ("up" if tone == "up" else ("accent" if tone == "acc" else tone))
    dot = '<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (X(pts[-1][0]), Y(pts[-1][1]), col)
    return ('<svg class="gw2-svg" viewBox="0 0 900 ' + str(h) + '" preserveAspectRatio="none" '
            'role="img" aria-label="' + C.esc(label or "series") + '">' + fill + zero
            + '<polyline points="' + line + '" fill="none" stroke="' + col
            + '" stroke-width="2" stroke-linejoin="round"/>' + dot + "</svg>")


def _page(title: str, current: str, body: str, pat: str = "") -> HTMLResponse:
    return HTMLResponse(shell.shell(title, _subnav(current) + body, extra_head=_CSS,
                                    current="Markets", pat_html=pat))


def _csv(rows, header) -> PlainTextResponse:
    """A server-rendered CSV (the playbook's server-CSV rule — never a client-only export)."""
    def cell(v):
        s = "" if v is None else str(v)
        return '"' + s.replace('"', '""') + '"' if ("," in s or '"' in s or "\n" in s) else s
    out = [",".join(header)] + [",".join(cell(c) for c in r) for r in rows]
    return PlainTextResponse("\n".join(out) + "\n", media_type="text/csv; charset=utf-8")


def _dock(conn) -> str:
    try:
        from src.web.home import pat_dock
        return pat_dock.dock_html(conn)
    except Exception:  # noqa: BLE001 — the copilot dock is never load-bearing for a page
        return ""


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — /dash/home/internals
# ══════════════════════════════════════════════════════════════════════════════════════
_INTERNALS_FENCE = (
    "The market's own vital signs, straight from the tape — how many stocks actually rose, "
    "whether buyers paid up for them, how much was delivered, and how independently names moved. "
    "Descriptive market-state, point-in-time. Breadth is not an index return and none of this is "
    "a signal, a ranking or advice."
)


def _internals_tiles(pack: dict) -> str:
    """The five vital signs. FREE = the number + a plain-English band. PRO = the reference —
    where that number sits in the full 2004-> history, the typical value, and which way it is
    moving (the owner's binding principle: a number in isolation is useless)."""
    vals, refs = pack.get("values") or {}, pack.get("refs") or {}
    out = []
    for key, _col, label, unit, dp, low_w, high_w in R.INTERNALS_METRICS:
        v = vals.get(key)
        ref = refs.get(key) or {}
        p = ref.get("pctile")
        band = "—"
        if p is not None:
            band = high_w if p >= 66 else (low_w if p <= 33 else "middle of its range")
        big = ('<span class="g-num">' + _n(v, dp) + C.esc(unit) + "</span>") if v is not None else "—"
        out.append(_tile(label, big, band,
                         C.ref_chip(ref, unit=unit, dp=dp, trend=ref.get("trend"))))
    return '<div class="gw2-tiles">' + "".join(out) + "</div>"


def _internals_hero(pack: dict, window: str) -> str:
    """THE HERO: price-breadth vs the tape. When price-breadth rises while the tape distributes,
    the market is being DISTRIBUTED INTO STRENGTH — a warning a cap-weighted index cannot show."""
    rows = pack.get("rows") or []
    if len(rows) < 3:
        return C.empty("The internals snapshot hasn't landed enough history yet.")
    k = max(5, len(rows) // 60)
    pb = _roll([(R._f(r.get("pct_adv")) - 50.0) if r.get("pct_adv") is not None else None
                for r in rows], k)
    tp = _roll([r.get("mep_net") for r in rows], k)
    last = rows[-1]
    pa, mn = R._f(last.get("pct_adv")), R._f(last.get("mep_net"))
    read = "Today's divergence read is unavailable for this session."
    if pa is not None and mn is not None:
        price_up, tape_up = (pa >= 50), (mn >= 0)
        if price_up and not tape_up:
            read = ("<b>More stocks are rising than falling while the tape distributes</b> — "
                    "advances are being sold into. The index can hide this entirely.")
        elif (not price_up) and tape_up:
            read = ("<b>More stocks are falling than rising while the tape accumulates</b> — "
                    "weakness is being bought. Declines are meeting real demand.")
        elif price_up:
            read = "<b>Breadth and the tape agree, positively</b> — advances are backed by buying effort."
        else:
            read = "<b>Breadth and the tape agree, negatively</b> — declines are backed by selling effort."
    return ('<div class="gw2-lbl">Price-breadth · % advancing (smoothed, centred at 50)</div>'
            + _series_svg(pb, h=96, signed=True, tone="acc", label="Price breadth")
            + '<div class="gw2-lbl">The tape · net accumulation − distribution (smoothed)</div>'
            + _series_svg(tp, h=96, signed=True, tone="warn", label="The tape")
            + '<div class="gw2-read">' + read + "</div>"
            + C.learn("Two strips. The top is how many stocks rose versus fell each day. The bottom "
                      "is whether buyers were paying up or quietly stepping back. They usually agree — "
                      "where they part company is the story. Neither line predicts anything; both "
                      "describe what already happened."))


def _internals_regimes(pack: dict) -> str:
    rows = pack.get("rows") or []
    if len(rows) < 3:
        return ""
    k = max(5, len(rows) // 60)
    blocks = [
        ("Delivery conviction — is it real buying?", "avg_dp", "acc",
         "The share of volume actually taken to demat rather than churned intraday. It fell "
         "structurally from roughly 64% (2004-13) to the mid-50s after 2020 as the F&O and algo era "
         "took over — and it SPIKES on panic days, when intraday traders vanish and only genuine "
         "holders transact."),
        ("Dispersion — stock-picker's or macro market?", "disp", "warn",
         "How far apart daily returns sit across the universe. High means names move on their own "
         "merits, so selection matters more; low means everything moves together on the day's big "
         "news. It jumps in every crisis."),
        ("Coil — the market's volatility spring", "avg_comp", "acc",
         "Average range compression across the universe. Below 1 the market is wound tight and "
         "quiet; above 1 it is snapping around. The violent readings line up with the crashes."),
    ]
    out = ""
    for title, col, tone, plain in blocks:
        out += ('<div class="gw2-h3">' + C.esc(title) + "</div>"
                + _series_svg(_roll([r.get(col) for r in rows], k), h=84, tone=tone, label=title)
                + C.learn(plain))
    return out


def _internals_anchors(pack: dict) -> str:
    anchors = pack.get("anchors") or []
    if not anchors:
        return C.empty("The history needed for the crisis fingerprints hasn't landed yet.")
    body = ""
    for a in anchors:
        body += ("<tr><td class=\"l k\">" + C.esc(a.get("d")) + "</td>"
                 '<td class="l">' + C.esc(a.get("label")) + "</td>"
                 "<td>" + _n(a.get("pct_adv"), 0, "%") + "</td>"
                 "<td>" + _sn(a.get("mep_net"), 0) + "</td>"
                 "<td>" + _n(a.get("avg_dp"), 0, "%") + "</td>"
                 "<td>" + _n(a.get("disp"), 2) + "</td>"
                 "<td>" + _n(a.get("avg_comp"), 2) + "</td></tr>")
    return (_scroll(_table([("Date", "l"), ("What happened", "l"), ("Advancing", "r"),
                            ("Tape", "r"), ("Delivery", "r"), ("Dispersion", "r"), ("Coil", "r")],
                           body), "sm")
            + C.learn("A sanity check, not a study: the same five gauges on the days everyone "
                      "remembers. On crash days almost nothing rose, buying pressure was deeply "
                      "negative and trading was violent — exactly what you would expect if the "
                      "gauges are measuring what they claim to."))


def _internals_drill(pack: dict, drill: dict, window: str) -> str:
    """The texture behind a breadth number: pick a recent session, see who actually moved it."""
    sessions = pack.get("sessions") or []
    if not sessions:
        return ""
    cur = (drill or {}).get("d") or ""
    chips = ""
    for d in sessions[::-1][:20]:
        on = ' class="on" aria-current="true"' if d == cur else ""
        chips += ("<a" + on + ' href="/dash/home/internals?window=' + C.esc(window)
                  + "&drill=" + C.esc(d) + '">' + C.esc(str(d)[5:]) + "</a>")
    body = '<div class="gw2-seg">' + chips + "</div>"
    if not drill:
        return body + C.empty("Pick a session above to see the names that carried it.")
    cols = ""
    for title, key in (("Biggest risers", "up"), ("Biggest fallers", "down")):
        rows = ""
        for z in drill.get(key) or []:
            rows += ('<tr><td class="l k">' + _sym(z.get("symbol")) + "</td>"
                     "<td>" + _sn(z.get("chg"), 2, "%") + "</td>"
                     "<td>" + _n((z.get("dval") or 0) / 1e7, 2, " cr") + "</td></tr>")
        cols += ('<div><div class="gw2-lbl">' + title + " · " + C.esc(drill.get("d")) + "</div>"
                 + _scroll(_table([("Symbol", "l"), ("Move", "r"), ("Delivered", "r")],
                                  rows or '<tr><td class="l">—</td><td>—</td><td>—</td></tr>'),
                           "sm") + "</div>")
    return body + '<div class="gw2-two">' + cols + "</div>"


def _divergence_block(div: dict) -> str:
    """The RSI-of-RS divergence watch (classic /dash/divergence), rebuilt in the Graphite kit."""
    edu = C.learn("A divergence is a CHARACTERISATION of what already happened to a sector's "
                  "relative strength versus the broad market — the line and its momentum "
                  "disagreeing. It is an early-warning description, never a buy or sell "
                  "instruction, and nothing here is ranked or scored.")
    bull, bear = div.get("bull") or [], div.get("bear") or []
    if not bull and not bear:
        return (C.empty("No relative-strength divergences are flagged right now — the nightly RS "
                        "run flags them when they appear.") + edu)

    def col(title, items, cls, note):
        rows = ""
        for it in items:
            rsi = it.get("rsi")
            rows += ('<tr><td class="l k">' + C.esc(str(it.get("name") or "").replace("Nifty ", ""))
                     + "</td><td>" + (_n(rsi, 0) if rsi is not None else "—") + "</td>"
                     '<td class="l">' + C.esc(it.get("date") or "") + "</td></tr>")
        return ('<div><div class="gw2-lbl"><span class="gw2-pill ' + cls + '">' + title
                + "</span></div>"
                + _scroll(_table([("Index / sector", "l"), ("RSI-of-RS", "r"), ("Flagged", "l")],
                                 rows or '<tr><td class="l">none</td><td>—</td><td class="l">—</td></tr>'),
                          "sm")
                + '<p class="gw2-csv">' + C.esc(note) + "</p></div>")

    strip = ""
    for title, key, cls in (("Oversold", "oversold", "up"), ("Overbought", "overbought", "wn")):
        items = div.get(key) or []
        if not items:
            continue
        strip += ('<span class="gw2-chip"><span class="h">' + title + "</span>"
                  + C.esc(" · ".join("%s %s" % (str(i["name"]).replace("Nifty ", ""), _n(i["rsi"], 0))
                                     for i in items)) + "</span>")
    return ('<div class="gw2-two">'
            + col("Bullish divergence", bull, "up",
                  "Relative strength made a lower low but its momentum made a higher low — the "
                  "decline is losing force.")
            + col("Bearish divergence", bear, "dn",
                  "Relative strength made a higher high but its momentum made a lower high — the "
                  "advance is losing force.")
            + "</div>"
            + (('<div class="gw2-lbl">Momentum extremes</div><div class="gw2-chips">' + strip
                + "</div>") if strip else "")
            + edu)


_NO_INTERNALS = ("The market-internals snapshot hasn't been built on this host yet. It is derived "
                 "from the bhav copy plus the delivery tape, one row per trading day — this page "
                 "reads it and never fabricates a series.")


def _internals_body(conn, window: str, drill_date: str) -> str:
    """Every zone renders in BOTH states. An empty read shows an honest empty body — it never
    removes the block (a disappearing section reads as "this doesn't exist") and never removes the
    fence or the education with it."""
    pack = R.internals_pack(conn, window)
    div = R.rs_divergence(conn)
    drill = R.internals_drill(conn, drill_date) if (pack and drill_date) else {}
    seg = _seg("/dash/home/internals", "window",
               (("1y", "1 year"), ("3y", "3 years"), ("5y", "5 years"), ("all", "Full history")),
               window)
    edu_vitals = C.learn("Five numbers describe the market underneath the one everyone quotes: how "
                         "many stocks rose, whether buyers paid up, how much was actually "
                         "delivered, how independently names moved, and how wound-up the tape is.")
    regimes = _internals_regimes(pack)
    sub = ("as of " + C.esc(pack.get("as_of") or "") + " · " + str(pack.get("all_n") or 0)
           + " sessions on record") if pack else "awaiting the nightly snapshot"
    return (
        C.fence(_INTERNALS_FENCE)
        + C.zone("The market's vital signs", "market_internals_daily · nightly",
                 (_internals_tiles(pack) if pack else C.empty(_NO_INTERNALS)) + edu_vitals,
                 sub=sub, name="Vital signs")
        + C.zone("Price-breadth versus the tape", "market_internals_daily · nightly",
                 seg + _internals_hero(pack, window)
                 + _csv_note("/dash/home/internals", "window=" + C.esc(window)),
                 sub="the market's two breadths — where they part company is the story",
                 name="Breadth vs tape")
        + C.zone("Regimes — delivery, dispersion, coil", "market_internals_daily · nightly",
                 C.pro_teaser(regimes, cta_sub="Delivery, dispersion and coil regimes over the "
                                               "full archive", advertise=False)
                 if regimes else C.empty(_NO_INTERNALS),
                 sub="the slower-moving backdrop", name="Regimes")
        + C.zone("What carried a session", "bhavcopy_rows · EOD",
                 _internals_drill(pack, drill, window) if pack
                 else C.empty("Pick a session once the internals snapshot has landed."),
                 sub="the names behind a breadth number", name="Session drill")
        + C.zone("Crisis fingerprints", "market_internals_daily · 2004→",
                 _internals_anchors(pack),
                 sub="the internals on the days everyone remembers", name="Crisis fingerprints")
        + C.zone("Divergence watch", "rs_extras · nightly", _divergence_block(div),
                 sub="relative strength vs its own momentum", name="Divergence watch")
    )


@router.get("/dash/home/internals", response_class=HTMLResponse, include_in_schema=False)
def internals_page(request: Request):
    """Market internals — the absolute health of the market beneath the index, back to 2004,
    plus the relative-strength divergence watch. Consolidates the classic /dash/market-internals
    and /dash/divergence. Read-only; never 500s."""
    from src.core.db import get_conn
    window = request.query_params.get("window", "1y")
    if window not in R.INTERNALS_WINDOWS:
        window = "1y"
    drill = str(request.query_params.get("drill", ""))[:10]
    fmt = request.query_params.get("format", "")
    body, pat = "", ""
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            if fmt == "csv":
                pack = R.internals_pack(conn, window)
                return _csv([(r.get("d"), r.get("adv"), r.get("dec"), r.get("pct_adv"),
                              r.get("avg_dp"), r.get("mep_net"), r.get("disp"), r.get("avg_comp"))
                             for r in (pack.get("rows") or [])],
                            ["date", "advancing", "declining", "pct_advancing", "delivery_pct",
                             "tape_net", "dispersion", "coil"])
            body = _internals_body(conn, window, drill)
            pat = _dock(conn)
    except Exception:  # noqa: BLE001 — a heavy/edge read must never 500 the page
        body = (C.fence("Market internals haven't landed on this host yet.")
                + C.empty("Check back after the next nightly run."))
    return _page("Market internals", "internals", body, pat)


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — /dash/home/flows
# ══════════════════════════════════════════════════════════════════════════════════════
_FLOWS_FENCE = (
    "Who is positioned which way, and how crowded that book already is. Cash flows are the "
    "exchange's post-close FII/DII prints; positioning is NSE participant-wise open interest and "
    "per-stock F&O open interest. Descriptive context (D62) — a percentile is not a forecast, and "
    "nothing here ranks, picks or recommends."
)
_FNO_PHASE0 = (
    "F&O honesty fence: the Phase-0 edge gate (2026-07-24) tested these reads for cross-sectional "
    "edge. Only PCR selected at all, weakly (δ≈0.06) and FORWARD-TEST-ONLY; max-pain distance, "
    "basis and OI-change failed. This board ranks and flags — it never picks."
)


def _flows_cash(conn) -> str:
    """FII/DII cash — REUSED from the home's own reads (sister-data rule: extend, never rebuild)."""
    from src.web.home import reads
    rows = reads.fii_dii_recent(conn)
    if not rows:
        return C.empty("FII/DII cash flows haven't landed for today yet.")
    deep = reads.fii_dii_deep(conn)
    return (C.flows_block(rows, deep=deep)
            + C.learn("Foreign and domestic institutions publish their cash-market buying and "
                      "selling after the close. Only the two aggregate categories exist in the "
                      "exchange feed — there is no cash-versus-derivatives split to show, so none "
                      "is invented here."))


def _participants_block(p: dict) -> str:
    if not p:
        return C.empty("Participant open-interest data hasn't landed on this host yet.")
    stance = R.participant_stance_word(p.get("ratio"))
    ref = p.get("ratio_ref") or {}
    net = p.get("fii_net")
    tiles = _tile("FII index-futures stance", C.esc(stance.upper()),
                  ("long:short " + _n(p.get("ratio"), 2)) if p.get("ratio") else "ratio unavailable",
                  C.ref_chip(ref, dp=2))
    tiles += _tile("FII net index futures",
                   _sn((net / 1e5) if net is not None else None, 2, "L"),
                   "contracts, lakhs · as of " + C.esc(p.get("as_of") or ""))
    tiles += _tile("Stored history", '<span class="g-num">' + str(p.get("n_hist") or 0) + "</span>",
                   "sessions of participant OI")
    spark = ""
    series = [x for x in (p.get("ratio_series") or []) if x is not None]
    if len(series) >= 2:
        spark = ('<div class="gw2-lbl">FII long:short, recent sessions</div>'
                 + _series_svg(series, h=70, tone="acc", label="FII long to short ratio"))
    mirror = ""
    if p.get("opposite"):
        mirror = ('<div class="gw2-read"><b>Foreign investors and everyday clients are on opposite '
                  "sides</b> of index futures today — the classic institutional-versus-retail "
                  "split. It is an observation about positioning, not a verdict on who is right.</div>")
    body = ""
    for r in p.get("rows") or []:
        body += ('<tr><td class="l k">' + C.esc(r.get("label")) + "</td>"
                 "<td>" + _sn((r["idx_net"] / 1e5) if r.get("idx_net") is not None else None, 2, "L")
                 + "</td><td>" + _n(r.get("ls"), 2) + "</td>"
                 "<td>" + _sn((r["stk_net"] / 1e5) if r.get("stk_net") is not None else None, 2, "L")
                 + "</td><td>" + _sn((r["opt_bias"] / 1e5) if r.get("opt_bias") is not None else None,
                                     2, "L") + "</td></tr>")
    matrix = _scroll(_table([("Participant", "l"), ("Index futures net", "r"), ("Long : short", "r"),
                             ("Stock futures net", "r"), ("Index option lean", "r")], body), "sm")
    hist = ""
    for h in p.get("history") or []:
        hist += ('<tr><td class="l">' + C.esc(h.get("d")) + "</td>"
                 "<td>" + _sn((h["net"] / 1e5) if h.get("net") is not None else None, 2, "L")
                 + "</td><td>" + _n(h.get("ls"), 2) + "</td></tr>")
    hist_tbl = C.pro_more('<div class="gw2-lbl">Recent FII sessions</div>'
                          + _scroll(_table([("Date", "l"), ("Net", "r"), ("Long : short", "r")],
                                           hist), "sm"))
    return ('<div class="gw2-tiles">' + tiles + "</div>" + spark + mirror + matrix + hist_tbl
            + C.learn("FII = foreign investors · DII = Indian mutual funds and insurers · Pro = "
                      "professional trading desks · Client = everyday and wealthy retail. \"Long\" "
                      "is a bet up, \"short\" a bet down. Market-aggregate positioning, published "
                      "daily after the close — a sentiment descriptor, never a timing signal."))


def _fno_table(board: dict, limit: int, pro: bool = False) -> str:
    rows = (board.get("rows") or [])[:limit]
    if not rows:
        return C.empty("No F&O positioning rows for the latest session.")
    body = ""
    for r in rows:
        q = r.get("quadrant") or "—"
        qcls = ("up" if q in ("LONG_BUILDUP", "SHORT_COVER")
                else ("dn" if q in ("SHORT_BUILDUP",) else "wn"))
        body += ('<tr><td class="l k">' + _sym(r.get("sym")) + "</td>"
                 '<td class="l"><span class="gw2-pill ' + qcls + '">'
                 + C.esc(R.FNO_QUADRANTS.get(q, str(q).lower())) + "</span></td>"
                 "<td>" + str(r.get("streak") or 0) + "d</td>"
                 "<td>" + (_n(r.get("oi_pct"), 0) if r.get("oi_pct") is not None else "—") + "</td>"
                 "<td>" + (_n(r.get("pcr_pct"), 0) if r.get("pcr_pct") is not None else "—") + "</td>"
                 "<td>" + (_n(r.get("dist_pct"), 0) if r.get("dist_pct") is not None else "—") + "</td>"
                 "<td>" + _n(r.get("pcr"), 2) + "</td>"
                 "<td>" + _sn(r.get("dist"), 1, "%") + "</td></tr>")
    return _scroll(_table([("Symbol", "l"), ("Positioning", "l"), ("Held", "r"),
                           ("OI pctl", "r"), ("PCR pctl", "r"), ("Max-pain pctl", "r"),
                           ("PCR", "r"), ("vs max-pain", "r")], body),
                   "lg" if pro else "")


def _fno_block(board: dict, sort: str) -> str:
    seg = _seg("/dash/home/flows", "sort",
               (("oi_pct", "Crowdedness"), ("pcr_pct", "Put-heaviness"),
                ("dist_pct", "Max-pain gap"), ("streak", "Persistence"), ("sym", "A–Z")), sort)
    if not board:
        # the fence and the control stay on the page even with no rows — an honesty statement
        # that vanishes when the data is missing was never really attached to the surface.
        return (C.fence(_FNO_PHASE0) + seg
                + C.empty("Per-stock F&O open interest hasn't landed on this host yet."))
    chips = ""
    for f in board.get("flags") or []:
        chips += ('<div class="gw2-chip"><span class="h">' + C.esc(f.get("kind")) + "</span>"
                  + _sym(f.get("sym")) + " — " + C.esc(f.get("text")) + "</div>")
    free = _fno_table(board, 12)
    pro = C.pro_teaser(_fno_table(board, 200, pro=True),
                       cta_sub="The full F&O cross-section, every name ranked against its own history",
                       advertise=False)
    return (C.fence(_FNO_PHASE0) + seg
            + (('<div class="gw2-lbl">Reality checks read straight off the data</div>'
                '<div class="gw2-chips">' + chips + "</div>") if chips else "")
            + '<div class="gw2-lbl">Top names by the selected ranking</div>' + free
            + '<div class="gw2-lbl">The full cross-section</div>' + pro
            + _csv_note("/dash/home/flows", "sort=" + C.esc(sort))
            + C.learn("Every free tool shows today's F&O snapshot. The context nobody adds is "
                      "whether today is unusual FOR THIS NAME. A short-covering day on a book that "
                      "still sits in its 90th percentile of open interest means the shorts merely "
                      "rolled — they did not leave. Percentiles need at least "
                      + str(R.FNO_MINPTS) + " sessions of a stock's own history before they are "
                      "shown at all."))


def _flows_body(conn, sort: str) -> str:
    part = R.participants_pack(conn)
    board = R.fno_board(conn, sort)
    return (C.fence(_FLOWS_FENCE)
            + C.zone("Cash flows — foreign vs domestic", "fii_dii_flows · post-close",
                     _flows_cash(conn), sub="who bought the cash market today", name="Cash flows")
            + C.zone("Derivatives positioning — who is long, who is short",
                     "participant_oi · daily after close", _participants_block(part),
                     sub="FII · DII · Pro · Client", name="Participants")
            + C.zone("F&O positioning versus each stock's own history", "fno_oi_signals · nightly",
                     _fno_block(board, sort),
                     sub="is this crowded, or is this normal for this name?", name="F&O board"))


@router.get("/dash/home/flows", response_class=HTMLResponse, include_in_schema=False)
def flows_page(request: Request):
    """Flows & positioning — institutional cash flows, market-aggregate derivatives positioning,
    and every F&O name ranked against its own history. Consolidates the classic /dash/participants
    and /dash/fno beside the home's existing FII/DII reads. Read-only; never 500s."""
    from src.core.db import get_conn
    sort = request.query_params.get("sort", "oi_pct")
    if sort not in R.FNO_SORTS:
        sort = "oi_pct"
    fmt = request.query_params.get("format", "")
    body, pat = "", ""
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            if fmt == "csv":
                board = R.fno_board(conn, sort)
                return _csv([(r.get("sym"), r.get("date"), r.get("quadrant"), r.get("streak"),
                              r.get("oi_pct"), r.get("pcr_pct"), r.get("dist_pct"), r.get("pcr"),
                              r.get("dist"), r.get("basis"), r.get("n_hist"))
                             for r in (board.get("rows") or [])],
                            ["symbol", "trade_date", "positioning", "streak_days", "oi_pctile",
                             "pcr_pctile", "maxpain_pctile", "pcr", "maxpain_gap_pct", "basis_pct",
                             "own_history_sessions"])
            body = _flows_body(conn, sort)
            pat = _dock(conn)
    except Exception:  # noqa: BLE001
        body = (C.fence("Flow and positioning data hasn't landed on this host yet.")
                + C.empty("Check back after the next nightly run."))
    return _page("Flows & positioning", "flows", body, pat)


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — /dash/home/events
# ══════════════════════════════════════════════════════════════════════════════════════
_EVENTS_FENCE = (
    "The dated calendar — what goes ex, who reports, who is overdue against their own rhythm, and "
    "which names the exchange has put under restriction. This page states WHAT happens WHEN and "
    "stops there: the ledger closed both drift stories on the corporate-actions feed (dividend "
    "drift tested null, rebrand pump dead) and the tradeable results-reaction book was falsified."
)
_PEAD_FENCE = (
    "Descriptive only. This board is the honest residue of the 2026-07-05 post-earnings study, "
    "whose TRADEABLE version was falsified — net return/vol 0.10 against the benchmark's 0.85. "
    "Every number below is realized history or an explicitly labelled base rate, never a forecast "
    "for any single name."
)

_CA_LABEL = {"DIVIDEND": "Dividend", "BONUS": "Bonus", "SPLIT": "Split", "RIGHTS": "Rights",
             "BUYBACK": "Buyback", "DEMERGER": "Demerger", "SCHEME": "Scheme"}


_CA_EDU = ("An ex-date is the first day a share trades WITHOUT the entitlement — buy on or after it "
           "and the dividend, bonus or split goes to the seller. Splits and bonuses shown here are "
           "the same events that adjust every price series on this site. Logistics, not a strategy.")


def _ca_block(cal: dict, recent: list) -> str:
    if not cal or not cal.get("rows"):
        return (C.empty("Nothing goes ex in the selected window — or the corporate-actions feed "
                        "hasn't landed on this host yet.") + C.learn(_CA_EDU))
    counts = cal.get("counts") or {}
    tiles = _tile("Going ex", '<span class="g-num">' + str(cal.get("n") or 0) + "</span>",
                  "in the next " + str(cal.get("window")) + " days")
    for t in R.CA_TYPES:
        if counts.get(t):
            tiles += _tile(_CA_LABEL.get(t, t.title()),
                           '<span class="g-num">' + str(counts[t]) + "</span>", "ex-dates ahead")
    body = ""
    for day in cal.get("days") or []:
        for i, r in enumerate(day.get("rows") or []):
            when = C.esc(day.get("d")) if i == 0 else ""
            ratio = ""
            if r.get("ratio_from") and r.get("ratio_to"):
                ratio = C.esc("%s : %s" % (r.get("ratio_to"), r.get("ratio_from")))
            body += ('<tr><td class="l k">' + when + "</td>"
                     '<td class="l">' + _sym(r.get("symbol")) + "</td>"
                     '<td class="l"><span class="gw2-pill">'
                     + C.esc(_CA_LABEL.get(str(r.get("action_type") or "").upper(),
                                           r.get("action_type") or "—")) + "</span></td>"
                     '<td class="l">' + ratio + "</td>"
                     '<td class="l">' + C.esc(str(r.get("details") or "")[:80]) + "</td></tr>")
    past = ""
    for r in recent or []:
        past += ('<tr><td class="l">' + C.esc(r.get("ex_date")) + "</td>"
                 '<td class="l k">' + _sym(r.get("symbol")) + "</td>"
                 '<td class="l">' + C.esc(r.get("action_type") or "—") + "</td></tr>")
    return ('<div class="gw2-tiles">' + tiles + "</div>"
            + _scroll(_table([("Ex-date", "l"), ("Symbol", "l"), ("Action", "l"),
                              ("Ratio", "l"), ("Detail", "l")], body))
            + (C.pro_more('<div class="gw2-lbl">Just went ex — and restructure context</div>'
                          + _scroll(_table([("Date", "l"), ("Symbol", "l"), ("Action", "l")], past),
                                    "sm")) if past else "")
            + _csv_note("/dash/home/events", "window=" + str(cal.get("window")))
            + C.learn(_CA_EDU))


def _results_block(board: dict, upcoming: list) -> str:
    up = ""
    for r in (upcoming or [])[:14]:
        up += ('<tr><td class="l">' + C.esc(r.get("meeting_date") or r.get("date") or "") + "</td>"
               '<td class="l k">' + _sym(r.get("symbol")) + "</td>"
               '<td class="l">' + C.esc(str(r.get("purpose") or "Results")[:60]) + "</td></tr>")
    up_html = ('<div class="gw2-lbl">Who reports next</div>'
               + _scroll(_table([("Board meeting", "l"), ("Symbol", "l"), ("Purpose", "l")], up),
                         "sm")) if up else ""
    if not board or not board.get("rows"):
        return (up_html + C.fence(_PEAD_FENCE)
                + C.empty("The results-reaction snapshot lives in the research database and is "
                          "built by the nightly job — it is not present on this host."))
    tiles = (_tile("Recent events", '<span class="g-num">' + str(board.get("n_all") or 0) + "</span>",
                   "in the snapshot")
             + _tile("Delivery-confirmed beats",
                     '<span class="g-num">' + str(board.get("n_confirmed") or 0) + "</span>",
                     "big surprise + heavy delivery")
             + _tile("Settled", '<span class="g-num">' + str(board.get("n_settled") or 0) + "</span>",
                     "full 60 sessions elapsed"))
    body = ""
    for r in board.get("rows") or []:
        beat, shi, dhi = r.get("beat"), r.get("sue_high"), r.get("deliv_high")
        if shi and dhi:
            lbl, cls = "top beat · delivery ✓", "up"
        elif shi:
            lbl, cls = "top beat", "up"
        elif beat and dhi:
            lbl, cls = "beat · delivery ✓", "up"
        elif beat:
            lbl, cls = "beat", ""
        elif dhi:
            lbl, cls = "miss · delivery ✓", "wn"
        else:
            lbl, cls = "in-line / miss", "dn"
        def pc(v):
            f = R._f(v)
            return _sn(f * 100.0, 1, "%") if f is not None else "—"
        body += ('<tr><td class="l">' + C.esc(r.get("t0")) + "</td>"
                 '<td class="l k">' + _sym(r.get("sym")) + "</td>"
                 '<td class="l"><span class="gw2-pill ' + cls + '">' + lbl + "</span></td>"
                 "<td>" + _sn(r.get("sue"), 2) + "</td>"
                 "<td>" + _n(r.get("deliv_x"), 2, "×") + "</td>"
                 "<td>" + pc(r.get("ear")) + "</td><td>" + pc(r.get("car22")) + "</td>"
                 "<td>" + pc(r.get("car60")) + "</td>"
                 '<td class="l">' + ("settled" if r.get("settled") else "accruing") + "</td></tr>")
    seg = _seg("/dash/home/events", "results",
               (("all", "All recent"), ("confirmed", "Delivery-confirmed top beats")),
               board.get("view") or "all")
    return (up_html + C.fence(_PEAD_FENCE) + '<div class="gw2-tiles">' + tiles + "</div>" + seg
            + _scroll(_table([("Reported", "l"), ("Symbol", "l"), ("Read", "l"), ("Surprise", "r"),
                              ("Delivery", "r"), ("Day move", "r"), ("22-day", "r"),
                              ("60-day", "r"), ("Status", "l")], body))
            + C.learn("Surprise is the seasonal net-profit surprise computed from the company's own "
                      "history — no analyst estimates are used. Delivery is the reaction window's "
                      "delivered value against the same stock's trailing median: the strong hand "
                      "showing up rather than intraday churn. The 22- and 60-day columns are the "
                      "REALIZED abnormal move versus the broad index, shown only once the window "
                      "has actually elapsed."))


def _cadence_block(pack: dict, evt: str) -> str:
    seg = _seg("/dash/home/events", "evt",
               tuple((k, ("All events" if k == "all" else k.replace("_", " ").title()))
                     for k in R.CADENCE_EVENTS), evt)
    if not pack:
        return seg + C.empty("The event-cadence snapshot hasn't been built on this host yet.")

    def tbl(rows, overdue):
        out = ""
        for r in rows:
            mid = (("%.0f wk" % abs(R._f(r.get("variance_weeks")) or 0)) if overdue
                   else C.esc(r.get("anchor") or "—"))
            out += ('<tr><td class="l k">' + _sym(r.get("symbol")) + "</td>"
                    '<td class="l">' + C.esc(str(r.get("event_type") or "").replace("_", " ").title())
                    + "</td><td>" + mid + "</td>"
                    '<td class="l">' + C.esc(r.get("lo") or "—") + " → " + C.esc(r.get("hi") or "—")
                    + "</td><td>" + str(r.get("n_history") or 0) + "</td></tr>")
        return _scroll(_table([("Symbol", "l"), ("Event", "l"),
                               ("Overdue by" if overdue else "Expected", "r"),
                               ("Window", "l"), ("Times seen", "r")],
                              out or '<tr><td class="l">none</td><td class="l">—</td><td>—</td>'
                                     '<td class="l">—</td><td>—</td></tr>'), "sm")
    over, exp = pack.get("overdue") or [], pack.get("expected") or []
    tiles = (_tile("Overdue", '<span class="g-num">' + str(len(over)) + "</span>",
                   "past their own window, nothing filed")
             + _tile("Expected soon", '<span class="g-num">' + str(len(exp)) + "</span>",
                     "within " + str(pack.get("horizon")) + " days")
             + _tile("Dormant", '<span class="g-num">' + str(pack.get("dormant") or 0) + "</span>",
                     "beyond " + str(pack.get("cap")) + " weeks — stopped, not late"))
    return (seg + '<div class="gw2-tiles">' + tiles + "</div>"
            + '<div class="gw2-two"><div><div class="gw2-lbl">Overdue vs their own rhythm</div>'
            + tbl(over, True) + "</div><div><div class=\"gw2-lbl\">Expected by cadence</div>"
            + tbl(exp, False) + "</div></div>"
            + C.learn("This is the additive cut beside the two announced calendars: not what has "
                      "been declared, but what a company's OWN past rhythm says should have arrived "
                      "by now. Timing only, measured in weeks — factual event cadence, never a "
                      "price prediction."))


_BB_JS = """<script>(function(){
var f=document.getElementById("gw2-bb"); if(!f) return;
function num(id){var e=document.getElementById(id); var v=e?parseFloat(e.value):NaN; return isNaN(v)?0:v;}
function money(v){return (v<0?"−₹":"₹")+Math.abs(v).toLocaleString("en-IN",{maximumFractionDigits:0});}
function calc(){
  var sh=num("gw2-sh"),cost=num("gw2-cost"),bb=num("gw2-bb-price"),ex=num("gw2-exit"),a=num("gw2-acc")/100;
  a=Math.max(0,Math.min(1,a));
  var acc=Math.round(sh*a), res=sh-acc;
  var tender=acc*(bb-cost), residual=res*(ex-cost), net=tender+residual;
  var be=(a<1)?(cost-a*(bb-cost)/(1-a)):cost;
  var out={"gw2-o-acc":acc.toLocaleString("en-IN"),"gw2-o-tender":money(tender),
           "gw2-o-res":money(residual),"gw2-o-net":money(net),
           "gw2-o-be":(a<1?money(be):"n/a — full acceptance")};
  for(var k in out){var e=document.getElementById(k); if(e) e.textContent=out[k];}
  var cap=document.getElementById("gw2-o-cap");
  if(cap){var val=sh*cost; cap.textContent=money(val)+(val>200000?"  — above the ₹2,00,000 small-shareholder line":"  — within the ₹2,00,000 small-shareholder line");}
}
f.addEventListener("input",calc); calc();})();</script>"""


def _buyback_block(rows: list) -> str:
    def fld(fid, label, val, step="1"):
        return ('<div><label for="' + fid + '">' + C.esc(label) + "</label>"
                '<input id="' + fid + '" type="number" step="' + step + '" value="' + C.esc(val)
                + '" inputmode="decimal"></div>')
    form = ('<form id="gw2-bb" class="gw2-form" onsubmit="return false">'
            + fld("gw2-sh", "Shares held", "500")
            + fld("gw2-cost", "Your cost / share (₹)", "300", "0.05")
            + fld("gw2-bb-price", "Buyback price (₹)", "400", "0.05")
            + fld("gw2-exit", "Assumed exit for the rest (₹)", "300", "0.05")
            + fld("gw2-acc", "Acceptance ratio (%)", "35", "1")
            + "</form>")
    outs = ""
    for oid, label in (("gw2-o-acc", "Shares accepted"), ("gw2-o-tender", "Tender profit"),
                       ("gw2-o-res", "Residual P&L"), ("gw2-o-net", "Net P&L"),
                       ("gw2-o-be", "Breakeven exit"), ("gw2-o-cap", "Holding value")):
        outs += ('<div class="gw2-tile"><div class="n" id="' + oid + '">—</div>'
                 '<div class="l">' + C.esc(label) + "</div></div>")
    tbl = ""
    for r in rows or []:
        tbl += ('<tr><td class="l k">' + _sym(r.get("symbol")) + "</td>"
                '<td class="l">' + C.esc(r.get("ex_date") or "—") + "</td>"
                '<td class="l">' + C.esc(r.get("record_date") or "—") + "</td>"
                "<td>" + (_n(r.get("price"), 2) if r.get("price") else "—") + "</td>"
                '<td class="l">' + C.esc(str(r.get("details") or "")[:70]) + "</td></tr>")
    anchor = (('<div class="gw2-lbl">Buybacks on the corporate-actions feed</div>'
               + _scroll(_table([("Symbol", "l"), ("Ex-date", "l"), ("Record date", "l"),
                                 ("Price", "r"), ("Detail", "l")], tbl), "sm"))
              if tbl else C.empty("No buyback rows on the feed for the last year."))
    return (form + '<div class="gw2-out">' + outs + "</div>" + _BB_JS + anchor
            + C.fence("The acceptance ratio is YOUR assumption. Companies publish the realized "
                      "accepted-versus-tendered ratio only after an offer closes and it is not in "
                      "our data — we refuse to fabricate a prior, so change the number and watch "
                      "the answer move. Eligibility for the reserved category is holdings worth "
                      "₹2,00,000 or less ON THE RECORD DATE, so size with a buffer: a rally into "
                      "the record date can push you over the line. Arithmetic, not advice.")
            + C.learn("SEBI reserves 15% of every tender buyback for small shareholders — holdings "
                      "worth ₹2,00,000 or less by market value on the record date. That reservation "
                      "gives small holders a structurally better acceptance ratio than the general "
                      "category, and it survives precisely BECAUSE it is capped per person: "
                      "institutions cannot reach it. Personal-scale arithmetic."))


_SURVEIL_FENCE = ("Context, never a gate. A name entering the exchange's surveillance measures "
                  "often sees mechanically forced flows — leveraged positions unwinding under 100% "
                  "margins or trade-to-trade settlement. That is information about plumbing, not a "
                  "verdict on the company, and no study has been run on this feed in either "
                  "direction.")


def _surveillance_block(pack: dict) -> str:
    if not pack:
        return (C.fence(_SURVEIL_FENCE)
                + C.empty("The surveillance feed hasn't landed on this host yet."))
    cur = pack.get("current") or {}
    tiles = _tile("Transitions", '<span class="g-num">' + str(pack.get("n_events") or 0) + "</span>",
                  "in the last " + str(pack.get("days")) + " days")
    tiles += _tile("Names flagged", '<span class="g-num">' + str(pack.get("n_flagged") or 0) + "</span>",
                   "with any move in the window")
    for fw in ("ASM-LT", "ASM-ST", "GSM"):
        if cur.get(fw):
            tiles += _tile(fw.replace("-", " · "),
                           '<span class="g-num">' + str(len(cur[fw])) + "</span>", "under it now")
    if cur.get("BAND"):
        tiles += _tile("Tight bands", '<span class="g-num">' + str(len(cur["BAND"])) + "</span>",
                       "names on a 2% or 5% band")
    body = ""
    for e in pack.get("events") or []:
        d = e.get("direction")
        cls = "dn" if d == "up" else ("up" if d == "down" else "")
        mark = "▲" if d == "up" else ("▽" if d == "down" else "→")
        move = C.esc("%s → %s" % (e.get("frm") or "—", e.get("to") or "—"))
        body += ('<tr><td class="l">' + C.esc(e.get("d")) + "</td>"
                 '<td class="l k">' + _sym(e.get("symbol")) + "</td>"
                 '<td class="l"><span class="gw2-pill">' + C.esc(e.get("kind")) + "</span></td>"
                 '<td class="l ' + cls + '">' + mark + " " + C.esc(e.get("what")) + "</td>"
                 '<td class="l">' + move + "</td></tr>")
    return ('<div class="gw2-tiles">' + tiles + "</div>"
            + _scroll(_table([("Date", "l"), ("Symbol", "l"), ("Framework", "l"),
                              ("Move", "l"), ("Stage", "l")], body))
            + C.fence(_SURVEIL_FENCE)
            + C.learn("ASM and GSM are the exchange's Additional and Graded Surveillance Measures: "
                      "stage-based curbs — higher margins, trade-to-trade settlement, trading "
                      "restrictions — applied to names with unusual price or volume behaviour. A "
                      "narrower price band means the stock may move less before trading halts."))


def _bandlock_fence(birth: str = "") -> str:
    return C.fence("A close-at-band streak is a queue-imbalance tell — context, never a gate. No "
                   "study exists on band-lock streaks in either direction; any drift or return "
                   "claim would need its own pre-registered test first. The honest window: bands "
                   "are reconstructable only back to the feed's first captured day"
                   + ((" (" + str(birth) + ")") if birth else "")
                   + ", so this board deepens every trading night and never fabricates earlier "
                     "history.")


def _bandlock_block(pack: dict) -> str:
    if not pack:
        return (_bandlock_fence()
                + C.empty("The price-band feed hasn't landed on this host yet."))
    tiles = (_tile("Locked up", '<span class="g-num up">' + str(pack.get("up") or 0) + "</span>",
                   "closed at the upper band")
             + _tile("Locked down", '<span class="g-num dn">' + str(pack.get("down") or 0) + "</span>",
                     "closed at the lower band")
             + _tile("On streaks", '<span class="g-num">' + str(pack.get("n_flagged") or 0) + "</span>",
                     str(pack.get("min_streak")) + "+ consecutive days")
             + _tile("Window", '<span class="g-num">' + str(pack.get("n_days") or 0) + "</span>",
                     "sessions since " + C.esc(pack.get("feed_birth") or "")))
    body = ""
    for s in pack.get("streaks") or []:
        up = s.get("dir") == "up"
        body += ('<tr><td class="l k">' + _sym(s.get("symbol")) + "</td>"
                 '<td class="l"><span class="gw2-pill ' + ("up" if up else "dn") + '">'
                 + ("▲ upper" if up else "▼ lower") + "</span></td>"
                 "<td>" + str(s.get("days") or 0) + "d</td>"
                 "<td>" + _n(s.get("band"), 0, "%") + "</td>"
                 "<td>" + _sn(s.get("move_pct"), 2, "%") + "</td>"
                 '<td class="l">' + C.esc(s.get("first_date") or "") + "</td></tr>")
    return ('<div class="gw2-tiles">' + tiles + "</div>"
            + _scroll(_table([("Symbol", "l"), ("Direction", "l"), ("Streak", "r"),
                              ("Band", "r"), ("Move over streak", "r"), ("Since", "l")], body), "sm")
            + _bandlock_fence(pack.get("feed_birth") or "")
            + C.learn("Every stock has a daily price band — the most it may move before trading "
                      "halts. A name that CLOSED at that limit had more buyers (or sellers) queued "
                      "than the band allowed to transact. Consecutive days of it means the "
                      "imbalance kept going."))


def _events_body(conn, window: int, sym: str, evt: str, results_view: str) -> str:
    from src.web.home import reads
    cal = R.ca_calendar(conn, days=window, sym=sym)
    recent = R.ca_recent(conn)
    board = R.results_board(conn, view=results_view)
    upcoming = reads.upcoming_results(days=30)
    cadence = R.event_cadence(conn, evt=evt)
    surveil = R.surveillance_tape(conn)
    locks = R.band_locks(conn)
    wseg = _seg("/dash/home/events", "window", ((30, "30 days"), (60, "60 days"), (120, "120 days")),
                window)
    return (C.fence(_EVENTS_FENCE)
            + C.zone("Going ex — the corporate-actions calendar", "corporate_actions · nightly",
                     wseg + _ca_block(cal, recent),
                     sub="dividends · bonuses · splits · rights · buybacks", name="Going ex")
            + C.zone("Results and what happened after", "results_reactions · nightly",
                     _results_block(board, upcoming),
                     sub="the surprise, the delivery behind it, the realized drift", name="Results")
            + C.zone("Event cadence — who is overdue against their own rhythm",
                     "seasonal_events · snapshot", _cadence_block(cadence, evt),
                     sub="timing only, measured in weeks", name="Event cadence")
            + C.zone("Buyback tender calculator", "corporate_actions · nightly",
                     _buyback_block(R.buyback_rows(conn)),
                     sub="the reserved small-shareholder category, done as arithmetic",
                     name="Buyback calculator")
            + C.zone("Surveillance transitions", "surveillance_flags · nightly",
                     _surveillance_block(surveil),
                     sub="ASM · GSM · price-band moves", name="Surveillance")
            + C.zone("Band locks", "price_bands_current · nightly", _bandlock_block(locks),
                     sub="names pinned at their daily limit", name="Band locks"))


@router.get("/dash/home/events", response_class=HTMLResponse, include_in_schema=False)
def events_page(request: Request):
    """Events & restrictions — the corporate-actions calendar, the results-reaction board, event
    cadence, the buyback tender calculator, surveillance transitions and band locks. Consolidates
    six classic Markets lenses. Read-only; never 500s."""
    from src.core.db import get_conn
    try:
        window = int(request.query_params.get("window", 30))
    except (TypeError, ValueError):
        window = 30
    if window not in (30, 60, 120):
        window = 30
    sym = str(request.query_params.get("sym", ""))[:24]
    evt = request.query_params.get("evt", "all")
    if evt not in R.CADENCE_EVENTS:
        evt = "all"
    rview = request.query_params.get("results", "all")
    if rview not in ("all", "confirmed"):
        rview = "all"
    fmt = request.query_params.get("format", "")
    body, pat = "", ""
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            if fmt == "csv":
                cal = R.ca_calendar(conn, days=window, sym=sym)
                return _csv([(r.get("ex_date"), r.get("symbol"), r.get("action_type"),
                              r.get("record_date"), r.get("ratio_from"), r.get("ratio_to"),
                              r.get("details")) for r in (cal.get("rows") or [])],
                            ["ex_date", "symbol", "action", "record_date", "ratio_from",
                             "ratio_to", "detail"])
            body = _events_body(conn, window, sym, evt, rview)
            pat = _dock(conn)
    except Exception:  # noqa: BLE001
        body = (C.fence("The events estate hasn't landed on this host yet.")
                + C.empty("Check back after the next nightly run."))
    return _page("Events & restrictions", "events", body, pat)


# ══════════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — /dash/home/attention
# ══════════════════════════════════════════════════════════════════════════════════════
_ATTENTION_FENCE = (
    "An event here is a derived judgement that something CHANGED — never a recommendation. "
    "Magnitude ranks attention within a single batch; it is not a return forecast, and no study "
    "exists on what follows one of these events. The lenses' own fences ride along: concall "
    "credibility is descriptive-only, the accumulation tape is a descriptor (D62), and bulk/block "
    "deal prints are logistics."
)


def _attention_rows(pack: dict) -> str:
    rows = pack.get("rows") or []
    if not rows:
        return C.empty("No state-changes fired in this batch.")
    body = ""
    for r in rows:
        lens = str(r.get("lens") or "")
        label = C.LENS_LABELS.get(lens, lens.upper() or "signal")
        d = str(r.get("direction") or "")
        cls = "up" if d == "up" else ("dn" if d == "down" else "")
        move = C.esc("%s → %s" % (r.get("from_state") or "—", r.get("to_state") or "—"))
        mag = R._f(r.get("magnitude"))
        body += ('<tr><td class="l k">' + _sym(r.get("symbol")) + "</td>"
                 '<td class="l"><span class="gw2-pill">' + C.esc(label) + "</span></td>"
                 '<td class="l ' + cls + '">'
                 + C.esc(str(r.get("event_type") or "").replace("_", " ")) + "</td>"
                 '<td class="l">' + move + "</td>"
                 "<td>" + (_n(mag, 2) if mag is not None else "—") + "</td>"
                 '<td class="l">' + C.esc(str(r.get("note") or "")[:90]) + "</td></tr>")
    return _scroll(_table([("Symbol", "l"), ("Lens", "l"), ("What changed", "l"),
                           ("From → to", "l"), ("Magnitude", "r"), ("Note", "l")], body), "lg")


def _attention_block(pack: dict) -> str:
    if not pack:
        return C.empty("The signal-event bus is empty on this host — it fills on the nightly run.")
    tiles = (_tile("In this batch", '<span class="g-num">' + str(pack.get("n_batch") or 0) + "</span>",
                   "state-changes on " + C.esc(pack.get("batch") or ""))
             + _tile("On record", '<span class="g-num">' + str(pack.get("total") or 0) + "</span>",
                     "events across every batch"))
    for lens, n in list((pack.get("per_lens") or {}).items())[:3]:
        tiles += _tile(C.LENS_LABELS.get(lens, lens.upper()),
                       '<span class="g-num">' + str(n) + "</span>", "in this batch")
    chips = ("<a" + ("" if pack.get("lens") else ' class="on" aria-current="true"')
             + ' href="/dash/home/attention">All lenses</a>')
    for lens in R.ATTENTION_LENSES:
        n = (pack.get("per_lens") or {}).get(lens)
        if not n:
            continue
        on = ' class="on" aria-current="true"' if pack.get("lens") == lens else ""
        chips += ("<a" + on + ' href="/dash/home/attention?lens=' + lens + '">'
                  + C.esc(C.LENS_LABELS.get(lens, lens.upper())) + " " + str(n) + "</a>")
    replay = ""
    if pack.get("replay"):
        replay = ('<div class="gw2-read">You asked for <b>' + C.esc(pack.get("asked"))
                  + "</b>; the nearest batch on or before that date is <b>"
                  + C.esc(pack.get("batch")) + "</b>. An exact-date miss is shown as the batch it "
                  "resolved to — it never reads as an empty tape.</div>")
    hist = ""
    for b in (pack.get("batches") or [])[:12]:
        by = b.get("by_lens") or {}
        hist += ('<tr><td class="l k">' + C.esc(b.get("as_of")) + "</td>"
                 "<td>" + str(sum(by.values())) + "</td>"
                 '<td class="l">' + C.esc(" · ".join("%s %d" % (k, v) for k, v in by.items()))
                 + "</td></tr>")
    return ('<div class="gw2-tiles">' + tiles + "</div>" + replay
            + '<div class="gw2-seg">' + chips + "</div>" + _attention_rows(pack)
            + C.pro_more('<div class="gw2-lbl">Recent batches</div>'
                         + _scroll(_table([("Batch", "l"), ("Events", "r"), ("By lens", "l")], hist),
                                   "sm"))
            + _csv_note("/dash/home/attention",
                        ("lens=" + C.esc(pack.get("lens"))) if pack.get("lens") else "")
            + C.learn("Every lens on this site emits a typed event when a name's state flips — a "
                      "relative-strength band break, an accumulation phase change, a credibility "
                      "step, a positioning flip. This is all of them in one tape, ranked by how "
                      "big the change was, with the raw before and after beside each verdict."))


def _alerts_block(pack: dict) -> str:
    if not pack:
        return C.empty("No curated alerts on this host yet.")
    counts = pack.get("counts") or {}
    sev = pack.get("severity") or {}
    band = C.count_band(sev)
    body = ""
    for a in pack.get("alerts") or []:
        s = a.get("severity")
        cls = "dn" if s == "critical" else "wn"
        val = a.get("valence")
        vcls = "up" if val == "opportunity" else ("dn" if val == "risk" else "")
        body += ('<tr><td class="l k">' + _sym(a.get("symbol")) + "</td>"
                 '<td class="l"><span class="gw2-pill ' + cls + '">' + C.esc(s or "") + "</span></td>"
                 '<td class="l ' + vcls + '">' + C.esc(val or "neutral") + "</td>"
                 '<td class="l">' + C.esc(C.LENS_LABELS.get(a.get("lens"),
                                                            str(a.get("lens") or "").upper())) + "</td>"
                 '<td class="l">' + C.esc("%s → %s" % (a.get("from_state") or "—",
                                                       a.get("to_state") or "—")) + "</td>"
                 '<td class="l">' + C.esc(a.get("as_of") or "") + "</td></tr>")
    total = counts.get("total", 0)
    return (band + '<p class="gw2-csv">' + str(total) + " active alert(s) in the last "
            + str(pack.get("days")) + " days.</p>"
            + _scroll(_table([("Symbol", "l"), ("Severity", "l"), ("Reads as", "l"),
                              ("Lens", "l"), ("From → to", "l"), ("Date", "l")], body), "sm")
            + C.learn("The rail is the short list, not the firehose: only the highest-impact "
                      "state-changes are promoted onto it, each fires once, and it is kept as it "
                      "rolls past today's batch. Dismissing an alert is an owner action and stays "
                      "on the classic review page — this view is read-only."))


def _attention_body(conn, as_of: str, lens: str) -> str:
    pack = R.attention_queue(conn, as_of=as_of, lens=lens)
    rail = R.alert_rail(conn)
    return (C.fence(_ATTENTION_FENCE)
            + C.zone("The alert rail", "signal_alert_state · nightly", _alerts_block(rail),
                     sub="the curated, severity-graded short list", name="Alert rail")
            + C.zone("The attention queue", "signal_events · nightly", _attention_block(pack),
                     sub="every lens's state-changes, ranked by size of change", name="Attention queue"))


@router.get("/dash/home/attention", response_class=HTMLResponse, include_in_schema=False)
def attention_page(request: Request):
    """What changed — the full, magnitude-ranked attention queue plus the curated alert rail; the
    depth behind the Graphite home's "What changed today" band. Ports the classic /dash/attention.
    `?as_of=` replays any past batch (last-batch-on-or-before). Read-only; never 500s."""
    from src.core.db import get_conn
    as_of = str(request.query_params.get("as_of", ""))[:10]
    lens = request.query_params.get("lens", "")
    if lens not in R.ATTENTION_LENSES:
        lens = ""
    fmt = request.query_params.get("format", "")
    body, pat = "", ""
    try:
        with get_conn() as conn:
            conn.row_factory = __import__("sqlite3").Row
            if fmt == "csv":
                pack = R.attention_queue(conn, as_of=as_of, lens=lens, limit=500)
                return _csv([(r.get("as_of"), r.get("symbol"), r.get("lens"), r.get("event_type"),
                              r.get("direction"), r.get("from_state"), r.get("to_state"),
                              r.get("magnitude"), r.get("note"))
                             for r in (pack.get("rows") or [])],
                            ["batch", "symbol", "lens", "event", "direction", "from", "to",
                             "magnitude", "note"])
            body = _attention_body(conn, as_of, lens)
            pat = _dock(conn)
    except Exception:  # noqa: BLE001
        body = (C.fence("The signal-event bus hasn't landed on this host yet.")
                + C.empty("Check back after the next nightly run."))
    return _page("What changed", "attention", body, pat)


def _selftest() -> int:
    """Offline structure check — proves every page renders end-to-end against the live DB
    (empty or populated) with the Graphite marker and no legacy/preview marker."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    for path in ("/dash/home/internals", "/dash/home/flows", "/dash/home/events",
                 "/dash/home/attention"):
        r = c.get(path)
        assert r.status_code == 200, (path, r.status_code)
        assert "data-ui-g" in r.text and "gw2-sub" in r.text, path
        for bad in ("data-ui-v3", "pv3-", 'id="uk-main"'):
            assert bad not in r.text, (path, bad)
        assert c.get(path + "?format=csv").status_code == 200, path
    print("home/internals_pages selftest OK — 4 pages + 4 CSVs render, Graphite-scoped, "
          "no legacy markers  (" + _dt.date.today().isoformat() + ")")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
